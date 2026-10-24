"""Adapter between the TV3 HTTP API and the TV1/TV2 RAG engine."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from app.core.exceptions import RAGServiceException
from app.schemas.chat import CitationItem

BACKEND_ROOT = Path(__file__).resolve().parents[2]
RAG_DATA_ROOT = BACKEND_ROOT / "data"

# The paths point to the shared TV1 data folders regardless of the process cwd.
os.environ.setdefault("RAG_DATA_DIR", str(RAG_DATA_ROOT / "processed"))
os.environ.setdefault("QDRANT_PATH", str(RAG_DATA_ROOT / "qdrant"))
os.environ.setdefault(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
try:
    from rag_project import ask_rag
except ImportError as exc:  # Give a clear setup error when TV1/TV2 dependencies are absent.
    _IMPORT_ERROR: Exception | None = exc
else:
    _IMPORT_ERROR = None


class RAGService:
    def ask(self, query: str, session_id: str) -> Dict[str, Any]:
        if _IMPORT_ERROR is not None:
            raise RAGServiceException(
                "RAG chưa sẵn sàng. Hãy cài các thư viện trong backend/requirements.txt."
            ) from _IMPORT_ERROR

        index_file = RAG_DATA_ROOT / "processed" / "bm25.pkl"
        if not index_file.exists():
            return {
                "answer": "Chưa tìm thấy thông tin phù hợp trong tài liệu hiện có. Quản trị viên cần thêm tài liệu và chạy pipeline lập chỉ mục.",
                "citations": [],
                "confidence_score": 0.0,
                "session_id": session_id,
            }

        try:
            result = ask_rag(query)
        except Exception as exc:
            raise RAGServiceException("Hệ thống tri thức AI tạm thời không phản hồi.") from exc

        if result.get("error"):
            raise RAGServiceException("Không thể truy vấn chỉ mục RAG. Hãy kiểm tra dữ liệu và cấu hình.")

        citations: List[CitationItem] = []
        for citation in result.get("citations", []):
            doc_name = citation.get("doc_name")
            if not doc_name:
                continue
            citations.append(
                CitationItem(
                    doc_name=str(doc_name),
                    page_number=citation.get("page_number"),
                    chapter=citation.get("chapter"),
                    article=citation.get("article"),
                    clause=citation.get("clause"),
                    chunk_id=citation.get("chunk_id"),
                )
            )

        return {
            "answer": result.get("answer") or "Chưa tìm thấy thông tin phù hợp trong tài liệu hiện có.",
            "citations": citations,
            "confidence_score": result.get("confidence_score"),
            "session_id": session_id,
        }


rag_service = RAGService()
