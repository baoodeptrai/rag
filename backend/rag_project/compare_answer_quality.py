"""Compare manually scored answer-quality runs on the same frozen data."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path


METRICS = {
    "answer_correct_rate": ("answer_correct", "answerable"),
    "answer_complete_rate": ("answer_complete", "answerable"),
    "answer_grounded_rate": ("answer_grounded", "answerable"),
    "citation_document_correct_rate": ("citation_document_correct", "answerable"),
    "citation_page_correct_rate": ("citation_page_correct", "answerable"),
    "citation_evidence_supported_rate": ("citation_evidence_supports_answer", "answerable"),
    "false_refusal_rate": ("system_refused", "answerable"),
    "correct_refusal_rate": ("system_refused", "expected_refusal"),
}


def parse_bool(value: str) -> bool | None:
    value = (value or "").strip().casefold()
    if value in {"true", "1", "yes"}: return True
    if value in {"false", "0", "no"}: return False
    return None


def load_run(path: Path) -> tuple[list[dict], dict]:
    source = path.resolve()
    metadata_path = source.with_suffix(source.suffix + ".metadata.json")
    if not source.is_file() or not metadata_path.is_file():
        raise ValueError(f"CSV or metadata file not found: {source}")
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not rows:
        raise ValueError(f"Run CSV is empty: {source}")
    required = {"dataset_sha256", "corpus_sha256", "model_tag_from_backend_env", "orchestrator_model_tag_from_backend_env"}
    missing = required - metadata.keys()
    if missing:
        raise ValueError(f"Run metadata missing {sorted(missing)}: {metadata_path}")
    ids = [row.get("question_id", "").strip() for row in rows]
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"Run must contain unique question_id values: {source}")
    metadata["source_path"] = str(source)
    return rows, metadata


def score_rows(rows: list[dict], metadata: dict) -> list[dict]:
    answerable = [row for row in rows if parse_bool(row.get("expected_refusal", "")) is False]
    expected_refusal = [row for row in rows if parse_bool(row.get("expected_refusal", "")) is True]
    errors = [row for row in rows if (row.get("request_error") or "").strip()]
    successful = [row for row in rows if not (row.get("request_error") or "").strip()]
    output = []

    def add(metric: str, cohort: str, subset: list[dict], field: str) -> None:
        scored = [parse_bool(row.get(field, "")) for row in subset if not (row.get("request_error") or "").strip()]
        scored = [value for value in scored if value is not None]
        output.append({"answer_model": metadata["model_tag_from_backend_env"],
                       "orchestrator_model": metadata["orchestrator_model_tag_from_backend_env"],
                       "metric": metric, "cohort": cohort, "numerator": sum(scored),
                       "denominator": len(scored),
                       "rate": sum(scored) / len(scored) if scored else ""})

    output.append({"answer_model": metadata["model_tag_from_backend_env"],
                   "orchestrator_model": metadata["orchestrator_model_tag_from_backend_env"],
                   "metric": "request_error_rate", "cohort": "all", "numerator": len(errors),
                   "denominator": len(rows), "rate": len(errors) / len(rows)})
    for metric, (field, cohort) in METRICS.items():
        add(metric, cohort, answerable if cohort == "answerable" else expected_refusal, field)
    latencies = []
    for row in successful:
        try: latencies.append(float(row["latency_ms"]))
        except (KeyError, TypeError, ValueError): pass
    output.append({"answer_model": metadata["model_tag_from_backend_env"],
                   "orchestrator_model": metadata["orchestrator_model_tag_from_backend_env"],
                   "metric": "end_to_end_latency_ms_median", "cohort": "successful_requests",
                   "numerator": "", "denominator": len(latencies),
                   "rate": statistics.median(latencies) if latencies else ""})
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", nargs="+", type=Path, help="At least two manually scored answer run CSV files")
    parser.add_argument("--output", type=Path, help="Comparison CSV; defaults to a timestamped file in evaluation results")
    args = parser.parse_args()
    if len(args.input_csv) < 2:
        parser.error("provide at least two answer run CSV files")
    try:
        runs = [load_run(path) for path in args.input_csv]
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    metadata = [item[1] for item in runs]
    for field in ("dataset_sha256", "corpus_sha256", "orchestrator_model_tag_from_backend_env"):
        values = {str(item[field]) for item in metadata}
        if len(values) != 1:
            print(f"Runs are not comparable: {field} differs ({sorted(values)}).", file=sys.stderr)
            return 2
    id_sets = [{row["question_id"].strip() for row in rows} for rows, _ in runs]
    if any(ids != id_sets[0] for ids in id_sets[1:]):
        print("Runs are not comparable: question_id sets differ.", file=sys.stderr)
        return 2

    output_rows = [row for rows, meta in runs for row in score_rows(rows, meta)]
    output = args.output or (Path(__file__).resolve().parents[2] / "docs" / "evaluation" / "results" /
                             f"answer_quality_model_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    if not output.is_absolute(): output = Path.cwd() / output
    if output.exists():
        print(f"Refusing to overwrite existing comparison: {output}", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["answer_model", "orchestrator_model", "metric", "cohort", "numerator", "denominator", "rate"])
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"Compared {len(runs)} runs on {len(id_sets[0])} matching questions.")
    print(f"Comparison: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
