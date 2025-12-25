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

from taskcoachlib import gui, config, persistence
from taskcoachlib.domain import task, note, category
from unittests import dummy
import os
import shutil
import wx
import test


class IOControllerTest(test.TestCase):
    def setUp(self):
        task.Task.settings = self.settings = config.Settings(load=False)
        self.taskFile = dummy.TaskFile()
        self.iocontroller = gui.IOController(
            self.taskFile, lambda *args: None, self.settings
        )
        self.filename1 = "whatever.tsk"
        self.filename2 = "another.tsk"

    def tearDown(self):
        self.taskFile.close()
        self.taskFile.stop()
        for filename in self.filename1, self.filename2:
            if os.path.exists(filename):
                os.remove(filename)
            if os.path.exists(filename + ".lock"):
                shutil.rmtree(filename + ".lock")  # pragma: no cover
            if os.path.exists(filename + ".delta"):
                os.remove(filename + ".delta")
        super().tearDown()

    def doIOAndCheckRecentFiles(
        self,
        open=None,
        saveas=None,  # pylint: disable=W0622
        saveselection=None,
        merge=None,
        expectedFilenames=None,
    ):
        open = open or []
        saveas = saveas or []
        saveselection = saveselection or []
        merge = merge or []
        self.doIO(open, saveas, saveselection, merge)
        self.checkRecentFiles(
            expectedFilenames or open + saveas + saveselection + merge
        )

    def doIO(
        self, open, saveas, saveselection, merge
    ):  # pylint: disable=W0622
        for filename in open:
            self.iocontroller.open(filename, fileExists=lambda filename: True)
        for filename in saveas:
            self.iocontroller.saveas(filename)
        for filename in saveselection:
            self.iocontroller.saveselection([], filename)
        for filename in merge:
            self.iocontroller.merge(filename)

    def checkRecentFiles(self, expectedFilenames):
        expectedFilenames.reverse()
        expectedFilenames = str(expectedFilenames)
        self.assertEqual(
            expectedFilenames, self.settings.get("file", "recentfiles")
        )

    def testOpenFileAddsItToRecentFiles(self):
        self.doIOAndCheckRecentFiles(open=[self.filename1])

    def testOpenTwoFilesAddBothToRecentFiles(self):
        self.doIOAndCheckRecentFiles(open=[self.filename1, self.filename2])

    def testOpenTheSameFileTwiceAddsItToRecentFilesOnce(self):
        self.doIOAndCheckRecentFiles(
            open=[self.filename1] * 2, expectedFilenames=[self.filename1]
        )

    def testSaveFileAsAddsItToRecentFiles(self):
        self.doIOAndCheckRecentFiles(saveas=[self.filename1])

    def testMergeFileAddsItToRecentFiles(self):
        self.doIOAndCheckRecentFiles(
            open=[self.filename1], merge=[self.filename2]
        )

    def testSaveSelectionAddsItToRecentFiles(self):
        self.doIOAndCheckRecentFiles(saveselection=[self.filename1])

    def testMaximumNumberOfRecentFiles(self):
        maximumNumberOfRecentFiles = self.settings.getint(
            "file", "maxrecentfiles"
        )
        filenames = [
            "filename %d" % index
            for index in range(maximumNumberOfRecentFiles + 1)
        ]
        self.doIOAndCheckRecentFiles(
            filenames, expectedFilenames=filenames[1:]
        )

    def testSaveTaskFileWithoutTasksButWithNotes(self):
        self.taskFile.notes().append(note.Note(subject="Note"))

        def saveasReplacement(*args, **kwargs):  # pylint: disable=W0613
            self.saveAsCalled = True  # pylint: disable=W0201

        originalSaveAs = self.iocontroller.__class__.saveas
        self.iocontroller.__class__.saveas = saveasReplacement
        self.iocontroller.save()
        self.assertTrue(self.saveAsCalled)
        self.iocontroller.__class__.saveas = originalSaveAs

    def testIOErrorOnSave(self):
        self.taskFile.setFilename(self.filename1)

        def saveasReplacement(*args, **kwargs):  # pylint: disable=W0613
            self.saveAsCalled = True

        originalSaveAs = self.iocontroller.__class__.saveas
        self.iocontroller.__class__.saveas = saveasReplacement
        self.taskFile.raiseError = IOError

        def showerror(*args, **kwargs):  # pylint: disable=W0613
            self.showerrorCalled = True  # pylint: disable=W0201

        self.iocontroller.save(showerror=showerror)
        self.assertTrue(self.showerrorCalled and self.saveAsCalled)
        self.iocontroller.__class__.saveas = originalSaveAs

    def testIOErrorOnSaveAs(self):
        self.taskFile.raiseError = IOError

        def saveasReplacement(*args, **kwargs):  # pylint: disable=W0613
            self.saveAsCalled = True

        originalSaveAs = self.iocontroller.__class__.saveas

        def showerror(*args, **kwargs):  # pylint: disable=W0613
            self.showerrorCalled = True
            # Prevent the recursive call of saveas:
            self.iocontroller.__class__.saveas = saveasReplacement

        self.iocontroller.saveas(filename=self.filename1, showerror=showerror)
        self.assertTrue(self.showerrorCalled and self.saveAsCalled)
        self.iocontroller.__class__.saveas = originalSaveAs

    def testSaveSelectionAddsCategories(self):
        task1 = task.Task()
        task2 = task.Task()
        self.taskFile.tasks().extend([task1, task2])
        aCategory = category.Category("A Category")
        self.taskFile.categories().append(aCategory)
        for eachTask in self.taskFile.tasks():
            eachTask.addCategory(aCategory)
            aCategory.addCategorizable(eachTask)
        self.iocontroller.saveselection(
            tasks=self.taskFile.tasks(), filename=self.filename1
        )
        taskFile = persistence.TaskFile()
        taskFile.setFilename(self.filename1)
        taskFile.load()
        try:
            self.assertEqual(1, len(taskFile.categories()))
        finally:
            taskFile.close()
            taskFile.stop()

    def testSaveSelectionAddsParentCategoriesWhenSubcategoriesAreUsed(self):
        task1 = task.Task()
        self.taskFile.tasks().extend([task1])
        aCategory = category.Category("A category")
        aSubCategory = category.Category("A subcategory")
        aCategory.addChild(aSubCategory)
        self.taskFile.categories().append(aCategory)
        task1.addCategory(aSubCategory)
        aSubCategory.addCategorizable(task1)
        self.iocontroller.saveselection(
            tasks=self.taskFile.tasks(), filename=self.filename1
        )
        taskFile = persistence.TaskFile()
        taskFile.setFilename(self.filename1)
        taskFile.load()
        self.assertEqual(2, len(taskFile.categories()))

    def testIOErrorOnSaveSave(self):
        self.taskFile.raiseError = IOError
        self.taskFile.setFilename(self.filename1)

        def showerror(*args, **kwargs):  # pylint: disable=W0613
            self.showerrorCalled = True

        self.taskFile.tasks().append(task.Task())
        self.iocontroller._saveSave(
            self.taskFile, showerror
        )  # pylint: disable=W0212
        self.assertTrue(self.showerrorCalled)

    def testIOErrorOnExport(self):
        self.taskFile.setFilename(self.filename1)
        self.taskFile.tasks().append(task.Task())

        def showerror(*args, **kwargs):  # pylint: disable=W0613
            self.showerrorCalled = True

        def openfile(*args, **kwargs):  # pylint: disable=W0613
            raise IOError

        self.iocontroller.exportAsHTML(
            None, filename="Don't ask", openfile=openfile, showerror=showerror
        )
        self.assertTrue(self.showerrorCalled)

    def testNothingDeleted(self):
        self.taskFile.tasks().append(task.Task(subject="Task"))
        self.taskFile.notes().append(note.Note(subject="Note"))
        self.assertFalse(self.iocontroller.hasDeletedItems())

    def testNoteDeleted(self):
        self.taskFile.tasks().append(task.Task(subject="Task"))
        myNote = note.Note(subject="Note")
        myNote.markDeleted()
        self.taskFile.notes().append(myNote)
        self.assertTrue(self.iocontroller.hasDeletedItems())

    def testTaskDeleted(self):
        myTask = task.Task(subject="Task")
        myTask.markDeleted()
        self.taskFile.tasks().append(myTask)
        self.taskFile.notes().append(note.Note(subject="Note"))
        self.assertTrue(self.iocontroller.hasDeletedItems())

    def testPurgeNothing(self):
        myTask = task.Task(subject="Task")
        myNote = note.Note(subject="Note")
        self.taskFile.tasks().append(myTask)
        self.taskFile.notes().append(myNote)
        self.iocontroller.purgeDeletedItems()
        self.assertEqual(self.taskFile.tasks(), [myTask])
        self.assertEqual(self.taskFile.notes(), [myNote])

    def testPurgeNote(self):
        myTask = task.Task(subject="Task")
        myNote = note.Note(subject="Note")
        self.taskFile.tasks().append(myTask)
        self.taskFile.notes().append(myNote)
        myNote.markDeleted()
        self.iocontroller.purgeDeletedItems()
        self.assertEqual(self.taskFile.tasks(), [myTask])
        self.assertEqual(self.taskFile.notes(), [])

    def testPurgeTask(self):
        myTask = task.Task(subject="Task")
        myNote = note.Note(subject="Note")
        self.taskFile.tasks().append(myTask)
        self.taskFile.notes().append(myNote)
        myTask.markDeleted()
        self.iocontroller.purgeDeletedItems()
        self.assertEqual(self.taskFile.tasks(), [])
        self.assertEqual(self.taskFile.notes(), [myNote])

    def testMerge(self):
        mergeFile = persistence.TaskFile()
        mergeFile.setFilename(self.filename2)
        mergeFile.tasks().append(task.Task(subject="Task to merge"))
        mergeFile.save()
        mergeFile.close()
        targetFile = persistence.TaskFile()
        iocontroller = gui.IOController(
            targetFile, lambda *args: None, self.settings
        )
        iocontroller.merge(self.filename2)
        try:
            self.assertEqual(
                "Task to merge", list(targetFile.tasks())[0].subject()
            )
        finally:
            mergeFile.close()
            mergeFile.stop()
            targetFile.close()
            targetFile.stop()

    def testOpenWhenLockFailed(self):
        self.taskFile.raiseError = persistence.LockFailed

        def askOpenUnlocked(*args, **kwargs):  # pylint: disable=W0613
            self.askOpenUnlockedCalled = True

        self.iocontroller._IOController__askOpenUnlocked = askOpenUnlocked
        self.iocontroller.open(
            self.filename1, fileExists=lambda filename: True
        )
        self.assertTrue(self.askOpenUnlockedCalled)

    def testOpenWhenAlreadyLocked(self):
        self.taskFile.raiseError = persistence.LockTimeout

        def askBreakLock(*args, **kwargs):  # pylint: disable=W0613
            self.askBreakLockCalled = True

        self.iocontroller._IOController__askBreakLock = askBreakLock
        self.iocontroller.open(
            self.filename1, fileExists=lambda filename: True
        )
        self.assertTrue(self.askBreakLockCalled)


