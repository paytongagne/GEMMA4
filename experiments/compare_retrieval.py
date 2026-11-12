"""Reproducible read-only localization comparison on explicit task manifests."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from gemma4_agent.evaluation import evaluate, load_tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path, help='JSONL: task_id, repository, issue, target_files, split')
    parser.add_argument('--budgets', type=int, nargs='+', default=[500, 1500, 3000])
    parser.add_argument('--seed', type=int, default=13)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = evaluate(load_tasks(args.manifest), budgets=args.budgets, seed=args.seed)
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + '\n', encoding='utf-8')
        print(f'Report saved: {args.output}')
    for budget in sorted(set(args.budgets)):
        print(f'Budget: {budget} source characters')
        for method in report['methods']:
            s = report['summary'][f'{budget}:{method}']
            print(f'  {method:<16} any-recall={s["any_file_recall"]:.3f} all-recall={s["all_file_recall"]:.3f} MRR={s["mean_reciprocal_rank"]:.3f}')
    print('NOTE: localization only. No Gemma 4 inference or patch resolution measured.')


if __name__ == '__main__':
    main()
