import tempfile, json, logging, traceback
from pathlib import Path
from typing import Optional
import redis as redis_lib

from config import get_settings
from ingestion.cloner import clone_repo, url_to_repo_id, validate_github_url
from ingestion.file_filter import get_indexable_files
from ingestion.chunker import chunk_file
from ingestion.embedder import embed_chunks
from storage.qdrant import create_collection, upsert_chunks
from models.schemas import IndexStatus

logger = logging.getLogger(__name__)

settings = get_settings()

# Upstash requires TLS; rewrite redis:// → rediss:// if needed.
_redis_url = settings.redis_url
if _redis_url.startswith("redis://") and "upstash.io" in _redis_url:
    _redis_url = "rediss://" + _redis_url[len("redis://"):]

redis_client = redis_lib.from_url(_redis_url, decode_responses=True, ssl_cert_reqs="none")


def update_status(repo_id: str, status: IndexStatus, progress: int = 0,
                  total_chunks: int = 0, error: Optional[str] = None, repo_url: str = "") -> None:
    data = {"status": status.value, "progress": progress,
            "total_chunks": total_chunks, "repo_url": repo_url}
    if error:
        data["error"] = error
    redis_client.set(f"job:{repo_id}", json.dumps(data), ex=86400)


def get_status(repo_id: str) -> Optional[dict]:
    data = redis_client.get(f"job:{repo_id}")
    return json.loads(data) if data else None


def run_pipeline(github_url: str, repo_id: str) -> None:
    clean_url = validate_github_url(github_url)
    logger.info("[pipeline:%s] Starting — url=%s", repo_id, clean_url)
    update_status(repo_id, IndexStatus.CLONING, repo_url=clean_url)

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            logger.info("[pipeline:%s] Cloning %s", repo_id, clean_url)
            try:
                repo_path = clone_repo(clean_url, tmp_path)
            except Exception as e:
                logger.error("[pipeline:%s] Clone failed: %s\n%s", repo_id, e, traceback.format_exc())
                raise

            update_status(repo_id, IndexStatus.CHUNKING, progress=10, repo_url=clean_url)

            try:
                files = get_indexable_files(repo_path)
            except Exception as e:
                logger.error("[pipeline:%s] File scan failed: %s\n%s", repo_id, e, traceback.format_exc())
                raise

            logger.info("[pipeline:%s] %d indexable files found", repo_id, len(files))

            all_chunks = []
            for i, file_path in enumerate(files):
                try:
                    all_chunks.extend(chunk_file(file_path, repo_path, repo_id))
                except Exception as e:
                    logger.warning("[pipeline:%s] Skipping %s — chunk error: %s", repo_id, file_path, e)
                if i % 20 == 0:
                    update_status(repo_id, IndexStatus.CHUNKING,
                                  progress=10 + int((i / len(files)) * 40),
                                  total_chunks=len(all_chunks), repo_url=clean_url)

            logger.info("[pipeline:%s] %d total chunks produced", repo_id, len(all_chunks))
            if not all_chunks:
                raise RuntimeError("Chunking produced 0 chunks — check file_filter and chunker logs above")

            update_status(repo_id, IndexStatus.EMBEDDING, progress=50,
                          total_chunks=len(all_chunks), repo_url=clean_url)

            try:
                dense_embeddings, sparse_embeddings = embed_chunks(all_chunks)
            except Exception as e:
                logger.error("[pipeline:%s] Embedding failed: %s\n%s", repo_id, e, traceback.format_exc())
                raise

            logger.info("[pipeline:%s] Embeddings done, storing in Qdrant", repo_id)
            update_status(repo_id, IndexStatus.STORING, progress=85,
                          total_chunks=len(all_chunks), repo_url=clean_url)

            try:
                create_collection(repo_id)
                upsert_chunks(repo_id, all_chunks, dense_embeddings, sparse_embeddings)
            except Exception as e:
                logger.error("[pipeline:%s] Qdrant upsert failed: %s\n%s", repo_id, e, traceback.format_exc())
                raise

            update_status(repo_id, IndexStatus.DONE, progress=100,
                          total_chunks=len(all_chunks), repo_url=clean_url)
            logger.info("[pipeline:%s] Done — %d chunks indexed", repo_id, len(all_chunks))

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        logger.error("[pipeline:%s] Pipeline failed: %s", repo_id, error_msg)
        update_status(repo_id, IndexStatus.ERROR, error=error_msg, repo_url=clean_url)
        raise
