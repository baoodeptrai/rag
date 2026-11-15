"""Local, human-reviewed analysis of document amendments against active chunks."""
from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from typing import Any

from .ingest import chunk_section, read_document, split_sections
from .rag import _call_local_model, _tokens


def _new_document_chunks(path: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    context = {"chapter": None, "article": None, "clause": None}
    for page in read_document(path):
        sections = split_sections(page["text"])
        if sections:
            if sections[0].get("chapter") is None: sections[0]["chapter"] = context["chapter"]
            if sections[0].get("article") is None: sections[0]["article"] = context["article"]
            if sections[0].get("clause") is None: sections[0]["clause"] = context["clause"]
            for section in sections:
                for key in context:
                    if section.get(key) is not None: context[key] = section[key]
        elif page["text"]:
            sections = [{"chapter": None, "article": None, "clause": None, "text": page["text"]}]
        for section in sections:
            chunks.extend(chunk_section(section, path.name, page["page_number"]))
    return chunks


def analyze_amendment(file_name: str, related_document: str, raw_dir: Path) -> list[dict[str, Any]]:
    """Compare each new chunk with lexical candidates from the linked active source."""
    if Path(file_name).name != file_name or Path(related_document).name != related_document:
        raise ValueError("Tên tài liệu không hợp lệ.")
    new_path = raw_dir / file_name
    if not new_path.is_file() or not (raw_dir / related_document).is_file():
        raise FileNotFoundError("Không tìm thấy tài liệu sửa đổi hoặc tài liệu gốc đang hoạt động.")

    bm25_path = raw_dir.parent / "processed" / "bm25.pkl"
    if not bm25_path.is_file():
        raise FileNotFoundError("Chưa có index hiện hành để đối chiếu. Hãy lập chỉ mục tài liệu gốc trước.")
    with bm25_path.open("rb") as stream:
        old_chunks, bm25 = pickle.load(stream)
    old_indices = [i for i, chunk in enumerate(old_chunks) if chunk.get("doc_name") == related_document]
    if not old_indices or bm25 is None:
        raise ValueError("Không tìm thấy chunks đang hoạt động của tài liệu gốc trong index.")

    new_chunks = _new_document_chunks(new_path)
    if not new_chunks:
        raise ValueError("Không trích xuất được nội dung từ tài liệu sửa đổi.")
    if len(new_chunks) > 50:
        raise ValueError(f"Tài liệu tạo thành {len(new_chunks)} chunks; hãy chia nhỏ để AI phân tích tối đa 50 chunks mỗi lần.")

    model = os.getenv("ORCHESTRATOR_MODEL", "qwen3:4b").strip()
    if not model:
        raise RuntimeError("Chưa cấu hình ORCHESTRATOR_MODEL trong backend/.env.")
    results = []
    for new_chunk in new_chunks:
        scores = bm25.get_scores(_tokens(new_chunk["text"]))
        candidate_indices = sorted(old_indices, key=lambda i: float(scores[i]), reverse=True)[:3]
        candidates = [old_chunks[i] for i in candidate_indices]
        if not candidates or not any(float(scores[i]) > 0 for i in candidate_indices):
            results.append({
                "new_chunk_id": new_chunk["chunk_id"],
                "new_page_number": new_chunk.get("page_number"),
                "new_article": new_chunk.get("article"),
                "new_text": new_chunk["text"][:500],
                "classification": "uncertain",
                "superseded_chunk_ids": [],
                "confidence": 0.0,
                "rationale": "Không tìm được đoạn tương ứng đủ gần trong tài liệu gốc; cần quản trị viên xem thủ công.",
                "candidates": [],
            })
            continue

        candidate_ids = [str(chunk["chunk_id"]) for chunk in candidates]
        schema = {
            "type": "object",
            "properties": {
                "classification": {"type": "string", "enum": ["replace", "add", "unchanged", "uncertain"]},
                "superseded_chunk_ids": {"type": "array", "items": {"type": "string", "enum": candidate_ids}},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "rationale": {"type": "string"},
            },
            "required": ["classification", "superseded_chunk_ids", "confidence", "rationale"],
            "additionalProperties": False,
        }
        old_context = "\n\n".join(
            f"OLD chunk_id={chunk['chunk_id']} | trang={chunk.get('page_number')} | {chunk.get('article')}\n{chunk['text'][:850]}"
            for chunk in candidates
        )
        prompt = (
            "So sánh từng đoạn mới với các đoạn cũ bên dưới. Chỉ phân loại replace khi đoạn mới rõ ràng "
            "thay thế hoặc sửa nội dung của cùng một quy định; không xem đoạn cùng chủ đề là thay thế. "
            "Thông tin bổ sung là add; không đủ căn cứ là uncertain. Chỉ chọn chunk_id có trong danh sách; "
            "không tự suy diễn hiệu lực pháp lý.\n\n"
            f"NEW chunk_id={new_chunk['chunk_id']} | trang={new_chunk.get('page_number')} | {new_chunk.get('article')}\n"
            f"{new_chunk['text'][:1100]}\n\nOLD CANDIDATES:\n{old_context}"
        )
        raw = _call_local_model(model, [
            {"role": "system", "content": "Bạn là trợ lý đối chiếu phiên bản văn bản, chạy offline. Chỉ trả JSON theo schema."},
            {"role": "user", "content": prompt},
        ], num_predict=180, response_format=schema)
        parsed = json.loads(raw)
        classification = parsed.get("classification", "uncertain")
        superseded = [item for item in parsed.get("superseded_chunk_ids", []) if item in candidate_ids]
        confidence = parsed.get("confidence", 0)
        try: confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError): confidence = 0.0
        if classification != "replace" or not superseded:
            superseded = []
            if classification == "replace": classification = "uncertain"
        results.append({
            "new_chunk_id": new_chunk["chunk_id"],
            "new_page_number": new_chunk.get("page_number"),
            "new_article": new_chunk.get("article"),
            "new_text": new_chunk["text"][:500],
            "classification": classification,
            "superseded_chunk_ids": superseded,
            "confidence": confidence,
            "rationale": str(parsed.get("rationale", ""))[:500],
            "candidates": [{
                "chunk_id": chunk["chunk_id"],
                "page_number": chunk.get("page_number"),
                "article": chunk.get("article"),
                "text": chunk["text"][:500],
            } for chunk in candidates],
        })
    return results
