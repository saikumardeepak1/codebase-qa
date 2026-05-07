from fastapi import APIRouter, BackgroundTasks, HTTPException
from models.schemas import IndexRepoRequest, IndexRepoResponse, RepoStatusResponse, IndexStatus
from ingestion.cloner import validate_github_url, url_to_repo_id
from ingestion.pipeline import get_status, run_pipeline
from storage.qdrant import collection_point_count

router = APIRouter()


def _run_pipeline_sync(github_url: str, repo_id: str) -> None:
    run_pipeline(github_url, repo_id)


@router.post("/repos/index", response_model=IndexRepoResponse)
async def index_repo(request: IndexRepoRequest, background_tasks: BackgroundTasks):
    try:
        clean_url = validate_github_url(request.github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    repo_id = url_to_repo_id(clean_url)
    existing = get_status(repo_id)
    already_done = (
        existing
        and existing.get("status") == IndexStatus.DONE.value
        and collection_point_count(repo_id) > 0
    )
    if already_done:
        return IndexRepoResponse(repo_id=repo_id, status=IndexStatus.DONE, message="Already indexed.")

    background_tasks.add_task(_run_pipeline_sync, clean_url, repo_id)
    return IndexRepoResponse(repo_id=repo_id, status=IndexStatus.PENDING, message="Indexing started.")


@router.get("/repos/{repo_id}/status", response_model=RepoStatusResponse)
async def get_repo_status(repo_id: str):
    data = get_status(repo_id)
    if not data:
        raise HTTPException(status_code=404, detail="Repo not found.")
    return RepoStatusResponse(
        repo_id=repo_id,
        status=IndexStatus(data["status"]),
        progress=data.get("progress", 0),
        total_chunks=data.get("total_chunks", 0),
        error=data.get("error"),
        repo_url=data.get("repo_url", "")
    )
