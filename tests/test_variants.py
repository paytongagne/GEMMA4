from pathlib import Path
import importlib.util
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_variants',ROOT/'tools/build_variants.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class VariantTests(unittest.TestCase):
    def test_variant_builds_and_matching_configs(self):
        with tempfile.TemporaryDirectory() as t:
            records=module.build_variants(ROOT/'submission',Path(t))
            self.assertEqual(len(records),4)
            contents={}
            for record in records:
                with zipfile.ZipFile(record['artifact']) as z:
                    self.assertIn('agent.yaml',z.namelist())
                    self.assertIsNone(z.testzip())
                    contents[record['variant']]={n:z.read(n) for n in z.namelist()}
            self.assertEqual(contents['graph_12b']['eval_config.yaml'],contents['lexical_12b']['eval_config.yaml'])
            self.assertEqual(contents['graph_12b']['configs/sampling.yaml'],contents['lexical_12b']['configs/sampling.yaml'])
            self.assertEqual(contents['graph_12b']['agent.yaml'],contents['lexical_12b']['agent.yaml'])
            self.assertNotEqual(contents['graph_12b']['prompts/system.md'],contents['lexical_12b']['prompts/system.md'])
            self.assertIn(b'gemma-4-e4b-it-qat-w4a16-ct',contents['graph_e4b']['agent.yaml'])

if __name__=='__main__':unittest.main()
