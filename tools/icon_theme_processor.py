#!/usr/bin/env python3
"""Common library for icon theme processing.

Used by icon_grid_browser.py, icon_next_hints.py, and icon_duplicates.py.
Provides ThemeProcessor class for parsing, scanning, and key generation.
"""

import json
import os
import re
import sys
from pathlib import Path


# Path to ICON_THEME_CATALOG.json
_SCRIPT_DIR = Path(__file__).parent
_PROJECT_DIR = _SCRIPT_DIR.parent
_CANON_THEMES_PATH = _PROJECT_DIR / "taskcoachlib" / "gui" / "icons" / "ICON_THEME_CATALOG.json"

# Cached catalog (loaded once)
_canon_themes_cache = None


def load_canon_themes():
    """Load canonical theme catalog from ICON_THEME_CATALOG.json."""
    global _canon_themes_cache
    if _canon_themes_cache is not None:
        return _canon_themes_cache

    if not _CANON_THEMES_PATH.is_file():
        print(f"FATAL ERROR! Theme catalog not found: {_CANON_THEMES_PATH}")
        sys.exit(1)

    with open(_CANON_THEMES_PATH) as f:
        _canon_themes_cache = json.load(f)
    return _canon_themes_cache


def get_theme_config(theme):
    """Get config for a theme from the catalog."""
    catalog = load_canon_themes()
    config = catalog.get(theme)
    if not config:
        print(f"FATAL ERROR! Theme '{theme}' not found in ICON_THEME_CATALOG.json")
        sys.exit(1)
    return config


