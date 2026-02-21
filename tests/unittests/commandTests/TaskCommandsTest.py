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
from taskcoachlib import command, patterns, config
from taskcoachlib.domain import task, effort, date, category, attachment


class TaskCommandTestCase(CommandTestCase, asserts.Mixin):
    def setUp(self):
        super().setUp()
        self.settings = task.Task.settings = config.Settings(load=False)
        self.list = self.taskList = task.TaskList()
        self.categories = category.CategoryList()
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

    def tearDown(self):
        super().tearDown()
        command.Clipboard().clear()

    def delete(self, items=None, shadow=False):
        if items == "all":
            items = list(self.list)
        command.DeleteTaskCommand(self.list, items or [], shadow=shadow).do()

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

    def newSubTask(self, tasks=None, markCompleted=False):
        tasks = tasks or []
        newSubTask = command.NewSubTaskCommand(self.taskList, tasks)
        if markCompleted:
            for subtask in newSubTask.items:
                subtask.setCompletionDateTime()
        newSubTask.do()

    def dragAndDrop(self, dropTarget, tasks=None):
        command.DragAndDropTaskCommand(
            self.taskList, tasks or [], drop=dropTarget
        ).do()

    def editPlannedStart(
        self, newPlannedStartDateTime, tasks=None, keep_delta=False
    ):
        command.EditPlannedStartDateTimeCommand(
            self.taskList,
            tasks or [],
            newValue=newPlannedStartDateTime,
            keep_delta=keep_delta,
        ).do()

    def editDue(self, newDueDateTime, tasks=None, keep_delta=False):
        command.EditDueDateTimeCommand(
            self.taskList,
            tasks or [],
            newValue=newDueDateTime,
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
    def testDeleteAllTasks(self):
        self.taskList.append(self.task2)
        self.delete("all")
        self.assertDoUndoRedo(
            self.assertEmptyTaskList,
            lambda: self.assertTaskList([self.task1, self.task2]),
        )

    def testDeleteOneTask(self):
        self.taskList.append(self.task2)
        self.delete([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertTaskList([self.task2]),
            lambda: self.assertTaskList([self.task1, self.task2]),
        )

    def testDeleteEmptyList(self):
        self.taskList.remove(self.task1)
        self.delete("all")
        self.assertDoUndoRedo(self.assertEmptyTaskList)

    def testDeleteEmptyList_NoCommandHistory(self):
        self.taskList.remove(self.task1)
        self.delete("all")
        self.assertDoUndoRedo(lambda: self.assertHistoryAndFuture([], []))

    def testDelete(self):
        self.delete("all")
        self.assertDoUndoRedo(
            self.assertEmptyTaskList,
            lambda: self.assertTaskList(self.originalList),
        )

    def testDeleteTaskWithCategory(self):
        self.category.addCategorizable(self.task1)
        self.task1.addCategory(self.category)
        self.delete("all")
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.category.categorizables()),
            lambda: self.assertEqual(
                set([self.task1]), self.category.categorizables()
            ),
        )

    def testDeleteTaskWithTwoCategories(self):
        cat1 = category.Category("category 1")
        cat2 = category.Category("category 2")
        self.categories.extend([cat1, cat2])
        for cat in cat1, cat2:
            cat.addCategorizable(self.task1)
            self.task1.addCategory(cat)
        self.delete("all")
        self.assertDoUndoRedo(
            lambda: self.assertFalse(
                cat1.categorizables() or cat2.categorizables()
            ),
            lambda: self.assertTrue(
                set([self.task1])
                == cat1.categorizables()
                == cat2.categorizables()
            ),
        )

    def testDeleteTaskThatIsPrerequisite(self):
        self.task2.addPrerequisites([self.task1])
        self.task1.addDependencies([self.task2])
        self.taskList.append(self.task2)
        self.delete([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.task2.prerequisites()),
            lambda: self.assertTrue(self.task2.prerequisites()),
        )

    def testDeleteTaskThatIsDependency(self):
        self.task2.addPrerequisites([self.task1])
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

    def assertShadowed(self, *shadowedTasks):
        for shadowedTask in shadowedTasks:
            self.assertTrue(shadowedTask.isDeleted())

    def testDeleteParent(self):
        self.delete([self.parent])
        self.assertDeleteWorks()

    def testDeleteParentWhileShadowing(self):
        self.delete([self.parent], shadow=True)
        self.assertShadowed(self.parent, *self.parent.children())

    def testDeleteParentAndChild(self):
        self.delete([self.parent, self.child])
        self.assertDeleteWorks()

    def testDeleteParentAndGrandchild(self):
        self.delete([self.parent, self.grandchild])
        self.assertDeleteWorks()

    def testDeleteLastNotCompletedChildMarksParentAsCompleted(self):
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.markCompleted([self.child2])
        self.delete([self.child])
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.parent.completed()),
            lambda: self.assertFalse(self.parent.completed()),
        )

    def testDeleteParentAndChildWhenChildBelongsToCategory(self):
        self.category.addCategorizable(self.child)
        self.child.addCategory(self.category)
        self.delete([self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.category.categorizables()),
            lambda: self.assertEqual(
                set([self.child]), self.category.categorizables()
            ),
        )

    def testDeleteParentAndChildWhenParentAndChildBelongToDifferentCategories(
        self,
    ):
        cat1 = category.Category("category 1")
        cat2 = category.Category("category 2")
        self.categories.extend([cat1, cat2])
        cat1.addCategorizable(self.child)
        self.child.addCategory(cat1)
        cat2.addCategorizable(self.parent)
        self.parent.addCategory(cat2)
        self.delete([self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(
                cat1.categorizables() or cat2.categorizables()
            ),
            lambda: self.assertTrue(
                set([self.child]) == cat1.categorizables()
                and set([self.parent]) == cat2.categorizables()
            ),
        )

    def testDeleteParentAndChildWhenParentAndChildBelongToSameCategory(self):
        for eachTask in self.parent, self.child:
            self.category.addCategorizable(eachTask)
            eachTask.addCategory(self.category)
        self.delete([self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.category.categorizables()),
            lambda: self.assertEqualLists(
                [self.parent, self.child], self.category.categorizables()
            ),
        )


class DeleteCommandWithTasksWithEffortTest(CommandWithEffortTestCase):
    def testDeleteActiveTask(self):
        self.list = self.taskList
        self.delete([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(1, len(self.effortList)),
            lambda: self.assertEqual(2, len(self.effortList)),
        )


class NewTaskCommandTest(TaskCommandTestCase):
    def new(self, **kwargs):
        newTaskCommand = command.NewTaskCommand(self.taskList, **kwargs)
        newTask = newTaskCommand.items[0]
        newTaskCommand.do()
        return newTask

    def testNewTask(self):
        newTask = self.new()
        self.assertDoUndoRedo(
            lambda: self.assertTaskList([self.task1, newTask]),
            lambda: self.assertTaskList(self.originalList),
        )

    def testNewTaskWithCategory(self):
        cat = category.Category("cat")
        newTask = self.new(categories=[cat])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(set([cat]), newTask.categories()),
            lambda: self.assertTaskList(self.originalList),
        )

    def testNewTaskWithCategory_AddsTaskToCategory(self):
        cat = category.Category("cat")
        newTask = self.new(categories=[cat])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(set([newTask]), cat.categorizables()),
            lambda: self.assertFalse(cat.categorizables()),
        )

    def testNewTaskWithPrerequisite(self):
        newTask = self.new(prerequisites=[self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.task1]), newTask.prerequisites()
            ),
            lambda: self.assertTaskList(self.originalList),
        )

    def testNewTaskWithPrerequisite_AddsDependency(self):
        newTask = self.new(prerequisites=[self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([newTask]), self.task1.dependencies()
            ),
            lambda: self.assertFalse(self.task1.dependencies()),
        )

    def testNewTaskWithDependency(self):
        newTask = self.new(dependencies=[self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.task1]), newTask.dependencies()
            ),
            lambda: self.assertTaskList(self.originalList),
        )

    def testNewTaskWithDependency_AddsPrerequisite(self):
        newTask = self.new(dependencies=[self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([newTask]), self.task1.prerequisites()
            ),
            lambda: self.assertFalse(self.task1.prerequisites()),
        )

    def testNewTaskWithAttachment(self):
        att = attachment.FileAttachment("filename")
        newTask = self.new(attachments=[att])
        self.assertDoUndoRedo(
            lambda: self.assertEqual([att], newTask.attachments()),
            lambda: self.assertTaskList(self.originalList),
        )

    def testNewTaskWithKeywords(self):
        dateTime = date.DateTime(2042, 2, 3)
        newTask = self.new(plannedStartDateTime=dateTime)
        self.assertEqual(dateTime, newTask.plannedStartDateTime())

    def testItemsAreNew(self):
        self.assertTrue(command.NewTaskCommand(self.taskList).items_are_new())


