# Patch Logging Guide

This document explains the logging output you should see to verify that all patches are being loaded and executed correctly.

## Complete Execution Path

When you run TaskCoach, the following sequence should occur with corresponding log output:

### 1. Python Starts & Loads usercustomize.py (FIRST)

The venv's `usercustomize.py` is automatically loaded by Python on startup.

**Expected Log Output:**
```
[WXPYTHON_PATCH] ======================================================================
[WXPYTHON_PATCH] usercustomize.py is being loaded
[WXPYTHON_PATCH] Initializing wxPython hypertreelist patch import hook
[WXPYTHON_PATCH] ======================================================================
[WXPYTHON_PATCH] ✓ WxPatchFinder installed at position 0 in sys.meta_path
[WXPYTHON_PATCH] sys.meta_path now has X finders
[WXPYTHON_PATCH]
[WXPYTHON_PATCH] Import hook installation complete
[WXPYTHON_PATCH] ======================================================================
```

**What this proves:** The import hook is installed and ready to intercept imports.

---

### 2. TaskCoach Imports monkeypatches Module

TaskCoach imports `taskcoachlib.workarounds.monkeypatches` at startup.

**Expected Log Output:**
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

**What this proves:** Python compatibility patches are loaded.

---

### 3. TaskCoach Imports wx.lib.agw.hypertreelist

When TaskCoach needs the tree list widget, it imports the hypertreelist module.
The import hook intercepts this import and loads our patched version.

**Expected Log Output:**
```
[WXPYTHON_PATCH] Import hook triggered for: wx.lib.agw.hypertreelist
[WXPYTHON_PATCH] Looking for patched file at: /path/to/.venv/lib/python3.X/site-packages/wx/lib/agw/hypertreelist.py
[WXPYTHON_PATCH] ✓ Patched file found! Loading patched version...
[WXPYTHON_PATCH] ✓ Module spec created: ModuleSpec(name='wx.lib.agw.hypertreelist', loader=...)
[WXPYTHON_PATCH] ======================================================================
[WXPYTHON_PATCH] PATCHED wx.lib.agw.hypertreelist module is being loaded
[WXPYTHON_PATCH] This version includes fixes for TR_FULL_ROW_HIGHLIGHT and
[WXPYTHON_PATCH] TR_FILL_WHOLE_COLUMN_BACKGROUND background coloring issues
[WXPYTHON_PATCH] ======================================================================
```

**What this proves:**
- The import hook successfully intercepted the import
- The patched file was found in the venv
- The patched module is being loaded (not the system version)

---

## Verification Steps

### Step 1: Install the Patch

```bash
./setup_bookworm.sh      # Creates venv
./apply-wxpython-patch.sh # Installs patch
```

### Step 2: Test Import Hook

```bash
source .venv/bin/activate
python3 test_wx_import.py
```

**Expected Output:**
```
Python executable: /path/to/.venv/bin/python3
[WXPYTHON_PATCH] ======================================================================
[WXPYTHON_PATCH] usercustomize.py is being loaded
[... import hook logs ...]
wx imported from: /usr/lib/python3/dist-packages/wx/__init__.py
wx version: 4.2.x
[WXPYTHON_PATCH] Import hook triggered for: wx.lib.agw.hypertreelist
[... patched module loading logs ...]
hypertreelist imported from: /path/to/.venv/lib/python3.X/site-packages/wx/lib/agw/hypertreelist.py

✓ Issue #2081 patch PRESENT - TR_FULL_ROW_HIGHLIGHT background fix!
✓ PR #2088 patch PRESENT - TR_FILL_WHOLE_COLUMN_BACKGROUND fix!

✓✓ ALL PATCHES VERIFIED - Background coloring should work correctly!
```

### Step 3: Run TaskCoach

```bash
./taskcoach-run.sh
```

**Expected Log Output (on startup):**
1. First: usercustomize.py logs (import hook installation)
2. Second: monkeypatches.py logs (Python compatibility)
3. Third: hypertreelist.py logs (background color patch loaded)

### Step 4: Test Background Coloring

1. Create some tasks
2. Assign them to categories with colors (Bug=red, Feature=green, etc.)
3. View them in the tree list

**Visual Verification:**
- Full row backgrounds should be colored
- Right-aligned date columns should be fully colored
- No white gaps between columns
- Colors span the complete window width

---

## Troubleshooting

### No Logs Appear

**Problem:** You don't see any `[WXPYTHON_PATCH]` logs.

**Diagnosis:** The venv's usercustomize.py is not being loaded.

**Solutions:**
1. Make sure you're running from within the venv: `source .venv/bin/activate`
2. Check that usercustomize.py exists: `ls .venv/lib/python3.*/site-packages/usercustomize.py`
3. Re-run the patch script: `./apply-wxpython-patch.sh`

---

### Import Hook Logs Appear But Patched File Not Found

**Problem:** You see the import hook logs but it says "Patched file NOT found".

**Diagnosis:** The hypertreelist.py file wasn't copied to the venv.

**Solutions:**
1. Re-run the patch script: `./apply-wxpython-patch.sh`
2. Check the file exists: `ls .venv/lib/python3.*/site-packages/wx/lib/agw/hypertreelist.py`

---

### Patched Module Loads But Background Colors Don't Work

**Problem:** Logs show the patched module is loaded but colors still don't appear.

**Diagnosis:** The patch may not be correct or TaskCoach may not be using the right flags.

**Solutions:**
1. Run test_wx_import.py to verify both patches are present
2. Check TaskCoach code to see if it's using TR_FULL_ROW_HIGHLIGHT or TR_FILL_WHOLE_COLUMN_BACKGROUND flags
3. Look at the viewer code in taskcoachlib/gui/viewer/

---

## Log Prefixes

- `[WXPYTHON_PATCH]`: wxPython background coloring patch (import hook and patched module)
- `[MONKEYPATCH]`: Python compatibility patches (inspect.getargspec, Window.SetSize)

---

## Expected Timeline

```
[0.0s] Python starts
[0.0s] [WXPYTHON_PATCH] usercustomize.py loads and installs import hook
[0.1s] TaskCoach starts
[0.1s] [MONKEYPATCH] monkeypatches.py loads
[0.2s] [WXPYTHON_PATCH] Import hook intercepts hypertreelist import
[0.2s] [WXPYTHON_PATCH] Patched hypertreelist.py loads
[0.5s] GUI appears with correctly colored backgrounds
```

---

## Success Criteria

You know the patch is working correctly when you see ALL of the following:

- ✅ usercustomize.py loads on Python startup
- ✅ Import hook is installed in sys.meta_path
- ✅ Import hook intercepts wx.lib.agw.hypertreelist import
- ✅ Patched file is found and loaded
- ✅ test_wx_import.py reports both patches present
- ✅ Category row backgrounds display correctly in TaskCoach

If any of these fail, use the troubleshooting section above.
