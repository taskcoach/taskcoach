"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>

Task Coach is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Task Coach is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""
Simple time/duration controls with explicit subfields and translatable labels.

Visually identical to smartdatetimectrl Entry controls - single painted field
with navigable subfields. Uses explicit element lists instead of format strings.

Elements list:
- Tuple: (fieldType, value) or (fieldType, value, choices) - numeric subfield
- ("literal", "text") - static text label (use _() for translation)

Example:
    elements = [
        ("day", 1),                    # day field, no dropdown
        ("literal", "d "),
        ("hour", 2, [8, 9, 10, 17]),   # hour field with dropdown choices
        ("literal", ":"),
        ("minute", 30, [0, 15, 30, 45]),
    ]

Dropdown Choices - Static or Dynamic:
    Choices can be a list or a callable (for dynamic updates):

    # Static choices (evaluated once at creation):
    hourChoices=[8, 9, 10, 17, 18]

    # Dynamic choices (evaluated each time dropdown opens):
    hourChoices=lambda: get_hour_choices_from_settings(settings)

    Dynamic choices are useful when preferences may change while the control
    is open (e.g., user changes "Minutes between suggested times" in prefs).

IMPORTANT - Focus Event Handling for External Code:
    When binding EVT_KILL_FOCUS or EVT_SET_FOCUS to these controls from
    external code (e.g., editor dialogs, forms), the handler MUST call
    event.Skip() to allow the event to propagate to the control's internal
    focus handlers. Without event.Skip(), the control will not update its
    visual focus state (highlight won't clear on focus loss).

    Example (in editor.py or similar):
        # Binding in external code
        self._durationCtrl.Bind(wx.EVT_KILL_FOCUS, self.onDurationFocusLost)

        def onDurationFocusLost(self, event):
            # Do your processing...
            self.saveValue()
            event.Skip()  # REQUIRED - allows control to update focus state

    This is a fundamental wxPython/wxWidgets rule: focus event handlers should
    almost always call event.Skip() to allow default handling and propagation.
"""

import wx
import wx.adv
import math
import datetime
import time
import calendar
from pubsub import pub

from taskcoachlib.i18n import _
from taskcoachlib.domain import date


# =============================================================================
# Helper Functions
# =============================================================================

def getTextCtrlContentOffset():
    """Get the content offset for custom-painted controls that use DrawTextCtrl.

    Returns (offsetX, offsetY) - the total offset from control edge to content.
    This includes:
    - Border padding (SYS_EDGE): The 3D border drawn by DrawTextCtrl
    - Inner gap (SYS_BORDER): The 1px gap between border and content in standard controls

    Falls back to sensible defaults if metrics are unsupported (-1 on some platforms).

    Usage:
        offsetX, offsetY = getTextCtrlContentOffset()
        # Draw content starting at (offsetX, offsetY)
        # Content width = controlWidth - offsetX * 2
    """
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


def getLocaleDateFormat(override=None):
    """Detect or return the date format based on locale or override setting.

    Args:
        override: Optional format string to override locale detection.
                  Format: "XYZ?" where XYZ is field order (Y=year, M=month, D=day)
                  and ? is separator. E.g., "YMD-", "MDY/", "DMY.", "DMY/"

    Returns a tuple: (field_order, separator)
    - field_order: list of field names in display order, e.g., ['month', 'date_day', 'year']
    - separator: the separator character used between fields, e.g., '/' or '-' or '.'

    This mimics the approach from smartdatetimectrl.py to ensure the same
    locale-aware date formatting.
    """
    # Check for override setting
    if override:
        field_map = {'Y': 'year', 'M': 'month', 'D': 'date_day'}
        if len(override) >= 4:
            order_str = override[:3].upper()
            separator = override[3]
            field_order = [field_map.get(c, 'year') for c in order_str]
            return (field_order, separator)

    # Use a test date with unique values that are easy to identify:
    # year=3333, month=11, day=22 - these won't be confused with each other
    test_date = datetime.date(year=3333, month=11, day=22)
    formatted = test_date.strftime("%x")

    # Find positions of each component in the formatted string
    # Year could appear as "3333" (4-digit) or "33" (2-digit)
    year_pos = formatted.find("3333")
    if year_pos == -1:
        year_pos = formatted.find("33")

    month_pos = formatted.find("11")
    day_pos = formatted.find("22")

    # If we can't find all components, fall back to ISO format
    if year_pos == -1 or month_pos == -1 or day_pos == -1:
        return (['year', 'month', 'date_day'], '-')

    # Sort by position to get the order
    components = [
        (year_pos, 'year'),
        (month_pos, 'month'),
        (day_pos, 'date_day'),
    ]
    components.sort(key=lambda x: x[0])
    field_order = [comp[1] for comp in components]

    # Detect the separator by finding the first non-digit character after the first field
    # Common separators: '/', '-', '.'
    separator = '-'  # Default to ISO style
    for char in formatted:
        if char in '/-. ':
            separator = char
            break

    return (field_order, separator)


def getDetectedLocaleDateFormat():
    """Get the auto-detected locale date format (ignoring any override).

    Returns a tuple: (field_order, separator) detected from strftime("%x").
    """
    return getLocaleDateFormat(override=None)


def getDateFormatFromSettings():
    """Get the date format override from user settings.

    Returns the format string (e.g., "YMD-", "MDY/") or empty string for automatic.
    """
    try:
        from taskcoachlib.config import settings
        return settings.Settings().get("view", "dateformat")
    except Exception:
        return ""


def getEffectiveDateFormat():
    """Get the effective date format, respecting user settings.

    Returns a tuple: (field_order, separator) based on settings or locale detection.
    """
    override = getDateFormatFromSettings()
    return getLocaleDateFormat(override=override if override else None)


def getDateFormatFunctionForOldControl():
    """Get a format function suitable for the old smartdatetimectrl DateEntry.

    Returns a function that takes a date and returns a formatted string,
    which DateEntry parses to understand field order.

    If no override is set, returns None (use default locale detection).
    """
    override = getDateFormatFromSettings()
    if not override or len(override) < 4:
        return None  # Use default

    # Build format string from override (e.g., "YMD-" -> "%Y-%m-%d")
    order_str = override[:3].upper()
    separator = override[3]

    format_map = {'Y': '%Y', 'M': '%m', 'D': '%d'}
    format_parts = [format_map.get(c, '%Y') for c in order_str]
    strftime_format = separator.join(format_parts)

    def format_func(d):
        return d.strftime(strftime_format)

    return format_func


def getDetectedLocaleTimeFormat():
    """Detect locale time format (12-hour vs 24-hour).

    Returns "12" if locale uses 12-hour format with AM/PM, "24" otherwise.
    """
    # Test with a time that would show AM/PM indicator
    test_time = datetime.time(hour=14, minute=30)
    formatted = test_time.strftime("%X")  # Locale's time format

    # Check for AM/PM indicators
    am_indicator = datetime.time(hour=1).strftime("%p")
    pm_indicator = datetime.time(hour=13).strftime("%p")

    if am_indicator or pm_indicator:
        # Locale has AM/PM, check if it's used in the format
        if "PM" in formatted.upper() or "AM" in formatted.upper():
            return "12"
        # Check for localized AM/PM
        if pm_indicator and pm_indicator in formatted:
            return "12"

    return "24"


def getTimeFormatFromSettings():
    """Get the time format override from user settings.

    Returns "24", "12", or "" for automatic.
    """
    try:
        from taskcoachlib.config import settings
        return settings.Settings().get("view", "timeformat")
    except Exception:
        return ""


def getEffectiveTimeFormat():
    """Get the effective time format, respecting user settings.

    Returns "24" or "12".

    When set to automatic (empty string), detects from system locale.
    Default setting is "24" to match original design.
    """
    override = getTimeFormatFromSettings()
    if override in ("24", "12"):
        return override
    # Automatic: detect from system locale
    return getDetectedLocaleTimeFormat()


def getHourRangeForTimeFormat(timeFormat=None):
    """Get the appropriate hour range for dropdown choices based on time format.

    Args:
        timeFormat: "24", "12", or None to use effective format from settings

    Returns:
        list: [0, 1, ..., 23] for 24-hour mode, [1, 2, ..., 12] for 12-hour mode
    """
    if timeFormat is None:
        timeFormat = getEffectiveTimeFormat()
    if timeFormat == "12":
        return list(range(1, 13))
    return list(range(24))


def getDefaultHourChoices(timeFormat=None):
    """Get default hour choices for TimeCtrl dropdowns.

    In 24-hour mode: returns working hours from settings (efforthourstart to efforthourend)
    In 12-hour mode: returns 1-12

    Args:
        timeFormat: "24", "12", or None to use effective format from settings

    Returns:
        list of hour values for dropdown
    """
    if timeFormat is None:
        timeFormat = getEffectiveTimeFormat()
    if timeFormat == "12":
        return list(range(1, 13))
    # 24-hour mode: use working hours from settings
    try:
        from taskcoachlib.config import settings
        start = settings.Settings().getint("view", "efforthourstart")
        end = settings.Settings().getint("view", "efforthourend")
        # Cap at 23 to handle legacy settings that may have sentinel value 24
        return list(range(start, min(end + 1, 24)))
    except Exception:
        return list(range(8, 18))  # Fallback: 8 AM to 5 PM


def getDefaultMinuteChoices():
    """Get default minute choices for TimeCtrl dropdowns from settings.

    Returns minutes based on effortminuteinterval setting.

    Returns:
        list of minute values for dropdown
    """
    try:
        from taskcoachlib.config import settings
        interval = settings.Settings().getint("view", "effortminuteinterval")
        return list(range(0, 60, interval))
    except Exception:
        return [0, 15, 30, 45]  # Fallback: 15-minute intervals


def getDefaultSecondChoices():
    """Get default second choices for TimeCtrl dropdowns from settings.

    Returns seconds based on effortsecondinterval setting.

    Returns:
        list of second values for dropdown
    """
    try:
        from taskcoachlib.config import settings
        interval = settings.Settings().getint("view", "effortsecondinterval")
        return list(range(0, 60, interval))
    except Exception:
        return [0, 15, 30, 45]  # Fallback: 15-second intervals


def getDefaultDayChoices():
    """Get default day choices for DurationCtrl dropdowns.

    Returns:
        list of day values for dropdown
    """
    return [0, 1, 2, 3, 5, 7, 14, 21, 28, 30, 60, 90]


def getDefaultDurationHourChoices():
    """Get default hour choices for DurationCtrl dropdowns.

    Returns a pattern suitable for duration entry (not time-of-day).

    Returns:
        list of hour values for dropdown
    """
    return [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20]


def getCalendarColours():
    """Get the active calendar colour set based on current theme mode.

    Returns a dict with keys: 'weekday_header_bg', 'weekday_header_fg',
    'weekend_day_fg', 'today_border', 'other_month_bg'.
    Each value is a wx.Colour, except 'other_month_bg' which is
    wx.Colour or None (None means use system default).
    """
    try:
        import ast
        app = wx.GetApp()
        s = getattr(app, 'settings', None)
        if s is None:
            from taskcoachlib.config import settings as settings_mod
            s = settings_mod.Settings()
        theme = s.get("window", "theme")

        if theme == "automatic":
            from taskcoachlib.application.application import detect_dark_theme
            is_dark = detect_dark_theme()
        else:
            is_dark = (theme == "dark")

        section = "calendar_dark" if is_dark else "calendar_light"

        use_system = s.get(section, "other_month_bg_system") == "True"
        if use_system:
            other_month_bg = None
        else:
            other_month_bg = wx.Colour(*ast.literal_eval(s.get(section, "other_month_bg")))

        return {
            'weekday_header_bg': wx.Colour(*ast.literal_eval(s.get(section, "weekday_header_bg"))),
            'weekday_header_fg': wx.Colour(*ast.literal_eval(s.get(section, "weekday_header_fg"))),
            'weekend_day_fg': wx.Colour(*ast.literal_eval(s.get(section, "weekend_day_fg"))),
            'today_border': wx.Colour(*ast.literal_eval(s.get(section, "today_border"))),
            'other_month_bg': other_month_bg,
        }
    except Exception:
        return {
            'weekday_header_bg': wx.LIGHT_GREY,
            'weekday_header_fg': wx.BLUE,
            'weekend_day_fg': wx.RED,
            'today_border': wx.RED,
            'other_month_bg': None,
        }


def monthcalendarex(year, month, weeks=0):
    """Return a matrix of (year, month, day) tuples for a calendar month display.

    Includes days from previous/next months to fill complete weeks.
    The weeks parameter adds extra weeks before and after the month.
    """
    weekDay, monthLength = calendar.monthrange(year, month)
    startDate = datetime.date(year, month, 1)
    endDate = datetime.date(year, month, monthLength)
    # To start of week
    startDate -= datetime.timedelta(
        days=(startDate.weekday() - calendar.firstweekday()) % 7
    )
    endDate += datetime.timedelta(
        days=(7 + calendar.firstweekday() - endDate.weekday()) % 7
    )
    startDate -= datetime.timedelta(weeks=weeks)
    endDate += datetime.timedelta(weeks=weeks)
    monthCal = list()
    while startDate < endDate:
        week = list()
        for dayNumber in range(7):
            theDate = startDate + datetime.timedelta(days=dayNumber)
            week.append((theDate.year, theDate.month, theDate.day))
        monthCal.append(week)
        startDate += datetime.timedelta(weeks=1)
    return monthCal


# Field type definitions: (width, min, max, pad_zeros)
# The control knows these field types internally
# pad_zeros: True = pad with zeros (hours, minutes), False = no padding (days)
# Dropdown choices must be provided by caller - no defaults
FIELD_TYPES = {
    # Duration/time fields
    "day": (3, 0, 999, False),
    "hour": (2, 0, 23, True),
    "hour12": (2, 1, 12, False),  # 12-hour format: 1-12, no leading zero
    "minute": (2, 0, 59, True),
    "second": (2, 0, 59, True),
    "period": (2, 0, 1, False),  # AM=0, PM=1 (special display handling)
    # Date fields - calendar popup instead of dropdowns
    "year": (4, 1, 9999, True),
    "month": (2, 1, 12, True),
    "date_day": (2, 1, 31, True),
}


# =============================================================================
# Event Types
# =============================================================================

wxEVT_POPUP_DISMISS = wx.NewEventType()
EVT_POPUP_DISMISS = wx.PyEventBinder(wxEVT_POPUP_DISMISS)

wxEVT_CHOICE_SELECTED = wx.NewEventType()
EVT_CHOICE_SELECTED = wx.PyEventBinder(wxEVT_CHOICE_SELECTED)

wxEVT_CHOICE_PREVIEW = wx.NewEventType()
EVT_CHOICE_PREVIEW = wx.PyEventBinder(wxEVT_CHOICE_PREVIEW)

wxEVT_VALUE_CHANGED = wx.NewEventType()
EVT_VALUE_CHANGED = wx.PyEventBinder(wxEVT_VALUE_CHANGED, 1)


class ValueChangedEvent(wx.PyCommandEvent):
    """Event fired when a control's value changes (live, before focus loss)."""

    def __init__(self, owner):
        super().__init__(wxEVT_VALUE_CHANGED, owner.GetId())
        self.SetEventObject(owner)


class PopupDismissEvent(wx.PyCommandEvent):
    """Event fired when popup is dismissed."""

    def __init__(self, owner):
        super().__init__(wxEVT_POPUP_DISMISS)
        self.SetEventObject(owner)


class ChoiceSelectedEvent(wx.PyCommandEvent):
    """Event fired when a choice is selected in popup."""

    def __init__(self, owner, value):
        super().__init__(wxEVT_CHOICE_SELECTED)
        self.__value = value
        self.SetEventObject(owner)

    def GetValue(self):
        return self.__value


class ChoicePreviewEvent(wx.PyCommandEvent):
    """Event fired when navigating choices in popup (live preview)."""

    def __init__(self, owner, value):
        super().__init__(wxEVT_CHOICE_PREVIEW)
        self.__value = value
        self.SetEventObject(owner)

    def GetValue(self):
        return self.__value


# =============================================================================
# Popup Window Classes
# =============================================================================

class _PopupWindow(wx.Dialog):
    """Popup window base class. wx.PopupWindow doesn't work well cross-platform."""

    def __init__(self, *args, **kwargs):
        kwargs["style"] = (
            wx.FRAME_NO_TASKBAR | wx.NO_BORDER | wx.FRAME_FLOAT_ON_PARENT
        )
        if "__WXMSW__" in wx.PlatformInfo:
            kwargs["style"] |= wx.WANTS_CHARS
        super().__init__(*args, **kwargs)

        # No border on panel - DrawTextCtrl handles border and focus styling
        style = wx.BORDER_NONE
        if "__WXMSW__" in wx.PlatformInfo:
            style |= wx.WANTS_CHARS
        self.__interior = wx.Panel(self, style=style)
        self._dismissed = False

        self.Bind(wx.EVT_ACTIVATE, self._onActivate)
        if "__WXMAC__" in wx.PlatformInfo:
            self.Bind(wx.EVT_CHAR, self._onChar)
        else:
            self.__interior.Bind(wx.EVT_CHAR, self._onChar)

        self.Fill(self.__interior)

        sizer = wx.BoxSizer()
        sizer.Add(self.__interior, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def interior(self):
        return self.__interior

    def Fill(self, interior):
        """Override to populate the popup interior."""
        pass

    def Popup(self, position):
        self.Move(position)
        self.Show()
        if "__WXGTK__" in wx.PlatformInfo:
            self.SetFocus()

    def Dismiss(self):
        if self._dismissed:
            return
        self._dismissed = True
        self.Hide()
        self.Unbind(wx.EVT_ACTIVATE)
        self.Unbind(wx.EVT_CHAR)
        try:
            interior = self.interior()
            if interior:
                interior.Unbind(wx.EVT_CHAR)
                interior.Unbind(wx.EVT_PAINT)
                interior.Unbind(wx.EVT_LEFT_UP)
        except RuntimeError:
            pass
        self.ProcessEvent(PopupDismissEvent(self))
        wx.CallLater(100, self._safeDestroy)

    def _safeDestroy(self):
        try:
            if self:
                self.Destroy()
        except RuntimeError:
            pass

    def _onChar(self, event):
        if not self.HandleKey(event):
            self.GetParent().OnChar(event)

    def HandleKey(self, event):
        return False

    def _onActivate(self, event):
        if event.GetActive():
            event.Skip()
        else:
            self.Dismiss()


class _ChoicesPopup(_PopupWindow):
    """Dropdown popup for field choices. Width matches target field."""

    def __init__(self, choices, value, minWidth, font, *args, **kwargs):
        self.__choices = choices
        self.__originalValue = value  # Value when popup opened
        self.__highlightedValue = value  # Currently highlighted (mouse or keys)
        self.__minWidth = minWidth  # Minimum width to match field
        self.__font = font  # Font from parent control
        super().__init__(*args, **kwargs)

    def Fill(self, interior):
        interior.Bind(wx.EVT_PAINT, self._onPaint)
        interior.Bind(wx.EVT_LEFT_UP, self._onLeftUp)
        interior.Bind(wx.EVT_MOTION, self._onMotion)
        interior.Bind(wx.EVT_LEAVE_WINDOW, self._onLeaveWindow)
        self.SetClientSize(self._getExtent(wx.ClientDC(interior)))

    def _getExtent(self, dc):
        dc.SetFont(self.__font)
        maxW = self.__minWidth  # Start with minimum width from field
        # Standard item padding: 2px vertical, 4px horizontal
        vPad = 2
        hPad = 4
        contentOffsetX, contentOffsetY = getTextCtrlContentOffset()
        totH = 0
        for label, value in self.__choices:
            tw, th = dc.GetTextExtent(str(label))
            maxW = max(tw, maxW)
            totH += th + vPad * 2  # Add vertical padding per item
        self.__itemHeight = None  # Will be set during paint
        return wx.Size(maxW + hPad * 2 + contentOffsetX * 2, totH + contentOffsetY * 2)

    def _onPaint(self, event):
        dc = wx.PaintDC(event.GetEventObject())
        win = event.GetEventObject()
        w, h = self.GetClientSize()
        renderer = wx.RendererNative.Get()

        # Draw text control frame with editing focus highlight (blue ring)
        renderer.DrawTextCtrl(win, dc, wx.Rect(0, 0, w, h), wx.CONTROL_FOCUSED)

        dc.SetFont(self.__font)

        # Standard item padding
        vPad = 2
        hPad = 4
        contentOffsetX, contentOffsetY = getTextCtrlContentOffset()
        y = contentOffsetY

        for label, value in self.__choices:
            tw, th = dc.GetTextExtent(label)
            itemH = th + vPad * 2
            itemRect = wx.Rect(contentOffsetX, y, w - contentOffsetX * 2, itemH)

            isHighlighted = (value == self.__highlightedValue)

            if isHighlighted:
                # Use native selection rectangle rendering (fully highlighted)
                renderer.DrawItemSelectionRect(
                    win, dc, itemRect,
                    wx.CONTROL_SELECTED | wx.CONTROL_FOCUSED
                )

            # Draw text right-aligned with padding, vertically centered
            textY = y + vPad
            textX = w - contentOffsetX - hPad - tw
            if isHighlighted:
                dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
            else:
                dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOXTEXT))
            dc.DrawText(label, textX, textY)

            y += itemH

        self.__itemHeight = itemH if self.__choices else 0

    def __highlightedIndex(self):
        for idx, (label, value) in enumerate(self.__choices):
            if value == self.__highlightedValue:
                return idx
        return 0

    def HandleKey(self, event):
        keyCode = event.GetKeyCode()
        if keyCode == wx.WXK_UP:
            self.__highlightedValue = self.__choices[
                (self.__highlightedIndex() + len(self.__choices) - 1) % len(self.__choices)
            ][1]
            self.Refresh()
            return True

        if keyCode == wx.WXK_DOWN:
            self.__highlightedValue = self.__choices[
                (self.__highlightedIndex() + 1) % len(self.__choices)
            ][1]
            self.Refresh()
            return True

        if keyCode == wx.WXK_RETURN:
            self.ProcessEvent(ChoiceSelectedEvent(self, self.__highlightedValue))
            return True

        if keyCode == wx.WXK_ESCAPE:
            self.Dismiss()
            return True

        return False

    def _onLeftUp(self, event):
        vPad = 2
        _, contentOffsetY = getTextCtrlContentOffset()
        y = contentOffsetY
        dc = wx.ClientDC(event.GetEventObject())
        dc.SetFont(self.__font)
        for label, value in self.__choices:
            tw, th = dc.GetTextExtent(label)
            itemH = th + vPad * 2
            if event.GetY() >= y and event.GetY() < y + itemH:
                self.ProcessEvent(ChoiceSelectedEvent(self, value))
                break
            y += itemH

    def _onMotion(self, event):
        """Track mouse movement to highlight item under cursor."""
        vPad = 2
        _, contentOffsetY = getTextCtrlContentOffset()
        y = contentOffsetY
        dc = wx.ClientDC(event.GetEventObject())
        dc.SetFont(self.__font)
        newHighlight = None
        for label, value in self.__choices:
            tw, th = dc.GetTextExtent(label)
            itemH = th + vPad * 2
            if event.GetY() >= y and event.GetY() < y + itemH:
                newHighlight = value
                break
            y += itemH
        if newHighlight is not None and newHighlight != self.__highlightedValue:
            self.__highlightedValue = newHighlight
            self.Refresh()

    def _onLeaveWindow(self, event):
        """Mouse left popup - keep current highlight (don't clear it)."""
        # Don't clear highlight when mouse leaves - standard dropdown behavior




