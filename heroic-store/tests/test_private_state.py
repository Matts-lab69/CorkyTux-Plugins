"""Private-state tests for the GOG auth file, state dir and debug log."""
import importlib.machinery
import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "heroic-store"


def load():
    loader = importlib.machinery.SourceFileLoader("heroic_private", str(SCRIPT))
    spec = importlib.util.spec_from_loader("heroic_private", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


class PrivateStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.state = self.base / "config"
        self.old = (self.m.CONFIG_DIR, self.m.GOGDL_AUTH_JSON)
        self.m.CONFIG_DIR = self.state
        self.m.GOGDL_AUTH_JSON = self.state / "gogdl_auth.json"

    def tearDown(self):
        self.m.CONFIG_DIR, self.m.GOGDL_AUTH_JSON = self.old
        self.tmp.cleanup()

    def test_state_dir_migrates_0755_to_0700(self):
        self.state.mkdir(parents=True)
        os.chmod(self.state, 0o755)
        self.m._ensure_private_dir(self.state)
        self.assertEqual(mode(self.state), 0o700)

    def test_gogdl_auth_file_is_0600_from_open(self):
        self.m._gogdl_auth_file()
        self.assertEqual(mode(self.state), 0o700)
        self.assertEqual(mode(self.m.GOGDL_AUTH_JSON), 0o600)

    def test_debug_log_is_0600_and_replaces_old_mode(self):
        self.state.mkdir(parents=True)
        log = self.state / "sso_debug.log"
        log.write_text("old")
        os.chmod(log, 0o644)
        with self.m._open_private_log(log, truncate=True) as fh:
            fh.write("new")
        self.assertEqual(mode(log), 0o600)
        self.assertEqual(log.read_text(), "new")

    def test_state_helper_does_not_follow_symlinks(self):
        target = self.base / "outside"
        target.mkdir()
        os.chmod(target, 0o755)
        link = self.base / "state"
        os.symlink(target, link)
        self.m._ensure_private_dir(link)
        self.assertEqual(mode(target), 0o755)


if __name__ == "__main__":
    unittest.main()
