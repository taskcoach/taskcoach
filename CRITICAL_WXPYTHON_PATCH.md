# ⚠️ CRITICAL: wxPython Background Color Patch

**Status**: REQUIRED WORKAROUND
**Severity**: HIGH - Visual bug affects core functionality
**Version**: 1.1.1.005 (527ecf1)
**Last Updated**: 2025-11-16

---

## 🔴 IMPORTANCE

This patch is **ABSOLUTELY CRITICAL** for TaskCoach to display category row background colors correctly on Debian Bookworm. Without it, only text backgrounds are colored, not full rows, making the category system nearly unusable.

**This workaround is required until:**
- Debian ships wxPython 4.2.4+ (which includes the upstream fix), OR
- wxPython 4.2.4+ becomes available via `pip install` in a venv

---

## 📋 Summary

**Problem**: Debian Bookworm ships wxPython 4.2.0, which has two critical bugs affecting background coloring in tree list widgets:

1. **Issue #2081**: `TR_FULL_ROW_HIGHLIGHT` flag doesn't draw item backgrounds
2. **Issue #1898**: `TR_FILL_WHOLE_COLUMN_BACKGROUND` doesn't fill right-aligned columns

**Solution**: We patch the `hypertreelist.py` file in the venv with fixes from wxPython PR #2088 (merged upstream in wxPython 4.2.4).

**Impact**: Category-based row coloring works correctly, matching TaskCoach's original design.

---

## 🔧 How The Patch Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Python Startup                                              │
│  ↓                                                           │
│ usercustomize.py loads (automatic in venv)                  │
│  ↓                                                           │
│ Import hook installed at sys.meta_path[0]                   │
│  ↓                                                           │
│ TaskCoach imports wx.lib.agw.hypertreelist                  │
│  ↓                                                           │
│ Import hook intercepts → loads PATCHED version from venv    │
│  ↓                                                           │
│ System version BYPASSED                                     │
│  ↓                                                           │
│ Full row backgrounds work correctly! ✓                      │
└─────────────────────────────────────────────────────────────┘
```

### Components

1. **`patches/wxpython/hypertreelist.py`** (5380 lines)
   - Patched copy of wxPython 4.2.0's hypertreelist.py
   - Contains fixes from wxPython PR #2088
   - Applied Roland171281's fix for Issue #2081
   - Applied Jorilx's fix for Issue #1898

2. **`apply-wxpython-patch.sh`** (110 lines)
   - Copies patched file to `.venv/lib/python3.11/site-packages/wx/lib/agw/`
   - Creates `usercustomize.py` with import hook
   - Verifies patch applied successfully
   - Called automatically by `setup_bookworm.sh` at step [6/7]

3. **`usercustomize.py`** (generated, 50 lines)
   - Auto-loaded by Python on startup when in venv
   - Installs MetaPathFinder at position 0
   - Intercepts imports of `wx.lib.agw.hypertreelist`
   - Redirects to patched version
   - Includes comprehensive logging with `[WXPYTHON_PATCH]` prefix

4. **`test_wx_import.py`** (57 lines)
   - Verifies both patches are present in loaded module
   - Checks for Issue #2081 fix marker
   - Checks for PR #2088 fix marker
   - Reports success/failure

---

## 🐛 The Bugs (Technical Details)

### Bug #1: Issue #2081 - TR_FULL_ROW_HIGHLIGHT

**File**: `wx/lib/agw/hypertreelist.py`
**Line**: ~3027 (in patched version)
**Function**: `TreeListMainWindow.PaintItem()`

**Original Code** (BROKEN):
```python
elif drawItemBackground:
    pass
    # We have to colour the item background for each column separately
    # So it is better to move this functionality in the subsequent for loop.
else:
    dc.SetTextForeground(colText)
```

**Patched Code** (FIXED):
```python
elif drawItemBackground:
    # Fix from Issue #2081 (Roland171281) - Draw full row background
    itemrect = wx.Rect(0, item.GetY() + off_h, total_w-1, total_h - off_h)
    dc.SetBrush(wx.Brush(colBg, wx.SOLID))
    dc.DrawRectangle(itemrect)
    dc.SetTextForeground(colText)
else:
    dc.SetTextForeground(colText)
