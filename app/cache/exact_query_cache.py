import hashlib
import time

# ---------------------------------------
# In-memory cache
# ---------------------------------------

_EXACT_CACHE: dict[str, dict] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def normalize_query(query: str) -> str:
    return " ".join(query.lower().strip().split())


def make_cache_key(
    *,
    model: str,
    query: str,
    registry_hash: str
) -> str:
    raw = f"{model}|{normalize_query(query)}|{registry_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached_pipeline(cache_key: str) -> str | None:
    entry = _EXACT_CACHE.get(cache_key)
    if not entry:
        return None

    # TTL check
    if time.time() - entry["ts"] > CACHE_TTL_SECONDS:
        del _EXACT_CACHE[cache_key]
        return None

    return entry["pipeline"]


def set_cached_pipeline(cache_key: str, pipeline: str):
    _EXACT_CACHE[cache_key] = {
        "pipeline": pipeline,
        "ts": time.time()
    }
