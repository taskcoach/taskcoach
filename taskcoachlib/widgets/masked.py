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

from taskcoachlib import operating_system
from wx.lib import masked
import wx
import locale


class FixOverwriteSelectionMixin(object):
    def _SetSelection(self, start, end):
        if operating_system.isGTK():  # pragma: no cover
            # By exchanging the start and end parameters we make sure that the
            # cursor is at the start of the field so that typing overwrites the
            # current field instead of moving to the next field:
            start, end = end, start
        super()._SetSelection(start, end)

    def _OnKeyDown(self, event):
        # Allow Ctrl+Tab keyboard navigation in notebook.
        # Just skipping the event does not work; propagate it all the way up...
        # Note: Only handle Ctrl+Tab, not Shift+Tab (which is normal reverse navigation)
        if (
            event.GetKeyCode() == wx.WXK_TAB
            and event.ControlDown()
            and hasattr(self.GetParent(), "NavigateBook")
        ):
            if self.GetParent().NavigateBook(event):
                return
        super()._OnKeyDown(event)


class TextCtrl(FixOverwriteSelectionMixin, masked.TextCtrl):
    pass


class AmountCtrl(FixOverwriteSelectionMixin, masked.NumCtrl):
    def __init__(self, parent, value=0, locale_conventions=None):
        locale_conventions = locale_conventions or locale.localeconv()
        decimalChar = locale_conventions["decimal_point"] or "."
        groupChar = locale_conventions["thousands_sep"] or ","
        groupDigits = len(locale_conventions["grouping"]) > 1
        # The thousands separator may come up as ISO-8859-1 character
        # 0xa0, which looks like a space but isn't ASCII, which
        # confuses NumCtrl... Play it safe and avoid any non-ASCII
        # character here, or groupChars that consist of multiple characters.
        if len(groupChar) > 1 or ord(groupChar) >= 128:
            groupChar = ","
        # Prevent decimalChar and groupChar from being the same:
        if groupChar == decimalChar:
            groupChar = "." if decimalChar == "," else ","
        super().__init__(
            parent,
            value=value,
            allowNegative=False,
            fractionWidth=2,
            selectOnEntry=True,
            decimalChar=decimalChar,
            groupChar=groupChar,
            groupDigits=groupDigits,
        )


class TimeDeltaCtrl(TextCtrl):
    """Masked edit control for entering or displaying time deltas of the
    form <hour>:<minute>:<second>. Entering negative time deltas is not
    allowed, displaying negative time deltas is allowed if the control
    is read only."""

    def __init__(
        self,
        parent,
        hours,
        minutes,
        seconds,
        readonly=False,
        negative_value=False,
        *args,
        **kwargs
    ):
        # If the control is read only (meaning it could potentially have to
        # show negative values) or if the value is actually negative, allow
        # the minus sign in the mask. Otherwise only allow for numbers.
        mask = "X{9}:##:##" if negative_value or readonly else "#{9}:##:##"
        hours = self.__hour_string(hours, negative_value)
        super().__init__(
            parent,
            mask=mask,
            formatcodes="FS",
            fields=[
                masked.Field(formatcodes="Rr", defaultValue=hours),
                masked.Field(defaultValue="%02d" % minutes),
                masked.Field(defaultValue="%02d" % seconds),
            ],
            *args,
            **kwargs
        )

    def set_value(self, hours, minutes, seconds, negative_value=False):
        hours = self.__hour_string(hours, negative_value)
        self.SetCtrlParameters(
            formatcodes="FS",
            fields=[
                masked.Field(formatcodes="Rr", defaultValue=hours),
                masked.Field(defaultValue="%02d" % minutes),
                masked.Field(defaultValue="%02d" % seconds),
            ],
        )
        self.Refresh()

    @staticmethod
    def __hour_string(hours, negative_value):
        """If the value is negative (e.g. over budget), place a minus sign
        before the hours number and make sure the field has the appropriate
        width."""
        return (
            "%9s" % ("-" + "%d" % hours) if negative_value else "%9d" % hours
        )
