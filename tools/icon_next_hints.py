#!/usr/bin/env python3
"""Find the next icon without hints in the catalog JSONs and list all image paths.

For each icon, searches the ENTIRE theme repo for every file matching the bare
filename, hashes them all, and reports everything.  The worker does the analysis.
See the plan for the worker procedure when CONFLICT or (dup) flags appear.
"""

import json
import os
import hashlib
import re
import sys

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "icon_grid_browser_data")
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

from icon_theme_processor import ThemeProcessor, load_canon_themes
ICONS_DIR = os.path.expanduser("~/Downloads/icons")

_canon_themes = load_canon_themes()


def save_json_compact_arrays(filepath, data):
    """Save JSON with indent=2 but arrays on single lines."""
    text = json.dumps(data, indent=2)
    # Collapse multi-line arrays to single lines
    # Match arrays that span multiple lines and contain only simple values
    def collapse_array(match):
        content = match.group(0)
        # Remove newlines and extra spaces, keep single spaces after commas
        collapsed = re.sub(r'\[\s+', '[', content)
        collapsed = re.sub(r'\s+\]', ']', collapsed)
        collapsed = re.sub(r',\s+', ', ', collapsed)
        return collapsed
    # Match arrays: [ followed by values on multiple lines ending with ]
    text = re.sub(r'\[\s*\n\s+[^\[\]]*?\s*\]', collapse_array, text)
    with open(filepath, "w") as f:
        f.write(text)


def rel_path(abs_path):
    """Convert absolute path to relative path from PROJECT_DIR."""
    rel = os.path.relpath(abs_path, PROJECT_DIR)
    if not rel.startswith(".."):
        rel = "./" + rel
    return rel


class HintsThemeProcessor(ThemeProcessor):
    """Extended ThemeProcessor with hints-specific functionality."""

    def __init__(self, cat_info):
        theme_name = cat_info.get("theme")
        if not theme_name:
            print(f"FATAL ERROR! STOP WORKING! No 'theme' specified for catalog: {cat_info['file']}")
            sys.exit(1)
        super().__init__(theme_name, cat_info["search_root"])
        self.cat_info = cat_info
        self.pack_name = os.path.splitext(cat_info["file"])[0]

    def log_anomaly(self, message):
        """Log to anomaly file."""
        anomaly_file = os.path.join(DATA_DIR, f"{self.pack_name}_anomalies.txt")
        with open(anomaly_file, "a") as af:
            af.write(f"{message}\n")
        print(f"Logged to: {rel_path(anomaly_file)}")

# Catalogs in processing order.
# "theme": key in ICON_THEME_CATALOG.json for path_pattern and categories.
# "search_root": top-level repo dir, searched recursively for all occurrences.
# "base": structured icon tree, used only for path display (rel paths).
LOCAL_THEMES_SORTED = [
    {
        "file": "nuvola.json",
        "theme": "nuvola",
        "search_root": os.path.join(ICONS_DIR, "nuvola"),
        "base": os.path.join(ICONS_DIR, "nuvola"),
    },
    {
        "file": "oxygen.json",
        "theme": "oxygen",
        "search_root": os.path.join(ICONS_DIR, "oxygen-icons-master"),
        "base": os.path.join(ICONS_DIR, "oxygen-icons-master"),
    },
    {
        "file": "papirus.json",
        "theme": "papirus",
        "search_root": os.path.join(ICONS_DIR, "papirus-icon-theme-master"),
        "base": os.path.join(ICONS_DIR, "papirus-icon-theme-master/Papirus"),
    },
    {
        "file": "breeze.json",
        "theme": "breeze",
        "search_root": os.path.join(ICONS_DIR, "breeze-icons-master"),
        "base": os.path.join(ICONS_DIR, "breeze-icons-master/icons"),
    },
    {
        "file": "internal.json",
        "theme": "taskcoach",
        "search_root": os.path.join(PROJECT_DIR, "taskcoachlib/gui/icons"),
        "base": os.path.join(PROJECT_DIR, "taskcoachlib/gui/icons"),
    },
]


