# DateTime Controls

Simple time and duration input controls with explicit subfields and translatable labels.
Self-contained module with custom-painted single field and navigable subfields.

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

Controls must update automatically when the underlying data changes from external sources (background tasks, other windows, other processes). This is handled by `AttributeSync`.

**Code reference:** `taskcoachlib/gui/dialog/attributesync.py`

`AttributeSync` provides bidirectional synchronization between UI controls and domain objects:

1. **User edits control** → `onAttributeEdited()` → executes command → updates domain
2. **External change to domain** → `onAttributeChanged()` → calls `control.SetValue()` → updates display

**Key methods AttributeSync expects on controls:**
- `GetValue()` - returns domain-compatible value (e.g., `date.DateTime`)
- `SetValue(newValue)` - sets value from domain type
- `Bind(eventType, handler)` - binds to control's change event

### Sync on Focus Loss (Same as Subject Field)

DateTimeCombo uses `wx.EVT_KILL_FOCUS` for synchronization, matching the subject field pattern. This prevents sorted lists from jumping around during edits - changes only sync when focus leaves the control.

**Code reference:** `taskcoachlib/gui/dialog/editor.py` (example usage)
```python
self._plannedStartDateTimeSync = attributesync.AttributeSync(
    "plannedStartDateTime",           # Attribute getter name on domain object
    self._plannedStartDateTimeCombo,  # Control with GetValue/SetValue
    plannedStartDateTime,             # Current value
    self.items,                       # Domain objects being edited
    command.EditPlannedStartDateTimeCommand,  # Command class
    wx.EVT_KILL_FOCUS,                # Sync when focus leaves (same as subject)
    self.items[0].plannedStartDateTimeChangedEventType(),  # Domain change event
    callback=self.__onPlannedStartChanged,
)
```

**Why EVT_KILL_FOCUS:**
- Standard wx event that fires when focus leaves the control
- List reorders only when edit is complete, not during typing
- Same pattern as subject field (SingleLineTextCtrl)

DateTimeCombo's `Bind()` method forwards `EVT_KILL_FOCUS` to all three sub-widgets (checkbox, date, time), so focus moving between them triggers sync - which is acceptable since each field change is a complete edit.

**Domain-compatible GetValue/SetValue:**

DateTimeCombo provides `GetValue()` and `SetValue()` that work with `date.DateTime` domain objects:

**Code reference:** `taskcoachlib/widgets/maskedtimectrl.py:1687-1717`
```python
def GetValue(self):
    """Returns date.DateTime() (sentinel) when unchecked, or
    date.DateTime.fromDateTime(dt) when checked."""
    if not self._checkbox.GetValue():
        return date.DateTime()  # Sentinel for "no value"
    dt = datetime.datetime.combine(self._dateCtrl.GetDate(), self._timeCtrl.GetTime())
    return date.DateTime.fromDateTime(dt)

def SetValue(self, newValue):
    """If newValue == date.DateTime() (sentinel), unchecks.
    Otherwise sets the value and checks."""
    if newValue == date.DateTime():
        self._checkbox.SetValue(False)
        self._updateEnabled()
    else:
        self._checkbox.SetValue(True)
        self._dateCtrl.SetDate(newValue.date())
        self._timeCtrl.SetTime(datetime.time(newValue.hour, newValue.minute, newValue.second))
        self._updateEnabled()
```

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
| **Enter** | Open dropdown for current field (if choices provided) |
| **Escape** | Close dropdown without changing value |
| **0-9** | Type digits directly into field |
| **Backspace/Delete** | Remove last digit from field |

### Dropdown Behavior

The dropdown popup is self-contained (`_ChoicesPopup` class).

**Opening the dropdown** (only if choices were provided):
- Click on a subfield to open its dropdown
- Press Enter when a subfield is focused
- Clicking the same field with dropdown open closes it (toggle behavior)

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
- `dayChoices, hourChoices, minuteChoices, secondChoices`: Dropdown choices (None = no dropdown)
- `showSeconds`: If True, include seconds field (default False)

