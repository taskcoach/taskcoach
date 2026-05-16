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
| **Linux/GTK (any X11 session: KDE Plasma 5/6, XFCE, LXDE, MATE, Cinnamon, i3, …)** | `x11_mit_screensaver` | `libXss.so.1` `XScreenSaverQueryInfo` via the X11 MIT-SCREEN-SAVER extension | The X server's real input idle. Probed before `dbus_screensaver` because KDE Plasma 6 returns a *bogus* `GetSessionIdleTime` value on X11 without raising. Works on any X11 session advertising the extension; correctly unavailable on Wayland. |
| **Linux/GTK (KDE Plasma 6, wlroots, COSMIC, Wayland)** | `ext_idle_notify` | `ext-idle-notify-v1` Wayland protocol via a **vendored** `pywayland` binding (`taskcoachlib/thirdparty/ext_idle_notify_v1`); a daemon thread holds an `ext_idle_notification_v1` armed at a 1 s timeout and tracks `idled`/`resumed` | Covers KWin (Plasma 5.27+, all Plasma 6), wlroots (Sway, Hyprland, niri, river, Wayfire) and COSMIC. Only attempted when `WAYLAND_DISPLAY` is set and core `pywayland` is importable; otherwise skipped silently. GNOME Mutter does not implement this protocol, but GNOME is already covered by `dbus_mutter`. |
| **Linux/GTK (KDE Plasma 5 fallback)** | `dbus_screensaver` | DBus call `org.freedesktop.ScreenSaver.GetSessionIdleTime` on `/ScreenSaver` | Last-resort fallback only. Plasma 5 implements it; on Plasma 6 it returns `NotSupported` (Wayland) or a bogus value (X11, already handled by `x11_mit_screensaver` winning first). |
| **Linux/GTK (other)** | none | none | If all four probes fail, a one-time warning is logged and the feature silently disables itself for the session. |

### Compositor Coverage Today

| Scenario | Covered by |
|----------|------------|
| GNOME on X11 or Wayland | `dbus_mutter` |
| KDE Plasma 5/6 on **X11** (and XFCE, LXDE, MATE, Cinnamon, i3, …) | `x11_mit_screensaver` |
| KDE Plasma 6 on **Wayland** | `ext_idle_notify` (was uncovered before) |
| wlroots compositors (Sway, Hyprland, niri, river, Wayfire) | `ext_idle_notify` (requires core `python3-pywayland`) |
| COSMIC (System76) | `ext_idle_notify` (requires core `python3-pywayland`) |
| KDE Plasma 5 on Wayland | `ext_idle_notify`, else `dbus_screensaver` fallback |

