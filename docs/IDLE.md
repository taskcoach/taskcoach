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
| **Windows** | `win32_GetLastInputInfo` | `user32.GetLastInputInfo` + `kernel32.GetTickCount` | Single backend, no fallback. Works on all supported Windows versions. Both are unsigned 32-bit millisecond counts that wrap after 49.7 days of uptime; the difference is taken modulo 2^32. |
| **macOS** | `iokit_HIDIdleTime` | IOKit `IORegistryEntryCreateCFProperty` on `IOHIDSystem`, property `HIDIdleTime` | Pure-ctypes; loads `IOKit.framework` and `CoreFoundation.framework`. Replaces the pre-2026 `_idle.so` C extension. |
| **Linux/GTK (GNOME, X11 or Wayland)** | `dbus_mutter` | DBus call `org.gnome.Mutter.IdleMonitor.GetIdletime` on `/org/gnome/Mutter/IdleMonitor/Core`, through PyGObject's Gio | Returns milliseconds. Works for GNOME Shell sessions including Wayland. Each reading is addressed to the name's current owner, so a restarted GNOME Shell keeps answering, and waits at most 1 s (`_DBUS_TIMEOUT_MS`); a failed reading counts as not idle. |
| **Linux/GTK (any X11 session: KDE Plasma 5/6, XFCE, LXDE, MATE, Cinnamon, i3, …)** | `x11_mit_screensaver` | `libXss.so.1` `XScreenSaverQueryInfo` via the X11 MIT-SCREEN-SAVER extension | The X server's real input idle. Works on any X11 session advertising the extension; unavailable on Wayland, where Xwayland disables the extension. |
| **Linux/GTK (KDE Plasma 5.27+, wlroots, COSMIC, Wayland)** | `ext_idle_notify` | `ext-idle-notify-v1` Wayland protocol, asked through `libwayland-client` with ctypes (`powermgt/wayland_idle.py`); an `ext_idle_notification_v1` armed at a 1 s timeout reports `idled`/`resumed`, read on each poll; input only where the compositor offers version 2 ([Idle inhibitors](#idle-inhibitors-on-version-1-compositors)) | Covers KWin (Plasma 5.27+, all Plasma 6), wlroots (Sway, Hyprland, niri, river, Wayfire, labwc) and COSMIC. `libwayland-client` comes with GTK, so nothing more is installed. Only attempted when `WAYLAND_DISPLAY` is set. GNOME Mutter does not implement this protocol, but GNOME is already covered by `dbus_mutter`. |
| **Linux/GTK (other)** | none | none | If all three probes fail, a one-time warning is logged and the feature silently disables itself for the session. |

### Compositor Coverage Today

| Scenario | Covered by |
|----------|------------|
| GNOME on X11 or Wayland | `dbus_mutter` |
| KDE Plasma 5/6 on **X11** (and XFCE, LXDE, MATE, Cinnamon, i3, …) | `x11_mit_screensaver` |
| KDE Plasma 5.27 and 6 on **Wayland** (Kubuntu 24.04 to 26.04) | `ext_idle_notify` |
| wlroots compositors (Sway, Hyprland, niri, river, Wayfire, labwc) | `ext_idle_notify` |
| COSMIC (System76) | `ext_idle_notify` |
| KDE Plasma 5.24 on Wayland (Kubuntu 22.04), Cinnamon on Wayland | none |
| The Flatpak on any Wayland desktop but GNOME | none: no Wayland socket ([Known Gaps](#known-gaps)) |

Researched 2026-10-06 from the desktops' sources
([DEPENDENCIES.md](DEPENDENCIES.md#dbus-python-to-do-92)): Cinnamon's
Muffin names its monitor `org.cinnamon.Muffin.IdleMonitor`, so
Cinnamon on Wayland has none. A fourth probe, `dbus_screensaver`
(`org.freedesktop.ScreenSaver.GetSessionIdleTime`), was removed then,
**ruled by designer**: reached only when the others failed, it gave
no true reading on any desktop (0 on Plasma 5.24 Wayland, so never
idle; errors elsewhere).

Checked again 2026-10-25 from the sources, for KDE Plasma on Wayland:

- Xwayland turns MIT-SCREEN-SAVER off when it runs rootless, as
  every compositor starts it (xserver commit `5c20e4b8`, Xwayland
  21.1); Xwayland 24.1 lists no such extension. `x11_mit_screensaver`
  therefore fails on Wayland rather than reading X11 input only.
- KDE's `GetSessionIdleTime` answers
  `org.freedesktop.DBus.Error.NotSupported` on Wayland since Plasma
  5.27 (kscreenlocker commit `a4244d3c`); KDE has no other D-Bus
  reading of the idle time there.
- KWin offers `ext-idle-notify-v1` since Plasma 5.27, at version 2
  since 6.4.

So on KDE Plasma Wayland `ext_idle_notify` is the only reading.

---

## Backend Probe Order (Linux)

`LinuxIdleQuery._initialize()` in `taskcoachlib/powermgt/idle.py` runs
lazily on the first `get_idle_seconds()` call. It probes:

1. `dbus_mutter` - attempts a real `GetIdletime()` call over the
   session bus connection (`Gio.bus_get_sync()`), kept on success.
2. `x11_mit_screensaver` - opens `DISPLAY`, checks for the
   `MIT-SCREEN-SAVER` extension via `XQueryExtension`, then allocates
   the screensaver info struct: the X server's real input idle. Fails
   on a Wayland session (Xwayland disables the extension), falling
   through to the next probe.
3. `ext_idle_notify` - skipped immediately unless `WAYLAND_DISPLAY`
   is set. Connects to the compositor, binds `wl_seat` (version 1)
   and `ext_idle_notifier_v1` (version 2 where offered, else 1), asks
   for an `ext_idle_notification_v1` armed at a 1 s timeout (version
   2's `get_input_idle_notification`, else `get_idle_notification`;
   the probe log says which), whose `idled`/`resumed` events each poll
   reads without waiting. Success means the globals were advertised
   and the notification was created without a protocol error. A lost
   connection logs `Wayland compositor connection lost: not idle` and
   reads not idle from then on.

   `powermgt/wayland_idle.py` speaks the protocol through
   `libwayland-client.so.0` with ctypes: the protocol's two
   interfaces are written out as `wayland-scanner` would generate
   them, and requests go through `wl_proxy_marshal_array_flags`
   (Wayland 1.20+, Ubuntu 22.04 and later). `IdleQueryTest` checks
   those tables against the installed protocol files, since a
   mistake there crashes instead of raising.

Each attempt records `(method_name, success, detail)` in
`self._probe_log`. The first success wins; later methods are not
probed. The selected method is exposed via `get_backend_name()`.

The probe is triggered explicitly at startup by `IdleController`
when the feature is enabled, so subsequent runtime calls hit the
already-selected backend with no extra cost. With the feature
disabled no backend is probed or queried.

---

## Setting

| Setting | Section | Default | Units | Effect |
|---------|---------|---------|-------|--------|
| `minidletime` | `feature` | `0` | minutes | Threshold for going idle. `0` disables the feature. |

Defined in `taskcoachlib/config/defaults.py` (section `feature`).
Editable in Preferences > Features as "Idle time notice".

`IdleController.get_min_idle_time()` returns the value times 60
(seconds) and is read on every poll. `IdleController` also observes the
setting (Publisher event `feature.minidletime`), so a change in
Preferences starts or stops polling at once.

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

`IdleNotifier` in `taskcoachlib/powermgt/idle.py` polls on the
GlobalTimer `timer.second` tick (see [SCHEDULERS.md](SCHEDULERS.md)).

```
       (no efforts tracked, or threshold 0)
              |
              v
        +-----------+   tracking starts    +-----------+
        | stopped   | -------------------> | AWAKE     |
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

- It **polls only while at least one effort is tracked, the threshold
  is above 0 and the computer is not suspended**.
  `IdleController._on_tracked_changed` calls `resume()` / `pause()`,
  and a threshold change goes through it too; the main window's
  Publisher events `powermgt.off` / `powermgt.on` (Windows only) call
  `poweroff()` / `poweron()`.
- `_last_activity` is recomputed on every poll as
  `time.time() - get_idle_seconds()`. It is also checked before the
  query, so a gap between polls (a suspend, which idle counters may
  not include) counts as idle.
- `_gone_to_sleep` is captured when the threshold is first crossed and
  passed to `wake()` so the dialog shows when the user actually
  stopped being active. Return is detected on the next tick, within
  about a second.

---

## Startup Logging

When the feature is enabled (`minidletime > 0`), `IdleController` logs a
one-shot summary at startup (or when it is first turned on) using the
standard `log_step` utility with
prefix `[IDLE]`. The log proves which backend was selected and that a
real query returned a sensible value. At runtime it logs
`Polling started; threshold=<n>s` and `Polling stopped`,
`Idle threshold reached while tracking effort` on sleep and
`Wake from idle; idle since <time>` on wake.

Example output on a Debian LXDE/X11 box:

```
[HH:MM:SS.xxx] [IDLE] Idle time notice enabled; threshold=4 min (240s)
[HH:MM:SS.xxx] [IDLE] Probing idle backend on linux...
[HH:MM:SS.xxx] [IDLE]   dbus_mutter: unavailable (Error: g-dbus-error-quark: GDBus.Error:org.freedesktop.DBus.Error.ServiceUnknown: The name org.gnome.Mutter.IdleMonitor was not provided by any .service files (2))
[HH:MM:SS.xxx] [IDLE]   x11_mit_screensaver: OK
[HH:MM:SS.xxx] [IDLE] Selected backend: x11_mit_screensaver
[HH:MM:SS.xxx] [IDLE] Test query returned idle=0.01s
```

Example output on a KDE Plasma Wayland session:

```
[HH:MM:SS.xxx] [IDLE] Idle time notice enabled; threshold=1 min (60s)
[HH:MM:SS.xxx] [IDLE] Probing idle backend on linux...
[HH:MM:SS.xxx] [IDLE]   dbus_mutter: unavailable (...)
[HH:MM:SS.xxx] [IDLE]   x11_mit_screensaver: unavailable (MIT-SCREEN-SAVER extension not present)
[HH:MM:SS.xxx] [IDLE]   ext_idle_notify: OK (version 2, input only)
[HH:MM:SS.xxx] [IDLE] Selected backend: ext_idle_notify
[HH:MM:SS.xxx] [IDLE] Test query returned idle=0.00s
```

Example output when the feature is disabled:

```
(no [IDLE] lines)
```

Example output when no backend is available (e.g. Cinnamon on
Wayland, or the Flatpak on KDE Plasma Wayland):

```
[HH:MM:SS.xxx] [IDLE] Idle time notice enabled; threshold=4 min (240s)
[HH:MM:SS.xxx] [IDLE] Probing idle backend on linux...
[HH:MM:SS.xxx] [IDLE]   dbus_mutter: unavailable (...)
[HH:MM:SS.xxx] [IDLE]   x11_mit_screensaver: unavailable (MIT-SCREEN-SAVER extension not present)
[HH:MM:SS.xxx] [IDLE]   ext_idle_notify: unavailable (...)
[HH:MM:SS.xxx] [IDLE] WARNING: no backend available; idle-time notice will not function
```

The block appears during `MainWindow` construction, near the `[TRAY]`
block (it currently logs just before `[TRAY]` because the controller
is instantiated before the taskbar icon).

---

## Known Gaps

### The Flatpak on Wayland desktops other than GNOME

The Flatpak has only the X11 socket (`--socket=x11`, with
`GDK_BACKEND=x11`): Flatpak then hides the compositor's socket and
unsets `WAYLAND_DISPLAY`, so `ext_idle_notify` is not tried, and
Xwayland has no MIT-SCREEN-SAVER. On KDE Plasma, wlroots desktops and
COSMIC on Wayland the Flatpak has no idle reading. `--socket=wayland`
beside `--socket=x11` would give it one, the window staying on X11,
but Flathub's linter refuses both sockets together
(`finish-args-contains-both-x11-and-wayland`, [FLATPAK.md](FLATPAK.md)).

### Idle inhibitors on version 1 compositors

`ext_idle_notify` asks for version 2's `get_input_idle_notification`
where the compositor offers it (KWin 6.4+, wlroots 0.20): input only,
as the readings on GNOME, X11, Windows and macOS. Where only version 1
is offered (KWin 5.27 to 6.3, as on Kubuntu 24.04; wlroots 0.18), its
`get_idle_notification` also counts idle inhibitors: while a shown
window holds a `zwp_idle_inhibitor` (a video player, a browser playing
a video), KWin's idle timer stops, so time away is not noticed, and a
seat already idle sends no `resumed` until the inhibitor ends
(`src/idledetector.cpp` in KWin 6.6).

### Setting changes during a session

The summary is logged once, the first time the feature is on: at
startup, or when Preferences turns `minidletime` from `0` to a
threshold during the session. Later threshold changes log only
`Polling started; threshold=<n>s`. Before 2026-10-02 a feature turned
on during the session logged no summary until a restart (P107 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues)).

---

## File Reference

| File | Role |
|------|------|
| `taskcoachlib/powermgt/idle.py` | `IdleQuery` per platform (`LinuxIdleQuery`, `WindowsIdleQuery`, `MacIdleQuery`), plus the cross-platform `IdleNotifier` state machine. |
| `taskcoachlib/powermgt/wayland_idle.py` | The `ext-idle-notify-v1` client of `libwayland-client`, through ctypes. |
| `taskcoachlib/powermgt/__init__.py` | Imports the right `IdleNotifier` per platform. |
| `taskcoachlib/gui/idlecontroller.py` | `IdleController` (subscribes to the effort tracker, forwards wake events to the dialog) and `WakeFromIdleFrame` (the notification UI). |
| `taskcoachlib/gui/mainwindow.py` | Instantiates `IdleController` during `MainWindow.__init__`. |
| `taskcoachlib/gui/dialog/preferences.py` | Adds the "Idle time notice" integer field to the Features tab. |
| `taskcoachlib/config/defaults.py` | Declares `feature.minidletime = 0`. |
| `taskcoachlib/meta/debug.py` | `log_step(*args, prefix="IDLE")` writer used for startup output. |

---

## Libraries

No idle reading needs a package of its own:

| Backend | Library | Where it comes from |
|---------|---------|---------------------|
| `dbus_mutter` | PyGObject's Gio | a dependency of the deb, rpm and Arch packages, in the Flatpak's runtime (not in the AppImage); `python3-dbus` until 2026-10-06 ([DEPENDENCIES.md](DEPENDENCIES.md#dbus-python-to-do-92)) |
| `x11_mit_screensaver` | `libXss.so.1` | a dependency of the packages (`libxss1`) |
| `ext_idle_notify` | `libwayland-client.so.0` | a dependency of GTK 3, so of wxPython; `python3-pywayland` until 2026-10-25 ([DEPENDENCIES.md](DEPENDENCIES.md#pywayland-to-do-88)) |

---

## See Also

- [LOGGING_GUIDE.md](LOGGING_GUIDE.md) - general logging conventions and prefix list.
- [WAYLAND_ISSUES.md](WAYLAND_ISSUES.md) - other Wayland-related platform notes.
