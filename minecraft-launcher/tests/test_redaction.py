"""Redaction tests: no secret may reach a log, a message or a protocol event.

Un test por patron, mas los tests de integracion (argv, die).

Uso: python3 -m unittest tests.test_redaction
"""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "minecraft-launcher"


def load():
    loader = importlib.machinery.SourceFileLoader("mc_launcher_redaction", str(SCRIPT))
    spec = importlib.util.spec_from_loader("mc_launcher_redaction", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class RedactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def red(self, text):
        return self.m._redact_secrets(text)

    # 1. --accessToken <value>
    def test_cli_access_token_flag_is_redacted(self):
        out = self.red("java -jar game.jar --accessToken eyJhbGciOi.superSecret")
        self.assertNotIn("eyJhbGciOi.superSecret", out)
        self.assertIn("--accessToken " + self.m.REDACTED, out)

    # 2. --password <value>
    def test_cli_password_flag_is_redacted(self):
        out = self.red("minecraft-launcher ely-auth --password hunter2")
        self.assertNotIn("hunter2", out)
        self.assertIn("--password " + self.m.REDACTED, out)

    # 3. --api-key <value>
    def test_cli_api_key_flag_is_redacted(self):
        out = self.red("curse-auth-config --api-key $2a$10$abc")
        self.assertNotIn("$2a$10$abc", out)
        self.assertIn("--api-key " + self.m.REDACTED, out)

    # 4. JSON token fields
    def test_json_token_fields_are_redacted(self):
        out = self.red('{"accessToken": "abc123", "clientToken": "def456", '
                       '"refresh_token": "ghi789", "identityToken": "jkl012"}')
        for secret in ("abc123", "def456", "ghi789", "jkl012"):
            self.assertNotIn(secret, out)
        self.assertEqual(out.count(self.m.REDACTED), 4)
        bare = self.red("login failed: accessToken=mno345")
        self.assertNotIn("mno345", bare)
        self.assertIn(self.m.REDACTED, bare)

    # 5. JSON secret fields
    def test_json_secret_fields_are_redacted(self):
        out = self.red('{"password": "hunter2", "api_key": "key-123", '
                       '"user_code": "ABCD-EFGH", "device_code": "dc-999"}')
        for secret in ("hunter2", "key-123", "ABCD-EFGH", "dc-999"):
            self.assertNotIn(secret, out)
        self.assertEqual(out.count(self.m.REDACTED), 4)
        bare = self.red("request failed: password=hunter3 api_key=key-456")
        self.assertNotIn("hunter3", bare)
        self.assertNotIn("key-456", bare)

    # 6. Authorization: Bearer <token>
    def test_authorization_bearer_header_is_redacted(self):
        out = self.red("Authorization: Bearer eyJraWQiOiJzZWNyZXQ")
        self.assertNotIn("eyJraWQiOiJzZWNyZXQ", out)
        self.assertIn("Bearer " + self.m.REDACTED, out)

    # 7. x-api-key header
    def test_x_api_key_header_is_redacted(self):
        out = self.red("x-api-key: $2a$10$abcdef")
        self.assertNotIn("$2a$10$abcdef", out)
        self.assertIn("x-api-key: " + self.m.REDACTED, out)

    # 8. Xbox RpsTicket and XBL3.0 identity token
    def test_xbox_tokens_are_redacted(self):
        rps = self.red('{"RpsTicket": "d=microsoft_access_token"}')
        self.assertNotIn("microsoft_access_token", rps)
        xbl = self.red('{"identityToken": "XBL3.0 x=uhs_value;xsts_token"}')
        self.assertNotIn("xsts_token", xbl)
        self.assertNotIn("uhs_value", xbl)

    # argv: the flag stays visible, its value does not
    def test_redact_argv_hides_the_value_of_a_secret_flag(self):
        argv = ["/usr/bin/java", "-jar", "game.jar", "--accessToken", "secret-token",
                "--username", "Player", "--uuid", "1234"]
        out = self.m._redact_argv(argv)
        self.assertNotIn("secret-token", " ".join(out))
        self.assertIn("--accessToken", out)
        self.assertIn("Player", out)
        self.assertIn("1234", out)

    # argv: --flag=value form
    def test_redact_argv_handles_equals_form(self):
        out = self.m._redact_argv(["--password=hunter2", "--accessToken=abc"])
        self.assertNotIn("hunter2", " ".join(out))
        self.assertNotIn("abc", " ".join(out))

    # the log header path: what cmd_launch writes
    def test_launch_command_line_is_redacted(self):
        command = ["/usr/bin/java", "-jar", "game.jar", "--accessToken", "tok-123",
                   "--username", "Player"]
        header = f"# cmd: {' '.join(self.m._redact_argv(command))}"
        self.assertNotIn("tok-123", header)
        self.assertIn(self.m.REDACTED, header)

    # die(): the message is redacted before it is emitted
    def test_die_redacts_the_error_message(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit):
                self.m.die(3, "login failed: accessToken=abc123 password=hunter2")
        payload = json.loads(buf.getvalue().strip())
        self.assertNotIn("abc123", payload["message"])
        self.assertNotIn("hunter2", payload["message"])

    # the device-code event must keep the code: the user has to type it
    def test_device_code_event_is_not_redacted(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.m.emit({"type": "device_code", "user_code": "ABCD-EFGH"})
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(payload["user_code"], "ABCD-EFGH")


if __name__ == "__main__":
    unittest.main()
