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

    def test_create(self):
        self.assertEqual(0, len(self.effortList))

    def onEvent(self, event):
        self.events.append(event)

    def test_notification_after_append(self):
        self.task.addEffort(self.effort)
        self.assertEqual(self.effort, self.events[0].value())

    def test_append(self):
        self.task.addEffort(self.effort)
        self.assertEqual(1, len(self.effortList))
        self.assertTrue(self.effort in self.effortList)

    def test_efforts_of_a_copy_of_a_task_stay_out(self):
        # A copy (same id), such as a merged file's, is another list's
        copy = task.Task(id=self.task.id())
        copy.addEffort(effort.Effort(copy, date.DateTime(2004, 1, 1)))
        self.assertEqual(0, len(self.effortList))

    def test_notification_after_remove(self):
        self.task.addEffort(self.effort)
        self.task.removeEffort(self.effort)
        self.assertEqual(self.effort, self.events[0].value())

    def test_remove(self):
        self.task.addEffort(self.effort)
        self.task.removeEffort(self.effort)
        self.assertEqual(0, len(self.effortList))

    def test_append_task_with_effort(self):
        new_task = task.Task()
        new_task.addEffort(effort.Effort(new_task))
        self.taskList.append(new_task)
        self.assertEqual(1, len(self.effortList))

    def test_create_when_task_list_is_filled(self):
        self.task.addEffort(self.effort)
        effort_list = effort.EffortList(task.TaskList([self.task]))
        self.assertEqual(1, len(effort_list))

    def test_add_effort_to_child(self):
        child = task.Task(parent=self.task)
        self.taskList.append(child)
        child.addEffort(effort.Effort(child))
        self.assertEqual(1, len(self.effortList))

    def test_max_date_time(self):
        self.assertEqual(None, self.effortList.maxDateTime())

    def test_max_date_time_one_effort(self):
        self.task.addEffort(self.effort)
        self.assertEqual(self.effort.getStop(), self.effortList.maxDateTime())

    def test_max_date_time_one_tracking_effort(self):
        self.task.addEffort(effort.Effort(self.task))
        self.assertEqual(None, self.effortList.maxDateTime())

    def test_max_date_time_two_efforts(self):
        self.task.addEffort(self.effort)
        now = date.DateTime.now()
        self.task.addEffort(effort.Effort(self.task, None, now))
        self.assertEqual(now, self.effortList.maxDateTime())

    def test_nr_tracking(self):
        self.assertEqual(0, self.effortList.nr_being_tracked())

    def test_original_length(self):
        self.assertEqual(0, self.effortList.original_length())

    def test_remove_items(self):
        self.task.addEffort(self.effort)
        self.effortList.removeItems([self.effort])
        self.assertEqual(0, len(self.effortList))
        self.assertEqual(0, len(self.task.efforts()))

    def test_remove_all_items(self):
        self.task.addEffort(self.effort)
        effort2 = effort.Effort(
            self.task, date.DateTime(2005, 1, 1), date.DateTime(2005, 1, 2)
        )
        self.task.addEffort(effort2)
        self.effortList.removeItems([effort2, self.effort])
        self.assertEqual(0, len(self.effortList))
        self.assertEqual(0, len(self.task.efforts()))

    def test_extend(self):
        self.effortList.extend([self.effort])
        self.assertEqual(1, len(self.effortList))
        self.assertTrue(self.effort in self.effortList)
        self.assertEqual(1, len(self.task.efforts()))
        self.assertEqual(self.effort, self.task.efforts()[0])

    def test_remove_task_with_effort(self):
        self.task.addEffort(self.effort)
        another_task = task.Task("Another task without effort")
        self.taskList.append(another_task)
        self.assertEqual(1, len(self.effortList))
        self.taskList.remove(self.task)
        self.assertEqual(0, len(self.effortList))

    def test_remove_task_without_effort(self):
        self.task.addEffort(self.effort)
        another_task = task.Task("Another task without effort")
        self.taskList.append(another_task)
        self.assertEqual(1, len(self.effortList))
        self.taskList.remove(another_task)
        self.assertEqual(1, len(self.effortList))

    def test_change_task(self):
        self.task.addEffort(self.effort)
        another_task = task.Task("Another task without effort")
        self.taskList.append(another_task)
        self.assertEqual(1, len(self.effortList))
        self.effort.set_task(another_task)
        self.assertEqual(1, len(self.effortList))
