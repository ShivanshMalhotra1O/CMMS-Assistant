from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager
import yaml
import time
import traceback

from app.agents.chatbot import ChatbotAgent
from app.agents.tasker import TaskerAgent
from app.agents.executers import ActionExecutor

from app.models.schemas import ChatRequest, ChatResponse
from app.orchestration.router import route_intent, Intent
from app.policy.engine import (
    evaluate_policy,
    resolve_resource,
    PolicyDecision,
)
from app.policy.roles import Action
from app.policy.engine import Resource

from app.models.models_list import get_model
from app.core.llm_warmup import warmup_llm
from app.db.mongodb import get_db
from app.core.logging import logger


db = get_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting CMMS AI application")
    warmup_llm()
    logger.info("LLM warmup completed")
    yield
    logger.info("Shutting down CMMS AI application")

app = FastAPI(lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent

app.mount(
    "/frontend",
    StaticFiles(directory=BASE_DIR / "frontend"),
    name="frontend",
)

@app.get("/")
def root():
    return FileResponse(BASE_DIR / "frontend" / "index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

# Load registry.yaml
REGISTRY_PATH = BASE_DIR / "registry" / "registry.yaml"

if not REGISTRY_PATH.exists():
    raise RuntimeError("Registry YAML not found")

with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    registry = yaml.safe_load(f)

if not registry or "collections" not in registry:
    raise RuntimeError("Invalid registry format - missing 'collections'")

logger.info(f"Loaded registry with collections: {list(registry.get('collections', {}).keys())}")

chat_model = get_model(
    provider="local_host",
    model_name="qwen2.5:7b"
)

chatbot = ChatbotAgent(chat_model)
tasker = TaskerAgent()
executor = ActionExecutor()


def get_collection_name(resource: Resource) -> str:
    """Map Resource enum to MongoDB collection name (camelCase)"""
    mapping = {
        Resource.WORK_ORDER: "workorders",
        Resource.ASSET: "assets",
        Resource.PM: "preventivemaintenances",
    }
    return mapping.get(resource, "workorders")


def get_resource_key(resource: Resource) -> str:
    """Map Resource enum to registry resource key"""
    mapping = {
        Resource.WORK_ORDER: "work_orders",
        Resource.ASSET: "assets",
        Resource.PM: "preventive_maintenance",
    }
    return mapping.get(resource, "work_orders")


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    user_message = request.message
    user_context = request.user

    logger.info("Incoming chat request")
    logger.debug(f"User message: {user_message}")

    intent = route_intent(user_message)
    logger.info(f"Detected intent: {intent}")

    policy_result = evaluate_policy(
        intent=intent,
        user_context=user_context,
        user_input=user_message
    )

    if policy_result.decision in {PolicyDecision.BLOCK, PolicyDecision.CLARIFY}:
        logger.warning(
            f"Policy decision: {policy_result.decision} | Reason: {policy_result.reason}"
        )
        return {"response": policy_result.reason}

    if intent == Intent.CHAT:
        logger.info("Handling pure chat intent")
        return {"response": chatbot.run(user_message)}

    if intent == Intent.EXECUTE_TASK:
        logger.info("Handling task execution intent")

        start_time = time.perf_counter()

        try:
            resource_enum = resolve_resource(user_message)
            logger.info(f"Resolved resource: {resource_enum}")
            
            resource_key = get_resource_key(resource_enum)
            collection_name = get_collection_name(resource_enum)
            
            logger.info(f"Mapped to resource_key: {resource_key}, collection: {collection_name}")
            
            pipeline_text = tasker.run(user_input=user_message, resource=collection_name)
            logger.info(f"Generated pipeline: {pipeline_text}")

            action = Action.VIEW
            action_key = action.value

            logger.info(f"Calling ActionExecutor with:")
            logger.info(f"  - collection_name: {collection_name}")
            logger.info(f"  - resource_key: {resource_key}")
            logger.info(f"  - action_key: {action_key}")
            
            result = executor.execute_action(
                db=db,
                registry=registry.get("collections", {}),
                collection_name=collection_name,
                pipeline_text=pipeline_text,
                resource_key=None,
                action_key=None,
                limit=20
            )

            # Calculate total time AFTER execution
            total_time = round(time.perf_counter() - start_time, 3)
            
            metrics = tasker.get_metrics()

            logger.info(
                f"Task execution completed | "
                f"collection={collection_name} | "
                f"resource={resource_key} | "
                f"result_length={len(result)} chars | "
                f"tokens={metrics.get('total_tokens', 0)} | "
                f"llm_used={metrics.get('llm_used', False)} | "
                f"cache_hit={metrics.get('cache_hit', False)} | "
                f"examples={metrics.get('examples_used', 0)}"
            )

            if not result or result.startswith("❌"):
                logger.warning(f"Execution returned error or empty: {result[:100]}")
            
            # Add metrics footer to response
            if metrics.get('cache_hit'):
                result += f"\n\n⚡ Query retrieved from cache in {total_time}s"
            elif metrics.get('llm_used'):
                examples_info = f" (guided by {metrics['examples_used']} past examples)" if metrics.get('examples_used', 0) > 0 else ""
                result += f"\n\n💡 Query generated in {total_time}s using ~{metrics['total_tokens']} tokens{examples_info}"
            else:
                result += f"\n\n💡 Query completed in {total_time}s (using fallback)"
            
            return {"response": result}

        except Exception as e:
            logger.error(f"Task execution failed: {type(e).__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"response": f"❌ Error: Unable to process your request. {str(e)}"}

    logger.error("Unsupported intent encountered")
    return {"response": "❌ Unsupported intent"}