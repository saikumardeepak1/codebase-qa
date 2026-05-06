# CLAUDE.md — Codebase Q&A Assistant (Production RAG)
# ONE NIGHT FULL BUILD — NO COMPROMISES

> READ THIS ENTIRE FILE BEFORE WRITING A SINGLE LINE OF CODE.
> Build everything in the exact order listed. Do not skip steps.
> After each step, verify it works before moving to the next.
> When something breaks, fix it before continuing.

---

## What We Are Building

A production-grade RAG system. User pastes a GitHub URL → system indexes the entire codebase → user chats with it and gets cited answers pointing to exact files and functions.

**Full stack, no cuts:**
- FastAPI backend with async endpoints
- Celery + Redis for background indexing jobs
- tree-sitter AST-based code chunking
- OpenAI embeddings (batched)
- Qdrant vector DB with hybrid search (dense + sparse)
- Cohere reranking
- Claude streaming with citations
- Langfuse observability on every query
- Next.js 14 frontend with SSE streaming
- Docker Compose for local dev
- Railway + Vercel deployment configs ready

---

## Project Structure

Create this exact structure before writing any code:

```
codebase-qa/
├── CLAUDE.md
├── .env.example
├── .env                        ← copy from .env.example, fill in real keys
├── .gitignore
├── docker-compose.yml
│
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── celeryconfig.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── repos.py
│   │   ├── chat.py
│   │   └── health.py
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── cloner.py
│   │   ├── file_filter.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   └── pipeline.py
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── searcher.py
│   │   ├── reranker.py
│   │   └── context_builder.py
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── prompts.py
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   └── qdrant.py
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── index_repo.py
│   │
│   └── models/
│       ├── __init__.py
│       └── schemas.py
│
└── frontend/
    ├── package.json
    ├── next.config.ts
    ├── tailwind.config.ts
    ├── tsconfig.json
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx
        │   └── chat/
        │       └── [repoId]/
        │           └── page.tsx
        ├── components/
        │   ├── RepoInput.tsx
        │   ├── IndexingStatus.tsx
        │   ├── ChatWindow.tsx
        │   ├── MessageBubble.tsx
        │   └── CitationCard.tsx
        ├── hooks/
        │   ├── useIndexingStatus.ts
        │   └── useChat.ts
        └── lib/
            └── api.ts
```

---

## Environment Variables

Create `.env.example` with exactly this content:

```bash
# LLM
ANTHROPIC_API_KEY=your_key_here

# Embeddings
OPENAI_API_KEY=your_key_here

# Reranking
COHERE_API_KEY=your_key_here

# Vector DB
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# Queue
REDIS_URL=redis://localhost:6379

# Observability
LANGFUSE_PUBLIC_KEY=your_key_here
LANGFUSE_SECRET_KEY=your_key_here
LANGFUSE_HOST=https://cloud.langfuse.com

# Optional - increases GitHub API rate limit
GITHUB_TOKEN=

# App
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000
```

---

## Step 1 — Docker Compose

Create `docker-compose.yml`:

```yaml
version: "3.9"

services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  qdrant_data:
  redis_data:
```

**Verify:** Run `docker compose up -d` — both services must be healthy before continuing.

---

## Step 2 — Backend Requirements

Create `backend/requirements.txt` with exactly these packages:

```
# Framework
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.9

# Config
pydantic-settings==2.4.0
python-dotenv==1.0.1

# Task queue
celery==5.4.0
redis==5.0.8

# Vector DB
qdrant-client==1.11.1

# Embeddings
openai==1.47.0

# LLM
anthropic==0.34.2

# Reranking
cohere==5.9.4

# Observability
langfuse==2.53.5

# Code parsing
tree-sitter==0.23.1
tree-sitter-languages==1.10.2

# Git
gitpython==3.1.43

# Utils
httpx==0.27.2
tenacity==9.0.0
tiktoken==0.7.0
```

Install: `pip install -r requirements.txt`

---

## Step 3 — Config

Create `backend/config.py`:

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM
    anthropic_api_key: str
    openai_api_key: str
    cohere_api_key: str

    # Storage
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    redis_url: str = "redis://localhost:6379"

    # Observability
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # Optional
    github_token: str = ""
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

---

## Step 4 — Pydantic Schemas

Create `backend/models/schemas.py`:

