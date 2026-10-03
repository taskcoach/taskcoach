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
from taskcoachlib import config
from taskcoachlib.domain import task, effort


class DummyEvent(object):
    def Skip(self):
        pass


class ReminderDialogTest(test.TestCase):
    def setUp(self):
        self.settings = config.settings.current()
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
            self.aTask, self.taskList, self.effortList, self.settings, None
        )
        # Past the pause that blocks an accidental close
        reminder_dialog._isFrozen = False
        return reminder_dialog

    def testRememberZeroSnoozeTime(self):
        reminderDialog = self.createReminderDialog()
        reminderDialog.snoozeOptions.SetSelection(0)
        reminderDialog.on_close(DummyEvent())
        self.assertEqual(0, self.settings.getint("view", "defaultsnoozetime"))

    def testRememberSnoozeTime(self):
        reminderDialog = self.createReminderDialog()
        reminderDialog.snoozeOptions.SetSelection(2)
        reminderDialog.on_close(DummyEvent())
        self.assertEqual(10, self.settings.getint("view", "defaultsnoozetime"))

    def testUseDefaultSnoozeTime(self):
        self.settings.set("view", "defaultsnoozetime", "15")
        reminderDialog = self.createReminderDialog()
        self.assertEqual(
            "15 minutes", reminderDialog.snoozeOptions.GetStringSelection()
        )

    def testDontUseDefaultSnoozeTimeWhenItsNotInTheListOfOptions(self):
        self.settings.set("view", "defaultsnoozetime", "17")
        reminderDialog = self.createReminderDialog()
        self.assertEqual(
            "5 minutes", reminderDialog.snoozeOptions.GetStringSelection()
        )

    def testRememberReminderReplaceDefaultSnoozeTime(self):
        reminderDialog = self.createReminderDialog()
        reminderDialog.replaceDefaultSnoozeTime.SetValue(False)
        reminderDialog.on_close(DummyEvent())
        self.assertEqual(
            False, self.settings.getboolean("view", "replacedefaultsnoozetime")
        )

    def testUseReminderReplaceDefaultSnoozeTime(self):
        self.settings.setboolean("view", "replacedefaultsnoozetime", False)
        reminderDialog = self.createReminderDialog()
        self.assertEqual(
            False, reminderDialog.replaceDefaultSnoozeTime.GetValue()
        )
