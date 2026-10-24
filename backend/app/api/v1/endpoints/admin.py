from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, status, Depends
from app.schemas.admin import DocumentUploadResponse
from app.services.file_service import file_service, FileService

router = APIRouter()


@router.post(
    "/admin/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin tải lên tài liệu mới (.pdf, .docx)"
)
async def upload_document(
    file: UploadFile = File(..., description="Tệp tài liệu (.pdf hoặc .docx)"),
    category: Optional[str] = Form(default="dao_tao", description="Phân loại tài liệu"),
    file_svc: FileService = Depends(lambda: file_service)
):
    safe_name, file_size, formatted_size = await file_svc.save_upload_file(file)

    return DocumentUploadResponse(
        success=True,
        file_name=safe_name,
        file_size_bytes=file_size,
        file_size_formatted=formatted_size,
        category=category,
        message="Tài liệu đã được tải lên thành công."
    )
