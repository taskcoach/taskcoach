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

from unittests import asserts
from .CommandTestCase import CommandTestCase
from taskcoachlib import command, patterns
from taskcoachlib.domain import task, effort, date, category, attachment
from taskcoachlib.config import settings


class TaskCommandTestCase(CommandTestCase, asserts.Mixin):
    def setUp(self):
        super().setUp()
        self.list = self.taskList = self.task_file.tasks()
        self.categories = self.task_file.categories()
        self.category = category.Category("cat")
        self.categories.append(self.category)
        self.task1 = task.Task(
            "task1",
            plannedStartDateTime=date.Now(),
            dueDateTime=date.Now() + date.ONE_HOUR,
        )
        self.task2 = task.Task("task2", plannedStartDateTime=date.Now())
        self.taskList.append(self.task1)
        self.originalList = [self.task1]

    def assert_members(self, members):
        """Each category's members, and each member claims it. Delete
        and undo change no membership: a deleted task keeps its
        categories, to come back with them."""
        for cat, expected in members.items():
            self.assertEqual(expected, cat.members())
            for each in expected:
                self.assertIn(cat, each.categories())

    def delete(self, items=None):
        if items == "all":
            items = list(self.list)
        command.DeleteTaskCommand(self.list, items or []).do()

    def paste(self, items=None):  # pylint: disable=W0221
        if items:
            command.PasteAsSubItemCommand(self.taskList, items).do()
        else:
            super().paste()

    def copy(self, items=None):
        command.CopyCommand(self.list, items or []).do()

    def markCompleted(self, tasks=None):
        command.MarkCompletedCommand(self.taskList, tasks or []).do()

    def editPercentageComplete(self, tasks=None, percentage=50):
        command.EditPercentageCompleteCommand(
            self.taskList, tasks or [], newValue=percentage
        ).do()

    def markActive(self, tasks=None):
        command.MarkActiveCommand(self.taskList, tasks or []).do()

    def markInactive(self, tasks=None):
        command.MarkInactiveCommand(self.taskList, tasks or []).do()

    def newSubTask(self, tasks=None, mark_completed=False):
        tasks = tasks or []
        new_sub_task = command.NewSubTaskCommand(self.taskList, tasks)
        if mark_completed:
            for subtask in new_sub_task.items:
                subtask.set_completion_date_time()
        new_sub_task.do()

    def dragAndDrop(self, drop_target, tasks=None):
        command.DragAndDropTaskCommand(
            self.taskList, tasks or [], drop=drop_target
        ).do()

    def editPlannedStart(
        self, new_planned_start_date_time, tasks=None, keep_delta=False
    ):
        command.EditPlannedStartDateTimeCommand(
            self.taskList,
            tasks or [],
            newValue=new_planned_start_date_time,
            keep_delta=keep_delta,
        ).do()

    def editDue(self, new_due_date_time, tasks=None, keep_delta=False):
        command.EditDueDateTimeCommand(
            self.taskList,
            tasks or [],
            newValue=new_due_date_time,
            keep_delta=keep_delta,
        ).do()


class CommandWithChildrenTestCase(TaskCommandTestCase):
    def setUp(self):
        super().setUp()
        self.parent = task.Task("parent")
        self.child = task.Task("child")
        self.parent.addChild(self.child)
        self.child2 = task.Task("child2")
        self.parent.addChild(self.child2)
        self.grandchild = task.Task("grandchild")
        self.child.addChild(self.grandchild)
        self.originalList.extend(
            [self.parent, self.child, self.child2, self.grandchild]
        )
        self.taskList.append(self.parent)


class CommandWithEffortTestCase(TaskCommandTestCase):
    def setUp(self):
        super().setUp()
        self.list = self.effortList = effort.EffortList(self.taskList)
        self.effort1 = effort.Effort(self.task1)
        self.task1.addEffort(self.effort1)
        self.effort2 = effort.Effort(
            self.task2, date.DateTime(2004, 1, 1), date.DateTime(2004, 1, 2)
        )
        self.task2.addEffort(self.effort2)
        self.taskList.append(self.task2)
        self.originalEffortList = [self.effort1, self.effort2]


