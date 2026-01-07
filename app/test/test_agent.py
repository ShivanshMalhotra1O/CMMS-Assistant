from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
from pathlib import Path
from dotenv import load_dotenv
import time
import json

from app.memory.query_memory import retrieve_similar_queries, hash_registry
from app.cache.exact_query_cache import (
    get_cached_pipeline,
    set_cached_pipeline,
    make_cache_key
)
from app.query.mongo_executor import MongoExecutor   
import yaml
import re


load_dotenv()

# -------------------------------------------------------------------
# 1️⃣ LOAD REGISTRY
# -------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
REGISTRY_PATH = BASE_DIR / "registry" / "registry.yaml"

if not REGISTRY_PATH.exists():
    raise FileNotFoundError(f"Registry not found at {REGISTRY_PATH}")

REGISTRY_TEXT = REGISTRY_PATH.read_text(encoding="utf-8")
REGISTRY_HASH = hash_registry(REGISTRY_TEXT)
def parse_registry(registry_text: str) -> dict:
    return yaml.safe_load(registry_text)["collections"]

REGISTRY = parse_registry(REGISTRY_TEXT)

# -------------------------------------------------------------------
# 2️⃣ SYSTEM PROMPT (NO RAW BRACES)
# -------------------------------------------------------------------

SYSTEM_PROMPT = """
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

EXAMPLE (Valid, symbolic structure only):
[
  <$match : <deleted : false>>,
  <$limit : 20>
]

IMPORTANT:
- Use normal JSON syntax in your output
- Do NOT include angle brackets
- Always return an array
- When in doubt, be STRICT and REGISTRY-SAFE

IMPORTANT SCHEMA NOTE:

- Work order assignment is represented by the `people` field.
- The `people` field is an array of user `_id` values.
- For queries involving "assigned to", "technician", or "responsible",
  you MUST use the `people` field.
  
"""

def build_semantic_index(registry: dict) -> dict:
    index = {}
    for collection, spec in registry.items():
        for field, field_spec in spec.get("fields", {}).items():
            semantics = field_spec.get("semantics")
            if semantics:
                index.setdefault(semantics.lower(), []).append({
                    "collection": collection,
                    "field": field
                })
    return index

SEMANTIC_INDEX = build_semantic_index(REGISTRY)

def apply_semantic_repairs(pipeline: list[dict], user_query: str) -> list[dict]:
    tokens = set(re.findall(r"[a-zA-Z]+", user_query.lower()))

    for semantic, targets in SEMANTIC_INDEX.items():
        if semantic not in tokens:
            continue

        for target in targets:
            field = target["field"]

            # Fix incorrect lookups
            for stage in pipeline:
                if "$lookup" in stage:
                    stage["$lookup"]["localField"] = field

            # Ensure lookup exists if missing
            if not any("$lookup" in s for s in pipeline):
                pipeline.insert(0, {
                    "$lookup": {
                        "from": "users",
                        "localField": field,
                        "foreignField": "_id",
                        "as": "resolvedUsers"
                    }
                })

    return pipeline



# -------------------------------------------------------------------
# 3️⃣ EXPERIENCE BLOCK BUILDER
# -------------------------------------------------------------------

def escape_braces(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")


def build_experience_block(examples: list[dict]) -> str:
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

# -------------------------------------------------------------------
# 4️⃣ LLM SETUP
# -------------------------------------------------------------------

MODEL_NAME = "gpt-oss:latest"

llm = ChatOpenAI(
    model=MODEL_NAME,
    base_url=os.getenv("LLM_BASE_URL"),
    api_key=os.getenv("LLM_API_KEY", "dummy"),
    temperature=0,
)

# Escape system prompt, then re-enable registry placeholder
SYSTEM_PROMPT_ESCAPED = escape_braces(SYSTEM_PROMPT)
SYSTEM_PROMPT_ESCAPED = SYSTEM_PROMPT_ESCAPED.replace("{{registry}}", "{registry}")

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_ESCAPED),
    ("system", "{experience_block}"),
    ("user", "{query}")
])

# -------------------------------------------------------------------
# 5️⃣ EXECUTOR
# -------------------------------------------------------------------

executor = MongoExecutor()

# -------------------------------------------------------------------
# 6️⃣ INTERACTIVE RUNNER
# -------------------------------------------------------------------

def run_agent():
    print("\n🔹 CMMS MongoDB Aggregation Agent")
    print(f"🔹 Registry: {REGISTRY_PATH}")
    print("🔹 Model: Qwen2.5-14B-Instruct")
    print("🔹 Execution: ENABLED")
    print("🔹 Type your query or 'exit'\n")

    while True:
        user_input = input("Query > ").strip()
        if user_input.lower() == "exit":
            break

        try:
            start_time = time.perf_counter()

            cache_key = make_cache_key(
                model=MODEL_NAME,
                query=user_input,
                registry_hash=REGISTRY_HASH
            )

            cached_pipeline = get_cached_pipeline(cache_key)

            if cached_pipeline:
                pipeline_text = cached_pipeline
                used_llm = False
                examples_used = 0
                print("⚡ Exact match cache hit")
            else:
                examples = retrieve_similar_queries(
                    user_query=user_input,
                    registry_text=REGISTRY_TEXT,
                    top_k=3
                )

                experience_block = build_experience_block(examples)
                escaped_registry = escape_braces(REGISTRY_TEXT)

                formatted_prompt = prompt.format_messages(
                    registry=escaped_registry,
                    experience_block=experience_block,
                    query=user_input
                )

                response = llm.invoke(formatted_prompt)
                pipeline_text = response.content.strip()

                parsed = json.loads(pipeline_text)
                if isinstance(parsed, dict):
                    parsed = [parsed]
                if not isinstance(parsed, list):
                    raise ValueError("LLM output must be a JSON array")

                # 🔥 GENERIC REGISTRY-SEMANTIC REPAIR
                parsed = apply_semantic_repairs(parsed, user_input)

                pipeline_text = json.dumps(parsed, ensure_ascii=False)
                set_cached_pipeline(cache_key, pipeline_text)

                used_llm = True
                examples_used = len(examples)

            results = executor.execute_aggregation(
                collection_name="workorders",
                pipeline_text=pipeline_text,
                limit=20
            )

            end_time = time.perf_counter()

            print("\nGenerated Pipeline:\n")
            print(f"db.workorders.aggregate({pipeline_text})\n")

            print("Results:\n")
            for r in results:
                print(r)

            print(f"\n⏱ Time: {end_time - start_time:.2f}s")
            print(f"🧠 Examples used: {examples_used}")
            print(f"🤖 LLM used: {used_llm}")
            print(f"📄 Rows returned: {len(results)}")
            print("\n" + "-" * 60 + "\n")

        except Exception as e:
            print("❌ Error TYPE:", type(e))
            print("❌ Error REPR:", repr(e))
            raise


if __name__ == "__main__":
    run_agent()
