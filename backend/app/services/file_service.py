import os
import re
import logging
from typing import Tuple
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

    async def save_upload_file(self, file: UploadFile) -> Tuple[str, int, str]:
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
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        total_size = 0

        try:
            with open(target_path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    total_size += len(chunk)
                    if total_size > max_bytes:
                        buffer.close()
                        if os.path.exists(target_path):
                            os.remove(target_path)
                        raise FileValidationException(
                            f"Dung lượng file vượt quá giới hạn ({settings.MAX_FILE_SIZE_MB}MB)."
                        )
                    buffer.write(chunk)

            formatted_size = self.format_file_size(total_size)
            logger.info(f"Đã lưu file: {safe_name} ({formatted_size})")
            return safe_name, total_size, formatted_size

        except FileValidationException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi lưu file {safe_name}: {str(e)}", exc_info=True)
            if os.path.exists(target_path):
                os.remove(target_path)
            raise FileValidationException(f"Không thể lưu file: {str(e)}")


file_service = FileService()
