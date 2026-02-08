"""Icon library - loads icons from theme JSON files and resolves paths.

Modeled after tools/icon_theme_processor.py but focused on runtime path resolution.
Uses path_pattern from ICON_THEME_CATALOG.json to build icon file paths.

Path patterns:
- nuvola/oxygen/papirus: {theme}/{size}x{size}/{category}/{file}
- breeze: {theme}/{category}/{size}/{file}
- taskcoach: {size}x{size}/{file}
- legacy: {file} (with size in filename like icon16x16.png)
"""

import json
import os

from taskcoachlib.meta.debug import log_step

# Module directory (taskcoachlib/gui/icons/)
_ICONS_DIR = os.path.dirname(os.path.abspath(__file__))

# Cache for loaded data
_catalog = None
_theme_icons = {}


def _load_catalog():
    """Load and cache the theme catalog."""
    global _catalog
    if _catalog is None:
        catalog_path = os.path.join(_ICONS_DIR, "ICON_THEME_CATALOG.json")
        if os.path.exists(catalog_path):
            try:
                with open(catalog_path, "r", encoding="utf-8") as f:
                    _catalog = json.load(f)
            except json.JSONDecodeError as e:
                log_step(f"ERROR: Failed to parse {catalog_path}: {e}", prefix="ICON")
                _catalog = {}
        else:
            log_step(f"ERROR: Theme catalog not found: {catalog_path}", prefix="ICON")
            _catalog = {}
    return _catalog


def _load_theme_icons(theme):
    """Load and cache icons from a theme JSON file."""
    global _theme_icons
    if theme not in _theme_icons:
        catalog = _load_catalog()
        theme_config = catalog.get(theme, {})

        if not theme_config:
            log_step(f"ERROR: Theme '{theme}' not found in catalog", prefix="ICON")
            _theme_icons[theme] = {}
            return _theme_icons[theme]

        icons_file = theme_config.get("icons_file")
        if not icons_file:
            log_step(f"ERROR: Theme '{theme}' has no icons_file in catalog", prefix="ICON")
            _theme_icons[theme] = {}
            return _theme_icons[theme]

        json_path = os.path.join(_ICONS_DIR, icons_file)
        if not os.path.exists(json_path):
            log_step(f"ERROR: Theme icons file not found: {json_path}", prefix="ICON")
            _theme_icons[theme] = {}
            return _theme_icons[theme]

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            _theme_icons[theme] = data.get("icons", {})
        except json.JSONDecodeError as e:
            log_step(f"ERROR: Failed to parse {json_path}: {e}", prefix="ICON")
            _theme_icons[theme] = {}

    return _theme_icons[theme]


def build_icon_path(theme, category, filename, size):
    """Build full path to an icon file using the theme's path pattern.

    Args:
        theme: Theme name (e.g., "nuvola", "legacy")
        category: Category name (e.g., "devices") - may be empty for some themes
        filename: Icon filename with extension (e.g., "printer.png")
        size: Icon size as int (e.g., 16)

    Returns:
        Absolute path to icon file, or None on error.
    """
    if not filename:
        log_step(f"ERROR: build_icon_path called with empty filename for theme '{theme}'", prefix="ICON")
        return None

    # Legacy theme: flat format with size in filename
    if theme == "legacy":
        stem, ext = os.path.splitext(filename)
        size_str = f"{size}x{size}"
        return os.path.join(_ICONS_DIR, f"{stem}{size_str}{ext}")

    # Other themes: use path pattern from catalog
    catalog = _load_catalog()
    theme_config = catalog.get(theme, {})
    path_pattern = theme_config.get("path_pattern")

    if not path_pattern:
        log_step(f"ERROR: Theme '{theme}' has no path_pattern in catalog", prefix="ICON")
        return None

    # Build path by substituting pattern variables
    size_str = f"{size}x{size}"
    path = path_pattern
    path = path.replace("{theme}", theme)
    path = path.replace("{size}x{size}", size_str)
    path = path.replace("{size}", str(size))
    if category:
        path = path.replace("{category}", category)
    path = path.replace("{file}", filename)

    return os.path.join(_ICONS_DIR, path)


def get_chooseable_icons(theme):
    """Get icons from a theme suitable for the icon picker.

    Args:
        theme: Theme name (e.g., "nuvola")

    Returns:
        Dict of {icon_key: {"label": ..., "hints": [...], "theme": ..., "category": ..., "file": ...}}
        Only returns primary icons (skips duplicates).
    """
    if not theme:
        log_step("ERROR: get_chooseable_icons called with empty theme", prefix="ICON")
        return {}

    icons = _load_theme_icons(theme)
    result = {}

    for icon_key, icon_data in icons.items():
        # Skip duplicates
        if "duplicate_of" in icon_data:
            continue

        # Validate required fields
        filename = icon_data.get("file")
        if not filename:
            log_step(f"ERROR: Icon '{icon_key}' missing 'file' field", prefix="ICON")
            continue

        label = icon_data.get("label")
        if not label:
            log_step(f"ERROR: Icon '{icon_key}' missing 'label' field", prefix="ICON")
            continue

        result[icon_key] = {
            "label": label,
            "hints": icon_data.get("hints", []),
            "theme": theme,  # Store key, use get_theme_label() for display
            "category": icon_data.get("category", ""),
            "file": filename,
        }

    return result


def get_theme_label(theme):
    """Get display label for a theme (e.g., 'Nuvola' for 'nuvola')."""
    catalog = _load_catalog()
    theme_config = catalog.get(theme, {})
    return theme_config.get("name", theme.title())


def get_available_themes():
    """Get list of themes that have icon JSON files in the app directory."""
    themes = []
    catalog = _load_catalog()
    for theme_name, theme_config in catalog.items():
        icons_file = theme_config.get("icons_file")
        if icons_file:
            json_path = os.path.join(_ICONS_DIR, icons_file)
            if os.path.exists(json_path):
                themes.append(theme_name)
    return themes