```python
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class IndexStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    DONE = "done"
    ERROR = "error"


class IndexRepoRequest(BaseModel):
    github_url: str


class IndexRepoResponse(BaseModel):
    repo_id: str
    status: IndexStatus
    message: str


class RepoStatusResponse(BaseModel):
    repo_id: str
    status: IndexStatus
    progress: int = 0
    total_chunks: int = 0
    error: Optional[str] = None
    repo_url: str = ""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    repo_id: str
    question: str
    history: List[ChatMessage] = []


class Citation(BaseModel):
    index: int
    file_path: str
    symbol_name: str
    start_line: int
    end_line: int
    language: str


class CodeChunk(BaseModel):
    repo_id: str
    file_path: str
    language: str
    chunk_type: str
    symbol_name: str
    start_line: int
    end_line: int
    content: str
```

---

## Step 5 — Qdrant Storage

Create `backend/storage/qdrant.py`:

```python
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
```

---

## Step 6 — File Filter

Create `backend/ingestion/file_filter.py`:

```python
from pathlib import Path
from typing import List

EXCLUDED_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", "coverage", ".pytest_cache", ".mypy_cache",
    "vendor", "third_party", ".eggs", "eggs", "target", "out",
    ".idea", ".vscode", "tmp", "temp", "logs", "migrations"
}

EXCLUDED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".mp4",
    ".zip", ".tar", ".gz", ".rar", ".lock", ".sum",
    ".min.js", ".min.css", ".map", ".woff", ".woff2", ".ttf",
    ".pyc", ".pyo", ".class", ".o", ".so", ".dll", ".exe", ".bin"
}

SUPPORTED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java",
    ".cpp", ".c", ".h", ".hpp", ".cs", ".rb", ".php", ".swift",
    ".kt", ".scala", ".sh", ".bash",
    ".md", ".txt", ".rst", ".yaml", ".yml", ".toml", ".json",
    ".html", ".css", ".sql", ".graphql", ".proto"
}

MAX_FILE_BYTES = 200_000


def should_include_file(path: Path, repo_root: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDED_DIRS:
            return False
    if path.suffix not in SUPPORTED_EXTENSIONS:
        return False
    if path.suffix in EXCLUDED_EXTENSIONS:
        return False
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return False
    except OSError:
        return False
    return True


def get_indexable_files(repo_root: Path) -> List[Path]:
    files = []
    for path in repo_root.rglob("*"):
        if path.is_file() and should_include_file(path, repo_root):
            files.append(path)
    return files
```

---

## Step 7 — AST Chunker (Most Critical File)

Create `backend/ingestion/chunker.py`:

