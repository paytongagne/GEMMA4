"""Launch the official swegemma CLI on user-supplied Kaggle public tasks.

This is a wrapper, not a replacement for the official evaluator. Requires the
Kaggle-provided swegemma environment, local inference server and Docker runtime.
No outside model/task data is downloaded by this tool.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def build_command(*, tasks: Path, snapshots: Path, submission: Path, results: Path,
                  task_id: str | None = None, tool_calls: int = 32,
                  time_minutes: int = 6, concurrency: int = 1) -> list[str]:
    """Construct command without a shell, using only validated local files."""
    if not tasks.is_file() or not snapshots.is_dir() or not submission.is_dir():
        raise ValueError("Official tasks.jsonl, snapshots/ and unpacked submission/ are required")
    if not (submission / "agent.yaml").is_file():
        raise ValueError("submission directory lacks agent.yaml")
    if not (1 <= tool_calls <= 1000 and 1 <= time_minutes <= 120 and 1 <= concurrency <= 16):
        raise ValueError("Invalid evaluation budget")
    argv = ["swegemma", "eval", "--tasks", str(tasks.resolve()),
            "--snapshots-dir", str(snapshots.resolve()),
            "--submission-dir", str(submission.resolve()),
            "--results-dir", str(results.resolve()),
            "--sandbox", "docker", "--max-tool-calls", str(tool_calls),
            "--max-time-minutes", str(time_minutes),
            "--concurrency", str(concurrency), "--display", "auto"]
    if task_id:
        if len(task_id) > 256 or any(c.isspace() for c in task_id):
            raise ValueError("Invalid task identifier")
        argv += ["--task-id", task_id]
    return argv


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--snapshots-dir", required=True, type=Path)
    ap.add_argument("--submission-dir", default=ROOT / "submission", type=Path)
    ap.add_argument("--results-dir", default=ROOT / "runs" / "official", type=Path)
    ap.add_argument("--task-id", help="Use ONE public development task first")
    ap.add_argument("--max-tool-calls", type=int, default=32)
    ap.add_argument("--max-time-minutes", type=int, default=6)
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--execute", action="store_true", help="Launch sandboxed official evaluator (opt-in)")
    args = ap.parse_args()
    try:
        cmd = build_command(tasks=args.tasks, snapshots=args.snapshots_dir,
                            submission=args.submission_dir, results=args.results_dir,
                            task_id=args.task_id, tool_calls=args.max_tool_calls,
                            time_minutes=args.max_time_minutes, concurrency=args.concurrency)
    except ValueError as error:
        ap.error(str(error))
    print(json.dumps({"command_argv": cmd, "will_execute": args.execute}, indent=2))
    if not args.execute:
        print("Dry run only. Pass --execute after verifying the official Kaggle environment.")
        return
    if shutil.which("swegemma") is None or shutil.which("docker") is None:
        ap.error("The official swegemma CLI and Docker must both be available")
    args.results_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(cmd, check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
