#!/usr/bin/env python3
"""Import icons from tools catalog to app library.

Usage:
    python tools/icon_import_theme.py <theme> <size>

Arguments:
    theme: Theme name (nuvola, oxygen, papirus, breeze)
    size: Target size to import (e.g., 16)

The script processes ONE ICON AT A TIME with this order:
1. Copy/resize image file
2. Add entry to app JSON and save
3. Add 'inherits' to tools JSON and save (commit marker)

Icons with 'inherits' field are skipped (already done), so script can resume.

Examples:
    python tools/icon_import_theme.py nuvola 16
"""

import json
import os
import re
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: PIL/Pillow required for image resizing")
    print("Install with: pip install Pillow")
    sys.exit(1)

# Path setup
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = SCRIPT_DIR / "icon_grid_browser_data"
ICONS_DIR = PROJECT_DIR / "taskcoachlib" / "gui" / "icons"
EXTERNAL_ICONS_DIR = Path.home() / "Downloads" / "icons"

# Theme source directories
THEME_SOURCES = {
    "nuvola": EXTERNAL_ICONS_DIR / "nuvola",
    "oxygen": EXTERNAL_ICONS_DIR / "oxygen-icons-master",
    "papirus": EXTERNAL_ICONS_DIR / "papirus-icon-theme-master" / "Papirus",
    "breeze": EXTERNAL_ICONS_DIR / "breeze-icons-master" / "icons",
}

KNOWN_THEMES = list(THEME_SOURCES.keys())


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
    with open(filepath, "w") as f:
        f.write(text)


def find_source_image(theme_source, category, filename, sizes):
    """Find source image path, preferring smallest size for resize.

    Returns (path, size) tuple or (None, None) if not found.
    """
    for size in sorted(sizes):
        path = theme_source / f"{size}x{size}" / category / filename
        if path.exists():
            return path, size
    return None, None


def resize_image(src_path, dst_path, target_size):
    """Resize image to target size using high-quality resampling."""
    with Image.open(src_path) as img:
        resized = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
        resized.save(dst_path, "PNG")


def main():
    if len(sys.argv) < 3:
        print("Usage: python icon_import_theme.py <theme> <size>", file=sys.stderr)
        print(f"Themes: {', '.join(KNOWN_THEMES)}", file=sys.stderr)
        sys.exit(1)

    theme = sys.argv[1]
    try:
        target_size = int(sys.argv[2])
    except ValueError:
        print(f"ERROR: size must be an integer, got '{sys.argv[2]}'", file=sys.stderr)
        sys.exit(1)

    if theme not in KNOWN_THEMES:
        print(f"ERROR: Unknown theme '{theme}'", file=sys.stderr)
        print(f"Available: {', '.join(KNOWN_THEMES)}", file=sys.stderr)
        sys.exit(1)

    # Paths
    tools_json_path = DATA_DIR / f"{theme}.json"
    app_json_path = ICONS_DIR / f"{theme}.json"
    theme_source = THEME_SOURCES[theme]

    if not tools_json_path.is_file():
        print(f"ERROR: {tools_json_path} not found", file=sys.stderr)
        sys.exit(1)

    if not theme_source.is_dir():
        print(f"ERROR: Source directory not found: {theme_source}", file=sys.stderr)
        sys.exit(1)

    print(f"Theme: {theme}")
    print(f"Target size: {target_size}px")
    print(f"Source: {theme_source}")

    # Load tools catalog
    with open(tools_json_path) as f:
        tools_data = json.load(f)

    # Load or create app JSON
    if app_json_path.is_file():
        with open(app_json_path) as f:
            app_data = json.load(f)
        print(f"Resuming: {app_json_path}")
    else:
        app_data = {
            "_comment": f"Icons imported from {theme.title()} theme. See ICON_THEME_CATALOG.json for theme metadata.",
            "icons": {}
        }
        print(f"Creating: {app_json_path}")

    tools_icons = tools_data.get("icons", {})
    app_icons = app_data.get("icons", {})

    # Count already done
    already_done = sum(1 for v in tools_icons.values() if "inherits" in v)
    remaining = len(tools_icons) - already_done

    print(f"Total: {len(tools_icons)}, Already done: {already_done}, Remaining: {remaining}")

    if remaining == 0:
        print("ALL_DONE")
        return

    # Get categories and create directories
    categories = set()
    for icon_data in tools_icons.values():
        if "category" in icon_data:
            categories.add(icon_data["category"])

    for category in sorted(categories):
        cat_dir = ICONS_DIR / theme / f"{target_size}x{target_size}" / category
        cat_dir.mkdir(parents=True, exist_ok=True)

    # Process one icon at a time
    processed = 0
    for icon_key, icon_data in tools_icons.items():
        # Skip if already processed
        if "inherits" in icon_data:
            continue

        # Get required fields
        category = icon_data.get("category")
        filename = icon_data.get("file")
        sizes = icon_data.get("sizes", [])
        name = icon_data.get("label")
        hints = icon_data.get("hints", [])
        is_duplicate = "duplicate_of" in icon_data

        if not filename or not category:
            print(f"ERROR: {icon_key} missing file or category - STOPPING")
            sys.exit(1)

        if not name:
            print(f"ERROR: {icon_key} missing name field - STOPPING")
            sys.exit(1)

        # Build app JSON entry
        app_entry = {
            "label": name,
            "category": category,
            "file": filename,
            "source_sizes": sizes,
            "hints": hints,
        }

        if is_duplicate:
            # Duplicate: no image copy, sizes = []
            app_entry["sizes"] = []
            app_entry["duplicate_of"] = icon_data["duplicate_of"]
            action = "dup"
        else:
            # Primary: copy or resize image
            dst_path = ICONS_DIR / theme / f"{target_size}x{target_size}" / category / filename

            if target_size in sizes:
                # Step 1: Direct copy image
                src_path = theme_source / f"{target_size}x{target_size}" / category / filename
                if not src_path.exists():
                    print(f"ERROR: {icon_key} source not found: {src_path} - STOPPING")
                    sys.exit(1)
                shutil.copy2(src_path, dst_path)
                app_entry["sizes"] = [target_size]
                action = "copy"
            else:
                # Step 1: Resize image from smallest available
                src_path, src_size = find_source_image(theme_source, category, filename, sizes)
                if not src_path:
                    print(f"ERROR: {icon_key} no source found for resize - STOPPING")
                    sys.exit(1)
                resize_image(src_path, dst_path, target_size)
                app_entry["sizes"] = [target_size]
                action = f"resize({src_size})"

            # Copy duplicates array if present
            if "duplicates" in icon_data:
                app_entry["duplicates"] = icon_data["duplicates"]

        # Step 2: Add to app JSON and save
        app_icons[icon_key] = app_entry
        app_data["icons"] = app_icons
        save_json_compact_arrays(app_json_path, app_data)

        # Step 3: Mark as done in tools JSON and save (commit marker)
        icon_data["inherits"] = icon_key
        save_json_compact_arrays(tools_json_path, tools_data)

        processed += 1
        print(f"[{already_done + processed}/{len(tools_icons)}] {action}: {icon_key}")

    print(f"\n--- DONE ---")
    print(f"Processed: {processed}")
    print(f"Total in app JSON: {len(app_icons)}")


if __name__ == "__main__":
    main()