class ThemeProcessor:
    """Processes icons for a single theme. All methods know current theme via self."""

    def __init__(self, theme, search_root=None):
        """Initialize processor for a theme.

        Args:
            theme: Theme identifier (e.g., "oxygen", "legacy")
            search_root: Root directory to search for icons (optional)
        """
        self.theme = theme
        self.config = get_theme_config(theme)
        self.search_root = search_root

    def _get_pattern_tokens(self):
        """Get pattern tokens from path_pattern (without {theme}/ prefix)."""
        pattern = self.config.get("path_pattern")
        if not pattern:
            print(f"FATAL ERROR! Theme '{self.theme}' missing 'path_pattern'")
            sys.exit(1)
        # Remove {theme}/ prefix if present
        if pattern.startswith("{theme}/"):
            pattern = pattern[8:]
        return pattern.split("/")

    def parse(self, path):
        """Parse path using sequential matching against path_pattern.

        Returns dict {size, category, file} or None if path doesn't match.
        FATAL ERROR if category/size not in catalog's valid lists.
        """
        # Get path relative to search_root
        if self.search_root and path.startswith(str(self.search_root)):
            rel_path = path[len(str(self.search_root)):].lstrip("/")
        else:
            rel_path = str(path)

        # Legacy exception: two formats, no categories
        if self.theme == "legacy":
            result = {"size": None, "category": None, "file": None}
            if "/" in rel_path:
                # Sized directory: 16x16/icon.png
                m = re.match(r'^(\d+)x(\d+)/(.+)$', rel_path)
                if m and m.group(1) == m.group(2):
                    result["size"] = int(m.group(1))
                    result["file"] = m.group(3)
                    return result
            else:
                # Flat file: add16x16.png
                m = re.match(r'^(.+?)(\d+)x(\d+)\.(png|svg)$', rel_path)
                if m and m.group(2) == m.group(3):
                    result["size"] = int(m.group(2))
                    result["file"] = f"{m.group(1)}.{m.group(4)}"
                    return result
            return None

        tokens = self._get_pattern_tokens()
        parts = rel_path.split("/")

        # Check part count matches token count
        if len(parts) != len(tokens):
            return None

        result = {"size": None, "category": None, "file": None}
        valid_categories = set(self.config.get("categories", []))
        valid_sizes = set(self.config.get("sizes", []))

        for token, part in zip(tokens, parts):
            if token == "{file}":
                result["file"] = part
            elif token == "{category}":
                if valid_categories and part not in valid_categories:
                    print(f"FATAL ERROR! category '{part}' not in catalog's categories: {sorted(valid_categories)}")
                    sys.exit(1)
                result["category"] = part
            elif "{size}" in token:
                # Extract leading digits (handles 64x64, 64x64@2x, 16, etc.)
                match = re.match(r"(\d+)", part)
                if not match:
                    return None
                size = int(match.group(1))
                if valid_sizes and size not in valid_sizes:
                    print(f"FATAL ERROR! size '{size}' not in catalog's sizes: {sorted(valid_sizes)}")
                    sys.exit(1)
                result["size"] = size
            else:
                # Unknown token, path doesn't match pattern
                return None

        return result

    def generate_key(self, category, filename):
        """Generate icon key: {theme}_{category}_{stem} or {theme}_{stem} if no category."""
        stem = Path(filename).stem
        if category:
            return f"{self.theme}_{category}_{stem}"
        return f"{self.theme}_{stem}"

    def scan_directory(self, base=None):
        """Scan directory and build inventory of all icons found.

        Returns dict of {key: {"sizes": [...], "category": str, "file": str}}
        """
        if base is None:
            base = self.search_root
        if base is None:
            print(f"FATAL ERROR! No directory to scan for theme '{self.theme}'")
            sys.exit(1)

        base = Path(base)
        all_files = list(base.rglob("*.svg")) + list(base.rglob("*.png"))

        discovered = {}
        for f in all_files:
            if "-symbolic" in f.name:
                continue

            parsed = self.parse(str(f))
            if not parsed:
                continue

            size = parsed["size"]
            category = parsed["category"]
            filename = parsed["file"]

            key = self.generate_key(category, filename)

            if key not in discovered:
                discovered[key] = {"sizes": set(), "paths": {}, "category": category, "file": filename}
            discovered[key]["sizes"].add(size)
            discovered[key]["paths"][size] = str(f)

        # Convert sizes sets to sorted lists
        for info in discovered.values():
            info["sizes"] = sorted(info["sizes"])
        return discovered

    def validate_icon_data(self, icon_key, icon_data):
        """Validate icon_data has required category and file properties.

        Returns dict {category, file} or exits with fatal error if invalid.
        """
        category = icon_data.get("category")
        filename = icon_data.get("file")

        if not filename:
            print(f"FATAL ERROR! icon '{icon_key}' missing 'file' property")
            sys.exit(1)

        has_categories = bool(self.config.get("categories"))
        if has_categories:
            if not category:
                print(f"FATAL ERROR! icon '{icon_key}' missing 'category' property")
                sys.exit(1)
            valid_categories = set(self.config["categories"])
            if category not in valid_categories:
                print(f"FATAL ERROR! category '{category}' not in theme's categories: {sorted(valid_categories)}")
                sys.exit(1)

        return {"category": category, "file": filename}

    def _build_glob_pattern(self, category, filename):
        """Build glob pattern from path_pattern with size as wildcard."""
        pattern = self.config.get("path_pattern", "")
        pattern = pattern.replace("{size}x{size}", "*")
        pattern = pattern.replace("{size}", "*")
        if category:
            pattern = pattern.replace("{category}", category)
        pattern = pattern.replace("{file}", filename)
        if pattern.startswith("{theme}/"):
            pattern = pattern[8:]
        if self.search_root:
            return os.path.join(str(self.search_root), pattern)
        return pattern

    def find_all_on_disk(self, filename, category=None):
        """Find all files using glob with size wildcard.

        Args:
            filename: e.g., "face-angel.png"
            category: e.g., "emotes" (None for themes without categories)
        """
        import glob
        stem = Path(filename).stem
        hits = []
        for ext in (".png", ".svg"):
            pattern = self._build_glob_pattern(category, stem + ext)
            hits.extend(glob.glob(pattern))
        return hits

    def convert_svg_to_png(self, svg_path):
        """Convert SVG to PNG. Returns png_path on success, or error string on failure."""
        parsed = self.parse(svg_path)
        if not parsed:
            return f"path_pattern did not match: {svg_path}"

        size = parsed["size"]
        png_path = svg_path[:-4] + ".png"

        if os.path.exists(png_path):
            return png_path

        try:
            import cairosvg
            cairosvg.svg2png(url=svg_path, write_to=png_path,
                            output_width=size, output_height=size)
            return png_path
        except Exception as e:
            return f"SVG conversion failed: {svg_path} - {e}"
