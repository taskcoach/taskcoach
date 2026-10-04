"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2026 Task Coach developers <developers@taskcoach.org>

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

from unittest import mock

import test
import wx
from taskcoachlib.config import settings
from taskcoachlib.widgets import (
    CalendarConfigDialog,
    HierarchicalCalendarConfigDialog,
)


class ConfigDialogTestCase(test.wxTestCase):
    """The calendar views' settings dialogs read and write their
    view's section of the one Settings object."""

    def make(self, dialog_class, section):
        # The harness destroys the frame's children after each test
        return dialog_class(section, self.frame)

    @staticmethod
    def press_ok(dialog):
        # Not shown modally in the test
        with mock.patch.object(dialog, "EndModal"):
            dialog.ok()


class CalendarConfigTest(ConfigDialogTestCase):
    def test_shows_the_views_settings(self):
        settings.calendarviewer.periodcount = 3
        settings.calendarviewer.shownow = False
        dialog = self.make(CalendarConfigDialog, "calendarviewer")
        self.assertEqual(
            (3, False),
            (dialog._spanCount.GetValue(), dialog._shownow.GetValue()),
        )

    def test_writes_the_chosen_ones(self):
        dialog = self.make(CalendarConfigDialog, "calendarviewer")
        dialog._spanCount.SetValue(2)
        dialog._spanType.SetSelection(1)  # Weeks
        dialog._display.SetSelection(4)  # All tasks
        dialog._shownow.SetValue(False)
        dialog._highlight.SetColour(wx.Colour(10, 20, 30))
        self.press_ok(dialog)
        options = settings.calendarviewer
        self.assertEqual(
            (2, 2, True, True, True, False, "10,20,30"),
            (
                options.periodcount,
                options.viewtype,
                options.shownostart,
                options.shownodue,
                options.showunplanned,
                options.shownow,
                options.highlightcolor,
            ),
        )


class HierarchicalCalendarConfigTest(ConfigDialogTestCase):
    def test_shows_the_views_settings(self):
        settings.hierarchicalcalendarviewer.headerformat = 2
        dialog = self.make(
            HierarchicalCalendarConfigDialog, "hierarchicalcalendarviewer"
        )
        self.assertEqual(
            (False, True),
            (dialog._weekNumber.GetValue(), dialog._dates.GetValue()),
        )

    def test_writes_the_chosen_ones(self):
        dialog = self.make(
            HierarchicalCalendarConfigDialog, "hierarchicalcalendarviewer"
        )
        dialog._spanType.SetSelection(2)  # Month
        dialog._shownow.SetValue(False)
        dialog._weekNumber.SetValue(True)
        dialog._dates.SetValue(True)
        dialog._highlight.SetColour(wx.Colour(1, 2, 3))
        self.press_ok(dialog)
        options = settings.hierarchicalcalendarviewer
        self.assertEqual(
            (2, False, 3, "1,2,3"),
            (
                options.calendarformat,
                options.drawnow,
                options.headerformat,
                options.todaycolor,
            ),
        )
