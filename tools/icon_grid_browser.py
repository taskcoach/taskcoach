#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Icon Grid Browser — Standalone dev tool for browsing TaskCoach icons
and external icon theme packs.

Usage:
    python tools/icon_grid_browser.py

Requires: wxPython (from TaskCoach), cairosvg (for SVG rendering)
"""

import sys
import os
import re
import json
import io
from pathlib import Path
from dataclasses import dataclass, field

# --- Dependency check (only extras beyond TaskCoach requirements) ---
try:
    import cairosvg
except ImportError:
    print("ERROR: cairosvg is required for SVG icon rendering.")
    print("  Install: pip install cairosvg  or  sudo apt install python3-cairosvg")
    sys.exit(1)

import wx

# --- Path setup ---
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
ICONS_DIR = REPO_ROOT / "taskcoachlib" / "gui" / "icons"
ARTPROVIDER_PATH = REPO_ROOT / "taskcoachlib" / "gui" / "artprovider.py"
ICON_MAPPING_PATH = ICONS_DIR / "ICON_MAPPING.json"
ICON_SOURCES_PATH = ICONS_DIR / "ICON_SOURCES.json"
EXTERNAL_ICONS_BASE = REPO_ROOT.parent / "icons"
DATA_DIR = SCRIPT_DIR / "icon_grid_browser_data"


# Theme pack definitions: (id, label, base_path, path_pattern_func)
# path_pattern_func(base, size, category, filename) -> Path
THEME_PACKS = {
    "nuvola_local_zip": {
        "label": "Nuvola (Local Zip)",
        "path": str(EXTERNAL_ICONS_BASE / "nuvola_local_zip"),
        "license": "LGPL-2.1",
    },
    "nuvola_github": {
        "label": "Nuvola (GitHub)",
        "path": str(EXTERNAL_ICONS_BASE / "nuvola-icon-theme-master" / "usr" / "share" / "icons" / "nuvola"),
        "license": "LGPL-2.1",
    },
    "papirus": {
        "label": "Papirus",
        "path": str(EXTERNAL_ICONS_BASE / "papirus-icon-theme-master" / "Papirus"),
        "license": "GPL-3.0",
    },
    "breeze": {
        "label": "Breeze",
        "path": str(EXTERNAL_ICONS_BASE / "breeze-icons-master" / "icons"),
        "license": "LGPL-2.1",
    },
    "oxygen": {
        "label": "Oxygen",
        "path": str(EXTERNAL_ICONS_BASE / "oxygen-icons-master"),
        "license": "LGPL-2.1",
    },
}


# ============================================================================
# Data Layer
# ============================================================================

@dataclass
class IconEntry:
    id: str
    name: str = ""
    hints: list = field(default_factory=list)
    source: str = ""  # nuvola, papirus, breeze, oxygen
    category: str = ""
    status: str = "external"  # included, duplicate, legacy, external
    sizes: dict = field(default_factory=dict)  # size -> path_str
    duplicates: list = field(default_factory=list)
    original_file: str = ""  # original filename in source library



class IconDataModel:
    """Loads and indexes all icon data from repo files and external theme packs."""

    def __init__(self):
        self._entries = {}  # key -> IconEntry
        self._chooseable_ids = set()
        self._chooseable_hints = {}  # tc_icon_id -> list of hint strings
        self._icon_mapping = {}
        self._icon_sources = {}
        self._bitmap_cache = {}  # (key, size) -> wx.Bitmap
        self._discovered_sizes = set()  # all sizes seen across all packs

    @property
    def discovered_sizes(self):
        """All icon sizes discovered across all loaded packs, sorted."""
        return sorted(self._discovered_sizes)

    def load_internal(self):
        """Load internal icons: artprovider metadata, ICON_MAPPING, disk files."""
        self._load_artprovider()
        self._load_icon_mapping()
        self._load_icon_sources()
        self._scan_disk_icons()
        self._save_internal_catalog()

    def _load_artprovider(self):
        """Parse chooseableItems from artprovider.py via regex."""
        if not ARTPROVIDER_PATH.exists():
            return
        content = ARTPROVIDER_PATH.read_text()

        # Match both _icon and non-_icon entries
        pattern = r'"(\w+)":\s*\{\s*"name":\s*_\("([^"]+)"\),\s*"hints":\s*\[([^\]]*)\]'
        start = content.find("chooseableItems")
        if start < 0:
            return
        section = content[start:]

        for m in re.finditer(pattern, section):
            icon_id = m.group(1)
            name = m.group(2)
            hints_raw = m.group(3)
            hints = [hm.group(1) for hm in re.finditer(r'_\("([^"]+)"\)', hints_raw)]

            self._chooseable_ids.add(icon_id)
            self._chooseable_hints[icon_id] = hints
            key = ("internal", icon_id)
            if key not in self._entries:
                self._entries[key] = IconEntry(id=icon_id)
            entry = self._entries[key]
            entry.name = name
            entry.hints = hints
            entry.status = "included"

    def _load_icon_mapping(self):
        """Load ICON_MAPPING.json for provenance data."""
        if not ICON_MAPPING_PATH.exists():
            return
        data = json.loads(ICON_MAPPING_PATH.read_text())
        for icon_id, info in data.items():
            if icon_id.startswith("_"):
                continue
            if not isinstance(info, dict):
                continue
            self._icon_mapping[icon_id] = info
            key = ("internal", icon_id)
            if key in self._entries:
                entry = self._entries[key]
                entry.source = info.get("source", "")
                entry.category = info.get("category", "")
                entry.original_file = info.get("file", "")
                entry.duplicates = info.get("duplicates", [])

    def _load_icon_sources(self):
        """Load ICON_SOURCES.json."""
        if not ICON_SOURCES_PATH.exists():
            return
        self._icon_sources = json.loads(ICON_SOURCES_PATH.read_text())

    # --- Catalog load/save/merge ---

    def _catalog_path(self, pack_id):
        """Return path to per-pack catalog JSON file."""
        return DATA_DIR / f"{pack_id}.json"

    def _load_catalog(self, pack_id):
        """Load existing per-pack catalog from disk. Returns dict of icons."""
        path = self._catalog_path(pack_id)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text())
            return data.get("icons", {})
        except (json.JSONDecodeError, KeyError):
            return {}

    def _save_catalog(self, pack_id, icons, comment=None):
        """Write per-pack catalog JSON to disk.

        Only writes if the icons content has changed.
        """
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if comment is None:
            comment = f"Auto-maintained catalog for {pack_id} theme pack. Icons/sizes are additive only."
        path = self._catalog_path(pack_id)

        data = {
            "_comment": comment,
            "icons": icons,
        }
        new_content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

        # Skip write if content unchanged
        if path.exists() and path.read_text() == new_content:
            return

        path.write_text(new_content)

    def _merge_catalog(self, pack_id, discovered_icons):
        """Additively merge discovered icons into the existing catalog.

        Icons/sizes are additive (never removed).
        Hints/inherits/duplicates/duplicate_of are updatable from discovered data.
        Logs missing icons (in catalog but not on disk).

        Args:
            pack_id: theme pack identifier
            discovered_icons: dict of {cat_file: {"sizes": [...], ...}}
        Returns:
            merged catalog dict
        """
        existing = self._load_catalog(pack_id)

        # Merge discovered into existing
        for cat_file, info in discovered_icons.items():
            if cat_file in existing:
                # Additive sizes: union of existing and discovered
                existing_sizes = set(existing[cat_file].get("sizes", []))
                new_sizes = set(info.get("sizes", []))
                existing[cat_file]["sizes"] = sorted(existing_sizes | new_sizes)
                # Updatable fields: only update if present in discovered
                for field in ("hints", "inherits", "duplicates", "duplicate_of"):
                    if field in info:
                        existing[cat_file][field] = info[field]
            else:
                # New icon — add it
                existing[cat_file] = info

        # Log missing icons (in catalog but not discovered on disk)
        for cat_file in existing:
            if cat_file not in discovered_icons:
                sizes = existing[cat_file].get("sizes", [])
                print(f"CATALOG: {pack_id}/{cat_file} not found on disk (was: {sizes})")

        return existing

    def _scan_disk_icons(self):
        """Scan internal icons directory using the generic scanner."""
        scanned = self._scan_icon_directory(ICONS_DIR)

        for cat_file, info in scanned.items():
            # Legacy flat icons get _legacy/ prefix from scanner
            if cat_file.startswith("_legacy/"):
                icon_id = Path(cat_file).stem  # strip _legacy/ and extension
            elif "/" in cat_file:
                # New format: category/name.png — use stem as icon_id
                icon_id = Path(cat_file).stem
            else:
                icon_id = Path(cat_file).stem

            key = ("internal", icon_id)
            if key not in self._entries:
                clean_name = icon_id.replace("_icon", "").replace("_", " ").title()
                self._entries[key] = IconEntry(
                    id=icon_id,
                    name=clean_name,
                    status="legacy" if icon_id not in self._chooseable_ids else "included",
                )
            entry = self._entries[key]
            # Add file paths for each discovered size
            for size in info.get("sizes", []):
                if size in entry.sizes:
                    continue
                # Resolve actual path
                if cat_file.startswith("_legacy/"):
                    # Legacy: {name}{N}x{N}.png in ICONS_DIR root
                    legacy_name = cat_file.split("/", 1)[1]  # e.g. "arrow_down_icon.png"
                    stem = Path(legacy_name).stem
                    ext = Path(legacy_name).suffix
                    p = ICONS_DIR / f"{stem}{size}x{size}{ext}"
                else:
                    # New format: {N}x{N}/{category}/{file} or {category}/{N}/{file}
                    parts = cat_file.split("/")
                    if len(parts) == 2:
                        p = ICONS_DIR / f"{size}x{size}" / cat_file
                    else:
                        p = ICONS_DIR / cat_file
                if p.exists():
                    entry.sizes[size] = str(p)

    def _save_internal_catalog(self):
        """Save internal icons as a catalog for external reference."""
        discovered = {}
        for key, entry in self._entries.items():
            if key[0] != "internal":
                continue
            icon_id = entry.id
            info = {"sizes": sorted(entry.sizes.keys())}
            if entry.name:
                info["name"] = entry.name
            if entry.hints:
                info["hints"] = entry.hints
            if entry.source:
                info["source"] = entry.source
            if entry.category:
                info["category"] = entry.category
            if entry.original_file:
                info["original_file"] = entry.original_file
            if entry.duplicates:
                info["duplicates"] = entry.duplicates
            discovered[icon_id] = info

        catalog = self._merge_catalog("internal", discovered)
        self._save_catalog("internal", catalog,
                          comment="Internal TaskCoach icons from artprovider.py and disk.")

    def load_theme_pack(self, pack_id):
        """Load all icons from an external theme pack directory.

        Scans disk, merges into persistent catalog (additive for icons/sizes),
        resolves hints from catalog, and creates IconEntry objects.
        """
        pack = THEME_PACKS.get(pack_id)
        if not pack:
            return
        base = Path(pack["path"])
        if not base.exists():
            return

        # Build reverse mapping from ICON_MAPPING duplicates
        dup_files = set()  # filenames known as duplicates
        imported_files = {}  # filename -> tc_icon_id
        dup_of_map = {}  # duplicate filename -> canonical cat/file
        for tc_name, info in self._icon_mapping.items():
            if not isinstance(info, dict):
                continue
            if info.get("source") == pack_id:
                f = info.get("file", "")
                cat = info.get("category", "")
                canonical_key = f"{cat}/{f}" if cat and f else ""
                if f:
                    imported_files[f] = tc_name
                for dup in info.get("duplicates", []):
                    df = dup.get("file", "")
                    if df and dup.get("source") == pack_id:
                        dup_files.add(df)
                        if canonical_key:
                            dup_of_map[df] = canonical_key

        # Scan disk to discover all icons and sizes
        discovered = self._scan_icon_directory(base)

        if not discovered:
            return

        # Add duplicate relationships (bidirectional) to discovered icons
        for cat_file, info in list(discovered.items()):
            filename = cat_file.split("/")[-1] if "/" in cat_file else cat_file
            # Mark duplicates with duplicate_of back-reference
            if filename in dup_of_map:
                info["duplicate_of"] = dup_of_map[filename]
            # Mark canonical icons with their duplicates list
            if filename in imported_files:
                dups_for_this = [
                    d for d in self._icon_mapping.get(imported_files[filename], {}).get("duplicates", [])
                    if d.get("source") == pack_id
                ]
                if dups_for_this:
                    info["duplicates"] = dups_for_this

        # Merge into persistent catalog and save
        catalog = self._merge_catalog(pack_id, discovered)
        self._save_catalog(pack_id, catalog)

        # Build IconEntry objects from merged catalog
        for cat_file, info in catalog.items():
            parts = cat_file.split("/", 1)
            if len(parts) == 2:
                category, filename = parts
            else:
                category, filename = "", parts[0]
            stem = Path(filename).stem
            icon_id = f"{pack_id}:{cat_file}"

            # Determine status
            if filename in imported_files:
                status = "included"
            elif filename in dup_files:
                status = "duplicate"
            else:
                status = "external"

            # Resolve hints: inherits resolves from artprovider
            hints = []
            if "inherits" in info:
                tc_id = info["inherits"]
                if tc_id in self._chooseable_hints:
                    hints = self._chooseable_hints[tc_id]
            elif "hints" in info:
                hints = info["hints"]

            # Build sizes dict with actual file paths (only for sizes on disk)
            sizes = {}
            for sz in info.get("sizes", []):
                if pack_id == "breeze":
                    p = base / category / str(sz) / filename
                else:
                    p = base / f"{sz}x{sz}" / category / filename
                if p.exists():
                    sizes[sz] = str(p)

            key = (pack_id, icon_id)
            self._entries[key] = IconEntry(
                id=icon_id,
                name=stem.replace("-", " ").replace("_", " ").title(),
                hints=hints,
                source=pack_id,
                category=category,
                status=status,
                sizes=sizes,
                duplicates=info.get("duplicates", []),
                original_file=filename,
            )

    def _scan_icon_directory(self, base):
        """Scan any icon directory and build inventory of all icons found.

        Collects all .svg and .png files in one pass, then parses paths to
        extract size, category, and filename. Handles all known layouts:
          - {N}x{N}/{category}/{file}   (Papirus, Oxygen, Nuvola, internal)
          - {category}/{N}/{file}        (Breeze)
          - {name}{N}x{N}.png           (legacy flat, internal only)

        Returns dict of {cat/file: {"sizes": [...]}}
        """
        all_files = list(base.rglob("*.svg")) + list(base.rglob("*.png"))

        # Path patterns (relative to base)
        pat_nxn = re.compile(r'^(\d+)x(\d+)/([^/]+)/(.+)$')
        pat_bare = re.compile(r'^([^/]+)/(\d+)/(.+)$')
        pat_legacy = re.compile(r'^(.+?)(\d+)x(\d+)\.(png|svg)$')

        discovered = {}  # cat/file -> set of sizes
        for f in all_files:
            if "-symbolic" in f.name:
                continue
            try:
                rel = str(f.relative_to(base))
            except ValueError:
                continue

            # Pattern: {N}x{N}/{category}/{file}
            m = pat_nxn.match(rel)
            if m and m.group(1) == m.group(2):
                size = int(m.group(1))
                cat_file = f"{m.group(3)}/{m.group(4)}"
                discovered.setdefault(cat_file, set()).add(size)
                self._discovered_sizes.add(size)
                continue

            # Pattern: {category}/{N}/{file}
            m = pat_bare.match(rel)
            if m:
                size = int(m.group(2))
                cat_file = f"{m.group(1)}/{m.group(3)}"
                discovered.setdefault(cat_file, set()).add(size)
                self._discovered_sizes.add(size)
                continue

            # Pattern: {name}{N}x{N}.ext (legacy flat — no category)
            m = pat_legacy.match(rel)
            if m and "/" not in rel:
                size = int(m.group(2))
                cat_file = f"_legacy/{m.group(1)}.{m.group(4)}"
                discovered.setdefault(cat_file, set()).add(size)
                self._discovered_sizes.add(size)
                continue

        return {k: {"sizes": sorted(v)} for k, v in discovered.items()}

    def get_filtered(self, query="", themes=None, show_included=True,
                     show_duplicates=True, show_legacy=True,
                     min_size=None, sort_key=None):
        """Return filtered list of IconEntry."""
        if themes is None:
            themes = set()

        results = []
        query_terms = query.lower().split() if query else []

        for key, entry in self._entries.items():
            pack = key[0]

            # Theme filter — external packs need to be selected
            if pack not in ("internal",):
                if pack not in themes:
                    continue
            # Internal icons with a known external source: only show if
            # that source is selected OR the icon is included/legacy
            if pack == "internal" and entry.source in THEME_PACKS:
                if entry.source not in themes and entry.status not in ("included", "legacy"):
                    continue

            # Size filter: only show icons with at least one size >= min_size
            if min_size and entry.sizes:
                if max(entry.sizes.keys()) < min_size:
                    continue

            # Status filter
            if entry.status == "included" and not show_included:
                continue
            if entry.status == "duplicate" and not show_duplicates:
                continue
            if entry.status == "legacy" and not show_legacy:
                continue

            # Search filter
            if query_terms:
                search_text = f"{entry.name} {entry.id} {' '.join(entry.hints)} {entry.source} {entry.category}".lower()
                if not all(t in search_text for t in query_terms):
                    continue

            results.append(entry)

        if sort_key:
            results.sort(key=sort_key)
        else:
            results.sort(key=lambda e: (e.source, e.name.lower()))
        return results

    def get_bitmap(self, entry, size):
        """Get a wx.Bitmap for the given entry at the given size."""
        cache_key = (id(entry), size)
        if cache_key in self._bitmap_cache:
            return self._bitmap_cache[cache_key]

        # Find best available size
        path_str = entry.sizes.get(size)
        if not path_str:
            # Try nearest size
            available = sorted(entry.sizes.keys())
            if not available:
                return wx.NullBitmap
            nearest = min(available, key=lambda s: abs(s - size))
            path_str = entry.sizes[nearest]

        bitmap = self._load_bitmap(path_str, size)
        self._bitmap_cache[cache_key] = bitmap
        return bitmap

    def _load_bitmap(self, path_str, target_size):
        """Load a bitmap from a file path or zip entry."""
        try:
            if path_str.endswith(".svg"):
                png_data = cairosvg.svg2png(
                    url=str(path_str),
                    output_width=target_size,
                    output_height=target_size,
                )
                stream = io.BytesIO(png_data)
                image = wx.Image(stream)
            else:
                image = wx.Image(path_str)

            if not image.IsOk():
                return wx.NullBitmap

            # Rescale if needed
            if image.GetWidth() != target_size or image.GetHeight() != target_size:
                image.Rescale(target_size, target_size, wx.IMAGE_QUALITY_HIGH)

            return image.ConvertToBitmap()
        except Exception:
            return wx.NullBitmap

    def get_license(self, source):
        """Get license for a source library."""
        if source in THEME_PACKS:
            return THEME_PACKS[source].get("license", "Unknown")
        if source in self._icon_sources:
            return self._icon_sources[source].get("license", "Unknown")
        return "Unknown"

    def clear_cache(self):
        """Clear the bitmap cache (e.g., on size change)."""
        self._bitmap_cache.clear()


# ============================================================================
# Instruction Text Generation
# ============================================================================

def _generate_hints_step(step_num, clean_id, entry):
    """Generate the catalog hints step for import instructions.

    Hints flow one way: catalog → app. After importing, the catalog entry
    switches to 'inherits' so it tracks the app's canonical hints.
    """
    cat_file = f"{entry.category}/{entry.original_file}"
    catalog_file = f"tools/icon_grid_browser_data/{entry.source}.json"
    has_hints = bool(entry.hints)
    lines = []
    if has_hints:
        lines.append(f"{step_num}. Merge catalog hints into artprovider.py:")
        lines.append(f"   The catalog has these hints for this icon: {entry.hints}")
        lines.append(f"   Review and merge relevant hints into the artprovider.py")
        lines.append(f"   chooseableItems entry above (step {step_num - 1}).")
    lines.append(f"{'   ' if has_hints else ''}")
    step = step_num + (1 if has_hints else 0)
    lines.append(f"{step}. Update {catalog_file} to use inherits:")
    lines.append(f"   Replace any 'hints' entry with an 'inherits' reference:")
    lines.append(f'     "{cat_file}": {{"inherits": "{clean_id}", ...}}')
    lines.append(f"   This links the catalog entry to the app's canonical hints.")
    return lines


def generate_import_instructions(entry, display_size):
    """Generate copy-pasteable import instructions for an icon."""
    lines = []
    lines.append("Import this icon into the TaskCoach icon library:")
    lines.append("")

    clean_id = entry.id.split(":")[-1].split("/")[-1] if ":" in entry.id else entry.id
    clean_id = clean_id.replace("-", "_")
    source_sizes = sorted(entry.sizes.keys())
    source_sizes_str = ",".join(str(s) for s in source_sizes)
    target_size = display_size

    if entry.source in ("papirus", "breeze"):
        # SVG source — render with cairosvg at 16x16 only
        src_path_16 = entry.sizes.get(target_size) or next(iter(entry.sizes.values()), "")
        dest = f"taskcoachlib/gui/icons/{target_size}x{target_size}/{clean_id}.png"

        lines.append("1. View the source SVG at all available sizes:")
        for sz, p in sorted(entry.sizes.items()):
            lines.append(f"   {sz}x{sz}: {p}")
        lines.append("")
        lines.append(f"2. Render at {target_size}x{target_size} with cairosvg:")
        lines.append(f"   cairosvg {src_path_16} -o {dest} -W {target_size} -H {target_size}")
        lines.append("")
        lines.append("3. Add entry to ICON_MAPPING.json (document ALL source sizes):")
        lines.append(f'   "{clean_id}": {{')
        lines.append(f'     "source": "{entry.source}",')
        lines.append(f'     "category": "{entry.category}",')
        lines.append(f'     "file": "{entry.original_file}",')
        lines.append(f'     "source_sizes": "{source_sizes_str}"')
        lines.append("   }")
        lines.append(f"   Note: source_sizes lists ALL sizes available in the source")
        lines.append(f"   library ({source_sizes_str}), not just the imported size.")
        lines.append("")
        lines.append("4. Add entry to artprovider.py chooseableItems:")
        lines.append(f'   "{clean_id}": {{')
        lines.append(f'     "name": _("{entry.name}"),')
        lines.append(f'     "hints": [_("hint1"), _("hint2"), ...],')
        lines.append("   }")
        lines.append("   View the icon at ALL available sizes to choose hints that describe")
        lines.append("   what the icon visually represents and what it could be used for.")
        lines.append("")
        lines.extend(_generate_hints_step(5, clean_id, entry))

    elif entry.source == "oxygen":
        # PNG source — copy 16x16 only
        src_path_16 = entry.sizes.get(target_size) or next(iter(entry.sizes.values()), "")
        dest = f"taskcoachlib/gui/icons/{target_size}x{target_size}/{clean_id}.png"

        lines.append("1. View the source PNG at all available sizes:")
        for sz, p in sorted(entry.sizes.items()):
            lines.append(f"   {sz}x{sz}: {p}")
        lines.append("")
        lines.append(f"2. Copy the {target_size}x{target_size} PNG:")
        lines.append(f"   cp {src_path_16} {dest}")
        lines.append("")
        lines.append("3. Add entry to ICON_MAPPING.json (document ALL source sizes):")
        lines.append(f'   "{clean_id}": {{')
        lines.append(f'     "source": "{entry.source}",')
        lines.append(f'     "category": "{entry.category}",')
        lines.append(f'     "file": "{entry.original_file}",')
        lines.append(f'     "source_sizes": "{source_sizes_str}"')
        lines.append("   }")
        lines.append(f"   Note: source_sizes lists ALL sizes available in the source")
        lines.append(f"   library ({source_sizes_str}), not just the imported size.")
        lines.append("")
        lines.append("4. Add entry to artprovider.py chooseableItems:")
        lines.append(f'   "{clean_id}": {{')
        lines.append(f'     "name": _("{entry.name}"),')
        lines.append(f'     "hints": [_("hint1"), _("hint2"), ...],')
        lines.append("   }")
        lines.append("   View the icon at ALL available sizes to choose hints that describe")
        lines.append("   what the icon visually represents and what it could be used for.")
        lines.append("")
        lines.extend(_generate_hints_step(5, clean_id, entry))

    elif entry.source == "nuvola":
        # Nuvola PNG source — copy target size
        src_path = entry.sizes.get(target_size) or next(iter(entry.sizes.values()), "")
        dest = f"taskcoachlib/gui/icons/{target_size}x{target_size}/{clean_id}.png"

        lines.append("1. View the source PNG at all available sizes:")
        for sz, p in sorted(entry.sizes.items()):
            lines.append(f"   {sz}x{sz}: {p}")
        lines.append("")
        lines.append(f"2. Copy the {target_size}x{target_size} PNG:")
        lines.append(f"   cp {src_path} {dest}")
        lines.append("")
        lines.append("3. Add entry to ICON_MAPPING.json (document ALL source sizes):")
        lines.append(f'   "{clean_id}": {{')
        lines.append(f'     "source": "nuvola",')
        lines.append(f'     "category": "{entry.category}",')
        lines.append(f'     "file": "{entry.original_file}",')
        lines.append(f'     "source_sizes": "{source_sizes_str}"')
        lines.append("   }")
        lines.append(f"   Note: source_sizes lists ALL sizes available in the source")
        lines.append(f"   library ({source_sizes_str}), not just the imported size.")
        lines.append("")
        lines.append("4. Add entry to artprovider.py chooseableItems:")
        lines.append(f'   "{clean_id}": {{')
        lines.append(f'     "name": _("{entry.name}"),')
        lines.append(f'     "hints": [_("hint1"), _("hint2"), ...],')
        lines.append("   }")
        lines.append("   View the icon at ALL available sizes to choose hints that describe")
        lines.append("   what the icon visually represents and what it could be used for.")
        lines.append("")
        lines.extend(_generate_hints_step(5, clean_id, entry))

    else:
        lines.append("(No specific import instructions for this source.)")

    return "\n".join(lines)


def generate_duplicate_instructions(entry):
    """Generate instructions for documenting an icon as a duplicate."""
    lines = []
    lines.append("Document this icon as a duplicate of an existing icon:")
    lines.append("")
    lines.append('Add to ICON_MAPPING.json under the parent icon\'s "duplicates" array:')
    lines.append(f'  {{"source": "{entry.source}", "category": "{entry.category}",')
    lines.append(f'   "file": "{entry.original_file}"}}')
    return "\n".join(lines)


# ============================================================================
# UI Layer
# ============================================================================

# Border colors
COLOR_INCLUDED = wx.Colour(76, 175, 80)    # green
COLOR_DUPLICATE = wx.Colour(158, 158, 158)  # grey
COLOR_LEGACY = wx.Colour(255, 193, 7)       # yellow
COLOR_EXTERNAL = wx.Colour(220, 220, 220)   # light grey (no border)
COLOR_HOVER = wx.Colour(33, 150, 243)       # blue highlight

CELL_PADDING = 8
TEXT_HEIGHT = 30  # space for 2 lines of text below icon


class IconGridPanel(wx.ScrolledWindow):
    """Scrollable grid of icon cells with custom painting."""

    def __init__(self, parent, model):
        super().__init__(parent, style=wx.VSCROLL | wx.WANTS_CHARS)
        self._model = model
        self._entries = []
        self._display_size = 32
        self._dark_bg = False
        self._hover_index = -1
        self._pinned = False
        self._pinned_index = -1
        self._popup = None

        self.SetScrollRate(0, 20)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_SIZE, self._on_size)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self._on_leave)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_click)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

    @property
    def cell_width(self):
        return self._display_size + CELL_PADDING * 2 + 40

    @property
    def cell_height(self):
        return self._display_size + CELL_PADDING * 2 + TEXT_HEIGHT

    @property
    def cols(self):
        w = self.GetClientSize().width
        return max(1, w // self.cell_width)

    def set_entries(self, entries):
        self._entries = entries
        self._hover_index = -1
        self._pinned = False
        self._pinned_index = -1
        self._destroy_popup()
        self._update_virtual_size()
        self.Scroll(0, 0)
        self.Refresh()

    def set_display_size(self, size):
        self._display_size = size
        self._model.clear_cache()
        self._update_virtual_size()
        self.Refresh()

    def set_dark_bg(self, dark):
        self._dark_bg = dark
        self.Refresh()

    def _update_virtual_size(self):
        cols = self.cols
        rows = (len(self._entries) + cols - 1) // cols if cols > 0 else 0
        self.SetVirtualSize(self.GetClientSize().width, rows * self.cell_height + 20)

    def _index_at(self, x, y):
        """Get entry index at pixel position (in virtual coords)."""
        vx, vy = self.CalcUnscrolledPosition(x, y)
        cols = self.cols
        col = vx // self.cell_width
        row = vy // self.cell_height
        if col >= cols:
            return -1
        idx = row * cols + col
        if idx >= len(self._entries):
            return -1
        return idx

    def _cell_rect(self, index):
        """Get the rect for a cell in virtual coordinates."""
        cols = self.cols
        row = index // cols
        col = index % cols
        x = col * self.cell_width
        y = row * self.cell_height
        return wx.Rect(x, y, self.cell_width, self.cell_height)

    def _border_color(self, entry):
        return _status_border_color(entry)

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        self.DoPrepareDC(dc)

        bg = wx.Colour(40, 40, 40) if self._dark_bg else wx.Colour(245, 245, 245)
        dc.SetBackground(wx.Brush(bg))
        dc.Clear()

        # Calculate visible range
        view_start = self.GetViewStart()
        client_h = self.GetClientSize().height
        scroll_y = view_start[1] * 20  # scroll rate
        cols = self.cols

        first_row = max(0, scroll_y // self.cell_height)
        last_row = (scroll_y + client_h) // self.cell_height + 1
        first_idx = first_row * cols
        last_idx = min(len(self._entries), (last_row + 1) * cols)

        text_color = wx.Colour(220, 220, 220) if self._dark_bg else wx.Colour(60, 60, 60)
        sub_color = wx.Colour(160, 160, 160) if self._dark_bg else wx.Colour(120, 120, 120)

        for i in range(first_idx, last_idx):
            entry = self._entries[i]
            rect = self._cell_rect(i)
            is_highlighted = (i == self._hover_index or
                              (self._pinned and i == self._pinned_index))

            # Cell background
            cell_bg = wx.Colour(50, 50, 50) if self._dark_bg else wx.Colour(255, 255, 255)
            dc.SetBrush(wx.Brush(cell_bg))

            # Outer highlight border (hover or pinned)
            if is_highlighted:
                dc.SetPen(wx.Pen(COLOR_HOVER, 3))
                dc.DrawRoundedRectangle(rect.x + 1, rect.y + 1, rect.width - 2, rect.height - 2, 5)

            # Inner status color border (always visible)
            status_color = self._border_color(entry)
            if entry.status == "external" and not is_highlighted:
                dc.SetPen(wx.Pen(wx.Colour(200, 200, 200), 1))
            else:
                dc.SetPen(wx.Pen(status_color, 2))
            dc.SetBrush(wx.Brush(cell_bg))
            dc.DrawRoundedRectangle(rect.x + 5, rect.y + 5, rect.width - 10, rect.height - 10, 3)

            # Icon
            bitmap = self._model.get_bitmap(entry, self._display_size)
            if bitmap.IsOk():
                ix = rect.x + (rect.width - self._display_size) // 2
                iy = rect.y + CELL_PADDING
                dc.DrawBitmap(bitmap, ix, iy, True)

            # Name text — left-aligned, clipped to cell width
            dc.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            dc.SetTextForeground(text_color)
            max_tw = rect.width - 12  # inner padding
            name = entry.name
            tw, th = dc.GetTextExtent(name)
            while tw > max_tw and len(name) > 1:
                name = name[:-1]
                tw, th = dc.GetTextExtent(name)
            tx = rect.x + (rect.width - tw) // 2
            ty = rect.y + CELL_PADDING + self._display_size + 2
            dc.DrawText(name, tx, ty)

            # Source text — left-truncated, centered
            dc.SetFont(wx.Font(7, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            dc.SetTextForeground(sub_color)
            src = entry.source or "internal"
            tw2, th2 = dc.GetTextExtent(src)
            tx2 = rect.x + (rect.width - tw2) // 2
            dc.DrawText(src, tx2, ty + th + 1)

    def _on_size(self, event):
        self._update_virtual_size()
        self.Refresh()
        event.Skip()

    def _on_motion(self, event):
        if self._pinned:
            # No hover changes while pinned
            event.Skip()
            return
        idx = self._index_at(event.GetX(), event.GetY())
        if idx != self._hover_index:
            self._hover_index = idx
            self.Refresh()
            if idx >= 0:
                self._show_popup(idx, event.GetPosition())
            else:
                self._destroy_popup()
        event.Skip()

    def _on_leave(self, event):
        if self._pinned:
            self._hover_index = -1
            self.Refresh()
            event.Skip()
            return
        # Don't dismiss if mouse moved to popup
        if self._popup and self._popup.IsShown():
            pos = wx.GetMousePosition()
            popup_rect = self._popup.GetScreenRect()
            if popup_rect.Contains(pos):
                event.Skip()
                return
        self._hover_index = -1
        self._destroy_popup()
        self.Refresh()
        event.Skip()

    def _on_click(self, event):
        idx = self._index_at(event.GetX(), event.GetY())
        if idx >= 0:
            # Pin popup to this icon
            self._pinned = True
            self._pinned_index = idx
            self._show_popup(idx, event.GetPosition())
        else:
            # Click on empty space unpins
            self._pinned = False
            self._pinned_index = -1
            self._destroy_popup()
        self.SetFocus()
        event.Skip()

    def _on_key_down(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.unpin()
        else:
            event.Skip()

    def unpin(self):
        """Dismiss pinned popup and clear all highlights."""
        self._pinned = False
        self._pinned_index = -1
        self._hover_index = -1
        self._destroy_popup()
        self.Refresh()

    def _show_popup(self, index, pos):
        self._destroy_popup()
        if index < 0 or index >= len(self._entries):
            return
        entry = self._entries[index]
        screen_pos = self.ClientToScreen(pos)

        self._popup = IconDetailPopup(self, self._model, entry, self._display_size)
        popup_size = self._popup.GetSize()
        display_idx = wx.Display.GetFromPoint(screen_pos)
        if display_idx == wx.NOT_FOUND:
            display_idx = 0
        display_rect = wx.Display(display_idx).GetClientArea()

        x = screen_pos.x + 20
        y = screen_pos.y + 20

        # Keep on screen
        if x + popup_size.width > display_rect.GetRight():
            x = screen_pos.x - popup_size.width - 10
        if y + popup_size.height > display_rect.GetBottom():
            y = display_rect.GetBottom() - popup_size.height

        self._popup.SetPosition(wx.Point(x, y))
        self._popup.Show()

    def _destroy_popup(self):
        if self._popup:
            self._popup.Destroy()
            self._popup = None


def _status_border_color(entry):
    """Return the border color for an icon's status."""
    if entry.status == "included":
        return COLOR_INCLUDED
    elif entry.status == "duplicate":
        return COLOR_DUPLICATE
    elif entry.status == "legacy":
        return COLOR_LEGACY
    else:
        return COLOR_EXTERNAL


