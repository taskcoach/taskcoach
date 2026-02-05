#!/usr/bin/env python3
"""Find the next icon without hints in the catalog JSONs and list all image paths.

For each icon, searches the ENTIRE theme repo for every file matching the bare
filename, hashes them all, and reports everything.  The worker does the analysis.
See the plan for the worker procedure when CONFLICT or (dup) flags appear.
"""

import json
import os
import hashlib
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
ICONS_DIR = os.path.expanduser("~/Downloads/icons")


def rel_path(abs_path):
    """Convert absolute path to relative path from PROJECT_DIR."""
    rel = os.path.relpath(abs_path, PROJECT_DIR)
    if not rel.startswith(".."):
        rel = "./" + rel
    return rel

# Catalogs in processing order.
# "search_root": top-level repo dir, searched recursively for all occurrences.
# "base": structured icon tree, used only for path display (rel paths).
CATALOGS = [
    {
        "file": "nuvola_github.json",
        "search_root": os.path.join(ICONS_DIR, "nuvola-icon-theme-master"),
        "base": os.path.join(ICONS_DIR, "nuvola-icon-theme-master/usr/share/icons/nuvola"),
    },
    {
        "file": "nuvola_local_zip.json",
        "search_root": os.path.join(ICONS_DIR, "nuvola_local_zip"),
        "base": os.path.join(ICONS_DIR, "nuvola_local_zip"),
    },
    {
        "file": "papirus.json",
        "search_root": os.path.join(ICONS_DIR, "papirus-icon-theme-master"),
        "base": os.path.join(ICONS_DIR, "papirus-icon-theme-master/Papirus"),
    },
    {
        "file": "breeze.json",
        "search_root": os.path.join(ICONS_DIR, "breeze-icons-master"),
        "base": os.path.join(ICONS_DIR, "breeze-icons-master/icons"),
    },
    {
        "file": "oxygen.json",
        "search_root": os.path.join(ICONS_DIR, "oxygen-icons-master"),
        "base": os.path.join(ICONS_DIR, "oxygen-icons-master"),
    },
    {
        "file": "internal.json",
        "search_root": os.path.join(PROJECT_DIR, "taskcoachlib/gui/icons"),
        "base": os.path.join(PROJECT_DIR, "taskcoachlib/gui/icons"),
    },
]


def find_all_on_disk(search_root, icon_key):
    """Recursively search the entire theme directory for all files matching the icon's bare name.

    icon_key is e.g. "actions/message.png". We extract the stem ("message") and
    search for message.png and message.svg anywhere under search_root.

    Returns a list of all matching absolute paths, in os.walk discovery order.
    """
    basename = os.path.basename(icon_key)
    stem, _ = os.path.splitext(basename)
    targets = {stem + ".png", stem + ".svg"}

    hits = []
    for dirpath, dirnames, filenames in os.walk(search_root):
        for fn in filenames:
            if fn in targets:
                hits.append(os.path.join(dirpath, fn))
    return hits


