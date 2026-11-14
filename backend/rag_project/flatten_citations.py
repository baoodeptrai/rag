"""Create one review row per citation from an answer-quality response CSV."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path


FIELDS = [
    "question_id", "citation_index", "question", "expected_answer", "source_doc",
    "gold_evidence", "returned_doc", "returned_page", "returned_chapter",
    "returned_article", "returned_clause", "returned_chunk_id",
    "citation_document_correct", "citation_page_correct",
    "citation_evidence_supports_answer", "reviewer", "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path, help="Raw answer-quality run CSV")
    parser.add_argument("--output", type=Path, help="Citation-review CSV path")
    args = parser.parse_args()
    source = args.input_csv if args.input_csv.is_absolute() else Path.cwd() / args.input_csv
    if not source.exists():
        print(f"Input CSV not found: {source}", file=sys.stderr)
        return 2

    output = args.output or source.with_name(source.stem + "_citation_review.csv")
    if not output.is_absolute(): output = Path.cwd() / output
    if output.exists():
        print(f"Refusing to overwrite existing review file: {output}", file=sys.stderr)
        return 2

    review_rows: list[dict] = []
    malformed = 0
    with source.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            raw_citations = row.get("citations_returned", "") or "[]"
            try:
                citations = json.loads(raw_citations)
                if not isinstance(citations, list): raise ValueError("citations must be a list")
            except (json.JSONDecodeError, ValueError):
                malformed += 1
                continue
            for index, citation in enumerate(citations, 1):
                if not isinstance(citation, dict):
                    malformed += 1
                    continue
                review_rows.append({
                    "question_id": row.get("question_id", ""),
                    "citation_index": index,
                    "question": row.get("question", ""),
                    "expected_answer": row.get("expected_answer", ""),
                    "source_doc": row.get("source_doc", ""),
                    "gold_evidence": row.get("gold_evidence", ""),
                    "returned_doc": citation.get("doc_name", ""),
                    "returned_page": citation.get("page_number", ""),
                    "returned_chapter": citation.get("chapter", ""),
                    "returned_article": citation.get("article", ""),
                    "returned_clause": citation.get("clause", ""),
                    "returned_chunk_id": citation.get("chunk_id", ""),
                    "citation_document_correct": "",
                    "citation_page_correct": "",
                    "citation_evidence_supports_answer": "",
                    "reviewer": "",
                    "notes": "",
                })

    if not review_rows:
        print("No valid citations found to review.", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(review_rows)
    print(f"Citation rows: {len(review_rows)}; malformed responses: {malformed}")
    print(f"Review file: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
