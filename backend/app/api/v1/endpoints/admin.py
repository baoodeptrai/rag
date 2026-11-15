from __future__ import annotations

import hmac
import json
import os
from datetime import date, datetime, timezone
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


def _date_field(value: str, field_name: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} phải theo định dạng YYYY-MM-DD.") from exc


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
    document_number: str = Form(default=""),
    supersedes_number: str = Form(default=""),
    published_at: str = Form(default=""),
    effective_from: str = Form(default=""),
    effective_until: str = Form(default=""),
    file_svc: FileService = Depends(lambda: file_service),
):
    if change_type not in {"new", "replace", "amendment"}:
        raise HTTPException(status_code=422, detail="Loại cập nhật tài liệu không hợp lệ.")
    if change_type == "replace" and not related_document and not supersedes_number.strip():
        raise HTTPException(status_code=422, detail="Hãy chọn tài liệu cũ cần thay thế.")
    if change_type == "amendment" and related_document:
        if not (Path(settings.RAG_RAW_DIR) / related_document).is_file():
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu gốc liên quan.")

    published = _date_field(published_at, "Ngày ban hành")
    starts = _date_field(effective_from, "Ngày hiệu lực")
    ends = _date_field(effective_until, "Ngày hết hiệu lực")
    if starts and ends and ends < starts:
        raise HTTPException(status_code=422, detail="Ngày hết hiệu lực không được trước ngày hiệu lực.")

    registry = _registry()
    raw_dir = Path(settings.RAG_RAW_DIR)
    replace_name = related_document if change_type == "replace" else None
    superseded_name = None
    if supersedes_number.strip():
        wanted = supersedes_number.strip().casefold()
        matches = [
            name for name, info in registry.items()
            if (raw_dir / name).is_file()
            and isinstance(info, dict)
            and str(info.get("document_number", "")).strip().casefold() == wanted
        ]
        if not matches:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu đang dùng có số {supersedes_number.strip()} để thay thế.")
        if len(matches) > 1:
            raise HTTPException(status_code=409, detail=f"Có nhiều tài liệu đang dùng mang số {supersedes_number.strip()}; cần quản trị viên xử lý trùng số trước.")
        superseded_name = matches[0]
        if replace_name and replace_name != superseded_name:
            raise HTTPException(status_code=422, detail="Tài liệu chọn thay thế không khớp với số văn bản bị thay thế.")
        replace_name = superseded_name
        change_type = "replace"

    normalized_number = document_number.strip()
    if normalized_number:
        duplicate_numbers = [
            name for name, info in registry.items()
            if name != replace_name and (raw_dir / name).is_file()
            and isinstance(info, dict)
            and str(info.get("document_number", "")).strip().casefold() == normalized_number.casefold()
        ]
        if duplicate_numbers:
            raise HTTPException(status_code=409, detail=f"Số văn bản {normalized_number} đã được gán cho tài liệu đang dùng: {', '.join(duplicate_numbers)}.")

    file_name, size, formatted = await file_svc.save_upload_file(file, replace_name=replace_name)
    archived_name = replace_name
    archived_info = registry.get(replace_name, {}) if replace_name else {}
    archived_number = supersedes_number.strip() or str(archived_info.get("document_number") or "")
    if replace_name:
        registry.pop(replace_name, None)
    registry[file_name] = {
        "change_type": change_type,
        "category": category,
        "related_document": related_document if change_type == "amendment" else None,
        "supersedes_document": archived_name,
        "supersedes_number": archived_number or None,
        "document_number": normalized_number or None,
        "published_at": published,
        "effective_from": starts,
        "effective_until": ends,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "index_status": "pending",
    }
    _save_registry(registry)

    index_status = "pending"
    message = "Đã lưu tài liệu. Hãy cập nhật chỉ mục để đưa nội dung vào chatbot."
    if replace_name:
        from rag_project.pipeline import main as run_pipeline
        try:
            pipeline_result = await run_in_threadpool(run_pipeline)
        except Exception:
            pipeline_result = 1
        if pipeline_result == 0:
            registry = _registry()
            registry[file_name]["index_status"] = "active"
            _save_registry(registry)
            index_status = "active"
            message = f"Đã lưu trữ {archived_name}, cập nhật chỉ mục và đưa văn bản mới vào sử dụng."
        else:
            message = f"Đã lưu trữ {archived_name} và nhận văn bản mới, nhưng lập chỉ mục chưa thành công. Chỉ mục trước vẫn hoạt động; hãy sửa lỗi rồi dựng lại chỉ mục."
    return {
        "success": True,
        "file_name": file_name,
        "file_size_bytes": size,
        "file_size_formatted": formatted,
        "change_type": change_type,
        "related_document": related_document,
        "supersedes_document": archived_name,
        "index_status": index_status,
        "message": message,
    }


