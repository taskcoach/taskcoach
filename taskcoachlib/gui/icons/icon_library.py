"""Icon library - loads icons from pre-generated icons_parsed.py modules.

At runtime, imports icons_parsed.py (pre-computed by generate_icons_parsed_py.py)
which contains all icon metadata and pre-resolved file paths. No JSON or
index.theme parsing happens at runtime.

Legacy theme is the only exception: flat files with size in filename.
"""

import importlib
import json
import os

from taskcoachlib.meta.debug import log_step

# Module directory (taskcoachlib/gui/icons/)
_ICONS_DIR = os.path.dirname(os.path.abspath(__file__))

# Cache for loaded data
_catalog = None
_theme_parsed = {}  # theme -> icons_parsed module data
_duplicate_map = None  # {duplicate_key: target_key} built from all themes
_failed_icons = set()  # icon keys that failed to load as bitmaps


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


def _load_theme_parsed(theme):
    """Load and cache icons_parsed.py module for a theme.

    Returns dict with 'icons' and 'contexts' from the module.
    """
    global _theme_parsed
    if theme not in _theme_parsed:
        module_name = f"taskcoachlib.gui.icons.{theme}.icons_parsed"
        try:
            mod = importlib.import_module(module_name)
            _theme_parsed[theme] = {
                "icons": getattr(mod, "icons", {}),
                "contexts": getattr(mod, "contexts", {}),
            }
        except ImportError as e:
            log_step(f"ERROR: Failed to import {module_name}: {e}", prefix="ICON")
            _theme_parsed[theme] = {"icons": {}, "contexts": {}}

    return _theme_parsed[theme]


def _build_duplicate_map():
    """Build {duplicate_key: target_key} from all loaded themes.

    Called once after themes are loaded. Walks all icons in all themes
    and maps any icon with duplicate_of to its target.
    """
    global _duplicate_map
    _duplicate_map = {}
    for theme_data in _theme_parsed.values():
        for icon_key, icon_data in theme_data["icons"].items():
            target = icon_data.get("duplicate_of")
            if target:
                _duplicate_map[icon_key] = target


def resolve_duplicate(icon_name):
    """Resolve a duplicate icon name to its target.

    If icon_name is a duplicate_of another icon, returns the target
    and logs the conversion. Otherwise returns icon_name unchanged.
    """
    if not icon_name or _duplicate_map is None:
        return icon_name
    target = _duplicate_map.get(icon_name)
    if target:
        log_step(f"Resolving duplicate icon '{icon_name}' -> '{target}'", prefix="ICON")
        return target
    return icon_name


def get_context_label(theme, context_id):
    """Get display label for a context (e.g., 'Actions' for 'actions').

    Reads from icons_parsed.py contexts dict.
    """
    parsed = _load_theme_parsed(theme)
    return parsed["contexts"].get(context_id, context_id.title())


def build_icon_path(theme, icon_key, size):
    """Build full path to an icon file using pre-computed paths.

    Looks up the icon_key in icons_parsed.py and returns the absolute
    path for the requested size. No index.theme parsing at runtime.

    Args:
        theme: Theme name (e.g., "nuvola", "legacy")
        icon_key: Icon key (e.g., "nuvola_devices_print_printer")
        size: Icon size as int (e.g., 16)

    Returns:
        Absolute path to icon file, or None if not found.
    """
    parsed = _load_theme_parsed(theme)
    icon_data = parsed["icons"].get(icon_key)
    if not icon_data:
        log_step(f"ERROR: Icon key '{icon_key}' not found in theme '{theme}'", prefix="ICON")
        return None

    paths = icon_data.get("paths", {})
    rel_path = paths.get(size)
    if not rel_path:
        available = sorted(paths.keys()) if paths else []
        log_step(f"ERROR: Icon '{icon_key}' has no size {size} (available: {available})", prefix="ICON")
        return None
    return os.path.join(_ICONS_DIR, theme, rel_path)


def build_legacy_icon_path(filename, size):
    """Build path for a legacy icon (flat format with size in filename).

    Args:
        filename: Icon filename with extension (e.g., "printer.png")
        size: Icon size as int (e.g., 16)

    Returns:
        Absolute path to icon file.
    """
    stem, ext = os.path.splitext(filename)
    return os.path.join(_ICONS_DIR, f"{stem}{size}x{size}{ext}")


