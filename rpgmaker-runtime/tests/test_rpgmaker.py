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


class ApiRuntime(unittest.TestCase):
    """Versiones/listas vía box.api estructurado (sin parsear texto CLI)."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _proc(self, rc=0, out="", err=""):
        import subprocess
        return subprocess.CompletedProcess([], rc, out, err)

    def test_first_available(self):
        import json
        fake = self._proc(0, json.dumps({"versions": ["v0.117.0", "v0.116.0"]}))
        with mock.patch.object(self.m, "_box_api", return_value=fake) as ba:
            self.assertEqual(self.m._api_first_available("nwjs"), "v0.117.0")
            self.assertIn("fetch_nwjs_available", ba.call_args.args[0][0])

    def test_first_available_vacio_falla(self):
        import json
        fake = self._proc(0, json.dumps({"versions": []}))
        with mock.patch.object(self.m, "_box_api", return_value=fake):
            with self.assertRaises(SystemExit):
                self.m._api_first_available("easyrpg")

    def test_runtime_lines(self):
        import json
        fake = self._proc(0, json.dumps({
            "nwjs": ["v0.117.0 x64 /r/nw"], "easyrpg": ["0.8.1 x64 /r/er"]}))
        with mock.patch.object(self.m, "_box_api", return_value=fake):
            nw, er = self.m._api_runtime_lines()
        self.assertEqual(nw, ["v0.117.0 x64 /r/nw"])
        self.assertEqual(er, ["0.8.1 x64 /r/er"])

    def test_runtime_lines_basura_falla(self):
        fake = self._proc(0, "not-json{{{")
        with mock.patch.object(self.m, "_box_api", return_value=fake):
            with self.assertRaises(SystemExit):
                self.m._api_runtime_lines()


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


class AvailableParsing(unittest.TestCase):
    """Formato upstream 26.9.138: '  1. v0.117.0 (195.7 MB)'."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _versions(self, out):
        import re
        return re.findall(r"^\s*\d+\.\s+(\S+)", out, flags=re.MULTILINE)

    def test_con_tamano(self):
        self.assertEqual(
            self._versions("Available NW.js versions (page 1, x64):\n"
                           "  1. v0.117.0 (195.7 MB)\n  2. v0.116.0 (194.9 MB)\n"),
            ["v0.117.0", "v0.116.0"])

    def test_easyrpg(self):
        self.assertEqual(
            self._versions("  1. 0.8.1 (5.9 MB)\n"),
            ["0.8.1"])

    def test_formato_viejo_sigue(self):
        self.assertEqual(self._versions("  1. 0.8.1\n"), ["0.8.1"])


class SessionCommands(unittest.TestCase):
    """sessions/stop/runtime-remove/config-show (box hijo mockeado)."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def _proc(self, rc=0, out="", err=""):
        import subprocess
        return subprocess.CompletedProcess([], rc, out, err)

    def test_sessions_ok(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            events = []
            fake = self._proc(0, json.dumps({"sessions": ["a"], "identifier": "id1"}))
            with mock.patch.object(self.m, "_box_api", return_value=fake), \
                 mock.patch.object(self.m, "emit", side_effect=SystemExit(0)) as em:
                with self.assertRaises(SystemExit):
                    self.m.cmd_sessions([tmp])
            payload = em.call_args.args[0]
            self.assertEqual((payload["sessions"], payload["identifier"]), (["a"], "id1"))

    def test_sessions_fallo(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = self._proc(1, "", "boom")
            with mock.patch.object(self.m, "_box_api", return_value=fake):
                with self.assertRaises(SystemExit):
                    self.m.cmd_sessions([tmp])

    def test_sessions_sin_path(self):
        with self.assertRaises(SystemExit):
            self.m.cmd_sessions([])

    def test_stop_ok(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            fake = self._proc(0, json.dumps({"stopped": ["a"]}))
            with mock.patch.object(self.m, "_box_api", return_value=fake), \
                 mock.patch.object(self.m, "emit", side_effect=SystemExit(0)) as em:
                with self.assertRaises(SystemExit):
                    self.m.cmd_stop([tmp])
            self.assertEqual(em.call_args.args[0]["stopped"], ["a"])

    def test_runtime_remove_uso(self):
        with self.assertRaises(SystemExit):
            self.m.cmd_runtime_remove(["nwjs"])
        with self.assertRaises(SystemExit):
            self.m.cmd_runtime_remove([])

    def test_runtime_remove_ok(self):
        fake = self._proc(0, "removed 0.8.1", "")
        with mock.patch.object(self.m, "run_box_rpg", return_value=fake), \
             mock.patch.object(self.m, "emit", side_effect=SystemExit(0)) as em:
            with self.assertRaises(SystemExit):
                self.m.cmd_runtime_remove(["easyrpg", "0.8.1"])
        payload = em.call_args.args[0]
        self.assertEqual((payload["kind"], payload["removed_version"]), ("easyrpg", "0.8.1"))

    def test_config_show_ok(self):
        fake = self._proc(0, "preferred_runtime: (none)\n", "")
        with mock.patch.object(self.m, "run_box_rpg", return_value=fake), \
             mock.patch.object(self.m, "emit", side_effect=SystemExit(0)) as em:
            with self.assertRaises(SystemExit):
                self.m.cmd_config_show([])
        self.assertIn("preferred_runtime", em.call_args.args[0]["output"])


if __name__ == "__main__":
    unittest.main()
