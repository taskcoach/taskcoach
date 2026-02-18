# Toolbar

Toolbar architecture: rendering, sizing, perspective serialization, and
customization dialog.

## Table of Contents

- [TODO](#todo)
- [Architecture](#architecture)
- [Icon Sizes](#icon-sizes)
- [Perspective Serialization](#perspective-serialization)
- [Toolbar Customization Dialog](#toolbar-customization-dialog)
- [File Reference](#file-reference)
- [See Also](#see-also)

---

## TODO

1. **Replace sentinel types with named constants for separator/spacer.**
   The toolbar command list uses `None` to represent a separator and the bare
   integer `1` to represent a spacer. These sentinels are checked via
   `uiCmd is None` and `isinstance(uiCmd, int)` in at least 6 places across
   `toolbar.py`, `dialog/toolbar.py`, and `uicommandcontainer.py`. This is
   fragile and unclear. Replace with named sentinel objects (e.g.
   `SEPARATOR = object()` and `SPACER = object()`) or a small enum. The
   convention originates in `UICommandContainerMixin.appendUICommands()` which
   dispatches `None` to `AppendSeparator()` and `int` to
   `AppendStretchSpacer(uiCommand)`. The perspective serialization
   (`_filterCommands`, `perspective()`) also encodes them as the strings
   `"Separator"` and `"Spacer"` in the comma-separated perspective format.

---

## Architecture

The toolbar is built on `wx.lib.agw.aui.AuiToolBar`. Two classes layer
on top:

- **`_Toolbar`** — adapter subclass that bridges the old `AddLabelTool` API
  to the current `AuiToolBar.AddTool`, handles disabled bitmap generation
  (greyscale conversion), and manages bitmap size via `SetToolBitmapSize`.

- **`ToolBar`** — the real toolbar. Owns a list of `UICommand` objects
  (plus `None`/`int` sentinels for separator/spacer — see TODO #1). Loads
  and saves a "perspective" string to settings. Supports runtime
  customization via the toolbar editor dialog.

- **`MainToolBar`** — thin subclass for the AUI-managed main window toolbar.

---

## Icon Sizes

All toolbars use `LIST_ICON_SIZE` (16px) except the main toolbar, which
has three user-selectable sizes.

### Constants

- **`TOOLBAR_ICON_SIZE`** — `toolbar.py` — alias for `LIST_ICON_SIZE`.
  Used by viewer-embedded toolbars (`viewer/base.py`).
- **`MAIN_TOOLBAR_ICON_SIZE_SMALL`** (16) — `config/defaults.py`
- **`MAIN_TOOLBAR_ICON_SIZE_MEDIUM`** (22) — `config/defaults.py`
- **`MAIN_TOOLBAR_ICON_SIZE_LARGE`** (32) — `config/defaults.py`
- **`MAIN_TOOLBAR_ICON_SIZE_DEFAULT`** — `config/defaults.py` — equals
  `MAIN_TOOLBAR_ICON_SIZE_MEDIUM`.

### Anchor points

- **Config default:** `config/defaults.py` — `defaults["view"]["toolbar"]`
  stores the active size as a string tuple (e.g. `"(22, 22)"`), generated
  from `MAIN_TOOLBAR_ICON_SIZE_DEFAULT`.
- **Size menu:** `gui/menu.py` `ToolBarMenu` — radio buttons for small,
  medium, large. Values are `(size, size)` tuples built from the constants.
- **ToolBar constructor:** `gui/toolbar.py` `ToolBar.__init__()` — `size`
  parameter defaults to `(MAIN_TOOLBAR_ICON_SIZE_DEFAULT,) * 2`, applied
  via `SetToolBitmapSize()`.
- **Viewer toolbar:** `gui/viewer/base.py` — always passes
  `(TOOLBAR_ICON_SIZE,) * 2` (fixed at 16px).
- **Settings flow:** menu selection → `settings.setvalue()` → pubsub →
  `mainwindow.showToolBar(value)` → `MainToolBar(size=value)`.

---

## Perspective Serialization

The toolbar's visible commands are serialized as a comma-separated string
of command unique names, stored in settings. Special entries:

- `"Separator"` — maps to `None` in the command list, rendered as
  `AuiToolBar.AddSeparator()`
- `"Spacer"` — maps to `1` (int) in the command list, rendered as
  `AuiToolBar.AddStretchSpacer(1)`

`_filterCommands()` deserializes: builds an index of command names, adds
the two special entries, and maps each name in the perspective string to
its command object. `perspective()` serializes back.

---

## Toolbar Customization Dialog

`dialog/toolbar.py` — a modal dialog for reordering, showing, and hiding
toolbar commands. Two `wx.ListCtrl` panels ("Available tools" and "Tools")
with drag-and-drop between them.

### Icon display

Both list controls borrow the shared `ImageListCache` (see
[ICON_DISPLAY.md — Image List Cache](ICON_DISPLAY.md#image-list-cache))
via `SetImageList()`. Real command icons use `image_list_cache.get_index()`
for lazy loading. Separator and spacer items have no icon (image index
`-1`, the wxPython convention for "no image").

### List management

See [LIST_MANAGEMENT.md](LIST_MANAGEMENT.md) for the general pattern of
`wx.ListCtrl` population, selection tracking, and item state updates used
in this dialog.

---

## File Reference

- Toolbar classes: `taskcoachlib/gui/toolbar.py`
- Customization dialog: `taskcoachlib/gui/dialog/toolbar.py`
- UICommand container mixin: `taskcoachlib/gui/uicommand/uicommandcontainer.py`
- Toolbar size menu: `taskcoachlib/gui/menu.py` (`ToolBarMenu`)
- Toolbar size constants: `taskcoachlib/config/defaults.py`
- Default toolbar size setting: `taskcoachlib/config/defaults.py` (`defaults["view"]["toolbar"]`)
- Viewer-embedded toolbar: `taskcoachlib/gui/viewer/base.py`

---

## See Also

- [ICON_DISPLAY.md](ICON_DISPLAY.md) — Image List Cache, icon rendering
- [ICON_LIBRARY.md](ICON_LIBRARY.md) — Icon catalog, `LIST_ICON_SIZE`
- [LIST_MANAGEMENT.md](LIST_MANAGEMENT.md) — wx.ListCtrl patterns