def get_chooseable_icons(theme):
    """Get icons from a theme suitable for the icon picker.

    Args:
        theme: Theme name (e.g., "nuvola")

    Returns:
        Dict of {icon_key: {"label": ..., "hints": [...], "theme": ...,
                             "context": ..., "file": ..., "paths": {...}}}
        Only returns primary icons (skips duplicates).
    """
    if not theme:
        log_step("ERROR: get_chooseable_icons called with empty theme", prefix="ICON")
        return {}

    parsed = _load_theme_parsed(theme)
    icons = parsed["icons"]
    result = {}

    for icon_key, icon_data in icons.items():
        # Skip duplicates
        if "duplicate_of" in icon_data:
            continue

        # Validate required fields
        file_name = icon_data.get("file")
        if not file_name:
            log_step(f"ERROR: Icon '{icon_key}' missing 'file' field", prefix="ICON")
            continue

        label = icon_data.get("label")
        if not label:
            log_step(f"ERROR: Icon '{icon_key}' missing 'label' field", prefix="ICON")
            continue

        paths = icon_data.get("paths", {})
        if not paths:
            log_step(f"ERROR: Icon '{icon_key}' has no sizes, skipping", prefix="ICON")
            continue

        result[icon_key] = {
            "label": label,
            "hints": icon_data.get("hints", []),
            "theme": theme,
            "context": icon_data.get("context", ""),
            "file": file_name,
            "paths": icon_data.get("paths", {}),
        }

    return result


def get_theme_label(theme):
    """Get display label for a theme (e.g., 'Nuvola' for 'nuvola')."""
    catalog = _load_catalog()
    theme_config = catalog.get(theme, {})
    return theme_config.get("name", theme.title())


def get_available_themes():
    """Get list of active themes that have icons_parsed.py in the app directory."""
    themes = []
    catalog = _load_catalog()
    for theme_name, theme_config in catalog.items():
        if not theme_config.get("active", False):
            continue
        parsed_path = os.path.join(_ICONS_DIR, theme_name, "icons_parsed.py")
        if os.path.exists(parsed_path):
            themes.append(theme_name)
        else:
            log_step(f"ERROR: Active theme '{theme_name}' missing {theme_name}/icons_parsed.py", prefix="ICON")
    return themes


# --- Phase B: Deferred error tracking ---

def mark_icon_failed(icon_key):
    """Record that an icon failed to load as a bitmap."""
    _failed_icons.add(icon_key)


def get_failed_icons():
    """Return the set of icon keys that failed to load."""
    return frozenset(_failed_icons)


def is_icon_in_catalog(icon_key):
    """Check if an icon key exists in any loaded theme's parsed data."""
    for theme_data in _theme_parsed.values():
        if icon_key in theme_data["icons"]:
            return True
    return False


# --- Phase C: Prevalidation after task file load ---

def validate_icons(all_chooseable, tasks=None, categories=None, notes=None):
    """Validate all icon references after task file load.

    Checks every task, category, and note that has an icon assigned.
    Reports two kinds of errors:
    - MISSING FROM CATALOG: icon name not in chooseableItems
    - FAILED TO LOAD: icon was in catalog but bitmap failed to load

    Args:
        all_chooseable: The chooseableItems dict from artprovider
        tasks: list of root task objects
        categories: list of root category objects
        notes: list of root note objects
    """
    failed = get_failed_icons()
    errors = []

    def _check_object(obj, path_parts):
        """Check a single object's icon and recurse into children."""
        obj_type = type(obj).__name__
        subject = getattr(obj, "subject", lambda: "")()
        current = f"[{obj_type}] {subject}"
        current_path = path_parts + [current]

        icon_name = obj.icon() if hasattr(obj, "icon") else ""
        if icon_name:
            path_str = " -> ".join(current_path)
            if icon_name not in all_chooseable:
                if not is_icon_in_catalog(icon_name):
                    errors.append(f"MISSING FROM CATALOG: '{icon_name}' at {path_str}")
            if icon_name in failed:
                errors.append(f"FAILED TO LOAD: '{icon_name}' at {path_str}")

        # Recurse into children
        if hasattr(obj, "children"):
            for child in obj.children():
                _check_object(child, current_path)
        if hasattr(obj, "notes"):
            for child_note in obj.notes():
                _check_object(child_note, current_path)

    for collection, label in [(categories, "categories"),
                              (tasks, "tasks"),
                              (notes, "notes")]:
        if collection:
            for obj in collection:
                _check_object(obj, [])

    for error in errors:
        log_step(f"ERROR: Icon {error}", prefix="ICON")
