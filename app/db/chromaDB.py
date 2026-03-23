import chromadb
from datetime import datetime
import os
import uuid
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

# ── ChromaDB setup ────────────────────────────────────────────────────────────
CHROMA_PATH = os.path.join(ROOT, "chroma_store")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
messages_collection = chroma_client.get_or_create_collection(
    name="session_messages",
    metadata={"hnsw:space": "cosine"}
)
 
 
def save_message(session_id: str, role: str, content: str, extra: dict = None):
    """Save a single message to ChromaDB."""
    msg_id = str(uuid.uuid4())
    metadata = {
        "session_id": session_id,
        "role": role,                          # user / assistant / tool_call / tool_result
        "timestamp": datetime.utcnow().isoformat(),
        **(extra or {})
    }
    # ChromaDB requires string values in metadata
    metadata = {k: str(v) for k, v in metadata.items()}
 
    messages_collection.add(
        ids=[msg_id],
        documents=[content],
        metadatas=[metadata]
    )
    return msg_id
 
 
def get_session_messages(session_id: str) -> list:
    """Retrieve all messages for a session in chronological order."""
    results = messages_collection.get(
        where={"session_id": session_id},
        include=["documents", "metadatas"]
    )
    if not results["ids"]:
        return []
 
    # Zip and sort by timestamp
    messages = [
        {
            "id": mid,
            "role": meta["role"],
            "content": doc,
            "timestamp": meta["timestamp"],
            "session_id": meta["session_id"],
            **{k: v for k, v in meta.items() if k not in ["role", "content", "timestamp", "session_id"]}
        }
        for mid, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
    ]
    return sorted(messages, key=lambda x: x["timestamp"])
 
 
def get_all_sessions() -> list:
    """Get list of unique session IDs with their first message."""
    results = messages_collection.get(include=["metadatas", "documents"])
    if not results["ids"]:
        return []
 
    # Group by session_id, keep earliest message as preview
    sessions = {}
    for mid, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
        sid = meta["session_id"]
        if sid not in sessions or meta["timestamp"] < sessions[sid]["timestamp"]:
            sessions[sid] = {
                "session_id": sid,
                "preview": doc[:80] + ("..." if len(doc) > 80 else ""),
                "timestamp": meta["timestamp"]
            }
 
    return sorted(sessions.values(), key=lambda x: x["timestamp"], reverse=True)
 