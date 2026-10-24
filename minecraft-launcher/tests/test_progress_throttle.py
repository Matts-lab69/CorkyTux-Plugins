"""The progress stream must not outrun the launcher's 50 ms event pump.

Uso: python3 -m unittest tests.test_progress_throttle
"""
import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "minecraft-launcher"


def load():
    loader = importlib.machinery.SourceFileLoader("mc_launcher_progress", str(SCRIPT))
    spec = importlib.util.spec_from_loader("mc_launcher_progress", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class ProgressThrottleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_burst_is_coalesced(self):
        now = [0.0]
        gate = self.m._ProgressThrottle(interval=0.1, clock=lambda: now[0])
        self.assertTrue(gate.allow("Download a.jar"))
        now[0] = 0.01
        self.assertFalse(gate.allow("Download b.jar"))
        now[0] = 0.11
        self.assertTrue(gate.allow("Download c.jar"))

    def test_stage_change_is_immediate(self):
        now = [0.0]
        gate = self.m._ProgressThrottle(interval=0.1, clock=lambda: now[0])
        self.assertTrue(gate.allow("Download a.jar"))
        now[0] = 0.01
        self.assertTrue(gate.allow("Install java runtime"))
        now[0] = 0.02
        self.assertTrue(gate.allow("Download b.jar"))
        self.assertFalse(gate.allow("Download c.jar"))

    def test_force_always_passes(self):
        now = [0.0]
        gate = self.m._ProgressThrottle(interval=0.1, clock=lambda: now[0])
        self.assertTrue(gate.allow("Downloading files"))
        self.assertTrue(gate.allow("Downloading files", force=True))

    def test_status_categories(self):
        self.assertEqual(self.m._progress_stage("Download a.jar"),
                         "Downloading files")
        self.assertEqual(self.m._progress_stage("Download Assets"),
                         "Download Assets")
        self.assertEqual(self.m._progress_stage("Extract overrides/x]"),
                         "Extracting files")
        self.assertEqual(self.m._progress_stage("Install java runtime"),
                         "Install java runtime")

    def test_callbacks_keep_the_first_and_the_final_progress(self):
        out = []
        original = self.m.emit
        self.m.emit = out.append
        try:
            cb = self.m._install_callbacks()
            cb["setMax"](10)
            for value in range(11):
                cb["setProgress"](value)
            cb["setStatus"]("Installation complete")
        finally:
            self.m.emit = original
        self.assertLessEqual(len(out), 3)
        self.assertEqual(out[0]["percent"], 0.0)
        self.assertEqual(out[-2]["percent"], 100.0)
        self.assertEqual(out[-1]["stage"], "Installation complete")


if __name__ == "__main__":
    unittest.main()
