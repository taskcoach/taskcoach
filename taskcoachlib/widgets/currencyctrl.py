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


class CurrencyValidator(wx.Validator):
    """Validator that restricts input to valid currency characters:
    digits, a single locale-aware decimal point, and navigation keys."""

    def __init__(self, decimal_char=None):
        super().__init__()
        self._decimalChar = decimal_char or locale.localeconv().get("decimal_point", ".")
        if not self._decimalChar:
            self._decimalChar = "."
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def Clone(self):
        return CurrencyValidator(self._decimalChar)

    def Validate(self, parent):
        return True

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

    def OnChar(self, event):
        keycode = event.GetKeyCode()

        # Always allow navigation/control keys
        if keycode < wx.WXK_SPACE or keycode == wx.WXK_DELETE:
            event.Skip()
            return
        if keycode in (wx.WXK_RETURN, wx.WXK_TAB, wx.WXK_BACK,
                       wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_HOME, wx.WXK_END):
            event.Skip()
            return
        # Allow Ctrl+key combos (copy, paste, select all, etc.)
        if event.ControlDown() or event.CmdDown():
            event.Skip()
            return

        char = chr(keycode) if keycode < 256 else None

        if char is None:
            event.Skip()
            return

        # Allow digits
        if char.isdigit():
            event.Skip()
            return

        # Allow single decimal point
        if char == self._decimalChar:
            ctrl = self.GetWindow()
            if self._decimalChar not in ctrl.GetValue():
                event.Skip()
            return

        # Block everything else (no beep, just silently reject)


class CurrencyCtrl(wx.TextCtrl):
    """Currency input control using wx.TextCtrl + CurrencyValidator.

    Replaces the crash-prone wx.lib.masked.NumCtrl (AmountCtrl).
    Right-aligned, locale-aware decimal point, formats to 2dp on focus loss.
    """

    def __init__(self, parent, value=0.0, **kwargs):
        self._decimalChar = locale.localeconv().get("decimal_point", ".") or "."
        super().__init__(
            parent,
            style=wx.TE_RIGHT | wx.TE_PROCESS_TAB,
            validator=CurrencyValidator(self._decimalChar),
            **kwargs,
        )
        self.SetValue(value)
        self.Bind(wx.EVT_KILL_FOCUS, self._onKillFocus)

    def GetValue(self):
        """Return the current value as a float."""
        text = super().GetValue().strip()
        if not text:
            return 0.0
        # Normalize locale decimal to Python float decimal
        text = text.replace(self._decimalChar, ".")
        try:
            return float(text)
        except ValueError:
            return 0.0

    def SetValue(self, value):
        """Set the control to display a formatted float value."""
        if isinstance(value, (int, float)):
            text = self._format(value)
        else:
            text = str(value)
        super().SetValue(text)

    def _format(self, value):
        """Format a float to 2 decimal places using locale decimal char."""
        formatted = "%.2f" % value
        if self._decimalChar != ".":
            formatted = formatted.replace(".", self._decimalChar)
        return formatted

    def _onKillFocus(self, event):
        """Auto-format to 2 decimal places when focus leaves the control."""
        event.Skip()
        if not self.IsEnabled():
            return
        current = self.GetValue()
        self.SetValue(current)
