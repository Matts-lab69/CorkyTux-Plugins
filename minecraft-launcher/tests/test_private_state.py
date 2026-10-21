"""Private-state tests for accounts.json, the CurseForge key and launch logs.

Uso: python3 -m unittest tests.test_private_state
"""
import importlib.machinery
import importlib.util
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "minecraft-launcher"


def load():
    loader = importlib.machinery.SourceFileLoader("mc_launcher_private", str(SCRIPT))
    spec = importlib.util.spec_from_loader("mc_launcher_private", loader)
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
        self.state = self.base / "config" / "plugins" / "minecraft-launcher"
        self.old = (self.m.CONFIG_DIR, self.m.ACCOUNTS_FILE,
                    self.m.CURSE_JSON, self.m.LOGS_DIR)
        self.m.CONFIG_DIR = self.state
        self.m.ACCOUNTS_FILE = self.state / "accounts.json"
        self.m.CURSE_JSON = self.state / "curseforge.json"
        self.m.LOGS_DIR = self.base / "logs"

    def tearDown(self):
        (self.m.CONFIG_DIR, self.m.ACCOUNTS_FILE,
         self.m.CURSE_JSON, self.m.LOGS_DIR) = self.old
        self.tmp.cleanup()

    def test_save_accounts_creates_0700_dir_and_0600_file_from_open(self):
        accounts = [{"id": "abc", "name": "Player", "access_token": "secret"}]
        self.m._save_accounts(accounts)
        self.assertEqual(mode(self.m.CONFIG_DIR), 0o700)
        self.assertEqual(mode(self.m.ACCOUNTS_FILE), 0o600)
        self.assertEqual(json.loads(self.m.ACCOUNTS_FILE.read_text()), accounts)

    def test_load_accounts_migrates_existing_0755_dir_and_0644_file(self):
        self.m.CONFIG_DIR.mkdir(parents=True)
        os.chmod(self.m.CONFIG_DIR, 0o755)
        accounts = [{"id": "abc", "name": "Player", "access_token": "secret"}]
        self.m.ACCOUNTS_FILE.write_text(json.dumps(accounts))
        os.chmod(self.m.ACCOUNTS_FILE, 0o644)

        self.assertEqual(self.m._load_accounts(), accounts)
        self.assertEqual(mode(self.m.CONFIG_DIR), 0o700)
        self.assertEqual(mode(self.m.ACCOUNTS_FILE), 0o600)

    def test_curse_key_is_0600_from_creation_and_overwrites_old_mode(self):
        self.state.mkdir(parents=True)
        self.m.CURSE_JSON.write_text('{"api_key": "old"}')
        os.chmod(self.m.CURSE_JSON, 0o644)

        self.m._write_private_json(self.m.CURSE_JSON, {"api_key": "new"})
        self.assertEqual(mode(self.m.CURSE_JSON), 0o600)
        self.assertEqual(json.loads(self.m.CURSE_JSON.read_text()),
                         {"api_key": "new"})

    def test_launch_log_is_0600_and_replaces_old_mode(self):
        self.m.LOGS_DIR.mkdir(parents=True)
        os.chmod(self.m.LOGS_DIR, 0o755)
        log = self.m.LOGS_DIR / "Minecraft-test.log"
        log.write_text("old")
        os.chmod(log, 0o644)

        with self.m._open_private_log(log) as fh:
            fh.write("--accessToken secret")
        self.assertEqual(mode(self.m.LOGS_DIR), 0o700)
        self.assertEqual(mode(log), 0o600)
        self.assertEqual(log.read_text(), "--accessToken secret")

    def test_harden_does_not_follow_symlinks(self):
        self.state.mkdir(parents=True)
        target = self.base / "outside.json"
        target.write_text("{}")
        os.chmod(target, 0o644)
        link = self.state / "accounts.json"
        os.symlink(target, link)
        self.m._harden_private_file(link)
        self.assertEqual(mode(target), 0o644)
        self.assertTrue(link.is_symlink())


if __name__ == "__main__":
    unittest.main()
