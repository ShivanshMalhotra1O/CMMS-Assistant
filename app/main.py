from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager
import yaml

from app.agents.chatbot import ChatbotAgent
from app.agents.tasker import TaskerAgent
from app.agents.executers import execute_action

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

# -------------------- DB --------------------
db = get_db()

# -------------------- App Lifespan --------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    warmup_llm()
    yield

app = FastAPI(lifespan=lifespan)

# -------------------- Frontend --------------------
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

# -------------------- Registry --------------------
REGISTRY_PATH = BASE_DIR / "registry" / "resources.yaml"

if not REGISTRY_PATH.exists():
    raise RuntimeError("Resource registry YAML not found")

with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    registry = yaml.safe_load(f)

if not registry or not isinstance(registry, dict):
    raise RuntimeError("Invalid resource registry format")

# -------------------- Models --------------------
chat_model = get_model(
    provider="local_host",
    model_name="qwen2.5:7b"
)

chatbot = ChatbotAgent(chat_model)
tasker = TaskerAgent()

# -------------------- Chat Route --------------------
@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    user_message = request.message
    user_context = request.user

    # 1️⃣ Intent detection
    intent = route_intent(user_message)

    # 2️⃣ Policy check (intent + role + text)
    policy_result = evaluate_policy(
        intent=intent,
        user_context=user_context,
        user_input=user_message
    )

    if policy_result.decision in {PolicyDecision.BLOCK, PolicyDecision.CLARIFY}:
        return {"response": policy_result.reason}

    # 3️⃣ Pure chat
    if intent == Intent.CHAT:
        response = chatbot.run(user_message)
        return {"response": response}

    # 4️⃣ Task execution flow
    if intent == Intent.EXECUTE_TASK:

        # Resolve resource ONCE
        resource_enum = resolve_resource(user_message)
        resource = resource_enum.value

        # 4.1 Task interpretation (LLM)
        task = tasker.run(user_message, resource)

        # 4.2 Use TaskCommand directly
        action = Action(task.action)
        resource = Resource(task.resource)

        # 4.3 Extract filters
        params = task.filters.model_dump(exclude_none=True)

        # 4.4 Execute
        result = execute_action(
            db=db,
            registry=registry,
            action=action,
            resource=resource,
            params=params,
       
        )

        return {"response": result}

    return {"response": "Unsupported intent"}
