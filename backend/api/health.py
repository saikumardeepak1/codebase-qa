from fastapi import APIRouter, Query
import redis as redis_lib
from qdrant_client import QdrantClient
from config import get_settings
import os

router = APIRouter()
settings = get_settings()

REQUIRED_ENV_VARS = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "COHERE_API_KEY",
    "QDRANT_URL",
    "QDRANT_API_KEY",
    "REDIS_URL",
]


@router.get("/health")
async def health():
    status = {"status": "ok", "qdrant": "unknown", "redis": "unknown"}
    try:
        QdrantClient(url=settings.qdrant_url).get_collections()
        status["qdrant"] = "ok"
    except Exception as e:
        status["qdrant"] = f"error: {e}"
    try:
        redis_lib.from_url(settings.redis_url).ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {e}"
    return status


@router.get("/debug/index-status")
async def debug_index_status(repo_id: str = Query(..., description="repo_id to inspect")):
    result: dict = {
        "repo_id": repo_id,
        "qdrant": {},
        "redis": {},
        "env": {},
    }

    # --- Qdrant ---
    collection = f"repo_{repo_id}"
    try:
        client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
        info = client.get_collection(collection)
        result["qdrant"] = {
            "connected": True,
            "collection": collection,
            "points_count": info.points_count,
            "status": str(info.status),
        }
    except Exception as e:
        result["qdrant"] = {
            "connected": False,
            "collection": collection,
            "error": str(e),
        }

    # --- Redis / Upstash ---
    try:
        r = redis_lib.from_url(settings.redis_url, decode_responses=True)
        r.ping()
        job_data = r.get(f"job:{repo_id}")
        result["redis"] = {
            "connected": True,
            "url_scheme": settings.redis_url.split("://")[0],
            "job_key_exists": job_data is not None,
            "job_data": job_data,
        }
    except Exception as e:
        result["redis"] = {
            "connected": False,
            "url_scheme": settings.redis_url.split("://")[0],
            "error": str(e),
        }

    # --- Env vars (names only, never values) ---
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    present = [v for v in REQUIRED_ENV_VARS if os.environ.get(v)]
    result["env"] = {"present": present, "missing": missing}

    return result
