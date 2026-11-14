import asyncio
import logging
import os

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.api.v1.router import api_router
from app.schemas.common import HealthResponse

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API Trợ lý ảo AI Hỗ trợ Sinh viên dựa trên RAG.",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Đăng ký xử lý lỗi
register_exception_handlers(app)


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Hệ thống"],
    summary="Kiểm tra trạng thái máy chủ"
)
async def root_health():
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        service="student-rag-backend-api"
    )


@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs")


app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def warm_retrieval_embedding():
    """Load the local embedding model before accepting chat requests."""
    try:
        from rag_project.rag import _embedding_model

        model_name = os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )
        await asyncio.to_thread(_embedding_model, model_name)
        logging.getLogger(__name__).info("Local retrieval embedding model is ready")
    except Exception:
        # Keep health/docs available so a missing local model can be diagnosed;
        # the chat path will report its retrieval error when used.
        logging.getLogger(__name__).exception("Could not warm the local retrieval embedding model")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
