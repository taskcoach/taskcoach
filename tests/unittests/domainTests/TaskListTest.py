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
        self.taskList = task.TaskList()
        year = date.Now().year
        self.task1 = task.Task(dueDateTime=date.DateTime(year + 1, 1, 1))
        self.task2 = task.Task(dueDateTime=date.DateTime(year + 2, 1, 1))
        self.task3 = task.Task()

    def nrStatus(self, status):
        return self.taskList.nr_of_tasks_per_status()[status]

    def test_nr_of_tasks_per_status_of_an_empty_task_list(self):
        counts = self.taskList.nr_of_tasks_per_status()
        for status in task.Task.possibleStatuses():
            self.assertEqual(0, counts[status])

    def test_nr_completed(self):
        self.assertEqual(0, self.nrStatus(task.status.completed))
        self.taskList.append(self.task1)
        self.assertEqual(0, self.nrStatus(task.status.completed))
        self.task1.set_completion_date_time()
        self.assertEqual(1, self.nrStatus(task.status.completed))

    def test_nr_overdue(self):
        self.assertEqual(0, self.nrStatus(task.status.overdue))
        self.taskList.append(self.task1)
        self.assertEqual(0, self.nrStatus(task.status.overdue))
        self.task1.set_due_date_time(date.DateTime(1990, 1, 1))
        self.assertEqual(1, self.nrStatus(task.status.overdue))

    def test_nr_due_soon(self):
        self.assertEqual(0, self.nrStatus(task.status.duesoon))
        self.taskList.append(task.Task(dueDateTime=date.Now() + date.ONE_HOUR))
        self.assertEqual(1, self.nrStatus(task.status.duesoon))

    def test_nr_being_tracked(self):
        self.assertEqual(0, self.taskList.nr_being_tracked())
        active_task = task.Task()
        active_task.addEffort(effort.Effort(active_task))
        self.taskList.append(active_task)
        self.assertEqual(1, self.taskList.nr_being_tracked())

    def test_original_length(self):
        self.assertEqual(0, self.taskList.original_length())

    def test_min_priority_empty_task_list(self):
        self.assertEqual(0, self.taskList.min_priority())

    def test_min_priority_one_task_with_default_priority(self):
        self.taskList.append(self.task1)
        self.assertEqual(self.task1.priority(), self.taskList.min_priority())

    def test_min_priority_one_task_with_non_default_priority(self):
        self.taskList.append(task.Task(priority=-5))
        self.assertEqual(-5, self.taskList.min_priority())

    def test_min_priority_two_tasks(self):
        self.taskList.extend([task.Task(priority=3), task.Task(priority=5)])
        self.assertEqual(3, self.taskList.min_priority())

    def test_max_priority_empty_task_list(self):
        self.assertEqual(0, self.taskList.max_priority())

    def test_max_priority_one_task_with_default_priority(self):
        self.taskList.append(self.task1)
        self.assertEqual(self.task1.priority(), self.taskList.max_priority())

    def test_max_priority_one_task_with_non_default_priority(self):
        self.taskList.append(task.Task(priority=-5))
        self.assertEqual(-5, self.taskList.max_priority())

    def test_max_priority_two_tasks(self):
        self.taskList.extend([task.Task(priority=3), task.Task(priority=5)])
        self.assertEqual(5, self.taskList.max_priority())
