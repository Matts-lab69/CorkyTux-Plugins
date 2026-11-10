"""Hermetic editorial rail cache tests; no credentials or transport access."""
import concurrent.futures
import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def load():
    script = Path(__file__).resolve().parent.parent / "heroic-store"
    loader = importlib.machinery.SourceFileLoader("heroic_rails", str(script))
    spec = importlib.util.spec_from_loader("heroic_rails", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class GogRailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/tmp/opencode")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        config = patch.object(self.m, "CONFIG_DIR", self.root)
        config.start()
        self.addCleanup(config.stop)
        clock = patch("time.time", return_value=1_000_000)
        clock.start()
        self.addCleanup(clock.stop)
        self.path = self.m._gog_rail_cache_dir() / "sale.json"

    def write_cache(self, **fields):
        data = {"ts": 1_000_000, "ttl": self.m.GOG_RAIL_TTL,
                "v": self.m.GOG_RAIL_POOL_V, "items": [{"title": "Cached"}]}
        data.update(fields)
        self.path.write_text(json.dumps(data))

    def command(self, refresh=False, products=None, error=None):
        with patch.object(self.m, "_gog_rail_fetch", return_value=products or [],
                          side_effect=error) as fetch, patch.object(self.m, "emit") as emit:
            self.m.cmd_gog_rail(SimpleNamespace(list="sale", refresh=refresh))
            return emit.call_args.args[0], fetch.call_count

    def test_fresh_cache_and_force_refresh(self):
        self.write_cache()
        result, calls = self.command()
        self.assertEqual(calls, 0)
        self.assertTrue(result["cached"])
        self.assertFalse(result["stale"])
        result, calls = self.command(refresh=True)
        self.assertEqual(calls, 1)
        self.assertFalse(result["cached"])
        self.assertFalse(result["stale"])

    def test_invalid_cache_data_is_ignored(self):
        for text in ("broken", "[]", "null"):
            with self.subTest(text=text):
                self.path.write_text(text)
                self.assertIsNone(self.m._gog_rail_cache_get("sale"))
        for fields in ({"v": -1}, {"items": {}}, {"ts": "invalid"},
                       {"ts": 1_000_001}, {"ts": float("inf")},
                       {"ts": float("nan")}, {"ts": 10 ** 400},
                       {"ttl": float("inf")}, {"ttl": -1}):
            with self.subTest(fields=fields):
                self.write_cache(**fields)
                self.assertIsNone(self.m._gog_rail_cache_get("sale"))
                self.assertIsNone(self.m._gog_rail_cache_get("sale", allow_stale=True))

    def test_ttl_and_stale_boundaries(self):
        for age, fresh, stale in ((3600, True, True), (3601, False, True),
                                  (604800, False, True), (604801, False, False)):
            with self.subTest(age=age):
                self.write_cache(ts=1_000_000 - age)
                self.assertEqual(self.m._gog_rail_cache_get("sale") is not None, fresh)
                self.assertEqual(self.m._gog_rail_cache_get(
                    "sale", allow_stale=True) is not None, stale)

    def test_stale_fallback_including_empty_list_and_forced_refresh(self):
        for items in ([], [{"title": "Cached", "price_final": "$5"}]):
            for refresh in (False, True):
                with self.subTest(items=items, refresh=refresh):
                    self.write_cache(ts=990_000, items=items)
                    result, calls = self.command(refresh=refresh, error=OSError("offline"))
                    self.assertEqual(calls, 1)
                    self.assertEqual(result["items"], items)
                    self.assertTrue(result["cached"])
                    self.assertTrue(result["stale"])
                    self.assertTrue(result["partial"])
                    self.assertIn("prices may be outdated", result["warning"])

    def test_network_failure_without_usable_cache(self):
        for fields in ({"v": -1}, {"ts": 1}, {"items": None}):
            self.write_cache(**fields)
            result, calls = self.command(error=OSError("offline"))
            self.assertEqual(calls, 1)
            self.assertEqual(result["items"], [])
            self.assertTrue(result["partial"])
            self.assertFalse(result["cached"])
            self.assertFalse(result["stale"])

    def test_refresh_success_replaces_stale_cache(self):
        self.write_cache(ts=990_000)
        products = [{"id": "1", "title": "Fresh", "price": {"discount": "50%"}}]
        result, calls = self.command(refresh=True, products=products)
        self.assertEqual(calls, 1)
        self.assertEqual(result["items"][0]["title"], "Fresh")
        self.assertEqual(self.m._gog_rail_cache_get("sale"), result["items"])

    def test_invalid_names_rejected_before_directory_access(self):
        with patch.object(self.m, "_gog_rail_cache_dir") as directory:
            for name in ("../sale", "", "sale.json"):
                with self.assertRaises(ValueError):
                    self.m._gog_rail_cache_get(name)
                with self.assertRaises(ValueError):
                    self.m._gog_rail_cache_set(name, [])
            directory.assert_not_called()

    def test_replacement_failure_preserves_previous_and_cleans_temporary(self):
        self.write_cache()
        previous = self.path.read_bytes()
        with patch("os.replace", side_effect=OSError("replace failed")):
            self.m._gog_rail_cache_set("sale", [{"title": "New"}])
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_flush_failure_is_nonfatal_and_cleans_temporary(self):
        self.write_cache()
        previous = self.path.read_bytes()
        with patch("os.fsync", side_effect=OSError("flush failed")):
            self.m._gog_rail_cache_set("sale", [])
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_symlink_leaf_and_predictable_temporary_target_unchanged(self):
        target = self.root / "outside"
        target.write_text("untouched")
        self.path.symlink_to(target)
        predictable = self.path.with_suffix(".json.tmp")
        predictable.symlink_to(target)
        self.m._gog_rail_cache_set("sale", [])
        self.assertEqual(target.read_text(), "untouched")
        self.assertFalse(self.path.is_symlink())
        self.assertEqual(json.loads(self.path.read_text())["items"], [])

    def test_concurrent_writes_remain_valid_and_clean(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as workers:
            list(workers.map(lambda number: self.m._gog_rail_cache_set(
                "sale", [{"id": str(number)}]), range(32)))
        data = json.loads(self.path.read_text())
        self.assertEqual(data["v"], self.m.GOG_RAIL_POOL_V)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])


if __name__ == "__main__":
    unittest.main()
