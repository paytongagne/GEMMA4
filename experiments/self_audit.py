"""Development self-audit on this real, evolving project repository.

Manual labels are deliberately small and not held out. This measures retrieval
sanity, NOT Gemma coding ability or generalization to unseen software bugs.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemma4_agent.evaluation import evaluate, load_tasks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=ROOT / "experiments" / "self_audit_tasks.jsonl", type=Path)
    parser.add_argument("--output", default=ROOT / "runs" / "self_audit.json", type=Path)
    parser.add_argument("--budgets", default=[700, 1500, 3000], nargs="+", type=int)
    args = parser.parse_args()
    report = evaluate(load_tasks(args.manifest), budgets=args.budgets, seed=13, bootstrap_draws=1000)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Development labels (NOT held-out): {report['task_count']} tasks")
    print("Budget (chars) | lexical | structural | file graph | evidence graph")
    for b in sorted(set(args.budgets)):
        ratios = [report['summary'][f'{b}:{m}']['any_file_recall'] for m in (
            'lexical','structural','file_graph','evidence_graph')]
        print(f"{b:>14} | " + " | ".join(f"{x:.1%}" for x in ratios))
    print('Detailed per-task cases:', args.output)


if __name__ == '__main__':
    main()
