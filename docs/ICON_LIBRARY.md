# Icon Library

## IMPORTANT: Complete Import Cycle

**When adding a new icon, ALL THREE steps are required:**

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

**ICON_MAPPING.json alone does NOT make an icon usable!** It only documents where the icon came from. The PNG file and artprovider.py entry are required for the icon to appear in the picker.

**View the actual icon** before writing hints - describe what you SEE, not just the filename.

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
- `ICON_SOURCES.json` - Source repositories (URL, license)
- `ICON_MAPPING.json` - Maps icon names to source + original filename

**Metadata** (names, hints) is in `taskcoachlib/gui/artprovider.py:chooseableItems`.

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
├── ICON_SOURCES.json         # Source repositories
├── ICON_MAPPING.json         # Icon provenance
│
├── # Legacy icons (flat, coexist during migration)
├── person_icon16x16.png      # Legacy: keep _icon suffix
└── person_icon22x22.png
```

### ICON_SOURCES.json

Defines source repositories (one entry per icon set):
```json
{
  "papirus": {
    "url": "https://github.com/PapirusDevelopmentTeam/papirus-icon-theme",
    "license": "GPL-3.0"
  },
  "breeze": {
    "url": "https://github.com/KDE/breeze-icons",
    "license": "LGPL-2.1"
  },
  "twemoji": {
    "url": "https://github.com/twitter/twemoji",
    "license": "MIT"
  },
  "nuvola": {
    "url": "https://github.com/nicubunu/nuvola-icon-theme",
    "license": "LGPL-2.1"
  },
  "taskcoach": {
    "url": "https://github.com/taskcoach/taskcoach",
    "license": "GPL-3.0"
  }
}
```

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
- `source` - Library name (must exist in ICON_SOURCES.json)
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
- `gnome-themes-extras-0.9.0` - Contains Nuvola SVG sources (274 vectors), but unmaintained since 2005

**Legacy/Unmaintained sets:**

| Set | Status | Notes |
|-----|--------|-------|
| Nuvola | Unmaintained | Final v1.0 by David Vignoni. Mirror: https://github.com/spartrekus/nuvola-icon-theme |
| gnome-themes-extra | Archived | https://gitlab.gnome.org/GNOME/gnome-themes-extra (v3.28, read-only) |

The standalone `nuvola/` folder (3,706 PNGs) is more complete than gnome-themes-extras Nuvola (274 SVGs).
Keep both if you want SVG sources for potential future scaling.

**Reference links:**
- [Nuvola - Wikipedia](https://en.wikipedia.org/wiki/Nuvola) - History and background
- [gnome-themes-extra - GitLab](https://gitlab.gnome.org/GNOME/gnome-themes-extra) - Archived official repo
- [spartrekus/nuvola-icon-theme - GitHub](https://github.com/spartrekus/nuvola-icon-theme) - Community mirror

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

7. **Update ICON_SOURCES.json** (if new source):
   ```json
   "papirus": {
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

   **Important:** Always VIEW the actual icon image before writing hints. Don't rely solely on the filename—icons often depict something different from their name. For example:
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

## TODO

### Monochrome Icon Support
- [ ] Add support for monochrome (symbolic) icons from Breeze, Adwaita
- [ ] Implement icon recoloring: monochrome icons can be tinted to match theme
- [ ] Add icon color options to the icon picker:
  - Primary color picker for monochrome icons
  - Preview of tinted icon before selection
- [ ] Document which icon sets have monochrome variants

**Note:** Currently only pre-colored icons are used. Breeze icons have colors (#232629 dark gray + accent colors like #da4453 red, #27ae60 green) - they are NOT monochrome. The `-symbolic` variants ARE monochrome. Only the `-symbolic` versions should be excluded until recoloring support is implemented.

### Duplicate Icon Review
- [x] Document duplicates in ICON_MAPPING.json to prevent re-importing
- [ ] Audit new icons against existing legacy icons for visual duplicates

See `ICON_MAPPING.json` for documented duplicates (in the `duplicates` field of each icon entry).

## See Also

- [ICON_PLURALIZE.md](ICON_PLURALIZE.md) - Plural/singular icon mapping
- [TASK_STATUS.md](TASK_STATUS.md) - Status icon system
