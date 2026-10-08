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

import glob
import os
import shutil
import stat
import tempfile
from unittest import mock
import wx
import test
from taskcoachlib import command, patterns, persistence
from taskcoachlib.domain import (
    base,
    task,
    effort,
    date,
    category,
    note,
    attachment,
)
from taskcoachlib.config import settings


class FakeAttachment(base.Object):
    def __init__(self, type_, location, notes=None, data=None):
        super().__init__()
        self.type_ = type_
        self.__location = location
        self.__data = data
        self.__notes = notes or []

    def data(self):
        return self.__data

    def location(self):
        return self.__location

    def notes(self, recursive=False):
        return self.__notes


class TaskFileTestCase(test.TestCase):
    def setUp(self):
        self.createTaskFiles()
        self.task = task.Task(subject="task")
        self.taskFile.tasks().append(self.task)
        self.category = category.Category("category")
        self.taskFile.categories().append(self.category)
        self.note = note.Note(subject="note")
        self.taskFile.notes().append(self.note)
        self.effort = effort.Effort(
            self.task, date.DateTime(2004, 1, 1), date.DateTime(2004, 1, 2)
        )
        self.task.addEffort(self.effort)
        self.filename = "test.tsk"
        self.filename2 = "test2.tsk"
        super().setUp()

    def createTaskFiles(self):
        # pylint: disable=W0201
        self.taskFile = persistence.TaskFile()
        self.emptyTaskFile = persistence.TaskFile()

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()
        self.emptyTaskFile.close()
        self.emptyTaskFile.stop()
        self.remove(
            self.filename,
            self.filename2,
            self.filename + ".lock",
            self.filename2 + ".lock",
        )

    def remove(self, *filenames):
        for filename in filenames:
            tries = 0
            while os.path.exists(filename) and tries < 3:
                try:  # Don't fail on random 'Access denied' errors.
                    os.remove(filename)
                    break
                except WindowsError:  # pragma: no cover pylint: disable=E0602
                    tries += 1