```python
# Without seconds (default)
ctrl = DurationCtrl(parent, days=1, hours=8, minutes=30,
    dayChoices=[0, 1, 2, 3, 5, 7, 14, 30],
    hourChoices=list(range(24)),
    minuteChoices=[0, 15, 30, 45])

# With seconds (for effort tracking)
ctrl = DurationCtrl(parent, days=0, hours=2, minutes=30, seconds=15,
    dayChoices=None,
    hourChoices=list(range(24)),
    minuteChoices=[0, 15, 30, 45],
    showSeconds=True,
    secondChoices=[0, 15, 30, 45])

duration = ctrl.GetDuration()  # timedelta
ctrl.SetDuration(timedelta(days=1, hours=2))
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
- `dayChoices, hourChoices, minuteChoices, secondChoices`: Dropdown choices (None = no dropdown)
- `showSeconds`: If True, include seconds field (default False)

```python
# Without seconds (default)
ctrl = DurationCtrlVerbose(parent, days=0, hours=0, minutes=0,
    dayChoices=[0, 1, 2, 3, 5, 7],
    hourChoices=list(range(24)),
    minuteChoices=[0, 15, 30, 45])

# With seconds (for effort tracking)
ctrl = DurationCtrlVerbose(parent, days=0, hours=2, minutes=30, seconds=15,
    dayChoices=None,  # Hide days dropdown
    hourChoices=list(range(24)),
    minuteChoices=[0, 15, 30, 45],
    showSeconds=True,
    secondChoices=[0, 15, 30, 45])

duration = ctrl.GetDuration()  # datetime.timedelta
ctrl.SetDuration(datetime.timedelta(hours=1, minutes=30))
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

### DateCtrl
Locale-aware date control with automatic field ordering and separators.

The control automatically detects the system locale's date format using `strftime("%x")` and arranges the year/month/day fields accordingly:
- **US locale**: `01/18/2026` (month/day/year with `/`)
- **European locales**: `18/01/2026` (day/month/year with `/`)
- **ISO/Canadian locale**: `2026-01-18` (year-month-day with `-`)

Click or Enter opens a calendar popup for date selection. Arrow keys in the calendar navigate by day (left/right) or week (up/down). Navigation buttons allow month changes and jumping to today.

```python
ctrl = DateCtrl(parent, year=2026, month=1, day=18)
ctrl = DateCtrl(parent)  # Defaults to today's date
ctrl = DateCtrl(parent, minDate=datetime.date(2020, 1, 1), maxDate=datetime.date(2030, 12, 31))
date = ctrl.GetDate()  # datetime.date
ctrl.SetDate(datetime.date(2026, 6, 15))
```

Individual date fields can still be edited with Up/Down arrows and typed digits.

**Locale Detection:** The `getLocaleDateFormat()` helper function parses `strftime("%x")` output to determine field order and separator, matching the behavior of the old `smartdatetimectrl.py`.

**User Override:** Users can override the automatic locale detection in **Preferences → Regional**:
- **Date format**: Automatic, YYYY-MM-DD (ISO), YYYY/MM/DD (East Asian), MM/DD/YYYY (US), DD/MM/YYYY (European), DD.MM.YYYY (German)
- **Time format**: Automatic, 24-hour, 12-hour with AM/PM

**Note:** When "Automatic" time format is selected, the default is 24-hour format (matching the old `smartdatetimectrl` behavior, which was hardcoded to 24-hour). Users can explicitly select "12-hour" to enable AM/PM display.

The settings are stored in `TaskCoach.ini` under `[view]` as `dateformat` and `timeformat`. Helper functions:
- `getEffectiveDateFormat()` - Returns format tuple respecting user settings
- `getEffectiveTimeFormat()` - Returns "24" or "12" respecting user settings (defaults to "24" when automatic)
- `getDateFormatFromSettings()` - Raw setting value
- `getDateFormatFunctionForOldControl()` - Format function for legacy smartdatetimectrl

### DateTimeCombo
Flexible combo providing checkbox, DateCtrl, and TimeCtrl as separate widgets for table layout alignment.

**Constructor:**
```python
DateTimeCombo(parent, value=None, hourChoices=None, minuteChoices=None, showSeconds=False, secondChoices=None)
```

**Parameters:**
- `parent`: Parent window
- `value`: `datetime.datetime` object (checked) or `None` (unchecked)
- `hourChoices`: List of hour values for dropdown, or `None` for no dropdown
- `minuteChoices`: List of minute values for dropdown, or `None` for no dropdown
- `showSeconds`: If `True`, use TimeWithSecondsCtrl instead of TimeCtrl
- `secondChoices`: List of second values for dropdown (only used if `showSeconds=True`)

**Checkbox State Determined by Value:**
- `value=datetime` → checkbox checked, fields show that datetime
- `value=None` → checkbox unchecked, fields disabled

**Three States:**
1. **Checked** (normal): checkbox ON, fields enabled and editable
2. **Unchecked**: checkbox OFF, fields disabled, `GetDateTime()` returns `None`
3. **Inactive** (`SetEditable(False)`): checkbox ON but disabled, fields show values greyed out (read-only, not editable)

