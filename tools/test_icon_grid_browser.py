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
# Theme pack tests (parameterized via subclass)
# ---------------------------------------------------------------------------

class _ThemePackTest(_BaseLoaderTest):
    pack_id = None  # override in subclass
    min_icons = 10

    def setUp(self):
        if type(self) is _ThemePackTest:
            self.skipTest("base class")
        super().setUp()

    def _available(self):
        pack = igb.THEME_PACKS.get(self.pack_id)
        return pack and Path(pack["path"]).exists()

    def _load(self):
        self.model.load_internal()
        self.model.load_theme_pack(self.pack_id)

    def test_creates_catalog(self):
        if not self._available():
            self.skipTest(f"{self.pack_id} not on disk")
        self._load()
        self.assertTrue((igb.DATA_DIR / f"{self.pack_id}.json").exists())

    def test_has_entries(self):
        if not self._available():
            self.skipTest(f"{self.pack_id} not on disk")
        self._load()
        count = sum(1 for k in self.model._entries if k[0] == self.pack_id)
        self.assertGreaterEqual(count, self.min_icons)

    def test_catalog_valid_json(self):
        if not self._available():
            self.skipTest(f"{self.pack_id} not on disk")
        self._load()
        data = json.loads((igb.DATA_DIR / f"{self.pack_id}.json").read_text())
        self.assertIn("icons", data)
        self.assertNotIn("_updated", data)
        for cat_file, info in data["icons"].items():
            self.assertIn("sizes", info, f"{cat_file} missing sizes")
            self.assertGreater(len(info["sizes"]), 0, f"{cat_file} empty sizes")

    def test_no_leaked_browser_hints(self):
        """Catalog should not contain hints from the deleted ICON_BROWSER_HINTS.json."""
        if not self._available():
            self.skipTest(f"{self.pack_id} not on disk")
        self._load()
        data = json.loads((igb.DATA_DIR / f"{self.pack_id}.json").read_text())
        hints_count = sum(1 for v in data["icons"].values() if "hints" in v)
        self.assertEqual(hints_count, 0,
                         "Fresh catalog should have no hints (hints are tool-generated only)")

    def test_discovers_sizes(self):
        if not self._available():
            self.skipTest(f"{self.pack_id} not on disk")
        self._load()
        self.assertGreater(len(self.model.discovered_sizes), 0)

    def test_idempotent(self):
        if not self._available():
            self.skipTest(f"{self.pack_id} not on disk")
        self._load()
        content1 = (igb.DATA_DIR / f"{self.pack_id}.json").read_text()

        model2 = igb.IconDataModel()
        model2.load_internal()
        model2.load_theme_pack(self.pack_id)
        content2 = (igb.DATA_DIR / f"{self.pack_id}.json").read_text()

        self.assertEqual(content1, content2)


class TestPapirus(_ThemePackTest):
    pack_id = "papirus"
    min_icons = 5000


class TestOxygen(_ThemePackTest):
    pack_id = "oxygen"
    min_icons = 500


class TestNuvolaLocalZip(_ThemePackTest):
    pack_id = "nuvola_local_zip"
    min_icons = 200


class TestNuvolaGithub(_ThemePackTest):
    pack_id = "nuvola_github"
    min_icons = 200


class TestBreeze(_ThemePackTest):
    pack_id = "breeze"
    min_icons = 1000


# ---------------------------------------------------------------------------
# Catalog merge logic
# ---------------------------------------------------------------------------

class TestCatalogMerge(_BaseLoaderTest):

    def test_additive_sizes(self):
        self.model._save_catalog("test", {"actions/test.svg": {"sizes": [16]}})
        merged = self.model._merge_catalog("test", {"actions/test.svg": {"sizes": [32]}})
        self.assertEqual(merged["actions/test.svg"]["sizes"], [16, 32])

    def test_additive_icons(self):
        self.model._save_catalog("test", {"actions/old.svg": {"sizes": [16]}})
        merged = self.model._merge_catalog("test", {"actions/new.svg": {"sizes": [22]}})
        self.assertIn("actions/old.svg", merged)
        self.assertIn("actions/new.svg", merged)

    def test_missing_icon_preserved(self):
        self.model._save_catalog("test", {"actions/gone.svg": {"sizes": [16]}})
        merged = self.model._merge_catalog("test", {"actions/new.svg": {"sizes": [22]}})
        self.assertIn("actions/gone.svg", merged)

    def test_hints_updatable(self):
        self.model._save_catalog("test", {"a/t.svg": {"sizes": [16], "hints": ["old"]}})
        merged = self.model._merge_catalog("test", {"a/t.svg": {"sizes": [16], "hints": ["new"]}})
        self.assertEqual(merged["a/t.svg"]["hints"], ["new"])

    def test_inherits_updatable(self):
        self.model._save_catalog("test", {"a/t.svg": {"sizes": [16], "hints": ["old"]}})
        merged = self.model._merge_catalog("test", {"a/t.svg": {"sizes": [16], "inherits": "x"}})
        self.assertEqual(merged["a/t.svg"]["inherits"], "x")

    def test_skip_write_when_unchanged(self):
        icons = {"actions/test.svg": {"sizes": [16]}}
        self.model._save_catalog("test", icons)
        mtime1 = (igb.DATA_DIR / "test.json").stat().st_mtime
        time.sleep(0.05)
        self.model._save_catalog("test", icons)
        mtime2 = (igb.DATA_DIR / "test.json").stat().st_mtime
        self.assertEqual(mtime1, mtime2)


# ---------------------------------------------------------------------------
# Generic directory scanner
# ---------------------------------------------------------------------------

class TestScanIconDirectory(_BaseLoaderTest):

    def _tree(self, base, files):
        for f in files:
            p = base / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"\x89PNG")  # minimal fake

    def test_nxn_layout(self):
        base = Path(self._tmpdir) / "nxn"
        self._tree(base, ["16x16/actions/test.png", "32x32/actions/test.png",
                          "16x16/apps/other.svg"])
        result = self.model._scan_icon_directory(base)
        self.assertEqual(sorted(result["actions/test.png"]["sizes"]), [16, 32])
        self.assertIn("apps/other.svg", result)

    def test_bare_layout(self):
        base = Path(self._tmpdir) / "bare"
        self._tree(base, ["actions/16/test.svg", "actions/22/test.svg"])
        result = self.model._scan_icon_directory(base)
        self.assertEqual(sorted(result["actions/test.svg"]["sizes"]), [16, 22])

    def test_legacy_layout(self):
        base = Path(self._tmpdir) / "legacy"
        self._tree(base, ["person16x16.png", "person32x32.png"])
        result = self.model._scan_icon_directory(base)
        self.assertIn("_legacy/person.png", result)
        self.assertEqual(sorted(result["_legacy/person.png"]["sizes"]), [16, 32])

    def test_symbolic_excluded(self):
        base = Path(self._tmpdir) / "sym"
        self._tree(base, ["16x16/actions/test.svg", "16x16/actions/test-symbolic.svg"])
        result = self.model._scan_icon_directory(base)
        self.assertIn("actions/test.svg", result)
        self.assertNotIn("actions/test-symbolic.svg", result)

    def test_sizes_added_to_discovered(self):
        base = Path(self._tmpdir) / "disc"
        self._tree(base, ["42x42/actions/test.png"])
        self.model._scan_icon_directory(base)
        self.assertIn(42, self.model._discovered_sizes)


if __name__ == "__main__":
    unittest.main()
