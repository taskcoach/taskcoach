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

MasterScheduler checks each task's reminder every second and sends
'task.reminder.trigger', which ReminderController handles. See
docs/REMINDERS.md.
"""

import test
import wx
from taskcoachlib import gui, config, patterns, persistence
from taskcoachlib.domain import task, date, effort


class ReminderControllerUnderTest(gui.remindercontroller.ReminderController):
    def __init__(self, *args, **kwargs):
        self.messages = []
        self.userAttentionRequested = False
        super().__init__(*args, **kwargs)

    def showReminderMessage(self, message):  # pylint: disable=W0221
        class DummyDialog(object):
            def __init__(self, *args, **kwargs):
                pass

            def Bind(self, *args, **kwargs):
                pass

            def GetSize(self):
                return wx.Size(100, 100)

            def SetPosition(self, position):
                pass

            def Show(self):
                pass

        super().showReminderMessage(message, DummyDialog)
        self.messages.append(message)

    def requestUserAttention(self):
        self.userAttentionRequested = True


class DummyWindow(wx.Frame):
    def __init__(self):
        super().__init__(None)
        self.taskFile = persistence.TaskFile()


class ReminderControllerTestCase(test.TestCase):
    def setUp(self):
        settings = config.settings.current()
        self.taskList = task.TaskList()
        self.effortList = effort.EffortList(self.taskList)
        self.dummyWindow = DummyWindow()
        self.reminderController = ReminderControllerUnderTest(
            self.dummyWindow, self.taskList, self.effortList, settings
        )
        self.nowDateTime = date.DateTime.now()
        self.reminderDateTime = self.nowDateTime + date.ONE_HOUR

    def tearDown(self):
        super().tearDown()
        self.dummyWindow.taskFile.close()
        self.dummyWindow.taskFile.stop()


class ReminderControllerTest(ReminderControllerTestCase):
    def setUp(self):
        super().setUp()
        self.task = task.Task("Task")
        self.taskList.append(self.task)

    def test_due_reminder_is_shown(self):
        self.task.set_reminder(date.Now())
        self.task.processReminder(date.Now())
        self.assertEqual([self.task], self.reminderController.messages)

    def test_future_reminder_is_not_shown(self):
        self.task.set_reminder(date.Now() + date.ONE_HOUR)
        self.task.processReminder(date.Now())
        self.assertEqual([], self.reminderController.messages)

    def test_no_reminder_is_shown_after_shutdown(self):
        self.reminderController.shutdown()
        self.task.triggerReminder()
        self.assertEqual([], self.reminderController.messages)

    def dummyCloseEvent(self, snoozeTimeDelta=None, openAfterClose=False):
        class DummySnoozeOptions(object):
            Selection = 0

            def GetClientData(self, *args):  # pylint: disable=W0613
                return snoozeTimeDelta

        class DummyDialog(object):
            task = self.task
            openTaskAfterClose = openAfterClose
            ignoreSnoozeOption = False
            snoozeOptions = DummySnoozeOptions()

            def Destroy(self):
                pass

        class DummyEvent(object):
            EventObject = DummyDialog()

            def Skip(self):
                pass

        return DummyEvent()

    def testOnCloseReminderResetsReminder(self):
        self.task.set_reminder(self.reminderDateTime)
        self.reminderController.on_close_reminder_dialog(
            self.dummyCloseEvent(), show=False
        )
        self.assertEqual(date.DateTime(), self.task.reminder())

    def testOnCloseReminderSetsReminder(self):
        self.task.set_reminder(self.reminderDateTime)
        self.reminderController.on_close_reminder_dialog(
            self.dummyCloseEvent(date.ONE_HOUR), show=False
        )
        self.assertTrue(
            abs(self.nowDateTime + date.ONE_HOUR - self.task.reminder())
            < date.TimeDelta(seconds=5)
        )

    def test_snoozing_is_an_undo_step(self):
        # Every change to the file is (docs/UNDO_REDO.md, Design Intent)
        self.task.set_reminder(self.reminderDateTime)
        self.reminderController.on_close_reminder_dialog(
            self.dummyCloseEvent(date.ONE_HOUR), show=False
        )
        patterns.CommandHistory().undo()
        self.assertEqual(self.reminderDateTime, self.task.reminder())

    def testOnCloseMayOpenTask(self):
        self.task.set_reminder(self.reminderDateTime)
        frame = self.reminderController.on_close_reminder_dialog(
            self.dummyCloseEvent(openAfterClose=True), show=False
        )
        self.assertTrue(frame)
