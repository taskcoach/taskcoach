#!/usr/bin/env python3
"""Generate translation files from icon library JSON files.

Usage:
    python tools/generate_icon_i18n.py [theme]

If theme is specified, only regenerate that theme's .py file.
If no theme specified, regenerate all themes with icons.

Examples:
    python tools/generate_icon_i18n.py           # Regenerate all
    python tools/generate_icon_i18n.py oxygen    # Regenerate oxygen only
"""

import json
import sys
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
ICONS_DIR = REPO_ROOT / "taskcoachlib" / "gui" / "icons"


def generate_i18n_py(theme: str) -> bool:
    """Generate {theme}_i18n.py from {theme}.json.

    Returns True if file was generated, False if no icons to generate.
    """
    json_path = ICONS_DIR / f"{theme}.json"
    py_path = ICONS_DIR / f"{theme}_i18n.py"

    if not json_path.exists():
        print(f"Error: {json_path} not found")
        return False

    with open(json_path, "r") as f:
        data = json.load(f)

    icons = data.get("icons", {})
    if not icons:
        print(f"No icons in {theme}.json, skipping")
        return False

    lines = [
        f"# Generated from {theme}.json - DO NOT EDIT MANUALLY",
        f"# Regenerate with: python tools/generate_icon_i18n.py {theme}",
        "from taskcoachlib.i18n import _",
        "",
        "icons = {",
    ]

    for icon_id, info in sorted(icons.items()):
        name = info.get("label", "")
        hints = info.get("hints", [])

        if not name and not hints:
            continue

        lines.append(f'    "{icon_id}": {{')

        if name:
            # Escape any quotes in the name
            escaped_name = name.replace('"', '\\"')
            lines.append(f'        "label": _("{escaped_name}"),')

        if hints:
            hints_str = ", ".join(f'_("{h}")' for h in hints)
            lines.append(f'        "hints": [{hints_str}],')

        lines.append("    },")

    lines.append("}")
    lines.append("")  # Trailing newline

    with open(py_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Generated {py_path}")
    return True


def get_themes_with_icons() -> list[str]:
    """Return list of themes that have icons in their JSON files."""
    themes = []
    for json_file in ICONS_DIR.glob("*.json"):
        # Skip catalog and mapping files
        if json_file.name in ("ICON_THEME_CATALOG.json", "ICON_MAPPING.json"):
            continue

        with open(json_file, "r") as f:
            data = json.load(f)

        if data.get("icons"):
            themes.append(json_file.stem)

    return sorted(themes)


def main():
    if len(sys.argv) > 1:
        theme = sys.argv[1]
        generate_i18n_py(theme)
    else:
        themes = get_themes_with_icons()
        if not themes:
            print("No themes with icons found")
            return

        print(f"Regenerating {len(themes)} theme(s): {', '.join(themes)}")
        for theme in themes:
            generate_i18n_py(theme)


if __name__ == "__main__":
    main()
