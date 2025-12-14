# wxPython Patch for Full-Row Background Coloring

This directory contains a patched version of wxPython's `hypertreelist.py` file.

## Patch Status (2025-12-14)

| Debian Release | wxPython Version | Patch Required? |
|----------------|------------------|-----------------|
| Bookworm (12)  | 4.2.0+dfsg-3     | YES |
| Trixie (13)    | 4.2.3+dfsg-2     | YES |
| Sid (unstable) | 4.2.3+dfsg-2     | YES |

**Upstream fix**: wxPython 4.2.4 (released October 28, 2025) - not yet in Debian.

## What This Fixes

The patch applies fixes from wxPython [PR #2088](https://github.com/wxWidgets/Phoenix/pull/2088) (included in wxPython 4.2.4) to wxPython < 4.2.4:

- ✓ Full-row background colors (not just text backgrounds)
- ✓ Right-aligned columns (date fields) now fully colored
- ✓ Background colors span complete window width
- ✓ No white gaps between colored cells

## Changes Made

### Fix 1: TR_FULL_ROW_HIGHLIGHT (Issue #2081, line 3011)

Fixes background coloring when `TR_FULL_ROW_HIGHLIGHT` flag is enabled.

**Original code**:
```python
elif drawItemBackground:
    pass
    # We have to colour the item background for each column separately
    # So it is better to move this functionality in the subsequent for loop.
else:
    dc.SetTextForeground(colText)
```

**Patched code**:
```python
elif drawItemBackground:
    itemrect = wx.Rect(0, item.GetY() + off_h, total_w-1, total_h - off_h)
    dc.SetBrush(wx.Brush(colBg, wx.SOLID))
    dc.DrawRectangle(itemrect)
    dc.SetTextForeground(colText)
else:
    dc.SetTextForeground(colText)
```

### Fix 2: TR_FILL_WHOLE_COLUMN_BACKGROUND for Right-Aligned Columns (Issue #1898, lines 3122, 3135, 3152)

Fixes background coloring for right-aligned columns when `TR_FILL_WHOLE_COLUMN_BACKGROUND` flag is enabled.

**Original code** (3 locations):
```python
if self.HasAGWFlag(TR_FILL_WHOLE_COLUMN_BACKGROUND):
    itemrect = wx.Rect(text_x-2, item.GetY() + off_h, col_w-2*_MARGIN, total_h - off_h)
```

**Patched code**:
```python
if self.HasAGWFlag(TR_FILL_WHOLE_COLUMN_BACKGROUND):
    itemrect = wx.Rect(x_colstart, item.GetY() + off_h, col_w, total_h - off_h)
```

**Why this fix is needed**: For right-aligned text, `text_x` is positioned far from the left edge of the column, leaving gaps in the background. Using `x_colstart` (column start position) ensures the background fills the entire column width.

## Installation Methods

There are two ways to apply this patch, depending on how Task Coach is installed:

### Method 1: Development / Source Installation (venv)

For developers or users running Task Coach from source using a virtual environment.

**How it works:**
1. The venv is created with `--system-site-packages` to access system wxPython
2. The patched file is copied to `.venv/lib/python3.11/site-packages/wx/lib/agw/hypertreelist.py`
3. An import hook in `usercustomize.py` intercepts imports of `wx.lib.agw.hypertreelist`
4. Python loads the patched venv version instead of the system version
5. No system files are modified

**Installation:**
```bash
./apply-wxpython-patch.sh
```

This script:
1. Creates the necessary directory structure in the venv
2. Copies the patched file to the correct location
3. Installs the import hook (`usercustomize.py`)
4. Verifies the patch was applied successfully

### Method 2: Debian Package Installation (system-wide)

For users installing Task Coach via a `.deb` package. Debian packages do not use virtual environments.

**How it works:**
1. The patched `hypertreelist.py` is bundled within the Task Coach package
2. Installed to `/usr/share/taskcoach/lib/hypertreelist.py`
3. Task Coach activates an import hook at startup to use the bundled version
4. The system wxPython package remains unmodified

**Key difference:** The venv approach relies on Python's site-packages search order, while the Debian package approach bundles the file and uses an import hook activated by the application itself.

For Debian packaging details, see [docs/DEBIAN_PACKAGING.md](../../docs/DEBIAN_PACKAGING.md).

## Maintenance

To update this patch:

1. Get the original file from system: `/usr/lib/python3/dist-packages/wx/lib/agw/hypertreelist.py`
2. Apply the changes shown above
3. Save to `patches/wxpython/hypertreelist.py`
4. Run `./apply-wxpython-patch.sh` to update the venv

## Debian Quilt Patch

For official Debian packaging, a quilt-format patch with DEP-3 headers is available at:
`debian/patches/fix-hypertreelist-background-coloring.patch`

This patch is listed in `debian/patches/series` and will be applied during package build.

## References

- [wxPython Issue #2081](https://github.com/wxWidgets/Phoenix/issues/2081): TR_FULL_ROW_HIGHLIGHT broken in Phoenix 4.x
- [wxPython Issue #1898](https://github.com/wxWidgets/Phoenix/issues/1898): TR_FILL_WHOLE_COLUMN_BACKGROUND broken for right-aligned columns
- [wxPython PR #2088](https://github.com/wxWidgets/Phoenix/pull/2088): Fix for both issues (merged August 5, 2025)
- [wxPython 4.2.4 Release](https://wxpython.org/news/2025-10-28-wxpython-424-release/index.html): Released October 28, 2025
