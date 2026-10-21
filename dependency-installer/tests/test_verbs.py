"""Tests for the dependency installer: the verb map and the media confidence.

Uso: python3 -m unittest tests.test_verbs
"""
import importlib.machinery
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "dependency-installer"


def load():
    loader = importlib.machinery.SourceFileLoader("dep_installer", str(SCRIPT))
    spec = importlib.util.spec_from_loader("dep_installer", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class CheckVerbsTests(unittest.TestCase):
    """`check-verbs` tells which mapped verb the winetricks can load."""

    def test_check_verbs_reports_the_mapped_verbs(self):
        with tempfile.TemporaryDirectory() as tmp:
            proton = Path(tmp) / "proton"
            winetricks = proton / "protonfixes" / "winetricks"
            winetricks.parent.mkdir(parents=True)
            winetricks.write_text(
                "#!/bin/sh\nload_physx() { :; }\nload_xinput() { :; }\n"
            )
            winetricks.chmod(0o755)
            out = subprocess.run(
                [str(SCRIPT), "check-verbs", "--proton", str(proton)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(out.returncode, 0, out.stderr)
            doc = json.loads(out.stdout)
            verbs = {v["verb"]: v["ok"] for v in doc["verbs"]}
            # The renamed verbs are the real winetricks function names.
            self.assertIn("physx", verbs)
            self.assertIn("xinput", verbs)
            self.assertTrue(verbs["physx"], verbs)
            self.assertTrue(verbs["xinput"], verbs)
            # The retired verbs are gone for good.
            self.assertNotIn("coreaudio", verbs)
            self.assertNotIn("wmvcore", verbs)
            # A verb without a winetricks function is reported as missing.
            self.assertIn("quartz", doc["missing"])
            self.assertFalse(doc["ok"])


class MediaConfidenceTests(unittest.TestCase):
    """A media DLL only found in a bundled DLL is weak evidence."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _scan(self, game_dir):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.m.scan_game(str(game_dir))
        return json.loads(buf.getvalue().strip())

    def test_media_dll_in_a_bundled_dll_is_optional(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / "game"
            (game / "sub").mkdir(parents=True)
            (game / "sub" / "data.dll").write_bytes(b"MZ\x00\x00quartz.dll\x00")
            doc = self._scan(game)
            directshow = next(d for d in doc["deps"] if d["id"] == "quartz")
            self.assertEqual(directshow["confidence"], "low", directshow)
            self.assertEqual(directshow["status"], "optional", directshow)

    def test_media_dll_in_a_top_level_exe_is_a_real_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / "game"
            game.mkdir(parents=True)
            (game / "game.exe").write_bytes(b"MZ\x00\x00quartz.dll\x00")
            doc = self._scan(game)
            directshow = next(d for d in doc["deps"] if d["id"] == "quartz")
            self.assertEqual(directshow["confidence"], "detected", directshow)
            self.assertEqual(directshow["status"], "missing", directshow)

    def test_an_optional_dep_does_not_need_an_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / "game"
            (game / "sub").mkdir(parents=True)
            (game / "sub" / "data.dll").write_bytes(b"MZ\x00\x00quartz.dll\x00")
            doc = self._scan(game)
            optional = [d["id"] for d in doc["deps"] if d.get("status") == "optional"]
            self.assertIn("quartz", optional)
            # Nothing needs installing: the optional dep is not in the list.
            self.assertIn("All 0 dependencies already installed", doc["message"])


if __name__ == "__main__":
    unittest.main()
