from __future__ import annotations
import re, json, hashlib
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
HEADER_RE = re.compile(r"^(Chương\s+[IVXLCDM0-9]+\b.*|Điều\s+\d+\b.*|Khoản\s+\d+\b.*)$", re.I)
ARTICLE_RE = re.compile(r"^Điều\s+\d+\b.*", re.I)
CHAPTER_RE = re.compile(r"^Chương\s+[IVXLCDM0-9]+\b.*", re.I)
CLAUSE_RE = re.compile(r"^Khoản\s+\d+\b.*", re.I)


def clean(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_document(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    pages = []
    if suffix == ".pdf":
        import pymupdf
        with pymupdf.open(path) as pdf:
            for i, page in enumerate(pdf):
                pages.append({"page_number": i + 1, "text": clean(page.get_text("text"))})
    elif suffix == ".docx":
        from docx import Document
        doc = Document(path)
        # Preserve paragraph order; page numbers are unavailable from python-docx.
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        for table in doc.tables:
            text += "\n" + "\n".join(" | ".join(c.text.strip() for c in row.cells) for row in table.rows)
        pages.append({"page_number": None, "text": clean(text)})
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
    return pages


def split_sections(text: str) -> list[dict[str, Any]]:
    sections, current = [], {"chapter": None, "article": None, "clause": None, "lines": []}
    def flush():
        content = "\n".join(current["lines"]).strip()
        if content:
            sections.append({k: current[k] for k in ("chapter", "article", "clause")} | {"text": content})
        current["lines"] = []
    for line in text.splitlines():
        line = line.strip()
        if not line: continue
        if CHAPTER_RE.match(line): flush(); current.update(chapter=line, article=None, clause=None)
        elif ARTICLE_RE.match(line): flush(); current.update(article=line, clause=None)
        elif CLAUSE_RE.match(line): flush(); current.update(clause=line)
        current["lines"].append(line)
    flush()
    return sections


def chunk_section(section: dict[str, Any], doc_name: str, page_number: int | None,
                  max_tokens: int = 600, overlap: int = 80) -> list[dict[str, Any]]:
    words = TOKEN_RE.findall(section["text"])
    if not words: return []
    stride = max(1, max_tokens - overlap)
    out = []
    for start in range(0, len(words), stride):
        part = words[start:start + max_tokens]
        if not part: break
        text = " ".join(part)
        seed = f"{doc_name}|{page_number}|{section.get('chapter')}|{section.get('article')}|{section.get('clause')}|{start}|{text}"
        out.append({"chunk_id": hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16],
                    "doc_name": doc_name, "page_number": page_number,
                    "chapter": section.get("chapter"), "article": section.get("article"),
                    "clause": section.get("clause"), "text": text})
        if start + max_tokens >= len(words): break
    return out


def build_chunks(raw_dir: Path, output: Path, max_tokens=600, overlap=80) -> dict[str, Any]:
    files = sorted(p for p in raw_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".pdf", ".docx"})
    registry_path = raw_dir.parent / "document_registry.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {}
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Không thể đọc metadata tài liệu {registry_path}: {exc}") from exc
    if not isinstance(registry, dict):
        raise ValueError(f"Metadata tài liệu phải là JSON object: {registry_path}")
    superseded_chunk_ids = {
        str(chunk_id)
        for info in registry.values() if isinstance(info, dict)
        for chunk_id in info.get("superseded_chunk_ids", [])
    }
    chunks, page_count, errors, duplicates = [], 0, [], []
    superseded_skipped = 0
    seen_content: dict[str, str] = {}
    for path in files:
        try:
            pages = read_document(path); page_count += len(pages)
            normalized_text = re.sub(r"\s+", " ", " ".join(p["text"] for p in pages)).strip().casefold()
            content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
            if content_hash in seen_content:
                duplicates.append({"file": path.name, "duplicate_of": seen_content[content_hash], "content_sha256": content_hash})
                continue
            seen_content[content_hash] = path.name
            document_metadata = registry.get(path.name, {})
            if not isinstance(document_metadata, dict):
                document_metadata = {}
            context = {"chapter": None, "article": None, "clause": None}
            for page in pages:
                sections = split_sections(page["text"])
                if sections:
                    if sections[0].get("chapter") is None: sections[0]["chapter"] = context["chapter"]
                    if sections[0].get("article") is None: sections[0]["article"] = context["article"]
                    if sections[0].get("clause") is None: sections[0]["clause"] = context["clause"]
                    for section in sections:
                        for key in context:
                            if section.get(key) is not None: context[key] = section[key]
                if not sections and page["text"]:
                    sections = [{"chapter": None, "article": None, "clause": None, "text": page["text"]}]
                for section in sections:
                    rows = chunk_section(section, path.name, page["page_number"], max_tokens, overlap)
                    for row in rows:
                        if row["chunk_id"] in superseded_chunk_ids:
                            superseded_skipped += 1
                            continue
                        row.update({
                            key: document_metadata.get(key)
                            for key in ("category", "document_number", "published_at", "effective_from", "effective_until")
                        })
                    chunks.extend(rows)
        except Exception as exc:
            errors.append({"file": path.name, "error": str(exc)})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for row in chunks: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    missing = sum(any(row.get(k) is None for k in ("doc_name", "page_number", "chapter", "article", "clause")) for row in chunks)
    report = {"files_found": len(files), "files_read": len(files)-len(errors), "pages_or_documents": page_count,
              "chunks": len(chunks), "empty_chunks": sum(not x["text"].strip() for x in chunks),
              "chunks_with_optional_metadata_missing": missing, "duplicates_skipped": duplicates,
              "superseded_chunks_skipped": superseded_skipped,
              "errors": errors, "output": str(output)}
    return report
