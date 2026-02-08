#!/usr/bin/env python3
"""Migrate prep tool JSON files from old format to new format.

Old format:
    "emotes/face-angel.png": {
        "sizes": [16, 22, 32, 48, 64, 128],
        "hints": ["angel", ...]
    }

New format:
    "oxygen_emotes_face-angel": {
        "category": "emotes",
        "file": "face-angel.png",
        "sizes": [16, 22, 32, 48, 64, 128],
        "hints": ["angel", ...]
    }

Usage:
    python tools/migrate_prep_json_format.py [--dry-run]
"""

import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PREP_TOOL_DIR = SCRIPT_DIR / "icon_grid_browser_data"

# Mapping of JSON file to theme name
THEME_MAP = {
    "oxygen.json": "oxygen",
    "papirus.json": "papirus",
    "nuvola.json": "nuvola",
    "nuvola_github.json": "nuvola",
    "nuvola_local_zip.json": "nuvola",
    "breeze.json": "breeze",
    "internal.json": "taskcoach",
}


def old_key_to_new_key(old_key: str, theme: str) -> tuple[str, str, str]:
    """Convert old key format to new key format.

    Args:
        old_key: e.g., "emotes/face-angel.png" or "face-angel.png"
        theme: e.g., "oxygen"

    Returns:
        (new_key, category, file)
        e.g., ("oxygen_emotes_face-angel", "emotes", "face-angel.png")
    """
    if "/" in old_key:
        category, filename = old_key.split("/", 1)
    else:
        category = None
        filename = old_key

    # Strip extension for key
    stem = Path(filename).stem

    if category:
        new_key = f"{theme}_{category}_{stem}"
    else:
        new_key = f"{theme}_{stem}"

    return new_key, category, filename


def migrate_json_file(json_path: Path, theme: str, dry_run: bool = False) -> bool:
    """Migrate a single JSON file to new format.

    Returns True if file was modified.
    """
    with open(json_path, "r") as f:
        data = json.load(f)

    icons = data.get("icons", {})
    if not icons:
        print(f"  No icons in {json_path.name}, skipping")
        return False

    # Check if already migrated (look for underscore-based keys)
    first_key = next(iter(icons.keys()))
    if "_" in first_key and "/" not in first_key:
        print(f"  {json_path.name} appears already migrated, skipping")
        return False

    # Migrate
    new_icons = {}
    for old_key, info in icons.items():
        new_key, category, filename = old_key_to_new_key(old_key, theme)

        new_info = {
            "category": category,
            "file": filename,
        }
        # Copy other fields in order
        for field in ("sizes", "hints", "inherits", "duplicates", "duplicate_of", "unstructured"):
            if field in info:
                new_info[field] = info[field]

        new_icons[new_key] = new_info

    data["icons"] = new_icons

    if dry_run:
        print(f"  Would migrate {len(new_icons)} icons in {json_path.name}")
        # Show first 3 examples
        for i, (old_key, new_key) in enumerate(zip(icons.keys(), new_icons.keys())):
            if i >= 3:
                print(f"    ... and {len(icons) - 3} more")
                break
            print(f"    {old_key} -> {new_key}")
    else:
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  Migrated {len(new_icons)} icons in {json_path.name}")

    return True


def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("DRY RUN - no files will be modified\n")

    migrated = 0
    for json_file, theme in THEME_MAP.items():
        json_path = PREP_TOOL_DIR / json_file
        if not json_path.exists():
            continue

        print(f"Processing {json_file} (theme: {theme})...")
        if migrate_json_file(json_path, theme, dry_run):
            migrated += 1

    print(f"\nMigrated {migrated} file(s)")


if __name__ == "__main__":
    main()
