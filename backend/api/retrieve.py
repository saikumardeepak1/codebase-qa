from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, IndexStatus
from retrieval.searcher import search_chunks
from retrieval.reranker import rerank_chunks
from retrieval.context_builder import build_context
from ingestion.pipeline import get_status

router = APIRouter()


@router.post("/retrieve")
async def retrieve(request: ChatRequest):
    status_data = get_status(request.repo_id)
    if not status_data or status_data.get("status") != IndexStatus.DONE.value:
        raise HTTPException(status_code=400, detail="Repo not fully indexed yet.")

    raw_chunks = await search_chunks(request.repo_id, request.question, top_k=20)
    if not raw_chunks:
        return {"context": "", "citations": []}

    reranked = rerank_chunks(request.question, raw_chunks, top_n=5)
    context, citations = build_context(reranked)

    return {
        "context": context,
        "citations": [c.model_dump() for c in citations],
    }
