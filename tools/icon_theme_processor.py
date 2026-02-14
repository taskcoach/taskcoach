#!/usr/bin/env python3
"""Common library for icon theme processing.

Used by icon_generate_labels.py, icon_next_hints.py, icon_duplicates.py,
icon_build_check_contexts.py, and icon_rebuild_catalog_sizes.py.

Provides ThemeCatalog (entry point) and Theme (single theme with lazy-loaded
properties and processing methods). Parses XDG index.theme files for
directory→metadata mapping. Every theme must have an index.theme file.
"""

import configparser
import hashlib
import json
import os
import re
import sys
from pathlib import Path


# Path to ICON_THEME_CATALOG.json
_SCRIPT_DIR = Path(__file__).parent
_PROJECT_DIR = _SCRIPT_DIR.parent
_CANON_THEMES_PATH = _SCRIPT_DIR / "ICON_THEME_CATALOG.json"

# Valid icon file extensions
ICON_EXTENSIONS = (".svg", ".svgz", ".png")

# Sentinel for lazy-loaded properties where None is a valid value
_SENTINEL = object()


def fatal_error(message):
    """Print a fatal error message and exit."""
    print(f"FATAL ERROR! {message}", file=sys.stderr)
    sys.exit(1)


def usage_error(docstring, message=None):
    """Print help (docstring) and optional error message, then exit."""
    print(docstring)
    if message:
        print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def save_json_compact_arrays(filepath, data):
    """Save JSON with indent=2 but arrays on single lines."""
    text = json.dumps(data, indent=2)
    def collapse_array(match):
        content = match.group(0)
        collapsed = re.sub(r'\[\s+', '[', content)
        collapsed = re.sub(r'\s+\]', ']', collapsed)
        collapsed = re.sub(r',\s+', ', ', collapsed)
        return collapsed
    text = re.sub(r'\[\s*\n\s+[^\[\]]*?\s*\]', collapse_array, text)
    if not text.endswith("\n"):
        text += "\n"
    with open(filepath, "w") as f:
        f.write(text)


