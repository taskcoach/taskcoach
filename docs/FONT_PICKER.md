# Font Picker

This document describes the `FontPickerCtrl` widget used in Task Coach for selecting fonts in appearance and preferences dialogs.

## Production Control — `FontPickerCtrl(buttons.GenButton)`

`taskcoachlib/widgets/fontpicker.py`

A custom-drawn button that displays the selected font name (in that font) and opens `wx.FontDialog` on click. Uses `GenButton` to avoid native GTK hover/press rendering artifacts.

### Features

| Feature | Status |
|---------|--------|
| Font preview (button text rendered in selected font) | Done |
| Foreground color preview | Done |
| Background color preview | Done |
| Read-only mode (no click, no tab focus) | Done |
| Two sizing modes (grow + fixedWidth with ellipsis) | Done |
| Focus indicator (DrawFocusRect when focused) | Done |
| Opens wx.FontDialog on click | Done |
| Fires wx.FontPickerEvent on change | Done |

### Sizing Modes

- **Grow** (`fixedWidth=None`, default): button grows to fit the font description text. Requires two parts:
  1. **Button-level**: on content change, calls `InvalidateBestSize()` + `SetInitialSize()` and walks `Layout()` up the parent chain to the top-level window.
  2. **Panel-level**: the wrapping `PanelWithBoxSizer` (e.g. `FontEntry`, `IconEntry`) must use `fitNoMinSize()` instead of `fit()`. `fit()` calls `SetSizerAndFit` which locks the panel's min size, preventing shrinking. `fitNoMinSize()` calls `SetSizer` only — see Variation 3 vs 5 in the demo section below.
  Used in editor Appearance tab. The `IconPicker` control uses the same pattern.
- **Fixed width** (`fixedWidth=N`): button constrained to N pixels, label ellipsized via `wx.Control.Ellipsize()` in `DrawLabel`. Used in Preferences dialog (`fixedWidth=75`).

### Focus and Tab Traversal

- **Editable** (`readOnly=False`): button accepts tab focus. When focused, draws a native dotted focus rectangle via `wx.RendererNative.DrawFocusRect`.
- **Read-only** (`readOnly=True`): binds `EVT_NAVIGATION_KEY` to skip the control (preserving tab direction) and `EVT_SET_FOCUS` to reject click-focus. Click is also swallowed in `onClick`.

In the editor Appearance tab, only the Override section's controls (checkbox + picker) are tabbable. The Derived and Effective sections use `readOnly=True`, which disables both clicking and tab focus. The `ColourPickerCtrl` follows the same pattern.

### API

```python
picker = FontPickerCtrl(parent, font=font, colour=colour, bgColour=bgColour,
                         readOnly=False, fixedWidth=None)

# Get/set
picker.GetSelectedFont() / picker.SetSelectedFont(font)
picker.GetSelectedColour() / picker.SetSelectedColour(colour)
picker.GetSelectedBgColour() / picker.SetSelectedBgColour(colour)
```

### Usage Sites

| File | Usage | Mode |
|------|-------|------|
| `taskcoachlib/gui/dialog/entry.py` | FontEntry picker (Override section) | grow |
| `taskcoachlib/gui/dialog/editor.py` | Derived font (read-only) | grow |
| `taskcoachlib/gui/dialog/editor.py` | Effective font (read-only) | grow |
| `taskcoachlib/gui/dialog/preferences.py` | Theme font setting | fixedWidth=75 |
| `taskcoachlib/gui/dialog/preferences.py` | Appearance font | fixedWidth=75 |

### Cross-Platform Focus Control

`SetCanFocus(False)` is unreliable on native GTK widgets (only works on pure Python controls like `GenButton`). The cross-platform approach uses two event bindings:

1. **`EVT_NAVIGATION_KEY`** — intercepts tab traversal before focus is set. Calls `Navigate(event.GetDirection())` to skip the control while preserving forward/backward direction (Tab vs Shift+Tab).
2. **`EVT_SET_FOCUS`** — catches click-focus and any other focus paths. Checks `wx.GetKeyState(wx.WXK_SHIFT)` to determine direction, then calls `wx.CallAfter(self.Navigate, forward)` to move focus away in the correct direction.

This pattern is used by:
- **FontPickerCtrl**: binds both events when `readOnly=True`.
- **ColourPickerCtrl**: binds both events on outer and inner controls when `readOnly=True`.
- **Display-only widgets** (`wx.StaticBitmap`, `wx.StaticText`, `wx.Panel`): same bindings in `editor.py`.

See `COLOUR_PICKER.md` for the colour picker details.

### Files

| File | Purpose |
|------|---------|
| `taskcoachlib/widgets/fontpicker.py` | Production `FontPickerCtrl` (GenButton) |
| `taskcoachlib/widgets/__init__.py` | Exports `FontPickerCtrl` |
| `taskcoachlib/gui/dialog/editor.py` | Uses FontPickerCtrl in Override/Derived/Effective sections |
| `taskcoachlib/gui/dialog/entry.py` | `FontEntry` wraps FontPickerCtrl |
| `taskcoachlib/gui/dialog/preferences.py` | Theme font settings use FontPickerCtrl |