**Default to "Now":** When unchecked and user checks the checkbox, "now" is used as the initial value.

```python
import datetime

# Checked combo with specific datetime (value=datetime means checked)
combo = DateTimeCombo(panel,
    value=datetime.datetime(2026, 1, 20, 9, 0),
    hourChoices=[8, 9, 10, 11, 12],
    minuteChoices=[0, 15, 30, 45])

# Unchecked combo (value=None means unchecked)
combo = DateTimeCombo(panel, value=None)  # Check to see "now"

# Initialization pattern for domain objects:
# The value alone determines the checked state
# Note: date.DateTime is a datetime.datetime subclass
value = existingValue if existingValue != date.DateTime() else None

combo = DateTimeCombo(panel, value=value,
    hourChoices=list(range(8, 18)),
    minuteChoices=[0, 15, 30, 45])

# Get individual widgets for flexible table layout
grid.Add(wx.StaticText(panel, label="Due date:"))  # Column 1: label
grid.Add(combo.GetCheckBox())   # Column 2: checkbox only
grid.Add(combo.GetDateCtrl())   # Column 3: date
grid.Add(combo.GetTimeCtrl())   # Column 4: time

# Or get all widgets as tuple
checkbox, dateCtrl, timeCtrl = combo.GetWidgets()

# Value access
dt = combo.GetDateTime()  # datetime or None if unchecked
combo.SetDateTime(datetime.datetime(2026, 1, 18, 14, 30))
combo.SetDateTime(None)  # Unchecks the checkbox

# State control
combo.SetEditable(False)  # Inactive: values visible but greyed, not editable
combo.SetEditable(True)   # Normal editable mode
combo.IsEditable()        # Check if editable
combo.IsChecked()         # Check if checkbox is checked
```

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

Subclass `FieldsCtrl`:

```python
class MyDurationCtrl(FieldsCtrl):
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
        return datetime.timedelta(
            days=self.GetFieldValue('day'),
            hours=self.GetFieldValue('hour'),
            minutes=self.GetFieldValue('minute')
        )

    def SetDuration(self, duration):
        if duration is None:
            duration = datetime.timedelta()
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
python3 docs/scripts/demo_maskedtimectrl.py
```

## Technical Notes

### Module Structure

The module is fully self-contained with these components:

- **Helper functions**: `getTextCtrlContentOffset()` (system metrics for custom painting), `monthcalendarex()` (calendar grid generation)
- **Event types**: `EVT_POPUP_DISMISS`, `EVT_CHOICE_SELECTED`, `EVT_CHOICE_PREVIEW`
- **Event classes**: `PopupDismissEvent`, `ChoiceSelectedEvent`, `ChoicePreviewEvent`
- **Popup classes**: `_PopupWindow` (base), `_ChoicesPopup` (dropdown), `_CalendarPopup` (date selection)
- **Field class**: `NumericField` (individual editable subfield)
- **Control classes**: `FieldsCtrl` (base), `DurationCtrl`, `DurationCtrlVerbose`, `TimeCtrl`, `TimeWithSecondsCtrl`, `DateCtrl`

### Font Customization

Controls use `self.GetFont()` for rendering, allowing callers to customize the font:

```python
ctrl = DurationCtrl(parent, days=1, hours=2, minutes=30)
ctrl.SetFont(wx.Font(12, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
```

### Custom Painting

The control uses `wx.EVT_PAINT` with `wx.PaintDC` for custom rendering. Each subfield and literal is positioned during `__init__` and stored in `_widgets` as `(item, x, y, w, h)` tuples.

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

All `FieldsCtrl`-based controls support read-only mode:

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

### Sync Pattern: Standard wx.EVT_KILL_FOCUS

The controls use standard `wx.EVT_KILL_FOCUS` for synchronization, just like other wx controls (e.g., SingleLineTextCtrl for subject field). This approach:

- Syncs only when the user finishes editing (focus leaves)
- Prevents list reordering during typing
- Uses standard wx events (no custom event types needed)
- Matches the pattern used throughout the application

**AttributeSync Usage:**

```python
self._plannedStartDateTimeSync = attributesync.AttributeSync(
    "plannedStartDateTime",
    self._plannedStartDateTimeCombo,
    plannedStartDateTime,
    self.items,
    command.EditPlannedStartDateTimeCommand,
    wx.EVT_KILL_FOCUS,  # Standard wx event
    self.items[0].plannedStartDateTimeChangedEventType(),
)
```

**Setters:**
- `SetTime(t)` - TimeCtrl, TimeWithSecondsCtrl
- `SetDate(d)` - DateCtrl
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
