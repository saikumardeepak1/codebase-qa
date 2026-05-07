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
    chunk_strategy: str = "ast"


class CodeChunk(BaseModel):
    repo_id: str
    file_path: str
    language: str
    chunk_type: str
    symbol_name: str
    start_line: int
    end_line: int
    content: str
    chunk_strategy: str = "ast"
