"""The Ely.by password must travel on stdin, never in the command line.

Uso: python3 -m unittest tests.test_ely_password
"""
import importlib.machinery
import importlib.util
import io
import json
import sys
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "minecraft-launcher"

SECRET = "s3cr3t-p4ssw0rd"


def load():
    loader = importlib.machinery.SourceFileLoader("mc_launcher_ely", str(SCRIPT))
    spec = importlib.util.spec_from_loader("mc_launcher_ely", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class ElyPasswordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def setUp(self):
        # An unreachable URL: the request fails at once, with no network.
        self.old_url = self.m.ELY_AUTH_URL
        self.m.ELY_AUTH_URL = "http://127.0.0.1:9/auth"
        self.old_request = self.m._ely_request

    def tearDown(self):
        self.m.ELY_AUTH_URL = self.old_url
        self.m._ely_request = self.old_request

    def _args(self, **kwargs):
        base = {
            "username": "player",
            "password": "",
            "password_stdin": True,
            "probe": False,
        }
        base.update(kwargs)
        return types.SimpleNamespace(**base)

    def test_the_password_is_read_from_stdin(self):
        captured = []

        def fake_request(url, payload):
            captured.append(payload)
            return 401, {"errorMessage": "Invalid credentials"}

        self.m._ely_request = fake_request
        out, err = io.StringIO(), io.StringIO()
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(SECRET + "\n")
        try:
            with redirect_stdout(out), redirect_stderr(err):
                with self.assertRaises(SystemExit):
                    self.m.cmd_ely_auth(self._args())
        finally:
            sys.stdin = old_stdin
        self.assertTrue(captured, "the plugin must send the request")
        self.assertEqual(captured[0]["password"], SECRET)
        self.assertNotIn(SECRET, out.getvalue())
        self.assertNotIn(SECRET, err.getvalue())

    def test_the_password_never_reaches_the_output(self):
        out, err = io.StringIO(), io.StringIO()
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(SECRET + "\n")
        try:
            with redirect_stdout(out), redirect_stderr(err):
                with self.assertRaises(SystemExit):
                    self.m.cmd_ely_auth(self._args())
        finally:
            sys.stdin = old_stdin
        self.assertNotIn(SECRET, out.getvalue())
        self.assertNotIn(SECRET, err.getvalue())

    def test_a_password_in_the_command_line_is_refused(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                self.m.cmd_ely_auth(self._args(password=SECRET, password_stdin=False))
        self.assertEqual(cm.exception.code, 2)
        text = out.getvalue() + err.getvalue()
        self.assertNotIn(SECRET, text, "the refused password must not be echoed")
        self.assertIn("stdin", text.lower(), "the error must say how to send it")

    def test_the_probe_answers_what_the_launcher_needs(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.m.cmd_ely_auth(self._args(probe=True))
        doc = json.loads(out.getvalue().strip())
        self.assertTrue(doc["ok"])
        self.assertTrue(doc["password_stdin"])
        self.assertNotIn(SECRET, out.getvalue())


class ElyProbeCliTests(unittest.TestCase):
    """The real parser has to accept the probe with no credentials.

    The launcher calls `ely-auth --probe` before it has a username or a
    password. A required --username turned that probe into a usage error,
    and the launcher answered "the installed Ely.by plugin is too old" on a
    plugin that was in fact new.
    """

    def _run(self, argv, stdin=""):
        import os
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as home:
            return subprocess.run(
                [sys.executable, str(SCRIPT), *argv],
                input=stdin,
                capture_output=True,
                text=True,
                env={**os.environ, "HOME": home},
                timeout=60,
            )

    def test_the_probe_runs_with_no_username(self):
        proc = self._run(["ely-auth", "--probe"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        doc = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertTrue(doc.get("ok"), doc)
        self.assertIs(doc.get("password_stdin"), True)

    def test_a_sign_in_without_a_username_is_still_refused(self):
        proc = self._run(["ely-auth", "--password-stdin"])
        self.assertEqual(proc.returncode, 2)
        doc = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(doc.get("type"), "error")
        self.assertIn("username and password required", doc.get("message", ""))


if __name__ == "__main__":
    unittest.main()
