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

from unittest import mock

import test
import wx
from wx import siplib
from taskcoachlib import widgets
from taskcoachlib.gui.dialog import version
from taskcoachlib.help import tips
from taskcoachlib.tools import wxhelper
from taskcoachlib.widgets import iconpicker

# What wxGTK's deferred first show leaves before the window is mapped
# (docs/WINDOW_GEOMETRY.md, First Show on wxGTK): needing a window
# manager, it is made here by hand
_LOST_POSITION = wx.Point(1, 22)
_TITLE_BAR = 27


def defer_first_show(window):
    """The position lost, the title bar taken from the contents."""
    width, height = window.GetClientSize()
    window.SetPosition(_LOST_POSITION)
    window.SetClientSize(width, height - _TITLE_BAR)


def show(window):
    """The first show's event, as wx sends it."""
    event = wx.ShowEvent(window.GetId(), True)
    event.SetEventObject(window)
    window.GetEventHandler().ProcessEvent(event)


class KeepPlacementAtFirstShowTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.dialog = wx.Dialog(self.frame, title="Dialog")
        sizer = wx.BoxSizer()
        sizer.Add(wx.Panel(self.dialog, size=(300, 200)))
        self.dialog.SetSizer(sizer)
        self.dialog.Fit()
        self.dialog.SetPosition(wx.Point(100, 120))

    def tearDown(self):
        self.dialog.Destroy()
        super().tearDown()

    def test_a_lost_position_is_set_again(self):
        wxhelper.keep_placement_at_first_show(self.dialog)
        defer_first_show(self.dialog)
        show(self.dialog)
        self.assertEqual(wx.Point(100, 120), self.dialog.GetPosition())

    def test_a_fitted_window_gets_its_contents_size_back(self):
        fitted = self.dialog.GetClientSize()
        wxhelper.keep_placement_at_first_show(self.dialog)
        defer_first_show(self.dialog)
        show(self.dialog)
        self.assertEqual(fitted, self.dialog.GetClientSize())

    def test_a_window_given_its_size_keeps_the_size_it_has(self):
        self.dialog.SetSize(600, 700)
        wxhelper.keep_placement_at_first_show(self.dialog)
        defer_first_show(self.dialog)
        deferred = self.dialog.GetSize()
        show(self.dialog)
        self.assertEqual(deferred, self.dialog.GetSize())

    def test_the_last_placement_is_kept(self):
        wxhelper.keep_placement_at_first_show(self.dialog)
        self.dialog.SetPosition(wx.Point(200, 220))
        wxhelper.keep_placement_at_first_show(self.dialog)
        defer_first_show(self.dialog)
        show(self.dialog)
        self.assertEqual(wx.Point(200, 220), self.dialog.GetPosition())

    def test_only_the_first_show(self):
        # Later shows keep where the user moved the window
        wxhelper.keep_placement_at_first_show(self.dialog)
        show(self.dialog)
        self.dialog.SetPosition(wx.Point(300, 320))
        show(self.dialog)
        self.assertEqual(wx.Point(300, 320), self.dialog.GetPosition())

    def test_centred_on_its_parent(self):
        wxhelper.centre_on_parent(self.dialog)
        centred = self.dialog.GetPosition()
        defer_first_show(self.dialog)
        show(self.dialog)
        self.assertEqual(centred, self.dialog.GetPosition())


class MostOfTheScreenTest(test.wxTestCase):
    """A window opens at most 80% of its monitor's work area each way,
    its contents scrolling (docs/WINDOW_GEOMETRY.md, Decisions 10)."""

    area = (0, 0, 800, 600)  # 80%: 640x480

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(
            wxhelper, "work_area_of", return_value=self.area
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def dialog(self, size):
        dialog = wx.Dialog(self.frame, title="Dialog", size=size)
        return dialog

    def test_each_way_on_its_own(self):
        self.assertEqual((640, 300), wxhelper.most_of((700, 300), self.area))

    def test_a_larger_dialog_is_cut(self):
        dialog = self.dialog((700, 550))
        wxhelper.centre_on_parent(dialog)
        self.assertEqual((640, 480), tuple(dialog.GetSize()))

    def test_a_smaller_dialog_keeps_its_size(self):
        dialog = self.dialog((600, 400))
        wxhelper.centre_on_parent(dialog)
        self.assertEqual((600, 400), tuple(dialog.GetSize()))

    def test_help_about_and_license(self):
        dialog = widgets.HTMLDialog("Title", "<p>Text</p>", parent=self.frame)
        self.assertEqual((640, 480), tuple(dialog.GetSize()))

    def test_the_icon_picker_opens_as_tall_as_a_window_may(self):
        dialog = iconpicker._IconDialog(self.frame, None)
        self.assertEqual((640, 480), tuple(dialog._desired_size))


class DialogsKeepTheirPlacementTest(test.wxTestCase):
    def assert_keeps_its_placement(self, dialog):
        placed = dialog.GetPosition(), dialog.GetClientSize()
        defer_first_show(dialog)
        show(dialog)
        self.assertEqual(
            placed, (dialog.GetPosition(), dialog.GetClientSize())
        )

    def test_tip_of_the_day(self):
        dialog = tips.TipDialog(self.frame, tip_provider=tips.TipProvider(0))
        self.assert_keeps_its_placement(dialog)
        dialog.Destroy()

    def test_new_version(self):
        dialog = version.NewVersionDialog(
            self.frame, version="0.0", message=""
        )
        self.assert_keeps_its_placement(dialog)
        dialog.Destroy()


class ClosedDialogsAreDestroyedTest(test.wxTestCase):
    def test_tip_of_the_day(self):
        dialog = tips.TipDialog(self.frame, tip_provider=tips.TipProvider(0))
        dialog.Show()
        dialog.Close()
        test.settle()
        self.assertTrue(siplib.isdeleted(dialog))

    def test_new_version(self):
        dialog = version.NewVersionDialog(
            self.frame, version="0.0", message=""
        )
        dialog.Show()
        dialog.Close()
        test.settle()
        self.assertTrue(siplib.isdeleted(dialog))


class CentreOnAppMonitorTest(test.wxTestCase):
    """A reminder on the monitor the system reports for the main
    window, as editors and dialogs (docs/WINDOW_GEOMETRY.md,
    Decisions 8)."""

    def test_the_monitor_is_the_systems_for_the_main_window(self):
        dialog = wx.Dialog(self.frame, title="Reminder", size=(200, 100))
        main = wx.GetApp().GetTopWindow()
        with mock.patch.object(
            main, "IsShown", return_value=True
        ), mock.patch.object(
            wx.Display, "GetFromWindow", return_value=0
        ) as from_window:
            wxhelper.centre_on_app_monitor(dialog)
        from_window.assert_called_once_with(main)
