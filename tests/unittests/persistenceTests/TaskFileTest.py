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

import os, wx
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
            self.filename + ".delta",
            self.filename2 + ".delta",
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

    def testNeedSave_AfterTaskMarkedDeleted(self):
        self.task.markDeleted()
        self.assertTrue(self.taskFile.need_save())

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
        self.task.setBudget(date.TimeDelta(10))
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterChangeHourlyFee(self):
        self.task.setHourlyFee(100)
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterChangeFixedFee(self):
        self.task.setFixedFee(500)
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
        self.task.setRecurrence(date.Recurrence("daily"))
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterChangeSetting(self):
        self.task.setShouldMarkCompletedWhenAllChildrenCompleted(True)
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

    def testNeedSave_AfterMarkDeleted(self):
        self.taskFile.notes().append(self.note)
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.note.markDeleted()
        self.assertTrue(self.taskFile.need_save())

    def testNeedSave_AfterMarkNotDeleted(self):
        self.taskFile.notes().append(self.note)
        self.note.markDeleted()
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.note.cleanDirty()
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

    def testSaveAs(self):
        self.taskFile.saveas("new.tsk")
        self.taskFile.load()
        self.assertEqual(1, len(self.taskFile.tasks()))
        self.taskFile.close()
        self.remove("new.tsk", "new.tsk.delta")

    def testSaveAsOverwrites(self):
        self.taskFile.saveas("new.tsk")
        self.taskFile.close()
        self.taskFile.tasks().extend([task.Task(subject="foo")])
        self.taskFile.saveas("new.tsk")
        self.assertEqual(1, len(self.taskFile.tasks()))
        self.taskFile.close()
        self.remove("new.tsk", "new.tsk.delta")


