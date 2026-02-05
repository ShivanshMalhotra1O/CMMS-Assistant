from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
from pathlib import Path
from dotenv import load_dotenv
import yaml
import json
import hashlib
import time

from app.cache.exact_query_cache import (
    get_cached_pipeline,
    set_cached_pipeline,
    make_cache_key
)
from app.memory.query_memory import (
    retrieve_similar_queries,
    store_query_memory,
    hash_registry
)

load_dotenv()


def escape_braces(text: str) -> str:
    """Escape braces for LangChain prompt templates"""
    return text.replace("{", "{{").replace("}", "}}")


def estimate_tokens(text: str) -> int:
    """Estimate token count using simple heuristic"""
    return len(text) // 4


def build_experience_block(examples: list[dict]) -> str:
    """Build experience block from similar past queries"""
    if not examples:
        return ""

    lines = [
        "====================================",
        "PAST SUCCESSFUL QUERIES (GUIDANCE ONLY)",
        "Use these as reference patterns.",
        "DO NOT copy blindly.",
        "====================================\n"
    ]

    for ex in examples:
        lines.append("User Query:")
        lines.append(str(ex["user_query"]))
        lines.append("Mongo Pipeline:")
        
        pipeline = ex["pipeline"]
        if not isinstance(pipeline, str):
            pipeline = json.dumps(pipeline, ensure_ascii=False)
        
        pipeline = escape_braces(pipeline)
        lines.append(pipeline)
        lines.append("")

    return "\n".join(lines)


