from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    success: bool = Field(True, description="Trạng thái tải lên thành công")
    file_name: str = Field(..., description="Tên file gốc đã được làm sạch an toàn")
    file_size_bytes: int = Field(..., description="Dung lượng file tính bằng bytes")
    file_size_formatted: str = Field(..., description="Dung lượng file hiển thị dễ đọc (KB/MB)")
    category: Optional[str] = Field(default="chung", description="Danh mục phân loại tài liệu")
    message: str = Field(..., description="Thông báo trạng thái xử lý")
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Thời điểm tải lên (UTC)"
    )
