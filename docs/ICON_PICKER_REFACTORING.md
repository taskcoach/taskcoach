# Icon Picker Refactoring

This document describes the custom `IconPicker` widget used in Task Coach for selecting icons in preferences and appearance dialogs.

## Table of Contents

- [TODO Items](#todo-items)
- [Final Implementation](#final-implementation)
- [Features](#features)
- [Usage](#usage)
- [The no_icon Parameter](#the-no_icon-parameter)
- [Files Involved](#files-involved)
- [Technical Details](#technical-details)
  - [Button Active Appearance](#button-active-appearance)
  - [Focus Indicator](#focus-indicator)
  - [Escape Key Handling](#escape-key-handling)
- [Appendix: wxWidgets Reference](#appendix-wxwidgets-reference)

## TODO Items

### Demo Control Issues

| # | Issue | Status | Notes |
|---|-------|--------|-------|
| 38 | ~~Demo picker not working and not updated~~ | Done | The demo script was removed (2026-09); the picker is tested in the app. |


### Search Box Issues

| # | Issue | Status | Notes |
|---|-------|--------|-------|
| 18 | ~~Not getting focus~~ | Done | Fixed with `CallAfter(self._focus_search)`. Tab order also fixed: list → Clear → Cancel → OK. |
| 19 | ~~Cursor stuck in main textbox~~ | Done | Resolved by modal `_IconDialog` (no focus competition with main window). |


### Feature Implementation

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 37 | ~~Use shared `ImageListCache` instead of private `_image_list`~~ | Done | Replaced private `_image_list` and `_image_map` with shared `image_list_cache` singleton. Picker now uses `image_list_cache.get_index(icon_id)` for lazy loading and `image_list_cache.image_list` via `SetImageList()` — same pattern as all viewers. Bitmap removed from item tuples (6-tuple instead of 7). |

### Integration Tasks

| # | Task | Status | Notes |
|---|------|--------|-------|
| 30 | Create reusable widget in taskcoachlib/widgets/iconpicker.py | Done | `IconPicker` class with hints support |
| 32 | Integrate into entry.py IconPicker | Done | Uses widgets.IconPicker, auto-width |
| 33 | Add icon hints to icon_library.py | Done | Icon hints now in each theme's `icons_parsed.py` |
| 34 | Test on Windows/macOS | Not Started | Cross-platform verification |

### Transparent Empty Bitmap

| # | Task | Status | Notes |
|---|------|--------|-------|
| 35 | ~~Review if `TRANSPARENT_EMPTY_ICON` still needed~~ | Done | Removed. The "No icon" state sets `bmpLabel = None` directly, with a `SetBitmapLabel` guard to prevent wxPython bug #2093. |

### Status Legend

- **Done**: Completed and integrated
- **Not Started**: Work has not begun

</details>

## Final Implementation

The `IconPicker` widget (`taskcoachlib/widgets/iconpicker.py`) is a custom searchable icon picker built on `wx.lib.buttons.ThemedGenBitmapTextButton` with a `wx.Dialog` modal.

**Architecture:**
```
IconPicker (ThemedGenBitmapTextButton)
├── Button: displays one icon + label (no list-building)
├── SetValue(icon_id) looks up catalog icon metadata directly
├── exclude parameter: None / "status" / "data" (passed to dialog)
├── Custom painting via DrawLabel/DrawBezel
└── _IconDialog (wx.Dialog) — modal, input=icon_id, output=icon_id
    ├── _get_excluded_icons() — resolves exclude mode to actual icon_id set
    ├── _load_icons() — builds item list from catalog (fresh each open)
    ├── wx.SearchCtrl (filter input)
    └── _IconListCtrl (wx.ListCtrl, wx.LC_VIRTUAL)
        └── 5 columns: Label (with icon), Hints, Theme, Context, icon_id (COL_ICON_ID=4)
        └── Virtual: OnGetItemText/OnGetItemImage/OnGetItemAttr callbacks
        └── SetItemCount(n) for O(1) population (only visible rows rendered)
```

**Why Modal Dialog:**
- Modal dialog (`ShowModal()`) is positioned by the window manager, working correctly on all platforms including Wayland
- The previous `wx.MiniFrame` popup required `ClientToScreen()` + `SetPosition()` which fails on Wayland (coordinates ignored for xdg_toplevel windows)
- `wx.PopupTransientWindow` was avoided due to caret visibility bugs on GTK3 (wxWidgets issue #18261) — but since the modal dialog approach works cleanly, this is no longer relevant

**Font Picker:** The `FontPickerCtrl` in `taskcoachlib/widgets/fontpicker.py` is a separate widget for font selection. See `docs/FONT_PICKER.md` for details.

**Key Features:**
- Searchable dropdown with hints column
- Theme-aware via `wx.SystemSettings` colors
- Keyboard navigation (arrows, Enter, Escape)
- Disabled item support (strikethrough, unselectable)
- Fixed-width option with text ellipsis
- "No icon" option via `no_icon` parameter
- Button grows/shrinks to fit selected icon label
- Separation of concerns: button only displays one icon, dialog owns list-building
- List built fresh each dialog open (no persistent list state on button)
- `COL_ICON_ID = 4` column constant for readable list access
- Virtual `wx.ListCtrl` (`wx.LC_VIRTUAL`) — only visible rows are
  rendered.  Previous non-virtual implementation was slow for large
  icon sets (500+) because every `_rebuild_list()` call did O(n)
  `InsertItem` + `SetItem` + `SetItemTextColour` native wx calls.
  Now uses `SetItemCount(n)` (O(1)) and `OnGetItemText`/`OnGetItemImage`/
  `OnGetItemAttr` callbacks for visible rows only.  Opening and filtering
  are near-instant regardless of icon count.

## Features

All planned features have been implemented:

| Feature | Status |
|---------|--------|
| Icon displayed in closed control | Done |
| Icon + text in dropdown items | Done |
| Search/filter by typing | Done |
| Search hints column (grey, searchable) | Done |
| Disabled/inactive rows (strikethrough) | Done |
| Ellipsis for long text | Done |
| Fixed width control option | Done |
| Wide popup, narrow control | Done |
| Theme-aware styling | Done |
| Keyboard navigation | Done |
| "No icon" option | Done |
| Escape cancels dialog | Done |

### Search

The popup includes a visible search box at the top:

- `wx.SearchCtrl` for filter input
- Filters items as user types
- Searches both label and hints columns

### Search Hints

Icons support additional searchable text shown in a secondary column:
- "LED - Blue" also matches "status", "indicator", "light"
- "Checkmark" also matches "done", "complete", "finished"

**Display:** Grey text column, truncated if too long.

**Data structure:**
```python
# Item format: (icon_id, label, hints, theme_label, context_label, enabled)
("nuvola_actions_ledblue", "LED - Blue", "status indicator light", "Legacy", "", True)
```

### Icon Data in icon_library.py

Icon names and hints are stored in each theme's `icons_parsed.py` (generated from
`icons.json` by `python tools/generate_icons_parsed_py.py <theme>`).

Each hint term is individually translatable via the `_()` function. The IconPicker joins hints with spaces for search functionality.

**Adding New Icons:**

1. Add icon PNG to the proper theme directory
2. Add entry to the theme's `icons.json`
3. Run `python tools/generate_icons_parsed_py.py <theme>`

### Disabled Items

Icons can be disabled in the picker via the `exclude` parameter:
- `None`: no exclusion (all icons enabled)
- `"status"`: exclude icons used in status configuration (for task/category editor)
- `"data"`: exclude icons used by tasks, categories, and notes (for status preferences)

The dialog resolves the actual excluded icon_ids internally via `_get_excluded_icons()`.

Disabled icons show:
- Grey text color and greyscale icon
- Unselectable (skipped in keyboard nav, clicks ignored)
- Still visible in list for user awareness

## Usage

```python
from taskcoachlib import widgets

# Basic usage - includes "No icon" option by default
picker = widgets.IconPicker(parent, current_icon_id="calendar_icon")

# With excluded icons (shown as disabled/strikethrough)
picker = widgets.IconPicker(parent, current_icon_id, exclude="status")

# Without "No icon" option - user must select an icon
picker = widgets.IconPicker(parent, current_icon_id, no_icon=False)

# Fixed width (no grow/shrink, text truncated with ellipsis)
picker = widgets.IconPicker(parent, current_icon_id, fixed_width=120)

# Get/set the selected icon
icon_id = picker.GetValue()  # Returns "" for "No icon", or icon_id string
picker.SetValue("calendar_icon")
```

## The no_icon Parameter

The `IconPicker` widget has a built-in `no_icon` parameter (default: `True`) that adds a "No icon" option to the picker.

**When `no_icon=True` (default):**
- Adds a "No icon" option allowing users to clear the icon selection
- Returns empty string `""` as the value when selected

**When `no_icon=False`:**
- No "No icon" option available
- User must select an actual icon

**Usage in Task Coach:**
- Task/Category editors: `no_icon=True` - allows clearing icon
- Preferences status icons: `no_icon=True` - allows "No icon" for statuses

## Files Involved

| File | Purpose |
|------|---------|
| `taskcoachlib/widgets/iconpicker.py` | The `IconPicker` widget |
| `taskcoachlib/widgets/__init__.py` | Exports `IconPicker` class |
| `taskcoachlib/gui/dialog/entry.py` | `IconEntry` uses `IconPicker` (auto-width) |
| `taskcoachlib/gui/dialog/preferences.py` | Status icon pickers (120px fixed width) |
| `taskcoachlib/gui/icons/icon_library.py` | Icon definitions and hints |

## Technical Details

### Dynamic Sizing (Grow/Shrink)

Two sizing modes:

- **Grow** (`fixed_width=None`, default): button grows and shrinks to fit the selected icon label.
- **Fixed width** (`fixed_width=N`): button constrained to N pixels. Does not grow or shrink. Label text is ellipsized via `wx.Control.Ellipsize()` in `DrawLabel`. Used in Preferences dialog (`fixed_width=120`).

In grow mode, after selection changes, `_update_button()` calls:

1. `InvalidateBestSize()` — clears cached size so `DoGetBestSize()` is recalculated
2. `SetInitialSize()` — applies the new best size to the control
3. Walks `Layout()` up the parent chain to the top-level window — propagates the size change through all parent sizers

The wrapping `IconEntry` panel uses `fitNoMinSize()` (which calls `SetSizer` only) instead of `fit()` (which calls `SetSizerAndFit`). `SetSizerAndFit` locks the panel's minimum size at initial layout, preventing the button from shrinking when a shorter label is selected. This is the same fix used for `FontEntry` — see `FONT_PICKER.md` Variation 3 vs 5.

### Button Active Appearance

**Problem:** When "No icon" is selected, `ThemedGenBitmapTextButton` would render with an inactive appearance.

**Root Cause:** `GenBitmapButton.SetBitmapLabel()` calls `bitmap.ConvertToImage()` which fails on `None` or `wx.NullBitmap`.

**Solution:** Create a 16x16 transparent placeholder bitmap and always use it for "No icon":

```python
self._empty_bmp = wx.Bitmap(self.ICON_SIZE, self.ICON_SIZE, 32)
self._empty_bmp.UseAlpha()
dc = wx.MemoryDC(self._empty_bmp)
dc.SetBackground(wx.Brush(wx.Colour(0, 0, 0, 0)))
dc.Clear()
dc.SelectObject(wx.NullBitmap)
```

### Focus Indicator

`ThemedGenBitmapTextButton` with `wx.BORDER_NONE` disables focus indicator by default. Solution:

```python
self.SetUseFocusIndicator(True)

def DrawFocusIndicator(self, dc, w, h):
    rect = wx.Rect(3, 3, w - 6, h - 6)
    wx.RendererNative.Get().DrawFocusRect(self, dc, rect)
```

### Escape Key Handling

Pressing Escape in the modal dialog cancels the selection and closes the dialog. Since `_IconDialog` uses `ShowModal()`, Escape calls `EndModal(wx.ID_CANCEL)`:

```python
def _on_key(self, event):
    key = event.GetKeyCode()
    if key == wx.WXK_ESCAPE:
        self.EndModal(wx.ID_CANCEL)
    else:
        event.Skip()
```

No `EVT_CHAR_HOOK` interception is needed — the modal dialog handles Escape natively.

---

## Appendix: wxWidgets Reference

The following reference material was used during development.

### Theme Colors Used

| Element | Color |
|---------|-------|
| Button text | `SYS_COLOUR_BTNTEXT` |
| Disabled text | `SYS_COLOUR_GRAYTEXT` |
| Hints text | `SYS_COLOUR_GRAYTEXT` |
| List background | `SYS_COLOUR_LISTBOX` |
| Selection background | `SYS_COLOUR_HIGHLIGHT` |
| Selection text | `SYS_COLOUR_HIGHLIGHTTEXT` |

### RendererNative Methods Used

| Method | Usage |
|--------|-------|
| `DrawPushButton(win, dc, rect, flags)` | Button bezel |
| `DrawFocusRect(win, dc, rect, flags)` | Focus indicator |

### Control Flags

| Flag | Usage |
|------|-------|
| `CONTROL_PRESSED` | Button pressed |
| `CONTROL_CURRENT` | Mouse hover |
| `CONTROL_DISABLED` | Disabled state |

---

## Historical Reference (Collapsed)

<details>
<summary>Click to expand original research notes</summary>

## Complete wx.SystemColour Reference

Use `wx.SystemSettings.GetColour(wx.SYS_COLOUR_*)` to retrieve theme colors.

### All System Colours

| Constant | Description |
|----------|-------------|
| `SYS_COLOUR_SCROLLBAR` | Scrollbar grey area |
| `SYS_COLOUR_DESKTOP` | Desktop/background colour |
| `SYS_COLOUR_ACTIVECAPTION` | Active window caption |
| `SYS_COLOUR_INACTIVECAPTION` | Inactive window caption |
| `SYS_COLOUR_MENU` | Menu background |
| `SYS_COLOUR_WINDOW` | Window background (editable text areas) |
| `SYS_COLOUR_WINDOWFRAME` | Window frame/border |
| `SYS_COLOUR_MENUTEXT` | Menu text |
| `SYS_COLOUR_WINDOWTEXT` | Text in generic windows |
| `SYS_COLOUR_CAPTIONTEXT` | Caption, size box, scrollbar text |
| `SYS_COLOUR_ACTIVEBORDER` | Active window border |
| `SYS_COLOUR_INACTIVEBORDER` | Inactive window border |
| `SYS_COLOUR_APPWORKSPACE` | MDI application background |
| `SYS_COLOUR_HIGHLIGHT` | Selected item background |
| `SYS_COLOUR_HIGHLIGHTTEXT` | Selected item text |
| `SYS_COLOUR_BTNFACE` | Button/control face (grey inactive) |
| `SYS_COLOUR_BTNSHADOW` | Button shadow/border |
| `SYS_COLOUR_GRAYTEXT` | Disabled/greyed text |
| `SYS_COLOUR_BTNTEXT` | Button text |
| `SYS_COLOUR_INACTIVECAPTIONTEXT` | Inactive caption text |
| `SYS_COLOUR_BTNHIGHLIGHT` | Button highlight edge |
| `SYS_COLOUR_3DDKSHADOW` | Dark shadow for 3D elements |
| `SYS_COLOUR_3DLIGHT` | Light colour for 3D elements |
| `SYS_COLOUR_INFOTEXT` | Tooltip text |
| `SYS_COLOUR_INFOBK` | Tooltip background |
| `SYS_COLOUR_LISTBOX` | List/dropdown background |
| `SYS_COLOUR_HOTLIGHT` | Hyperlink/hot-tracked item |
| `SYS_COLOUR_MENUHILIGHT` | Menu highlight (flat menus) |
| `SYS_COLOUR_MENUBAR` | Menu bar background (flat menus) |
| `SYS_COLOUR_LISTBOXTEXT` | List/dropdown text |
| `SYS_COLOUR_LISTBOXHIGHLIGHTTEXT` | Unfocused selection text |

## Icon Picker Theme Mapping

### Closed Combo Control - Property to Theme Mapping

| Property | State | Theme Variable | Notes |
|----------|-------|----------------|-------|
| Background | Normal (readonly) | `SYS_COLOUR_BTNFACE` | Grey, non-editable appearance |
| Background | Editable | `SYS_COLOUR_WINDOW` | White, editable appearance |
| Background | Disabled | `SYS_COLOUR_BTNFACE` | Same as readonly |
| Text | Normal | `SYS_COLOUR_BTNTEXT` | Standard button text |
| Text | Disabled | `SYS_COLOUR_GRAYTEXT` | Greyed out |
| Border | Normal | `SYS_COLOUR_BTNSHADOW` | 1px border |
| Border | Hover | `SYS_COLOUR_HIGHLIGHT` | Highlighted border |
| Border | Pressed/Open | `SYS_COLOUR_BTNSHADOW` | Same as normal |
| Focus Rect | Tab Focus | `DrawFocusRect()` | Dotted line, full control |
| Cursor | Always | `wx.CURSOR_ARROW` | No text cursor for readonly |

### Dropdown Button - Property to Theme Mapping

| Property | State | Method/Flag | Notes |
|----------|-------|-------------|-------|
| Appearance | Normal | `DrawComboBoxDropButton(flags=0)` | Native button |
| Appearance | Hover | `DrawComboBoxDropButton(CONTROL_CURRENT)` | Highlighted |
| Appearance | Pressed | `DrawComboBoxDropButton(CONTROL_PRESSED)` | Depressed |
| Appearance | Disabled | `DrawComboBoxDropButton(CONTROL_DISABLED)` | Greyed |

### Popup/Dropdown - Property to Theme Mapping

| Property | State | Theme Variable | Notes |
|----------|-------|----------------|-------|
| Background | Normal | `SYS_COLOUR_WINDOW` | Or `SYS_COLOUR_MENU` |
| Border | Normal | `SYS_COLOUR_BTNSHADOW` | Draw 1px border using system color |

### VListBox Items - Property to Theme Mapping

| Property | State | Theme Variable | Notes |
|----------|-------|----------------|-------|
| Background | Normal | `SYS_COLOUR_LISTBOX` | List background |
| Background | Selected | `SYS_COLOUR_HIGHLIGHT` | Full highlight |
| Background | Hover | Blend of LISTBOX + HIGHLIGHT | ~33% highlight |
| Background | Disabled | `SYS_COLOUR_LISTBOX` | Same as normal |
| Text | Normal | `SYS_COLOUR_LISTBOXTEXT` | Standard list text |
| Text | Selected | `SYS_COLOUR_HIGHLIGHTTEXT` | Contrast text |
| Text | Hover | `SYS_COLOUR_LISTBOXTEXT` | Keep normal text |
| Text | Disabled | `SYS_COLOUR_GRAYTEXT` | Greyed out |
| Hints | Normal | `SYS_COLOUR_GRAYTEXT` | Secondary text |
| Hints | Selected | `SYS_COLOUR_HIGHLIGHTTEXT` | Match selection |
| Icon | Disabled | Greyscale conversion | Desaturated |

### Search Control - Property to Theme Mapping

| Property | State | Theme Variable | Notes |
|----------|-------|----------------|-------|
| All | All | Native `wx.SearchCtrl` | Handles own theming |

## wx.RendererNative Methods

Use `wx.RendererNative.Get()` for platform-native drawing.

| Method | Usage |
|--------|-------|
| `DrawTextCtrl(win, dc, rect, flags)` | Native text control (editable) |
| `DrawComboBoxDropButton(win, dc, rect, flags)` | Dropdown button with arrow |
| `DrawDropArrow(win, dc, rect, flags)` | Just the dropdown arrow |
| `DrawItemSelectionRect(win, dc, rect, flags)` | Native list selection |
| `DrawPushButton(win, dc, rect, flags)` | Standard push button |
| `DrawFocusRect(win, dc, rect, flags)` | Dotted focus rectangle |

### Control Flags (wx.CONTROL_*)

| Flag | Value | Usage |
|------|-------|-------|
| `CONTROL_FOCUSED` | Focus | Control has keyboard focus |
| `CONTROL_PRESSED` | Pressed | Button pressed (popup shown) |
| `CONTROL_CURRENT` | Hover/Current | Mouse hover or keyboard current |
| `CONTROL_SELECTED` | Selected | Item is selected |
| `CONTROL_DISABLED` | Disabled | Control/item is disabled |

## wxComboCtrlBase Internal State (Reference)

From wxWidgets source (`src/common/combocmn.cpp`):

| Internal State | Flag | Description |
|----------------|------|-------------|
| Button state | `m_btnState` | Tracks `CONTROL_CURRENT` (hover), `CONTROL_PRESSED` |
| Control flags | `m_iFlags` | Internal state flags |
| Popup shown | `IsPopupShown()` | True when dropdown visible |

**HandleButtonMouseEvent** flow:
1. Mouse enter → set `CONTROL_CURRENT` → refresh
2. Mouse down → set `CONTROL_PRESSED` → show popup
3. Mouse leave → clear `CONTROL_CURRENT` → refresh

## wxVListBox Internal State (Reference)

From wxWidgets source (`src/generic/vlbox.cpp`):

| Internal State | Variable | Description |
|----------------|----------|-------------|
| Current item | `m_current` | Keyboard-focused item (single always) |
| Selection | `m_selStore` | Selected items (multi-select mode) |
| Selection bg | `m_colBgSel` | Custom selection background |

**OnDrawBackground** uses:
- `wxCONTROL_SELECTED` for selected items
- `wxCONTROL_CURRENT` for keyboard-current item
- `wxCONTROL_FOCUSED` when control has focus

## wx.ComboCtrl API Reference

### Key Methods

| Method | Description |
|--------|-------------|
| `SetPopupControl(popup)` | Associate wx.ComboPopup |
| `GetPopupControl()` | Get current popup |
| `IsPopupShown()` | True if popup visible |
| `ShowPopup()` / `Popup()` | Show popup |
| `HidePopup()` / `Dismiss()` | Hide popup |
| `SetPopupMinWidth(width)` | Minimum popup width |
| `SetPopupMaxHeight(height)` | Maximum popup height |
| `GetButtonSize()` | Dropdown button dimensions |
| `GetTextCtrl()` | Internal text control |

### Events

| Event | Description |
|-------|-------------|
| `EVT_COMBOBOX_DROPDOWN` | Popup shown - refresh to show pressed button |
| `EVT_COMBOBOX_CLOSEUP` | Popup hidden |
| `EVT_TEXT` | Text changed |

### Styles

| Style | Description |
|-------|-------------|
| `wx.CB_READONLY` | Not editable (may block tab on GTK) |
| `wx.TE_PROCESS_ENTER` | Generate enter events |

## wx.ComboPopup API Reference

### Required Methods

| Method | Description |
|--------|-------------|
| `Init()` | Initialize variables |
| `Create(parent)` | Create popup control |
| `GetControl()` | Return popup window |
| `GetStringValue()` | Return selected value string |

### Optional Methods

| Method | Description |
|--------|-------------|
| `SetStringValue(value)` | Receive value from ComboCtrl |
| `OnPopup()` | Called when popup shown |
| `OnDismiss()` | Called when popup hidden |
| `GetAdjustedSize(minW, prefH, maxH)` | Return preferred size |
| `Dismiss()` | Close popup from within |

## wx.VListBox API Reference

### Required Methods

| Method | Description |
|--------|-------------|
| `OnDrawItem(dc, rect, n)` | Draw item n |
| `OnMeasureItem(n)` | Return height of item n |

### Optional Methods

| Method | Description |
|--------|-------------|
| `OnDrawBackground(dc, rect, n)` | Draw item background |
| `OnDrawSeparator(dc, rect, n)` | Draw separator |

### Selection Methods

| Method | Description |
|--------|-------------|
| `SetSelection(n)` | Select item (-1 to clear) |
| `GetSelection()` | Get selected index |
| `IsSelected(n)` | Check if selected |
| `IsCurrent(n)` | Check if keyboard focus |
| `SetItemCount(count)` | Set total items |
| `RefreshAll()` | Refresh display |
| `SetSelectionBackground(colour)` | Selection color |

## Related Issues

- Font picker also needed similar treatment (fixed width, ellipsis)
- Color picker buttons in preferences
- Consistent control sizing across preferences dialog

