# AUI (Advanced User Interface)

This document covers AUI-related topics for Task Coach, which uses wxPython's AGW AUI library (`wx.lib.agw.aui`) to manage dockable panels/viewers.

## Contents

1. [Layout Persistence](#layout-persistence)
   - [Pane Names Carry Instance Numbers](#pane-names-carry-instance-numbers)
   - [AUI-Generated Panes](#aui-generated-panes)
   - [Planned: Fit Floating Panes to the Monitors](#planned-fit-floating-panes-to-the-monitors)
2. [Sash Cursor Seep-Through Fix](#sash-cursor-seep-through-fix)
3. [System Colour Change Event](#system-colour-change-event)
4. [Destroy Event](#destroy-event)
5. [Managers Never Freed](#managers-never-freed)
6. [Page Painted Over the Tabs](#page-painted-over-the-tabs)
7. [Captions Drawn at the Next Paint](#captions-drawn-at-the-next-paint)
8. [Related Documentation](#related-documentation)

---

## Layout Persistence

### Overview

Task Coach persists and restores panel layouts across application restarts. The layout (which panels are open, their positions, sizes, docked/floating state) is saved when the application closes and restored on startup.

### How It Works

**Saving Layout:**
When Task Coach closes, it calls `AuiManager.SavePerspective()` which encodes the entire UI layout into a string. This string is stored in `TaskCoach.ini` under `[view] perspective`.

Each viewer/panel has a unique name derived from:
- Base type name (e.g., `categoryviewer`, `effortviewer`, `taskviewer`)
- Instance number for multiple viewers of same type (e.g., `categoryviewer1`, `categoryviewer2`)

**Restoring Layout:**
On startup, Task Coach calls `AuiManager.LoadPerspective()` with the saved string. AUI matches pane names between the saved perspective and the current windows.

### Best Practice: Trust AUI's Built-in Mismatch Handling

**Important:** Do NOT implement custom validation of the perspective string before loading.

Per the [wxPython AUI documentation](https://docs.wxpython.org/wx.lib.agw.aui.framemanager.AuiManager.html):

> "All currently existing panes that have an object in 'perspective' with the same name ('equivalent') will receive the layout parameters of the object in 'perspective'. Existing panes that do not have an equivalent in 'perspective' remain unchanged, objects in 'perspective' having no equivalent in the manager are ignored."

This means AUI already handles all mismatch scenarios gracefully:

| Scenario | AUI Behavior |
|----------|--------------|
| Saved pane no longer exists | Ignored (no error) |
| New pane not in saved layout | Uses default position |
| Viewer count changed | Each pane matched by name individually |
| Viewer type renamed between versions | Old entries ignored, new ones use defaults |

### Why Custom Validation Is Harmful

A previous implementation tried to validate viewer counts by parsing the perspective string:

```python
# DON'T DO THIS - causes more bugs than it prevents
def __perspective_and_settings_viewer_count_differ(self, viewer_type):
    perspective_count = perspective.count("name=%s" % viewer_type)
    settings_count = settings.getint("view", "%scount" % viewer_type)
    return perspective_count != settings_count
```

This approach had multiple failure modes:

1. **Substring collisions**: `"effortviewer"` matched `"effortviewerforselectedtasks"`
2. **Numbered instances missed**: Pattern didn't match `categoryviewer1`, `categoryviewer2`, etc.
3. **False invalidation**: Any mismatch discarded the ENTIRE saved layout

The correct approach is to simply load the perspective and let AUI handle it:

```python
# DO THIS - simple and robust
def __restore_perspective(self):
    perspective = settings.view.perspective
    try:
        self.manager.LoadPerspective(perspective)
    except Exception:
        self.manager.LoadPerspective("")  # Fall back to default
```

### Pane Names Carry Instance Numbers

A pane's name is `viewer.settingsSection()`, which appends the viewer's
instance number for every instance after the first: `taskviewer`,
`taskviewer1`, `taskviewer2`. `NumberedInstances` (in
`patterns/metaclass.py`) hands out the lowest number not held by a
registered instance. An instance stays registered until it is garbage
collected, so a closed viewer can hold its number for a while.

This matters because the layout is persisted in two places that encode
different things:

| What | Where | Encodes |
|------|-------|---------|
| Pane layout | `[view] perspective` | Pane **names**, so instance numbers |
| Viewer set | `[view] <type>count` | **Cardinality** only |

Closing any viewer other than the highest-numbered one leaves a gap in
the names. Close `taskviewer1` of three and the surviving panes are
`taskviewer` and `taskviewer2`, while the count is 2. A count cannot
express a gap, so recreating from it alone yields `taskviewer` and
`taskviewer1`: AUI then ignores the saved `taskviewer2` (no window with
that name) and leaves the new `taskviewer1` at its default position.
Part of the layout silently fails to restore.

**Therefore: the perspective is the source of truth for which instance
numbers to recreate**, not the count.
`addViewers._instance_numbers_to_add()` reads the numbers back out of
the perspective and passes each one explicitly to the viewer
constructor; `NumberedInstances` honours an explicitly supplied
`instanceNumber` instead of assigning the lowest unused one. The count
remains only as a fallback for viewer types the perspective has no panes
for, such as on a first run.

The name match is anchored on the separator (`name=<section>(\d*)`
followed by `;`, `|`, or end of string) so that `effortviewer` does not
also match `effortviewerforselectedtasks`. That substring collision is
the same trap described in "Why Custom Validation Is Harmful" above.

### AUI-Generated Panes

Dragging panes together creates a tab group, and AUI adds a pane of its
own named `__notebook_0`, `__notebook_1`, and so on, with the tabbed
viewers becoming notebook pages referring to it by `notebook_id`. These
names appear in the saved perspective but match no window we create.

**They are recreated by `LoadPerspective` itself and need no handling.**
Verified against wxPython 4.2.0 / AGW: a 13-pane layout containing an
auto-notebook restored with every pane's dock direction, layer, row,
position, proportion and size identical to what was saved. The manager
gained the `__notebook_0` pane during the load.

This is worth stating because upstream reports say otherwise. A
[wxPython-users thread](https://groups.google.com/g/wxpython-users/c/HmNe0lvnwMY)
describes panes dragged into a spontaneously generated notebook
disappearing on restore, and the AGW maintainer confirmed it as a bug.
That does not reproduce on the version in use here, so do not spend time
working around it, and do not treat `__notebook_*` entries with no
matching window as evidence of a problem.

### Perspective String Format

The perspective string uses this format:
- Panes separated by `|`
- Attributes within a pane separated by `;`
- Key attributes: `name`, `caption`, `state`, `dir`, `layer`, `row`, `pos`, `prop`, `bestw`, `besth`, etc.

Example:
```
name=taskviewer;caption=Tasks;state=67372030;dir=5;layer=0;row=0;pos=0;...
|name=categoryviewer;caption=Categories;state=67372030;dir=4;layer=0;...
|name=categoryviewer1;caption=Categories;state=67372030;dir=2;layer=0;...
```

### Pane Naming Convention

Task Coach viewer names follow this pattern:

| Viewer Type | First Instance | Additional Instances |
|-------------|----------------|----------------------|
| Task Viewer | `taskviewer` | `taskviewer1`, `taskviewer2`, ... |
| Category Viewer | `categoryviewer` | `categoryviewer1`, `categoryviewer2`, ... |
| Effort Viewer | `effortviewer` | `effortviewer1`, `effortviewer2`, ... |
| Effort (Selected) | `effortviewerforselectedtasks` | `effortviewerforselectedtasks1`, ... |
| Note Viewer | `noteviewer` | `noteviewer1`, `noteviewer2`, ... |
| Calendar Viewer | `calendarviewer` | `calendarviewer1`, `calendarviewer2`, ... |

The name is determined by `viewer.settingsSection()` in `taskcoachlib/gui/viewer/base.py`.

### Planned: Fit Floating Panes to the Monitors

The perspective stores each floating pane's position and size, and
`LoadPerspective()` restores them as saved, whatever the current
monitors: a pane saved on a monitor that is gone can open off screen.
Plan: after `LoadPerspective()`, pass each floating pane's rect through
the shared `fit_to_monitors()`
([WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md#planned-refactoring)) and set
the result with `FloatingPosition()` and `FloatingSize()` before
`Update()`. This adapts the loaded geometry only; it does not validate
the perspective string
([Best Practice](#best-practice-trust-auis-built-in-mismatch-handling)).

### Related Files

| File | Purpose |
|------|---------|
| `taskcoachlib/gui/mainwindow.py` | `__restore_perspective()`, `__save_perspective()`, `__save_viewer_counts()` |
| `taskcoachlib/gui/viewer/base.py` | `settingsSection()` - generates unique pane names |
| `taskcoachlib/gui/viewer/factory.py` | `_instance_numbers_to_add()` - reads instance numbers back from the perspective |
| `taskcoachlib/patterns/metaclass.py` | `NumberedInstances` - assigns instance numbers, honours an explicit one |
| `taskcoachlib/gui/viewer/container.py` | `add_viewer()` - adds panes to AUI manager |
| `taskcoachlib/widgets/frame.py` | `add_pane()` - configures AuiPaneInfo |
| `taskcoachlib/config/settings.py` | Stores perspective in INI file |

---

## Sash Cursor Seep-Through Fix

### Problem

When a dialog or popup window is positioned over the main window's sash areas, the sash resize cursor incorrectly "seeps through" and appears when hovering over empty areas of the foreground window. Controls in the dialog block this correctly, but empty panel areas do not.

**Key observation:** This is purely a visual cursor artifact - the sash cannot actually be dragged through the popup window.

### Root Cause

`wx.lib.agw.aui.AuiManager.OnSetCursor()` receives `EVT_SET_CURSOR` events and performs hit testing on sash rectangles without checking if another window is occluding the frame. Controls block the cursor seep-through because they handle `EVT_SET_CURSOR` themselves and set their own cursor. Empty areas let the event propagate to the main frame.

### Solution

Make dialogs handle `EVT_SET_CURSOR` the same way controls do - set a standard cursor without calling `Skip()`. This prevents the event from propagating to the main window's AuiManager.

Implemented via monkey-patch on `wx.Dialog` at application startup in `taskcoachlib/widgets/__init__.py`.

### Related Files

| File | Purpose |
|------|---------|
| `taskcoachlib/widgets/__init__.py` | `_install_dialog_cursor_fix()` - patches wx.Dialog |
| `wx/lib/agw/aui/framemanager.py` | System file - `OnSetCursor()` that causes the issue |

---

## System Colour Change Event

`AuiManager` is pushed onto its window's event handler stack and handles
`EVT_SYS_COLOUR_CHANGED` without calling `Skip()`, so the window's own
handlers and its children never see the event. The main window's
manager is a subclass that skips it, so `MainWindow` can follow system
light/dark switches (see [SETTINGS.md](SETTINGS.md#system-theme-changes)).
The manager inside each AGW `AuiNotebook` (editor pages, docked
notebooks) still consumes it.

### Related Files

| File | Purpose |
|------|---------|
| `taskcoachlib/widgets/frame.py` | `_AuiManager` - skips `EVT_SYS_COLOUR_CHANGED` |
| `wx/lib/agw/aui/framemanager.py` | System file - `OnSysColourChanged()` without `Skip()` |

---

## Destroy Event

`AuiManager.OnDestroy()` handles `EVT_WINDOW_DESTROY` of its managed
window without `Skip()`. The main window removes its manager in
`onClose()` before it is destroyed, so its own destroy handlers run;
an `AuiNotebook`'s manager (the task editor's pages) stays, so
handlers bound on the notebook never run. Neither the crash guard's
timer watch ([CRASH_GUARD.md](CRASH_GUARD.md)) nor the Publisher's
unsubscribe on destroy covers a notebook: a timer it owns ticks into
freed memory once it is gone. The app's calls go through
`patterns.later`, which checks the owner when each call is due
([DEFERRED_CALLS.md](DEFERRED_CALLS.md)).

---

## Managers Never Freed

An `AuiManager` binds its handlers to itself, so nothing frees it
([CRASH_GUARD.md](CRASH_GUARD.md#event-handlers-that-are-not-windows)),
nor what it holds. Besides the main window's, Task Coach has one in
each floating view's frame, in each notebook AUI makes for views
dropped onto one another, and in the notebook of every editor and of
Preferences. Each one closed stayed in memory with its window's
objects: a closed floating view, a closed editor's or Preferences'
pages. On master too: 11 MB after opening and closing 20 task
editors.

`free_with_window()` (`taskcoachlib/widgets/frame.py`) deletes a
manager once its window is destroyed. `_AuiManager` applies it in
AUI's factory methods, `CreateFloatingFrame()` and
`CreateNotebook()`; `widgets.Notebook` applies it to itself. While
pushed onto its window, the manager receives the window's destroy
event, and ends it; once removed, the window does. A top-level
window's event comes after its wrapper is deleted.

`_AuiManager.ClosePane()` also:

- removes a floating pane's frame manager from the frame before AUI
  destroys it, as AUI's `DetachPane()` does. Reset window layout with
  a floating view logged `wxAssertionError ... any pushed event
  handlers must have been removed`.
- clears AUI's drag state (`_action_window`, `_action_pane`) when it
  holds the closed pane: the pane whose caption was clicked last stays
  there until the next click.

A pane docked by dragging leaves a copy of its pane info in the drag
state, with its old floating frame, until the next caption click or
until the pane closes.

---

## Page Painted Over the Tabs

### Problem

On GTK 3, a task editor page shown for the first time could draw
widgets over the tab row until something repainted the tabs: the
Progress page's percentage control and slider, the Effort page's
details dropdown, and the Search box of the Effort, Notes and
Attachments pages (at the row's empty right end, so easy to miss).
Seen with the editor maximized or resized.

### Root Cause

`AuiNotebook.SetSelection()` shows the page (`SetActivePage()`), then
paints at once (`Update()` in `AuiTabFrame.DoSizing()` and after
setting the tab fonts). GTK 3 places a shown widget only at the next
frame, so that paint drew the page unplaced, at the notebook's top left
over the tabs. Placing it then repainted nothing there: unplaced, the
page counted as 1x1. Only widgets with a size drew: GTK sizes a hidden
widget only when wx resizes it during a window layout (maximizing,
resizing), so only the widgets that stretch with the notebook (the
Progress slider and dropdown, the viewers and their toolbars). Fixed
size widgets stayed 1x1 and drew nothing; the Prerequisites and
Categories pages create theirs when first selected; a page shown once
keeps its place.

### Solution

`Notebook.SetSelection()` freezes the notebook for the call, so the
forced paints skip it and the page draws at the next frame, placed.
Found with the geometry trace ([DEVELOPMENT.md](DEVELOPMENT.md#diagnosing)).

### Related Files

| File | Purpose |
|------|---------|
| `taskcoachlib/widgets/notebook.py` | `Notebook.SetSelection()` - freezes the notebook |
| `wx/lib/agw/aui/auibook.py` | System file - `SetSelection()`, `AuiTabFrame.DoSizing()` |

---

## Captions Drawn at the Next Paint

### Problem

Making another view active froze the window for a second or more with
all views open: a click from one list into another, View > Activate
next viewer, Ctrl+PgDn (P160 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues)).

### Root Cause

AGW's `RefreshCaptions()`, run on each activation, repaints the
window at once (`Update()`) after marking each caption, so seven
views cost seven full repaints, about 0.1 s each on Xvfb and more on a
loaded machine. A switch from the menu or the keys runs it twice: the
view taking the focus activates its pane again.

### Solution

`_AuiManager.RefreshCaptions()` marks the captions only; they are
drawn at the next paint, a moment later. Its other callers (a
notebook tab's caption, a floating view activated, a caption drag)
need no more.

### Related Files

| File | Purpose |
|------|---------|
| `taskcoachlib/widgets/frame.py` | `_AuiManager.RefreshCaptions()` - no repaint at once |
| `wx/lib/agw/aui/framemanager.py` | System file - `RefreshCaptions()`, `ActivatePane()` |

---

## Related Documentation

- **[Wayland Issues](WAYLAND_ISSUES.md#aui-docking)** - Docking problems on Wayland display servers
- **[Window Geometry](WINDOW_GEOMETRY.md)** - Size and position of the main window and editors

## External References

- [wxPython AUI Manager Documentation](https://docs.wxpython.org/wx.lib.agw.aui.framemanager.AuiManager.html)
- [wxPython AUI Discussion Forum](https://discuss.wxpython.org/t/wx-aui-loadperspective-problems/23698)
