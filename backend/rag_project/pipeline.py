from pathlib import Path
import os
import shutil
from .ingest import build_chunks
from .indexing import build_indexes


def _replace_active_index(staged: list[tuple[Path, Path]], backup_dir: Path) -> None:
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
    processed = base / "data" / "processed"
    staging = processed / ".staging"
    if staging.exists(): shutil.rmtree(staging)
    staging.mkdir(parents=True)
    candidate_chunks = staging / "chunks.jsonl"
    report = build_chunks(base/"data/raw", candidate_chunks)
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
        built = build_indexes(candidate_chunks, candidate_bm25, candidate_qdrant, "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        active_qdrant = base / "data" / "qdrant"
        active_chunks = processed / "chunks.jsonl"
        active_bm25 = processed / "bm25.pkl"
        _replace_active_index(
            [(candidate_chunks, active_chunks), (candidate_bm25, active_bm25), (candidate_qdrant, active_qdrant)],
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