```

**Why it was broken**: The `pass` statement meant backgrounds were never drawn. The comment suggested moving it to the column loop, but that causes clipping issues.

**The fix**: Draw the full-row background BEFORE the column loop, spanning from x=0 to x=total_width.

---

### Bug #2: Issue #1898 - TR_FILL_WHOLE_COLUMN_BACKGROUND for Right-Aligned Columns

**File**: `wx/lib/agw/hypertreelist.py`
**Lines**: Multiple locations (~3122, 3135, 3152 in original)
**Function**: `TreeListMainWindow.PaintItem()` column loop

**Original Code** (BROKEN):
```python
if self.HasAGWFlag(TR_FILL_WHOLE_COLUMN_BACKGROUND):
    itemrect = wx.Rect(text_x-2, item.GetY() + off_h, col_w-2*_MARGIN, total_h - off_h)
```

**Patched Code** (FIXED):
```python
if self.HasAGWFlag(TR_FILL_WHOLE_COLUMN_BACKGROUND):
    itemrect = wx.Rect(x_colstart, item.GetY() + off_h, col_w, total_h - off_h)
```

**Why it was broken**: For right-aligned text (like dates), `text_x` is far from the left edge of the column. Using `text_x-2` as the rectangle's x-position creates gaps on the left side.

**The fix**: Use `x_colstart` (the column's starting position) to ensure the background fills the entire column width, regardless of text alignment.

---

## 📊 Visual Comparison

### BEFORE Patch (wxPython 4.2.0 stock)
```
╔═══════════════════════════════════════════════════════╗
║ Subject               │ Planned  │ Due      │ Status ║
╠═══════════════════════════════════════════════════════╣
║ Bug task              │ 2007-02  │ 2007-02  │ Active ║  ← Only text BG red
║   ^red text^          │   ^gap^  │   ^gap^  │        ║
║                       │          │          │        ║
║ Feature task          │ 2007-03  │ 2007-03  │ Active ║  ← Only text BG green
║   ^green text^        │   ^gap^  │   ^gap^  │        ║
╚═══════════════════════════════════════════════════════╝
```

### AFTER Patch (wxPython 4.2.0 + PR #2088)
```
╔═══════════════════════════════════════════════════════╗
║ Subject               │ Planned  │ Due      │ Status ║
╠═══════════════════════════════════════════════════════╣
║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│▓▓▓▓▓▓▓▓▓▓│▓▓▓▓▓▓▓▓▓▓│▓▓▓▓▓▓▓▓║  ← FULL ROW red
║▓Bug task▓▓▓▓▓▓▓▓▓▓▓▓▓▓│▓2007-02▓▓│▓2007-02▓▓│▓Active▓║
║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│▓▓▓▓▓▓▓▓▓▓│▓▓▓▓▓▓▓▓▓▓│▓▓▓▓▓▓▓▓║
║░░░░░░░░░░░░░░░░░░░░░░░│░░░░░░░░░░│░░░░░░░░░░│░░░░░░░░║  ← FULL ROW green
║░Feature task░░░░░░░░░░│░2007-03░░│░2007-03░░│░Active░║
║░░░░░░░░░░░░░░░░░░░░░░░│░░░░░░░░░░│░░░░░░░░░░│░░░░░░░░║
╚═══════════════════════════════════════════════════════╝
```

**Key differences:**
- Full-width background coloring across ALL columns
- Right-aligned date columns fully colored (no gaps)
- Consistent visual appearance matching original design
- Categories easily distinguishable at a glance

---

## 🚀 Installation

The patch is **automatically applied** during setup:

```bash
./setup_bookworm.sh
```

This runs step [6/7] which calls `apply-wxpython-patch.sh` automatically.

### Verification

```bash
source .venv/bin/activate
python3 test_wx_import.py
```

**Expected output:**
```
======================================================================
wxPython Patch Verification Script
Version 1.1.1.003 (f20c4dc)
======================================================================

[WXPYTHON_PATCH] ======================================================================
[WXPYTHON_PATCH] usercustomize.py is being loaded
[WXPYTHON_PATCH] Initializing wxPython hypertreelist patch import hook
[WXPYTHON_PATCH] ======================================================================
[WXPYTHON_PATCH] ✓ WxPatchFinder installed at position 0 in sys.meta_path
[WXPYTHON_PATCH] sys.meta_path now has 4 finders
[WXPYTHON_PATCH]
[WXPYTHON_PATCH] Import hook installation complete
[WXPYTHON_PATCH] ======================================================================

Python executable: /home/user/.../taskcoach/.venv/bin/python3
wx imported from: /usr/lib/python3/dist-packages/wx/__init__.py
wx version: 4.2.0

