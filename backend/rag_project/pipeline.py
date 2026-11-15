from pathlib import Path
import json
import os
import shutil
from dotenv import load_dotenv
from .ingest import build_chunks
from .indexing_lock import INDEX_LOCK
from .indexing import build_indexes


def _replace_active_index(staged: list[tuple[Path, Path]], backup_dir: Path) -> None:
    with INDEX_LOCK:
        _replace_active_index_unlocked(staged, backup_dir)


def _replace_active_index_unlocked(staged: list[tuple[Path, Path]], backup_dir: Path) -> None:
    """Promote a complete staged corpus and restore the previous one on failure."""
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True)
    moved_old: list[tuple[Path, Path]] = []
    moved_new: list[Path] = []
    try:
        for _, active in staged:
            if active.exists():
                backup = backup_dir / active.name
                os.replace(active, backup)
                moved_old.append((active, backup))
        for candidate, active in staged:
            active.parent.mkdir(parents=True, exist_ok=True)
            os.replace(candidate, active)
            moved_new.append(active)
    except Exception:
        for active in reversed(moved_new):
            if active.is_dir(): shutil.rmtree(active)
            elif active.exists(): active.unlink()
        for active, backup in reversed(moved_old):
            if backup.exists(): os.replace(backup, active)
        raise


def main():
    base = Path(__file__).resolve().parents[1]
    load_dotenv(base / ".env", override=False)
    processed = base / "data" / "processed"
    raw_dir = Path(os.getenv("RAG_RAW_DIR", str(base / "data" / "raw")))
    staging = processed / ".staging"
    if staging.exists(): shutil.rmtree(staging)
    staging.mkdir(parents=True)
    candidate_chunks = staging / "chunks.jsonl"
    try:
        report = build_chunks(raw_dir, candidate_chunks)
    except Exception:
        if staging.exists(): shutil.rmtree(staging)
        raise
    print("Ingestion:", report)
    if report["errors"]:
        shutil.rmtree(staging)
        print("Có tài liệu lỗi khi đọc; giữ nguyên chỉ mục đang chạy để tránh thay bằng dữ liệu thiếu.")
        return 1
    # Build all candidate artifacts away from the active index. This also
    # supports an empty corpus, which deliberately clears the old index.
    candidate_bm25 = staging / "bm25.pkl"
    candidate_qdrant = staging / "qdrant"
    try:
        embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        built = build_indexes(candidate_chunks, candidate_bm25, candidate_qdrant, embedding_model)
        candidate_metadata = staging / "index_metadata.json"
        candidate_metadata.write_text(json.dumps({
            "schema_version": 1,
            "embedding_model": embedding_model,
            "chunks_indexed": built["chunks_indexed"],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        active_qdrant = base / "data" / "qdrant"
        active_chunks = processed / "chunks.jsonl"
        active_bm25 = processed / "bm25.pkl"
        active_metadata = processed / "index_metadata.json"
        _replace_active_index(
            [(candidate_chunks, active_chunks), (candidate_bm25, active_bm25),
             (candidate_qdrant, active_qdrant), (candidate_metadata, active_metadata)],
            processed / ".last-good-index",
        )
    except Exception:
        if staging.exists(): shutil.rmtree(staging)
        raise
    if staging.exists(): shutil.rmtree(staging)
    print("Indexes:", built)
    print(f"Index đã cập nhật: {report['chunks']} chunks; bỏ qua {len(report['duplicates_skipped'])} file trùng nội dung.")
    return 0

if __name__ == "__main__": raise SystemExit(main())
