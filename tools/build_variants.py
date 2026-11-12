"""Produce paired, config-identical agent variants for Kaggle development studies.

These are *candidate* archives requiring the official compiler and real-task tests.
The public competition limits submissions; evaluate candidates locally first.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_submission import build

GRAPH_LINE = (
    "- Use search_similar_code(issue or error message, k=8) for high-level localization; "
    "where exact dotted symbols emerge, use get_code_neighbors(node, max_neighbors=20) "
    "to inspect callers/dependencies. A graph result is a *hint*, not proof. "
    "Never call graph tools repeatedly without a concrete hypothesis."
)
LEXICAL_LINE = (
    "- Use repository text and symbol names to localize, with bounded `rg -n` or grep, "
    "then read the candidate source files. Do not call graph or embedding tools. "
    "A text match is a hypothesis, not proof."
)


def build_variants(submission: Path, dest: Path) -> list[dict]:
    if not submission.is_dir():
        raise ValueError("Missing submission")
    prompt = (submission / 'prompts/system.md').read_text(encoding='utf-8')
    if prompt.count(GRAPH_LINE) != 1:
        raise ValueError("Graph instruction anchor changed; inspect prompt before changing baseline")
    dest.mkdir(parents=True, exist_ok=True)
    variants = [
        ('graph_12b', 'gemma-4-12b-it-qat-w4a16-ct', prompt),
        ('lexical_12b', 'gemma-4-12b-it-qat-w4a16-ct', prompt.replace(GRAPH_LINE, LEXICAL_LINE)),
        ('graph_e4b', 'gemma-4-e4b-it-qat-w4a16-ct', prompt),
        ('graph_31b', 'gemma-4-31b-it-qat-w4a16-ct', prompt),
    ]
    summaries = []
    with tempfile.TemporaryDirectory(prefix='gemma4-variants-') as temp:
        for name, model, variant_prompt in variants:
            stage = Path(temp) / name
            shutil.copytree(submission, stage)
            agent_yaml = stage / 'agent.yaml'
            contents = agent_yaml.read_text(encoding='utf-8')
            # Change one model scalar without changing budgets or other parameters.
            old = 'gemma-4-12b-it-qat-w4a16-ct'
            if contents.count(old) != 1:
                raise ValueError('Expected exactly one base-model declaration')
            agent_yaml.write_text(contents.replace(old, model), encoding='utf-8')
            (stage / 'prompts/system.md').write_text(variant_prompt, encoding='utf-8')
            output = dest / f'{name}.zip'
            info = build(stage, output)
            summaries.append({'variant': name, 'model': model,
                              'policy': 'lexical' if name.startswith('lexical') else 'graph',
                              'archive_bytes': info['bytes'], 'artifact': str(output)})
    (dest / 'variant_manifest.json').write_text(json.dumps(summaries, indent=2)+'\n', encoding='utf-8')
    return summaries


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--submission-dir', type=Path, default=ROOT/'submission')
    ap.add_argument('--output-dir', type=Path, default=ROOT/'artifacts'/'variants')
    args=ap.parse_args()
    for record in build_variants(args.submission_dir,args.output_dir):
        print(json.dumps(record))

if __name__=='__main__': main()
