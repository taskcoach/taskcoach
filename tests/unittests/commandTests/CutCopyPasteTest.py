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
from .TaskCommandsTest import (
    TaskCommandTestCase,
    CommandWithChildrenTestCase,
    CommandWithEffortTestCase,
)
from taskcoachlib import command
from taskcoachlib.domain import note


class CutCommandWithTasksTest(TaskCommandTestCase):
    def testCutTasks_WithoutSelection(self):
        self.cut()
        self.assertDoUndoRedo(lambda: self.assertTaskList([self.task1]))

    def testCutTasks_SpecificTask(self):
        self.taskList.append(self.task2)
        self.cut([self.task1])
        self.assertDoUndoRedo(
            lambda: (
                self.assertTaskList([self.task2]),
                self.assertEqual([self.task1], command.Clipboard().get()[0]),
            ),
            lambda: (
                self.assertTaskList([self.task1, self.task2]),
                self.assertFalse(command.Clipboard()),
            ),
        )

    def testCutTasks_All(self):
        self.cut("all")
        self.assertDoUndoRedo(
            self.assertEmptyTaskList,
            lambda: self.assertTaskList(self.originalList),
        )

    def test_cut_task_is_no_member_in_the_list(self):
        # A cut task keeps its categories, to take them with it
        self.task1.addCategory(self.category)
        self.cut("all")
        self.assertDoUndoRedo(
            lambda: self.assertFalse(
                self.category.members() & set(self.taskList)
            ),
            lambda: self.assertEqual(
                {self.task1},
                self.category.members() & set(self.taskList),
            ),
        )


class CutCommandWithTasksWithChildrenTest(CommandWithChildrenTestCase):
    def testCutParent(self):
        self.cut([self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertTaskList([self.task1]),
            lambda: self.assertTaskList(self.originalList),
        )

    def testCutChild(self):
        self.cut([self.child])
        self.assertDoUndoRedo(
            lambda: (
                self.assertTaskList([self.task1, self.child2, self.parent]),
                self.assertEqual([self.child2], self.parent.children()),
            ),
            lambda: (
                self.assertTaskList(self.originalList),
                self.failUnlessParentAndChild(self.parent, self.child),
            ),
        )

    def testCutParentAndChild(self):
        self.cut([self.child, self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertTaskList([self.task1]),
            lambda: self.assertTaskList(self.originalList),
        )


class CutCommandWithEffortTest(CommandWithEffortTestCase):
    def testCutEfforts_WithoutSelection(self):
        self.cut()
        self.assertDoUndoRedo(
            lambda: self.assertEffortList(self.originalEffortList)
        )

    def testCutEfforts_Selection(self):
        self.cut([self.effort1])
        self.assertDoUndoRedo(
            lambda: self.assertEffortList([self.effort2]),
            lambda: self.assertEffortList(self.originalEffortList),
        )

    def testCutEfforts_All(self):
        self.cut("all")
        self.assertDoUndoRedo(
            lambda: self.assertEffortList([]),
            lambda: self.assertEffortList(self.originalEffortList),
        )


class NoteCommandTestCase(CommandTestCase, asserts.Mixin):
    def setUp(self):
        super().setUp()
        self.note1 = note.Note()
        self.note2 = note.Note()
        self.list = self.noteContainer = note.NoteContainer(
            [self.note1, self.note2]
        )
        self.original = note.NoteContainer([self.note1, self.note2])


class CutCommandWithNotes(NoteCommandTestCase):
    def testCutNotes_WithoutSelection(self):
        self.cut()
        self.assertDoUndoRedo(lambda: self.assertNoteContainer(self.original))

    def testCutNotes_Selection(self):
        self.cut([self.note1])
        self.assertDoUndoRedo(
            lambda: self.assertNoteContainer(note.NoteContainer([self.note2])),
            lambda: self.assertNoteContainer(self.original),
        )

    def testCutNotes_All(self):
        self.cut("all")
        self.assertDoUndoRedo(
            lambda: self.assertNoteContainer(note.NoteContainer()),
            lambda: self.assertNoteContainer(self.original),
        )


class PasteCommandWithTasksTest(TaskCommandTestCase):
    def testPasteWithoutPreviousCut(self):
        self.paste()
        self.assertDoUndoRedo(lambda: self.assertTaskList(self.originalList))

    def testPaste(self):
        self.cut([self.task1])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(1, len(self.taskList)),
            self.assertEmptyTaskList,
        )

    def testClipboardIsNotEmptyAfterPaste(self):
        self.cut([self.task1])
        self.paste()
        # pylint: disable=W0212
        self.assertDoUndoRedo(
            lambda: self.assertEqual(1, len(command.Clipboard()._contents))
        )

    def test_the_first_paste_after_a_cut_moves_the_task(self):
        self.cut([self.task1])
        self.paste()
        self.assertTrue(any(each is self.task1 for each in self.taskList))

    def test_a_second_paste_after_a_cut_pastes_a_copy(self):
        self.cut([self.task1])
        self.paste()
        self.paste()
        ids = [each.id() for each in self.taskList]
        self.assertEqual((2, True), (len(set(ids)), self.task1.id() in ids))

    def test_a_paste_after_a_copy_pastes_a_copy(self):
        command.CopyCommand(self.taskList, [self.task1]).do()
        self.paste()
        self.assertEqual(2, len({each.id() for each in self.taskList}))

    def test_a_paste_after_redoing_the_cut_and_its_paste_pastes_a_copy(self):
        self.cut([self.task1])
        self.paste()
        self.undo()
        self.undo()
        self.redo()
        self.redo()
        self.paste()
        ids = [each.id() for each in self.taskList]
        self.assertEqual((2, True), (len(set(ids)), self.task1.id() in ids))


class PasteCommandWithNotesTest(NoteCommandTestCase):
    def testPasteWithoutPreviousCut(self):
        self.paste()
        self.assertDoUndoRedo(lambda: self.assertNoteContainer(self.original))

    def testPaste(self):
        self.cut([self.note1])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(2, len(self.original)),
            lambda: self.assertNoteContainer([self.note2]),
        )


