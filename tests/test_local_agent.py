import difflib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gemma4_agent.local_agent import (OpenAICompatibleModel, repair, validate_patch)


class FakeModel:
    def __init__(self, patch):
        self.patch = patch
        self.calls = 0

    def complete(self, system, prompt):
        self.calls += 1
        assert "SOURCE CONTEXT" in prompt
        return self.patch


def make_diff(original, replacement, rel="calc.py"):
    return "".join(difflib.unified_diff(original.splitlines(True), replacement.splitlines(True),
                                        fromfile=f"a/{rel}", tofile=f"b/{rel}"))


class LocalAgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "tests").mkdir()
        self.old = "def double(x):\n    return x + x + 1\n"
        self.new = "def double(x):\n    return x + x\n"
        (self.root / "calc.py").write_text(self.old)
        (self.root / "tests" / "test_calc.py").write_text(
            "import sys, unittest\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n"
            "from calc import double\nclass TestCalc(unittest.TestCase):\n"
            "    def test_double(self):\n        self.assertEqual(double(4), 8)\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_end_to_end_mock_patch_with_opt_in_local_tests(self):
        model = FakeModel(make_diff(self.old, self.new))
        report = repair(self.root, "double(4) returns 9, should return 8", model, model_name="test-only-mock",
                        verify_command=[sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
                        allow_local_tests=True)
        self.assertEqual(report.status, "locally_verified", report.verify_output)
        self.assertEqual(report.changed_files, ["calc.py"])
        self.assertEqual(model.calls, 1)
        self.assertEqual((self.root / "calc.py").read_text(), self.old, "Original repo should not be altered")

    def test_without_opt_in_never_executes_tests(self):
        report = repair(self.root, "double bug", FakeModel(make_diff(self.old, self.new)),
                        model_name="mock", verify_command=["nonexistent-command"])
        self.assertEqual(report.verify_status, "not_run")
        self.assertEqual(report.status, "patch_applied")

    def test_rejects_traversal_and_test_file_edits(self):
        with self.assertRaises(ValueError):
            validate_patch(make_diff("a\n", "b\n", "../outside.py"), self.root)
        with self.assertRaises(ValueError):
            validate_patch(make_diff("a\n", "b\n", "tests/test_calc.py"), self.root)

    def test_refuses_remote_http_and_remote_without_opt_in(self):
        with self.assertRaises(ValueError):
            OpenAICompatibleModel("https://example.org/v1/chat/completions", "m")
        with self.assertRaises(ValueError):
            OpenAICompatibleModel("http://example.org/v1/chat/completions", "m", allow_remote=True)
        OpenAICompatibleModel("http://127.0.0.1:8000/v1/chat/completions", "m")

    def test_unapplicable_patch_fails_closed(self):
        bogus = make_diff("def broken():\n    pass\n", "def broken():\n    return 1\n")
        result = repair(self.root, "double bug", FakeModel(bogus), model_name="mock")
        self.assertEqual(result.status, "unapplicable_patch")

    def test_no_patch(self):
        result = repair(self.root, "fix", FakeModel("NO_PATCH"), model_name="mock")
        self.assertEqual(result.status, "unresolved")


if __name__ == "__main__":
    unittest.main()