With the `ext_idle_notify` backend this covers effectively all
Linux desktop sessions. The only remaining uncovered case is a
Wayland session whose `pywayland` binding is absent **and** which
implements neither `org.gnome.Mutter.IdleMonitor` nor
`org.freedesktop.ScreenSaver.GetSessionIdleTime`; see
[Known Gaps](#known-gaps).

---

## Backend Probe Order (Linux)

`LinuxIdleQuery._initialize()` in `taskcoachlib/powermgt/idle.py` runs
lazily on the first `getIdleSeconds()` call. It probes:

1. `dbus_mutter` - attempts a real `GetIdletime()` call. Caches the
   interface on success.
2. `x11_mit_screensaver` - opens `DISPLAY`, checks for the
   `MIT-SCREEN-SAVER` extension via `XQueryExtension`, then allocates
   the screensaver info struct. Probed **before** `dbus_screensaver`
   on purpose: on an X11 session this reads the X server's real input
   idle directly. KDE Plasma 6 answers
   `org.freedesktop.ScreenSaver.GetSessionIdleTime` with a bogus
   non-zero value (it does *not* raise), so if `dbus_screensaver`
   were probed first it would be wrongly selected and the notice
   would fire constantly. Correctly fails on a Wayland session (no
   MIT-SCREEN-SAVER), falling through to the next probe.
3. `ext_idle_notify` - skipped immediately unless `WAYLAND_DISPLAY`
   is set and the vendored binding imports. Connects to the Wayland
   display, binds `ext_idle_notifier_v1` + `wl_seat`, creates an
   `ext_idle_notification_v1` armed at a 1 s timeout, and starts a
   daemon thread that dispatches `idled`/`resumed` events. Success
   means the globals were advertised and the notification was
   created without a protocol error. The protocol binding is
   **vendored** at `taskcoachlib/thirdparty/ext_idle_notify_v1`
   (generated by `pywayland-scanner`), because distribution
   `python3-pywayland` ships only the core `wayland` protocol; the
   runtime requirement is therefore just core `pywayland`.
4. `dbus_screensaver` - attempts a real `GetSessionIdleTime()` call.
   Last-resort fallback for the few Plasma 5 setups that depend on
   it. Fails on Plasma 6 with `NotSupported` (Wayland) or returns a
   bogus value (X11, already handled by step 2 winning first).

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
[22:50:43.287] [IDLE]   ext_idle_notify: unavailable (no WAYLAND_DISPLAY (not a Wayland session))
[22:50:43.287] [IDLE]   x11_mit_screensaver: OK
[22:50:43.287] [IDLE] Selected backend: x11_mit_screensaver
[22:50:43.287] [IDLE] Test query returned idle=0.01s
```

Example output on a KDE Plasma 6 Wayland box with `python3-pywayland`
installed (the scenario this backend was added for):

```
[16:15:29.901] [IDLE] Idle time notice enabled; threshold=1 min (60s)
[16:15:29.901] [IDLE] Probing idle backend on linux...
[16:15:30.019] [IDLE]   dbus_mutter: unavailable (DBusException: org.freedesktop.DBus.Error.ServiceUnknown: The name org.gnome.Mutter.IdleMonitor was not provided by any .service files)
[16:15:30.019] [IDLE]   dbus_screensaver: unavailable (DBusException: org.freedesktop.DBus.Error.NotSupported: GetSessionIdleTime is not supported on this platform)
[16:15:30.030] [IDLE]   ext_idle_notify: OK
[16:15:30.030] [IDLE] Selected backend: ext_idle_notify
[16:15:30.030] [IDLE] Test query returned idle=0.00s
```

Example output when the feature is disabled:

```
(no [IDLE] lines)
```

Example output when no backend is available (e.g. a wlroots Wayland
session today):

```
[HH:MM:SS.xxx] [IDLE] Idle time notice enabled; threshold=4 min (240s)
[HH:MM:SS.xxx] [IDLE] Probing idle backend on linux...
[HH:MM:SS.xxx] [IDLE]   dbus_mutter: unavailable (...)
[HH:MM:SS.xxx] [IDLE]   dbus_screensaver: unavailable (...)
[HH:MM:SS.xxx] [IDLE]   x11_mit_screensaver: unavailable (MIT-SCREEN-SAVER extension not present)
[HH:MM:SS.xxx] [IDLE] WARNING: no backend available; idle-time notice will not function
```

The block appears during `MainWindow` construction, near the `[TRAY]`
block (it currently logs just before `[TRAY]` because the controller
is instantiated before the taskbar icon).

---

## Known Gaps

### Wayland session without core `pywayland`

The `ext_idle_notify` backend speaks
[`ext-idle-notify-v1`](https://wayland.app/protocols/ext-idle-notify-v1).
Distribution `python3-pywayland` ships **only the core `wayland`
protocol** by design, so `pywayland.protocol.ext_idle_notify_v1`
never exists at runtime. The protocol binding is therefore
**vendored** in the tree (`taskcoachlib/thirdparty/ext_idle_notify_v1`,
generated by `pywayland-scanner`; see that directory's README). The
only runtime requirement is **core `pywayland`** itself (for
`pywayland.client`, `pywayland.protocol_core`,
`pywayland.protocol.wayland`). Like `import dbus`, the import is
guarded, so its absence only skips this one probe.

`python3-pywayland` is packaged on every distribution that ships a
Plasma 6 desktop (Debian 13 Trixie, Fedora 39+, Arch, Ubuntu 25.10+),
so the affected users have it available. The residual gap is a
Wayland session that has **no** core `pywayland` installed **and**
implements neither `org.gnome.Mutter.IdleMonitor` nor a working
`org.freedesktop.ScreenSaver.GetSessionIdleTime`. There the feature
silently disables itself; installing `python3-pywayland` resolves it
without a Task Coach upgrade (the binding is already vendored).

GNOME Mutter does not implement `ext-idle-notify-v1` as of early
2026, but GNOME is covered by `dbus_mutter`, which is probed first.

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
| `taskcoachlib/gui/idlecontroller.py` | `IdleController` (subscribes to the effort tracker, forwards wake events to the dialog) and `WakeFromIdleFrame` (the notification UI). |
| `taskcoachlib/gui/mainwindow.py` | Instantiates `IdleController` during `MainWindow.__init__`. |
| `taskcoachlib/gui/dialog/preferences.py` | Adds the "Idle time notice" integer field to the Features tab. |
| `taskcoachlib/config/defaults.py` | Declares `feature.minidletime = 0`. |
| `taskcoachlib/meta/debug.py` | `log_step(*args, prefix="IDLE")` writer used for startup output. |

---

## Optional Bindings

Two idle backends rely on Python bindings that Task Coach declares
only as **optional** dependencies (never hard, never bundled),
exactly like the spell-check dictionaries:

| Backend | Binding | How it is declared |
|---------|---------|--------------------|
| `dbus_mutter`, `dbus_screensaver` | `python3-dbus` | `optdepends` (Arch), `Recommends:` (Fedora `.spec`), and injected into `Recommends:` per codename by the `build-deb.yml` CI step for all Debian/Ubuntu targets. Guarded `import dbus`. |
| `ext_idle_notify` | `python3-pywayland` | `optdepends` (Arch), `Recommends:` (Fedora `.spec`), and injected into `Recommends:` by `build-deb.yml` only for Plasma 6 codenames that package it (currently `trixie`). Guarded `import pywayland`. |

Note the distinction: the C library `libwayland-client.so.0` **is**
guaranteed present (it is a hard dependency of `libgtk-3-0`, which
Task Coach pulls in via wxPython), but the Python *binding*
`pywayland` is a separate package and is not automatically
installed. Same for `libdbus` versus `python3-dbus`. Both bindings
degrade silently when absent. See
[PACKAGING.md](PACKAGING.md) for the per-distro picture.

---

## See Also

- [LOGGING_GUIDE.md](LOGGING_GUIDE.md) - general logging conventions and prefix list.
- [AUI_WAYLAND_ISSUES.md](AUI_WAYLAND_ISSUES.md) - other Wayland-related platform notes.
