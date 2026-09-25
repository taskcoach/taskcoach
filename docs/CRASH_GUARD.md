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

Task Coach uses wxPython, which wraps C++ widgets. When Python holds a reference to a wx object whose C++ counterpart has been destroyed, calling any method on it causes a segfault. This commonly happens with `wx.CallAfter`: a callback is scheduled, but the target widget is destroyed before the callback fires. The same class of crash happens without any Python involvement when a `wx.Timer` is still running after its owner window has been destroyed: the timer keeps a raw C++ pointer to the owner and delivers the next tick into freed memory.

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
- `wx.Timer(window)` still running when `window` is destroyed, for example a timer (re)started by an event that is processed after the window's close handler already stopped it. No Python code runs when the tick arrives, so the only trace is a native crash with `MainLoop` as the only Python frame
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

### 2. wx.Timer Owner Guard (`monkeypatches.py`)

`wx.Timer.Start`, `StartOnce` and `SetOwner` are patched. When a timer whose owner is a `wx.Window` is started:

- The call stack of the `Start()` caller is recorded (source lines are only looked up if the stack is logged, so the cost per start is small)
- The owner is watched with `EVT_WINDOW_DESTROY`, holding only a weak reference to the timer so timer lifetimes are unchanged
- When the owner is destroyed, the timer is moved to a harmless sink owner. wx runs later-bound handlers first, so the owner's own destroy handler may still stop the timer after the guard; only a tick that actually reaches the sink stops the timer and logs a `[CRASH_GUARD]` message with the stack the timer was last started from
- A later `Start()` on a timer whose owner was destroyed is refused and logged with the current stack; `SetOwner()` clears that state

Without this guard the crash happens entirely in C++, so neither the `wx.CallAfter` guard nor `OnExceptionInMainLoop` sees it, and `faulthandler` shows only `MainLoop`. Timers whose owner is not a window (`wx.CallLater`, `wx.PyTimer`, timers owned by a plain `wx.EvtHandler`) pass through unchanged.

### 3. OnExceptionInMainLoop (`application.py`, `wxApp`)

Catches any unhandled Python exception that occurs during wx event dispatch. Logs the full traceback with a `[CRASH_GUARD]` prefix and returns `True` to continue running. Without this, some exceptions during event handling are silently swallowed by wx.

### 4. faulthandler (`taskcoach.py`)

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

### Timer still running after its owner window was destroyed:
```
[00:21:21.826] [CRASH_GUARD] Stopped timer still running after its owner window was destroyed: owner=EffortEditBook timer_id=844
[00:21:21.826] [CRASH_GUARD] Without this guard this tick would have been dispatched to the freed owner (native crash).
[00:21:21.826] [CRASH_GUARD] Timer was last started from:
...
[00:21:21.826] [CRASH_GUARD]     File ".../wx/core.py", line 2262, in MainLoop
[00:21:21.826] [CRASH_GUARD]       rv = wx.PyApp.MainLoop(self)
[00:21:21.826] [CRASH_GUARD]     File ".../taskcoachlib/gui/dialog/attributesync.py", line 62, in onAttributeEdited
[00:21:21.826] [CRASH_GUARD]       self.__executeCommand(new_value)
...
[00:21:21.826] [CRASH_GUARD]     File ".../taskcoachlib/gui/dialog/editor.py", line 4221, in __updateTimeSpentDisplay
[00:21:21.826] [CRASH_GUARD]       self.__startTimeSpentTimer()
[00:21:21.826] [CRASH_GUARD]     File ".../taskcoachlib/gui/dialog/editor.py", line 4254, in __startTimeSpentTimer
[00:21:21.826] [CRASH_GUARD]       self._timeSpentTimer.Start(1000)
```

From the effort editor case, before its fix: the start time of a tracked effort was changed and the dialog closed with the title bar X while the time field still had focus. The queued start-time commit ran after the close handler had stopped the timer, and restarted it on the page about to be destroyed. Fixed by moving the Time Spent display from its own `wx.Timer` to the GlobalTimer tick (see [SCHEDULERS.md](SCHEDULERS.md#subscribing-to-the-tick)).

### Start() of a timer whose owner window was destroyed:
```
[16:30:45.150] [CRASH_GUARD] Blocked Start() of timer whose owner window was destroyed: timer_id=-31950
[16:30:45.150] [CRASH_GUARD] Start() called from:
[16:30:45.150] [CRASH_GUARD]   File "...", line ..., in ...
```

### Unhandled exception in event loop:
```
[16:30:45.130] [CRASH_GUARD] Unhandled exception in MainLoop: Traceback (most recent call last):
  File "...", line ..., in ...
RuntimeError: wrapped C/C++ object of type TreeListMainWindow has been deleted
```

---

## Debugging a Segfault

If a segfault still occurs (the guards don't catch everything: direct event handlers on dead widgets bypass `CallAfter`, and the timer guard only covers timers owned by a `wx.Window`):

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
| `taskcoachlib/workarounds/monkeypatches.py` | `wx.CallAfter` wrapper, `wx.Timer` owner guard |
| `taskcoachlib/application/application.py` | `wxApp.OnExceptionInMainLoop` |
| `taskcoach.py` | `faulthandler.enable()` setup |
| `taskcoachlib/meta/debug.py` | `log_step()` utility for ad-hoc debugging |
