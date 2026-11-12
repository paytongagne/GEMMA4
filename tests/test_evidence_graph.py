import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gemma4_agent.evidence_graph import index_evidence_graph, select_context, tokenize
from gemma4_agent.evaluation import evaluate, load_tasks, Task


class EvidenceGraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "pkg").mkdir()
        (self.root / "pkg/__init__.py").write_text("")
        (self.root / "pkg/api.py").write_text("from .store import fetch as load\n\ndef submit_order(value):\n    return load(value)\n")
        (self.root / "pkg/store.py").write_text("def fetch(value):\n    return value['payload']\n")
        (self.root / "pkg/helper.py").write_text("def other(value):\n    return value\n")
        (self.root / "pkg/logic.py").write_text("class Parser:\n    def parse(self, data):\n        return self.validate(data)\n\n    def validate(self, data):\n        return data.strip()\n")
        self.idx = index_evidence_graph(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_normalization(self):
        self.assertEqual(tokenize("camelCase and read_file"), {"camel", "case", "read", "file"})

    def test_imported_call_edge(self):
        self.assertTrue(any(e.kind == "imported_call" and "api.py" in e.source and "store.py" in e.destination for e in self.idx.edges))

    def test_self_method_edge(self):
        self.assertTrue(any(e.kind == "self_method" and "Parser.parse" in e.source and "Parser.validate" in e.destination for e in self.idx.edges))

    def test_relative_import_edge(self):
        self.assertIn("pkg/store.py", self.idx.file_neighbors["pkg/api.py"])

    def test_budget_never_exceeded(self):
        for method in ("lexical", "structural", "file_graph", "evidence_graph"):
            pack = select_context(self.idx, "submit_order payload", method, 150)
            self.assertLessEqual(pack.used_chars, 150)
            self.assertEqual(pack.used_chars, sum(s.span.cost for s in pack.selections))
            self.assertEqual(pack.files, list(dict.fromkeys(pack.files)))

    def test_same_result_repeated(self):
        a = select_context(self.idx, "submit_order bug", "evidence_graph", 500)
        b = select_context(self.idx, "submit_order bug", "evidence_graph", 500)
        self.assertEqual(a, b)

    def test_malformed_syntax_retained(self):
        (self.root / "pkg/bad.py").write_text("def broken(:\n")
        idx = index_evidence_graph(self.root)
        self.assertTrue(any(s.symbol == "<unparsed>" for s in idx.spans))
        self.assertTrue(idx.warnings)

    def test_methods_validate(self):
        for method in ("unknown", ""):
            with self.assertRaises(ValueError):
                select_context(self.idx, "issue", method)
        with self.assertRaises(ValueError):
            select_context(self.idx, "issue", budget_chars=0)
        with self.assertRaises(ValueError):
            select_context(self.idx, "issue", seed_count=0)

    def test_nonempty_and_evidence(self):
        pack = select_context(self.idx, "submit_order failure", "evidence_graph", 900)
        self.assertIn("pkg/api.py", pack.files)
        self.assertIn("pkg/store.py", pack.files)
        evidence = [r for s in pack.selections for r in s.evidence]
        self.assertTrue(any("imported_call" in r for r in evidence))

    def test_empty_query(self):
        self.assertFalse(select_context(self.idx, "the a of", "lexical").selections)

    def test_evaluator_pairs_identically(self):
        tasks = [Task("001", str(self.root), "submit_order broken", ("pkg/api.py",), "dev"),
                 Task("002", str(self.root), "Parser validate", ("pkg/logic.py",), "dev")]
        r = evaluate(tasks, budgets=[150, 600], bootstrap_draws=200)
        self.assertEqual(r["task_count"], 2)
        self.assertEqual(len(r["task_details"]), 2 * 2 * 4)
        self.assertIn("600:evidence_graph-lexical", r["paired_vs_lexical"])
        self.assertIn("patch generation", r["not_measured"])
        self.assertEqual(r, evaluate(tasks, budgets=[150, 600], bootstrap_draws=200))

    def test_manifest_guardrails(self):
        path = self.root / "manifest.jsonl"
        path.write_text(json.dumps({"task_id":"001", "repository":".", "issue":"bug", "target_files":["pkg/api.py"], "split":"dev"})+"\n")
        self.assertEqual(load_tasks(path)[0].task_id, "001")
        path.write_text(json.dumps({"task_id":"001", "repository":".", "issue":"bug", "target_files":["../escape.py"], "split":"dev"})+"\n")
        with self.assertRaises(ValueError):
            load_tasks(path)


if __name__ == '__main__':
    unittest.main()
