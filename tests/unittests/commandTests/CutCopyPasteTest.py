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
from taskcoachlib import command, patterns
from taskcoachlib.config import settings
from taskcoachlib.domain import base, note, task


class CutCommandWithTasksTest(TaskCommandTestCase):
    def test_cut_tasks_without_selection(self):
        self.cut()
        self.assertDoUndoRedo(lambda: self.assertTaskList([self.task1]))

    def test_cut_tasks_specific_task(self):
        self.taskList.append(self.task2)
        self.cut([self.task1])
        self.assertDoUndoRedo(
            lambda: (
                self.assertTaskList([self.task2]),
                self.assertEqual([self.task1], command.Clipboard().get()[0]),
            ),
            lambda: (
                self.assertTaskList([self.task1, self.task2]),
                # The clipboard is not undone (docs/UNDO_REDO.md)
                self.assertEqual([self.task1], command.Clipboard().get()[0]),
            ),
        )

    def test_cut_tasks_all(self):
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
    def test_cut_parent(self):
        self.cut([self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertTaskList([self.task1]),
            lambda: self.assertTaskList(self.originalList),
        )

    def test_cut_child(self):
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

    def test_cut_parent_and_child(self):
        self.cut([self.child, self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertTaskList([self.task1]),
            lambda: self.assertTaskList(self.originalList),
        )


class CutCommandWithEffortTest(CommandWithEffortTestCase):
    def test_cut_efforts_without_selection(self):
        self.cut()
        self.assertDoUndoRedo(
            lambda: self.assertEffortList(self.originalEffortList)
        )

    def test_cut_efforts_selection(self):
        self.cut([self.effort1])
        self.assertDoUndoRedo(
            lambda: self.assertEffortList([self.effort2]),
            lambda: self.assertEffortList(self.originalEffortList),
        )

    def test_cut_efforts_all(self):
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
        self.list = self.noteContainer = self.task_file.notes()
        self.noteContainer.extend([self.note1, self.note2])
        self.original = note.NoteContainer([self.note1, self.note2])


class CutCommandWithNotes(NoteCommandTestCase):
    def test_cut_notes_without_selection(self):
        self.cut()
        self.assertDoUndoRedo(lambda: self.assertNoteContainer(self.original))

    def test_cut_notes_selection(self):
        self.cut([self.note1])
        self.assertDoUndoRedo(
            lambda: self.assertNoteContainer(note.NoteContainer([self.note2])),
            lambda: self.assertNoteContainer(self.original),
        )

    def test_cut_notes_all(self):
        self.cut("all")
        self.assertDoUndoRedo(
            lambda: self.assertNoteContainer(note.NoteContainer()),
            lambda: self.assertNoteContainer(self.original),
        )


class PasteCommandWithTasksTest(TaskCommandTestCase):
    def test_paste_without_previous_cut(self):
        self.paste()
        self.assertDoUndoRedo(lambda: self.assertTaskList(self.originalList))

    def test_paste(self):
        self.cut([self.task1])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(1, len(self.taskList)),
            self.assertEmptyTaskList,
        )

    def test_clipboard_is_not_empty_after_paste(self):
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
    def test_paste_without_previous_cut(self):
        self.paste()
        self.assertDoUndoRedo(lambda: self.assertNoteContainer(self.original))

    def test_paste(self):
        self.cut([self.note1])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(2, len(self.original)),
            lambda: self.assertNoteContainer([self.note2]),
        )


class PasteCommandWithEffortTest(CommandWithEffortTestCase):
    def test_paste_without_previous_cut(self):
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEffortList(self.originalEffortList)
        )

    def test_paste(self):
        self.cut([self.effort1])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(2, len(self.originalEffortList)),
            lambda: self.assertEqualLists([self.effort2], self.effortList),
        )

    def test_clipboard_is_not_empty_after_paste(self):
        self.cut([self.effort1])
        self.paste()
        # pylint: disable=W0212
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                [self.effort1], command.Clipboard()._contents
            )
        )