class Theme:
    """Represents a single theme (variant-expanded).

    Created by ThemeCatalog — callers should not construct directly.
    Combines the previous standalone functions (get_theme_dir, load_theme_icons_data,
    load_theme_index, etc.) and ThemeProcessor methods into a single object with
    lazy-loaded properties.
    """

    def __init__(self, theme_id, theme_base_id, theme_dir, config):
        """Initialize a theme.

        Args:
            theme_id:      Expanded variant id (e.g., "papirus-dark", "oxygen")
            theme_base_id: Base catalog key (e.g., "papirus", "oxygen")
            theme_dir:     Relative path from project root (e.g., "papirus/Papirus-Dark")
            config:        Raw catalog config dict for the base theme
        """
        self.theme_id = theme_id
        self.theme_base_id = theme_base_id
        self.config = config
        self.dir = str(_PROJECT_DIR / theme_dir)
        self.icons_path = str(_PROJECT_DIR / theme_dir / "icons.json")
        self.contexts_path = str(_PROJECT_DIR / theme_dir / "contexts.json")

        # Lazy-loaded caches
        self._index = None
        self._context_map = None
        self._icons_data = None
        self._contexts = _SENTINEL
        self._xdg_to_internal = None

    # --- Lazy-loaded properties ---

    @property
    def index(self):
        """Parsed index.theme directory map. Fatal if missing."""
        if self._index is None:
            self._index = self._load_index()
        return self._index

    @property
    def context_map(self):
        """Dict mapping internal_context_id → list of index entries."""
        if self._context_map is None:
            self._context_map = self._build_context_map()
        return self._context_map

    @property
    def icons_data(self):
        """Parsed icons.json dict. Fatal if missing."""
        if self._icons_data is None:
            self._icons_data = self._load_icons_data()
        return self._icons_data

    @property
    def contexts(self):
        """Parsed contexts.json dict, or None if file doesn't exist."""
        if self._contexts is _SENTINEL:
            self._contexts = self._load_contexts()
        return self._contexts

    # --- Private loaders ---

    def _load_index(self):
        """Parse index.theme and return dir_map."""
        index_path = os.path.join(self.dir, "index.theme")
        if not os.path.isfile(index_path):
            fatal_error(f"index.theme not found: {index_path}")

        cfg = configparser.ConfigParser(interpolation=None)
        cfg.optionxform = str
        cfg.read(index_path, encoding="utf-8")

        if not cfg.has_section("Icon Theme"):
            fatal_error(f"index.theme has no [Icon Theme] section: "
                        f"{index_path}")

        dir_entries = []
        for key in ("Directories", "ScaledDirectories"):
            raw = cfg.get("Icon Theme", key, fallback="")
            if raw.strip():
                dir_entries.extend(d.strip() for d in raw.split(",")
                                  if d.strip())

        dir_map = {}
        for dir_entry in dir_entries:
            if not cfg.has_section(dir_entry):
                continue
            section = cfg[dir_entry]
            size = int(section.get("Size", "0"))
            scale = int(section.get("Scale", "1"))
            xdg_context = section.get("Context") or None
            type_ = section.get("Type", "Threshold")
            min_size = (int(section["MinSize"])
                        if "MinSize" in section else None)
            max_size = (int(section["MaxSize"])
                        if "MaxSize" in section else None)
            dir_map[dir_entry] = {
                "size": size,
                "scale": scale,
                "effective_size": size * scale,
                "xdg_context": xdg_context,
                "type": type_,
                "min_size": min_size,
                "max_size": max_size,
            }

        if not dir_map:
            fatal_error(f"index.theme has no directory entries: "
                        f"{index_path}")

        return dir_map

    def _get_internal_context_id(self, xdg_context):
        """Map xdg_context to internal_context_id using contexts.json."""
        if self._xdg_to_internal is None:
            if not self.contexts:
                fatal_error(f"contexts.json missing or empty for "
                            f"theme '{self.theme_id}'")
            self._xdg_to_internal = {}
            for ctx_id, ctx_info in self.contexts.items():
                xdg = ctx_info.get("xdg_context")
                if not xdg:
                    fatal_error(f"context '{ctx_id}' missing xdg_context "
                                f"in contexts.json for theme "
                                f"'{self.theme_id}'")
                self._xdg_to_internal[xdg] = ctx_id
        if xdg_context not in self._xdg_to_internal:
            fatal_error(f"xdg_context '{xdg_context}' not found "
                        f"in contexts.json for theme '{self.theme_id}'")
        return self._xdg_to_internal[xdg_context]

    def _build_context_map(self):
        """Build internal_context_id → list of index entries mapping."""
        context_map = {}
        for dir_path, meta in self.index.items():
            xdg_context = meta["xdg_context"]
            if xdg_context is None:
                continue
            internal_context_id = self._get_internal_context_id(xdg_context)
            entry = dict(meta)
            entry["dir"] = dir_path
            if internal_context_id not in context_map:
                context_map[internal_context_id] = []
            context_map[internal_context_id].append(entry)
        return context_map

    def _load_icons_data(self):
        """Load icons.json."""
        if not os.path.isfile(self.icons_path):
            fatal_error(f"icons.json not found: {self.icons_path}")
        with open(self.icons_path) as f:
            return json.load(f)

    def _load_contexts(self):
        """Load contexts.json. Returns dict or None if file doesn't exist."""
        if not os.path.isfile(self.contexts_path):
            return None
        with open(self.contexts_path) as f:
            return json.load(f)

    # --- Processing methods ---

    def strip_dir_base(self, path):
        """Strip theme dir from a path, return clean relative path."""
        _, rel = path.split(self.dir, 1)
        if rel.startswith("/"):
            rel = rel[1:]
        return rel

    def match_dir(self, path, is_file=False, strict=True):
        """Match a path against the index dir_map.

        Args:
            path: Directory path relative to theme root.
            is_file: If True, strip the filename before matching.
            strict: If True (default), fatal on no match.
                    If False, return None.
        """
        if is_file:
            path, _ = os.path.split(path)
        entry = self.index.get(path)
        if entry is None and strict:
            fatal_error(f"Directory '{path}' not found in index.theme "
                        f"for theme '{self.theme_id}'")
        return entry

    def generate_id(self, internal_context_id, filename):
        """Generate icon id: {theme}_{context}_{stem} or {theme}_{stem}."""
        stem = Path(filename).stem
        if internal_context_id:
            return f"{self.theme_id}_{internal_context_id}_{stem}"
        return f"{self.theme_id}_{stem}"

    def get_file_info(self, path):
        """Build file info dict for an icon file path."""
        rel = self.strip_dir_base(path)
        meta = self.match_dir(rel, is_file=True)
        return {
            "path": path,
            "rel_path": rel,
            "file": os.path.basename(path),
            "effective_size": meta["effective_size"],
            "xdg_context": meta["xdg_context"],
            "file_size": os.path.getsize(path),
        }

    def add_file_hash(self, file_info):
        """Add MD5 hash (12 hex chars) to file info dict."""
        with open(file_info["path"], "rb") as f:
            file_info["hash"] = hashlib.md5(f.read()).hexdigest()[:12]
        return file_info

    def validate_icon_data(self, icon_id, icon_data):
        """Validate icon_data has required file property.

        Returns dict {internal_context_id, file} or exits with fatal error.
        """
        internal_context_id = icon_data.get("context")
        filename = icon_data.get("file")
        if not filename:
            fatal_error(f"icon '{icon_id}' missing 'file' property")
        return {"internal_context_id": internal_context_id, "file": filename}

    def scan_directory(self, base=None):
        """Scan directory and build inventory of all icons found.

        Skips symlinks (both files and directories) and files in
        directories not in index.theme.
        Returns dict of {icon_id: {sizes, xdg_context, file, paths}}
        """
        if base is None:
            base = self.dir
        base_str = str(base)
        exts = ICON_EXTENSIONS
        all_files = []
        for dirpath, dirnames, filenames in os.walk(base_str):
            dirnames[:] = [d for d in dirnames
                           if not os.path.islink(os.path.join(dirpath, d))]
            for fn in filenames:
                if fn.lower().endswith(exts):
                    full = os.path.join(dirpath, fn)
                    if not os.path.islink(full):
                        all_files.append(full)
        base = Path(base_str)

        discovered = {}
        dir_cache = {}
        skipped_dirs = {}
        skipped_exts = {}
        for f in all_files:
            rel = os.path.relpath(f, base_str)
            dir_part, filename = os.path.split(rel)
            if dir_part not in dir_cache:
                dir_cache[dir_part] = self.match_dir(dir_part, strict=False)
            meta = dir_cache[dir_part]
            if meta is None:
                _, ext = os.path.splitext(filename)
                ext = ext.lower().lstrip(".")
                if dir_part not in skipped_dirs:
                    skipped_dirs[dir_part] = {}
                skipped_dirs[dir_part][ext] = (
                    skipped_dirs[dir_part].get(ext, 0) + 1)
                skipped_exts[ext] = skipped_exts.get(ext, 0) + 1
                continue
            size = meta["effective_size"]
            xdg_context = meta["xdg_context"]
            internal_context_id = (self._get_internal_context_id(xdg_context)
                                   if xdg_context else None)
            key = self.generate_id(internal_context_id, filename)
            if key not in discovered:
                discovered[key] = {
                    "sizes": set(), "paths": {},
                    "xdg_context": xdg_context, "file": filename,
                }
            discovered[key]["sizes"].add(size)
            if size not in discovered[key]["paths"]:
                discovered[key]["paths"][size] = []
            discovered[key]["paths"][size].append(str(f))

        if skipped_dirs:
            print(f"  Skipped files in directories not in index.theme:")
            for d in sorted(skipped_dirs):
                dir_exts = skipped_dirs[d]
                dir_total = sum(dir_exts.values())
                ext_detail = ", ".join(
                    f"{e} {dir_exts[e]}" for e in sorted(dir_exts))
                print(f"    {d}/  {dir_total} files ({ext_detail})")
            total = sum(skipped_exts.values())
            exts = ", ".join(f"{e} {skipped_exts[e]}"
                            for e in sorted(skipped_exts))
            print(f"  Total skipped: {total} files ({exts})")
            print()

        for info in discovered.values():
            info["sizes"] = sorted(info["sizes"])
        return discovered

    def find_all_on_disk(self, filename):
        """Find all files matching filename across the theme directory.

        Skips symlinks (both files and directories).
        Returns (matched, unmatched) tuple of path lists.
        """
        stem = Path(filename).stem
        matched = []
        unmatched = []
        for dirpath, dirnames, filenames in os.walk(self.dir):
            dirnames[:] = [d for d in dirnames
                           if not os.path.islink(os.path.join(dirpath, d))]
            for fn in filenames:
                fn_stem, ext = os.path.splitext(fn)
                if fn_stem != stem:
                    continue
                full = os.path.join(dirpath, fn)
                if os.path.islink(full):
                    continue
                ext = ext.lower()
                if ext not in ICON_EXTENSIONS:
                    fatal_error(f"Unexpected file type '{ext}' for "
                                f"'{full}' in theme '{self.theme_id}'")
                rel = self.strip_dir_base(full)
                dir_part, _ = os.path.split(rel)
                if self.index and dir_part in self.index:
                    matched.append(full)
                else:
                    unmatched.append(full)
        return matched, unmatched

    def find_icon_files_in_context(self, internal_context_id, filename):
        """Find all size variants of an icon within its context.

        Returns list of absolute path strings.
        Skips directories reached through symlinks (e.g. @2x dirs).
        """
        if internal_context_id not in self.context_map:
            fatal_error(f"Context '{internal_context_id}' not found "
                        f"in index for theme '{self.theme_id}'")

        stem = Path(filename).stem
        hits = []
        for entry in self.context_map[internal_context_id]:
            dir_path = os.path.join(self.dir, entry["dir"])
            if os.path.realpath(dir_path) != os.path.abspath(dir_path):
                continue
            for match in Path(dir_path).glob(stem + ".*"):
                if match.is_symlink():
                    continue
                ext = match.suffix.lower()
                if ext not in ICON_EXTENSIONS:
                    fatal_error(f"Unexpected file type '{ext}' for "
                                f"'{match}' in theme '{self.theme_id}'")
                hits.append(str(match))
        return hits

    def convert_svg_to_png(self, svg_path):
        """Convert SVG to PNG. Returns png_path or error string."""
        rel = self.strip_dir_base(svg_path)
        meta = self.match_dir(rel, is_file=True)
        size = meta["effective_size"]
        png_path = str(Path(svg_path).with_suffix(".png"))
        if os.path.exists(png_path):
            return png_path
        try:
            import cairosvg
            cairosvg.svg2png(url=svg_path, write_to=png_path,
                            output_width=size, output_height=size)
            return png_path
        except Exception as e:
            return f"SVG conversion failed: {svg_path} - {e}"


