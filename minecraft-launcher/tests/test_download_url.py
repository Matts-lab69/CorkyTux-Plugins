"""Download URLs must be percent-encoded once, before the request leaves.

Uso: python3 -m unittest tests.test_download_url
"""
import importlib.machinery
import importlib.util
import io
import tempfile
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "minecraft-launcher"

CF_SPACE = ("https://mediafilez.forgecdn.net/files/2835/526/"
            "OpenTerrainGenerator-1.12.2 - v8.3.jar")
CF_SPACE_OK = ("https://mediafilez.forgecdn.net/files/2835/526/"
               "OpenTerrainGenerator-1.12.2%20-%20v8.3.jar")


def load():
    loader = importlib.machinery.SourceFileLoader("mc_launcher_urls", str(SCRIPT))
    spec = importlib.util.spec_from_loader("mc_launcher_urls", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class DownloadUrlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_space_in_the_path(self):
        self.assertEqual(self.m._quote_download_url(CF_SPACE), CF_SPACE_OK)

    def test_plus_is_encoded(self):
        self.assertEqual(
            self.m._quote_download_url("https://cdn.example/a+b.jar"),
            "https://cdn.example/a%2Bb.jar")

    def test_brackets_are_encoded(self):
        self.assertEqual(
            self.m._quote_download_url("https://cdn.example/mod[1].jar"),
            "https://cdn.example/mod%5B1%5D.jar")

    def test_hash_is_encoded(self):
        self.assertEqual(
            self.m._quote_download_url("https://cdn.example/mod#1.jar"),
            "https://cdn.example/mod%231.jar")

    def test_encoded_question_mark_is_not_doubled(self):
        self.assertEqual(
            self.m._quote_download_url("https://cdn.example/mod%3F1.jar"),
            "https://cdn.example/mod%3F1.jar")

    def test_space_in_the_query(self):
        self.assertEqual(
            self.m._quote_download_url("https://cdn.example/dl?file=My Mod.jar"),
            "https://cdn.example/dl?file=My%20Mod.jar")

    def test_unicode(self):
        self.assertEqual(
            self.m._quote_download_url("https://cdn.example/Modo espa\u00f1ol \u00f1.jar"),
            "https://cdn.example/Modo%20espa%C3%B1ol%20%C3%B1.jar")

    def test_already_encoded_is_unchanged(self):
        self.assertEqual(self.m._quote_download_url(CF_SPACE_OK), CF_SPACE_OK)

    def test_plain_url_is_unchanged(self):
        url = "https://cdn.example/plain-1.0.jar"
        self.assertEqual(self.m._quote_download_url(url), url)

    def test_idempotent(self):
        for url in (CF_SPACE, CF_SPACE_OK, "https://cdn.example/a+b.jar",
                    "https://cdn.example/mod#1.jar",
                    "https://cdn.example/Modo espa\u00f1ol \u00f1.jar",
                    "https://cdn.example/dl?file=My Mod.jar"):
            once = self.m._quote_download_url(url)
            self.assertEqual(self.m._quote_download_url(once), once, url)

    def test_relative_or_empty_is_unchanged(self):
        for url in ("", "/files/2835/526/a b.jar", "not a url"):
            self.assertEqual(self.m._quote_download_url(url), url)

    def test_download_helper_encodes_before_the_request(self):
        seen = {}

        def fake(req, timeout=None):
            seen["url"] = req.full_url
            seen["headers"] = req.header_items()
            raise urllib.error.URLError("no network in this test")

        real = urllib.request.urlopen
        urllib.request.urlopen = fake
        try:
            with tempfile.TemporaryDirectory() as tmp:
                dest = Path(tmp) / "out.jar"
                with redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit) as ctx:
                        self.m._download_with_progress(CF_SPACE, dest, "probe")
                self.assertEqual(ctx.exception.code, 3)
                self.assertFalse(dest.exists())
        finally:
            urllib.request.urlopen = real
        self.assertEqual(seen["url"], CF_SPACE_OK)
        self.assertEqual(seen["headers"], [("User-agent", self.m.MODRINTH_UA)])


if __name__ == "__main__":
    unittest.main()