class PasteCommandWithTasksWithChildrenTest(CommandWithChildrenTestCase):
    def test_cut_and_paste_child(self):
        self.cut([self.child])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(5, len(self.taskList)),
            lambda: self.assertTaskList(
                [self.task1, self.parent, self.child2]
            ),
        )

    def test_cut_and_paste_parent_and_child(self):
        self.cut([self.parent, self.child])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(5, len(self.taskList)),
            lambda: self.assertTaskList([self.task1]),
        )

    def test_cut_and_paste_parent_and_grand_child(self):
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
    def test_paste_child(self):
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

    def test_paste_extra_child(self):
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

    def test_paste_child_marks_new_parent_as_not_completed(self):
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.markCompleted([self.parent])
        self.cut([self.task1])
        self.paste([self.parent])
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.parent.completed()),
            lambda: self.assertTrue(self.parent.completed()),
        )

    def test_paste_completed_child_does_not_mark_parent_as_not_completed(self):
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
            # Only the paste is undone: the cut stands
            lambda: self.assertEqual(
                (1, 0), (len(self.task2.efforts()), len(self.task1.efforts()))
            ),
        )
        self.undo()
        self.undo()  # The cut
        self.assertEqual(1, len(self.task1.efforts()))


class CutAndPasteTasksIntegrationTest(TaskCommandTestCase):
    def test_undo_cut_and_paste(self):
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

    def test_undo_cut_and_paste(self):
        self.cut([self.child])
        self.paste()
        self.undo()
        self.undo()
        self.assertTaskListUnchanged()

    def test_undo_cut_and_paste_as_subtask(self):
        self.cut([self.child])
        self.paste([self.child2])
        self.undo()
        self.undo()
        self.assertTaskListUnchanged()

    def test_undo_cut_and_paste_parent_and_grand_child(self):
        self.cut([self.parent, self.grandchild])
        self.paste()
        self.undo()
        self.undo()
        self.assertTaskListUnchanged()

    def test_redo_cut_and_paste_parent_and_grand_child(self):
        self.cut([self.parent, self.grandchild])
        self.paste()
        self.undo()
        self.undo()
        self.redo()
        self.redo()
        self.assertEqual(5, len(self.taskList))
        self.assertFalse(self.child.children())


class CopyCommandWithTasksTest(TaskCommandTestCase):
    def test_copy_task_without_selection(self):
        self.copy([])
        self.assertDoUndoRedo(
            lambda: self.assertEqual([], command.Clipboard().get()[0]),
            self.assertTaskList(self.originalList),
        )

    def assert_no_undo_step(self):
        # A copy changes nothing in the file (docs/UNDO_REDO.md)
        self.assertFalse(patterns.CommandHistory().has_history())

    def test_copy_task(self):
        self.copy([self.task1])
        copied_task = command.Clipboard().get()[0][0]
        self.assertTaskCopy(self.task1, copied_task)
        self.assertTaskList(self.originalList)
        self.assert_no_undo_step()


class CopyCommandWithTasksWithChildrenTest(CommandWithChildrenTestCase):
    def test_copy(self):
        self.copy([self.parent])
        copied_task = command.Clipboard().get()[0][0]
        self.assertTaskCopy(self.parent, copied_task)
        self.assertTaskList(self.originalList)
        self.assertFalse(patterns.CommandHistory().has_history())


