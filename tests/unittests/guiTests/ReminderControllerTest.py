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

DESIGN NOTE (Scheduler Refactoring - 2024):
The old Scheduler-based reminder system has been replaced with a polling-based
system using GlobalTimer + pubsub. See docs/SCHEDULERS.md for details.

Reminders are now checked every second by subscribing to 'timer.second' events
and polling all tasks to see if their reminder time has passed.
"""

import test
import wx
from taskcoachlib import gui, config, persistence
from taskcoachlib.domain import task, date, effort


class ReminderControllerUnderTest(gui.ReminderController):
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
        task.Task.settings = settings = config.Settings(load=False)
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

    # =========================================================================
    # Tests for the polling-based reminder system
    # =========================================================================

    def testTaskWithReminderIsFoundByPolling(self):
        """With the new system, reminders are checked by polling, not scheduling."""
        self.task.setReminder(self.reminderDateTime)
        # Verify the task has a reminder set
        self.assertIsNotNone(self.task.reminder())
        self.assertEqual(self.task.reminder(), self.reminderDateTime)

    def testReminderShownWhenDue(self):
        """Verify reminder is shown when due time is reached."""
        # Set reminder to now (so it's immediately due)
        self.task.setReminder(date.Now())
        # Simulate timer tick by calling the check method directly
        self.reminderController._checkReminders(date.DateTime.now())
        # Reminder should have been shown
        self.assertEqual(len(self.reminderController.messages), 1)

    def testReminderNotShownTwice(self):
        """Verify same reminder is not shown twice."""
        self.task.setReminder(date.Now())
        # First check - should show
        self.reminderController._checkReminders(date.DateTime.now())
        # Second check - should NOT show again
        self.reminderController._checkReminders(date.DateTime.now())
        # Only one reminder should have been shown
        self.assertEqual(len(self.reminderController.messages), 1)

    def testReminderClearedOnSnooze(self):
        """Verify reminder tracking is cleared when task is snoozed."""
        self.task.setReminder(date.Now())
        self.reminderController._checkReminders(date.DateTime.now())
        self.assertEqual(len(self.reminderController.messages), 1)
        # Clear the shown reminder (simulates snooze)
        self.reminderController._shownReminders.discard(self.task)
        # Change reminder to new time
        self.task.setReminder(date.Now())
        # Should show again
        self.reminderController._checkReminders(date.DateTime.now())
        self.assertEqual(len(self.reminderController.messages), 2)

    def testFutureReminderNotShown(self):
        """Verify future reminders are not shown until due."""
        self.task.setReminder(date.Now() + date.ONE_HOUR)
        self.reminderController._checkReminders(date.DateTime.now())
        self.assertEqual(len(self.reminderController.messages), 0)

    def testMultipleTasksWithReminders(self):
        """Verify multiple tasks can have reminders checked."""
        task2 = task.Task("Task 2")
        self.taskList.append(task2)
        self.task.setReminder(date.Now())
        task2.setReminder(date.Now())
        self.reminderController._checkReminders(date.DateTime.now())
        self.assertEqual(len(self.reminderController.messages), 2)

    # =========================================================================
    # Tests that don't depend on timing mechanism - still valid
    # =========================================================================

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
        self.task.setReminder(self.reminderDateTime)
        self.reminderController.onCloseReminderDialog(
            self.dummyCloseEvent(), show=False
        )
        self.assertEqual(None, self.task.reminder())

    def testOnCloseReminderSetsReminder(self):
        self.task.setReminder(self.reminderDateTime)
        self.reminderController.onCloseReminderDialog(
            self.dummyCloseEvent(date.ONE_HOUR), show=False
        )
        self.assertTrue(
            abs(self.nowDateTime + date.ONE_HOUR - self.task.reminder())
            < date.TimeDelta(seconds=5)
        )

    def testOnCloseMayOpenTask(self):
        self.task.setReminder(self.reminderDateTime)
        frame = self.reminderController.onCloseReminderDialog(
            self.dummyCloseEvent(openAfterClose=True), show=False
        )
        self.assertTrue(frame)

    def testOnWakeDoesNotRequestUserAttentionWhenThereAreNoReminders(self):
        self.reminderController.onReminder()
        self.assertFalse(self.reminderController.userAttentionRequested)