class DeleteCommandWithTasksTest(TaskCommandTestCase):
    def test_delete_all_tasks(self):
        self.taskList.append(self.task2)
        self.delete("all")
        self.assertDoUndoRedo(
            self.assertEmptyTaskList,
            lambda: self.assertTaskList([self.task1, self.task2]),
        )

    def test_delete_one_task(self):
        self.taskList.append(self.task2)
        self.delete([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertTaskList([self.task2]),
            lambda: self.assertTaskList([self.task1, self.task2]),
        )

    def test_delete_empty_list(self):
        self.taskList.remove(self.task1)
        self.delete("all")
        self.assertDoUndoRedo(self.assertEmptyTaskList)

    def test_delete_empty_list_no_command_history(self):
        self.taskList.remove(self.task1)
        self.delete("all")
        self.assertDoUndoRedo(lambda: self.assert_history_and_future([], []))

    def test_delete(self):
        self.delete("all")
        self.assertDoUndoRedo(
            self.assertEmptyTaskList,
            lambda: self.assertTaskList(self.originalList),
        )

    def test_deleted_task_keeps_its_category(self):
        self.task1.addCategory(self.category)
        self.delete("all")
        members = {self.category: {self.task1}}
        self.assertDoUndoRedo(
            lambda: self.assert_members(members),
            lambda: self.assert_members(members),
        )

    def test_deleted_task_keeps_its_two_categories(self):
        cat1 = category.Category("category 1")
        cat2 = category.Category("category 2")
        self.categories.extend([cat1, cat2])
        for cat in cat1, cat2:
            self.task1.addCategory(cat)
        self.delete("all")
        members = {cat1: {self.task1}, cat2: {self.task1}}
        self.assertDoUndoRedo(
            lambda: self.assert_members(members),
            lambda: self.assert_members(members),
        )

    def test_delete_task_that_is_prerequisite(self):
        self.task2.add_prerequisites([self.task1])
        self.task1.add_dependencies([self.task2])
        self.taskList.append(self.task2)
        self.delete([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.task2.prerequisites()),
            lambda: self.assertTrue(self.task2.prerequisites()),
        )

    def test_delete_task_that_is_dependency(self):
        self.task2.add_prerequisites([self.task1])
        self.task1.add_dependencies([self.task2])
        self.taskList.append(self.task2)
        self.delete([self.task2])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.task1.dependencies()),
            lambda: self.assertTrue(self.task1.dependencies()),
        )


class DeleteCommandWithTasksWithChildrenTest(CommandWithChildrenTestCase):
    def assertDeleteWorks(self):
        self.assertDoUndoRedo(
            self.assertParentAndAllChildrenDeleted,
            self.assertTaskListUnchanged,
        )

    def assertParentAndAllChildrenDeleted(self):
        self.assertTaskList([self.task1])

    def assertTaskListUnchanged(self):
        self.assertTaskList(self.originalList)
        self.failUnlessParentAndChild(self.parent, self.child)
        self.failUnlessParentAndChild(self.child, self.grandchild)

    def test_delete_parent(self):
        self.delete([self.parent])
        self.assertDeleteWorks()

    def test_delete_parent_and_child(self):
        self.delete([self.parent, self.child])
        self.assertDeleteWorks()

    def test_delete_parent_and_grandchild(self):
        self.delete([self.parent, self.grandchild])
        self.assertDeleteWorks()

    def test_delete_last_not_completed_child_marks_parent_as_completed(self):
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.markCompleted([self.child2])
        self.delete([self.child])
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.parent.completed()),
            lambda: self.assertFalse(self.parent.completed()),
        )

    def test_deleted_child_keeps_its_category(self):
        self.child.addCategory(self.category)
        self.delete([self.parent])
        members = {self.category: {self.child}}
        self.assertDoUndoRedo(
            lambda: self.assert_members(members),
            lambda: self.assert_members(members),
        )

    def test_deleted_parent_and_child_keep_their_categories(self):
        cat1 = category.Category("category 1")
        cat2 = category.Category("category 2")
        self.categories.extend([cat1, cat2])
        self.child.addCategory(cat1)
        self.parent.addCategory(cat2)
        self.delete([self.parent])
        members = {cat1: {self.child}, cat2: {self.parent}}
        self.assertDoUndoRedo(
            lambda: self.assert_members(members),
            lambda: self.assert_members(members),
        )

    def test_deleted_parent_and_child_keep_a_shared_category(self):
        for each_task in self.parent, self.child:
            each_task.addCategory(self.category)
        self.delete([self.parent])
        members = {self.category: {self.parent, self.child}}
        self.assertDoUndoRedo(
            lambda: self.assert_members(members),
            lambda: self.assert_members(members),
        )


