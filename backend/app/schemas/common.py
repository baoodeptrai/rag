from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Trạng thái máy chủ (ví dụ: healthy)")
    version: str = Field(..., description="Phiên bản API hiện tại")
    service: str = Field(..., description="Tên định danh dịch vụ")


class ErrorResponse(BaseModel):
    success: bool = Field(False, description="Luôn là False khi có lỗi xảy ra")
    error_code: str = Field(..., description="Mã định danh lỗi (ví dụ: VALIDATION_ERROR)")
    message: str = Field(..., description="Thông điệp mô tả lỗi chi tiết cho người dùng")
