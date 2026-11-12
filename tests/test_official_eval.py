import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

def load_tool(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

harness = load_tool('official_eval.py', 'official_eval')
reporter = load_tool('report_official_eval.py', 'report_official_eval')

class OfficialEvaluationTests(unittest.TestCase):
    def test_dry_run_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'tasks.jsonl').write_text('{}\n')
            (root/'snapshots').mkdir()
            (root/'submission').mkdir()
            (root/'submission'/'agent.yaml').write_text('name: test\n')
            cmd = harness.build_command(tasks=root/'tasks.jsonl', snapshots=root/'snapshots',
                        submission=root/'submission', results=root/'results', task_id='repo__123')
            self.assertEqual(cmd[0:2], ['swegemma', 'eval'])
            self.assertIn('--task-id',cmd)
            with self.assertRaises(ValueError):
                harness.build_command(tasks=root/'tasks.jsonl', snapshots=root/'snapshots',
                                     submission=root/'submission', results=root/'results', tool_calls=-1)

    def test_report_known_unknown_and_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            values = [
                {'instance_id':'a','resolved':True},
                {'instance_id':'b','resolved':False,'error':'patch did not apply'},
                {'instance_id':'c','score':0},
                {'instance_id':'d','error':'not evaluated'},
            ]
            (root/'task_results.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in values))
            (root/'summary.json').write_text(json.dumps({'resolution_rate':1/3}))
            r=reporter.parse_results(root)
            self.assertEqual(r['known_resolution_count'],3)
            self.assertEqual(r['unknown_resolution_count'],1)
            self.assertEqual(r['resolved_count'],1)
            self.assertAlmostEqual(r['resolution_rate_known_tasks'],1/3,places=4)
            self.assertEqual(r['failure_reasons']['patch did not apply'],1)
            self.assertIn('33.33%',reporter.to_markdown(r))

    def test_missing_results_fail_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                reporter.parse_results(Path(tmp))

if __name__ == '__main__':
    unittest.main()
