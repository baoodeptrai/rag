from fastapi import APIRouter, status
from app.schemas.common import HealthResponse
from app.core.config import settings

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Kiểm tra trạng thái dịch vụ"
)
async def check_health():
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        service="student-rag-backend-api"
    )
