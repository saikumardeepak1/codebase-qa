import cohere
from typing import List, Dict, Any
from config import get_settings
from tenacity import retry, stop_after_attempt, wait_exponential

settings = get_settings()
co = cohere.ClientV2(settings.cohere_api_key)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def rerank_chunks(question: str, chunks: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
    if not chunks:
        return []
    documents = [c["content"] for c in chunks]
    response = co.rerank(query=question, documents=documents,
                         model="rerank-english-v3.0", top_n=min(top_n, len(chunks)))
    reranked = []
    for result in response.results:
        chunk = chunks[result.index].copy()
        chunk["rerank_score"] = result.relevance_score
        reranked.append(chunk)
    return reranked
