import tempfile, json
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

settings = get_settings()
redis_client = redis_lib.from_url(settings.redis_url, decode_responses=True)


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
    update_status(repo_id, IndexStatus.CLONING, repo_url=clean_url)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        print(f"[pipeline] Cloning {clean_url}")
        repo_path = clone_repo(clean_url, tmp_path)
        update_status(repo_id, IndexStatus.CHUNKING, progress=10, repo_url=clean_url)

        files = get_indexable_files(repo_path)
        print(f"[pipeline] {len(files)} indexable files")

        all_chunks = []
        for i, file_path in enumerate(files):
            all_chunks.extend(chunk_file(file_path, repo_path, repo_id))
            if i % 20 == 0:
                update_status(repo_id, IndexStatus.CHUNKING,
                              progress=10 + int((i / len(files)) * 40),
                              total_chunks=len(all_chunks), repo_url=clean_url)

        print(f"[pipeline] {len(all_chunks)} total chunks")
        update_status(repo_id, IndexStatus.EMBEDDING, progress=50,
                      total_chunks=len(all_chunks), repo_url=clean_url)

        dense_embeddings, sparse_embeddings = embed_chunks(all_chunks)
        update_status(repo_id, IndexStatus.STORING, progress=85,
                      total_chunks=len(all_chunks), repo_url=clean_url)

        create_collection(repo_id)
        upsert_chunks(repo_id, all_chunks, dense_embeddings, sparse_embeddings)

        update_status(repo_id, IndexStatus.DONE, progress=100,
                      total_chunks=len(all_chunks), repo_url=clean_url)
        print(f"[pipeline] Done. {len(all_chunks)} chunks indexed.")
