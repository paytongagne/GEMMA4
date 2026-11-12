"""Aggregate actual *official* swegemma results without inventing scores."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean


def parse_results(results_dir: Path) -> dict:
    path = results_dir / "task_results.jsonl"
    if not path.is_file():
        raise ValueError(f"Expected official task results at {path}")
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at line {number}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"Task result at line {number} must be an object")
        rows.append(row)
    if not rows:
        raise ValueError("Official results contain no tasks")
    resolved_values = []
    failure_reasons = Counter()
    unknown = 0
    for row in rows:
        resolved = row.get("resolved")
        if not isinstance(resolved, bool):
            score = row.get("score")
            if isinstance(score, (int, float)) and not isinstance(score, bool) and score in (0, 1):
                resolved = bool(score)
            else:
                unknown += 1
                continue
        resolved_values.append(resolved)
        if not resolved:
            failure_reasons[str(row.get("error") or row.get("failure_reason") or "unspecified")[:160]] += 1
    known = len(resolved_values)
    official_summary = results_dir / "summary.json"
    declared = None
    if official_summary.is_file():
        try:
            declared = json.loads(official_summary.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raise ValueError("Invalid official summary.json")
    return {
        "source": "swegemma task_results.jsonl (local aggregate)",
        "model_measured": "Refer to source trace; cannot infer from results filenames",
        "task_count": len(rows),
        "known_resolution_count": known,
        "unknown_resolution_count": unknown,
        "resolved_count": sum(resolved_values),
        "resolution_rate_known_tasks": round(mean(resolved_values), 5) if known else None,
        "failure_reasons": dict(failure_reasons.most_common()),
        "official_summary_available": declared is not None,
        "official_summary_resolution_rate": declared.get("resolution_rate") if isinstance(declared, dict) else None,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "warning": "Not an official leaderboard score; verify completeness, task split, model, and harness version.",
    }


def to_markdown(report: dict) -> str:
    rate = report["resolution_rate_known_tasks"]
    value = f"{rate*100:.2f}%" if rate is not None else "unknown"
    lines = ["# Official Harness Results (Local Summary)", "",
             f"- Tasks reported: **{report['task_count']}**",
             f"- Tasks with verifiable outcomes: **{report['known_resolution_count']}**",
             f"- Tasks with unknown outcome: **{report['unknown_resolution_count']}**",
             f"- Resolved tasks: **{report['resolved_count']}**",
             f"- Resolution rate among known tasks: **{value}**", "",
             "## Failure reasons", ""]
    for reason, count in report["failure_reasons"].items():
        lines.append(f"- {reason}: {count}")
    lines += ["", "> " + report["warning"], ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results-dir", required=True, type=Path)
    ap.add_argument("--output-dir", type=Path)
    args = ap.parse_args()
    report = parse_results(args.results_dir)
    out = args.output_dir or args.results_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "gemma4_official_summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (out / "gemma4_official_summary.md").write_text(to_markdown(report), encoding="utf-8")
    print(to_markdown(report))


if __name__ == "__main__":
    main()
