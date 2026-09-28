"""Tests sin red del update atomico de mods (fase 1.3b).

Cada mod se descarga a `<nombre>.corky-part` y solo al completar se hace
os.replace sobre el destino: si la descarga falla, el jar anterior queda
intacto (tambien en update in-place, dest == old).

Uso: python3 tests/test_mod_update.py (stdlib, sin red).
"""
import importlib.machinery
import importlib.util
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent.parent / "minecraft-launcher"


def load():
    loader = importlib.machinery.SourceFileLoader("mc_launcher", str(SCRIPT))
    spec = importlib.util.spec_from_loader("mc_launcher", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _ns(mc_dir, fname="viejo.jar", force=True):
    return types.SimpleNamespace(addon_type="mods", file=fname,
                                 mc_version="1.21", loader="fabric",
                                 force=force, mc_dir=str(mc_dir))


def _latest(fname="nuevo.jar", vid="v2"):
    return [{"id": vid, "version_number": "2.0", "loaders": ["fabric"],
             "game_versions": ["1.21"],
             "files": [{"filename": fname, "primary": True,
                        "url": "https://x/y.jar"}]}]


class AtomicUpdate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _env(self, tmp, fname="viejo.jar"):
        mods = Path(tmp) / "mods"
        mods.mkdir(parents=True)
        (mods / fname).write_bytes(b"jar-viejo" * 500)
        (mods / (fname + ".corky.json")).write_text(json.dumps(
            {"project_id": "pid1", "version_id": "v1",
             "version_number": "1.0", "title": "M"}))
        return mods

    def test_mismo_nombre_fallo_conserva_jar(self):
        with tempfile.TemporaryDirectory() as tmp:
            mods = self._env(tmp)
            events = []
            with mock.patch.object(self.m, "_mr_project_versions",
                                    return_value=_latest("viejo.jar")), \
                 mock.patch.object(self.m, "_download_with_progress",
                                    side_effect=RuntimeError("red")), \
                 mock.patch.object(self.m, "emit", events.append):
                with self.assertRaises(SystemExit):
                    self.m.cmd_mod_update(_ns(tmp))
            self.assertEqual((mods / "viejo.jar").read_bytes(), b"jar-viejo" * 500)
            self.assertFalse((mods / "viejo.jar.corky-part").exists())
            rec = json.loads((mods / "viejo.jar.corky.json").read_text())
            self.assertEqual(rec["version_id"], "v1")

    def test_mismo_nombre_exito_reemplaza(self):
        with tempfile.TemporaryDirectory() as tmp:
            mods = self._env(tmp)
            events = []
            def fake_dl(url, dest, stage):
                Path(dest).write_bytes(b"jar-nuevo" * 500)
            with mock.patch.object(self.m, "_mr_project_versions",
                                    return_value=_latest("viejo.jar")), \
                 mock.patch.object(self.m, "_download_with_progress",
                                    side_effect=fake_dl), \
                 mock.patch.object(self.m, "emit", events.append):
                self.m.cmd_mod_update(_ns(tmp))
            self.assertEqual((mods / "viejo.jar").read_bytes(), b"jar-nuevo" * 500)
            self.assertFalse((mods / "viejo.jar.corky-part").exists())
            rec = json.loads((mods / "viejo.jar.corky.json").read_text())
            self.assertEqual((rec["version_id"], rec["version_number"]), ("v2", "2.0"))
            done = [e for e in events if e.get("type") == "done"][-1]
            self.assertTrue(done["updated"])

    def test_nombre_distinto_fallo_no_toca_old(self):
        with tempfile.TemporaryDirectory() as tmp:
            mods = self._env(tmp)
            with mock.patch.object(self.m, "_mr_project_versions",
                                    return_value=_latest("nuevo.jar")), \
                 mock.patch.object(self.m, "_download_with_progress",
                                    side_effect=RuntimeError("red")), \
                 mock.patch.object(self.m, "emit", lambda e: None):
                with self.assertRaises(SystemExit):
                    self.m.cmd_mod_update(_ns(tmp))
            self.assertTrue((mods / "viejo.jar").is_file())
            self.assertFalse((mods / "nuevo.jar").exists())
            self.assertFalse((mods / "nuevo.jar.corky-part").exists())

    def test_nombre_distinto_exito_mueve_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            mods = self._env(tmp)
            def fake_dl(url, dest, stage):
                Path(dest).write_bytes(b"jar-nuevo" * 500)
            with mock.patch.object(self.m, "_mr_project_versions",
                                    return_value=_latest("nuevo.jar")), \
                 mock.patch.object(self.m, "_download_with_progress",
                                    side_effect=fake_dl), \
                 mock.patch.object(self.m, "emit", lambda e: None):
                self.m.cmd_mod_update(_ns(tmp))
            self.assertFalse((mods / "viejo.jar").exists())
            self.assertTrue((mods / "nuevo.jar").is_file())
            self.assertFalse((mods / "viejo.jar.corky.json").exists())
            rec = json.loads((mods / "nuevo.jar.corky.json").read_text())
            self.assertEqual(rec["version_id"], "v2")


if __name__ == "__main__":
    unittest.main()
