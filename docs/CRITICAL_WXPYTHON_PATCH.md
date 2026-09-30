# wxPython Background Color Patch

Task Coach carries its own copy of `wx.lib.agw.hypertreelist` at
`taskcoachlib/patches/hypertreelist.py` and loads it in place of
wxPython's on every wxPython version. The tree views are
HyperTreeLists (`taskcoachlib/widgets/treectrl.py`), so their row
colours for categories and statuses depend on it.

## The Fixes

The tree views ask for whole-row colours
(`wx.TR_FULL_ROW_HIGHLIGHT`). wxPython before 4.2.4 (Debian 12 ships
4.2.0, Debian 13 4.2.3) colours only the text:

- [Issue #2081](https://github.com/wxWidgets/Phoenix/issues/2081):
  with `TR_FULL_ROW_HIGHLIGHT`, `TreeListMainWindow.PaintItem()` drew
  no item background (a `pass` where the drawing belongs). The copy
  draws the full row before the column loop.
- [Issue #1898](https://github.com/wxWidgets/Phoenix/issues/1898):
  with `TR_FILL_WHOLE_COLUMN_BACKGROUND`, the background started at the
  text, leaving a gap before right-aligned columns such as dates. The
  copy also draws the full row before the column loop.

Both come from [PR #2088](https://github.com/wxWidgets/Phoenix/pull/2088)
(cbeytas), in wxPython 4.2.4.

## Task Coach's Changes

The copy is a fork, not a stopgap until 4.2.4: it also carries Task
Coach's own changes, among them

- the two-tone hover outline (`settings2.window.hoverlinewidth`,
  `_refresh_hover_row()`);
- `_isValidColour()` checks before drawing: an invalid colour raises
  an assertion in `wxMacCreateCGColor()` on macOS;
- column resizing: in auto-resize mode the resize column cannot be
  dragged, and shows a no-entry cursor;
- a `[TREELIST]` log when an item's texts and the columns disagree
  ([LOGGING_GUIDE.md](LOGGING_GUIDE.md#prefixes)).

## Loading

`taskcoachlib/workarounds/monkeypatches.py` installs
`HyperTreeListPatchFinder` at `sys.meta_path[0]` when imported;
`taskcoach.py` and `tests/test.py` import it before anything imports
wx's tree widgets. The finder answers only for
`wx.lib.agw.hypertreelist` and finds the copy relative to its own
file, so it works in every package: the copy ships inside
`taskcoachlib` (`setup.py` packages `taskcoachlib.*`, `MANIFEST.in`
grafts `taskcoachlib`, the Windows, macOS, AppImage and Flatpak builds
copy the package). Without the copy the finder is not installed and
wxPython's module loads.

`debian/copyright` lists the copy under the wxWindows Library
Licence, its original licence.

## Updating the Copy

To take changes from a newer wxPython:

1. Diff the copy against that version's
   `wx/lib/agw/hypertreelist.py` (run Python without Task Coach's
   finder to import wxPython's).
2. Take wxPython's changes into the copy; keep the fixes above where
   wxPython lacks them, and Task Coach's changes.
3. Check in the app: a category with a background colour colours its
   tasks' whole rows, the date columns included, with no gaps; the
   hover outline follows the mouse.

## Known Issue

Truncated text in right-aligned and centered columns is cut on the
wrong side; the cause is `ChopText()` in wxPython's customtreectrl,
not this copy
([TODO.md](TODO.md#hypertreelist-text-truncation-bug-standard-wxpython-issue)).

## Other Runtime Patches

`monkeypatches.py` also patches wx at import:

- `Window.SetSize`: a negative width or height becomes 0 in the two-
  and four-number forms, since GTK asserts `height >= -1`; a `wx.Size`
  or `wx.Rect` passes as is.
- `wx.CallAfter` crash guard and `wx.Timer` owner guard
  ([CRASH_GUARD.md](CRASH_GUARD.md)).
