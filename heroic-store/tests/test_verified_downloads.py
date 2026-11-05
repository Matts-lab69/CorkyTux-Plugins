import importlib.machinery
import importlib.util
import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent.parent / "heroic-store"


def load():
    loader = importlib.machinery.SourceFileLoader("heroic_store", str(SCRIPT))
    spec = importlib.util.spec_from_loader("heroic_store", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class VerifiedDownloads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_managed_tools_pin_release_urls_and_digests(self):
        self.assertEqual(self.m.TOOL_RELEASES["legendary"]["url"],
                         "https://github.com/legendary-gl/legendary/releases/download/0.21.1/legendary_linux_x64")
        self.assertEqual(self.m.TOOL_RELEASES["gogdl"]["sha256"],
                         "2aa2b59c83d3bfbe7b60ead91c6297b263b5d1e6c233a04b7409bafe26738f02")

    def test_path_tools_do_not_skip_pinned_managed_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            events = []
            downloaded = []

            def fake_download(url, dest, expected):
                downloaded.append((url, Path(dest), expected))
                Path(dest).write_bytes(b"verified fixture")

            with mock.patch.object(self.m, "CONFIG_DIR", config), \
                    mock.patch("platform.machine", return_value="x86_64"), \
                    mock.patch.object(self.m.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"), \
                    mock.patch.object(self.m, "_download_verified", side_effect=fake_download), \
                    mock.patch.object(self.m, "_sha256_file", side_effect=lambda path: self.m.TOOL_RELEASES[Path(path).name]["sha256"]), \
                    mock.patch.object(self.m, "emit", events.append):
                self.m.cmd_setup(None)
                self.assertEqual(self.m._find_bin("legendary"), str(config / "bin" / "legendary"))
            self.assertEqual(len(downloaded), 2)
            self.assertTrue(any(event.get("type") == "done" for event in events))

    def test_system_fallback_is_reported_unverified(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            managed = config / "bin" / "gogdl"
            managed.parent.mkdir(parents=True)
            managed.write_bytes(b"invalid managed executable")
            fallback = Path(directory) / "gogdl-system"
            fallback.write_bytes(b"system executable")
            fallback.chmod(0o755)
            with mock.patch.object(self.m, "CONFIG_DIR", config), \
                    mock.patch.object(self.m.shutil, "which", return_value=str(fallback)):
                selected = self.m._find_bin("gogdl")
                self.assertEqual(selected, str(fallback))
                self.assertEqual(self.m._tool_integrity("gogdl", selected),
                                 "system-fallback-unverified")

    def test_invalid_managed_binary_on_path_is_not_used_or_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            managed = config / "bin" / "legendary"
            managed.parent.mkdir(parents=True)
            managed.write_bytes(b"tampered managed binary")
            managed.chmod(0o755)
            with mock.patch.object(self.m, "CONFIG_DIR", config), \
                    mock.patch.object(self.m.shutil, "which", return_value=str(managed)):
                selected = self.m._find_bin("legendary")
                self.assertEqual(selected, "")
                self.assertEqual(self.m._tool_integrity("legendary", selected), "invalid-managed")
                with mock.patch.object(self.m, "emit", lambda _event: None):
                    with self.assertRaises(SystemExit):
                        self.m._require_binary(selected, "legendary")

    def test_any_setup_hash_failure_aborts_after_another_tool_is_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            bindir = config / "bin"
            bindir.mkdir(parents=True)
            (bindir / "legendary").write_bytes(b"already verified")
            (bindir / "legendary").chmod(0o755)
            (bindir / "gogdl").write_bytes(b"old gogdl")
            events = []

            def file_hash(path):
                return self.m.TOOL_RELEASES["legendary"]["sha256"] if Path(path).name == "legendary" else "old"

            with mock.patch.object(self.m, "CONFIG_DIR", config), \
                    mock.patch("platform.machine", return_value="x86_64"), \
                    mock.patch.object(self.m.shutil, "which", return_value=None), \
                    mock.patch.object(self.m, "_sha256_file", side_effect=file_hash), \
                    mock.patch.object(self.m, "_download_verified", side_effect=ValueError("SHA-256 mismatch")), \
                    mock.patch.object(self.m, "emit", events.append):
                with self.assertRaises(SystemExit) as raised:
                    self.m.cmd_setup(None)
            self.assertEqual(raised.exception.code, 3)
            self.assertEqual((bindir / "gogdl").read_bytes(), b"old gogdl")
            self.assertFalse(any(event.get("type") == "done" and event.get("ok") for event in events))
            self.assertTrue(any(event.get("type") == "error" for event in events))

    def test_download_checksum_mismatch_preserves_destination_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "tool"
            dest.write_bytes(b"old verified binary")
            response = mock.MagicMock()
            response.__enter__.return_value.read.side_effect = [b"bad", b""]
            with mock.patch("urllib.request.urlopen", return_value=response):
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    self.m._download_verified("https://example.invalid/tool", dest,
                                              "0" * 64)
            self.assertEqual(dest.read_bytes(), b"old verified binary")
            self.assertEqual(list(Path(directory).iterdir()), [dest])

    def test_umu_archive_digest_checked_before_extract(self):
        with tempfile.TemporaryDirectory() as directory:
            umu_dir = Path(directory) / "umu"
            umu_dir.mkdir()
            (umu_dir / "umu").write_bytes(b"old verified runner")
            (umu_dir / ".verified-install.json").write_text("old manifest")
            events = []
            with mock.patch.object(self.m, "UMU_DIR", umu_dir), \
                    mock.patch.object(self.m, "UMU_BIN", umu_dir / "umu"), \
                    mock.patch.object(self.m, "UMU_MANIFEST", umu_dir / ".verified-install.json"), \
                    mock.patch.object(self.m, "_umu_bin", return_value=""), \
                    mock.patch("urllib.request.urlopen", return_value=_Response(b"invalid")), \
                    mock.patch.object(self.m, "emit", events.append):
                with self.assertRaises(SystemExit):
                    self.m.cmd_umu_setup(None)
            self.assertEqual((umu_dir / "umu").read_bytes(), b"old verified runner")
            self.assertEqual((umu_dir / ".verified-install.json").read_text(), "old manifest")
            self.assertFalse(list(umu_dir.glob("umu-*.tar")))
            self.assertTrue(any(e.get("type") == "error" for e in events))

    def test_umu_official_layout_installs_exact_runner_and_ignores_safe_alias(self):
        payload = _umu_fixture()
        with tempfile.TemporaryDirectory() as directory:
            umu_dir = Path(directory) / "managed"
            events = []
            with mock.patch.object(self.m, "UMU_DIR", umu_dir), \
                    mock.patch.object(self.m, "UMU_BIN", umu_dir / "umu"), \
                    mock.patch.object(self.m, "UMU_MANIFEST", umu_dir / ".verified-install.json"), \
                    mock.patch.object(self.m, "UMU_RELEASE", {
                        "url": "https://example.invalid/umu.tar",
                        "sha256": hashlib.sha256(payload).hexdigest()}), \
                    mock.patch.object(self.m, "_umu_bin", return_value=""), \
                    mock.patch("shutil.which", return_value="/usr/bin/umu"), \
                    mock.patch("urllib.request.urlopen", return_value=_Response(payload)), \
                    mock.patch.object(self.m, "emit", events.append):
                self.m.cmd_umu_setup(None)
            self.assertEqual((umu_dir / "umu").read_bytes(), b"official runner fixture")
            self.assertTrue((umu_dir / ".verified-install.json").is_file())
            self.assertTrue(any(e.get("type") == "done" and e.get("ok") for e in events))

    def test_umu_archive_path_and_escaping_link_are_rejected(self):
        for payload in (_tar_with_path("../escape", b"bad"),
                        _tar_with_link("umu/umu_run.py", "../../escape")):
            with self.subTest(payload=len(payload)), tempfile.TemporaryDirectory() as directory:
                archive = Path(directory) / "bad.tar"
                archive.write_bytes(payload)
                with self.assertRaises(ValueError):
                    self.m._safe_extract_tar(archive, Path(directory) / "extract")

    def test_invalid_managed_umu_on_path_is_not_verified_or_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            umu_dir = Path(directory) / "umu"
            umu_dir.mkdir(mode=0o700)
            umu_bin = umu_dir / "umu"
            umu_bin.write_bytes(b"tampered umu")
            umu_bin.chmod(0o755)
            manifest = umu_dir / ".verified-install.json"
            manifest.write_text("{}")
            manifest.chmod(0o600)
            events = []
            with mock.patch.object(self.m, "UMU_DIR", umu_dir), \
                    mock.patch.object(self.m, "UMU_BIN", umu_bin), \
                    mock.patch.object(self.m, "UMU_MANIFEST", manifest), \
                    mock.patch("shutil.which", return_value=str(umu_bin)), \
                    mock.patch.object(self.m, "emit", events.append):
                self.assertEqual(self.m._umu_bin(), "")
                self.m.cmd_umu_status(None)
            status = events[0]
            self.assertFalse(status["available"])
            self.assertFalse(status["verified"])
            self.assertEqual(status["path"], "")
            self.assertEqual(status["integrity"], "invalid-managed")

    def test_non_object_umu_manifest_is_invalid_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = root / "umu"
            runner.write_bytes(b"runner")
            runner.chmod(0o755)
            manifest = root / ".verified-install.json"
            manifest.write_text("[]")
            manifest.chmod(0o600)
            with mock.patch.object(self.m, "UMU_DIR", root), \
                    mock.patch.object(self.m, "UMU_BIN", runner), \
                    mock.patch.object(self.m, "UMU_MANIFEST", manifest):
                self.assertFalse(self.m._umu_managed_valid())

    def test_valid_managed_umu_wins_over_external_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            umu_dir = Path(directory) / "umu"
            events = []
            with mock.patch.object(self.m, "UMU_DIR", umu_dir), \
                    mock.patch.object(self.m, "UMU_BIN", umu_dir / "umu"), \
                    mock.patch.object(self.m, "_umu_managed_valid", return_value=True), \
                    mock.patch("shutil.which", return_value="/usr/bin/umu"), \
                    mock.patch.object(self.m, "emit", events.append):
                self.assertEqual(self.m._umu_bin(), str(umu_dir / "umu"))
                self.m.cmd_umu_status(None)
            self.assertTrue(events[0]["verified"])
            self.assertEqual(events[0]["integrity"], "verified")

    def test_external_umu_fallback_is_allowed_but_unverified(self):
        with tempfile.TemporaryDirectory() as directory:
            umu_dir = Path(directory) / "umu"
            external = Path(directory) / "system-umu"
            external.write_bytes(b"system runner")
            external.chmod(0o755)
            events = []
            with mock.patch.object(self.m, "UMU_DIR", umu_dir), \
                    mock.patch.object(self.m, "UMU_BIN", umu_dir / "umu"), \
                    mock.patch.object(self.m, "_umu_managed_valid", return_value=False), \
                    mock.patch("shutil.which", return_value=str(external)), \
                    mock.patch.object(self.m, "emit", events.append):
                self.assertEqual(self.m._umu_bin(), str(external))
                self.m.cmd_umu_status(None)
            self.assertTrue(events[0]["available"])
            self.assertFalse(events[0]["verified"])
            self.assertEqual(events[0]["integrity"], "external runner; unverified")

    def test_pinned_sha256_digests_have_correct_hex_lengths(self):
        # Every pinned SHA-256 must be exactly 64 lowercase hex digits.
        hex_chars = set("0123456789abcdef")
        for name, release in self.m.TOOL_RELEASES.items():
            digest = release["sha256"]
            self.assertEqual(len(digest), 64,
                             f"TOOL_RELEASES[{name!r}]['sha256'] must be 64 hex chars")
            self.assertTrue(set(digest) <= hex_chars,
                            f"TOOL_RELEASES[{name!r}]['sha256'] must be lowercase hex")
        umu_digest = self.m.UMU_RELEASE["sha256"]
        self.assertEqual(len(umu_digest), 64,
                         "UMU_RELEASE['sha256'] must be 64 hex chars")
        self.assertTrue(set(umu_digest) <= hex_chars,
                        "UMU_RELEASE['sha256'] must be lowercase hex")


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


def _tar_with_path(name, data):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        info = tarfile.TarInfo(name)
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    return output.getvalue()


def _umu_fixture():
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        info = tarfile.TarInfo("umu")
        info.type = tarfile.DIRTYPE
        archive.addfile(info)
        runner = b"official runner fixture"
        info = tarfile.TarInfo("umu/umu-run")
        info.mode = 0o744
        info.size = len(runner)
        archive.addfile(info, io.BytesIO(runner))
        alias = tarfile.TarInfo("umu/umu_run.py")
        alias.type = tarfile.SYMTYPE
        alias.linkname = "umu-run"
        archive.addfile(alias)
    return output.getvalue()


def _tar_with_link(name, target):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        info = tarfile.TarInfo(name)
        info.type = tarfile.SYMTYPE
        info.linkname = target
        archive.addfile(info)
    return output.getvalue()


if __name__ == "__main__":
    unittest.main()