class TaskFileMergeTest(TaskFileTestCase):
    def setUp(self):
        super().setUp()
        self.mergeFile = persistence.TaskFile()
        self.mergeFile.setFilename("merge.tsk")

    def tearDown(self):
        self.mergeFile.close()
        self.mergeFile.stop()
        self.remove("merge.tsk", "merge.tsk.delta")
        super().tearDown()

    def merge(self):
        self.mergeFile.save()
        self.taskFile.merge("merge.tsk")

    def testMerge_Tasks(self):
        self.mergeFile.tasks().append(task.Task())
        self.merge()
        self.assertEqual(2, len(self.taskFile.tasks()))

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

    def testMerge_SameTask(self):
        mergedTask = task.Task(subject="merged task", id=self.task.id())
        self.mergeFile.tasks().append(mergedTask)
        self.merge()
        self.assertEqual(1, len(self.taskFile.tasks()))
        self.assertEqual(
            "merged task", list(self.taskFile.tasks())[0].subject()
        )

    def testMerge_SameNote(self):
        mergedNote = note.Note(subject="merged note", id=self.note.id())
        self.mergeFile.notes().append(mergedNote)
        self.merge()
        self.assertEqual(1, len(self.taskFile.notes()))
        self.assertEqual(
            "merged note", list(self.taskFile.notes())[0].subject()
        )

    def testMerge_SameCategory(self):
        mergedCategory = category.Category(
            subject="merged category", id=self.category.id()
        )
        self.mergeFile.categories().append(mergedCategory)
        self.merge()
        self.assertEqual(1, len(self.taskFile.categories()))
        self.assertEqual(
            "merged category", list(self.taskFile.categories())[0].subject()
        )

    def testMerge_CategoryLinkedToTask(self):
        self.task.addCategory(self.category)
        self.category.addCategorizable(self.task)
        mergedCategory = category.Category(
            "merged category", id=self.category.id()
        )
        self.mergeFile.categories().append(mergedCategory)
        self.merge()
        self.assertEqual(
            self.category.id(), list(self.task.categories())[0].id()
        )

    def testMerge_CategoryLinkedToNote(self):
        self.note.addCategory(self.category)
        self.category.addCategorizable(self.note)
        mergedCategory = category.Category(
            "merged category", id=self.category.id()
        )
        self.mergeFile.categories().append(mergedCategory)
        self.merge()
        self.assertEqual(
            self.category.id(), list(self.note.categories())[0].id()
        )

    def testMerge_ExistingCategoryWithoutExistingSubCategoryRemovesTheSubCategory(
        self,
    ):
        subCategory = category.Category("subcategory")
        self.category.addChild(subCategory)
        self.taskFile.categories().append(subCategory)
        self.task.addCategory(subCategory)
        subCategory.addCategorizable(self.task)
        self.assertEqual(2, len(self.taskFile.categories()))
        mergedCategory = category.Category(
            "merged category", id=self.category.id()
        )
        self.mergeFile.categories().append(mergedCategory)
        self.merge()
        self.assertEqual(1, len(self.taskFile.categories()))


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

    def testFileIsNotLockedInitially(self):
        self.assertFalse(self.taskFile.is_locked())
        self.assertFalse(self.emptyTaskFile.is_locked())

    def testFileIsNotLockedAfterLoading(self):
        self.taskFile.load(self.filename)
        self.assertFalse(self.taskFile.is_locked())

    def testFileIsNotLockedAfterClosing(self):
        self.taskFile.close()
        self.assertFalse(self.taskFile.is_locked())

    def testFileIsnotLockedAfterLoadingAndClosing(self):
        self.taskFile.load(self.filename)
        self.taskFile.close()
        self.assertFalse(self.taskFile.is_locked())

    def testFileIsNotLockedAfterSaving(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.assertFalse(self.taskFile.is_locked())

    def testFileIsNotLockedAfterSavingAndClosing(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.taskFile.close()
        self.assertFalse(self.taskFile.is_locked())

    def testFileIsNotLockedAfterSaveAs(self):
        self.taskFile.saveas(self.filename)
        self.assertFalse(self.taskFile.is_locked())

    def testFileIsNotLockedAfterSaveAndSaveAs(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.taskFile.saveas(self.filename2)
        self.assertFalse(self.taskFile.is_locked())

    def testFileCanBeLoadedAfterClose(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.taskFile.close()
        self.emptyTaskFile.load(self.filename)
        self.assertEqual(1, len(self.emptyTaskFile.tasks()))

    def testOriginalFileCanBeLoadedAfterSaveAs(self):
        self.taskFile.setFilename(self.filename)
        self.taskFile.save()
        self.taskFile.saveas(self.filename2)
        self.taskFile.close()
        self.emptyTaskFile.load(self.filename)
        self.assertEqual(1, len(self.emptyTaskFile.tasks()))


class TaskFileMonitorTestBase(TaskFileTestCase):
    def setUp(self):
        super().setUp()

        self.taskFile.saveas(self.filename)
        self.taskFile.load()

        self.otherFile = persistence.TaskFile()
        self.otherFile.setFilename(self.filename)
        self.otherFile.load()

    def tearDown(self):
        self.otherFile.close()
        self.otherFile.stop()
        self.remove("other.tsk")
        super().tearDown()

    def testTaskExistsAfterLoad(self):
        self.assertEqual(self.taskFile.monitor().getChanges(self.task), set())

    def testCategoryExistsAfterLoad(self):
        self.assertEqual(
            self.taskFile.monitor().getChanges(self.category), set()
        )

    def testNoteExistsAfterLoad(self):
        self.assertEqual(self.taskFile.monitor().getChanges(self.note), set())

    def testChangeTask(self):
        self.task.setSubject("New subject")
        self.assertEqual(
            self.taskFile.monitor().getChanges(self.task), set(["subject"])
        )

    def testChangeCategory(self):
        self.category.setSubject("New subject")
        self.assertEqual(
            self.taskFile.monitor().getChanges(self.category), set(["subject"])
        )

    def testChangeNone(self):
        self.note.setSubject("New subject")
        self.assertEqual(
            self.taskFile.monitor().getChanges(self.note), set(["subject"])
        )

    def testChangesResetAfterSave(self):
        self.task.setSubject("New subject")
        self.taskFile.save()
        self.assertEqual(
            self.taskFile.monitor().getChanges(self.task), set([])
        )

    def testResetAfterClose(self):
        self.taskFile.close()
        self.assertEqual(self.taskFile.monitor().getChanges(self.task), None)

    def _loadChangesFromFile(self, filename):
        return persistence.ChangesXMLReader(
            open(filename + ".delta", "r")
        ).read()

    def testGUIDPresentAfterLoad(self):
        self.assertTrue(
            self.taskFile.monitor().guid()
            in self._loadChangesFromFile(self.filename)
        )

    def testGUIDNotPresentAfterClose(self):
        self.taskFile.close()
        self.assertFalse(
            self.taskFile.monitor().guid()
            in self._loadChangesFromFile(self.filename)
        )

    def testChangeOtherSetsChanges(self):
        self.otherFile.monitor().setChanges(self.task.id(), set(["subject"]))
        self.otherFile.save()
        allChanges = self._loadChangesFromFile(self.filename)
        self.assertEqual(
            allChanges[self.taskFile.monitor().guid()].getChanges(self.task),
            set(["subject"]),
        )
        self.assertEqual(
            allChanges[self.otherFile.monitor().guid()].getChanges(self.task),
            set(),
        )

    def testDeleteObject(self):
        self.otherFile.tasks().remove(self.otherFile.tasks().rootItems()[0])
        self.otherFile.save()
        allChanges = self._loadChangesFromFile(self.filename)
        self.assertEqual(
            allChanges[self.taskFile.monitor().guid()].getChanges(self.task),
            set(["__del__"]),
        )
        self.assertEqual(
            allChanges[self.otherFile.monitor().guid()].getChanges(self.task),
            None,
        )

    def testDiskChangesAfterLoad(self):
        changes = self._loadChangesFromFile(self.filename)[
            self.taskFile.monitor().guid()
        ]
        self.assertEqual(changes.getChanges(self.task), set())

    def testNewObject(self):
        item = task.Task(subject="New task")
        self.otherFile.tasks().append(item)
        self.otherFile.save()
        self.taskFile.save()
        allChanges = self._loadChangesFromFile(self.filename)
        self.assertEqual(
            allChanges[self.otherFile.monitor().guid()].getChanges(item), set()
        )
        self.assertEqual(
            allChanges[self.taskFile.monitor().guid()].getChanges(item), set()
        )


class TaskFileMultiUserTestBase(object):
    def setUp(self):
        self.createTaskFiles()

        self.task = task.Task(subject="Task")
        self.taskFile1.tasks().append(self.task)

        self.category = category.Category(subject="Category")
        self.taskFile1.categories().append(self.category)

        self.note = note.Note(subject="Note")
        self.taskFile1.notes().append(self.note)

        self.taskNote = note.Note(subject="Task note")
        self.task.addNote(self.taskNote)

        self.attachment = attachment.FileAttachment("foobarfile")
        self.task.addAttachment(self.attachment)

        self.filename = "test.tsk"

        self.taskFile1.setFilename(self.filename)
        self.taskFile2.setFilename(self.filename)

        self.taskFile1.save()
        self.taskFile2.load()

    def createTaskFiles(self):
        # pylint: disable-msg=W0201
        self.taskFile1 = persistence.TaskFile()
        self.taskFile2 = persistence.TaskFile()

    def tearDown(self):
        self.taskFile1.close()
        self.taskFile1.stop()
        self.taskFile2.close()
        self.taskFile2.stop()
        self.remove(self.filename)

    def remove(self, *filenames):
        for filename in filenames:
            tries = 0
            while os.path.exists(filename) and tries < 3:
                try:  # Don't fail on random 'Access denied' errors.
                    os.remove(filename)
                    break
                except WindowsError:
                    tries += 1

    def _assertIdInList(self, objects, id_):
        for obj in objects:
            if obj.id() == id_:
                break
        else:
            self.fail("ID %s not found" % id_)
        return obj

    def _testCreateObjectInOther(self, class_, listName):
        newObject = class_(subject="New %s" % class_.__name__)
        getattr(self.taskFile1, listName)().append(newObject)
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(len(getattr(self.taskFile2, listName)()), 2)
        self._assertIdInList(
            getattr(self.taskFile2, listName)().rootItems(), newObject.id()
        )

    def testOtherCreatesCategory(self):
        self._testCreateObjectInOther(category.Category, "categories")

    def testOtherCreatesTask(self):
        self._testCreateObjectInOther(task.Task, "tasks")

    def testOtherCreatesNote(self):
        self._testCreateObjectInOther(note.Note, "notes")

    def _testCreateChildInOther(self, listName):
        item = getattr(self.taskFile1, listName)().rootItems()[0]
        subItem = item.newChild(subject="New sub%s" % item.__class__.__name__)
        getattr(self.taskFile1, listName)().append(subItem)
        item.addChild(subItem)
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(len(getattr(self.taskFile2, listName)()), 2)
        otherItem = getattr(self.taskFile2, listName)().rootItems()[0]
        self.assertEqual(len(otherItem.children()), 1)
        self.assertEqual(otherItem.children()[0].id(), subItem.id())

    def testOtherCreatesSubcategory(self):
        self._testCreateChildInOther("categories")

    def testOtherCreatesSubtask(self):
        self._testCreateChildInOther("tasks")

    def testOtherCreatesSubnote(self):
        self._testCreateChildInOther("notes")

    def _testCreateObjectWithChildInOther(self, class_, listName):
        item = class_(subject="New %s" % class_.__name__)
        subItem = item.newChild(subject="New sub%s" % class_.__name__)
        item.addChild(subItem)
        getattr(self.taskFile1, listName)().append(item)
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(len(getattr(self.taskFile2, listName)()), 3)
        otherItem = self._assertIdInList(
            getattr(self.taskFile2, listName)().rootItems(), item.id()
        )
        self.assertEqual(len(otherItem.children()), 1)
        self.assertEqual(otherItem.children()[0].id(), subItem.id())

    def testOtherCreatesCategoryWithChild(self):
        self._testCreateObjectWithChildInOther(category.Category, "categories")

    def testOtherCreatesTaskWithChild(self):
        self._testCreateObjectWithChildInOther(task.Task, "tasks")

    def testOtherCreatesNoteWithChild(self):
        self._testCreateObjectWithChildInOther(note.Note, "notes")

    def _testCreateObjectAndReparentExisting(self, listName):
        item = getattr(self.taskFile1, listName)().rootItems()[0]
        newItem = item.__class__(subject="New %s" % item.__class__.__name__)
        getattr(self.taskFile1, listName)().append(newItem)
        newItem.addChild(item)
        item.setParent(newItem)
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(len(getattr(self.taskFile2, listName)()), 2)
        for otherItem in getattr(self.taskFile2, listName)().rootItems():
            if otherItem.id() == newItem.id():
                break
        else:
            self.fail()
        self.assertEqual(len(otherItem.children()), 1)
        self.assertEqual(otherItem.children()[0].id(), item.id())

    def testOtherCreatesCategoryAndReparentsExisting(self):
        self._testCreateObjectAndReparentExisting("categories")

    def testOtherCreatesTaskAndReparentsExisting(self):
        self._testCreateObjectAndReparentExisting("tasks")

    def testOtherCreatesNoteAndReparentsExisting(self):
        self._testCreateObjectAndReparentExisting("notes")

    def _testChangeAttribute(self, name, value, listName):
        obj = getattr(self.taskFile1, listName)().rootItems()[0]
        getattr(obj, "set" + name[0].upper() + name[1:])(value)
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            getattr(
                getattr(self.taskFile2, listName)().rootItems()[0], name
            )(),
            value,
        )

    def _testExpand(self, listName):
        obj = getattr(self.taskFile1, listName)().rootItems()[0]
        obj.expand()
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertTrue(
            getattr(self.taskFile2, listName)().rootItems()[0].isExpanded()
        )

    def testChangeCategoryName(self):
        self._testChangeAttribute("subject", "New category name", "categories")

    def testChangeCategoryDescription(self):
        self._testChangeAttribute(
            "description", "New category description", "categories"
        )

    def testExpandCategory(self):
        self._testExpand("categories")

    def testChangeTaskSubject(self):
        self._testChangeAttribute("subject", "New task subject", "tasks")

    def testChangeTaskDescription(self):
        self._testChangeAttribute(
            "description", "New task description", "tasks"
        )

    def testExpandTask(self):
        self._testExpand("tasks")

    def testChangeNoteSubject(self):
        self._testChangeAttribute("subject", "New note subject", "notes")

    def testChangeNoteDescription(self):
        self._testChangeAttribute(
            "description", "New note description", "notes"
        )

    def testChangeTaskStartDateTime(self):
        self._testChangeAttribute(
            "plannedStartDateTime", date.DateTime(2011, 6, 15), "tasks"
        )

    def testChangeTaskDueDateTime(self):
        self._testChangeAttribute(
            "dueDateTime", date.DateTime(2011, 7, 16), "tasks"
        )

    def testChangeTaskCompletionDateTime(self):
        self._testChangeAttribute(
            "completionDateTime", date.DateTime(2011, 2, 1), "tasks"
        )

    def testChangeTaskPrecentageComplete(self):
        self._testChangeAttribute("percentageComplete", 42, "tasks")

    def testChangeTaskRecurrence(self):
        self._testChangeAttribute(
            "recurrence", date.Recurrence("daily", 3), "tasks"
        )

    def testChangeTaskReminder(self):
        self._testChangeAttribute(
            "reminder", date.DateTime(2999, 2, 1), "tasks"
        )

    def testChangeTaskBudget(self):
        self._testChangeAttribute(
            "budget", date.TimeDelta(seconds=60), "tasks"
        )

    def testChangeTaskPriority(self):
        self._testChangeAttribute("priority", 42, "tasks")

    def testChangeTaskHourlyFee(self):
        self._testChangeAttribute("hourlyFee", 42, "tasks")

    def testChangeTaskFixedFee(self):
        self._testChangeAttribute("fixedFee", 42, "tasks")

    def testChangeTaskShouldMarkCompletedWhenAllChildrenCompleted(self):
        self._testChangeAttribute(
            "shouldMarkCompletedWhenAllChildrenCompleted", False, "tasks"
        )

    def testExpandNote(self):
        self._testExpand("notes")

    def _testChangeAppearance(
        self, listName, attrName, initialValue, newValue
    ):
        setName = "set" + attrName[0].upper() + attrName[1:]
        obj = getattr(self.taskFile1, listName)().rootItems()[0]
        newObj = getattr(self.taskFile2, listName)().rootItems()[0]
        getattr(obj, setName)(initialValue)
        getattr(newObj, setName)(initialValue)
        self.taskFile1.monitor().resetAllChanges()
        self.taskFile2.monitor().resetAllChanges()
        getattr(obj, setName)(newValue)
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(getattr(newObj, attrName)(), newValue)

    def testChangeCategoryForeground(self):
        self._testChangeAppearance(
            "categories", "foregroundColor", (128, 128, 128), (255, 255, 0)
        )

    def testChangeCategoryBackground(self):
        self._testChangeAppearance(
            "categories", "backgroundColor", (128, 128, 128), (255, 255, 0)
        )

    def testChangeCategoryIcon(self):
        self._testChangeAppearance(
            "categories", "icon", "initialIcon", "finalIcon"
        )

    def testChangeCategorySelectedIcon(self):
        self._testChangeAppearance(
            "categories", "selectedIcon", "initialIcon", "finalIcon"
        )

    def testChangeNoteForeground(self):
        self._testChangeAppearance(
            "notes", "foregroundColor", (128, 128, 128), (255, 255, 0)
        )

    def testChangeNoteBackground(self):
        self._testChangeAppearance(
            "notes", "backgroundColor", (128, 128, 128), (255, 255, 0)
        )

    def testChangeNoteIcon(self):
        self._testChangeAppearance("notes", "icon", "initialIcon", "finalIcon")

    def testChangeNoteSelectedIcon(self):
        self._testChangeAppearance(
            "notes", "selectedIcon", "initialIcon", "finalIcon"
        )

    def testChangeTaskBackground(self):
        self._testChangeAppearance(
            "tasks", "backgroundColor", (128, 128, 128), (255, 255, 0)
        )

    def testChangeTaskIcon(self):
        self._testChangeAppearance("tasks", "icon", "initialIcon", "finalIcon")

    def testChangeTaskSelectedIcon(self):
        self._testChangeAppearance(
            "tasks", "selectedIcon", "initialIcon", "finalIcon"
        )

    def testChangeExclusiveSubcategories(self):
        self.category.makeSubcategoriesExclusive(True)
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertTrue(
            self.taskFile2.categories()
            .rootItems()[0]
            .hasExclusiveSubcategories()
        )

    def _testAddObjectCategory(self, listName):
        obj = getattr(self.taskFile1, listName)().rootItems()[0]
        obj.addCategory(self.category)
        self.category.addCategorizable(obj)
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        newObj = getattr(self.taskFile2, listName)().rootItems()[0]
        self.assertEqual(len(newObj.categories()), 1)
        self.assertEqual(newObj.categories().pop().id(), self.category.id())

    def testAddNoteCategory(self):
        self._testAddObjectCategory("notes")

    def testAddTaskCategory(self):
        self._testAddObjectCategory("tasks")

    def _testChangeObjectCategory(self, listName):
        self.category2 = category.Category(subject="Other category")
        self.taskFile1.categories().append(self.category2)
        obj = getattr(self.taskFile1, listName)().rootItems()[0]
        obj.addCategory(self.category)
        self.category.addCategorizable(obj)
        self.taskFile1.save()
        self.taskFile2.save()
        # Load => CategoryList => addCategory()...
        self.taskFile1.monitor().resetAllChanges()

        self.category.removeCategorizable(obj)
        obj.removeCategory(self.category)
        self.category2.addCategorizable(obj)
        obj.addCategory(self.category2)

        self.taskFile1.save()
        self.taskFile2.monitor().resetAllChanges()
        self.doSave(self.taskFile2)

        newObj = getattr(self.taskFile2, listName)().rootItems()[0]
        self.assertEqual(len(newObj.categories()), 1)
        self.assertEqual(newObj.categories().pop().id(), self.category2.id())

    def testChangeNoteCategory(self):
        self._testChangeObjectCategory("notes")

    def testChangeTaskCategory(self):
        self._testChangeObjectCategory("tasks")

    def _testDeleteObject(self, listName):
        item = getattr(self.taskFile1, listName)().rootItems()[0]
        getattr(self.taskFile1, listName)().remove(item)
        self.taskFile1.save()
        self.taskFile2.monitor().setChanges(item.id(), set())
        self.doSave(self.taskFile2)
        self.assertEqual(len(getattr(self.taskFile1, listName)()), 0)
        self.assertEqual(len(getattr(self.taskFile2, listName)()), 0)

    def _testDeleteModifiedLocalObject(self, listName):
        item = getattr(self.taskFile1, listName)().rootItems()[0]
        getattr(self.taskFile1, listName)().remove(item)
        self.taskFile1.save()
        getattr(self.taskFile2, listName)().rootItems()[0].setSubject(
            "New subject."
        )
        self.doSave(self.taskFile2)
        self.assertEqual(len(getattr(self.taskFile2, listName)()), 1)

    def _testDeleteModifiedRemoteObject(self, listName):
        getattr(self.taskFile1, listName)().rootItems()[0].setSubject(
            "New subject."
        )
        self.taskFile1.save()
        item = getattr(self.taskFile2, listName)().rootItems()[0]
        getattr(self.taskFile2, listName)().remove(item)
        self.doSave(self.taskFile2)
        self.assertEqual(len(getattr(self.taskFile2, listName)()), 1)
        self.assertEqual(
            getattr(self.taskFile2, listName)().rootItems()[0].subject(),
            "New subject.",
        )

    def testDeleteCategory(self):
        self._testDeleteObject("categories")

    def testDeleteNote(self):
        self._testDeleteObject("notes")

    def testDeleteTask(self):
        self._testDeleteObject("tasks")

    def testDeleteModifiedLocalCategory(self):
        self._testDeleteModifiedLocalObject("categories")

    def testDeleteModifiedLocalNote(self):
        self._testDeleteModifiedLocalObject("notes")

    def testDeleteModifiedLocalTask(self):
        self._testDeleteModifiedLocalObject("tasks")

    def testDeleteModifiedRemoteCategory(self):
        self._testDeleteModifiedRemoteObject("categories")

    def testDeleteModifiedRemoteNote(self):
        self._testDeleteModifiedRemoteObject("notes")

    def testDeleteModifiedRemoteTask(self):
        self._testDeleteModifiedRemoteObject("tasks")

    def _testAddNoteToObject(self, listName):
        newNote = note.Note(subject="Other note")
        getattr(self.taskFile1, listName)().rootItems()[0].addNote(newNote)
        noteCount = len(
            getattr(self.taskFile1, listName)().rootItems()[0].notes()
        )
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            len(getattr(self.taskFile2, listName)().rootItems()[0].notes()),
            noteCount,
        )

    def testAddNoteToTask(self):
        self._testAddNoteToObject("tasks")

    def testAddNoteToCategory(self):
        self._testAddNoteToObject("categories")

    def testAddNoteToAttachment(self):
        newNote = note.Note(subject="Attachment note")
        self.attachment.addNote(newNote)
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            len(
                self.taskFile2.tasks().rootItems()[0].attachments()[0].notes()
            ),
            1,
        )

    def _testAddAttachmentToObject(self, listName):
        newAttachment = attachment.FileAttachment("Other attachment")
        getattr(self.taskFile1, listName)().rootItems()[0].addAttachment(
            newAttachment
        )
        attachmentCount = len(
            getattr(self.taskFile1, listName)().rootItems()[0].attachments()
        )
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            len(
                getattr(self.taskFile2, listName)()
                .rootItems()[0]
                .attachments()
            ),
            attachmentCount,
        )

    def testAddAttachmentToTask(self):
        self._testAddAttachmentToObject("tasks")

    def testAddAttachmentToCategory(self):
        self._testAddAttachmentToObject("categories")

    def testAddAttachmentToNote(self):
        self._testAddAttachmentToObject("notes")

    def _testRemoveNoteFromObject(self, listName):
        newNote = note.Note(subject="Other note")
        noteCount = len(
            getattr(self.taskFile1, listName)().rootItems()[0].notes()
        )
        getattr(self.taskFile1, listName)().rootItems()[0].addNote(newNote)
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.taskFile2.save()

        getattr(self.taskFile1, listName)().rootItems()[0].removeNote(newNote)
        self.taskFile2.monitor().setChanges(newNote.id(), set())
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            len(getattr(self.taskFile2, listName)().rootItems()[0].notes()),
            noteCount,
        )

    def testRemoveNoteFromTask(self):
        self._testRemoveNoteFromObject("tasks")

    def testRemoveNoteFromCategory(self):
        self._testRemoveNoteFromObject("categories")

    def testRemoveNoteFromAttachment(self):
        newNote = note.Note(subject="Attachment note")
        self.attachment.addNote(newNote)
        self.taskFile1.save()
        self.taskFile2.save()

        self.taskFile1.tasks().rootItems()[0].attachments()[0].removeNote(
            newNote
        )
        self.taskFile2.monitor().setChanges(newNote.id(), set())
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            len(
                self.taskFile2.tasks().rootItems()[0].attachments()[0].notes()
            ),
            0,
        )

    def _testRemoveAttachmentFromObject(self, listName):
        newAttachment = attachment.FileAttachment("Other attachment")
        attachmentCount = len(
            getattr(self.taskFile1, listName)().rootItems()[0].attachments()
        )
        getattr(self.taskFile1, listName)().rootItems()[0].addAttachment(
            newAttachment
        )
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.taskFile2.save()

        getattr(self.taskFile1, listName)().rootItems()[0].removeAttachment(
            newAttachment
        )
        self.taskFile2.monitor().setChanges(newAttachment.id(), set())
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            len(
                getattr(self.taskFile2, listName)()
                .rootItems()[0]
                .attachments()
            ),
            attachmentCount,
        )

    def testRemoveAttachmentFromTask(self):
        self._testRemoveAttachmentFromObject("tasks")

    def testRemoveAttachmentFromCategory(self):
        self._testRemoveAttachmentFromObject("categories")

    def testRemoveAttachmentFromNote(self):
        self._testRemoveAttachmentFromObject("notes")

    def testChangeNoteBelongingToTask(self):
        self.taskNote.setSubject("New subject")
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            self.taskFile2.tasks().rootItems()[0].notes()[0].subject(),
            "New subject",
        )

    def testChangeAttachmentBelongingToTask(self):
        self.attachment.setLocation("new location")
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            self.taskFile2.tasks().rootItems()[0].attachments()[0].location(),
            "new location",
        )

    def testAddChildToNoteBelongingToTask(self):
        subNote = self.taskNote.newChild(subject="Child note")
        self.taskNote.addChild(subNote)
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            len(self.taskFile2.tasks().rootItems()[0].notes()[0].children()), 1
        )

    def testRemoveChildToNoteBelongingToTask(self):
        subNote = self.taskNote.newChild(subject="Child note")
        self.taskNote.addChild(subNote)
        self.taskFile1.save()
        self.taskFile2.save()

        self.taskNote.removeChild(subNote)
        self.taskFile2.monitor().setChanges(subNote.id(), set())
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            len(self.taskFile2.tasks().rootItems()[0].notes()[0].children()), 0
        )

    def testAddCategorizedNoteBelongingToOtherCategory(self):
        # Categories should be handled in priority...
        cat1 = category.Category(subject="Cat #1")
        cat2 = category.Category(subject="Cat #2")
        newNote = note.Note(subject="Note")
        cat1.addNote(newNote)
        newNote.addCategory(cat2)
        cat2.addCategorizable(newNote)
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        try:
            self.doSave(self.taskFile2)
        except Exception as e:
            self.fail(str(e))

    def testAddEffortToTask(self):
        newEffort = effort.Effort(
            self.task, date.DateTime(2011, 5, 1), date.DateTime(2011, 6, 1)
        )
        self.task.addEffort(newEffort)
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            newEffort.id(),
            self.taskFile2.tasks().rootItems()[0].efforts()[0].id(),
        )

    def testRemoveEffortFromTask(self):
        newEffort = effort.Effort(
            self.task, date.DateTime(2011, 5, 1), date.DateTime(2011, 6, 1)
        )
        self.task.addEffort(newEffort)
        self.taskFile1.save()
        self.taskFile2.save()
        self.task.removeEffort(newEffort)
        self.taskFile2.monitor().setChanges(newEffort.id(), set())
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            len(self.taskFile2.tasks().rootItems()[0].efforts()), 0
        )

    def testChangeEffortTask(self):
        newTask = task.Task(subject="Other task")
        self.taskFile1.tasks().append(newTask)
        newEffort = effort.Effort(
            self.task, date.DateTime(2011, 5, 1), date.DateTime(2011, 6, 1)
        )
        self.task.addEffort(newEffort)
        self.taskFile1.save()
        self.taskFile2.save()
        newEffort.setTask(newTask)
        self.taskFile2.monitor().setChanges(newEffort.id(), set())
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        for theTask in self.taskFile2.tasks():
            if theTask.id() == newTask.id():
                self.assertEqual(len(theTask.efforts()), 1)
                break
        else:
            self.fail()

    def testChangeEffortStart(self):
        newEffort = effort.Effort(
            self.task, date.DateTime(2011, 5, 1), date.DateTime(2011, 6, 1)
        )
        self.task.addEffort(newEffort)
        self.taskFile1.save()
        self.taskFile2.save()
        # This is needed because the setTask in sync() generates a DEL event
        self.taskFile1.monitor().setChanges(newEffort.id(), set())
        newDate = date.DateTime(2010, 6, 1)
        newEffort.setStart(newDate)
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            self.taskFile2.tasks().rootItems()[0].efforts()[0].getStart(),
            newDate,
        )

    def testChangeEffortStop(self):
        newEffort = effort.Effort(
            self.task, date.DateTime(2011, 5, 1), date.DateTime(2011, 6, 1)
        )
        self.task.addEffort(newEffort)
        self.taskFile1.save()
        self.taskFile2.save()
        # This is needed because the setTask in sync() generates a DEL event
        self.taskFile1.monitor().setChanges(newEffort.id(), set())
        newDate = date.DateTime(2012, 6, 1)
        newEffort.setStop(newDate)
        self.taskFile2.monitor().resetAllChanges()
        self.taskFile1.save()
        self.doSave(self.taskFile2)
        self.assertEqual(
            self.taskFile2.tasks().rootItems()[0].efforts()[0].getStop(),
            newDate,
        )

    def testAddPrerequisite(self):
        newTask = task.Task(subject="Prereq")
        self.taskFile1.tasks().append(newTask)
        self.taskFile2.save()
        self.task.addPrerequisites([newTask])
        self.taskFile2.load()
        self.taskFile1.save()
        self.taskFile2.monitor().resetAllChanges()
        self.doSave(self.taskFile2)

        for tsk in self.taskFile2.tasks():
            if tsk.id() == self.task.id():
                self.assertEqual(len(tsk.prerequisites()), 1)
                self.assertEqual(
                    list(tsk.prerequisites())[0].id(), newTask.id()
                )
                break
        else:
            self.fail()

    def testRemovePrerequisite(self):
        newTask = task.Task(subject="Prereq")
        self.taskFile1.tasks().append(newTask)
        self.task.addPrerequisites([newTask])
        self.taskFile1.save()
        self.taskFile2.load()
        self.task.removePrerequisites([newTask])
        self.taskFile1.save()
        self.taskFile2.monitor().resetAllChanges()
        self.doSave(self.taskFile2)

        for tsk in self.taskFile2.tasks():
            if tsk.id() == self.task.id():
                self.assertEqual(len(tsk.prerequisites()), 0)
                break
        else:
            self.fail()


class TaskFileMultiUserTestSave(TaskFileMultiUserTestBase, TaskFileTestCase):
    def doSave(self, taskFile):
        taskFile.save()


class TaskFileMultiUserTestMerge(TaskFileMultiUserTestBase, TaskFileTestCase):
    def doSave(self, taskFile):
        taskFile.merge_disk_changes()
