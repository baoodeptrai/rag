"""Summarize citation-level manual review rows without calling a model."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


METRICS = {
    "document_correct_rate": "citation_document_correct",
    "page_correct_rate": "citation_page_correct",
    "evidence_support_rate": "citation_evidence_supports_answer",
}


def parsed_bool(value: str) -> bool | None:
    normalized = (value or "").strip().casefold()
    if normalized in {"true", "1", "yes"}: return True
    if normalized in {"false", "0", "no"}: return False
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path, help="Citation review CSV")
    parser.add_argument("--output", type=Path, help="Summary CSV path")
    args = parser.parse_args()
    source = args.input_csv if args.input_csv.is_absolute() else Path.cwd() / args.input_csv
    if not source.exists():
        print(f"Input CSV not found: {source}", file=sys.stderr)
        return 2
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        print("Citation review CSV is empty.", file=sys.stderr)
        return 2

    output_rows: list[dict] = []
    all_correct: list[bool] = []
    for metric, field in METRICS.items():
        values = [parsed_bool(row.get(field, "")) for row in rows]
        scored = [value for value in values if value is not None]
        output_rows.append({"metric": metric, "numerator": sum(scored), "denominator": len(scored),
                            "rate": sum(scored) / len(scored) if scored else ""})
    for row in rows:
        values = [parsed_bool(row.get(field, "")) for field in METRICS.values()]
        if all(value is not None for value in values):
            all_correct.append(all(values))
    output_rows.append({"metric": "all_three_correct_rate", "numerator": sum(all_correct),
                        "denominator": len(all_correct),
                        "rate": sum(all_correct) / len(all_correct) if all_correct else ""})

    output = args.output or source.with_name(source.stem + "_summary.csv")
    if not output.is_absolute(): output = Path.cwd() / output
    if output.exists():
        print(f"Refusing to overwrite existing summary: {output}", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["metric", "numerator", "denominator", "rate"])
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"Citation rows: {len(rows)}")
    print(f"Summary: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