class DeleteCommandWithTasksWithEffortTest(CommandWithEffortTestCase):
    def test_delete_active_task(self):
        self.list = self.taskList
        self.delete([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(1, len(self.effortList)),
            lambda: self.assertEqual(2, len(self.effortList)),
        )


class NewTaskCommandTest(TaskCommandTestCase):
    def new(self, **kwargs):
        new_task_command = command.NewTaskCommand(self.taskList, **kwargs)
        new_task = new_task_command.items[0]
        new_task_command.do()
        return new_task

    def test_new_task(self):
        new_task = self.new()
        self.assertDoUndoRedo(
            lambda: self.assertTaskList([self.task1, new_task]),
            lambda: self.assertTaskList(self.originalList),
        )

    def test_new_task_with_category(self):
        cat = category.Category("cat")
        new_task = self.new(categories=[cat])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(set([cat]), new_task.categories()),
            lambda: self.assertTaskList(self.originalList),
        )

    def test_new_task_with_category_is_its_member(self):
        # Undone, it keeps the category, to come back with it on redo
        cat = category.Category("cat")
        new_task = self.new(categories=[cat])
        members = {cat: {new_task}}
        self.assertDoUndoRedo(
            lambda: self.assert_members(members),
            lambda: self.assert_members(members),
        )

    def test_new_task_with_prerequisite(self):
        new_task = self.new(prerequisites=[self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.task1]), new_task.prerequisites()
            ),
            lambda: self.assertTaskList(self.originalList),
        )

    def test_new_task_with_prerequisite_adds_dependency(self):
        new_task = self.new(prerequisites=[self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([new_task]), self.task1.dependencies()
            ),
            lambda: self.assertFalse(self.task1.dependencies()),
        )

    def test_new_task_with_dependency(self):
        new_task = self.new(dependencies=[self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.task1]), new_task.dependencies()
            ),
            lambda: self.assertTaskList(self.originalList),
        )

    def test_new_task_with_dependency_adds_prerequisite(self):
        new_task = self.new(dependencies=[self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([new_task]), self.task1.prerequisites()
            ),
            lambda: self.assertFalse(self.task1.prerequisites()),
        )

    def test_new_task_with_attachment(self):
        att = attachment.FileAttachment("filename")
        new_task = self.new(attachments=[att])
        self.assertDoUndoRedo(
            lambda: self.assertEqual([att], new_task.attachments()),
            lambda: self.assertTaskList(self.originalList),
        )

    def test_new_task_with_keywords(self):
        date_time = date.DateTime(2042, 2, 3)
        new_task = self.new(plannedStartDateTime=date_time)
        self.assertEqual(date_time, new_task.plannedStartDateTime())

    def test_items_are_new(self):
        self.assertTrue(command.NewTaskCommand(self.taskList).items_are_new())