[WXPYTHON_PATCH] Import hook triggered for: wx.lib.agw.hypertreelist
[WXPYTHON_PATCH] Looking for patched file at: .venv/lib/python3.11/site-packages/wx/lib/agw/hypertreelist.py
[WXPYTHON_PATCH] ✓ Patched file found! Loading patched version...
[WXPYTHON_PATCH] ✓ Module spec created: ModuleSpec(name='wx.lib.agw.hypertreelist', ...)
[WXPYTHON_PATCH] ======================================================================
[WXPYTHON_PATCH] PATCHED wx.lib.agw.hypertreelist module is being loaded
[WXPYTHON_PATCH] This version includes fixes for TR_FULL_ROW_HIGHLIGHT and
[WXPYTHON_PATCH] TR_FILL_WHOLE_COLUMN_BACKGROUND background coloring issues
[WXPYTHON_PATCH] ======================================================================

hypertreelist imported from: .venv/lib/python3.11/site-packages/wx/lib/agw/hypertreelist.py

✓ Issue #2081 patch PRESENT - TR_FULL_ROW_HIGHLIGHT background fix!
✓ PR #2088 patch PRESENT - TR_FILL_WHOLE_COLUMN_BACKGROUND fix!

✓✓ ALL PATCHES VERIFIED - Background coloring should work correctly!
```

---

## 📝 Logging Output

All patch-related operations log to stdout with prefix `[WXPYTHON_PATCH]` or `[MONKEYPATCH]`.

### Startup Sequence

1. **Python starts** → `usercustomize.py` auto-loads
2. **Import hook installs** → Logs installation at `sys.meta_path[0]`
3. **TaskCoach imports monkeypatches** → `[MONKEYPATCH]` logs appear
4. **TaskCoach imports hypertreelist** → Import hook intercepts
5. **Patched module loads** → `[WXPYTHON_PATCH]` logs confirm

### Log Prefixes

- `[WXPYTHON_PATCH]` - wxPython background coloring patch
- `[MONKEYPATCH]` - Python compatibility patches (inspect.getargspec, Window.SetSize)

### Example Full Startup Log

```
[MONKEYPATCH] ======================================================================
[MONKEYPATCH] Module taskcoachlib.workarounds.monkeypatches is being loaded
[MONKEYPATCH] ======================================================================
[MONKEYPATCH] inspect.getargspec is missing (Python 3.11+)
[MONKEYPATCH] Applying inspect.getargspec workaround patch...
[MONKEYPATCH] ✓ inspect.getargspec patch applied successfully
[MONKEYPATCH]
[MONKEYPATCH] Applying Window.SetSize patch for GTK assertion fix...
[MONKEYPATCH] Original method: wx.core.Window.SetSize
[MONKEYPATCH] ✓ Window.SetSize patch applied successfully
[MONKEYPATCH]
[MONKEYPATCH] ======================================================================
[MONKEYPATCH] All monkeypatches have been applied successfully
[MONKEYPATCH] Module loading complete
[MONKEYPATCH] ======================================================================
```

---

## 🔍 Troubleshooting

### Problem: Patch not applied (test fails)

**Symptom**: `test_wx_import.py` reports patches MISSING

**Diagnosis**:
```bash
ls .venv/lib/python3.11/site-packages/wx/lib/agw/hypertreelist.py
```

If file doesn't exist, patch wasn't applied.

**Solution**:
```bash
./apply-wxpython-patch.sh
```

---

### Problem: No `[WXPYTHON_PATCH]` logs appear

**Symptom**: Only `[MONKEYPATCH]` logs, no wxPython patch logs

**Diagnosis**: `usercustomize.py` not loaded

**Solution**:
```bash
# Check if file exists
ls .venv/lib/python3.11/site-packages/usercustomize.py

# If missing, re-apply patch
./apply-wxpython-patch.sh

