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

# Undo puts back exactly what the file stores: the file written after
# undo is the file written before the action, dates included, and redo
# gives the file written after it (docs/UNDO_REDO.md, Architecture).

import io

import wx

import test
from taskcoachlib import command, config, patterns, persistence
from taskcoachlib.domain import attachment, category, date, effort, note, task
from taskcoachlib.patterns.snapshot import Snapshot, Step

OLD = date.DateTime(2020, 1, 1, 12, 0, 0)
NOW = date.DateTime(2026, 9, 30, 9, 30, 0)


class UndoTest(test.TestCase):
    def setUp(self):
        super().setUp()
        task.Task.settings = config.Settings(load=False)
        self.history = patterns.CommandHistory()
        self.history.clear()
        self.addCleanup(self.history.clear)
        self.task_file = persistence.TaskFile()
        self.addCleanup(self.task_file.stop)
        self.addCleanup(self.task_file.close)
        self.tasks = self.task_file.tasks()
        self.categories = self.task_file.categories()
        self.notes = self.task_file.notes()
        self.category = category.Category("Category")
        self.subcategory = category.Category("Subcategory")
        self.category.addChild(self.subcategory)
        self.categories.append(self.category)
        self.parent = task.Task(subject="Parent")
        self.child = task.Task(
            subject="Child", recurrence=date.Recurrence("daily")
        )
        self.child.set_due_date_time(NOW)
        self.parent.addChild(self.child)
        self.other = task.Task(subject="Other")
        self.tasks.extend([self.parent, self.other])
        self.effort = effort.Effort(self.child, OLD, OLD + date.ONE_HOUR)
        self.child.addEffort(self.effort)
        self.note = note.Note(subject="Note")
        self.parent.addNote(self.note)
        self.file = attachment.FileAttachment("report.pdf")
        self.mail = attachment.MailAttachment(
            "mid:1@example.com", subject="Quote", from_name="Alice"
        )
        self.parent.addAttachments(self.file, self.mail)
        self.other.addCategory(self.subcategory)
        self.top_note = note.Note(subject="Top")
        self.notes.append(self.top_note)
        # Any dating shows in the file
        for item, _fields in Snapshot().items.values():
            item.set_modification_datetime(OLD)

    def xml(self):
        stream = io.BytesIO()
        stream.name = "undo.tsk"
        persistence.XMLWriter(stream).write(
            self.tasks, self.categories, self.notes
        )
        return stream.getvalue().decode("utf-8")

    def settle(self):
        """What the views do in reaction runs (UndoWithEditorsTest)."""

    def assert_undone_and_redone(self, change):
        before, stored_before = self.xml(), Snapshot()
        with self.history.action("change"):
            change()
        self.settle()
        after, stored_after = self.xml(), Snapshot()
        self.assertNotEqual(before, after)
        self.history.undo()
        self.settle()
        self.assertEqual(before, self.xml())
        # In memory too, the links not saved included
        self.assertFalse(Step("", stored_before, Snapshot()))
        self.history.redo()
        self.settle()
        self.assertEqual(after, self.xml())
        self.assertFalse(Step("", stored_after, Snapshot()))
        # Nothing else was recorded
        self.assertEqual(
            (["change"], []),
            (
                [str(step) for step in self.history.get_history()],
                self.history.get_future(),
            ),
        )

    def test_texts_and_appearance(self):
        def change():
            self.parent.setSubject("Renamed")
            self.parent.setDescription("Text")
            self.parent.setForegroundColor(wx.RED)
            self.parent.setBackgroundColor(wx.BLUE)
            self.parent.set_icon_id("star")
            self.parent.setOrdering(42)

        self.assert_undone_and_redone(change)

    def test_dates(self):
        def change():
            self.other.set_planned_start_date_time(NOW)
            self.other.set_due_date_time(NOW + date.ONE_DAY)
            self.other.set_actual_start_date_time(NOW)
            self.other.set_reminder(NOW)

        self.assert_undone_and_redone(change)

    def test_snooze(self):
        self.other.set_reminder(NOW)
        self.assert_undone_and_redone(
            lambda: self.other.snooze_reminder(date.ONE_HOUR)
        )

    def test_a_new_reminder_ends_the_snooze(self):
        self.other.set_reminder(NOW)
        self.other.snooze_reminder(date.ONE_HOUR)
        self.assert_undone_and_redone(
            lambda: self.other.set_reminder(NOW + date.ONE_DAY)
        )

    def test_numbers(self):
        def change():
            self.other.setPriority(3)
            self.other.set_budget(date.ONE_HOUR)
            self.other.set_hourly_fee(10)
            self.other.set_fixed_fee(100)
            self.other.setPercentageComplete(50)
            self.other.setPlannedDuration(date.ONE_HOUR)
            self.other.setPlannedDurationMode("adjdue")
            self.other.set_should_mark_completed_when_all_children_completed(
                False
            )
            self.other.set_recurrence(date.Recurrence("weekly"))

        self.assert_undone_and_redone(change)

    def test_completing_a_recurring_task(self):
        # The recurrence moves its dates and the parent may complete
        self.assert_undone_and_redone(
            lambda: self.child.set_completion_date_time(NOW)
        )

    def test_completing_a_parent_completes_its_subtasks(self):
        self.child.set_recurrence()
        self.assert_undone_and_redone(
            lambda: self.parent.set_completion_date_time(NOW)
        )

    def test_prerequisites(self):
        def change():
            self.other.add_prerequisites([self.child])
            self.other.addTaskAsDependencyOf([self.child])

        self.assert_undone_and_redone(change)

    def test_categories(self):
        def change():
            self.parent.addCategory(self.category)
            self.other.removeCategory(self.subcategory)
            self.category.makeSubcategoriesExclusive()
            self.category.setStylePriority(2)

        self.assert_undone_and_redone(change)

    def test_efforts(self):
        def change():
            self.effort.setStart(OLD - date.ONE_HOUR)
            self.effort.setDescription("Work")
            self.other.addEffort(effort.Effort(self.other, OLD, OLD))

        self.assert_undone_and_redone(change)

    def test_starting_tracking(self):
        self.assert_undone_and_redone(
            lambda: command.StartEffortCommand(self.tasks, [self.other]).do()
        )

    def test_stopping_tracking(self):
        command.StartEffortCommand(self.tasks, [self.other]).do()
        self.history.clear()
        self.assert_undone_and_redone(
            lambda: command.StopEffortCommand(self.task_file.efforts()).do()
        )

    def test_moving_an_effort(self):
        self.assert_undone_and_redone(lambda: self.effort.set_task(self.other))

    def test_notes_and_attachments(self):
        def change():
            self.note.setSubject("Renamed")
            self.note.addChild(note.Note(subject="Subnote"))
            self.top_note.setDescription("Text")
            self.file.setLocation("other.pdf")
            self.mail.setDescription("Call back")
            self.other.addNote(note.Note(subject="New"))
            self.parent.removeAttachments(self.file)

        self.assert_undone_and_redone(change)

    def test_new_subtask(self):
        self.assert_undone_and_redone(
            lambda: command.NewSubTaskCommand(self.tasks, [self.other]).do()
        )

    def test_moving_a_subtask(self):
        self.assert_undone_and_redone(
            lambda: command.DragAndDropTaskCommand(
                self.tasks, [self.child], drop=[self.other]
            ).do()
        )

    def test_deleting_a_task(self):
        self.other.add_prerequisites([self.child])
        self.child.add_dependencies([self.other])
        self.assert_undone_and_redone(
            lambda: command.DeleteTaskCommand(self.tasks, [self.parent]).do()
        )

    def test_deleting_a_category(self):
        self.assert_undone_and_redone(
            lambda: command.DeleteCategoryCommand(
                self.categories, [self.category]
            ).do()
        )

    def test_cut_and_paste(self):
        def change():
            command.CutCommand(self.tasks, [self.child]).do()
            command.PasteAsSubItemCommand(self.tasks, [self.other]).do()

        self.assert_undone_and_redone(change)