class NewSubTaskCommandTest(TaskCommandTestCase):
    def test_new_sub_task_without_selection(self):
        self.newSubTask()
        self.assertDoUndoRedo(lambda: self.assertTaskList(self.originalList))

    def test_new_subtask_keeps_the_parents_date(self):
        # Children are the reverse of the subtasks' parent link
        self.task1.set_modification_datetime(date.DateTime(2020, 1, 1))
        self.newSubTask([self.task1])
        self.assertEqual(
            date.DateTime(2020, 1, 1), self.task1.modificationDateTime()
        )

    def test_new_sub_task(self):
        self.newSubTask([self.task1])
        new_sub_task = self.task1.children()[0]
        self.assertDoUndoRedo(
            lambda: self.assertNewSubTask(new_sub_task),
            lambda: self.assertTaskList(self.originalList),
        )

    def assertNewSubTask(self, new_sub_task):
        self.assertEqual(len(self.originalList) + 1, len(self.taskList))
        self.assertEqualLists([new_sub_task], self.task1.children())

    def test_new_sub_task_marks_parent_as_not_completed(self):
        self.markCompleted([self.task1])
        self.newSubTask([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.task1.completed()),
            lambda: self.assertTrue(self.task1.completed()),
        )

    def test_new_sub_task_marks_grand_parent_as_not_completed(self):
        self.newSubTask([self.task1])
        self.markCompleted([self.task1])
        self.newSubTask([self.task1.children()[0]])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.task1.completed()),
            lambda: self.assertTrue(self.task1.completed()),
        )

    def test_new_completed_sub_task(self):
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.newSubTask([self.task1], mark_completed=True)
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.task1.completed()),
            lambda: self.assertFalse(self.task1.completed()),
        )

    def test_new_sub_task_without_due_date_doesnt_reset_parents_due_date(self):
        due_date_time = date.Now() + date.TWO_HOURS
        self.task1.set_due_date_time(due_date_time)
        self.newSubTask([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(due_date_time, self.task1.dueDateTime())
        )

    def test_items_are_new(self):
        self.assertTrue(
            command.NewSubTaskCommand(self.taskList, []).items_are_new()
        )


class MarkCompletedCommandTest(CommandWithChildrenTestCase):
    def test_mark_completed(self):
        self.markCompleted([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.task1.completed()),
            lambda: self.assertFalse(self.task1.completed()),
        )

    def test_mark_completed_task_already_completed(self):
        self.task1.set_completion_date_time()
        self.markCompleted([self.task1])
        self.assertDoUndoRedo(lambda: self.assertTrue(self.task1.completed()))

    def test_mark_completed_parent(self):
        self.markCompleted([self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertTrue(
                self.child.completed()
                and self.child2.completed()
                and self.grandchild.completed()
            ),
            lambda: self.assertFalse(
                self.child.completed()
                or self.child2.completed()
                or self.grandchild.completed()
            ),
        )

    def test_mark_completed_parent_when_child_already_completed(self):
        self.markCompleted([self.child])
        self.markCompleted([self.parent])
        self.assertDoUndoRedo(lambda: self.assertTrue(self.child.completed()))

    def test_mark_completed_grand_child(self):
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.markCompleted([self.grandchild])
        self.assertDoUndoRedo(
            lambda: self.assertTrue(
                self.child.completed() and not self.parent.completed()
            ),
            lambda: self.assertFalse(
                self.child.completed() or self.parent.completed()
            ),
        )

    def test_undo_puts_back_the_date_of_every_task_it_changed(self):
        # The child is completed by its last subtask, not by the command
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        before = date.DateTime(2020, 1, 1)
        for each in (self.child, self.grandchild):
            each.set_modification_datetime(before)
        self.markCompleted([self.grandchild])

        def dates():
            return [
                self.child.modificationDateTime(),
                self.grandchild.modificationDateTime(),
            ]

        changed = dates()
        self.assertTrue(before < min(changed))
        self.assertDoUndoRedo(
            lambda: self.assertEqual(changed, dates()),
            lambda: self.assertEqual([before, before], dates()),
        )

    def test_mark_completed_stops_effort_tracking(self):
        self.task1.addEffort(effort.Effort(self.task1))
        self.markCompleted([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.task1.isBeingTracked()),
            lambda: self.assertTrue(self.task1.isBeingTracked()),
        )

    def test_mark_completed_child_does_not_stop_effort_tracking_of_parent(
        self,
    ):
        self.parent.addEffort(effort.Effort(self.parent))
        self.markCompleted([self.child])
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.parent.isBeingTracked())
        )

    def test_mark_recurring_task_completed_completion_date_is_not_set(self):
        self.task1.set_recurrence(date.Recurrence("weekly"))
        self.markCompleted([self.task1])
        self.assertDoUndoRedo(lambda: self.assertFalse(self.task1.completed()))

    def test_mark_recurring_task_completed_planned_start_date_is_increased(
        self,
    ):
        self.task1.set_recurrence(date.Recurrence("weekly"))
        planned_start_date_time = self.task1.plannedStartDateTime()
        new_planned_start_date_time = planned_start_date_time + date.TimeDelta(
            days=7
        )
        self.markCompleted([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                new_planned_start_date_time, self.task1.plannedStartDateTime()
            ),
            lambda: self.assertEqual(
                planned_start_date_time, self.task1.plannedStartDateTime()
            ),
        )

    def test_mark_recurring_task_completed_due_date_is_increased(self):
        self.task1.set_recurrence(date.Recurrence("weekly"))
        tomorrow = date.Tomorrow()
        self.task1.set_due_date_time(tomorrow)
        new_due_date = tomorrow + date.ONE_WEEK
        self.markCompleted([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(new_due_date, self.task1.dueDateTime()),
            lambda: self.assertEqual(tomorrow, self.task1.dueDateTime()),
        )

    def test_mark_recurring_task_completed_actual_start_date_is_reset(self):
        self.task1.set_recurrence(date.Recurrence("weekly"))
        now = date.Now()
        self.task1.set_actual_start_date_time(now)
        self.markCompleted([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            ),
            lambda: self.assertEqual(now, self.task1.actualStartDateTime()),
        )

    def test_completing_parent_removes_recurrence_of_recurring_child(
        self,
    ):
        self.child.set_recurrence(date.Recurrence("daily"))
        self.markCompleted([self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.child.recurrence()),
            lambda: self.assertEqual(
                date.Recurrence("daily"), self.child.recurrence()
            ),
        )

    def test_mark_parent_with_recurring_child_completed_makes_child_completed(
        self,
    ):
        self.child.set_recurrence(date.Recurrence("daily"))
        self.markCompleted([self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.child.completed()),
            lambda: self.assertFalse(self.child.completed()),
        )


class EditRecurrenceCommandTest(TaskCommandTestCase):
    """A new recurrence keeps how many times each task has recurred:
    "Stop after N recurrences" counts them (P168)."""

    def setUp(self):
        super().setUp()
        self.taskList.append(self.task2)
        for each, count in ((self.task1, 3), (self.task2, 5)):
            each.set_recurrence(
                date.Recurrence("weekly", maximum=10, count=count)
            )
        command.EditRecurrenceCommand(
            self.taskList,
            [self.task1, self.task2],
            newValue=date.Recurrence("daily", maximum=10),
        ).do()

    def test_each_task_keeps_its_count(self):
        self.assertEqual(
            [("daily", 3), ("daily", 5)],
            [
                (each.recurrence().unit, each.recurrence().count)
                for each in (self.task1, self.task2)
            ],
        )

    def test_each_task_gets_its_own_recurrence(self):
        self.assertIsNot(self.task1.recurrence(), self.task2.recurrence())

    def test_undo(self):
        self.undo()
        self.assertEqual(
            [("weekly", 3), ("weekly", 5)],
            [
                (each.recurrence().unit, each.recurrence().count)
                for each in (self.task1, self.task2)
            ],
        )


class EditPercentageCompleteTest(TaskCommandTestCase):
    def test_edit_percentage_complete(self):
        self.editPercentageComplete([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(50, self.task1.percentageComplete()),
            lambda: self.assertEqual(0, self.task1.percentageComplete()),
        )

    def test_task_is_started_after_editing_percentage_complete(self):
        self.editPercentageComplete([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertNotEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            ),
            lambda: self.assertEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            ),
        )

    def test_name_for_one_task(self):
        edit = command.EditPercentageCompleteCommand(
            self.taskList, [self.task1], newValue=50
        )
        self.assertEqual('Change percentage complete of "task1"', str(edit))

    def test_name_for_several_tasks(self):
        edit = command.EditPercentageCompleteCommand(
            self.taskList, [self.task1, self.task2], newValue=50
        )
        self.assertEqual("Change percentage complete", str(edit))


class MarkActiveCommandTest(TaskCommandTestCase):
    def test_mark_inactive_task_active(self):
        self.markActive([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertNotEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            ),
            lambda: self.assertEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            ),
        )

    def test_mark_completed_task_active(self):
        now = date.Now()
        self.task1.set_completion_date_time(now)
        self.markActive([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                date.DateTime(), self.task1.completionDateTime()
            ),
            lambda: self.assertEqual(now, self.task1.completionDateTime()),
        )

    def test_ignore_task_that_is_already_active(self):
        now = date.Now()
        self.task1.set_actual_start_date_time(now)
        self.markActive([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(now, self.task1.actualStartDateTime())
        )

    def test_task_with_future_actual_start_date_time(self):
        tomorrow = date.Tomorrow()
        self.task1.set_actual_start_date_time(tomorrow)
        self.markActive([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertAlmostEqual(
                date.Now().toordinal(),
                self.task1.actualStartDateTime().toordinal(),
                places=2,
            ),
            lambda: self.assertEqual(
                tomorrow, self.task1.actualStartDateTime()
            ),
        )


class MarkInactiveCommandTest(TaskCommandTestCase):
    def test_mark_active_task_inactive(self):
        now = date.Now()
        self.task1.set_actual_start_date_time(now)
        self.markInactive([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            ),
            lambda: self.assertEqual(now, self.task1.actualStartDateTime()),
        )

    def test_mark_completed_task_inactive(self):
        now = date.Now()
        self.task1.set_completion_date_time(now)
        self.markInactive([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                date.DateTime(), self.task1.completionDateTime()
            ),
            lambda: self.assertEqual(now, self.task1.completionDateTime()),
        )

    def test_ignore_task_that_is_already_inactive(self):
        self.markInactive([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            )
        )

    def test_task_with_future_actual_start_date_time(self):
        tomorrow = date.Tomorrow()
        self.task1.set_actual_start_date_time(tomorrow)
        self.markInactive([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            ),
            lambda: self.assertEqual(
                tomorrow, self.task1.actualStartDateTime()
            ),
        )


class DragAndDropTaskCommandTest(CommandWithChildrenTestCase):
    def test_cannot_drop_on_parent(self):
        self.dragAndDrop([self.parent], [self.child])
        self.assertFalse(patterns.CommandHistory().has_history())

    def test_cannot_drop_on_child(self):
        self.dragAndDrop([self.child], [self.parent])
        self.assertFalse(patterns.CommandHistory().has_history())

    def test_cannot_drop_on_grandchild(self):
        self.dragAndDrop([self.grandchild], [self.parent])
        self.assertFalse(patterns.CommandHistory().has_history())

    def test_drop_as_root_task(self):
        self.dragAndDrop([], [self.grandchild])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(None, self.grandchild.parent()),
            lambda: self.assertEqual(self.child, self.grandchild.parent()),
        )

    def test_undo_drop_on_completed_task_completes_its_parent_again(self):
        completed = date.DateTime(2026, 9, 1)
        self.parent.set_completion_date_time(completed)
        self.taskList.append(self.task1)
        # The open task reopens the child it lands on, and its parent
        self.dragAndDrop([self.child], [self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.parent.completed()),
            lambda: self.assertEqual(
                completed, self.parent.completionDateTime()
            ),
        )


class PriorityCommandTestCase(TaskCommandTestCase):
    def setUp(self):
        super().setUp()
        self.taskList.append(self.task2)

    def assertDoUndoRedo(
        self, priority1do, priority2do, priority1undo, priority2undo
    ):  # pylint: disable=W0221
        super().assertDoUndoRedo(
            lambda: self.assertTrue(
                priority1do == self.task1.priority()
                and priority2do == self.task2.priority()
            ),
            lambda: self.assertTrue(
                priority1undo == self.task1.priority()
                and priority2undo == self.task2.priority()
            ),
        )


class MaxPriorityCommandTest(PriorityCommandTestCase):
    def max_priority(self, tasks=None):
        command.MaxPriorityCommand(self.taskList, tasks or []).do()

    def test_empty_selection(self):
        self.max_priority()
        self.assertDoUndoRedo(0, 0, 0, 0)

    def test_one_task_when_both_tasks_have_same_priority(self):
        self.max_priority([self.task1])
        self.assertDoUndoRedo(1, 0, 0, 0)

    def test_both_tasks_when_both_tasks_have_same_priority(self):
        self.max_priority([self.task1, self.task2])
        self.assertDoUndoRedo(1, 1, 0, 0)

    def test_make_lowest_priority_the_max_priority(self):
        self.task2.setPriority(2)
        self.max_priority([self.task1])
        self.assertDoUndoRedo(3, 2, 0, 2)


class MinPriorityCommandTest(PriorityCommandTestCase):
    def min_priority(self, tasks=None):
        command.MinPriorityCommand(self.taskList, tasks or []).do()

    def test_empty_selection(self):
        self.min_priority()
        self.assertDoUndoRedo(0, 0, 0, 0)

    def test_one_task_when_both_tasks_have_same_priority(self):
        self.min_priority([self.task1])
        self.assertDoUndoRedo(-1, 0, 0, 0)

    def test_both_tasks_when_both_tasks_have_same_priority(self):
        self.min_priority([self.task1, self.task2])
        self.assertDoUndoRedo(-1, -1, 0, 0)

    def test_make_lowest_priority_the_max_priority(self):
        self.task2.setPriority(-2)
        self.min_priority([self.task1])
        self.assertDoUndoRedo(-3, -2, 0, -2)


class IncreasePriorityCommandTest(PriorityCommandTestCase):
    def incPriority(self, tasks=None):
        command.IncPriorityCommand(self.taskList, tasks or []).do()

    def test_empty_selection(self):
        self.incPriority()
        self.assertDoUndoRedo(0, 0, 0, 0)

    def test_one_task_when_both_tasks_have_same_priority(self):
        self.incPriority([self.task1])
        self.assertDoUndoRedo(1, 0, 0, 0)

    def test_both_tasks_when_both_tasks_have_same_priority(self):
        self.incPriority([self.task1, self.task2])
        self.assertDoUndoRedo(1, 1, 0, 0)

    def test_inc_lowest_priority(self):
        self.task2.setPriority(-2)
        self.incPriority([self.task2])
        self.assertDoUndoRedo(0, -1, 0, -2)


class DecreasePriorityCommandTest(PriorityCommandTestCase):
    def decPriority(self, tasks=None):
        command.DecPriorityCommand(self.taskList, tasks or []).do()

    def test_empty_selection(self):
        self.decPriority()
        self.assertDoUndoRedo(0, 0, 0, 0)

    def test_one_task_when_both_tasks_have_same_priority(self):
        self.decPriority([self.task1])
        self.assertDoUndoRedo(-1, 0, 0, 0)

    def test_both_tasks_when_both_tasks_have_same_priority(self):
        self.decPriority([self.task1, self.task2])
        self.assertDoUndoRedo(-1, -1, 0, 0)

    def test_dec_lowest_priority(self):
        self.task2.setPriority(-2)
        self.decPriority([self.task2])
        self.assertDoUndoRedo(0, -3, 0, -2)


class EditReminderCommandTest(TaskCommandTestCase):
    def editReminder(self, tasks=None):
        command.EditReminderDateTimeCommand(
            self.taskList, tasks or [], newValue=date.Now() + date.ONE_HOUR
        ).do()

    def test_edit_reminder(self):
        self.editReminder([self.task1])
        # Not set is the latest date (docs/ATTRIBUTE_PATTERN.md)
        self.assertDoUndoRedo(
            lambda: self.assertNotEqual(
                date.DateTime(), self.task1.reminder()
            ),
            lambda: self.assertEqual(date.DateTime(), self.task1.reminder()),
        )


class AddNoteCommandTest(TaskCommandTestCase):
    def addNote(self, tasks=None):
        command.AddNoteCommand(self.taskList, tasks or []).do()

    # pylint: disable=E1101

    def test_empty_selection(self):
        self.addNote()
        self.assertDoUndoRedo(lambda: self.assertFalse(self.task1.notes()))

    def test_add_note(self):
        self.addNote([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.task1.notes()),
            lambda: self.assertFalse(self.task1.notes()),
        )

    def test_add_note_to_multiple_tasks_at_once(self):
        self.addNote([self.task1, self.task2])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(
                self.task1.notes()[0] == self.task2.notes()[0]
            ),
            lambda: self.assertFalse(self.task1.notes() or self.task2.notes()),
        )


