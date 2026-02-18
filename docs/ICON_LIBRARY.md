# Icon Library

## Terminology

- **Named Icon**: An icon entry in the catalog, identified by its icon ID (e.g., `nuvola_devices_print_printer`). A Named Icon has metadata (sizes, hints, inherits) and corresponds to one visual concept.
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


### 2. System Tray Context Menu Icons — Review
- [ ] Right-click tray menu may not render icons on modern desktops (GTK3/Wayland/libappindicator)
- [ ] `MainWindowRestore` declares `bitmap="restore"` but icon may never be visible
- [ ] Audit all tray menu entries for dead icon references
- [ ] Decide: remove bitmap= from tray-only commands, or fix tray icon rendering

### 3. Refactor Overlay Icon Hack — DONE
- [x] Replaced `+` overlay hack with SyntheticIcon system
- [x] `synthetic_icon_generator.py` composes main icon + overlay at request time, caches per-size
- [x] `_CreateBitmap` routes `theme="synthetic"` entries to `synthetic_icon_generator.get_bitmap()`
- [x] 6 hide-task icons registered as `synthetic_hide_{status}` in `chooseableItems`
- [x] Live-check cache invalidation (compares current vs last base icon ID)
- [x] No pubsub, no `+` parsing, no `_CreateOverlayBitmap`
- See [ICON_DISPLAY.md](ICON_DISPLAY.md) § Synthetic Icons for architecture details

### 4. IMPORTANT: Stale Content Review
A lot of information in this document is stale because of the current transition
to icon-distillery sourced icons and the refactor to follow XDG specifications.
Sections referencing `ICON_MAPPING.json` or legacy-only workflows may no
longer reflect the current architecture. (`artprovider.py` has been removed;
icon metadata now lives in `_legacy_icon_defs()` inside `icon_library.py`.)

## IMPORTANT: Complete Import Cycle

### Icon-Distillery Icons

