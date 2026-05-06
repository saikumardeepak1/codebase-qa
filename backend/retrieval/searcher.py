from ingestion.embedder import embed_query
from storage.qdrant import hybrid_search
from typing import List, Dict, Any


async def search_chunks(repo_id: str, question: str, top_k: int = 20) -> List[Dict[str, Any]]:
    dense, sparse = embed_query(question)
    return await hybrid_search(repo_id, dense, sparse, top_k=top_k)
