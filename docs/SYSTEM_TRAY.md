# System Tray Icon Implementation

This document describes the system tray (notification area) icon implementation in Task Coach across different platforms and desktop environments.

## Table of Contents

- [TODO](#todo)
- [Overview](#overview)
- [Implementation Architecture](#implementation-architecture)
- [Platform Behavior Matrix](#platform-behavior-matrix)
- [Windows Quit-from-Tray Safety](#windows-quit-from-tray-safety)
- [Tested Configurations](#tested-configurations)
- [References](#references)
- [Why AppIndicator on Linux?](#why-appindicator-on-linux)
- [Menu Contents](#menu-contents)
- [Dependencies](#dependencies)
- [Icon Animation](#icon-animation)
- [Debugging](#debugging)
- [Files](#files)
- [Code Duplication](#code-duplication)
- [Why a Separate tray/hicolor Theme?](#why-a-separate-trayhicolor-theme)
- [See Also](#see-also)

---

## TODO

1. **Extract base class.** `TaskBarIcon` and `AppIndicatorTaskBarIcon` duplicate
   ~100 lines of identical logic (see [Code Duplication](#code-duplication)).
   Extract shared logic into `TaskBarIconBase(patterns.Observer)`. Subclasses
   override only `_set_icon()` and menu handling. `TaskBarIcon` additionally
   inherits from `wx.adv.TaskBarIcon`.

---

## Overview

Task Coach displays a system tray icon that allows users to:
- Show/hide the main window
- Access common actions (new task, new effort, etc.)
- Start/stop effort tracking
- See tracking status via icon animation

## Implementation Architecture

### Platform Detection Flow

```
create_taskbar_icon(mainwindow, taskList, settings)
  │
  ├─ Linux/GTK + AppIndicator available → AppIndicatorTaskBarIcon
  │   .__init__()
  │       → indicator.set_icon_theme_path(.../icons/tray)
  │   .__setIcon()
  │       → self.__indicator.set_icon_full("taskcoach-app", self.__tooltipText)
  │
  ├─ Windows / Mac → TaskBarIcon (wx.adv.TaskBarIcon)
  │   .__setIcon()
  │       ├─ Mac   → size = TRAY_ICON_SIZE_MACOS (128)
  │       └─ Other → size = LIST_ICON_SIZE (16)
  │       → icon = icon_catalog.get_wx_icon(icon_id, size)
  │       → self.SetIcon(icon, self.__tooltipText)
  │
  └─ Fallback → tries AppIndicator, then wx anyway
```

### Icon blinking

When effort tracking is active, the tray icon blinks between `taskcoach-clock`
and `taskcoach-timer` each second (AppIndicator), or `nuvola_apps_clock` and
`nuvola_apps_ktimer` (wx.adv.TaskBarIcon). Both icons need tray-appropriate sizes.
Size constants: `TRAY_ICON_SIZE_MACOS` (128) and `LIST_ICON_SIZE` (16) in
`taskbaricon.py`.

### Classes

| Class | File | Purpose |
|-------|------|---------|
| `TaskBarIcon` | `taskbaricon.py` | wx.adv.TaskBarIcon wrapper for Windows/macOS |
| `AppIndicatorTaskBarIcon` | `taskbaricon.py` | AppIndicator wrapper for Linux |
| `AppIndicatorIcon` | `appindicator.py` | Low-level AppIndicator/GTK bindings |
| `TaskBarMenu` | `menu.py` | wx.Menu for Windows/macOS right-click |

## Platform Behavior Matrix

| OS | Distro | Desktop | Session | Implementation | Left-Click | Right-Click | Notes |
|----|--------|---------|---------|----------------|------------|-------------|-------|
| Windows | — | — | — | wx.adv.TaskBarIcon | Show/hide | Popup menu | Full support |
| macOS | — | — | — | wx.adv.TaskBarIcon | Show/hide | Popup menu | Full support |
| Linux | — | GNOME | X11 | AppIndicator | Menu | Menu | Requires extension [1] |
| Linux | — | GNOME | Wayland | AppIndicator | Menu | Menu | Requires extension [1] |
| Linux | Ubuntu | GNOME | X11 | AppIndicator | Menu | Menu | Extension pre-installed |
| Linux | Ubuntu | GNOME | Wayland | AppIndicator | Menu | Menu | Extension pre-installed |
| Linux | — | KDE Plasma | X11 | AppIndicator | Menu | Conflict [2] | Use left-click |
| Linux | — | KDE Plasma | Wayland | AppIndicator | Menu | Menu | |
| Linux | — | XFCE | X11 | AppIndicator | Menu | Menu | wx may work [3] |
| Linux | — | LXDE | X11 | AppIndicator | Menu | Menu | wx right-click broken [4] |
| Linux | — | LXQt | X11 | AppIndicator | Menu | Menu | |
| Linux | — | LXQt | Wayland | AppIndicator | Menu | Menu | |
| Linux | — | MATE | X11 | AppIndicator | Menu | Menu | |
| Linux | — | Cinnamon | X11 | AppIndicator | Menu | Menu | wx may work [3] |

**Notes:**

[1] **GNOME Extension Required**: GNOME Shell removed built-in system tray support. Install the [AppIndicator Support](https://extensions.gnome.org/extension/615/appindicator-support/) extension. Ubuntu pre-installs this extension, so Ubuntu users don't need to install it manually.

[2] **KDE X11 Right-Click Issues**: Known KDE bugs affect right-click behavior on X11. [Bug 449870](https://bugs.kde.org/show_bug.cgi?id=449870) reports tray icons not reacting to right-click, and [Bug 409768](https://bugs.kde.org/show_bug.cgi?id=409768) reports conflicts where right-clicking causes subsequent clicks to misbehave. Users should use left-click instead.

[3] **wx.adv.TaskBarIcon may work**: According to [wxWidgets documentation](https://wxpython.org/Phoenix/docs/html/wx.adv.TaskBarIcon.html) and user reports, XFCE and Cinnamon support the freedesktop.org System Tray Protocol and wx.adv.TaskBarIcon has been confirmed working on these desktops. Currently using AppIndicator for consistency across all Linux.

[4] **LXDE wx broken**: Confirmed that wx.adv.TaskBarIcon does not receive right-click events on LXDE, even though `IsAvailable()` returns True. Left-click works but right-click events are never delivered.

## Windows Quit-from-Tray Safety

### The Problem

On Windows, `PopupMenu()` runs a **modal event loop** — it blocks until the
user dismisses the menu. When the user clicks Quit from the tray menu:

1. `PopupMenu()` is still active (modal, blocking)
2. `FileQuit.do_command()` calls `mainwindow.Close(force=True)`
3. `onClose()` calls `quitApplication()` which destroys the tray icon
4. `PopupMenu()` returns to a destroyed object → **segfault**

### The Fix

`FileQuit.do_command()` uses `wx.CallAfter()` to defer the `Close()` call:

```python
def do_command(self, event):
    wx.CallAfter(self.main_window().Close, force=True)
```

This lets `PopupMenu()` return cleanly before `quitApplication()` tears
down the tray icon. The AppIndicator implementation already uses this
pattern (line 546: `lambda w: wx.CallAfter(self.__window.Close)`).

### Best Practices (from wxPython docs)

The wxPython documentation recommends:

1. **Override `CreatePopupMenu()`** instead of calling `PopupMenu()` manually —
   wx handles the menu lifecycle and destroys it after the user dismisses it.
2. **Or override `GetPopupMenu()`** to reuse the same menu object without
   automatic destruction.
3. **`Destroy()` on TaskBarIcon schedules delayed destruction** for the next
   event loop iteration, but this doesn't help when `quitApplication()`
   immediately tears everything down in the same call chain.
4. **Always defer quit actions with `wx.CallAfter`** when triggered from a
   tray popup menu, so the modal menu loop exits first.

Task Coach uses manual `PopupMenu()` + `wx.CallAfter` for the quit action,
which is safe and avoids the need to restructure the menu system.

## Tested Configurations

| OS | Distro | Desktop | Session | wx.adv.TaskBarIcon | AppIndicator |
|----|--------|---------|---------|-------------------|--------------|
| Windows | — | — | — | Full support | N/A |
| macOS | — | — | — | Full support | N/A |
| Linux | Debian | LXDE | X11 | Left-click only | Full support |
| Linux | Kubuntu | KDE Plasma | X11 | Left-click only | Left-click only (right conflict) |
| Linux | Kubuntu | KDE Plasma | Wayland | N/A (no XEmbed) | Full support |

## References

- [wxPython TaskBarIcon Documentation](https://wxpython.org/Phoenix/docs/html/wx.adv.TaskBarIcon.html)
- [GitHub Issue #2080 - TaskBarIcon click events not firing](https://github.com/wxWidgets/Phoenix/issues/2080)
- [GitHub Issue #754 - TaskBarIcon not working in Ubuntu](https://github.com/wxWidgets/Phoenix/issues/754)

## Why AppIndicator on Linux?

### The Problem with wx.adv.TaskBarIcon on Linux

`wx.adv.TaskBarIcon` uses the X11 XEmbed protocol for system tray icons. Testing revealed:

1. **Right-click events not received**: On LXDE, KDE, and potentially other desktops, `EVT_TASKBAR_RIGHT_UP` events are never delivered to the application, even though the icon appears and left-click works.

2. **Wayland incompatibility**: XEmbed doesn't exist on Wayland, so `wx.adv.TaskBarIcon` cannot work at all.

3. **Inconsistent behavior**: Different desktop environments handle the XEmbed tray differently, leading to unpredictable behavior.

### The AppIndicator Solution

AppIndicator (libayatana-appindicator) implements the StatusNotifierItem (SNI) protocol:

- **Works on Wayland**: SNI is D-Bus based, no X11 dependency
- **Works on X11**: Has XEmbed fallback for older trays
- **Consistent menu behavior**: Menu always works via left-click
- **Modern standard**: Adopted by KDE, Ubuntu, and most modern desktops

### Why No Left-Click/Right-Click Differentiation?

**This is a limitation of the SNI protocol design, not Wayland itself.**

The StatusNotifierItem (SNI) protocol that AppIndicator implements is **menu-centric by design**. In the SNI specification, clicking the tray icon shows the menu - there is no concept of separate left-click and right-click actions in the protocol.

The chain of causation:

1. **wx.adv.TaskBarIcon** uses the **XEmbed** protocol (X11-only) which supports click differentiation
2. **XEmbed doesn't exist on Wayland** → wx.adv.TaskBarIcon cannot work on Wayland at all
3. **AppIndicator** (using SNI) works on both X11 and Wayland, but SNI has no click differentiation
4. We must use AppIndicator on Wayland, and for consistency use it on all Linux

So while Wayland forces us to use AppIndicator (since XEmbed isn't available), the loss of click differentiation is due to the SNI protocol's design philosophy, not a Wayland restriction per se.

### Trade-offs

| Feature | wx.adv.TaskBarIcon | AppIndicator |
|---------|-------------------|--------------|
| Left-click action | Custom (show/hide) | Shows menu |
| Right-click action | Shows menu | Shows menu (or conflict on KDE X11) |
| Wayland support | No | Yes |
| X11 support | Partial* | Yes |
| Menu updates | Dynamic | Rebuild on change |

*Right-click broken on many desktops

### Window Show/Hide on Wayland

#### What Wayland actually tells the client

`xdg_toplevel.configure` reports a `states` array on every change,
including compositor/WM-initiated ones: `maximized`, `fullscreen`,
`activated` (focus), `resizing`, `tiled_*`, `suspended`, and
`constrained_*`. So **maximize, fullscreen and focus are knowable**
even when the WM triggers them.

There is **no `minimized` state**. The xdg-shell spec says verbatim
of `set_minimized`: *"Request that the compositor minimize your
surface. There is no way to know if the surface is currently
minimized, nor is there any way to unset minimization on this
surface."* It is a one-way client to compositor request with zero
feedback. So **no Wayland client of any toolkit can detect a
WM-initiated minimize via core xdg-shell** - this is the protocol,
not a Task Coach or GTK bug (KeePassXC #6502 and others hit the same
wall). The only indirect hints are `wl_surface.frame` callbacks
stopping, or the newer `xdg_toplevel.suspended` state, both of which
mean "not currently being painted / not visible" (occlusion, screen
off, alt-tab), which is coarser than and not equivalent to
"minimized" - and GTK3 does not surface either.

Toolkit angle: GTK3 (frozen at 3.24) never sets
`GDK_WINDOW_STATE_ICONIFIED` on Wayland and predates `suspended`;
GTK4 does expose `GDK_TOPLEVEL_STATE_MINIMIZED` /
`GDK_TOPLEVEL_STATE_SUSPENDED`. wxPython 4.2 is wxGTK-on-GTK3, so
`IsIconized()` is permanently False on Wayland and `IsActive()` /
`IsShown()` are unreliable there.

#### Why the old `IsActive()` heuristic was wrong

The previous code treated `not IsActive()` as "Wayland minimized" and
did `Hide()+Show()`. But the tray Show/Hide is driven by the GTK menu
item, and opening that menu **deactivates the main window**, so
`IsActive()` is False whenever the callback runs. Execution therefore
hit the `not IsActive()` branch and did `Hide()+Show()` - hiding then
instantly re-showing the window. Net effect: minimize appeared to do
nothing. That heuristic *was* the reported "appindicator minimize
does not work" bug.

#### Correct design for the tray toggle

For the tray "Show/Hide", Task Coach *initiates* the visibility
change, so it must not query unreliable window state at all. Track
intended visibility ourselves and toggle deterministically: if
believed-shown -> `Hide()`; if believed-hidden -> `Show()` +
`Raise()`. (`Raise()` / `gtk_window_present()` still needs a valid
`xdg_activation_v1` token to actually focus-raise; tray actions
arrive over D-Bus with no input serial, so raise is best-effort -
KDE's SNI host passes an activation token in some cases, but it is
not guaranteed. This is a Wayland-wide constraint, see
[KDE - On Window Activation](https://planet.kde.org/kai-uwe-broulik-2025-08-04-on-window-activation/).)

#### Out-of-band detection (the SNI-analogous channel)

Detecting a *WM-initiated* minimize (e.g. the titlebar minimize
button) is impossible via xdg-shell, but it *is* possible out-of-band
via window-management protocols, exactly as SNI is an out-of-band
D-Bus channel for the tray icon:

- **KDE: `org_kde_plasma_window_management`** - exposes an explicit
  `minimized` state per toplevel plus a state-changed event. This is
  what the Plasma taskbar uses.
- **wlroots: `wlr-foreign-toplevel-management-unstable-v1` +
  `ext-foreign-toplevel-list-v1`** - enumerate toplevels, read/track
  `minimized`, request (un)minimize.

Real "minimize to tray on Wayland" tools confirm this: `kwin-minimize2tray`
and `WKDocker` work via a **KWin script** (compositor-side, where
state is fully known) plus a helper; `KDocker` is X11-only and does
not support Wayland.

For Task Coach this would mean the same pattern as the idle
`ext-idle-notify-v1` backend: optional `pywayland` + a vendored
`plasma-window-management` binding, opening a side Wayland connection
and matching our own toplevel by `app_id`/title. It is KDE-specific
(GNOME implements none of these; wlroots needs the `wlr`/`ext`
variant), non-trivial, and only needed for the titlebar-minimize ->
tray path; the tray Show/Hide toggle needs none of it.

References: [xdg-shell protocol](https://wayland.app/protocols/xdg-shell),
[KDE plasma-window-management](https://wayland.app/protocols/kde-plasma-window-management),
[wlr-foreign-toplevel-management](https://wayland.app/protocols/wlr-foreign-toplevel-management-unstable-v1),
[kwin-minimize2tray](https://github.com/luisbocanegra/kwin-minimize2tray),
[KeePassXC #6502](https://github.com/keepassxreboot/keepassxc/issues/6502).

#### Why Wayland is designed this way

This is not primarily a security restriction; it is the core Wayland
principle that **the compositor owns window management**. In X11 any
client could raise itself, grab focus, and query/move/minimize any
window, which produced focus-stealing and cross-app snooping. Under
Wayland the client describes *content*; the compositor and user decide
*presentation* (stacking, focus, minimize, placement).

Consequences:

- **Minimize is a window-management policy decision, so it belongs to
  the compositor.** An app may *request* `set_minimized` (a hint); it
  is deliberately not told it happened and cannot un-minimize itself.
- The security/anti-focus-stealing aspect is real but secondary:
  restore requires an `xdg_activation_v1` token the compositor can
  reject, specifically to end X11-style focus-stealing. Seeing *other*
  windows is the genuine privacy concern, which is why those are
  separate compositor-gated protocols.

Reframe: there is no single "minimize" concept that the app fakes with
a hide. There are two things X11 conflated:

1. **Minimize** (titlebar button) - the compositor's job; the app
   should not intercept it.
2. **Run in background with no window** - an application-lifecycle
   choice the app legitimately owns: unmap its own surface (`Hide`)
   and offer the SNI tray icon to return. An app is always allowed to
   not show a window.

For the "stop rendering when not visible" use case, Wayland's honest
signal is the absence of `wl_surface.frame` callbacks / the
`suspended` state ("you are not being painted"), which is more
accurate than a minimized flag because it also covers occlusion and
other-workspace.

#### Modern best practice (2025-2026)

Synthesis of current upstream guidance (KDE, freedesktop):

| Concern | Best practice | Task Coach status |
|---------|---------------|-------------------|
| Tray presence | StatusNotifierItem over D-Bus | Have it (libayatana) |
| Going hidden | App owns hide/show itself (self-tracked); prefer **close-to-background** over intercepting the minimize button (the latter is now an anti-pattern, flagged for GNOME) | The self-tracked tray Show/Hide toggle is exactly this |
| "Running in background" declaration | `org.freedesktop.portal.Background` (XDG portal; KDE/GNOME/Cinnamon/Deepin). Future-proof, but *indication only* - it does **not** restore the window | Optional future add-on; does not solve restore |
| Restore / raise | Use the `xdg-activation-v1` token the SNI host passes on tray `Activate` | Limited: libayatana is menu-centric and does not forward the token, so `Raise()` is best-effort. Full compliance needs raw-SNI or Qt/KStatusNotifierItem, not GTK3+libayatana |

Conclusion: the self-tracked Show/Hide toggle is the modern-correct
approach for the hide side (Wayland has no minimize, so every app must
own this). Intercepting the titlebar minimize button should be dropped
as an anti-pattern rather than "fixed". The fully-correct restore path
(activation token) is gated by the libayatana toolkit - an honest
limitation shared by all GTK3+libayatana apps (KeePassXC #6502 is the
canonical example).

Best-practice references:
[KDE - On Window Activation (Broulik, 2025)](https://blog.broulik.de/2025/08/on-window-activation/),
[Betterbird - System tray on Linux/Wayland (2026)](https://blog.betterbird.eu/2026/01/system-tray-support-on-linux-and-windows-and-wayland),
[Liferea - use the Background portal](https://github.com/lwindolf/liferea/issues/1418),
[Spotube - minimize-to-tray anti-pattern](https://github.com/KRTirtho/spotube/issues/1330).

#### Coverage matrix: where "minimize to tray, keep taskbar entry" can work

The two factors are **independent**: whether a taskbar/window-list is
present (configurable on GNOME and bare wlroots), and whether the
session exposes a *client-usable* window-management protocol (a
property of the compositor, not the panel). Every row states the
session type explicitly.

| Session | Taskbar present? | Client window-mgmt protocol | Keep entry + restore from tray? |
|---------|------------------|-----------------------------|----------------------------------|
| **X11** (any DE) | yes (WM-provided) | n/a, native | Yes - native `Iconize()` / `restore()` |
| **Windows / macOS** | yes (native) | n/a, native | Yes - native |
| **KDE Plasma, Wayland** | yes (default) | `org_kde_plasma_window_management` | Yes - out-of-band backend |
| **COSMIC, Wayland** | yes (default) | `cosmic-toplevel` (or `wlr`) | Yes - out-of-band backend |
| **wlroots (Sway/Hyprland/river/niri/…), Wayland, with a Waybar taskbar** | yes (user-added) | `wlr-foreign-toplevel-management` | Yes - out-of-band backend |
| **wlroots, Wayland, no taskbar configured** | no | (present, irrelevant) | N/A - plain Hide/Show is fine (nothing to lose) |
| **GNOME (Mutter), Wayland, default** | no | none (by GNOME design) | N/A - plain Hide/Show is fine (nothing to lose) |
| **GNOME (Mutter), Wayland, + taskbar extension (Dash to Panel, Window List, …)** | **yes (user-added)** | **none** | **No app-side solution** |

The last row is the single irreducible dead end: the user has a
taskbar, but Mutter exposes no client window-management protocol and
its extension taskbars are driven by GNOME Shell's internal JS APIs
that an external app cannot reach (and GTK3 `Iconize()` is a no-op on
Wayland anyway). It cannot be solved from application code; it is
documented here as a known limitation. On that configuration the tray
"Hide" is unavoidably tray-only, by Mutter's design - not a Task
Coach defect.

Consequence for implementation: a single "out-of-band toplevel
manager" abstraction with two protocol backends
(`org_kde_plasma_window_management` for KDE,
`wlr-foreign-toplevel-management` for wlroots/COSMIC, same vendored
pattern as the idle backend) covers every session that has both a
taskbar and a protocol; native `Iconize()`/`restore()` covers
X11/Windows/macOS; plain Hide/Show is correct where there is no
taskbar; only GNOME-with-a-taskbar-extension is unsupported and
documented as such.

#### Implementation

`taskcoachlib/gui/toplevelcontroller.py` implements this:

- `ToplevelController` - abstract `is_minimized()` / `minimize()` /
  `restore()`.
- `NativeController` - X11/Windows/macOS; wx `Iconize()`/`restore()`
  (preserves the macOS raise behaviour).
- `KdePlasmaController` - KDE Wayland; on-demand side connection via
  the vendored `org_kde_plasma_window_management` binding
  (`taskcoachlib/thirdparty/plasma_window_management`), matches our
  own toplevel by PID then title, and `set_state`s minimized /
  unminimized+active. Any failure falls back to `HideShowController`.
- `HideShowController` - universal fallback (`Hide()`/`Show()`).
- `create_toplevel_controller()` - the startup probe selecting the
  backend (mirrors the idle backend probe).

Both `TaskBarIcon.onTaskbarClick` and
`AppIndicatorTaskBarIcon.onTaskbarClick` (and the "Show/Hide" menu
item, which calls `onTaskbarClick`) now delegate to the controller:
`controller.restore()` if `is_minimized()` else
`controller.minimize()`. The previous
`IsIconized()/IsShown()/IsActive()` heuristic is removed.

The wlroots/COSMIC backend (`wlr-foreign-toplevel-management`) is
follow-up work; until it lands those sessions use the Hide/Show
fallback. KDE Wayland runtime behaviour requires on-box verification
(no compositor in CI), the same caveat as the idle backend.

## Menu Contents

Both `TaskBarMenu` (Windows/macOS) and `AppIndicatorTaskBarIcon._buildGtkMenu`
(Linux) provide the same items:

1. **Hide / Restore** - Toggle main window visibility (dynamic label)
2. **New task...** - Create a new task
3. **New task from template** - Submenu with saved templates
4. **New effort...** - Create a new effort entry
5. **New category...** - Create a new category
6. **New note...** - Create a new note
7. **Start tracking effort** - Submenu with trackable tasks (hierarchical)
8. **Stop/Resume tracking** - Dynamic based on state:
   - When tracking: "Stop tracking [task name]"
   - When paused: "Resume tracking [last task name]"
   - When no recent effort: Hidden
9. **Quit** - Exit the application

The AppIndicator menu rebuilds automatically when:
- Task list changes (tasks added/removed)
- Tracking starts or stops
- Task subjects change

The wx `TaskBarMenu` updates dynamic submenus and state-dependent labels
in `popupTaskBarMenu()` each time the menu is shown.

### Hide / Restore Toggle

`MainWindowRestore` (in `uicommand.py`) is a state-aware UICommand:
- When the window is visible: label is **"Hide"**, action calls `Iconize()`
- When the window is hidden/iconized: label is **"Restore"**, action calls `restore()`

The label is updated dynamically via `getMenuText()`: `popupTaskBarMenu()`
calls `item._command.getMenuText()` and applies `SetItemLabel()` before
showing the menu. The AppIndicator GTK menu uses "Show/Hide Task Coach"
as a static label (GTK menus don't support per-show label changes as easily).

## Dependencies

### Linux

AppIndicator requires GObject Introspection bindings:

**Debian/Ubuntu:**
```bash
sudo apt install gir1.2-ayatanaappindicator3-0.1
```

**Fedora:**
```bash
sudo dnf install libayatana-appindicator-gtk3
```

**Arch Linux:**
```bash
sudo pacman -S libayatana-appindicator
```

### GNOME Shell Note

GNOME Shell removed built-in system tray support. GNOME users need the [AppIndicator Support](https://extensions.gnome.org/extension/615/appindicator-support/) extension. Ubuntu pre-installs this extension.

## Icon Animation

When effort tracking is active, the tray icon blinks between two states:
- `taskcoach-clock` - Clock face
- `taskcoach-timer` - Stopwatch

This is controlled by the setting `window.blinktaskbariconwhentrackingeffort`.

## Debugging

Debug logging can be enabled by looking for `[TRAY]` prefix in console output:

```
[15:21:01.054] [TRAY] create_taskbar_icon called
[15:21:01.055] [TRAY] Desktop environment: KDE
[15:21:01.055] [TRAY] wx.adv.TaskBarIcon.IsAvailable() = True
[15:21:01.055] [TRAY] _APPINDICATOR_AVAILABLE = True
[15:21:01.055] [TRAY] needs_appindicator = True
[15:21:01.055] [TRAY] Using AppIndicator (desktop requires it)
```

Key log messages:
- `Using AppIndicator (desktop requires it)` - Linux, using AppIndicator
- `Using wx.adv.TaskBarIcon (native)` - Windows/macOS

## Files

| File | Purpose |
|------|---------|
| `taskcoachlib/gui/taskbaricon.py` | Main implementation, factory function |
| `taskcoachlib/gui/appindicator.py` | AppIndicator/GTK bindings |
| `taskcoachlib/gui/menu.py` | TaskBarMenu class for wx platforms |
| `taskcoachlib/gui/uicommand/uicommand.py` | FileQuit (deferred quit), MainWindowRestore (Hide/Restore toggle) |
| `taskcoachlib/gui/icons/` | Icon files (PNG at various sizes) |

## Code Duplication

`TaskBarIcon` and `AppIndicatorTaskBarIcon` in `taskbaricon.py` duplicate
~100 lines of identical logic. Only `__setIcon()` and menu handling differ.

### Shared (duplicated)

| Code | Description |
|------|-------------|
| Observer registration | `registerObserver`, `pub.subscribe` for task/tracking/due events |
| `onTaskListChanged` | Tooltip + start/stop ticking |
| `onTrackingChanged` | Register/remove subject observer, tooltip, start/stop |
| `onChangeSubject` | Tooltip update |
| `onChangeDueDateTime` | Tooltip update |
| `onChangeDueDateTime_Deprecated` | Tooltip update |
| `onEverySecond` | Blink setting check, toggle icon, set icon |
| `toolTipMessages` | Status message templates |
| `__setTooltipText` | Build tooltip from tracked tasks / status counts |
| `__set_default_icon` | Reset icon_id / tray_icon_id to default |
| `__toggle_tracking_icon` | Swap tick/tack icon_id / tray_icon_id |
| `__startOrStopTicking` | Dispatch to start/stop |
| `__startTicking` / `__stopTicking` | Clock + icon control |
| `startClock` / `stopClock` / `_onTimerSecond` | Timer pub/sub |
| Getters | `tooltip()`, `icon_id()` / `tray_icon_id()`, `default_icon_id()` / `default_tray_icon_id()` |

### Platform-specific (different)

| TaskBarIcon (Windows/Mac) | AppIndicatorTaskBarIcon (Linux) |
|---|---|
| `__setIcon`: `icon_catalog.get_wx_icon(id, size)` → `self.SetIcon()` | `__setIcon`: `indicator.set_icon_full("taskcoach-app", tooltip)` via tray/hicolor theme |
| `onIdle` — wx idle loop change detection | (none — calls `__setIcon` directly) |
| `onTaskbarClick(event)` — Mac Raise branch | `onTaskbarClick(event=None)` — simpler |
| `setPopupMenu` — wx.Bind right-click | `setPopupMenu` — stores, builds GTK menu |
| `popupTaskBarMenu` — wx.PopupMenu | GTK menu building + action handlers (~300 lines) |
| wx click event binding in `__init__` | (none) |
| `mainwindow.Bind(EVT_IDLE)` | (none) |
| (none) | wx compatibility stubs (Bind, Unbind, ProcessEvent, UpdateWindowUI) |
| (none) | `RemoveIcon`, `Destroy` |

---

## Why a Separate tray/hicolor Theme?

`set_icon_theme_path(path)` expects `path` to **contain** theme directories (like
`/usr/share/icons/` contains `hicolor/`, `Adwaita/`). Only the current theme, its
inheritance chain, and the `hicolor` fallback are searched during icon lookup.

The original fix passed bare names (`korganizer`, `clock`, `ktimer`) with the path
pointing at the nuvola theme directory itself — wrong level, and `nuvola` is never in
any desktop theme's inheritance chain, so the icons were never found via theme lookup.

Additionally, names like `korganizer`, `clock`, `ktimer` collide with system themes
(KDE Breeze, GNOME Adwaita). KDE would find its own `korganizer` icon in Breeze
before ever checking our custom path.

The solution follows the Electron/Chromium pattern: create a bundled `hicolor/` theme
with uniquely-prefixed names (`taskcoach-app`, `taskcoach-clock`, `taskcoach-timer`)
that don't exist in any system theme. Since `hicolor` is the universal fallback —
always searched last by both GTK (`gtk_icon_theme`) and Qt (`QIcon::fromTheme` /
`KIconLoader`) — the icons are guaranteed to be found regardless of desktop environment.

```
taskcoachlib/gui/icons/tray/          ← set_icon_theme_path() points here
  hicolor/                            ← universal fallback theme
    index.theme
    {16,22,32,48,64,128}x.../apps/
      taskcoach-app.png               ← unique name, no collision
      taskcoach-clock.png
      taskcoach-timer.png
```

### Approaches tried and rejected

| # | Approach | LXDE | KDE | Why it failed |
|---|----------|------|-----|---------------|
| 1 | **Absolute paths** via `icon_catalog.get_path()` (pre-v1, commit `a20c9164c`) | Works | Wrong icon (Breeze calendar) | KDE's SNI host extracts the stem from the absolute path and resolves it through the system theme. `/path/to/korganizer.png` → KDE looks up `korganizer` in Breeze → finds Breeze's calendar icon, not ours. |
| 2 | **Bare names** (`korganizer`, `clock`, `ktimer`) + `set_icon_theme_path(nuvola/)` (v1 fix, commit `851cbe3fd`) | Broken (can't resolve) | Wrong icon (still Breeze) | `set_icon_theme_path` expects the **parent** of a theme dir, not the theme dir itself. And even with the correct level, `nuvola` is not in any theme's inheritance chain so it's never searched. Names also collide with system themes. |
| 3 | **Bundled `tray/hicolor`** with unique `taskcoach-*` names (current, commit `26df25b47`) | Works | Works | `hicolor` is the universal fallback, always searched. Unique names avoid collisions. |

**Do not revisit approaches #1 or #2.** They are fundamentally broken due to how
KDE's SNI host resolves icon names through the system theme.

**References:** libayatana-appindicator `app-indicator.c`, KDE
`statusnotifieritemsource.cpp`, Electron `app_indicator_icon.cc`.

## See Also

- [ICON_DISPLAY.md — Tray Icons](ICON_DISPLAY.md#tray-icons) - Icon access methods and platform sizes


