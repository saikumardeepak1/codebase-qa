from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models.schemas import ChatRequest, IndexStatus
from retrieval.searcher import search_chunks
from retrieval.reranker import rerank_chunks
from retrieval.context_builder import build_context
from llm.client import stream_answer
from ingestion.pipeline import get_status
import json

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest):
    status_data = get_status(request.repo_id)
    if not status_data or status_data.get("status") != IndexStatus.DONE.value:
        raise HTTPException(status_code=400, detail="Repo not fully indexed yet.")

    async def event_stream():
        yield ": keep-alive\n\n"  # forces browser to open the stream immediately

        raw_chunks = await search_chunks(request.repo_id, request.question, top_k=20)
        if not raw_chunks:
            yield f"data: {json.dumps({'type': 'chunk', 'content': 'No relevant code found.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        reranked = rerank_chunks(request.question, raw_chunks, top_n=5)
        context, citations = build_context(reranked)
        history = [msg.model_dump() for msg in request.history]

        async for event in stream_answer(
            question=request.question, context=context,
            citations=citations, repo_id=request.repo_id, history=history
        ):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
