import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gemma4_agent.retrieval import index_repository, retrieve


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        (root / "pkg").mkdir()
        (root / "pkg" / "__init__.py").write_text("")
        (root / "pkg" / "handler.py").write_text(
            "from pkg.storage import load_records\n"
            "def handle_request(payload):\n    return load_records(payload)\n")
        (root / "pkg" / "storage.py").write_text(
            "def load_records(payload):\n    return payload['records']\n")
        (root / "pkg" / "formatting.py").write_text(
            "def format_title(title):\n    return title.upper()\n")
        (root / "broken.py").write_text("def incomplete(:\n")
        self.idx = index_repository(root)

    def tearDown(self):
        self.temp.cleanup()

    def test_index_and_import_graph(self):
        self.assertIn("pkg/storage.py", self.idx.neighbors["pkg/handler.py"])
        self.assertIn("pkg/handler.py", self.idx.neighbors["pkg/storage.py"])
        self.assertTrue(any(s.name == "load_records" for s in self.idx.spans))

    def test_structural_prioritizes_named_function(self):
        results = retrieve(self.idx, "load_records crashes", "structural")
        self.assertEqual(results[0].name, "load_records")

    def test_graph_surfaces_import_neighbor(self):
        results = retrieve(self.idx, "handle_request fails", "graph")
        paths = {r.path for r in results}
        self.assertIn("pkg/handler.py", paths)
        self.assertIn("pkg/storage.py", paths)

    def test_malformed_python_is_searchable(self):
        self.assertTrue(any(s.path == "broken.py" for s in self.idx.spans))

    def test_budget_and_validation(self):
        results = retrieve(self.idx, "load_records", max_chars=60)
        self.assertLessEqual(sum(len(s.text) for s in results), 60)
        with self.assertRaises(ValueError):
            retrieve(self.idx, "test", method="future_method")
        with self.assertRaises(ValueError):
            retrieve(self.idx, "test", max_chars=0)


if __name__ == "__main__":
    unittest.main()
