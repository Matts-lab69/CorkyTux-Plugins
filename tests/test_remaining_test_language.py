"""Guard the remaining explicitly translated regression-test vocabulary."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RemainingTestLanguage(unittest.TestCase):
    def test_translated_usage_and_rpg_method_names(self):
        for directory in ("minecraft-launcher/tests", "rpgmaker-runtime/tests"):
            for path in (ROOT / directory).glob("*.py"):
                with self.subTest(file=path.name):
                    source = path.read_text()
                    self.assertNotIn("Uso:", source)
                    self.assertIsNone(re.search(
                        r"def (?:test_)?\w*(?:antes_que|vacio_falla|basura_falla|"
                        r"sin_display|x11_puro|pide_x11|con_codigo|emite_timeout|"
                        r"formato_viejo|autoriza_raiz|sessions_fallo|sessions_sin_path)\w*", source))
        self.assertNotIn("vanilla primero, luego", (ROOT / "minecraft-launcher/tests/test_install_legacy.py").read_text())


if __name__ == "__main__":
    unittest.main()
