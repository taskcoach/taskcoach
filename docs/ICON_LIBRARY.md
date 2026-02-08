# Icon Library

## Terminology

- **Named Icon**: An icon entry in a catalog JSON file or artprovider.py, identified by its key (e.g., `devices/print_printer.png`). A Named Icon has metadata (sizes, hints, inherits) and corresponds to one visual concept.
- **Icon Image**: A specific size rendering (PNG file) of a Named Icon. A single Named Icon typically has multiple Icon Images at different sizes (16x16, 22x22, 32x32, 48x48, 64x64, 128x128).

## Table of Contents

- [TODO](#todo)
- [IMPORTANT: Complete Import Cycle](#important-complete-import-cycle)
- [Current Architecture](#current-architecture)
- [Required Sizes](#required-sizes)
- [Directory Structure](#directory-structure)
- [Icon Format](#icon-format)
- [Icon Categories](#icon-categories)
- [Icon Sources](#icon-sources)
- [Mixing Icons from Different Sources](#mixing-icons-from-different-sources)
- [Icon Set Comparison](#icon-set-comparison)
- [Notes on Icon Sets](#notes-on-icon-sets)
- [Adding New Icons](#adding-new-icons)
- [Migration from Legacy Icons](#migration-from-legacy-icons)
- [Recently Added Icons](#recently-added-icons)
- [Icon Grid Browser (Dev Tool)](#icon-grid-browser-dev-tool)
- [Icon Hints Worker Plan](#icon-hints-plan)
- [See Also](#see-also)

## TODO

### 1. Monochrome Icon Support
- [ ] Add support for monochrome (symbolic) icons from Breeze, Adwaita
- [ ] Implement icon recoloring: monochrome icons can be tinted to match theme
- [ ] Add icon color options to the icon picker:
  - Primary color picker for monochrome icons
  - Preview of tinted icon before selection
- [ ] Document which icon sets have monochrome variants

**Note:** Currently only pre-colored icons are used. Breeze icons have colors (#232629 dark gray + accent colors like #da4453 red, #27ae60 green) - they are NOT monochrome. The `-symbolic` variants ARE monochrome. Only the `-symbolic` versions should be excluded until recoloring support is implemented.

### 2. Duplicate Icon Review
- [x] Document duplicates in ICON_MAPPING.json to prevent re-importing
- [ ] Audit new icons against existing legacy icons for visual duplicates

See `ICON_MAPPING.json` for documented duplicates (in the `duplicates` field of each icon entry).

### 3. Refactor Overlay Icon Hack
- [ ] Create proper pre-composed "symbolic" theme icons to replace the `+` overlay hack
- [ ] Current `ArtProvider.CreateBitmap()` parses `main+overlay` strings to compose icons at runtime
- [ ] This hack breaks when icon names contain `+` (e.g., `text-x-c++src` from C++ files)
- [ ] Used by: `ViewerHideTasks` toolbar buttons (`completedtasks+cross_red_icon`, etc.)
- [ ] Solution: Pre-compose at load time into "symbolic" theme, remove `+` parsing hack
- [ ] See `_CreateOverlayBitmap()` in `artprovider.py`

## IMPORTANT: Complete Import Cycle

**When adding a new icon, ALL FOUR steps are required:**

1. **Convert SVG → PNG** (minimum 16x16):
   ```bash
   inkscape source.svg -o icons/16x16/iconname.png -w 16 -h 16
   ```

2. **Add to ICON_MAPPING.json** (provenance):
   ```json
   "iconname": {"source": "papirus", "category": "apps", "file": "source.svg", "source_sizes": "16,22,24,32,48,64"}
   ```
   Note: `source_sizes` documents sizes available in the SOURCE library, not what we've imported.

3. **Add to artprovider.py** (searchable metadata):
   ```python
   "iconname": {
       "name": _("Icon Name"),
       "hints": [_("keyword1"), _("keyword2")],
   },
   ```

4. **Update per-pack catalog** (icon browser search):
   - If the icon has `"hints"` in its catalog file (`tools/icon_grid_browser_data/{source}.json`),
     review and merge relevant hints into the artprovider.py hints above.
   - Replace the hints entry with `"inherits"` pointing to the new TaskCoach icon ID:
     ```json
     "apps/source.svg": {"inherits": "iconname", "sizes": [16, 22, 24, 32, 48, 64]}
     ```
   - This is a one-way merge: hints flow from the catalog into artprovider.py,
     then the catalog switches to `inherits` so it tracks the app's canonical hints.
   - If no hints exist yet, just add the `"inherits"` field to the existing entry.

**ICON_MAPPING.json alone does NOT make an icon usable!** It only documents where the icon came from. The PNG file and artprovider.py entry are required for the icon to appear in the picker.

**View the actual icon at ALL available sizes** before writing hints - describe what you SEE, not just the filename. Small sizes (16x16) can look very different from large sizes (48x48, 128x128).

### Coherence Check

Run the coherence check after adding icons to verify all three components are in sync:

```bash
python taskcoachlib/gui/icons/check_icon_coherence.py
```

Reports orphan entries and missing files:
- PNG files without ICON_MAPPING.json entry
- PNG files without artprovider.py entry
- ICON_MAPPING.json entries without PNG files
- artprovider.py entries without PNG files
- Icons with fewer than 5 hints (minimum required for good searchability)

Exit code 0 = all coherent, exit code 1 = issues found.

**Minimum 5 hints required** for each icon in artprovider.py to ensure searchability.

---

## Current Architecture

The icon system supports **two formats** (hybrid mode):

1. **New format** (preferred): Size-based directories (no `_icon` suffix)
   ```
   icons/16x16/bank_account.png
   icons/22x22/bank_account.png
   ```

2. **Legacy format**: Flat files with size suffix
   ```
   icons/person_icon16x16.png
   icons/person_icon22x22.png
   ```

The `ArtProvider` checks new format first, falls back to legacy. Both coexist.

**Provenance tracking:**
- `ICON_THEME_CATALOG.json` - Theme metadata (URL, license, path_pattern, categories, sizes)
- `ICON_MAPPING.json` - Maps icon names to theme + original filename

**Metadata** (names, hints) is in `taskcoachlib/gui/artprovider.py:chooseableItems`.

## Two-System Architecture

There are **two separate systems** for managing icons:

### 1. Prep Tools (Discovery/Cataloging)

**Purpose:** Discover and catalog icons in EXTERNAL theme packs for selection.

**Location:** `tools/icon_grid_browser_data/`

**Files:**
- `oxygen.json`, `papirus.json`, `nuvola.json` - Catalogs of ALL icons in each theme pack
- Contains: sizes, hints (for discovery/search)
- NOT part of the app - just tooling for icon selection

**Key format:** `{category}/{filename}` (e.g., `emotes/face-angel.png`)

### 2. App Internal Library (Imported Icons)

**Purpose:** Icons actually USED by TaskCoach.

**Location:** `taskcoachlib/gui/icons/`

**Files:**
- `oxygen.json`, `papirus.json` - Registry of IMPORTED icons with metadata
- `oxygen_i18n.py`, `papirus_i18n.py` - Generated translation files
- `oxygen/16x16/emotes/face-angel.png` - Actual icon files

**Key format:** `{theme}_{category}_{filename}` (e.g., `oxygen_emotes_face-angel`)

### Theme Identifiers

Every icon belongs to a theme. The theme identifier is required for all icon
operations to ensure consistent key generation.

| Theme | Description |
|-------|-------------|
| `oxygen` | Oxygen icons from KDE |
| `papirus` | Papirus icons |
| `breeze` | Breeze icons from KDE |
| `nuvola` | Nuvola icons |
| `taskcoach` | New custom TaskCoach icons following XDG structure |
| `legacy` | Old internal icons using flat format (exception, see below) |

Note: The codebase previously used "source" and "pack" inconsistently. All new
code should use "theme" for consistency. ICON_MAPPING.json still uses "source"
for backward compatibility but will eventually migrate to "theme".

### Themes Without Categories vs Legacy Exception

**Themes without categories** still follow XDG icon theme structure:
- `taskcoach`: path pattern `{size}x{size}/{file}` (e.g., `16x16/custom.png`)
- Category is simply omitted from the path
- Key format: `{theme}_{stem}` (e.g., `taskcoach_custom`)
- These are normal XDG-compliant icons

**Legacy theme is a special exception:**
- Mixed formats coexist (historical reasons):
  1. Flat files with size in filename: `add16x16.png`, `edit22x22.png`
  2. Some icons in sized directories: `16x16/something.png`
- Key format: `legacy_{stem}` (e.g., `legacy_add`)

**Handling the legacy exception:**
- Legacy icons require hardcoded handling for both formats
- Flat files: parse size from filename, reconstruct clean filename
  - Example: `add16x16.png` → size=16, file=`add.png`
- Sized directories: parse normally like XDG themes
  - Example: `16x16/icon.png` → size=16, file=`icon.png`
- This exception handling will remain until all legacy icons are migrated to taskcoach theme

**Do not confuse:**
- A theme without categories (taskcoach) → normal XDG structure, just no category
- The legacy theme → flat files with size in filename, requires special parsing

### Key Generation Strategy

When scanning icon directories, keys must be generated consistently so that disk
scans match catalog entries. Inconsistent keys cause silent merge failures where
discovered icons are treated as new and existing entries are logged as missing.

**Strategy:** Generate consistent keys at scan time using the theme. The scanner
receives the theme and generates keys in the correct format immediately, rather
than trying to translate between formats later.

**Data flow:**
1. Disk scanner receives theme identifier
2. For each icon found, scanner generates key: `{theme}_{category}_{stem}`
3. Scanner also extracts category and file as separate fields
4. Catalog load returns entries with the same key format
5. Merge finds matches because keys are identical
6. Use category and file from info dict directly - no fallback parsing

**Why this is robust:**
- Single source of truth for key format (the scanner)
- Fail-fast on missing data - errors surface immediately, not masked by fallbacks
- No silent failures - merge works correctly or fails visibly
- Sequential decomposition in path parsing reduces complexity

**Sequential decomposition in path parsing:**

When parsing disk paths to extract size, category, and filename, we decompose
sequentially starting with the simplest parts. First get the relative path from
the base directory. Then try pattern matching in order of commonality. Once a
pattern matches, extract all components and build the key.

This approach reduces search complexity because each step narrows the possibilities.
If one pattern does not match, try the next. The result is simpler logic that
handles theme variations (different directory structures, HiDPI variants) without
complex regex or fragile assumptions.

### Import Flow

```
External Theme Pack          Prep Tool                    App Internal Library
~/Downloads/icons/oxygen/    tools/.../oxygen.json   -->  taskcoachlib/gui/icons/oxygen/
(source files)               (hints for discovery)        (imported icons + JSON + .py)
```

**After import:**
1. Icon file copied to app library
2. Entry added to app JSON with `name`, `hints`, `category`, `file`, `source_sizes`
3. Prep tool JSON updated: `hints` replaced with `inherits: "icon_id"`
4. Translation .py file regenerated

## Required Sizes

| Size | Usage | Required For |
|------|-------|--------------|
| **16x16** | Tree lists, menus, dialogs, buttons | All icons |
| **22x22** | Medium toolbar | Toolbar icons |
| **32x32** | Large toolbar, template picker | Toolbar icons |
| 48x48 | Window icon bundle | App icon only |
| 64x64 | Window icon bundle (HiDPI) | App icon only |
| 128x128 | Window icon bundle (HiDPI) | App icon only |

**For icon picker (object icons):** Only 16x16 is needed.

## Directory Structure

### Current (Legacy) Layout

Icons stored flat with size suffix:
```
taskcoachlib/gui/icons/
├── person_icon16x16.png
├── person_icon22x22.png
├── person_icon32x32.png
└── ...
```

### New Layout (Hybrid Compatible)

Size-based directories with provenance tracking:
```
taskcoachlib/gui/icons/
├── 16x16/                    # All icons need 16x16
│   ├── homebank.png          # New icons: no _icon suffix
│   ├── bitcoin.png
│   └── ...
├── 22x22/                    # Toolbar icons
│   └── ...
├── 32x32/                    # Toolbar icons
│   └── ...
├── ICON_THEME_CATALOG.json   # Theme metadata (path patterns, categories, sizes)
├── ICON_MAPPING.json         # Icon provenance (legacy, keep during transition)
│
├── # Legacy icons (flat, coexist during migration)
├── person_icon16x16.png      # Legacy: keep _icon suffix
└── person_icon22x22.png
```

### Target Layout (Per-Theme Structure)

The target structure uses per-theme JSON files and mirrors each theme's path_pattern:
```
taskcoachlib/gui/icons/
├── ICON_THEME_CATALOG.json   # Theme metadata, references per-theme JSONs via icons_file
│
├── # Per-theme JSON files (icons imported from each theme)
├── papirus.json              # Papirus icons: hints, sizes, category
├── oxygen.json               # Oxygen icons
├── nuvola.json               # Nuvola icons
├── taskcoach.json            # Internal TaskCoach icons
│
├── # Directory structure follows theme's path_pattern:
├── # Papirus/Oxygen/Nuvola: {size}x{size}/{category}/{file}
├── 16x16/
│   ├── actions/
│   │   └── edit-copy.png
│   ├── apps/
│   │   └── homebank.png
│   └── status/
│       └── led_blue.png
│
├── # Breeze: {category}/{size}/{file}
├── actions/
│   ├── 16/
│   │   └── edit-copy.png
│   └── 22/
│       └── edit-copy.png
│
├── # TaskCoach (no categories): {size}x{size}/{file}
├── 16x16/
│   └── custom_icon.png
│
├── # Legacy (keep until fully migrated)
├── ICON_MAPPING.json         # Global provenance (deprecated)
├── person_icon16x16.png      # Flat legacy icons
└── person_icon22x22.png
```

**Migration path:**
1. New icons go into theme-specific structure with per-theme JSON
2. Legacy icons remain in flat structure with ICON_MAPPING.json
3. Both coexist until all legacy icons are migrated
4. Remove ICON_MAPPING.json and flat files when migration complete

### ICON_THEME_CATALOG.json

Defines icon theme metadata including path structure (one entry per theme):
```json
{
  "papirus": {
    "url": "https://github.com/PapirusDevelopmentTeam/papirus-icon-theme",
    "license": "GPL-3.0",
    "debian_package": "papirus-icon-theme",
    "debian_url": "https://tracker.debian.org/pkg/papirus-icon-theme",
    "path_pattern": "{theme}/{size}x{size}/{category}/{file}",
    "sizes": [16, 22, 24, 32, 48, 64],
    "categories": ["actions", "apps", "devices", "emblems", "mimetypes", "places", "status"]
  },
  "breeze": {
    "url": "https://invent.kde.org/frameworks/breeze-icons",
    "license": "LGPL-2.1",
    "debian_package": "breeze-icons",
    "debian_url": "https://tracker.debian.org/pkg/breeze-icons",
    "path_pattern": "{theme}/{category}/{size}/{file}",
    "sizes": [12, 16, 22, 32, 48, 64],
    "categories": ["actions", "apps", "devices", "emblems", "mimetypes", "places", "status"]
  }
}
```

**Fields:**
- `url` - Project homepage (GitHub, KDE Invent, etc.)
- `license` - SPDX license identifier
- `debian_package` - Debian package name (optional)
- `debian_url` - Debian package tracker URL (optional)
- `path_pattern` - Path template for icon files
- `sizes` - Available icon sizes as array
- `categories` - Valid category names for this theme
- `icons_file` - Per-theme JSON file for imported icons (e.g., `papirus.json`)
- `note` - Additional notes (optional)

**Path pattern tokens:**
- `{theme}` - Theme directory name (e.g., `Papirus`, `icons`)
- `{size}x{size}` - Dimension format (e.g., `16x16`, also matches `64x64@2x` HiDPI)
- `{size}` - Bare size number (e.g., `16`)
- `{category}` - Category name (e.g., `actions`, `apps`)
- `{file}` - Filename with extension

### Path Parsing Strategy

**Why sequential parsing instead of regex?**

Different icon themes have different directory structures:
- Oxygen: `{theme}/{size}x{size}/{category}/{file}` (size before category)
- Breeze: `{theme}/{category}/{size}/{file}` (category before size)
- Some themes have HiDPI variants: `64x64@2x` alongside `64x64`

A single regex pattern cannot handle all variations robustly. Sequential parsing
adapts to each theme's `path_pattern` and handles edge cases like:
- HiDPI directories (`64x64@2x` → extracts base size 64)
- Bare size numbers (`16` vs `16x16`)
- Variable token order per theme

**Logic:**

The `path_pattern` in ICON_THEME_CATALOG.json defines the exact folder sequence.
We split both the pattern and the path by `/`, then match positionally. This gives
us exactly where each component (size, category, file) should be.

**Validation:**

Categories and sizes are validated against the catalog's authoritative lists.
If a path contains an unexpected category or size, it's a FATAL ERROR - the catalog
must be updated rather than silently accepting unknown values.

**Sequential processing (pseudocode):**

```
1. pattern = config["path_pattern"]                    # e.g., "{theme}/{size}x{size}/{category}/{file}"
2. tokens = pattern.removePrefix("{theme}/").split("/") # → ["{size}x{size}", "{category}", "{file}"]
3. parts = path.relativeTo(search_root).split("/")      # → ["64x64@2x", "emotes", "face.png"]

4. if len(parts) != len(tokens):
       return None  # path doesn't match pattern

5. for i, (token, part) in enumerate(zip(tokens, parts)):
       if token == "{file}":
           result.file = part
       elif token == "{category}":
           if part not in config["categories"]:
               FATAL ERROR
           result.category = part
       elif "{size}" in token:
           size = extractLeadingDigits(part)  # "64x64@2x" → 64
           if size not in config["sizes"]:
               FATAL ERROR
           result.size = size

6. return result  # {file, category, size}
```

**Example:** Path `64x64@2x/emotes/face-uncertain.png`

| Position | Token | Part | Extraction |
|----------|-------|------|------------|
| 0 | `{size}x{size}` | `64x64@2x` | size = 64 (leading digits) |
| 1 | `{category}` | `emotes` | validated against categories |
| 2 | `{file}` | `face-uncertain.png` | file = `face-uncertain.png` |

### Per-Theme JSON Files (App Internal Library)

Each theme has a JSON file containing imported icons with metadata:

```json
// taskcoachlib/gui/icons/oxygen.json
{
  "icons": {
    "oxygen_emotes_face-angel": {
      "name": "Face - Angel",
      "category": "emotes",
      "file": "face-angel.png",
      "source_sizes": [16, 22, 32, 48, 64, 128],
      "hints": ["angel", "halo", "innocent", "good", "smiley", "face"]
    }
  }
}
```

**Fields:**
- `name` - Display name for UI (English, title case, "Category - Description" format)
- `category` - XDG category (actions, apps, emotes, etc.)
- `file` - Original filename with extension
- `source_sizes` - Array of sizes available in source theme
- `hints` - Search keywords (English)

**Key format:** `{theme}_{category}_{filename-without-extension}`
- Example: `oxygen_emotes_face-angel`
- Underscores separate components; original filename preserved (dashes/underscores intact)

### Translation Generation

The app library JSON files are the source of truth. A tool generates per-theme Python
files for translation:

```
oxygen.json  →  oxygen_i18n.py (generated)
papirus.json →  papirus_i18n.py (generated)
```

**Generated Python structure:**
```python
# Generated from oxygen.json - DO NOT EDIT MANUALLY
from taskcoachlib.i18n import _

icons = {
    "oxygen_emotes_face-angel": {
        "name": _("Face - Angel"),
        "hints": [_("angel"), _("halo"), _("innocent"), _("good"), _("smiley"), _("face")],
    },
}
```

This wraps `name` and `hints` in `_()` for gettext translation extraction.

**Generation tool:**
```bash
# Regenerate all themes with icons
python tools/generate_icon_i18n.py

# Regenerate a specific theme only
python tools/generate_icon_i18n.py oxygen
python tools/generate_icon_i18n.py nuvola
```

The tool reads `taskcoachlib/gui/icons/{theme}.json` and generates `taskcoachlib/gui/icons/{theme}_i18n.py`.

### ICON_MAPPING.json

Maps TaskCoach icon names to their source (provenance tracking):
```json
{
  "_naming": "NEW icons use clean names (no _icon suffix). LEGACY icons retain _icon suffix.",

  "led_blue_icon": {"source": "taskcoach", "file": "led_blue.png"},

  "homebank": {
    "source": "papirus",
    "category": "apps",
    "file": "homebank.svg",
    "duplicates": [
      {"source": "papirus", "category": "apps", "file": "fr.free.Homebank.svg"}
    ]
  },
  "bitcoin": {"source": "papirus", "category": "apps", "file": "bitcoin.svg", "source_sizes": "16,22,24,32,48,64"},
  "wallet_closed": {"source": "oxygen", "category": "status", "file": "wallet-closed.png", "source_sizes": "16,22,32,48"}
}
```

**Naming Convention:**
- **New icons** (no suffix): Use original name or descriptive name (e.g., `homebank`, `bitcoin`, `wallet_closed`)

**Fields:**
- `source` - Theme name (must exist in ICON_THEME_CATALOG.json)
- `category` - Subfolder in source (actions/apps/status)
- `file` - Original filename in source repo
- `source_sizes` - Sizes available in the SOURCE library (for provenance tracking)
- `duplicates` - Equivalent files in source library (same icon, different names)

**Notes:**
- `source_sizes` tracks what's available in the source library, NOT what we've imported
- Imported sizes are derived from filesystem (check 16x16/, 22x22/, etc. directories)
- Different sources can have same original filename (e.g., both have `bookmark.svg`)

**Duplicates:**
- The `duplicates` field lists equivalent source files that are NOT imported
- Purpose: Prevent accidentally importing the same icon under a different name later
- When checking if an icon exists, check BOTH the `file` field AND all `duplicates` entries
- Example: `homebank.svg` is imported; `fr.free.Homebank.svg` is documented as duplicate but not imported

## Icon Format

**Runtime format: PNG only**

| Format | Use |
|--------|-----|
| PNG | Shipped runtime icons (all sizes) |
| SVG | Source archive only (optional, for regenerating PNGs) |

wxPython has no native SVG support. All icons are pre-rendered PNGs.

**Optional SVG archive** (separate repo or gitignored):
```
icons/svg/                    # Source SVGs for regeneration
├── person_icon.svg
└── ...
```

## Icon Categories

### Objects (icon picker candidates)
User-selectable icons for tasks/categories. Need 16x16 only.
- Person, people, contacts
- Book, bookmark, document
- Folder variants
- Heart, star, flag
- Tools, home, work
- Animals, food, nature

### Actions
Toolbar/menu commands. Need 16x16, 22x22, 32x32.
- edit-copy, edit-paste, edit-cut
- document-new, document-save
- go-next, go-previous

### Status
State indicators. Need 16x16 only.
- LED icons (blue, green, red, yellow, etc.)
- Checkmarks, errors, warnings

## Icon Sources

### Downloading Icon Sets

Download and unzip icon sets to an **external directory** (not inside the repo):

```
~/Downloads/icons/
├── papirus-icon-theme-master/    # Primary source
├── oxygen-icons-master/          # Classic KDE
├── breeze-icons-master/          # Modern KDE
├── nuvola/                       # Legacy TaskCoach source
├── twemoji-master/               # Emoji icons
└── openmoji-master/              # More emoji
```

**Why external?** Files in repo (even gitignored) can be deleted by `git clean -fdx` or hard reset.

**Download URLs:**
- Papirus: https://github.com/PapirusDevelopmentTeam/papirus-icon-theme/archive/master.zip
- Oxygen: https://github.com/KDE/oxygen-icons/archive/master.zip
- Breeze: https://github.com/KDE/breeze-icons/archive/master.zip
- Twemoji: https://github.com/twitter/twemoji/archive/master.zip
- OpenMoji: https://github.com/hfg-gmuend/openmoji/archive/master.zip

**Optional/Low priority:**
- `pix.zip` - Moodle web GIFs (user, admin, grades icons - low quality)
- `gnome-themes-extras-0.9.0` - Adwaita/HighContrast GTK themes and icons, unmaintained since 2005

**Legacy/Unmaintained sets:**

| Set | Status | Notes |
|-----|--------|-------|
| Nuvola | Unmaintained | Final v1.0 by David Vignoni. Mirror: https://github.com/spartrekus/nuvola-icon-theme |
| gnome-themes-extra | Archived | Adwaita/HighContrast themes. https://gitlab.gnome.org/GNOME/gnome-themes-extra (v3.28, read-only) |

**Reference links:**
- [Nuvola - Wikipedia](https://en.wikipedia.org/wiki/Nuvola) - History and background
- [spartrekus/nuvola-icon-theme - GitHub](https://github.com/spartrekus/nuvola-icon-theme) - Community mirror (PNGs, 3,706 icons)
- [gnome-themes-extra - GitLab](https://gitlab.gnome.org/GNOME/gnome-themes-extra) - Adwaita/HighContrast themes (archived, v3.28)

### Currently Used
- **Nuvola/KDE** - Current TaskCoach icons (LGPL)

### Pre-Colored Icon Libraries

Only pre-colored (not monochrome) icon sets are listed. These have full-color icons ready to use.

| Set | Icons | Dark/Light | Sizes | License | URL |
|-----|-------|------------|-------|---------|-----|
| **Papirus** | 6,000+ | Yes (Papirus, Papirus-Dark, Papirus-Light) | 16,22,24,32,48,64 | GPL 3.0 | https://github.com/PapirusDevelopmentTeam/papirus-icon-theme |
| **Breeze** | 2,000+ | Yes (breeze, breeze-dark) | 16,22,32,48,64 | LGPL | https://github.com/KDE/breeze-icons |
| **Oxygen** | 2,000+ | No | 16,22,32,48,64,128 | LGPL | https://github.com/KDE/oxygen-icons |
| **Adwaita** | 2,000+ | Yes (built-in symbolic recoloring) | 16,22,24,32,48,64 | LGPL/CC BY-SA | https://gitlab.gnome.org/GNOME/adwaita-icon-theme |
| **Tango** | 1,000+ | No | 16,22,32,48 | Public Domain | http://tango.freedesktop.org/ |
| **Numix** | 3,000+ | Yes (Numix, Numix-Light) | 16,22,24,32,48,64 | GPL 3.0 | https://github.com/numixproject/numix-icon-theme |
| **Elementary** | 1,500+ | No (designed for light) | 16,24,32,48,64,128 | GPL 3.0 | https://github.com/elementary/icons |
| **Mint-Y** | 2,000+ | Yes (Mint-Y, Mint-Y-Dark) | 16,22,24,32,48,64 | GPL 3.0 | https://github.com/linuxmint/mint-y-icons |
| **Yaru** | 1,500+ | Yes (Yaru, Yaru-dark) | 16,22,24,32,48 | CC BY-SA 4.0 | https://github.com/ubuntu/yaru |

### Pre-Colored Emoji Libraries

| Set | Icons | Dark/Light | License | URL |
|-----|-------|------------|---------|-----|
| **Twemoji** | 3,600+ | No (universal) | MIT | https://github.com/twitter/twemoji |
| **OpenMoji** | 4,000+ | No (universal) | CC BY-SA 4.0 | https://github.com/hfg-gmuend/openmoji |
| **Noto Color Emoji** | 3,600+ | No (universal) | Apache 2.0 | https://github.com/googlefonts/noto-emoji |
| **Fluent Emoji** | 1,500+ | No (universal) | MIT | https://github.com/microsoft/fluentui-emoji |

### Icon Aggregators

| Site | Description | URL |
|------|-------------|-----|
| **Iconduck** | Free icon search, colored sets | https://iconduck.com |
| **SVG Repo** | 500,000+ SVGs, filter by color | https://svgrepo.com |
| **Icon-icons** | Searchable collection | https://icon-icons.com |

## Mixing Icons from Different Sources

### Naming Strategy

TaskCoach defines its own icon names—source filenames are only for provenance:

| Source File | TaskCoach Name | Why |
|-------------|----------------|-----|
| `papirus/homebank.svg` | `homebank` | Use original app name |
| `papirus/cryptomator.svg` | `cryptomator` | Use original app name |
| `oxygen/wallet-closed.png` | `wallet_closed` | Descriptive (not an app) |
| `twemoji/2764.svg` | `heart` | Human readable |

**Naming convention:**
- **New icons:** No `_icon` suffix (clean names)
- **Legacy icons:** Retain `_icon` suffix for backward compatibility

Different sources can have identical filenames. ICON_MAPPING.json tracks which source each TaskCoach icon came from.

### Freedesktop.org Naming Spec

Standard action/status icons have same names across compliant sets:

| Specification Compliance | Icon Sets |
|--------------------------|-----------|
| **Full compliance** | Adwaita, Breeze, Oxygen, Tango |
| **High compliance** | Papirus, Numix, Mint-Y, Yaru, Elementary |
| **Partial/Custom** | Nuvola (predates spec) |

Example: `document-save.svg` exists in Breeze, Adwaita, Papirus with same meaning.

### Visual Consistency Considerations

| Concern | Recommendation |
|---------|----------------|
| **Style mixing** | Pick one primary set (e.g., Papirus), supplement from similar sets |
| **Color palette** | KDE sets (Breeze, Oxygen, Papirus) share similar palettes |
| **Line weight** | Papirus uses thicker lines than Breeze at 16x16 |
| **Perspective** | Avoid mixing flat (Breeze) with 3D (Oxygen) icons |

**Recommended combinations:**
- Papirus + Breeze (both modern, similar weight)
- Oxygen + Nuvola (both classic 3D style)
- Adwaita + Elementary (both GNOME-derived)

### Size Compatibility

All major sets provide pixel-perfect versions for standard sizes:

| Size | Papirus | Breeze | Oxygen | Adwaita |
|------|---------|--------|--------|---------|
| 16x16 | ✓ | ✓ | ✓ | ✓ |
| 22x22 | ✓ | ✓ | ✓ | ✓ |
| 24x24 | ✓ | ✗ | ✗ | ✓ |
| 32x32 | ✓ | ✓ | ✓ | ✓ |
| 48x48 | ✓ | ✓ | ✓ | ✓ |
| 64x64 | ✓ | ✓ | ✓ | ✓ |

**Important:** Never scale between sizes—each size is hand-optimized. Use the SVG from the correct size folder.

## Icon Set Comparison

### Desktop Environment Icon Sets

| Set | Total Icons | Apps | Actions | Status | Places | Format | Active |
|-----|-------------|------|---------|--------|--------|--------|--------|
| **Papirus** | 6,000+ | 8,000+ | 400+ | 200+ | 100+ | SVG | ✓ Very |
| **Breeze** | 2,000+ | 300+ | 300+ | 100+ | 50+ | SVG | ✓ Yes |
| **Oxygen** | 2,000+ | 170+ | 250+ | 100+ | 50+ | SVG | Maint. |
| **Adwaita** | 2,000+ | 200+ | 300+ | 100+ | 50+ | SVG | ✓ Yes |
| **Tango** | 1,000+ | 100+ | 200+ | 50+ | 30+ | SVG/PNG | Legacy |
| **Numix** | 3,000+ | 2,000+ | 200+ | 100+ | 50+ | SVG | Slow |
| **Elementary** | 1,500+ | 200+ | 200+ | 100+ | 50+ | SVG | ✓ Yes |

### Theme Variants

| Set | Standard | Dark | Light | Other |
|-----|----------|------|-------|-------|
| **Papirus** | Papirus | Papirus-Dark | Papirus-Light | ePapirus (elementary) |
| **Breeze** | breeze | breeze-dark | — | — |
| **Oxygen** | oxygen | — | — | — |
| **Adwaita** | adwaita | symbolic (recolorable) | — | — |
| **Numix** | Numix | — | Numix-Light | Numix-Circle |
| **Mint-Y** | Mint-Y | Mint-Y-Dark | — | Color variants |
| **Yaru** | Yaru | Yaru-dark | Yaru-light | Color variants |

### Style Comparison

| Set | Visual Style | Best For |
|-----|--------------|----------|
| **Papirus** | Flat with subtle gradients, vibrant colors | Modern apps, good at all sizes |
| **Breeze** | Flat, minimalist, muted colors | Clean modern UI |
| **Oxygen** | 3D, glossy, detailed shading | Classic desktop look |
| **Adwaita** | Flat, symbolic, GNOME style | GTK apps |
| **Nuvola** | 3D, glossy (early 2000s style) | Legacy compatibility |

### License Comparison

| Set | License | Commercial Use | Modification | Attribution |
|-----|---------|----------------|--------------|-------------|
| **Papirus** | GPL 3.0 | ✓ | ✓ (share-alike) | Required |
| **Breeze** | LGPL | ✓ | ✓ | Required |
| **Oxygen** | LGPL | ✓ | ✓ | Required |
| **Adwaita** | LGPL/CC BY-SA | ✓ | ✓ | Required |
| **Tango** | Public Domain | ✓ | ✓ | Not required |
| **Twemoji** | MIT | ✓ | ✓ | Required |
| **OpenMoji** | CC BY-SA 4.0 | ✓ | ✓ (share-alike) | Required |

## Notes on Icon Sets

**Papirus** - Best choice for TaskCoach:
- Largest colored set with consistent style
- Has Light/Dark/Standard variants
- Active development
- Pixel-perfect for each size (16x16 looks crisp)

**Breeze** - Good alternative:
- Modern KDE Plasma style
- Clean dark/light variants
- Slightly more minimalist than Papirus

**Oxygen** - Legacy option:
- Classic KDE look (matches current Nuvola style)
- No dark variant
- Still maintained but less active

## Adding New Icons

**WARNING: All three steps (PNG + ICON_MAPPING.json + artprovider.py) are required!**
See "IMPORTANT: Complete Import Cycle" at the top of this document.

### From Pre-Colored Sets (e.g., Papirus)

1. **Choose a TaskCoach icon name** (source-agnostic):
   - Use original app name if recognizable: `homebank`, `bitcoin`, `cryptomator`
   - Use descriptive name otherwise: `wallet_closed`, `bank_building`
   - **New icons: NO `_icon` suffix** (clean names)
   - Legacy icons retain `_icon` suffix for backward compatibility

2. **Find icon in source repo** (size-specific folder):
   - `/Papirus/16x16/apps/` - Application icons
   - `/Papirus/16x16/places/` - Folder icons
   - `/Papirus/16x16/status/` - Status indicators
   - `/Papirus/16x16/emblems/` - Decorative emblems

3. **Follow symlinks** (Papirus uses aliases):
   ```bash
   ls -la icon.svg
   # If symlink, follow to real file
   ```

4. **Convert SVG to PNG** (use size-specific SVG, never scale):
   ```bash
   # For each required size, use that size's SVG
   rsvg-convert Papirus/16x16/apps/homebank.svg -o 16x16/homebank.png
   rsvg-convert Papirus/22x22/apps/homebank.svg -o 22x22/homebank.png
   rsvg-convert Papirus/32x32/apps/homebank.svg -o 32x32/homebank.png
   ```
   Alternative tools: `inkscape icon.svg -o icon.png` or `cairosvg`

5. **Add to size directories**:
   ```
   taskcoachlib/gui/icons/16x16/homebank.png
   taskcoachlib/gui/icons/22x22/homebank.png  # if toolbar icon
   taskcoachlib/gui/icons/32x32/homebank.png  # if toolbar icon
   ```

6. **Update ICON_MAPPING.json** (provenance):
   ```json
   "homebank": {"source": "papirus", "category": "apps", "file": "homebank.svg", "source_sizes": "16,22,24,32,48,64"}
   ```

7. **Update ICON_THEME_CATALOG.json** (if new theme):
   ```json
   "papirus": {
     "url": "https://github.com/PapirusDevelopmentTeam/papirus-icon-theme",
     "license": "GPL-3.0",
     "path_pattern": "{theme}/{size}x{size}/{category}/{file}",
     "sizes": [16, 22, 24, 32, 48, 64],
     "categories": ["actions", "apps", "devices", "emblems", "mimetypes", "places", "status"]
   }
   ```

8. **Add metadata to artprovider.py** (for icon picker):
   ```python
   "homebank": {
       "name": _("HomeBank"),
       "hints": [_("finance"), _("banking"), _("budget")],
   },
   ```

   **Important:** Always VIEW the actual icon at ALL available sizes before writing hints. Small sizes (16x16) can look very different from large sizes (48x48, 128x128). Don't rely solely on the filename—icons often depict something different from their name. For example:
   - An icon named `accessories-safe.svg` might show a vault, lockbox, or strongbox
   - An icon named `wallet-open.svg` might show bills, cards, or coins inside

   Describe what you SEE in the icon, not what the filename suggests.

### Handling Missing Sizes

If icon only has 16x16 but 22x22 or 32x32 is requested at runtime:
- Log warning: `"person_icon: missing 32x32, using scaled 16x16"`
- Return scaled version (quality degradation acceptable for rare cases)

Run validation during development to identify gaps:
```bash
# Find icons missing expected sizes
for icon in 16x16/*.png; do
  name=$(basename "$icon")
  [ ! -f "22x22/$name" ] && echo "Missing 22x22: $name"
  [ ! -f "32x32/$name" ] && echo "Missing 32x32: $name"
done
```

## Migration from Legacy Icons

When removing old icons, add mapping to `persistence/xml/reader.py`:

```python
_deprecated_icons = {
    "old_icon_name": "new_icon_name",
}
```

This auto-migrates saved task files using old icon names.

## Recently Added Icons

See `ICON_MAPPING.json` for the full list of imported icons with provenance.

## Icon Grid Browser (Dev Tool)

A standalone wxPython tool for visually browsing all TaskCoach icons and external icon theme packs in a grid layout with filtering, hover previews, and copy-pasteable import instructions.

### Running

```bash
python tools/icon_grid_browser.py
```

### Requirements

Beyond TaskCoach's standard dependencies (wxPython, etc.), this tool requires:

- **cairosvg** — for rendering SVG icons from Papirus/Breeze theme packs

```bash
# Debian/Ubuntu
sudo apt install python3-cairosvg

# pip
pip install cairosvg
```

The tool exits with install instructions if cairosvg is missing.

### Features

- **Scrollable icon grid** with auto-wrapping columns
- **Search** by name, ID, or hints (debounced)
- **Display size selector** (dynamically populated from discovered sizes)
- **Theme pack multi-select** — Nuvola, Papirus, Breeze, Oxygen (see [External Icon Theme Packs](#external-icon-theme-packs))
- **Filter checkboxes** — show/hide included icons, duplicates, dark background
- **Hover popup** showing all available sizes and metadata
- **Copy-pasteable import instructions** (varies by source type)
- **Copy-pasteable duplicate instructions** for documenting duplicates

### Border Color Key

| Color  | Meaning |
|--------|---------|
| Green  | Icon is in `artprovider.chooseableItems` (included in TaskCoach) |
| Grey   | Icon is a documented duplicate in `ICON_MAPPING.json` |
| Yellow | Legacy Nuvola icon (on disk via `iconmap.py`) |
| None   | Icon exists in external theme pack but not yet imported |

### Per-Pack Catalog Files

The tool maintains persistent catalog files in `tools/icon_grid_browser_data/`:

```
tools/icon_grid_browser_data/
├── papirus.json          # Papirus theme catalog
├── oxygen.json           # Oxygen theme catalog
├── nuvola.json           # Nuvola theme catalog
├── breeze.json           # Breeze theme catalog
└── internal.json         # Internal TaskCoach icons
```

Each catalog is a persistent record of all icons ever discovered in that theme pack.
Icons and sizes are **additive** (never removed from the catalog, even if the icon
disappears from disk — a log message is printed instead).

Catalog entries can also contain:
- `"hints"` — search keywords describing what the icon looks like (generated by the tool)
- `"inherits"` — references a TaskCoach icon ID to inherit hints from artprovider.py
- `"duplicates"` / `"duplicate_of"` — bidirectional duplicate relationships
- `"unstructured"` — `true` if the file was found outside the theme pack's standard
  directory structure (e.g., at repo root or in a non-category folder like `2/`).
  The icon key for unstructured entries is the relative path from `search_root`
  (e.g., `2/kalarm.png` instead of `actions/kalarm.png`). These are tracked for
  completeness but may not follow the theme's normal `{category}/{size}/{filename}` layout.

### Hints Workflow

Hints describe what an icon visually depicts and are used for search in the browser.

**Generating hints:** View the icon at ALL available sizes in the browser, then add
descriptive keywords to the catalog file as a `"hints"` array. Describe what you SEE,
not just the filename.

**On import (one-way merge):** When importing an icon into TaskCoach:
1. Review the catalog hints and merge relevant ones into artprovider.py `chooseableItems`
2. Replace the `"hints"` entry in the catalog with `"inherits": "icon_id"`
3. The catalog entry now tracks the app's canonical hints via the inherits reference

This is a one-time, one-way merge. After setting `inherits`, the catalog no longer
stores its own hints — it inherits them from the app.

### External Icon Theme Packs

The tool looks for external theme packs in the `../icons/` sibling directory (see [Downloading Icon Sets](#downloading-icon-sets) for setup).

Theme pack checkboxes are automatically disabled if the expected directory is not found on disk.

## Icon Duplicates Script

Finds duplicate icon files by content hash, grouped by icon name. Reports icons where ALL sizes are duplicates (full duplicates) first, then icons with partial duplicates.

### Running

```bash
python tools/icon_duplicates.py <theme> [path]
```

Arguments:
- `theme`: Theme name (nuvola, oxygen, papirus, breeze, taskcoach)
- `path`: Optional start path. If omitted, uses default from LOCAL_THEMES.

### Output

The script shows which icons are already marked in the catalog JSON:
- `[PRIMARY]` — Icon has `"duplicates"` array (canonical icon)
- `[duplicate_of: key]` — Icon has `"duplicate_of"` field
- `[DONE]` — All icons in the group are marked

For partial duplicates, additional flags indicate superset patterns:
- `[SUSPECTED SUPERSET]` — This icon has more sizes than matching `[FULL-DUP]` icons
- `[FULL-DUP]` — The matching icon is part of a full-duplicate group

### Superset Pattern

When a partial duplicate has MORE sizes than matching full-duplicate icons, it's flagged as `[SUSPECTED SUPERSET]`. This typically means:
- The partial icon is the complete/canonical version (e.g., 6 sizes)
- The full-dup icons are subsets with fewer sizes (e.g., only 48px)
- At overlapping sizes, the content is identical

**Worker action:** When you see `[SUSPECTED SUPERSET]`:
1. Review the icon visually to confirm it's the same image
2. If confirmed, make this icon PRIMARY with `"duplicates"` array
3. Update all matching `[FULL-DUP]` icons to have `"duplicate_of"` pointing to this icon
4. If an existing PRIMARY in the full-dup group, change it to `"duplicate_of"` as well

### Example

```bash
python tools/icon_duplicates.py nuvola > tools/nuvola_duplicates.txt
```

## Icon Import Script (Migrate JSON Entries)

Imports icons from the tools prep catalog to the app internal library. Creates directory structure, copies primary icon images, and transforms JSON entries.

### Running

```bash
python tools/icon_import_theme.py <theme> [--dry-run]
```

Arguments:
- `theme`: Theme name (nuvola, oxygen, papirus, breeze)
- `--dry-run`: Show what would be done without making changes

### Field Transformation Table

| Field | Tools JSON (Source) | App Primary | App Duplicate |
|-------|---------------------|-------------|---------------|
| `name` | has | copy | copy |
| `category` | has | copy | copy |
| `file` | has | copy | copy |
| `sizes` | has | rename → `source_sizes` | rename → `source_sizes` |
| `source_sizes` | n/a | **NEW** (from `sizes`) | **NEW** (from `sizes`) |
| `sizes` | has | **NEW** (files copied) | **NEW** (empty `[]`) |
| `hints` | has | copy | copy |
| `duplicates` | has (primary only) | copy | n/a |
| `duplicate_of` | has (dup only) | n/a | copy |
| `inherits` | **ADD** (after import) | n/a | n/a |

### Key Differences

- **`source_sizes`**: What sizes exist in the source theme (renamed from tools `sizes`)
- **`sizes`**: What sizes were actually imported to app (primaries have files, duplicates have `[]`)
- **`inherits`**: Added to tools JSON only, points to itself (the app icon key). App JSON never has `inherits`.

### Example: Primary Icon

**Tools JSON BEFORE:**
```json
"nuvola_devices_printer": {
  "category": "devices",
  "file": "printer.png",
  "sizes": [16, 22, 32, 48, 64, 128],
  "hints": ["printer", "print", ...],
  "name": "Printer",
  "duplicates": ["nuvola_apps_kjobviewer", ...]
}
```

**Tools JSON AFTER (adds `inherits`):**
```json
"nuvola_devices_printer": {
  "category": "devices",
  "file": "printer.png",
  "sizes": [16, 22, 32, 48, 64, 128],
  "hints": ["printer", "print", ...],
  "name": "Printer",
  "duplicates": ["nuvola_apps_kjobviewer", ...],
  "inherits": "nuvola_devices_printer"
}
```

**App JSON (new entry):**
```json
"nuvola_devices_printer": {
  "name": "Printer",
  "category": "devices",
  "file": "printer.png",
  "source_sizes": [16, 22, 32, 48, 64, 128],
  "sizes": [16],
  "hints": ["printer", "print", ...],
  "duplicates": ["nuvola_apps_kjobviewer", ...]
}
```

### Example: Duplicate Icon

**Tools JSON BEFORE:**
```json
"nuvola_mimetypes_file_locked": {
  "category": "mimetypes",
  "file": "file_locked.png",
  "sizes": [16, 32, 48, 64, 128],
  "hints": ["file", "locked", ...],
  "name": "File Locked",
  "duplicate_of": "nuvola_mimetypes_file_locked-[Converted]"
}
```

**Tools JSON AFTER (adds `inherits` pointing to itself):**
```json
"nuvola_mimetypes_file_locked": {
  "category": "mimetypes",
  "file": "file_locked.png",
  "sizes": [16, 32, 48, 64, 128],
  "hints": ["file", "locked", ...],
  "name": "File Locked",
  "duplicate_of": "nuvola_mimetypes_file_locked-[Converted]",
  "inherits": "nuvola_mimetypes_file_locked"
}
```

**App JSON (empty `sizes` since no files copied):**
```json
"nuvola_mimetypes_file_locked": {
  "name": "File Locked",
  "category": "mimetypes",
  "file": "file_locked.png",
  "source_sizes": [16, 32, 48, 64, 128],
  "sizes": [],
  "hints": ["file", "locked", ...],
  "duplicate_of": "nuvola_mimetypes_file_locked-[Converted]"
}
```

### Image File Copying

- **Primary icons**: Copy 16x16 PNG files to `taskcoachlib/gui/icons/{theme}/16x16/{category}/`
- **Duplicate icons**: No files copied (they reference the primary's image via `duplicate_of`)

## Icon Hints Worker Plan

Pre-Plan instructions: Copy this "Icon Hints Work Plan" verbatim from ./docs/ICON_LIBRARY.md to your plan file, except for this sentence.

Add `"hints"` arrays to all icons in the catalog JSON files so they're searchable in the icon grid browser.

### Catalogs to Process (in order)
1. `nuvola.json` (741 icons)
2. `oxygen.json` (2,053 icons)
3. `papirus.json` (17,516 icons)
4. `breeze.json` (4,238 icons)
5. `internal.json` (71 icons)

### Workflow

```
1. Run: python3 tools/icon_next_hints.py
2. Follow the NEXT STEP - WORKER INSTRUCTIONS in the script output
3. Go back to 1 and execute the steps again
4. Do not stop until the script tells you all the work is done! If the script gives you another file, that means your work is NOT complete!
```

### Anomaly Logs
- Location: `tools/icon_grid_browser_data/{theme}_anomalies.txt`
- Log any issues: conflicts resolved, icons added/skipped, anything unusual


### Key Files
- **Script**: `./tools/icon_next_hints.py`
- **Catalogs**: `./tools/icon_grid_browser_data/*.json`
- **Anomaly logs**: `./tools/icon_grid_browser_data/{theme}_anomalies.txt`

## See Also

- [ICON_PLURALIZE.md](ICON_PLURALIZE.md) - Plural/singular icon mapping
- [TASK_STATUS.md](TASK_STATUS.md) - Status icon system
