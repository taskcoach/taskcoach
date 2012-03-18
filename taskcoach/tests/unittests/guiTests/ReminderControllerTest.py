'''
Task Coach - Your friendly task manager
Copyright (C) 2004-2012 Task Coach developers <developers@taskcoach.org>

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
'''

import test, wx
from taskcoachlib import gui, config, persistence
from taskcoachlib.domain import task, date, effort


class ReminderControllerUnderTest(gui.ReminderController):
    def __init__(self, *args, **kwargs):
        self.messages = []
        self.userAttentionRequested = False
        super(ReminderControllerUnderTest, self).__init__(*args, **kwargs)
        
    def showReminderMessage(self, message): # pylint: disable-msg=W0221
        class DummyDialog(object):
            def __init__(self, *args, **kwargs):
                pass
            def Bind(self, *args, **kwargs):
                pass
            def Show(self):
                pass
        super(ReminderControllerUnderTest, self).showReminderMessage(message, DummyDialog)
        self.messages.append(message)
    
    def requestUserAttention(self):
        self.userAttentionRequested = True

        
class DummyWindow(wx.Frame):
    def __init__(self):
        super(DummyWindow, self).__init__(None)
        self.taskFile = persistence.TaskFile()
    

class ReminderControllerTestCase(test.TestCase):
    def setUp(self):
        task.Task.settings = settings = config.Settings(load=False)
        self.taskList = task.TaskList()
        self.effortList = effort.EffortList(self.taskList)
        self.reminderController = ReminderControllerUnderTest(DummyWindow(), 
            self.taskList, self.effortList, settings)
        self.nowDateTime = date.DateTime.now()
        self.reminderDateTime = self.nowDateTime + date.TimeDelta(hours=1)
        
    def tearDown(self):
        date.Scheduler().shutdown(False, False)
        date.Scheduler.deleteInstance()
        

class ReminderControllerTest(ReminderControllerTestCase):
    def setUp(self):
        super(ReminderControllerTest, self).setUp()
        self.task = task.Task('Task')
        self.taskList.append(self.task)
        
    def testSetTaskReminderSchedulesJob(self):
        self.task.setReminder(self.reminderDateTime)
        self.failUnless(date.Scheduler().get_jobs())
        
    def testAfterReminderJobIsRemovedFromScheduler(self):
        self.task.setReminder(self.reminderDateTime)
        self.failUnless(date.Scheduler().get_jobs())
        date.Scheduler()._process_jobs(self.reminderDateTime) # pylint: disable-msg=W0212
        self.failIf(date.Scheduler().get_jobs())
        
    def testAddTaskWithReminderSchedulesJob(self):
        taskWithReminder = task.Task('Task with reminder', 
                                     reminder=self.reminderDateTime)
        self.taskList.append(taskWithReminder)
        self.failUnless(date.Scheduler().get_jobs())
                
    def testRemoveTaskWithReminderRemovesClockEventFromPublisher(self):
        self.task.setReminder(self.reminderDateTime)
        self.taskList.remove(self.task)
        self.assertRaises(KeyError, date.Scheduler().unschedule(self.reminderController.onReminder))
                
    def testChangeReminderRemovesOldReminder(self):
        self.task.setReminder(self.reminderDateTime)
        self.task.setReminder(self.reminderDateTime + date.TimeDelta(hours=1))
        self.assertRaises(KeyError, date.Scheduler().unschedule(self.reminderController.onReminder))
        
    def testMarkTaskCompletedRemovesReminder(self):
        self.task.setReminder(self.reminderDateTime)
        self.failUnless(date.Scheduler().get_jobs())
        self.task.setCompletionDateTime(date.Now())
        self.assertRaises(KeyError, date.Scheduler().unschedule(self.reminderController.onReminder))
        
    def dummyCloseEvent(self, snoozeTimeDelta=None, openAfterClose=False):
        class DummySnoozeOptions(object):
            Selection = 0
            def GetClientData(self, *args): # pylint: disable-msg=W0613
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
        self.reminderController.onCloseReminderDialog(self.dummyCloseEvent(), 
                                                     show=False)
        self.assertEqual(None, self.task.reminder())

    def testOnCloseReminderSetsReminder(self):
        self.task.setReminder(self.reminderDateTime)
        oneHour = date.TimeDelta(hours=1)
        self.reminderController.onCloseReminderDialog(\
            self.dummyCloseEvent(oneHour), show=False)
        self.failUnless(abs(self.nowDateTime + oneHour - self.task.reminder()) \
                        < date.TimeDelta(seconds=5))

    def testOnCloseMayOpenTask(self):
        self.task.setReminder(self.reminderDateTime)
        frame = self.reminderController.onCloseReminderDialog(\
            self.dummyCloseEvent(openAfterClose=True), show=False)
        self.failUnless(frame)
        
    def testOnWakeDoesNotRequestUserAttentionWhenThereAreNoReminders(self):
        self.reminderController.onWake(None)
        self.failIf(self.reminderController.userAttentionRequested)
