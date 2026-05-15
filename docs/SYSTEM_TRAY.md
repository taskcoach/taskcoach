# System Tray Icon Implementation

How Task Coach exposes its system tray (notification area) icon on each
platform.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Linux: Direct StatusNotifierItem](#linux-direct-statusnotifieritem)
- [Windows / macOS: wx.adv.TaskBarIcon](#windows--macos-wxadvtaskbaricon)
- [Menu Contents](#menu-contents)
- [Window Show/Hide on Wayland](#window-showhide-on-wayland)
- [Windows Quit-from-Tray Safety](#windows-quit-from-tray-safety)
- [Icon Theme (Linux)](#icon-theme-linux)
- [Dependencies](#dependencies)
- [Debugging](#debugging)
- [Files](#files)

## Overview

The tray icon lets users:

- show/hide the main window
- create tasks, efforts, categories, notes
- start/stop effort tracking (icon blinks while tracking)
- quit the application

## Architecture

```
create_taskbar_icon(mainwindow, taskList, settings)
  │
  ├─ Linux/GTK + SNI watcher on bus → SniTaskBarIcon
  │     uses sni.SniIcon (direct D-Bus, dbus-python)
  │     ItemIsMenu = False  → left-click triggers Activate()
  │     right-click triggers ContextMenu() → popup_at_pointer(Gtk.Menu)
  │
  └─ everything else → TaskBarIcon (wx.adv.TaskBarIcon)
        XEmbed on X11; native on Windows/macOS
```

| Class | File | Purpose |
|-------|------|---------|
| `SniTaskBarIcon` | `taskbaricon.py` | Linux tray, uses `SniIcon` |
| `SniIcon` | `sni.py` | Direct SNI server (~250 lines, dbus-python) |
| `TaskBarIcon` | `taskbaricon.py` | wx.adv.TaskBarIcon wrapper (Windows/macOS, X11 fallback) |
| `TaskBarMenu` | `menu.py` | `wx.Menu` for the wx path |

## Linux: Direct StatusNotifierItem

`sni.py` implements `org.kde.StatusNotifierItem` directly over D-Bus. The
SNI specification defines three click methods on the interface:

- `Activate(x, y)` — left-click
- `ContextMenu(x, y)` — right-click
- `SecondaryActivate(x, y)` — middle-click

Plus an `ItemIsMenu` boolean property. When `false`, well-behaved hosts call
`Activate()` on left-click; when `true`, they show the menu instead.

Task Coach sets `ItemIsMenu = false` and binds `Activate()` to its own
show/hide handler. Right-click invokes `ContextMenu()`, which calls
`Gtk.Menu.popup_at_pointer(None)` on the pre-built menu.

No `DBusMenu` (the `com.canonical.dbusmenu` companion protocol) is exposed —
the `Menu` property returns the sentinel path `/NO_DBUSMENU`, which makes
hosts fall through to `ContextMenu()`.

### Why not libayatana-appindicator?

That was Task Coach's previous backend. It implements SNI under the hood
but hardcodes `ItemIsMenu = true` and provides no `Activate` callback, so
every click on the icon drops the menu — left-click and right-click are
indistinguishable. Direct SNI removes that wrapper to recover click
differentiation. (See git history for the libayatana-based implementation
that was removed when direct SNI landed.)

### Compatibility

| Host | Status |
|------|--------|
| KDE Plasma (X11 and Wayland) | Confirmed working |
| GNOME Shell + AppIndicator Support extension | Expected to work (SNI host) |
| Ubuntu GNOME (extension pre-installed) | Expected to work |
| XFCE + statusnotifier plugin | Expected to work |
| MATE / Cinnamon / LXQt / LXDE with SNI plugin | Expected to work |
| No SNI watcher on the bus | Falls back to `wx.adv.TaskBarIcon` (XEmbed) |

"Expected to work" means the protocol is correct and we expect the host to
honour it; not yet verified on hardware.

## Windows / macOS: wx.adv.TaskBarIcon

The wx-native path. `TaskBarIcon` subclasses `wx.adv.TaskBarIcon` directly,
binds `EVT_TASKBAR_LEFT_DOWN`/`LEFT_DCLICK`, and uses `wx.Menu` for the
right-click popup. Icon sizes: `TRAY_ICON_SIZE_MACOS = 128` on macOS,
`LIST_ICON_SIZE = 16` everywhere else.

## Menu Contents

The right-click menu contains:

1. **Hide / Restore** — toggle main window visibility (label depends on state)
2. **New task...**
3. **New task from template** — submenu with saved templates
4. **New effort...**
5. **New category...**
6. **New note...**
7. **Start tracking effort** — submenu with trackable tasks (hierarchical)
8. **Stop / Resume tracking** — dynamic based on current tracking state
9. **Quit**

`SniTaskBarIcon` rebuilds its `Gtk.Menu` whenever task list, tracking state,
or task subjects change. `TaskBarIcon` updates dynamic submenus and labels
inside `popupTaskBarMenu()` each time the menu is shown.

### Hide / Restore Toggle

`MainWindowRestore` (in `uicommand.py`) is state-aware:

- Window visible: label is **Hide**, action calls `Iconize()`
- Window hidden/iconized: label is **Restore**, action calls `restore()`

The wx menu updates the label via `getMenuText()` before each show. The
GTK menu uses a static "Show/Hide Task Coach" label since GTK menus don't
update labels per-show as cheaply.

## Window Show/Hide on Wayland

Wayland's `xdg-shell` has no "unminimize" request and no way to query
minimized state — by design. GTK3's Wayland backend never sets
`GDK_WINDOW_STATE_ICONIFIED`, so wxGTK's `IsIconized()` always returns
False. `restore()` calls `Iconize(False)` → `gdk_window_show()`, which is
a no-op if already mapped. `Raise()` calls `gtk_window_present()`, which
needs a valid `xdg_activation_v1` token; tray clicks come through D-Bus
with no input serial → ignored.

The workaround uses `IsActive()` to detect the Wayland case (it goes False
when the compositor minimizes, even though `IsIconized()` stays False),
then forces a Wayland surface remap via `Hide()` + `Show()`:

```python
if IsIconized() or not IsShown():    # X11: wx knows → normal restore
    restore(event)
elif not IsActive():                 # Wayland: compositor minimized, wx doesn't know
    Hide(); Show()                   # force surface remap
else:
    Hide()                           # explicit hide-to-tray
```

The proper fix would be KDE's `ProvideXdgActivationToken()` D-Bus method,
which Electron uses. Not exposed by libayatana-appindicator (now removed)
or its glib variant as of 2026-05; could be added on top of our direct-SNI
path in the future.

## Windows Quit-from-Tray Safety

On Windows, `PopupMenu()` runs a **modal event loop** — it blocks until the
user dismisses the menu. Without care, the Quit menu item destroys the
tray icon while the modal loop is still running, segfaulting on return.

`FileQuit.do_command()` defers the close with `wx.CallAfter`:

```python
def do_command(self, event):
    wx.CallAfter(self.main_window().Close, force=True)
```

This lets `PopupMenu()` return cleanly before `quitApplication()` tears
down the tray icon. The SNI/GTK path uses the same pattern.

## Icon Theme (Linux)

`SniIcon` exposes `IconThemePath` and `IconName` SNI properties, pointing at
the bundled icon theme:

```
taskcoachlib/gui/icons/tray/
  hicolor/
    index.theme
    {16,22,32,48,64,128}x.../apps/
      taskcoach-app.png       ← left-click default
      taskcoach-clock.png     ← tracking, frame 1
      taskcoach-timer.png     ← tracking, frame 2
```

`hicolor` is the universal fallback always searched by both GTK
(`gtk_icon_theme`) and Qt (`QIcon::fromTheme`), so the icons resolve
regardless of the user's active system theme. The unique `taskcoach-*`
prefix avoids name collisions (an earlier attempt used `korganizer` /
`clock` / `ktimer` and KDE Breeze stole every lookup before reaching us).

## Dependencies

### Linux

```
# Debian / Ubuntu
sudo apt install python3-dbus

# Fedora
sudo dnf install python3-dbus

# Arch
sudo pacman -S python-dbus
```

`dbus-python` is what `sni.py` builds on. Without it `SNI_AVAILABLE` is
False and we fall back to `wx.adv.TaskBarIcon`.

### GNOME Shell note

GNOME Shell removed built-in system tray support. GNOME users need the
[AppIndicator Support](https://extensions.gnome.org/extension/615/appindicator-support/)
extension (an SNI watcher; despite the name, our direct-SNI path uses it
just the same). Ubuntu pre-installs it.

## Debugging

Look for `[TRAY]` lines in the log:

```
[09:21:01] [TRAY] create_taskbar_icon called
[09:21:01] [TRAY] Desktop environment: KDE
[09:21:01] [TRAY] _SNI_AVAILABLE = True
[09:21:01] [TRAY] wx.adv.TaskBarIcon.IsAvailable() = False
[09:21:01] [TRAY] Using SniTaskBarIcon (direct SNI)
```

Key lines:

- `Using SniTaskBarIcon (direct SNI)` — Linux with SNI watcher
- `Using TaskBarIcon (wx.adv.TaskBarIcon)` — everything else

## Files

| File | Purpose |
|------|---------|
| `taskcoachlib/gui/taskbaricon.py` | `SniTaskBarIcon`, `TaskBarIcon`, factory |
| `taskcoachlib/gui/sni.py` | `SniIcon` — D-Bus StatusNotifierItem server |
| `taskcoachlib/gui/menu.py` | `TaskBarMenu` for the wx path |
| `taskcoachlib/gui/uicommand/uicommand.py` | `FileQuit`, `MainWindowRestore` |
| `taskcoachlib/gui/icons/tray/hicolor/` | Bundled tray icon theme |