class WhatUndoTellsTest(test.TestCase):
    """Undo and redo tell the views what the change told them: the
    work a change does beyond storing lives in its field's callback,
    which runs whether it is set or put back (docs/UNDO_REDO.md,
    Architecture)."""

    def setUp(self):
        super().setUp()
        task.Task.settings = config.Settings(load=False)
        self.history = patterns.CommandHistory()
        self.history.clear()
        self.addCleanup(self.history.clear)
        self.task_file = persistence.TaskFile()
        self.addCleanup(self.task_file.stop)
        self.addCleanup(self.task_file.close)
        self.parent = task.Task(subject="Parent")
        self.child = task.Task(subject="Child")
        self.parent.addChild(self.child)
        self.other = task.Task(subject="Other")
        self.task_file.tasks().extend([self.parent, self.other])

    def change(self, what):
        with self.history.action("change"):
            what()

    def test_undo_of_resuming_tracking_tells_it_stopped(self):
        worked = effort.Effort(self.child, OLD, OLD + date.ONE_HOUR)
        self.child.addEffort(worked)
        self.change(lambda: worked.setStop(OLD + 2 * date.ONE_HOUR))
        self.change(lambda: worked.setStop(date.DateTime.max))  # Resume
        tracking = test.ChangeRecorder(task.Task.trackingChangedEventType())
        self.history.undo()
        stopped = set(tracking)
        del tracking[:]
        self.history.redo()
        # An event's sources come in no set order
        self.assertEqual(
            (
                {(False, self.child), (False, self.parent)},
                {(True, self.child), (True, self.parent)},
            ),
            (stopped, set(tracking)),
        )

    def test_undo_of_moving_a_tracked_subtask_tells_both_parents(self):
        self.child.addEffort(effort.Effort(self.child, OLD))  # Tracked
        self.change(
            lambda: command.DragAndDropTaskCommand(
                self.task_file.tasks(), [self.child], drop=[self.other]
            ).do()
        )
        tracking = test.ChangeRecorder(task.Task.trackingChangedEventType())
        self.history.undo()
        self.assertEqual(
            {(True, self.parent), (False, self.other)},
            {each for each in tracking if each[1] is not self.child},
        )

    def test_undo_of_a_subject_tells_the_linked_tasks(self):
        self.other.add_prerequisites([self.parent])
        self.other.addTaskAsDependencyOf([self.parent])
        self.change(lambda: self.parent.setSubject("Renamed"))
        linked = test.ChangeRecorder(task.Task.prerequisitesChangedEventType())
        self.history.undo()
        self.assertIn(self.other, linked)

    def test_undo_of_a_colour_shows_at_once(self):
        self.change(lambda: self.other.setForegroundColor(wx.RED))
        self.assertEqual(wx.RED, self.other.effectiveFgColor())
        self.history.undo()
        self.assertNotEqual(wx.RED, self.other.effectiveFgColor())
        self.history.redo()
        self.assertEqual(wx.RED, self.other.effectiveFgColor())