## Experimental Refactoring — Demo Variations

```bash
python3 docs/scripts/font_picker_demo.py
```

The demo shows 11 variations in a scrollable window with reference standard buttons for size comparison. `FontPickerCtrl2` and other custom controls live in the demo script only — they are not used in the TC app.

### Why GenButton Was Kept

Several alternative button types were evaluated as replacements. All had rendering artifacts:

- **wx.Button (FontPickerCtrl2)**: on GTK with a light theme, `SetBackgroundColour` with a dark color causes a visible white press-offset blur when the button is unpressed. The inverse occurs with a dark theme and light bg. This artifact is present at rest — not just during interaction.
- **wx.Button with BORDER_NONE (flat)**: even flat (borderless) variants produce a blur artifact on hover. The native GTK hover highlight bleeds through the custom background color.
- **ThemedGenButton**: uses `RendererNative` for the bezel, which looks correct on GTK but is not guaranteed across platforms. The background rectangle drawn in `DrawLabel` has squared corners that don't match the native rounded bezel. Using `DrawRoundedRectangle` with a guessed radius is fragile.

The baseline `GenButton` avoids all of these by doing its own painting without relying on native button rendering. While it has cosmetic limitations (flat appearance, no native bezel), it renders correctly and consistently.

### Demo Variations

#### Variation 1 — Baseline (GenButton, production)

The production `FontPickerCtrl`. Reference for comparison.

#### Variation 2 — FontPickerCtrl2 (grow)

`wx.Button` font picker, grows to fit. Dark bg causes blur artifact at rest.

#### Variation 3 — Checkbox + FPC2 panel (SetSizerAndFit — BROKEN)

Mimics production `FontEntry`: checkbox + `FontPickerCtrl2` in a panel using `SetSizerAndFit`. Button won't grow after font change because `SetSizerAndFit` locks the panel's min size.

#### Variation 4 — Checkbox + FPC2 FLAT panel (SetSizerAndFit, BORDER_NONE)

Same as V3 but with `wx.BORDER_NONE` flat buttons. Hover still causes blur artifact.

#### Variation 5 — Checkbox + FPC2 panel (fix: SetSizer only)

Same as V3 but uses `SetSizer` instead of `SetSizerAndFit` — never locks min size. Button grows naturally. NOTE: clearing `SetMinSize((-1,-1))` + `InvalidateBestSize()` + walking `Layout()` up also works, but `SetSizer`-only is simpler and was kept as the chosen approach.

#### Variation 6 — FontPickerCtrl2 (fixedWidth=75)

`wx.Button` font picker with `fixedWidth=75` — pre-ellipsized label. Same blur artifact as V2.

#### Variation 7 — ThemedGenButton + DrawLabel bg (old attempt)

`ThemedGenButton` with `FIXED_WIDTH=75`, bg painted in `DrawLabel`. Rejected — sizing doesn't match standard buttons.

#### Variation 8 — wx.Button, no bg override

Plain `wx.Button` with font and fg only, no `SetBackgroundColour()`.

#### Variation 9 — ThemedGenButton, grow (icon picker pattern)

`ThemedGenButton` with custom `DrawLabel` following icon picker pattern. Grows to fit. Squared bg rectangle doesn't match rounded native bezel.

#### Variation 10 — ThemedGenButton, fixedWidth=75 + ellipsis (icon picker pattern)

Same as V9 but with `fixedWidth`. Ellipsis via `wx.Control.Ellipsize()` in `DrawLabel`.

#### Variation 11 — ThemedGenButton grow, dark bg

`ThemedGenButton` tested with standard configs including "White on black". Exposes the GTK button press blur artifact with dark backgrounds.

### Ellipsis Approaches

Two methods for text ellipsis were evaluated:

**Method A: DrawLabel ellipsis (Variations 9, 10)** — Ellipsize during painting inside `DrawLabel`. Recalculates on every paint. Requires `ThemedGenButton` subclass.

**Method B: Pre-ellipsize label (Variation 6)** — Ellipsize the label string before `SetLabel()`. Works with plain `wx.Button`. Static (not recalculated on resize). Padding estimate is approximate.

The production control uses Method A in `DrawLabel` for the fixedWidth mode.

### Test Configurations

Each variation is tested with:

| Config | Font | FG Color | BG Color | Read-Only |
|--------|------|----------|----------|-----------|
| Default font, system colors | System default | System text | None | No |
| Bold, red text | Bold system | Red | None | No |
| Italic serif, blue on yellow | 12pt Serif Italic | Blue | Light yellow | No |
| Default, system fg on light blue | System default | System text | Light blue | No |
| White on black | System default | White | Black | No |
| Read-only, italic serif | 12pt Serif Italic | Blue | Light yellow | Yes |
