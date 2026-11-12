"""Offline smoke test on deliberately tiny synthetic examples.

This is NOT a SWE-bench experiment and does NOT measure Gemma 4 repair success.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gemma4_agent.retrieval import index_repository, retrieve

CASES = [
    {"issue": "handle_request fails on invalid payload", "target": "pkg/handler.py"},
    {"issue": "load_records should handle missing records", "target": "pkg/storage.py"},
    {"issue": "format_title should trim whitespace", "target": "pkg/formatting.py"},
]

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("")
    (root / "pkg" / "handler.py").write_text(
        "from pkg.storage import load_records\ndef handle_request(payload):\n    return load_records(payload)\n")
    (root / "pkg" / "storage.py").write_text(
        "def load_records(payload):\n    return payload['records']\n")
    (root / "pkg" / "formatting.py").write_text(
        "def format_title(title):\n    return title.upper()\n")
    index = index_repository(root)
    report = {"experiment": "synthetic_smoke_test", "tasks": len(CASES), "model_used": False, "methods": {}}
    for method in ("lexical", "structural", "graph"):
        hits = 0
        examples = []
        for case in CASES:
            selected = retrieve(index, case["issue"], method=method, max_chars=200)
            paths = [span.path for span in selected]
            hit = case["target"] in paths
            hits += int(hit)
            examples.append({"issue": case["issue"], "expected_file": case["target"], "retrieved_files": paths, "hit": hit})
        report["methods"][method] = {"file_recall_at_budget": hits / len(CASES), "cases": examples}
    print(json.dumps(report, indent=2))
