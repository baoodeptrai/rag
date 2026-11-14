"""Collect real chatbot answers/citations for manual citation/refusal review.

Run with the local backend already started. This sends one chat request per
selected dataset question and refuses non-loopback API hosts. It never reads or
prints API keys.
"""
from __future__ import annotations

import argparse
import csv
import json
import hashlib
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "docs" / "evaluation" / "golden_dataset_v2_draft.csv"
OUT_DIR = ROOT / "docs" / "evaluation" / "results"

FIELDS = [
    "question_id", "category", "question", "expected_answer", "expected_refusal", "expected_refusal_reason",
    "source_doc", "pipeline_page", "gold_evidence", "gold_chunk_ids",
    "system_answer", "citations_returned", "system_confidence_score",
    "latency_ms", "answer_correct", "answer_complete",
    "citation_document_correct", "citation_page_correct",
    "citation_evidence_supports_answer", "answer_grounded", "system_refused",
    "reviewer", "notes", "request_error",
]


def call_chat(base_url: str, question: str, session_id: str, timeout: float) -> dict:
    body = json.dumps({"message": question, "session_id": session_id}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def configured_model() -> str | None:
    env_file = ROOT / "backend" / ".env"
    if not env_file.exists():
        return os.getenv("LLM_MODEL")
    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"^\s*LLM_MODEL\s*=\s*[\"']?([^\"'#\s]+)", line)
        if match:
            return match.group(1)
    return os.getenv("LLM_MODEL")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Local backend URL")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--limit", type=int, default=0, help="Optional first N rows; prefer --question-ids for stratified smoke tests")
    selection.add_argument("--question-ids", help="Comma-separated IDs, e.g. G001,G010,G059")
    parser.add_argument("--timeout", type=float, default=90.0, help="Timeout per chat request in seconds")
    parser.add_argument("--delay", type=float, default=0.3, help="Pause between requests in seconds")
    parser.add_argument("--output", type=Path, help="Optional output CSV path")
    args = parser.parse_args()

    parsed_base = urlparse(args.base_url)
    if parsed_base.scheme != "http" or parsed_base.hostname not in {"localhost", "127.0.0.1", "::1"}:
        print("Offline evaluation only allows a local backend URL (localhost).", file=sys.stderr)
        return 2

    if not DATASET.exists():
        print(f"Dataset not found: {DATASET}", file=sys.stderr)
        return 2
    with DATASET.open(encoding="utf-8-sig", newline="") as stream:
        dataset = list(csv.DictReader(stream))
    if args.question_ids:
        requested_ids = [item.strip() for item in args.question_ids.split(",") if item.strip()]
        if len(set(requested_ids)) != len(requested_ids):
            print("Question IDs must not be repeated.", file=sys.stderr)
            return 2
        by_id = {row["question_id"]: row for row in dataset}
        missing_ids = [item for item in requested_ids if item not in by_id]
        if missing_ids:
            print(f"Unknown question IDs: {', '.join(missing_ids)}", file=sys.stderr)
            return 2
        dataset = [by_id[item] for item in requested_ids]
    elif args.limit > 0:
        dataset = dataset[:args.limit]
    if not dataset:
        print("No questions selected.", file=sys.stderr)
        return 2

    output = args.output or OUT_DIR / f"answer_quality_run_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.csv"
    if not output.is_absolute():
        output = ROOT / output
    metadata_path = output.with_suffix(output.suffix + ".metadata.json")
    if output.exists() or metadata_path.exists():
        print(f"Refusing to overwrite an existing run artifact: {output}", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    chunks_path = ROOT / "backend" / "data" / "processed" / "chunks.jsonl"
    dataset_hash = sha256_file(DATASET)
    corpus_hash = sha256_file(chunks_path)
    model_tag = configured_model()
    print(f"This will send {len(dataset)} chat requests to local backend {args.base_url}.")
    print(f"Configured model: {model_tag or 'unknown'}; corpus hash: {corpus_hash or 'missing'}.")
    confirmation = os.getenv("RAG_EVAL_CONFIRM") or input("Type RUN to continue: ")
    if confirmation.strip() != "RUN":
        print("Cancelled; no requests were sent.")
        return 0

    with output.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        stream.flush()
        for index, row in enumerate(dataset, 1):
            print(f"[{index}/{len(dataset)}] {row['question_id']}: {row['question']}", flush=True)
            result = {field: "" for field in FIELDS}
            result.update({
                "question_id": row["question_id"],
                "category": row["category"],
                "question": row["question"],
                "expected_answer": row["expected_answer"],
                "expected_refusal": "true" if row["answerable"].lower() == "false" else "false",
                "expected_refusal_reason": row.get("expected_refusal_reason", ""),
                "source_doc": row.get("source_doc", ""),
                "pipeline_page": row.get("pipeline_page", ""),
                "gold_evidence": row.get("gold_evidence", ""),
                "gold_chunk_ids": row.get("gold_chunk_ids", ""),
            })
            request_start = time.perf_counter()
            try:
                response = call_chat(args.base_url, row["question"], f"eval-{row['question_id']}", args.timeout)
                result["latency_ms"] = round((time.perf_counter() - request_start) * 1000, 3)
                result["system_answer"] = response.get("answer", "")
                result["citations_returned"] = json.dumps(response.get("citations", []), ensure_ascii=False)
                result["system_confidence_score"] = response.get("confidence_score", "")
                if any(marker in result["system_answer"].casefold() for marker in (
                    "không thể tạo câu trả lời bằng mô hình", "chưa cấu hình llm_base_url",
                )):
                    result["request_error"] = "Backend returned a model configuration/generation error with HTTP success."
            except urllib.error.HTTPError as exc:
                result["latency_ms"] = round((time.perf_counter() - request_start) * 1000, 3)
                try:
                    body = exc.read().decode("utf-8", errors="replace")[:1000]
                except Exception:
                    body = ""
                result["request_error"] = f"HTTP {exc.code}: {body}"
            except Exception as exc:
                result["latency_ms"] = round((time.perf_counter() - request_start) * 1000, 3)
                result["request_error"] = f"{type(exc).__name__}: {exc}"
            writer.writerow(result)
            stream.flush()  # Preserve completed requests if a later one fails.
            if index < len(dataset) and args.delay > 0:
                time.sleep(args.delay)

    print(f"Saved answers and citations to: {output}")
    metadata = {
        "run_file": output.name,
        "base_url": args.base_url,
        "model_tag_from_backend_env": model_tag,
        "dataset_path": str(DATASET.relative_to(ROOT)),
        "dataset_sha256": dataset_hash,
        "corpus_path": str(chunks_path.relative_to(ROOT)),
        "corpus_sha256": corpus_hash,
        "question_ids": [row["question_id"] for row in dataset],
        "request_count": len(dataset),
        "created_at": datetime.now().astimezone().isoformat(),
    }
    with metadata_path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(f"Run metadata: {metadata_path}")
    print("Manual scoring columns are blank intentionally; compare each row with the source document before scoring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
