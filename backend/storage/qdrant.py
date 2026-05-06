from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    SparseVectorParams, SparseIndexParams,
    SparseVector, FusionQuery, Fusion, Prefetch
)
from config import get_settings
from models.schemas import CodeChunk
from typing import List, Dict, Any
import uuid

settings = get_settings()

sync_client = QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key or None,
)

async_client = AsyncQdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key or None,
)

DENSE_VECTOR_SIZE = 1536


def collection_name(repo_id: str) -> str:
    return f"repo_{repo_id}"


def create_collection(repo_id: str) -> None:
    name = collection_name(repo_id)
    try:
        sync_client.delete_collection(name)
    except Exception:
        pass

    sync_client.create_collection(
        collection_name=name,
        vectors_config={
            "dense": VectorParams(size=DENSE_VECTOR_SIZE, distance=Distance.COSINE)
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(
                index=SparseIndexParams(on_disk=False)
            )
        }
    )


def upsert_chunks(
    repo_id: str,
    chunks: List[CodeChunk],
    dense_embeddings: List[List[float]],
    sparse_embeddings: List[Dict[str, Any]]
) -> None:
    name = collection_name(repo_id)
    batch_size = 250
    points = []

    for chunk, dense, sparse in zip(chunks, dense_embeddings, sparse_embeddings):
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector={
                "dense": dense,
                "sparse": SparseVector(
                    indices=sparse["indices"],
                    values=sparse["values"]
                )
            },
            payload=chunk.model_dump()
        ))

    for i in range(0, len(points), batch_size):
        sync_client.upsert(
            collection_name=name,
            points=points[i:i + batch_size]
        )


async def hybrid_search(
    repo_id: str,
    query_dense: List[float],
    query_sparse: Dict[str, Any],
    top_k: int = 20
) -> List[Dict[str, Any]]:
    name = collection_name(repo_id)

    results = await async_client.query_points(
        collection_name=name,
        prefetch=[
            Prefetch(query=query_dense, using="dense", limit=top_k),
            Prefetch(
                query=SparseVector(
                    indices=query_sparse["indices"],
                    values=query_sparse["values"]
                ),
                using="sparse",
                limit=top_k
            )
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=top_k,
        with_payload=True
    )

    return [{"score": r.score, **r.payload} for r in results.points]


def collection_exists(repo_id: str) -> bool:
    try:
        sync_client.get_collection(collection_name(repo_id))
        return True
    except Exception:
        return False