class IconDetailPopup(wx.PopupWindow):
    """Hover/pinned popup showing icon details, all sizes, and copyable instructions."""

    BORDER_WIDTH = 3

    def __init__(self, parent, model, entry, display_size):
        super().__init__(parent, flags=wx.BORDER_NONE)

        # Outer border panel — color matches the icon's status
        border = wx.Panel(self)
        border.SetBackgroundColour(_status_border_color(entry))

        # Inner content panel
        panel = wx.Panel(border)
        panel.SetBackgroundColour(wx.Colour(255, 255, 245))
        sizer = wx.BoxSizer(wx.VERTICAL)

        # --- Header ---
        header_font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        name_label = wx.StaticText(panel, label=f'"{entry.name}" ({entry.id})')
        name_label.SetFont(header_font)
        sizer.Add(name_label, 0, wx.ALL, 5)

        license_str = model.get_license(entry.source)
        info = f"Source: {entry.source or 'internal'}  |  License: {license_str}  |  Status: {entry.status}"
        info_label = wx.StaticText(panel, label=info)
        info_label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(info_label, 0, wx.LEFT | wx.RIGHT, 5)

        if entry.hints:
            hints_label = wx.StaticText(panel, label=f"Hints: {', '.join(entry.hints)}")
            hints_label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            sizer.Add(hints_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        # --- Size previews (all sizes this icon has on disk) ---
        size_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for size in sorted(entry.sizes.keys()):
            bmp = model.get_bitmap(entry, size)
            if bmp.IsOk():
                vbox = wx.BoxSizer(wx.VERTICAL)
                sb = wx.StaticBitmap(panel, bitmap=bmp)
                vbox.Add(sb, 0, wx.ALIGN_CENTER | wx.ALL, 2)
                lbl = wx.StaticText(panel, label=str(size))
                lbl.SetFont(wx.Font(7, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                vbox.Add(lbl, 0, wx.ALIGN_CENTER)
                size_sizer.Add(vbox, 0, wx.RIGHT, 6)

        sizer.Add(size_sizer, 0, wx.ALL, 5)

        # --- Import instructions ---
        import_text = generate_import_instructions(entry, display_size)
        sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        import_hdr = wx.BoxSizer(wx.HORIZONTAL)
        import_label = wx.StaticText(panel, label="Import instructions:")
        import_label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        import_hdr.Add(import_label, 1, wx.ALIGN_CENTER_VERTICAL)
        import_copy_btn = wx.Button(panel, label="Copy", size=(50, 22))
        import_copy_btn.Bind(wx.EVT_BUTTON, lambda e: self._copy_to_clipboard(import_text))
        import_hdr.Add(import_copy_btn, 0, wx.LEFT, 5)
        sizer.Add(import_hdr, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        import_ctrl = wx.TextCtrl(
            panel, value=import_text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
            size=(500, 160),
        )
        import_ctrl.SetFont(wx.Font(8, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(import_ctrl, 0, wx.ALL | wx.EXPAND, 5)

        # --- Duplicate instructions ---
        dup_text = generate_duplicate_instructions(entry)
        sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        dup_hdr = wx.BoxSizer(wx.HORIZONTAL)
        dup_label = wx.StaticText(panel, label="Duplicate instructions:")
        dup_label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        dup_hdr.Add(dup_label, 1, wx.ALIGN_CENTER_VERTICAL)
        dup_copy_btn = wx.Button(panel, label="Copy", size=(50, 22))
        dup_copy_btn.Bind(wx.EVT_BUTTON, lambda e: self._copy_to_clipboard(dup_text))
        dup_hdr.Add(dup_copy_btn, 0, wx.LEFT, 5)
        sizer.Add(dup_hdr, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        dup_ctrl = wx.TextCtrl(
            panel, value=dup_text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
            size=(500, 70),
        )
        dup_ctrl.SetFont(wx.Font(8, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(dup_ctrl, 0, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(sizer)

        # Layout: border panel wraps content with BORDER_WIDTH margin
        bw = self.BORDER_WIDTH
        border_sizer = wx.BoxSizer(wx.VERTICAL)
        border_sizer.Add(panel, 1, wx.ALL | wx.EXPAND, bw)
        border.SetSizer(border_sizer)

        # Let sizers compute the needed size from content
        sizer.Fit(panel)
        border_sizer.Fit(border)

        outer_sizer = wx.BoxSizer(wx.VERTICAL)
        outer_sizer.Add(border, 1, wx.EXPAND)
        self.SetSizerAndFit(outer_sizer)

    def _copy_to_clipboard(self, text):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()


class CheckListComboPopup(wx.ComboPopup):
    """Popup with a CheckListBox for multi-select dropdown."""

    def __init__(self, labels, pack_ids, available):
        super().__init__()
        self._labels = labels
        self._pack_ids = pack_ids
        self._available = available
        self._checklist = None

    def Create(self, parent):
        self._checklist = wx.CheckListBox(parent, choices=self._labels)
        self._checklist.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT,
                                         wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        # Grey out unavailable items
        for i, pid in enumerate(self._pack_ids):
            if not self._available.get(pid):
                self._checklist.SetItemForegroundColour(i, wx.Colour(180, 120, 120))
        self._checklist.Bind(wx.EVT_CHECKLISTBOX, self._on_check)
        return True

    def GetControl(self):
        return self._checklist

    def GetAdjustedSize(self, minWidth, prefHeight, maxHeight):
        count = self._checklist.GetCount()
        h = min(count * 24 + 6, maxHeight)
        return wx.Size(max(minWidth, 300), h)

    def _on_check(self, event):
        idx = event.GetInt()
        pid = self._pack_ids[idx]
        # Prevent checking unavailable packs
        if not self._available.get(pid):
            self._checklist.Check(idx, False)
            return
        # Update combo text and fire event
        combo = self.GetComboCtrl()
        combo.update_text()
        # Fire EVT_TEXT so ControlsPanel picks up the change
        evt = wx.CommandEvent(wx.wxEVT_TEXT, combo.GetId())
        evt.SetEventObject(combo)
        combo.GetEventHandler().ProcessEvent(evt)

    def is_checked(self, idx):
        return self._checklist.IsChecked(idx)

    def check(self, idx, state):
        self._checklist.Check(idx, state)


class CheckListComboCtrl(wx.ComboCtrl):
    """Dropdown combo that shows a CheckListBox popup for multi-select."""

    def __init__(self, parent, labels, pack_ids, available, **kwargs):
        super().__init__(parent, style=wx.CB_READONLY, **kwargs)
        self._pack_ids = pack_ids
        self._labels = labels
        self._available = available
        self._popup = CheckListComboPopup(labels, pack_ids, available)
        self.SetPopupControl(self._popup)
        self.update_text()

    def check(self, idx, state):
        self._popup.check(idx, state)

    def update_text(self):
        selected = []
        for i, pid in enumerate(self._pack_ids):
            if self._popup.is_checked(i):
                # Use short label (strip " (not found)" etc)
                label = THEME_PACKS[pid]["label"]
                selected.append(label)
        self.SetText(", ".join(selected) if selected else "(none)")

    def get_checked_ids(self):
        return {self._pack_ids[i]
                for i in range(len(self._pack_ids))
                if self._popup.is_checked(i)}


class ControlsPanel(wx.Panel):
    """Top control bar: label above, control below, all in a horizontal row."""

    SORT_CHOICES = ["Icon Name", "Status", "Theme Pack"]
    SORT_KEYS = {
        "Theme Pack": lambda e: (e.source, e.name.lower()),
        "Icon Name": lambda e: e.name.lower(),
        "Status": lambda e: (e.status, e.source, e.name.lower()),
    }

    def __init__(self, parent, model, on_filter_changed):
        super().__init__(parent)
        self._model = model
        self._on_filter_changed = on_filter_changed

        # Helper to create a label-above-control column
        def make_col(label_text, ctrl, min_width=0):
            col = wx.BoxSizer(wx.VERTICAL)
            lbl = wx.StaticText(self, label=label_text)
            lbl.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                wx.FONTWEIGHT_BOLD))
            col.Add(lbl, 0, wx.BOTTOM, 3)
            if min_width:
                ctrl.SetMinSize((min_width, -1))
            col.Add(ctrl, 0, wx.EXPAND)
            return col

        row_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 1. Search
        self._search = wx.SearchCtrl(self, size=(200, -1))
        self._search.SetDescriptiveText("Search icons...")
        self._search.ShowCancelButton(True)
        row_sizer.Add(make_col("Search", self._search), 0, wx.RIGHT, 12)

        # 2. Display size — populated from model's discovered sizes
        initial_sizes = model.discovered_sizes or [16, 32]
        self._size_values = list(initial_sizes)
        self._size_choice = wx.Choice(self, choices=[str(s) for s in self._size_values])
        self._size_choice.SetSelection(0)
        row_sizer.Add(make_col("Size", self._size_choice), 0, wx.RIGHT, 12)

        # 3. Theme packs (dropdown multi-select)
        self._theme_pack_ids = []
        self._theme_available = {}
        popup_labels = []
        for pack_id, pack_info in THEME_PACKS.items():
            path = Path(pack_info["path"])
            exists = path.exists()
            self._theme_pack_ids.append(pack_id)
            self._theme_available[pack_id] = exists
            path_display = pack_info["path"]
            try:
                path_display = str(Path(path_display).relative_to(REPO_ROOT.parent))
            except ValueError:
                pass
            if exists:
                popup_labels.append(f"{pack_info['label']}  ({path_display})")
            else:
                popup_labels.append(f"{pack_info['label']}  ({path_display}) — not found")

        self._theme_combo = CheckListComboCtrl(
            self, popup_labels, self._theme_pack_ids,
            self._theme_available, size=(220, -1))
        for i, pack_id in enumerate(self._theme_pack_ids):
            if self._theme_available.get(pack_id) and pack_id == "nuvola_local_zip":
                self._theme_combo.check(i, True)
        self._theme_combo.update_text()
        row_sizer.Add(make_col("Theme Packs", self._theme_combo), 0, wx.RIGHT, 12)

        # 4. Sort
        self._sort_choice = wx.Choice(self, choices=self.SORT_CHOICES)
        self._sort_choice.SetSelection(0)  # default: Theme Pack
        row_sizer.Add(make_col("Sort By", self._sort_choice), 0, wx.RIGHT, 12)

        # 5. Show included
        self._cb_included = wx.CheckBox(self, label="Included")
        self._cb_included.SetValue(True)
        row_sizer.Add(make_col("Show", self._cb_included), 0, wx.RIGHT, 12)

        # 6. Show duplicates
        self._cb_duplicates = wx.CheckBox(self, label="Duplicates")
        self._cb_duplicates.SetValue(True)
        row_sizer.Add(make_col("", self._cb_duplicates), 0, wx.RIGHT, 12)

        # 7. Show legacy
        self._cb_legacy = wx.CheckBox(self, label="Legacy")
        self._cb_legacy.SetValue(True)
        row_sizer.Add(make_col("", self._cb_legacy), 0, wx.RIGHT, 12)

        # 8. Dark background
        self._cb_dark = wx.CheckBox(self, label="Dark BG")
        row_sizer.Add(make_col("", self._cb_dark), 0, wx.RIGHT, 12)

        # 8. Count
        self._count_label = wx.StaticText(self, label="0 / 0")
        row_sizer.Add(make_col("Showing", self._count_label), 0)

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(row_sizer, 0, wx.ALL, 8)
        self.SetSizer(outer)

        # Bind events
        self._search_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_search_timer, self._search_timer)
        self._search.Bind(wx.EVT_TEXT, self._on_search_text)
        self._search.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self._on_search_cancel)
        self._size_choice.Bind(wx.EVT_CHOICE, self._on_change)
        self._sort_choice.Bind(wx.EVT_CHOICE, self._on_change)
        self._cb_included.Bind(wx.EVT_CHECKBOX, self._on_change)
        self._cb_duplicates.Bind(wx.EVT_CHECKBOX, self._on_change)
        self._cb_legacy.Bind(wx.EVT_CHECKBOX, self._on_change)
        self._cb_dark.Bind(wx.EVT_CHECKBOX, self._on_change)
        self._theme_combo.Bind(wx.EVT_TEXT, self._on_theme_change)

    def _on_search_text(self, event):
        self._search_timer.StartOnce(300)

    def _on_search_cancel(self, event):
        self._search.SetValue("")
        self._on_filter_changed()

    def _on_search_timer(self, event):
        self._on_filter_changed()

    def _on_change(self, event):
        self._on_filter_changed()

    def _on_theme_change(self, event):
        # Load theme pack data for newly enabled packs
        for pack_id in self._theme_combo.get_checked_ids():
            self._model.load_theme_pack(pack_id)
        self.update_size_choices()
        self._on_filter_changed()

    @property
    def search_query(self):
        return self._search.GetValue()

    def update_size_choices(self):
        """Refresh the size dropdown from model's discovered sizes."""
        new_sizes = self._model.discovered_sizes or [16, 32]
        if new_sizes != self._size_values:
            prev = self.display_size
            self._size_values = list(new_sizes)
            self._size_choice.Set([str(s) for s in self._size_values])
            # Restore previous selection or pick closest
            if prev in self._size_values:
                self._size_choice.SetSelection(self._size_values.index(prev))
            else:
                closest = min(self._size_values, key=lambda s: abs(s - prev))
                self._size_choice.SetSelection(self._size_values.index(closest))

    @property
    def display_size(self):
        idx = self._size_choice.GetSelection()
        if idx < 0 or idx >= len(self._size_values):
            return self._size_values[0] if self._size_values else 16
        return self._size_values[idx]

    @property
    def selected_themes(self):
        return self._theme_combo.get_checked_ids()

    @property
    def sort_key(self):
        name = self.SORT_CHOICES[self._sort_choice.GetSelection()]
        return self.SORT_KEYS[name]

    @property
    def show_included(self):
        return self._cb_included.IsChecked()

    @property
    def show_duplicates(self):
        return self._cb_duplicates.IsChecked()

    @property
    def show_legacy(self):
        return self._cb_legacy.IsChecked()

    @property
    def dark_bg(self):
        return self._cb_dark.IsChecked()

    def set_count(self, visible, total):
        self._count_label.SetLabel(f"{visible} / {total}")


class IconGridBrowserFrame(wx.Frame):
    """Main window for the icon grid browser."""

    def __init__(self):
        super().__init__(None, title="TaskCoach Icon Browser", size=(1100, 750))

        self._model = IconDataModel()

        # Load internal data
        self._model.load_internal()

        # Build UI
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self._controls = ControlsPanel(self, self._model, self._on_filter_changed)
        main_sizer.Add(self._controls, 0, wx.EXPAND)

        main_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND)

        self._grid = IconGridPanel(self, self._model)
        main_sizer.Add(self._grid, 1, wx.EXPAND)

        self.SetSizer(main_sizer)

        # Frame-level Escape key binding (works regardless of focus)
        escape_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self._on_escape, id=escape_id)
        accel = wx.AcceleratorTable([
            wx.AcceleratorEntry(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, escape_id),
        ])
        self.SetAcceleratorTable(accel)

        # Load theme packs that are checked by default
        for pack_id in self._controls.selected_themes:
            self._model.load_theme_pack(pack_id)

        # Initial filter
        self._on_filter_changed()

    def _on_escape(self, event):
        self._grid.unpin()

    def _on_filter_changed(self):
        display_size = self._controls.display_size
        sort_key = self._controls.sort_key
        entries = self._model.get_filtered(
            query=self._controls.search_query,
            themes=self._controls.selected_themes,
            show_included=self._controls.show_included,
            show_duplicates=self._controls.show_duplicates,
            show_legacy=self._controls.show_legacy,
            min_size=display_size,
            sort_key=sort_key,
        )

        self._grid.set_display_size(display_size)
        self._grid.set_dark_bg(self._controls.dark_bg)
        self._grid.set_entries(entries)

        # Count total
        all_entries = self._model.get_filtered(
            themes=self._controls.selected_themes,
            show_included=True,
            show_duplicates=True,
            show_legacy=True,
            min_size=display_size,
        )
        self._controls.set_count(len(entries), len(all_entries))


# ============================================================================
# Entry point
# ============================================================================

def main():
    app = wx.App()
    frame = IconGridBrowserFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
