from fastapi import APIRouter, HTTPException
from models.schemas import IndexRepoRequest, IndexRepoResponse, RepoStatusResponse, IndexStatus
from ingestion.cloner import validate_github_url, url_to_repo_id
from ingestion.pipeline import get_status
from tasks.index_repo import index_repo_task

router = APIRouter()


@router.post("/repos/index", response_model=IndexRepoResponse)
async def index_repo(request: IndexRepoRequest):
    try:
        clean_url = validate_github_url(request.github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    repo_id = url_to_repo_id(clean_url)
    existing = get_status(repo_id)
    if existing and existing.get("status") == IndexStatus.DONE.value:
        return IndexRepoResponse(repo_id=repo_id, status=IndexStatus.DONE, message="Already indexed.")

    index_repo_task.delay(clean_url, repo_id)
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
