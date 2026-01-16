# System Tray Icon Implementation

This document describes the system tray (notification area) icon implementation in Task Coach across different platforms and desktop environments.

## Overview

Task Coach displays a system tray icon that allows users to:
- Show/hide the main window
- Access common actions (new task, new effort, etc.)
- Start/stop effort tracking
- See tracking status via icon animation

## Implementation Architecture

### Platform Detection Flow

```
create_taskbar_icon()
    |
    +-- Linux/GTK? --Yes--> Use AppIndicator (all Linux)
    |
    +-- No --> wx.adv.TaskBarIcon (Windows, macOS)
```

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
- `clock_icon` - Clock face
- `clock_stopwatch_icon` - Stopwatch

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

## History

- **Original**: wx.adv.TaskBarIcon only
- **2026-01**: Added AppIndicator support for Wayland
- **2026-01**: Switched to AppIndicator for all Linux due to wx.adv.TaskBarIcon right-click issues