```python
"""
AST-based code chunker using tree-sitter.
Each function, class, and method becomes its own chunk.
This is what separates this project from naive RAG tutorials.
"""

from pathlib import Path
from typing import List
from tree_sitter_languages import get_parser
from models.schemas import CodeChunk
import tiktoken

LANGUAGE_MAP = {
    ".py": "python", ".ts": "typescript", ".tsx": "tsx",
    ".js": "javascript", ".jsx": "javascript", ".go": "go",
    ".rs": "rust", ".java": "java", ".cpp": "cpp", ".c": "c",
    ".h": "c", ".hpp": "cpp", ".cs": "c_sharp", ".rb": "ruby",
    ".php": "php", ".swift": "swift", ".kt": "kotlin",
}

FUNCTION_NODE_TYPES = {
    "python": ["function_definition", "async_function_definition", "class_definition"],
    "typescript": ["function_declaration", "method_definition", "class_declaration"],
    "tsx": ["function_declaration", "method_definition", "class_declaration"],
    "javascript": ["function_declaration", "method_definition", "class_declaration"],
    "go": ["function_declaration", "method_declaration", "type_declaration"],
    "rust": ["function_item", "impl_item", "struct_item", "enum_item"],
    "java": ["method_declaration", "class_declaration", "constructor_declaration"],
    "cpp": ["function_definition", "class_specifier"],
    "c": ["function_definition"],
}

MAX_CHUNK_TOKENS = 512
ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(ENCODING.encode(text))


def get_node_name(node, source_bytes: bytes) -> str:
    for child in node.children:
        if child.type in ("identifier", "name"):
            return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
    return "unknown"


def split_large_chunk(content: str, max_tokens: int = MAX_CHUNK_TOKENS) -> List[str]:
    lines = content.split("\n")
    chunks, current, current_tokens = [], [], 0
    for line in lines:
        line_tokens = count_tokens(line)
        if current_tokens + line_tokens > max_tokens and current:
            chunks.append("\n".join(current))
            current = current[-10:]
            current_tokens = count_tokens("\n".join(current))
        current.append(line)
        current_tokens += line_tokens
    if current:
        chunks.append("\n".join(current))
    return chunks


def chunk_code_file(file_path: Path, repo_root: Path, repo_id: str) -> List[CodeChunk]:
    suffix = file_path.suffix.lower()
    language_name = LANGUAGE_MAP.get(suffix)
    if not language_name:
        return []

    try:
        source = file_path.read_bytes()
        relative_path = str(file_path.relative_to(repo_root))
        parser = get_parser(language_name)
        tree = parser.parse(source)
        node_types = FUNCTION_NODE_TYPES.get(language_name, [])
        chunks: List[CodeChunk] = []

        def walk(node):
            if node.type in node_types:
                content = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                symbol_name = get_node_name(node, source)
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1

                if count_tokens(content) > MAX_CHUNK_TOKENS:
                    for i, sub in enumerate(split_large_chunk(content)):
                        chunks.append(CodeChunk(
                            repo_id=repo_id, file_path=relative_path,
                            language=language_name, chunk_type=node.type,
                            symbol_name=f"{symbol_name}_part{i+1}",
                            start_line=start_line, end_line=end_line, content=sub
                        ))
                else:
                    chunks.append(CodeChunk(
                        repo_id=repo_id, file_path=relative_path,
                        language=language_name, chunk_type=node.type,
                        symbol_name=symbol_name, start_line=start_line,
                        end_line=end_line, content=content
                    ))
                return  # don't recurse into matched nodes

            for child in node.children:
                walk(child)

        walk(tree.root_node)

        if not chunks:
            content = source.decode("utf-8", errors="replace")
            chunks = chunk_text_file(content, relative_path, repo_id, language_name)

        return chunks
    except Exception as e:
        print(f"[chunker] Failed to parse {file_path}: {e}")
        return []


def chunk_text_file(content: str, relative_path: str, repo_id: str, language: str = "text") -> List[CodeChunk]:
    lines = content.split("\n")
    chunks, current_lines, current_tokens, chunk_index = [], [], 0, 0

    for line in lines:
        line_tokens = count_tokens(line)
        is_heading = line.startswith("## ") or line.startswith("# ")
        over_limit = current_tokens + line_tokens > MAX_CHUNK_TOKENS

        if (is_heading or over_limit) and current_lines:
            chunks.append(CodeChunk(
                repo_id=repo_id, file_path=relative_path, language=language,
                chunk_type="text", symbol_name=f"chunk_{chunk_index}",
                start_line=0, end_line=0, content="\n".join(current_lines)
            ))
            chunk_index += 1
            current_lines, current_tokens = [], 0

        current_lines.append(line)
        current_tokens += line_tokens

    if current_lines:
        chunks.append(CodeChunk(
            repo_id=repo_id, file_path=relative_path, language=language,
            chunk_type="text", symbol_name=f"chunk_{chunk_index}",
            start_line=0, end_line=0, content="\n".join(current_lines)
        ))

    return chunks


def chunk_file(file_path: Path, repo_root: Path, repo_id: str) -> List[CodeChunk]:
    suffix = file_path.suffix.lower()
    if suffix in LANGUAGE_MAP:
        return chunk_code_file(file_path, repo_root, repo_id)
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        relative_path = str(file_path.relative_to(repo_root))
        return chunk_text_file(content, relative_path, repo_id, suffix.lstrip(".") or "text")
    except Exception:
        return []
```

---

## Step 8 — Cloner

Create `backend/ingestion/cloner.py`:

```python
import subprocess
import hashlib
from pathlib import Path
from urllib.parse import urlparse
from config import get_settings

settings = get_settings()


def validate_github_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc not in ("github.com", "www.github.com"):
        raise ValueError(f"Not a GitHub URL: {url}")
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub repo URL: {url}")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    return f"https://github.com/{owner}/{repo}"


def url_to_repo_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def clone_repo(github_url: str, target_dir: Path) -> Path:
    clean_url = validate_github_url(github_url)
    if settings.github_token:
        parsed = urlparse(clean_url)
        clone_url = f"https://{settings.github_token}@{parsed.netloc}{parsed.path}"
    else:
        clone_url = clean_url

    repo_path = target_dir / "repo"
    repo_path.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--single-branch", clone_url, str(repo_path)],
        capture_output=True, text=True, timeout=120
    )

    if result.returncode != 0:
        raise RuntimeError(f"Git clone failed: {result.stderr}")

    return repo_path
```

