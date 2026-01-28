# Colour Picker

This document describes the `ColourPickerCtrl` widget used in Task Coach for selecting colours in appearance and preferences dialogs.

## Background

### The Two Colour Dialogs on GTK3

On GTK3, wxPython historically had two different colour picker dialogs:

1. **`GtkColorChooserDialog`** — the GTK3-native colour chooser. This is what `wx.ColourPickerCtrl` opens by default on GTK3. It shows a palette of preset colours, plus a "+" button to open a custom colour editor (single-colour editing mode).
2. **`wx.ColourDialog`** — wxWidgets' own cross-platform colour dialog. On Windows and macOS, this opens the system colour picker. On GTK3, it opens `GtkColorSelectionDialog` (the older GTK colour dialog), which wxWidgets continued to use because `GtkColorChooserDialog` does not support retrieving the custom palette (see [wxWidgets #15733](https://github.com/wxWidgets/wxWidgets/issues/15733)).

### The Bug — `set_rgba` Ignored in Editor Mode

`GtkColorChooserDialog` has a bug where `gtk_color_chooser_set_rgba()` is not propagated to the custom colour editor. When the user clicks the "+" button to enter the single-colour editing mode, the editor does not receive the currently selected colour. Instead, it always defaults to a hardcoded red colour, regardless of what was previously set. This made it impossible to fine-tune colours — every visit to the custom colour editor started from red.

This was reported as [GNOME Bug #761005](https://bugzilla.gnome.org/show_bug.cgi?id=761005) and fixed in GTK commit `526fd89` (Jan 2016, by Sebastien Lafargue) in `gtkcolorchooserwidget.c`. The fix checks if the editor is visible and propagates the colour directly: `gtk_color_chooser_set_rgba(GTK_COLOR_CHOOSER(cc->priv->editor), &color)`. However, this fix may not be present in all GTK3 distributions, and a similar regression was reported for GTK4 in [PyGObject #561](https://gitlab.gnome.org/GNOME/pygobject/-/issues/561).

`wx.ColourDialog` (which uses the older `GtkColorSelectionDialog` on GTK3) does not have this bug — it correctly pre-selects the current colour on all platforms. On Windows and macOS, `wx.ColourDialog` and the native picker are effectively the same system dialog, so this issue is GTK3-specific.

### The Fix

The custom `ColourPickerCtrl` was introduced in PR #316 (`d13db6d66`, Jan 2026) as a drop-in replacement. On GTK, it intercepts all activation paths on the native picker button and opens `wx.ColourDialog` instead of the broken `GtkColorChooserDialog`. On Windows/macOS the native picker works correctly and all events are passed through unchanged.

The initial implementation used a modeless dialog with explicit lifecycle management (`_dialog` tracking, `EVT_WINDOW_DESTROY` cleanup). This was simplified in PR #322 (`1fee77da7`, Jan 2026) to use a modal `ShowModal()` call, eliminating the dialog tracking and cleanup code.

NOTE: The original documentation for this refactoring was written but never committed and has been lost. This document reconstructs that information from git history and code review.

## Production Control — `ColourPickerCtrl(wx.ColourPickerCtrl)`

`taskcoachlib/widgets/colourpicker.py`

### Features

| Feature | Status |
|---------|--------|
| Colour preview (native swatch button) | Done |
| Opens wx.ColourDialog on click (GTK) | Done |
| Native picker on Windows/macOS | Done |
| Read-only mode (no click, no tab focus) | Done |
| Fires wx.ColourPickerEvent on change | Done |

### Read-Only Mode and Tab Traversal

- **Editable** (`readOnly=False`): picker accepts tab focus and opens colour dialog on click/Enter/Space.
- **Read-only** (`readOnly=True`): both the outer composite control and the inner picker button bind `EVT_NAVIGATION_KEY` (to skip the control preserving tab direction) and `EVT_SET_FOCUS` (to reject click-focus). This is a composite control — the inner button is a separate wx window in the tab order, so both must be handled. `SetCanFocus(False)` alone is unreliable on native GTK widgets. Click, double-click, Enter/Space, and button events are also swallowed.

In the editor Appearance tab, the Derived and Effective sections use `readOnly=True`, which disables both clicking and tab focus. Only the Override section's colour pickers are tabbable/editable.

### GTK Workaround Detail

On GTK, the native `GtkColorChooserDialog` opened by `wx.ColourPickerCtrl` does not correctly pre-select the current colour in its custom colour editor (the "+" button) — see GNOME Bug #761005 above. The workaround intercepts all activation paths on the inner picker button and opens `wx.ColourDialog` instead:

- `EVT_LEFT_DOWN` / `EVT_LEFT_DCLICK` — opens `wx.ColourDialog` instead
- `EVT_KEY_DOWN` (Enter/Space) — opens `wx.ColourDialog` instead
- `EVT_BUTTON` — swallowed to prevent native GTK dialog from opening

On non-GTK platforms, all events are passed through to the native handler via `event.Skip()`.

### API

```python
picker = ColourPickerCtrl(parent, colour=wx.Colour(...), readOnly=False)

# Standard wx.ColourPickerCtrl API
picker.GetColour() / picker.SetColour(colour)

# Read-only control
picker.SetReadOnly(bool) / picker.IsReadOnly()
```

### Usage Sites

| File | Usage | Read-Only |
|------|-------|-----------|
| `taskcoachlib/gui/dialog/entry.py` | ColorEntry picker (Override section) | No |
| `taskcoachlib/gui/dialog/editor.py` | Derived fg/bg colour | Yes |
| `taskcoachlib/gui/dialog/editor.py` | Effective fg/bg colour | Yes |
| `taskcoachlib/gui/dialog/preferences.py` | Theme colour settings | No |

### Files

| File | Purpose |
|------|---------|
| `taskcoachlib/widgets/colourpicker.py` | Production `ColourPickerCtrl` |
| `taskcoachlib/widgets/__init__.py` | Exports `ColourPickerCtrl` |
| `taskcoachlib/gui/dialog/editor.py` | Uses ColourPickerCtrl in Override/Derived/Effective sections |
| `taskcoachlib/gui/dialog/entry.py` | `ColorEntry` wraps ColourPickerCtrl |
| `taskcoachlib/gui/dialog/preferences.py` | Theme colour settings use ColourPickerCtrl |

### Git History

| Commit | PR | Description |
|--------|----|-------------|
| `d13db6d66` | #316 | Introduced custom ColourPickerCtrl with GTK workaround (modeless dialog) |
| `1fee77da7` | #322 | Simplified to modal ShowModal(), removed dialog lifecycle tracking |
| `3d3eebac4` | — | Fixed TypeError: `col=` → `colour=` parameter name |
| `6433f2a89` | — | Added readOnly with SetCanFocus (initial attempt) |
| `cd09a0e82` | — | Switched to EVT_NAVIGATION_KEY + EVT_SET_FOCUS for reliable focus rejection |
| `1e6d955c1` | — | Fixed reverse-tab direction via wx.GetKeyState(wx.WXK_SHIFT) |
