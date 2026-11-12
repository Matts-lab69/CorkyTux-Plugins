"""Require real child-process coverage for every inventoried entrypoint."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "existing_command_contract", ROOT / "tests/test_command_contract.py"
)
CONTRACT_TESTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT_TESTS)

# The existing argparse tests already execute each command with --help.
PROBES = {
    "appimage-launcher": (["status"], 0, None),
    "rpgmaker-runtime": (["scan", "{missing}"], 2, "path does not exist"),
    "dependency-installer": (["scan", "{empty}"], 0, None),
    "dll-overrides-automator": (["scan", "{empty}"], 0, None),
    "emulator-manager": (["corky-list"], 0, None),
}


class EntrypointSubprocessContract(unittest.TestCase):
    def test_every_inventory_entrypoint_has_subprocess_coverage(self):
        covered = CONTRACT_TESTS.ARGPARSE | set(PROBES)
        self.assertEqual(covered, set(CONTRACT_TESTS.CONTRACT))
        for plugin, (arguments, _, _) in PROBES.items():
            self.assertIn(arguments[0], {entry["command"] for entry in CONTRACT_TESTS.CONTRACT[plugin]})

    def test_custom_entrypoints_accept_real_readonly_commands(self):
        for plugin, (arguments, exit_code, expected_error) in PROBES.items():
            with self.subTest(plugin=plugin), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                empty = base / "empty-game"
                empty.mkdir()
                replacements = {"empty": str(empty), "missing": str(base / "missing-game")}
                argv = [value.format(**replacements) for value in arguments]
                environment = {
                    "HOME": temporary,
                    "XDG_CONFIG_HOME": str(base / "config"),
                    "XDG_DATA_HOME": str(base / "data"),
                    "XDG_CACHE_HOME": str(base / "cache"),
                    "TMPDIR": temporary,
                    "PATH": "",
                    "LANG": "C.UTF-8",
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
                result = subprocess.run(
                    [sys.executable, str(ROOT / plugin / plugin), *argv],
                    cwd=base,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                self.assertEqual(result.returncode, exit_code, result.stderr)
                events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
                self.assertTrue(events, "entrypoint must emit its actual JSON protocol")
                if expected_error:
                    # RPG fail() emits the JSON-lines error envelope consumed by
                    # Launcher plugin_process: type=error and message, not error.
                    self.assertEqual(events, [{
                        "ok": False,
                        "type": "error",
                        "message": f"{expected_error}: {replacements['missing']}",
                    }])
                else:
                    self.assertTrue(any(event.get("ok") is True for event in events), result.stdout)


if __name__ == "__main__":
    unittest.main()