---

## Step 9 — Embedder

Create `backend/ingestion/embedder.py`:

```python
from openai import OpenAI
from typing import List, Dict, Any, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential
from models.schemas import CodeChunk
from config import get_settings
import math, re
from collections import Counter

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)
EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
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
    return {"indices": indices, "values": values}


def embed_chunks(chunks: List[CodeChunk]) -> Tuple[List[List[float]], List[Dict[str, Any]]]:
    texts = [f"File: {c.file_path}\nSymbol: {c.symbol_name}\n\n{c.content}" for c in chunks]
    dense_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        dense_embeddings.extend(embed_batch(batch))
        print(f"[embedder] {min(i + BATCH_SIZE, len(texts))}/{len(texts)} chunks embedded")
    sparse_embeddings = [build_sparse_vector(t) for t in texts]
    return dense_embeddings, sparse_embeddings


def embed_query(question: str) -> Tuple[List[float], Dict[str, Any]]:
    dense = embed_batch([question])[0]
    sparse = build_sparse_vector(question)
    return dense, sparse
```

---

## Step 10 — Ingestion Pipeline

Create `backend/ingestion/pipeline.py`:

```python
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
```

---

## Step 11 — Celery

Create `backend/celeryconfig.py`:

```python
from config import get_settings
settings = get_settings()
broker_url = settings.redis_url
result_backend = settings.redis_url
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
task_track_started = True
```

Create `backend/tasks/index_repo.py`:

```python
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
```

---

## Step 12 — Retrieval

Create `backend/retrieval/searcher.py`:

```python
from ingestion.embedder import embed_query
from storage.qdrant import hybrid_search
from typing import List, Dict, Any


async def search_chunks(repo_id: str, question: str, top_k: int = 20) -> List[Dict[str, Any]]:
    dense, sparse = embed_query(question)
    return await hybrid_search(repo_id, dense, sparse, top_k=top_k)
```

Create `backend/retrieval/reranker.py`:

```python
import cohere
from typing import List, Dict, Any
from config import get_settings
from tenacity import retry, stop_after_attempt, wait_exponential

settings = get_settings()
co = cohere.Client(settings.cohere_api_key)


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
```

Create `backend/retrieval/context_builder.py`:

```python
from typing import List, Dict, Any, Tuple
from models.schemas import Citation


def build_context(chunks: List[Dict[str, Any]]) -> Tuple[str, List[Citation]]:
    context_parts = []
    citations = []

    for i, chunk in enumerate(chunks, start=1):
        file_path = chunk.get("file_path", "unknown")
        symbol = chunk.get("symbol_name", "unknown")
        language = chunk.get("language", "text")
        start_line = chunk.get("start_line", 0)
        end_line = chunk.get("end_line", 0)
        content = chunk.get("content", "")

        context_parts.append(
            f"[{i}] {file_path} — {symbol} (lines {start_line}-{end_line})\n"
            f"```{language}\n{content}\n```"
        )
        citations.append(Citation(
            index=i, file_path=file_path, symbol_name=symbol,
            start_line=start_line, end_line=end_line, language=language
        ))

    return "\n\n---\n\n".join(context_parts), citations
```

---

## Step 13 — LLM + Langfuse

Create `backend/llm/prompts.py`:

```python
SYSTEM_PROMPT = """You are an expert code analyst. You answer questions about software codebases.

You are given numbered code chunks retrieved from the codebase. Use them to answer the question.

Rules:
- Always cite your sources using [1], [2], [3] notation referencing the chunk numbers
- Be precise about file paths and function names
- If the answer is not in the provided chunks, say so explicitly — do not hallucinate
- If you spot a bug or security issue while answering, mention it
- Keep answers concise but complete
"""

def build_user_prompt(context: str, question: str) -> str:
    return f"""Here are relevant code chunks from the repository:

{context}

---

Question: {question}

Answer with citations [1], [2], etc."""
```

Create `backend/llm/client.py`:

