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
from taskcoachlib.gui import dialog
from taskcoachlib import config
from taskcoachlib.domain import task, effort


class DummyEvent(object):
    def Skip(self):
        pass


class ReminderDialogTest(test.TestCase):
    def setUp(self):
        self.settings = config.Settings(load=False)
        task.Task.settings = self.settings
        self.aTask = task.Task("subject")
        self.taskList = task.TaskList([self.aTask])
        self.effortList = effort.EffortList(self.taskList)

    def createReminderDialog(self):
        return dialog.reminder.ReminderDialog(
            self.aTask, self.taskList, self.effortList, self.settings, None
        )

    @test.skipOnPlatform("__WXGTK__")  # Causes SIGSEGV
    def testRememberZeroSnoozeTime(self):
        reminderDialog = self.createReminderDialog()
        reminderDialog.snoozeOptions.SetSelection(0)
        reminderDialog.on_close(DummyEvent())
        self.assertEqual(0, self.settings.getint("view", "defaultsnoozetime"))

    @test.skipOnPlatform("__WXGTK__")  # Causes SIGSEGV
    def testRememberSnoozeTime(self):
        reminderDialog = self.createReminderDialog()
        reminderDialog.snoozeOptions.SetSelection(2)
        reminderDialog.on_close(DummyEvent())
        self.assertEqual(10, self.settings.getint("view", "defaultsnoozetime"))

    @test.skipOnPlatform("__WXGTK__")  # Causes SIGSEGV
    def testUseDefaultSnoozeTime(self):
        self.settings.set("view", "defaultsnoozetime", "15")
        reminderDialog = self.createReminderDialog()
        self.assertEqual(
            "15 minutes", reminderDialog.snoozeOptions.GetStringSelection()
        )

    @test.skipOnPlatform("__WXGTK__")  # Causes SIGSEGV
    def testDontUseDefaultSnoozeTimeWhenItsNotInTheListOfOptions(self):
        self.settings.set("view", "defaultsnoozetime", "17")
        reminderDialog = self.createReminderDialog()
        self.assertEqual(
            "5 minutes", reminderDialog.snoozeOptions.GetStringSelection()
        )

    @test.skipOnPlatform("__WXGTK__")  # Causes SIGSEGV
    def testRememberReminderReplaceDefaultSnoozeTime(self):
        reminderDialog = self.createReminderDialog()
        reminderDialog.replaceDefaultSnoozeTime.SetValue(False)
        reminderDialog.on_close(DummyEvent())
        self.assertEqual(
            False, self.settings.getboolean("view", "replacedefaultsnoozetime")
        )

    @test.skipOnPlatform("__WXGTK__")  # Causes SIGSEGV
    def testUseReminderReplaceDefaultSnoozeTime(self):
        self.settings.setboolean("view", "replacedefaultsnoozetime", False)
        reminderDialog = self.createReminderDialog()
        self.assertEqual(
            False, reminderDialog.replaceDefaultSnoozeTime.GetValue()
        )
