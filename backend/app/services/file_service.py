import os
import re
import logging
import tempfile
from datetime import datetime, timezone
from typing import Tuple
from uuid import uuid4
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import FileValidationException

logger = logging.getLogger("rag_backend.file_service")


class FileService:
    def __init__(self):
        self.upload_dir = settings.RAG_RAW_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

    def sanitize_filename(self, filename: str) -> str:
        """Làm sạch tên file để tránh lỗi hệ điều hành và Path Traversal."""
        basename = os.path.basename(filename)
        cleaned = re.sub(r'[^a-zA-Z0-9_\u00C0-\u024F\u1EA0-\u1EF9\.\-]', '_', basename)
        return cleaned

    def format_file_size(self, size_in_bytes: int) -> str:
        """Định dạng kích thước file sang KB hoặc MB."""
        if size_in_bytes < 1024:
            return f"{size_in_bytes} B"
        elif size_in_bytes < 1024 * 1024:
            return f"{size_in_bytes / 1024:.2f} KB"
        else:
            return f"{size_in_bytes / (1024 * 1024):.2f} MB"

    async def save_upload_file(self, file: UploadFile, replace_name: str | None = None) -> Tuple[str, int, str]:
        """Kiểm tra định dạng, dung lượng và lưu file."""
        original_name = file.filename or "unknown_document"
        safe_name = self.sanitize_filename(original_name)

        # Kiểm tra đuôi mở rộng
        _, ext = os.path.splitext(safe_name)
        ext_lower = ext.lower()
        if ext_lower not in settings.allowed_extensions_list:
            raise FileValidationException(
                f"Định dạng file '{ext}' không được hỗ trợ. Chỉ chấp nhận: {settings.ALLOWED_EXTENSIONS}"
            )

        # Lưu file và kiểm tra dung lượng theo stream
        target_path = os.path.join(self.upload_dir, safe_name)
        replacement_path = None
        if replace_name:
            replacement_name = self.sanitize_filename(replace_name)
            if replacement_name != replace_name or os.path.basename(replace_name) != replace_name:
                raise FileValidationException("Tên tài liệu cần thay thế không hợp lệ.")
            replacement_path = os.path.join(self.upload_dir, replacement_name)
            if not os.path.isfile(replacement_path):
                raise FileValidationException("Không tìm thấy tài liệu đang hoạt động cần thay thế.")
            if os.path.exists(target_path) and os.path.abspath(target_path) != os.path.abspath(replacement_path):
                raise FileValidationException("Tên file mới đã được dùng. Hãy đổi tên file hoặc chọn đúng tài liệu cần thay thế.")
        elif os.path.exists(target_path):
            raise FileValidationException("File cùng tên đã tồn tại. Hãy chọn chế độ thay thế bản hiện hành.")
        temp_path = None
        archive_path = None
        archive_original_path = None
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        total_size = 0

        try:
            fd, temp_path = tempfile.mkstemp(prefix=".upload-", suffix=ext_lower, dir=self.upload_dir)
            with os.fdopen(fd, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    total_size += len(chunk)
                    if total_size > max_bytes:
                        raise FileValidationException(
                            f"Dung lượng file vượt quá giới hạn ({settings.MAX_FILE_SIZE_MB}MB)."
                        )
                    buffer.write(chunk)

            # Preserve a prior same-name source outside the active corpus before
            # promoting the complete upload into raw/.
            source_to_archive = replacement_path or (target_path if os.path.exists(target_path) else None)
            if source_to_archive and os.path.exists(source_to_archive):
                archive_original_path = source_to_archive
                archive_dir = os.path.join(os.path.dirname(self.upload_dir), "archive")
                os.makedirs(archive_dir, exist_ok=True)
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                archive_path = os.path.join(archive_dir, f"{stamp}-{uuid4().hex[:8]}-{os.path.basename(source_to_archive)}")
                os.replace(source_to_archive, archive_path)
            try:
                os.replace(temp_path, target_path)
            except Exception:
                if archive_path and archive_original_path and os.path.exists(archive_path) and not os.path.exists(archive_original_path):
                    os.replace(archive_path, archive_original_path)
                raise
            temp_path = None

            formatted_size = self.format_file_size(total_size)
            logger.info(f"Đã lưu file: {safe_name} ({formatted_size})")
            return safe_name, total_size, formatted_size

        except FileValidationException:
            if temp_path and os.path.exists(temp_path): os.remove(temp_path)
            raise
        except Exception as e:
            logger.error(f"Lỗi khi lưu file {safe_name}: {str(e)}", exc_info=True)
            if temp_path and os.path.exists(temp_path): os.remove(temp_path)
            raise FileValidationException(f"Không thể lưu file: {str(e)}")


file_service = FileService()
