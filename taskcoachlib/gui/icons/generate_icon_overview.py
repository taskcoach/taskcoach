#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate an HTML overview of all TaskCoach icons.

Reads icon metadata from artprovider.py and scans the icons directory
to find all available sizes for each icon.

Usage:
    python generate_icon_overview.py

Output:
    icon_overview.html in the same directory
"""

import os
import re
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ICONS_DIR = SCRIPT_DIR
OUTPUT_FILE = SCRIPT_DIR / "icon_overview.html"

# Standard sizes to check
SIZES = [16, 22, 24, 32, 48, 64]


def parse_chooseable_items():
    """Parse chooseableItems from artprovider.py to get icon metadata."""
    artprovider_path = SCRIPT_DIR.parent / "artprovider.py"

    if not artprovider_path.exists():
        print(f"Warning: {artprovider_path} not found")
        return {}

    content = artprovider_path.read_text()

    # Find the chooseableItems dict
    match = re.search(r'chooseableItems\s*=\s*\{', content)
    if not match:
        print("Warning: chooseableItems not found in artprovider.py")
        return {}

    # Extract icon entries using regex
    # Pattern: "icon_name": { "name": _("Name"), "hints": [...] }
    icons = {}

    # Find all icon definitions
    pattern = r'"(\w+_icon)":\s*\{\s*"name":\s*_\("([^"]+)"\),\s*"hints":\s*\[([^\]]*)\]'

    for match in re.finditer(pattern, content):
        icon_id = match.group(1)
        name = match.group(2)
        hints_raw = match.group(3)

        # Parse hints
        hints = []
        for hint_match in re.finditer(r'_\("([^"]+)"\)', hints_raw):
            hints.append(hint_match.group(1))

        icons[icon_id] = {
            "name": name,
            "hints": hints
        }

    return icons


def find_icon_sizes(icon_id):
    """Find all available sizes for an icon (both legacy and new format)."""
    sizes_found = {}

    for size in SIZES:
        # Check new format: 16x16/icon_name.png
        new_path = ICONS_DIR / f"{size}x{size}" / f"{icon_id}.png"
        if new_path.exists():
            sizes_found[size] = str(new_path.relative_to(ICONS_DIR))
            continue

        # Check legacy format: icon_name16x16.png
        legacy_path = ICONS_DIR / f"{icon_id}{size}x{size}.png"
        if legacy_path.exists():
            sizes_found[size] = str(legacy_path.relative_to(ICONS_DIR))

    return sizes_found


def scan_all_icons():
    """Scan directory to find all icon IDs."""
    icon_ids = set()

    # Scan legacy format files
    for f in ICONS_DIR.glob("*_icon*.png"):
        # Extract icon_id from filename like "person_icon16x16.png"
        match = re.match(r'(.+_icon)\d+x\d+\.png$', f.name)
        if match:
            icon_ids.add(match.group(1))

    # Scan new format directories
    for size_dir in ICONS_DIR.iterdir():
        if size_dir.is_dir() and re.match(r'\d+x\d+$', size_dir.name):
            for f in size_dir.glob("*_icon.png"):
                icon_ids.add(f.stem)

    return sorted(icon_ids)


def load_icon_mapping():
    """Load ICON_MAPPING.json for provenance info."""
    mapping_path = ICONS_DIR / "ICON_MAPPING.json"
    if mapping_path.exists():
        return json.loads(mapping_path.read_text())
    return {}


def generate_html(icons_data):
    """Generate the HTML overview file."""

    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskCoach Icon Overview</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 { color: #333; margin-bottom: 5px; }
        .subtitle { color: #666; margin-bottom: 20px; }

        .controls {
            position: sticky;
            top: 0;
            background: #fff;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            z-index: 100;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
        }

        .search-box {
            flex: 1;
            min-width: 250px;
        }
        .search-box input {
            width: 100%;
            padding: 10px 15px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 6px;
            outline: none;
        }
        .search-box input:focus {
            border-color: #4a90d9;
        }

        .options label {
            margin-right: 15px;
            cursor: pointer;
        }

        .stats {
            color: #666;
            font-size: 14px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            background: #fff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }

        th, td {
            border: 1px solid #e0e0e0;
            padding: 8px 10px;
            text-align: left;
            font-size: 13px;
        }

        th {
            background: #4a90d9;
            color: white;
            position: sticky;
            top: 80px;
            font-weight: 500;
        }
        th.size-col {
            text-align: center;
            width: 50px;
        }

        tr:nth-child(even) { background: #fafafa; }
        tr:hover { background: #e8f4ff; }
        tr.hidden { display: none; }

        .icon-cell {
            text-align: center;
            background: #fff;
            padding: 4px;
            min-width: 30px;
        }
        .icon-cell.dark { background: #2d2d2d; }
        .icon-cell img {
            image-rendering: pixelated;
            image-rendering: crisp-edges;
            vertical-align: middle;
        }
        .icon-cell.missing {
            background: #f5f5f5;
            color: #ccc;
            font-size: 11px;
        }

        .icon-name { font-weight: 600; color: #333; }
        .icon-id { font-family: monospace; font-size: 11px; color: #666; }

        .hint-tag {
            display: inline-block;
            background: #e3f2fd;
            color: #1565c0;
            padding: 2px 6px;
            border-radius: 10px;
            margin: 2px;
            font-size: 11px;
        }

        .source-tag {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 500;
        }
        .source-taskcoach { background: #e8f5e9; color: #2e7d32; }
        .source-papirus { background: #fff3e0; color: #e65100; }
        .source-oxygen { background: #e3f2fd; color: #1565c0; }
        .source-nuvola { background: #fce4ec; color: #c2185b; }
        .source-breeze { background: #f3e5f5; color: #7b1fa2; }
        .source-unknown { background: #f5f5f5; color: #666; }

        .no-results {
            text-align: center;
            padding: 40px;
            color: #666;
            font-size: 18px;
        }
    </style>
</head>
<body>
    <h1>TaskCoach Icon Overview</h1>
    <p class="subtitle">All icons available in the icon picker</p>

    <div class="controls">
        <div class="search-box">
            <input type="text" id="search" placeholder="Search by name, ID, or hints..." autofocus>
        </div>
        <div class="options">
            <label><input type="checkbox" id="darkBg"> Dark background</label>
            <label><input type="checkbox" id="hideIncomplete"> Hide incomplete (missing sizes)</label>
        </div>
        <div class="stats">
            <span id="visibleCount">0</span> / <span id="totalCount">0</span> icons
        </div>
    </div>

    <table id="iconTable">
        <thead>
            <tr>
'''

    # Add size columns
    for size in SIZES:
        html += f'                <th class="size-col">{size}</th>\n'

    html += '''                <th>Name</th>
                <th>Icon ID</th>
                <th>Source</th>
                <th>Hints</th>
            </tr>
        </thead>
        <tbody>
'''

    # Add icon rows
    for icon in icons_data:
        icon_id = icon['id']
        name = icon.get('name', icon_id.replace('_icon', '').replace('_', ' ').title())
        hints = icon.get('hints', [])
        source = icon.get('source', 'unknown')
        sizes = icon.get('sizes', {})

        # Data attributes for searching
        search_text = f"{name} {icon_id} {' '.join(hints)}".lower()
        has_all_sizes = len(sizes) == len(SIZES)

        html += f'            <tr data-search="{search_text}" data-complete="{str(has_all_sizes).lower()}">\n'

        # Size columns
        for size in SIZES:
            if size in sizes:
                path = sizes[size]
                html += f'                <td class="icon-cell"><img src="{path}" alt="{size}x{size}"></td>\n'
            else:
                html += f'                <td class="icon-cell missing">-</td>\n'

        # Name
        html += f'                <td class="icon-name">{name}</td>\n'

        # Icon ID
        html += f'                <td class="icon-id">{icon_id}</td>\n'

        # Source
        source_class = f"source-{source}" if source else "source-unknown"
        html += f'                <td><span class="source-tag {source_class}">{source or "legacy"}</span></td>\n'

        # Hints
        hints_html = ''.join(f'<span class="hint-tag">{h}</span>' for h in hints)
        html += f'                <td>{hints_html}</td>\n'

        html += '            </tr>\n'

    html += '''        </tbody>
    </table>

    <div id="noResults" class="no-results" style="display: none;">
        No icons match your search.
    </div>

    <script>
        const table = document.getElementById('iconTable');
        const tbody = table.querySelector('tbody');
        const rows = tbody.querySelectorAll('tr');
        const searchInput = document.getElementById('search');
        const darkBgCheckbox = document.getElementById('darkBg');
        const hideIncompleteCheckbox = document.getElementById('hideIncomplete');
        const visibleCountSpan = document.getElementById('visibleCount');
        const totalCountSpan = document.getElementById('totalCount');
        const noResults = document.getElementById('noResults');

        totalCountSpan.textContent = rows.length;

        function updateVisibility() {
            const searchTerms = searchInput.value.toLowerCase().split(/\\s+/).filter(t => t);
            const hideIncomplete = hideIncompleteCheckbox.checked;
            let visibleCount = 0;

            rows.forEach(row => {
                const searchText = row.dataset.search;
                const isComplete = row.dataset.complete === 'true';

                // Check search terms (AND logic)
                const matchesSearch = searchTerms.length === 0 ||
                    searchTerms.every(term => searchText.includes(term));

                // Check completeness filter
                const matchesComplete = !hideIncomplete || isComplete;

                if (matchesSearch && matchesComplete) {
                    row.classList.remove('hidden');
                    visibleCount++;
                } else {
                    row.classList.add('hidden');
                }
            });

            visibleCountSpan.textContent = visibleCount;
            noResults.style.display = visibleCount === 0 ? 'block' : 'none';
            table.style.display = visibleCount === 0 ? 'none' : 'table';
        }

        function updateDarkBg() {
            document.querySelectorAll('.icon-cell:not(.missing)').forEach(cell => {
                cell.classList.toggle('dark', darkBgCheckbox.checked);
            });
        }

        searchInput.addEventListener('input', updateVisibility);
        hideIncompleteCheckbox.addEventListener('change', updateVisibility);
        darkBgCheckbox.addEventListener('change', updateDarkBg);

        // Initial update
        updateVisibility();
    </script>
</body>
</html>
'''

    return html


def main():
    print("Scanning icons directory...")

    # Get all icon IDs from filesystem
    all_icon_ids = scan_all_icons()
    print(f"Found {len(all_icon_ids)} icons in filesystem")

    # Get metadata from artprovider.py
    metadata = parse_chooseable_items()
    print(f"Found {len(metadata)} icons with metadata in artprovider.py")

    # Get provenance from ICON_MAPPING.json
    mapping = load_icon_mapping()
    print(f"Found {len(mapping)} icons in ICON_MAPPING.json")

    # Build icons data
    icons_data = []

    for icon_id in all_icon_ids:
        icon_info = {
            'id': icon_id,
            'sizes': find_icon_sizes(icon_id)
        }

        # Add metadata if available
        if icon_id in metadata:
            icon_info['name'] = metadata[icon_id]['name']
            icon_info['hints'] = metadata[icon_id]['hints']

        # Add source if available
        if icon_id in mapping:
            icon_info['source'] = mapping[icon_id].get('source', 'unknown')

        # Only include icons that have at least one size
        if icon_info['sizes']:
            icons_data.append(icon_info)

    print(f"Building overview for {len(icons_data)} icons...")

    # Generate HTML
    html = generate_html(icons_data)

    # Write output
    OUTPUT_FILE.write_text(html)
    print(f"Generated: {OUTPUT_FILE}")
    print(f"Open in browser: file://{OUTPUT_FILE.absolute()}")


if __name__ == '__main__':
    main()