class PasteCommandWithEffortTest(CommandWithEffortTestCase):
    def testPasteWithoutPreviousCut(self):
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEffortList(self.originalEffortList)
        )

    def testPaste(self):
        self.cut([self.effort1])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(2, len(self.originalEffortList)),
            lambda: self.assertEqualLists([self.effort2], self.effortList),
        )

    def testClipboardIsNotEmptyAfterPaste(self):
        self.cut([self.effort1])
        self.paste()
        # pylint: disable=W0212
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                [self.effort1], command.Clipboard()._contents
            )
        )


class PasteCommandWithTasksWithChildrenTest(CommandWithChildrenTestCase):
    def testCutAndPasteChild(self):
        self.cut([self.child])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(5, len(self.taskList)),
            lambda: self.assertTaskList(
                [self.task1, self.parent, self.child2]
            ),
        )

    def testCutAndPasteParentAndChild(self):
        self.cut([self.parent, self.child])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(5, len(self.taskList)),
            lambda: self.assertTaskList([self.task1]),
        )

    def testCutAndPasteParentAndGrandChild(self):
        self.cut([self.parent, self.grandchild])
        self.paste()
        self.assertDoUndoRedo(
            lambda: (
                self.assertEqual(5, len(self.taskList)),
                self.failUnlessParentAndChild(self.parent, self.child),
            ),
            lambda: self.assertTaskList([self.task1]),
        )


class PasteIntoTaskCommandTest(CommandWithChildrenTestCase):
    def testPasteChild(self):
        self.cut([self.child])
        self.paste([self.task1])
        self.assertDoUndoRedo(
            lambda: (
                self.assertEqual(5, len(self.taskList)),
                self.assertEqual(1, len(self.task1.children())),
                self.failUnlessParentAndChild(self.child, self.grandchild),
            ),
            lambda: (
                self.assertEqual(1, len(self.parent.children())),
                self.assertEqual([], self.task1.children()),
            ),
        )

    def testPasteExtraChild(self):
        self.cut([self.task1])
        self.paste([self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(3, len(self.parent.children())),
            lambda: (
                self.assertEqual(2, len(self.parent.children())),
                self.assertTaskList(
                    [self.parent, self.child, self.child2, self.grandchild]
                ),
            ),
        )

    def testPasteChild_MarksNewParentAsNotCompleted(self):
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.markCompleted([self.parent])
        self.cut([self.task1])
        self.paste([self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.parent.completed()),
            lambda: self.assertTrue(self.parent.completed()),
        )

    def testPasteCompletedChild_DoesNotMarkParentAsNotCompleted(self):
        self.markCompleted([self.task1, self.parent])
        self.cut([self.task1])
        self.paste([self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.parent.completed()),
            lambda: self.assertTrue(self.parent.completed()),
        )


class PasteIntoTaskCommandWithEffortTest(CommandWithEffortTestCase):
    def test_paste(self):
        self.cut([self.effort1])
        # As the task viewer does: efforts go back to their own list,
        # with the task as their parent
        command.PasteAsSubItemCommand(items=[self.task2]).do()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(2, len(self.task2.efforts())),
            lambda: self.assertEqual(1, len(self.task1.efforts())),
        )


class CutAndPasteTasksIntegrationTest(TaskCommandTestCase):
    def testUndoCutAndPaste(self):
        self.cut([self.task1])
        self.paste()
        self.undo()
        self.undo()
        self.assertTaskList(self.originalList)


