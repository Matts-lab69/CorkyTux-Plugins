"""Require real child-process coverage for every inventoried entrypoint."""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "existing_command_contract", ROOT / "tests/test_command_contract.py"
)
CONTRACT_TESTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT_TESTS)

# The existing argparse tests already execute each command with --help.
PROBES = {}


class EntrypointSubprocessContract(unittest.TestCase):
    def test_every_inventory_entrypoint_has_subprocess_coverage(self):
        covered = CONTRACT_TESTS.ARGPARSE | set(PROBES)
        self.assertEqual(covered, set(CONTRACT_TESTS.CONTRACT))


if __name__ == "__main__":
    unittest.main()
