"""Compare structure-aware and fixed-size chunks with the same BM25 retriever.

Run from the repository root:
    python backend/rag_project/compare_chunking.py

The script uses source evidence text, not structure-aware chunk IDs, to derive
relevant chunks separately for each chunking strategy. It does not call an LLM
or overwrite the chatbot's indexes.
"""
from __future__ import annotations

import csv
import argparse
import hashlib
import json
import re
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from rag_project.ingest import TOKEN_RE, read_document  # noqa: E402

DATASET = ROOT / "docs" / "evaluation" / "golden_dataset_v2_draft.csv"
CHUNKS_PATH = BACKEND / "data" / "processed" / "chunks.jsonl"
RAW_DIR = BACKEND / "data" / "raw"
OUT_DIR = ROOT / "docs" / "evaluation" / "results"
MAX_TOKENS = 600
OVERLAP = 80
TOP_K = 5


def normalize(text: str) -> str:
    return "".join(char.casefold() for char in text if char.isalnum())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), re.UNICODE)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_fixed_chunks(source_path: Path) -> tuple[list[dict], dict[int, str]]:
    chunks: list[dict] = []
    source_pages: dict[int, str] = {}
    stride = MAX_TOKENS - OVERLAP
    for page in read_document(source_path):
        page_number = page["page_number"]
        text = page["text"]
        source_pages[page_number] = text
        words = TOKEN_RE.findall(text)
        for start in range(0, len(words), stride):
            part = words[start:start + MAX_TOKENS]
            if not part:
                break
            chunk_text = " ".join(part)
            seed = f"{source_path.name}|fixed|{page_number}|{start}|{chunk_text}"
            chunks.append({
                "chunk_id": hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16],
                "doc_name": source_path.name,
                "page_number": page_number,
                "chapter": None,
                "article": None,
                "clause": None,
                "text": chunk_text,
            })
            if start + MAX_TOKENS >= len(words):
                break
    return chunks, source_pages


def evidence_units(value: str) -> list[str]:
    return [unit.strip() for unit in value.split(" | ") if unit.strip()]


def gold_for_variant(row: dict, chunks: list[dict], source_pages: dict[int, str]) -> tuple[set[str], list[str]]:
    primary_page = int(row["pipeline_page"])
    gold_ids: set[str] = set()
    issues: list[str] = []
    for unit in evidence_units(row.get("gold_evidence", "")):
        needle = normalize(unit)
        if not needle:
            continue
        matching_pages = [
            page for page, source_text in source_pages.items()
            if needle in normalize(source_text)
        ]
        if primary_page in matching_pages:
            matching_pages = [primary_page]
        if not matching_pages:
            issues.append(f"evidence does not match source PDF: {unit[:60]}")
            continue
        for page in matching_pages:
            page_chunks = [chunk for chunk in chunks if chunk.get("page_number") == page]
            exact = [chunk for chunk in page_chunks if needle in normalize(chunk["text"])]
            if exact:
                gold_ids.update(chunk["chunk_id"] for chunk in exact)
                continue
            # A source phrase can cross a chunk boundary. Assign the overlapping
            # page chunks only if together they preserve the full evidence phrase.
            normalized_chunks = [(chunk, normalize(chunk["text"])) for chunk in page_chunks]
            joined = "".join(text for _, text in normalized_chunks)
            if needle in joined:
                cursor = joined.find(needle)
                end = cursor + len(needle)
                offset = 0
                for chunk, text in normalized_chunks:
                    chunk_start, chunk_end = offset, offset + len(text)
                    if max(cursor, chunk_start) < min(end, chunk_end):
                        gold_ids.add(chunk["chunk_id"])
                    offset = chunk_end
            else:
                issues.append(f"evidence split/normalization issue on PDF page {page}: {unit[:60]}")
    return gold_ids, issues


