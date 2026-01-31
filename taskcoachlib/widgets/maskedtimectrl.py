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


class _CalendarPopup(_PopupWindow):
    """Calendar popup for date selection."""

    def __init__(self, selection, font, minDate=None, maxDate=None, *args, **kwargs):
        self.__originalDate = selection  # Value when popup opened
        self.__highlightedDate = selection  # Currently highlighted (mouse or keys)
        self.__year = selection.year
        self.__month = selection.month
        self.__minDate = minDate
        self.__maxDate = maxDate
        self.__maxDim = None
        self.__font = font
        self.__days = []
        super().__init__(*args, **kwargs)
        pub.subscribe(self._onColoursChanged, 'calendar.colours.changed')

    def _onColoursChanged(self):
        self.Refresh()

    def Dismiss(self):
        pub.unsubscribe(self._onColoursChanged, 'calendar.colours.changed')
        super().Dismiss()

    def HandleKey(self, event):
        """Handle keyboard navigation within the calendar popup.

        Arrow keys move the selection:
        - Left/Right: Move by 1 day
        - Up/Down: Move by 1 week (7 days)

        Enter confirms the selection, Escape cancels.
        """
        keyCode = event.GetKeyCode()

        if keyCode == wx.WXK_ESCAPE:
            self.Dismiss()
            return True
        elif keyCode == wx.WXK_RETURN:
            self.GetParent()._setDateFromCalendar(self.__highlightedDate)
            self.Dismiss()
            return True
        elif keyCode == wx.WXK_LEFT:
            self.__MoveHighlight(datetime.timedelta(days=-1))
            return True
        elif keyCode == wx.WXK_RIGHT:
            self.__MoveHighlight(datetime.timedelta(days=1))
            return True
        elif keyCode == wx.WXK_UP:
            self.__MoveHighlight(datetime.timedelta(days=-7))
            return True
        elif keyCode == wx.WXK_DOWN:
            self.__MoveHighlight(datetime.timedelta(days=7))
            return True
        return False

    def __MoveHighlight(self, delta):
        """Move the calendar highlight by the given timedelta."""
        newDate = self.__highlightedDate + delta
        # Check min/max bounds
        if self.__minDate is not None and newDate < self.__minDate:
            wx.Bell()
            return
        if self.__maxDate is not None and newDate > self.__maxDate:
            wx.Bell()
            return
        # Check year bounds (datetime supports 1-9999)
        if newDate.year < 1 or newDate.year > 9999:
            wx.Bell()
            return
        self.__highlightedDate = newDate
        # Update displayed month/year if highlight moved to different month
        if self.__highlightedDate.year != self.__year or self.__highlightedDate.month != self.__month:
            self.__year = self.__highlightedDate.year
            self.__month = self.__highlightedDate.month
            self.SetClientSize(self._getExtent(wx.ClientDC(self.interior())))
        self.Refresh()

    def Fill(self, interior):
        interior.Bind(wx.EVT_PAINT, self._onPaint)
        interior.Bind(wx.EVT_LEFT_UP, self._onLeftUp)
        interior.Bind(wx.EVT_MOTION, self._onMotion)
        interior.Bind(wx.EVT_LEAVE_WINDOW, self._onLeaveWindow)
        self.SetClientSize(self._getExtent(wx.ClientDC(interior)))

    def _getExtent(self, dc):
        dc.SetFont(self.__font)
        W, H = 0, 0
        for month in range(1, 13):
            header = datetime.date(year=self.__year, month=month, day=11).strftime("%B %Y")
            tw, th = dc.GetTextExtent(header)
            W = max(W, tw)
            H = max(H, th)
        header = datetime.date(year=self.__year, month=self.__month, day=1).strftime("%B %Y")

        lines = monthcalendarex(self.__year, self.__month, weeks=1)
        self.__maxDim = 0
        for line in lines:
            for year, month, day in line:
                tw, th = dc.GetTextExtent("%d" % day)
                self.__maxDim = max(self.__maxDim, tw, th)

        for hdr in calendar.weekheader(2).split():
            tw, th = dc.GetTextExtent(hdr)
            self.__maxDim = max(self.__maxDim, tw, th)

        # Add spacing for cell content
        self.__maxDim += 4
        contentOffsetX, contentOffsetY = getTextCtrlContentOffset()
        return wx.Size(
            max(W + 48 + 4, self.__maxDim * len(lines[0])) + contentOffsetX * 2,
            H + 2 + self.__maxDim * (len(lines) + 1) + contentOffsetY * 2,
        )

    def _onPaint(self, event):
        win = event.GetEventObject()
        dc = wx.PaintDC(win)
        w, h = self.GetClientSize()
        renderer = wx.RendererNative.Get()

        # Draw text control frame with editing focus highlight (blue ring)
        renderer.DrawTextCtrl(win, dc, wx.Rect(0, 0, w, h), wx.CONTROL_FOCUSED)

        contentOffsetX, contentOffsetY = getTextCtrlContentOffset()
        contentW = w - contentOffsetX * 2

        dc.SetFont(self.__font)
        self.__win = win  # Store for drawFocusRect calls
        self.__contentOffsetX = contentOffsetX  # Store for content positioning
        self.__contentOffsetY = contentOffsetY

        # Get theme-aware calendar colours
        colours = getCalendarColours()

        # Header: current month/year
        textColour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
        dc.SetPen(wx.Pen(textColour))
        dc.SetBrush(wx.Brush(textColour))
        dc.SetTextForeground(textColour)

        header = datetime.date(year=self.__year, month=self.__month, day=1).strftime("%B %Y")
        tw, th = dc.GetTextExtent(header)
        dc.DrawText(header, contentOffsetX + (contentW - 48 - tw) // 2, contentOffsetY)

        buttonDim = min(th, 10)

        cx = w - contentOffsetX - 24
        cy = contentOffsetY + th // 2 + 1

        gc = wx.GraphicsContext.Create(dc)
        gc.SetPen(gc.CreatePen(wx.Pen(textColour)))
        gc.SetBrush(gc.CreateBrush(wx.Brush(textColour)))

        # Prev month button (left arrow)
        if self.__month != 1 or self.__year != 1:
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
        if self.__month != 12 or self.__year != 9999:
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
        dc.DrawRectangle(contentOffsetX, y, self.__maxDim * 7, self.__maxDim)
        dc.SetTextForeground(colours['weekday_header_fg'])
        for idx, hdr in enumerate(calendar.weekheader(2).split()):
            tw, th_hdr = dc.GetTextExtent(hdr)
            dc.DrawText(
                hdr,
                contentOffsetX + self.__maxDim * idx + int((self.__maxDim - tw) // 2),
                y + int((self.__maxDim - th_hdr) // 2),
            )

        y += self.__maxDim

        # Days
        self.__days = []
        for line in monthcalendarex(self.__year, self.__month, weeks=1):
            x = contentOffsetX
            for dayIndex, (year, month, day) in enumerate(line):
                dt = datetime.date(year=year, month=month, day=day)
                active = (self.__minDate is None or dt >= self.__minDate) and (
                    self.__maxDate is None or dt <= self.__maxDate
                )
                thisMonth = year == self.__year and month == self.__month

                dc.SetPen(wx.Pen(textColour))
                dc.SetTextForeground(
                    colours['weekend_day_fg'] if (dayIndex + calendar.firstweekday()) % 7 in [5, 6] else textColour
                )

                # Draw backgrounds first so highlight can paint on top
                if not active:
                    inactiveBg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
                    dc.SetPen(wx.Pen(inactiveBg))
                    dc.SetBrush(wx.Brush(inactiveBg))
                    dc.DrawRectangle(x, y, self.__maxDim, self.__maxDim)
                elif not thisMonth:
                    otherMonthBg = colours['other_month_bg'] if colours['other_month_bg'] is not None else wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
                    dc.SetPen(wx.Pen(otherMonthBg))
                    dc.SetBrush(wx.Brush(otherMonthBg))
                    dc.DrawRectangle(x, y, self.__maxDim, self.__maxDim)

                isHighlighted = (dt == self.__highlightedDate and active)

                if isHighlighted:
                    # Single highlight style for both mouse hover and keyboard navigation
                    drawFocusRect(self.__win, dc, x, y, self.__maxDim, self.__maxDim)
                    dc.SetTextForeground(
                        wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
                    )

                # Highlight today with border
                now = datetime.datetime.now()
                if (dt.year, dt.month, dt.day) == (now.year, now.month, now.day):
                    dc.SetPen(wx.Pen(colours['today_border']))
                    dc.SetBrush(wx.TRANSPARENT_BRUSH)
                    dc.DrawRectangle(x, y, self.__maxDim, self.__maxDim)

                label = "%d" % day
                tw, th_day = dc.GetTextExtent(label)
                dc.DrawText(
                    label,
                    x + (self.__maxDim - tw) // 2,
                    y + (self.__maxDim - th_day) // 2,
                )

                if active:
                    self.__days.append((x, y, (year, month, day)))
                x += self.__maxDim
            y += self.__maxDim

    def _onLeftUp(self, event):
        w, h = self.GetClientSize()
        contentOffsetX, contentOffsetY = getTextCtrlContentOffset()

        dc = wx.ClientDC(self.interior())
        dc.SetFont(self.__font)
        header = datetime.date(year=self.__year, month=self.__month, day=1).strftime("%B %Y")
        tw, th = dc.GetTextExtent(header)

        # Buttons area (top right, accounting for content offset)
        if event.GetY() < contentOffsetY + th + 2 and event.GetX() > w - contentOffsetX - 48:
            if event.GetX() < w - contentOffsetX - 48 + 16 and (self.__month != 1 or self.__year != 1):
                # Prev month
                if self.__month == 1:
                    self.__year -= 1
                    self.__month = 12
                else:
                    self.__month -= 1
            elif event.GetX() < w - contentOffsetX - 48 + 32:
                # Today button
                today = datetime.datetime.now()
                self.__year = today.year
                self.__month = today.month
            elif self.__month != 12 or self.__year != 9999:
                # Next month
                if self.__month == 12:
                    self.__year += 1
                    self.__month = 1
                else:
                    self.__month += 1
            self.SetClientSize(self._getExtent(wx.ClientDC(self.interior())))
            self.Refresh()
            return

        # Day selection
        for x, y, (year, month, day) in self.__days:
            if (
                event.GetX() >= x
                and event.GetX() < x + self.__maxDim
                and event.GetY() >= y
                and event.GetY() < y + self.__maxDim
            ):
                self.GetParent()._setDateFromCalendar(
                    datetime.date(year=year, month=month, day=day)
                )
                self.Dismiss()
                break

    def _onMotion(self, event):
        """Track mouse movement to highlight day under cursor."""
        newHighlight = None
        for x, y, (year, month, day) in self.__days:
            if (
                event.GetX() >= x
                and event.GetX() < x + self.__maxDim
                and event.GetY() >= y
                and event.GetY() < y + self.__maxDim
            ):
                newHighlight = datetime.date(year=year, month=month, day=day)
                break
        if newHighlight is not None and newHighlight != self.__highlightedDate:
            self.__highlightedDate = newHighlight
            self.Refresh()

    def _onLeaveWindow(self, event):
        """Keep highlight when mouse leaves popup - standard dropdown behavior."""
        # Don't clear highlight when mouse leaves - standard dropdown behavior
        pass


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
    """A numeric subfield within a FieldsCtrl."""

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
        # Always validate (e.g., DateCtrl adjusts day when month changes)
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
        # Notify observer of value change (for live preview updates)
        if hasattr(self.__observer, 'NotifyValueChanged'):
            self.__observer.NotifyValueChanged()

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
                # First digit: replace value entirely
                self.SetValue(number)
            else:
                newVal = (self.__value * 10 + number) % int(math.pow(10, self.__width))
                self.SetValue(newVal)
            self.__digitCount += 1
            self.__observer.DismissPopup()
            # Auto-advance to next field after all digits typed
            if self.__digitCount >= self.__width:
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


class FieldsCtrl(wx.Panel):
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

        # Set minimum size
        self.SetMinSize(wx.Size(
            curX + self.MARGIN,
            minH + 2 * self.MARGIN
        ))

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
        flags = 0
        if hasFocus and not self._readOnly:
            flags |= wx.CONTROL_FOCUSED
        if not self.IsEnabled() or self._readOnly:
            flags |= wx.CONTROL_DISABLED

        wx.RendererNative.Get().DrawTextCtrl(self, dc, wx.Rect(0, 0, w, h), flags)

        dc.SetFont(self.GetFont())

        if self.IsEnabled() and not self._readOnly:
            # Normal editable mode - show values
            textColour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
            for widget, x, y, ww, hh in self._widgets:
                if isinstance(widget, str):
                    dc.SetTextForeground(textColour)
                    dc.DrawText(widget, int(x), int(y))
                else:
                    # NumericField - draw focus highlight only if focused
                    if widget == self._focus and hasFocus:
                        drawFocusRect(self, dc, x, y, ww, hh)
                        dc.SetTextForeground(
                            wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
                        )
                    else:
                        dc.SetTextForeground(textColour)
                    widget.PaintValue(dc, x, y, ww, hh)
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
                    dc.DrawText(widget, int(x), int(y))
                else:
                    widget.PaintValue(dc, x, y, ww, hh)

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
        # Find the widget entry for the focused field
        for widget, x, y, w, h in self._widgets:
            if widget == self._focus:
                choices = self._focus.GetChoices()
                if choices:
                    self._showPopup(self._focus, choices, x, y, w, h)
                break

    # Time thresholds for focus and popup behavior (in seconds)
    FOCUS_DELAY = 0.05  # Minimum time before showing popup after focus
    POPUP_TOGGLE_DELAY = 0.2  # Time window to detect click-to-close toggle

    def _onLeftUp(self, event):
        pt = event.GetPosition()

        # No interaction in read-only mode
        if self._readOnly:
            event.Skip()
            return

        # Find which widget was clicked
        for widget, x, y, w, h in self._widgets:
            if isinstance(widget, NumericField):
                if x <= pt.x <= x + w and y <= pt.y <= y + h:
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
                                self._showPopup(widget, choices, x, y, w, h)

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
            self._focus.ResetState()  # Clear any partial digit entry
        self.Refresh()
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
        """Called when a field value changes. Fires EVT_VALUE_CHANGED event."""
        if not getattr(self, '_suppressEvents', False):
            self._fireValueChanged()

    def _fireValueChanged(self):
        """Fire EVT_VALUE_CHANGED event to notify listeners of value change."""
        event = ValueChangedEvent(self)
        wx.PostEvent(self, event)

    def SetFieldValueQuiet(self, name, value):
        """Set a field value without firing events."""
        self._suppressEvents = True
        try:
            self.SetFieldValue(name, value)
        finally:
            self._suppressEvents = False


class DurationCtrl(FieldsCtrl):
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

    def SetTimeDelta(self, duration):
        """Alias for SetDuration for consistency with other controls."""
        self.SetDuration(duration)

    def GetValue(self):
        """Alias for GetDuration for AttributeSync compatibility."""
        return self.GetDuration()

    def SetValue(self, duration):
        """Alias for SetDuration for AttributeSync compatibility."""
        self.SetDuration(duration)


class DurationCtrlVerbose(FieldsCtrl):
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

    def SetTimeDelta(self, duration):
        """Alias for SetDuration for consistency with other controls."""
        self.SetDuration(duration)

    def GetValue(self):
        """Alias for GetDuration for AttributeSync compatibility."""
        return self.GetDuration()

    def SetValue(self, duration):
        """Alias for SetDuration for AttributeSync compatibility."""
        self.SetDuration(duration)


class TimeCtrl(FieldsCtrl):
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


class TimeWithSecondsCtrl(FieldsCtrl):
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


class DateCtrl(FieldsCtrl):
    """Date control with locale-aware field order and separators.

    Automatically detects the system locale's date format using strftime("%x")
    and arranges year/month/day fields accordingly:
    - US: MM/DD/YYYY
    - Europe: DD/MM/YYYY
    - ISO/Canada: YYYY-MM-DD

    The dateFormat parameter can override the automatic detection:
    - None or "": Use automatic locale detection
    - "YMD-": Year-Month-Day with hyphen (ISO format)
    - "MDY/": Month/Day/Year with slash (US format)
    - "DMY/": Day/Month/Year with slash (European format)
    - "DMY.": Day.Month.Year with dot (German format)
    """

    def __init__(self, parent, year=None, month=None, day=None,
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
        self._calendarPopup = None

        # Get date format: use explicit override, or read from settings, or detect from locale
        if dateFormat is not None:
            # Explicit format passed - use it directly
            field_order, separator = getLocaleDateFormat(override=dateFormat if dateFormat else None)
        else:
            # No explicit format - use effective format from settings
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

    def _onChar(self, event):
        """Override to show calendar popup on Enter instead of field dropdown."""
        if not self._focus:
            event.Skip()
            return

        keyCode = event.GetKeyCode()

        # Tab exits control (always allowed, even in read-only mode)
        if keyCode == wx.WXK_TAB:
            self.DismissPopup()
            self.Navigate(not event.ShiftDown())
            return

        # Block all other input in read-only mode
        if self._readOnly:
            return

        # Escape dismisses popup
        if keyCode == wx.WXK_ESCAPE:
            if self._popup or self._calendarPopup:
                self.DismissPopup()
                return
            event.Skip()
            return

        # Enter or F4 toggles calendar popup
        if keyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_F4):
            if self._calendarPopup:
                self.DismissPopup()
            else:
                self._showCalendarPopup()
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
        """Override to show calendar popup on click."""
        # No interaction in read-only mode
        if self._readOnly:
            event.Skip()
            return

        pt = event.GetPosition()

        # Check if click is inside the control
        w, h = self.GetClientSize()
        if 0 <= pt.x <= w and 0 <= pt.y <= h:
            # Set focus if not already focused
            if not self.HasFocus():
                self.SetFocus()
                self._focusStamp = time.time()
                self.Refresh()
                return

            # Find which field was clicked and focus it
            for widget, x, y, fw, fh in self._widgets:
                if isinstance(widget, NumericField):
                    if x <= pt.x <= x + fw and y <= pt.y <= y + fh:
                        self._focus = widget
                        self._focus.ResetState()
                        break

            # Check for toggle behavior (click when calendar is open)
            if self._calendarPopup is not None:
                self.DismissPopup()
            elif (
                self._popupDismissedWidget is not None
                and time.time() - self._popupDismissedTime < self.POPUP_TOGGLE_DELAY
            ):
                # Just closed, don't reopen
                self._popupDismissedWidget = None
            else:
                # Show calendar popup
                if time.time() - self._focusStamp >= self.FOCUS_DELAY:
                    self._showCalendarPopup()

            self.Refresh()
            return

        event.Skip()

    def _showCalendarPopup(self):
        """Show the calendar popup for date selection."""
        if self._calendarPopup is not None:
            return

        selection = self.GetDate()
        popup = _CalendarPopup(
            selection, self.GetFont(),
            minDate=self._minDate, maxDate=self._maxDate,
            parent=self
        )
        self._calendarPopup = popup

        # Position popup below the control, left-aligned
        pos = self.ClientToScreen(wx.Point(0, self.GetClientSize().GetHeight()))
        popup.Popup(pos)
        popup.Bind(EVT_POPUP_DISMISS, self._onCalendarDismiss)

    def _onCalendarDismiss(self, event):
        """Handle calendar popup dismissal."""
        self._popupDismissedWidget = self
        self._popupDismissedTime = time.time()
        self._calendarPopup = None
        self._returningFromPopup = True
        self.SetFocus()
        event.Skip()

    def _setDateFromCalendar(self, date):
        """Set date from calendar popup selection."""
        self.SetDate(date)

    def DismissPopup(self):
        """Dismiss any open popup (calendar or field dropdown)."""
        if self._calendarPopup:
            self._calendarPopup.Dismiss()
            self._calendarPopup = None
        super().DismissPopup()

    def ValidateChange(self, field, value):
        """Validate date changes, adjusting day if needed for month/year changes."""
        # Get current values (already updated by NumericField.SetValue)
        year = self.GetFieldValue('year')
        month = self.GetFieldValue('month')
        day = self.GetFieldValue('date_day')

        # Clamp day to valid range for month/year
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


class DateTimeCombo:
    """Flexible date/time combo providing separate widgets for table layout.

    Creates a checkbox, DateCtrl, and TimeCtrl that are linked together.
    The checkbox state is determined by the value:
    - value=None → checkbox unchecked, fields disabled
    - value=datetime → checkbox checked, fields show that datetime

    Three states:
    1. Checked (normal): checkbox ON, fields enabled and editable
    2. Unchecked: checkbox OFF, fields disabled, GetDateTime() returns None
    3. Inactive (SetEditable(False)): checkbox ON but disabled, fields show
       values greyed out (read-only), not editable

    When user checks an unchecked control, "now" is used as the initial value.

    For flexible table layouts, get individual widgets with:
    - GetCheckBox() - wx.CheckBox (no label - add label separately)
    - GetDateCtrl() - DateCtrl
    - GetTimeCtrl() - TimeCtrl or TimeWithSecondsCtrl

    Or use GetWidgets() to get all three as a tuple.

    Example usage in a table layout:
        combo = DateTimeCombo(panel, value=datetime.datetime.now())  # checked
        combo = DateTimeCombo(panel, value=None)  # unchecked
        grid.Add(wx.StaticText(panel, label="Due date"))  # Column 1: label
        grid.Add(combo.GetCheckBox())  # Column 2: checkbox only
        grid.Add(combo.GetDateCtrl())  # Column 3: date
        grid.Add(combo.GetTimeCtrl())  # Column 4: time

    Args:
        parent: Parent window for the widgets
        value: datetime.datetime object, or None for unchecked state.
               None means checkbox is unchecked; datetime means checked.
        hourChoices, minuteChoices: Dropdown choices for time fields (None = no dropdown)
        showSeconds: If True, use TimeWithSecondsCtrl instead of TimeCtrl (default False)
        secondChoices: Dropdown choices for seconds field (only used if showSeconds=True)
    """

    def __init__(self, parent, value=None,
                 hourChoices=None, minuteChoices=None,
                 showSeconds=False, secondChoices=None):
        self._parent = parent
        self._showSeconds = showSeconds

        # Checkbox state determined by whether value is None
        checked = value is not None

        # For display purposes, use "now" when unchecked (shown when user checks it)
        display_value = value if value is not None else datetime.datetime.now()

        # Create checkbox (no label - label is added separately by caller)
        self._checkbox = wx.CheckBox(parent)
        self._checkbox.SetValue(checked)
        self._checkbox.Bind(wx.EVT_CHECKBOX, self._onCheckboxChanged)

        # Create date control with values
        self._dateCtrl = DateCtrl(parent, year=display_value.year,
                                  month=display_value.month, day=display_value.day)

        # Create time control with values
        if showSeconds:
            self._timeCtrl = TimeWithSecondsCtrl(
                parent, hours=display_value.hour, minutes=display_value.minute,
                seconds=display_value.second,
                hourChoices=hourChoices, minuteChoices=minuteChoices, secondChoices=secondChoices
            )
        else:
            self._timeCtrl = TimeCtrl(
                parent, hours=display_value.hour, minutes=display_value.minute,
                hourChoices=hourChoices, minuteChoices=minuteChoices
            )

        # Set initial enabled state based on checkbox
        self._updateEnabled()

    def _onCheckboxChanged(self, event):
        """Handle checkbox state change."""
        self._updateEnabled()
        # Fire value changed event from date control (checkbox affects whether value is set)
        wx.PostEvent(self._dateCtrl, ValueChangedEvent(self._dateCtrl))
        event.Skip()

    def _updateEnabled(self):
        """Update enabled state of date/time controls based on checkbox.

        When unchecked, fields show "N/A" but values are preserved internally.
        When re-checked, previous values reappear.
        """
        enabled = self._checkbox.GetValue()
        self._dateCtrl.Enable(enabled)
        self._timeCtrl.Enable(enabled)
        # Values are NOT reset - they are preserved internally

    # Widget accessors for flexible layout
    def GetCheckBox(self):
        """Get the checkbox widget for layout."""
        return self._checkbox

    def GetDateCtrl(self):
        """Get the date control widget for layout."""
        return self._dateCtrl

    def GetTimeCtrl(self):
        """Get the time control widget for layout."""
        return self._timeCtrl

    def GetWidgets(self):
        """Get all widgets as a tuple: (checkbox, dateCtrl, timeCtrl)."""
        return (self._checkbox, self._dateCtrl, self._timeCtrl)

    def CreateRowPanel(self, parent=None):
        """Create a panel containing checkbox + date + time in a horizontal row.

        This simplifies grid layouts by putting all datetime widgets in one cell.
        Widgets are reparented to the new panel.

        Args:
            parent: Parent window for the panel. If None, uses the original parent.

        Returns:
            wx.Panel containing the three widgets arranged horizontally.
        """
        if parent is None:
            parent = self._parent

        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Reparent widgets to the panel
        self._checkbox.Reparent(panel)
        self._dateCtrl.Reparent(panel)
        self._timeCtrl.Reparent(panel)

        # Arrange: checkbox | date | time
        sizer.Add(self._checkbox, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        sizer.Add(self._dateCtrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        sizer.Add(self._timeCtrl, 0, wx.ALIGN_CENTER_VERTICAL)

        panel.SetSizer(sizer)
        return panel

    def ContainsControl(self, ctrl):
        """Return True if ctrl is one of our child controls (checkbox, dateCtrl, timeCtrl)."""
        return ctrl in (self._checkbox, self._dateCtrl, self._timeCtrl)

    def HasOpenPopup(self):
        """Return True if any child control has an open popup (calendar or dropdown).

        Used by inline editors to prevent closing while user interacts with popups.
        """
        # Check dateCtrl for calendar popup
        if hasattr(self._dateCtrl, '_calendarPopup') and self._dateCtrl._calendarPopup is not None:
            return True
        # Check dateCtrl for field dropdown
        if hasattr(self._dateCtrl, '_popup') and self._dateCtrl._popup is not None:
            return True
        # Check timeCtrl for field dropdown
        if hasattr(self._timeCtrl, '_popup') and self._timeCtrl._popup is not None:
            return True
        return False

    def Bind(self, eventType, handler, source=None, id=wx.ID_ANY, id2=wx.ID_ANY):
        """Bind event handler to child controls.

        For EVT_VALUE_CHANGED, binds to both dateCtrl and timeCtrl,
        wrapping the handler so event.GetEventObject() returns this DateTimeCombo.
        """
        if eventType == EVT_VALUE_CHANGED:
            # Wrap handler to set event object to this DateTimeCombo
            combo = self  # Capture self for closure
            def wrappedHandler(event):
                event.SetEventObject(combo)
                handler(event)
            self._dateCtrl.Bind(eventType, wrappedHandler)
            self._timeCtrl.Bind(eventType, wrappedHandler)
        else:
            # For other events, bind to all child controls
            self._checkbox.Bind(eventType, handler, source, id, id2)
            self._dateCtrl.Bind(eventType, handler, source, id, id2)
            self._timeCtrl.Bind(eventType, handler, source, id, id2)

    # Value accessors
    def IsChecked(self):
        """Return whether the checkbox is checked."""
        return self._checkbox.GetValue()

    def SetChecked(self, checked):
        """Set the checkbox state and update enabled state."""
        self._checkbox.SetValue(checked)
        self._updateEnabled()

    def GetDateTime(self):
        """Get combined datetime value, or None if unchecked."""
        if not self._checkbox.GetValue():
            return None
        d = self._dateCtrl.GetDate()
        t = self._timeCtrl.GetTime()
        return datetime.datetime.combine(d, t)

    def SetDateTime(self, dt):
        """Set datetime value. If None, unchecks the checkbox."""
        if dt is None:
            self._checkbox.SetValue(False)
            self._updateEnabled()
        else:
            self._checkbox.SetValue(True)
            self._dateCtrl.SetDate(dt.date())
            self._timeCtrl.SetTime(dt.time())
            self._updateEnabled()

    # Domain-compatible GetValue/SetValue for AttributeSync
    def GetValue(self):
        """Get value as domain date.DateTime for AttributeSync compatibility.

        Returns date.DateTime() (sentinel) when unchecked, or
        date.DateTime.fromDateTime(dt) when checked.
        This matches datectrl.py:156-171 behavior.
        """
        if not self._checkbox.GetValue():
            return date.DateTime()  # Sentinel for "no value"
        d = self._dateCtrl.GetDate()
        t = self._timeCtrl.GetTime()
        dt = datetime.datetime.combine(d, t)
        return date.DateTime.fromDateTime(dt)

    def SetValue(self, newValue):
        """Set value from domain date.DateTime for AttributeSync compatibility.

        If newValue is None or date.DateTime() (sentinel), unchecks the checkbox.
        Otherwise sets the value and checks the checkbox.
        This matches datectrl.py:173-177 behavior.

        Note: Domain sends None for reminder (special case in setReminder),
        while other date fields send date.DateTime() sentinel.
        """
        if newValue is None or newValue == date.DateTime():
            # No value: None (reminder) or date.DateTime() sentinel (other dates)
            self._checkbox.SetValue(False)
            self._updateEnabled()
        else:
            self._checkbox.SetValue(True)
            self._dateCtrl.SetDate(newValue.date())
            self._timeCtrl.SetTime(datetime.time(newValue.hour, newValue.minute, newValue.second))
            self._updateEnabled()

    def GetDate(self):
        """Get just the date value."""
        return self._dateCtrl.GetDate()

    def SetDate(self, d):
        """Set just the date value."""
        self._dateCtrl.SetDate(d)

    def GetTime(self):
        """Get just the time value."""
        return self._timeCtrl.GetTime()

    def SetTime(self, t):
        """Set just the time value."""
        self._timeCtrl.SetTime(t)

    # Enable/disable all widgets
    def Enable(self, enable=True):
        """Enable or disable all widgets.

        When disabled, all three widgets (checkbox, date, time) are greyed out.
        When enabled, checkbox becomes active and date/time depend on checkbox state.
        """
        self._checkbox.Enable(enable)
        if enable:
            # Restore normal state: date/time depend on checkbox
            self._updateEnabled()
        else:
            # Force disable date/time regardless of checkbox
            self._dateCtrl.Enable(False)
            self._timeCtrl.Enable(False)

    def Disable(self):
        """Disable all widgets."""
        self.Enable(False)

    def IsEnabled(self):
        """Return whether the combo is enabled."""
        return self._checkbox.IsEnabled()

    def GetChildren(self):
        """Return child widgets for AttributeSync focus binding."""
        return [self._checkbox, self._dateCtrl, self._timeCtrl]

    def GetId(self):
        """Return ID for AttributeSync widget validity check."""
        return self._checkbox.GetId()

    def SetEditable(self, editable=True):
        """Set whether the combo is editable (inactive mode).

        When editable=False (inactive):
        - Checkbox is disabled (shows checked state but not clickable)
        - Date/time fields show values greyed out (read-only, not "N/A")
        - Values are preserved and visible

        This is different from Enable(False) which shows "N/A" in the fields.
        """
        self._checkbox.Enable(editable)
        self._dateCtrl.SetReadOnly(not editable)
        self._timeCtrl.SetReadOnly(not editable)

    def IsEditable(self):
        """Return whether the combo is editable."""
        return self._checkbox.IsEnabled() and not self._dateCtrl.IsReadOnly()

    def SetFocus(self):
        """Set focus to the date control (or checkbox if date is disabled)."""
        if self._dateCtrl.IsEnabled():
            self._dateCtrl.SetFocus()
        else:
            self._checkbox.SetFocus()

    # Bind events
    def Bind(self, eventType, handler):
        """Bind an event handler to the combo's widgets.

        Event routing:
        - EVT_KILL_FOCUS: all three (for commit-on-focus-loss pattern)
        - EVT_CHECKBOX: checkbox only
        - Other events: all three
        """
        if eventType == wx.EVT_CHECKBOX:
            self._checkbox.Bind(eventType, handler)
        else:
            # Bind to all three widgets
            self._checkbox.Bind(eventType, handler)
            self._dateCtrl.Bind(eventType, handler)
            self._timeCtrl.Bind(eventType, handler)