# Verify you're in venv
source .venv/bin/activate
which python3  # Should show .venv/bin/python3
```

---

### Problem: Backgrounds still not colored

**Symptom**: Patch applied and verified, but backgrounds don't show

**Possible causes**:

1. **TaskCoach not using the right flags**
   - Check if `TR_FULL_ROW_HIGHLIGHT` or `TR_FILL_WHOLE_COLUMN_BACKGROUND` is set
   - Look in `taskcoachlib/gui/viewer/` for tree list creation

2. **Categories don't have colors set**
   - Open TaskCoach → Edit → Preferences → Categories
   - Ensure categories have background colors assigned

3. **Wrong wxPython version loaded**
   - Run `python3 -c "import wx; print(wx.__file__)"`
   - Should show system path: `/usr/lib/python3/dist-packages/wx/__init__.py`
   - hypertreelist should show venv path

---

## ⏰ When Can We Remove This Patch?

This workaround can be removed when **ANY** of the following conditions are met:

### Option 1: Debian Ships wxPython 4.2.4+

**Current Status** (2025-11-16):
- Debian Bookworm (12): wxPython 4.2.0 (patch REQUIRED)
- Debian Trixie (13): TBD - check when released
- Debian Sid (unstable): TBD

**How to check**:
```bash
apt-cache policy python3-wxgtk4.0
```

If version >= 4.2.4, the upstream fix is included.

**Action when available**:
1. Update system: `sudo apt-get update && sudo apt-get upgrade`
2. Remove patch infrastructure:
   ```bash
   rm -rf .venv/lib/python3.*/site-packages/wx/
   rm -f .venv/lib/python3.*/site-packages/usercustomize.py
   rm -f apply-wxpython-patch.sh
   rm -rf patches/wxpython/
   ```
3. Update `setup_bookworm.sh` to remove step [6/7]
4. Test thoroughly

---

### Option 2: wxPython 4.2.4+ Available via pip

**Current Status** (2025-11-16):
- wxPython in PyPI requires building from source
- Debian's system wxPython is pre-compiled for Python 3.11
- pip install would require C++ compiler + dependencies

**How to check**:
```bash
pip index versions wxPython
```

Look for binary wheels (`.whl`) for Linux.

**Action when available**:
1. Add to `setup_bookworm.sh`:
   ```bash
   pip install wxPython>=4.2.4
   ```
2. Remove system wxPython dependency
3. Remove patch infrastructure (same as Option 1)
4. Test thoroughly

---

## 📚 References

### Upstream Issues & PRs

- **wxPython Issue #2081**: "TR_FULL_ROW_HIGHLIGHT broken in Phoenix 4.x"
  - Reporter: Roland171281
  - https://github.com/wxWidgets/Phoenix/issues/2081

- **wxPython Issue #1898**: "TR_FILL_WHOLE_COLUMN_BACKGROUND broken for right-aligned columns"
  - Reporter: Jorilx
  - https://github.com/wxWidgets/Phoenix/issues/1898

- **wxPython PR #2088**: "Fix for both issues"
  - Author: cbeytas
  - Merged: 2023
  - Included in: wxPython 4.2.4+
  - https://github.com/wxWidgets/Phoenix/pull/2088

### TaskCoach Project

- **GitHub**: https://github.com/taskcoach/taskcoach
- **Original Issue**: Category row coloring not working on Debian Bookworm
- **Screenshots**: See `test screenshots/Category Row Color Problem 01.png` and `02.png`

### Documentation Files

- **LOGGING_GUIDE.md**: Complete logging reference
- **DEBIAN_BOOKWORM_SETUP.md**: Setup instructions
- **patches/wxpython/README.md**: Patch technical details

---

## 👥 Credits

**Patch Development**:
- Roland171281: Identified Issue #2081 and proposed fix
- Jorilx: Identified Issue #1898 and proposed fix
- cbeytas: Created PR #2088 merging both fixes
- wxPython Team: Merged PR #2088 into 4.2.4

**TaskCoach Integration**:
- Claude (Anthropic AI): Integration, testing, documentation
- Session: claude/add-module-loading-logs-01SvgNHroJJfg6fZCGp2mqd5

---

## 📄 License

The patched `hypertreelist.py` file retains its original wxPython license (wxWindows Library Licence).

The integration scripts (`apply-wxpython-patch.sh`, `test_wx_import.py`, etc.) follow TaskCoach's GPL-3.0 license.

---

## ✅ Verification Checklist

Use this checklist to verify the patch is working correctly:

- [ ] `setup_bookworm.sh` completes successfully
- [ ] Step [6/7] "Applying wxPython patch" runs without errors
- [ ] `test_wx_import.py` reports "✓✓ ALL PATCHES VERIFIED"
- [ ] `[WXPYTHON_PATCH]` logs appear when running TaskCoach
- [ ] `[MONKEYPATCH]` logs appear when running TaskCoach
- [ ] Created a task with a category (e.g., "Bug" with red color)
- [ ] Full row background is red (not just text background)
- [ ] Right-aligned date columns have full red background
- [ ] No white gaps between columns
- [ ] Multiple categories show different colors correctly
- [ ] Colors span complete window width

If ALL items are checked ✓, the patch is working correctly!

---

**⚠️ DO NOT REMOVE THIS PATCH UNTIL WXPYTHON 4.2.4+ IS AVAILABLE IN DEBIAN OR VIA PIP**

Last verified working: 2025-11-16
Debian version: 12 (Bookworm)
wxPython version: 4.2.0
Python version: 3.11.2
