from fastapi import APIRouter
import redis as redis_lib
from qdrant_client import QdrantClient
from config import get_settings

router = APIRouter()
settings = get_settings()

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
