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
from taskcoachlib import config
from taskcoachlib.domain import task, effort, date


class TaskListTest(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.taskList = task.TaskList()
        year = date.Now().year
        self.task1 = task.Task(dueDateTime=date.DateTime(year + 1, 1, 1))
        self.task2 = task.Task(dueDateTime=date.DateTime(year + 2, 1, 1))
        self.task3 = task.Task()

    def nrStatus(self, status):
        return self.taskList.nr_of_tasks_per_status()[status]

    def testNrOfTasksPerStatusOfAnEmptyTaskList(self):
        counts = self.taskList.nr_of_tasks_per_status()
        for status in task.Task.possibleStatuses():
            self.assertEqual(0, counts[status])

    def testNrCompleted(self):
        self.assertEqual(0, self.nrStatus(task.status.completed))
        self.taskList.append(self.task1)
        self.assertEqual(0, self.nrStatus(task.status.completed))
        self.task1.setCompletionDateTime()
        self.assertEqual(1, self.nrStatus(task.status.completed))

    def testNrOverdue(self):
        self.assertEqual(0, self.nrStatus(task.status.overdue))
        self.taskList.append(self.task1)
        self.assertEqual(0, self.nrStatus(task.status.overdue))
        self.task1.setDueDateTime(date.DateTime(1990, 1, 1))
        self.assertEqual(1, self.nrStatus(task.status.overdue))

    def testNrDueSoon(self):
        self.assertEqual(0, self.nrStatus(task.status.duesoon))
        self.taskList.append(task.Task(dueDateTime=date.Now() + date.ONE_HOUR))
        self.assertEqual(1, self.nrStatus(task.status.duesoon))

    def testNrBeingTracked(self):
        self.assertEqual(0, self.taskList.nr_being_tracked())
        activeTask = task.Task()
        activeTask.addEffort(effort.Effort(activeTask))
        self.taskList.append(activeTask)
        self.assertEqual(1, self.taskList.nr_being_tracked())

    def testOriginalLength(self):
        self.assertEqual(0, self.taskList.original_length())

    def testMinPriority_EmptyTaskList(self):
        self.assertEqual(0, self.taskList.min_priority())

    def testMinPriority_OneTaskWithDefaultPriority(self):
        self.taskList.append(self.task1)
        self.assertEqual(self.task1.priority(), self.taskList.min_priority())

    def testMinPriority_OneTaskWithNonDefaultPriority(self):
        self.taskList.append(task.Task(priority=-5))
        self.assertEqual(-5, self.taskList.min_priority())

    def testMinPriority_TwoTasks(self):
        self.taskList.extend([task.Task(priority=3), task.Task(priority=5)])
        self.assertEqual(3, self.taskList.min_priority())

    def testMaxPriority_EmptyTaskList(self):
        self.assertEqual(0, self.taskList.max_priority())

    def testMaxPriority_OneTaskWithDefaultPriority(self):
        self.taskList.append(self.task1)
        self.assertEqual(self.task1.priority(), self.taskList.max_priority())

    def testMaxPriority_OneTaskWithNonDefaultPriority(self):
        self.taskList.append(task.Task(priority=-5))
        self.assertEqual(-5, self.taskList.max_priority())

    def testMaxPriority_TwoTasks(self):
        self.taskList.extend([task.Task(priority=3), task.Task(priority=5)])
        self.assertEqual(5, self.taskList.max_priority())
