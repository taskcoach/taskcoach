#!/usr/bin/env python3
"""Unit tests for icon_grid_browser.py catalog generation and idempotency."""

import json
import shutil
import tempfile
import time
import unittest
import importlib.util
from pathlib import Path

import wx

# Load the module under test via importlib (it's not a package)
_SCRIPT = Path(__file__).resolve().parent / "icon_grid_browser.py"
_spec = importlib.util.spec_from_file_location("icon_grid_browser", str(_SCRIPT))
igb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(igb)


class _BaseLoaderTest(unittest.TestCase):
    """Shared setup: wx.App, temp data dir, model instance."""

    app = None

    @classmethod
    def setUpClass(cls):
        if _BaseLoaderTest.app is None:
            _BaseLoaderTest.app = wx.App(False)

    def setUp(self):
        self._orig_data_dir = igb.DATA_DIR
        self._tmpdir = tempfile.mkdtemp(prefix="igb_test_")
        igb.DATA_DIR = Path(self._tmpdir)
        self.model = igb.IconDataModel()

    def tearDown(self):
        igb.DATA_DIR = self._orig_data_dir
        shutil.rmtree(self._tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Internal icons
# ---------------------------------------------------------------------------

class TestInternalLoader(_BaseLoaderTest):

    def test_creates_catalog(self):
        self.model.load_internal()
        self.assertTrue((igb.DATA_DIR / "internal.json").exists())

    def test_has_entries(self):
        self.model.load_internal()
        count = sum(1 for k in self.model._entries if k[0] == "internal")
        self.assertGreater(count, 100)

    def test_discovers_sizes(self):
        self.model.load_internal()
        self.assertIn(16, self.model.discovered_sizes)
        self.assertGreater(len(self.model.discovered_sizes), 1)

    def test_catalog_valid_json(self):
        self.model.load_internal()
        data = json.loads((igb.DATA_DIR / "internal.json").read_text())
        self.assertIn("icons", data)
        self.assertIn("_comment", data)
        self.assertNotIn("_updated", data)

    def test_idempotent(self):
        self.model.load_internal()
        content1 = (igb.DATA_DIR / "internal.json").read_text()

        model2 = igb.IconDataModel()
        model2.load_internal()
        content2 = (igb.DATA_DIR / "internal.json").read_text()

        self.assertEqual(content1, content2)


# ---------------------------------------------------------------------------
# Theme tests (parameterized via subclass)
# ---------------------------------------------------------------------------

class _ThemePackTest(_BaseLoaderTest):
    theme_id = None  # override in subclass
    min_icons = 10

    def setUp(self):
        if type(self) is _ThemePackTest:
            self.skipTest("base class")
        super().setUp()

    def _available(self):
        theme_info = igb.LOCAL_THEMES.get(self.theme_id)
        return theme_info and Path(theme_info["search_root"]).exists()

    def _load(self):
        self.model.load_internal()
        self.model.load_theme(self.theme_id)

    def test_creates_catalog(self):
        if not self._available():
            self.skipTest(f"{self.theme_id} not on disk")
        self._load()
        self.assertTrue((igb.DATA_DIR / f"{self.theme_id}.json").exists())

    def test_has_entries(self):
        if not self._available():
            self.skipTest(f"{self.theme_id} not on disk")
        self._load()
        count = sum(1 for k in self.model._entries if k[0] == self.theme_id)
        self.assertGreaterEqual(count, self.min_icons)

    def test_catalog_valid_json(self):
        if not self._available():
            self.skipTest(f"{self.theme_id} not on disk")
        self._load()
        data = json.loads((igb.DATA_DIR / f"{self.theme_id}.json").read_text())
        self.assertIn("icons", data)
        self.assertNotIn("_updated", data)
        for cat_file, info in data["icons"].items():
            self.assertIn("sizes", info, f"{cat_file} missing sizes")
            self.assertGreater(len(info["sizes"]), 0, f"{cat_file} empty sizes")

    def test_no_leaked_browser_hints(self):
        """Catalog should not contain hints from the deleted ICON_BROWSER_HINTS.json."""
        if not self._available():
            self.skipTest(f"{self.theme_id} not on disk")
        self._load()
        data = json.loads((igb.DATA_DIR / f"{self.theme_id}.json").read_text())
        hints_count = sum(1 for v in data["icons"].values() if "hints" in v)
        self.assertEqual(hints_count, 0,
                         "Fresh catalog should have no hints (hints are tool-generated only)")

    def test_discovers_sizes(self):
        if not self._available():
            self.skipTest(f"{self.theme_id} not on disk")
        self._load()
        self.assertGreater(len(self.model.discovered_sizes), 0)

    def test_idempotent(self):
        if not self._available():
            self.skipTest(f"{self.theme_id} not on disk")
        self._load()
        content1 = (igb.DATA_DIR / f"{self.theme_id}.json").read_text()

        model2 = igb.IconDataModel()
        model2.load_internal()
        model2.load_theme(self.theme_id)
        content2 = (igb.DATA_DIR / f"{self.theme_id}.json").read_text()

        self.assertEqual(content1, content2)


class TestPapirus(_ThemePackTest):
    theme_id = "papirus"
    min_icons = 5000


class TestOxygen(_ThemePackTest):
    theme_id = "oxygen"
    min_icons = 500


class TestNuvola(_ThemePackTest):
    theme_id = "nuvola"
    min_icons = 200


class TestBreeze(_ThemePackTest):
    theme_id = "breeze"
    min_icons = 1000


# ---------------------------------------------------------------------------
# Catalog merge logic
# ---------------------------------------------------------------------------

class TestCatalogMerge(_BaseLoaderTest):

    def test_additive_sizes(self):
        self.model._save_catalog("test", {"test_actions_test": {"sizes": [16], "category": "actions", "file": "test.svg"}})
        merged = self.model._merge_catalog("test", {"test_actions_test": {"sizes": [32], "category": "actions", "file": "test.svg"}})
        self.assertEqual(merged["test_actions_test"]["sizes"], [16, 32])

    def test_additive_icons(self):
        self.model._save_catalog("test", {"test_actions_old": {"sizes": [16], "category": "actions", "file": "old.svg"}})
        merged = self.model._merge_catalog("test", {"test_actions_new": {"sizes": [22], "category": "actions", "file": "new.svg"}})
        self.assertIn("test_actions_old", merged)
        self.assertIn("test_actions_new", merged)

    def test_missing_icon_preserved(self):
        self.model._save_catalog("test", {"test_actions_gone": {"sizes": [16], "category": "actions", "file": "gone.svg"}})
        merged = self.model._merge_catalog("test", {"test_actions_new": {"sizes": [22], "category": "actions", "file": "new.svg"}})
        self.assertIn("test_actions_gone", merged)

    def test_hints_updatable(self):
        self.model._save_catalog("test", {"test_a_t": {"sizes": [16], "category": "a", "file": "t.svg", "hints": ["old"]}})
        merged = self.model._merge_catalog("test", {"test_a_t": {"sizes": [16], "category": "a", "file": "t.svg", "hints": ["new"]}})
        self.assertEqual(merged["test_a_t"]["hints"], ["new"])

    def test_inherits_updatable(self):
        self.model._save_catalog("test", {"test_a_t": {"sizes": [16], "category": "a", "file": "t.svg", "hints": ["old"]}})
        merged = self.model._merge_catalog("test", {"test_a_t": {"sizes": [16], "category": "a", "file": "t.svg", "inherits": "x"}})
        self.assertEqual(merged["test_a_t"]["inherits"], "x")

    def test_skip_write_when_unchanged(self):
        icons = {"test_actions_test": {"sizes": [16], "category": "actions", "file": "test.svg"}}
        self.model._save_catalog("test", icons)
        mtime1 = (igb.DATA_DIR / "test.json").stat().st_mtime
        time.sleep(0.05)
        self.model._save_catalog("test", icons)
        mtime2 = (igb.DATA_DIR / "test.json").stat().st_mtime
        self.assertEqual(mtime1, mtime2)


if __name__ == "__main__":
    unittest.main()
