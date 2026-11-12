"""Generate a toy multi-file localization suite. Not a scientific benchmark."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SOURCES = {
    'app/__init__.py': '',
    'app/handlers.py': '''from .storage import fetch_record as lookup
from .formatters import display_name

def handle_profile(payload):
    record = lookup(payload["user_id"])
    return display_name(record)
''',
    'app/storage.py': '''def fetch_record(key):
    cache = {"123": {"name": "Ada"}}
    return cache[key]
''',
    'app/formatters.py': '''def display_name(record):
    return record["name"].upper()
''',
    'app/validate.py': '''class Cleaner:
    def normalize(self, value):
        return self.remove_punctuation(value).strip()

    def remove_punctuation(self, value):
        return value.replace("!", "")
''',
    'app/calculate.py': '''def calculate_total(items):
    return sum(float(item["price"]) for item in items)
''',
    'app/alternate.py': '''def handle_profile(payload):
    return {"user_id": payload.get("user_id")}
''',
    'app/report.py': '''from .storage import fetch_record

def render_report(user_id):
    record = fetch_record(user_id)
    return record["name"]
''',
    'app/broken.py': 'def half_written(:\n',
}

TASKS = [
    ('toy-001', 'handle_profile crashes when account is absent', ['app/storage.py'], 'dev'),
    ('toy-002', 'display_name capitalization is wrong', ['app/formatters.py'], 'dev'),
    ('toy-003', 'Cleaner normalize should remove repeated punctuation', ['app/validate.py'], 'dev'),
    ('toy-004', 'calculate_total errors on decimal money input', ['app/calculate.py'], 'dev'),
    ('toy-005', 'render_report crashes when record missing', ['app/storage.py', 'app/report.py'], 'heldout_toy'),
    ('toy-006', 'handle_profile should validate payload shape before lookup', ['app/handlers.py'], 'heldout_toy'),
    ('toy-007', 'half_written source cannot be parsed', ['app/broken.py'], 'heldout_toy'),
]


def build(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    repo = path / 'toy_repository'
    repo.mkdir(exist_ok=True)
    for rel, source in SOURCES.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding='utf-8')
    manifest = path / 'toy_tasks.jsonl'
    with manifest.open('w', encoding='utf-8') as f:
        for ident, issue, files, split in TASKS:
            f.write(json.dumps({'task_id': ident, 'repository': 'toy_repository', 'issue': issue, 'target_files': files, 'split': split}) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', default='runs/toy_suite', type=Path)
    args = parser.parse_args()
    print(build(args.output_dir))
