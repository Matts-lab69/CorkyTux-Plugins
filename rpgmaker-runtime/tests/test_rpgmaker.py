"""Tests sin red del wrapper rpgmaker-runtime (fase 2.2).

Cubre deteccion local (hint UI), parseo de runtimes, deteccion X11 y el
reenvio de flags de `run`, sin invocar box-rpg real ni tocar disco del
usuario. El camino con backend real se verifica en vivo (ver
docs/rpgmaker-upgrade.md).

Uso: python3 tests/test_rpgmaker.py (stdlib, sin red).
"""
import importlib.machinery
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent.parent / "rpgmaker-runtime"


def load():
    loader = importlib.machinery.SourceFileLoader("rpg_rt", str(SCRIPT))
    spec = importlib.util.spec_from_loader("rpg_rt", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class DetectHint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _mk(self, tmp, files=(), dirs=()):
        base = Path(tmp)
        for d in dirs:
            (base / d).mkdir(parents=True, exist_ok=True)
        for f in files:
            p = base / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}" if f.endswith(".json") else "x")
        return base

    def test_mz_antes_que_mv(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self._mk(tmp,
                files=("index.html", "js/plugins.js", "js/rmmz_core.js",
                        "package.json"),
                dirs=("js", "data"))
            got = self.m.detect_engine_hint(base)
            self.assertEqual((got["engine"], got.get("variant")), ("mv_mz", "mz"))

    def test_mv(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self._mk(tmp,
                files=("www/index.html", "www/js/plugins.js", "package.json"))
            got = self.m.detect_engine_hint(base)
            self.assertEqual((got["engine"], got.get("variant")), ("mv_mz", "mv"))

    def test_2k3(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self._mk(tmp, files=("RPG_RT.ini", "RPG_RT.ldb", "RPG_RT.lmt"))
            self.assertEqual(self.m.detect_engine_hint(base)["engine"], "2k3")

    def test_xp_no_soportado(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self._mk(tmp, files=("Game.ini", "Data/Scripts.rvdata2"),
                             dirs=("Data",))
            got = self.m.detect_engine_hint(base)
            self.assertEqual(got["engine"], "unsupported")

    def test_desconocido(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                self.m.detect_engine_hint(Path(tmp))["engine"], "unknown")
            self.assertEqual(
                self.m.detect_engine_hint(Path(tmp) / "nope")["engine"], "unknown")


class RuntimeLines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_vacio(self):
        self.assertEqual(
            self.m._parse_runtime_lines("no nwjs runtimes installed\n"), [])

    def test_lista(self):
        self.assertEqual(
            self.m._parse_runtime_lines("0.85.3\n0.83.0\n"),
            ["0.85.3", "0.83.0"])


class NeedsX11(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_sin_display(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(self.m._needs_x11())

    def test_x11_puro(self):
        with mock.patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True):
            self.assertTrue(self.m._needs_x11())

    def test_wayland_con_socket(self):
        with tempfile.TemporaryDirectory() as tmp:
            sock = Path(tmp) / "wayland-0"
            sock.write_text("")
            env = {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0",
                   "XDG_RUNTIME_DIR": tmp}
            with mock.patch.dict(os.environ, env, clear=True):
                self.assertFalse(self.m._needs_x11())


class RunForwarding(unittest.TestCase):
    """run reenvia opt-ins y pide --x11 en X11 (sin lanzar nada real)."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _run(self, tmp, extra=(), env=None):
        captured = {}
        fake = mock.Mock(returncode=0)
        with tempfile.TemporaryDirectory() as game:
            argv = [game, *extra]
            with mock.patch.object(self.m, "run_box_rpg",
                                    return_value=fake) as rbr, \
                 mock.patch("subprocess.Popen") as pop, \
                 mock.patch.dict(os.environ, env or {}, clear=True), \
                 mock.patch.object(self.m, "emit",
                                    side_effect=SystemExit(0)):
                with self.assertRaises(SystemExit):
                    self.m.cmd_run(argv)
            captured["box_calls"] = [c.args[0] for c in rbr.call_args_list]
            captured["launch"] = pop.call_args.args[0]
        return captured

    def test_flags_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = self._run(tmp, ("--allow-network", "--gamemode", "--sdk",
                                  "--ci-mount", "--allow-game-writes"))
            for f in ("--allow-network", "--gamemode", "--sdk", "--ci-mount",
                      "--allow-game-writes"):
                self.assertIn(f, got["launch"])

    def test_x11_solo_en_x11(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = self._run(tmp, (), {"DISPLAY": ":0"})
            self.assertIn("--x11", got["launch"])
            got2 = self._run(tmp, (), {})
            self.assertNotIn("--x11", got2["launch"])

    def test_copy_root_file_repetible(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = self._run(tmp, ("--copy-root-file", "a.csv",
                                  "--copy-root-file", "b.csv"))
            self.assertEqual(got["launch"].count("--copy-root-file"), 2)

    def test_autoriza_raiz(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = self._run(tmp)
            self.assertIn("allowed-game-root", got["box_calls"][0])


if __name__ == "__main__":
    unittest.main()
