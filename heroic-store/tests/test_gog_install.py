"""Tests sin red del paso (a): parseo de progreso gogdl, lang, builds, carpetas.

NOTA: las líneas de progreso son SINTÉTICAS (derivadas de los format
strings de gogdl/dl/progressbar.py, NO capturadas de una descarga real).
En la prueba real con Hank se capturan líneas verdaderas y se agregan
como fixtures. written_raw/total_raw son contadores SIN unidad confirmada.

Uso: python3 tests/test_gog_install.py (stdlib, sin pytest ni red).
"""
import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "heroic-store"


def load():
    # El plugin no tiene extensión .py: SourceFileLoader explícito.
    loader = importlib.machinery.SourceFileLoader("heroic_store", str(SCRIPT))
    spec = importlib.util.spec_from_loader("heroic_store", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class ProgressLines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_v2_progress_con_eta(self):
        ev = self.m._parse_progress_line(
            "[PROGRESS] INFO: = Progress: 42.50 123456/789012, "
            "Running for: 00:01:23, ETA: 00:05:00")
        self.assertEqual(ev["percent"], 42.5)
        self.assertEqual((ev["written_raw"], ev["total_raw"]), (123456, 789012))
        self.assertEqual(ev["eta_s"], 300)

    def test_v2_progress_sin_eta(self):
        ev = self.m._parse_progress_line("= Progress: 0.00 0/789012")
        self.assertEqual(ev["percent"], 0.0)
        self.assertIsNone(ev["eta_s"])

    def test_v2_speed_sola(self):
        ev = self.m._parse_progress_line(
            "[PROGRESS] INFO:  + Download\t- 8.20 MiB/s (raw) / 1.50 MiB/s (decompressed)")
        self.assertIsNone(ev["percent"])
        self.assertEqual(ev["speed_mibs"], 8.2)

    def test_porcentaje_generico_legendary(self):
        ev = self.m._parse_progress_line("Downloaded 1.2 GB (45%)")
        self.assertEqual((ev["stage"], ev["percent"]), ("downloading", 45.0))

    def test_ruido_no_es_progreso(self):
        self.assertIsNone(self.m._parse_progress_line(
            "[API] INFO: Getting Dependencies repository"))
        self.assertIsNone(self.m._parse_progress_line(""))
        self.assertIsNone(self.m._parse_progress_line(
            "[PROGRESS] INFO: = Downloaded: 12.34 MiB, Written: 45.67 MiB"))


class LangPick(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_en_us_si_esta(self):
        self.assertEqual(
            self.m._gog_pick_lang({"languages": ["de-DE", "en-US"]}, ""), "en-US")

    def test_primero_si_no_esta(self):
        self.assertEqual(
            self.m._gog_pick_lang({"languages": ["fr-FR"]}, ""), "fr-FR")

    def test_override_manual(self):
        self.assertEqual(
            self.m._gog_pick_lang({"languages": ["fr-FR"]}, "de-DE"), "de-DE")

    def test_sin_lista_vacio(self):
        self.assertEqual(self.m._gog_pick_lang({}, ""), "")


class LinuxBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_solo_windows(self):
        info = {"builds": {"items": [{"os": "windows"}]}}
        self.assertFalse(self.m._gog_has_linux_build(info))

    def test_con_linux(self):
        info = {"builds": {"items": [{"os": "windows"}, {"os": "linux"}]}}
        self.assertTrue(self.m._gog_has_linux_build(info))

    def test_info_vacio(self):
        self.assertFalse(self.m._gog_has_linux_build({}))


class SanitizeFolder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_nombre_real(self):
        self.assertEqual(
            self.m._sanitize_folder("Hank Straightjacket", "1831618557"),
            "Hank Straightjacket")

    def test_fallback(self):
        self.assertEqual(self.m._sanitize_folder("...   ", "1831618557"), "1831618557")
        self.assertEqual(self.m._sanitize_folder("", "1831618557"), "1831618557")


if __name__ == "__main__":
    unittest.main(verbosity=2)