class NewSubTaskCommandTest(TaskCommandTestCase):
    def testNewSubTask_WithoutSelection(self):
        self.newSubTask()
        self.assertDoUndoRedo(lambda: self.assertTaskList(self.originalList))

    def testNewSubTask(self):
        self.newSubTask([self.task1])
        newSubTask = self.task1.children()[0]
        self.assertDoUndoRedo(
            lambda: self.assertNewSubTask(newSubTask),
            lambda: self.assertTaskList(self.originalList),
        )

    def assertNewSubTask(self, newSubTask):
        self.assertEqual(len(self.originalList) + 1, len(self.taskList))
        self.assertEqualLists([newSubTask], self.task1.children())

    def testNewSubTask_MarksParentAsNotCompleted(self):
        self.markCompleted([self.task1])
        self.newSubTask([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.task1.completed()),
            lambda: self.assertTrue(self.task1.completed()),
        )

    def testNewSubTask_MarksGrandParentAsNotCompleted(self):
        self.newSubTask([self.task1])
        self.markCompleted([self.task1])
        self.newSubTask([self.task1.children()[0]])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.task1.completed()),
            lambda: self.assertTrue(self.task1.completed()),
        )

    def testNewCompletedSubTask(self):
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.newSubTask([self.task1], markCompleted=True)
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.task1.completed()),
            lambda: self.assertFalse(self.task1.completed()),
        )

    def testNewSubTaskWithoutDueDateDoesntResetParentsDueDate(self):
        dueDateTime = date.Now() + date.TWO_HOURS
        self.task1.setDueDateTime(dueDateTime)
        self.newSubTask([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(dueDateTime, self.task1.dueDateTime())
        )

    def testItemsAreNew(self):
        self.assertTrue(
            command.NewSubTaskCommand(self.taskList, []).items_are_new()
        )


class MarkCompletedCommandTest(CommandWithChildrenTestCase):
    def testMarkCompleted(self):
        self.markCompleted([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.task1.completed()),
            lambda: self.assertFalse(self.task1.completed()),
        )

    def testMarkCompleted_TaskAlreadyCompleted(self):
        self.task1.setCompletionDateTime()
        self.markCompleted([self.task1])
        self.assertDoUndoRedo(lambda: self.assertTrue(self.task1.completed()))

    def testMarkCompletedParent(self):
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

    def testMarkCompletedParent_WhenChildAlreadyCompleted(self):
        self.markCompleted([self.child])
        self.markCompleted([self.parent])
        self.assertDoUndoRedo(lambda: self.assertTrue(self.child.completed()))

    def testMarkCompletedGrandChild(self):
        self.settings.setboolean(
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

    def testMarkCompletedStopsEffortTracking(self):
        self.task1.addEffort(effort.Effort(self.task1))
        self.markCompleted([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.task1.isBeingTracked()),
            lambda: self.assertTrue(self.task1.isBeingTracked()),
        )

    def testMarkCompletedChildDoesNotStopEffortTrackingOfParent(self):
        self.parent.addEffort(effort.Effort(self.parent))
        self.markCompleted([self.child])
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.parent.isBeingTracked())
        )

    def testMarkRecurringTaskCompleted_CompletionDateIsNotSet(self):
        self.task1.setRecurrence(date.Recurrence("weekly"))
        self.markCompleted([self.task1])
        self.assertDoUndoRedo(lambda: self.assertFalse(self.task1.completed()))

    def testMarkRecurringTaskCompleted_PlannedStartDateIsIncreased(self):
        self.task1.setRecurrence(date.Recurrence("weekly"))
        plannedStartDateTime = self.task1.plannedStartDateTime()
        newPlannedStartDateTime = plannedStartDateTime + date.TimeDelta(days=7)
        self.markCompleted([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                newPlannedStartDateTime, self.task1.plannedStartDateTime()
            ),
            lambda: self.assertEqual(
                plannedStartDateTime, self.task1.plannedStartDateTime()
            ),
        )

    def testMarkRecurringTaskCompleted_DueDateIsIncreased(self):
        self.task1.setRecurrence(date.Recurrence("weekly"))
        tomorrow = date.Tomorrow()
        self.task1.setDueDateTime(tomorrow)
        newDueDate = tomorrow + date.ONE_WEEK
        self.markCompleted([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(newDueDate, self.task1.dueDateTime()),
            lambda: self.assertEqual(tomorrow, self.task1.dueDateTime()),
        )

    def testMarkRecurringTaskCompleted_ActualStartDateIsReset(self):
        self.task1.setRecurrence(date.Recurrence("weekly"))
        now = date.Now()
        self.task1.setActualStartDateTime(now)
        self.markCompleted([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            ),
            lambda: self.assertEqual(now, self.task1.actualStartDateTime()),
        )

    def testMarkParentWithRecurringChildCompleted_RemovesChildRecurrence(self):
        self.child.setRecurrence(date.Recurrence("daily"))
        self.markCompleted([self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.child.recurrence()),
            lambda: self.assertEqual(
                date.Recurrence("daily"), self.child.recurrence()
            ),
        )

    def testMarkParentWithRecurringChildCompleted_MakesChildCompleted(self):
        self.child.setRecurrence(date.Recurrence("daily"))
        self.markCompleted([self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.child.completed()),
            lambda: self.assertFalse(self.child.completed()),
        )


class EditPercentageCompleteTest(TaskCommandTestCase):
    def testEditPercentageComplete(self):
        self.editPercentageComplete([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(50, self.task1.percentageComplete()),
            lambda: self.assertEqual(0, self.task1.percentageComplete()),
        )

    def testTaskIsStartedAfterEditingPercentageComplete(self):
        self.editPercentageComplete([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertNotEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            ),
            lambda: self.assertEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            ),
        )


class MarkActiveCommandTest(TaskCommandTestCase):
    def testMarkInactiveTaskActive(self):
        self.markActive([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertNotEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            ),
            lambda: self.assertEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            ),
        )

    def testMarkCompletedTaskActive(self):
        now = date.Now()
        self.task1.setCompletionDateTime(now)
        self.markActive([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                date.DateTime(), self.task1.completionDateTime()
            ),
            lambda: self.assertEqual(now, self.task1.completionDateTime()),
        )

    def testIgnoreTaskThatIsAlreadyActive(self):
        now = date.Now()
        self.task1.setActualStartDateTime(now)
        self.markActive([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(now, self.task1.actualStartDateTime())
        )

    def testTaskWithFutureActualStartDateTime(self):
        tomorrow = date.Tomorrow()
        self.task1.setActualStartDateTime(tomorrow)
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
    def testMarkActiveTaskInactive(self):
        now = date.Now()
        self.task1.setActualStartDateTime(now)
        self.markInactive([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            ),
            lambda: self.assertEqual(now, self.task1.actualStartDateTime()),
        )

    def testMarkCompletedTaskInactive(self):
        now = date.Now()
        self.task1.setCompletionDateTime(now)
        self.markInactive([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                date.DateTime(), self.task1.completionDateTime()
            ),
            lambda: self.assertEqual(now, self.task1.completionDateTime()),
        )

    def testIgnoreTaskThatIsAlreadyInactive(self):
        self.markInactive([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                date.DateTime(), self.task1.actualStartDateTime()
            )
        )

    def testTaskWithFutureActualStartDateTime(self):
        tomorrow = date.Tomorrow()
        self.task1.setActualStartDateTime(tomorrow)
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
    def testCannotDropOnParent(self):
        self.dragAndDrop([self.parent], [self.child])
        self.assertFalse(patterns.CommandHistory().hasHistory())

    def testCannotDropOnChild(self):
        self.dragAndDrop([self.child], [self.parent])
        self.assertFalse(patterns.CommandHistory().hasHistory())

    def testCannotDropOnGrandchild(self):
        self.dragAndDrop([self.grandchild], [self.parent])
        self.assertFalse(patterns.CommandHistory().hasHistory())

    def testDropAsRootTask(self):
        self.dragAndDrop([], [self.grandchild])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(None, self.grandchild.parent()),
            lambda: self.assertEqual(self.child, self.grandchild.parent()),
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

    def testEmptySelection(self):
        self.max_priority()
        self.assertDoUndoRedo(0, 0, 0, 0)

    def testOneTaskWhenBothTasksHaveSamePriority(self):
        self.max_priority([self.task1])
        self.assertDoUndoRedo(1, 0, 0, 0)

    def testBothTasksWhenBothTasksHaveSamePriority(self):
        self.max_priority([self.task1, self.task2])
        self.assertDoUndoRedo(1, 1, 0, 0)

    def testMakeLowestPriorityTheMaxPriority(self):
        self.task2.setPriority(2)
        self.max_priority([self.task1])
        self.assertDoUndoRedo(3, 2, 0, 2)


class MinPriorityCommandTest(PriorityCommandTestCase):
    def min_priority(self, tasks=None):
        command.MinPriorityCommand(self.taskList, tasks or []).do()

    def testEmptySelection(self):
        self.min_priority()
        self.assertDoUndoRedo(0, 0, 0, 0)

    def testOneTaskWhenBothTasksHaveSamePriority(self):
        self.min_priority([self.task1])
        self.assertDoUndoRedo(-1, 0, 0, 0)

    def testBothTasksWhenBothTasksHaveSamePriority(self):
        self.min_priority([self.task1, self.task2])
        self.assertDoUndoRedo(-1, -1, 0, 0)

    def testMakeLowestPriorityTheMaxPriority(self):
        self.task2.setPriority(-2)
        self.min_priority([self.task1])
        self.assertDoUndoRedo(-3, -2, 0, -2)


class IncreasePriorityCommandTest(PriorityCommandTestCase):
    def incPriority(self, tasks=None):
        command.IncPriorityCommand(self.taskList, tasks or []).do()

    def testEmptySelection(self):
        self.incPriority()
        self.assertDoUndoRedo(0, 0, 0, 0)

    def testOneTaskWhenBothTasksHaveSamePriority(self):
        self.incPriority([self.task1])
        self.assertDoUndoRedo(1, 0, 0, 0)

    def testBothTasksWhenBothTasksHaveSamePriority(self):
        self.incPriority([self.task1, self.task2])
        self.assertDoUndoRedo(1, 1, 0, 0)

    def testIncLowestPriority(self):
        self.task2.setPriority(-2)
        self.incPriority([self.task2])
        self.assertDoUndoRedo(0, -1, 0, -2)


class DecreasePriorityCommandTest(PriorityCommandTestCase):
    def decPriority(self, tasks=None):
        command.DecPriorityCommand(self.taskList, tasks or []).do()

    def testEmptySelection(self):
        self.decPriority()
        self.assertDoUndoRedo(0, 0, 0, 0)

    def testOneTaskWhenBothTasksHaveSamePriority(self):
        self.decPriority([self.task1])
        self.assertDoUndoRedo(-1, 0, 0, 0)

    def testBothTasksWhenBothTasksHaveSamePriority(self):
        self.decPriority([self.task1, self.task2])
        self.assertDoUndoRedo(-1, -1, 0, 0)

    def testDecLowestPriority(self):
        self.task2.setPriority(-2)
        self.decPriority([self.task2])
        self.assertDoUndoRedo(0, -3, 0, -2)


class EditReminderCommandTest(TaskCommandTestCase):
    def editReminder(self, tasks=None):
        command.EditReminderDateTimeCommand(
            self.taskList, tasks or [], newValue=date.Now() + date.ONE_HOUR
        ).do()

    def testEditReminder(self):
        self.editReminder([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.task1.reminder()),
            lambda: self.assertFalse(self.task1.reminder()),
        )


class AddNoteCommandTest(TaskCommandTestCase):
    def addNote(self, tasks=None):
        command.AddNoteCommand(self.taskList, tasks or []).do()

    # pylint: disable=E1101

    def testEmptySelection(self):
        self.addNote()
        self.assertDoUndoRedo(lambda: self.assertFalse(self.task1.notes()))

    def testAddNote(self):
        self.addNote([self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.task1.notes()),
            lambda: self.assertFalse(self.task1.notes()),
        )

    def testAddNoteToMultipleTasksAtOnce(self):
        self.addNote([self.task1, self.task2])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(
                self.task1.notes()[0] == self.task2.notes()[0]
            ),
            lambda: self.assertFalse(self.task1.notes() or self.task2.notes()),
        )


