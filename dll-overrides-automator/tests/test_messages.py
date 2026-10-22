"""Characterization tests: they pin the exact wording of the plugin messages.

They exist so that the conversion to f-strings cannot change a single word
of what the launcher shows the user.

Uso: python3 -m unittest tests.test_messages
"""
import importlib.machinery
import importlib.util
import io
import json
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "dll-overrides-automator"


def load():
    loader = importlib.machinery.SourceFileLoader("dll_overrides", str(SCRIPT))
    spec = importlib.util.spec_from_loader("dll_overrides", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class MessageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        # A read-only directory would block the cleanup.
        for root, dirs, _files in os.walk(self.base):
            for d in dirs:
                try:
                    os.chmod(os.path.join(root, d), 0o755)
                except OSError:
                    pass
        self.tmp.cleanup()

    def _out(self):
        buf = io.StringIO()
        return buf

    def _call(self, fn, *args):
        """Call fn and return (exit_code, stdout)."""
        buf = io.StringIO()
        code = 0
        with redirect_stdout(buf):
            try:
                code = fn(*args)
            except SystemExit as e:
                code = e.code
        return code, buf.getvalue()

    def _doc(self, *args):
        code, out = self._call(*args)
        return code, json.loads(out.strip())

    def _readonly(self, path):
        os.chmod(path, stat.S_IRUSR | stat.S_IXUSR)

    # 1. scan: not a directory
    def test_scan_reports_a_missing_directory(self):
        missing = str(self.base / "nope")
        code, doc = self._doc(self.m.scan, missing)
        self.assertEqual(code, 2)
        self.assertEqual(doc, {"ok": False, "error": f"not a directory: {missing}"})

    # 2. scan: the override list keeps the "base=suffix;" shape
    def test_scan_builds_the_override_list(self):
        game = self.base / "game"
        game.mkdir()
        (game / "winmm.txt").write_text("winmm.dll\n")
        code, doc = self._doc(self.m.scan, str(game))
        self.assertEqual(code, 0)
        self.assertEqual(doc["overrides"], "winmm=n")

    # 3. scan: a text file it cannot read
    def test_scan_warns_when_a_text_file_cannot_be_read(self):
        game = self.base / "game"
        game.mkdir()
        link = game / "winmm.txt"
        os.symlink(str(game / "missing.txt"), str(link))
        code, doc = self._doc(self.m.scan, str(game))
        self.assertEqual(code, 0)
        self.assertEqual(len(doc["warnings"]), 1)
        self.assertTrue(doc["warnings"][0].startswith(f"cannot read {link}: "),
                        doc["warnings"])

    # 4. scan: an ini it cannot parse
    def test_scan_warns_on_a_broken_ini(self):
        game = self.base / "game"
        game.mkdir()
        ini = game / "onlinefix.ini"
        ini.write_text("this is not an ini file\n")
        code, doc = self._doc(self.m.scan, str(game))
        self.assertEqual(code, 0)
        self.assertEqual(len(doc["warnings"]), 1)
        self.assertTrue(doc["warnings"][0].startswith(f"cannot parse ini {ini}: "),
                        doc["warnings"])

    # 5. scan: the symlink it cannot create
    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "root ignores the permission bits")
    def test_scan_warns_when_the_symlink_fails(self):
        game = self.base / "game"
        (game / "sub").mkdir(parents=True)
        # `onlinefix.json` is the trigger of the Newtonsoft repair.
        (game / "onlinefix.json").write_text("{}")
        (game / "Launcher.exe").write_bytes(b"MZ")
        (game / "sub" / "Newtonsoft.Json.dll").write_bytes(b"x")
        self._readonly(game)
        code, doc = self._doc(self.m.scan, str(game))
        self.assertEqual(code, 0)
        self.assertEqual(len(doc["warnings"]), 1)
        self.assertTrue(doc["warnings"][0].startswith("symlink failed "),
                        doc["warnings"])
        self.assertIn("Newtonsoft.Json.dll", doc["warnings"][0])

    # 6. patch: not a directory
    def test_patch_reports_a_missing_directory(self):
        missing = str(self.base / "nope")
        code, doc = self._doc(self.m.cmd_patch, missing)
        self.assertEqual(code, 2)
        self.assertEqual(doc, {"ok": False, "error": f"not a directory: {missing}"})

    # 7. patch: no steamfix dlls
    def test_patch_reports_no_steamfix_dlls(self):
        fixdir = self.base / "fix"
        fixdir.mkdir()
        code, doc = self._doc(self.m.cmd_patch, str(fixdir))
        self.assertEqual(code, 2)
        self.assertEqual(doc, {"ok": False, "error": f"no steamfix dlls in {fixdir}"})

    # 8. patch: the dll it cannot patch
    def test_patch_reports_the_failure_of_a_dll(self):
        fixdir = self.base / "fix"
        fixdir.mkdir()
        dll = fixdir / "steamfix1.dll"
        dll.write_bytes(b"x")
        empty_vendor = self.base / "vendor"
        empty_vendor.mkdir()
        old_vendor = self.m.VENDOR
        self.m.VENDOR = str(empty_vendor)
        try:
            code, doc = self._doc(self.m.cmd_patch, str(fixdir))
        finally:
            self.m.VENDOR = old_vendor
        self.assertEqual(code, 2)
        self.assertEqual(len(doc["failed"]), 1)
        self.assertTrue(doc["failed"][0].startswith(f"{dll}: "), doc["failed"])

    # 9. unpatch: not a directory
    def test_unpatch_reports_a_missing_directory(self):
        missing = str(self.base / "nope")
        code, doc = self._doc(self.m.cmd_unpatch, missing)
        self.assertEqual(code, 2)
        self.assertEqual(doc, {"ok": False, "error": f"not a directory: {missing}"})

    # 10. unpatch: the backup it cannot restore
    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "root ignores the permission bits")
    def test_unpatch_reports_a_failure(self):
        fixdir = self.base / "fix"
        fixdir.mkdir()
        backup = fixdir / "steamfix1.dll.noofllpath"
        backup.write_bytes(b"x")
        self._readonly(fixdir)
        code, doc = self._doc(self.m.cmd_unpatch, str(fixdir))
        self.assertEqual(code, 0)
        self.assertEqual(len(doc["missing"]), 1)
        self.assertTrue(doc["missing"][0].startswith(f"{backup.name}: "),
                        doc["missing"])

    # 11. status: not a directory
    def test_status_reports_a_missing_directory(self):
        missing = str(self.base / "nope")
        code, doc = self._doc(self.m.cmd_status, missing)
        self.assertEqual(code, 2)
        self.assertEqual(doc, {"ok": False, "error": f"not a directory: {missing}"})

    # 12. install: the prefix it cannot create
    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "root ignores the permission bits")
    def test_install_reports_a_prefix_it_cannot_create(self):
        proton = self.base / "proton"
        proton.write_text("#!/bin/sh\nexit 0\n")
        os.chmod(proton, 0o755)
        ro = self.base / "ro"
        ro.mkdir()
        self._readonly(ro)
        code, doc = self._doc(self.m.cmd_install, [
            "--game", "G", "--prefix", str(ro / "prefix"), "--installdir", str(self.base),
            "--proton", str(proton), str(self.base / "setup.exe")])
        self.assertEqual(code, 3)
        self.assertTrue(doc["error"].startswith("cannot create prefix: "), doc)

    # 13. install: the installer it cannot find
    def test_install_reports_a_missing_installer(self):
        proton = self.base / "proton"
        proton.write_text("#!/bin/sh\nexit 0\n")
        os.chmod(proton, 0o755)
        missing = str(self.base / "setup.exe")
        code, doc = self._doc(self.m.cmd_install, [
            "--game", "G", "--prefix", str(self.base / "prefix"),
            "--installdir", str(self.base), "--proton", str(proton), missing])
        self.assertEqual(code, 3)
        self.assertEqual(doc, {"ok": False, "error": f"installer not found: {missing}"})

    # 14. install: the proton it cannot start
    def test_install_reports_a_proton_it_cannot_start(self):
        proton = self.base / "proton"
        proton.write_text("#!/bin/sh\nexit 0\n")
        os.chmod(proton, 0o600)
        installer = self.base / "setup.exe"
        installer.write_bytes(b"x")
        code, doc = self._doc(self.m.cmd_install, [
            "--game", "G", "--prefix", str(self.base / "prefix"),
            "--installdir", str(self.base), "--proton", str(proton), str(installer)])
        self.assertEqual(code, 3)
        self.assertTrue(doc["error"].startswith("cannot start installer: "), doc)

    # 15. install: the exit code of the installer
    def test_install_reports_the_exit_code_of_the_installer(self):
        proton = self.base / "proton"
        proton.write_text("#!/bin/sh\nexit 3\n")
        os.chmod(proton, 0o755)
        installer = self.base / "setup.exe"
        installer.write_bytes(b"x")
        code, doc = self._doc(self.m.cmd_install, [
            "--game", "G", "--prefix", str(self.base / "prefix"),
            "--installdir", str(self.base), "--proton", str(proton), str(installer)])
        self.assertEqual(code, 3)
        self.assertEqual(doc["error"], "installer exit 3")
        self.assertEqual(doc["installer"], str(installer))


if __name__ == "__main__":
    unittest.main()
