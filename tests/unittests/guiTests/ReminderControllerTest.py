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

import test, wx, time
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

    def testSetTaskReminderSchedulesJob(self):
        self.task.setReminder(self.reminderDateTime)
        self.assertTrue(date.Scheduler().get_jobs())

    @test.skipOnTwistedVersions("12.")
    def testAfterReminderJobIsRemovedFromScheduler(self):
        self.task.setReminder(date.Now() + date.TimeDelta(seconds=1))
        self.assertTrue(date.Scheduler().get_jobs())
        # Process wx events instead of reactor.iterate()
        # NOTE (Twisted Removal - 2024): Using wx event processing
        t0 = time.time()
        while time.time() - t0 < 1.1:
            wx.GetApp().Yield(True)
            time.sleep(0.05)
        self.assertFalse(date.Scheduler().get_jobs())

    def testAddTaskWithReminderSchedulesJob(self):
        taskWithReminder = task.Task(
            "Task with reminder", reminder=self.reminderDateTime
        )
        self.taskList.append(taskWithReminder)
        self.assertTrue(date.Scheduler().get_jobs())

    def testRemoveTaskWithReminderRemovesClockEventFromPublisher(self):
        self.task.setReminder(self.reminderDateTime)
        job = date.Scheduler().get_jobs()[0]
        self.taskList.remove(self.task)
        self.assertFalse(job in date.Scheduler().get_jobs())

    def testChangeReminderRemovesOldReminder(self):
        self.task.setReminder(self.reminderDateTime)
        job = date.Scheduler().get_jobs()[0]
        self.task.setReminder(self.reminderDateTime + date.ONE_HOUR)
        jobs = date.Scheduler().get_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertFalse(job is jobs[0])

    def testMarkTaskCompletedRemovesReminder(self):
        self.task.setReminder(self.reminderDateTime)
        self.assertTrue(date.Scheduler().get_jobs())
        self.task.setCompletionDateTime(date.Now())
        self.assertFalse(date.Scheduler().get_jobs())

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
