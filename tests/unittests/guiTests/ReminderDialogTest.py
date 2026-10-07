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

import test
import wx
from unittest import mock
from taskcoachlib.gui import dialog
from taskcoachlib.domain import task, effort
from taskcoachlib.config import settings


class DummyEvent(object):
    def Skip(self):
        pass


class ReminderDialogTest(test.TestCase):
    def setUp(self):
        self.aTask = task.Task("subject")
        self.taskList = task.TaskList([self.aTask])
        self.effortList = effort.EffortList(self.taskList)
        # Without a window manager, asking for attention crashes GTK
        for patcher in (
            mock.patch.object(
                dialog.reminder.ReminderDialog, "RequestUserAttention"
            ),
            mock.patch("taskcoachlib.sounds.play"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        for window in wx.GetTopLevelWindows():
            if isinstance(window, dialog.reminder.ReminderDialog):
                window.Destroy()
        wx.Yield()
        super().tearDown()

    def createReminderDialog(self):
        reminder_dialog = dialog.reminder.ReminderDialog(
            self.aTask, self.taskList, self.effortList, None
        )
        # Past the pause that blocks an accidental close
        reminder_dialog._isFrozen = False
        return reminder_dialog

    def test_remember_zero_snooze_time(self):
        reminder_dialog = self.createReminderDialog()
        reminder_dialog.snoozeOptions.SetSelection(0)
        reminder_dialog.on_close(DummyEvent())
        self.assertEqual(0, settings.get("view", "defaultsnoozetime"))

    def test_remember_snooze_time(self):
        reminder_dialog = self.createReminderDialog()
        reminder_dialog.snoozeOptions.SetSelection(2)
        reminder_dialog.on_close(DummyEvent())
        self.assertEqual(10, settings.get("view", "defaultsnoozetime"))

    def test_use_default_snooze_time(self):
        settings.set("view", "defaultsnoozetime", 15)
        reminder_dialog = self.createReminderDialog()
        self.assertEqual(
            "15 minutes", reminder_dialog.snoozeOptions.GetStringSelection()
        )

    def test_dont_use_default_snooze_time_when_its_not_in_the_list_of_options(
        self,
    ):
        settings.set("view", "defaultsnoozetime", 17)
        reminder_dialog = self.createReminderDialog()
        self.assertEqual(
            "5 minutes", reminder_dialog.snoozeOptions.GetStringSelection()
        )

    def test_remember_reminder_replace_default_snooze_time(self):
        reminder_dialog = self.createReminderDialog()
        reminder_dialog.replaceDefaultSnoozeTime.SetValue(False)
        reminder_dialog.on_close(DummyEvent())
        self.assertEqual(
            False, settings.get("view", "replacedefaultsnoozetime")
        )

    def test_use_reminder_replace_default_snooze_time(self):
        settings.set("view", "replacedefaultsnoozetime", False)
        reminder_dialog = self.createReminderDialog()
        self.assertEqual(
            False, reminder_dialog.replaceDefaultSnoozeTime.GetValue()
        )