class TaskerAgent:
    def __init__(self):
        """Initialize the TaskerAgent with cache and memory"""
        
        # Load registry
        BASE_DIR = Path(__file__).resolve().parents[1]
        registry_path = BASE_DIR / "registry" / "registry.yaml"
        
        if not registry_path.exists():
            raise FileNotFoundError(f"Registry not found at {registry_path}")
        
        self.registry_text = registry_path.read_text(encoding="utf-8")
        self.registry = yaml.safe_load(self.registry_text)
        
        # Create registry hash
        self.registry_hash = hash_registry(self.registry_text)
        
        # Model name for cache/memory
        self.model_name = "gpt-oss:latest"
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=self.model_name,
            base_url=os.getenv("LLM_BASE_URL"),
            api_key=os.getenv("LLM_API_KEY", "dummy"),
            temperature=0
        )

        # Token tracking
        self.last_metrics = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "llm_used": False,
            "cache_hit": False,
            "examples_used": 0
        }

        # System prompt (without experience block placeholder)
        system_prompt_raw = """
You are an expert MongoDB aggregation query generator for a CMMS system.

You are provided with a YAML registry that is the SINGLE SOURCE OF TRUTH.
Anything defined in the registry MUST be used exactly as specified.
You are NOT allowed to invent, assume, normalize, or infer any field names,
enum values, statuses, or constants that are not explicitly present
in the registry.

====================================================
YAML REGISTRY (AUTHORITATIVE)
====================================================
{registry}
====================================================

CRITICAL OUTPUT CONTRACT (ABSOLUTE):

1. You MUST output a JSON ARRAY.
2. NEVER output a single JSON object.
3. Even for a single stage, wrap it in an array.
4. Output MUST be valid JSON only (no markdown, no comments).

SCHEMA & VALUE ENFORCEMENT (MANDATORY):

- You MUST ONLY use:
  - Fields that exist in the registry
  - Enum values that exist in the registry
- You MUST NOT:
  - Invent domain values (e.g. "Operational", "Running", "Active" unless defined)
  - Guess or map human-friendly synonyms
  - Expand enums beyond what is listed

If a user request implies a value that DOES NOT exist in the registry:
- DO NOT guess
- DO NOT approximate
- Instead, fall back to the closest valid registry-safe query
  (e.g. omit the invalid filter and explain via structure, not text)

IMPORTANT:
- Use normal JSON syntax in your output
- Do NOT include angle brackets or symbolic notation
- Always return an array
- When in doubt, be STRICT and REGISTRY-SAFE
- Always add a filter for deleted: false or deleted: {$ne: true} to exclude deleted records

IMPORTANT SCHEMA NOTE:

- Work order assignment is represented by the `people` field.
- The `people` field is an array of user `_id` values.
- For queries involving "assigned to", "technician", or "responsible",
  you MUST use the `people` field.
- For input that contains work order id and if it contains id (like WO 22) then add - automatically after WO (it will become WO-22) and then pass this to db in query.
- For queries where we are asking details about people or related to people database , then always mention people name, department and   userTitle.

[{"$match": {"deleted": {"$ne": true}}}]
```

Which returns ALL non-deleted PMs instead of just upcoming ones.

## The Fix:

Your pipeline generation prompt needs to tell the LLM to use MongoDB's date operators, not JavaScript `new Date()`.

**Add this to your pipeline generation prompt:**
```
CRITICAL: Date Handling in MongoDB Pipelines

When comparing dates in MongoDB aggregation pipelines:
- DO NOT use `new Date()` - this is invalid JSON
- USE MongoDB aggregation expressions for current date:
  - For match stage: Use `$$NOW` system variable
  - Or use ISODate string format: "2026-01-09T00:00:00.000Z"

Examples:

❌ WRONG (invalid JSON):
{"nextGenerationDate": {"$gte": new Date()}}

✅ CORRECT (using $$NOW):
{
  "$expr": {
    "$gte": ["$nextGenerationDate", "$$NOW"]
  }
}

✅ CORRECT (using date comparison with current date as string):
For "upcoming" queries, generate the current date as an ISO string in the pipeline.

For preventive maintenance "upcoming" queries specifically:
[
  {
    "$match": {
      "deleted": false,
      "$expr": {
        "$gte": ["$nextGenerationDate", "$$NOW"]
      }
    }
  },
  { "$sort": { "nextGenerationDate": 1 } }
]

------------------------------------
USER REQUEST
------------------------------------
{user_input}

------------------------------------
Generate the MongoDB aggregation pipeline now.
"""
        
        # Escape braces, then re-enable placeholders
        system_prompt_escaped = escape_braces(system_prompt_raw)
        system_prompt_escaped = system_prompt_escaped.replace("{{registry}}", "{registry}")
        system_prompt_escaped = system_prompt_escaped.replace("{{user_input}}", "{user_input}")
        
        self.base_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt_escaped)
        ])
        
        # Prompt with experience
        prompt_with_exp = system_prompt_escaped + "\n\n{experience_block}"
        self.prompt_with_experience = ChatPromptTemplate.from_messages([
            ("system", prompt_with_exp)
        ])
        
        print(f"DEBUG → TaskerAgent initialized with registry hash: {self.registry_hash[:8]}")

    def run(self, user_input: str, resource: str = "workorders") -> str:
        """Generate MongoDB aggregation pipeline from natural language"""
        
        start_time = time.time()
        
        # 1. Check exact cache first
        cache_key = make_cache_key(
            model=self.model_name,
            query=user_input,
            registry_hash=self.registry_hash
        )
        
        cached_pipeline = get_cached_pipeline(cache_key)
        
        if cached_pipeline:
            print(f"⚡ CACHE HIT for query: '{user_input[:50]}...'")
            
            self.last_metrics = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "llm_used": False,
                "cache_hit": True,
                "examples_used": 0
            }
            
            return cached_pipeline
        
        print(f"🔍 CACHE MISS - Checking memory for similar queries...")
        
        # 2. Retrieve similar queries from memory
        examples = retrieve_similar_queries(
            user_query=user_input,
            registry_text=self.registry_text,
            model=self.model_name,
            top_k=3
        )
        
        examples_used = len(examples)
        
        if examples_used > 0:
            print(f"💡 Found {examples_used} similar past queries to guide generation")
        
        try:
            escaped_registry = escape_braces(self.registry_text)
            
            # Choose prompt based on whether we have examples
            if examples:
                experience_block = build_experience_block(examples)
                formatted_prompt = self.prompt_with_experience.format_messages(
                    registry=escaped_registry,
                    user_input=user_input,
                    experience_block=experience_block
                )
            else:
                formatted_prompt = self.base_prompt.format_messages(
                    registry=escaped_registry,
                    user_input=user_input
                )

            # Estimate prompt tokens
            prompt_text = formatted_prompt[0].content if formatted_prompt else ""
            prompt_tokens = estimate_tokens(prompt_text)
            
            # Call LLM
            response = self.llm.invoke(formatted_prompt)
            pipeline_text = response.content.strip()
            
            # Estimate completion tokens
            completion_tokens = estimate_tokens(pipeline_text)
            total_tokens = prompt_tokens + completion_tokens
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Store metrics
            self.last_metrics = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "llm_used": True,
                "cache_hit": False,
                "examples_used": examples_used
            }
            
            print(f"DEBUG → Token Usage (est): ~{total_tokens} tokens "
                  f"(prompt: ~{prompt_tokens}, completion: ~{completion_tokens})")
            
            # Remove markdown code blocks if present
            if pipeline_text.startswith("```"):
                lines = pipeline_text.split("\n")
                pipeline_text = "\n".join(lines[1:-1]) if len(lines) > 2 else pipeline_text
                pipeline_text = pipeline_text.strip()
            
            # Validate JSON and ensure deleted filter
            try:
                pipeline = json.loads(pipeline_text)
                if isinstance(pipeline, dict):
                    pipeline = [pipeline]
                
                if not pipeline or len(pipeline) == 0:
                    pipeline = [{"$match": {"deleted": {"$ne": True}}}]
                
                # Ensure deleted filter is in the first $match stage
                has_deleted_filter = False
                for stage in pipeline:
                    if "$match" in stage:
                        match_stage = stage["$match"]
                        if "deleted" in match_stage:
                            has_deleted_filter = True
                            # Ensure it filters out deleted records
                            if match_stage["deleted"] not in [False, {"$ne": True}, {"$eq": False}]:
                                match_stage["deleted"] = {"$ne": True}
                        break
                
                # If no deleted filter exists, add it to first $match or create new $match
                if not has_deleted_filter:
                    for stage in pipeline:
                        if "$match" in stage:
                            stage["$match"]["deleted"] = {"$ne": True}
                            has_deleted_filter = True
                            break
                    
                    # If still no $match stage, add one at the beginning
                    if not has_deleted_filter:
                        pipeline.insert(0, {"$match": {"deleted": {"$ne": True}}})
                
                pipeline_text = json.dumps(pipeline, ensure_ascii=False)
                print(f"DEBUG → Ensured deleted filter in pipeline")
                
            except json.JSONDecodeError as e:
                print(f"DEBUG → JSON validation failed: {e}")
                print(f"DEBUG → Raw pipeline: {pipeline_text}")
                pipeline_text = '[{"$match": {"deleted": {"$ne": true}}}]'
            
            # 3. Cache the successful result
            set_cached_pipeline(cache_key, pipeline_text)
            print(f"💾 Cached pipeline for future use")
            
            # 4. Store in memory for future similar queries
            try:
                store_query_memory(
                    user_query=user_input,
                    resource=resource,
                    pipeline=pipeline_text,
                    model=self.model_name,
                    registry_text=self.registry_text,
                    execution_time_ms=execution_time_ms
                )
            except Exception as e:
                print(f"⚠️ Failed to store in memory: {e}")
            
            print("DEBUG → Generated Pipeline:", pipeline_text)
            return pipeline_text
            
        except Exception as e:
            print(f"❌ TaskerAgent Error: {type(e).__name__}: {e}")
            
            # Reset metrics for fallback
            self.last_metrics = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "llm_used": False,
                "cache_hit": False,
                "examples_used": 0
            }
            
            fallback = '[{"$match": {"deleted": {"$ne": true}}}]'
            
            # Cache the fallback too
            set_cached_pipeline(cache_key, fallback)
            
            return fallback
    
    def get_metrics(self) -> dict:
        """Get the metrics from the last run"""
        return self.last_metrics.copy()