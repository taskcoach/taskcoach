# System Tray Icon Implementation

This document describes the system tray (notification area) icon implementation in Task Coach across different platforms and desktop environments.

## Table of Contents

- [TODO](#todo)
- [Overview](#overview)
- [Implementation Architecture](#implementation-architecture)
- [Platform Behavior Matrix](#platform-behavior-matrix)
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

Wayland's xdg-shell has no "unminimize" request and no way to query minimized
state — by design. GTK3's Wayland backend never sets
`GDK_WINDOW_STATE_ICONIFIED` (`gtk_window_iconify()` is an empty stub), so
wxGTK's `IsIconized()` always returns False. `restore()` calls
`Iconize(False)` → `gdk_window_show()` — no-op if already mapped. `Raise()`
calls `gtk_window_present()` which needs a valid `xdg_activation_v1` token,
but tray clicks come through D-Bus with no input serial → ignored.

The fix uses `IsActive()` to detect the Wayland case (goes False when the
compositor minimizes, even though `IsIconized()` stays False), then forces a
Wayland surface remap via `Hide()` + `Show()`:

```python
if IsIconized() or not IsShown():    # X11: wx knows → normal restore
    restore(event)
elif not IsActive():                 # Wayland: compositor minimized, wx doesn't know
    Hide() + Show()                  # force surface remap
else:
    Iconize()
```

The proper fix would be KDE's `ProvideXdgActivationToken()` D-Bus method
(what Electron uses), but libayatana-appindicator does not support it — the
method is not in its D-Bus introspection XML, and neither does the newer
libayatana-appindicator-glib (as of 2026-02).

## Menu Contents

The AppIndicator menu provides:

1. **Show/Hide Task Coach** - Toggle main window visibility
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

The menu rebuilds automatically when:
- Task list changes (tasks added/removed)
- Tracking starts or stops
- Task subjects change

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
| `__set_default_icon` | Reset icon_id to default |
| `__toggle_tracking_icon` | Swap tick/tack icon_id |
| `__startOrStopTicking` | Dispatch to start/stop |
| `__startTicking` / `__stopTicking` | Clock + icon control |
| `startClock` / `stopClock` / `_onTimerSecond` | Timer pub/sub |
| Getters | `tooltip()`, `icon_id()`, `default_icon_id()` |

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