class PlannedDatesFollowTheModeTest(TaskCommandTestCase):
    """A planned date changed outside the editor follows the task's
    duration mode, as in the editor (P150)."""

    def setUp(self):
        super().setUp()
        self.start = date.DateTime(2026, 1, 30, 9, 0, 0)
        self.due = self.start + date.ONE_DAY
        self.task1.set_planned_start_date_time(self.start)
        self.task1.set_due_date_time(self.due)

    def set_mode(self, mode):
        self.task1.setPlannedDurationMode(mode)
        self.task1.setPlannedDuration(date.ONE_DAY)

    def assert_period(self, start, due, duration):
        self.assertEqual(
            (start, due, duration),
            (
                self.task1.plannedStartDateTime(),
                self.task1.dueDateTime(),
                self.task1.plannedDuration(),
            ),
        )

    def assert_do_undo_redo(self, *period):
        self.assertDoUndoRedo(
            lambda: self.assert_period(*period),
            lambda: self.assert_period(self.start, self.due, date.ONE_DAY),
        )

    def test_adjust_due_a_new_start_moves_the_due_date(self):
        self.set_mode("adjdue")
        new_start = self.start + date.ONE_HOUR
        self.editPlannedStart(new_start, [self.task1])
        self.assert_do_undo_redo(
            new_start, new_start + date.ONE_DAY, date.ONE_DAY
        )

    def test_adjust_due_a_new_due_date_sets_the_duration(self):
        self.set_mode("adjdue")
        new_due = self.due + date.ONE_DAY
        self.editDue(new_due, [self.task1])
        self.assert_do_undo_redo(self.start, new_due, date.TimeDelta(days=2))

    def test_adjust_start_a_new_due_date_moves_the_start(self):
        self.set_mode("adjstart")
        new_due = self.due + date.ONE_HOUR
        self.editDue(new_due, [self.task1])
        self.assert_do_undo_redo(new_due - date.ONE_DAY, new_due, date.ONE_DAY)

    def test_adjust_start_a_new_start_sets_the_duration(self):
        self.set_mode("adjstart")
        new_start = self.start - date.ONE_DAY
        self.editPlannedStart(new_start, [self.task1])
        self.assert_do_undo_redo(new_start, self.due, date.TimeDelta(days=2))

    def test_a_move_keeps_the_duration_in_every_mode(self):
        for mode in ("implicit", "adjdue", "adjstart"):
            self.set_mode(mode)
            self.editPlannedStart(
                self.start + date.ONE_HOUR, [self.task1], keep_delta=True
            )
            self.assert_period(
                self.start + date.ONE_HOUR,
                self.due + date.ONE_HOUR,
                date.ONE_DAY,
            )
            self.editPlannedStart(self.start, [self.task1], keep_delta=True)

    def test_both_ends_given_set_the_duration(self):
        self.set_mode("adjstart")
        command.EditPlannedStartDateTimeCommand(
            self.taskList,
            [self.task1],
            newValue=self.start + date.ONE_HOUR,
            other_value=self.due + date.TWO_HOURS,
        ).do()
        self.assert_period(
            self.start + date.ONE_HOUR,
            self.due + date.TWO_HOURS,
            date.ONE_DAY + date.ONE_HOUR,
        )

    def test_without_the_other_date_nothing_else_changes(self):
        self.set_mode("adjdue")
        self.task1.set_due_date_time(None)
        self.editPlannedStart(self.start + date.ONE_HOUR, [self.task1])
        self.assert_period(
            self.start + date.ONE_HOUR, date.DateTime(), date.ONE_DAY
        )

    def test_implicit_the_other_date_stays(self):
        self.set_mode("implicit")
        self.editPlannedStart(self.start + date.ONE_HOUR, [self.task1])
        self.assert_period(
            self.start + date.ONE_HOUR, self.due, date.TimeDelta(hours=23)
        )


