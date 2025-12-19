from fastapi import FastAPI

from app.agents.chatbot import ChatbotAgent
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

from app.policy.engine import PolicyDecision, PolicyResult, evaluate_policy

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


# OpenAI
# model = get_model(
#     provider="openai",
#     model_name="gpt-4o-mini"
# )

# Local Hostes
model = get_model(
    provider="local_host",
    model_name="qwen2.5:7b"
)

chatbot = ChatbotAgent(model)


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

    logger.info(f"Chat request: {request.message}")
    user_message = request.message
    user_contxt = request.user
    # chat_history.append({"role": "user", "content": request.message})

    intent = route_intent(user_message)

    policy_result = evaluate_policy(
        intent = intent,
        user_context=user_contxt,
        user_input=user_message
    )

    if policy_result.decision == PolicyDecision.ALLOW:
        response = chatbot.run(user_message)
        return {"response": response}
    
    if policy_result.decision == PolicyDecision.BLOCK:
        return{"response":policy_result.reason}

    return {"response": "Unsupported intent"}
    
# print (f"Chat history: {chat_history}")