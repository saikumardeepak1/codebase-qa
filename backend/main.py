from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.health import router as health_router
from api.repos import router as repos_router
from api.chat import router as chat_router
from api.retrieve import router as retrieve_router
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
app.include_router(retrieve_router, tags=["retrieve"])