@router.post("/admin/reindex", summary="Cập nhật chỉ mục từ kho tài liệu", dependencies=[Depends(require_admin)])
async def reindex_documents():
    from rag_project.pipeline import main as run_pipeline

    result = await run_in_threadpool(run_pipeline)
    if result != 0:
        raise HTTPException(status_code=422, detail="Không thể cập nhật chỉ mục. Chỉ mục cũ vẫn được giữ; hãy kiểm tra file lỗi trong backend/data/raw.")
    registry = _registry()
    for info in registry.values():
        if isinstance(info, dict) and info.get("index_status") == "pending":
            info["index_status"] = "active"
    _save_registry(registry)
    return {"success": True, "message": "Đã cập nhật chỉ mục. Tài liệu mới hiện có thể được dùng trong câu trả lời."}


@router.post("/admin/documents/metadata", summary="Cập nhật số hiệu và thời hạn tài liệu", dependencies=[Depends(require_admin)])
async def update_document_metadata(
    file_name: str = Form(...),
    document_number: str = Form(default=""),
    published_at: str = Form(default=""),
    effective_from: str = Form(default=""),
    effective_until: str = Form(default=""),
):
    raw_dir = Path(settings.RAG_RAW_DIR)
    if Path(file_name).name != file_name or not (raw_dir / file_name).is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu hiện hành.")
    number = document_number.strip()
    registry = _registry()
    if number:
        duplicates = [
            name for name, info in registry.items()
            if name != file_name and (raw_dir / name).is_file() and isinstance(info, dict)
            and str(info.get("document_number", "")).strip().casefold() == number.casefold()
        ]
        if duplicates:
            raise HTTPException(status_code=409, detail=f"Số văn bản {number} đã gán cho tài liệu: {', '.join(duplicates)}.")
    published = _date_field(published_at, "Ngày ban hành")
    starts = _date_field(effective_from, "Ngày hiệu lực")
    ends = _date_field(effective_until, "Ngày hết hiệu lực")
    if starts and ends and ends < starts:
        raise HTTPException(status_code=422, detail="Ngày hết hiệu lực không được trước ngày hiệu lực.")

    info = registry.get(file_name, {})
    if not isinstance(info, dict):
        info = {}
    info.update({
        "document_number": number or None,
        "published_at": published,
        "effective_from": starts,
        "effective_until": ends,
        "index_status": "pending",
    })
    registry[file_name] = info
    _save_registry(registry)

    from rag_project.pipeline import main as run_pipeline
    try:
        result = await run_in_threadpool(run_pipeline)
    except Exception:
        result = 1
    if result != 0:
        return {"success": True, "index_status": "pending", "message": "Metadata đã lưu nhưng chỉ mục chưa được cập nhật. Chỉ mục trước vẫn hoạt động; hãy kiểm tra lỗi rồi dựng lại."}
    registry = _registry()
    registry[file_name]["index_status"] = "active"
    _save_registry(registry)
    return {"success": True, "index_status": "active", "message": f"Đã cập nhật metadata và lập chỉ mục lại {file_name}."}