**TODO: Review — this is a subset of the [Migration Procedure](#migration-procedure).**

0. ***If Migration:*** Follow [Migration Procedure](#migration-procedure) instead
1. Copy/update `index.theme` from distillery (if new theme or new size directories)
2. Copy/update `contexts.json` from distillery (if new context)
3. Copy/merge icon entry into app's `{theme}/icons.json`
4. Copy required PNG files into `{theme}/...` (same paths as source)
5. Run `python tools/generate_icons_parsed_py.py <theme>` (review/correct errors)

### Legacy Icons

1. **Convert SVG → PNG** (minimum 16x16):
   ```bash
   inkscape source.svg -o icons/16x16/iconname.png -w 16 -h 16
   ```

2. **Add to ICON_MAPPING.json** (provenance) — **POSSIBLY DEPRECATED/ORPHANED - TO REVIEW**:
   ```json
   "iconname": {"source": "papirus", "context": "apps", "file": "source.svg", "source_sizes": "16,22,24,32,48,64"}
   ```
   Note: `source_sizes` documents sizes available in the SOURCE library, not what we've imported.

3. **Add to `_legacy_icon_defs()` in `icon_library.py`** (hardcoded metadata):
   Legacy icons have no `icons.json` or `icons_parsed.py` — their definitions
   are hardcoded in `_legacy_icon_defs()` in `icon_library.py`.

**ICON_MAPPING.json alone does NOT make an icon usable!** It only documents where the icon came from. The PNG file and a `_legacy_icon_defs()` entry in `icon_library.py` are required for the icon to appear in the picker.

**View the actual icon at ALL available sizes** before writing hints - describe what you SEE, not just the filename. Small sizes (16x16) can look very different from large sizes (48x48, 128x128).


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

The icon catalog checks new format first, falls back to legacy. Both coexist.

**Provenance tracking:**
- `ICON_THEME_CATALOG.json` - Theme metadata (URL, license, active)
- `ICON_MAPPING.json` - Maps icon names to theme + original filename

**Metadata** (names, hints) is in `_legacy_icon_defs()` inside `taskcoachlib/gui/icons/icon_library.py`.

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
build_icon_path(theme="nuvola", icon_id="nuvola_devices_print_printer", size=16):
1. Import {theme}/icons_parsed.py (cached)
2. Look up icon_id → paths dict
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
index.theme ─┘        │                                              icon_library.py
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
2. gui.init()        Initialize icon catalog
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

  "_led_blue_icon_MIGRATED": "→ nuvola_actions_ledblue",

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

**WARNING: All three steps (PNG + ICON_MAPPING.json + `_legacy_icon_defs()`) are required!**
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

8. **Add metadata to `_legacy_icon_defs()` in `icon_library.py`** (for icon picker):
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

Legacy icons (flat PNGs like `hearts_icon16x16.png`) predate the XDG theme system.
When a theme equivalent exists, the legacy icon should be retired and migrated.

### Completed Migrations

| Legacy Name | Replacement | Visual Match |
|-------------|-------------|-------------|
| `bell_icon` | `nuvola_apps_preferences-desktop-notification-bell` | Golden bell |
| `bomb_icon` | `nuvola_apps_clanbomber` | Black bomb |
| `bookmark_icon` | `nuvola_apps_package_favorite` | Single red glossy heart |
| `cactus` | `nuvola_apps_khangman` | Green cactus |
| `heart_icon` | `nuvola_apps_package_favorite` | Single red glossy heart |
| `hearts_icon` | `nuvola_apps_amor` | Multiple red hearts |
| `folder_favorite_icon` | `nuvola_places_folder-favorites` | Blue folder with red heart |
| `clock_alarm_icon` | `nuvola_apps_kalarm` | Orange alarm clock |
| `energy_icon` | `nuvola_apps_preferences-system-power-management` | Battery/power/energy |
| `lamp_icon` | `nuvola_apps_ktip` | Lightbulb/tip/idea |
| `traffic_go_icon` | `nuvola_places_start-here` | KDE gear/cog logo |
| `trafficlight_icon` | `nuvola_apps_ksysv` | Traffic light |
| `key_icon` | `nuvola_status_key-single` | Single golden key |
| `keys_icon` | `nuvola_status_key-group` | Multiple keys/keyring |
| `music_piano_icon` | `nuvola_actions_piano` | Piano keyboard |
| `music_note_icon` | `nuvola_actions_playsound` | Music note |
| `cd_icon` | `nuvola_devices_media-optical` | CD/disc |
| `chat_icon` | `nuvola_apps_chat` | Chat bubble |
| `cake_icon` | `nuvola_apps_preferences-web-browser-cookies` | Cake/cookie |
| `camera_icon` | `nuvola_devices_camera-photo` | Camera |
| `wrench_icon` | `nuvola_actions_configure` | Wrench/settings |
| `wizard_icon` | `nuvola_actions_tools-wizard` | Wizard/magic wand |
| `weather_umbrella_icon` | `nuvola_apps_preferences-desktop-color` | Colorful umbrella |
| `weather_lightning_icon` | `nuvola_apps_preferences-web-browser-cache` | Lightning bolt |
| `weather_sunny_icon` | `nuvola_apps_kweather` | Sun with clouds |
| `tea_icon` | `nuvola_apps_kteatime` | Tea cup |
| `terminal_icon` | `nuvola_apps_terminal` | Terminal/console |
| `remote_icon` | `nuvola_devices_remote` | Remote control |
| `run_icon` | `nuvola_mimetypes_application-x-executable` | Executable/run |
| `password_icon` | `nuvola_status_dialog-password` | Password/lock |
| `bug_icon` | `nuvola_apps_kbugbuster` | Ladybug |
| `book_icon` | `nuvola_apps_accessories-dictionary` | Book |
| `books_icon` | `nuvola_apps_bookcase` | Books/bookcase |
| `computer_laptop_icon` | `nuvola_apps_laptop_pcmcia` | Laptop computer |
| `trashcan_icon` | `nuvola_places_user-trash` | Trash can / recycle bin |
| `person_talking_icon` | `nuvola_categories_applications-education` | Person speaking/education |
| `pencil_icon` | `nuvola_actions_draw-freehand` | Pencil |
| `palette_icon` | `nuvola_apps_kcoloredit` | Color palette |
| `briefcase_icon` | `nuvola_apps_preferences-desktop-user` | Briefcase |
| `person_icon` | `nuvola_apps_preferences-desktop-user` | Person/user |
| `persons_icon` | `nuvola_apps_kuser` | People/group |
| `person_id_icon` | `nuvola_actions_contact-new` | Person ID card |
| `contact_card_icon` | `nuvola_mimetypes_text-x-vcard` | Contact/business card |
| `symbol_plus_icon` | `nuvola_actions_list-add` | Plus/add symbol |
| `symbol_minus_icon` | `nuvola_actions_list-remove` | Minus/remove symbol |
| `star_red_icon` | `nuvola_apps_mozilla` | Red star |
| `sign_important_icon` | `nuvola_status_dialog-warning` | Warning/important sign |
| `science_icon` | `nuvola_categories_applications-science` | Science flask |
| `arrow_down_icon` | `nuvola_actions_go-down` | Down arrow |
| `arrow_forward_icon` | `nuvola_actions_go-next` | Forward arrow |
| `arrow_up_icon` | `nuvola_actions_go-up` | Up arrow |
| `arrows_looped_blue_icon` | `nuvola_actions_kaboodleloop` | Blue looped arrows |
| `arrows_looped_green_icon` | `nuvola_actions_view-refresh` | Green looped arrows |
| `box_icon` | `nuvola_apps_kpackage` | Box/package |
| `paperclip_icon` | `nuvola_status_mail-attachment` | Paperclip/attachment |
| `attach_icon` | `nuvola_status_mail-attachment` | Blue paperclip/attachment |
| `fsview_icon` | `nuvola_apps_fsview` | Color swatches/theme |
| `print` | `nuvola_devices_printer` | Printer (main toolbar) |
| `undo` | `nuvola_actions_edit-undo` | Undo arrow (main toolbar) |
| `redo` | `nuvola_actions_edit-redo` | Redo arrow (main toolbar) |
| `save` | `nuvola_devices_media-floppy` | Floppy disk/save (main toolbar) |
| `mergedisk` | `nuvola_actions_go-top` | Merge disk changes (main toolbar) |
| `fileopen` | `nuvola_actions_document-open` | File open folder (main toolbar) |
| `calendar_icon` | `nuvola_apps_date` | Calendar |
| `graph_icon` | `nuvola_apps_kchart` | Chart/graph |
| `computer_desktop_icon` | `nuvola_devices_computer` | Desktop computer |
| `computer_handheld_icon` | `nuvola_devices_pda` | Handheld/PDA |
| `cookie_icon` | `nuvola_apps_preferences-web-browser-cookies` | Cookie/treat |
| `cogwheels_icon` | `nuvola_apps_kcmsystem` | Cogwheels/gears |
| `cogwheel_icon` | `nuvola_apps_preferences-system-session-services` | Cogwheel/gear |
| `printer_icon` | `nuvola_devices_printer` | Printer |
| `led_blue_questionmark_icon` | `nuvola_actions_help-about` | Question mark |
| `reload_icon` | `nuvola_actions_view-refresh` | Reload/refresh arrows |
| `sticky_note_icon` | `nuvola_apps_knotes` | Sticky note/post-it |
| `magnifier_glass_icon` | `nuvola_apps_xmag` | Magnifier glass/search |
| `life_ring_icon` | `nuvola_apps_help-browser` | Life ring/help |
| `led_blue_information_icon` | `nuvola_status_dialog-information` | Information |
| `calculator_icon` | `nuvola_apps_accessories-calculator` | Calculator |
| `clock_icon` | `nuvola_apps_clock` | Blue clock (tracking/effort) |
| `note_icon` | `nuvola_apps_knotes` | Yellow note/post-it |
| `lock_locked_icon` | `nuvola_actions_decrypted` | Locked padlock |
| `lock_unlocked_icon` | `nuvola_actions_encrypted` | Unlocked padlock |
| `charts_icon` | `nuvola_apps_kchart` | Charts/statistics |
| `cross_red_icon` | `nuvola_status_dialog-error` | Red cross/error |
| `die_icon` | `nuvola_apps_atlantik` | Die/dice |
| `document_icon` | `nuvola_mimetypes_application-x-dvi` | Document/file |
| `earth_blue_icon` | `nuvola_categories_applications-internet` | Blue globe/earth |
| `folder_important_icon` | `nuvola_places_folder-important` | Important folder |
| `folder_green_icon` | `nuvola_places_folder-green` | Green folder |
| `folder_grey_icon` | `nuvola_places_folder-grey` | Grey folder |
| `folder_orange_icon` | `nuvola_places_folder-orange` | Orange folder |
| `folder_purple_icon` | `nuvola_places_folder-violet` | Purple folder |
| `folder_red_icon` | `nuvola_places_folder-red` | Red folder |
| `folder_yellow_icon` | `nuvola_places_folder-yellow` | Yellow folder |
| `folder_blue_icon` | `nuvola_mimetypes_inode-directory` | Blue folder (default category) |
| `folder_blue_arrow_icon` | `nuvola_places_folder-downloads` | Blue folder with arrow |
| `house_red_icon` | `nuvola_places_user-home` | Red house |
| `house_green_icon` | `nuvola_actions_go-home` | Green house |
| `led_blue_icon` | `nuvola_actions_ledblue` | Blue LED (active task status) |
| `led_blue_light_icon` | `nuvola_actions_ledlightblue` | Light blue LED |
| `led_green_icon` | `nuvola_actions_ledgreen` | Green LED |
| `led_red_icon` | `nuvola_actions_ledred` | Red LED (overdue task status) |
| `led_purple_icon` | `nuvola_actions_ledpurple` | Purple LED (late task status) |
| `led_orange_icon` | `nuvola_actions_ledorange` | Orange LED (due soon task status) |
| `led_green_light_icon` | `nuvola_actions_ledlightgreen` | Light green LED |
| `led_yellow_icon` | `nuvola_actions_ledyellow` | Yellow LED |
| `exit` | `nuvola_actions_application-exit` | Power/exit button (FileQuit) |
| `new` | `nuvola_actions_document-new` | New document icon (new item commands) |
| `copy` | `nuvola_actions_edit-copy` | Copy (EditCopy) |
| `paste` | `nuvola_actions_edit-paste` | Paste (EditPaste) |
| `cut` | `nuvola_actions_edit-cut` | Cut (EditCut) |
| `saveas` | `nuvola_actions_document-save-as` | Save As (FileSaveAs) |
| `close` | `nuvola_actions_dialog-close` | Close (FileClose) |
| `delete` | `nuvola_actions_edit-delete` | Delete |
| `viewnewviewer` | `nuvola_actions_tab-new-background` | New viewer menu |
| `activatenextviewer` | `nuvola_actions_tab-duplicate` | Activate next viewer |
| `edit` | `nuvola_actions_edit` | Edit item |
| `incpriority` | `nuvola_actions_arrow-up` | Increase priority |
| `decpriority` | `nuvola_actions_arrow-down` | Decrease priority |
| `maxpriority` | `nuvola_actions_arrow-up-double` | Max priority |
| `minpriority` | `nuvola_actions_arrow-down-double` | Min priority |
| `error_icon` | `nuvola_status_dialog-error` | Error icon |
| `envelope_icon` | `nuvola_apps_email` | Envelope/mail |
| `envelopes_icon` | `nuvola_actions_mail-queue` | Multiple envelopes/mail queue |

#### TaskCoach Custom Icons

These icons are custom to Task Coach (not from an upstream XDG theme). They
are maintained in icon-distillery (`~/Downloads/icon-distillery/taskcoach/`)
and imported into the `taskcoach` theme following the same XDG structure as
nuvola/oxygen.

**Theme wiring** is already in place:
- `ICON_THEME_CATALOG.json`: `"taskcoach"` is `"active": true`
- `icon_library.py`: theme loop uses `get_available_themes()`
  (reads the catalog dynamically — no code change needed for new themes)
- `defaults.py`: `"theme_taskcoach": "True"` in `iconpicker` section
- `preferences.py`: checkbox "Show TaskCoach icons in picker"
- `iconpicker.py`: `theme_taskcoach` filter in enabled_themes block

**Import procedure for new taskcoach icons:**

1. Prepare the icon in icon-distillery (`~/Downloads/icon-distillery/taskcoach/`).
   The distillery produces `icons.json`, `contexts.json`, `index.theme`, and
   PNG files in `{size}x{size}/` directories.

2. **Manually** update the app theme files. The distillery is a **superset**
   — it will include icons AND sizes that TaskCoach does NOT need now.
   Only copy and update the minimum required to migrate the **target icons**.
   Do NOT blindly copy the full JSON/theme files. Instead:

   - **`icons.json`**: Add only the target icon's entry to the app's
     `taskcoachlib/gui/icons/taskcoach/icons.json`. Copy that single
     entry from the distillery's `icons.json`.
   - **`contexts.json`**: If the target icon uses a new context not yet
     in the app's file, add that context entry. Otherwise skip.
   - **`index.theme`**: If the target icon introduces a new size
     directory not yet listed, add the `[NxN]` section. Otherwise skip.
   - **PNG files**: Copy only the PNG(s) for the target icon, and only
     the sizes it actually needs (see Size Requirements above):
     ```
     cp icon-distillery/taskcoach/16x16/icon_name.png  taskcoachlib/gui/icons/taskcoach/16x16/
     cp icon-distillery/taskcoach/22x22/icon_name.png  taskcoachlib/gui/icons/taskcoach/22x22/  # only if needed
     cp icon-distillery/taskcoach/32x32/icon_name.png  taskcoachlib/gui/icons/taskcoach/32x32/  # only if needed
     ```

3. Run the generator to produce `icons_parsed.py`:
   ```
   python3 tools/generate_icons_parsed_py.py taskcoach
   ```

4. Follow the standard Migration Procedure below (deprecated_icons, remove
   from chooseableItems, update hardcoded refs, delete legacy PNGs, update docs).
   In Step 3.1, the replacement name uses `taskcoach_{context}_{stem}` instead
   of `nuvola_{context}_{stem}`.

**Size requirements for taskcoach icons:**

Main toolbar icons (see table in Step 2 below) require **16, 22, AND 32px**.
All three sizes must be produced by the distillery and copied into the
corresponding `{size}x{size}/` directories. The `index.theme` and `icons.json`
from the distillery already declare these sizes.

Tier 1 (user-assignable) and Tier 2 icons not on the main toolbar only need
16px.

**Completed taskcoach migrations:**

| Legacy Name | Replacement | Visual Match |
|-------------|-------------|-------------|
| `arrow_down_with_status_icon` | `taskcoach_actions_arrow_down_with_status_icon` | Down arrow with status overlay (sort indicator) |
| `arrow_up_with_status_icon` | `taskcoach_actions_arrow_up_with_status_icon` | Up arrow with status overlay (sort indicator) |
| `clock_menu_icon` | `taskcoach_actions_clock_menu_icon` | Clock with dropdown triangle (effort start button, 16/22/32) |
| `clock_resume_icon` | `taskcoach_actions_clock_resume_icon` | Clock with play overlay (effort resume, 16/22/32) |
| `clock_stop_icon` | `taskcoach_actions_clock_stop_icon` | Clock with red stop overlay (effort stop, 16/22/32) |
| `led_grey_icon` | `taskcoach_actions_led_grey_icon` | Grey LED circle (inactive task status, 16) |
| `tree_collapse_all` | `taskcoach_actions_tree_collapse_all` | Collapse all tree nodes (viewer toolbar, 16) |
| `tree_expand_all` | `taskcoach_actions_tree_expand_all` | Expand all tree nodes (viewer toolbar, 16) |
| `paste_subitem` | `taskcoach_actions_paste_subitem` | Paste as subitem/subcategory (menu, 16) |
| `newsub` | `taskcoach_actions_newsub` | New sub-item/subtask (menu + viewer toolbar, 16) |
| `viewalltasks` | `taskcoach_actions_viewalltasks` | Three colored circles, clear all filters (viewer toolbar, 16) |
| `activatepreviousviewer` | `taskcoach_actions_tab-duplicate-left` | Green window with left arrow, mirrored tab-duplicate (menu, 16) |
| `arrow_down_right` | `taskcoach_actions_arrow_down_right` | Green arrow pointing down-right, indent/demote (menu + editor, 16) |
| `checkall` | `taskcoach_actions_checkall` | Check all categories (editor toolbar, 16) |
| `uncheckall` | `taskcoach_actions_uncheckall` | Uncheck all categories (editor toolbar, 16) |
| `timer_icon` | `nuvola_apps_ktimer` | Clock with blue/red hands (user-assignable, 16) |
| `star_yellow_icon` | `taskcoach_actions_star_yellow_icon` | Yellow star (user-assignable, 16) |
| `folder_blue_light_icon` | `taskcoach_actions_folder_blue_light_icon` | Light blue folder (user-assignable + plural target, 16) |
| `file_important_icon` | `taskcoach_actions_file_important_icon` | File with exclamation (user-assignable, 16) |
| `file_locked_icon` | `taskcoach_actions_file_locked_icon` | File with lock (user-assignable, 16) |
| `link_icon` | `taskcoach_actions_link_icon` | Blue chain link, DnD prereq/dep cursor (16/22/32) |
| `folder_home_icon` | `nuvola_places_user-home` | House icon, DnD root-drop cursor (16/22/32 imported) |
| `earth_green_icon` | `taskcoach_actions_earth_green_icon` | Green globe (user-assignable, 16) |
| `next` | `nuvola_actions_go-next-document` | Right arrow, calendar/toolbar next (16) |
| `prev` | `nuvola_actions_go-previous-document` | Left arrow, calendar/toolbar prev (16) |
| `newtmpl` | `taskcoach_actions_newtmpl` | Orange sticky note, new template toolbar button (16) |
| `timelineviewer` | `taskcoach_actions_timelineviewer` | Timeline/gantt chart viewer tab icon (16) |
| `taskcoach` | `nuvola_apps_korganizer` | App identity icon — window, tray, notifications (16/22/32/48/64/128) |
| `progress` | `nuvola_actions_go-last` | Progress bar arrow, editor progress tab icon (16) |
| `clock_stopwatch_icon` | `nuvola_apps_ktimer` | Stopwatch, tray tack icon (16/48/128 for tray) |
| `up` | `nuvola_actions_arrow-up` | Up arrow, toolbar reorder move up (16) |
| `down` | `nuvola_actions_arrow-down` | Down arrow, toolbar reorder move down (16) |
| `box_in_icon` | `taskcoach_actions_box_in_icon` | Green inbox/download box (user-assignable, 16) |
| `box_out_icon` | `taskcoach_actions_box_out_icon` | Red outbox/upload box (user-assignable, 16) |
| `checkmark_green_icon` | `nuvola_actions_ok` | Green checkmark, completed-tasks status default (16) |
| `checkmark_green_icon_multiple` | `taskcoach_actions_checkmark_green_icon_multiple` | Double green checkmarks, plural variant (custom, 16) |
| `listview` | `nuvola_actions_view-list-details` | List view icon, orphaned (16) |
| `windows` | `nuvola_apps_window_list` | Overlapping windows, preferences page icon (16) |
| `restore` | `nuvola_apps_preferences-system-windows` | Restore window command icon (16) |
| `squaremapviewer` | `taskcoach_actions_squaremapviewer` | Square map/treemap viewer tab icon (custom, 16) |
| `magnifier_glass_dropdown_icon` | `taskcoach_actions_magnifier_glass_dropdown_icon` | Search menu dropdown icon (custom, 16) |
| `fileopen_red` | `taskcoach_actions_fileopen_red` | Red file icon, broken/missing attachment indicator (custom, 16) |
| `exportashtml` | `nuvola_mimetypes_text-html` | HTML export menu command icon (16) |
| `exportasvcal` | `nuvola_mimetypes_text-vcalendar` | iCalendar export menu command icon (16) |
| `exportascsv` | `nuvola_mimetypes_x-office-spreadsheet` | CSV export menu command icon (16) |
| `sort` | `taskcoach_actions_sort` | Manual ordering indicator in tree views (custom, 16) |
| `cat_icon` | `nuvola_categories_applications-toys` | Cat icon, user-assignable (16) |
| `incpriority` | `nuvola_actions_arrow-up` | Increase priority (menu submenu icon) |

### Migration Procedure

Follow these steps for each legacy icon being retired.

#### Step 1 — Where-used analysis (comprehensive)

Search ALL code for the legacy icon name. Every reference must be accounted for:

- **Python code**: `grep -r "icon_name" taskcoachlib/ tests/`
- **Menus and toolbars**: hardcoded UI references in viewer/toolbar code
- **Icon picker**: `icon_catalog.viewer_icon_ids()` in `icon_library.py`
- **Defaults**: task status icons, type defaults, viewer defaults
- **Plural/singular mappings**: `itemImagePlural` in `domain/attribute/icon/__init__.py`
- **Documentation**: `docs/ICON_PLURALIZE.md`, `docs/ICON_LIBRARY.md`, demo scripts
- **Data files**: JSON catalogs, `icons_parsed.py`, `nuvola/icons.json`
- **Test data**: unit tests using the icon name as test data
- **Auto-generated files**: `SOURCES.txt` (auto-updates on build, no manual action)

#### Step 2 — Identify the theme equivalent

1. Search nuvola `icons.json` / `icons_parsed.py` by hints, label, or visual match
2. **Visually compare** the legacy icon and the nuvola candidate side-by-side
   (open/view both image files) to confirm they are the same icon
3. **Check available sizes.** User-assignable icons (Tier 1) only need 16px —
   the tree view, icon picker, menus, and editors all request `(16, 16)`
   via `icon_catalog.get_bitmap()`. Viewer toolbars are
   also fixed at `(16, 16)` (`viewer/base.py:75`). If the nuvola icon has
   16px, no additional sizes are needed.

   **Main toolbar icons require 16, 22, AND 32px.** The main toolbar
   (`MainToolBar`) is user-resizable via View > Toolbar menu: Small (16×16),
   Medium (22×22, default), Large (32×32). If the migrated icon is any of
   these 9 main toolbar commands, import all 3 sizes from the distillery:

   | # | Command class | Current bitmap= |
   |---|---------------|-----------------|
   | 1 | FileOpen | `fileopen` |
   | 2 | FileSave | `save` |
   | 3 | FileMergeDiskChanges | `mergedisk` |
   | 4 | Print | `print` |
   | 5 | EditUndo | `undo` |
   | 6 | EditRedo | `redo` |
   | 7 | EffortStartButton | `taskcoach_actions_clock_menu_icon` |
   | 8 | EffortStop | `taskcoach_actions_clock_resume_icon` |
   | 9 | EditToolBarPerspective | `nuvola_apps_preferences-system-session-services` |

   (Defined in `mainwindow.py:434` + auto-appended at `toolbar.py:144`)

   **Templates dialog** (`templates.py:119`) also requests 32×32 for its
   BitmapButtons (go-up, go-down, list-add).

   **Never generate or scale icons to create missing sizes.** Each size is
   hand-optimized in the source theme. If a size is missing from the
   distillery, contact the icon-distillery owner to produce it from the
   original source (SVG or nearest size). Do not use `convert -resize`
   or any other scaling tool.

   **Do not confuse with the system tray icon path**, which
   requests 128px on Mac — that is only for the application/tray icon,
   not user-assignable icons.
4. Note any duplicates pointing to the target icon

#### Step 3 — Code changes

1. **`persistence/xml/reader.py`**: Add entry to `_deprecated_icons` dict.
   This auto-converts old icon names when loading XML task files. On next save,
   the new name is written permanently.

   ```python
   _deprecated_icons = {
       "old_icon_name": "nuvola_context_newname",
   }
   ```

2. **`icon_library.py`**: Remove the legacy entry from `_legacy_icon_defs()`.
   Users now see the proper nuvola icon in the picker instead.

3. **`domain/attribute/icon/__init__.py`**: Remove the migrated icon's entry
   from `itemImagePlural` if it was the singular (key) side of a mapping.
   Do NOT replace the key with the new nuvola name — the plural icon
   (e.g., `keys_icon`) is a separate icon that needs its own migration.
   Just delete the row. Update `docs/ICON_PLURALIZE.md` likewise.

4. **Test files**: Update any tests using the legacy icon name as test data.

#### Step 4 — Delete legacy files

Delete the legacy PNG files from `taskcoachlib/gui/icons/`.
Legacy icons use one of two naming conventions:
- Flat: `name_icon{size}x{size}.png` (e.g., `bomb_icon16x16.png`)
- Size-dir: `{size}x{size}/name.png` (e.g., `16x16/cactus.png`)

#### Step 5 — Update documentation

- `docs/ICON_PLURALIZE.md` — remove row from plural table if applicable
- `docs/scripts/icon_picker_refactoring_demo.py` — update test data
- `docs/ICON_LIBRARY.md` — add to "Completed Migrations" table above
- Delete `icon_overview.html` and `generate_icon_overview.py` if not already removed

#### Step 6 — Verify

1. Launch app, open icon picker — old icon gone, theme equivalent present
2. Load a task file with old icon name — confirm auto-migration
3. Save and reopen — confirm XML now has new icon name
4. Check log output — no errors for the migrated icon

### Migration Tiers

- **Tier 1 — User-assignable only** (hearts, bombs, keys, etc.): straightforward,
  follow procedure above. The icon appears only in the picker and user data files.
- **Tier 2 — Hardcoded defaults** (status LEDs, type icons, viewer icons): requires
  additional code changes beyond the deprecated mapping (default values in code).
- **Tier 3 — Semantic pairs** (LED→folder, singular→plural with different images):
  needs replacement concept, not just renaming.

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
