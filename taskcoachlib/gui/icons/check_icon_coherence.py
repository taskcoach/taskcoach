#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Icon Coherence Check Report

Validates consistency between:
1. ICON_MAPPING.json - provenance tracking
2. 16x16/*.png files - actual icon files
3. artprovider.py chooseableItems - searchable metadata

Reports ONLY exceptions (orphans, missing entries).
Exit code: 0 if all coherent, 1 if issues found.

Usage:
    python check_icon_coherence.py
"""

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ICONS_16 = SCRIPT_DIR / "16x16"
MAPPING_FILE = SCRIPT_DIR / "ICON_MAPPING.json"
SOURCES_FILE = SCRIPT_DIR / "ICON_THEME_CATALOG.json"
ARTPROVIDER = SCRIPT_DIR.parent / "artprovider.py"


def load_icon_sources():
    """Load valid source names from ICON_THEME_CATALOG.json."""
    if not SOURCES_FILE.exists():
        return set()
    data = json.loads(SOURCES_FILE.read_text())
    return set(data.keys())


def load_mapping_icons():
    """Load icon names from ICON_MAPPING.json (excluding comments/metadata)."""
    if not MAPPING_FILE.exists():
        return set()
    data = json.loads(MAPPING_FILE.read_text())
    return {k for k in data.keys() if not k.startswith("_")}


def load_mapping_data():
    """Load full ICON_MAPPING.json data for field validation."""
    if not MAPPING_FILE.exists():
        return {}
    return json.loads(MAPPING_FILE.read_text())


def load_png_icons():
    """Load icon names from 16x16/*.png files (new format)."""
    if not ICONS_16.exists():
        return set()
    return {f.stem for f in ICONS_16.glob("*.png")}


def load_legacy_png_icons():
    """Load icon names from legacy format (*16x16.png files in icons root)."""
    icons = set()
    for f in SCRIPT_DIR.glob("*16x16.png"):
        # Extract icon name: person_icon16x16.png -> person_icon
        name = f.stem.replace("16x16", "")
        if name:  # Skip if name would be empty
            icons.add(name)
    return icons


def load_artprovider_icons():
    """Load icon names and hint counts from artprovider.py chooseableItems.

    Returns: (set of icon names, dict of icon -> hint count)
    """
    if not ARTPROVIDER.exists():
        return set(), {}

    content = ARTPROVIDER.read_text()

    icons = set()
    hint_counts = {}

    # Find chooseableItems dict and extract keys + hint counts
    in_chooseable = False
    brace_count = 0
    current_icon = None

    for line in content.split('\n'):
        if 'chooseableItems' in line and '=' in line:
            in_chooseable = True
            brace_count = 0

        if in_chooseable:
            brace_count += line.count('{') - line.count('}')

            # Match icon entries: "icon_name": {
            match = re.match(r'\s*"([a-zA-Z0-9_]+)":\s*\{', line)
            if match:
                current_icon = match.group(1)
                icons.add(current_icon)

            # Count hints in hints line
            if current_icon and '"hints"' in line:
                # Count _() calls in the hints array
                hints = re.findall(r'_\(["\'][^"\']+["\']\)', line)
                hint_counts[current_icon] = len(hints)
                current_icon = None

            if brace_count <= 0 and in_chooseable and '{' in content[:content.find(line)]:
                break

    return icons, hint_counts


MIN_HINTS = 5  # Minimum required hints per icon


def check_coherence():
    """Check coherence and report exceptions."""
    mapping = load_mapping_icons()
    mapping_data = load_mapping_data()
    valid_sources = load_icon_sources()
    dir_pngs = load_png_icons()        # Icons in 16x16/ directory
    legacy_pngs = load_legacy_png_icons()  # Icons in flat format (*16x16.png)
    artprovider, hint_counts = load_artprovider_icons()

    # All available PNG icons (either format)
    all_pngs = dir_pngs | legacy_pngs

    issues = []

    # === ICON_MAPPING.json FIELD VALIDATION ===

    # Check required fields and valid sources
    missing_fields = []
    invalid_sources = []
    missing_category = []
    missing_sizes = []

    for icon_name, info in mapping_data.items():
        if icon_name.startswith("_"):
            continue  # Skip comments/metadata

        if not isinstance(info, dict):
            missing_fields.append(f"{icon_name} (not a dict)")
            continue

        # Required: source
        if "source" not in info:
            missing_fields.append(f"{icon_name} (missing 'source')")
        else:
            # Validate source exists in ICON_THEME_CATALOG.json
            if info["source"] not in valid_sources:
                invalid_sources.append(f"{icon_name} (source='{info['source']}')")

        # Required: file
        if "file" not in info:
            missing_fields.append(f"{icon_name} (missing 'file')")

        # Required for new icons (no _icon suffix): category
        if not icon_name.endswith("_icon") and "category" not in info:
            missing_category.append(icon_name)

        # Required: source_sizes field (sizes available in source library) with at least 16
        if "source_sizes" not in info:
            missing_sizes.append(f"{icon_name} (missing 'source_sizes')")
        else:
            sizes = str(info["source_sizes"]).split(",")
            if "16" not in sizes:
                missing_sizes.append(f"{icon_name} (source_sizes={info['source_sizes']}, missing 16)")

    if missing_fields:
        issues.append(("ICON_MAPPING.json → missing required fields", sorted(missing_fields)))

    if invalid_sources:
        issues.append(("ICON_MAPPING.json → source not in ICON_THEME_CATALOG.json", sorted(invalid_sources)))

    if missing_category:
        issues.append(("ICON_MAPPING.json → new icons missing 'category'", sorted(missing_category)))

    if missing_sizes:
        issues.append(("ICON_MAPPING.json → missing 'source_sizes' field (must include 16)", sorted(missing_sizes)))

    # === ICON_MAPPING.json PNG CHECKS ===

    # In ICON_MAPPING but no PNG (either format)
    mapping_no_png = mapping - all_pngs
    if mapping_no_png:
        issues.append(("ICON_MAPPING.json → missing PNG file (need at least 16x16)", sorted(mapping_no_png)))

    # In ICON_MAPPING but no artprovider entry
    mapping_no_art = mapping - artprovider
    if mapping_no_art:
        issues.append(("ICON_MAPPING.json → missing artprovider.py entry", sorted(mapping_no_art)))

    # === PNG FILE CHECKS ===

    # PNG in 16x16/ but not in ICON_MAPPING (orphan new-format icons)
    dir_png_no_mapping = dir_pngs - mapping
    if dir_png_no_mapping:
        issues.append(("16x16/*.png → missing ICON_MAPPING.json entry", sorted(dir_png_no_mapping)))

    # PNG in 16x16/ but not in artprovider
    dir_png_no_art = dir_pngs - artprovider
    if dir_png_no_art:
        issues.append(("16x16/*.png → missing artprovider.py entry", sorted(dir_png_no_art)))

    # === ARTPROVIDER CHECKS ===

    # artprovider entry but no PNG (either format)
    art_no_png = artprovider - all_pngs
    if art_no_png:
        issues.append(("artprovider.py → missing PNG file", sorted(art_no_png)))

    # Icons with fewer than MIN_HINTS hints
    few_hints = [f"{icon} ({count} hints)" for icon, count in hint_counts.items()
                 if count < MIN_HINTS]
    if few_hints:
        issues.append((f"artprovider.py → fewer than {MIN_HINTS} hints", sorted(few_hints)))

    return issues


def main():
    print("=" * 60)
    print("Icon Coherence Check Report")
    print("=" * 60)
    print()

    issues = check_coherence()

    if not issues:
        print("✓ All icons are coherent. No issues found.")
        print()
        print("Checked:")
        print(f"  - ICON_THEME_CATALOG.json: {len(load_icon_sources())} sources")
        print(f"  - ICON_MAPPING.json: {len(load_mapping_icons())} entries")
        print(f"  - 16x16/*.png: {len(load_png_icons())} files")
        print(f"  - artprovider.py: {len(load_artprovider_icons()[0])} entries")
        return 0

    print("ISSUES FOUND:")
    print()

    for description, items in issues:
        print(f"✗ {description}:")
        for item in items:
            print(f"    - {item}")
        print()

    print("-" * 60)
    print(f"Total: {sum(len(items) for _, items in issues)} issues in {len(issues)} categories")
    return 1


if __name__ == "__main__":
    sys.exit(main())