class ThemeCatalog:
    """Manages the icon theme catalog. Entry point for all theme access.

    Loads ICON_THEME_CATALOG.json, expands variants into Theme objects.
    Skipped themes (skip=True) are excluded from theme_ids().

    Usage:
        catalog = ThemeCatalog()
        theme = catalog.get_theme("oxygen")
        theme.icons_data  # lazy-loaded
        theme.index       # lazy-loaded

        for theme_id in catalog.theme_ids():
            theme = catalog.get_theme(theme_id)
    """

    def __init__(self):
        self._path = str(_CANON_THEMES_PATH)

        if not _CANON_THEMES_PATH.is_file():
            fatal_error(f"Theme catalog not found: {_CANON_THEMES_PATH}")

        with open(_CANON_THEMES_PATH) as f:
            self._raw = json.load(f)

        self._themes = {}
        self._skipped = {}

        for base_id, config in self._raw.items():
            variants = config.get("variants", [])
            skip = config.get("skip", False)

            if not variants:
                theme = Theme(base_id, base_id, base_id, config)
                if skip:
                    self._skipped[base_id] = theme
                else:
                    self._themes[base_id] = theme
            else:
                for variant in variants:
                    vid = variant["id"]
                    theme_dir = f"{base_id}/{variant['dir']}"
                    theme = Theme(vid, base_id, theme_dir, config)
                    if skip:
                        self._skipped[vid] = theme
                    else:
                        self._themes[vid] = theme

    def get_theme(self, theme_id):
        """Look up theme by id, print header, return Theme.

        Standard entry point for all scripts needing a Theme.
        Fatal if theme_id not found.
        """
        if theme_id in self._themes:
            theme = self._themes[theme_id]
        elif theme_id in self._skipped:
            theme = self._skipped[theme_id]
        else:
            # Helpful error for base theme id when variants exist
            if theme_id in self._raw:
                variants = self._raw[theme_id].get("variants", [])
                if variants:
                    ids = ", ".join(v["id"] for v in variants)
                    fatal_error(f"Theme '{theme_id}' has variants. "
                                f"Use one of: {ids}")
            all_ids = ", ".join(sorted(self._themes.keys()))
            fatal_error(f"Theme '{theme_id}' not found. Available: {all_ids}")
        print(f"Theme: {theme.theme_id}")
        print(f"Directory: {theme.dir}")
        return theme

    def theme_ids(self):
        """Return sorted list of non-skipped theme ids."""
        return sorted(self._themes.keys())

    def catalog_path(self):
        """Return path to ICON_THEME_CATALOG.json."""
        return self._path

    def print_available(self):
        """Print available/missing themes to stderr."""
        for base_id in sorted(self._raw.keys()):
            if (_PROJECT_DIR / base_id).is_dir():
                print(f"  {base_id}: Available", file=sys.stderr)
            else:
                print(f"  {base_id}: Directory not found", file=sys.stderr)


