"""Tests sin red del verbo loader-versions (fase 1.3c).

Cubre:
- modo por lote --loaders a,b,c: un solo "done" con todas las respuestas
  en el orden pedido, errores por loader capturados en "errors".
- workaround NeoForge/26.3: _probe_mc prueba "1."+mc cuando el loader
  no reconoce el id de version moderno (mll normaliza a "1.x").
- modo individual --loader conserva el formato de respuesta previo.

Uso: python3 tests/test_loader_versions.py (stdlib, sin red).
"""
import importlib.machinery
import importlib.util
import types
import unittest

SCRIPT = __import__("pathlib").Path(__file__).resolve().parent.parent / "minecraft-launcher"


def load():
    loader = importlib.machinery.SourceFileLoader("mc_launcher", str(SCRIPT))
    spec = importlib.util.spec_from_loader("mc_launcher", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class FakeLoader:
    """Minimal stand-in for minecraft_launcher_lib.mod_loader.ModLoader."""

    def __init__(self, supported, versions, latest):
        self.supported = set(supported)
        self.versions = versions
        self.latest = latest

    def is_minecraft_version_supported(self, mc):
        return mc in self.supported

    def get_loader_versions(self, mc, stable_only):
        return list(self.versions.get(mc, []))

    def get_latest_loader_version(self, mc):
        if mc in self.latest:
            return self.latest[mc]
        raise RuntimeError(f"no latest for {mc}")


class LoaderVersionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()
        cls.m.mll = types.SimpleNamespace(
            mod_loader=types.SimpleNamespace(get_mod_loader=lambda loader: cls.loaders[loader]))
        cls.m.emit = lambda ev: cls.events.append(ev)
        cls.loaders = {}

    def setUp(self):
        self.events = []
        type(self).events = self.events

    def _ns(self, mc_version="26.3", loader="", loaders=""):
        return types.SimpleNamespace(mc_version=mc_version, loader=loader,
                                     loaders=loaders)

    def _set(self, loaders):
        type(self).loaders = loaders


class BatchTests(LoaderVersionsTests):
    def test_batch_answers_all_requested_loaders_in_order(self):
        # fabric soporta 26.3 directo; neoforge solo via "1.26.3"
        # (workaround); quilt explota al listar -> error visible.
        self._set({
            "fabric": FakeLoader(["26.3"], {"26.3": ["0.19.5"]},
                                 {"26.3": "0.19.5"}),
            "neoforge": FakeLoader(["1.26.3"], {"1.26.3": []},
                                   {"1.26.3": "26.3.0.51-beta"}),
            "quilt": FakeLoader(["26.3"], {}, {}),
        })
        self.m.cmd_loader_versions(
            self._ns(loaders="fabric,neoforge,quilt"))
        self.assertEqual(len(self.events), 1, "un solo done en un arranque")
        doc = self.events[0]
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["mc_version"], "26.3")
        names = [loader["loader"] for loader in doc["loaders"]]
        self.assertEqual(names, ["fabric", "neoforge"],
                         "orden pedido preservado; el que explota va a errors")
        fabric = doc["loaders"][0]
        self.assertTrue(fabric["supported"])
        self.assertEqual(fabric["versions"], ["0.19.5"])
        neo = doc["loaders"][1]
        self.assertTrue(neo["supported"], "workaround 1.26.3 debe marcar soporte")
        self.assertEqual(neo["mc_version_matched"], "1.26.3")
        self.assertIn("quilt", doc["errors"], "fallo del loader, nunca silencioso")
        self.assertNotIn("fabric", doc["errors"])
        self.assertNotIn("neoforge", doc["errors"])

    def test_batch_unknown_loader_dies(self):
        with self.assertRaises(SystemExit):
            self.m.cmd_loader_versions(self._ns(loaders="fabric,optifine"))
        self.assertEqual(len(self.events), 1)
        self.assertTrue(self.events[0]["message"].startswith("loader must be"))

    def test_batch_empty_loaders_dies(self):
        with self.assertRaises(SystemExit):
            self.m.cmd_loader_versions(self._ns(loaders="  , ,"))

    def test_neither_loader_nor_loaders_dies(self):
        with self.assertRaises(SystemExit):
            self.m.cmd_loader_versions(self._ns(loader="", loaders=""))


class WorkaroundTests(LoaderVersionsTests):
    def test_neoforge_26_3_resolved_through_legacy_spelling(self):
        # mll normaliza a "1.x": "26.3" nunca esta en get_minecraft_versions
        # de NeoForge aunque "1.26.3" si. _probe_mc debe probar el prefijo.
        neo = FakeLoader(["1.26.3"], {"1.26.3": ["26.3.0.51-beta"]},
                         {"1.26.3": "26.3.0.51-beta"})
        self.assertEqual(self.m._probe_mc(neo, "26.3"), "1.26.3")
        self.assertEqual(self.m._probe_mc(neo, "1.26.3"), "1.26.3",
                         "ids legacy directos quedan igual")
        self.assertIsNone(self.m._probe_mc(neo, "26.9"),
                          "sin pareja legacy -> unsupported")

    def test_supported_direct_version_untouched(self):
        fab = FakeLoader(["26.3"], {"26.3": ["0.19.5"]}, {"26.3": "0.19.5"})
        self.assertEqual(self.m._probe_mc(fab, "26.3"), "26.3")

    def test_single_mode_reports_false_when_neither_spelling_matches(self):
        # Neoforge para una version que no existe ni legacy ni moderna.
        self._set({"fabric": FakeLoader([], {}, {})})
        self.m.cmd_loader_versions(self._ns(loader="fabric"))
        doc = self.events[0]
        self.assertFalse(doc["supported"])
        self.assertEqual(doc["versions"], [])
        self.assertEqual(doc["loader"], "fabric")

    def test_single_mode_supported_shape_preserved(self):
        self._set({"fabric": FakeLoader(["26.3"], {"26.3": ["0.19.5"]},
                                        {"26.3": "0.19.5"})})
        self.m.cmd_loader_versions(self._ns(loader="fabric"))
        doc = self.events[0]
        self.assertTrue(doc["supported"])
        self.assertEqual(doc["versions"], ["0.19.5"])
        self.assertEqual(doc["latest"], "0.19.5")
        self.assertEqual(doc["loader"], "fabric")
        # el workaround tambien vale en modo individual
        neo = FakeLoader(["1.26.3"], {"1.26.3": ["26.3.0.51-beta"]},
                         {"1.26.3": "26.3.0.51-beta"})
        self._set({"neoforge": neo})
        self.m.cmd_loader_versions(self._ns(loader="neoforge"))
        doc = self.events[-1]
        self.assertTrue(doc["supported"])
        self.assertEqual(doc["versions"], ["26.3.0.51-beta"])


if __name__ == "__main__":
    unittest.main()
