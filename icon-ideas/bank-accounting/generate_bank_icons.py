#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate HTML overview of bank/accounting icons from source libraries.

Analyzes:
- Available sizes in each library
- Color count in SVG/PNG files
- Whether icon already exists in TaskCoach (legacy or new format)
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict

# Paths (assumes taskcoach and icons are sibling directories in Downloads)
SCRIPT_DIR = Path(__file__).parent
TC_ICONS = SCRIPT_DIR.parent.parent / "taskcoachlib" / "gui" / "icons"
ICONS_DIR = SCRIPT_DIR.parent.parent.parent / "icons"  # ../../../icons (sibling to taskcoach)

PAPIRUS = ICONS_DIR / "papirus-icon-theme-master" / "Papirus"
BREEZE = ICONS_DIR / "breeze-icons-master" / "icons"
OXYGEN = ICONS_DIR / "oxygen-icons-master"

OUTPUT_FILE = SCRIPT_DIR / "index.html"

SIZES = [16, 22, 24, 32, 48, 64]


def count_svg_colors(filepath):
    """Count unique hex colors in SVG file."""
    try:
        content = filepath.read_text()
        colors = set(re.findall(r'#[0-9a-fA-F]{6}', content))
        return len(colors)
    except:
        return 0


def count_png_colors(filepath):
    """Estimate colors in PNG (requires PIL, returns -1 if unavailable)."""
    try:
        from PIL import Image
        img = Image.open(filepath)
        colors = img.getcolors(maxcolors=256)
        return len(colors) if colors else -1
    except:
        return -1


def load_icon_mapping():
    """Load ICON_MAPPING.json to check what's already imported.

    Returns reverse mapping: original_file -> taskcoach_name
    Also includes duplicates so we detect icons that are already covered.
    """
    mapping_file = TC_ICONS / "ICON_MAPPING.json"
    if mapping_file.exists():
        data = json.loads(mapping_file.read_text())
        # Build reverse mapping: original_file -> taskcoach_name
        reverse = {}
        for tc_name, info in data.items():
            if isinstance(info, dict):
                # Map the main file
                main_file = info.get('file', '')
                if main_file:
                    reverse[main_file] = tc_name

                # Also map duplicates (they're covered by the main icon)
                for dup in info.get('duplicates', []):
                    dup_file = dup.get('file', '')
                    if dup_file:
                        reverse[dup_file] = f"{tc_name} (duplicate)"
        return reverse
    return {}


def check_legacy_icons():
    """Get list of legacy icons (flat files with size suffix)."""
    icons = set()
    for f in TC_ICONS.glob("*_icon*.png"):
        match = re.match(r'(.+_icon)\d+x\d+\.png$', f.name)
        if match:
            icons.add(match.group(1))
    return icons


def check_new_icons():
    """Get list of new format icons."""
    icons = set()
    size_dir = TC_ICONS / "16x16"
    if size_dir.exists():
        for f in size_dir.glob("*.png"):
            icons.add(f.stem)
    return icons


