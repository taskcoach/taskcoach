#!/usr/bin/env python3
"""Generate icons_parsed.py from icon theme data files.

Reads icons.json, contexts.json, and index.theme for each active theme,
pre-resolves all icon file paths per size, and writes a single Python
module that the app imports at runtime. No JSON/theme parsing at runtime.

Also validates that the `sizes` field in each icon entry matches what's
actually on disk (errors on mismatch).

Usage:
    python tools/generate_icons_parsed_py.py [--update-sizes] [theme]

Options:
    --update-sizes  Rebuild `sizes` from disk and remove `source_sizes`,
                    saving changes back to icons.json.

If theme is specified, only regenerate that theme's icons_parsed.py file.
If no theme specified, regenerate all active themes with icons.

Examples:
    python tools/generate_icons_parsed_py.py                       # Regenerate all
    python tools/generate_icons_parsed_py.py oxygen                # Regenerate oxygen only
    python tools/generate_icons_parsed_py.py --update-sizes        # Rebuild sizes for all
    python tools/generate_icons_parsed_py.py --update-sizes nuvola # Rebuild sizes for nuvola
"""

import json
import os
import sys
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
ICONS_DIR = REPO_ROOT / "taskcoachlib" / "gui" / "icons"

# Import the Theme class from icon_theme_processor (unmodified copy from
# icon-distillery). We construct Theme objects directly, not via ThemeCatalog.
sys.path.insert(0, str(SCRIPT_DIR))
from icon_theme_processor import Theme, save_json_compact_arrays


