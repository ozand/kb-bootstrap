"""Offline checks: ordinary test collection never invokes QMD."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml

SPEC = importlib.util.spec_from_file_location('membership_smoke', Path(__file__).parents[1] / 'tools/qmd_membership_smoke.py')
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)

class MembershipFixtureTests(unittest.TestCase):
    def test_explicit_consent_required_before_any_process(self):
        with patch.object(smoke, 'run_bounded', side_effect=AssertionError('must not run')):
            with self.assertRaises(ValueError):
                smoke.execute()

    def test_hook_free_owned_single_collection_and_unique_tokens(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, state, cwd, tokens = smoke.prepare(base)
            config = yaml.safe_load((state / 'config/membership.yml').read_text(encoding='utf-8'))
            self.assertEqual(set(config), {'collections', 'models'})
            self.assertEqual(set(config['collections']), {'fixture'})
            spec = config['collections']['fixture']
            self.assertEqual(set(spec), {'path', 'pattern', 'ignore'})
            self.assertEqual(Path(spec['path']), root)
            self.assertEqual(spec['ignore'], smoke.IGNORE)
            self.assertEqual(len(tokens), len(set(tokens.values())))
            self.assertTrue(all((root / path).is_file() for path in tokens))
            self.assertEqual(list(cwd.iterdir()), [])
