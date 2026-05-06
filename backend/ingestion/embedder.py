from openai import OpenAI
from typing import List, Dict, Any, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential
from models.schemas import CodeChunk
from config import get_settings
import math, re, time
from collections import Counter, defaultdict

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)
EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100


@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=2, min=5, max=60)
)
def embed_batch(texts: List[str]) -> List[List[float]]:
    response = client.embeddings.create(model=EMBED_MODEL, input=texts, encoding_format="float")
    return [item.embedding for item in response.data]


def build_sparse_vector(text: str) -> Dict[str, Any]:
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
    if not tokens:
        return {"indices": [0], "values": [0.1]}
    counts = Counter(tokens)
    total = len(tokens)
    indices, values = [], []
    for token, count in counts.items():
        idx = abs(hash(token)) % 30000
        tf = count / total
        idf = math.log(1 + len(token))
        indices.append(idx)
        values.append(float(tf * idf))

    merged = defaultdict(float)
    for idx, val in zip(indices, values):
        merged[idx] += val

    return {
        "indices": list(merged.keys()),
        "values": [float(v) for v in merged.values()]
    }


def embed_chunks(chunks: List[CodeChunk]) -> Tuple[List[List[float]], List[Dict[str, Any]]]:
    texts = [f"File: {c.file_path}\nSymbol: {c.symbol_name}\n\n{c.content}" for c in chunks]
    dense_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        dense_embeddings.extend(embed_batch(batch))
        print(f"[embedder] {min(i + BATCH_SIZE, len(texts))}/{len(texts)} chunks embedded")
        time.sleep(1)
    sparse_embeddings = [build_sparse_vector(t) for t in texts]
    return dense_embeddings, sparse_embeddings


def embed_query(question: str) -> Tuple[List[float], Dict[str, Any]]:
    dense = embed_batch([question])[0]
    sparse = build_sparse_vector(question)
    return dense, sparse