def retrieval_metrics(ranked_ids: list[str], gold_ids: set[str]) -> tuple[float, float, float]:
    if not gold_ids:
        return 0.0, 0.0, 0.0
    hits = [rank for rank, chunk_id in enumerate(ranked_ids[:TOP_K], 1) if chunk_id in gold_ids]
    return len(hits) / len(gold_ids), float(bool(hits)), 1 / hits[0] if hits else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
                        help="Output folder name; defaults to a timestamp")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id):
        parser.error("--run-id may contain only letters, numbers, underscores and hyphens")
    if not DATASET.exists() or not CHUNKS_PATH.exists():
        print("Missing submission dataset or existing structure-aware chunks.", file=sys.stderr)
        return 2
    with DATASET.open(encoding="utf-8-sig", newline="") as stream:
        questions = [row for row in csv.DictReader(stream) if row["answerable"].lower() == "true"]
    if not questions:
        print("No answerable questions found.", file=sys.stderr)
        return 2
    structure_chunks = load_jsonl(CHUNKS_PATH)
    pdf_files = {path.name: path for path in RAW_DIR.rglob("*.pdf")}
    source_name = questions[0]["source_doc"]
    source_path = pdf_files.get(source_name)
    if source_path is None or any(row["source_doc"] != source_name for row in questions):
        print("This comparison expects all answerable questions to use one PDF source.", file=sys.stderr)
        return 2
    fixed_chunks, source_pages = build_fixed_chunks(source_path)
    for page in {int(row["pipeline_page"]) for row in questions}:
        source_pages.setdefault(page, "")

    try:
        from rank_bm25 import BM25Okapi
    except ImportError as exc:
        print(f"Missing dependency rank-bm25: {exc}", file=sys.stderr)
        return 2

    variants = {"Structure-aware": structure_chunks, "Fixed-size": fixed_chunks}
    indexes = {
        name: BM25Okapi([tokens(chunk["text"]) for chunk in chunks])
        for name, chunks in variants.items()
    }
    rows_out: list[dict] = []
    summary: list[dict] = []
    issues_all: list[str] = []
    print(f"Comparing {len(questions)} answerable questions with BM25, top-k={TOP_K}...")
    for name, chunks in variants.items():
        bm25 = indexes[name]
        query_scores: list[tuple[float, float, float]] = []
        latencies: list[float] = []
        for row in questions:
            gold_ids, issues = gold_for_variant(row, chunks, source_pages)
            if issues:
                issues_all.extend(f"{name} {row['question_id']}: {issue}" for issue in issues)
            if not gold_ids:
                print(f"No gold evidence chunks mapped for {name} {row['question_id']}; aborting.", file=sys.stderr)
                return 2
            start = time.perf_counter()
            scores = bm25.get_scores(tokens(row["question"]))
            order = sorted(range(len(chunks)), key=lambda idx: float(scores[idx]), reverse=True)
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            top = order[:TOP_K]
            top_chunks = [{
                "rank": rank,
                "chunk_id": chunks[idx]["chunk_id"],
                "page": chunks[idx].get("page_number"),
                "score": round(float(scores[idx]), 6),
                "is_gold": chunks[idx]["chunk_id"] in gold_ids,
                "text_preview": chunks[idx]["text"][:220],
            } for rank, idx in enumerate(top, 1)]
            recall, hit, mrr = retrieval_metrics([chunks[idx]["chunk_id"] for idx in top], gold_ids)
            query_scores.append((recall, hit, mrr))
            rows_out.append({
                "question_id": row["question_id"],
                "question": row["question"],
                "variant": name,
                "gold_evidence_chunks": len(gold_ids),
                "recall_at_5": recall,
                "hit_rate_at_5": hit,
                "mrr_at_5": mrr,
                "latency_ms": round(latency, 3),
                "top_5": json.dumps(top_chunks, ensure_ascii=False),
            })
        summary.append({
            "variant": name,
            "retriever": "BM25-only",
            "n_answerable": len(questions),
            "chunk_count": len(chunks),
            "max_tokens": MAX_TOKENS,
            "overlap_tokens": OVERLAP,
            "k": TOP_K,
            "mean_recall_at_5": statistics.mean(s[0] for s in query_scores),
            "hit_rate_at_5": statistics.mean(s[1] for s in query_scores),
            "mrr_at_5": statistics.mean(s[2] for s in query_scores),
            "median_latency_ms": statistics.median(latencies),
        })

    run_dir = OUT_DIR / "runs" / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    detail_path = run_dir / "chunking_per_question.csv"
    summary_path = run_dir / "chunking_summary.csv"
    if detail_path.exists() or summary_path.exists():
        print(f"Chunking output already exists; choose another --run-id: {run_dir}", file=sys.stderr)
        return 2
    with detail_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows_out[0].keys())
        writer.writeheader()
        writer.writerows(rows_out)
    with summary_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=summary[0].keys())
        writer.writeheader()
        writer.writerows(summary)

    metadata = {
        "run_id": args.run_id,
        "created_at": datetime.now().astimezone().isoformat(),
        "dataset": str(DATASET.relative_to(ROOT)),
        "dataset_sha256": sha256_file(DATASET),
        "corpus": str(CHUNKS_PATH.relative_to(ROOT)),
        "corpus_sha256": sha256_file(CHUNKS_PATH),
        "source_pdf": str(source_path.relative_to(ROOT)),
        "source_pdf_sha256": sha256_file(source_path),
        "n_answerable": len(questions),
        "retriever": "BM25-only",
        "top_k": TOP_K,
        "chunk_variants": {
            "structure_aware": {"chunk_count": len(structure_chunks)},
            "fixed_size": {"chunk_count": len(fixed_chunks), "max_tokens": MAX_TOKENS, "overlap_tokens": OVERLAP},
        },
        "labels_status": "provisional; independent cross-review pending",
    }
    metadata_path = run_dir / "chunking_run_metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Structure-aware chunks: {len(structure_chunks)}; fixed-size chunks: {len(fixed_chunks)}")
    for result in summary:
        print("{variant}: Recall@5={mean_recall_at_5:.3f}, HitRate@5={hit_rate_at_5:.3f}, MRR@5={mrr_at_5:.3f}, median latency={median_latency_ms:.3f} ms".format(**result))
    print(f"Summary: {summary_path}")
    print(f"Per-question top-5: {detail_path}")
    print(f"Run metadata: {metadata_path}")
    if issues_all:
        issue_path = run_dir / "chunking_label_warnings.txt"
        issue_path.write_text("\n".join(issues_all) + "\n", encoding="utf-8")
        print(f"Evidence mapping warnings: {len(issues_all)}; see {issue_path}")
        return 1
    print("Evidence snippets mapped to source pages and chunks for both variants.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
