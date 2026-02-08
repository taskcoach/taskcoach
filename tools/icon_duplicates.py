#!/usr/bin/env python3
"""Find duplicate icon files by content hash, grouped by icon name.

Usage:
    python icon_duplicates.py <theme> [path]

Arguments:
    theme: Theme name (nuvola, oxygen, papirus, breeze, taskcoach)
    path:  Optional start path. If omitted, uses default from LOCAL_THEMES.

Reports icons where ALL sizes are duplicates first (full duplicates),
then icons with partial duplicates.

Workflow:
    Output to {theme}_duplicates.txt in the tools directory, then process:
    python icon_duplicates.py nuvola > tools/nuvola_duplicates.txt

Examples:
    python icon_duplicates.py nuvola
    python icon_duplicates.py oxygen ~/Downloads/icons/oxygen-icons-master
"""

import hashlib
import json
import os
import sys
from collections import defaultdict

# Add tools directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from icon_theme_processor import ThemeProcessor

# Catalog JSON paths for each theme
CATALOG_PATHS = {
    "nuvola": os.path.join(SCRIPT_DIR, "icon_grid_browser_data/nuvola.json"),
    "oxygen": os.path.join(SCRIPT_DIR, "icon_grid_browser_data/oxygen.json"),
    "papirus": os.path.join(SCRIPT_DIR, "icon_grid_browser_data/papirus.json"),
    "breeze": os.path.join(SCRIPT_DIR, "icon_grid_browser_data/breeze.json"),
    "taskcoach": os.path.join(SCRIPT_DIR, "icon_grid_browser_data/internal.json"),
}


def load_catalog_marked(theme):
    """Load catalog and return sets of icons marked as duplicates or duplicate_of."""
    catalog_path = CATALOG_PATHS.get(theme)
    if not catalog_path or not os.path.exists(catalog_path):
        return set(), set(), {}, {}

    with open(catalog_path) as f:
        data = json.load(f)

    icons = data.get("icons", {})
    has_duplicates = set()  # icons with "duplicates" array (primary icons)
    has_duplicate_of = set()  # icons with "duplicate_of" field
    refers_to_map = {}  # target_key -> list of referrer keys
    catalog_by_name = {}  # icon key -> icon info dict

    for key, info in icons.items():
        catalog_by_name[key] = info

        if "duplicates" in info:
            has_duplicates.add(key)
        if "duplicate_of" in info:
            has_duplicate_of.add(key)
            target = info["duplicate_of"]
            if target not in refers_to_map:
                refers_to_map[target] = []
            refers_to_map[target].append(key)

    return has_duplicates, has_duplicate_of, refers_to_map, catalog_by_name

# Default paths for each theme
LOCAL_THEMES = {
    "nuvola": os.path.expanduser("~/Downloads/icons/nuvola"),
    "oxygen": os.path.expanduser("~/Downloads/icons/oxygen-icons-master"),
    "papirus": os.path.expanduser("~/Downloads/icons/papirus-icon-theme-master"),
    "breeze": os.path.expanduser("~/Downloads/icons/breeze-icons-master"),
    "taskcoach": os.path.join(os.path.dirname(SCRIPT_DIR), "taskcoachlib/gui/icons"),
}


def hash_file(path):
    """Return MD5 hash of file contents."""
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def find_icons(start_path):
    """Find all PNG and SVG files under start_path."""
    icons = []
    for root, dirs, files in os.walk(start_path):
        # Skip symbolic icon directories
        if "-symbolic" in root:
            continue
        for name in files:
            if name.lower().endswith((".png", ".svg")):
                if "-symbolic" not in name:
                    icons.append(os.path.join(root, name))
    return icons