class EditDuePlannedStartDateCommandTest(TaskCommandTestCase):
    def testSetPlannedStartDateToTomorrow(self):
        previousStart = self.task1.plannedStartDateTime()
        newStart = date.Now() + date.ONE_HOUR
        self.editPlannedStart(newStart, [self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                newStart, self.task1.plannedStartDateTime()
            ),
            lambda: self.assertEqual(
                previousStart, self.task1.plannedStartDateTime()
            ),
        )

    def testSetDueDateToTomorrow(self):
        previousDue = self.task1.dueDateTime()
        newDue = date.Now() + date.ONE_HOUR
        self.editDue(newDue, [self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(newDue, self.task1.dueDateTime()),
            lambda: self.assertEqual(previousDue, self.task1.dueDateTime()),
        )

    def testPushingBackPlannedStartDatePushesBackDueDate(self):
        self.task1.setDueDateTime(date.Now() + date.TWO_HOURS)
        previousPlannedStart = self.task1.plannedStartDateTime()
        previousDue = self.task1.dueDateTime()
        pushBack = date.ONE_HOUR
        newPlannedStart = previousPlannedStart + pushBack
        expectedDue = previousDue + pushBack
        self.editPlannedStart(newPlannedStart, [self.task1], keep_delta=True)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(expectedDue, self.task1.dueDateTime()),
            lambda: self.assertEqual(previousDue, self.task1.dueDateTime()),
        )

    def testPushingBackDueDatePushesBackPlannedStartDate(self):
        self.task1.setDueDateTime(date.Now() + date.TWO_HOURS)
        previousPlannedStart = self.task1.plannedStartDateTime()
        previousDue = self.task1.dueDateTime()
        pushBack = date.ONE_HOUR
        newDue = previousDue + pushBack
        expectedPlannedStart = previousPlannedStart + pushBack
        self.editDue(newDue, [self.task1], keep_delta=True)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                expectedPlannedStart, self.task1.plannedStartDateTime()
            ),
            lambda: self.assertEqual(
                previousPlannedStart, self.task1.plannedStartDateTime()
            ),
        )

    def testPushingBackPlannedStartDateDoesNotPushBackDueDate(self):
        self.task1.setDueDateTime(date.Now() + date.TWO_HOURS)
        previousPlannedStart = self.task1.plannedStartDateTime()
        previousDue = self.task1.dueDateTime()
        pushBack = date.ONE_HOUR
        newPlannedStart = previousPlannedStart + pushBack
        expectedDue = previousDue
        self.editPlannedStart(newPlannedStart, [self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(expectedDue, self.task1.dueDateTime()),
            lambda: self.assertEqual(previousDue, self.task1.dueDateTime()),
        )

    def testPushingBackDueDateDoesNotPushBackPlannedStartDate(self):
        self.task1.setDueDateTime(date.Now() + date.TWO_HOURS)
        previousPlannedStart = self.task1.plannedStartDateTime()
        previousDue = self.task1.dueDateTime()
        pushBack = date.ONE_HOUR
        newDue = previousDue + pushBack
        expectedPlannedStart = previousPlannedStart
        self.editDue(newDue, [self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                expectedPlannedStart, self.task1.plannedStartDateTime()
            ),
            lambda: self.assertEqual(
                previousPlannedStart, self.task1.plannedStartDateTime()
            ),
        )

    def testMissingDueDateIsNotPushedBack(self):
        previousPlannedStart = self.task1.plannedStartDateTime()
        pushBack = date.ONE_HOUR
        newPlannedStart = previousPlannedStart + pushBack
        expectedDue = date.DateTime()
        self.task1.setDueDateTime(expectedDue)
        self.editPlannedStart(newPlannedStart, [self.task1], keep_delta=True)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(expectedDue, self.task1.dueDateTime())
        )

    def testMissingPlannedStartDateIsNotPushedBack(self):
        self.task1.setPlannedStartDateTime(date.DateTime())
        self.task1.setDueDateTime(date.Now() + date.TWO_HOURS)
        previousDue = self.task1.dueDateTime()
        pushBack = date.ONE_HOUR
        newDue = previousDue + pushBack
        expectedStart = date.DateTime()
        self.editDue(newDue, [self.task1], keep_delta=True)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                expectedStart, self.task1.plannedStartDateTime()
            )
        )

    def testDueDateIsNotPushedBackWhenPlannedStartDateIsMissing(self):
        self.task1.setPlannedStartDateTime(date.DateTime())
        self.task1.setDueDateTime(date.Now() + date.TWO_HOURS)
        pushBack = date.ONE_HOUR
        newStart = date.Now() + pushBack
        expectedDue = self.task1.dueDateTime()
        self.editPlannedStart(newStart, [self.task1], keep_delta=True)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(expectedDue, self.task1.dueDateTime())
        )

    def testPlannedStartDateIsNotPushedBackWhenDueDateIsMissing(self):
        pushBack = date.ONE_HOUR
        newDue = date.Now() + pushBack
        expectedStart = self.task1.plannedStartDateTime()
        self.task1.setDueDateTime(date.DateTime())
        self.editDue(newDue, [self.task1], keep_delta=True)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                expectedStart, self.task1.plannedStartDateTime()
            )
        )

    def testSetInfinitePlannedStartDate(self):
        newPlannedStartDateTime = date.DateTime()
        originalPlannedStartDateTime = self.task1.plannedStartDateTime()
        self.editPlannedStart(newPlannedStartDateTime, [self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                newPlannedStartDateTime, self.task1.plannedStartDateTime()
            ),
            lambda: self.assertEqual(
                originalPlannedStartDateTime, self.task1.plannedStartDateTime()
            ),
        )

    def testSetInfinitePlannedStartDateDoesNotChangeDueDate(self):
        newPlannedStartDateTime = date.DateTime()
        originalDueDateTime = self.task1.dueDateTime()
        self.editPlannedStart(
            newPlannedStartDateTime, [self.task1], keep_delta=True
        )
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                originalDueDateTime, self.task1.dueDateTime()
            )
        )

    def testSetInfiniteDueDate(self):
        newDueDateTime = date.DateTime()
        originalDueDateTime = self.task1.dueDateTime()
        self.editDue(newDueDateTime, [self.task1])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(newDueDateTime, self.task1.dueDateTime()),
            lambda: self.assertEqual(
                originalDueDateTime, self.task1.dueDateTime()
            ),
        )

    def testSetInfiniteDueDateDoesNotChangePlannedStartDate(self):
        newDueDateTime = date.DateTime()
        originalPlannedStartDateTime = self.task1.plannedStartDateTime()
        self.editDue(newDueDateTime, [self.task1], keep_delta=True)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                originalPlannedStartDateTime, self.task1.plannedStartDateTime()
            )
        )