```python
import anthropic, json
from langfuse import Langfuse
from config import get_settings
from llm.prompts import SYSTEM_PROMPT, build_user_prompt
from models.schemas import Citation
from typing import List, AsyncGenerator, Dict, Any

settings = get_settings()
anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
langfuse = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    host=settings.langfuse_host,
)


async def stream_answer(
    question: str,
    context: str,
    citations: List[Citation],
    repo_id: str,
    history: List[Dict[str, str]] = []
) -> AsyncGenerator[str, None]:
    trace = langfuse.trace(
        name="rag_query",
        input={"question": question, "repo_id": repo_id},
        metadata={"num_citations": len(citations)}
    )

    user_prompt = build_user_prompt(context, question)
    messages = [{"role": m["role"], "content": m["content"]} for m in history[-6:]]
    messages.append({"role": "user", "content": user_prompt})

    span = trace.span(name="llm_call", input={"messages": messages})
    full_response = ""

    try:
        with anthropic_client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                yield f"data: {json.dumps({'type': 'chunk', 'content': text})}\n\n"

        yield f"data: {json.dumps({'type': 'citations', 'data': [c.model_dump() for c in citations]})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

        span.end(output={"response": full_response})
        trace.update(output={"answer": full_response})
    except Exception as e:
        span.end(output={"error": str(e)}, level="ERROR")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    finally:
        langfuse.flush()
```

---

## Step 14 — API Endpoints

Create `backend/api/health.py`:

```python
from fastapi import APIRouter
import redis as redis_lib
from qdrant_client import QdrantClient
from config import get_settings

router = APIRouter()
settings = get_settings()

@router.get("/health")
async def health():
    status = {"status": "ok", "qdrant": "unknown", "redis": "unknown"}
    try:
        QdrantClient(url=settings.qdrant_url).get_collections()
        status["qdrant"] = "ok"
    except Exception as e:
        status["qdrant"] = f"error: {e}"
    try:
        redis_lib.from_url(settings.redis_url).ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {e}"
    return status
```

Create `backend/api/repos.py`:

```python
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
```

Create `backend/api/chat.py`:

```python
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

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

---

## Step 15 — FastAPI Main

Create `backend/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.health import router as health_router
from api.repos import router as repos_router
from api.chat import router as chat_router
from config import get_settings

settings = get_settings()
app = FastAPI(title="Codebase Q&A API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["health"])
app.include_router(repos_router, tags=["repos"])
app.include_router(chat_router, tags=["chat"])
```

**CHECKPOINT:** Run `uvicorn main:app --reload` from the `backend/` dir. `GET /health` must return qdrant=ok and redis=ok before continuing.

---

## Step 16 — Frontend

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app
npm install react-markdown react-syntax-highlighter @types/react-syntax-highlighter lucide-react
```

Create `frontend/src/lib/api.ts`:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Citation {
  index: number;
  file_path: string;
  symbol_name: string;
  start_line: number;
  end_line: number;
  language: string;
}

export async function indexRepo(githubUrl: string) {
  const res = await fetch(`${API_BASE}/repos/index`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: githubUrl }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ repo_id: string; status: string }>;
}

export async function getRepoStatus(repoId: string) {
  const res = await fetch(`${API_BASE}/repos/${repoId}/status`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{
    status: string; progress: number; total_chunks: number; error?: string;
  }>;
}

export async function streamChat(
  repoId: string,
  question: string,
  history: { role: string; content: string }[],
  onChunk: (text: string) => void,
  onCitations: (citations: Citation[]) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_id: repoId, question, history }),
  });

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const lines = decoder.decode(value).split("\n");
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const event = JSON.parse(line.slice(6));
        if (event.type === "chunk") onChunk(event.content);
        if (event.type === "citations") onCitations(event.data);
        if (event.type === "done") onDone();
        if (event.type === "error") onError(event.message);
      } catch {}
    }
  }
}
```

Create `frontend/src/hooks/useIndexingStatus.ts`:

```typescript
import { useState, useEffect } from "react";
import { getRepoStatus } from "@/lib/api";

export function useIndexingStatus(repoId: string | null) {
  const [status, setStatus] = useState("pending");
  const [progress, setProgress] = useState(0);
  const [totalChunks, setTotalChunks] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!repoId || status === "done" || status === "error") return;
    const interval = setInterval(async () => {
      try {
        const data = await getRepoStatus(repoId);
        setStatus(data.status);
        setProgress(data.progress);
        setTotalChunks(data.total_chunks);
        if (data.error) setError(data.error);
        if (data.status === "done" || data.status === "error") clearInterval(interval);
      } catch (e) { console.error(e); }
    }, 2000);
    return () => clearInterval(interval);
  }, [repoId, status]);

  return { status, progress, totalChunks, error };
}
```

Create `frontend/src/hooks/useChat.ts`:

```typescript
import { useState, useCallback } from "react";
import { streamChat, Citation } from "@/lib/api";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
}