def find_papirus_icons():
    """Find all Papirus financial/banking icons."""
    icons = []

    # Actions - include all financial/bank/currency/tax/budget
    actions_dir = PAPIRUS / "16x16" / "actions"
    if actions_dir.exists():
        for f in actions_dir.glob("*.svg"):
            name = f.stem
            if any(k in name for k in ['financial', 'bank', 'currency', 'tax', 'budget']):
                # Skip symbolic versions
                if '-symbolic' in name:
                    continue

                sizes = {}
                for size in SIZES:
                    path = PAPIRUS / f"{size}x{size}" / "actions" / f"{name}.svg"
                    if path.exists():
                        sizes[size] = str(path)

                colors = count_svg_colors(f)
                icons.append({
                    'library': 'papirus',
                    'category': 'actions',
                    'name': name,
                    'file': f"{name}.svg",
                    'sizes': sizes,
                    'colors': colors,
                })

    # Apps - include financial/money apps but skip version duplicates
    apps_dir = PAPIRUS / "16x16" / "apps"
    app_keywords = ['money', 'bank', 'wallet', 'finance', 'budget', 'calculator',
                    'safe', 'bitcoin', 'ethereum', 'litecoin', 'coin', 'ledger',
                    'accounting', 'cash', 'crypto', 'trezor', 'electrum', 'monero',
                    'skrooge', 'gnucash', 'kmymoney', 'homebank']

    # Skip patterns - non-finance matches
    skip_patterns = [
        'pcbcalculator',      # PCB design, not finance
        'kicad',              # PCB design
        'qcalcfilehash',      # File hash calc, not finance
        'distributor-logo',   # OS logos
        'passwordcalc',       # Password tool
        'e-juice-calc',       # Vaping calculator
        'nicotine',           # Not finance
        'opl3_bank',          # Audio bank editor, not finance
        'opn2_bank',          # Audio bank editor, not finance
    ]

    if apps_dir.exists():
        for f in apps_dir.glob("*.svg"):
            name = f.stem
            name_lower = name.lower()

            if '-symbolic' in name:
                continue

            # Skip versioned/non-finance patterns
            if any(skip in name_lower for skip in skip_patterns):
                continue

            # Match keywords
            if any(k in name_lower for k in app_keywords):
                sizes = {}
                for size in SIZES:
                    path = PAPIRUS / f"{size}x{size}" / "apps" / f"{name}.svg"
                    if path.exists():
                        sizes[size] = str(path)

                colors = count_svg_colors(f)
                icons.append({
                    'library': 'papirus',
                    'category': 'apps',
                    'name': name,
                    'file': f"{name}.svg",
                    'sizes': sizes,
                    'colors': colors,
                })

    return icons


def find_breeze_icons():
    """Find Breeze financial/banking icons."""
    icons = []

    actions_dir = BREEZE / "actions" / "16"
    if actions_dir.exists():
        for f in actions_dir.glob("*.svg"):
            name = f.stem
            if any(k in name for k in ['financial', 'bank', 'currency', 'budget']):
                if '-symbolic' in name:
                    continue

                sizes = {}
                for size in SIZES:
                    path = BREEZE / "actions" / str(size) / f"{name}.svg"
                    if path.exists():
                        sizes[size] = str(path)

                colors = count_svg_colors(f)
                icons.append({
                    'library': 'breeze',
                    'category': 'actions',
                    'name': name,
                    'file': f"{name}.svg",
                    'sizes': sizes,
                    'colors': colors,
                })

    return icons


def find_oxygen_icons():
    """Find Oxygen financial/banking icons."""
    icons = []

    keywords = ['bank', 'wallet', 'calculator', 'money']

    for cat in ['actions', 'apps', 'status']:
        cat_dir = OXYGEN / "16x16" / cat
        if cat_dir.exists():
            for f in cat_dir.glob("*.png"):
                name = f.stem
                if any(k in name for k in keywords):
                    sizes = {}
                    for size in SIZES:
                        path = OXYGEN / f"{size}x{size}" / cat / f"{name}.png"
                        if path.exists():
                            sizes[size] = str(path)

                    colors = count_png_colors(f)
                    icons.append({
                        'library': 'oxygen',
                        'category': cat,
                        'name': name,
                        'file': f"{name}.png",
                        'sizes': sizes,
                        'colors': colors,
                    })

    return icons