class CutAndPasteWithChildrenIntegrationTest(CommandWithChildrenTestCase):
    def assertTaskListUnchanged(self):
        self.assertTaskList(self.originalList)
        self.failUnlessParentAndChild(self.parent, self.child)
        self.failUnlessParentAndChild(self.child, self.grandchild)

    def testUndoCutAndPaste(self):
        self.cut([self.child])
        self.paste()
        self.undo()
        self.undo()
        self.assertTaskListUnchanged()

    def testUndoCutAndPasteAsSubtask(self):
        self.cut([self.child])
        self.paste([self.child2])
        self.undo()
        self.undo()
        self.assertTaskListUnchanged()

    def testUndoCutAndPasteParentAndGrandChild(self):
        self.cut([self.parent, self.grandchild])
        self.paste()
        self.undo()
        self.undo()
        self.assertTaskListUnchanged()

    def testRedoCutAndPasteParentAndGrandChild(self):
        self.cut([self.parent, self.grandchild])
        self.paste()
        self.undo()
        self.undo()
        self.redo()
        self.redo()
        self.assertEqual(5, len(self.taskList))
        self.assertFalse(self.child.children())


class CopyCommandWithTasksTest(TaskCommandTestCase):
    def testCopyTaskWithoutSelection(self):
        self.copy([])
        self.assertDoUndoRedo(
            lambda: self.assertEqual([], command.Clipboard().get()[0]),
            self.assertTaskList(self.originalList),
        )

    def testCopyTask(self):
        self.copy([self.task1])
        copiedTask = command.Clipboard().get()[0][0]
        self.assertDoUndoRedo(
            lambda: (
                self.assertTaskCopy(self.task1, copiedTask),
                self.assertTaskList(self.originalList),
            ),
            lambda: (
                self.assertTaskList(self.originalList),
                self.assertFalse(command.Clipboard()),
            ),
        )


class CopyCommandWithTasksWithChildrenTest(CommandWithChildrenTestCase):
    def testCopy(self):
        self.copy([self.parent])
        copiedTask = command.Clipboard().get()[0][0]
        self.assertDoUndoRedo(
            lambda: self.assertTaskCopy(self.parent, copiedTask),
            lambda: (
                self.assertTaskList(self.originalList),
                self.assertFalse(command.Clipboard()),
            ),
        )


class CopyCommandWithEffortTest(CommandWithEffortTestCase):
    def testCopyEffortWithoutSelection(self):
        self.copy([])
        self.assertDoUndoRedo(
            lambda: self.assertEqual([], command.Clipboard().get()[0]),
            self.assertEffortList(self.originalEffortList),
        )

    def testCopyEffort(self):
        self.copy([self.effort1])
        copiedEffort = command.Clipboard().get()[0][0]
        self.assertDoUndoRedo(
            lambda: self.assertEqualEfforts(self.effort1, copiedEffort),
            lambda: (
                self.assertEffortList(self.originalEffortList),
                self.assertFalse(command.Clipboard()),
            ),
        )

    def testCopyMultipleEfforts(self):
        self.copy([self.effort1, self.effort2])
        copiedEfforts = command.Clipboard().get()[0]
        self.assertDoUndoRedo(
            lambda: (
                self.assertEqualEfforts(self.effort1, copiedEfforts[0]),
                self.assertEqualEfforts(self.effort2, copiedEfforts[1]),
            ),
            lambda: (
                self.assertEffortList(self.originalEffortList),
                self.assertFalse(command.Clipboard()),
            ),
        )


class DragAndDropWithTasksTest(CommandWithChildrenTestCase):
    def dragAndDrop(self, draggedItems, dropItem):  # pylint: disable=W0222
        command.DragAndDropTaskCommand(
            self.taskList, draggedItems, drop=[dropItem]
        ).do()

    def testDragAndDropRootTask(self):
        self.taskList.append(self.task2)
        self.dragAndDrop([self.task2], self.task1)
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.task2 in self.task1.children()),
            lambda: self.assertFalse(self.task2 in self.task1.children()),
        )

    def testDontAllowDropOnSelf(self):
        self.dragAndDrop([self.task1], self.task1)
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.task1 in self.task1.children())
        )

    def testDragChildTaskAndDropOnOtherRootTask(self):
        self.dragAndDrop([self.child2], self.task1)
        self.assertDoUndoRedo(
            lambda: (
                self.assertTrue(self.child2 in self.task1.children()),
                self.assertFalse(self.child2 in self.parent.children()),
            ),
            lambda: (
                self.assertFalse(self.child2 in self.task1.children()),
                self.assertTrue(self.child2 in self.parent.children()),
            ),
        )

    def testDragChildAndDropOnOwnParent(self):
        self.dragAndDrop([self.child2], self.parent)
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.child2 in self.parent.children())
        )

    def testDragParentAndDropOnOwnChild(self):
        self.dragAndDrop([self.parent], self.child2)
        self.assertDoUndoRedo(
            lambda: (
                self.assertTrue(self.child2 in self.parent.children()),
                self.assertFalse(self.parent in self.child2.children()),
            )
        )
