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
from taskcoachlib.filesystem import resourcelock
from unittests import dummy
import os
import shutil
import tempfile
import wx
import test


def in_use_elsewhere(test_case):
    """Make every lock appear held by another Task Coach."""

    def in_use(path, purpose):
        raise resourcelock.LockInUse(path, {"pid": "4321"})

    original = resourcelock.acquire
    resourcelock.acquire = in_use
    test_case.addCleanup(setattr, resourcelock, "acquire", original)


def select_file_once(test_case, filename):
    """Let the file dialog return filename, then cancel (a retry)."""
    answers = [filename]
    original = wx.FileSelector
    wx.FileSelector = lambda *args, **kwargs: (
        answers.pop() if answers else ""
    )
    test_case.addCleanup(setattr, wx, "FileSelector", original)


class IOControllerTest(test.TestCase):
    def setUp(self):
        task.Task.settings = self.settings = config.Settings(load=False)
        self.taskFile = dummy.TaskFile()
        self.iocontroller = gui.iocontroller.IOController(
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
                os.remove(filename + ".lock")
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
            self.iocontroller.open(filename, file_exists=lambda filename: True)
        for filename in saveas:
            self.iocontroller.save_as(filename)
        for filename in saveselection:
            self.iocontroller.save_selection([], filename)
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
        # Opening leaves lock files, which are never deleted
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        filenames = [
            os.path.join(directory, "filename %d" % index)
            for index in range(maximumNumberOfRecentFiles + 1)
        ]
        self.doIOAndCheckRecentFiles(
            filenames, expectedFilenames=filenames[1:]
        )

    def testSaveTaskFileWithoutTasksButWithNotes(self):
        self.taskFile.notes().append(note.Note(subject="Note"))

        def saveasReplacement(*args, **kwargs):  # pylint: disable=W0613
            self.saveAsCalled = True  # pylint: disable=W0201

        originalSaveAs = self.iocontroller.__class__.save_as
        self.iocontroller.__class__.save_as = saveasReplacement
        self.iocontroller.save()
        self.assertTrue(self.saveAsCalled)
        self.iocontroller.__class__.save_as = originalSaveAs

    def testIOErrorOnSave(self):
        self.taskFile.setFilename(self.filename1)

        def saveasReplacement(*args, **kwargs):  # pylint: disable=W0613
            self.saveAsCalled = True

        originalSaveAs = self.iocontroller.__class__.save_as
        self.iocontroller.__class__.save_as = saveasReplacement
        self.taskFile.raiseError = IOError

        def showerror(*args, **kwargs):  # pylint: disable=W0613
            self.showerrorCalled = True  # pylint: disable=W0201

        self.iocontroller.save(showerror=showerror)
        self.assertTrue(self.showerrorCalled and self.saveAsCalled)
        self.iocontroller.__class__.save_as = originalSaveAs

    def testIOErrorOnSaveAs(self):
        self.taskFile.raiseError = IOError

        def saveasReplacement(*args, **kwargs):  # pylint: disable=W0613
            self.saveAsCalled = True

        originalSaveAs = self.iocontroller.__class__.save_as

        def showerror(*args, **kwargs):  # pylint: disable=W0613
            self.showerrorCalled = True
            # Prevent the recursive call of saveas:
            self.iocontroller.__class__.save_as = saveasReplacement

        self.iocontroller.save_as(filename=self.filename1, showerror=showerror)
        self.assertTrue(self.showerrorCalled and self.saveAsCalled)
        self.iocontroller.__class__.save_as = originalSaveAs

    def testSaveSelectionAddsCategories(self):
        task1 = task.Task()
        task2 = task.Task()
        self.taskFile.tasks().extend([task1, task2])
        aCategory = category.Category("A Category")
        self.taskFile.categories().append(aCategory)
        for eachTask in self.taskFile.tasks():
            eachTask.addCategory(aCategory)
            aCategory.addCategorizable(eachTask)
        self.iocontroller.save_selection(
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
        self.iocontroller.save_selection(
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
        self.iocontroller._save_save(
            self.taskFile, showerror
        )  # pylint: disable=W0212
        self.assertTrue(self.showerrorCalled)

    def test_other_error_on_save_shows_a_message(self):
        self.taskFile.raiseError = ValueError("corrupt file on disk")
        self.taskFile.setFilename(self.filename1)
        messages = []
        self.assertFalse(
            self.iocontroller._save_save(  # pylint: disable=W0212
                self.taskFile,
                lambda message, **kwargs: messages.append(message),
            )
        )
        self.assertIn("corrupt file on disk", messages[0])

    def test_keyboard_interrupt_on_save_is_not_caught(self):
        self.taskFile.raiseError = KeyboardInterrupt
        self.taskFile.setFilename(self.filename1)
        with self.assertRaises(KeyboardInterrupt):
            self.iocontroller._save_save(  # pylint: disable=W0212
                self.taskFile, lambda *args, **kwargs: None
            )

    def test_save_selection_to_a_file_open_elsewhere_is_refused(self):
        with open(self.filename1, "w") as other:
            other.write("theirs")
        in_use_elsewhere(self)
        select_file_once(self, "")
        messages = []
        self.iocontroller.save_selection(
            [task.Task()],
            self.filename1,
            showerror=lambda message, **kwargs: messages.append(message),
        )
        self.assertIn("4321", messages[0])
        with open(self.filename1) as other:
            self.assertEqual("theirs", other.read())

    def test_save_selection_releases_the_lock_and_the_tasks(self):
        selected = task.Task()
        self.taskFile.tasks().append(selected)
        self.iocontroller.save_selection([selected], self.filename1)
        with open(self.filename1 + ".lock", "rb") as lock_file:
            self.assertEqual(b"", lock_file.read())
        dirty = test.ChangeRecorder("taskfile.dirty")
        selected.setSubject("changed")
        self.assertEqual(
            [],
            [
                task_file
                for task_file in dirty
                if task_file is not self.taskFile
            ],
        )

    def test_save_selection_onto_the_open_file_is_refused(self):
        open_file = persistence.LockedTaskFile()
        kept = task.Task(subject="kept")
        open_file.tasks().extend([kept, task.Task(subject="not selected")])
        open_file.setFilename(self.filename1)
        open_file.save()
        iocontroller = gui.iocontroller.IOController(
            open_file, lambda *args: None, self.settings
        )
        select_file_once(self, "")
        messages = []
        try:
            iocontroller.save_selection(
                [kept],
                self.filename1,
                showerror=lambda message, **kwargs: messages.append(message),
            )
            self.assertTrue(open_file.is_locked())
        finally:
            open_file.close()  # Before tearDown removes the lock file
            open_file.stop()
        self.assertIn("open task file", messages[0])
        on_disk = persistence.TaskFile(read_only=True)
        on_disk.load(self.filename1)
        self.assertEqual(2, len(on_disk.tasks()))
        on_disk.close()
        on_disk.stop()

    def testIOErrorOnExport(self):
        self.taskFile.setFilename(self.filename1)
        self.taskFile.tasks().append(task.Task())

        def showerror(*args, **kwargs):  # pylint: disable=W0613
            self.showerrorCalled = True

        def openfile(*args, **kwargs):  # pylint: disable=W0613
            raise IOError

        self.iocontroller.export_as_html(
            None, filename="Don't ask", openfile=openfile, showerror=showerror
        )
        self.assertTrue(self.showerrorCalled)

    def testMerge(self):
        mergeFile = persistence.TaskFile()
        mergeFile.setFilename(self.filename2)
        mergeFile.tasks().append(task.Task(subject="Task to merge"))
        mergeFile.save()
        mergeFile.close()
        targetFile = persistence.TaskFile()
        iocontroller = gui.iocontroller.IOController(
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

    def test_open_lists_the_duplicate_ids_it_corrected(self):
        with open(self.filename1, "w", encoding="utf-8") as fd:
            fd.write(
                '<?taskcoach release="2.0.3" tskversion="37"?>\n'
                '<tasks><task id="1" subject="first"/>'
                '<task id="1" subject="second"/></tasks>'
            )
        task_file = persistence.TaskFile()
        iocontroller = gui.iocontroller.IOController(
            task_file, lambda *args: None, self.settings
        )
        messages = []
        try:
            iocontroller.open(
                self.filename1,
                showerror=lambda message, **kwargs: messages.append(message),
            )
        finally:
            task_file.close()
            task_file.stop()
        self.assertEqual(
            (1, True, True),
            (
                len(messages),
                "Kept its ID: Task: first" in messages[0],
                "New ID: Task: second" in messages[0],
            ),
        )

    def test_open_when_in_use(self):
        self.taskFile.raiseError = resourcelock.LockInUse(
            self.filename1, {"pid": "4321"}
        )
        messages = []
        self.iocontroller.open(
            self.filename1,
            showerror=lambda message, **kwargs: messages.append(message),
            file_exists=lambda filename: True,
        )
        self.assertIn("4321", messages[0])


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
        self.iocontroller = gui.iocontroller.IOController(
            self.taskFile, lambda *args: None, self.settings
        )

    def tearDown(self):
        self.taskFile.close()
        self.taskFile.stop()
        wx.FileSelector = self.originalFileSelector
        wx.MessageBox = self.originalMessageBox
        super().tearDown()

    def testCancelSaveAsExistingFile(self):
        self.iocontroller.save_as(file_exists=lambda filename: True)
        self.assertTrue(self.userWarned)

    def testCancelSaveSelectionToExistingFile(self):
        self.iocontroller.save_selection([], file_exists=lambda filename: True)
        self.assertTrue(self.userWarned)

    def testCancelExportAsHTMLToExistingFile(self):
        self.iocontroller.export_as_html(
            None, file_exists=lambda filename: True
        )
        self.assertTrue(self.userWarned)

    def testCancelExportAsCSVToExistingFile(self):
        self.iocontroller.export_as_csv(
            None, file_exists=lambda filename: True
        )
        self.assertTrue(self.userWarned)

    def testCancelExportAsICalendarToExistingFile(self):
        self.iocontroller.export_as_icalendar(
            None, file_exists=lambda filename: True
        )
        self.assertTrue(self.userWarned)


class IOControllerReplaceFileTest(test.TestCase):
    """Replacing a task file after our own overwrite prompt (a name
    typed without extension) removes its auto import/export files."""

    def setUp(self):
        super().setUp()
        self.directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.directory)
        self.name = os.path.join(self.directory, "tasks")
        for extension in (".tsk", ".txt", ".html"):
            open(self.name + extension, "w").close()
        select_file_once(self, self.name)
        original = wx.MessageBox
        wx.MessageBox = lambda *args, **kwargs: wx.YES
        self.addCleanup(setattr, wx, "MessageBox", original)
        task.Task.settings = self.settings = config.Settings(load=False)
        self.settings.setlist("file", "autoexport", ["Todo.txt"])
        self.task_file = dummy.TaskFile()
        self.addCleanup(self.task_file.stop)
        self.iocontroller = gui.iocontroller.IOController(
            self.task_file, lambda *args: None, self.settings
        )
        self.messages = []

    def showerror(self, message, **kwargs):
        self.messages.append(message)

    def test_replaced_file_loses_its_auto_files(self):
        self.iocontroller.save_as(showerror=self.showerror)
        self.assertFalse(os.path.exists(self.name + ".txt"))

    def test_file_open_elsewhere_keeps_its_auto_files(self):
        in_use_elsewhere(self)
        self.iocontroller.save_as(showerror=self.showerror)
        self.assertIn("4321", self.messages[0])
        self.assertTrue(os.path.exists(self.name + ".txt"))

    def test_export_keeps_the_auto_files_of_a_task_file(self):
        def openfile(*args, **kwargs):
            raise IOError("stop before writing")

        self.iocontroller.export_as_html(
            None, openfile=openfile, showerror=self.showerror
        )
        self.assertTrue(os.path.exists(self.name + ".txt"))


class IOControllerChangedOnDiskTest(test.TestCase):
    """Another program changed the open file: nothing replaces its
    changes unasked (docs/PERSISTENCE_XML.md, Saving)."""

    def setUp(self):
        super().setUp()
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        self.filename = os.path.join(directory, "tasks.tsk")
        self.other_filename = os.path.join(directory, "other.tsk")
        task.Task.settings = self.settings = config.Settings(load=False)
        self.task_file = persistence.TaskFile()
        self.addCleanup(self.task_file.stop)
        self.addCleanup(self.task_file.close)
        self.task = task.Task(subject="ours")
        self.task_file.tasks().append(self.task)
        self.task_file.setFilename(self.filename)
        self.task_file.save()
        self.iocontroller = gui.iocontroller.IOController(
            self.task_file, lambda *args: None, self.settings
        )
        self.iocontroller._ask = self.ask
        self.answers = []
        self.questions = 0

    def ask(self, message, labels):
        self.questions += 1
        return self.answers.pop(0)

    def change_on_disk(self, *answers):
        """Another program adds a task, reported by the watcher;
        answers are for the questions that follow."""
        self.answers.extend(answers)
        self.add_their_task()
        self.task_file.check_disk()

    def add_their_task(self):
        theirs = persistence.TaskFile(read_only=True)
        try:
            theirs.load(self.filename)
            theirs.tasks().append(task.Task(subject="theirs"))
            theirs.save()
        finally:
            theirs.close()
            theirs.stop()

    def subjects(self, task_file):
        return sorted(each.subject() for each in task_file.tasks())

    def subjects_on_disk(self, filename=None):
        on_disk = persistence.TaskFile(read_only=True)
        try:
            on_disk.load(filename or self.filename)
            return self.subjects(on_disk)
        finally:
            on_disk.close()
            on_disk.stop()

    def open_copy_kept(self):
        return any(each is self.task for each in self.task_file.tasks())

    def test_reload(self):
        self.change_on_disk(0)
        self.assertEqual(
            (["ours", "theirs"], False, False),
            (
                self.subjects(self.task_file),
                self.open_copy_kept(),
                self.task_file.changed_on_disk(),
            ),
        )

    def test_merge(self):
        self.change_on_disk(1)
        self.assertEqual(
            (["ours", "theirs"], True, False),
            (
                self.subjects(self.task_file),
                self.open_copy_kept(),
                self.task_file.changed_on_disk(),
            ),
        )

    def test_later(self):
        self.change_on_disk(2)
        self.assertEqual(
            (["ours"], True),
            (self.subjects(self.task_file), self.task_file.changed_on_disk()),
        )

    def test_save_merges_first(self):
        self.task.setSubject("ours, changed")
        self.change_on_disk(2)  # Later
        self.answers.append(0)  # Merge and save
        self.assertTrue(self.iocontroller.save())
        self.assertEqual(
            (["ours, changed", "theirs"], 2),
            (self.subjects_on_disk(), self.questions),
        )

    def test_save_asks_once_about_an_unreported_change(self):
        self.task.setSubject("ours, changed")
        self.add_their_task()
        self.answers.append(2)  # Cancel
        self.assertFalse(self.iocontroller.save())
        self.assertEqual(
            (1, ["ours", "theirs"]), (self.questions, self.subjects_on_disk())
        )

    def test_save_as_leaves_the_changed_file(self):
        self.task.setSubject("ours, changed")
        select_file_once(self, self.other_filename)
        self.change_on_disk(1)  # Save as
        self.assertEqual(
            (["ours", "theirs"], ["ours, changed"]),
            (
                self.subjects_on_disk(),
                self.subjects_on_disk(self.other_filename),
            ),
        )

    def test_cancel_saves_nothing(self):
        self.task.setSubject("ours, changed")
        self.change_on_disk(2, 2)  # Later, then Cancel
        self.assertFalse(self.iocontroller.save())
        self.assertEqual(["ours", "theirs"], self.subjects_on_disk())
