from __future__ import annotations

import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

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


@router.get("/admin/documents", summary="Danh sách tài liệu", dependencies=[Depends(require_admin)])
async def list_documents():
    raw_dir = Path(settings.RAG_RAW_DIR)
    registry = _registry()
    documents = []
    if raw_dir.exists():
        for path in sorted(raw_dir.iterdir(), key=lambda item: item.name.casefold()):
            if path.is_file() and path.suffix.lower() in {".pdf", ".docx"}:
                item = {
                    "file_name": path.name,
                    "size_bytes": path.stat().st_size,
                    "status": "active",
                }
                item.update(registry.get(path.name, {}))
                documents.append(item)
    return {"documents": documents}


@router.post("/admin/upload", summary="Thêm hoặc thay PDF/DOCX", dependencies=[Depends(require_admin)])
async def upload_document(
    file: UploadFile = File(...),
    change_type: str = Form(default="new"),
    related_document: Optional[str] = Form(default=None),
    file_svc: FileService = Depends(lambda: file_service),
):
    if change_type not in {"new", "replace"}:
        raise HTTPException(status_code=422, detail="Chỉ hỗ trợ thêm mới hoặc thay tài liệu.")
    if change_type == "replace":
        if not related_document:
            raise HTTPException(status_code=422, detail="Hãy chọn tài liệu cần thay thế.")
        if Path(related_document).name != related_document or not (Path(settings.RAG_RAW_DIR) / related_document).is_file():
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu cần thay thế.")

    file_name, size, formatted = await file_svc.save_upload_file(
        file, replace_name=related_document if change_type == "replace" else None
    )
    registry = _registry()
    if change_type == "replace" and related_document != file_name:
        registry.pop(related_document, None)
    registry[file_name] = {
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "index_status": "pending",
        "replaces": related_document if change_type == "replace" else None,
    }
    _save_registry(registry)

    index_status = "pending"
    message = "Đã thêm tài liệu. Bấm Cập nhật kho để chatbot sử dụng file mới."
    if change_type == "replace":
        from rag_project.pipeline import main as run_pipeline
        try:
            result = await run_in_threadpool(run_pipeline)
        except Exception:
            result = 1
        if result == 0:
            registry = _registry()
            registry[file_name]["index_status"] = "active"
            _save_registry(registry)
            index_status = "active"
            message = f"Đã thay {related_document} bằng {file_name} và cập nhật kho."
        else:
            message = "Đã lưu bản mới và lưu trữ bản cũ, nhưng cập nhật kho chưa thành công. Hãy bấm Cập nhật kho sau khi xử lý lỗi."
    return {
        "success": True,
        "file_name": file_name,
        "file_size_bytes": size,
        "file_size_formatted": formatted,
        "change_type": change_type,
        "index_status": index_status,
        "message": message,
    }


@router.post("/admin/reindex", summary="Cập nhật kho tài liệu", dependencies=[Depends(require_admin)])
async def reindex_documents():
    from rag_project.pipeline import main as run_pipeline

    result = await run_in_threadpool(run_pipeline)
    if result != 0:
        raise HTTPException(status_code=422, detail="Không thể cập nhật kho. Chỉ mục cũ vẫn được giữ; hãy kiểm tra file PDF/DOCX trong thư mục tài liệu.")
    registry = _registry()
    for info in registry.values():
        if isinstance(info, dict) and info.get("index_status") == "pending":
            info["index_status"] = "active"
    _save_registry(registry)
    return {"success": True, "message": "Đã cập nhật kho tài liệu. Các file hiện hành có thể được dùng trong câu trả lời."}


@router.post("/admin/documents/delete", summary="Xóa tài liệu khỏi kho hiện hành", dependencies=[Depends(require_admin)])
async def delete_document(file_name: str = Form(...)):
    raw_dir = Path(settings.RAG_RAW_DIR)
    if Path(file_name).name != file_name or Path(file_name).suffix.lower() not in {".pdf", ".docx"}:
        raise HTTPException(status_code=422, detail="Tên file không hợp lệ.")
    source = raw_dir / file_name
    if not source.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu đang dùng.")

    archive_dir = raw_dir.parent / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archived = archive_dir / f"{stamp}-{uuid4().hex[:8]}-{file_name}"
    registry = _registry()
    previous_info = registry.pop(file_name, None)
    try:
        os.replace(source, archived)
        _save_registry(registry)
        from rag_project.pipeline import main as run_pipeline
        result = await run_in_threadpool(run_pipeline)
        if result != 0:
            raise RuntimeError("pipeline failed")
    except Exception as exc:
        if archived.exists() and not source.exists():
            os.replace(archived, source)
        if previous_info is not None:
            registry[file_name] = previous_info
        _save_registry(registry)
        raise HTTPException(status_code=422, detail="Chưa xóa được tài liệu vì cập nhật chỉ mục thất bại. File đã được khôi phục vào kho đang dùng.") from exc

    return {"success": True, "message": f"Đã xóa {file_name} khỏi kho và cập nhật chỉ mục. Bản sao được giữ trong kho lưu trữ."}
