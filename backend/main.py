from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.health import router as health_router
from api.repos import router as repos_router
from api.chat import router as chat_router
from api.retrieve import router as retrieve_router
from config import get_settings

settings = get_settings()
app = FastAPI(title="Codebase Q&A API", version="1.0.0")

ALLOWED_ORIGINS = settings.cors_origins.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # CORSMiddleware doesn't add headers to unhandled 500 responses, so the
    # browser sees a CORS error instead of the real error. Add them manually.
    origin = request.headers.get("origin", "")
    headers = {}
    if origin and (origin in ALLOWED_ORIGINS or "*" in ALLOWED_ORIGINS):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers=headers,
    )

app.include_router(health_router, tags=["health"])
app.include_router(repos_router, tags=["repos"])
app.include_router(chat_router, tags=["chat"])
app.include_router(retrieve_router, tags=["retrieve"])
