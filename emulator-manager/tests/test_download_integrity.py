import hashlib
import importlib.machinery
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "emulator-manager"


def load():
    loader = importlib.machinery.SourceFileLoader("emulator_manager", str(SCRIPT))
    spec = importlib.util.spec_from_loader("emulator_manager", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class DownloadIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_selected_release_asset_carries_digest_from_same_response(self):
        data = {"assets": [{"name": "Dolphin-x86_64.AppImage",
                            "browser_download_url": "https://download.invalid/dolphin",
                            "digest": "sha256:" + "a" * 64}]}
        with mock.patch.object(self.m, "_github_release", return_value=data):
            selected, error = self.m.find_download_asset("Dolphin")
        self.assertIsNone(error)
        self.assertEqual(selected["digest"], "sha256:" + "a" * 64)
        self.assertEqual(selected["url"], "https://download.invalid/dolphin")

    def test_duckstation_x86_selects_x64_after_arm_assets(self):
        release = _duckstation_release([
            "DuckStation-arm64.AppImage", "DuckStation-armhf.AppImage",
            "DuckStation-x64-SSE2.AppImage", "DuckStation-x64.AppImage",
        ])
        with mock.patch.object(self.m, "_github_release", return_value=release), \
                mock.patch.object(self.m, "get_arch", return_value="x86_64"):
            selected, error = self.m.find_download_asset("DuckStation")
        self.assertIsNone(error)
        self.assertEqual(selected["name"], "DuckStation-x64-SSE2.AppImage")
        self.assertEqual(selected["digest"], "sha256:" + "2" * 64)
        self.assertEqual(selected["url"], "https://download.invalid/duckstation-2")

    def test_architecture_aliases_are_filtered_and_unambiguous_generic_fallback_remains(self):
        names = ["Dolphin-arm64.AppImage", "Dolphin-aarch64.AppImage",
                 "Dolphin-x64.AppImage", "Dolphin-x86_64.AppImage",
                 "Dolphin-amd64.AppImage", "Dolphin-armhf.AppImage",
                 "Dolphin-armv7.AppImage"]
        release = _assets(names)
        for arch, expected in (("x86_64", "Dolphin-x64.AppImage"),
                               ("aarch64", "Dolphin-arm64.AppImage")):
            with self.subTest(arch=arch), \
                    mock.patch.object(self.m, "_github_release", return_value=release), \
                    mock.patch.object(self.m, "get_arch", return_value=arch):
                selected, error = self.m.find_download_asset("Dolphin")
            self.assertIsNone(error)
            self.assertEqual(selected["name"], expected)
            selected_index = names.index(expected)
            self.assertEqual(selected["digest"],
                             "sha256:" + str(selected_index) * 64)

        generic = _assets(["Dolphin.AppImage"])
        with mock.patch.object(self.m, "_github_release", return_value=generic), \
                mock.patch.object(self.m, "get_arch", return_value="aarch64"):
            selected, error = self.m.find_download_asset("Dolphin")
        self.assertIsNone(error)
        self.assertEqual(selected["name"], "Dolphin.AppImage")

    def test_each_supported_architecture_alias_is_selectable(self):
        cases = (("x86_64", "Dolphin-x64.AppImage", "Dolphin-arm64.AppImage"),
                 ("x86_64", "Dolphin-x86_64.AppImage", "Dolphin-armhf.AppImage"),
                 ("x86_64", "Dolphin-amd64.AppImage", "Dolphin-armv7.AppImage"),
                 ("aarch64", "Dolphin-arm64.AppImage", "Dolphin-x64.AppImage"),
                 ("aarch64", "Dolphin-aarch64.AppImage", "Dolphin-amd64.AppImage"))
        for arch, expected, rejected in cases:
            with self.subTest(arch=arch, expected=expected):
                release = _assets([rejected, expected])
                with mock.patch.object(self.m, "_github_release", return_value=release), \
                        mock.patch.object(self.m, "get_arch", return_value=arch):
                    selected, error = self.m.find_download_asset("Dolphin")
                self.assertIsNone(error)
                self.assertEqual(selected["name"], expected)
                self.assertEqual(selected["digest"], release["assets"][1]["digest"])

    def test_ambiguous_unmarked_arch_assets_are_not_chosen(self):
        release = _assets(["Dolphin-one.AppImage", "Dolphin-two.AppImage"])
        with mock.patch.object(self.m, "_github_release", return_value=release), \
                mock.patch.object(self.m, "get_arch", return_value="aarch64"):
            selected, error = self.m.find_download_asset("Dolphin")
        self.assertIsNone(selected)
        self.assertIn("No aarch64 AppImage", error)

    def test_verified_download_replaces_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "app.AppImage"
            dest.write_bytes(b"old")
            content = b"new verified appimage"
            with mock.patch("urllib.request.urlopen", return_value=_Response(content)):
                result = self.m._download_appimage(
                    "https://download.invalid/app", dest,
                    "sha256:" + hashlib.sha256(content).hexdigest())
            self.assertTrue(result["verified"])
            self.assertEqual(dest.read_bytes(), content)
            self.assertEqual(list(Path(directory).iterdir()), [dest])

    def test_checksum_mismatch_keeps_previous_image_and_cleans_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "app.AppImage"
            dest.write_bytes(b"old")
            with mock.patch("urllib.request.urlopen", return_value=_Response(b"tampered")):
                result = self.m._download_appimage(
                    "https://download.invalid/app", dest, "sha256:" + "0" * 64)
            self.assertFalse(result["ok"])
            self.assertIn("checksum mismatch", result["message"].lower())
            self.assertEqual(dest.read_bytes(), b"old")
            self.assertEqual(list(Path(directory).iterdir()), [dest])

    def test_missing_digest_reports_unverified_and_keeps_install_behavior(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "app.AppImage"
            with mock.patch("urllib.request.urlopen", return_value=_Response(b"app")):
                result = self.m._download_appimage("https://download.invalid/app", dest, None)
            self.assertTrue(result["ok"])
            self.assertFalse(result["verified"])
            self.assertIn("no official checksum", result["warning"].lower())

    def test_malformed_digest_is_error(self):
        for digest in ("sha256:nope", "sha1:" + "a" * 40, "sha512:" + "a" * 64):
            with self.subTest(digest=digest):
                with self.assertRaises(ValueError):
                    self.m._parse_official_digest(digest)

    def test_missing_digest_is_not_fetched_again(self):
        release = {"assets": [{"name": "Dolphin.AppImage",
                               "browser_download_url": "https://download.invalid/app",
                               "digest": None}]}
        with mock.patch.object(self.m, "_github_release", return_value=release) as fetch:
            selected, _ = self.m.find_download_asset("Dolphin")
            self.assertIsNone(selected["digest"])
            self.assertEqual(fetch.call_count, 1)


class _Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        data, self.data = self.data, b""
        return data


def _assets(names):
    return {"assets": [{"name": name,
                        "browser_download_url": f"https://download.invalid/{index}",
                        "digest": "sha256:" + str(index) * 64}
                       for index, name in enumerate(names)]}


def _duckstation_release(names):
    release = _assets(names)
    for index, asset in enumerate(release["assets"]):
        asset["browser_download_url"] = f"https://download.invalid/duckstation-{index}"
    return release


if __name__ == "__main__":
    unittest.main()
