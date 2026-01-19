# AUI (Advanced User Interface)

This document covers AUI-related topics for Task Coach, which uses wxPython's AGW AUI library (`wx.lib.agw.aui`) to manage dockable panels/viewers.

## Contents

1. [Layout Persistence](#layout-persistence)
2. [Related Documentation](#related-documentation)

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
| `taskcoachlib/gui/mainwindow.py` | `__restore_perspective()`, `__save_perspective()` |
| `taskcoachlib/gui/viewer/base.py` | `settingsSection()` - generates unique pane names |
| `taskcoachlib/gui/viewer/container.py` | `addViewer()` - adds panes to AUI manager |
| `taskcoachlib/widgets/frame.py` | `addPane()` - configures AuiPaneInfo |
| `taskcoachlib/config/settings.py` | Stores perspective in INI file |

---

## Related Documentation

- **[AUI Wayland Issues](AUI_WAYLAND_ISSUES.md)** - Docking problems on Wayland display servers
- **[Window Position Persistence Analysis](WINDOW_POSITION_PERSISTENCE_ANALYSIS.md)** - Related window position tracking

## External References

- [wxPython AUI Manager Documentation](https://docs.wxpython.org/wx.lib.agw.aui.framemanager.AuiManager.html)
- [wxPython AUI Discussion Forum](https://discuss.wxpython.org/t/wx-aui-loadperspective-problems/23698)