class IOControllerOverwriteExistingFileTest(test.TestCase):
    def setUp(self):
        super().setUp()
        self.originalFileSelector = wx.FileSelector
        wx.FileSelector = (
            lambda *args, **kwargs: "filename without extension to trigger our own overwrite warning"
        )
        self.originalMessageBox = wx.MessageBox

        def messageBox(*args, **kwargs):  # pylint: disable=W0613
            self.userWarned = True
            return wx.CANCEL

        wx.MessageBox = messageBox
        task.Task.settings = self.settings = config.Settings(load=False)
        self.taskFile = dummy.TaskFile()
        self.iocontroller = gui.IOController(
            self.taskFile, lambda *args: None, self.settings
        )

    def tearDown(self):
        self.taskFile.close()
        self.taskFile.stop()
        wx.FileSelector = self.originalFileSelector
        wx.MessageBox = self.originalMessageBox
        super().tearDown()

    def testCancelSaveAsExistingFile(self):
        self.iocontroller.saveas(fileExists=lambda filename: True)
        self.assertTrue(self.userWarned)

    def testCancelSaveSelectionToExistingFile(self):
        self.iocontroller.saveselection([], fileExists=lambda filename: True)
        self.assertTrue(self.userWarned)

    def testCancelExportAsHTMLToExistingFile(self):
        self.iocontroller.exportAsHTML(None, fileExists=lambda filename: True)
        self.assertTrue(self.userWarned)

    def testCancelExportAsCSVToExistingFile(self):
        self.iocontroller.exportAsCSV(None, fileExists=lambda filename: True)
        self.assertTrue(self.userWarned)

    def testCancelExportAsICalendarToExistingFile(self):
        self.iocontroller.exportAsICalendar(
            None, fileExists=lambda filename: True
        )
        self.assertTrue(self.userWarned)
