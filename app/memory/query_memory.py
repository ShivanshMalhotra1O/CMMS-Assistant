import chromadb
from chromadb.config import Settings
from datetime import datetime
import hashlib
from typing import Optional

# -----------------------------------------
# Vector memory (experience replay)
# -----------------------------------------

client = chromadb.Client(
    Settings(
        persist_directory="./query_memory_chroma",
        anonymized_telemetry=False
    )
)

collection = client.get_or_create_collection(
    name="cmms_query_memory"
)

# -----------------------------------------
# Utilities
# -----------------------------------------

def normalize_query(query: str) -> str:
    return " ".join(query.lower().strip().split())


def hash_registry(registry_text: str) -> str:
    return hashlib.sha256(registry_text.encode()).hexdigest()


def make_memory_id(
    *,
    query: str,
    model: str,
    registry_hash: str
) -> str:
    raw = f"{normalize_query(query)}|{model}|{registry_hash}|{datetime.utcnow().isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()

# -----------------------------------------
# Store memory (ONLY ON SUCCESS)
# -----------------------------------------

def store_query_memory(
    *,
    user_query: str,
    resource: str,
    pipeline: str,
    model: str,
    registry_text: str,
    execution_time_ms: Optional[int] = None,
):
    normalized = normalize_query(user_query)
    registry_hash = hash_registry(registry_text)

    collection.add(
        documents=[normalized],
        metadatas=[{
            "resource": resource,
            "pipeline": pipeline,
            "model": model,
            "registry_hash": registry_hash,
            "execution_time_ms": execution_time_ms,
            "created_at": datetime.utcnow().isoformat(),
            "status": "success",   # 🔒 only store good examples
        }],
        ids=[make_memory_id(
            query=user_query,
            model=model,
            registry_hash=registry_hash,
        )],
    )

    client.persist()

# -----------------------------------------
# Retrieve similar (SAFE FILTERING)
# -----------------------------------------

def retrieve_similar_queries(
    *,
    user_query: str,
    registry_text: str,
    model: str | None = None,
    top_k: int = 3,
):
    normalized = normalize_query(user_query)
    registry_hash = hash_registry(registry_text)

    conditions = [
        {"registry_hash": registry_hash},
        {"status": "success"},
    ]

    if model:
        conditions.append({"model": model})

    where_filter = {
        "$and": conditions
    }

    results = collection.query(
        query_texts=[normalized],
        n_results=top_k,
        where=where_filter,
    )

    examples = []

    if results and results.get("documents"):
        for i in range(len(results["documents"][0])):
            meta = results["metadatas"][0][i]
            examples.append({
                "user_query": results["documents"][0][i],
                "pipeline": meta["pipeline"],
                "execution_time_ms": meta.get("execution_time_ms"),
            })

    return examples
