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
import wx
from pubsub import pub
import test
from taskcoachlib import persistence, config
from taskcoachlib.domain import (
    base,
    task,
    effort,
    date,
    category,
    note,
    attachment,
)


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

    def notes(self):
        return self.__notes


class TaskFileTestCase(test.TestCase):
    def setUp(self):
        self.settings = task.Task.settings = config.Settings(load=False)
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
    def testIsEmptyInitially(self):
        self.assertTrue(self.emptyTaskFile.isEmpty())

    def testHasNoTasksInitially(self):
        self.assertFalse(self.emptyTaskFile.tasks())

    def testHasNoCategoriesInitially(self):
        self.assertFalse(self.emptyTaskFile.categories())

    def testHasNoNotesInitially(self):
        self.assertFalse(self.emptyTaskFile.notes())

    def testHasNoEffortsInitially(self):
        self.assertFalse(self.emptyTaskFile.efforts())

    def testFileNameAfterCreate(self):
        self.assertEqual("", self.taskFile.filename())

    def testFileName(self):
        self.taskFile.setFilename(self.filename)
        self.assertEqual(self.filename, self.taskFile.filename())

    def testLoadWithoutFilename(self):
        self.taskFile.load()
        self.assertTrue(self.taskFile.isEmpty())

    def testLoadFromNotExistingFile(self):
        self.taskFile.setFilename(self.filename)
        self.assertFalse(os.path.isfile(self.taskFile.filename()))
        self.taskFile.load()
        self.assertTrue(self.taskFile.isEmpty())

    def testClose_EmptyTaskFileWithoutFilename(self):
        self.taskFile.close()
        self.assertEqual("", self.taskFile.filename())
        self.assertTrue(self.taskFile.isEmpty())

    def testClose_EmptyTaskFileWithFilename(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.close()
        self.assertEqual("", self.taskFile.filename())
        self.assertTrue(self.taskFile.isEmpty())

    def testClose_TaskFileWithTasksDeletesTasks(self):
        self.taskFile.close()
        self.assertTrue(self.taskFile.isEmpty())

    def testClose_TaskFileWithCategoriesDeletesCategories(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.close()
        self.assertTrue(self.taskFile.isEmpty())

    def testClose_TaskFileWithNotesDeletesNotes(self):
        self.taskFile.notes().append(note.Note())
        self.taskFile.close()
        self.assertTrue(self.taskFile.isEmpty())

    def testDoesNotNeedSave_Initial(self):
        self.assertFalse(self.emptyTaskFile.need_save())

    def testDoesNotNeedSave_AfterSetFileName(self):
        self.emptyTaskFile.setFilename(self.filename)
        self.assertFalse(self.emptyTaskFile.need_save())

    def testLastFilename_IsEmptyInitially(self):
        self.assertEqual("", self.taskFile.lastFilename())

    def testLastFilename_EqualsCurrentFilenameAfterSetFilename(self):
        self.taskFile.setFilename(self.filename)
        self.assertEqual(self.filename, self.taskFile.lastFilename())

    def testLastFilename_EqualsPreviousFilenameAfterClose(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.close()
        self.assertEqual(self.filename, self.taskFile.lastFilename())

    def testLastFilename_IsEmptyAfterClosingTwice(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.close()
        self.taskFile.close()
        self.assertEqual(self.filename, self.taskFile.lastFilename())

    def testLastFilename_EqualsCurrentFilenameAfterSaveAs(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.saveas(self.filename2)
        self.assertEqual(self.filename2, self.taskFile.lastFilename())

    def testTaskFileContainsTask(self):
        self.assertTrue(self.task in self.taskFile)

    def testTaskFileDoesNotContainTask(self):
        self.assertFalse(task.Task() in self.taskFile)

    def testTaskFileContainsNote(self):
        newNote = note.Note()
        self.taskFile.notes().append(newNote)
        self.assertTrue(newNote in self.taskFile)

    def testTaskFileDoesNotContainNote(self):
        self.assertFalse(note.Note() in self.taskFile)

    def testTaskFileContainsCategory(self):
        newCategory = category.Category("Category")
        self.taskFile.categories().append(newCategory)
        self.assertTrue(newCategory in self.taskFile)

    def testTaskFileDoesNotContainCategory(self):
        self.assertFalse(category.Category("Category") in self.taskFile)

    def testTaskFileContainsEffort(self):
        newEffort = effort.Effort(self.task)
        self.task.addEffort(newEffort)
        self.assertTrue(newEffort in self.taskFile)

    def testTaskFileDoesNotContainEffort(self):
        self.assertFalse(effort.Effort(self.task) in self.taskFile)


class DirtyTaskFileTest(TaskFileTestCase):
    def setUp(self):
        super().setUp()
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()

    def testSetupFileDoesNotNeedSave(self):
        self.assertFalse(self.taskFile.need_save())

    def testNeedSave_AfterNewTaskAdded(self):
        newTask = task.Task(subject="Task")
        self.emptyTaskFile.tasks().append(newTask)
        self.assertTrue(self.emptyTaskFile.need_save())

    def testNeedSave_AfterNewNoteAdded(self):
        newNote = note.Note(subject="Note")
        self.emptyTaskFile.notes().append(newNote)
        self.assertTrue(self.emptyTaskFile.need_save())

    def testNeedSave_AfterNoteRemoved(self):
        self.taskFile.notes().remove(self.note)
        self.assertTrue(self.taskFile.need_save())

    def testDoesNotNeedSave_AfterSave(self):
        self.emptyTaskFile.tasks().append(task.Task())
        self.emptyTaskFile.setFilename(self.filename)
        self.emptyTaskFile.save()
        self.assertFalse(self.emptyTaskFile.need_save())

    def testDoesNotNeedSave_AfterClose(self):
        self.taskFile.close()
        self.assertFalse(self.taskFile.need_save())

    def testNeedSave_AfterMerge(self):
        self.emptyTaskFile.merge(self.filename)
        self.assertTrue(self.emptyTaskFile.need_save())

    def testDoesNotNeedSave_AfterLoad(self):
        self.taskFile.tasks().append(task.Task())
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.taskFile.close()
        self.taskFile.load()
        self.assertFalse(self.taskFile.need_save())

    def testNeedSave_AfterEffortAdded(self):
        self.task.addEffort(effort.Effort(self.task, None, None))
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterEffortRemoved(self):
        newEffort = effort.Effort(self.task, None, None)
        self.task.addEffort(newEffort)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.task.removeEffort(newEffort)
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

    def testNeedSave_AfterEditTaskSubject(self):
        self.task.setSubject("new subject")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterEditTaskDescription(self):
        self.task.setDescription("new description")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterEditTaskForegroundColor(self):
        self.task.setForegroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterEditTaskBackgroundColor(self):
        self.task.setBackgroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterEditTaskPlannedStartDateTime(self):
        self.task.setPlannedStartDateTime(date.Now() + date.ONE_HOUR)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterEditTaskDueDate(self):
        self.task.setDueDateTime(date.Tomorrow())
        self.assertTrue(self.taskFile.need_save())

    def test_status_changed_by_the_clock_needs_no_save(self):
        due = date.Now() + date.ONE_HOUR
        self.task.setDueDateTime(due)
        self.taskFile.save()
        self.task.compute_stored_status(due + date.ONE_SECOND)  # Overdue
        self.assertEqual(task.status.overdue, self.task.computedStatus())
        self.assertFalse(self.taskFile.need_save())

    def testNeedSave_AfterEditTaskCompletionDate(self):
        self.task.setCompletionDateTime(date.Now())
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterEditPercentageComplete(self):
        self.task.setPercentageComplete(50)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterEditEffortDescription(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.effort.setDescription("new description")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterEditEffortStart(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.effort.setStart(date.DateTime(2005, 1, 1, 10, 0, 0))
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterEditEffortStop(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.effort.setStop(date.DateTime(2005, 1, 1, 10, 0, 0))
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterEditEffortTask(self):
        task2 = task.Task()
        self.taskFile.tasks().append(task2)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.effort.setTask(task2)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterEditEffortForegroundColor(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.effort.setForegroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterEditEffortBackgroundColor(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.effort.setBackgroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterTaskAddedToCategory(self):
        self.task.addCategory(self.category)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterTaskRemovedFromCategory(self):
        self.task.addCategory(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.task.removeCategory(self.category)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterNoteAddedToCategory(self):
        self.note.addCategory(self.category)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterNoteRemovedFromCategory(self):
        self.note.addCategory(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.need_save())
        self.note.removeCategory(self.category)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterAddingNoteToTask(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.task.addNote(note.Note(subject="Note"))  # pylint: disable=E1101
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterTaskNoteChanged(self):
        self.taskFile.setFilename(self.filename)
        newNote = note.Note(subject="Note")
        self.task.addNote(newNote)  # pylint: disable=E1101
        self.taskFile.save()
        newNote.setSubject("New subject")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterChangePriority(self):
        self.task.setPriority(10)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterChangeBudget(self):
        self.task.set_budget(date.TimeDelta(10))
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterChangeHourlyFee(self):
        self.task.set_hourly_fee(100)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterChangeFixedFee(self):
        self.task.set_fixed_fee(500)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterAddChild(self):
        self.taskFile.setFilename(self.filename)
        child = task.Task()
        self.taskFile.tasks().append(child)
        self.taskFile.save()
        self.task.addChild(child)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterRemoveChild(self):
        self.taskFile.setFilename(self.filename)
        child = task.Task()
        self.taskFile.tasks().append(child)
        self.task.addChild(child)
        self.taskFile.save()
        self.task.removeChild(child)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterSetReminder(self):
        self.task.setReminder(date.DateTime(2005, 1, 1, 10, 0, 0))
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterChangeRecurrence(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.task.set_recurrence(date.Recurrence("daily"))
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterChangeSetting(self):
        self.task.set_should_mark_completed_when_all_children_completed(True)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterAddingCategory(self):
        self.taskFile.categories().append(self.category)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterRemovingCategory(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.taskFile.categories().remove(self.category)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterFilteringCategory(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.category.setFiltered()
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterCategorySubjectChanged(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.category.setSubject("new subject")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterCategoryDescriptionChanged(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.category.setDescription("new description")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterChangingCategoryForegroundColor(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.category.setForegroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterChangingCategoryBackgroundColor(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.category.setBackgroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterMakingSubclassesExclusive(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.category.makeSubcategoriesExclusive()
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterNoteSubjectChanged(self):
        list(self.taskFile.notes())[0].setSubject("new subject")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterNoteDescriptionChanged(self):
        list(self.taskFile.notes())[0].setDescription("new description")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterNoteForegroundColorChanged(self):
        list(self.taskFile.notes())[0].setForegroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterNoteBackgroundColorChanged(self):
        list(self.taskFile.notes())[0].setBackgroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterAddNoteChild(self):
        list(self.taskFile.notes())[0].addChild(note.Note())
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterRemoveNoteChild(self):
        child = note.Note()
        list(self.taskFile.notes())[0].addChild(child)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        list(self.taskFile.notes())[0].removeChild(child)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterChangingTaskExpansionState(self):
        self.task.expand()
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterChangingCategoryExpansionState(self):
        self.taskFile.categories().append(self.category)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.category.expand()
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterChangingNoteExpansionState(self):
        self.taskFile.notes().append(self.note)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.note.expand()
        self.assertTrue(self.taskFile.need_save())

    def testLastFilename_EqualsCurrentFilenameAfterSetFilename(self):
        self.taskFile.setFilename(self.filename)
        self.assertEqual(self.filename, self.taskFile.lastFilename())

    def testLastFilename_EqualsPreviousFilenameAfterClose(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.close()
        self.assertEqual(self.filename, self.taskFile.lastFilename())

    def testLastFilename_EqualsPreviousFilenameAfterClosingTwice(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.close()
        self.taskFile.close()
        self.assertEqual(self.filename, self.taskFile.lastFilename())

    def testLastFilename_EqualsCurrentFilenameAfterSaveAs(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.saveas(self.filename2)
        self.assertEqual(self.filename2, self.taskFile.lastFilename())


class ChangingAttachmentsTestsMixin(object):
    def testNeedSave_AfterAttachmentAdded(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.item.addAttachments(self.attachment)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterAttachmentRemoved(self):
        self.taskFile.setFilename(self.filename)
        self.item.addAttachments(self.attachment)
        self.taskFile.save()
        self.item.removeAttachments(self.attachment)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterAttachmentsReplaced(self):
        self.taskFile.setFilename(self.filename)
        self.item.addAttachments(self.attachment)
        self.taskFile.save()
        self.item.setAttachments([FakeAttachment("file", "attachment2")])
        self.assertTrue(self.taskFile.need_save())

    def addAttachment(self, anAttachment):
        self.taskFile.setFilename(self.filename)
        self.item.addAttachments(anAttachment)
        self.taskFile.save()

    def addFileAttachment(self):
        self.fileAttachment = attachment.FileAttachment(
            "Old location"
        )  # pylint: disable=W0201
        self.addAttachment(self.fileAttachment)

    def testNeedSave_AfterFileAttachmentLocationChanged(self):
        self.addFileAttachment()
        self.fileAttachment.setLocation("New location")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterFileAttachmentSubjectChanged(self):
        self.addFileAttachment()
        self.fileAttachment.setSubject("New subject")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterFileAttachmentDescriptionChanged(self):
        self.addFileAttachment()
        self.fileAttachment.setDescription("New description")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterFileAttachmentForegroundColorChanged(self):
        self.addFileAttachment()
        self.fileAttachment.setForegroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterFileAttachmentBackgroundColorChanged(self):
        self.addFileAttachment()
        self.fileAttachment.setBackgroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterFileAttachmentNoteAdded(self):
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

    def testNeedSave_AfterURIAttachmentLocationChanged(self):
        self.addURIAttachment()
        self.uriAttachment.setLocation("New location")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterURIAttachmentSubjectChanged(self):
        self.addURIAttachment()
        self.uriAttachment.setSubject("New subject")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterURIAttachmentDescriptionChanged(self):
        self.addURIAttachment()
        self.uriAttachment.setDescription("New description")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterURIAttachmentForegroundColorChanged(self):
        self.addURIAttachment()
        self.uriAttachment.setForegroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterURIAttachmentBackgroundColorChanged(self):
        self.addURIAttachment()
        self.uriAttachment.setBackgroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterURIAttachmentNoteAdded(self):
        self.addURIAttachment()
        self.uriAttachment.addNote(
            note.Note(subject="Note")
        )  # pylint: disable=E1101
        self.assertTrue(self.taskFile.need_save())

    def addMailAttachment(self):
        self.mailAttachment = attachment.MailAttachment(
            self.filename,  # pylint: disable=W0201
            readMail=lambda location: ("", ""),
        )
        self.addAttachment(self.mailAttachment)

    def testNeedSave_AfterMailAttachmentLocationChanged(self):
        self.addMailAttachment()
        self.mailAttachment.setLocation("New location")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterMailAttachmentSubjectChanged(self):
        self.addMailAttachment()
        self.mailAttachment.setSubject("New subject")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterMailAttachmentDescriptionChanged(self):
        self.addMailAttachment()
        self.mailAttachment.setDescription("New description")
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterMailAttachmentForegroundColorChanged(self):
        self.addMailAttachment()
        self.mailAttachment.setForegroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterMailAttachmentBackgroundColorChanged(self):
        self.addMailAttachment()
        self.mailAttachment.setBackgroundColor(wx.RED)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterMailAttachmentNoteAdded(self):
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
            sorted([eachTask.subject() for eachTask in tasks]),
            sorted(
                [eachTask.subject() for eachTask in self.emptyTaskFile.tasks()]
            ),
        )
        self.assertEqual(
            sorted([eachCategory.subject() for eachCategory in categories]),
            sorted(
                [
                    eachCategory.subject()
                    for eachCategory in self.emptyTaskFile.categories()
                ]
            ),
        )
        self.assertEqual(
            sorted([eachNote.subject() for eachNote in notes]),
            sorted(
                [eachNote.subject() for eachNote in self.emptyTaskFile.notes()]
            ),
        )

    def testSaveAndLoad(self):
        self.saveAndLoad(
            [task.Task(subject="ABC"), task.Task(dueDateTime=date.Tomorrow())]
        )

    def testSaveAndLoadTaskWithChild(self):
        parentTask = task.Task()
        childTask = task.Task(parent=parentTask)
        parentTask.addChild(childTask)
        self.saveAndLoad([parentTask, childTask])

    def testSaveAndLoadCategory(self):
        self.saveAndLoad([], [self.category])

    def testSaveAndLoadNotes(self):
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

    def testSaveAs(self):
        self.taskFile.saveas("new.tsk")
        self.taskFile.load()
        self.assertEqual(1, len(self.taskFile.tasks()))
        self.taskFile.close()
        self.remove("new.tsk")

    def testSaveAsOverwrites(self):
        self.taskFile.saveas("new.tsk")
        self.taskFile.close()
        self.taskFile.tasks().extend([task.Task(subject="foo")])
        self.taskFile.saveas("new.tsk")
        self.assertEqual(1, len(self.taskFile.tasks()))
        self.taskFile.close()
        self.remove("new.tsk")


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

    def testMerge_Tasks(self):
        self.mergeFile.tasks().append(task.Task())
        self.merge()
        self.assertEqual(2, len(self.taskFile.tasks()))

    def test_merge_sends_no_messages_about_the_merged_file(self):
        self.mergeFile.save()
        names = []

        def on_filename_changed(filename):
            names.append(filename)

        pub.subscribe(on_filename_changed, "taskfile.filenameChanged")
        try:
            self.taskFile.merge("merge.tsk")
        finally:
            pub.unsubscribe(on_filename_changed, "taskfile.filenameChanged")
        self.assertEqual([], names)

    def test_merge_only_reads_the_merged_file(self):
        # It may be open in another Task Coach
        self.mergeFile.save()
        os.utime("merge.tsk", ns=(10**18, 10**18))
        self.taskFile.merge("merge.tsk")
        self.assertEqual(10**18, os.stat("merge.tsk").st_mtime_ns)
        self.assertEqual(["merge.tsk"], glob.glob("merge.tsk*"))

    def testMerge_TasksWithSubtask(self):
        parent = task.Task(subject="parent")
        child = task.Task(subject="child")
        parent.addChild(child)
        child.setParent(parent)
        self.mergeFile.tasks().extend([parent, child])
        self.merge()
        self.assertEqual(3, len(self.taskFile.tasks()))
        self.assertEqual(2, len(self.taskFile.tasks().rootItems()))

    def testMerge_OneCategoryInMergeFile(self):
        self.taskFile.categories().remove(self.category)
        self.mergeFile.categories().append(self.category)
        self.merge()
        self.assertEqual(
            [self.category.subject()],
            [cat.subject() for cat in self.taskFile.categories()],
        )

    def testMerge_DifferentCategories(self):
        self.mergeFile.categories().append(
            category.Category("another category")
        )
        self.merge()
        self.assertEqual(2, len(self.taskFile.categories()))

    def testMerge_SameSubject(self):
        self.mergeFile.categories().append(
            category.Category(self.category.subject())
        )
        self.merge()
        self.assertEqual(
            [self.category.subject()] * 2,
            [cat.subject() for cat in self.taskFile.categories()],
        )

    def testMerge_CategoryWithTask(self):
        self.taskFile.categories().remove(self.category)
        self.mergeFile.categories().append(self.category)
        aTask = task.Task(subject="merged task")
        self.mergeFile.tasks().append(aTask)
        self.category.addCategorizable(aTask)
        self.merge()
        self.assertEqual(
            aTask.id(),
            list(list(self.taskFile.categories())[0].categorizables())[0].id(),
        )

    def testMerge_Notes(self):
        newNote = note.Note(subject="new note")
        self.mergeFile.notes().append(newNote)
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
        self.category.addCategorizable(self.task)
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
        their_child.setParent(their_parent)
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

    def testMerge_SameNote(self):
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

    def testMerge_SameCategory(self):
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

    def test_task_links_to_the_winning_category(self):
        self.task.addCategory(self.category)
        self.category.addCategorizable(self.task)
        self.category.set_modification_datetime(date.DateTime(2020, 1, 1))
        their_category = self.their_copy(
            self.category, "merged category", date.DateTime(2021, 1, 1)
        )
        their_task = task.Task(subject="task", id=self.task.id())
        their_category.addCategorizable(their_task)
        their_task.addCategory(their_category)
        self.mergeFile.categories().append(their_category)
        self.mergeFile.tasks().append(their_task)
        self.merge()
        winner = list(self.taskFile.categories())[0]
        self.assertIs(winner, list(self.task.categories())[0])
        self.assertEqual("merged category", winner.subject())

    def testMerge_CategoryLinkedToTask(self):
        self.task.addCategory(self.category)
        self.category.addCategorizable(self.task)
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

    def testMerge_CategoryLinkedToNote(self):
        self.note.addCategory(self.category)
        self.category.addCategorizable(self.note)
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
        subcategory.addCategorizable(self.task)
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

    def test_save_writes_memory_over_changes_on_disk(self):
        # One Task Coach per file: saving merges nothing from the disk
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        other = persistence.TaskFile()
        self.addCleanup(other.stop)
        other.load(self.filename)
        other.tasks().append(task.Task(subject="on disk"))
        other.save()
        other.close()
        self.taskFile.tasks().remove(self.task)
        self.taskFile.save()
        self.taskFile.close()
        self.emptyTaskFile.load(self.filename)
        self.assertEqual(0, len(self.emptyTaskFile.tasks()))

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
