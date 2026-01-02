# Issue #98: Segmentation Fault on Ubuntu 24.04.3 (HiDPI/KDE)

**Possibly related:**
- https://github.com/taskcoach/taskcoach/issues/64 (Segfault on Ubuntu 24.04)

## Summary

Task Coach crashes with a segmentation fault on startup for a user running Ubuntu 24.04.3 with KDE desktop and a HiDPI display (3840x2400).

**GitHub Issue:** https://github.com/taskcoach/taskcoach/issues/98

**Status:** UNDER INVESTIGATION - HiDPI display suspected as root cause

---

## User's Environment (Issue #98)

| Component | Version |
|-----------|---------|
| OS | Ubuntu 24.04.3 LTS (noble) |
| Kernel | Linux 6.8.0-90-generic |
| Python | 3.12.3 (GCC 13.3.0) |
| wxPython | 4.2.1 gtk3 (phoenix) |
| wxWidgets | 3.2.4 |
| GTK | 3.24.41 |
| glibc | 2.39 |
| Desktop | KDE (primary), MATE (secondary testing) |
| Display | HiDPI 3840x2400 (reported as 1920x1200 @ 192 PPI) |

### Environment Discrepancy: Kernel vs Distro Version

| Claimed Distro | Expected Kernel | Actual Kernel | Analysis |
|----------------|-----------------|---------------|----------|
| Ubuntu 24.04.3 LTS | 6.14 (HWE) | 6.8.0-90-generic | **Mismatch** |

Ubuntu 24.04.3 LTS ships with kernel 6.14. The user has kernel 6.8, which indicates:
- System was upgraded from 24.04.0/24.04.1 (not fresh install), OR
- User is running GA kernel instead of HWE kernel

This may affect reproducibility as older kernels may have different display/HiDPI handling.

---

## Crash Details

### Error
```
Fatal Python error: Segmentation fault
```

### Location
- **File:** `taskcoachlib/config/settings.py`
- **Line:** 116
- **Function:** `acquire_ini_lock()`

### GTK Warnings Before Crash
```
Gtk-WARNING: Theme parsing error: gtk.css:3:35: Missing semicolon at end of declaration
Gtk-WARNING: Theme parsing error: gtk.css:4:35: Missing semicolon at end of declaration
... (lines 3-12)
```

These GTK theme parsing warnings may indicate a corrupted or incompatible GTK theme, which could contribute to display-related crashes.

---

## User Testing Summary

### Test 1: KDE Desktop (Primary Environment)
- **Result:** CRASH on startup
- **Crash point:** `acquire_ini_lock()` in settings.py

### Test 2: After Removing Config File
- **Action:** Removed `~/.config/Task Coach/TaskCoach.ini`
- **Result:** Application started successfully in MATE

### Test 3: MATE Desktop with Clean Config
- **Result:** Application starts
- **Crash trigger:** "Adding a new task triggers segfault in typical manner"

### Test 4: Second System (Non-HiDPI)
- **Display:** 2560x1440 (standard DPI)
- **Result:** NO CRASHES after clean install
- **Conclusion:** HiDPI display (3840x2400) correlates with failure

---

## Comparison with Test Systems (January 2, 2026)

### Environment Comparison

| Component | Issue #98 User | Issue #64 Test System | Match |
|-----------|----------------|----------------------|-------|
| OS | Ubuntu 24.04.3 | Ubuntu 24.04 | Similar |
| Kernel | 6.8.0-90-generic | 6.14.0-37-generic | **No** (user older) |
| Python | 3.12.3 | 3.12.3 | Yes |
| wxPython | 4.2.1 gtk3 | 4.2.1 gtk3 | Yes |
| wxWidgets | 3.2.4 | 3.2.4 | Yes |
| GTK | 3.24.41 | 3.24.41 | Yes |
| glibc | 2.39 | 2.39 | Yes |
| Desktop | KDE | X11/GNOME | **No** |
| Display | 3840x2400 HiDPI | 1920x1029 | **No** |
| Monitors | 1 (HiDPI) | 1 (standard) | **No** |

### Key Differences

