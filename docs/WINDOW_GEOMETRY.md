# Window Geometry

How Task Coach remembers and restores the size, position and maximized
state of the main window and the editors.

Related:

- Panel layout, including floating panes, is AUI's own saving and
  restoring: [AUI.md](AUI.md).
- Minimize and hide from the tray: [SYSTEM_TRAY.md](SYSTEM_TRAY.md).
- Wayland limits: [AUI_WAYLAND_ISSUES.md](AUI_WAYLAND_ISSUES.md).

## Index

- [Decisions](#decisions)
- [Current Behaviour](#current-behaviour)
  - [Main Window](#main-window)
  - [Start Minimized](#start-minimized)
  - [Editors](#editors)
  - [Settings](#settings)
  - [Tracing](#tracing)
  - [Differences from Production](#differences-from-production)
- [Platforms](#platforms)
  - [Platform Matrix](#platform-matrix)
  - [Direct Placement](#direct-placement)
  - [wxWidgets Facilities](#wxwidgets-facilities)
  - [Other Toolkits](#other-toolkits)
  - [First Show on wxGTK](#first-show-on-wxgtk)
- [What Did Not Work](#what-did-not-work)
- [Trials](#trials)
- [Known Issues](#known-issues)
- [Tests](#tests)
- [Planned Refactoring](#planned-refactoring)
- [References](#references)

---

## Decisions

Decided with the maintainer, 2026-09-27:

1. **One restore path for any number of monitors.** A single monitor
   is a subset of several: geometry saved with more monitors than are
   present is fitted onto the monitors there are. No special case for
   one monitor, so what works on several works on one.
2. **Saved state is never thrown away.** A main window whose monitor
   is gone goes to the nearest monitor, keeps its size unless that is
   larger than the monitor, and keeps its maximized state. Editors
   follow 8.
3. **Main window and the edit window first.** All editors are one
   window class; other windows (Preferences and the like) come later.
   Each editor type keeps its own geometry per set of tabs, as before
   ([Editors](#editors)).
4. **The window manager has the last word.** Where placement is not
   direct (7), it is observed until quiet, then corrected at most three
   times, each checked when quiet again, and accepted: never a loop
   ([Placement Strategy](#placement-strategy)).
5. **Measure on the real desktop.** Xvfb results are only indicative
   (see [How It Was Measured](#how-it-was-measured)).
6. **Generic across platforms.** One design for Windows, macOS, every
   X11 window manager and Wayland, with variations only where a
   platform forces them or a simpler path is proven (7)
   ([Platform Matrix](#platform-matrix)). The
   development desktop's window manager must not shape the design. New
   findings go into the matrix, marked measured, source or untested,
   instead of being searched again.
7. **Direct placement where proven.** Where the platform applies
   position, size and maximize during the call and years of use raised
   no geometry reports, the geometry is set once before the first show
   and not checked: no quiet periods, no attempts. Windows and macOS
   qualify ([Direct Placement](#direct-placement)); every other
   platform uses observed placement (4).
8. **Editors open on the main window's monitor.** The user works in
   the main window, so an editor opened from it appears there; another
   monitor offers nothing and risks an editor opening out of sight. A
   saved position on another monitor is invalid: the editor is
   centered on the main window with its saved size, and a saved
   maximized editor is maximized on the main window's monitor. Anything
   else unusable (no saved size, a size larger than the monitor, the
   main window's monitor unknown) falls back to the default: the
   system decides. This is the production rule, kept.
9. **Fix technical errors only.** The end results of the production
   code are kept: what is restored, where, and when a saved value is
   dropped. The work removes jitter (extra moves and resizes, fighting
   the window manager) and bugs, with the fewest moves as the first
   goal. A window shown once where the window manager put it, then
   moved once, is acceptable. The one change of result is 2
   ([Differences from Production](#differences-from-production)).

---

## Current Behaviour

`WindowGeometryTracker` (`taskcoachlib/gui/windowdimensionstracker.py`)
handles both window kinds; `WindowDimensionsTracker` adds start
minimized for the main window.

### Main Window

The saved position, size and maximized state are the **desired
state**.

On Windows and macOS ([Direct Placement](#direct-placement)) it is set
once before the first show: rule 1, `SetSize()`, `Maximize()` if saved
maximized, and the window counts as placed at once (rules 8 and 9).

Elsewhere (X11, Wayland) placement is observed, not assumed: each step
is checked only once the window is **quiet**, when neither position
nor size changed for a quiet period, and the platform's result is then
accepted. The same steps run on every window manager.

1. Load: the saved rect is fitted to the monitors by
   `fit_to_monitors()`. A rect whose title bar lies on a monitor and
   whose size fits that monitor's work area is kept exactly, even if
   partly off screen. Otherwise the size is reduced to the work area
   the rect overlaps most, or else the nearest one, and the rect is
   moved inside it. Maximized is kept. Without a saved position (always
   on Wayland) the window manager places it: the size, fitted to the
   first monitor, and maximized are kept.
2. Before the first `Show()`: `SetSize()` with the fitted rect. On
   GTK, until the first `EVT_SHOW` the requested size is also the
   minimum size, so wxGTK maps the window at that size
   ([First Show on wxGTK](#first-show-on-wxgtk)); then the minimum is
   600x400 again. At the first `EVT_SHOW`, if wx reports another
   position or size than requested, the request was lost and the
   position is sent again while the window is not mapped yet, so it
   maps there (`_resend_lost_request()`).
3. From the first `EVT_SHOW`, every `EVT_MOVE`, `EVT_SIZE`,
   `EVT_MAXIMIZE` and restore from minimized sent by the platform that
   changes the geometry restarts the quiet period (one
   `patterns.later.call`, [DEFERRED_CALLS.md](DEFERRED_CALLS.md)).
   Events wx sends during our own requests do not count, nor layouts
   that change nothing (`SendSizeEvent()`). Event handlers never
   correct.
4. Quiet period: 1 s for the first check, since startup is slow, then
   500 ms; always at least twice the platform's slowest answer so far
   (time from our request, or the first show, to a change it caused),
   up to 3 s. A slow or loaded computer gets longer periods.
5. Quiet: position (not on Wayland) and size are compared with the
   desired ones. If they differ, one attempt sets them, checked at the
   next quiet; after three attempts the result is accepted. A window
   maximized meanwhile, by the user or the window manager, is placed:
   maximized, with the saved normal geometry to return to.
6. Then, if saved maximized, `Maximize()`, checked the same way (three
   attempts, then accepted). A minimized window is maximized once it is
   restored.
7. A step that has not become quiet 10 s after it started (the window
   keeps changing, for instance dragged at once by the user) is ended
   and its result accepted; a saved maximized state not tried yet is
   kept.
8. Placed: moves and resizes update the state, position (not on
   Wayland) and size only while the window is neither maximized nor
   iconized. Minimized, the maximized state to restore to is kept.
9. `MainWindow.save_settings()` writes the state on close.

See [Placement Strategy](#placement-strategy) for why, and
[Trials](#trials) 12 and 13 for the measurements behind the numbers.

### Start Minimized

With `starticonized` "Always" the main window is shown and minimized at
start. While minimized:

- Where placement is observed, it is placed like any window (rules 3
  to 5): openbox honours moves of a mapped window even when minimized,
  so the restore lands on the saved position directly. A saved
  maximized window is maximized when it is restored.
- Where the geometry is set before the show (Windows, macOS),
  minimizing a window not shown yet drops the `Maximize()` asked
  before it (wxMSW): a saved maximized window is maximized when first
  restored.
- `ViewerContainer` does not focus the active viewer. Focusing a
  control of a minimized window makes the window manager activate, and
  so restore, it on X11; this restored every window started minimized.
  The skipped focus is given on the first restore.

**"If it was iconized last session"** (the default, P43 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues);
proposed 2026-09-30, for the designer's review). The preference picks
the start: Never, Always, or the window's state at the last quit. That
state is saved geometry: from 2007 to release 1.4.6 the tracker wrote
`iconized` at quit beside the position and size, and read it at start.
The fork's tracker (December 2025) dropped it, so the default has
started normally in every 2.0.x release, and the geometry work kept
that result ([Decisions](#decisions) 9).

Proposal:

1. The main window's saved state gains `iconized`: at the quit
   (`save()`, rule 9) the window was minimized or hidden in the tray,
   the tray's own test (`IsIconized() or not IsShown()`,
   `toplevelcontroller.py`). Position, size and maximized stay the
   state to restore to (rule 8). Editors are not concerned.
2. At start: Always, or last session with `iconized` saved, takes the
   path above, unchanged; Never, or not saved, starts normally. Only
   the decision is new, not the placement.
3. Old settings files: `iconized` has not been written since the fork
   and reads False, so the first start after the update is normal.

| Quit | Next start |
|---|---|
| File > Quit, or closing the window (quits) | Normal |
| Tray menu > Quit while minimized or hidden in the tray | Minimized (hidden, with "Hide main window when iconized") |
| Log out while minimized | Minimized |
| Close with "Minimize main window when closed", then Quit from the tray | Minimized |

Limit: on Wayland GTK 3 never reports a window minimized
([SYSTEM_TRAY.md](SYSTEM_TRAY.md)), so a minimized window saves as not
minimized there; a window hidden by the tray (the fallback on GNOME)
is seen.

### Editors

`Editor` (`taskcoachlib/gui/dialog/editor.py`) creates the tracker with
its parent, after `widgets.Dialog` has fitted and centered it. Editors
stay on the parent's monitor ([Decisions](#decisions) 8), as in
production:

1. Parent's monitor unknown: the saved geometry is cleared and the
   system decides.
2. No saved position: the saved size, or without one the 400x300
   minimum, centered on the parent. The fitted size is smaller
   (226x297 for a task), because the pages no longer report a best
   size ([PYTHON3_MIGRATION_1.md](PYTHON3_MIGRATION_1.md)).
3. Saved size larger than the parent's monitor: the saved geometry is
   cleared and the system decides.
4. Position off that monitor: saved size, centered on the parent.
5. Otherwise the saved position and size.
6. Saved maximized: maximized once placed, so on the parent's monitor.
7. Wayland: the saved size only; the compositor places the editor.

Placement is then observed as for the main window (rules 3 to 7).
Usually the editor maps where requested. After an editor is closed,
though, the next one may take wxGTK's deferred first show, where the
requested position is lost; sending it again at the first show
([Main Window](#main-window) rule 2) makes it map where requested.
Why the deferral happens: `on_close_editor()` hides the editor before
destroying it, openbox then publishes zero frame extents for it
(`client_unmanage()`), and wxGTK stores them in its frame extents
cache, shared by all windows, when they arrive before the destroy. A
new window whose cached title bar height is 0 defers its first show
([First Show on wxGTK](#first-show-on-wxgtk)). The fitted size at
creation tells: 224x270 instead of 228x297.

The state is saved in `on_close_editor()`, in the editor's settings
section: one per editor type (task, category, note, attachment) and
set of tabs, plus `[effortdialog]`. Editing several items at once shows
fewer tabs, so it has its own section; a release that adds a tab (such
as Path) starts a new section, and the old one stays unused.

### Differences from Production

Reviewed against the production tracker (master, 2026-09-27) for
[Decisions](#decisions) 9. "Code" means read in the code, not
measured.

| Case | Production | Now | Kind |
|---|---|---|---|
| First show (GTK) | Maps at the 600x400 minimum where the window manager puts it, resized and moved to the saved geometry; up to three more resets to 600x400, each corrected back | Maps at the saved size and position, no move (openbox) | Technical |
| Corrections | On every move and resize, including stale ones | Once quiet, at most three, then accepted | Technical |
| Window manager refuses a position | Fought; the window never counts as placed, so the user's moves and resizes that session are not saved (code) | Accepted after three attempts; changes saved | Technical |
| Main window not active at start (the user types elsewhere) | Never counts as placed: same loss (code) | Placed whatever the focus | Technical |
| Start minimized "Always" | Restores itself at once | Stays minimized; maximized on restore | Technical |
| Saved maximized | Maximized once placed, not checked | Maximized once placed, checked up to three times | Same result |
| Main window rect on no monitor, or larger than the monitor | Minimum size where the window manager puts it, not maximized | Fitted to the nearest monitor, size and maximized kept | Changed by [Decisions](#decisions) 2 |
| Editors | Rules 1 to 6 above | Same | Same result |
| Wayland | Saves (0, 0) as the position on the first run (code) | Positions neither restored nor saved; sizes and maximized kept | Technical |
| Windows, macOS | Set before show, checked and corrected after it; macOS set the client size, then corrected it back | Set before show, not checked | Same result |

### Settings

| Section | Key | Use |
|---------|-----|-----|
| `[window]` | `position`, `size`, `maximized` | Main window state |
| `[window]` | `starticonized`, `hidewheniconized` | [Start Minimized](#start-minimized) |
| `[window]` | `iconized` | Not used since December 2025; the proposal for "If it was iconized last session" ([Start Minimized](#start-minimized)) |
| `[<type>dialog_with_<tabs>]`, `[effortdialog]` | `position`, `size` | Editor state, one section per editor type and set of tabs |
| same | `maximized` | Written; editors have a maximize box |
| same | `perspective` | Tab layout, saved but not loaded (see [PYTHON3_MIGRATION_1.md](PYTHON3_MIGRATION_1.md)) |

### Tracing

Every placement step is logged with the `[GEOMETRY]` prefix, the window
(`window`, or the editor type such as `taskdialog`) and the
milliseconds since the tracker started: saved, fitted and requested
geometry, monitors, every `EVT_SHOW`/`EVT_MOVE`/`EVT_SIZE`/
`EVT_MAXIMIZE`/`EVT_ICONIZE` with the window state, each quiet check,
attempt and accepted result, and the time from each `EVT_SIZE` to the
next idle (layout and paint). Tracing stops once placed, with direct
placement once shown; the state written on close is always logged.

---

## Platforms

Researched 2026-09-27; "measured" means seen on the real desktop,
"source" means read in the window manager's or toolkit's code or docs
(see [References](#references)), "untested" means neither.

### Platform Matrix

| Platform, window manager | Position before first show | Move after show | Own size | Maximize, minimize | State the app can read | Evidence |
|---|---|---|---|---|---|---|
| Windows (wxMSW) | Honoured | Honoured | Yes | Both, also before show | All | Source (wx); years of use ([Direct Placement](#direct-placement)); untested here |
| macOS (wxOSX) | Honoured | Honoured | Yes | "Maximize" is zoom; full screen is a separate space | All | Source (wx); years of use ([Direct Placement](#direct-placement)); untested here |
| X11, openbox (LXDE) | Kept when the app claims it (program or user position); Task Coach's new window lands at (80, 0), as if requested at (0, 0) | Honoured, but kept out of the panel's width on every monitor | Yes, but GTK maps the first window at its minimum or natural size ([First Show on wxGTK](#first-show-on-wxgtk)) | Both; maximized before show lands on the monitor the window was placed on | All | Measured; source (openbox `place.c`) |
| X11, KWin (KDE) | Kept when the app claims it, unless a window rule says otherwise; moved if outside the screen | Honoured | Yes | Both | All | Source (KWin `x11window.cpp`); untested |
| X11, Mutter (GNOME), Muffin (Cinnamon) | Ignores a program position; reports differ on whether a user position is kept | Reported as vetoed at times | Yes | Both | All | Source (Zed issue, DisplayXR issue); untested |
| X11, Xfwm4 (Xfce), Marco (MATE), others | Unknown | Unknown | Yes | Both | All | Untested |
| X11 tiling (i3 and the like) | Ignored for tiled windows | Ignored for tiled windows | Tiled windows get the tile's size | Depends | All | Untested |
| Wayland (Mutter, KWin, wlroots/Sway) | Impossible: no protocol for it | Impossible; `GetPosition()` is (0, 0) | Yes: the app picks its size unless maximized, tiled or full screen | Requests only | Maximized, full screen, focus; never minimized (GTK3 `IsIconized()` is always False) | Source (xdg-shell); see [SYSTEM_TRAY.md](SYSTEM_TRAY.md) |
| XWayland (`GDK_BACKEND=x11` under Wayland) | As X11 with the compositor's X11 rules | As X11 | Yes | Both | All | Not a supported mode ([AUI_WAYLAND_ISSUES.md](AUI_WAYLAND_ISSUES.md)) |

Consequences for the design:

- No platform guarantees the requested position, and Wayland gives
  none at all, so the tracker must accept what it gets.
- The same window can be placed at once (Windows, macOS, KWin, openbox
  once the lost request is sent again), elsewhere than requested
  (refused positions) or not at all (Wayland). On X11 and Wayland
  "placed" has to be observed; Windows and macOS are known to place at
  once ([Direct Placement](#direct-placement)).
- On Wayland positions must be neither corrected nor saved: saving
  (0, 0) there would overwrite the position saved in an X11 session.
- Wayland gained a protocol for compositors to restore windows
  (`xdg-session-management`, merged 2025; KWin and GNOME implementing);
  toolkits have to use it, see [wxWidgets Facilities](#wxwidgets-facilities).

### Direct Placement

Platforms where the geometry is set once before the first show and not
checked ([Decisions](#decisions) 7). A platform is listed only when
its toolkit applies position, size and maximize during the call and
releases used that path for years without geometry reports. Checked
2026-09-27; add the date and evidence when extending the list.

| Platform | How wx applies it | Years of use | Reports |
|---|---|---|---|
| Windows (wxMSW) | `SetSize()` calls `SetWindowPos()`, applied at once, also on a hidden window. `Maximize()` before show maximizes at show, on the monitor of the normal rect, which un-maximizing restores. | Task Coach set position and size before the first show from 0.20 (2005), maximize from 2008; the Python 3 port added checks after show on every platform in late 2025. Builds now use wxPython 4.3.1 (wxWidgets 3.3). | Last fix: windows on the wrong monitor on Windows 7 (1.2.26, August 2011, bug 3370403). None since in the release notes nor in this repository's issues. |
| macOS (wxOSX) | `SetSize()` sets the frame at once; `Maximize()` zooms. | Same as Windows. Builds use wxPython 4.3.1. | Last fixes: a window moved to (0, 0) hid its title bar under the menu bar, (50, 50) since July 2013; size corrections for the wxMac of 2012. None since. |

macOS size: upstream saved and set the client size, with an 18 pixel
correction for the wxMac of 2012; the Python 3 port set the client
size after the frame size and corrected the difference after show. Now the frame size
is set and saved, as on Windows: to confirm on a Mac
([Next Steps](#next-steps)).

Not listed: X11, where every window manager answers later and in its
own way, and Wayland, which has no positions
([Platform Matrix](#platform-matrix)).

### wxWidgets Facilities

- `wxTopLevelWindow::SaveGeometry()`/`RestoreToGeometry()` (wxWidgets
  3.1.2 and later, used by `wxPersistentTLW`): position, size, maximized
  and minimized. On Windows it uses the native window placement. On GTK
  it also saves the title bar and border sizes, so a restored window
  skips the postponed first show. The generic restore keeps the
  position only if the saved top left or bottom right lies on a
  monitor. wxWidgets 3.3 adds Wayland session restore through
  `xdg-session-management`.
- The generic restore sets position, size, then `Maximize()` and
  `Iconize()`, all before the first show, and raises the size to the
  window's best size. It does not check the result afterwards.
- wxPython 4.2.3 (wxWidgets 3.2.7) exposes these methods, but its
  `GeometrySerializer` "cannot be instantiated or sub-classed" (checked
  2026-09-27), so they cannot be used from Python.
- wxWidgets 3.3 renames it `GeometryStore`, and wxPython 4.3 binds it
  as abstract (`etg/toplevel.py`), so a Python subclass backed by the
  settings should work (untested). The Windows and macOS builds use
  4.3.1; the Linux packages use their distribution's 4.1.1 to 4.2.5
  ([PACKAGING.md](PACKAGING.md)), so Linux has to do without it for
  years.
- What it would replace here: the minimum-size step and sending the
  lost position again ([Main Window](#main-window) rule 2) are
  workarounds for the deferred first show, which the saved title bar
  and border sizes avoid. The monitor fitting, the quiet-period checks
  and the editor rules are ours either way.
- `wx.lib.agw.persist` (`PersistentFrame`) is pure Python: position,
  size and maximized through `SetPosition()`/`SetSize()`, nothing more
  than the tracker does.

### Other Toolkits

Checked 2026-09-27:

- Windows: `GetWindowPlacement()`/`SetWindowPlacement()` are the
  intended way to save and restore a window, in workspace
  coordinates, with the normal rect of a maximized or minimized
  window; wxMSW uses them.
- GNOME: save size, maximized and full screen only; "The position of
  the window is best left to the window manager". GTK 4 has no API to
  move a window at all.
- Qt: `saveGeometry()`/`restoreGeometry()` fit to the available
  screens, but on X11 "might not work because an invisible window does
  not have a frame yet", and "some window managers fail to implement"
  the way X offers around it.
- Wayland: applications cannot position windows; restoring is the
  compositor's job through `xdg-session-management`, which wxWidgets
  3.3.4 supports.

So restoring the position is simple where the system owns it (Windows,
macOS), and on X11 every toolkit works around the window manager and
the late frame, or gives it up.

### First Show on wxGTK

Measured on 2026-09-27 (Debian 13, GTK 3.24.49, wxPython 4.2.3,
wxWidgets 3.2.7, openbox), by reading GTK's own size with
`gtk_window_get_size()` at each step:

1. Before `Show()`, GTK holds the requested size (1000x700).
2. `Show()` only realizes the window: wxGTK postpones mapping the first
   decorated window until the window manager has reported the frame
   extents (title bar and borders).
3. Meanwhile GTK's size becomes 2x1 and wx reports a spurious 4x28
   (the (6, 28) of [PYTHON3_MIGRATION_2.md](PYTHON3_MIGRATION_2.md#window-position-tracking-with-aui)).
4. The window is mapped at GTK's natural size, 269x27, or at the
   minimum size when that is larger, and only then resized.

So GTK does not respect the size set before the first show, whatever
the minimum is. The requested position is lost on this path too: the
window maps at the window manager's spot, (80, 0) on openbox, while
editors that skip the deferral map where requested (measured
2026-09-27). wxGTK defers when its cached title bar height is 0
(`src/gtk/toplevel.cpp`, `Show()`), as for the first window of the
session. The position is not lost in GTK, which keeps a position set
before mapping and sends it with `PPosition` (`gtk_window_move()`,
`gtk_window_move_resize()` in `gtkwindow.c`): setting it again at the
first `EVT_SHOW`, while the deferred window is not mapped, makes it
map there ([Trials](#trials) 16). Once the frame extents are known, later windows (the
editors) map at the requested size. The minimum-size step in
[Main Window](#main-window) rule 2 turns this behaviour into the
requested size.

---

## What Did Not Work

Do not repeat these:

- Saving on every `EVT_MOVE`/`EVT_SIZE`: records spurious values from
  `LoadPerspective()`, `SendSizeEvent()` and GTK realization
  ([PYTHON3_MIGRATION_2.md](PYTHON3_MIGRATION_2.md#window-position-tracking-with-aui)).
- Delays with magic numbers (`wx.CallLater(500, ...)`) to skip those
  events: not deterministic (same section).
- Saving only on close, without corrections: the window manager's
  placement wins on X11 and the position is lost.
- Adding `USER_POS` from Python with `gtk_window_parse_geometry()` just
  before `Show()`: wxGTK rewrites the size hints, so it never reaches
  the X server (checked with `xprop WM_NORMAL_HINTS`).
- `Maximize()` before the first `Show()` on X11: the window manager
  maximizes it on the monitor it picks, not the saved one; on its own,
  un-maximizing also gives GTK's natural size ([Trials](#trials) 3, 7).
- Setting the minimum size only after the first show: the window maps
  at 269x27 instead ([Trials](#trials) 1).
- Starting minimized to hide the intermediate steps: the window manager
  animates the restore from the taskbar ([Trials](#trials) 5).
- Correcting on every event: stale events trigger more corrections, and
  a refused position is fought in a loop; correcting once per idle
  round still fought three times in quick succession
  ([Trials](#trials) 9).
- Waiting for the window to be active before it counts as placed: it
  never is when the user works in another window meanwhile
  ([Trials](#trials) 10).
- Correcting the window manager's first placement inside the event:
  while mapping wx reports 6x28, so `SetPosition()` also resized the
  window to the minimum and it bounced ([Trials](#trials) 15).
- `SetMinSize()` and `SetSizerAndFit()` on editor pages lock the
  editor's size ([PYTHON3_MIGRATION_1.md](PYTHON3_MIGRATION_1.md)).
- Slow resizing while dragging panel dividers: toolbar size loop, AUI
  live resize throttling and deferred column resizing
  ([PYTHON3_MIGRATION_3.md](PYTHON3_MIGRATION_3.md#aui-divider-drag-visual-feedback)).
- Hiding intermediate states with transparency: needs a compositor, so
  not on every desktop.

---

## Trials

All on 2026-09-27. Trials 0 to 6 under Xvfb with openbox, saved
geometry (300, 200) 1000x700, 2 or 3 runs each; the rest on the real
desktop: LXDE (openbox), two stacked 1920x1080 monitors, the laptop
below (primary, panel on the left) and an external one above. "Visible
states" are what `xwininfo` saw every 10 to 20 ms. Each resize lays out
and paints the panes, viewers and columns again (35 to 576 ms), a move
does not.

| # | Change | Result | Kept |
|---|--------|--------|------|
| 0 | Baseline | Minimum 600x400 at the window manager's spot, move, resize; in the log up to three more resets to 600x400 corrected back (ping-pong); ready after 445 to 830 ms. Saved maximized: four states, two intermediate resizes. | - |
| 1 | Minimum size set after placing | First frame 269x27 instead of 600x400: worse. | No |
| 2 | Requested size as the minimum until `EVT_SHOW` | First frame at the saved size, then one move; no ping-pong; ready after 350 to 420 ms. First run appears at the default size at once. | Yes |
| 3 | Saved maximized: `Maximize()` before `Show()`; check the position on the first un-maximize | One monitor: appears maximized at once, un-maximize restores the saved geometry. Two monitors (real desktop): maximized on the wrong monitor. | Not on X11 |
| 4 | Editor without a saved size keeps its fitted size | Fitted size is 226x297, raised to the 400x300 minimum and centered off by the difference: worse. | No |
| 5 | Start minimized, move, restore | The restore slides from the taskbar through ten positions in 150 ms: worse. | No |
| 6 | No corrections before the first `EVT_SHOW` | Same corrections, same ready time. | No |
| 7 | Trial 3 only where the monitor cannot be wrong; on X11 place first, then maximize | Every saved case, on either monitor, ends on its monitor. | Yes |
| 8 | `fit_to_monitors()` instead of dropping invalid geometry | Saved below the laptop, maximized: maximized on the laptop. Saved above the upper monitor: moved inside it. 2500x1300: reduced to 1920x1080. Partly off screen but reachable: kept exactly. | Yes |
| 9 | One correction per round, window manager accepted after three rounds | The refused (0, 0) on the upper monitor was corrected 18 times in 50 ms before; then once per round, three rounds. Still quick repeated attempts. | Replaced by 12 |
| 10 | Ready once placed by the window manager, not only once active | A check started while the user worked elsewhere never became ready and never maximized. | Replaced by 12 |
| 11 | Start minimized: no viewer focus while minimized; placed while minimized | Stays minimized (it was restored 150 to 180 ms after start, also on master). The restore lands on the saved position; saved maximized: restored there, then maximized. | Yes |
| 12 | Placement checked when quiet (300 ms), at most two attempts, then accepted; maximize the same way on every platform | Normal start: one move, checked, placed 0.9 s after show. Maximized: moved, maximized, placed 1.2 s after show. Refused (0, 0): two attempts 300 ms apart, then (80, 0) accepted, as wx then reports. Monitor gone: fitted, maximized there. Start minimized: placed while minimized, maximized on restore. A move after placement is kept. | Refined by 13 |
| 13 | For slow computers: first quiet period 1 s, then 500 ms, at least twice the slowest answer (up to 3 s); our own events not counted; three attempts; 10 s step limit | Normal: openbox answered after 243 ms, one move after 1 s, placed 1.7 s after show. Maximized: answer 288 ms, so 575 ms periods; placed 2.5 s after show. Refused: three attempts 500 ms apart, then accepted. Monitor gone and start minimized as in 12. | Yes |
| 14 | Direct placement on Windows and macOS ([Decisions](#decisions) 7): set before show, maximize before show, placed at once; macOS saves the frame size | Linux unchanged: normal, one move, placed 2.1 s after show; maximized on the laptop, placed 2.6 s after show. Windows and macOS not measured here. | Yes |
| 15 | Correct the window manager's first placement at once; layouts that change nothing (`SendSizeEvent()`) no longer restart the quiet period, which the app's own layouts stretched to 1.4 s | At once: extra resizes and bounces, see below. Ignoring those layouts: kept. | Partly |
| 16 | At the first show, if wx no longer reports the requested geometry, send the position again before the window is mapped | Normal: maps at the saved spot, no move, no attempt. Maximized: maps at the saved spot, maximized 1.1 s later. Refused: maps where openbox allows, three attempts, accepted. Start minimized: stays minimized, maximized on restore. No saved position: openbox places it. Editors (Xvfb with openbox, one at a time, closed 0.8 to 1.4 s after opening): the lost case came on the 6th open; the previous code showed that editor at openbox's default spot until it was closed, now it appears at its saved spot and never moves. | Yes |

High-frequency trace for trial 12 (the app's own `GetPosition()` and
`GetSize()` sampled every 5 ms, next to `xwininfo` on the real window):

- After the first show, wx reports the requested position until the
  window manager's placement arrives, 140 to 150 ms later.
- A maximize applies about 80 ms after the request; in between wx
  reports "maximized" with a wrong size (876x856).
- A resize from outside reaches wx up to 60 ms after the screen
  (layout and paint); a move about 3 ms after.
- The window became visible about 270 ms after the first show. With
  trial 12 it is visible at the window manager's spot for about 300 ms
  before the one move (openbox), with trial 13 about 1 s.

Trial 15 on the real desktop (normal start at (600, 250), maximized at
(300, 1300), a 2500x1300 rect the window manager refuses):

| Variant | Result |
|---|---|
| Correct the first placement at once, inside the event | While mapping wx reports 6x28, so `SetPosition()` also resized the window to the 600x400 minimum: a second attempt for the size, and bounces between (80, 0) and the saved spot. The old ping-pong. |
| At once, after the event (`wx.CallAfter`) | One move 120 to 160 ms after the placement, seen at the window manager's spot for about 90 ms; still races with mapping if it runs before the size settles. |
| Debounce only, layouts that change nothing ignored (kept) | Normal: one move 1.0 s after show, placed 1.9 s. Maximized: one move, then maximized, placed 2.5 s. Refused: three attempts 500 ms apart, then accepted. No extra resize. |

The user's tests on the real desktop, each step a quit and reopen:

| Saved | Reopened |
|-------|----------|
| Maximized on the laptop monitor | Normal size there, maximized 0.2 to 0.4 s later |
| Maximized on the upper monitor | Normal size there, maximized 0.1 s later |
| Normal, 1252x858, upper monitor | Same place and size |
| Normal, moved to the laptop monitor | Same place and size |
| Editor saved on the other monitor than the main window | Centered on the main window's monitor ([Editors](#editors) rule 3) |
| Editor resized and moved, closed, reopened (twice) | Same place and size |

Before trial 7 the user found a window maximized on the laptop coming
back maximized on the upper monitor; that is what trial 7 fixed. The
first spot openbox chose was corrected before it became visible.

---

## Known Issues

| Case | What the user sees |
|------|--------------------|
| Saved maximized | Normal size at the saved spot for about 1 s, then maximized: maximize waits until the placement is quiet. |
| Refused position (openbox keeps windows out of the panel's width) | Where openbox allows; three attempts 500 ms apart, then accepted. |
| Editor, first open of a set of tabs | 400x300, tabs scrolled and fields cut off. |

Other issues:

- Editors after closing one: measured under Xvfb with openbox
  ([Trials](#trials) 16); on the real desktop still to confirm.
- `MainWindowMaximizedTest` waits for the placement to be quiet, with
  the window not minimized (unloaded settings start minimized); plain
  `xvfb-run` has no window manager to grant the maximize, so it is
  skipped there.
- Unused settings keys (see [Settings](#settings)).
- The scheduler blocked the UI thread 60 ms (200 tasks) to 600 ms
  (5000 tasks) every second, so resizing stuttered with large files
  whatever the geometry code did. Since the master scheduler refactor
  its full pass runs only at the seconds that change something, about
  once a minute with typical files
  ([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#cost-after)).

---

## Tests

Automated (`tests/unittests/widgetTests/WindowDimensionsTrackerTest.py`):
`fit_to_monitors()` for the two-monitor layout (kept, removed monitor,
too large, off every monitor, panel), the minimum-size step, that moves
and resizes are kept only once placed, and the placement steps with a
fake window whose platform may refuse moves or maximizing (one
correction places it; refused moves and maximize are tried three times,
then accepted; maximize follows placement; a slow answer lengthens the
quiet period; a layout that changes nothing is not an answer; a lost
request is sent again before the show, with a step aside when wx
already holds the position; a window maximized meanwhile is placed; the
step limit keeps a saved maximized state), direct placement (set and
maximized before show, placed at once, no quiet checks; started
minimized, maximized when restored), no saved position keeping the
saved maximized, Wayland (sizes and maximized kept, positions left
alone), and the editor rules on two fake monitors.

What the window manager does (placement, visible steps, monitors,
animations) needs a real desktop. Manual checklist, reading the
`[GEOMETRY]` log:

1. Normal start on each monitor: same place and size, no move.
2. Maximized on each monitor, quit, reopen: maximized on that monitor.
3. Un-maximize after 2: the saved normal geometry.
4. Monitor removed (or saved rect on no monitor): nearest monitor, same
   size and state.
5. Saved size larger than the monitor: reduced to it.
6. Start minimized "Always": stays minimized; restore lands on the
   saved position; saved maximized is maximized after the restore.
7. Editor: resize, move, close, reopen; saved on the other monitor:
   centered on the main window's monitor.
8. Start while typing in another window: the window still gets placed
   and maximized.
9. Windows and macOS: 1 to 7, each without a visible move or resize;
   on macOS the size stays the same over several restarts.
10. Editor opened, closed after about 1 s, opened again, several
    times: every editor appears on the main window's monitor at once,
    never at the window manager's spot first.

### Testing in Progress

Status 2026-09-27; update it as each one is done.

| Test | Checklist | Status |
|---|---|---|
| Editor reopened after a close about 1 s after opening, real desktop | 10 | Passed under Xvfb with openbox ([Trials](#trials) 16); real desktop to test |
| Main window on the real desktop: normal, maximized, each monitor | 1 to 3 | Checked with separate settings; to test |
| Start minimized "Always", saved maximized | 6 | Checked; to test |
| Editor rules: other monitor, maximized there, too large | 7 | To test |
| Windows | 9 | To test |
| macOS, including the size over several restarts | 9 | To test |
| Another X11 window manager (KWin or Mutter) | 1 to 7, 10 | To test |
| Wayland: sizes and maximized kept, positions left alone | 1, 2, 6 | To test |

---

## Planned Refactoring

**Status:** trials 2, 7, 8, 11, 13, 14, 16 and part of 15 are in the
code. Goal: reopen the main window and the editors at their last size
and position without visible jumps, and adapt to monitor changes the
way current desktop apps do.

### Placement Strategy

Chosen 2026-09-27 and in the code ([Trials](#trials) 12 to 14): on
X11 and Wayland observe until quiet, then act, at most three times,
then accept ([Main Window](#main-window) rules 3 to 7); on Windows and
macOS set once ([Direct Placement](#direct-placement)). Goals:

1. One observed path for every platform that does not place at once;
   window managers differ only in what they allow
   ([Platform Matrix](#platform-matrix)).
2. Bounded work: no loops, no polling, at most three attempts, each
   checked only once quiet.
3. Accept the platform's decision; never fight it.
4. Never lose the saved state ([Decisions](#decisions) 2).
5. Independent of focus, of any one window manager and of the
   computer's speed.

No platform tells an application "placement is done" in a way wxPython
exposes. Windows and macOS apply a position or size during the call,
so there is nothing to observe. An X11 window manager answers later, each in its own way; focus comes
from it after placing, but not when the user works in another window
or focus stealing prevention is on, so focus can only be a hint, never
a condition ([Trials](#trials) 10). Wayland has a configure handshake,
but GTK keeps it internal. What every platform shows is the geometry
changing and then no longer changing, so that is what is observed.

What could go wrong, and how it is handled:

| Situation | Without care | Handled by |
|---|---|---|
| Slow or loaded computer: the window manager answers after the quiet period | wx still reports the requested geometry, so it looks right; the late placement is then kept as if the user had moved the window | A long first quiet period (1 s) and periods of at least twice the slowest answer seen (rule 4) |
| The app itself is busy (layout and paint took 50 to 576 ms) | Events are handled late | Handled events restart the quiet period, so a busy app waits longer |
| The window manager refuses a position or size | Fighting it, as the old code did (18 moves in 50 ms) | Three attempts, each a full quiet period apart, then accepted |
| The window manager keeps adjusting | Never quiet | The 10 s step limit, then accepted |
| The user drags the window at once | The drag corrected back | Moves keep restarting the quiet period until the step limit; a drag after placement is kept |
| wx reports a size in between (876x856 while maximizing) | Checked too early | Only checked once quiet |

Other options, kept for later:

| Option | How | Trade-offs |
|---|---|---|
| B. Correct at once, settle to accept | Correct on the first differing position after the show, usually before the window is visible; the quiet period only confirms. | Tried in trial 15: inside the event it resized to the minimum and bounced; after the event it races with mapping. Only with a check that the size has settled. |
| C. Claim the position (X11) | Mark the position as user specified before the first show, as Qt and Chromium do. | Needs a GTK-level workaround, since wxGTK offers no way; X11 only. Less needed since the lost request is sent again (trial 16): GTK already sends `PPosition`. |
| D. wxWidgets' own geometry saving | `SaveGeometry()`/`RestoreToGeometry()` ([wxWidgets Facilities](#wxwidgets-facilities)). | Not usable from wxPython 4.2.3; revisit with wxWidgets 3.3, which would also bring Wayland session restore. |

A quiet period cannot tell the window manager's moves from the
user's: a drag in the first moments ends in the step limit (rule 7) and
is accepted.

Left:

- **Editors:** decide a first-open size, the fitted size is too small.
  Apply `fit_to_monitors()` to them.
- **Tracker state:** once placed, record the normal rect only while the
  window is shown and neither maximized nor iconized;
  `fit_to_monitors()` already carries the restore rules.
- **Floating panes:** use `fit_to_monitors()` from the AUI code (see
  [AUI.md](AUI.md#planned-fit-floating-panes-to-the-monitors)).
- **Maximized after start minimized:** maximize while minimized, to
  save the resize after the restore.
- **DPI:** check which DPI awareness the Windows builds run with
  (`application.py` only logs it). If per-monitor, store sizes in DIPs
  (`ToDIP()`/`FromDIP()`) so a window moved between monitors with
  different scaling keeps its size. GTK already uses logical pixels.
- `iconized`: use it or remove it, with the designer's decision on
  "If it was iconized last session" ([Start Minimized](#start-minimized)).

### Not Yet Examined

- Jitter while dragging a window border; the trials are about
  reopening. Candidates: the scheduler's passes above, and
  `MainWindow.onResize()`, which sets the toolbar's size and minimum
  sizes on every `EVT_SIZE`.
- Other window managers (KWin, Mutter on X11) may honour the program
  specified position, which would remove the move there.
- Seen once under Xvfb only: opening an editor left a small window
  showing a "Description" tab at the top left of the screen. Check on
  a real desktop.

### How It Was Measured

The real app from the repository, with `--ini` and its own
`XDG_CONFIG_HOME`/`XDG_DATA_HOME` and a scratch task file, on the real
desktop. The `[window]` section is reset before each run (the app
saves its geometry on exit). The app logs every step
([Tracing](#tracing)); `xwininfo -id <window>` polled every 10 to 20 ms
shows the visible states (find the window with
`xdotool search --all --pid <pid> ...`: without `--all` the conditions
are or-ed and another Task Coach matches), `xprop WM_NORMAL_HINTS` the
hints that reached the X server. GTK's own size was read with
`gtk_window_get_size()`, and the cause of the restore after start
minimized with a stack trace on `EVT_ICONIZE`, both in temporary traces
not kept.

Editors need key presses (Insert opens a new task, Escape closes it):
a locked desktop grabs the keyboard, and GTK ignores keys sent to a
window with `xdotool key --window`, so the editor runs of trial 16 used
`Xvfb` with openbox and the desktop's openbox configuration, one editor
at a time.

Trials 0 to 6 ran under `Xvfb` plus `openbox`. Results there are only
indicative: timing differs from a real desktop, and on Debian 13 Xvfb
cannot simulate several monitors (it ignores extra `-screen`s with
`+xinerama`, and `xrandr --setmonitor` has no effect), which is how
trial 3 missed the wrong-monitor case.

### Next Steps

1. Test on Windows and macOS (direct placement; on macOS the frame
   size), and on X11 desktops other than LXDE ([Tests](#tests)
   checklist).
2. Where wxPython 4.3 or later is used, try `SaveGeometry()`/
   `RestoreToGeometry()` with a `GeometryStore` backed by the settings
   ([wxWidgets Facilities](#wxwidgets-facilities)); once Linux has it
   too, drop the minimum-size step and the resend.
3. Report upstream that wxGTK's deferred first show loses a position
   set before `Show()` ([First Show on wxGTK](#first-show-on-wxgtk)).
4. The items under Left, editors first.

---

## References

- [wxWidgets/Phoenix Issue #2214](https://github.com/wxWidgets/Phoenix/issues/2214) - Frame position problem on Linux
- [wxWidgets/Phoenix Issue #1217](https://github.com/wxWidgets/Phoenix/issues/1217) - GetHandle() returns XID
- [GTK gtk_window_move() docs](https://docs.gtk.org/gtk3/method.Window.move.html) - WM ignores initial positions
- [Gdk.WindowHints](https://docs.gtk.org/gdk3/flags.WindowHints.html) - USER_POS hint
- [Openbox place.c](https://github.com/mcz/openbox/blob/master/openbox/place.c) - keeps program and user positions unless per-app settings say otherwise
- [KWin x11window.cpp](https://invent.kde.org/hoshinolina/kwin/-/blob/v5.26.4/src/x11window.cpp) - `hasPosition()` and `placementDone` in `manage()`
- [Zed issue #64447](https://github.com/zed-industries/zed/issues/64447) - Mutter ignores the position without USPosition; static gravity
- [DisplayXR issue #729](https://github.com/DisplayXR/displayxr-runtime/issues/729) - Mutter reported to veto client geometry
- [Xlib WM_NORMAL_HINTS](https://tronche.com/gui/x/xlib/ICC/client-to-window-manager/wm-normal-hints.html) - USPosition, PPosition
- [Qt: Restoring a Window's Geometry](https://doc.qt.io/qt-6/restoring-geometry.html) and [X11 caveats](https://doc.qt.io/archives/qtextended4.4/geometry.html)
- [xdg-session-management](https://wayland.app/protocols/xx-session-management-v1) - Wayland window restore protocol, and [status report](https://itsfoss.com/news/wayland-session-management/)
- [GNOME: saving window state](https://developer.gnome.org/documentation/tutorials/save-state.html) - size and maximized only
- [WINDOWPLACEMENT](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-windowplacement) and [The Old New Thing](https://devblogs.microsoft.com/oldnewthing/20040707-00/?p=38523) - saving and restoring on Windows
- [Phoenix etg/toplevel.py](https://github.com/wxWidgets/Phoenix/blob/master/etg/toplevel.py) - `GeometryStore` bound as abstract; [wxWidgets 3.3 toplevel.h](https://github.com/wxWidgets/wxWidgets/blob/master/interface/wx/toplevel.h)
- [wxTopLevelWindow](https://docs.wxwidgets.org/latest/classwx_top_level_window.html) - `SaveGeometry()`, `RestoreToGeometry()`; [tlwgeom.h 3.2.7](https://github.com/wxWidgets/wxWidgets/blob/v3.2.7/include/wx/gtk/private/tlwgeom.h), [generic](https://github.com/wxWidgets/wxWidgets/blob/v3.2.7/include/wx/private/tlwgeom.h), [master (Wayland)](https://github.com/wxWidgets/wxWidgets/blob/master/include/wx/gtk/private/tlwgeom.h)
