# Issue #143: Segfault on Linux Mint MATE

GitHub Issue: https://github.com/taskcoach/taskcoach/issues/143

## Summary

Task Coach crashes with segmentation fault on Linux Mint MATE but runs correctly on Ubuntu GNOME with identical package versions and kernel.

## Confirmed Test Results

| # | Distro | Desktop | Kernel | Result |
|---|--------|---------|--------|--------|
| 1 | Ubuntu 24.04.3 | GNOME | 6.14.0-37-generic | **WORKS** |
| 2 | Ubuntu 24.04.3 | GNOME | 6.8.0-90-generic | **WORKS** |
| 3 | Linux Mint 22.3 | MATE | 6.8.0-90-generic | **CRASHES** |
| 4 | Linux Mint 21.3 | MATE | 6.8.0-90-generic | **CRASHES** |

## Ruled Out

- **Kernel version**: Same kernel (6.8.0-90) works on Ubuntu, crashes on Mint
- **Package versions**: Identical versions on Ubuntu 24.04 and Mint 22.3 (see below)
- **X11 vs Wayland**: Both test systems use X11
- **wxPython version mismatch**: Mint 22.3 uses system wxPython 4.2.1 (not pip)

## Package Versions (Identical on Ubuntu 24.04 and Mint 22.3)

```
Task Coach: 2.0.1.21
Python: 3.12.3
wxPython: 4.2.1 gtk3 (phoenix) wxWidgets 3.2.4
GTK: 3.24.41
glibc: 2.39
six: 1.16.0
pypubsub: 4.0.3
watchdog: 3.0.0
chardet: 5.2.0
python-dateutil: 2.8.2
pyparsing: 3.1.1
lxml: 5.2.1
pyxdg: 0.28
keyring: 24.3.1
numpy: 1.26.4
fasteners: 0.18
```

## Differences Between Working and Crashing Systems

| Factor | Ubuntu 24.04 (works) | Mint 22.3 (crashes) |
|--------|----------------------|---------------------|
| Desktop Environment | ubuntu:GNOME | MATE |
| Locale | en_US.UTF-8 | en_GB.UTF-8 |
| squaremap | 1.0.5 (installed) | missing |
| Base distro | Ubuntu | Ubuntu-derived |

## Crash Characteristics

### Mint 22.3 Crash (startup)
```
/usr/lib/python3/dist-packages/wx/lib/combotreebox.py:731: wxPyDeprecationWarning: Call to deprecated item. Use SetItemData instead.
  self._tree.SetItemPyData(item, clientData)
Fatal Python error: Segmentation fault

Current thread 0x000075786c949300 (most recent call first):
  File "/usr/lib/python3/dist-packages/wx/core.py", line 2262 in MainLoop
```

### Mint 21.3 Crash (effort creation)
```
/usr/lib/python3/dist-packages/taskcoachlib/gui/dialog/entry.py:349: Warning: invalid cast from 'GtkComboBox' to 'GtkComboBoxText'
(taskcoach:1467340): Gtk-CRITICAL **: gtk_combo_box_text_insert: assertion 'GTK_IS_COMBO_BOX_TEXT (combo_box)' failed

*** BUG ***
In pixman_region32_init_rect: Invalid rectangle passed

Fatal Python error: Segmentation fault
```

### Ubuntu 24.04 with kernel 6.8.0-90 (runs fine, has warnings)
```
(taskcoach:3351): Gtk-CRITICAL **: gtk_box_gadget_distribute: assertion 'size >= 0' failed in GtkScrollbar
/usr/lib/python3/dist-packages/wx/lib/combotreebox.py:731: wxPyDeprecationWarning: Call to deprecated item. Use SetItemData instead.
```

Note: Ubuntu shows GTK warnings but does not crash.

## Outstanding Questions

1. What is different about MATE's GTK configuration vs GNOME's?
2. Does Mint include MATE-specific GTK themes/settings that affect widget behavior?
3. Is there a MATE-specific library or configuration causing the GtkComboBox type mismatch?
4. Would installing Ubuntu MATE desktop (instead of GNOME) on the test system reproduce the crash?

## Next Steps to Reproduce

To isolate MATE as the cause, test on Ubuntu 24.04 with:
```bash
sudo apt install ubuntu-mate-desktop
# Log out, select MATE session, log in
# Run taskcoach.py
```

## Related Files

- `taskcoachlib/gui/dialog/entry.py` - Contains TaskEntry using combotreebox
- `wx/lib/combotreebox.py` - System wxPython widget showing deprecation warnings

## Date

2026-01-19
