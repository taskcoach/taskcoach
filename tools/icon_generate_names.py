#!/usr/bin/env python3
"""Generate 'name' field for icons in catalog JSON files.

Usage:
    python tools/icon_generate_names.py <theme>

Arguments:
    theme: Theme name (nuvola, oxygen, papirus, breeze, internal)

Generates names from filenames:
    - Remove extension (.png, .svg)
    - Replace '-' and '_' with space
    - Title case each word

Logs warnings for filenames with unexpected characters (not [a-zA-Z0-9_-]).

Examples:
    python tools/icon_generate_names.py nuvola
    python tools/icon_generate_names.py oxygen
"""

import json
import os
import re
import sys

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "icon_grid_browser_data")

# Known themes
KNOWN_THEMES = ["nuvola", "oxygen", "papirus", "breeze", "internal"]


def save_json_compact_arrays(filepath, data):
    """Save JSON with indent=2 but arrays on single lines."""
    text = json.dumps(data, indent=2)
    # Collapse multi-line arrays to single lines
    def collapse_array(match):
        content = match.group(0)
        collapsed = re.sub(r'\[\s+', '[', content)
        collapsed = re.sub(r'\s+\]', ']', collapsed)
        collapsed = re.sub(r',\s+', ', ', collapsed)
        return collapsed
    text = re.sub(r'\[\s*\n\s+[^\[\]]*?\s*\]', collapse_array, text)
    with open(filepath, "w") as f:
        f.write(text)


def generate_name_from_filename(filename):
    """Generate display name from filename.

    - Remove extension
    - Replace '-' and '_' with space
    - Title case each word

    Examples:
        printer.png -> Printer
        multimedia-player.png -> Multimedia Player
        print_printer.png -> Print Printer
    """
    # Remove extension
    stem = os.path.splitext(filename)[0]

    # Replace - and _ with space
    name = stem.replace('-', ' ').replace('_', ' ')

    # Title case
    name = name.title()

    return name


def check_unexpected_characters(filename):
    """Check if filename has unexpected characters.

    Expected: a-z, A-Z, 0-9, -, _, and . (for extension)
    Returns list of unexpected characters found, or empty list if clean.
    """
    stem = os.path.splitext(filename)[0]
    # Find characters that are NOT alphanumeric, dash, or underscore
    unexpected = re.findall(r'[^a-zA-Z0-9_-]', stem)
    return list(set(unexpected))


def main():
    if len(sys.argv) < 2:
        print("Usage: python icon_generate_names.py <theme>", file=sys.stderr)
        print(f"Themes: {', '.join(KNOWN_THEMES)}", file=sys.stderr)
        sys.exit(1)

    theme = sys.argv[1]
    if theme not in KNOWN_THEMES:
        print(f"Error: Unknown theme '{theme}'", file=sys.stderr)
        print(f"Available: {', '.join(KNOWN_THEMES)}", file=sys.stderr)
        sys.exit(1)

    json_path = os.path.join(DATA_DIR, f"{theme}.json")
    if not os.path.isfile(json_path):
        print(f"Error: {json_path} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Theme: {theme}")
    print(f"File: {json_path}")

    with open(json_path) as f:
        data = json.load(f)

    icons = data.get("icons", {})
    total = len(icons)
    already_have_name = 0
    names_added = 0
    errors = []

    for icon_key, icon_data in icons.items():
        # Check if name already exists first
        if "label" in icon_data:
            already_have_name += 1
            continue

        # Get filename
        filename = icon_data.get("file", "")
        if not filename:
            errors.append(f"ERROR: {icon_key} has no 'file' field")
            continue

        # Check for unexpected characters - skip these entries
        unexpected = check_unexpected_characters(filename)
        if unexpected:
            errors.append(f"ERROR: {icon_key} has unexpected characters: {unexpected}")
            continue  # Do NOT process - skip until resolved

        # Generate name
        name = generate_name_from_filename(filename)
        icon_data["label"] = name
        names_added += 1

    # Print errors
    if errors:
        print(f"\n--- ERRORS ({len(errors)}) - NOT PROCESSED ---")
        for e in errors:
            print(e)

    # Print summary
    print(f"\n--- SUMMARY ---")
    print(f"Total icons: {total}")
    print(f"Already had name: {already_have_name}")
    print(f"Names added: {names_added}")
    print(f"Errors (skipped): {len(errors)}")

    if names_added > 0:
        save_json_compact_arrays(json_path, data)
        print(f"\nUpdated: {json_path}")
    else:
        print(f"\nNo changes needed.")


if __name__ == "__main__":
    main()
