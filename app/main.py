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

app = FastAPI()

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
    model_name="gpt-oss:latest"
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
    intent = route_intent(request.message)
    logger.info(f"Intent: {intent}")
    chat_history.append({"role": "user", "content": request.message})

    if intent == Intent.CHAT:
        response = chatbot.run(request.message)
        logger.info(f"Chat response: {response}")
        chat_history.append({"role": "assistant", "content": response})
        return {"response": response}
    
    if intent == Intent.EXECUTE_TASK:
        return{"response": "It has not been implemented yet, still working on it"}
    
    if intent == Intent.ANALYZE:
        return{"response": "It has not been implemented yet, still working on it"}

    return {"response": "Unsupported intent"}
    
# print (f"Chat history: {chat_history}")