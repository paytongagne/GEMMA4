"""Artifact builder and deterministic offline Kaggle notebook integration."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_submission", ROOT / "tools" / "build_submission.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class SubmissionTests(unittest.TestCase):
    def test_builder_archive_and_validator(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "submission.zip"
            manifest = builder.build(ROOT / "submission", target)
            self.assertIn("agent.yaml", manifest["files"])
            self.assertEqual(manifest["model"], "gemma-4-12b-it-qat-w4a16-ct")
            with zipfile.ZipFile(target) as archive:
                self.assertTrue(archive.read("agent.yaml").startswith(b"agent_class:"))
                self.assertIsNone(archive.testzip())
                self.assertNotIn("submission/agent.yaml", archive.namelist())

    def test_missing_root_rejected(self):
        with self.assertRaises(ValueError):
            builder.validate({"prompts/system.md": b"hello"})

    def test_external_include_rejected(self):
        entries = builder.collect(ROOT / "submission")
        entries["agent.yaml"] = entries["agent.yaml"].replace(b"prompts/system.md", b"../secrets.md")
        with self.assertRaises(ValueError):
            builder.validate(entries)

    def test_notebook_reproduces_archive_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            notebook_path = Path(tmp) / "nb.ipynb"
            builder.make_kaggle_notebook(ROOT / "submission", notebook_path)
            nb = json.loads(notebook_path.read_text())
            self.assertEqual(nb["nbformat"], 4)
            source = "".join(nb["cells"][1]["source"])
            import os
            old = os.getcwd()
            try:
                os.chdir(tmp)
                exec(compile(source, str(notebook_path), "exec"), {"__name__": "__main__"})
            finally:
                os.chdir(old)
            with zipfile.ZipFile(Path(tmp) / "submission.zip") as archive:
                self.assertIn("agent.yaml", archive.namelist())
                self.assertIsNone(archive.testzip())


if __name__ == "__main__":
    unittest.main()
