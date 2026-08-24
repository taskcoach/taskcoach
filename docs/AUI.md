# AUI (Advanced User Interface)

This document covers AUI-related topics for Task Coach, which uses wxPython's AGW AUI library (`wx.lib.agw.aui`) to manage dockable panels/viewers.

## Contents

1. [Layout Persistence](#layout-persistence)
   - [Pane Names Carry Instance Numbers](#pane-names-carry-instance-numbers)
   - [AUI-Generated Panes](#aui-generated-panes)
2. [Sash Cursor Seep-Through Fix](#sash-cursor-seep-through-fix)
3. [Related Documentation](#related-documentation)

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
    perspective = self.settings.get("view", "perspective")
    try:
        self.manager.LoadPerspective(perspective)
    except Exception:
        self.manager.LoadPerspective("")  # Fall back to default
```

### Pane Names Carry Instance Numbers

A pane's name is `viewer.settingsSection()`, which appends the viewer's
instance number for every instance after the first: `taskviewer`,
`taskviewer1`, `taskviewer2`. `NumberedInstances` (in
`patterns/metaclass.py`) hands out the lowest number not held by a live
instance.

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

### Related Files

| File | Purpose |
|------|---------|
| `taskcoachlib/gui/mainwindow.py` | `__restore_perspective()`, `__save_perspective()`, `__save_viewer_counts()` |
| `taskcoachlib/gui/viewer/base.py` | `settingsSection()` - generates unique pane names |
| `taskcoachlib/gui/viewer/factory.py` | `_instance_numbers_to_add()` - reads instance numbers back from the perspective |
| `taskcoachlib/patterns/metaclass.py` | `NumberedInstances` - assigns instance numbers, honours an explicit one |
| `taskcoachlib/gui/viewer/container.py` | `addViewer()` - adds panes to AUI manager |
| `taskcoachlib/widgets/frame.py` | `addPane()` - configures AuiPaneInfo |
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

## Related Documentation

- **[AUI Wayland Issues](AUI_WAYLAND_ISSUES.md)** - Docking problems on Wayland display servers
- **[Window Position Persistence Analysis](WINDOW_POSITION_PERSISTENCE_ANALYSIS.md)** - Related window position tracking

## External References

- [wxPython AUI Manager Documentation](https://docs.wxpython.org/wx.lib.agw.aui.framemanager.AuiManager.html)
- [wxPython AUI Discussion Forum](https://discuss.wxpython.org/t/wx-aui-loadperspective-problems/23698)
