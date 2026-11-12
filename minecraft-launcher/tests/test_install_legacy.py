"""Offline NeoForge/26.3 installation tests through _base.install (option a).

Coverage:
- neoforge/26.3: the legacy path (eff=1.26.3 != 26.3) calls
  install_minecraft_version(vanilla) + _base.install + get_installed_version.
- neoforge/1.21.1: direct version spelling -> normal ml.install path.
- fabric/26.3: direct version spelling -> normal ml.install path.
- mll without _base: visible AttributeError, never silently ignored.

Usage: python3 tests/test_install_legacy.py (stdlib, no network).
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


class FakeBase:
    """Stand-in for minecraft_launcher_lib internal _base of neoforge."""

    def __init__(self, installed):
        self.installed = installed
        self.install_calls = []

    def install(self, version, mc_dir, callback, java, loader_version):
        self.install_calls.append((version, mc_dir, java, loader_version))

    def get_installed_version(self, version, loader_version):
        return self.installed


class FakeLoader:
    """Minimal ModLoader stand-in recording wrapper install() calls."""

    def __init__(self, supported, latest, base=None):
        self.supported = set(supported)
        self.latest = latest
        self._base = base
        self.wrapper_install_calls = []

    def is_minecraft_version_supported(self, mc):
        return mc in self.supported

    def get_latest_loader_version(self, mc):
        if mc in self.latest:
            return self.latest[mc]
        raise RuntimeError(f"no latest for {mc}")

    def get_loader_versions(self, mc, stable_only):
        return []

    def install(self, version, mc_dir, *, loader_version=None, callback=None):
        self.wrapper_install_calls.append((version, loader_version))
        return f"{loader_version}-installed"


class InstallLegacyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()
        cls.m.emit = lambda ev: cls.events.append(ev)
        cls.vanilla_installs = []

    def setUp(self):
        self.events = []
        type(self).events = self.events
        self.vanilla_installs = []
        type(self).vanilla_installs = self.vanilla_installs
        # mll records versions passed to install.install_minecraft_version.
        fake_install = types.SimpleNamespace(
            install_minecraft_version=lambda v, d, callback=None: type(self).vanilla_installs.append(v))
        self.m.mll = types.SimpleNamespace(
            mod_loader=types.SimpleNamespace(get_mod_loader=lambda _l: self.loader),
            install=fake_install,
        )
        self.m.LOCKS_DIR.mkdir(parents=True, exist_ok=True)

    def _args(self, version, loader, loader_version=""):
        return types.SimpleNamespace(version=version, loader=loader,
                                     loader_version=loader_version,
                                     mc_dir="/tmp/opencode/test-install-dir")


class NeoForgeLegacyInstallTests(InstallLegacyTests):
    def test_neoforge_26_3_uses_legacy_base_path(self):
        # 26.3 matches only through "1.26.3" -> _base path, not the wrapper.
        self.loader = FakeLoader(
            {"1.26.3"}, {"1.26.3": "26.3.0.51-beta"},
            base=FakeBase("neoforge-26.3.0.51-beta"))
        self.m.cmd_install(self._args("26.3", "neoforge"))
        self.assertEqual(self.loader.wrapper_install_calls, [],
                         "wrapper install() must not be used on the legacy path")
        self.assertIsNotNone(self.loader._base)
        self.assertEqual(self.loader._base.install_calls[0][0], "26.3",
                         "actual vanilla: 26.3, not 1.26.3")
        self.assertEqual(self.loader._base.install_calls[0][3], "26.3.0.51-beta")
        self.assertEqual(self.vanilla_installs,
                         ["26.3", "neoforge-26.3.0.51-beta"],
                         "vanilla first, then the final loader ID")
        doc = self.events[-1]
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["version"], "neoforge-26.3.0.51-beta")
        self.assertEqual(doc["loader_version"], "26.3.0.51-beta")
        self.assertEqual(doc["loader"], "neoforge")

    def test_beta_loader_version_flows_into_done(self):
        # An ID ending in -beta (beta build) uses the same installation path.
        self.loader = FakeLoader(
            {"1.26.3"}, {"1.26.3": "26.3.0.51-beta"},
            base=FakeBase("neoforge-26.3.0.51-beta"))
        self.m.cmd_install(self._args("26.3", "neoforge"))
        doc = self.events[-1]
        self.assertTrue(doc["ok"])
        self.assertTrue(doc["version"].endswith("-beta"))

    def test_neoforge_explicit_loader_version_kept(self):
        self.loader = FakeLoader(
            {"1.26.3"}, {"1.26.3": "26.3.0.51-beta"},
            base=FakeBase("neoforge-26.3.0.50"))
        self.m.cmd_install(self._args("26.3", "neoforge", loader_version="26.3.0.50"))
        self.assertEqual(self.loader._base.install_calls[0][3], "26.3.0.50")

    def test_mll_without_base_fails_loudly(self):
        # Old mll without _base.install: explicit error, not silently ignored.
        self.loader = FakeLoader({"1.26.3"}, {"1.26.3": "26.3.0.51-beta"}, base=None)
        with self.assertRaises(SystemExit):
            self.m.cmd_install(self._args("26.3", "neoforge"))
        self.assertTrue(self.events[-1]["message"].startswith("NeoForge install for 26.3"))


class DirectSpellingInstallTests(InstallLegacyTests):
    def test_neoforge_1_21_1_uses_wrapper(self):
        # Already normalized legacy ID -> normal wrapper, without _base.
        self.loader = FakeLoader(
            {"1.21.1"}, {"1.21.1": "21.1.218"},
            base=FakeBase("neoforge-21.1.218"))
        self.m.cmd_install(self._args("1.21.1", "neoforge"))
        self.assertEqual(self.loader.wrapper_install_calls, [("1.21.1", "21.1.218")])
        self.assertEqual(self.loader._base.install_calls, [],
                         "_base must not be used on the direct path")
        self.assertEqual(self.vanilla_installs, [])

    def test_fabric_26_3_uses_wrapper(self):
        self.loader = FakeLoader(
            {"26.3"}, {"26.3": "0.19.5"}, base=None)
        self.m.cmd_install(self._args("26.3", "fabric"))
        self.assertEqual(self.loader.wrapper_install_calls, [("26.3", "0.19.5")])
        doc = self.events[-1]
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["version"], "0.19.5-installed")


if __name__ == "__main__":
    unittest.main()
