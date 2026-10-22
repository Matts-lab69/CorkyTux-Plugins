"""The Epic catalog version and date, as the launcher shows them.

The fixture is a sanitized copy of the shape that `legendary list --json`
returns. The last test reads the real legendary cache read-only, when there
is one, to check the shape against the live data (it never writes and it
never prints a value).

Uso: python3 -m unittest tests.test_epic_version
"""
import importlib.machinery
import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "heroic-store"

# A sanitized element: no tokens, no account data, no catalog ids of a real
# game. It only keeps the shape of the fields the helper reads.
FIXTURE = {
    "app_name": "example",
    "app_title": "Example Game",
    "asset_infos": {
        "Windows": {
            "app_name": "example",
            "build_version": "1.2.3",
            "namespace": "ns",
        },
        "Linux": {
            "app_name": "example",
            "build_version": "9.9.9",
            "namespace": "ns",
        },
    },
    "metadata": {
        "lastModifiedDate": "2024-08-16T11:00:23.968Z",
    },
}


def load():
    loader = importlib.machinery.SourceFileLoader("heroic_store", str(SCRIPT))
    spec = importlib.util.spec_from_loader("heroic_store", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class EpicVersionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_the_version_comes_from_the_windows_build_version(self):
        version, last_updated = self.m._epic_version_and_date(FIXTURE)
        self.assertEqual(version, "1.2.3")
        self.assertEqual(last_updated, "2024-08-16")

    def test_the_date_is_cut_to_the_day(self):
        _, last_updated = self.m._epic_version_and_date(FIXTURE)
        self.assertRegex(last_updated, r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(len(last_updated), 10)

    def test_windows_wins_over_the_other_platforms(self):
        only_linux = {
            "asset_infos": {"Linux": {"build_version": "9.9.9"}},
            "metadata": {},
        }
        version, _ = self.m._epic_version_and_date(only_linux)
        self.assertEqual(version, "9.9.9")

    def test_a_game_without_catalog_data_gives_empty_values(self):
        version, last_updated = self.m._epic_version_and_date({})
        self.assertEqual(version, "")
        self.assertEqual(last_updated, "")

    def test_a_short_date_is_not_used(self):
        broken = {"asset_infos": {}, "metadata": {"lastModifiedDate": "2024-08"}}
        _, last_updated = self.m._epic_version_and_date(broken)
        self.assertEqual(last_updated, "")

    def test_it_matches_the_real_legendary_cache_read_only(self):
        cache = Path.home() / ".config" / "legendary" / "metadata"
        files = sorted(cache.glob("*.json")) if cache.is_dir() else []
        if not files:
            self.skipTest("there is no legendary cache on this machine")
        for path in files[:5]:
            with open(path, encoding="utf-8") as fh:
                element = json.load(fh)
            version, last_updated = self.m._epic_version_and_date(element)
            self.assertTrue(version, "no build_version in " + path.name)
            self.assertRegex(last_updated, r"^\d{4}-\d{2}-\d{2}$",
                             "no lastModifiedDate in " + path.name)


if __name__ == "__main__":
    unittest.main()
