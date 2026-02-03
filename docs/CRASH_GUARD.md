# Crash Guard System

## Table of Contents

1. [Overview](#overview)
2. [The Problem](#the-problem)
3. [Guards](#guards)
4. [Log Output](#log-output)
5. [Debugging a Segfault](#debugging-a-segfault)
6. [Key Files](#key-files)

---

## Overview

Task Coach uses wxPython, which wraps C++ widgets. When Python holds a reference to a wx object whose C++ counterpart has been destroyed, calling any method on it causes a segfault. This commonly happens with `wx.CallAfter` — a callback is scheduled, but the target widget is destroyed before the callback fires.

The crash guard system prevents these segfaults and logs diagnostic information when they would have occurred.

The crash guard is part of the runtime workarounds documented in [TODO.md — Monkeypatches and Workarounds](TODO.md#monkeypatches-and-workarounds).

---

## The Problem

wxPython segfaults from deleted C++ objects are:
- **Intermittent** — depend on timing between event dispatch, widget destruction, and deferred callbacks
- **Untraceable at C++ level** — Python's `faulthandler` can only show frames up to `wx.MainLoop`, not the actual C++ crash site
- **Silent** — without guards, the app simply dies with no useful information

Common triggers:
- `wx.CallAfter(widget.method)` where the widget is destroyed before the callback runs
- Event handlers firing on widgets that are being or have been closed (AUI panes, dialogs)
- `pub.subscribe` handlers referencing destroyed widgets
- HyperTreeList operations (`GetItemPyData`, `GetSelections`) on deleted tree items

---

## Guards

### 1. wx.CallAfter Wrapper (`monkeypatches.py`)

A global monkey-patch replaces `wx.CallAfter` with a guarded version. When the callback is a bound method on a `wx.Object`:

- The scheduling call stack is captured at `CallAfter` time
- Before executing the callback, `bool(obj)` is checked — returns `False` if the C++ object is deleted
- If the object is dead, the call is skipped and a `[CRASH_GUARD]` message is logged with the original scheduling traceback
- `RuntimeError` from deleted C++ objects is also caught as a fallback

Non-wx callbacks pass through with zero overhead.

### 2. OnExceptionInMainLoop (`application.py` — `wxApp`)

Catches any unhandled Python exception that occurs during wx event dispatch. Logs the full traceback with a `[CRASH_GUARD]` prefix and returns `True` to continue running. Without this, some exceptions during event handling are silently swallowed by wx.

### 3. faulthandler (`taskcoach.py`)

Enabled at startup with `all_threads=True`. Produces Python-level stack traces on hard crashes (SIGSEGV, SIGBUS). This is the last line of defense — if a segfault gets past the guards, faulthandler at least shows which Python code was executing.

---

## Log Output

All guard messages use the `CRASH_GUARD` prefix via `log_step()` (see `taskcoachlib/meta/debug.py`).

### Blocked CallAfter to destroyed object:
```
[16:30:45.123] [CRASH_GUARD] Blocked CallAfter to destroyed object: TreeListCtrl.DoResize
[16:30:45.123] [CRASH_GUARD] Originally scheduled from:
[16:30:45.123] [CRASH_GUARD]   File "taskcoachlib/widgets/autowidth.py", line 64, in onResize
[16:30:45.123] [CRASH_GUARD]     wx.CallAfter(self.DoResize)
```

### RuntimeError caught during callback:
```
[16:30:45.125] [CRASH_GUARD] RuntimeError calling TreeListCtrl.DoResize: wrapped C/C++ object has been deleted
[16:30:45.125] [CRASH_GUARD] Originally scheduled from:
[16:30:45.125] [CRASH_GUARD]   File "taskcoachlib/widgets/autowidth.py", line 64, in onResize
[16:30:45.125] [CRASH_GUARD]     wx.CallAfter(self.DoResize)
```

### Unhandled exception in event loop:
```
[16:30:45.130] [CRASH_GUARD] Unhandled exception in MainLoop: Traceback (most recent call last):
  File "...", line ..., in ...
RuntimeError: wrapped C/C++ object of type TreeListMainWindow has been deleted
```

---

## Debugging a Segfault

If a segfault still occurs (the guards don't catch everything — direct event handlers on dead widgets bypass `CallAfter`):

### Using GDB for C++ backtraces
```bash
gdb -ex run -ex "thread apply all bt" -ex quit --args python3 taskcoach.py
```

This shows the actual C++ frames that `faulthandler` cannot.

### Filtering guard logs
```bash
python3 taskcoach.py 2>&1 | grep CRASH_GUARD
```

If `CRASH_GUARD` messages appear during normal use, they indicate code paths that would have segfaulted without the guards. These should be investigated and fixed (typically by adding proper cleanup or removing unnecessary `CallAfter` usage).

---

## Key Files

| File | Component |
|------|-----------|
| `taskcoachlib/workarounds/monkeypatches.py` | `wx.CallAfter` wrapper |
| `taskcoachlib/application/application.py` | `wxApp.OnExceptionInMainLoop` |
| `taskcoach.py` | `faulthandler.enable()` setup |
| `taskcoachlib/meta/debug.py` | `log_step()` utility for ad-hoc debugging |