def main():
    if len(sys.argv) < 2:
        print("Usage: python icon_duplicates.py <theme> [path]", file=sys.stderr)
        print(f"Themes: {', '.join(LOCAL_THEMES.keys())}", file=sys.stderr)
        sys.exit(1)

    theme = sys.argv[1]
    if theme not in LOCAL_THEMES:
        print(f"Error: Unknown theme '{theme}'", file=sys.stderr)
        print(f"Available: {', '.join(LOCAL_THEMES.keys())}", file=sys.stderr)
        sys.exit(1)

    start_path = sys.argv[2] if len(sys.argv) > 2 else LOCAL_THEMES[theme]
    start_path = os.path.abspath(start_path)

    if not os.path.isdir(start_path):
        print(f"Error: {start_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    print(f"Theme: {theme}", file=sys.stderr)
    print(f"Scanning: {start_path}", file=sys.stderr)

    proc = ThemeProcessor(theme, start_path)

    # Load catalog to see which icons are already marked
    has_duplicates, has_duplicate_of, refers_to_map, catalog_by_name = load_catalog_marked(theme)

    def get_dup_of(icon_key):
        """Get duplicate_of value for icon, or None."""
        return catalog_by_name.get(icon_key, {}).get("duplicate_of")

    def print_dup_of(icon_key, indent="    "):
        """Print HAS duplicate_of line if icon has one. Returns the value."""
        dup_of = get_dup_of(icon_key)
        if dup_of:
            print(f"{indent}HAS duplicate_of: {dup_of}")
        return dup_of

    # Find all icons
    all_files = find_icons(start_path)
    print(f"Found {len(all_files)} icon files", file=sys.stderr)

    # Build icon inventory: icon_key -> {size: (path, hash)}
    icons = defaultdict(dict)

    for i, path in enumerate(all_files):
        if (i + 1) % 500 == 0:
            print(f"Processing: {i + 1}/{len(all_files)}", file=sys.stderr)

        parsed = proc.parse(path)
        if not parsed:
            continue

        size = parsed["size"]
        category = parsed["category"]
        filename = parsed["file"]

        # Use canonical key from theme processor
        icon_key = proc.generate_key(category, filename)

        try:
            h = hash_file(path)
            rel_path = os.path.relpath(path, start_path)
            icons[icon_key][size] = (rel_path, h)
        except Exception as e:
            print(f"Error hashing {path}: {e}", file=sys.stderr)

    print(f"Found {len(icons)} unique icons", file=sys.stderr)

    # Build hash signature for each icon (sorted tuple of (size, hash) pairs)
    # This lets us compare if two icons have identical content at all sizes
    icon_signatures = {}  # icon_name -> signature (frozenset of hashes)
    for icon_name, size_data in icons.items():
        # Signature is just the set of hashes (size-independent)
        hashes = frozenset(h for path, h in size_data.values())
        icon_signatures[icon_name] = hashes

    # Group icons by their hash sets to find full duplicates
    # Full duplicate = icons that have the exact same set of hashes
    sig_to_icons = defaultdict(list)
    for icon_name, sig in icon_signatures.items():
        sig_to_icons[sig].append(icon_name)

    # Find groups where all sizes match between icons
    full_dup_groups = []  # [(icon_names, sizes_info)]
    partial_dup_groups = []  # icons with some but not all sizes matching

    # Track which icons are already in full duplicate groups
    in_full_dup = set()

    # First pass: find icons with identical hash signatures
    for sig, icon_names in sig_to_icons.items():
        if len(icon_names) > 1:
            # These icons have the same set of hashes - full duplicates
            full_dup_groups.append(icon_names)
            in_full_dup.update(icon_names)

    # Second pass: find partial duplicates (same hash at individual sizes)
    # Build hash -> [(icon_name, size)] mapping
    hash_to_occurrences = defaultdict(list)
    for icon_name, size_data in icons.items():
        for size, (path, h) in size_data.items():
            hash_to_occurrences[h].append((icon_name, size, path))

    # Find hashes that appear in multiple icons (partial dups)
    partial_dups = defaultdict(list)  # hash -> [(icon_name, size, path)]
    for h, occurrences in hash_to_occurrences.items():
        # Get unique icon names for this hash
        unique_icons = set(icon_name for icon_name, size, path in occurrences)
        if len(unique_icons) > 1:
            # This hash appears in multiple different icons
            partial_dups[h] = occurrences

    # Output
    print(f"\nFull duplicates: {len(full_dup_groups)} groups", file=sys.stderr)
    print(f"Partial duplicate hashes: {len(partial_dups)}", file=sys.stderr)
    print()

    # Section 1: Full duplicates (all sizes identical)
    if full_dup_groups:
        print("=" * 70)
        print("FULL DUPLICATES (all sizes of these icons are identical)")
        print("=" * 70)
        print()

        # Sort by group size descending, then by first icon name
        full_dup_groups.sort(key=lambda g: (-len(g), g[0]))

        for group in full_dup_groups:
            # Get size count from first icon in group
            first_icon = group[0]
            size_count = len(icons[first_icon])

            # Find icons that refer to any icon in this group via duplicate_of
            referring_icons = []
            for icon_key in group:
                if icon_key in refers_to_map:
                    for ref_key in refers_to_map[icon_key]:
                        if ref_key not in group:  # Don't include icons already in group
                            referring_icons.append(ref_key)

            # Check if ALL icons in this group are marked (either PRIMARY or duplicate_of)
            all_marked = all(n in has_duplicates or n in has_duplicate_of for n in group)
            marked_str = " [DONE]" if all_marked else ""

            print(f"# {len(group)} identical icons ({size_count} size{'s' if size_count != 1 else ''} each):{marked_str}")
            for icon_name in sorted(group):
                size_data = icons[icon_name]
                sizes = sorted(size_data.keys())

                # Show marked status for each icon
                if icon_name in has_duplicates:
                    status = " [PRIMARY]"
                else:
                    status = ""

                print(f"  {icon_name}{status}")
                print_dup_of(icon_name, indent="      ")

                for size in sizes:
                    path, h = size_data[size]
                    print(f"    {size:4d}px  {h[:12]}  {path}")

            # Show referrers and targets summary
            if referring_icons:
                print(f"  [+{len(referring_icons)} referrers: {', '.join(sorted(referring_icons))}]")

            targets_outside = set()
            for icon_key in group:
                icon_info = catalog_by_name.get(icon_key, {})
                dup_of = icon_info.get("duplicate_of")
                if dup_of and dup_of not in group:
                    targets_outside.add(dup_of)
            if targets_outside:
                print(f"  [This group refers to: {', '.join(sorted(targets_outside))}]")

            print()

    # Section 2: Partial duplicates - grouped by icon name
    # Find icons that have at least one size with a duplicate (excluding full dups)
    icons_with_partial_dups = set()
    for h, occurrences in partial_dups.items():
        unique_icons = set(icon_name for icon_name, size, path in occurrences)
        # Only consider icons not already in full duplicate groups
        non_full_dup_icons = unique_icons - in_full_dup
        if len(non_full_dup_icons) >= 1 and len(unique_icons) > 1:
            icons_with_partial_dups.update(non_full_dup_icons)

    if icons_with_partial_dups:
        print("=" * 70)
        print("PARTIAL DUPLICATES (icons with some matching files)")
        print("=" * 70)
        print()

        # Build reverse lookup: hash -> list of (icon_name, size) for duplicates
        hash_to_other_icons = defaultdict(list)
        for h, occurrences in partial_dups.items():
            for icon_name, size, path in occurrences:
                hash_to_other_icons[h].append((icon_name, size))

        # Sort icons by number of duplicate matches, then by name
        def count_dup_matches(icon_name):
            count = 0
            for size, (path, h) in icons[icon_name].items():
                others = [n for n, s in hash_to_other_icons.get(h, []) if n != icon_name]
                count += len(others)
            return count

        sorted_icons = sorted(icons_with_partial_dups,
                              key=lambda n: (-count_dup_matches(n), n))

        for icon_name in sorted_icons:
            size_data = icons[icon_name]
            sizes = sorted(size_data.keys())

            # Collect ALL matching icons - track OTHER icon's matched sizes
            all_matches = {}  # other_name -> set of OTHER's sizes that matched
            for size, (path, h) in size_data.items():
                for other_name, other_size in hash_to_other_icons.get(h, []):
                    if other_name != icon_name:
                        if other_name not in all_matches:
                            all_matches[other_name] = set()
                        all_matches[other_name].add(other_size)  # Track THEIR size

            # Separate full-dup matches
            full_dup_matches = {k: v for k, v in all_matches.items() if k in in_full_dup}

            # Check if ALL sizes match a single other icon
            all_sizes_match_icon = None
            for other_name, match_sizes in all_matches.items():
                if match_sizes == set(sizes):
                    all_sizes_match_icon = other_name
                    break

            # Determine flags
            is_superset = False  # has more sizes AND matches all of other's sizes
            all_sizes_match = False  # ALL of our sizes match another icon
            all_sizes_match_icons = []  # icons where all our sizes match
            is_largest_match = False  # matches at largest common size
            has_multiple_full_dups = len(full_dup_matches) >= 2

            # Check superset and all-sizes-match against ALL matches
            for other_name, matched_other_sizes in all_matches.items():
                other_all_sizes = set(icons[other_name].keys())
                # Superset: we have more sizes AND matched ALL of their sizes
                if len(size_data) > len(other_all_sizes) and matched_other_sizes == other_all_sizes:
                    is_superset = True
                # All sizes match: ALL of our sizes match this other icon
                if len(matched_other_sizes) == len(size_data):
                    all_sizes_match = True
                    all_sizes_match_icons.append(other_name)

            for other_name, matched_other_sizes in full_dup_matches.items():
                # Check largest match: match at largest common size
                other_sizes = set(icons[other_name].keys())
                common_sizes = set(sizes) & other_sizes
                if common_sizes:
                    largest_common = max(common_sizes)
                    if largest_common in matched_other_sizes:
                        is_largest_match = True

            # Check if any matching full-dup icon has referrers (exclude self)
            referrer_info = []
            for other_key in full_dup_matches:
                if other_key in refers_to_map:
                    for ref_key in refers_to_map[other_key]:
                        if ref_key != icon_name:  # Don't include self
                            referrer_info.append(ref_key)
            has_referrers = len(referrer_info) > 0

            # Build status flags
            flags = []
            if all_sizes_match:
                flags.append("[ALL SIZES MATCH]")
            if is_superset:
                flags.append("[SUSPECTED SUPERSET]")
            if is_largest_match and not is_superset:
                flags.append("[REVIEW LARGEST]")
            if has_multiple_full_dups:
                flags.append("[REVIEW DUPLICATES]")
            if has_referrers:
                flags.append("[DUPLICATE_OF REFERRERS]")
            # Check catalog for duplicate_of and duplicates
            icon_info = catalog_by_name.get(icon_name, {})
            icon_dup_of = get_dup_of(icon_name)
            if icon_dup_of:
                flags.append("[DONE-DUPLICATE-OF]")

            # Check if this icon is [DONE] as PRIMARY
            # Requirements: has duplicates list, all listed have duplicate_of pointing here,
            # and all hash-matched icons are in the list
            icon_dups = icon_info.get("duplicates", [])
            is_done_primary = False
            if icon_dups:
                # Get all icons that match ALL our sizes (candidates for duplicates)
                expected_dups = set()
                for other_key, matched_sizes in all_matches.items():
                    # If other icon matches at ALL of our sizes, it should be a duplicate
                    if len(matched_sizes) == len(sizes):
                        expected_dups.add(other_key)

                # Check 1: All listed duplicates have duplicate_of pointing to us
                all_point_back = all(get_dup_of(d) == icon_name for d in icon_dups)

                # Check 2: All expected duplicates are in the list
                all_listed = expected_dups <= set(icon_dups)

                is_done_primary = all_point_back and all_listed
                if is_done_primary:
                    flags.append("[DONE-PRIMARY]")

            flag_str = " " + " ".join(flags) if flags else ""

            print(f"# {icon_name} ({len(sizes)} sizes){flag_str}")
            print_dup_of(icon_name)
            if icon_dups:
                print(f"    JSON DUPLICATES LIST:")
                for dup_key in icon_dups:
                    print(f"      {dup_key}")

            # Find largest PNG for this icon
            png_paths = [(s, p) for s, (p, h) in size_data.items() if p.endswith('.png')]
            if not png_paths:
                continue  # Skip if no PNG
            largest_png = max(png_paths, key=lambda x: x[0])[1]

            # Count duplicate files (sizes that have matches)
            dup_file_count = sum(1 for size, (path, h) in size_data.items()
                                 if any(n != icon_name for n, s in hash_to_other_icons.get(h, [])))

            # Print worker instructions if there are any duplicates
            if dup_file_count > 0:
                print("    WORKER INSTRUCTIONS:")
                print(f"      DUPLICATES: {dup_file_count} duplicate files found.")
                if all_sizes_match:
                    print("      ALL SIZES MATCH: Every size of this icon matches another icon.")
                    print("      This icon is likely duplicate_of that icon.")
                if is_superset:
                    print("      SUPERSET SUSPECTED: This icon has more sizes than matching icons.")
                    print("      This icon is likely the PRIMARY.")
                if is_largest_match and not is_superset:
                    print("      LARGEST MATCH: Largest common size is identical to [FULL-DUP] icons.")
                if has_multiple_full_dups:
                    print(f"      MULTIPLE DUPLICATES: Matches {len(full_dup_matches)} [FULL-DUP] icons.")
                if has_referrers:
                    print("      DUPLICATE_OF REFERRERS:")
                    for ref_key in sorted(referrer_info):
                        print(f"        {ref_key}")
                print("      ACTION - REQUIRED STEPS:")
                print("        1. List ALL sizes for EACH icon being compared")
                print("        2. View EVERY size for each icon - no exceptions")
                print("        3. DESCRIBE what you see (e.g., 'red heart with glossy highlight')")
                print("        4. WARNING: Different hashes may be visually identical!")
                print("        5. Compare side-by-side at each common size")
                print("        6. Only skip if images are VISUALLY DIFFERENT after viewing ALL")
                print("      Review these sections:")
                for match_key in sorted(all_matches.keys()):
                    print(f"        {match_key}")

            for size in sizes:
                path, h = size_data[size]
                # Find other icons with same hash at this size
                others = [(k, s) for k, s in hash_to_other_icons.get(h, [])
                          if k != icon_name]

                if others:
                    print(f"  {size:4d}px  {h[:12]}  {path}  (duplicate)")
                    for other_key, other_size in sorted(others):
                        # Get the other icon's file path
                        other_path = icons[other_key][other_size][0]
                        print(f"  {other_size:4d}px  {h[:12]}  {other_path}  (duplicate)")
                        print_dup_of(other_key, indent="          -> ")
                else:
                    print(f"  {size:4d}px  {h[:12]}  {path}  (unique)")

            print()


if __name__ == "__main__":
    main()
