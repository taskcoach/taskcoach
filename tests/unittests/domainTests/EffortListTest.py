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
from taskcoachlib import patterns, config
from taskcoachlib.domain import task, effort, date


class EffortListTest(test.TestCase):
    def setUp(self):
        self.events = []
        task.Task.settings = config.Settings(load=False)
        self.task = task.Task()
        self.taskList = task.TaskList()
        self.effortList = effort.EffortList(self.taskList)
        self.taskList.append(self.task)
        patterns.Publisher().registerObserver(
            self.onEvent,
            eventType=self.effortList.addItemEventType(),
            eventSource=self.effortList,
        )
        patterns.Publisher().registerObserver(
            self.onEvent,
            eventType=self.effortList.removeItemEventType(),
            eventSource=self.effortList,
        )
        self.effort = effort.Effort(
            self.task, date.DateTime(2004, 1, 1), date.DateTime(2004, 1, 2)
        )

    def testCreate(self):
        self.assertEqual(0, len(self.effortList))

    def onEvent(self, event):
        self.events.append(event)

    def testNotificationAfterAppend(self):
        self.task.addEffort(self.effort)
        self.assertEqual(self.effort, self.events[0].value())

    def testAppend(self):
        self.task.addEffort(self.effort)
        self.assertEqual(1, len(self.effortList))
        self.assertTrue(self.effort in self.effortList)

    def testNotificationAfterRemove(self):
        self.task.addEffort(self.effort)
        self.task.removeEffort(self.effort)
        self.assertEqual(self.effort, self.events[0].value())

    def testRemove(self):
        self.task.addEffort(self.effort)
        self.task.removeEffort(self.effort)
        self.assertEqual(0, len(self.effortList))

    def testAppendTaskWithEffort(self):
        newTask = task.Task()
        newTask.addEffort(effort.Effort(newTask))
        self.taskList.append(newTask)
        self.assertEqual(1, len(self.effortList))

    def testCreateWhenTaskListIsFilled(self):
        self.task.addEffort(self.effort)
        effortList = effort.EffortList(task.TaskList([self.task]))
        self.assertEqual(1, len(effortList))

    def testAddEffortToChild(self):
        child = task.Task(parent=self.task)
        self.taskList.append(child)
        child.addEffort(effort.Effort(child))
        self.assertEqual(1, len(self.effortList))

    def testMaxDateTime(self):
        self.assertEqual(None, self.effortList.maxDateTime())

    def testMaxDateTime_OneEffort(self):
        self.task.addEffort(self.effort)
        self.assertEqual(self.effort.getStop(), self.effortList.maxDateTime())

    def testMaxDateTime_OneTrackingEffort(self):
        self.task.addEffort(effort.Effort(self.task))
        self.assertEqual(None, self.effortList.maxDateTime())

    def testMaxDateTime_TwoEfforts(self):
        self.task.addEffort(self.effort)
        now = date.DateTime.now()
        self.task.addEffort(effort.Effort(self.task, None, now))
        self.assertEqual(now, self.effortList.maxDateTime())

    def testNrTracking(self):
        self.assertEqual(0, self.effortList.nr_being_tracked())

    def testOriginalLength(self):
        self.assertEqual(0, self.effortList.original_length())

    def testRemoveItems(self):
        self.task.addEffort(self.effort)
        self.effortList.removeItems([self.effort])
        self.assertEqual(0, len(self.effortList))
        self.assertEqual(0, len(self.task.efforts()))

    def testRemoveAllItems(self):
        self.task.addEffort(self.effort)
        effort2 = effort.Effort(
            self.task, date.DateTime(2005, 1, 1), date.DateTime(2005, 1, 2)
        )
        self.task.addEffort(effort2)
        self.effortList.removeItems([effort2, self.effort])
        self.assertEqual(0, len(self.effortList))
        self.assertEqual(0, len(self.task.efforts()))

    def testExtend(self):
        self.effortList.extend([self.effort])
        self.assertEqual(1, len(self.effortList))
        self.assertTrue(self.effort in self.effortList)
        self.assertEqual(1, len(self.task.efforts()))
        self.assertEqual(self.effort, self.task.efforts()[0])

    def testRemoveTaskWithEffort(self):
        self.task.addEffort(self.effort)
        anotherTask = task.Task("Another task without effort")
        self.taskList.append(anotherTask)
        self.assertEqual(1, len(self.effortList))
        self.taskList.remove(self.task)
        self.assertEqual(0, len(self.effortList))

    def testRemoveTaskWithoutEffort(self):
        self.task.addEffort(self.effort)
        anotherTask = task.Task("Another task without effort")
        self.taskList.append(anotherTask)
        self.assertEqual(1, len(self.effortList))
        self.taskList.remove(anotherTask)
        self.assertEqual(1, len(self.effortList))

    def testChangeTask(self):
        self.task.addEffort(self.effort)
        anotherTask = task.Task("Another task without effort")
        self.taskList.append(anotherTask)
        self.assertEqual(1, len(self.effortList))
        self.effort.setTask(anotherTask)
        self.assertEqual(1, len(self.effortList))
