"""Summarize the manually scored CSV produced by run_answer_quality_eval.py.

This script does not call a model. It reports question-level review rates,
keeps numerator/denominator visible, and excludes request failures from quality
denominators while counting them separately.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path


BOOLEAN_METRICS = {
    "answer_correct_rate": "answer_correct",
    "answer_complete_rate": "answer_complete",
    "answer_grounded_rate": "answer_grounded",
    "response_all_citations_document_correct_rate": "citation_document_correct",
    "response_all_citations_page_correct_rate": "citation_page_correct",
    "response_all_citations_evidence_supported_rate": "citation_evidence_supports_answer",
}


def boolean(value: str) -> bool | None:
    normalized = (value or "").strip().casefold()
    if normalized in {"true", "1", "yes"}: return True
    if normalized in {"false", "0", "no"}: return False
    return None


def add_rate(output: list[dict], metric: str, group: str, rows: list[dict], field: str,
             predicate=lambda row: True) -> None:
    values = [boolean(row.get(field, "")) for row in rows if predicate(row)]
    scored = [value for value in values if value is not None]
    output.append({"metric": metric, "group": group, "numerator": sum(scored),
                   "denominator": len(scored), "rate": sum(scored) / len(scored) if scored else ""})


def citation_count(row: dict) -> int | None:
    try:
        citations = json.loads(row.get("citations_returned", "") or "[]")
        return len(citations) if isinstance(citations, list) else None
    except (json.JSONDecodeError, TypeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path, help="Manually scored answer-quality CSV")
    parser.add_argument("--output", type=Path, help="Summary CSV path; defaults to <input>_summary.csv")
    args = parser.parse_args()
    source = args.input_csv if args.input_csv.is_absolute() else Path.cwd() / args.input_csv
    if not source.exists():
        print(f"Input CSV not found: {source}", file=sys.stderr)
        return 2

    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        print("Input CSV has no scored rows.", file=sys.stderr)
        return 2

    answerable = [row for row in rows if boolean(row.get("expected_refusal", "")) is False]
    expected_refusal = [row for row in rows if boolean(row.get("expected_refusal", "")) is True]
    errors = [row for row in rows if (row.get("request_error") or "").strip()]
    valid_responses = [row for row in rows if not (row.get("request_error") or "").strip()]
    summary: list[dict] = []
    summary.append({"metric": "request_error_rate", "group": "all", "numerator": len(errors),
                    "denominator": len(rows), "rate": len(errors) / len(rows)})
    summary.append({"metric": "request_error_count", "group": "all", "numerator": len(errors),
                    "denominator": len(rows), "rate": ""})

    for metric, field in BOOLEAN_METRICS.items():
        successful = lambda row: not (row.get("request_error") or "").strip()
        add_rate(summary, metric, "answerable", answerable, field, successful)
        add_rate(summary, metric, "expected_refusal", expected_refusal, field, successful)

    successful = lambda row: not (row.get("request_error") or "").strip()
    add_rate(summary, "false_refusal_rate", "answerable", answerable, "system_refused", successful)
    add_rate(summary, "correct_refusal_rate", "expected_refusal", expected_refusal, "system_refused", successful)
    answerable_success = [row for row in answerable if successful(row)]
    citation_counts = [citation_count(row) for row in answerable_success]
    scored_citation_counts = [count for count in citation_counts if count is not None]
    summary.append({"metric": "answerable_responses_with_at_least_one_citation_rate", "group": "answerable",
                    "numerator": sum(count > 0 for count in scored_citation_counts),
                    "denominator": len(scored_citation_counts),
                    "rate": sum(count > 0 for count in scored_citation_counts) / len(scored_citation_counts)
                    if scored_citation_counts else ""})
    # Separate refusal causes when the v2 dataset provides the reviewed field.
    refusal_reasons = sorted({(row.get("expected_refusal_reason") or "").strip() for row in expected_refusal} - {""})
    for reason in refusal_reasons:
        group_rows = [row for row in expected_refusal if (row.get("expected_refusal_reason") or "").strip() == reason]
        add_rate(summary, "correct_refusal_rate", f"expected_refusal:{reason}", group_rows,
                 "system_refused", successful)
    if expected_refusal and not refusal_reasons:
        add_rate(summary, "correct_refusal_rate", "expected_refusal:unclassified", expected_refusal,
                 "system_refused", successful)

    latencies = []
    for row in valid_responses:
        try: latencies.append(float(row["latency_ms"]))
        except (KeyError, TypeError, ValueError): pass
    summary.append({"metric": "end_to_end_latency_ms_median", "group": "successful_requests",
                    "numerator": "", "denominator": len(latencies),
                    "rate": statistics.median(latencies) if latencies else ""})

    output = args.output or source.with_name(source.stem + "_summary.csv")
    if not output.is_absolute(): output = Path.cwd() / output
    if output.exists():
        print(f"Refusing to overwrite existing summary: {output}", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["metric", "group", "numerator", "denominator", "rate"])
        writer.writeheader()
        writer.writerows(summary)
    print(f"Scored rows: {len(rows)}; request errors: {len(errors)}; successful requests: {len(valid_responses)}")
    print(f"Summary: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
