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
- [Icon Contexts](#icon-contexts)
- [Icon Sources](#icon-sources)
- [Mixing Icons from Different Sources](#mixing-icons-from-different-sources)
- [Icon Set Comparison](#icon-set-comparison)
- [Notes on Icon Sets](#notes-on-icon-sets)
- [Adding New Icons](#adding-new-icons)
- [Migration from Legacy Icons](#migration-from-legacy-icons)
- [Recently Added Icons](#recently-added-icons)
- [Icon Grid Browser and Duplicates (Dev Tools)](#icon-grid-browser-and-duplicates-dev-tools)
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
   "iconname": {"source": "papirus", "context": "apps", "file": "source.svg", "source_sizes": "16,22,24,32,48,64"}
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
   - Use icon-distillery (`~/Downloads/icon-distillery/`) for discovery and cataloging.
   - If the icon has `"hints"` in the distillery catalog, review and merge relevant hints
     into the artprovider.py hints above.
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
- `ICON_THEME_CATALOG.json` - Theme metadata (URL, license, active)
- `ICON_MAPPING.json` - Maps icon names to theme + original filename

**Metadata** (names, hints) is in `taskcoachlib/gui/artprovider.py:chooseableItems`.

## Two-System Architecture

There are **two separate systems** for managing icons:

### 1. Prep Tools (Discovery/Cataloging)

**Purpose:** Discover and catalog icons in EXTERNAL theme packs for selection.

**Tools:** icon-distillery (`../icon-distillery/`)
- Discovery, cataloging, browsing, hints, duplicates — all in icon-distillery
- Import catalogs: `{distillery}/{theme}/icons.json` (read by `tools/icon_import_theme.py`)

**Key format:** `{context}/{filename}` (e.g., `emotes/face-angel.png`)

### 2. App Internal Library (Imported Icons)

**Purpose:** Icons actually USED by TaskCoach.

**Location:** `taskcoachlib/gui/icons/`

**Files:**
- `oxygen/icons.json`, `nuvola/icons.json` - Registry of IMPORTED icons with metadata (generator input)
- `oxygen/icons_parsed.py`, `nuvola/icons_parsed.py` - Generated Python modules with pre-computed paths (runtime)
- `oxygen/contexts.json`, `oxygen/index.theme` - Context definitions and XDG metadata (generator input)
- `oxygen/16x16/emotes/face-angel.png` - Actual icon files

**Key format:** `{theme}_{context}_{filename}` (e.g., `oxygen_emotes_face-angel`)

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

### Themes Without Contexts vs Legacy Exception

**Themes without contexts** still follow XDG icon theme structure:
- Icons without a context match `index.theme` entries that have no `Context` field
- These are indexed as `(size, None)` in the XDG lookup cache
- Key format: `{theme}_{stem}` (e.g., `taskcoach_custom`)
- No path pattern fallback — all resolution goes through `index.theme`

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
- A theme without contexts (taskcoach) → normal XDG structure, just no context
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
2. For each icon found, scanner generates key: `{theme}_{context}_{stem}`
3. Scanner also extracts context and file as separate fields
4. Catalog load returns entries with the same key format
5. Merge finds matches because keys are identical
6. Use context and file from info dict directly - no fallback parsing

**Why this is robust:**
- Single source of truth for key format (the scanner)
- Fail-fast on missing data - errors surface immediately, not masked by fallbacks
- No silent failures - merge works correctly or fails visibly
- Sequential decomposition in path parsing reduces complexity

**Sequential decomposition in path parsing:**

When parsing disk paths to extract size, context, and filename, we decompose
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
2. Entry added to app JSON with `name`, `hints`, `context`, `file`, `source_sizes`
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
├── ICON_THEME_CATALOG.json   # Theme metadata (active, license, URL)
├── ICON_MAPPING.json         # Icon provenance (legacy, keep during transition)
│
├── # Legacy icons (flat, coexist during migration)
├── person_icon16x16.png      # Legacy: keep _icon suffix
└── person_icon22x22.png
```

### Target Layout (Per-Theme Structure)

The target structure uses per-theme subdirectories with JSON files, contexts, and index.theme:
```
taskcoachlib/gui/icons/
├── ICON_THEME_CATALOG.json   # Theme metadata (active, license, URL)
├── ICON_MAPPING.json          # Icon provenance (legacy, keep during transition)
│
├── nuvola/
│   ├── icons.json              # Nuvola icons: hints, sizes, context (generator input)
│   ├── contexts.json           # Context definitions from upstream (generator input)
│   ├── index.theme             # XDG index.theme from upstream (generator input)
│   └── icons_parsed.py         # Generated: pre-computed paths, translations (runtime)
├── oxygen/
│   ├── icons.json
│   ├── contexts.json
│   ├── index.theme
│   └── icons_parsed.py
├── papirus/
│   ├── icons.json
│   ├── contexts.json
│   └── index.theme
├── papirus-dark/               # Empty placeholder for future variants
├── papirus-light/              # Empty placeholder for future variants
├── taskcoach/
│   └── icons.json              # No index.theme (flat structure, no contexts)
│
├── # Per-theme icon files in subdirs:
├── nuvola/16x16/actions/edit-copy.png
├── oxygen/16x16/emotes/face-angel.png
│
├── # Legacy (keep until fully migrated)
├── ICON_MAPPING.json
├── person_icon16x16.png
└── person_icon22x22.png
```

**Migration path:**
1. New icons go into theme-specific structure with per-theme JSON
2. Legacy icons remain in flat structure with ICON_MAPPING.json
3. Both coexist until all legacy icons are migrated
4. Remove ICON_MAPPING.json and flat files when migration complete

### ICON_THEME_CATALOG.json

Defines icon theme metadata (one entry per theme):
```json
{
  "nuvola": {
    "name": "Nuvola",
    "active": true,
    "url": "https://github.com/spartrekus/nuvola-icon-theme",
    "license": "LGPL-2.1"
  }
}
```

**Fields:**
- `active` - Whether the theme is loaded at runtime (true/false)
- `url` - Project homepage
- `license` - SPDX license identifier
- `note` - Additional notes (optional)

File paths are hardcoded by convention: `{theme}/icons.json`, `{theme}/contexts.json`, `{theme}/index.theme`.

### XDG Path Resolution

Icon paths are resolved using the XDG Icon Theme Specification via `index.theme` files.

**What is index.theme?**

Each `index.theme` comes from the upstream theme distribution (GitHub/KDE). It lists a `Directories=` line with every directory path, and a `[dirpath]` section per directory with `Size`, `Context`, `Type`.

The directory path in the section header IS the relative path from the theme root:
```ini
[16x16/actions]
Size=16
Context=Actions
Type=Fixed
```
Means: look for icons in `{theme_root}/16x16/actions/`.

**Lookup algorithm (used by the generator `generate_icons_parsed_py.py` at build time):**

```
For each icon in icons.json:
1. Get icon's context_id (e.g. "devices"), look up xdg_context via contexts.json ("Devices")
2. From index.theme, find all (size, xdg_context) → dir_path entries
3. For each size/dir candidate, check file existence on disk
4. Record paths = {size: "relative/path"} — only sizes where file exists
5. Write to icons_parsed.py
```

**At runtime** (`build_icon_path` in `icon_library.py`):
```
build_icon_path(theme="nuvola", icon_key="nuvola_devices_print_printer", size=16):
1. Import {theme}/icons_parsed.py (cached)
2. Look up icon_key → paths dict
3. Look up size → relative path "16x16/devices/print_printer.png"
4. Join with theme dir → absolute path
```
No JSON or index.theme parsing at runtime.

**Why this replaces path_pattern:**

The old `path_pattern` hack was a single hardcoded template that couldn't handle:
- Oxygen's `base/` source-tree directory references
- Oxygen's `applets/{size}` reversed layout
- Papirus's `symbolic/` variants
- Breeze's `{context}/{size}/{file}` reversed structure

The XDG lookup iterates actual directory entries from `index.theme` and checks file existence — no pattern assumptions needed.

**Important: `index.theme` comes from icon-distillery — do not modify it here.**

The `index.theme` files are copied from icon-distillery, which sources them from upstream theme distributions. If an icon exists on disk but is not listed in `index.theme` (e.g., `16x16/emblems/` exists but `index.theme` has no `16x16/emblems` entry), the XDG lookup will not find it and an error is logged. If corrections are needed, modify `index.theme` in icon-distillery and re-copy.

**Theme-specific notes:**

- **Oxygen `base/`**: upstream `index.theme` lists `base/16x16/actions` but `base/` does not exist as a physical directory. It's a KDE source tree build artifact. The XDG lookup skips non-existent dirs naturally.
- **Oxygen `applets/`**: reversed layout `applets/22x22`, `applets/32x32` — DO exist on disk.
- **Nuvola `filesystems/`**: listed in `index.theme` but not present in distilled icons — skipped.
- **Papirus `symbolic/`**: `16x16/symbolic/actions/` etc. — symbolic icon variants, may not be present in our imported set.

### Runtime Loading Architecture

The app only imports `icons_parsed.py` at runtime — no JSON or index.theme parsing.

**Data flow:**
```
BUILD TIME (generator)                  RUNTIME (app)
icons.json ──┐                          icons_parsed.py ── import ──→ icon_library.py
contexts.json ──→ generate_icons_parsed_py.py                              │
index.theme ─┘        │                                              artprovider.py
                       ↓                                                   │
               icons_parsed.py                                     wx.Image(path)
```

**Three icon states after loading:**
1. **LOADED** — icon is in the catalog and bitmap loaded successfully
2. **MISSING FROM CATALOG** — icon name in task/category XML but not in any theme's `icons_parsed.py`
3. **FAILED TO LOAD** — icon is in catalog but bitmap file is missing or corrupt

**Duplicate icon auto-resolution:**

When loading a task file, if an object references a duplicate icon (one with `duplicate_of`
in `icons_parsed.py`), the name is automatically replaced with the target icon. This means
on next save the corrected name is written to the XML. A log message is emitted for each
conversion: `[ICON] Resolving duplicate icon 'old_name' -> 'target_name'`.

**Startup flow:**
```
1. Module import     Import icons_parsed.py → all metadata + paths known
                     Build duplicate_map from all themes
2. gui.init()        Push ArtProvider
3. MainWindow()      createImageList() → load PNGs from pre-computed paths
                     Failed bitmaps → empty substitution + mark_icon_failed()
4. Task file load    XML parsed → __parse_icon() resolves:
                       a. Deprecated icon names (_deprecated_icons)
                       b. Duplicate icons (duplicate_of → target)
                     THEN: validate_icons() checks all objects:
                       - MISSING FROM CATALOG → log error with object path
                       - FAILED TO LOAD → log error with object path
```

### Per-Theme JSON Files (App Internal Library)

Each theme has a JSON file containing imported icons with metadata:

```json
// taskcoachlib/gui/icons/oxygen/icons.json
{
  "icons": {
    "oxygen_emotes_face-angel": {
      "name": "Face - Angel",
      "context": "emotes",
      "file": "face-angel.png",
      "sizes": [16],
      "hints": ["angel", "halo", "innocent", "good", "smiley", "face"]
    }
  }
}
```

**Fields:**
- `name` - Display name for UI (English, title case, "Context - Description" format)
- `context` - XDG context (actions, apps, emotes, etc.)
- `file` - Original filename with extension
- `sizes` - Array of sizes with files on disk (rebuilt by `generate_icons_parsed_py.py --update-sizes`)
- `hints` - Search keywords (English)

**Key format:** `{theme}_{context}_{filename-without-extension}`
- Example: `oxygen_emotes_face-angel`
- Underscores separate components; original filename preserved (dashes/underscores intact)

### contexts.json

Each theme with contexts has a `contexts.json` mapping context IDs to XDG context names and display labels:

```json
{
  "actions": {"xdg_context": "Actions", "context_label": "Actions"},
  "devices": {"xdg_context": "Devices", "context_label": "Devices"},
  "emotes": {"xdg_context": "Emotes", "context_label": "Emotes"}
}
```

**Fields:**
- `xdg_context` - Maps lowercase context_id to the capitalized XDG Context name used in `index.theme`
- `context_label` - Display label for the icon picker's Context column

**Source:** Copied from icon-distillery, which generates them from upstream `index.theme` files.

### Generated Python Modules

The app library JSON files and index.theme are inputs to a generator tool. The tool
produces per-theme `icons_parsed.py` modules that contain all icon metadata, translations,
and **pre-resolved file paths**. At runtime, the app only imports these `.py` files —
it never parses `.json` or `.theme` files.

```
icons.json + contexts.json + index.theme  →  icons_parsed.py (generated)
```

**Generated Python structure:**
```python
# Generated from nuvola/icons.json, nuvola/contexts.json, nuvola/index.theme
# Regenerate with: python tools/generate_icons_parsed_py.py nuvola
from taskcoachlib.i18n import _

contexts = {
    "actions": _("Actions"),
    "devices": _("Devices"),
    ...
}

icons = {
    "nuvola_devices_print_printer": {
        "label": _("Print Printer"),
        "hints": [_("printer"), _("print"), ...],
        "context": "devices",
        "context_label": _("Devices"),
        "file": "print_printer.png",
        "paths": {
            16: "16x16/devices/print_printer.png",
            22: "22x22/devices/print_printer.png",
        },
    },
    ...
}
```

**Key points:**
- `paths` is a dict of `{size_int: "relative_path"}` — relative from theme dir
- Only sizes where the file exists on disk are included
- Duplicate icons have empty `paths` and a `duplicate_of` field pointing to the primary
- At XML load time, any reference to a duplicate icon is auto-resolved to the target (and logged)
- `contexts` dict is kept for translation extraction
- Labels and hints are wrapped in `_()` for gettext extraction

**Generation tool:**
```bash
# Regenerate all active themes
python tools/generate_icons_parsed_py.py

# Regenerate a specific theme only
python tools/generate_icons_parsed_py.py nuvola
python tools/generate_icons_parsed_py.py oxygen

# Rebuild sizes from disk and save back to icons.json (also removes source_sizes)
python tools/generate_icons_parsed_py.py --update-sizes
python tools/generate_icons_parsed_py.py --update-sizes nuvola
```

The tool uses `icon_theme_processor.py` (unmodified copy from icon-distillery) to parse
theme data, then generates `taskcoachlib/gui/icons/{theme}/icons_parsed.py`.

**Sizes validation:** Every generation run validates that the `sizes` field in each icon's
JSON entry matches the sizes actually found on disk. Mismatches are reported as errors
(size on disk but not in JSON, or in JSON but not on disk). Use `--update-sizes` to
rebuild `sizes` from disk after importing new icons.

### ICON_MAPPING.json

Maps TaskCoach icon names to their source (provenance tracking):
```json
{
  "_naming": "NEW icons use clean names (no _icon suffix). LEGACY icons retain _icon suffix.",

  "led_blue_icon": {"source": "taskcoach", "file": "led_blue.png"},

  "homebank": {
    "source": "papirus",
    "context": "apps",
    "file": "homebank.svg",
    "duplicates": [
      {"source": "papirus", "context": "apps", "file": "fr.free.Homebank.svg"}
    ]
  },
  "bitcoin": {"source": "papirus", "context": "apps", "file": "bitcoin.svg", "source_sizes": "16,22,24,32,48,64"},
  "wallet_closed": {"source": "oxygen", "context": "status", "file": "wallet-closed.png", "source_sizes": "16,22,32,48"}
}
```

**Naming Convention:**
- **New icons** (no suffix): Use original name or descriptive name (e.g., `homebank`, `bitcoin`, `wallet_closed`)

**Fields:**
- `source` - Theme name (must exist in ICON_THEME_CATALOG.json)
- `context` - Subfolder in source (actions/apps/status)
- `file` - Original filename in source repo
- `source_sizes` - Sizes available in the SOURCE library (for provenance tracking, ICON_MAPPING.json only)
- `duplicates` - Equivalent files in source library (same icon, different names)

**Notes:**
- `source_sizes` is only in ICON_MAPPING.json (legacy provenance). Per-theme `icons.json` files use `sizes` instead (actual files on disk).
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

## Icon Contexts

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
   "homebank": {"source": "papirus", "context": "apps", "file": "homebank.svg", "source_sizes": "16,22,24,32,48,64"}
   ```

7. **Update ICON_THEME_CATALOG.json** (if new theme):
   ```json
   "papirus": {
     "name": "Papirus",
     "active": false,
     "url": "https://github.com/PapirusDevelopmentTeam/papirus-icon-theme",
     "license": "GPL-3.0"
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

## Icon Grid Browser and Duplicates (Dev Tools)

The icon grid browser and icon duplicates scripts have been moved to icon-distillery (`~/Downloads/icon-distillery/scripts/`).

See icon-distillery for:
- `icon_grid_browser.py` — Visual icon browser with search, filtering, hover previews
- `icon_duplicates.py` — Duplicate detection by content hash
- `icon_next_hints.py` — Hints workflow automation
- `icon_generate_labels.py` — Label generation

### Import Catalogs

Import catalogs live in icon-distillery, read by `tools/icon_import_theme.py`:

```
../icon-distillery/
├── nuvola/icons.json     # Nuvola theme catalog
├── oxygen/icons.json     # Oxygen theme catalog
├── papirus/icons.json    # Papirus theme catalog (future)
└── breeze/icons.json     # Breeze theme catalog (future)
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
| `context` | has | copy | copy |
| `file` | has | copy | copy |
| `sizes` | has (source sizes) | **NEW** (files on disk) | **NEW** (empty `[]`) |
| `hints` | has | copy | copy |
| `duplicates` | has (primary only) | copy | n/a |
| `duplicate_of` | has (dup only) | n/a | copy |
| `inherits` | **ADD** (after import) | n/a | n/a |

### Key Differences

- **`sizes`** (tools JSON): What sizes exist in the source theme
- **`sizes`** (app JSON): What sizes have files on disk (rebuilt by `generate_icons_parsed_py.py --update-sizes`; validated on every generation run)
- **`inherits`**: Added to tools JSON only, points to itself (the app icon key). App JSON never has `inherits`.

### Example: Primary Icon

**Tools JSON BEFORE:**
```json
"nuvola_devices_printer": {
  "context": "devices",
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
  "context": "devices",
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
  "context": "devices",
  "file": "printer.png",
  "sizes": [16],
  "hints": ["printer", "print", ...],
  "duplicates": ["nuvola_apps_kjobviewer", ...]
}
```

### Example: Duplicate Icon

**Tools JSON BEFORE:**
```json
"nuvola_mimetypes_file_locked": {
  "context": "mimetypes",
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
  "context": "mimetypes",
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
  "context": "mimetypes",
  "file": "file_locked.png",
  "sizes": [],
  "hints": ["file", "locked", ...],
  "duplicate_of": "nuvola_mimetypes_file_locked-[Converted]"
}
```

### Image File Copying

- **Primary icons**: Copy 16x16 PNG files to `taskcoachlib/gui/icons/{theme}/16x16/{context}/`
- **Duplicate icons**: No files copied (they reference the primary's image via `duplicate_of`)

## Icon Hints Worker Plan

Add `"hints"` arrays to all icons in the catalog JSON files so they're searchable in the icon grid browser.

### Workflow

Use icon-distillery's hints script:

```
1. Run: python3 ~/Downloads/icon-distillery/scripts/icon_next_hints.py
2. Follow the NEXT STEP - WORKER INSTRUCTIONS in the script output
3. Go back to 1 and execute the steps again
4. Do not stop until the script tells you all the work is done!
```

### Key Files
- **Import catalogs**: `../icon-distillery/{theme}/icons.json`

## See Also

- [ICON_PLURALIZE.md](ICON_PLURALIZE.md) - Plural/singular icon mapping
- [TASK_STATUS.md](TASK_STATUS.md) - Status icon system