def main():
    for cat_info in CATALOGS:
        json_path = os.path.join(SCRIPT_DIR, cat_info["file"])
        if not os.path.isfile(json_path):
            continue

        with open(json_path) as f:
            data = json.load(f)

        icons = data.get("icons", {})
        total = len(icons)
        done = sum(1 for v in icons.values() if "hints" in v or "inherits" in v)

        for icon_key, icon_data in icons.items():
            if "hints" in icon_data or "inherits" in icon_data:
                continue

            # Found the next Named Icon to process
            json_sizes = sorted(icon_data.get("sizes", []))
            all_hits = find_all_on_disk(cat_info["search_root"], icon_key)

            # Expected category from icon_key, e.g. "actions" from "actions/message.png"
            category = icon_key.split("/")[0] if "/" in icon_key else None
            cat_pattern = f"/{category}/" if category else None

            # Hash and measure all files
            file_info = []  # [(path, hash, size_bytes)]
            for path in all_hits:
                with open(path, "rb") as fh:
                    data_bytes = fh.read()
                h = hashlib.md5(data_bytes).hexdigest()[:12]
                file_info.append((path, h, len(data_bytes)))

            # Pick READ_FILE: largest (by bytes) file in expected category
            read_file = None
            best_size = -1
            for path, h, sz in file_info:
                if cat_pattern and cat_pattern in path and sz > best_size:
                    best_size = sz
                    read_file = path

            print(f"CURRENT JSON ENTRY ({rel_path(json_path)})")
            print(f"  \"key\": \"{icon_key}\"")
            print(f"  \"sizes\": {json_sizes}")

            # List all files with hash, size, and flags (sorted by size desc)
            file_info.sort(key=lambda x: x[2], reverse=True)

            # Count hash occurrences to identify duplicates
            hash_counts = {}
            for path, h, sz in file_info:
                hash_counts[h] = hash_counts.get(h, 0) + 1

            has_conflicts = False
            has_dups = False

            print("DISK_FILES:")
            for path, h, sz in file_info:
                flags = []

                # Dup check: hash appears more than once
                if hash_counts[h] > 1:
                    flags.append("Duplicate")
                    has_dups = True

                # Conflict check: outside expected category
                in_category = cat_pattern and cat_pattern in path
                if not in_category:
                    flags.append("Conflict-Maybe")
                    has_conflicts = True

                flag_str = "  " + "  ".join(flags) if flags else ""
                print(f"  {h}  {sz}b{flag_str}  {rel_path(path)}")

            # Worker instruction blocks
            largest_file = rel_path(file_info[0][0]) if file_info else None
            pack_name = os.path.splitext(cat_info["file"])[0]
            print("NEXT STEP - WORKER INSTRUCTIONS")
            print("- Review the ABOVE file paths to verify the JSON \"sizes\" array is correct.")
            print("  Update it if the disk files show sizes not listed in the JSON.")
            print("  Format: \"sizes\" must be a SINGLE LINE array e.g.: \"sizes\": [#, #, ...]")
            print("- View the largest file (the first in the list). Then, generate 5-8 \"hints\"")
            print("  based on what you SEE in the image + filename context. Then, edit the JSON to")
            print("  add \"hints\": [...] array for this icon's key. Format: \"hints\" must be a")
            print("  SINGLE LINE array, e.g.: \"hints\": [\"keyword1\", \"keyword2\", ...]")
            if has_conflicts:
                print("- Conflict-Maybe FOUND. First, determine how many truly different")
                print("  icons (Named Icons) exist by grouping the ABOVE files by hash — each")
                print("  unique hash is a different icon. Then for each unique icon:")
                print("    CATEGORIZED (path contains a recognized category like /apps/, /devices/):")
                print("      Derive key as category/filename (e.g. apps/foo.png). Check if it")
                print("      exists in the JSON. If not, view the file, create a JSON entry with")
                print('      a proper non-duplicate Icon Name, "hints", "sizes", and log in anomaly file.')
                print("    UNSTRUCTURED (path has NO recognized category — loose file like 2/foo.png):")
                print("      Derive key from relative path to search_root (e.g. 2/foo.png). Add to")
                print('      JSON with "unstructured": true, "hints", and "sizes" from the file itself.')
                print("      Log the addition in the anomaly file.")
            if has_dups:
                print("- Duplicate FOUND. Duplicate hashes are mostly informational to")
                print("  help in your analysis. These are identical copies and usually")
                print("  need no action.")
            print("- If stuck (unreadable, missing, ambiguous): add \"hints\": [\"FATAL-ERROR\"] to the JSON,")
            print("  log the issue to the anomaly file, then run the script again to continue.")
            print(f"  Anomaly log: ./tools/icon_grid_browser_data/{pack_name}_anomalies.txt")
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