class EditDuePlannedStartDateCommandTest(TaskCommandTestCase):
    def test_set_planned_start_date_to_tomorrow(self):
        previous_start = self.task1.plannedStartDateTime()
        new_start = date.Now() + date.ONE_HOUR
        self.editPlannedStart(new_start, [self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                new_start, self.task1.plannedStartDateTime()
            ),
            lambda: self.assertEqual(
                previous_start, self.task1.plannedStartDateTime()
            ),
        )

    def test_set_due_date_to_tomorrow(self):
        previous_due = self.task1.dueDateTime()
        new_due = date.Now() + date.ONE_HOUR
        self.editDue(new_due, [self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(new_due, self.task1.dueDateTime()),
            lambda: self.assertEqual(previous_due, self.task1.dueDateTime()),
        )

    def test_pushing_back_planned_start_date_pushes_back_due_date(self):
        self.task1.set_due_date_time(date.Now() + date.TWO_HOURS)
        previous_planned_start = self.task1.plannedStartDateTime()
        previous_due = self.task1.dueDateTime()
        push_back = date.ONE_HOUR
        new_planned_start = previous_planned_start + push_back
        expected_due = previous_due + push_back
        self.editPlannedStart(new_planned_start, [self.task1], keep_delta=True)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(expected_due, self.task1.dueDateTime()),
            lambda: self.assertEqual(previous_due, self.task1.dueDateTime()),
        )

    def test_pushing_back_due_date_pushes_back_planned_start_date(self):
        self.task1.set_due_date_time(date.Now() + date.TWO_HOURS)
        previous_planned_start = self.task1.plannedStartDateTime()
        previous_due = self.task1.dueDateTime()
        push_back = date.ONE_HOUR
        new_due = previous_due + push_back
        expected_planned_start = previous_planned_start + push_back
        self.editDue(new_due, [self.task1], keep_delta=True)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                expected_planned_start, self.task1.plannedStartDateTime()
            ),
            lambda: self.assertEqual(
                previous_planned_start, self.task1.plannedStartDateTime()
            ),
        )

    def test_pushing_back_planned_start_date_does_not_push_back_due_date(self):
        self.task1.set_due_date_time(date.Now() + date.TWO_HOURS)
        previous_planned_start = self.task1.plannedStartDateTime()
        previous_due = self.task1.dueDateTime()
        push_back = date.ONE_HOUR
        new_planned_start = previous_planned_start + push_back
        expected_due = previous_due
        self.editPlannedStart(new_planned_start, [self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(expected_due, self.task1.dueDateTime()),
            lambda: self.assertEqual(previous_due, self.task1.dueDateTime()),
        )

    def test_pushing_back_due_date_does_not_push_back_planned_start_date(self):
        self.task1.set_due_date_time(date.Now() + date.TWO_HOURS)
        previous_planned_start = self.task1.plannedStartDateTime()
        previous_due = self.task1.dueDateTime()
        push_back = date.ONE_HOUR
        new_due = previous_due + push_back
        expected_planned_start = previous_planned_start
        self.editDue(new_due, [self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                expected_planned_start, self.task1.plannedStartDateTime()
            ),
            lambda: self.assertEqual(
                previous_planned_start, self.task1.plannedStartDateTime()
            ),
        )

    def test_missing_due_date_is_not_pushed_back(self):
        previous_planned_start = self.task1.plannedStartDateTime()
        push_back = date.ONE_HOUR
        new_planned_start = previous_planned_start + push_back
        expected_due = date.DateTime()
        self.task1.set_due_date_time(expected_due)
        self.editPlannedStart(new_planned_start, [self.task1], keep_delta=True)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(expected_due, self.task1.dueDateTime())
        )

    def test_missing_planned_start_date_is_not_pushed_back(self):
        self.task1.set_planned_start_date_time(date.DateTime())
        self.task1.set_due_date_time(date.Now() + date.TWO_HOURS)
        previous_due = self.task1.dueDateTime()
        push_back = date.ONE_HOUR
        new_due = previous_due + push_back
        expected_start = date.DateTime()
        self.editDue(new_due, [self.task1], keep_delta=True)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                expected_start, self.task1.plannedStartDateTime()
            )
        )

    def test_due_date_is_not_pushed_back_when_planned_start_date_is_missing(
        self,
    ):
        self.task1.set_planned_start_date_time(date.DateTime())
        self.task1.set_due_date_time(date.Now() + date.TWO_HOURS)
        push_back = date.ONE_HOUR
        new_start = date.Now() + push_back
        expected_due = self.task1.dueDateTime()
        self.editPlannedStart(new_start, [self.task1], keep_delta=True)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(expected_due, self.task1.dueDateTime())
        )

    def test_planned_start_date_is_not_pushed_back_when_due_date_is_missing(
        self,
    ):
        push_back = date.ONE_HOUR
        new_due = date.Now() + push_back
        expected_start = self.task1.plannedStartDateTime()
        self.task1.set_due_date_time(date.DateTime())
        self.editDue(new_due, [self.task1], keep_delta=True)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                expected_start, self.task1.plannedStartDateTime()
            )
        )

    def test_set_infinite_planned_start_date(self):
        new_planned_start_date_time = date.DateTime()
        original_planned_start_date_time = self.task1.plannedStartDateTime()
        self.editPlannedStart(new_planned_start_date_time, [self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                new_planned_start_date_time, self.task1.plannedStartDateTime()
            ),
            lambda: self.assertEqual(
                original_planned_start_date_time,
                self.task1.plannedStartDateTime(),
            ),
        )

    def test_set_infinite_planned_start_date_does_not_change_due_date(self):
        new_planned_start_date_time = date.DateTime()
        original_due_date_time = self.task1.dueDateTime()
        self.editPlannedStart(
            new_planned_start_date_time, [self.task1], keep_delta=True
        )
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                original_due_date_time, self.task1.dueDateTime()
            )
        )

    def test_set_infinite_due_date(self):
        new_due_date_time = date.DateTime()
        original_due_date_time = self.task1.dueDateTime()
        self.editDue(new_due_date_time, [self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                new_due_date_time, self.task1.dueDateTime()
            ),
            lambda: self.assertEqual(
                original_due_date_time, self.task1.dueDateTime()
            ),
        )

    def test_set_infinite_due_date_does_not_change_planned_start_date(self):
        new_due_date_time = date.DateTime()
        original_planned_start_date_time = self.task1.plannedStartDateTime()
        self.editDue(new_due_date_time, [self.task1], keep_delta=True)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                original_planned_start_date_time,
                self.task1.plannedStartDateTime(),
            )
        )
