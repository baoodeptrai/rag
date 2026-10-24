"""
File: run.py
Mô tả: File khởi động nhanh server FastAPI cho môi trường phát triển cục bộ.
Cách chạy:
    python run.py
"""

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"🚀 Đang khởi động {settings.PROJECT_NAME} tại http://localhost:{settings.PORT}")
    print(f"📄 Xem tài liệu Swagger UI tại: http://localhost:{settings.PORT}/docs")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
