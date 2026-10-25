"""_cf_pack_manifest must not leak its cfpack-* temp dir on failure.

Uso: python3 -m unittest tests.test_cf_pack_manifest
"""
import importlib.machinery
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "minecraft-launcher"


def load():
    loader = importlib.machinery.SourceFileLoader("mc_launcher_cfpack", str(SCRIPT))
    spec = importlib.util.spec_from_loader("mc_launcher_cfpack", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class CfPackManifestLeakTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _cfpack_dirs(self):
        return {p for p in Path(tempfile.gettempdir()).iterdir()
                if p.is_dir() and p.name.startswith("cfpack-")}

    def test_no_leak_on_download_failure(self):
        m = self.m
        before = self._cfpack_dirs()

        def fake_cf_get(path, params=None):
            return {"data": [{"id": 1, "downloadUrl": "http://example.invalid/pack.zip"}]}

        def fake_download(url, dest, stage):
            m.die(3, "boom")

        orig_cf_get = m._cf_get
        orig_download = m._download_with_progress
        m._cf_get = fake_cf_get
        m._download_with_progress = fake_download
        try:
            with self.assertRaises(SystemExit):
                m._cf_pack_manifest("123", "")
        finally:
            m._cf_get = orig_cf_get
            m._download_with_progress = orig_download

        after = self._cfpack_dirs()
        leaked = after - before
        self.assertEqual(leaked, set(),
                         f"cfpack temp dirs leaked: {leaked}")