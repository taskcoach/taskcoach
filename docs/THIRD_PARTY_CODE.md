# Third-Party Code

Everything Task Coach takes from other projects and ships, copies or
changes at runtime. Read it before diagnosing a bug in that code or
changing it; add to it whenever such code is added, and review it when
a dependency's version changes (a distribution release, a wxPython
pin).

## Before Analysing It

- **A copy's base is found by diffing**, against each upstream
  release's file. Dates and versions in its header are upstream's and
  often never updated (`hypertreelist.py` reads "Latest Revision: 30
  Jul 2014" in every release up to 4.3.1).
- **A copy can still run on the installed library.** List what it
  imports from the package it was taken from: those modules come from
  each build's installed version, and a change there reaches the copy
  ([BUNDLED_TREE_WIDGET.md](BUNDLED_TREE_WIDGET.md#one-widget-two-files)).
- **Each build installs its own versions**
  ([PACKAGING.md](PACKAGING.md#install-overview-by-build-target): wxPython
  4.0.7 on Ubuntu 22.04 to 4.3.1 on Windows, macOS and the Flatpak).
  The certified tests run one set ([TESTING.md](TESTING.md)); code
  that differs between builds is tested only where it runs.

## Bundled Copies

| Where | What | Details |
|-------|------|---------|
| `taskcoachlib/patches/hypertreelist.py`, `customtreectrl.py` | wxPython's tree widget, loaded in place of the installed one | [BUNDLED_TREE_WIDGET.md](BUNDLED_TREE_WIDGET.md) |
| `taskcoachlib/thirdparty/` | `deltaTime.py`, `ext_idle_notify_v1/`, `plasma_window_management/`, `timeline/`, `wxScheduler/` | provenance and changes in `taskcoachlib/thirdparty/README.txt` |

## Runtime Patches

Code that changes a library's behaviour for the whole process.

| Location | Patch | Purpose | Review notes |
|----------|-------|---------|--------------|
| `workarounds/monkeypatches.py` | tree widget import hook | Loads the bundled tree widget in place of wxPython's | Permanent ([BUNDLED_TREE_WIDGET.md](BUNDLED_TREE_WIDGET.md#loading)) |
| `workarounds/monkeypatches.py` | `Window.SetSize` clamp | A negative width or height becomes 0 (GTK asserts `height >= -1`) | Only the two- and four-number forms |
| `workarounds/monkeypatches.py` | `wx.CallAfter` crash guard | Skips callbacks to destroyed C++ objects instead of crashing | For library code; the app's own deferred calls go through `patterns.later` ([DEFERRED_CALLS.md](DEFERRED_CALLS.md), [CRASH_GUARD.md](CRASH_GUARD.md)) |
| `workarounds/monkeypatches.py` | `wx.Timer` owner guard (`Start`, `StartOnce`, `SetOwner`) | Moves a timer whose owner window is destroyed to a sink, logs where it was started | As above ([CRASH_GUARD.md](CRASH_GUARD.md)) |
| `workarounds/textundo.py` | `wx.TextCtrl` and `wx.SearchCtrl` `SetValue`, `ChangeValue`, `Clear` wrapped; `EVT_CHAR_HOOK` on the app | Undo and redo in text fields on GTK and in single-line ones on macOS; text the program sets starts a field's history over | wxWidgets 3.2.8 leaves `Undo()` a stub there; remove when it implements it ([MENUS.md](MENUS.md#keyboard-shortcuts)) |
| `workarounds/display.py` | `wx.Display` replaced (Windows) | Follows monitors plugged in or out | Possibly obsolete since wxWidgets 3.1; a Windows check is deferred (D6 in [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#deferred-or-will-not-do)). It has no `GetScaleFactor()`, so the startup report logs no scale factors on Windows (P125) |
| `widgets/__init__.py` | `wx.Dialog.__init__` binds `EVT_SET_CURSOR` | Stops the main window's sash cursor showing through dialogs | Required |
| `taskcoach.py` | `_set_wayland_app_id()` | Sets GLib's program name so Wayland docks match the window to its `.desktop` file | Required on Wayland |
| `application/application.py` | `OnExceptionInMainLoop` | Logs exceptions raised in wx event handlers instead of ending the program | wx's own hook, overridden ([CRASH_GUARD.md](CRASH_GUARD.md)) |

## Removed

- Bundled libraries removed in the Python 3 migration and since:
  `taskcoachlib/thirdparty/README.txt`.
- January 2026, from `taskcoach.py`: `XLIB_SKIP_ARGB_VISUALS=1` (an
  Ubuntu 10.10 workaround; its removal may resolve GitHub #64, user
  testing needed), the `mx.DateTime` import (Ubuntu 12.04), the
  `wxversion.select()` call (wx 2.8/3.0), the `/usr/share/pyshared`
  path (Ubuntu 12.04).
- 2026-09: the `inspect.getargspec` shim, the
  `wx.FontFromNativeInfoString` replacement
  (`wxhelper.font_from_native_info()`), the TEE module, the vendored
  `ntlm`, the old `patches/wxpython/` copy.
- 2026-10-01: the wxPython 2.8 menu workarounds (D7 in
  [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#deferred-or-will-not-do)).