def main():
    for cat_info in LOCAL_THEMES_SORTED:
        json_path = os.path.join(DATA_DIR, cat_info["file"])
        if not os.path.isfile(json_path):
            continue

        with open(json_path) as f:
            data = json.load(f)

        proc = HintsThemeProcessor(cat_info)
        icons = data.get("icons", {})
        total = len(icons)
        done = sum(1 for v in icons.values() if "hints" in v or "inherits" in v)

        for icon_key, icon_data in icons.items():
            if "hints" in icon_data or "inherits" in icon_data:
                continue

            # Found the next Named Icon to process
            json_sizes = sorted(icon_data.get("sizes", []))
            file_errors = []

            def log_file_error(error_msg):
                full_error = f"FILE_ERROR: {error_msg}"
                file_errors.append(full_error)
                proc.log_anomaly(f"{icon_key}: {full_error}")

            # Validate and extract category/file from icon_data
            validated = proc.validate_icon_data(icon_key, icon_data)
            category = validated["category"]
            filename = validated["file"]

            # FIRST PASS: Find SVGs and convert to PNG
            initial_hits = proc.find_all_on_disk(filename, category)
            svg_files = [p for p in initial_hits if p.endswith(".svg")]

            # Step 2: For each SVG, convert to PNG
            for svg_path in svg_files:
                result = proc.convert_svg_to_png(svg_path)
                if not result.endswith(".png"):
                    log_file_error(result)

            # Step 3: Verify all PNGs exist with non-zero size
            for svg_path in svg_files:
                png_path = svg_path[:-4] + ".png"
                if not os.path.exists(png_path):
                    log_file_error(f"PNG missing after conversion: {png_path}")
                elif os.path.getsize(png_path) == 0:
                    log_file_error(f"PNG has zero size: {png_path}")

            # If file errors, set hints and skip to next icon
            if file_errors:
                icon_data["hints"] = file_errors
                save_json_compact_arrays(json_path, data)
                continue

            # Step 4: Find all PNGs
            all_hits = [p for p in proc.find_all_on_disk(filename, category) if p.endswith(".png")]

            # Category already validated above
            expected_category = category

            # Hash, measure, and parse all files
            file_info = []  # [(path, hash, size_bytes, parsed)]
            for path in all_hits:
                with open(path, "rb") as fh:
                    data_bytes = fh.read()
                h = hashlib.md5(data_bytes).hexdigest()[:12]
                parsed = proc.parse(path)
                file_info.append((path, h, len(data_bytes), parsed))

            # Pick READ_FILE: largest (by bytes) file in expected category
            read_file = None
            best_size = -1
            for path, h, sz, parsed in file_info:
                path_cat = parsed["category"] if parsed else None
                if path_cat == expected_category and sz > best_size:
                    best_size = sz
                    read_file = path

            # Extract sizes from disk files in expected category and merge with JSON
            disk_sizes = set()
            for path, h, sz, parsed in file_info:
                if parsed and parsed.get("category") == expected_category:
                    disk_sizes.add(parsed["size"])
            merged_sizes = sorted(set(json_sizes) | disk_sizes)

            print(f"CURRENT JSON ENTRY ({rel_path(json_path)})")
            print(f"  \"key\": \"{icon_key}\"")
            print(f"  \"sizes\": {json_sizes}")

            # List all files with hash, size, and flags (sorted by size desc)
            file_info.sort(key=lambda x: x[2], reverse=True)

            # Count hash occurrences and detect color variants (single pass)
            hash_counts = {}
            file_variants = {}  # path -> "dark", "light", or None
            for path, h, sz, parsed in file_info:
                hash_counts[h] = hash_counts.get(h, 0) + 1
                if "-Dark" in path:
                    file_variants[path] = "dark"
                elif "-Light" in path:
                    file_variants[path] = "light"
                else:
                    file_variants[path] = None

            color_variants = sorted(set(v for v in file_variants.values() if v))

            has_dups = False

            # Check for conflicts (files outside expected category) - fatal error
            for path, h, sz, parsed in file_info:
                path_cat = parsed["category"] if parsed else None
                if path_cat != expected_category:
                    print(f"FATAL ERROR! STOP WORKING! Conflict: {rel_path(path)} is in category '{path_cat}', expected '{expected_category}'")
                    sys.exit(1)

            print("DISK_FILES:")
            for path, h, sz, parsed in file_info:
                flags = []

                # Color variant flag
                variant = file_variants[path]
                if variant:
                    flags.append(variant.capitalize())

                # Dup check: hash appears more than once
                if hash_counts[h] > 1:
                    flags.append("Duplicate")
                    has_dups = True

                flag_str = "  " + "  ".join(flags) if flags else ""
                print(f"  {h}  {sz}b{flag_str}  {rel_path(path)}")

            # Worker instruction blocks
            largest_file = rel_path(file_info[0][0]) if file_info else None
            print("NEXT STEP - WORKER INSTRUCTIONS")
            print("- Review the ABOVE file paths to verify the JSON \"sizes\" array is correct.")
            print("  Update it if the disk files show sizes not listed in the JSON.")
            print(f"  Use: \"sizes\": {merged_sizes}")
            print("  Format: \"sizes\" must always be a SINGLE LINE array.")
            print("- View the largest PNG file (the first PNG in the list). Then, generate 5-8 \"hints\"")
            print("  based on what you SEE in the image + filename context. Then, edit the JSON to")
            print("  add \"hints\": [...] array for this icon's key. Format: \"hints\" must be a")
            print("  SINGLE LINE array, e.g.: \"hints\": [\"keyword1\", \"keyword2\", ...]")
            if color_variants:
                print("- COLOR VARIANTS detected. View only the BASE image (not -Dark or -Light).")
                print("  Add to JSON: \"color_variants\": [\"dark\"] or [\"light\"] or [\"dark\", \"light\"] as applicable.")
            if has_dups:
                print("- Duplicate FOUND. Duplicate hashes are mostly informational to")
                print("  help in your analysis. These are identical copies and usually")
                print("  need no action.")
            print("- If stuck (unreadable, missing, ambiguous): add \"hints\": [\"FATAL-ERROR\"] to the JSON,")
            print("  log the issue to the anomaly file, then run the script again to continue.")
            print(f"  Anomaly log: ./tools/icon_grid_browser_data/{proc.pack_name}_anomalies.txt")
            print("- Commit and push branch icon-hints after processing ~25 icons, as a safety")
            print("  against a power failure, however this is NOT mean you have completed the work!")
            print("- Run this script again to get the next icon")
            print("- Go back to step 1 and execute the steps again (do not stop after pushing)")
            print("  Do not stop to summarize, discuss, get feedback or for anything else.")
            print("  Just run the script again keep looping and keep working!")

            return

    # If we get here, no icons need processing
    print("ALL_DONE")


if __name__ == "__main__":
    main()
