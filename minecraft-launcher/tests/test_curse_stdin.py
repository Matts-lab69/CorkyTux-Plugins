import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "minecraft-launcher"
TEST_INPUT = "CURSEFORGE_STDIN_TEST_INPUT"


class CurseStdinContract(unittest.TestCase):
    def test_real_cli_reads_stdin_without_exposing_the_input(self):
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, HOME=home)
            command = [str(SCRIPT), "curse-auth-config", "--api-key-stdin"]
            result = subprocess.run(
                command, input=TEST_INPUT, text=True, capture_output=True,
                env=env, timeout=20,
            )
            self.assertTrue(result.returncode == 0, "stdin command failed")
            self.assertTrue(TEST_INPUT not in result.stdout, "stdout leak")
            self.assertTrue(TEST_INPUT not in result.stderr, "stderr leak")
            self.assertTrue(all(TEST_INPUT not in part for part in command), "argv leak")
            saved = Path(home) / ".config/CorkyTux/plugins/minecraft-launcher/curseforge.json"
            self.assertTrue(json.loads(saved.read_text())["api_key"] == TEST_INPUT, "stdin not saved")
            self.assertTrue(stat.S_IMODE(saved.stat().st_mode) == 0o600, "private file mode")
            show = subprocess.run(
                [str(SCRIPT), "curse-auth-config", "--show"],
                text=True, capture_output=True, env=env, timeout=20,
            )
            self.assertTrue(show.returncode == 0, "show failed")
            self.assertTrue(TEST_INPUT not in show.stdout + show.stderr, "show leak")

    def test_empty_stdin_is_rejected_without_creating_configuration(self):
        with tempfile.TemporaryDirectory() as home:
            result = subprocess.run(
                [str(SCRIPT), "curse-auth-config", "--api-key-stdin"],
                input="", text=True, capture_output=True,
                env=dict(os.environ, HOME=home), timeout=20,
            )
            self.assertTrue(result.returncode != 0, "empty stdin unexpectedly accepted")
            saved = Path(home) / ".config/CorkyTux/plugins/minecraft-launcher/curseforge.json"
            self.assertFalse(saved.exists(), "empty input persisted")


if __name__ == "__main__":
    unittest.main()
