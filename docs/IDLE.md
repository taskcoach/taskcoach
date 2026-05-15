# Idle Time Detection

How Task Coach detects user inactivity and decides what to do about a
running effort entry. Used by the "Idle time notice" feature (Preferences
> Features > Idle time notice).

## Index

- [Feature Overview](#feature-overview)
- [Platform Support Matrix](#platform-support-matrix)
- [Backend Probe Order (Linux)](#backend-probe-order-linux)
- [Setting](#setting)
- [Wake-From-Idle Dialog](#wake-from-idle-dialog)
- [State Machine](#state-machine)
- [Startup Logging](#startup-logging)
- [Known Gaps](#known-gaps)
- [File Reference](#file-reference)
- [See Also](#see-also)

---

## Feature Overview

When a task is being tracked for effort and the user stops interacting
with the computer for at least `feature.minidletime` minutes, Task Coach
records a "went idle" timestamp. When the user returns, a notification
pops up offering to back-date the effort's stop time, optionally
resuming a fresh effort entry from "now".

The feature is off by default (`minidletime = 0`). It activates as soon
as the user sets a non-zero value in Preferences.

---

## Platform Support Matrix

Idle detection backend per platform. Backends are tried in order on
Linux; the first one that responds is used.

| Platform | Backend | Mechanism | Notes |
|----------|---------|-----------|-------|
| **Windows** | `win32_GetLastInputInfo` | `user32.GetLastInputInfo` + `kernel32.GetTickCount` | Single backend, no fallback. Works on all supported Windows versions. |
| **macOS** | `iokit_HIDIdleTime` | IOKit `IORegistryEntryCreateCFProperty` on `IOHIDSystem`, property `HIDIdleTime` | Pure-ctypes; loads `IOKit.framework` and `CoreFoundation.framework`. Replaces the pre-2026 `_idle.so` C extension. |
| **Linux/GTK (GNOME, X11 or Wayland)** | `dbus_mutter` | DBus call `org.gnome.Mutter.IdleMonitor.GetIdletime` on `/org/gnome/Mutter/IdleMonitor/Core` | Returns milliseconds. Works for GNOME Shell sessions including Wayland. |
| **Linux/GTK (KDE Plasma on X11)** | `dbus_screensaver` | DBus call `org.freedesktop.ScreenSaver.GetSessionIdleTime` on `/ScreenSaver` | Returns seconds. KDE KWin implements this on X11. On Plasma Wayland KWin replies `NotSupported`; see `wayland_ext_idle` below. |
| **Linux/GTK (KDE Plasma on Wayland, wlroots, COSMIC)** | `wayland_ext_idle` | `ext_idle_notifier_v1` Wayland staging protocol via `pywayland` | Event-driven; the backend translates `idled`/`resumed` events to the polling `get_idle_seconds()` API by registering a 1-second-timeout notification and tracking the `idled` timestamp. Requires `python3-pywayland` to be installed; the protocol bindings are vendored in `taskcoachlib/thirdparty/pywayland_protocols/ext_idle_notify_v1/`. |
| **Linux/GTK (legacy X11)** | `x11_mit_screensaver` | `libXss.so.1` `XScreenSaverQueryInfo` via the X11 MIT-SCREEN-SAVER extension | Final fallback. Works on any X11 session whose server advertises the extension. Does not work on Wayland-only compositors. |
| **Linux/GTK (other)** | none | none | If all four probes fail, a one-time warning is logged and the feature silently disables itself for the session. |

### Compositor Coverage Today

| Scenario | Covered by |
|----------|------------|
| GNOME on X11 or Wayland | `dbus_mutter` |
| KDE Plasma on X11 | `dbus_screensaver` |
| KDE Plasma on Wayland | `wayland_ext_idle` (KWin advertises `ext_idle_notifier_v1`) |
| LXDE, XFCE, MATE, Cinnamon, i3, Openbox on X11 | `x11_mit_screensaver` |
| wlroots compositors (Sway, Hyprland, niri, river, Wayfire) | `wayland_ext_idle` |
| COSMIC (System76) | `wayland_ext_idle` |

All mainstream Linux desktops are now covered, provided
`python3-pywayland` is installed for the Wayland backend.

---

## Backend Probe Order (Linux)

`LinuxIdleQuery._initialize()` in `taskcoachlib/powermgt/idle.py` runs
lazily on the first `getIdleSeconds()` call. It probes:

1. `dbus_mutter` - attempts a real `GetIdletime()` call. Caches the
   interface on success.
2. `dbus_screensaver` - attempts a real `GetSessionIdleTime()` call.
   Caches the interface on success.
3. `wayland_ext_idle` - if `WAYLAND_DISPLAY` is set and `pywayland` is
   importable, connects to the Wayland display, binds `wl_seat` and
   `ext_idle_notifier_v1`, and registers a 1-second-timeout
   notification with `idled`/`resumed` handlers. Caches the display
   and notification on success and registers an `atexit` hook to
   disconnect cleanly (workaround for a pywayland 0.4.x segfault on
   interpreter shutdown).
4. `x11_mit_screensaver` - opens `DISPLAY`, checks for the
   `MIT-SCREEN-SAVER` extension via `XQueryExtension`, then allocates
   the screensaver info struct.

Each attempt records `(method_name, success, detail)` in
`self._probe_log`. The first success wins; later methods are not
probed. The selected method is exposed via `get_backend_name()`.

The probe is triggered explicitly at startup by `IdleController`
when the feature is enabled, so subsequent runtime calls hit the
already-selected backend with no extra cost.

---

## Setting

| Setting | Section | Default | Units | Effect |
|---------|---------|---------|-------|--------|
| `minidletime` | `feature` | `0` | minutes | Threshold for going idle. `0` disables the feature. |

Defined in `taskcoachlib/config/defaults.py` (section `feature`).
Editable in Preferences > Features as "Idle time notice".

`IdleController.get_min_idle_time()` returns the value times 60
(seconds) and is consulted on every state-machine tick.

---

## Wake-From-Idle Dialog

When the user returns from an idle period during effort tracking, a
`WakeFromIdleFrame` notification is shown for each tracked effort.
It carries three buttons:

| Button | Action |
|--------|--------|
| Do nothing | Keep the effort running across the idle gap. |
| Stop it at *idle-time* | Back-date the effort's stop time to when the user went idle. |
| Stop it at *idle-time* and resume now | Same as above, plus start a fresh effort on the same task starting now. |

The dialog is rendered via `NotificationCenter().notify_frame(...)`.
Multiple tracked efforts each get their own dialog; a `_displayed`
set on the controller prevents duplicate dialogs for the same effort.

---

## State Machine

`IdleNotifier` in `taskcoachlib/powermgt/idle.py` runs on `wx.EVT_IDLE`.

```
       (no efforts tracked)
              |
              v
        +-----------+   tracking starts    +-----------+
        | unbound   | -------------------> | AWAKE     |
        +-----------+                      +-----------+
              ^                              |       ^
              | tracking stops               |       |
              |                              v       |
              |                          (idle >= threshold)
              |                              |       |
              |                              v       |
              |                          +-----------+
              |                          | SLEEPING  |
              |                          +-----------+
                                             |
                                  (user returns: idle < threshold)
                                  -> wake(goneToSleep) fires
```

- The handler is **bound only while at least one effort is tracked**.
  `IdleController.__onTrackedChanged` calls `resume()` / `pause()` on
  the underlying `IdleNotifier`.
- `lastActivity` is recomputed on every EVT_IDLE tick as
  `time.time() - getIdleSeconds()`.
- `goneToSleep` is captured when the threshold is first crossed and
  passed to `wake()` so the dialog shows when the user actually
  stopped being active.

---

## Startup Logging

When the feature is enabled (`minidletime > 0`), `IdleController` logs a
one-shot summary at startup using the standard `log_step` utility with
prefix `[IDLE]`. The log proves which backend was selected and that a
real query returned a sensible value. No additional logging is emitted
during normal operation (state transitions, dialog button choices),
since the startup probe has already verified the path works.

Example output on a Debian LXDE/X11 box:

```
[22:50:43.277] [IDLE] Idle time notice enabled; threshold=4 min (240s)
[22:50:43.277] [IDLE] Probing idle backend on linux...
[22:50:43.287] [IDLE]   dbus_mutter: unavailable (DBusException: org.freedesktop.DBus.Error.ServiceUnknown: The name org.gnome.Mutter.IdleMonitor was not provided by any .service files)
[22:50:43.287] [IDLE]   dbus_screensaver: unavailable (DBusException: org.freedesktop.DBus.Error.UnknownMethod: Unknown method GetSessionIdleTime or interface org.freedesktop.ScreenSaver.)
[22:50:43.287] [IDLE]   wayland_ext_idle: unavailable (WAYLAND_DISPLAY not set)
[22:50:43.287] [IDLE]   x11_mit_screensaver: OK
[22:50:43.287] [IDLE] Selected backend: x11_mit_screensaver
[22:50:43.287] [IDLE] Test query returned idle=0.01s
```

Example output when the feature is disabled:

```
(no [IDLE] lines)
```

Example output when no backend is available (e.g. a Wayland session
where `python3-pywayland` is not installed):

```
[HH:MM:SS.xxx] [IDLE] Idle time notice enabled; threshold=4 min (240s)
[HH:MM:SS.xxx] [IDLE] Probing idle backend on linux...
[HH:MM:SS.xxx] [IDLE]   dbus_mutter: unavailable (...)
[HH:MM:SS.xxx] [IDLE]   dbus_screensaver: unavailable (...)
[HH:MM:SS.xxx] [IDLE]   wayland_ext_idle: unavailable (pywayland not installed: ModuleNotFoundError: No module named 'pywayland')
[HH:MM:SS.xxx] [IDLE]   x11_mit_screensaver: unavailable (MIT-SCREEN-SAVER extension not present)
[HH:MM:SS.xxx] [IDLE] WARNING: no backend available; idle-time notice will not function
```

The block appears during `MainWindow` construction, near the `[TRAY]`
block (it currently logs just before `[TRAY]` because the controller
is instantiated before the taskbar icon).

---

## Known Gaps

### `python3-pywayland` not installed

The `wayland_ext_idle` backend depends on the `pywayland` Python
package being importable. On Debian/Ubuntu the relevant package is
`python3-pywayland`; on Fedora it is `python3-pywayland`; on Arch
it is `python-pywayland`. If the import fails, the probe records
`pywayland not installed` and the chain falls through to
`x11_mit_screensaver` (which will also fail on Wayland-only
sessions), at which point the feature silently disables itself.

The protocol bindings themselves are vendored in
`taskcoachlib/thirdparty/pywayland_protocols/ext_idle_notify_v1/`
because Debian Trixie's `python3-pywayland` 0.4.18 only ships the
core `pywayland.protocol.wayland` module. Regeneration command is
documented in that package's `__init__.py`.

### Setting changes during a session

The startup probe runs once at `IdleController.__init__`. If the user
toggles `minidletime` from `0` to non-zero (or vice versa) at runtime
via Preferences, the probe is not re-run. The feature still functions
because `get_min_idle_time()` is consulted on every tick; only the
startup log is missing. Not currently considered a bug; a restart
re-runs the probe.

---

## File Reference

| File | Role |
|------|------|
| `taskcoachlib/powermgt/idle.py` | `IdleQuery` per platform (`LinuxIdleQuery`, `WindowsIdleQuery`, `MacIdleQuery`), plus the cross-platform `IdleNotifier` state machine. |
| `taskcoachlib/powermgt/__init__.py` | Imports the right `IdleNotifier` per platform. |
| `taskcoachlib/thirdparty/pywayland_protocols/ext_idle_notify_v1/` | Vendored pywayland scanner output for the `ext-idle-notify-v1` staging protocol. Imported by the `wayland_ext_idle` backend. |
| `taskcoachlib/gui/idlecontroller.py` | `IdleController` (subscribes to the effort tracker, forwards wake events to the dialog) and `WakeFromIdleFrame` (the notification UI). |
| `taskcoachlib/gui/mainwindow.py` | Instantiates `IdleController` during `MainWindow.__init__`. |
| `taskcoachlib/gui/dialog/preferences.py` | Adds the "Idle time notice" integer field to the Features tab. |
| `taskcoachlib/config/defaults.py` | Declares `feature.minidletime = 0`. |
| `taskcoachlib/meta/debug.py` | `log_step(*args, prefix="IDLE")` writer used for startup output. |

---

## See Also

- [LOGGING_GUIDE.md](LOGGING_GUIDE.md) - general logging conventions and prefix list.
- [AUI_WAYLAND_ISSUES.md](AUI_WAYLAND_ISSUES.md) - other Wayland-related platform notes.
