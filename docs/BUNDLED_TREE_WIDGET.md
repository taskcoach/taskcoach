# Bundled Tree Widget

Task Coach's tree views (`taskcoachlib/widgets/treectrl.py`) are
HyperTreeLists. Task Coach ships its own copy of that widget in
`taskcoachlib/patches/` and loads it in place of the installed
wxPython's on every wxPython version, so every build runs the same tree
code: the code the certified test platform runs
([TESTING.md](TESTING.md)).

Listed with the other bundled and patched code in
[THIRD_PARTY_CODE.md](THIRD_PARTY_CODE.md).

## What Is Bundled

| File | Upstream base | Changes |
|------|---------------|---------|
| `hypertreelist.py` | wxPython 4.3.1's `wx/lib/agw/hypertreelist.py` (4.2.4 to 4.3.1 differ by one line) | Task Coach's, [below](#task-coachs-changes); the `Self` annotations dropped for Python 3.10 |
| `customtreectrl.py` | wxPython 4.3.1's `wx/lib/agw/customtreectrl.py` (the same since 4.2.4) | none |

The header dates inside the files are upstream's and say nothing of the
copy's age: `hypertreelist.py` reads "Latest Revision: 30 Jul 2014" in
every wxPython release up to 4.3.1. To find a copy's base, diff it
against each release's file
(`https://github.com/wxWidgets/Phoenix/tree/wxPython-X.Y.Z/wx/lib/agw`).

Moving from 4.2.2's and 4.2.3's files to 4.3.1's (To Do 67) brought
upstream's fixes from [PR #2088](https://github.com/wxWidgets/Phoenix/pull/2088)
that users see: large trees are faster (rows are laid out when needed
and only visible rows painted); typing in a tree view jumps to the next
task starting with the letters typed, where it toggled rows in and out
of the selection; a quick click on a column border no longer nudges
the column's width.

## One Widget, Two Files

`hypertreelist.py`'s main window (`TreeListMainWindow`) is a
`CustomTreeCtrl` subclass and relies on its internals: how it tracks
the selection, method signatures, helper functions. Upstream changes
the two files together. So they are bundled and loaded together, both
or neither, and updated together.

Why this rule exists: the Python 3 migration dropped Task Coach's own
`customtreectrl.py` for wxPython's and kept only the `hypertreelist.py`
copy, which then ran on each build's installed `customtreectrl`: 4.0.7
on Ubuntu 22.04 up to 4.3.1 on Windows, macOS and the Flatpak. wxPython
4.2.4 ([PR #2088](https://github.com/wxWidgets/Phoenix/pull/2088),
2025-10-28) made `CustomTreeCtrl` keep its selected rows in a set that
`UnselectAll()` alone clears. The copy and `treectrl.py` then
highlighted rows directly, outside that set, so on every build with
4.2.4 or later the tree views lost the selection at each rebuild (a sort, a filter or
search, the tree/list switch, a new task) and, after a filter, selected
the neighbouring task instead
([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#restoring-the-selection-after-a-rebuild);
GitHub #385; P118 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues)).
The certified tests run on 4.2.3 and could not see it. Bundling the
base fixed it, 2026-10-01.

Nor can the copy follow upstream one file at a time: 4.2.4's
`hypertreelist.py` does not import on an older `customtreectrl.py`
(`EnsureText`, `BisectChildren`).

## Why a Copy

- **Row colours.** Before 4.2.4 wxPython's HyperTreeList colours only
  the text of a row ([#2081](https://github.com/wxWidgets/Phoenix/issues/2081),
  [#1898](https://github.com/wxWidgets/Phoenix/issues/1898)); Debian
  and Ubuntu all ship older versions (Debian 13: 4.2.3). Category and
  status colours fill whole rows only with the copy.
- **Task Coach's changes** live inside the widget's drawing, mouse and
  editing code and cannot be added from outside.
- **One tree code everywhere**, tested once.

## Task Coach's Changes

In `hypertreelist.py`; the commit first making each change.

| Where | Change | Commit |
|-------|--------|--------|
| `PaintItem`, `OnPaint` | colours checked before making brushes: an invalid colour asserts in `wxMacCreateCGColor()` on macOS | `5342526c2` |
| `PaintItem` | the dragged row drawn like a selected one | `6a7681e9d` |
| `PaintItem`, `TreeListItem.SetImages()`/`GetImages()` | several icons in one column (the categories' icons) | `5ce0adef8` |
| `SetImageList` | no greyed copy of the image list (3,000+ icons); otherwise upstream's, rows marked for recalculation | `1c6d5d3a7` |
| `SetHoverItem`, `_refresh_hover_row`, `PaintLevel`, `OnMouse` | the two-tone hover outline (`settings2.window.hoverlinewidth`); mouse moves within a row do nothing | `78533ffab`, `a20c9164c` |
| `OnMouse` | a drag starts after 3 pixels, without the timer; a fast double-click opens the row clicked | `a1dad34df` |
| `OnMouse` | no drop target highlighted outside the window; the drag image hidden before a refresh | `def3832cf` |
| `TreeListHeaderWindow.OnMouse`, `IsColumnResizable` | in auto-resize mode the resize column cannot be dragged (Task Coach's not-allowed cursor) | `af844f2e6` |
| `EditCtrl.__init__` | the edit box as wide as the column | `4e096044d` |
| `EditCtrl.CancelEditing`, `EditTextCtrl.OnChar`, `Delete`, `ResetEditControl` | Escape and the deletion of the item edited cancel; any other end keeps the typed value (`StopEditing()`, a click elsewhere comes before the focus moves) | `def3832cf`, `f2e9f63d1` |
| `_OnDestroy` | the drag and find timers stopped when the window is destroyed | `def3832cf` |
| `OnPaint`, `AdjustMyScrollbars` | a layout recalculated while painting sets the scrollbars after the paint: GTK does not show a scrollbar changed while painting (a column hidden left the old range) | To Do 67 |
| `OnMouse` | the edit timer after a click waits the system's double-click time, not 250 ms: a third click within it makes a double click ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#in-place-editing)) | To Do 68 |

`treectrl.py` builds on these; it highlights the rows of the selection
it restores after a rebuild through `SetItemHilight()`, which keeps the
tree's selection set
([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#restoring-the-selection-after-a-rebuild)).

## Changing the Copy

**Ruled by designer 2026-10-01**: no regressions first, then a copy that
stays close to upstream, so each release can be taken in. Change the
copy only for behaviour Task Coach cannot add from its own code: the
widget's methods and events, or an override in its own tree control
(`TreeListCtrl` in `taskcoachlib/widgets/treectrl.py`, a `HyperTreeList`
subclass). Drawing, mouse and editing behaviour in `TreeListMainWindow`
and `TreeListHeaderWindow` can only change here, since the widget
creates those windows itself. Each change gets a row in the table
above, with its commit; a change goes once the widget does the same.

## Loading

`TreeWidgetFinder` in `taskcoachlib/workarounds/monkeypatches.py`
answers for `wx.lib.agw.hypertreelist` and `wx.lib.agw.customtreectrl`
with the two files, found next to each other relative to its own file,
and is installed only when both exist. `taskcoach.py` and
`tests/test.py` import it before anything imports a tree widget.
`BundledTreeWidgetTest` checks that both load from
`taskcoachlib/patches/` and that `UnselectAll()` clears every
highlight. To see which file a Python process loads:

```
python3 -c "import taskcoachlib.workarounds.monkeypatches, wx.lib.agw.customtreectrl as c; print(c.__file__)"
```

The files ship inside `taskcoachlib` in every package: `setup.py`
packages `taskcoachlib.*`, `MANIFEST.in` grafts it, and the Windows,
macOS, AppImage and Flatpak builds copy the package as files.
`debian/copyright` lists both under the wxWindows Library Licence.

## Updating the Bundle

1. Take both files from the same wxPython release.
2. Redo [Task Coach's changes](#task-coachs-changes) on
   `hypertreelist.py`; keep `customtreectrl.py` as released but for
   fixes taken from a later release, named in its header.
3. Keep both running on every supported Python: Ubuntu 22.04 has 3.10,
   and upstream's 4.2.4+ `hypertreelist.py` imports `typing.Self`
   (3.11) or `typing_extensions` (the copy drops it). Every wx call in
   the files must exist in 4.0.7 (Ubuntu 22.04).
4. Keep the selection working: a row highlighted without
   `SetItemHilight()` is not cleared by `UnselectAll()`, so
   `treectrl.py` and the copy highlight through it
   (`BundledTreeWidgetTest`).
5. Keep the rows' cached sizes right: from 4.2.4 on each row caches its
   size and its texts' sizes, which upstream's setters mark for
   recalculation; the copy's own `SetImageList()` does the same.
6. Keep each row's values with their column. The widget inserts or
   removes only a column's header, so Task Coach's tree control
   (`TreeListCtrl.InsertColumn()` and `DeleteColumn()` in
   `treectrl.py`) moves each row's per-column values itself:
   `TreeListItem`'s `_text`, `_col_images`, `_wnd` and `_bgColour`,
   its cached text sizes, and the copy's `_multiImages`. Check that a
   new release keeps these (`TreeListCtrlColumnsTest`).
7. Check, besides the catalog: whole-row colours of a category with a
   background colour, the date columns included; the hover outline;
   the selection kept across a sort, a filter, the tree/list switch
   and a new task; multi-selection with Ctrl and Shift; the keyboard;
   drag and drop; editing (Escape cancels, a click elsewhere keeps);
   a column shown and hidden, the scrollbar following; a parent
   collapsed; the editor's prerequisite and category trees; the export
   dialog's field tree; a dark theme; a file of 2,000 tasks. Compare
   each with a build of the previous bundle, screen by screen, the
   cursor included.

## Known Issues

- Truncated text in right-aligned and centred columns is cut on the
  wrong side: `ChopText()` in `customtreectrl.py`, now bundled, so it
  can be fixed here
  ([TODO.md](TODO.md#hypertreelist-text-truncation-bug-standard-wxpython-issue)).
