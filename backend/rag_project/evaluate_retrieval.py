"""Offline retrieval benchmark for the reviewed Golden Dataset.

Run from the repository root:
    python backend/rag_project/evaluate_retrieval.py

This does not call the configured LLM. Gold labels are provisional until human
cross-review is complete; generated files are evidence for retrieval only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pickle
import re
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

# The retrieval benchmark must use the already-cached local embedding model.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
DATASET = ROOT / "docs" / "evaluation" / "golden_dataset_v2_draft.csv"
CHUNKS_PATH = BACKEND / "data" / "processed" / "chunks.jsonl"
BM25_PATH = BACKEND / "data" / "processed" / "bm25.pkl"
QDRANT_PATH = BACKEND / "data" / "qdrant"
OUT_DIR = ROOT / "docs" / "evaluation" / "results"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TOP_K = 5
RRF_K = 60


def tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), re.UNICODE)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def metrics(ranked_ids: list[str], gold_ids: set[str]) -> tuple[float, float, float]:
    if not gold_ids:
        return (float("nan"),) * 3
    found = [rank for rank, chunk_id in enumerate(ranked_ids[:TOP_K], 1) if chunk_id in gold_ids]
    recall = len(found) / len(gold_ids)
    hit = 1.0 if found else 0.0
    reciprocal_rank = 1.0 / found[0] if found else 0.0
    return recall, hit, reciprocal_rank


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", help="Output folder name; defaults to a timestamp")
    parser.add_argument("--repeats", type=int, default=3, help="Measured retrieval runs per question")
    parser.add_argument("--warmup-repeats", type=int, default=1, help="Warm-up runs excluded from latency")
    args = parser.parse_args()
    if args.repeats < 1 or args.warmup_repeats < 0:
        parser.error("--repeats must be >= 1 and --warmup-repeats must be >= 0")
    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        parser.error("--run-id may contain only letters, numbers, underscores and hyphens")
    run_dir = OUT_DIR / "runs" / run_id
    if run_dir.exists():
        print(f"Run folder already exists; choose another --run-id: {run_dir}", file=sys.stderr)
        return 2

    if not DATASET.exists() or not BM25_PATH.exists() or not QDRANT_PATH.exists():
        print("Missing dataset or existing index. Build the index first.", file=sys.stderr)
        return 2
    if not CHUNKS_PATH.exists():
        print("Active chunks file is missing.", file=sys.stderr)
        return 2
    with DATASET.open(encoding="utf-8-sig", newline="") as stream:
        questions = list(csv.DictReader(stream))
    questions = [row for row in questions if row.get("answerable", "").lower() == "true"]
    if not questions:
        print("No answerable questions in the dataset.", file=sys.stderr)
        return 2
    if any(not row.get("gold_chunk_ids", "").strip() for row in questions):
        print("An answerable question is missing gold_chunk_ids. Verify the labels first.", file=sys.stderr)
        return 2

    with BM25_PATH.open("rb") as stream:
        chunks, bm25 = pickle.load(stream)
    chunk_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    expected_ids = {chunk_id for row in questions for chunk_id in row["gold_chunk_ids"].split(";") if chunk_id}
    unknown = expected_ids - set(chunk_by_id)
    if unknown:
        print(f"Gold chunk IDs absent from BM25 index: {sorted(unknown)}", file=sys.stderr)
        return 2

    print(f"Preparing benchmark for {len(questions)} answerable questions; importing retrieval libraries...", flush=True)
    try:
        from sentence_transformers import SentenceTransformer
        from qdrant_client import QdrantClient
    except ImportError as exc:
        print(f"Missing retrieval dependency: {exc}", file=sys.stderr)
        return 2

    print(f"Loading embedding model {MODEL_NAME} and local Qdrant index...")
    model = SentenceTransformer(MODEL_NAME)
    client = QdrantClient(path=str(QDRANT_PATH))
    if not client.collection_exists("rag_chunks"):
        client.close()
        print("Qdrant collection rag_chunks not found.", file=sys.stderr)
        return 2
    # Warm up embedding and Qdrant query paths outside measured latencies.
    warmup_query = "khởi tạo đo retrieval"
    try:
        warmup_vector = model.encode(warmup_query, normalize_embeddings=True, show_progress_bar=False).tolist()
        for _ in range(args.warmup_repeats):
            bm25.get_scores(tokens(warmup_query))
            client.query_points(collection_name="rag_chunks", query=warmup_vector, limit=max(TOP_K * 4, 20))
    except Exception:
        client.close()
        raise

    detail_rows: list[dict] = []
    scores: dict[str, dict[str, list[tuple[float, str]]]] = {name: {} for name in ("BM25", "Dense", "Hybrid_RRF")}
    try:
        for row in questions:
            query = row["question"]
            gold_ids = {item.strip() for item in row["gold_chunk_ids"].split(";") if item.strip()}
            bm_latencies, dense_latencies = [], []
            bm_ranked, dense_ranked = [], []
            for _ in range(args.repeats):
                start = time.perf_counter()
                bm_scores = bm25.get_scores(tokens(query))
                bm_order = sorted(range(len(chunks)), key=lambda i: float(bm_scores[i]), reverse=True)
                bm_ranked = [(float(bm_scores[i]), chunks[i]["chunk_id"]) for i in bm_order[:max(TOP_K * 4, 20)]]
                bm_latencies.append((time.perf_counter() - start) * 1000)

                start = time.perf_counter()
                vector = model.encode(query, normalize_embeddings=True, show_progress_bar=False).tolist()
                dense_hits = client.query_points(collection_name="rag_chunks", query=vector, limit=max(TOP_K * 4, 20)).points
                dense_ranked = [(float(hit.score), str(hit.payload["chunk_id"])) for hit in dense_hits]
                dense_latencies.append((time.perf_counter() - start) * 1000)
            bm_latency = statistics.median(bm_latencies)
            dense_latency = statistics.median(dense_latencies)
            hybrid_latency = statistics.median(a + b for a, b in zip(bm_latencies, dense_latencies))

            bm_ranks = {chunk_id: rank for rank, (_, chunk_id) in enumerate(bm_ranked, 1)}
            dense_ranks = {chunk_id: rank for rank, (_, chunk_id) in enumerate(dense_ranked, 1)}
            candidates = set(bm_ranks) | set(dense_ranks)
            fused = sorted(
                ((1 / (RRF_K + bm_ranks[cid]) if cid in bm_ranks else 0.0)
                 + (1 / (RRF_K + dense_ranks[cid]) if cid in dense_ranks else 0.0), cid)
                for cid in candidates
            )
            fused.reverse()
            hybrid_ranked = fused[:TOP_K * 4]

            methods = {
                "BM25": (bm_ranked, bm_latency),
                "Dense": (dense_ranked, dense_latency),
                "Hybrid_RRF": (hybrid_ranked, hybrid_latency),
            }
            for method, (ranked, latency) in methods.items():
                top = ranked[:TOP_K]
                ids = [cid for _, cid in top]
                recall, hit, mrr = metrics(ids, gold_ids)
                scores[method][row["question_id"]] = [recall, hit, mrr]
                details = [{
                    "rank": rank,
                    "chunk_id": cid,
                    "score": round(float(score), 6),
                    "page": chunk_by_id.get(cid, {}).get("page_number"),
                    "article_metadata": chunk_by_id.get(cid, {}).get("article"),
                    "is_gold": cid in gold_ids,
                } for rank, (score, cid) in enumerate(top, 1)]
                detail_rows.append({
                    "question_id": row["question_id"], "question": query, "method": method,
                    "gold_chunk_ids": ";".join(sorted(gold_ids)), "recall_at_5": recall,
                    "hit_rate_at_5": hit, "mrr_at_5": mrr, "retrieval_latency_ms": round(latency, 3),
                    "repeats": args.repeats,
                    "top_5": json.dumps(details, ensure_ascii=False),
                })
    finally:
        client.close()

    run_dir.mkdir(parents=True, exist_ok=False)
    dataset_hash = sha256_file(DATASET)
    corpus_hash = sha256_file(CHUNKS_PATH)
    detail_path = run_dir / "retrieval_per_question.csv"
    with detail_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=detail_rows[0].keys())
        writer.writeheader()
        writer.writerows(detail_rows)

    summary_rows = []
    for method in scores:
        vals = list(scores[method].values())
        summary_rows.append({
            "run_id": run_id, "method": method, "n_answerable": len(vals), "k": TOP_K,
            "mean_recall_at_5": statistics.mean(v[0] for v in vals),
            "hit_rate_at_5": statistics.mean(v[1] for v in vals),
            "mrr_at_5": statistics.mean(v[2] for v in vals),
            "median_latency_ms": statistics.median(
                float(r["retrieval_latency_ms"]) for r in detail_rows if r["method"] == method
            ),
            "repeats": args.repeats, "warmup_repeats": args.warmup_repeats,
            "embedding_model": MODEL_NAME, "dataset_sha256": dataset_hash,
            "corpus_sha256": corpus_hash,
        })
    summary_path = run_dir / "retrieval_summary.csv"
    with summary_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=summary_rows[0].keys())
        writer.writeheader()
        writer.writerows(summary_rows)

    metadata = {
        "run_id": run_id, "created_at": datetime.now().astimezone().isoformat(),
        "dataset": str(DATASET.relative_to(ROOT)), "dataset_sha256": dataset_hash,
        "corpus": str(CHUNKS_PATH.relative_to(ROOT)), "corpus_sha256": corpus_hash,
        "embedding_model": MODEL_NAME, "n_answerable": len(questions), "k": TOP_K,
        "rrf_k": RRF_K, "repeats": args.repeats, "warmup_repeats": args.warmup_repeats,
        "hardware_note": "Fill in CPU/GPU/RAM details before reporting latency.",
    }
    (run_dir / "run_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Dataset: {len(questions)} answerable questions (labels are provisional; human cross-review pending)")
    print(f"Run folder: {run_dir}")
    print(f"Summary: {summary_path}")
    print(f"Per-question top-5: {detail_path}")
    for row in summary_rows:
        print("{method}: Recall@5={mean_recall_at_5:.3f}, HitRate@5={hit_rate_at_5:.3f}, MRR@5={mrr_at_5:.3f}, median latency={median_latency_ms:.1f} ms".format(**row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
