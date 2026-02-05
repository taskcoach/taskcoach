# DateTime Controls

Simple time and duration input controls with explicit subfields and translatable labels.

## Index

- [TODO](#todo)
- [Location](#location)
- [Old Control Behavior Reference](#old-control-behavior-reference)
  - [N/A Display When Unchecked](#na-display-when-unchecked)
  - [SetNone: Unchecking the Checkbox](#setnone-unchecking-the-checkbox)
  - [Checkbox Checked: Values Appear from Sub-Controls](#checkbox-checked-values-appear-from-sub-controls)
  - [Suggested DateTime Feature](#suggested-datetime-feature)
  - [Built-in Default to "Now"](#built-in-default-to-now)
  - [Complete Flow Examples](#complete-flow-examples)
  - [External Update Mechanism (AttributeSync)](#external-update-mechanism-attributesync)
  - [Sync on Focus Loss (Same as Subject Field)](#sync-on-focus-loss-same-as-subject-field)
- [Design](#design)
  - [Element Format](#element-format)
  - [Dropdown Choices](#dropdown-choices)
  - [Built-in Field Types](#built-in-field-types)
  - [No Automatic Spacing](#no-automatic-spacing)
- [Navigation](#navigation)
  - [Keyboard Navigation](#keyboard-navigation)
  - [Dropdown Behavior](#dropdown-behavior)
- [Controls](#controls)
  - [DurationCtrl](#durationctrl)
  - [DurationCtrlVerbose](#durationctrlverbose)
  - [TimeCtrl](#timectrl)
  - [TimeWithSecondsCtrl](#timewithsecondsctrl)
  - [Locale and Date Format Settings](#locale-and-date-format-settings)
- [Events](#events)
- [Creating Custom Controls](#creating-custom-controls)
- [Translation](#translation)
- [Demo](#demo)
- [Technical Notes](#technical-notes)
  - [Module Structure](#module-structure)
  - [Font Customization](#font-customization)
  - [Custom Painting](#custom-painting)
  - [Native Theme Border](#native-theme-border)
  - [System Metrics for Cross-Platform Compatibility](#system-metrics-for-cross-platform-compatibility)
  - [Read-Only Mode](#read-only-mode)
  - [Focus Management](#focus-management)
  - [Popup Toggle Logic](#popup-toggle-logic)
  - [Dropdown Width and Position](#dropdown-width-and-position)
  - [Events from Popup](#events-from-popup)
  - [Sync Pattern: EVT_VALUE_CHANGED (DateTimeComboCtrl)](#sync-pattern-evt_value_changed-datetimecomboctrl)
  - [Sub-Control Stash Model](#sub-control-stash-model)
- [Wayland](#wayland)
  - [Problem](#problem)
  - [Why GDK_BACKEND=x11 Is Not Viable](#why-gdk_backendx11-is-not-viable)
  - [Solution: wx.PopupWindow on Wayland](#solution-wxpopupwindow-on-wayland)
- [2026-Jan Refactor: ComboCtrl Integration](#2026-jan-refactor-comboctrl-integration)
  - [Motivation](#motivation)
  - [Approach](#approach)
  - [Key Classes](#key-classes)
  - [Focus Management in DateComboCustomCtrl](#focus-management-in-datecombocustomctrl)
  - [Demo](#demo-1)
- [Platform-Specific DateComboRouterCtrl: Native Windows, Custom Elsewhere](#platform-specific-datecomborouterctrl-native-windows-custom-elsewhere)
  - [Windows — Native DatePickerCtrl with DTM_SETFORMAT](#windows--native-datepickerctrl-with-dtm_setformat)
  - [macOS — Custom Control (No Native Format Override)](#macos--custom-control-no-native-format-override)
  - [Architecture — Factory Function](#architecture--factory-function)
  - [Preferences Demo Live Update](#preferences-demo-live-update)

**Demo:** `docs/scripts/datetime_controls_demo.py`

---
Self-contained module with custom-painted single field and navigable subfields.

## TODO

1. ~~Add `Activate()` method to DateTimeComboCtrl~~ — **Done.** `ActivateValue()` on
   DateTimeComboCtrl. Editor uses it in `__activateStartDate()` / `__activateDueDate()`.
2. ~~Add `Deactivate()` method to DateTimeComboCtrl~~ — **Done.** `DeactivateValue()` on
   DateTimeComboCtrl. Editor deactivation goes through `DeactivateValue()` →
   widget fires event → AttributeSync → command → domain. ~~Previously went
   through commands directly (domain write → pubsub → SetValue(sentinel) →
   unchecks), violating widget-as-UI-SSOT principle.~~ Fixed: all editor
   helpers now go through the widget API.
3. ~~Checkbox toggle EVT_KILL_FOCUS gap~~ — **Resolved.** ~~Editor binds
   `EVT_CHECKBOX` via `combo.Bind(wx.EVT_CHECKBOX, handler)` and calls
   `sync.commit()` explicitly.~~
   **Update:** EVT_CHECKBOX is no longer exposed by DateTimeComboCtrl. The
   checkbox is an internal implementation detail. All AttributeSync instances
   now use `EVT_VALUE_CHANGED` as `editedEventType`, which fires on checkbox
   toggle AND date/time edits — no external EVT_CHECKBOX handlers needed.
   See [DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md) TODO item 9.
   **Superseded:** DateTimeComboCtrl now inherits `wx.EvtHandler` and posts
   `EVT_VALUE_CHANGED` on itself. See
   [DateTimeComboCtrl Event Ownership](#datetimecomboctrl-event-ownership).
4. **Sub-control stash model and event contract** — The sub-controls are the
   stash for DateTimeComboCtrl. `ActivateValue()` and `DeactivateValue()` must
   each fire `EVT_VALUE_CHANGED` when they change the control's
   externally-visible state. Sub-control events alone are not sufficient —
   they don't fire when only the checkbox changes. See
   [Sub-Control Stash Model](#sub-control-stash-model).
6. ~~**Editor helpers must go through widget API**~~ — **Done.** All task
   calc helpers (`__deactivateStartDate`, `__deactivateDueDate`,
   `__adjDueDate`, `__adjStartDate`, `__adjDuration`, etc.) have been
   inlined into `__syncTaskState` using `ActivateValue()`/`DeactivateValue()`
   /`SetDuration()` on the widget. The effort calc was already inline.
7. **Migrate remaining `EVT_KILL_FOCUS` AttributeSync sites to
   `EVT_VALUE_CHANGED`.** All `MaskedFieldsCtrl`-based controls are done —
   DurationCtrl (task and effort), budget (`MaskedDurationCtrl`), all
   DateTimeComboCtrl fields, hourly fee, and fixed fee now use plain
   `EVT_VALUE_CHANGED` with immediate commit. The control fires only on
   blur or programmatic complete-value write, so every event is a final
   value. **Remaining:** subject, description, and attachment location
   use `wx.TextCtrl` (per-keystroke `EVT_TEXT`) — different migration
   path. See [ATTRIBUTE_PATTERN.md TODO #1](ATTRIBUTE_PATTERN.md#todo).
8. **Planned: Extract popup from MaskedFieldsCtrl.** MaskedFieldsCtrl currently
   contains popup infrastructure (_ChoicesPopup, _openPopupForFocusedField,
   DismissPopup) that doesn't belong in the base masked field control. The base
   should only handle fields + navigation + digit entry. Each higher-level
   control decides what popup to attach:
   - DateComboCustomCtrl already follows this pattern (uses
     _CalendarComboPopup via wx.ComboCtrl, DateCtrl has no popup).
   - TimeCtrl will get its own wrapper with a single popup for the time block.
   - DurationCtrl will get its own wrapper with a single popup for the
     duration block.
   The popup may still live in MaskedFieldsCtrl as infrastructure that
   higher-level controls opt into, but it will be the higher-level control
   that decides — not the base class automatically.

9. **Consolidate "N/A" disabled state into DateTimeComboCtrl.** The "N/A"
   overlay when a date field is unchecked is currently implemented separately
   in each date picker: `DateComboCustomCtrl` paints it in `DateCtrl._onPaint`,
   and `_NativeDateCtrl` paints it in `_onPaintNA` (hiding the native picker).
   This should be consolidated so that `DateTimeComboCtrl` owns a single "N/A"
   paint layer that covers whichever date picker is behind it. The date picker
   itself would then only need Enabled/ReadOnly states — it would never need
   to know about "N/A". This removes duplicate logic and ensures consistent
   appearance across platforms.

## Location

`taskcoachlib/widgets/maskedtimectrl.py`

## Old Control Behavior Reference

The new controls should match the behavior of the old `smartdatetimectrl.py` system. Key behaviors to preserve:

### N/A Display When Unchecked

When the checkbox is unchecked, the old control shows **"N/A"** centered in light grey, hiding the actual values (which are preserved internally in the date/time sub-controls).

**Code reference:** `taskcoachlib/thirdparty/smartdatetimectrl.py:649-671`
```python
def OnPaint(self, event):
    ...
    if self.IsEnabled():
        # Paint actual values
        for widget, x, y, w, h in self.__widgets:
            ...
            widget.PaintValue(dc, x, y, w, h)
    else:
        # Disabled: show "N/A" instead of values
        text = "N/A"
        tw, th = dc.GetTextExtent(text)
        dc.SetTextForeground(wx.LIGHT_GREY)
        dc.DrawText(text, (w - tw) // 2, (h - th) // 2)
```

### SetNone: Unchecking the Checkbox

When `SetNone()` is called (or checkbox is unchecked), the control:
1. Sets checkbox to unchecked
2. Disables date/time sub-controls (triggers "N/A" painting)
3. **Does NOT clear the values** - they remain stored in the sub-controls

**Code reference:** `taskcoachlib/widgets/datectrl.py:179-181`
```python
def SetNone(self):
    self.__value = None
    self.__ctrl.SetDateTime(None)  # Calls smartdatetimectrl SetDateTime
```

**Code reference:** `taskcoachlib/thirdparty/smartdatetimectrl.py:2968-2980`
```python
def SetDateTime(self, value, notify=False):
    ...
    if value is None:
        if self.__enableNone:
            self.__checkbox.SetValue(False)  # Uncheck
            self.Enable(False)                # Disable (shows "N/A")
        # NOTE: Date/time sub-control values are NOT cleared!
```

### Checkbox Checked: Values Appear from Sub-Controls

When user checks the checkbox, the **already-stored values** from the date/time sub-controls become visible. The values were never erased - just hidden behind "N/A".

**Code reference:** `taskcoachlib/thirdparty/smartdatetimectrl.py:3008-3022`
```python
def OnToggleNone(self, event):
    if event.IsChecked():
        # Read values already stored in sub-controls
        evt = DateTimeChangeEvent(
            self,
            datetime.datetime.combine(
                self.__dateCtrl.GetDate(),   # Values were preserved!
                self.__timeCtrl.GetTime()
            ),
        )
    else:
        evt = DateTimeChangeEvent(self, None)
    self.ProcessEvent(evt)
    self.Enable(event.IsChecked())  # Enable/disable sub-controls
    self.Refresh()
    if event.IsChecked():
        self.__dateCtrl.SetFocus()  # Focus date field when checked
```

### Suggested DateTime Feature

When there is **no prior value** but a `suggestedDateTime` is provided:
1. Set the sub-control values to the suggested datetime
2. Call `SetNone()` to put in unchecked state (shows "N/A", values hidden)
3. When user checks the checkbox, the suggested values appear!

**Code reference:** `taskcoachlib/gui/dialog/entry.py:70-81`
```python
class DateTimeEntry(widgets.DateTimeCtrl):
    def __init__(self, ..., suggestedDateTime=None, ...):
        ...
        # If no initial value but suggested datetime provided
        if initialDateTime == date.DateTime() and suggestedDateTime:
            self.setSuggested(suggestedDateTime)
        else:
            self.SetValue(initialDateTime)

    def setSuggested(self, suggestedDateTime):
        super().SetValue(suggestedDateTime)  # Set values in sub-controls
        super().SetNone()                     # Uncheck (shows "N/A", hides values)
```

### Built-in Default to "Now"

The smartdatetimectrl has a **built-in fallback** when no value is provided - it defaults to "now".

**Code reference:** `taskcoachlib/thirdparty/smartdatetimectrl.py:2837`
```python
dateTime = value or datetime.datetime.now()  # Default to "now" if no value
```

**Code reference:** `taskcoachlib/thirdparty/smartdatetimectrl.py:2878-2879`
```python
if self.__enableNone and value is None:
    self.Enable(False)  # Disable (shows "N/A") but "now" is already stored
```

So when **NO prior value** and **NO suggested datetime**:
1. `value=None` passed to SmartDateTimeCtrl
2. `dateTime = None or datetime.datetime.now()` → sub-controls store "now"
3. `Enable(False)` called → shows "N/A"
4. User checks checkbox → "now" appears

The `suggestedDateTime` parameter in `entry.py` is for when a **different** suggestion is wanted (e.g., planned start date as suggestion for actual start date, rather than "now").

### Complete Flow Examples

**Example 1: No prior value, no suggested datetime**
1. Task has no actual start date, no suggestedDateTime provided
2. smartdatetimectrl defaults to "now" internally (line 2837)
3. Control disabled → shows "N/A"
4. User checks checkbox → "now" appears

**Example 2: No prior value, with suggested datetime**
1. Task has no actual start date, but `suggestedActualStartDateTime()` returns planned start
2. `setSuggested(plannedStart)` is called:
   - `SetValue(plannedStart)` → sub-controls store planned start (overrides "now")
   - `SetNone()` → checkbox unchecked, disabled, shows "N/A"
3. User sees "N/A" in the field
4. User checks checkbox → planned start appears (not "now")

**Example 3: Has prior value**
1. Task has actual start date set
2. `SetValue(actualStart)` is called → sub-controls store actual start, checkbox checked
3. User sees the actual start date/time

### External Update Mechanism (AttributeSync)

Controls must update automatically when the underlying data changes from external sources (background tasks, other windows, other processes). This is handled by `AttributeSync` (see ATTRIBUTE_PATTERN.md §Three-Layer Relationship, Layer 2).

**Code reference:** `taskcoachlib/gui/dialog/attributesync.py`

`AttributeSync` provides bidirectional synchronization between UI controls and domain objects:

1. **User edits control** → `onAttributeEdited()` → executes command → updates domain
2. **External change to domain** → `onAttributeChanged()` → calls `control.SetValue()` → updates display

**Key methods AttributeSync expects on controls:**
- `GetValue()` - returns domain-compatible value (e.g., `date.DateTime`)
- `SetValue(newValue)` - sets value from domain type
- `Bind(eventType, handler)` - binds to control's change event

### Sync via EVT_VALUE_CHANGED

Controls fire `EVT_VALUE_CHANGED` when a value changes. AttributeSync listens
to this event, calls `GetValue()`, and commits immediately.

Controls provide `GetValue()` / `SetValue()` that work with domain types
(`date.DateTime`, `date.TimeDelta`), making them compatible with AttributeSync.

See ATTRIBUTE_PATTERN.md for the full three-layer relationship.

### DateTimeComboCtrl Event Ownership

`DateTimeComboCtrl` is the composite control and **owns** the change event. It
inherits from `wx.EvtHandler` so it can host event handlers directly —
external code binds `EVT_VALUE_CHANGED` on the DTC itself, not on sub-controls.

**DTC fires `EVT_VALUE_CHANGED` in two cases:**

1. **Sub-control blur** — user edits date or time, leaves focus. DTC listens
   to `EVT_KILL_FOCUS` on sub-controls and fires its own `EVT_VALUE_CHANGED`.
2. **State transitions** — `ActivateValue()`, `DeactivateValue()`, checkbox
   click. These call `NotifyValueChanged()` at the end.

**Sub-control `EVT_VALUE_CHANGED` is trapped and dropped.** DTC binds a handler
on sub-control `EVT_VALUE_CHANGED` that explicitly consumes the event without
propagating. Sub-control change events are an implementation detail. This trap
also serves as a debug log point: if it fires, something is writing directly
to sub-controls instead of going through DTC's public API, which is a bug.

## Design

The control is **fully self-contained** with no external dependencies beyond wxPython and taskcoachlib.i18n.

**Completely independent from smartdatetimectrl.py** - no imports or shared code. This is a clean reimplementation with similar visual appearance but simplified architecture.

Uses **custom painting** on a single wx.Panel. All popup and event infrastructure is included in the module.

### Element Format

Controls are built from a list of **tuples**. Each tuple specifies either a field or a literal:

- **Field**: `("fieldtype", value)` or `("fieldtype", value, choices)`
- **Literal**: `("literal", "text")` - use `_()` for translation

### Dropdown Choices

Dropdowns are **only shown if choices are provided**:

- `None` (default): No dropdown - use Up/Down arrows to change value
- `[1, 2, 3, ...]`: Dropdown with these choices

```python
# No dropdown - Up/Down arrows increment by 1
("hour", 14)

# With dropdown - click or Enter shows choices
("hour", 14, [8, 9, 10, 11, 12, 13, 14, 15, 16, 17])
```

### Built-in Field Types

| Type | Width | Range | Display |
|------|-------|-------|---------|
| `"day"` | 3 | 0-999 | Right-aligned, no zeros: `"1"`, `"14"` |
| `"hour"` | 2 | 0-23 | Zero-padded: `"01"`, `"14"` |
| `"minute"` | 2 | 0-59 | Zero-padded: `"05"`, `"30"` |
| `"second"` | 2 | 0-59 | Zero-padded: `"05"`, `"30"` |
| `"year"` | 4 | 1-9999 | Zero-padded: `"2026"` |
| `"month"` | 2 | 1-12 | Zero-padded: `"01"`, `"12"` |
| `"date_day"` | 2 | 1-31 | Zero-padded: `"01"`, `"31"` |

Date fields (`year`, `month`, `date_day`) use calendar popup instead of dropdowns.

### No Automatic Spacing

The control adds **NO automatic margins** between elements. All spacing must be explicit in literal strings:

```python
# Correct: "1d 02:30" - space is part of the "d " literal
elements = [
    ("day", 1),
    ("literal", _("d") + " "),   # "d" immediately after day, then space
    ("hour", 2),
    ("literal", ":"),
    ("minute", 30),
]
```

## Navigation

### Keyboard Navigation

| Key | Action |
|-----|--------|
| **Tab** | Exit control (move to next widget in tab order) |
| **Shift+Tab** | Exit control (move to previous widget) |
| **Left arrow** | Previous subfield (wraps from first to last) |
| **Right arrow** | Next subfield (wraps from last to first) |
| **Up arrow** | Increment value by 1 (wraps at limits) |
| **Down arrow** | Decrement value by 1 (wraps at limits) |
| **Enter** | Toggle dropdown/calendar for current field (if choices provided) |
| **F4** | Toggle dropdown/calendar for current field (alternative to Enter) |
| **Escape** | Close dropdown without changing value |
| **0-9** | Type digits directly into field |
| **Backspace/Delete** | Remove last digit from field |

### Dropdown Behavior

The dropdown popup is self-contained (`_ChoicesPopup` class).

**Opening the dropdown** (only if choices were provided):
- Click on a subfield to open its dropdown
- Press Enter or F4 when a subfield is focused
- Clicking the same field with dropdown open closes it (toggle behavior)
- F4 is useful in inline editors where Enter confirms the edit

**Navigating within dropdown:**
- Up/Down arrows move selection through choices (wraps at ends)
- Selection changes update the field value immediately (live preview)

**Selecting a value:**
- Press Enter to confirm the highlighted choice and close dropdown
- Click on a choice to select it and close dropdown

**Closing without selection:**
- Press Escape to close dropdown (value reverts to before dropdown opened)
- Click outside the dropdown to close it

## Controls

### DurationCtrl
Compact duration format: `1d 02:30` or with seconds: `1d 02:30:15`

**Constructor:**
```python
DurationCtrl(parent, days=0, hours=0, minutes=0, seconds=0,
             dayChoices=None, hourChoices=None, minuteChoices=None,
             showSeconds=False, secondChoices=None)
```

**Parameters:**
- `days, hours, minutes, seconds`: Initial values
- `dayChoices`: Dropdown choices for days:
  - `None` (default): Use defaults `[0, 1, 2, 3, 5, 7, 14, 21, 28, 30, 60, 90]`
  - `list`: Use that specific list
  - `False`: No dropdown
- `hourChoices`: Dropdown choices for hours:
  - `None` (default): Use defaults `[0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20]`
  - `list`: Use that specific list
  - `False`: No dropdown
- `minuteChoices`: Dropdown choices for minutes:
  - `None` (default): Use defaults from settings (based on `effortminuteinterval`)
  - `list`: Use that specific list
  - `False`: No dropdown
- `showSeconds`: If True, include seconds field (default False)
- `secondChoices`: Dropdown choices for seconds:
  - `None` (default): Use defaults from settings (based on `effortsecondinterval`)
  - `list`: Use that specific list
  - `False`: No dropdown

```python
# With default dropdowns (recommended)
ctrl = DurationCtrl(parent, days=1, hours=8, minutes=30)

# With seconds (for effort tracking)
ctrl = DurationCtrl(parent, days=0, hours=2, minutes=30, seconds=15,
    showSeconds=True)

# Explicitly no dropdowns
ctrl = DurationCtrl(parent, days=1, hours=2, minutes=30,
    dayChoices=False, hourChoices=False, minuteChoices=False)

duration = ctrl.GetDuration()  # date.TimeDelta
ctrl.SetDuration(date.TimeDelta(days=1, hours=2))

# AttributeSync compatibility aliases
value = ctrl.GetValue()         # same as GetDuration()
ctrl.SetValue(duration)         # same as SetDuration()

# Negative durations (display only, e.g. budget left = -1:30:00)
ctrl.SetDuration(date.TimeDelta(hours=-1, minutes=-30))
# Day field shows "-" prefix, GetDuration() returns negative TimeDelta
```

### DurationCtrlVerbose
Duration with full word suffixes: `1 days 02 hours 30 mins` or with seconds: `1 days 02 hours 30 mins 15 secs`

**Constructor:**
```python
DurationCtrlVerbose(parent, days=0, hours=0, minutes=0, seconds=0,
                    dayChoices=None, hourChoices=None, minuteChoices=None,
                    showSeconds=False, secondChoices=None)
```

**Parameters:**
- `days, hours, minutes, seconds`: Initial values
- `dayChoices`: Dropdown choices for days:
  - `None` (default): Use defaults `[0, 1, 2, 3, 5, 7, 14, 21, 28, 30, 60, 90]`
  - `list`: Use that specific list
  - `False`: No dropdown
- `hourChoices`: Dropdown choices for hours:
  - `None` (default): Use defaults `[0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20]`
  - `list`: Use that specific list
  - `False`: No dropdown
- `minuteChoices`: Dropdown choices for minutes:
  - `None` (default): Use defaults from settings (based on `effortminuteinterval`)
  - `list`: Use that specific list
  - `False`: No dropdown
- `showSeconds`: If True, include seconds field (default False)
- `secondChoices`: Dropdown choices for seconds:
  - `None` (default): Use defaults from settings (based on `effortsecondinterval`)
  - `list`: Use that specific list
  - `False`: No dropdown

```python
# With default dropdowns (recommended)
ctrl = DurationCtrlVerbose(parent, days=0, hours=0, minutes=0)

# With seconds (for effort tracking)
ctrl = DurationCtrlVerbose(parent, days=0, hours=2, minutes=30, seconds=15,
    showSeconds=True)

# Explicitly no dropdowns
ctrl = DurationCtrlVerbose(parent, days=0, hours=0, minutes=0,
    dayChoices=False, hourChoices=False, minuteChoices=False)

duration = ctrl.GetDuration()  # date.TimeDelta
ctrl.SetDuration(date.TimeDelta(hours=1, minutes=30))
```

### TimeCtrl
Hours and minutes: `14:30` (24-hour) or `2:30 PM` (12-hour)

Supports both 24-hour and 12-hour time formats based on settings.

**Default Dropdowns:** TimeCtrl has built-in defaults from settings:
- **Hours**: Working hours from settings (24h mode) or 1-12 (12h mode)
- **Minutes**: Based on `effortminuteinterval` setting

```python
# With default dropdowns from settings (recommended)
ctrl = TimeCtrl(parent, hours=14, minutes=30)

# With custom dropdowns
ctrl = TimeCtrl(parent, hours=9, minutes=0,
    hourChoices=[9, 10, 11, 12, 13, 14, 15, 16, 17],
    minuteChoices=[0, 15, 30, 45])

# Explicitly no dropdowns
ctrl = TimeCtrl(parent, hours=14, minutes=30,
    hourChoices=False, minuteChoices=False)

# Explicit 12-hour format
ctrl = TimeCtrl(parent, hours=14, minutes=30, timeFormat="12")

time = ctrl.GetTime()  # datetime.time (always 24-hour internally)
ctrl.SetTime(datetime.time(14, 30))
```

**Dropdown Choices Parameters:**
- `None` (default): Use defaults from settings
- `[list]`: Use that specific list
- `False`: No dropdown

### TimeWithSecondsCtrl
Hours, minutes, seconds: `14:30:00` (24-hour) or `2:30:00 PM` (12-hour)

Same default behavior as TimeCtrl, plus seconds from `effortsecondinterval` setting.

```python
# With default dropdowns from settings
ctrl = TimeWithSecondsCtrl(parent, hours=14, minutes=30, seconds=0)

# With custom dropdowns
ctrl = TimeWithSecondsCtrl(parent, hours=0, minutes=0, seconds=0,
    hourChoices=list(range(24)),
    minuteChoices=list(range(60)),
    secondChoices=[0, 15, 30, 45])

# Explicitly no dropdowns
ctrl = TimeWithSecondsCtrl(parent, hours=14, minutes=30, seconds=0,
    hourChoices=False, minuteChoices=False, secondChoices=False)
```

### Locale and Date Format Settings

All date controls detect the system locale's date format using `strftime("%x")` and arrange year/month/day fields accordingly:
- **US locale**: `01/18/2026` (month/day/year with `/`)
- **European locales**: `18/01/2026` (day/month/year with `/`)
- **ISO/Canadian locale**: `2026-01-18` (year-month-day with `-`)

**User Override:** Users can override the automatic locale detection in **Preferences → Regional**:
- **Date format**: Automatic, YYYY-MM-DD (ISO), YYYY/MM/DD (East Asian), MM/DD/YYYY (US), DD/MM/YYYY (European), DD.MM.YYYY (German)
- **Time format**: Automatic, 24-hour, 12-hour with AM/PM

**Note:** When "Automatic" time format is selected, the default is 24-hour format. Users can explicitly select "12-hour" to enable AM/PM display.

The settings are stored in `TaskCoach.ini` under `[view]` as `dateformat` and `timeformat`. Helper functions:
- `getEffectiveDateFormat()` - Returns format tuple respecting user settings
- `getEffectiveTimeFormat()` - Returns "24" or "12" respecting user settings (defaults to "24" when automatic)
- `getDateFormatFromSettings()` - Raw setting value

See [LOCALE.md](LOCALE.md) for the common three-layer locale access pattern
used across all regional settings (date, time, decimal separator, currency).

## Events

Use standard wx events for sync:

```python
import wx

# Sync on focus loss (recommended - same pattern as subject field)
ctrl.Bind(wx.EVT_KILL_FOCUS, self.onFocusLost)
def onFocusLost(self, event):
    value = ctrl.GetValue()  # or GetTime(), GetDate(), GetDuration()
    event.Skip()
```

## Creating Custom Controls

Subclass `MaskedFieldsCtrl`:

```python
class MyDurationCtrl(MaskedFieldsCtrl):
    def __init__(self, parent, days=0, hours=0, minutes=0,
                 dayChoices=None, hourChoices=None, minuteChoices=None):
        elements = [
            ("day", days, dayChoices),
            ("literal", _("d") + " "),
            ("hour", hours, hourChoices),
            ("literal", ":"),
            ("minute", minutes, minuteChoices),
        ]
        super().__init__(parent, elements)

    def GetDuration(self):
        return date.TimeDelta(
            days=self.GetFieldValue('day'),
            hours=self.GetFieldValue('hour'),
            minutes=self.GetFieldValue('minute')
        )

    def SetDuration(self, duration):
        if duration is None:
            duration = date.TimeDelta()
        total = int(duration.total_seconds())
        days, remainder = divmod(total, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes = remainder // 60
        self.SetFieldValue('day', days)
        self.SetFieldValue('hour', hours)
        self.SetFieldValue('minute', minutes)
```

## Translation

Literal strings can use `_()` for translation:

```python
("literal", _("d") + " ")     # day suffix
("literal", " " + _("days") + " ")  # verbose
```

Add to `.po` files:
```
msgid "d"
msgstr "T"  # German: Tag
```

## Demo

```bash
python3 docs/scripts/datetime_controls_demo.py
```

## Technical Notes

### Module Structure

The module is fully self-contained with these components:

- **Helper functions**: `getTextCtrlContentOffset()` (system metrics for custom painting), `monthcalendarex()` (calendar grid generation)
- **Event types**: `EVT_POPUP_DISMISS`, `EVT_CHOICE_SELECTED`, `EVT_CHOICE_PREVIEW`
- **Event classes**: `PopupDismissEvent`, `ChoiceSelectedEvent`, `ChoicePreviewEvent`
- **Popup classes**: `_PopupWindow` (base), `_ChoicesPopup` (dropdown), `_CalendarPopup` (date selection)
- **Field class**: `NumericField` (individual editable subfield)
- **Control classes**: `MaskedFieldsCtrl` (base), `DurationCtrl`, `DurationCtrlVerbose`, `TimeCtrl`, `TimeWithSecondsCtrl`, `DateCtrl`, `DateComboCustomCtrl`, `DateComboRouterCtrl` (router), `DateTimeComboCtrl`

### Font Customization

Controls use `self.GetFont()` for rendering, allowing callers to customize the font:

```python
ctrl = DurationCtrl(parent, days=1, hours=2, minutes=30)
ctrl.SetFont(wx.Font(12, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
```

### Custom Painting

The control uses `wx.EVT_PAINT` with `wx.PaintDC` for custom rendering. Each subfield and literal is positioned during `__init__` and stored in `_widgets` as `(item, x, y, w, h)` tuples.

### Theme Colours

Most colours are queried from `wx.SystemSettings` at paint time for live theme switching. Calendar-specific colours are configurable via **Edit > Preferences > Theme** with separate settings for light and dark modes.

**MaskedFieldsCtrl (date/time entry fields):**

| Element | Colour Source | Notes |
|---------|--------------|-------|
| Normal text | `SYS_COLOUR_WINDOWTEXT` | Both field values and literal separators |
| Focused field background | `DrawItemSelectionRect` | Native selection rendering |
| Focused field text | `SYS_COLOUR_HIGHLIGHTTEXT` | |
| Disabled "N/A" text | `SYS_COLOUR_GRAYTEXT` | Shown when checkbox unchecked |
| Read-only text | `SYS_COLOUR_GRAYTEXT` | Shown when `SetEditable(False)` |
| Border | `DrawTextCtrl` | Native border with focus/disabled flags |

**Calendar Popup (`_CalendarPopup`):**

| Element | Colour Source | Notes |
|---------|--------------|-------|
| Header text (month/year) | `SYS_COLOUR_WINDOWTEXT` | |
| Navigation arrows | `SYS_COLOUR_WINDOWTEXT` | Prev/next month, today button |
| Weekday header background | `calendar_light/dark.weekday_header_bg` | Configurable in Theme preferences |
| Weekday header foreground | `calendar_light/dark.weekday_header_fg` | Configurable in Theme preferences |
| Weekday day numbers | `SYS_COLOUR_WINDOWTEXT` | Mon-Fri |
| Weekend day numbers | `calendar_light/dark.weekend_day_fg` | Configurable in Theme preferences |
| Inactive days background | `SYS_COLOUR_BTNFACE` | Days outside min/max range (not hoverable) |
| Other month days background | `SYS_COLOUR_BTNFACE` | Days not in current month |
| Highlighted day background | `DrawItemSelectionRect` | Native selection (hover/keyboard), drawn on top of backgrounds |
| Highlighted day text | `SYS_COLOUR_HIGHLIGHTTEXT` | Works for both current and other-month days |
| Today border | `calendar_light/dark.today_border` | Configurable in Theme preferences |
| Popup border | `DrawTextCtrl` | With `CONTROL_FOCUSED` flag |

**Calendar Colour Defaults:**

| Setting | Light Mode | Dark Mode |
|---------|-----------|-----------|
| `weekday_header_bg` | (192, 192, 192) grey | (60, 60, 60) dark grey |
| `weekday_header_fg` | (0, 0, 255) blue | (100, 160, 255) soft blue |
| `weekend_day_fg` | (255, 0, 0) red | (255, 100, 100) soft red |
| `today_border` | (255, 0, 0) red | (255, 100, 100) soft red |

### Native Theme Border

Controls use `wx.RendererNative.Get().DrawTextCtrl()` to draw borders matching the system theme:
- Rounded corners on modern themes
- Blue focus ring when control has focus
- Greyed background when disabled or read-only

Flags passed to the renderer:
- `wx.CONTROL_FOCUSED`: When control has focus (not in read-only mode)
- `wx.CONTROL_DISABLED`: When disabled or in read-only mode

### System Metrics for Cross-Platform Compatibility

The controls use `wx.SystemSettings.GetMetric()` to obtain system-specific spacing and padding values, ensuring native appearance across different operating systems and DPI settings.

**Key metrics used:**

| Metric | Purpose | Typical Values |
|--------|---------|----------------|
| `wx.SYS_EDGE_X` | Horizontal 3D border padding | 2px (Windows), varies by theme |
| `wx.SYS_EDGE_Y` | Vertical 3D border padding | 2px (Windows), varies by theme |
| `wx.SYS_BORDER_X` | Inner gap between border and content | 1px |
| `wx.SYS_BORDER_Y` | Inner gap between border and content | 1px |

**Total content offset:** Standard text controls have a visible gap between the border decoration and the content/selection area. This is achieved by combining both metrics:

```
contentOffset = SYS_EDGE + SYS_BORDER
```

**Usage pattern:**

The module provides a helper function `getTextCtrlContentOffset()` that encapsulates the system metrics logic with proper fallbacks:

```python
from taskcoachlib.widgets.maskedtimectrl import getTextCtrlContentOffset

# Get content offset for custom-painted controls
contentOffsetX, contentOffsetY = getTextCtrlContentOffset()

# Draw content starting at (contentOffsetX, contentOffsetY)
# Content width = controlWidth - contentOffsetX * 2
```

**Internal implementation (in the helper function):**

```python
def getTextCtrlContentOffset():
    # Border padding (3D edge for DrawTextCtrl)
    borderPadX = wx.SystemSettings.GetMetric(wx.SYS_EDGE_X)
    borderPadY = wx.SystemSettings.GetMetric(wx.SYS_EDGE_Y)
    if borderPadX < 0:
        borderPadX = 2  # Fallback if not supported
    if borderPadY < 0:
        borderPadY = 2

    # Inner gap between border and content (1px gap in standard controls)
    innerGapX = wx.SystemSettings.GetMetric(wx.SYS_BORDER_X)
    innerGapY = wx.SystemSettings.GetMetric(wx.SYS_BORDER_Y)
    if innerGapX < 0:
        innerGapX = 1
    if innerGapY < 0:
        innerGapY = 1

    return (borderPadX + innerGapX, borderPadY + innerGapY)
```

**Why this matters:**

1. **DPI Awareness**: System metrics scale automatically with display DPI
2. **Theme Consistency**: Values match the current OS theme
3. **Platform Independence**: Same code works across Windows, macOS, Linux
4. **Future Proofing**: New OS versions with different metrics handled automatically

**Other useful SystemSettings methods:**

```python
# Get system colors for native appearance
wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOX)      # List background
wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT) # Selected text
wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)    # Selection background
wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)     # Disabled text
```

### Read-Only Mode

All `MaskedFieldsCtrl`-based controls support read-only mode:

```python
ctrl.SetReadOnly(True)   # Values visible but greyed, not editable
ctrl.SetReadOnly(False)  # Normal editable mode
ctrl.IsReadOnly()        # Check read-only state
```

In read-only mode:
- Values are displayed with system grey text color (`wx.SYS_COLOUR_GRAYTEXT`)
- Background uses native disabled styling
- Keyboard input is blocked (except Tab for navigation)
- Mouse clicks do not open dropdowns or calendar

### Focus Management

- `wx.WANTS_CHARS` style captures Tab and arrow keys before default processing
- `_hasFocus` tracks whether control has system focus
- `_focus` tracks which subfield is currently selected
- `_focusStamp` records when focus was gained to prevent popup on initial click
- `_returningFromPopup` flag preserves subfield focus after popup closes

### Popup Toggle Logic

The popup toggle uses timing thresholds to handle race conditions:
- `FOCUS_DELAY` (50ms): Prevents popup on initial focus click
- `POPUP_TOGGLE_DELAY` (200ms): Detects click-to-close toggle

When popup closes via deactivate (click outside), `_popupDismissedWidget` and `_popupDismissedTime` track which field's popup was just closed, preventing immediate reopen on the same click.

### Dropdown Width and Position

The dropdown width uses the field width as minimum, ensuring the popup is at least as wide as the field. The popup is centered horizontally below the field so numeric values align visually.

### Events from Popup

The popup fires three events:
- `EVT_CHOICE_PREVIEW`: Arrow key navigation in dropdown (live update to field)
- `EVT_CHOICE_SELECTED`: Enter key or click selection (confirms value)
- `EVT_POPUP_DISMISS`: Popup closed for any reason (Escape, click outside, selection)

### Sync Pattern: EVT_VALUE_CHANGED (DateTimeComboCtrl)

DateTimeComboCtrl uses `EVT_VALUE_CHANGED` for AttributeSync synchronization.
This single event fires on all value changes: checkbox toggle, date edit,
and time edit. The checkbox is an internal implementation detail — external
code never binds to `EVT_CHECKBOX`.

Other controls (subject, description, budget, etc.) still use
`EVT_KILL_FOCUS` for synchronization to batch typed edits.

**AttributeSync Usage:**

```python
self._plannedStartDateTimeSync = attributesync.AttributeSync(
    "plannedStartDateTime",
    self._plannedStartDateTimeCombo,
    plannedStartDateTime,
    self.items,
    command.EditPlannedStartDateTimeCommand,
    widgets.EVT_VALUE_CHANGED,  # Fires on checkbox toggle AND date/time edits
    self.items[0].plannedStartDateTimeChangedEventType(),
)
```

**Setters:**
- `SetTime(t)` - TimeCtrl, TimeWithSecondsCtrl
- `SetDate(d)` - DateCtrl, DateComboCustomCtrl
- `SetDuration(d)` - DurationCtrl, DurationCtrlVerbose

**ValidateChange for Field Validation:**

The `ValidateChange()` method is used for field-level validation (e.g., clamping day to valid range when month changes), not for event firing:

```python
def ValidateChange(self, field, value):
    """Validate date changes, adjusting day if needed for month/year changes."""
    year = self.GetFieldValue('year')
    month = self.GetFieldValue('month')
    day = self.GetFieldValue('date_day')
    max_day = calendar.monthrange(year, month)[1]
    if day > max_day:
        self.SetFieldValue('date_day', max_day)
    return value
```

### Refresh and Update for Visual Sync

After updating field values programmatically (e.g., from `AttributeSync.onAttributeChanged()`), both `Refresh()` and `Update()` are called:

```python
self.__observer.Refresh()  # Mark for repaint
self.__observer.Update()   # Force immediate repaint
```

`Update()` is necessary because `Refresh()` only schedules a repaint for the next event loop iteration. During synchronous pubsub callbacks, this may not happen quickly enough, causing visual lag. `Update()` forces immediate processing of pending paint events.

### Sub-Control Stash Model

The sub-controls (DateComboRouterCtrl, TimeCtrl) are the stash for DateTimeComboCtrl. They
always hold a datetime value — they cannot be empty. When the checkbox is
unchecked, the sub-controls are hidden behind the "N/A" overlay but retain
their values. When the checkbox is checked, those same values become visible
and are returned by `GetValue()`. The checkbox is the gate; the sub-controls
are the stash.

At construction, the sub-controls are initialized with either:
- The domain value (`value` parameter), if the field is active (preset mode), or
- The preference-suggested datetime (`suggestedValue` parameter), if the field
  is inactive (propose mode), or
- `datetime.now()` as a fallback

See [DATETIME_PRESETS.md](DATETIME_PRESETS.md) for how `suggestedValue` is
computed from user preferences and passed at editor construction time
([Propose Mode](DATETIME_PRESETS.md#propose-mode),
[Suggested DateTime Computation](DATETIME_PRESETS.md#suggested-datetime-computation)).

The `_suggestedValue` constructor parameter is a one-time injection point.
Once the sub-controls are initialized, they are the single holder of the
datetime value regardless of checked/unchecked state. No separate stash
variable is needed for activate/deactivate cycles — the sub-controls
survive naturally.

**State Transition Event Contract:**

`ActivateValue()` and `DeactivateValue()` toggle the checkbox, which changes
the widget's externally-visible value (`GetValue()` returns real datetime vs
domain sentinel). Every such toggle must fire `EVT_VALUE_CHANGED` — this is
the contract that keeps AttributeSync in sync with the widget.

- **`ActivateValue(value=None)`**: If `value` provided, write to sub-controls
  via `SetDate`/`SetTime`. Check checkbox. Fire `EVT_VALUE_CHANGED`.
- **`DeactivateValue()`**: Uncheck checkbox. Fire `EVT_VALUE_CHANGED`.
  Sub-controls retain their values (they are the stash).

**Why explicit event firing is needed:**

Sub-controls fire their own events via `NotifyValueChanged()` when
`SetDate`/`SetTime` are called. But a checkbox toggle alone — without writing
to sub-controls — produces no sub-control event. The state transition methods
must fire explicitly to cover this case. Redundant events from sub-control
writes are harmless — AttributeSync's same-value guard deduplicates.

**User click path:** `_onCheckboxChanged` → `ActivateValue()`/`DeactivateValue()`
→ event fires from within the method.

**Programmatic path:** Editor calls `ActivateValue()`/`DeactivateValue()`
directly. Same event contract — the widget is self-contained.

## Wayland

### Problem

On Wayland, the dropdown popups (`_ChoicesPopup`, `_CalendarPopup`) appear at screen center instead of below their parent control. This is because:

- `_PopupWindow` uses `wx.Dialog` which maps to **xdg_toplevel** on Wayland
- Wayland does not allow apps to position xdg_toplevel windows
- `ClientToScreen()` returns wrong coordinates (often 0,0)
- `Move()` / `SetPosition()` is silently ignored by the compositor

Works correctly on X11 because X11 allows absolute screen positioning.

### Why GDK_BACKEND=x11 Is Not Viable

Forcing `GDK_BACKEND=x11` to run under XWayland is **NOT** a viable or sustainable solution:

- Requires user intervention (environment variable or wrapper script)
- Loses Wayland-native benefits (fractional scaling, gesture support, security)
- XWayland is a compatibility shim, not a target platform
- Not discoverable — users won't know why popups are misplaced
- Doesn't fix the root cause

### Solution: wx.PopupWindow on Wayland

`wx.PopupWindow` maps to **xdg_popup** on Wayland, which compositors DO position relative to their parent window. On Wayland, `_PopupWindow` uses `wx.PopupWindow` as its base class instead of `wx.Dialog`.

The GTK3 caret visibility bug (wxWidgets #18261) that affects `wx.PopupTransientWindow` does not apply here because:

- `_ChoicesPopup` uses a custom-painted list (no text input)
- `_CalendarPopup` is fully custom-painted (no text input)
- Only the icon picker had a SearchCtrl, and that was converted to a modal dialog

Platform-conditional base class:
- **Wayland**: `wx.PopupWindow` (xdg_popup, compositor-positioned)
- **X11/macOS**: `wx.Dialog` (proven cross-platform, absolute positioning works)

## 2026-Jan Refactor: ComboCtrl Integration

### Motivation

The original date control used `_PopupWindow` (wx.Dialog) for its calendar popup, which cannot be positioned on Wayland (xdg_toplevel ignores Move()/SetPosition()). Custom dropdown buttons using `RendererNative.DrawComboBoxDropButton()` are also invisible on Wayland.

### Approach

Use `wx.ComboCtrl` which provides a **native dropdown button** and manages popup positioning natively (including Wayland-safe xdg_popup). The inner date field is a clean `MaskedFieldsCtrl` subclass with all popup/frame logic removed.

### Key Classes

**`DateCtrl(MaskedFieldsCtrl)`** — Clean date control for embedding inside a ComboCtrl:
- No calendar popup, no frame drawing (`_drawFrame=False`), no field dropdown popups
- F4/Enter delegates to parent ComboCtrl.Popup()
- Click only changes subfield focus (no popup toggle)
- Custom `_onPaint` using `IsThisEnabled()` (own state) so parent ComboCtrl's disabled state for read-only mode shows greyed values, not "N/A"
- Same date validation, GetDate/SetDate, locale-aware format as DateComboCustomCtrl

**`DateComboCustomCtrl(wx.ComboCtrl)`** — ComboCtrl wrapper around `DateCtrl`:
- Native dropdown button and popup management
- `_CalendarComboPopup` for the calendar dropdown
- `SetReadOnly(True)` disables the ComboCtrl (greys button) + sets inner control read-only
- `Enable(False)` disables both ComboCtrl and inner control (shows "N/A")
- `HasOpenPopup()` — public API using `IsPopupShown()`
- `Bind()` override forwards UI events (EVT_KEY_DOWN, EVT_KILL_FOCUS, EVT_SET_FOCUS) to inner control
- Focus redirection from ComboCtrl's text control to inner DateCtrl

**`DateComboRouterCtrl`** — Router function returning the platform-appropriate date combo:
- Windows: `_NativeDateCtrl` (native `wx.adv.DatePickerCtrl` wrapper)
- Elsewhere (Linux, macOS): `DateComboCustomCtrl`

**`DateTimeComboCtrl(wx.EvtHandler)`** — Composite date/time control:
- Inherits from `wx.EvtHandler` so it can host event handlers directly
- Composes checkbox + `DateComboRouterCtrl` + `TimeCtrl`
- Owns the change event: fires `EVT_VALUE_CHANGED` on sub-control blur
  and from `ActivateValue()`/`DeactivateValue()`
- Traps and drops sub-control `EVT_VALUE_CHANGED` (debug log point)
- See [DateTimeComboCtrl Event Ownership](#datetimecomboctrl-event-ownership)

**DateTimeComboCtrl States:**

| State | Visual | Entered Via |
|-------|--------|------------|
| **Active + Editable** | Checkbox checked/enabled, fields editable | `ActivateValue()`, `SetEditable()` |
| **Inactive** | Checkbox unchecked/enabled, fields show "N/A" | `DeactivateValue()`, construct with `value=None` |
| **Active + Read-only** | Checkbox checked/disabled, fields greyed | `SetReadOnly()` |

**DateTimeComboCtrl State Transition Methods:**

| Method | Effect | Duration Calc Ref |
|--------|--------|-------------------|
| `ActivateValue(value=None)` | Inactive → Active. If `value` provided, writes to sub-controls. Checks checkbox. Fires `EVT_VALUE_CHANGED`. See [Sub-Control Stash Model](#sub-control-stash-model). | Steps 2.1, 3.1 |
| `DeactivateValue()` | Active → Inactive. Unchecks checkbox. Sub-controls retain values (they are the stash). Fires `EVT_VALUE_CHANGED`. See [Sub-Control Stash Model](#sub-control-stash-model). | Steps 2.5.2, 3.5.2 |
| `SetEditable()` | Make combo editable (no args) | UI Field States |
| `SetReadOnly()` | Make combo read-only (no args) | UI Field States |
| `HideCheckBox()` | Hide checkbox for always-active controls | Effort start |

**DateTimeComboCtrl State Query Methods:**

| Method | Returns |
|--------|---------|
| `IsActive()` | True if control has an active value (non-null) |
| `IsEditable()` | True if editable (not read-only) |
| `IsReadOnly()` | True if read-only |

**DateTimeComboCtrl Value Access:**

| Method | Type |
|--------|------|
| `GetValue()` / `SetValue()` | `date.DateTime` (domain-compatible for AttributeSync). `SetValue` routes through `ActivateValue`/`DeactivateValue`. |
| `GetDateTime()` | `datetime.datetime` or `None` (read-only) |
| `GetDate()` | `datetime.date` (read-only) |
| `GetTime()` | `datetime.time` (read-only) |

**DateTimeComboCtrl Layout Accessors** (for sizer arrangement, not state logic):

| Method | Returns |
|--------|---------|
| `GetCheckBox()` | `wx.CheckBox` |
| `GetDateCtrl()` | `DateComboCustomCtrl` |
| `GetTimeCtrl()` | `TimeCtrl` / `TimeWithSecondsCtrl` |
| `GetWidgets()` | Tuple of all three |
| `CreateRowPanel(parent)` | `wx.Panel` with all three arranged horizontally |

**Deprecated methods** (log warnings, no-op, prefer semantic methods above):
- `SetDateTime()` → `ActivateValue(datetime)` / `DeactivateValue()`
- `SetDate()` → `ActivateValue(datetime)`
- `SetTime()` → `ActivateValue(datetime)`
- `IsChecked()` → `IsActive()`
- `SetChecked(bool)` → `ActivateValue()` / `DeactivateValue()`
- `Activate()` → `ActivateValue()`
- `Deactivate()` → `DeactivateValue()`
- `Enable(bool)` → `SetEditable()` / `DeactivateValue()` + `SetReadOnly()`
- `Disable()` → `DeactivateValue()` + `SetReadOnly()`
- `IsEnabled()` → `IsEditable()`

**`_CalendarComboPopup(wx.ComboPopup)`** — Adapter wrapping the custom-painted calendar:
- `Create()` — creates interior panel, binds paint/mouse/key events
- `GetAdjustedSize()` — returns calendar dimensions
- `GetStringValue()` — returns selected date as ISO string
- `OnPopup()` — syncs selection from parent DateComboCustomCtrl
- Duck-typed `_getDateComboCustomCtrl()` finds parent via `hasattr` checks

### Focus Management in DateComboCustomCtrl

The ComboCtrl's internal text control is hidden behind the overlaid `DateCtrl`. DateComboCustomCtrl handles this by:

1. **Focus redirection**: `EVT_SET_FOCUS` on the ComboCtrl's text control redirects focus to the inner DateCtrl, with a `_redirectingFocus` guard to prevent recursion.
2. **Text interception**: `EVT_TEXT` handler clears any text the ComboCtrl auto-inserts.
3. **Post-selection focus**: After calendar date selection, focus moves to inner DateCtrl via `wx.CallAfter`.

### Wiring

`__init__.py` exports:
- `DateCtrl`
- `DateComboCustomCtrl`
- `DateComboRouterCtrl` (router)
- `DateTimeComboCtrl`

### Demo

Interactive demo showing all controls (duration, time, date, datetime combos)
with various configurations. Run from the project root:

```
python3 docs/scripts/datetime_controls_demo.py
```

## Platform-Specific DateComboRouterCtrl: Native Windows, Custom Elsewhere

TaskCoach requires two capabilities from a date picker control:

1. **Masked input** — day, month, and year are independently navigable and
   editable subfields (arrow keys move between fields, typing replaces the
   focused field). This prevents invalid freeform text entry and provides a
   consistent editing experience.
2. **Format override** — the display order and separator must match the user's
   chosen format (e.g. `YMD-`, `DMY/`, `MDY.`) from Preferences → Regional,
   not just the OS locale default.

`DateComboRouterCtrl` selects the implementation per platform based on whether
the native control satisfies both requirements:

| Platform | Native Control         | Masked Input | Format Override        | Router Returns          |
|----------|------------------------|--------------|------------------------|-------------------------|
| Windows  | Win32 Date-Time Picker | Yes          | Yes (`DTM_SETFORMATW`) | `_NativeDateCtrl`       |
| Linux    | GTK date entry         | No           | No                     | `DateComboCustomCtrl`   |
| macOS    | NSDatePicker           | Yes          | No (wxWidgets #9888)   | `DateComboCustomCtrl`   |

On **Linux**, `wx.adv.DatePickerCtrl` wraps a GTK widget that is a plain text
entry with a dropdown calendar — not a masked control. There is no GTK API to
set a custom date display format. Neither requirement is met, so Linux uses the
custom ComboCtrl + `DateCtrl` architecture.

On **Windows**, the native Win32 Date-Time Picker is already masked (each
subfield is independently selectable and editable) and supports
`DTM_SETFORMATW` for arbitrary format strings. Both requirements are met, and
the native control also fixes the rendering and focus problems that
`DateComboCustomCtrl` has on Windows (see below).

On **macOS**, `NSDatePicker` is masked but wxPython does not expose its format
API, and wxWidgets hardcodes MM/DD/YYYY regardless of locale. Only one
requirement is met, so macOS uses the custom control.

### Windows — Native DatePickerCtrl with DTM_SETFORMAT

**Problem:** On Windows, `DateCtrl` (a custom-painted `wx.Panel`)
inside the `wx.ComboCtrl` renders as a white box with no visible date text.
The panel's background painting conflicts with the ComboCtrl's native text
area. Tab navigation also breaks due to the focus redirection between the
ComboCtrl's internal text control and the inner panel (see
[Focus Management in DateComboCustomCtrl](#focus-management-in-datecombocustomctrl)).

**Solution:** On Windows, `DateComboRouterCtrl` returns a native `wx.adv.DatePickerCtrl` (the
Win32 Date-Time Picker control) instead of the ComboCtrl + `DateCtrl`
approach. This provides correct rendering, native keyboard navigation, and
accessibility out of the box.

**Format override:** The native Win32 Date-Time Picker supports the
`DTM_SETFORMATW` message (`0x1032`) to set an arbitrary display format at any
time. This is sent via `ctypes.windll.user32.SendMessageW`. The app's format
codes (see [Locale and Date Format Settings](#locale-and-date-format-settings))
are converted to Win32 date format tokens:

| App Format Code | Win32 Format String | Display |
|-----------------|--------------------:|---------|
| `"YMD-"` | `yyyy-MM-dd` | 2026-01-18 |
| `"YMD/"` | `yyyy/MM/dd` | 2026/01/18 |
| `"MDY/"` | `MM/dd/yyyy` | 01/18/2026 |
| `"DMY/"` | `dd/MM/yyyy` | 18/01/2026 |
| `"DMY."` | `dd.MM.yyyy` | 18.01.2026 |
| `""` (auto) | Detected from locale | varies |

**Live update:** `SetDateFormat(dateFormat)` re-sends `DTM_SETFORMATW` — the
native control updates instantly without needing to destroy/recreate.

### macOS — Custom Control (No Native Format Override)

`wx.adv.DatePickerCtrl` on macOS wraps `NSDatePicker`, which is a
segmented/masked control (each date component is independently editable with
stepper arrows). However:

- wxPython does not expose `NSDatePicker.dateFormatter` — there is no way to
  set a custom format without adding a PyObjC dependency.
- [wxWidgets #9888](https://github.com/wxWidgets/wxWidgets/issues/9888) (open
  since 2008) — the macOS `DatePickerCtrl` ignores the system locale and
  hardcodes MM/DD/YYYY.

Therefore macOS continues using `DateComboCustomCtrl` (the ComboCtrl +
`DateCtrl` architecture documented in [Key Classes](#key-classes)),
which correctly respects the app's format settings.

### Architecture — Factory Function

`DateComboRouterCtrl` is a router function that returns the appropriate implementation
for the current platform:

- **Windows** (`wx.Platform == '__WXMSW__'`): `_NativeDateCtrl` — wraps
  `wx.adv.DatePickerCtrl` with `DTM_SETFORMATW` for format control.
- **Elsewhere** (Linux, macOS): `DateComboCustomCtrl` — the ComboCtrl +
  `DateCtrl` architecture.

Both implementations expose the same public API:

| Method | Description |
|--------|-------------|
| `GetDate()` | Returns `datetime.date` |
| `SetDate(d)` | Sets date (`datetime.date` or `None` → today) |
| `SetDateFormat(fmt)` | Change display format (live on Windows, rebuild on others) |
| `SetReadOnly(bool)` | Grey values, block editing |
| `IsReadOnly()` | Query read-only state |
| `HasOpenPopup()` | Whether calendar popup is open |
| `DismissPopup()` | Close any open popup |
| `Enable(bool)` | Enable/disable (shows "N/A" when disabled) |
| `SetFocus()` | Move focus to the control |
| `Bind(evt, handler)` | Event binding with forwarding |

**Event bridging:** The Windows native wrapper translates
`wx.adv.EVT_DATE_CHANGED` from the native picker into the app's
`EVT_VALUE_CHANGED` (see [Events](#events)), so `DateTimeComboCtrl` and
`AttributeSync` work without changes.

### Preferences Demo Live Update

The Preferences → Regional date format preview (in `preferences.py`
`_rebuildDemoDateCtrl()`) destroys and recreates the `DateComboRouterCtrl`.
On Windows, `_NativeDateCtrl.SetDateFormat()` could update the native control
in place via `DTM_SETFORMATW`, but the current rebuild approach works on all
platforms.

- **Windows:** `DTM_SETFORMATW` updates the native control in place (via `SetDateFormat()`).
- **Other platforms:** Destroys and recreates the `DateComboRouterCtrl`
  with the new field order and separator, preserving the current date value.
