from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Nội dung câu hỏi của sinh viên"
    )
    session_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Mã định danh phiên hội thoại"
    )

    @field_validator("message")
    @classmethod
    def validate_message_not_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Nội dung câu hỏi không được để trống.")
        return cleaned


class CitationItem(BaseModel):
    doc_name: str = Field(..., description="Tên tệp tài liệu gốc")
    page_number: Optional[int] = Field(None, description="Số trang chứa nội dung")
    chapter: Optional[str] = Field(None, description="Tên hoặc số chương")
    article: Optional[str] = Field(None, description="Tên hoặc số điều quy chế")
    clause: Optional[str] = Field(None, description="Khoản trong điều quy chế")
    chunk_id: Optional[str] = Field(None, description="Mã định danh đoạn trích xuất vector")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Câu trả lời từ trợ lý ảo AI")
    citations: List[CitationItem] = Field(default_factory=list, description="Danh sách các nguồn trích dẫn")
    confidence_score: Optional[float] = Field(default=None, description="Độ tin cậy của câu trả lời")
    session_id: str = Field(..., description="Mã phiên hội thoại hiện tại")


class HistoryMessage(BaseModel):
    id: str = Field(..., description="Mã định danh tin nhắn")
    role: str = Field(..., description="Vai trò: user hoặc assistant")
    content: str = Field(..., description="Nội dung tin nhắn")
    citations: Optional[List[CitationItem]] = Field(default=None, description="Nguồn trích dẫn nếu có")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Thời gian gửi tin nhắn (UTC)"
    )


class ChatHistoryResponse(BaseModel):
    session_id: str = Field(..., description="Mã phiên hội thoại")
    total_messages: int = Field(..., description="Tổng số tin nhắn trong phiên")
    messages: List[HistoryMessage] = Field(default_factory=list, description="Danh sách tin nhắn")
