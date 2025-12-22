from fastapi import FastAPI
from app.agents.chatbot import ChatbotAgent
from app.agents.tasker import TaskerAgent
from app.models.schemas import ChatRequest, ChatResponse
from app.orchestration.router import route_intent, Intent
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.core.logging import logger
from app.core.memory import chat_history
from app.models.models_list import get_model
from app.core.llm_warmup import warmup_llm
from contextlib import asynccontextmanager
from app.agents.executers import execute_action
from app.policy.engine import PolicyDecision, PolicyResult, evaluate_policy, resolve_action, resolve_resource
from app.policy.roles import Action
import yaml
from app.db.mongodb import get_db

db = get_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    warmup_llm()
    yield
    # Shutdown (optional cleanup later)

app = FastAPI(lifespan=lifespan)

# Frontend
BASE_DIR = Path(__file__).resolve().parent

app.mount(
    "/frontend",
    StaticFiles(directory=BASE_DIR / "frontend"),
    name="frontend",
)

# Registry
REGISTRY_PATH = Path(__file__).parent / "registry" / "resources.yaml"

if not REGISTRY_PATH.exists():
    raise RuntimeError("Resource registry YAML not found")

with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    registry = yaml.safe_load(f)


if not registry or not isinstance(registry, dict):
    raise RuntimeError("Invalid resource registry format")


# ------------------------------- Models -------------------------------------------------------------------

# # OpenAI
# tasker_model = get_model(
#     provider="openai",
#     model_name="gpt-4o-mini"
# )

# Local Hosted
chat_model = get_model(
    provider="local_host",
    model_name="qwen2.5:7b"
)

chatbot = ChatbotAgent(chat_model)
tasker  = TaskerAgent()


# ------------------------------------ Routes ------------------------------------------------------------------

# Frontend Routes
@app.get("/")
def root():
    return FileResponse(BASE_DIR / "frontend" / "index.html")

# Route to get the health of the application
@app.get("/health")
def health():
    return {"status": "ok"}


# Route to chat with the chatbot
@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    user_message = request.message
    user_context = request.user

    # 1️⃣ Intent detection
    intent = route_intent(user_message)

    # 2️⃣ Policy check (intent + role)
    policy_result = evaluate_policy(
        intent=intent,
        user_context=user_context,
        user_input=user_message
    )

    if policy_result.decision == PolicyDecision.BLOCK:
        return {"response": policy_result.reason}

    if policy_result.decision == PolicyDecision.CLARIFY:
        return {"response": policy_result.reason}

    # 3️⃣ CHAT intent (no DB, no tasker)
    if intent == Intent.CHAT:
        response = chatbot.run(user_message)
        return {"response": response}

    # 4️⃣ TASK execution flow
    if intent == Intent.EXECUTE_TASK:

        # Resolve action + resource
        action = resolve_action(intent, user_message)
        resource = resolve_resource(user_message)

        # Extract parameters using Tasker (LLM / regex)
        params = tasker.run(action, resource, user_message)
        # params must be a dict

        # Execute using registry-driven executor
        result = execute_action(
            db=db,
            registry=registry,
            action=action,
            resource=resource,
            params=params
        )

        return {"response": result}

    return {"response": "Unsupported intent"}
