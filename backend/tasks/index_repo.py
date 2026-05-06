from celery import Celery
from ingestion.pipeline import run_pipeline, update_status
from models.schemas import IndexStatus

celery_app = Celery("codebase_qa")
celery_app.config_from_object("celeryconfig")


@celery_app.task(bind=True, name="tasks.index_repo")
def index_repo_task(self, github_url: str, repo_id: str) -> dict:
    try:
        run_pipeline(github_url, repo_id)
        return {"status": "done", "repo_id": repo_id}
    except Exception as e:
        update_status(repo_id, IndexStatus.ERROR, error=str(e))
        raise