| Factor | Issue #98 User | Test System | Likely Impact |
|--------|----------------|-------------|---------------|
| **HiDPI Display** | 3840x2400 @ 192 PPI | 1920x1029 | **HIGH** - Display scaling issues |
| **Desktop** | KDE | X11/GNOME | **MEDIUM** - Different compositor |
| **Kernel** | 6.8.0-90 | 6.14.0-37 | **LOW** - But may affect display drivers |
| **GTK Theme** | Has parse errors | Unknown | **MEDIUM** - Corrupted theme |

---

## Analysis

### HiDPI Display Discrepancy

The user's logs show a critical discrepancy:
- **Actual resolution:** 3840x2400 pixels
- **Reported resolution:** 1920x1200 pixels
- **PPI:** 192x192 (2x scaling)

This suggests wxWidgets/GTK is applying 200% scaling. The mismatch between actual and reported geometry may cause:
1. Memory access violations when calculating window positions
2. Buffer overflows in display rendering code
3. Invalid coordinates passed to GTK/wxWidgets functions

### Crash Location Difference

| Issue | Crash Location | Function |
|-------|----------------|----------|
| #64 | application.py:493 | `wx.Log.SetActiveTarget()` |
| #98 | settings.py:116 | `acquire_ini_lock()` |

Different crash locations suggest these may be different manifestations of the same underlying issue (HiDPI/display handling) or separate bugs.

## Suspected Root Cause

**Primary hypothesis:** HiDPI display scaling causes invalid geometry calculations in wxWidgets/GTK3 integration layer, leading to memory access violations.

**Supporting evidence:**
1. User's non-HiDPI system (2560x1440) has no crashes
2. Display geometry is reported incorrectly (3840x2400 → 1920x1200)
3. GTK theme parsing errors indicate possible display subsystem issues
4. KDE compositor may handle HiDPI differently than GNOME/X11

---

## Questions for User

1. **GTK Theme:** What GTK theme is active? The parsing errors suggest a corrupted theme file.
   ```bash
   cat ~/.config/gtk-3.0/gtk.css
   ```

2. **Display Scale Factor:** What is the KDE display scale setting?
   ```bash
   echo $QT_SCALE_FACTOR
   echo $GDK_SCALE
   ```

3. **Fresh Install Test:** Does a fresh Ubuntu 24.04.3 install (not upgrade) with kernel 6.14 work?

4. **X11 vs Wayland:** Is KDE running on X11 or Wayland?
   ```bash
   echo $XDG_SESSION_TYPE
   ```

5. **Scaling Environment Variables:** What display-related environment variables are set?
   ```bash
   env | grep -E "(SCALE|DPI|HI|DISPLAY|GDK|QT)"
   ```

---

## Potential Workarounds

### Workaround 1: Force 1x Scaling
```bash
export GDK_SCALE=1
export GDK_DPI_SCALE=1
./taskcoach-run.sh
```

### Workaround 2: Disable HiDPI
Set KDE display scaling to 100% (may make UI very small).

### Workaround 3: Use X11 Instead of Wayland
```bash
export XDG_SESSION_TYPE=x11
# or log into X11 session from login screen
```

### Workaround 4: Fresh Config
```bash
mv ~/.config/Task\ Coach ~/.config/Task\ Coach.backup
./taskcoach-run.sh
```

---

## Next Steps

1. **Reproduce on HiDPI:** Need access to a HiDPI display system to reproduce
2. **Add display diagnostics:** Enhance startup logging to capture:
   - Actual vs reported display geometry
   - Scale factors (GDK_SCALE, QT_SCALE_FACTOR)
   - Display PPI
3. **Test with different scaling:** See if the crash occurs at 100% vs 200% scaling

---

## Code to Investigate

### settings.py:116 - acquire_ini_lock()

The crash occurs during INI file locking. This may be a red herring - the actual crash could be in wx/GTK initialization that happens before this point, but the stack trace points here.

### Display geometry handling

Search for code that accesses display geometry:
- `wx.Display` usage
- `GetClientArea()`, `GetGeometry()` calls
- Window positioning code

---

## References

- [wxPython HiDPI Support](https://docs.wxpython.org/high_dpi_overview.html)
- [GTK3 HiDPI](https://wiki.archlinux.org/title/HiDPI#GTK_3)
- [KDE Plasma Scaling](https://wiki.archlinux.org/title/HiDPI#KDE_Plasma)

---

**Last Updated:** January 2, 2026