# =============================================================================
# Drawing Helpers
# =============================================================================

def drawFocusRect(win, dc, x, y, w, h):
    """Draw focus highlight rectangle using native rendering."""
    rect = wx.Rect(int(x), int(y), int(w), int(h))
    wx.RendererNative.Get().DrawItemSelectionRect(
        win, dc, rect, wx.CONTROL_SELECTED | wx.CONTROL_FOCUSED
    )


class NumericField:
    """A numeric subfield within a MaskedFieldsCtrl."""

    def __init__(self, name, width, minVal, maxVal, value, choices, observer, padZeros=True):
        self.__name = name
        self.__width = width
        self.__minVal = minVal
        self.__maxVal = maxVal
        self.__value = max(minVal, min(maxVal, value))
        self.__choices = None  # Will be set by SetChoices
        self.__observer = observer
        self.__padZeros = padZeros
        self.__digitCount = 0  # Number of digits typed in current entry
        self.__lastKeyTime = 0  # Timestamp of last digit keystroke
        self._negativePrefix = False  # If True, paint "-" before value
        self.SetChoices(choices)  # Use SetChoices for proper handling

    @property
    def name(self):
        return self.__name

    def GetValue(self):
        return self.__value

    def SetValue(self, value):
        oldValue = self.__value
        value = max(self.__minVal, min(self.__maxVal, int(value)))
        self.__value = value
        # Always validate (e.g., DateComboCustomCtrl adjusts day when month changes)
        result = self.__observer.ValidateChange(self, value)
        if result is None:
            # Validation rejected - restore old value
            self.__value = oldValue
            return
        if result != value:
            # Validation modified the value
            self.__value = result
        self.__observer.Refresh()
        self.__observer.Update()  # Force immediate repaint

    def SetRawValue(self, value):
        """Store value without clamping - used during typing."""
        self.__value = int(value)
        self.__observer.Refresh()
        self.__observer.Update()

    def GetChoices(self):
        """Get choices for dropdown. If choices is callable, call it to get fresh values.

        Choices are returned in tuple format: [(label, value), ...]
        If the source provides simple values [1, 2, 3], they are converted automatically.
        """
        choices = self.__choices() if callable(self.__choices) else self.__choices
        if not choices:
            return choices
        # Convert simple list [1, 2, 3] to tuple format [("1", 1), ...]
        if choices and not isinstance(choices[0], tuple):
            return [(str(v), v) for v in choices]
        return choices

    def SetChoices(self, choices):
        """Set choices. Can be a list or a callable that returns a list.

        Static choices are converted to tuple format immediately.
        Callable choices are converted each time GetChoices() is called.
        """
        if callable(choices):
            self.__choices = choices
        elif choices:
            # Convert simple list to tuple format for static choices
            if not isinstance(choices[0], tuple):
                self.__choices = [(str(v), v) for v in choices]
            else:
                self.__choices = choices
        else:
            self.__choices = []

    def GetExtent(self, dc):
        """Get the pixel size needed for this field."""
        # Use observer's font if available, otherwise system default
        font = self.__observer.GetFont() if self.__observer else wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        dc.SetFont(font)
        # Special handling for AM/PM period field
        if self.__name == "period":
            # Use the wider of AM/PM for consistent sizing
            amW, amH = dc.GetTextExtent("AM")
            pmW, pmH = dc.GetTextExtent("PM")
            return (max(amW, pmW), max(amH, pmH))
        w = max(self.__width, 1)
        if self._negativePrefix:
            w += 1  # Extra char for "-" prefix
        return dc.GetTextExtent("0" * w)

    def PaintValue(self, dc, x, y, w, h):
        """Paint the field value in its area.

        Zero-padded fields (hours, minutes): centered
        Space-padded fields (days): right-aligned so digit touches following literal
        Period field (AM/PM): displays text instead of number
        """
        # Use observer's font if available, otherwise system default
        font = self.__observer.GetFont() if self.__observer else wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        dc.SetFont(font)
        # Special handling for AM/PM period field
        if self.__name == "period":
            txt = "PM" if self.__value else "AM"
            tw, th = dc.GetTextExtent(txt)
            dc.DrawText(txt, int(x + (w - tw) / 2), int(y + (h - th) / 2))
            return
        if self.__padZeros:
            txt = ("%%0%dd" % max(self.__width, 1)) % self.__value
            tw, th = dc.GetTextExtent(txt)
            # Center zero-padded values
            dc.DrawText(txt, int(x + (w - tw) / 2), int(y + (h - th) / 2))
        else:
            # Right-align space-padded values so rightmost digit touches next element
            txt = str(self.__value)
            if self._negativePrefix:
                txt = "-" + txt
            tw, th = dc.GetTextExtent(txt)
            dc.DrawText(txt, int(x + w - tw), int(y + (h - th) / 2))

    def ResetState(self):
        """Reset digit entry state."""
        self.__digitCount = 0
        self.__lastKeyTime = 0

    def HandleKey(self, event):
        """Handle keyboard input. Returns True if handled."""
        keyCode = event.GetKeyCode()

        if keyCode == wx.WXK_UP:
            newVal = self.__value + 1
            if newVal > self.__maxVal:
                newVal = self.__minVal
            self.SetValue(newVal)
            return True

        if keyCode == wx.WXK_DOWN:
            newVal = self.__value - 1
            if newVal < self.__minVal:
                newVal = self.__maxVal
            self.SetValue(newVal)
            return True

        # Special handling for AM/PM period field
        if self.__name == "period":
            if keyCode in (ord('A'), ord('a')):
                self.SetValue(0)  # AM
                return True
            if keyCode in (ord('P'), ord('p')):
                self.SetValue(1)  # PM
                return True
            # Space bar toggles AM/PM
            if keyCode == wx.WXK_SPACE:
                self.SetValue(1 - self.__value)
                return True
            return False  # Don't allow numeric input for period field

        # Handle numeric input
        if wx.WXK_NUMPAD0 <= keyCode <= wx.WXK_NUMPAD9:
            number = keyCode - wx.WXK_NUMPAD0
        elif ord('0') <= keyCode <= ord('9'):
            number = keyCode - ord('0')
        else:
            number = -1

        if 0 <= number <= 9:
            now = time.time()
            # Reset if timeout elapsed since last keystroke (750ms)
            if now - self.__lastKeyTime > 0.75:
                self.__digitCount = 0
            self.__lastKeyTime = now

            if self.__digitCount == 0:
                # First digit: replace value entirely (no clamp during typing)
                self.SetRawValue(number)
            else:
                newVal = (self.__value * 10 + number) % int(math.pow(10, self.__width))
                self.SetRawValue(newVal)
            self.__digitCount += 1
            self.__observer.DismissPopup()
            # Auto-advance to next field after all digits typed
            if self.__digitCount >= self.__width:
                self.SetValue(self.__value)  # Clamp + validate before advancing
                self.__digitCount = 0
                self.__lastKeyTime = 0
                # Advance unless this is the last field
                fieldList = self.__observer._fieldList
                if fieldList and fieldList.index(self) < len(fieldList) - 1:
                    self.__observer._focusNextField()
            return True

        if keyCode in (wx.WXK_BACK, wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self.SetValue(int(self.__value / 10))
            return True

        return False


class MaskedFieldsCtrl(wx.Panel):
    """
    Base control with explicit subfields and labels.
    Visually identical to smartdatetimectrl Entry - single painted field.

    Elements list - each element is a tuple:
    - ("day", value) - day field with initial value, default choices
    - ("day", value, choices) - day field with custom choices list
    - ("hour", value) - hour field (0-23)
    - ("minute", value) - minute field (0-59)
    - ("second", value) - second field (0-59)
    - ("literal", "text") - literal text label (use _() for translation)

    Choices can be a simple list [1, 2, 3] or tuples [("label", value), ...]

    Example:
        elements = [
            ("day", 1),
            ("literal", _("d") + " "),
            ("hour", 2, [8, 9, 10, 17, 18]),  # custom hour choices
            ("literal", ":"),
            ("minute", 30),
        ]
    """

    def __init__(self, parent, elements):
        super().__init__(parent, style=wx.WANTS_CHARS)

        # Get margin from system metrics for native look
        self.MARGIN, _ = getTextCtrlContentOffset()

        self._drawFrame = True  # Draw own frame; False when inside ComboCtrl
        self._fields = {}  # name -> NumericField
        self._fieldList = []  # All NumericField objects in order
        self._widgets = []  # (item, x, y, w, h) - item is Field or string
        self._focus = None  # Currently focused field
        self._hasFocus = False
        self._popup = None
        self._focusStamp = 0  # Time when focus was gained
        self._returningFromPopup = False  # Flag to preserve focus after popup
        self._popupDismissedWidget = None  # Widget whose popup was just dismissed
        self._popupDismissedTime = 0  # When popup was dismissed
        self._readOnly = False  # Read-only mode: show values greyed, not editable

        # Build widgets from elements
        curX = self.MARGIN
        minW = 0
        minH = 0

        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())

        for i, elem in enumerate(elements):
            fieldType = elem[0]

            if fieldType == "literal":
                # Literal text label
                label = str(elem[1])
                tw, th = dc.GetTextExtent(label)
                self._widgets.append((label, curX, self.MARGIN, tw, th))
                minW += tw
                minH = max(minH, th)
                curX += tw
            elif fieldType in FIELD_TYPES:
                # Known field type
                # Element format: (fieldType, value) or (fieldType, value, choices)
                # choices can be a list of values [1, 2, 3] or list of tuples [("label", value), ...]
                # If no choices provided, there is no dropdown
                value = elem[1] if len(elem) > 1 else 0
                customChoices = elem[2] if len(elem) > 2 else None

                width, minVal, maxVal, padZeros = FIELD_TYPES[fieldType]

                # Pass choices to NumericField - it handles conversion and callables
                # Choices can be: None, list of values, list of tuples, or callable
                choices = customChoices

                field = NumericField(
                    fieldType, width, minVal, maxVal,
                    value, choices, self, padZeros
                )
                self._fields[fieldType] = field
                self._fieldList.append(field)

                w, h = field.GetExtent(dc)
                self._widgets.append((field, curX, self.MARGIN, w, h))
                minW += w
                minH = max(minH, h)
                curX += w

        # Set minimum size and remember the natural content size for centering
        self._naturalSize = wx.Size(curX + self.MARGIN, minH + 2 * self.MARGIN)
        self.SetMinSize(self._naturalSize)

        # Focus first field
        if self._fieldList:
            self._focus = self._fieldList[0]

        # Bind events
        self.Bind(wx.EVT_PAINT, self._onPaint)
        self.Bind(wx.EVT_CHAR, self._onChar)
        self.Bind(wx.EVT_LEFT_UP, self._onLeftUp)
        self.Bind(wx.EVT_SET_FOCUS, self._onSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self._onKillFocus)

    def _onPaint(self, event):
        dc = wx.PaintDC(self)
        w, h = self.GetClientSize()
        hasFocus = self._hasFocus

        # Draw native text control border using system theme
        # (skip when embedded inside ComboCtrl which provides its own frame)
        if self._drawFrame:
            flags = 0
            if hasFocus and not self._readOnly:
                flags |= wx.CONTROL_FOCUSED
            if not self.IsEnabled() or self._readOnly:
                flags |= wx.CONTROL_DISABLED
            wx.RendererNative.Get().DrawTextCtrl(self, dc, wx.Rect(0, 0, w, h), flags)

        dc.SetFont(self.GetFont())

        # Offset to center content when control is larger than minimum
        xOff, yOff = self._getContentOffset()

        if self.IsEnabled() and not self._readOnly:
            # Normal editable mode - show values
            textColour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
            for widget, x, y, ww, hh in self._widgets:
                if isinstance(widget, str):
                    dc.SetTextForeground(textColour)
                    dc.DrawText(widget, int(x + xOff), int(y + yOff))
                else:
                    # NumericField - draw focus highlight only if focused
                    if widget == self._focus and hasFocus:
                        drawFocusRect(self, dc, x + xOff, y + yOff, ww, hh)
                        dc.SetTextForeground(
                            wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
                        )
                    else:
                        dc.SetTextForeground(textColour)
                    widget.PaintValue(dc, x + xOff, y + yOff, ww, hh)
        elif not self.IsEnabled():
            # Disabled mode (unchecked checkbox) - show "N/A" centered
            # Values are preserved internally but hidden behind "N/A"
            # Matches old SmartDateTimeCtrl behavior (smartdatetimectrl.py:667-671)
            text = "N/A"
            tw, th = dc.GetTextExtent(text)
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
            dc.DrawText(text, (w - tw) // 2, (h - th) // 2)
        else:
            # Read-only mode (inactive) - show values greyed but visible
            # This is for SetEditable(False) state where values should be visible
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
            for widget, x, y, ww, hh in self._widgets:
                if isinstance(widget, str):
                    dc.DrawText(widget, int(x + xOff), int(y + yOff))
                else:
                    widget.PaintValue(dc, x + xOff, y + yOff, ww, hh)

    def _onChar(self, event):
        keyCode = event.GetKeyCode()

        if not self._focus:
            event.Skip()
            return

        # Block all input except Tab in read-only mode
        if self._readOnly:
            if keyCode == wx.WXK_TAB:
                self.Navigate(not event.ShiftDown())
            return

        # Tab exits control (matches Entry behavior)
        if keyCode == wx.WXK_TAB:
            self.DismissPopup()
            self.Navigate(not event.ShiftDown())
            return

        # Escape dismisses popup
        if keyCode == wx.WXK_ESCAPE:
            if self._popup:
                self.DismissPopup()
                return
            event.Skip()
            return

        # Enter or F4 toggles popup for current field
        if keyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_F4):
            if self._popup:
                self.DismissPopup()
            else:
                self._openPopupForFocusedField()
            return

        # Left/Right arrows wrap within subfields (matches Entry behavior)
        if keyCode == wx.WXK_LEFT:
            self._focusPrevField()
            return
        if keyCode == wx.WXK_RIGHT:
            self._focusNextField()
            return

        # Let the focused field handle the key
        if self._focus.HandleKey(event):
            return

        event.Skip()

    def _focusNextField(self):
        """Move to next field, wrapping from last to first."""
        if not self._fieldList:
            return
        try:
            idx = self._fieldList.index(self._focus)
            # Clamp + validate old field before leaving
            self._focus.SetValue(self._focus.GetValue())
            # Wrap: last -> first
            nextIdx = (idx + 1) % len(self._fieldList)
            self._focus = self._fieldList[nextIdx]
            self._focus.ResetState()
            self.DismissPopup()
            self.Refresh()
        except ValueError:
            pass

    def _focusPrevField(self):
        """Move to previous field, wrapping from first to last."""
        if not self._fieldList:
            return
        try:
            idx = self._fieldList.index(self._focus)
            # Clamp + validate old field before leaving
            self._focus.SetValue(self._focus.GetValue())
            # Wrap: first -> last
            prevIdx = (idx - 1) % len(self._fieldList)
            self._focus = self._fieldList[prevIdx]
            self._focus.ResetState()
            self.DismissPopup()
            self.Refresh()
        except ValueError:
            pass

    def _openPopupForFocusedField(self):
        """Open dropdown popup for currently focused field."""
        if not self._focus:
            return
        xOff, yOff = self._getContentOffset()
        # Find the widget entry for the focused field
        for widget, x, y, w, h in self._widgets:
            if widget == self._focus:
                choices = self._focus.GetChoices()
                if choices:
                    self._showPopup(self._focus, choices, x + xOff, y + yOff, w, h)
                break

    # Time thresholds for focus and popup behavior (in seconds)
    FOCUS_DELAY = 0.05  # Minimum time before showing popup after focus
    POPUP_TOGGLE_DELAY = 0.2  # Time window to detect click-to-close toggle

    def _getContentOffset(self):
        """Offset to center content when control is larger than natural size."""
        cw, ch = self.GetClientSize()
        mw, mh = self._naturalSize
        xOff = max(0, (cw - mw) // 2) if cw > mw else 0
        yOff = max(0, (ch - mh) // 2) if ch > mh else 0
        return xOff, yOff

    def _onLeftUp(self, event):
        pt = event.GetPosition()

        # No interaction in read-only mode
        if self._readOnly:
            event.Skip()
            return

        xOff, yOff = self._getContentOffset()
        # Find which widget was clicked
        for widget, x, y, w, h in self._widgets:
            if isinstance(widget, NumericField):
                if (x + xOff) <= pt.x <= (x + xOff) + w and (y + yOff) <= pt.y <= (y + yOff) + h:
                    # Clamp + validate old field before leaving
                    if self._focus and self._focus != widget:
                        self._focus.SetValue(self._focus.GetValue())
                    # Set focus to this field
                    self._focus = widget
                    self._focus.ResetState()
                    self.SetFocus()

                    # Check if clicking on same field with open popup - toggle close
                    if self._popup is not None and self._popup[1] == widget:
                        self.DismissPopup()
                    # Check if popup was just dismissed for this widget (toggle case)
                    elif (
                        self._popupDismissedWidget == widget
                        and time.time() - self._popupDismissedTime < self.POPUP_TOGGLE_DELAY
                    ):
                        # Popup was just closed by click, don't reopen (toggle off)
                        self._popupDismissedWidget = None
                    else:
                        # Dismiss any existing popup, then open new one
                        self.DismissPopup()
                        # Delay popup to avoid showing on initial focus
                        if time.time() - self._focusStamp >= self.FOCUS_DELAY:
                            choices = widget.GetChoices()
                            if choices:
                                self._showPopup(widget, choices, x + xOff, y + yOff, w, h)

                    self.Refresh()
                    return

        event.Skip()

    def _showPopup(self, field, choices, fieldX, fieldY, fieldW, fieldH):
        """Show dropdown popup for field. Width matches the field width, centered."""
        if self._popup:
            return

        # Get current value for highlighting
        currentValue = field.GetValue()

        # Create popup with field width as minimum width and same font
        popup = _ChoicesPopup(choices, currentValue, fieldW, self.GetFont(), self)
        self._popup = (popup, field)

        # Center popup horizontally on the field
        popupW = popup.GetSize().GetWidth()
        centerX = fieldX + (fieldW - popupW) // 2

        pos = self.ClientToScreen(wx.Point(int(centerX), int(fieldY + fieldH)))
        popup.Popup(pos)
        popup.Bind(EVT_POPUP_DISMISS, self._onPopupDismiss)
        popup.Bind(EVT_CHOICE_SELECTED, self._onChoiceSelected)
        popup.Bind(EVT_CHOICE_PREVIEW, self._onChoicePreview)

    def _onPopupDismiss(self, event):
        """Handle popup dismissal - track for toggle behavior and preserve focus."""
        if self._popup is not None:
            self._popupDismissedWidget = self._popup[1]
            self._popupDismissedTime = time.time()
        self._popup = None
        self._returningFromPopup = True
        self.SetFocus()  # Return focus to control
        event.Skip()

    def _onChoicePreview(self, event):
        """Handle preview of choice (arrow key navigation in popup)."""
        if self._popup:
            popup, field = self._popup
            field.SetValue(event.GetValue())
            self.Refresh()

    def _onChoiceSelected(self, event):
        """Handle choice selection from popup."""
        if self._popup:
            popup, field = self._popup
            field.SetValue(event.GetValue())
            popup.Dismiss()

    def DismissPopup(self):
        """Dismiss any open popup."""
        if self._popup:
            self._popup[0].Dismiss()
        self._popup = None

    def OnChar(self, event):
        """Handle char events from popup - delegate to internal handler."""
        self._onChar(event)

    def _onSetFocus(self, event):
        """Handle focus gain with proper subfield preservation.

        When returning from popup, preserve current subfield focus.
        When tabbing into control, focus first or last subfield based on direction.
        """
        self._hasFocus = True
        self._focusStamp = time.time()
        # Don't reset subfield focus when returning from popup
        if self._returningFromPopup:
            self._returningFromPopup = False
        else:
            # Set focus to first or last subfield based on Tab direction
            if self._fieldList:
                if wx.GetKeyState(wx.WXK_SHIFT):
                    self._focus = self._fieldList[-1]
                else:
                    self._focus = self._fieldList[0]
                self._focus.ResetState()
        self.Refresh()
        event.Skip()

    def _onKillFocus(self, event):
        """Handle focus loss - clear visual focus state.

        Note: Don't dismiss popup here - popup handles its own dismissal via
        EVT_ACTIVATE. Calling DismissPopup() here would break dropdowns.
        """
        self._hasFocus = False
        if self._focus:
            # Clamp + validate before losing focus
            self._focus.SetValue(self._focus.GetValue())
            self._focus.ResetState()  # Clear any partial digit entry
        self.Refresh()
        self.NotifyValueChanged()
        event.Skip()

    def ValidateChange(self, field, value):
        """Override in subclasses to validate field changes (e.g., clamp day for month)."""
        return value

    def GetField(self, name):
        return self._fields.get(name)

    def GetFieldValue(self, name):
        field = self._fields.get(name)
        return field.GetValue() if field else 0

    def SetFieldValue(self, name, value):
        field = self._fields.get(name)
        if field:
            field.SetValue(value)

    def SetFocus(self):
        super().SetFocus()

    def SetReadOnly(self, readOnly=True):
        """Set read-only mode. Shows values greyed out but visible, not editable."""
        self._readOnly = readOnly
        # Update window's focusability to match read-only state
        self.SetCanFocus(not readOnly)
        self.Refresh()

    def IsReadOnly(self):
        """Return whether control is in read-only mode."""
        return self._readOnly

    def AcceptsFocusFromKeyboard(self):
        """Skip this control when tabbing if it's read-only or disabled."""
        if self._readOnly or not self.IsEnabled():
            return False
        return super().AcceptsFocusFromKeyboard()

    def NotifyValueChanged(self):
        """Fire EVT_VALUE_CHANGED event to notify listeners of value change."""
        event = ValueChangedEvent(self)
        wx.PostEvent(self, event)


class DurationCtrl(MaskedFieldsCtrl):
    """Duration control: DDDd HH:MM[:SS] with translatable 'd' suffix.

    Args:
        parent: Parent window
        days, hours, minutes, seconds: Initial values
        dayChoices: Dropdown choices for days:
            - None (default): Use defaults [0, 1, 2, 3, 5, 7, 14, 21, 28, 30, 60, 90]
            - list: Use that specific list
            - False: No dropdown
        hourChoices: Dropdown choices for hours:
            - None (default): Use defaults [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20]
            - list: Use that specific list
            - False: No dropdown
        minuteChoices: Dropdown choices for minutes:
            - None (default): Use defaults from settings (based on effortminuteinterval)
            - list: Use that specific list
            - False: No dropdown
        showSeconds: If True, include seconds field (default False)
        secondChoices: Dropdown choices for seconds:
            - None (default): Use defaults from settings (based on effortsecondinterval)
            - list: Use that specific list
            - False: No dropdown
    """

    def __init__(self, parent, days=0, hours=0, minutes=0, seconds=0,
                 dayChoices=None, hourChoices=None, minuteChoices=None,
                 showSeconds=False, secondChoices=None):
        self._showSeconds = showSeconds

        # Resolve day choices: None=defaults, False=no dropdown, list=use as-is
        if dayChoices is None:
            dayChoices = getDefaultDayChoices()
        elif dayChoices is False:
            dayChoices = None

        # Resolve hour choices: None=defaults, False=no dropdown, list=use as-is
        if hourChoices is None:
            hourChoices = getDefaultDurationHourChoices()
        elif hourChoices is False:
            hourChoices = None

        # Resolve minute choices: None=defaults, False=no dropdown, list=use as-is
        if minuteChoices is None:
            minuteChoices = getDefaultMinuteChoices()
        elif minuteChoices is False:
            minuteChoices = None

        # Resolve second choices: None=defaults, False=no dropdown, list=use as-is
        if secondChoices is None:
            secondChoices = getDefaultSecondChoices()
        elif secondChoices is False:
            secondChoices = None

        elements = [
            ("day", days, dayChoices),
            ("literal", _("d") + " "),
            ("hour", hours, hourChoices),
            ("literal", ":"),
            ("minute", minutes, minuteChoices),
        ]

        if showSeconds:
            elements.append(("literal", ":"))
            elements.append(("second", seconds, secondChoices))

        self._negative = False
        super().__init__(parent, elements)

    def GetDuration(self):
        result = date.TimeDelta(
            days=self.GetFieldValue('day'),
            hours=self.GetFieldValue('hour'),
            minutes=self.GetFieldValue('minute')
        )
        if self._showSeconds:
            result += date.TimeDelta(seconds=self.GetFieldValue('second'))
        if self._negative:
            result = -result
        return result

    def GetTimeDelta(self):
        """Alias for GetDuration for consistency with other controls."""
        return self.GetDuration()

    def SetDuration(self, duration):
        """Set the duration value.

        Args:
            duration: timedelta or None (defaults to zero)
        """
        if duration is None:
            duration = date.TimeDelta()
        total = int(duration.total_seconds())
        negative = total < 0
        total = abs(total)
        days, remainder = divmod(total, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        self._negative = negative
        dayField = self._fields.get('day')
        if dayField:
            dayField._negativePrefix = negative
        self.SetFieldValue('day', days)
        self.SetFieldValue('hour', hours)
        self.SetFieldValue('minute', minutes)
        if self._showSeconds:
            self.SetFieldValue('second', seconds)
        self.NotifyValueChanged()

    def SetTimeDelta(self, duration):
        """Alias for SetDuration for consistency with other controls."""
        self.SetDuration(duration)

    def GetValue(self):
        """Alias for GetDuration for AttributeSync compatibility."""
        return self.GetDuration()

    def SetValue(self, duration):
        """Alias for SetDuration for AttributeSync compatibility."""
        self.SetDuration(duration)


class DurationCtrlVerbose(MaskedFieldsCtrl):
    """Duration control with full word suffixes: 000 days 00 hours 00 mins [00 secs].

    Args:
        parent: Parent window
        days, hours, minutes, seconds: Initial values
        dayChoices: Dropdown choices for days:
            - None (default): Use defaults [0, 1, 2, 3, 5, 7, 14, 21, 28, 30, 60, 90]
            - list: Use that specific list
            - False: No dropdown
        hourChoices: Dropdown choices for hours:
            - None (default): Use defaults [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20]
            - list: Use that specific list
            - False: No dropdown
        minuteChoices: Dropdown choices for minutes:
            - None (default): Use defaults from settings (based on effortminuteinterval)
            - list: Use that specific list
            - False: No dropdown
        showSeconds: If True, include seconds field (default False)
        secondChoices: Dropdown choices for seconds:
            - None (default): Use defaults from settings (based on effortsecondinterval)
            - list: Use that specific list
            - False: No dropdown
    """

    def __init__(self, parent, days=0, hours=0, minutes=0, seconds=0,
                 dayChoices=None, hourChoices=None, minuteChoices=None,
                 showSeconds=False, secondChoices=None):
        self._showSeconds = showSeconds

        # Resolve day choices: None=defaults, False=no dropdown, list=use as-is
        if dayChoices is None:
            dayChoices = getDefaultDayChoices()
        elif dayChoices is False:
            dayChoices = None

        # Resolve hour choices: None=defaults, False=no dropdown, list=use as-is
        if hourChoices is None:
            hourChoices = getDefaultDurationHourChoices()
        elif hourChoices is False:
            hourChoices = None

        # Resolve minute choices: None=defaults, False=no dropdown, list=use as-is
        if minuteChoices is None:
            minuteChoices = getDefaultMinuteChoices()
        elif minuteChoices is False:
            minuteChoices = None

        # Resolve second choices: None=defaults, False=no dropdown, list=use as-is
        if secondChoices is None:
            secondChoices = getDefaultSecondChoices()
        elif secondChoices is False:
            secondChoices = None

        elements = [
            ("day", days, dayChoices),
            ("literal", " " + _("days") + " "),
            ("hour", hours, hourChoices),
            ("literal", " " + _("hours") + " "),
            ("minute", minutes, minuteChoices),
            ("literal", " " + _("mins")),
        ]

        if showSeconds:
            elements.append(("literal", " "))
            elements.append(("second", seconds, secondChoices))
            elements.append(("literal", " " + _("secs")))

        self._negative = False
        super().__init__(parent, elements)

    def GetDuration(self):
        result = date.TimeDelta(
            days=self.GetFieldValue('day'),
            hours=self.GetFieldValue('hour'),
            minutes=self.GetFieldValue('minute')
        )
        if self._showSeconds:
            result += date.TimeDelta(seconds=self.GetFieldValue('second'))
        if self._negative:
            result = -result
        return result

    def GetTimeDelta(self):
        """Alias for GetDuration for consistency with other controls."""
        return self.GetDuration()

    def SetDuration(self, duration):
        """Set the duration value.

        Args:
            duration: timedelta or None (defaults to zero)
        """
        if duration is None:
            duration = date.TimeDelta()
        total = int(duration.total_seconds())
        negative = total < 0
        total = abs(total)
        days, remainder = divmod(total, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        self._negative = negative
        dayField = self._fields.get('day')
        if dayField:
            dayField._negativePrefix = negative
        self.SetFieldValue('day', days)
        self.SetFieldValue('hour', hours)
        self.SetFieldValue('minute', minutes)
        if self._showSeconds:
            self.SetFieldValue('second', seconds)
        self.NotifyValueChanged()

    def SetTimeDelta(self, duration):
        """Alias for SetDuration for consistency with other controls."""
        self.SetDuration(duration)

    def GetValue(self):
        """Alias for GetDuration for AttributeSync compatibility."""
        return self.GetDuration()

    def SetValue(self, duration):
        """Alias for SetDuration for AttributeSync compatibility."""
        self.SetDuration(duration)


class TimeCtrl(MaskedFieldsCtrl):
    """Simple time control: HH:MM (24-hour) or HH:MM AM/PM (12-hour).

    Supports both 24-hour and 12-hour time formats. The format can be
    specified explicitly or determined from settings.

    Args:
        parent: Parent window
        hours, minutes: Initial values (always in 24-hour format internally)
        hourChoices: Dropdown choices for hours:
            - None (default): Use defaults from settings (working hours for 24h, 1-12 for 12h)
            - list: Use that specific list
            - False: No dropdown
        minuteChoices: Dropdown choices for minutes:
            - None (default): Use defaults from settings (based on effortminuteinterval)
            - list: Use that specific list
            - False: No dropdown
        timeFormat: "24" for 24-hour, "12" for 12-hour with AM/PM, None to use settings
    """

    def __init__(self, parent, hours=0, minutes=0,
                 hourChoices=None, minuteChoices=None, timeFormat=None):
        # Determine time format from parameter or settings
        if timeFormat is not None:
            self._timeFormat = timeFormat if timeFormat in ("24", "12") else "24"
        else:
            self._timeFormat = getEffectiveTimeFormat()

        # Resolve hour choices: None=defaults, False=no dropdown, list=use as-is
        if hourChoices is None:
            hourChoices = getDefaultHourChoices(self._timeFormat)
        elif hourChoices is False:
            hourChoices = None

        # Resolve minute choices: None=defaults, False=no dropdown, list=use as-is
        if minuteChoices is None:
            minuteChoices = getDefaultMinuteChoices()
        elif minuteChoices is False:
            minuteChoices = None

        if self._timeFormat == "12":
            # 12-hour format: convert 24h to 12h display
            hour12, period = self._to12Hour(hours)
            elements = [
                ("hour12", hour12, hourChoices),
                ("literal", ":"),
                ("minute", minutes, minuteChoices),
                ("literal", " "),
                ("period", period, [("AM", 0), ("PM", 1)]),
            ]
        else:
            # 24-hour format (default)
            elements = [
                ("hour", hours, hourChoices),
                ("literal", ":"),
                ("minute", minutes, minuteChoices),
            ]

        super().__init__(parent, elements)

    def _to12Hour(self, hour24):
        """Convert 24-hour to 12-hour format. Returns (hour12, period)."""
        if hour24 == 0:
            return (12, 0)  # 12 AM
        elif hour24 < 12:
            return (hour24, 0)  # AM
        elif hour24 == 12:
            return (12, 1)  # 12 PM
        else:
            return (hour24 - 12, 1)  # PM

    def _to24Hour(self, hour12, period):
        """Convert 12-hour to 24-hour format."""
        if hour12 == 12:
            return 0 if period == 0 else 12  # 12 AM = 0, 12 PM = 12
        else:
            return hour12 if period == 0 else hour12 + 12

    def GetTime(self):
        if self._timeFormat == "12":
            hour12 = self.GetFieldValue('hour12')
            period = self.GetFieldValue('period')
            hour24 = self._to24Hour(hour12, period)
            return datetime.time(hour=hour24, minute=self.GetFieldValue('minute'))
        else:
            return datetime.time(
                hour=self.GetFieldValue('hour'),
                minute=self.GetFieldValue('minute')
            )

    def SetTime(self, t):
        """Set the time value.

        Args:
            t: datetime.time or None (defaults to 00:00)
        """
        if t is None:
            t = datetime.time()
        if self._timeFormat == "12":
            hour12, period = self._to12Hour(t.hour)
            self.SetFieldValue('hour12', hour12)
            self.SetFieldValue('period', period)
        else:
            self.SetFieldValue('hour', t.hour)
        self.SetFieldValue('minute', t.minute)


class TimeWithSecondsCtrl(MaskedFieldsCtrl):
    """Time control with seconds: HH:MM:SS (24-hour) or HH:MM:SS AM/PM (12-hour).

    Supports both 24-hour and 12-hour time formats. The format can be
    specified explicitly or determined from settings.

    Args:
        parent: Parent window
        hours, minutes, seconds: Initial values (always in 24-hour format internally)
        hourChoices: Dropdown choices for hours:
            - None (default): Use defaults from settings (working hours for 24h, 1-12 for 12h)
            - list: Use that specific list
            - False: No dropdown
        minuteChoices: Dropdown choices for minutes:
            - None (default): Use defaults from settings (based on effortminuteinterval)
            - list: Use that specific list
            - False: No dropdown
        secondChoices: Dropdown choices for seconds:
            - None (default): Use defaults from settings (based on effortsecondinterval)
            - list: Use that specific list
            - False: No dropdown
        timeFormat: "24" for 24-hour, "12" for 12-hour with AM/PM, None to use settings
    """

    def __init__(self, parent, hours=0, minutes=0, seconds=0,
                 hourChoices=None, minuteChoices=None, secondChoices=None,
                 timeFormat=None):
        # Determine time format from parameter or settings
        if timeFormat is not None:
            self._timeFormat = timeFormat if timeFormat in ("24", "12") else "24"
        else:
            self._timeFormat = getEffectiveTimeFormat()

        # Resolve hour choices: None=defaults, False=no dropdown, list=use as-is
        if hourChoices is None:
            hourChoices = getDefaultHourChoices(self._timeFormat)
        elif hourChoices is False:
            hourChoices = None

        # Resolve minute choices: None=defaults, False=no dropdown, list=use as-is
        if minuteChoices is None:
            minuteChoices = getDefaultMinuteChoices()
        elif minuteChoices is False:
            minuteChoices = None

        # Resolve second choices: None=defaults, False=no dropdown, list=use as-is
        if secondChoices is None:
            secondChoices = getDefaultSecondChoices()
        elif secondChoices is False:
            secondChoices = None

        if self._timeFormat == "12":
            # 12-hour format: convert 24h to 12h display
            hour12, period = self._to12Hour(hours)
            elements = [
                ("hour12", hour12, hourChoices),
                ("literal", ":"),
                ("minute", minutes, minuteChoices),
                ("literal", ":"),
                ("second", seconds, secondChoices),
                ("literal", " "),
                ("period", period, [("AM", 0), ("PM", 1)]),
            ]
        else:
            # 24-hour format (default)
            elements = [
                ("hour", hours, hourChoices),
                ("literal", ":"),
                ("minute", minutes, minuteChoices),
                ("literal", ":"),
                ("second", seconds, secondChoices),
            ]

        super().__init__(parent, elements)

    def _to12Hour(self, hour24):
        """Convert 24-hour to 12-hour format. Returns (hour12, period)."""
        if hour24 == 0:
            return (12, 0)  # 12 AM
        elif hour24 < 12:
            return (hour24, 0)  # AM
        elif hour24 == 12:
            return (12, 1)  # 12 PM
        else:
            return (hour24 - 12, 1)  # PM

    def _to24Hour(self, hour12, period):
        """Convert 12-hour to 24-hour format."""
        if hour12 == 12:
            return 0 if period == 0 else 12  # 12 AM = 0, 12 PM = 12
        else:
            return hour12 if period == 0 else hour12 + 12

    def GetTime(self):
        if self._timeFormat == "12":
            hour12 = self.GetFieldValue('hour12')
            period = self.GetFieldValue('period')
            hour24 = self._to24Hour(hour12, period)
            return datetime.time(
                hour=hour24,
                minute=self.GetFieldValue('minute'),
                second=self.GetFieldValue('second')
            )
        else:
            return datetime.time(
                hour=self.GetFieldValue('hour'),
                minute=self.GetFieldValue('minute'),
                second=self.GetFieldValue('second')
            )

    def SetTime(self, t):
        """Set the time value.

        Args:
            t: datetime.time or None (defaults to 00:00:00)
        """
        if t is None:
            t = datetime.time()
        if self._timeFormat == "12":
            hour12, period = self._to12Hour(t.hour)
            self.SetFieldValue('hour12', hour12)
            self.SetFieldValue('period', period)
        else:
            self.SetFieldValue('hour', t.hour)
        self.SetFieldValue('minute', t.minute)
        self.SetFieldValue('second', t.second)




class _CalendarComboPopup(wx.ComboPopup):
    """ComboPopup adapter for the custom-painted calendar.

    Wraps the calendar painting/interaction logic into the wx.ComboPopup
    interface, so it can be used with wx.ComboCtrl.
    The ComboCtrl provides the native dropdown button and manages the popup
    window (including Wayland-safe positioning).
    """

    def __init__(self, minDate=None, maxDate=None):
        super().__init__()
        self._minDate = minDate
        self._maxDate = maxDate
        self._panel = None
        self._selection = datetime.date.today()
        self._highlightedDate = self._selection
        self._originalDate = self._selection
        self._year = self._selection.year
        self._month = self._selection.month
        self._maxDim = None
        self._font = None
        self._days = []
        self._win = None
        self._contentOffsetX = 0
        self._contentOffsetY = 0

    def Create(self, parent):
        self._panel = wx.Panel(parent, style=wx.BORDER_NONE)
        self._panel.Bind(wx.EVT_PAINT, self._onPaint)
        self._panel.Bind(wx.EVT_LEFT_UP, self._onLeftUp)
        self._panel.Bind(wx.EVT_MOTION, self._onMotion)
        self._panel.Bind(wx.EVT_LEAVE_WINDOW, self._onLeaveWindow)
        self._panel.Bind(wx.EVT_CHAR, self._onChar)
        pub.subscribe(self._onColoursChanged, 'calendar.colours.changed')
        return True

    def GetControl(self):
        return self._panel

    def SetStringValue(self, val):
        """Parse date string from ComboCtrl text field."""
        pass  # We don't use the text field for date parsing

    def GetStringValue(self):
        """Return selected date as string."""
        return str(self._highlightedDate) if self._highlightedDate else ''

    def GetAdjustedSize(self, minWidth, prefHeight, maxHeight):
        if self._panel is None:
            return wx.Size(minWidth, prefHeight)
        dc = wx.ClientDC(self._panel)
        size = self._getExtent(dc)
        return size

    def _getDateComboCustomCtrl(self):
        """Get the DateComboCustomCtrl (ComboCtrl) that owns this popup."""
        combo = self.GetComboCtrl()
        if combo:
            if hasattr(combo, '_dateCtrl') and hasattr(combo, '_setDateFromCalendar'):
                return combo
        return None

    def OnPopup(self):
        """Called when popup is shown — sync selection from parent or text."""
        dc2 = self._getDateComboCustomCtrl()
        if dc2:
            self._selection = dc2._dateCtrl.GetDate()
            self._font = dc2._dateCtrl.GetFont()
        else:
            # Standalone ComboCtrl — try to parse date from text field
            combo = self.GetComboCtrl()
            if combo:
                self._font = combo.GetFont()
                text = combo.GetValue().strip()
                if text:
                    try:
                        self._selection = datetime.date.fromisoformat(text)
                    except (ValueError, AttributeError):
                        pass
        self._originalDate = self._selection
        self._highlightedDate = self._selection
        self._year = self._selection.year
        self._month = self._selection.month
        if self._panel:
            dc = wx.ClientDC(self._panel)
            self._panel.SetMinSize(self._getExtent(dc))

    def OnDismiss(self):
        """Called when popup is hidden."""
        pass

    def DestroyPopup(self):
        pub.unsubscribe(self._onColoursChanged, 'calendar.colours.changed')

    def _onColoursChanged(self):
        if self._panel:
            self._panel.Refresh()

    def _onChar(self, event):
        keyCode = event.GetKeyCode()
        if keyCode in (wx.WXK_ESCAPE, wx.WXK_F4):
            self.Dismiss()
        elif keyCode == wx.WXK_RETURN:
            dc2 = self._getDateComboCustomCtrl()
            if dc2:
                dc2._setDateFromCalendar(self._highlightedDate)
            self.Dismiss()
        elif keyCode == wx.WXK_LEFT:
            self._moveHighlight(datetime.timedelta(days=-1))
        elif keyCode == wx.WXK_RIGHT:
            self._moveHighlight(datetime.timedelta(days=1))
        elif keyCode == wx.WXK_UP:
            self._moveHighlight(datetime.timedelta(days=-7))
        elif keyCode == wx.WXK_DOWN:
            self._moveHighlight(datetime.timedelta(days=7))
        else:
            event.Skip()

    def _moveHighlight(self, delta):
        newDate = self._highlightedDate + delta
        if self._minDate is not None and newDate < self._minDate:
            wx.Bell()
            return
        if self._maxDate is not None and newDate > self._maxDate:
            wx.Bell()
            return
        if newDate.year < 1 or newDate.year > 9999:
            wx.Bell()
            return
        self._highlightedDate = newDate
        if self._highlightedDate.year != self._year or self._highlightedDate.month != self._month:
            self._year = self._highlightedDate.year
            self._month = self._highlightedDate.month
            dc = wx.ClientDC(self._panel)
            self._panel.SetMinSize(self._getExtent(dc))
            self._panel.GetParent().Layout()
        self._panel.Refresh()

    # --- Calendar painting and interaction ---

    def _getExtent(self, dc):
        if self._font:
            dc.SetFont(self._font)
        W, H = 0, 0
        for month in range(1, 13):
            header = datetime.date(year=self._year, month=month, day=11).strftime("%B %Y")
            tw, th = dc.GetTextExtent(header)
            W = max(W, tw)
            H = max(H, th)

        lines = monthcalendarex(self._year, self._month, weeks=1)
        self._maxDim = 0
        for line in lines:
            for year, month, day in line:
                tw, th = dc.GetTextExtent("%d" % day)
                self._maxDim = max(self._maxDim, tw, th)

        for hdr in calendar.weekheader(2).split():
            tw, th = dc.GetTextExtent(hdr)
            self._maxDim = max(self._maxDim, tw, th)

        self._maxDim += 4
        contentOffsetX, contentOffsetY = getTextCtrlContentOffset()
        return wx.Size(
            max(W + 48 + 4, self._maxDim * len(lines[0])) + contentOffsetX * 2,
            H + 2 + self._maxDim * (len(lines) + 1) + contentOffsetY * 2,
        )

    def _onPaint(self, event):
        win = event.GetEventObject()
        dc = wx.PaintDC(win)
        w, h = win.GetClientSize()
        renderer = wx.RendererNative.Get()

        renderer.DrawTextCtrl(win, dc, wx.Rect(0, 0, w, h), wx.CONTROL_FOCUSED)

        contentOffsetX, contentOffsetY = getTextCtrlContentOffset()
        contentW = w - contentOffsetX * 2

        if self._font:
            dc.SetFont(self._font)
        self._win = win
        self._contentOffsetX = contentOffsetX
        self._contentOffsetY = contentOffsetY

        colours = getCalendarColours()

        textColour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
        dc.SetPen(wx.Pen(textColour))
        dc.SetBrush(wx.Brush(textColour))
        dc.SetTextForeground(textColour)

        header = datetime.date(year=self._year, month=self._month, day=1).strftime("%B %Y")
        tw, th = dc.GetTextExtent(header)
        dc.DrawText(header, contentOffsetX + (contentW - 48 - tw) // 2, contentOffsetY)

        buttonDim = min(th, 10)

        cx = w - contentOffsetX - 24
        cy = contentOffsetY + th // 2 + 1

        gc = wx.GraphicsContext.Create(dc)
        gc.SetPen(gc.CreatePen(wx.Pen(textColour)))
        gc.SetBrush(gc.CreateBrush(wx.Brush(textColour)))

        # Prev month button (left arrow)
        if self._month != 1 or self._year != 1:
            gp = gc.CreatePath()
            xinf = w - contentOffsetX - 48 + 16 - buttonDim
            xsup = w - contentOffsetX - 48 + 16
            yinf = contentOffsetY + th / 2 + 1 - buttonDim / 2
            ysup = contentOffsetY + th / 2 + 1 + buttonDim / 2

            gp.MoveToPoint(xinf, contentOffsetY + th // 2 + 1)
            gp.AddArc(
                cx, cy,
                math.sqrt((xsup - cx) * (xsup - cx) + (yinf - cy) * (yinf - cy)),
                math.pi * 3 / 4, math.pi * 5 / 4, True,
            )
            gc.DrawPath(gp)

        # Next month button (right arrow)
        if self._month != 12 or self._year != 9999:
            gp = gc.CreatePath()
            xinf = w - contentOffsetX - 16
            xsup = w - contentOffsetX - 16 + buttonDim
            yinf = contentOffsetY + th / 2 + 1 - buttonDim / 2

            gp.MoveToPoint(xsup, contentOffsetY + th // 2 + 1)
            gp.AddArc(
                cx, cy,
                math.sqrt((xinf - cx) * (xinf - cx) + (yinf - cy) * (yinf - cy)),
                math.pi / 4, -math.pi / 4, False,
            )
            gc.DrawPath(gp)

        # Today button (circle)
        gp = gc.CreatePath()
        gp.AddArc(cx, cy, buttonDim * 3 / 4, 0, math.pi * 2, True)
        gc.DrawPath(gp)

        y = contentOffsetY + th + 2

        # Weekday headers
        hdrBg = colours['weekday_header_bg']
        dc.SetPen(wx.Pen(hdrBg))
        dc.SetBrush(wx.Brush(hdrBg))
        dc.DrawRectangle(contentOffsetX, y, self._maxDim * 7, self._maxDim)
        dc.SetTextForeground(colours['weekday_header_fg'])
        for idx, hdr in enumerate(calendar.weekheader(2).split()):
            tw, th_hdr = dc.GetTextExtent(hdr)
            dc.DrawText(
                hdr,
                contentOffsetX + self._maxDim * idx + int((self._maxDim - tw) // 2),
                y + int((self._maxDim - th_hdr) // 2),
            )

        y += self._maxDim

        # Days
        self._days = []
        for line in monthcalendarex(self._year, self._month, weeks=1):
            x = contentOffsetX
            for dayIndex, (year, month, day) in enumerate(line):
                dt = datetime.date(year=year, month=month, day=day)
                active = (self._minDate is None or dt >= self._minDate) and (
                    self._maxDate is None or dt <= self._maxDate
                )
                thisMonth = year == self._year and month == self._month

                dc.SetPen(wx.Pen(textColour))
                dc.SetTextForeground(
                    colours['weekend_day_fg'] if (dayIndex + calendar.firstweekday()) % 7 in [5, 6] else textColour
                )

                if not active:
                    inactiveBg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
                    dc.SetPen(wx.Pen(inactiveBg))
                    dc.SetBrush(wx.Brush(inactiveBg))
                    dc.DrawRectangle(x, y, self._maxDim, self._maxDim)
                elif not thisMonth:
                    otherMonthBg = colours['other_month_bg'] if colours['other_month_bg'] is not None else wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
                    dc.SetPen(wx.Pen(otherMonthBg))
                    dc.SetBrush(wx.Brush(otherMonthBg))
                    dc.DrawRectangle(x, y, self._maxDim, self._maxDim)

                isHighlighted = (dt == self._highlightedDate and active)

                if isHighlighted:
                    drawFocusRect(self._win, dc, x, y, self._maxDim, self._maxDim)
                    dc.SetTextForeground(
                        wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
                    )

                now = datetime.datetime.now()
                if (dt.year, dt.month, dt.day) == (now.year, now.month, now.day):
                    dc.SetPen(wx.Pen(colours['today_border']))
                    dc.SetBrush(wx.TRANSPARENT_BRUSH)
                    dc.DrawRectangle(x, y, self._maxDim, self._maxDim)

                label = "%d" % day
                tw, th_day = dc.GetTextExtent(label)
                dc.DrawText(
                    label,
                    x + (self._maxDim - tw) // 2,
                    y + (self._maxDim - th_day) // 2,
                )

                if active:
                    self._days.append((x, y, (year, month, day)))
                x += self._maxDim
            y += self._maxDim

    def _onLeftUp(self, event):
        w, h = self._panel.GetClientSize()
        contentOffsetX, contentOffsetY = getTextCtrlContentOffset()

        dc = wx.ClientDC(self._panel)
        if self._font:
            dc.SetFont(self._font)
        header = datetime.date(year=self._year, month=self._month, day=1).strftime("%B %Y")
        tw, th = dc.GetTextExtent(header)

        # Buttons area (top right)
        if event.GetY() < contentOffsetY + th + 2 and event.GetX() > w - contentOffsetX - 48:
            if event.GetX() < w - contentOffsetX - 48 + 16 and (self._month != 1 or self._year != 1):
                if self._month == 1:
                    self._year -= 1
                    self._month = 12
                else:
                    self._month -= 1
            elif event.GetX() < w - contentOffsetX - 48 + 32:
                today = datetime.datetime.now()
                self._year = today.year
                self._month = today.month
            elif self._month != 12 or self._year != 9999:
                if self._month == 12:
                    self._year += 1
                    self._month = 1
                else:
                    self._month += 1
            dc2 = wx.ClientDC(self._panel)
            self._panel.SetMinSize(self._getExtent(dc2))
            self._panel.GetParent().Layout()
            self._panel.Refresh()
            return

        # Day selection
        for x, y, (year, month, day) in self._days:
            if (
                event.GetX() >= x
                and event.GetX() < x + self._maxDim
                and event.GetY() >= y
                and event.GetY() < y + self._maxDim
            ):
                dc2 = self._getDateComboCustomCtrl()
                if dc2:
                    dc2._setDateFromCalendar(
                        datetime.date(year=year, month=month, day=day)
                    )
                self.Dismiss()
                break

    def _onMotion(self, event):
        newHighlight = None
        for x, y, (year, month, day) in self._days:
            if (
                event.GetX() >= x
                and event.GetX() < x + self._maxDim
                and event.GetY() >= y
                and event.GetY() < y + self._maxDim
            ):
                newHighlight = datetime.date(year=year, month=month, day=day)
                break
        if newHighlight is not None and newHighlight != self._highlightedDate:
            self._highlightedDate = newHighlight
            self._panel.Refresh()

    def _onLeaveWindow(self, event):
        pass


class DateCtrl(MaskedFieldsCtrl):
    """Date control designed for embedding inside a ComboCtrl.

    Raw masked date fields with all popup/frame/calendar logic removed.
    The parent ComboCtrl owns the dropdown — this control only handles
    subfield editing, keyboard navigation, and date validation.

    - No calendar popup (_showCalendarPopup, _onCalendarDismiss removed)
    - No frame drawing (_drawFrame = False)
    - No field dropdown popups (_openPopupForFocusedField = no-op)
    - F4/Enter delegates to parent ComboCtrl.Popup()
    - Click only changes subfield focus (no popup toggle)
    """

    def __init__(self, parent, comboCtrl, year=None, month=None, day=None,
                 minDate=None, maxDate=None, dateFormat=None):
        # Default to today's date
        today = datetime.date.today()
        if year is None:
            year = today.year
        if month is None:
            month = today.month
        if day is None:
            day = today.day

        self._minDate = minDate
        self._maxDate = maxDate
        self._comboCtrl = comboCtrl

        # Get date format: use explicit override, or read from settings, or detect from locale
        if dateFormat is not None:
            field_order, separator = getLocaleDateFormat(override=dateFormat if dateFormat else None)
        else:
            field_order, separator = getEffectiveDateFormat()

        # Map field names to their values
        field_values = {
            'year': year,
            'month': month,
            'date_day': day,
        }

        # Build elements list based on locale order
        elements = []
        for i, field_name in enumerate(field_order):
            if i > 0:
                elements.append(("literal", separator))
            elements.append((field_name, field_values[field_name]))

        super().__init__(parent, elements)
        self._drawFrame = False

    def _onPaint(self, event):
        """Paint override for embedded context.

        Uses IsThisEnabled() (own state) instead of IsEnabled() (parent chain)
        so that disabling the parent ComboCtrl for read-only visuals doesn't
        trigger the "N/A" branch. Only a direct Enable(False) on DateComboCustomCtrl
        (which propagates to this control's own state) shows "N/A".

        No frame drawing — the parent ComboCtrl provides the frame.
        """
        dc = wx.PaintDC(self)
        w, h = self.GetClientSize()
        dc.SetFont(self.GetFont())
        xOff, yOff = self._getContentOffset()

        if self._readOnly:
            # Read-only: greyed values (standalone or inside disabled ComboCtrl)
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
            for widget, x, y, ww, hh in self._widgets:
                if isinstance(widget, str):
                    dc.DrawText(widget, int(x + xOff), int(y + yOff))
                else:
                    widget.PaintValue(dc, x + xOff, y + yOff, ww, hh)
        elif not self.IsThisEnabled():
            # Disabled (checkbox unchecked): show "N/A" centered
            text = "N/A"
            tw, th = dc.GetTextExtent(text)
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
            dc.DrawText(text, (w - tw) // 2, (h - th) // 2)
        else:
            # Normal editable
            hasFocus = self._hasFocus
            textColour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
            for widget, x, y, ww, hh in self._widgets:
                if isinstance(widget, str):
                    dc.SetTextForeground(textColour)
                    dc.DrawText(widget, int(x + xOff), int(y + yOff))
                else:
                    if widget == self._focus and hasFocus:
                        drawFocusRect(self, dc, x + xOff, y + yOff, ww, hh)
                        dc.SetTextForeground(
                            wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
                        )
                    else:
                        dc.SetTextForeground(textColour)
                    widget.PaintValue(dc, x + xOff, y + yOff, ww, hh)

    def _onChar(self, event):
        """Handle keyboard input — F4/Enter open parent ComboCtrl popup."""
        if not self._focus:
            event.Skip()
            return

        keyCode = event.GetKeyCode()

        # Tab exits control (always allowed, even in read-only mode)
        if keyCode == wx.WXK_TAB:
            self.Navigate(not event.ShiftDown())
            return

        # Block all other input in read-only mode
        if self._readOnly:
            return

        # Escape — nothing to dismiss, let parent handle it
        if keyCode == wx.WXK_ESCAPE:
            event.Skip()
            return

        # F4/Enter open the parent ComboCtrl popup
        if keyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_F4):
            if self._comboCtrl:
                self._comboCtrl.Popup()
            return

        # Left/Right arrows navigate between subfields
        if keyCode == wx.WXK_LEFT:
            self._focusPrevField()
            return
        if keyCode == wx.WXK_RIGHT:
            self._focusNextField()
            return

        # Let the focused field handle the key (Up/Down for increment/decrement)
        if self._focus.HandleKey(event):
            return

        event.Skip()

    def _onLeftUp(self, event):
        """Click changes subfield focus only — no popup."""
        if self._readOnly:
            event.Skip()
            return

        pt = event.GetPosition()
        xOff, yOff = self._getContentOffset()

        for widget, x, y, w, h in self._widgets:
            if isinstance(widget, NumericField):
                if (x + xOff) <= pt.x <= (x + xOff) + w and (y + yOff) <= pt.y <= (y + yOff) + h:
                    # Clamp + validate old field before leaving
                    if self._focus and self._focus != widget:
                        self._focus.SetValue(self._focus.GetValue())
                    self._focus = widget
                    self._focus.ResetState()
                    self.SetFocus()
                    self.Refresh()
                    return

        event.Skip()

    def _openPopupForFocusedField(self):
        """No-op — embedded control has no field dropdown popups."""
        pass

    def DismissPopup(self):
        """No-op — embedded control owns no popups."""
        pass

    def ValidateChange(self, field, value):
        """Validate date changes, adjusting day if needed for month/year changes."""
        year = self.GetFieldValue('year')
        month = self.GetFieldValue('month')
        day = self.GetFieldValue('date_day')

        max_day = calendar.monthrange(year, month)[1]
        if day > max_day:
            day = max_day
            self.SetFieldValue('date_day', day)

        return value

    def GetDate(self):
        """Get the current date value."""
        return datetime.date(
            year=self.GetFieldValue('year'),
            month=self.GetFieldValue('month'),
            day=self.GetFieldValue('date_day')
        )

    def SetDate(self, d):
        """Set the date value.

        Args:
            d: datetime.date or None (defaults to today)
        """
        if d is None:
            d = datetime.date.today()
        self.SetFieldValue('year', d.year)
        self.SetFieldValue('month', d.month)
        self.SetFieldValue('date_day', d.day)


class DateComboCustomCtrl(wx.ComboCtrl):
    """Date control: DateCtrl inside a ComboCtrl.

    Uses DateCtrl which has all popup/frame logic removed at the
    class level. The ComboCtrl provides the native dropdown button and
    manages popup positioning.
    """

    def __init__(self, parent, year=None, month=None, day=None,
                 minDate=None, maxDate=None, dateFormat=None):
        super().__init__(parent)

        # Calendar popup via ComboPopup interface
        self._calendarPopup = _CalendarComboPopup(
            minDate=minDate, maxDate=maxDate
        )
        self.SetPopupControl(self._calendarPopup)

        # Clean embedded DateCtrl — no monkey-patches needed
        self._dateCtrl = DateCtrl(
            self, comboCtrl=self, year=year, month=month, day=day,
            minDate=minDate, maxDate=maxDate, dateFormat=dateFormat
        )

        # Derive horizontal padding from the vertical padding the ComboCtrl
        # naturally adds around the text area (theme-dependent).
        dateW, dateH = self._dateCtrl._naturalSize
        stdH = self.GetBestSize().height
        self._padding = max(0, (stdH - dateH) // 2)
        comboW = dateW + 2 * self._padding + self.GetButtonSize().width
        self.SetMinSize(wx.Size(comboW, stdH))

        # Redirect focus from ComboCtrl's text control to inner DateCtrl
        # so the caret never appears in the hidden text field.
        self._redirectingFocus = False
        self._tabbingOut = False
        self._popupWasShown = False
        textCtrl = self.GetTextCtrl()
        if textCtrl:
            textCtrl.Bind(wx.EVT_SET_FOCUS, self._onTextCtrlFocus)

        # Intercept Shift+Tab from inner DateCtrl: set _tabbingOut flag
        # so _onTextCtrlFocus knows to pass focus through instead of
        # redirecting back to DateCtrl.
        origNavigate = self._dateCtrl.Navigate
        def _navigateWithFlag(forward=True):
            if not forward:
                self._tabbingOut = True
            return origNavigate(forward)
        self._dateCtrl.Navigate = _navigateWithFlag

        # Intercept any text the ComboCtrl auto-inserts (e.g. on popup dismiss)
        self.Bind(wx.EVT_TEXT, self._onComboText)

        # Track when popup opens (covers both F4/Enter and button click)
        self.Bind(wx.EVT_COMBOBOX_DROPDOWN, self._onPopupOpen)

        # Position the DateCtrl on resize
        self.Bind(wx.EVT_SIZE, self._onSize)
        # Also do initial positioning after layout settles
        wx.CallAfter(self._positionDateCtrl)

    def _onTextCtrlFocus(self, event):
        """Redirect focus from ComboCtrl's text control to inner DateCtrl."""
        if self._redirectingFocus:
            return
        if self._tabbingOut:
            self._tabbingOut = False
            wx.CallAfter(self.GetTextCtrl().Navigate, False)
            return
        if self._popupWasShown:
            self._dateCtrl._returningFromPopup = True
            self._popupWasShown = False
        self._redirectingFocus = True
        self._dateCtrl.SetFocus()
        self._redirectingFocus = False

    def _onComboText(self, event):
        """Clear any text the ComboCtrl auto-inserts on popup dismiss."""
        if self.GetValue():
            self.ChangeValue('')

    def _positionDateCtrl(self):
        """Center the DateCtrl over the ComboCtrl's text area."""
        if not self:
            return
        comboW, comboH = self.GetClientSize()
        btnW = self.GetButtonSize().width
        textAreaW = comboW - btnW
        dateW, dateH = self._dateCtrl._naturalSize
        x = (textAreaW - dateW) // 2
        y = (comboH - dateH) // 2
        self._dateCtrl.SetPosition(wx.Point(max(0, x), max(0, y)))
        self._dateCtrl.SetSize(wx.Size(dateW, dateH))

    def _onSize(self, event):
        self._positionDateCtrl()
        event.Skip()

    def _onPopupOpen(self, event):
        """Track that popup was shown, so we can restore subfield on dismiss."""
        self._popupWasShown = True
        event.Skip()

    def _setDateFromCalendar(self, date):
        """Called by _CalendarComboPopup when user selects a date."""
        self._dateCtrl.SetDate(date)
        self.ChangeValue('')
        self._dateCtrl._returningFromPopup = True
        wx.CallAfter(self._dateCtrl.SetFocus)

    def DismissPopup(self):
        """Dismiss any open popup."""
        self.Dismiss()

    # --- Delegate public API to inner DateCtrl ---

    def GetDate(self):
        return self._dateCtrl.GetDate()

    def SetDate(self, d):
        self._dateCtrl.SetDate(d)

    def SetReadOnly(self, readOnly=True):
        """Set read-only mode: values greyed but visible, dropdown disabled.

        Disables the ComboCtrl (greys the dropdown button) and sets inner
        DateCtrl to read-only. The inner control's _onPaint uses
        IsThisEnabled() so it shows greyed values, not "N/A", even though
        the parent ComboCtrl is disabled.
        """
        self._dateCtrl.SetReadOnly(readOnly)
        super().Enable(not readOnly)

    def IsReadOnly(self):
        return self._dateCtrl.IsReadOnly()

    def HasOpenPopup(self):
        """Return True if the calendar popup is currently shown."""
        return self.IsPopupShown()

    def Bind(self, eventType, handler, source=None, id=wx.ID_ANY, id2=wx.ID_ANY):
        """Forward UI events to inner DateCtrl.

        Events like EVT_VALUE_CHANGED, EVT_KEY_DOWN, EVT_KILL_FOCUS, and
        EVT_SET_FOCUS fire on the inner control, not the ComboCtrl wrapper.
        Other events (e.g. EVT_SIZE) go to the ComboCtrl itself.
        """
        if eventType in (EVT_VALUE_CHANGED, wx.EVT_KEY_DOWN,
                         wx.EVT_KILL_FOCUS, wx.EVT_SET_FOCUS):
            self._dateCtrl.Bind(eventType, handler, source, id, id2)
        else:
            super().Bind(eventType, handler, source, id, id2)

    def Enable(self, enable=True):
        """Enable or disable the control (shows N/A when disabled)."""
        super().Enable(enable)
        self._dateCtrl.Enable(enable)

    def SetFocus(self):
        self._dateCtrl.SetFocus()


class _NativeDateCtrl(wx.Panel):
    """Windows wrapper around wx.adv.DatePickerCtrl.

    Provides the same public API as DateComboCustomCtrl so
    DateComboRouterCtrl callers don't need platform branches.

    Uses the Win32 Date-Time Picker control underneath, which provides:
    - Native rendering matching Windows theme
    - Correct tab navigation
    - Screen reader accessibility
    - Built-in dropdown calendar popup
    """

    def __init__(self, parent, year=None, month=None, day=None,
                 minDate=None, maxDate=None, dateFormat=None):
        super().__init__(parent)

        today = datetime.date.today()
        if year is None:
            year = today.year
        if month is None:
            month = today.month
        if day is None:
            day = today.day

        self._readOnly = False
        self._showingNA = False

        # Create native date picker (wx.DateTime months are 0-based)
        wxdt = wx.DateTime.FromDMY(day, month - 1, year)
        self._picker = wx.adv.DatePickerCtrl(
            self, dt=wxdt, style=wx.adv.DP_DROPDOWN
        )

        # Set date range if specified
        if minDate is not None or maxDate is not None:
            wxMin = self._date_to_wxdt(minDate) if minDate else wx.DefaultDateTime
            wxMax = self._date_to_wxdt(maxDate) if maxDate else wx.DefaultDateTime
            self._picker.SetRange(wxMin, wxMax)

        # Apply custom date format via Win32 DTM_SETFORMATW
        if dateFormat is not None:
            self.SetDateFormat(dateFormat)

        # Bridge native EVT_DATE_CHANGED → app's EVT_VALUE_CHANGED
        self._picker.Bind(wx.adv.EVT_DATE_CHANGED, self._onDateChanged)

        # Layout: picker fills the panel
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self._picker, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.SetMinSize(self._picker.GetBestSize())

        # Paint handler for "N/A" when disabled (picker hidden)
        self.bindPaintNA = lambda evt: self._onPaintNA(evt)
        self.Bind(wx.EVT_PAINT, self.bindPaintNA)

    # --- Date conversion helpers ---

    @staticmethod
    def _wxdt_to_date(wxdt):
        """wx.DateTime → datetime.date"""
        return datetime.date(wxdt.GetYear(), wxdt.GetMonth() + 1, wxdt.GetDay())

    @staticmethod
    def _date_to_wxdt(d):
        """datetime.date → wx.DateTime"""
        return wx.DateTime.FromDMY(d.day, d.month - 1, d.year)

    # --- N/A paint ---

    def _onPaintNA(self, event):
        """Paint 'N/A' centered when disabled. No-op when picker is visible."""
        if not self._showingNA:
            event.Skip()
            return
        dc = wx.PaintDC(self)
        w, h = self.GetClientSize()
        dc.SetBackground(wx.Brush(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)))
        dc.Clear()
        dc.SetFont(self._picker.GetFont())
        dc.SetTextForeground(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        text = "N/A"
        tw, th = dc.GetTextExtent(text)
        dc.DrawText(text, (w - tw) // 2, (h - th) // 2)

    # --- Event bridge ---

    def _onDateChanged(self, event):
        """Bridge native EVT_DATE_CHANGED → app's EVT_VALUE_CHANGED."""
        evt = ValueChangedEvent(self)
        wx.PostEvent(self, evt)

    # --- Public API (matching DateComboCustomCtrl) ---

    def GetDate(self):
        """Return current date as datetime.date."""
        return self._wxdt_to_date(self._picker.GetValue())

    def SetDate(self, d):
        """Set date from datetime.date."""
        self._picker.SetValue(self._date_to_wxdt(d))

    def SetReadOnly(self, readOnly=True):
        """Set read-only mode: picker greyed but values visible, not 'N/A'."""
        self._readOnly = readOnly
        self._showingNA = False
        self._picker.Show()
        self._picker.Enable(not readOnly)
        self.Refresh()

    def IsReadOnly(self):
        return self._readOnly

    def Enable(self, enable=True):
        """Enable or disable. When disabled, hides picker and paints 'N/A'."""
        super().Enable(enable)
        if enable:
            self._showingNA = False
            self._picker.Show()
            self._picker.Enable(True)
        else:
            self._picker.Hide()
            self._showingNA = True
        self.Refresh()
        return True

    def SetFocus(self):
        self._picker.SetFocus()

    def HasOpenPopup(self):
        """Native popup state is not queryable — return False."""
        return False

    def DismissPopup(self):
        """No-op — native control manages its own popup."""
        pass

    def Bind(self, eventType, handler, source=None, id=wx.ID_ANY, id2=wx.ID_ANY):
        """Route EVT_VALUE_CHANGED to this panel; others to super()."""
        if eventType in (EVT_VALUE_CHANGED, wx.EVT_KEY_DOWN,
                         wx.EVT_KILL_FOCUS, wx.EVT_SET_FOCUS):
            # These fire on the inner picker — bind there
            if eventType == EVT_VALUE_CHANGED:
                # EVT_VALUE_CHANGED fires on this panel (posted by _onDateChanged)
                super().Bind(eventType, handler, source, id, id2)
            else:
                self._picker.Bind(eventType, handler, source, id, id2)
        else:
            super().Bind(eventType, handler, source, id, id2)

    def SetDateFormat(self, dateFormat):
        """Set display format using Win32 DTM_SETFORMATW message.

        Args:
            dateFormat: 4-char format string (e.g. "YMD-", "MDY/", "DMY.")
                       as used by getLocaleDateFormat().
        """
        if wx.Platform != '__WXMSW__':
            return  # DTM_SETFORMATW is Windows-only

        field_order, separator = getLocaleDateFormat(override=dateFormat)
        dtp_map = {'year': 'yyyy', 'month': 'MM', 'date_day': 'dd'}
        fmt = separator.join(dtp_map[f] for f in field_order)

        try:
            import ctypes
            DTM_SETFORMATW = 0x1032  # DTM_FIRST (0x1000) + 50
            hwnd = self._picker.GetHandle()
            ctypes.windll.user32.SendMessageW(hwnd, DTM_SETFORMATW, 0, fmt)
        except Exception:
            pass  # Silently fail on non-Windows or if handle unavailable


def DateComboRouterCtrl(*args, **kwargs):
    """Router that returns the platform-appropriate date combo control.

    - Windows: _NativeDateCtrl (native Win32 Date-Time Picker)
    - Elsewhere (Linux, macOS): DateComboCustomCtrl (custom masked fields
      + calendar popup)
    """
    if wx.Platform == '__WXMSW__':
        return _NativeDateCtrl(*args, **kwargs)
    return DateComboCustomCtrl(*args, **kwargs)


class DateTimeComboCtrl(wx.EvtHandler):
    """Composite date/time control with checkbox, DateComboCustomCtrl, and TimeCtrl.

    Inherits wx.EvtHandler so it can host event handlers directly.
    DTC owns the change event — fires EVT_VALUE_CHANGED on sub-control
    blur and from ActivateValue()/DeactivateValue(). Sub-control
    EVT_VALUE_CHANGED events are trapped and dropped.

    The checkbox state is determined by the value:
    - value=None -> checkbox unchecked, fields disabled (show "N/A")
    - value=datetime -> checkbox checked, fields show that datetime

    Three states:
    1. Checked (normal): checkbox ON, fields enabled and editable
    2. Unchecked: checkbox OFF, fields disabled, GetDateTime() returns None
    3. Inactive (SetEditable(False)): checkbox ON but disabled, fields show
       values greyed out (read-only), not editable

    For flexible table layouts, get individual widgets with:
    - GetCheckBox() - wx.CheckBox (no label)
    - GetDateCtrl() - DateComboCustomCtrl
    - GetTimeCtrl() - TimeCtrl or TimeWithSecondsCtrl

    Args:
        parent: Parent window for the widgets
        value: datetime.datetime object, or None for unchecked state
        hourChoices, minuteChoices: Dropdown choices for time fields
        showSeconds: If True, use TimeWithSecondsCtrl (default False)
        secondChoices: Dropdown choices for seconds field
    """

    def __init__(self, parent, value=None, suggestedValue=None,
                 hourChoices=None, minuteChoices=None,
                 showSeconds=False, secondChoices=None):
        wx.EvtHandler.__init__(self)
        self._parent = parent
        self._showSeconds = showSeconds
        self._suggestedValue = suggestedValue

        checked = value is not None
        display_value = value if value is not None else (suggestedValue or datetime.datetime.now())

        self._checkbox = wx.CheckBox(parent)
        self._checkbox.SetValue(checked)
        self._checkbox.Bind(wx.EVT_CHECKBOX, self._onCheckboxChanged)

        self._dateCtrl = DateComboRouterCtrl(parent, year=display_value.year,
                                   month=display_value.month, day=display_value.day)

        if showSeconds:
            self._timeCtrl = TimeWithSecondsCtrl(
                parent, hours=display_value.hour, minutes=display_value.minute,
                seconds=display_value.second,
                hourChoices=hourChoices, minuteChoices=minuteChoices,
                secondChoices=secondChoices
            )
        else:
            self._timeCtrl = TimeCtrl(
                parent, hours=display_value.hour, minutes=display_value.minute,
                hourChoices=hourChoices, minuteChoices=minuteChoices
            )

        self._readOnly = False
        self._updateEnabled()

        # DTC owns the change event. Listen to sub-control blur and fire
        # DTC's own EVT_VALUE_CHANGED. Sub-control EVT_VALUE_CHANGED events
        # are trapped and explicitly dropped — DTC must never rely on them.
        self._dateCtrl.Bind(wx.EVT_KILL_FOCUS, self._onSubControlBlur)
        self._timeCtrl.Bind(wx.EVT_KILL_FOCUS, self._onSubControlBlur)
        self._dateCtrl.Bind(EVT_VALUE_CHANGED, self._onSubControlValueChanged)
        self._timeCtrl.Bind(EVT_VALUE_CHANGED, self._onSubControlValueChanged)

    def _onSubControlBlur(self, event):
        """Sub-control lost focus — fire DTC's own EVT_VALUE_CHANGED."""
        self.NotifyValueChanged()
        event.Skip()

    def _onSubControlValueChanged(self, event):
        """Trap and explicitly drop sub-control EVT_VALUE_CHANGED.

        DTC is the composite control and owns the change event. It fires
        EVT_VALUE_CHANGED on sub-control blur and from ActivateValue()/
        DeactivateValue(). Sub-control change events are an internal
        implementation detail and must not propagate to external handlers.

        IMPORTANT: This is a debug log point. If this fires, something is
        writing directly to the sub-controls instead of going through DTC's
        public API (ActivateValue, DeactivateValue, SetValue). That is a
        bug — all value changes must go through DTC.
        """
        # Do NOT call event.Skip() — intentionally consumed

    def NotifyValueChanged(self):
        """Fire EVT_VALUE_CHANGED on self (DTC is a wx.EvtHandler)."""
        event = ValueChangedEvent(self)
        wx.PostEvent(self, event)

    def _onCheckboxChanged(self, event):
        """Handle checkbox state change — route through abstraction."""
        checked = self._checkbox.GetValue()
        if checked:
            self.ActivateValue()
        else:
            self.DeactivateValue()
        event.Skip()

    def _updateEnabled(self):
        """Apply visual state based on checkbox + _readOnly flags.

        This is the single authority for the visual state of all sub-controls.
        SetEditable/SetReadOnly set flags and call this method.
        """
        checked = self._checkbox.GetValue()
        self._checkbox.Enable(not self._readOnly)

        if not checked:
            # Unchecked: show "N/A". Clear read-only first so inner control
            # paints "N/A" (not greyed values), then disable.
            self._dateCtrl.SetReadOnly(False)
            self._dateCtrl.Enable(False)
            self._timeCtrl.SetReadOnly(False)
            self._timeCtrl.Enable(False)
        elif self._readOnly:
            # Checked + read-only: re-enable from unchecked, then grey
            self._dateCtrl.Enable(True)
            self._dateCtrl.SetReadOnly(True)
            self._timeCtrl.Enable(True)
            self._timeCtrl.SetReadOnly(True)
        else:
            # Checked + editable: re-enable from unchecked
            self._dateCtrl.Enable(True)
            self._dateCtrl.SetReadOnly(False)
            self._timeCtrl.Enable(True)
            self._timeCtrl.SetReadOnly(False)

    # Widget accessors (for layout only — use state methods for logic)
    def GetCheckBox(self):
        return self._checkbox

    def GetDateCtrl(self):
        return self._dateCtrl

    def GetTimeCtrl(self):
        return self._timeCtrl

    def GetWidgets(self):
        return (self._checkbox, self._dateCtrl, self._timeCtrl)

    def HideCheckBox(self):
        """Hide the checkbox for always-active controls (e.g. effort start)."""
        self._checkbox.Hide()

    def CreateRowPanel(self, parent=None):
        """Create a panel containing checkbox + date + time in a horizontal row."""
        if parent is None:
            parent = self._parent

        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self._checkbox.Reparent(panel)
        self._dateCtrl.Reparent(panel)
        self._timeCtrl.Reparent(panel)

        sizer.Add(self._checkbox, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        sizer.Add(self._dateCtrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        sizer.Add(self._timeCtrl, 0, wx.ALIGN_CENTER_VERTICAL)

        panel.SetSizer(sizer)

        # Re-apply enabled state after reparenting. wx.ComboCtrl (DateComboCustomCtrl)
        # loses its native visual state (button greying, background color)
        # when reparented, because the platform re-creates theme state for
        # the new parent hierarchy. MaskedFieldsCtrl-based controls don't have
        # this issue since they paint everything in _onPaint.
        self._updateEnabled()

        return panel

    def ContainsControl(self, ctrl):
        return ctrl in (self._checkbox, self._dateCtrl, self._timeCtrl)

    def HasOpenPopup(self):
        """Return True if any child control has an open popup."""
        # DateComboCustomCtrl provides public HasOpenPopup()
        if self._dateCtrl.HasOpenPopup():
            return True
        # TimeCtrl uses MaskedFieldsCtrl._popup (same module, acceptable)
        if hasattr(self._timeCtrl, '_popup') and self._timeCtrl._popup is not None:
            return True
        return False

    def Bind(self, eventType, handler, source=None, id=wx.ID_ANY, id2=wx.ID_ANY):
        """Bind event handler.

        Routing:
        - EVT_VALUE_CHANGED: bind on self (DTC owns the change event via
          wx.EvtHandler). DTC fires this on sub-control blur and from
          ActivateValue()/DeactivateValue().
        - Other events (e.g. EVT_KILL_FOCUS): forwarded to all sub-controls.

        Note: EVT_CHECKBOX is NOT exposed — the checkbox is an internal
        implementation detail.
        """
        if eventType == EVT_VALUE_CHANGED:
            super().Bind(eventType, handler, source, id, id2)
        else:
            self._checkbox.Bind(eventType, handler, source, id, id2)
            self._dateCtrl.Bind(eventType, handler, source, id, id2)
            self._timeCtrl.Bind(eventType, handler, source, id, id2)

    # --- State transitions ---

    def _setCheckboxState(self, checked):
        """Set checkbox only if state differs (prevents recursive EVT_CHECKBOX)."""
        if self._checkbox.GetValue() != checked:
            self._checkbox.SetValue(checked)

    def ActivateValue(self, value=None):
        """Inactive → Active. Checks checkbox, optionally writes sub-controls.

        Args:
            value: datetime.datetime to set, or None to keep the internally
                   stored sub-control values (the stash).

        Contract: always fires EVT_VALUE_CHANGED.
        See DATETIME_CONTROLS.md, Sub-Control Stash Model.
        """
        if value is not None:
            self._dateCtrl.SetDate(value.date())
            self._timeCtrl.SetTime(value.time())
            self._suggestedValue = None
        elif self._suggestedValue is not None:
            self._dateCtrl.SetDate(self._suggestedValue.date())
            self._timeCtrl.SetTime(self._suggestedValue.time())
            self._suggestedValue = None
        self._setCheckboxState(True)
        self._updateEnabled()
        self.NotifyValueChanged()

    def DeactivateValue(self):
        """Active → Inactive. Unchecks checkbox, sub-controls retain values.

        The sub-controls are the stash — they hold the datetime while the
        checkbox is unchecked. Contract: always fires EVT_VALUE_CHANGED.
        See DATETIME_CONTROLS.md, Sub-Control Stash Model.
        """
        self._setCheckboxState(False)
        self._updateEnabled()
        self.NotifyValueChanged()

    def IsActive(self):
        """Return True if the control has an active value (non-null)."""
        return self._checkbox.GetValue()

    def GetDateTime(self):
        if not self._checkbox.GetValue():
            return None
        d = self._dateCtrl.GetDate()
        t = self._timeCtrl.GetTime()
        return datetime.datetime.combine(d, t)

    # Domain-compatible GetValue/SetValue for AttributeSync
    def GetValue(self):
        if not self._checkbox.GetValue():
            return date.DateTime()
        d = self._dateCtrl.GetDate()
        t = self._timeCtrl.GetTime()
        dt = datetime.datetime.combine(d, t)
        return date.DateTime.fromDateTime(dt)

    def SetValue(self, newValue):
        if newValue is None or newValue == date.DateTime():
            self.DeactivateValue()
        else:
            self.ActivateValue(datetime.datetime(
                newValue.year, newValue.month, newValue.day,
                newValue.hour, newValue.minute, newValue.second))

    def GetDate(self):
        return self._dateCtrl.GetDate()

    def GetTime(self):
        return self._timeCtrl.GetTime()

    def GetChildren(self):
        return [self._checkbox, self._dateCtrl, self._timeCtrl]

    def GetId(self):
        return self._checkbox.GetId()

    def SetEditable(self):
        """Make the combo editable.

        - Checkbox enabled (user can toggle)
        - Date/time fields editable with normal colors
        - Dropdown button active
        """
        self._readOnly = False
        self._updateEnabled()

    def SetReadOnly(self):
        """Make the combo read-only.

        - Checkbox disabled (shows checked state, not clickable)
        - Date/time fields show greyed values, not editable
        - Dropdown button disabled
        """
        self._readOnly = True
        self._updateEnabled()

    def IsEditable(self):
        """Return True if the combo is editable (not read-only)."""
        return not self._readOnly

    def IsReadOnly(self):
        """Return True if the combo is read-only."""
        return self._readOnly

    def SetFocus(self):
        if self._dateCtrl.IsEnabled():
            self._dateCtrl.SetFocus()
        else:
            self._checkbox.SetFocus()


