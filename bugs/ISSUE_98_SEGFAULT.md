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

## Test Systems Reported in Issue #98

### System 1: wolftune (Original Reporter) - CRASHES

| Component | Value |
|-----------|-------|
| OS | Ubuntu 24.04.3 LTS (noble) |
| Kernel | Linux 6.8.0-90-generic |
| Python | 3.12.3 |
| wxPython | 4.2.1 gtk3 (phoenix) |
| wxWidgets | 3.2.4 |
| Desktop | KDE |
| Display | HiDPI 3840x2400 (reported as 1920x1200) |
| **Result** | **CRASH** - Segfault on startup |

### System 2: thomas2net Computer #1 - CRASHES

| Component | Value |
|-----------|-------|
| OS | Ubuntu 24.04.3 LTS (noble) |
| Kernel | Linux 6.8.0-90-generic |
| Python | 3.12.3 |
| wxPython | 4.2.1 gtk3 |
| Desktop | KDE (primary), MATE (fallback) |
| Display | 1920x1200 (standard DPI) |
| **Result** | **CRASH** - KDE: won't start; MATE: crashes on adding task |

### System 3: thomas2net Computer #2 - WORKS

| Component | Value |
|-----------|-------|
| OS | Ubuntu 24.04.3 LTS (noble) |
| Kernel | Linux 6.8.0-84-generic |
| Python | 3.12.3 |
| wxPython | 4.2.1 gtk3 |
| Desktop | MATE |
| Display | 2560x1440 (standard DPI) |
| **Result** | **WORKS** - No crashes |

### System 4: Issue #64 Test System (Reference) - WORKS

| Component | Value |
|-----------|-------|
| OS | Ubuntu 24.04 |
| Kernel | Linux 6.14.0-37-generic |
| Python | 3.12.3 |
| wxPython | 4.2.1 gtk3 |
| wxWidgets | 3.2.4 |
| GTK | 3.24.41 |
| Desktop | X11/GNOME |
| Display | 1920x1029 (standard DPI) |
| **Result** | **WORKS** - No crashes |

---

## Cross-System Analysis

### Comparison Matrix

| Factor | System 1 (CRASH) | System 2 (CRASH) | System 3 (WORKS) | System 4 (WORKS) |
|--------|------------------|------------------|------------------|------------------|
| Kernel | 6.8.0-90 | 6.8.0-90 | 6.8.0-84 | 6.14.0-37 |
| Desktop | KDE | KDE/MATE | MATE | X11/GNOME |
| Display | 3840x2400 HiDPI | 1920x1200 | 2560x1440 | 1920x1029 |
| HiDPI | Yes (2x scale) | No | No | No |
| Crashes | Startup | Add task | None | None |

### Pattern Analysis

**What CRASHES have in common:**
- Kernel 6.8.0-90-generic (both crashing systems)
- KDE desktop environment (at least initially)
- Ubuntu 24.04.3 (claimed, but kernel suggests upgrade not fresh install)

**What WORKS have in common:**
- Different kernel versions (6.8.0-84 and 6.14.0-37)
- Non-KDE desktops (MATE, GNOME)
- Standard DPI displays (no 2x scaling)

**Key observations:**

1. **Kernel 6.8.0-90 is suspect** - Both crashing systems have this exact kernel version. The working system 3 has 6.8.0-84 (slightly older), and system 4 has 6.14.0-37 (much newer).

2. **HiDPI is NOT the only factor** - System 2 crashes with standard 1920x1200 display, disproving pure HiDPI theory.

3. **KDE is strongly correlated** - Both crashing systems use KDE. System 2 only partially works in MATE (crashes on adding task).

4. **Crash timing varies:**
   - System 1 (HiDPI + KDE): Crashes on startup
   - System 2 (standard + KDE→MATE): Crashes on adding task

   This suggests multiple crash paths or the same underlying issue manifesting differently.

### Crash Location Difference

| Issue | Crash Location | Function |
|-------|----------------|----------|
| #64 | application.py:493 | `wx.Log.SetActiveTarget()` |
| #98 | settings.py:116 | `acquire_ini_lock()` |

Different crash locations suggest these may be different manifestations of the same underlying issue (HiDPI/display handling) or separate bugs.

## Suspected Root Cause

### Updated Hypothesis (Based on Multi-System Analysis)

**Primary suspect: Kernel 6.8.0-90-generic + KDE combination**

The cross-system analysis reveals that HiDPI is NOT the sole cause:
- System 2 crashes with standard 1920x1200 display
- Both crashing systems share kernel 6.8.0-90 and KDE
- Working systems have different kernels (6.8.0-84, 6.14.0-37) and non-KDE desktops

**Possible causes (in order of likelihood):**

1. **Kernel 6.8.0-90 regression** - Something specific to this kernel version interacts badly with wxPython/GTK

2. **KDE/Plasma compositor issue** - KDE's compositor may handle wxWidgets windows differently, causing memory corruption

3. **GTK theme corruption** - The gtk.css parsing errors suggest a broken theme that may cause crashes

4. **Combination of factors** - The crash may require multiple conditions (specific kernel + KDE + possibly display config)

**Supporting evidence:**
- Both crashing systems: kernel 6.8.0-90-generic
- Working system 3: kernel 6.8.0-84-generic (6 patch versions older)
- Working system 4: kernel 6.14.0-37-generic (much newer)
- Both crashing systems started with KDE
- System 2 partially works in MATE but still crashes on task creation

---

## Questions for Users

### Critical: Kernel Version Test

Both crashing systems have kernel 6.8.0-90. Can users test with a different kernel?

```bash
# Check available kernels
dpkg --list | grep linux-image

# Boot into older kernel from GRUB menu, or install newer HWE kernel:
sudo apt install linux-generic-hwe-24.04
```

### Other Questions

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
