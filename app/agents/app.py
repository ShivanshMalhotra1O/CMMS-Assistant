import os
import sys
import uuid

# Go up from app/agents/ to project root
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Remove app/agents/ from sys.path BEFORE any imports
# so 'app' resolves to the package, not this file named app.py
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR in sys.path:
    sys.path.remove(THIS_DIR)

sys.path.insert(0, ROOT)

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
import re
import json
import time

from app.llm_models import creator_llm
from app.agents.creator.create_wo import tools as creator_tools, tool_map as creator_tool_map, work_order_prompt
from app.agents.retrieval.retrieval import tools as retrieval_tools, tool_map as retrieval_tool_map, retrieval_prompt
from app.db.chromaDB import save_message, get_session_messages, get_all_sessions, messages_collection

api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = creator_llm

ROUTER_PROMPT = """You are an intent classifier for a CMMS assistant.

Classify the user query into exactly one of these intents:

INTENT: create_workorder
  - User wants to create, raise, add, or log a new work order
  - Examples: "Create a work order for BFW BMV 1600", "Raise a damage work order"

INTENT: retrieve
  - User wants to see, find, list, show, get, or fetch existing records
  - Examples: "Show all open work orders", "List stopped assets", "Get WOs for BFW"

INTENT: unknown
  - General questions, greetings, or anything else

Respond with ONLY one word: create_workorder, retrieve, or unknown."""

GENERAL_PROMPT = "You are an intelligent CMMS assistant. Answer general queries about CMMS operations."


def clean_prompt(text: str) -> str:
    return re.sub(r'[^\x00-\x7F]+', '', text).strip()


def find_cached_response(user_input: str, current_session_id: str) -> dict | None:
    """Check if the exact same query was asked before in a different session."""
    results = messages_collection.get(
        where={"role": "user"},
        include=["documents", "metadatas"]
    )
    if not results["ids"]:
        return None

    user_input_clean = user_input.strip().lower()

    for doc, meta in zip(results["documents"], results["metadatas"]):
        session_id = meta["session_id"]

        # Skip current session and cached intents
        if session_id == current_session_id:
            continue
        if meta.get("intent") == "cached":
            continue

        # Exact match only
        if doc.strip().lower() != user_input_clean:
            continue

        # Found a matching user message — find the immediately following assistant message
        session_msgs = get_session_messages(session_id)
        for i, msg in enumerate(session_msgs):
            if (msg["role"] == "user"
                    and msg["content"].strip().lower() == user_input_clean
                    and msg.get("intent") != "cached"):
                # Look for the very next assistant message
                for j in range(i + 1, len(session_msgs)):
                    if session_msgs[j]["role"] == "assistant":
                        return {
                            "content": session_msgs[j]["content"],
                            "from_session": session_id,
                            "timestamp": session_msgs[j]["timestamp"]
                        }
    return None


def classify_intent(user_input: str) -> str:
    response = llm.invoke([
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=user_input)
    ])
    intent = response.content.strip().lower()
    if "create" in intent:
        return "create_workorder"
    elif "retriev" in intent:
        return "retrieve"
    return "unknown"


def stream_agent(system_prompt, tools, tool_map, user_input, session_id):
    llm_with_tools = llm.bind_tools(tools) if tools else llm
    messages = [
        SystemMessage(content=clean_prompt(system_prompt)),
        HumanMessage(content=user_input)
    ]

    total_input = 0
    total_output = 0
    start_time = time.time()

    for i in range(7):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        usage = response.response_metadata.get("token_usage") or response.response_metadata.get("usage", {})
        input_tokens  = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_input  += input_tokens
        total_output += output_tokens

        yield f"data: {json.dumps({'type': 'tokens', 'input': input_tokens, 'output': output_tokens, 'total_input': total_input, 'total_output': total_output})}\n\n"

        if not response.tool_calls:
            elapsed = round(time.time() - start_time, 2)

            save_message(session_id, "assistant", response.content, {
                "intent": "final",
                "input_tokens": total_input,
                "output_tokens": total_output,
                "time_seconds": elapsed
            })

            yield f"data: {json.dumps({'type': 'final', 'content': response.content, 'time': elapsed, 'total_input': total_input, 'total_output': total_output})}\n\n"
            break

        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']

            save_message(session_id, "tool_call", json.dumps(tool_args, default=str), {
                "tool_name": tool_name
            })

            yield f"data: {json.dumps({'type': 'tool_call', 'name': tool_name, 'args': tool_args})}\n\n"

            result = tool_map[tool_name].invoke(tool_args)
            messages.append(ToolMessage(content=str(result), tool_call_id=tool_call['id']))

            try:
                result_serialized = json.loads(json.dumps(result, default=str))
            except Exception:
                result_serialized = str(result)

            save_message(session_id, "tool_result", json.dumps(result_serialized, default=str), {
                "tool_name": tool_name
            })

            yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_name, 'result': result_serialized})}\n\n"


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


@api.get("/")
def index():
    return FileResponse(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    )


@api.post("/chat")
def chat(req: ChatRequest):
    user_input = req.message.strip()
    if not user_input:
        return {"error": "Empty message"}

    session_id = req.session_id or str(uuid.uuid4())

    # Check cache — if same query was asked before, return cached response
    cached = find_cached_response(user_input, session_id)
    if cached:
        def generate_cached():
            yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"
            yield f"data: {json.dumps({'type': 'intent', 'intent': 'cached'})}\n\n"
            yield f"data: {json.dumps({'type': 'final', 'content': cached['content'], 'time': 0, 'total_input': 0, 'total_output': 0, 'cached': True, 'from_session': cached['from_session']})}\n\n"
            yield "data: [DONE]\n\n"
        save_message(session_id, "user", user_input, {"intent": "cached"})
        save_message(session_id, "assistant", cached["content"], {"intent": "cached", "from_session": cached["from_session"]})
        return StreamingResponse(generate_cached(), media_type="text/event-stream")

    intent = classify_intent(user_input)
    save_message(session_id, "user", user_input, {"intent": intent})

    def generate():
        yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"
        yield f"data: {json.dumps({'type': 'intent', 'intent': intent})}\n\n"

        if intent == "create_workorder":
            yield from stream_agent(work_order_prompt, creator_tools, creator_tool_map, user_input, session_id)
        elif intent == "retrieve":
            yield from stream_agent(retrieval_prompt, retrieval_tools, retrieval_tool_map, user_input, session_id)
        else:
            start = time.time()
            response = llm.invoke([
                SystemMessage(content=GENERAL_PROMPT),
                HumanMessage(content=user_input)
            ])
            elapsed = round(time.time() - start, 2)

            save_message(session_id, "assistant", response.content, {
                "intent": "general",
                "time_seconds": elapsed
            })

            yield f"data: {json.dumps({'type': 'final', 'content': response.content, 'time': elapsed, 'total_input': 0, 'total_output': 0})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@api.get("/sessions")
def list_sessions():
    return {"sessions": get_all_sessions()}


@api.get("/sessions/{session_id}")
def get_session(session_id: str):
    return {"session_id": session_id, "messages": get_session_messages(session_id)}


@api.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    results = messages_collection.get(where={"session_id": session_id})
    if results["ids"]:
        messages_collection.delete(ids=results["ids"])
    return {"deleted": len(results["ids"]), "session_id": session_id}


@api.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="127.0.0.1", port=5000)