from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.config import settings

router = APIRouter(prefix="/documents")


@router.get("", summary="Danh sách PDF hiện hành")
async def list_public_documents():
    raw_dir = Path(settings.RAG_RAW_DIR)
    if not raw_dir.exists():
        return {"documents": []}
    docs = [
        {"file_name": path.name, "size_bytes": path.stat().st_size}
        for path in sorted(raw_dir.iterdir(), key=lambda item: item.name.casefold())
        if path.is_file() and path.suffix.lower() == ".pdf"
    ]
    return {"documents": docs}


@router.get("/pdf", summary="Đọc PDF hiện hành")
async def read_public_pdf(file_name: str = Query(...)):
    if Path(file_name).name != file_name or Path(file_name).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Tên file PDF không hợp lệ.")
    path = Path(settings.RAG_RAW_DIR) / file_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy file PDF đang dùng.")
    return FileResponse(path, media_type="application/pdf", filename=file_name, content_disposition_type="inline")
