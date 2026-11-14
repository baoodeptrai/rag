from __future__ import annotations

import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.services.file_service import FileService, file_service

router = APIRouter()
REGISTRY_PATH = Path(settings.RAG_RAW_DIR).parent / "document_registry.json"


def require_admin(authorization: Optional[str] = Header(default=None)) -> None:
    expected = settings.ADMIN_API_TOKEN.strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Chưa cấu hình ADMIN_API_TOKEN trong backend/.env.")
    supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not authorization or not authorization.startswith("Bearer ") or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Chỉ quản trị viên tài liệu mới được phép thực hiện thao tác này.")


def _registry() -> dict:
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_registry(registry: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = REGISTRY_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, REGISTRY_PATH)


@router.get("/admin/documents", summary="Danh sách tài liệu đang hoạt động", dependencies=[Depends(require_admin)])
async def list_documents():
    raw_dir = Path(settings.RAG_RAW_DIR)
    registry = _registry()

    def describe(path: Path, archived: bool = False):
        info = path.stat()
        item = {
            "file_name": path.name,
            "size_bytes": info.st_size,
            "modified_at": datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat(),
            "status": "archived" if archived else "active",
        }
        if not archived:
            item.update(registry.get(path.name, {}))
        return item

    active = sorted((describe(p) for p in raw_dir.iterdir() if p.is_file() and p.suffix.lower() in {".pdf", ".docx"}), key=lambda x: x["file_name"].lower()) if raw_dir.exists() else []
    archive_dir = raw_dir.parent / "archive"
    archive = sorted((describe(p, True) for p in archive_dir.iterdir() if p.is_file()), key=lambda x: x["modified_at"], reverse=True) if archive_dir.exists() else []
    return {"documents": active, "archive": archive}


@router.post("/admin/upload", summary="Tải tài liệu lên kho", dependencies=[Depends(require_admin)])
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="dao_tao"),
    change_type: str = Form(default="new"),
    related_document: Optional[str] = Form(default=None),
    file_svc: FileService = Depends(lambda: file_service),
):
    if change_type not in {"new", "replace", "amendment"}:
        raise HTTPException(status_code=422, detail="Loại cập nhật tài liệu không hợp lệ.")
    if change_type == "replace" and not related_document:
        raise HTTPException(status_code=422, detail="Hãy chọn tài liệu cũ cần thay thế.")
    if change_type == "amendment" and related_document:
        if not (Path(settings.RAG_RAW_DIR) / related_document).is_file():
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu gốc liên quan.")

    replace_name = related_document if change_type == "replace" else None
    file_name, size, formatted = await file_svc.save_upload_file(file, replace_name=replace_name)
    registry = _registry()
    if change_type == "replace" and related_document:
        registry.pop(related_document, None)
    registry[file_name] = {
        "change_type": change_type,
        "category": category,
        "related_document": related_document if change_type == "amendment" else None,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "index_status": "pending",
    }
    _save_registry(registry)
    return {
        "success": True,
        "file_name": file_name,
        "file_size_bytes": size,
        "file_size_formatted": formatted,
        "change_type": change_type,
        "related_document": related_document,
        "index_status": "pending",
        "message": "Đã lưu tài liệu. Hãy chạy Cập nhật chỉ mục để đưa nội dung vào chatbot.",
    }


@router.post("/admin/reindex", summary="Cập nhật chỉ mục từ kho tài liệu", dependencies=[Depends(require_admin)])
async def reindex_documents():
    from rag_project.pipeline import main as run_pipeline

    result = await run_in_threadpool(run_pipeline)
    if result != 0:
        raise HTTPException(status_code=422, detail="Không thể cập nhật chỉ mục. Chỉ mục cũ vẫn được giữ; hãy kiểm tra file lỗi trong backend/data/raw.")
    registry = _registry()
    for info in registry.values():
        if info.get("index_status") == "pending":
            info["index_status"] = "active"
    _save_registry(registry)
    return {"success": True, "message": "Đã cập nhật chỉ mục. Tài liệu mới hiện có thể được dùng trong câu trả lời."}
