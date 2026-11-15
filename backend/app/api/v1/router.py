from fastapi import APIRouter
from app.api.v1.endpoints import health, chat, admin, documents

api_router = APIRouter()

api_router.include_router(health.router, tags=["Hệ thống"])
api_router.include_router(chat.router, tags=["Hỏi đáp Trợ lý ảo AI"])
api_router.include_router(admin.router, tags=["Quản trị viên (Admin)"])
api_router.include_router(documents.router, tags=["Tài liệu đọc"])