export function useChat(repoId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (question: string) => {
    const userId = Date.now().toString();
    const assistantId = (Date.now() + 1).toString();

    setMessages(prev => [
      ...prev,
      { id: userId, role: "user", content: question },
      { id: assistantId, role: "assistant", content: "", isStreaming: true },
    ]);
    setIsLoading(true);

    const history = messages.map(m => ({ role: m.role, content: m.content }));

    await streamChat(
      repoId, question, history,
      chunk => setMessages(prev => prev.map(m =>
        m.id === assistantId ? { ...m, content: m.content + chunk } : m)),
      citations => setMessages(prev => prev.map(m =>
        m.id === assistantId ? { ...m, citations } : m)),
      () => {
        setMessages(prev => prev.map(m =>
          m.id === assistantId ? { ...m, isStreaming: false } : m));
        setIsLoading(false);
      },
      err => { console.error(err); setIsLoading(false); }
    );
  }, [messages, repoId]);

  return { messages, isLoading, sendMessage };
}
```

Build these components — tell Claude Code to implement each one fully:

- **`RepoInput.tsx`** — GitHub URL text input + "Analyze Repo" button. On submit calls `indexRepo()` and saves `repo_id` to localStorage, then navigates to `/chat/{repo_id}`.
- **`IndexingStatus.tsx`** — Uses `useIndexingStatus` hook. Shows animated progress bar, current step label (Cloning → Chunking → Embedding → Storing), and total chunks found. When status === "done", calls `onComplete()` prop.
- **`ChatWindow.tsx`** — Full chat layout. Uses `useChat`. Scrolls to bottom on new messages. Input box with send button at bottom.
- **`MessageBubble.tsx`** — Renders markdown content with `react-markdown`. Code blocks use `react-syntax-highlighter` with dark theme. Shows [1] [2] citation superscripts as clickable badges.
- **`CitationCard.tsx`** — Card showing file_path, symbol_name, line range. On click opens `https://github.com/{owner}/{repo}/blob/main/{file_path}#L{start_line}`. Parse owner/repo from repo_url stored in status.
- **`app/page.tsx`** — Landing page with `RepoInput`. Clean, minimal, shows recent repos from localStorage.
- **`app/chat/[repoId]/page.tsx`** — Fetches initial status. If not done, shows `IndexingStatus` with redirect to same page on complete. If done, shows `ChatWindow`.

---

## Step 17 — Deployment Configs

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `backend/railway.toml`:

```toml
[build]
builder = "dockerfile"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
```

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=https://your-railway-backend-url.railway.app
```

Deploy order:
1. Push backend to Railway → get backend URL
2. Add all env vars in Railway dashboard
3. Create second Railway service (same repo, same Dockerfile) with start command: `celery -A tasks.index_repo.celery_app worker --loglevel=info`
4. Add Railway Redis plugin
5. Add Qdrant Cloud free tier → get URL + API key
6. Deploy frontend to Vercel → set `NEXT_PUBLIC_API_URL`

---

## Final Build Order (run in this exact sequence tonight)

```
[  ] docker compose up -d
[  ] pip install -r backend/requirements.txt
[  ] Write Steps 3-15 (backend) in order
[  ] uvicorn main:app --reload → GET /health → all green
[  ] celery -A tasks.index_repo.celery_app worker --loglevel=info
[  ] POST /repos/index {"github_url": "https://github.com/tiangolo/fastapi"}
[  ] Poll GET /repos/{id}/status until done
[  ] POST /chat → verify real answer with citations
[  ] Build frontend (Step 16)
[  ] npm run dev → test full flow in browser
[  ] Deploy (Step 17)
```

First test question to verify everything works end-to-end:
> "how does dependency injection work?"

Expected: Answer citing files in `fastapi/` with line numbers you can click.

---

## Interview Demo (6 steps, memorize these)

1. Paste `https://github.com/tiangolo/fastapi` → show live progress bar
2. Ask: *"how does dependency injection work?"*
3. Click a citation → exact line opens on GitHub
4. Open Langfuse → show the full trace of that query
5. Explain: *"tree-sitter parses AST — every function is its own chunk, never split mid-scope"*
6. Explain: *"hybrid search merges vector similarity + BM25 keyword match, then Cohere reranks"*

That is the entire demo. Do not show anything else first.