class CopyAndPasteWithPrerequisitesTest(TaskCommandTestCase):
    """A copy keeps its original's prerequisites: those copied with it
    as their copies, the others as they are; no other task changes
    (GitHub #169, P205)."""

    def setUp(self):
        super().setUp()
        self.outside = self.task1
        self.first, self.second = task.Task("first"), task.Task("second")
        self.taskList.extend([self.first, self.second])
        self.first.add_prerequisites([self.outside])
        self.outside.add_dependencies([self.first])
        self.second.add_prerequisites([self.first])
        self.first.add_dependencies([self.second])

    def pasted(self):
        """Paste; return the pasted copies of first and second."""
        before = set(self.taskList)
        self.paste()
        new = set(self.taskList) - before
        by_subject = {each.subject(): each for each in new}
        return by_subject["first"], by_subject["second"]

    def test_tasks_copied_together_keep_their_links(self):
        self.copy([self.first, self.second])
        first, second = self.pasted()
        self.assertEqual({first}, second.prerequisites())
        self.assertEqual({second}, first.dependencies())

    def test_a_prerequisite_not_copied_stays(self):
        self.copy([self.first, self.second])
        first, _second = self.pasted()
        self.assertEqual({self.outside}, first.prerequisites())
        self.assertIn(first, self.outside.dependencies())

    def test_the_originals_keep_their_links(self):
        self.copy([self.first, self.second])
        self.pasted()
        self.assertEqual({self.first}, self.second.prerequisites())
        self.assertEqual({self.second}, self.first.dependencies())

    def test_a_prerequisite_deleted_before_the_paste_is_dropped(self):
        self.copy([self.first, self.second])
        self.delete([self.outside])
        first, _second = self.pasted()
        self.assertEqual(set(), first.prerequisites())

    def test_each_paste_links_its_own_copies(self):
        self.copy([self.first, self.second])
        self.pasted()
        first, second = self.pasted()
        self.assertEqual({first}, second.prerequisites())

    def test_cut_and_paste_keeps_the_links(self):
        self.cut([self.first, self.second])
        self.paste()
        self.assertEqual({self.first}, self.second.prerequisites())
        self.assertEqual({self.outside}, self.first.prerequisites())

    def view_showing_first(self):
        """A view's list, as a paste gets it: outside is hidden."""
        return base.SearchFilter(self.taskList, searchString="first")

    def test_a_prerequisite_the_view_hides_stays(self):
        self.copy([self.first])
        before = set(self.taskList)
        command.PasteCommand(self.view_showing_first()).do()
        (first,) = set(self.taskList) - before
        self.assertEqual({self.outside}, first.prerequisites())

    def test_a_cut_task_keeps_a_prerequisite_the_view_hides(self):
        self.cut([self.first])
        command.PasteCommand(self.view_showing_first()).do()
        self.assertEqual({self.outside}, self.first.prerequisites())
        self.assertIn(self.first, self.outside.dependencies())

    def test_a_prerequisite_is_the_files_own_item(self):
        # The file closed and opened again: other items, the same IDs
        self.copy([self.first])
        self.taskList.remove(self.outside)
        reopened = task.Task("outside", id=self.outside.id())
        self.taskList.append(reopened)
        first = self.pasted_first()
        (prerequisite,) = first.prerequisites()
        self.assertIs(reopened, prerequisite)
        self.assertIn(first, reopened.dependencies())

    def pasted_first(self):
        before = set(self.taskList)
        self.paste()
        (first,) = set(self.taskList) - before
        return first


class CopyCommandWithEffortTest(CommandWithEffortTestCase):
    def test_copy_effort_without_selection(self):
        self.copy([])
        self.assertDoUndoRedo(
            lambda: self.assertEqual([], command.Clipboard().get()[0]),
            self.assertEffortList(self.originalEffortList),
        )

    def test_copy_effort(self):
        self.copy([self.effort1])
        copied_effort = command.Clipboard().get()[0][0]
        self.assertEqualEfforts(self.effort1, copied_effort)
        self.assertEffortList(self.originalEffortList)
        self.assertFalse(patterns.CommandHistory().has_history())

    def test_copy_multiple_efforts(self):
        self.copy([self.effort1, self.effort2])
        copied_efforts = command.Clipboard().get()[0]
        self.assertEqualEfforts(self.effort1, copied_efforts[0])
        self.assertEqualEfforts(self.effort2, copied_efforts[1])
        self.assertEffortList(self.originalEffortList)
        self.assertFalse(patterns.CommandHistory().has_history())


class DragAndDropWithTasksTest(CommandWithChildrenTestCase):
    def dragAndDrop(self, dragged_items, dropItem):  # pylint: disable=W0222
        command.DragAndDropTaskCommand(
            self.taskList, dragged_items, drop=[dropItem]
        ).do()

    def test_drag_and_drop_root_task(self):
        self.taskList.append(self.task2)
        self.dragAndDrop([self.task2], self.task1)
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.task2 in self.task1.children()),
            lambda: self.assertFalse(self.task2 in self.task1.children()),
        )

    def test_dont_allow_drop_on_self(self):
        self.dragAndDrop([self.task1], self.task1)
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.task1 in self.task1.children())
        )

    def test_drag_child_task_and_drop_on_other_root_task(self):
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

    def test_drag_child_and_drop_on_own_parent(self):
        self.dragAndDrop([self.child2], self.parent)
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.child2 in self.parent.children())
        )

    def test_drag_parent_and_drop_on_own_child(self):
        self.dragAndDrop([self.parent], self.child2)
        self.assertDoUndoRedo(
            lambda: (
                self.assertTrue(self.child2 in self.parent.children()),
                self.assertFalse(self.parent in self.child2.children()),
            )
        )