def generate_html(papirus, breeze, oxygen, mapping, legacy_icons, new_icons):
    """Generate the HTML file."""

    def get_status(icon, mapping, legacy_icons, new_icons):
        """Check if icon exists in TaskCoach.

        Returns: (status, tc_name, in_legacy)
        status: 'yes' (imported), 'dup' (duplicate of imported), 'no' (not in TC)
        """
        file_name = icon['file']

        # Check if in ICON_MAPPING (already imported or documented duplicate)
        tc_name = mapping.get(file_name, '')

        if tc_name:
            if '(duplicate)' in tc_name:
                # This is a documented duplicate
                status = 'dup'
                tc_name = tc_name.replace(' (duplicate)', '')
            else:
                # This is the imported icon
                status = 'yes'
        else:
            status = 'no'

        # Check legacy by similar name pattern
        name_parts = icon['name'].replace('-', '_').split('_')
        in_legacy = any(
            any(part in leg.lower() for part in name_parts if len(part) > 3)
            for leg in legacy_icons
        )

        return status, tc_name, in_legacy

    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bank/Accounting Icon Ideas - Analysis</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 20px;
            background: #f5f5f5;
            font-size: 13px;
        }
        h1, h2 { color: #333; }
        .controls {
            position: sticky;
            top: 0;
            background: #fff;
            padding: 10px 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            z-index: 100;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
        }
        .controls label { margin-right: 15px; cursor: pointer; }
        .search-box input {
            padding: 8px 12px;
            font-size: 14px;
            border: 2px solid #ddd;
            border-radius: 6px;
            width: 250px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: #fff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        th, td {
            border: 1px solid #e0e0e0;
            padding: 4px 6px;
            text-align: left;
            font-size: 12px;
        }
        th {
            background: #4a90d9;
            color: white;
            position: sticky;
            top: 55px;
        }
        th.size-col { text-align: center; width: 40px; }
        tr:nth-child(even) { background: #fafafa; }
        tr:hover { background: #e8f4ff; }
        tr.in-new { background: #e8f5e9; }
        tr.filtered { display: none; }
        tr.in-new:hover { background: #c8e6c9; }
        .icon-cell {
            text-align: center;
            background: #fff;
            padding: 2px;
            min-width: 24px;
        }
        .icon-cell.dark { background: #2d2d2d; }
        .icon-cell img {
            image-rendering: pixelated;
            image-rendering: crisp-edges;
            vertical-align: middle;
            max-width: 64px;
            max-height: 64px;
        }
        .icon-cell.missing { background: #f5f5f5; color: #ccc; font-size: 10px; }
        .colors { text-align: center; font-weight: bold; }
        .colors-1, .colors-2 { color: #666; }
        .colors-3, .colors-4 { color: #1565c0; }
        .colors-5 { color: #2e7d32; }
        .status-yes { color: #2e7d32; font-weight: bold; }
        .status-dup { color: #1565c0; font-weight: bold; }
        .status-no { color: #999; }
        .status-maybe { color: #f57c00; }
        .tc-name { font-family: monospace; font-size: 10px; color: #666; }
        .hint-tag {
            display: inline-block;
            background: #e3f2fd;
            color: #1565c0;
            padding: 1px 4px;
            border-radius: 8px;
            margin: 1px;
            font-size: 10px;
        }
        .section-header {
            background: #333;
            color: white;
            padding: 8px 12px;
            margin-top: 20px;
        }
        .note { font-size: 11px; color: #666; margin-bottom: 10px; }
        .legend {
            background: #fff;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
            font-size: 11px;
        }
        .legend span { margin-right: 20px; }
    </style>
</head>
<body>
    <h1>Bank/Accounting Icon Ideas - Analysis</h1>

    <div class="legend">
        <strong>Legend:</strong>
        <span style="background:#e8f5e9;padding:2px 6px;">Green row = Already in TaskCoach</span>
        <span><strong class="status-yes">Yes</strong> = imported</span>
        <span><strong class="status-dup">Dup</strong> = duplicate of imported</span>
        <span><strong class="status-maybe">Maybe</strong> = similar legacy exists</span>
        <span><strong>Colors</strong> = unique hex colors</span>
    </div>

    <div class="controls">
        <div class="search-box">
            <input type="text" id="search" placeholder="Search icons..." autofocus>
        </div>
        <label><input type="checkbox" id="darkBg"> Dark background</label>
        <label><input type="checkbox" id="hideExisting"> Hide already imported</label>
    </div>
'''

    def render_table(icons, library_name, license_info):
        rows = []
        for icon in icons:
            status, tc_name, in_legacy = get_status(icon, mapping, legacy_icons, new_icons)

            row_class = 'in-new' if status in ('yes', 'dup') else ''
            search_data = f"{icon['name']} {icon['category']} {tc_name}".lower()

            row = f'<tr class="{row_class}" data-search="{search_data}" data-imported="{str(status != "no").lower()}">\n'

            # Size columns
            for size in SIZES:
                if size in icon['sizes']:
                    path = icon['sizes'][size]
                    # Make path relative
                    rel_path = path.replace('/home/user/Downloads/icons/', '../../../icons/')
                    row += f'<td class="icon-cell"><img src="{rel_path}"></td>\n'
                else:
                    row += '<td class="icon-cell missing">-</td>\n'

            # Colors
            colors = icon['colors']
            color_class = f'colors-{min(colors, 5)}' if colors > 0 else ''
            row += f'<td class="colors {color_class}">{colors if colors >= 0 else "?"}</td>\n'

            # In New
            if status == 'yes':
                row += f'<td class="status-yes">Yes<br><span class="tc-name">{tc_name}</span></td>\n'
            elif status == 'dup':
                row += f'<td class="status-dup">Dup<br><span class="tc-name">{tc_name}</span></td>\n'
            else:
                row += '<td class="status-no">No</td>\n'

            # In Legacy
            if in_legacy:
                row += '<td class="status-maybe">Maybe</td>\n'
            else:
                row += '<td class="status-no">No</td>\n'

            # Original file
            row += f'<td>{icon["file"]}</td>\n'

            # Category
            row += f'<td>{icon["category"]}</td>\n'

            row += '</tr>\n'
            rows.append(row)

        table = f'''
    <h2 class="section-header">{library_name} ({license_info}) - {len(icons)} icons</h2>
    <table>
        <thead>
            <tr>
                <th class="size-col">16</th>
                <th class="size-col">22</th>
                <th class="size-col">24</th>
                <th class="size-col">32</th>
                <th class="size-col">48</th>
                <th class="size-col">64</th>
                <th>Colors</th>
                <th>In New</th>
                <th>In Legacy</th>
                <th>Original File</th>
                <th>Cat</th>
            </tr>
        </thead>
        <tbody>
{''.join(rows)}
        </tbody>
    </table>
'''
        return table

    html += render_table(papirus, 'Papirus', 'GPL-3.0')
    html += render_table(breeze, 'Breeze', 'LGPL-2.1')
    html += render_table(oxygen, 'Oxygen', 'LGPL-2.1')

    html += '''
    <script>
        const tables = document.querySelectorAll('table');
        const searchInput = document.getElementById('search');
        const darkBgCheckbox = document.getElementById('darkBg');
        const hideExistingCheckbox = document.getElementById('hideExisting');

        function updateVisibility() {
            requestAnimationFrame(() => {
                const searchTerms = searchInput.value.toLowerCase().split(/\s+/).filter(t => t);
                const hideExisting = hideExistingCheckbox.checked;

                tables.forEach(table => {
                    table.querySelectorAll('tbody tr').forEach(row => {
                        const searchText = row.dataset.search || '';
                        const isImported = row.dataset.imported === 'true';

                        const matchesSearch = searchTerms.length === 0 ||
                            searchTerms.every(term => searchText.includes(term));
                        const matchesFilter = !hideExisting || !isImported;

                        row.classList.toggle('filtered', !(matchesSearch && matchesFilter));
                    });
                });
            });
        }

        function updateDarkBg() {
            document.querySelectorAll('.icon-cell:not(.missing)').forEach(cell => {
                cell.classList.toggle('dark', darkBgCheckbox.checked);
            });
        }

        searchInput.addEventListener('input', updateVisibility);
        hideExistingCheckbox.addEventListener('change', updateVisibility);
        darkBgCheckbox.addEventListener('change', updateDarkBg);
    </script>
</body>
</html>
'''
    return html


def main():
    print("Scanning icon libraries...")

    # Load existing TaskCoach data
    mapping = load_icon_mapping()
    legacy_icons = check_legacy_icons()
    new_icons = check_new_icons()

    print(f"TaskCoach: {len(mapping)} mapped, {len(legacy_icons)} legacy, {len(new_icons)} new")

    # Find icons from each library
    papirus = find_papirus_icons()
    breeze = find_breeze_icons()
    oxygen = find_oxygen_icons()

    print(f"Found: Papirus={len(papirus)}, Breeze={len(breeze)}, Oxygen={len(oxygen)}")

    # Generate HTML
    html = generate_html(papirus, breeze, oxygen, mapping, legacy_icons, new_icons)

    OUTPUT_FILE.write_text(html)
    print(f"Generated: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