def generate_icons_parsed_py(theme_id: str, update_sizes: bool = False) -> bool:
    """Generate {theme}/icons_parsed.py from theme data files.

    Uses the Theme class from icon_theme_processor to parse index.theme,
    contexts.json, and icons.json. Pre-resolves file paths for every icon
    at every available size.

    Always validates that `sizes` in icons.json matches sizes found on disk.

    If update_sizes is True, also:
    - Rebuilds `sizes` from disk (sorted list of sizes with files)
    - Removes `source_sizes` field
    - Saves changes back to icons.json

    Returns True if file was generated, False on error.
    """
    theme_dir = ICONS_DIR / theme_id
    icons_json = theme_dir / "icons.json"
    contexts_json = theme_dir / "contexts.json"
    index_theme = theme_dir / "index.theme"
    out_path = theme_dir / "icons_parsed.py"

    # Validate required files
    for required, label in [(icons_json, "icons.json"),
                            (contexts_json, "contexts.json"),
                            (index_theme, "index.theme")]:
        if not required.exists():
            print(f"Error: {label} not found: {required}")
            return False

    # Construct a Theme object. theme_dir is relative to _PROJECT_DIR which
    # is SCRIPT_DIR.parent (= REPO_ROOT). So we pass the relative path from
    # repo root.
    rel_theme_dir = str(theme_dir.relative_to(REPO_ROOT))
    config = {}  # minimal config — Theme only needs it for metadata we don't use
    theme = Theme(theme_id, theme_id, rel_theme_dir, config)

    icons_data = theme.icons_data
    icons = icons_data.get("icons", {})
    if not icons:
        print(f"No icons in {theme_id}/icons.json, skipping")
        return False

    contexts = theme.contexts or {}
    index = theme.index  # {dir_path: {size, xdg_context, ...}}

    # Build xdg_context -> internal_context_id reverse map
    xdg_to_internal = {}
    for ctx_id, ctx_info in contexts.items():
        xdg = ctx_info.get("xdg_context")
        if xdg:
            xdg_to_internal[xdg] = ctx_id

    # Build (size, xdg_context) -> [dir_paths] lookup from index
    size_context_dirs = {}
    for dir_path, meta in index.items():
        size = meta["effective_size"]
        xdg_context = meta["xdg_context"]
        key = (size, xdg_context)
        if key not in size_context_dirs:
            size_context_dirs[key] = []
        size_context_dirs[key].append(dir_path)

    # Resolve paths for each icon
    icons_output = {}
    for icon_id, icon_data in sorted(icons.items()):
        label = icon_data.get("label", "")
        hints = icon_data.get("hints", [])
        context_id = icon_data.get("context", "")
        filename = icon_data.get("file", "")
        duplicate_of = icon_data.get("duplicate_of")

        if not label and not hints:
            continue

        entry = {}
        if label:
            entry["label"] = label
        if hints:
            entry["hints"] = hints
        if context_id:
            entry["context"] = context_id
            ctx_info = contexts.get(context_id, {})
            context_label = ctx_info.get("context_label", context_id.title())
            entry["context_label"] = context_label
        if filename:
            entry["file"] = filename

        if duplicate_of:
            entry["duplicate_of"] = duplicate_of
            entry["paths"] = {}
            # Check for physical files that should not exist for duplicates
            if filename and context_id:
                xdg_context = contexts.get(context_id, {}).get("xdg_context")
                if xdg_context:
                    for (size, xdg_ctx), dir_paths in size_context_dirs.items():
                        if xdg_ctx != xdg_context:
                            continue
                        for dir_path in dir_paths:
                            full_path = theme_dir / dir_path / filename
                            if full_path.exists():
                                print(f"ERROR! Duplicate icon '{icon_id}' has physical file: {dir_path}/{filename} "
                                      f"(duplicate_of '{duplicate_of}') — remove the file or the duplicate_of flag",
                                      file=sys.stderr)
        elif filename and context_id:
            # Resolve paths using index.theme lookup
            xdg_context = contexts.get(context_id, {}).get("xdg_context")
            paths = {}
            if xdg_context:
                # Collect all sizes available in the index for this context
                seen_sizes = set()
                for (size, xdg_ctx), dir_paths in size_context_dirs.items():
                    if xdg_ctx != xdg_context:
                        continue
                    if size in seen_sizes:
                        continue
                    for dir_path in dir_paths:
                        full_path = theme_dir / dir_path / filename
                        if full_path.exists():
                            paths[size] = f"{dir_path}/{filename}"
                            seen_sizes.add(size)
                            break
            entry["paths"] = dict(sorted(paths.items()))
        elif filename:
            # No context — match entries without xdg_context
            paths = {}
            for (size, xdg_ctx), dir_paths in size_context_dirs.items():
                if xdg_ctx is not None:
                    continue
                for dir_path in dir_paths:
                    full_path = theme_dir / dir_path / filename
                    if full_path.exists():
                        paths[size] = f"{dir_path}/{filename}"
                        break
            entry["paths"] = dict(sorted(paths.items()))
        else:
            entry["paths"] = {}

        icons_output[icon_id] = entry

    # Validate sizes (always) and optionally update JSON
    validation_errors = 0
    json_modified = False
    for icon_id, icon_data in sorted(icons.items()):
        duplicate_of = icon_data.get("duplicate_of")
        resolved = icons_output.get(icon_id)
        if not resolved:
            continue

        # Remove source_sizes if updating
        if update_sizes and "source_sizes" in icon_data:
            del icon_data["source_sizes"]
            json_modified = True

        if duplicate_of:
            # Duplicates must NOT have files on disk or non-empty sizes
            disk_sizes = set(resolved.get("paths", {}).keys())
            if disk_sizes:
                print(f"ERROR: Duplicate icon '{icon_id}' (duplicate_of '{duplicate_of}') "
                      f"has files on disk for sizes {sorted(disk_sizes)} — "
                      f"remove files or duplicate_of flag", file=sys.stderr)
                validation_errors += 1
            json_sizes = icon_data.get("sizes", [])
            if json_sizes:
                print(f"ERROR: Duplicate icon '{icon_id}' (duplicate_of '{duplicate_of}') "
                      f"has non-empty sizes {json_sizes} in JSON — should be []",
                      file=sys.stderr)
                validation_errors += 1
            if update_sizes:
                if icon_data.get("sizes") != []:
                    icon_data["sizes"] = []
                    json_modified = True
        else:
            # Non-duplicate: must have sizes
            json_sizes = set(icon_data.get("sizes", []))
            disk_sizes = set(resolved.get("paths", {}).keys())

            if not json_sizes:
                print(f"ERROR: Icon '{icon_id}' has no sizes",
                      file=sys.stderr)
                validation_errors += 1

            if update_sizes:
                new_sizes = sorted(disk_sizes)
                if icon_data.get("sizes") != new_sizes:
                    icon_data["sizes"] = new_sizes
                    json_modified = True
            elif json_sizes:
                # Cross-check: sizes vs disk files
                on_disk_not_json = disk_sizes - json_sizes
                in_json_not_disk = json_sizes - disk_sizes
                for s in sorted(on_disk_not_json):
                    print(f"ERROR: {icon_id} has size {s} on disk but not in JSON sizes",
                          file=sys.stderr)
                    validation_errors += 1
                for s in sorted(in_json_not_disk):
                    print(f"ERROR: {icon_id} has size {s} in JSON sizes but not on disk",
                          file=sys.stderr)
                    validation_errors += 1

    if update_sizes and json_modified:
        save_json_compact_arrays(icons_json, icons_data)
        print(f"Updated {icons_json} (removed source_sizes, rebuilt sizes from disk)")

    if validation_errors:
        print(f"{validation_errors} size validation error(s) for {theme_id}", file=sys.stderr)

    # Build output lines
    sources = f"{theme_id}/icons.json, {theme_id}/contexts.json, {theme_id}/index.theme"
    lines = [
        f"# Generated from {sources} - DO NOT EDIT MANUALLY",
        f"# Regenerate with: python tools/generate_icons_parsed_py.py {theme_id}",
        "from taskcoachlib.i18n import _",
        "",
    ]

    # Output contexts dict
    if contexts:
        lines.append("contexts = {")
        for ctx_id, ctx_info in sorted(contexts.items()):
            label = ctx_info.get("context_label", ctx_id.title())
            escaped_label = label.replace('"', '\\"')
            lines.append(f'    "{ctx_id}": _("{escaped_label}"),')
        lines.append("}")
        lines.append("")

    # Output icons dict
    lines.append("icons = {")

    for icon_id, entry in sorted(icons_output.items()):
        lines.append(f'    "{icon_id}": {{')

        if "label" in entry:
            escaped = entry["label"].replace('"', '\\"')
            lines.append(f'        "label": _("{escaped}"),')

        if "hints" in entry and entry["hints"]:
            hints_str = ", ".join(f'_("{h}")' for h in entry["hints"])
            lines.append(f'        "hints": [{hints_str}],')

        if "context" in entry:
            lines.append(f'        "context": "{entry["context"]}",')

        if "context_label" in entry:
            escaped = entry["context_label"].replace('"', '\\"')
            lines.append(f'        "context_label": _("{escaped}"),')

        if "file" in entry:
            lines.append(f'        "file": "{entry["file"]}",')

        if "duplicate_of" in entry:
            lines.append(f'        "duplicate_of": "{entry["duplicate_of"]}",')

        paths = entry.get("paths", {})
        if paths:
            lines.append('        "paths": {')
            for size, path in sorted(paths.items()):
                lines.append(f'            {size}: "{path}",')
            lines.append("        },")
        else:
            lines.append('        "paths": {},')

        lines.append("    },")

    lines.append("}")
    lines.append("")  # Trailing newline

    with open(out_path, "w") as f:
        f.write("\n".join(lines))

    icon_count = len(icons_output)
    path_count = sum(len(e.get("paths", {})) for e in icons_output.values())
    print(f"Generated {out_path} ({icon_count} icons, {path_count} paths)")
    return True


def get_themes_with_icons() -> list[str]:
    """Return list of active themes from ICON_THEME_CATALOG.json."""
    catalog_path = ICONS_DIR / "ICON_THEME_CATALOG.json"
    if not catalog_path.exists():
        print(f"ERROR: {catalog_path} not found", file=sys.stderr)
        return []

    with open(catalog_path, "r") as f:
        catalog = json.load(f)

    themes = []
    for theme_id, theme_info in sorted(catalog.items()):
        if not theme_info.get("active", False):
            continue

        icons_path = ICONS_DIR / theme_id / "icons.json"
        if not icons_path.exists():
            print(f"WARNING: Active theme '{theme_id}' missing {theme_id}/icons.json, skipping")
            continue

        themes.append(theme_id)

    return themes


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    update_sizes = "--update-sizes" in sys.argv[1:]

    if args:
        theme = args[0]
        generate_icons_parsed_py(theme, update_sizes=update_sizes)
    else:
        themes = get_themes_with_icons()
        if not themes:
            print("No themes with icons found")
            return

        print(f"Regenerating {len(themes)} theme(s): {', '.join(themes)}")
        for theme in themes:
            generate_icons_parsed_py(theme, update_sizes=update_sizes)


if __name__ == "__main__":
    main()
