"""Guard the English maintenance notes without changing protocol fixtures."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RegressionNotesLanguage(unittest.TestCase):
    def test_minecraft_regression_notes_are_english(self):
        forbidden = ("Tests sin red", "Cubre:", "Uso:", "Un test por patron",
                     "wrapper install() NO se usa", "_base no se toca",
                     "debe marcar soporte", "sin pareja legacy")
        for name in ("test_install_legacy.py", "test_loader_versions.py",
                     "test_mod_update.py", "test_redaction.py"):
            source = (ROOT / "minecraft-launcher/tests" / name).read_text()
            for phrase in forbidden:
                with self.subTest(file=name, phrase=phrase):
                    self.assertNotIn(phrase, source)


if __name__ == "__main__":
    unittest.main()
