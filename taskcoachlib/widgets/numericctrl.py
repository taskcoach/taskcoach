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

import locale
import wx
from taskcoachlib.widgets.maskedtimectrl import EVT_VALUE_CHANGED, ValueChangedEvent


def _get_locale_decimal_char():
    """Get decimal separator from locale, with safe fallback."""
    return locale.localeconv().get("decimal_point", ".") or "."


def _get_configured_decimal_char():
    """Get decimal separator from preferences, falling back to locale.

    Fallback chain: configured pref -> locale -> "."
    """
    try:
        from taskcoachlib.config import settings
        val = settings.Settings().get("view", "decimal_separator")
        if val:
            return val
    except Exception:
        pass
    return _get_locale_decimal_char()


class NumericCtrl(wx.TextCtrl):
    """Numeric input control: free typing, blur-time validation, locale-aware.

    Constructor params:
        value: initial float value (default 0.0)
        decimal_places: None = floating (preserve user precision, strip
            trailing zeros), int = fixed (always format to N places)
        decimal_char: override for locale decimal; fallback chain:
            explicit param -> configured pref -> locale -> "."

    On blur: parse text as float. If valid, format and fire
    EVT_VALUE_CHANGED. If invalid, revert display to _lastSetValue
    (the domain value) without firing EVT_VALUE_CHANGED.

    API:
        GetValue() -> Python float (always period decimal internally)
        SetValue(float) -> formats with locale decimal for display,
            fires EVT_VALUE_CHANGED
    """

    def __init__(self, parent, value=0.0, decimal_places=None,
                 decimal_char=None, **kwargs):
        self._decimalPlaces = decimal_places
        self._decimalChar = decimal_char or _get_configured_decimal_char()
        self._lastSetValue = float(value)
        super().__init__(
            parent,
            style=wx.TE_RIGHT | wx.TE_PROCESS_TAB,
            **kwargs,
        )
        # Set initial display text without firing EVT_VALUE_CHANGED
        super().SetValue(self._format(self._lastSetValue))
        self.Bind(wx.EVT_KILL_FOCUS, self._onKillFocus)

    def GetValue(self):
        """Return the current value as a Python float (period decimal)."""
        text = super().GetValue().strip()
        if not text:
            return 0.0
        text = text.replace(self._decimalChar, ".")
        try:
            return float(text)
        except ValueError:
            return self._lastSetValue

    def SetValue(self, value):
        """Set the control to display a formatted float value.

        Updates _lastSetValue and fires EVT_VALUE_CHANGED.
        """
        if isinstance(value, (int, float)):
            self._lastSetValue = float(value)
        else:
            try:
                self._lastSetValue = float(value)
            except (ValueError, TypeError):
                self._lastSetValue = 0.0
        super().SetValue(self._format(self._lastSetValue))
        self._fireValueChanged()

    def _format(self, value):
        """Format a float for display using locale decimal char."""
        if self._decimalPlaces is not None:
            formatted = "%.*f" % (self._decimalPlaces, value)
        else:
            formatted = "%g" % value
        if self._decimalChar != ".":
            formatted = formatted.replace(".", self._decimalChar)
        return formatted

    def _onKillFocus(self, event):
        """Validate on blur: format if valid, revert if invalid."""
        event.Skip()
        if not self.IsEnabled():
            return
        text = super().GetValue().strip()
        if not text:
            parsed = 0.0
        else:
            normalized = text.replace(self._decimalChar, ".")
            try:
                parsed = float(normalized)
            except ValueError:
                # Invalid input: revert to domain value, no event
                super().SetValue(self._format(self._lastSetValue))
                return
        # Valid input: format and fire
        self._lastSetValue = parsed
        super().SetValue(self._format(parsed))
        self._fireValueChanged()

    def _fireValueChanged(self):
        """Fire EVT_VALUE_CHANGED to notify AttributeSync."""
        event = ValueChangedEvent(self)
        self.GetEventHandler().ProcessEvent(event)