class TaskFileTest(TaskFileTestCase):
    def test_is_empty_initially(self):
        self.assertTrue(self.emptyTaskFile.isEmpty())

    def test_owners_of_a_note_of_an_attachment(self):
        plan = attachment.FileAttachment("plan.txt")
        tools = note.Note(subject="Tools")
        plan.addNote(tools)
        self.task.addAttachments(plan)
        chains = self.taskFile.owner_chains()
        self.assertEqual(
            ([self.task], [self.task, plan], True),
            (
                chains[plan],
                chains[tools],
                tools in self.taskFile.categorizables(),
            ),
        )

    def test_has_no_tasks_initially(self):
        self.assertFalse(self.emptyTaskFile.tasks())

    def test_has_no_categories_initially(self):
        self.assertFalse(self.emptyTaskFile.categories())

    def test_has_no_notes_initially(self):
        self.assertFalse(self.emptyTaskFile.notes())

    def test_has_no_efforts_initially(self):
        self.assertFalse(self.emptyTaskFile.efforts())

    def test_file_name_after_create(self):
        self.assertEqual("", self.taskFile.filename())

    def test_file_name(self):
        self.taskFile.setFilename(self.filename)
        self.assertEqual(self.filename, self.taskFile.filename())

    def test_load_without_filename(self):
        self.taskFile.load()
        self.assertTrue(self.taskFile.isEmpty())

    def test_load_from_not_existing_file(self):
        self.taskFile.setFilename(self.filename)
        self.assertFalse(os.path.isfile(self.taskFile.filename()))
        self.taskFile.load()
        self.assertTrue(self.taskFile.isEmpty())

    def test_close_empty_task_file_without_filename(self):
        self.taskFile.close()
        self.assertEqual("", self.taskFile.filename())
        self.assertTrue(self.taskFile.isEmpty())

    def test_close_empty_task_file_with_filename(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.close()
        self.assertEqual("", self.taskFile.filename())
        self.assertTrue(self.taskFile.isEmpty())

    def test_close_task_file_with_tasks_deletes_tasks(self):
        self.taskFile.close()
        self.assertTrue(self.taskFile.isEmpty())

    def test_close_task_file_with_categories_deletes_categories(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.close()
        self.assertTrue(self.taskFile.isEmpty())

    def test_close_task_file_with_notes_deletes_notes(self):
        self.taskFile.notes().append(note.Note())
        self.taskFile.close()
        self.assertTrue(self.taskFile.isEmpty())

    def test_does_not_need_save_initial(self):
        self.assertFalse(self.emptyTaskFile.need_save())

    def test_does_not_need_save_after_set_file_name(self):
        self.emptyTaskFile.setFilename(self.filename)
        self.assertFalse(self.emptyTaskFile.need_save())

    def test_last_filename_is_empty_initially(self):
        self.assertEqual("", self.taskFile.lastFilename())

    def test_last_filename_equals_current_filename_after_set_filename(self):
        self.taskFile.setFilename(self.filename)
        self.assertEqual(self.filename, self.taskFile.lastFilename())

    def test_last_filename_equals_previous_filename_after_close(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.close()
        self.assertEqual(self.filename, self.taskFile.lastFilename())

    def test_last_filename_is_empty_after_closing_twice(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.close()
        self.taskFile.close()
        self.assertEqual(self.filename, self.taskFile.lastFilename())

    def test_last_filename_equals_current_filename_after_save_as(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.saveas(self.filename2)
        self.assertEqual(self.filename2, self.taskFile.lastFilename())

    def test_task_file_contains_task(self):
        self.assertTrue(self.task in self.taskFile)

    def test_task_file_does_not_contain_task(self):
        self.assertFalse(task.Task() in self.taskFile)

    def test_task_file_contains_note(self):
        new_note = note.Note()
        self.taskFile.notes().append(new_note)
        self.assertTrue(new_note in self.taskFile)

    def test_task_file_does_not_contain_note(self):
        self.assertFalse(note.Note() in self.taskFile)

    def test_task_file_contains_category(self):
        new_category = category.Category("Category")
        self.taskFile.categories().append(new_category)
        self.assertTrue(new_category in self.taskFile)

    def test_task_file_does_not_contain_category(self):
        self.assertFalse(category.Category("Category") in self.taskFile)

    def test_task_file_contains_effort(self):
        new_effort = effort.Effort(self.task)
        self.task.addEffort(new_effort)
        self.assertTrue(new_effort in self.taskFile)

    def test_task_file_does_not_contain_effort(self):
        self.assertFalse(effort.Effort(self.task) in self.taskFile)


class DirtyTaskFileTest(TaskFileTestCase):
    def setUp(self):
        super().setUp()
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()

    def test_setup_file_does_not_need_save(self):
        self.assertFalse(self.taskFile.need_save())

    def test_need_save_after_new_task_added(self):
        new_task = task.Task(subject="Task")
        self.emptyTaskFile.tasks().append(new_task)
        self.assertTrue(self.emptyTaskFile.need_save())

    def test_need_save_after_new_note_added(self):
        new_note = note.Note(subject="Note")
        self.emptyTaskFile.notes().append(new_note)
        self.assertTrue(self.emptyTaskFile.need_save())

    def test_need_save_after_note_removed(self):
        self.taskFile.notes().remove(self.note)
        self.assertTrue(self.taskFile.need_save())

    def test_does_not_need_save_after_save(self):
        self.emptyTaskFile.tasks().append(task.Task())
        self.emptyTaskFile.setFilename(self.filename)
        self.emptyTaskFile.save()
        self.assertFalse(self.emptyTaskFile.need_save())

    def test_does_not_need_save_after_close(self):
        self.taskFile.close()
        self.assertFalse(self.taskFile.need_save())

    def test_need_save_after_merge(self):
        self.emptyTaskFile.merge(self.filename)
        self.assertTrue(self.emptyTaskFile.need_save())

    def test_does_not_need_save_after_load(self):
        self.taskFile.tasks().append(task.Task())
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.taskFile.close()
        self.taskFile.load()
        self.assertFalse(self.taskFile.need_save())

    def write_file(self, versions):
        with open(self.filename, "w", encoding="utf-8") as fd:
            fd.write(
                '<?taskcoach release="2.0.3" %s?>\n'
                '<tasks><task id="t1" subject="Task" categories="c1"/>'
                '<category id="c1" subject="Category"/></tasks>' % versions
            )

    def test_a_file_older_releases_cannot_open_is_saved_again(self):
        # Saved by 2.0.3.0 before it wrote the forms older releases read
        # (docs/PERSISTENCE_XML.md, Versions and Compatibility)
        self.write_file('tskversion="38"')
        self.taskFile.setFilename(self.filename)
        self.taskFile.load()
        need_save = self.taskFile.need_save()
        self.taskFile.save()
        with open(self.filename, encoding="utf-8") as fd:
            written = fd.read()
        self.assertEqual(
            (True, True, True),
            (
                need_save,
                'tskversion="37" tskformat="39"' in written,
                'categorizables="t1"' in written,
            ),
        )

    def test_a_file_older_releases_open_needs_no_save(self):
        self.write_file('tskversion="37" tskformat="38"')
        self.taskFile.setFilename(self.filename)
        self.taskFile.load()
        self.assertFalse(self.taskFile.need_save())

    def test_duplicate_ids_are_corrected_and_need_save_after_load(self):
        with open(self.filename, "w", encoding="utf-8") as fd:
            fd.write(
                '<?taskcoach release="2.0.3" tskversion="37"?>\n'
                '<tasks><task id="1" subject="first"/>'
                '<task id="1" subject="second"/></tasks>'
            )
        self.taskFile.setFilename(self.filename)
        self.taskFile.load()
        self.assertEqual(
            (2, True),
            (
                len({each.id() for each in self.taskFile.tasks()}),
                self.taskFile.need_save(),
            ),
        )

    def test_need_save_after_effort_added(self):
        self.task.addEffort(effort.Effort(self.task, None, None))
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_effort_removed(self):
        new_effort = effort.Effort(self.task, None, None)
        self.task.addEffort(new_effort)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.task.removeEffort(new_effort)
        self.assertTrue(self.taskFile.need_save())

    def edit_subject(self):
        patterns.CommandHistory().clear()
        self.taskFile.save()
        command.EditSubjectCommand(
            self.taskFile.tasks(), [self.task], newValue="new"
        ).do()

    def test_undo_back_to_the_saved_state_needs_no_save(self):
        self.edit_subject()
        self.assertTrue(self.taskFile.need_save())
        patterns.CommandHistory().undo()
        self.assertFalse(self.taskFile.need_save())
        patterns.CommandHistory().redo()
        self.assertTrue(self.taskFile.need_save())

    def test_undo_back_past_a_command_that_changed_nothing(self):
        patterns.CommandHistory().clear()
        self.taskFile.save()
        command.CopyCommand(self.taskFile.tasks(), [self.task]).do()
        command.EditSubjectCommand(
            self.taskFile.tasks(), [self.task], newValue="new"
        ).do()
        patterns.CommandHistory().undo()
        self.assertFalse(self.taskFile.need_save())

    def test_copying_a_note_with_subnotes_needs_no_save(self):
        # Building the copy links its subnotes: no change to the file
        parent = note.Note(children=[note.Note(subject="subnote")])
        self.taskFile.notes().append(parent)
        self.taskFile.save()
        parent.copy()
        self.assertFalse(self.taskFile.need_save())

    def test_change_outside_commands_is_not_undone(self):
        self.edit_subject()
        self.task.setDescription("not a command")
        patterns.CommandHistory().undo()
        self.assertTrue(self.taskFile.need_save())

    def test_modification_date_change_needs_save(self):
        # Saved data: every change to an item's data sets it
        self.task.set_modification_datetime(date.Now())
        self.assertTrue(self.taskFile.need_save())

    def test_computed_change_needs_no_save(self):
        self.task.setEffectiveFgColor(wx.RED, wx.BLACK, "category")
        self.assertFalse(self.taskFile.need_save())

    def test_need_save_after_planned_duration_change(self):
        self.task.setPlannedDuration(date.ONE_HOUR)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_planned_duration_mode_change(self):
        self.task.setPlannedDurationMode("adjdue")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_edit_task_subject(self):
        self.task.setSubject("new subject")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_edit_task_description(self):
        self.task.setDescription("new description")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_edit_task_foreground_color(self):
        self.task.setForegroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_edit_task_background_color(self):
        self.task.setBackgroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_edit_task_planned_start_date_time(self):
        self.task.set_planned_start_date_time(date.Now() + date.ONE_HOUR)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_edit_task_due_date(self):
        self.task.set_due_date_time(date.Tomorrow())
        self.assertTrue(self.taskFile.need_save())

    def test_status_changed_by_the_clock_needs_no_save(self):
        due = date.Now() + date.ONE_HOUR
        self.task.set_due_date_time(due)
        self.taskFile.save()
        self.task.compute_stored_status(due + date.ONE_SECOND)  # Overdue
        self.assertEqual(task.status.overdue, self.task.computedStatus())
        self.assertFalse(self.taskFile.need_save())

    def test_need_save_after_edit_task_completion_date(self):
        self.task.set_completion_date_time(date.Now())
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_edit_percentage_complete(self):
        self.task.setPercentageComplete(50)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_edit_effort_description(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.effort.setDescription("new description")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_edit_effort_start(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.effort.setStart(date.DateTime(2005, 1, 1, 10, 0, 0))
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_edit_effort_stop(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.effort.setStop(date.DateTime(2005, 1, 1, 10, 0, 0))
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_edit_effort_task(self):
        task2 = task.Task()
        self.taskFile.tasks().append(task2)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.effort.set_task(task2)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_edit_effort_foreground_color(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.effort.setForegroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_edit_effort_background_color(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.effort.setBackgroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_task_added_to_category(self):
        self.task.addCategory(self.category)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_task_removed_from_category(self):
        self.task.addCategory(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.task.removeCategory(self.category)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_note_added_to_category(self):
        self.note.addCategory(self.category)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_note_removed_from_category(self):
        self.note.addCategory(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.note.removeCategory(self.category)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_adding_note_to_task(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.task.addNote(note.Note(subject="Note"))  # pylint: disable=E1101
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_task_note_changed(self):
        self.taskFile.setFilename(self.filename)
        new_note = note.Note(subject="Note")
        self.task.addNote(new_note)  # pylint: disable=E1101
        self.taskFile.save()
        new_note.setSubject("New subject")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_change_priority(self):
        self.task.setPriority(10)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_change_budget(self):
        self.task.set_budget(date.TimeDelta(10))
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_change_hourly_fee(self):
        self.task.set_hourly_fee(100)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_change_fixed_fee(self):
        self.task.set_fixed_fee(500)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_add_child(self):
        self.taskFile.setFilename(self.filename)
        child = task.Task()
        self.taskFile.tasks().append(child)
        self.taskFile.save()
        self.task.addChild(child)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_remove_child(self):
        self.taskFile.setFilename(self.filename)
        child = task.Task()
        self.taskFile.tasks().append(child)
        self.task.addChild(child)
        self.taskFile.save()
        self.task.removeChild(child)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_set_reminder(self):
        self.task.set_reminder(date.DateTime(2005, 1, 1, 10, 0, 0))
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_change_recurrence(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.task.set_recurrence(date.Recurrence("daily"))
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_change_setting(self):
        self.task.set_should_mark_completed_when_all_children_completed(True)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_adding_category(self):
        self.taskFile.categories().append(self.category)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_removing_category(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.taskFile.categories().remove(self.category)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_filtering_category(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.category.setFiltered()
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_category_subject_changed(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.category.setSubject("new subject")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_category_description_changed(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.category.setDescription("new description")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_changing_category_foreground_color(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.category.setForegroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_changing_category_background_color(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.category.setBackgroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_making_subclasses_exclusive(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.category.makeSubcategoriesExclusive()
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_note_subject_changed(self):
        list(self.taskFile.notes())[0].setSubject("new subject")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_note_description_changed(self):
        list(self.taskFile.notes())[0].setDescription("new description")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_note_foreground_color_changed(self):
        list(self.taskFile.notes())[0].setForegroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_note_background_color_changed(self):
        list(self.taskFile.notes())[0].setBackgroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_add_note_child(self):
        list(self.taskFile.notes())[0].addChild(note.Note())
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_remove_note_child(self):
        child = note.Note()
        list(self.taskFile.notes())[0].addChild(child)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        list(self.taskFile.notes())[0].removeChild(child)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_changing_task_expansion_state(self):
        self.task.expand()
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_changing_category_expansion_state(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.category.expand()
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_changing_note_expansion_state(self):
        self.taskFile.notes().append(self.note)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.note.expand()
        self.assertTrue(self.taskFile.need_save())

    def test_last_filename_equals_current_filename_after_set_filename(self):
        self.taskFile.setFilename(self.filename)
        self.assertEqual(self.filename, self.taskFile.lastFilename())

    def test_last_filename_equals_previous_filename_after_close(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.close()
        self.assertEqual(self.filename, self.taskFile.lastFilename())

    def test_last_filename_equals_previous_filename_after_closing_twice(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.close()
        self.taskFile.close()
        self.assertEqual(self.filename, self.taskFile.lastFilename())

    def test_last_filename_equals_current_filename_after_save_as(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.saveas(self.filename2)
        self.assertEqual(self.filename2, self.taskFile.lastFilename())


class ChangingAttachmentsTestsMixin(object):
    def test_need_save_after_attachment_added(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.item.addAttachments(self.attachment)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_attachment_removed(self):
        self.taskFile.setFilename(self.filename)
        self.item.addAttachments(self.attachment)
        self.taskFile.save()
        self.item.removeAttachments(self.attachment)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_attachments_replaced(self):
        self.taskFile.setFilename(self.filename)
        self.item.addAttachments(self.attachment)
        self.taskFile.save()
        self.item.setAttachments([FakeAttachment("file", "attachment2")])
        self.assertTrue(self.taskFile.need_save())

    def addAttachment(self, an_attachment):
        self.taskFile.setFilename(self.filename)
        self.item.addAttachments(an_attachment)
        self.taskFile.save()

    def addFileAttachment(self):
        self.fileAttachment = attachment.FileAttachment(
            "Old location"
        )  # pylint: disable=W0201
        self.addAttachment(self.fileAttachment)

    def test_need_save_after_file_attachment_location_changed(self):
        self.addFileAttachment()
        self.fileAttachment.setLocation("New location")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_file_attachment_subject_changed(self):
        self.addFileAttachment()
        self.fileAttachment.setSubject("New subject")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_file_attachment_description_changed(self):
        self.addFileAttachment()
        self.fileAttachment.setDescription("New description")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_file_attachment_foreground_color_changed(self):
        self.addFileAttachment()
        self.fileAttachment.setForegroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_file_attachment_background_color_changed(self):
        self.addFileAttachment()
        self.fileAttachment.setBackgroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_file_attachment_note_added(self):
        self.addFileAttachment()
        self.fileAttachment.addNote(
            note.Note(subject="Note")
        )  # pylint: disable=E1101
        self.assertTrue(self.taskFile.need_save())

    def addURIAttachment(self):
        self.uriAttachment = attachment.URIAttachment(
            "Old location"
        )  # pylint: disable=W0201
        self.addAttachment(self.uriAttachment)

    def test_need_save_after_uri_attachment_location_changed(self):
        self.addURIAttachment()
        self.uriAttachment.setLocation("New location")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_uri_attachment_subject_changed(self):
        self.addURIAttachment()
        self.uriAttachment.setSubject("New subject")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_uri_attachment_description_changed(self):
        self.addURIAttachment()
        self.uriAttachment.setDescription("New description")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_uri_attachment_foreground_color_changed(self):
        self.addURIAttachment()
        self.uriAttachment.setForegroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_uri_attachment_background_color_changed(self):
        self.addURIAttachment()
        self.uriAttachment.setBackgroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_uri_attachment_note_added(self):
        self.addURIAttachment()
        self.uriAttachment.addNote(
            note.Note(subject="Note")
        )  # pylint: disable=E1101
        self.assertTrue(self.taskFile.need_save())

    def addMailAttachment(self):
        # pylint: disable=W0201
        self.mailAttachment = attachment.MailAttachment("mid:1@example.com")
        self.addAttachment(self.mailAttachment)

    def test_need_save_after_mail_attachment_location_changed(self):
        self.addMailAttachment()
        self.mailAttachment.setLocation("New location")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_mail_attachment_subject_changed(self):
        self.addMailAttachment()
        self.mailAttachment.setSubject("New subject")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_mail_attachment_description_changed(self):
        self.addMailAttachment()
        self.mailAttachment.setDescription("New description")
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_mail_attachment_foreground_color_changed(self):
        self.addMailAttachment()
        self.mailAttachment.setForegroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_mail_attachment_background_color_changed(self):
        self.addMailAttachment()
        self.mailAttachment.setBackgroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def test_need_save_after_mail_attachment_note_added(self):
        self.addMailAttachment()
        self.mailAttachment.addNote(
            note.Note(subject="Note")
        )  # pylint: disable=E1101
        self.assertTrue(self.taskFile.need_save())


class TaskFileDirtyWhenChangingAttachmentsTestCase(TaskFileTestCase):
    def setUp(self):
        super().setUp()
        self.attachment = FakeAttachment("file", "attachment")


class TaskFileDirtyWhenChangingTaskAttachmentsTestCase(
    TaskFileDirtyWhenChangingAttachmentsTestCase, ChangingAttachmentsTestsMixin
):
    def setUp(self):
        super().setUp()
        self.item = self.task


class TaskFileDirtyWhenChangingNoteAttachmentsTestCase(
    TaskFileDirtyWhenChangingAttachmentsTestCase, ChangingAttachmentsTestsMixin
):
    def setUp(self):
        super().setUp()
        self.item = self.note


class TaskFileDirtyWhenChangingCategoryAttachmentsTestCase(
    TaskFileDirtyWhenChangingAttachmentsTestCase, ChangingAttachmentsTestsMixin
):
    def setUp(self):
        super(
            TaskFileDirtyWhenChangingCategoryAttachmentsTestCase, self
        ).setUp()
        self.item = self.category


class TaskFileSaveAndLoadTest(TaskFileTestCase):
    def setUp(self):
        super().setUp()
        self.emptyTaskFile.setFilename(self.filename)

    def saveAndLoad(self, tasks, categories=None, notes=None):
        categories = categories or []
        notes = notes or []
        self.emptyTaskFile.tasks().extend(tasks)
        self.emptyTaskFile.categories().extend(categories)
        self.emptyTaskFile.notes().extend(notes)
        self.emptyTaskFile.save()
        self.emptyTaskFile.load()
        self.assertEqual(
            sorted([each_task.subject() for each_task in tasks]),
            sorted(
                [
                    each_task.subject()
                    for each_task in self.emptyTaskFile.tasks()
                ]
            ),
        )
        self.assertEqual(
            sorted([each_category.subject() for each_category in categories]),
            sorted(
                [
                    each_category.subject()
                    for each_category in self.emptyTaskFile.categories()
                ]
            ),
        )
        self.assertEqual(
            sorted([each_note.subject() for each_note in notes]),
            sorted(
                [
                    each_note.subject()
                    for each_note in self.emptyTaskFile.notes()
                ]
            ),
        )

    def test_save_and_load(self):
        self.saveAndLoad(
            [task.Task(subject="ABC"), task.Task(dueDateTime=date.Tomorrow())]
        )

    def test_save_and_load_task_with_child(self):
        parent_task = task.Task()
        child_task = task.Task(parent=parent_task)
        parent_task.addChild(child_task)
        self.saveAndLoad([parent_task, child_task])

    def test_save_and_load_category(self):
        self.saveAndLoad([], [self.category])

    def test_save_and_load_notes(self):
        self.saveAndLoad([], [], [self.note])

    def test_save_and_load_keep_exclusivity_and_its_date(self):
        self.category.makeSubcategoriesExclusive()
        modification_datetime = self.category.modificationDateTime()
        self.saveAndLoad([], [self.category])
        loaded = list(self.emptyTaskFile.categories())[0]
        self.assertEqual(True, loaded.hasExclusiveSubcategories())
        self.assertEqual(modification_datetime, loaded.modificationDateTime())

    def test_save_and_load_keep_the_changed_style_priority_and_its_date(self):
        self.category.setStylePriority(3)
        modification_datetime = self.category.modificationDateTime()
        self.assertTrue(date.DateTime.min < modification_datetime)
        self.saveAndLoad([], [self.category])
        loaded = list(self.emptyTaskFile.categories())[0]
        self.assertEqual(
            (3, modification_datetime),
            (loaded.stylePriority(), loaded.modificationDateTime()),
        )

    def test_save_as(self):
        self.taskFile.saveas("new.tsk")
        self.taskFile.load()
        self.assertEqual(1, len(self.taskFile.tasks()))
        self.taskFile.close()
        self.remove("new.tsk")

    def test_save_as_overwrites(self):
        self.taskFile.saveas("new.tsk")
        self.taskFile.close()
        self.taskFile.tasks().extend([task.Task(subject="foo")])
        self.taskFile.saveas("new.tsk")
        self.assertEqual(1, len(self.taskFile.tasks()))
        self.taskFile.close()
        self.remove("new.tsk")

    def test_a_file_holding_characters_xml_forbids_opens(self):
        # Saved before stored text dropped them (P34)
        with open(self.filename, "w", encoding="utf-8") as file:
            file.write(
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<?taskcoach release="2.0.2" tskversion="37"?>\n'
                '<tasks><task id="1" subject="T">'
                "<description>\na\x00b\n</description></task></tasks>\n"
            )
        self.emptyTaskFile.load()
        self.assertEqual(
            "ab", list(self.emptyTaskFile.tasks())[0].description()
        )

    def test_text_saves_and_loads_whatever_was_pasted(self):
        # docs/ATTRIBUTE_PATTERN.md, Text
        self.saveAndLoad(
            [task.Task(subject="a\x0cb", description="c\x00d\ud800\ne")]
        )
        loaded = list(self.emptyTaskFile.tasks())[0]
        self.assertEqual(
            ("ab", "cd\ne"), (loaded.subject(), loaded.description())
        )


class TaskFileMergeTest(TaskFileTestCase):
    def setUp(self):
        super().setUp()
        self.mergeFile = persistence.TaskFile()
        self.mergeFile.setFilename("merge.tsk")
        # The open file as last changed in 2020
        for item in (self.task, self.category, self.note, self.effort):
            item.set_modification_datetime(date.DateTime(2020, 1, 1))

    def tearDown(self):
        self.mergeFile.close()
        self.mergeFile.stop()
        self.remove("merge.tsk")
        super().tearDown()

    def merge(self):
        self.mergeFile.save()
        self.taskFile.merge("merge.tsk")

    def test_merge_tasks(self):
        self.mergeFile.tasks().append(task.Task())
        self.merge()
        self.assertEqual(2, len(self.taskFile.tasks()))

    def test_a_merge_is_an_undo_step(self):
        # Every change to the file is (docs/UNDO_REDO.md, Design Intent)
        self.mergeFile.tasks().append(task.Task(subject="theirs"))
        self.merge()
        patterns.CommandHistory().undo()
        self.assertEqual([self.task], list(self.taskFile.tasks()))
        patterns.CommandHistory().redo()
        self.assertEqual(2, len(self.taskFile.tasks()))

    def test_merge_sends_no_messages_about_the_merged_file(self):
        self.mergeFile.save()
        names = test.ChangeRecorder("taskfile.filenameChanged")
        self.taskFile.merge("merge.tsk")
        self.assertEqual([], names)

    def test_merge_only_reads_the_merged_file(self):
        # It may be open in another Task Coach
        self.mergeFile.save()
        os.utime("merge.tsk", ns=(10**18, 10**18))
        self.taskFile.merge("merge.tsk")
        self.assertEqual(10**18, os.stat("merge.tsk").st_mtime_ns)
        self.assertEqual(["merge.tsk"], glob.glob("merge.tsk*"))

    def test_merge_tasks_with_subtask(self):
        parent = task.Task(subject="parent")
        child = task.Task(subject="child")
        parent.addChild(child)
        child.set_parent(parent)
        self.mergeFile.tasks().extend([parent, child])
        self.merge()
        self.assertEqual(3, len(self.taskFile.tasks()))
        self.assertEqual(2, len(self.taskFile.tasks().rootItems()))

    def test_merge_one_category_in_merge_file(self):
        self.taskFile.categories().remove(self.category)
        self.mergeFile.categories().append(self.category)
        self.merge()
        self.assertEqual(
            [self.category.subject()],
            [cat.subject() for cat in self.taskFile.categories()],
        )

    def test_merge_different_categories(self):
        self.mergeFile.categories().append(
            category.Category("another category")
        )
        self.merge()
        self.assertEqual(2, len(self.taskFile.categories()))

    def test_merge_same_subject(self):
        self.mergeFile.categories().append(
            category.Category(self.category.subject())
        )
        self.merge()
        self.assertEqual(
            [self.category.subject()] * 2,
            [cat.subject() for cat in self.taskFile.categories()],
        )

    def test_merge_category_with_task(self):
        self.taskFile.categories().remove(self.category)
        self.mergeFile.categories().append(self.category)
        a_task = task.Task(subject="merged task")
        self.mergeFile.tasks().append(a_task)
        a_task.addCategory(self.category)
        self.merge()
        self.assertEqual(
            a_task.id(),
            list(list(self.taskFile.categories())[0].members())[0].id(),
        )

    def test_merge_notes(self):
        new_note = note.Note(subject="new note")
        self.mergeFile.notes().append(new_note)
        self.merge()
        self.assertEqual(2, len(self.taskFile.notes()))

    def their_copy(self, item, subject, modified):
        # Created when modified: an undated copy has neither date, as
        # items from files written before the dates were kept
        return item.__class__(
            subject=subject,
            id=item.id(),
            creationDateTime=modified,
            modificationDateTime=modified,
        )

    def test_newer_copy_wins(self):
        self.task.set_modification_datetime(date.DateTime(2020, 1, 1))
        self.mergeFile.tasks().append(
            self.their_copy(self.task, "theirs", date.DateTime(2021, 1, 1))
        )
        self.merge()
        self.assertEqual(
            ["theirs"], [each.subject() for each in self.taskFile.tasks()]
        )

    def test_older_copy_loses(self):
        self.task.set_modification_datetime(date.DateTime(2020, 1, 1))
        self.mergeFile.tasks().append(
            self.their_copy(self.task, "theirs", date.DateTime(2019, 1, 1))
        )
        self.merge()
        self.assertEqual(
            ["task"], [each.subject() for each in self.taskFile.tasks()]
        )

    def test_copies_within_one_second_are_ordered(self):
        self.task.set_modification_datetime(
            date.Timestamp(2020, 1, 1, 0, 0, 0, 500)
        )
        self.mergeFile.tasks().append(
            self.their_copy(
                self.task, "theirs", date.Timestamp(2020, 1, 1, 0, 0, 0, 501)
            )
        )
        self.merge()
        self.assertEqual(
            ["theirs"], [each.subject() for each in self.taskFile.tasks()]
        )

    def test_undated_copy_follows_the_file_with_the_newest_date(self):
        self.mergeFile.tasks().append(
            self.their_copy(self.task, "theirs", date.DateTime.min)
        )
        self.mergeFile.notes().append(
            note.Note(modificationDateTime=date.DateTime(2021, 1, 1))
        )
        self.merge()
        merged = self.taskFile.tasks().getObjectById(self.task.id())
        self.assertEqual("theirs", merged.subject())

    def test_undated_copy_stays_when_the_open_file_is_newer(self):
        self.note.set_modification_datetime(date.DateTime(2021, 1, 1))
        self.mergeFile.tasks().append(
            self.their_copy(self.task, "theirs", date.DateTime.min)
        )
        self.merge()
        self.assertEqual(
            ["task"], [each.subject() for each in self.taskFile.tasks()]
        )

    def test_without_dates_the_open_file_keeps_its_copy(self):
        for item in (self.task, self.category, self.note, self.effort):
            item.set_modification_datetime(date.DateTime.min)
        self.mergeFile.tasks().append(
            self.their_copy(self.task, "theirs", date.DateTime.min)
        )
        self.merge()
        self.assertEqual(
            ["task"], [each.subject() for each in self.taskFile.tasks()]
        )

    def test_merged_items_keep_the_dates_of_their_copies(self):
        mine = date.DateTime(2020, 1, 1)
        theirs = date.DateTime(2021, 1, 1)
        self.task.set_modification_datetime(mine)
        self.task.addCategory(self.category)
        self.category.set_modification_datetime(mine)
        self.task.set_modification_datetime(mine)
        self.mergeFile.notes().append(
            self.their_copy(self.note, "theirs", theirs)
        )
        self.merge()
        self.assertEqual(
            [mine, mine, theirs],
            [
                self.task.modificationDateTime(),
                self.category.modificationDateTime(),
                list(self.taskFile.notes())[0].modificationDateTime(),
            ],
        )

    def test_subtasks_from_both_files_end_up_together(self):
        self.task.set_modification_datetime(date.DateTime(2020, 1, 1))
        mine = task.Task(subject="mine", parent=self.task)
        self.task.addChild(mine)
        self.taskFile.tasks().append(mine)
        parent = self.their_copy(
            self.task, "theirs", date.DateTime(2021, 1, 1)
        )
        theirs = task.Task(subject="their subtask", parent=parent)
        parent.addChild(theirs)
        self.mergeFile.tasks().extend([parent, theirs])
        self.merge()
        merged = self.taskFile.tasks().getObjectById(self.task.id())
        self.assertEqual(
            ("theirs", ["mine", "their subtask"]),
            (
                merged.subject(),
                sorted(child.subject() for child in merged.children()),
            ),
        )
        self.assertEqual(3, len(self.taskFile.tasks()))

    def test_a_merged_open_subtask_leaves_its_parent_completed(self):
        # The merge edits nothing, so the parent rules do not run
        self.task.set_completion_date_time(date.DateTime(2021, 6, 1))
        self.task.set_modification_datetime(date.DateTime(2022, 1, 1))
        parent = self.their_copy(
            self.task, "theirs", date.DateTime(2021, 1, 1)
        )
        theirs = task.Task(subject="their subtask", parent=parent)
        parent.addChild(theirs)
        self.mergeFile.tasks().extend([parent, theirs])
        self.merge()
        merged = self.taskFile.tasks().getObjectById(self.task.id())
        self.assertEqual(
            (date.DateTime(2021, 6, 1), ["their subtask"]),
            (
                merged.completionDateTime(),
                [child.subject() for child in merged.children()],
            ),
        )

    def test_merging_subtasks_completes_no_parent(self):
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        parent = self.their_copy(
            self.task, "theirs", date.DateTime(2021, 1, 1)
        )
        parent.set_reminder(date.DateTime(2030, 1, 1))
        open_child = task.Task(subject="open", parent=parent)
        done_child = task.Task(
            subject="done",
            parent=parent,
            completionDateTime=date.DateTime(2021, 1, 1),
        )
        parent.addChild(open_child)
        parent.addChild(done_child)
        parent.set_modification_datetime(date.DateTime(2021, 1, 1))
        self.mergeFile.tasks().extend([parent, open_child, done_child])
        self.merge()
        merged = self.taskFile.tasks().getObjectById(self.task.id())
        self.assertEqual(
            (False, date.DateTime(2030, 1, 1)),
            (merged.completed(), merged.reminder()),
        )

    def test_item_moves_to_the_parent_its_newer_copy_names(self):
        other_parent = task.Task(subject="other parent")
        self.taskFile.tasks().append(other_parent)
        child = task.Task(subject="child", parent=self.task)
        self.task.addChild(child)
        self.taskFile.tasks().append(child)
        child.set_modification_datetime(date.DateTime(2020, 1, 1))
        their_parent = task.Task(subject="other parent", id=other_parent.id())
        their_child = self.their_copy(
            child, "moved", date.DateTime(2021, 1, 1)
        )
        their_child.set_parent(their_parent)
        their_parent.addChild(their_child)
        self.mergeFile.tasks().extend([their_parent, their_child])
        self.merge()
        merged = self.taskFile.tasks().getObjectById(child.id())
        self.assertEqual(
            ("moved", other_parent.id(), []),
            (merged.subject(), merged.parent().id(), self.task.children()),
        )

    def test_prerequisites_point_to_the_winning_copies(self):
        self.task.set_modification_datetime(date.DateTime(2020, 1, 1))
        dependent = task.Task(subject="dependent")
        self.taskFile.tasks().append(dependent)
        dependent.add_prerequisites([self.task])
        self.task.add_dependencies([dependent])
        self.mergeFile.tasks().append(
            self.their_copy(self.task, "theirs", date.DateTime(2021, 1, 1))
        )
        self.merge()
        winner = self.taskFile.tasks().getObjectById(self.task.id())
        self.assertTrue(
            [winner] == list(dependent.prerequisites())
            and list(dependent.prerequisites())[0] is winner
        )
        self.assertEqual([dependent], list(winner.dependencies()))

    def older_copy_of_task(self):
        return self.their_copy(self.task, "task", date.DateTime(2019, 1, 1))

    def test_note_added_elsewhere_to_an_older_task_comes_over(self):
        their_task = self.older_copy_of_task()
        their_task.addNote(note.Note(subject="their note", id="n"))
        self.mergeFile.tasks().append(their_task)
        self.merge()
        self.assertEqual(
            ["their note"], [each.subject() for each in self.task.notes()]
        )

    def test_owned_note_edited_elsewhere_wins_by_its_own_date(self):
        mine = note.Note(subject="mine", id="n")
        self.task.addNote(mine)
        mine.set_modification_datetime(date.DateTime(2020, 1, 1))
        self.task.set_modification_datetime(date.DateTime(2020, 1, 1))
        their_task = self.older_copy_of_task()
        edited = note.Note(subject="edited", id="n")
        their_task.addNote(edited)
        edited.set_modification_datetime(date.DateTime(2021, 1, 1))
        self.mergeFile.tasks().append(their_task)
        self.merge()
        merged = self.taskFile.tasks().getObjectById(self.task.id())
        self.assertEqual(
            ("task", ["edited"]),
            (merged.subject(), [each.subject() for each in merged.notes()]),
        )
        # Its own date, although it replaced a copy in the owner's list
        self.assertEqual(
            date.DateTime(2021, 1, 1), merged.notes()[0].modificationDateTime()
        )

    def test_effort_recorded_elsewhere_comes_over(self):
        their_task = self.older_copy_of_task()
        their_task.addEffort(
            effort.Effort(
                their_task,
                date.DateTime(2021, 1, 1, 10, 0, 0),
                date.DateTime(2021, 1, 1, 11, 0, 0),
            )
        )
        # Older still: the effort set its actual start, and so its date
        their_task.set_modification_datetime(date.DateTime(2019, 1, 1))
        self.mergeFile.tasks().append(their_task)
        self.merge()
        self.assertEqual(2, len(self.task.efforts()))
        self.assertTrue(
            all(each.task() is self.task for each in self.task.efforts())
        )

    def test_merge_same_note(self):
        self.mergeFile.notes().append(
            self.their_copy(
                self.note, "merged note", date.DateTime(2021, 1, 1)
            )
        )
        self.merge()
        self.assertEqual(1, len(self.taskFile.notes()))
        self.assertEqual(
            "merged note", list(self.taskFile.notes())[0].subject()
        )

    def test_merge_same_category(self):
        self.mergeFile.categories().append(
            self.their_copy(
                self.category, "merged category", date.DateTime(2021, 1, 1)
            )
        )
        self.merge()
        self.assertEqual(1, len(self.taskFile.categories()))
        self.assertEqual(
            "merged category", list(self.taskFile.categories())[0].subject()
        )

    def link_task_to_category(self):
        self.task.addCategory(self.category)
        for item in self.task, self.category:
            item.set_modification_datetime(date.DateTime(2020, 1, 1))

    def test_task_links_to_the_winning_category(self):
        self.link_task_to_category()
        self.mergeFile.categories().append(
            self.their_copy(
                self.category, "merged category", date.DateTime(2021, 1, 1)
            )
        )
        self.merge()
        winner = list(self.taskFile.categories())[0]
        self.assertEqual("merged category", winner.subject())
        self.assertIs(winner, list(self.task.categories())[0])
        self.assertEqual([self.task], list(winner.members()))

    def test_membership_follows_the_tasks_winning_copy(self):
        # The task owns its categories: its newer copy keeps the link,
        # although the category's newer copy lists no member
        self.link_task_to_category()
        self.task.set_modification_datetime(date.DateTime(2022, 1, 1))
        self.mergeFile.categories().append(
            self.their_copy(
                self.category, "category", date.DateTime(2021, 1, 1)
            )
        )
        self.mergeFile.tasks().append(
            self.their_copy(self.task, "task", date.DateTime(2019, 1, 1))
        )
        self.merge()
        winner = list(self.taskFile.categories())[0]
        self.assertEqual({winner}, self.task.categories())
        self.assertIs(winner, list(self.task.categories())[0])
        self.assertEqual({self.task}, winner.members())

    def test_merge_category_linked_to_task(self):
        self.task.addCategory(self.category)
        # An older copy, without the link: the open file's stays
        self.mergeFile.categories().append(
            self.their_copy(
                self.category, "merged category", date.DateTime(2019, 1, 1)
            )
        )
        self.merge()
        self.assertEqual(
            self.category.id(), list(self.task.categories())[0].id()
        )

    def test_merge_category_linked_to_note(self):
        self.note.addCategory(self.category)
        # An older copy, without the link: the open file's stays
        self.mergeFile.categories().append(
            self.their_copy(
                self.category, "merged category", date.DateTime(2019, 1, 1)
            )
        )
        self.merge()
        self.assertEqual(
            self.category.id(), list(self.note.categories())[0].id()
        )

    def test_subcategory_missing_from_the_newer_copy_stays(self):
        subcategory = category.Category("subcategory", parent=self.category)
        self.category.addChild(subcategory)
        self.taskFile.categories().append(subcategory)
        self.task.addCategory(subcategory)
        self.mergeFile.categories().append(
            self.their_copy(
                self.category, "merged category", date.DateTime(2021, 1, 1)
            )
        )
        self.merge()
        merged = list(self.taskFile.categories().rootItems())[0]
        self.assertEqual(
            ("merged category", [subcategory]),
            (merged.subject(), merged.children()),
        )
        self.assertEqual([subcategory], list(self.task.categories()))


class LockedTaskFileLockTest(TaskFileTestCase):
    def createTaskFiles(self):
        # pylint: disable=W0201
        self.taskFile = persistence.LockedTaskFile()
        self.emptyTaskFile = persistence.LockedTaskFile()

    def tearDown(self):
        self.taskFile.close()
        self.taskFile.stop()
        self.emptyTaskFile.close()
        super().tearDown()

    def test_file_is_not_locked_initially(self):
        self.assertFalse(self.taskFile.is_locked())
        self.assertFalse(self.emptyTaskFile.is_locked())

    def test_file_is_locked_after_saving(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertTrue(self.taskFile.is_locked())

    def test_file_is_locked_after_loading(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.taskFile.close()
        self.emptyTaskFile.load(self.filename)
        self.assertTrue(self.emptyTaskFile.is_locked())

    def test_file_is_not_locked_after_saving_and_closing(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.taskFile.close()
        self.assertFalse(self.taskFile.is_locked())

    def test_save_as_moves_the_lock(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.taskFile.saveas(self.filename2)
        self.assertTrue(self.taskFile.is_locked())
        with open(self.filename + ".lock", "rb") as lock_file:
            self.assertEqual(b"", lock_file.read())
        with open(self.filename2 + ".lock", "rb") as lock_file:
            self.assertIn(b"pid=%d" % os.getpid(), lock_file.read())

    def test_file_can_be_loaded_after_close(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.taskFile.close()
        self.emptyTaskFile.load(self.filename)
        self.assertEqual(1, len(self.emptyTaskFile.tasks()))

    def test_original_file_can_be_loaded_after_save_as(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.taskFile.saveas(self.filename2)
        self.taskFile.close()
        self.emptyTaskFile.load(self.filename)
        self.assertEqual(1, len(self.emptyTaskFile.tasks()))

    def fail_writing(self):
        def write(*args, **kwargs):
            raise IOError("disk full")

        original = persistence.xml.XMLWriter.write
        persistence.xml.XMLWriter.write = write
        self.addCleanup(setattr, persistence.xml.XMLWriter, "write", original)

    def test_failed_save_keeps_the_file_on_disk(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        with open(self.filename, "rb") as saved:
            content = saved.read()
        self.fail_writing()
        self.taskFile.tasks().append(task.Task(subject="new"))
        with self.assertRaises(IOError):
            self.taskFile.save()
        with open(self.filename, "rb") as saved:
            self.assertEqual(content, saved.read())
        self.assertFalse(
            [name for name in os.listdir(".") if name.startswith("tmp-")]
        )

    def test_failed_save_as_keeps_the_file_it_would_replace(self):
        self.emptyTaskFile.setFilename(self.filename2)
        self.emptyTaskFile.save()
        self.emptyTaskFile.close()
        with open(self.filename2, "rb") as existing:
            content = existing.read()
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.fail_writing()
        with self.assertRaises(IOError):
            self.taskFile.saveas(self.filename2)
        with open(self.filename2, "rb") as existing:
            self.assertEqual(content, existing.read())
        self.assertFalse(
            [name for name in os.listdir(".") if name.startswith("tmp-")]
        )

    def test_save_keeps_the_permissions_of_the_file(self):
        if os.name == "nt":
            self.skipTest("needs POSIX permissions")
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        os.chmod(self.filename, 0o600)
        self.taskFile.tasks().append(task.Task(subject="new"))
        self.taskFile.save()
        mode = stat.S_IMODE(os.stat(self.filename).st_mode)
        self.assertEqual(0o600, mode)

    def test_save_through_a_link_keeps_the_link(self):
        if os.name == "nt":
            self.skipTest("needs POSIX symbolic links")
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        target = os.path.join(directory, "target.tsk")
        link = os.path.join(directory, "link.tsk")
        self.emptyTaskFile.setFilename(target)
        self.emptyTaskFile.save()
        self.emptyTaskFile.close()
        os.symlink(target, link)
        self.taskFile.setFilename(link)
        self.taskFile.save()
        self.assertTrue(os.path.islink(link))
        with open(target, "rb") as saved:
            self.assertIn(self.task.id().encode(), saved.read())

    def test_failed_save_as_keeps_the_name_and_the_lock(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.fail_writing()
        with self.assertRaises(IOError):
            self.taskFile.saveas(self.filename2)
        self.assertEqual(self.filename, self.taskFile.filename())
        with open(self.filename + ".lock", "rb") as lock_file:
            self.assertIn(b"pid=%d" % os.getpid(), lock_file.read())
        self.assertFalse(os.path.exists(self.filename2))


class DetachedTaskFileTest(TaskFileTestCase):
    def test_detached_file_keeps_but_no_longer_follows_its_objects(self):
        # A saved selection: its task belongs to self.taskFile
        selection = persistence.TaskFile()
        selection.tasks().append(self.task)
        selection.setFilename(self.filename2)
        selection.save()
        self.task.setSubject("followed")
        self.assertTrue(selection.need_save())
        selection.save()
        selection.detach()
        self.task.setSubject("no longer followed")
        self.assertFalse(selection.need_save())
        self.assertEqual([self.task], list(selection.tasks()))


class TaskFileChangedOnDiskTest(TaskFileTestCase):
    """Another program changed the open file (docs/PERSISTENCE_XML.md,
    Saving)."""

    def setUp(self):
        super().setUp()
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.noticed = test.ChangeRecorder("taskfile.changed")

    def change_on_disk(self):
        theirs = persistence.TaskFile(read_only=True)
        try:
            theirs.load(self.filename)
            theirs.tasks().append(task.Task(subject="theirs"))
            theirs.save()
        finally:
            theirs.close()
            theirs.stop()

    def notice_changes(self):
        self.taskFile.check_disk()

    def subjects_on_disk(self):
        on_disk = persistence.TaskFile(read_only=True)
        try:
            on_disk.load(self.filename)
            return sorted(each.subject() for each in on_disk.tasks())
        finally:
            on_disk.close()
            on_disk.stop()

    def test_own_save_is_no_change_on_disk(self):
        self.task.setSubject("ours")
        self.taskFile.save()
        self.notice_changes()
        self.assertEqual(
            (False, []), (self.taskFile.changed_on_disk(), self.noticed)
        )

    def test_change_by_another_program_is_noticed_once(self):
        self.change_on_disk()
        self.notice_changes()
        self.notice_changes()
        self.assertEqual(
            (True, [self.taskFile]),
            (self.taskFile.changed_on_disk(), self.noticed),
        )

    def test_save_notices_an_unreported_change(self):
        # Its callers tell the user (autosave, File > Save)
        self.change_on_disk()
        self.task.setSubject("ours")
        self.assertRaises(persistence.ChangedOnDiskError, self.taskFile.save)
        self.assertEqual(
            (True, [], ["task", "theirs"]),
            (
                self.taskFile.changed_on_disk(),
                self.noticed,
                self.subjects_on_disk(),
            ),
        )

    def test_save_keeps_the_changes_on_disk(self):
        self.change_on_disk()
        self.notice_changes()
        self.task.setSubject("ours")
        self.assertRaises(persistence.ChangedOnDiskError, self.taskFile.save)
        self.assertEqual(["task", "theirs"], self.subjects_on_disk())

    def test_merging_the_changes_on_disk_allows_saving(self):
        self.change_on_disk()
        self.notice_changes()
        self.task.setSubject("ours")
        self.taskFile.merge_changes_on_disk()
        self.taskFile.save()
        self.assertEqual(["ours", "theirs"], self.subjects_on_disk())

    def test_reloading_allows_saving(self):
        self.change_on_disk()
        self.notice_changes()
        self.taskFile.load()
        self.assertFalse(self.taskFile.changed_on_disk())

    def test_save_as_leaves_the_changed_file(self):
        self.change_on_disk()
        self.notice_changes()
        self.taskFile.saveas(self.filename2)
        self.assertEqual(
            (False, ["task", "theirs"]),
            (self.taskFile.changed_on_disk(), self.subjects_on_disk()),
        )

    def test_failed_save_as_keeps_the_change_on_disk(self):
        self.change_on_disk()
        self.notice_changes()
        self.taskFile._openForWrite = self.fail_to_write
        self.assertRaises(IOError, self.taskFile.saveas, self.filename2)
        self.taskFile.setFilename(self.filename)
        self.assertTrue(self.taskFile.changed_on_disk())

    @staticmethod
    def fail_to_write(*args, **kwargs):
        raise IOError("disk full")


class TaskFileSavedOnDiskTest(TaskFileTestCase):
    """A save puts the new file on disk before it replaces the old one,
    then the folder's entry, so a power cut right after a save leaves
    the old file or the new, never an empty one
    (docs/PERSISTENCE_XML.md, Saving)."""

    def save(self):
        """Save; what reached the disk, in order: ("file"|"folder") for
        each sync, the name for the replace."""
        events = []
        real_fsync, real_replace = os.fsync, os.replace

        def fsync(descriptor):
            folder = stat.S_ISDIR(os.fstat(descriptor).st_mode)
            events.append("folder" if folder else "file")
            real_fsync(descriptor)

        def replace(source, destination):
            events.append(os.path.basename(destination))
            real_replace(source, destination)

        with mock.patch.object(
            os, "fsync", side_effect=fsync
        ), mock.patch.object(os, "replace", side_effect=replace):
            self.taskFile.setFilename(self.filename)
            self.taskFile.save()
        return events

    def test_the_new_file_is_on_disk_before_it_replaces_the_old(self):
        self.assertEqual(["file", self.filename], self.save()[:2])

    def test_then_the_folder(self):
        events = self.save()
        self.assertIn("folder", events[events.index(self.filename) :])

    def test_a_file_written_in_place_is_on_disk_too(self):
        # In a synced cloud folder
        with mock.patch.object(
            persistence.taskfile.SafeWriteFile, "_isCloud", return_value=True
        ):
            self.assertIn("file", self.save())


class OneTrackedTaskTest(TaskFileTestCase):
    """One task tracked at a time: an effort of the file that starts
    being tracked ends the file's other tracked efforts
    (docs/EFFORTS.md, Tracking)."""

    def setUp(self):
        super().setUp()
        self.task2 = task.Task(subject="task 2")
        self.taskFile.tasks().append(self.task2)
        self.tracked = effort.Effort(self.task)
        self.task.addEffort(self.tracked)

    def test_a_new_tracked_effort_ends_the_other(self):
        self.task2.addEffort(effort.Effort(self.task2))
        self.assertFalse(self.tracked.isBeingTracked())

    def test_an_effort_tracked_again_ends_the_other(self):
        stopped = effort.Effort(
            self.task2, date.DateTime(2026, 1, 1), date.DateTime(2026, 1, 2)
        )
        self.task2.addEffort(stopped)
        self.assertTrue(self.tracked.isBeingTracked())
        stopped.setStop(date.DateTime.max)  # The effort editor's no stop
        self.assertFalse(self.tracked.isBeingTracked())

    def test_undoing_a_new_effort_tracks_the_other_again(self):
        patterns.CommandHistory().clear()
        command.NewEffortCommand(self.taskFile.efforts(), [self.task2]).do()
        self.assertFalse(self.tracked.isBeingTracked())
        patterns.CommandHistory().undo()
        self.assertTrue(self.tracked.isBeingTracked())

    def test_a_file_holding_several_keeps_them(self):
        # Saved by an older release
        with open(self.filename, "w", encoding="utf-8") as tsk:
            tsk.write(
                '<?taskcoach release="2.0.2.26" tskversion="37"?>\n'
                "<tasks>"
                '<task id="a" subject="A">'
                '<effort id="ea" start="2026-01-01 10:00:00"/></task>'
                '<task id="b" subject="B">'
                '<effort id="eb" start="2026-01-01 11:00:00"/></task>'
                "</tasks>"
            )
        self.emptyTaskFile.load(self.filename)
        self.assertEqual(2, self.tracked_count())

    def tracked_count(self):
        return len(
            [e for e in self.emptyTaskFile.efforts() if e.isBeingTracked()]
        )

    def test_a_view_of_one_keeps_the_others_tracked(self):
        # A view's list announces the tracked efforts it takes in, as
        # the task editor's Effort tab does for its task
        self.test_a_file_holding_several_keeps_them()
        task_a = [t for t in self.emptyTaskFile.tasks() if t.id() == "a"]
        effort.EffortList(task.TaskList(task_a))
        self.assertEqual(2, self.tracked_count())
