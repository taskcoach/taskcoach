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

from taskcoachlib import command, gui, patterns, persistence
from taskcoachlib.domain import task, note, category
from taskcoachlib.filesystem import resourcelock
from taskcoachlib.config import settings
from unittests import dummy
import os
import shutil
import tempfile
from unittest import mock
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
        self.taskFile = dummy.TaskFile()
        self.iocontroller = gui.iocontroller.IOController(
            self.taskFile, lambda *args: None
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
        expected_filenames=None,
    ):
        open = open or []
        saveas = saveas or []
        saveselection = saveselection or []
        merge = merge or []
        self.doIO(open, saveas, saveselection, merge)
        self.checkRecentFiles(
            expected_filenames or open + saveas + saveselection + merge
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

    def checkRecentFiles(self, expected_filenames):
        expected_filenames.reverse()
        self.assertEqual(
            expected_filenames, settings.get("file", "recentfiles")
        )

    def test_open_file_adds_it_to_recent_files(self):
        self.doIOAndCheckRecentFiles(open=[self.filename1])

    def test_open_two_files_add_both_to_recent_files(self):
        self.doIOAndCheckRecentFiles(open=[self.filename1, self.filename2])

    def test_open_the_same_file_twice_adds_it_to_recent_files_once(self):
        self.doIOAndCheckRecentFiles(
            open=[self.filename1] * 2, expected_filenames=[self.filename1]
        )

    def test_save_file_as_adds_it_to_recent_files(self):
        self.doIOAndCheckRecentFiles(saveas=[self.filename1])

    def test_merge_file_adds_it_to_recent_files(self):
        self.doIOAndCheckRecentFiles(
            open=[self.filename1], merge=[self.filename2]
        )

    def test_save_selection_adds_it_to_recent_files(self):
        self.doIOAndCheckRecentFiles(saveselection=[self.filename1])

    def test_maximum_number_of_recent_files(self):
        maximum_number_of_recent_files = settings.get("file", "maxrecentfiles")
        # Opening leaves lock files, which are never deleted
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        filenames = [
            os.path.join(directory, "filename %d" % index)
            for index in range(maximum_number_of_recent_files + 1)
        ]
        self.doIOAndCheckRecentFiles(
            filenames, expected_filenames=filenames[1:]
        )

    def test_save_task_file_without_tasks_but_with_notes(self):
        self.taskFile.notes().append(note.Note(subject="Note"))

        def saveasReplacement(*args, **kwargs):  # pylint: disable=W0613
            self.saveAsCalled = True  # pylint: disable=W0201

        original_save_as = self.iocontroller.__class__.save_as
        self.iocontroller.__class__.save_as = saveasReplacement
        self.iocontroller.save()
        self.assertTrue(self.saveAsCalled)
        self.iocontroller.__class__.save_as = original_save_as

    def test_io_error_on_save(self):
        self.taskFile.setFilename(self.filename1)

        def saveasReplacement(*args, **kwargs):  # pylint: disable=W0613
            self.saveAsCalled = True

        original_save_as = self.iocontroller.__class__.save_as
        self.iocontroller.__class__.save_as = saveasReplacement
        self.taskFile.raiseError = IOError

        def showerror(*args, **kwargs):  # pylint: disable=W0613
            self.showerrorCalled = True  # pylint: disable=W0201

        self.iocontroller.save(showerror=showerror)
        self.assertTrue(self.showerrorCalled and self.saveAsCalled)
        self.iocontroller.__class__.save_as = original_save_as

    def test_io_error_on_save_as(self):
        self.taskFile.raiseError = IOError

        def saveasReplacement(*args, **kwargs):  # pylint: disable=W0613
            self.saveAsCalled = True

        original_save_as = self.iocontroller.__class__.save_as

        def showerror(*args, **kwargs):  # pylint: disable=W0613
            self.showerrorCalled = True
            # Prevent the recursive call of saveas:
            self.iocontroller.__class__.save_as = saveasReplacement

        self.iocontroller.save_as(filename=self.filename1, showerror=showerror)
        self.assertTrue(self.showerrorCalled and self.saveAsCalled)
        self.iocontroller.__class__.save_as = original_save_as

    def test_save_selection_adds_categories(self):
        task1 = task.Task()
        task2 = task.Task()
        self.taskFile.tasks().extend([task1, task2])
        a_category = category.Category("A Category")
        self.taskFile.categories().append(a_category)
        for each_task in self.taskFile.tasks():
            each_task.addCategory(a_category)
        self.iocontroller.save_selection(
            tasks=self.taskFile.tasks(), filename=self.filename1
        )
        task_file = persistence.TaskFile()
        task_file.setFilename(self.filename1)
        task_file.load()
        try:
            self.assertEqual(1, len(task_file.categories()))
        finally:
            task_file.close()
            task_file.stop()

    def test_save_selection_adds_parent_categories_when_subcategories_are_used(
        self,
    ):
        task1 = task.Task()
        self.taskFile.tasks().extend([task1])
        a_category = category.Category("A category")
        a_sub_category = category.Category("A subcategory")
        a_category.addChild(a_sub_category)
        self.taskFile.categories().append(a_category)
        task1.addCategory(a_sub_category)
        self.iocontroller.save_selection(
            tasks=self.taskFile.tasks(), filename=self.filename1
        )
        task_file = persistence.TaskFile()
        task_file.setFilename(self.filename1)
        task_file.load()
        self.assertEqual(2, len(task_file.categories()))

    def test_io_error_on_save_save(self):
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

    def test_save_as_to_a_file_open_elsewhere_is_refused(self):
        with open(self.filename1, "w") as other:
            other.write("theirs")
        in_use_elsewhere(self)
        select_file_once(self, "")
        messages = []
        self.iocontroller.save_as(
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
            open_file, lambda *args: None
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

    def test_reopening_the_open_file_keeps_it_locked(self):
        open_file = persistence.LockedTaskFile()
        open_file.tasks().append(task.Task())
        open_file.setFilename(self.filename1)
        open_file.save()
        self.addCleanup(open_file.stop)
        self.addCleanup(open_file.close)  # Before tearDown's removal
        iocontroller = gui.iocontroller.IOController(
            open_file, lambda *args: None
        )
        released = []
        release = resourcelock.ResourceLock.release

        def record(lock):
            released.append(lock)
            release(lock)

        with mock.patch.object(resourcelock.ResourceLock, "release", record):
            iocontroller.open(self.filename1)
        self.assertEqual(([], True), (released, open_file.is_locked()))

    def test_io_error_on_export(self):
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

    def test_reading_a_file_shows_the_busy_pointer(self):
        # The window cannot answer while a file is read
        busy = []
        self.taskFile.load = lambda *args: busy.append(wx.IsBusy())
        self.taskFile.merge = lambda *args: busy.append(wx.IsBusy())
        self.iocontroller.open(self.filename1, file_exists=lambda name: True)
        self.iocontroller.merge(self.filename2)
        self.assertEqual([True, True, False], busy + [wx.IsBusy()])

    def test_reading_a_file_says_so_first(self):
        # The window cannot answer while a file is read
        messages, shown_at_read = [], []
        iocontroller = gui.iocontroller.IOController(
            self.taskFile, messages.append
        )
        self.taskFile.load = lambda *args: shown_at_read.append(messages[-1])
        self.taskFile.merge = lambda *args: shown_at_read.append(messages[-1])
        iocontroller.open(self.filename1, file_exists=lambda name: True)
        iocontroller.merge(self.filename2)
        self.assertEqual(
            ["Opening whatever.tsk...", "Merging another.tsk..."],
            shown_at_read,
        )

    def opening_messages(self):
        messages = []
        iocontroller = gui.iocontroller.IOController(
            self.taskFile, messages.append
        )
        iocontroller.open(self.filename1, file_exists=lambda name: True)
        return [each for each in messages if each.startswith("Closed")]

    def test_nothing_is_closed_before_the_first_file(self):
        # The start: no file, nothing in it, nothing to undo
        self.assertEqual([], self.opening_messages())

    def test_an_open_file_is_closed_first(self):
        self.taskFile.setFilename(self.filename2)
        self.assertEqual(["Closed another.tsk"], self.opening_messages())

    def test_the_busy_pointer_ends_before_an_error_shows(self):
        self.taskFile.raiseError = ValueError("unreadable")
        busy = []
        self.iocontroller.open(
            self.filename1,
            file_exists=lambda name: True,
            showerror=lambda *args, **kwargs: busy.append(wx.IsBusy()),
        )
        self.iocontroller.merge(
            self.filename2,
            showerror=lambda *args, **kwargs: busy.append(wx.IsBusy()),
        )
        self.assertEqual([False, False], busy)

    def test_merge(self):
        merge_file = persistence.TaskFile()
        merge_file.setFilename(self.filename2)
        merge_file.tasks().append(task.Task(subject="Task to merge"))
        merge_file.save()
        merge_file.close()
        target_file = persistence.TaskFile()
        iocontroller = gui.iocontroller.IOController(
            target_file, lambda *args: None
        )
        iocontroller.merge(self.filename2)
        try:
            self.assertEqual(
                "Task to merge", list(target_file.tasks())[0].subject()
            )
        finally:
            merge_file.close()
            merge_file.stop()
            target_file.close()
            target_file.stop()

    def test_open_lists_the_duplicate_ids_it_corrected(self):
        with open(self.filename1, "w", encoding="utf-8") as fd:
            fd.write(
                '<?taskcoach release="2.0.3" tskversion="37"?>\n'
                '<tasks><task id="1" subject="first"/>'
                '<task id="1" subject="second"/></tasks>'
            )
        task_file = persistence.TaskFile()
        iocontroller = gui.iocontroller.IOController(
            task_file, lambda *args: None
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
        self.taskFile = dummy.TaskFile()
        self.iocontroller = gui.iocontroller.IOController(
            self.taskFile, lambda *args: None
        )

    def tearDown(self):
        self.taskFile.close()
        self.taskFile.stop()
        wx.FileSelector = self.originalFileSelector
        wx.MessageBox = self.originalMessageBox
        super().tearDown()

    def test_cancel_save_as_existing_file(self):
        self.iocontroller.save_as(file_exists=lambda filename: True)
        self.assertTrue(self.userWarned)

    def test_cancel_save_selection_to_existing_file(self):
        self.iocontroller.save_selection([], file_exists=lambda filename: True)
        self.assertTrue(self.userWarned)

    def test_cancel_export_as_html_to_existing_file(self):
        self.iocontroller.export_as_html(
            None, file_exists=lambda filename: True
        )
        self.assertTrue(self.userWarned)

    def test_cancel_export_as_csv_to_existing_file(self):
        self.iocontroller.export_as_csv(
            None, file_exists=lambda filename: True
        )
        self.assertTrue(self.userWarned)

    def test_cancel_export_as_icalendar_to_existing_file(self):
        self.iocontroller.export_as_icalendar(
            None, file_exists=lambda filename: True
        )
        self.assertTrue(self.userWarned)


class IOControllerCloseTest(test.TestCase):
    def setUp(self):
        super().setUp()
        self.task_file = persistence.TaskFile()
        self.addCleanup(self.task_file.stop)
        self.addCleanup(self.task_file.close)
        self.addCleanup(patterns.CommandHistory().clear)
        self.iocontroller = gui.iocontroller.IOController(
            self.task_file, lambda *args: None
        )

    def test_undo_back_to_the_empty_file_after_close_needs_no_save(self):
        command.NewTaskCommand(self.task_file.tasks()).do()
        self.iocontroller.close(force=True)  # No file name: not saved
        command.NewTaskCommand(self.task_file.tasks()).do()
        patterns.CommandHistory().undo()
        self.assertFalse(self.task_file.need_save())


class IOControllerChangedOnDiskTest(test.TestCase):
    """Another program changed the open file: nothing replaces its
    changes unasked (docs/PERSISTENCE_XML.md, Saving)."""

    def setUp(self):
        super().setUp()
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        self.filename = os.path.join(directory, "tasks.tsk")
        self.other_filename = os.path.join(directory, "other.tsk")
        self.task_file = persistence.TaskFile()
        self.addCleanup(self.task_file.stop)
        self.addCleanup(self.task_file.close)
        self.task = task.Task(subject="ours")
        self.task_file.tasks().append(self.task)
        self.task_file.setFilename(self.filename)
        self.task_file.save()
        self.iocontroller = gui.iocontroller.IOController(
            self.task_file, lambda *args: None
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

    def test_a_forced_close_saves_to_a_copy_when_changed_on_disk(self):
        # The session ends: nobody can choose, nothing is lost
        self.task.setSubject("ours, edited")
        self.add_their_task()
        copy = os.path.join(
            os.path.dirname(self.filename),
            gui.iocontroller.copy_name(self.filename),
        )
        self.iocontroller.close(force=True)
        self.assertEqual(
            (["ours", "theirs"], ["ours, edited"]),
            (self.subjects_on_disk(), self.subjects_on_disk(copy)),
        )

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


class FileDialogFolderTest(test.TestCase):
    """Where each file dialog opens: the folder last chosen in a dialog
    of its kind this session; before that, the open task file's; with
    no saved file, Documents. Attachments keep theirs across sessions
    (docs/FILE_DIALOGS.md)."""

    def setUp(self):
        super().setUp()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.home = os.path.join(folder.name, "home")
        self.other = os.path.join(folder.name, "other")
        os.makedirs(self.home)
        os.makedirs(self.other)
        self.task_file = dummy.TaskFile()
        self.addCleanup(self.task_file.stop)
        self.iocontroller = gui.iocontroller.IOController(
            self.task_file, lambda *args: None
        )
        self.opened_in, self.answers = [], []

        def file_selector(*args, **kwargs):
            self.opened_in.append(kwargs.get("default_path"))
            return self.answers.pop(0) if self.answers else ""

        patcher = mock.patch.object(wx, "FileSelector", file_selector)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(settings.set, "file", "lastattachmentpath", "")

    def open_task_file_in(self, folder):
        self.task_file.setFilename(os.path.join(folder, "tasks.tsk"))

    def test_without_a_saved_file_documents(self):
        self.iocontroller.merge()
        self.assertEqual([gui.iocontroller.documents_folder()], self.opened_in)

    def test_then_the_task_files_folder(self):
        self.open_task_file_in(self.home)
        self.iocontroller.ask_import_csv_file()
        self.assertEqual([self.home], self.opened_in)

    def test_then_the_folder_last_chosen_in_its_kind(self):
        self.open_task_file_in(self.home)
        self.answers = [os.path.join(self.other, "a.tsk")]
        self.iocontroller.merge()
        self.iocontroller.merge()  # Cancelled
        self.iocontroller.ask_import_csv_file()  # Another kind
        self.assertEqual([self.home, self.other, self.home], self.opened_in)

    def test_an_export_follows_its_own_choice(self):
        self.open_task_file_in(self.home)
        self.answers = [os.path.join(self.other, "a.ics")]
        with mock.patch.object(persistence, "iCalendarWriter") as writer:
            writer.return_value.write.return_value = 0
            self.iocontroller.export_as_icalendar(None)
            self.iocontroller.export_as_icalendar(None)
        self.assertEqual([self.home, self.other], self.opened_in)

    def test_save_as_next_to_the_current_file(self):
        self.open_task_file_in(self.other)
        self.iocontroller.save_as()
        self.assertEqual([self.other], self.opened_in)

    def test_attachments_where_last_chosen(self):
        settings.set("file", "lastattachmentpath", self.other)
        self.open_task_file_in(self.home)
        self.assertEqual(
            self.other, gui.iocontroller.attachment_folder(self.task_file)
        )

    def test_attachments_else_the_task_files_folder(self):
        self.open_task_file_in(self.home)
        self.assertEqual(
            self.home, gui.iocontroller.attachment_folder(self.task_file)
        )

    def test_a_chosen_folder_deleted_since_falls_back(self):
        self.open_task_file_in(self.home)
        self.answers = [os.path.join(self.other, "a.tsk")]
        self.iocontroller.merge()
        os.rmdir(self.other)
        self.iocontroller.merge()
        self.assertEqual([self.home, self.home], self.opened_in)

    def test_an_attachment_folder_deleted_since_falls_back(self):
        settings.set("file", "lastattachmentpath", self.other)
        os.rmdir(self.other)
        self.open_task_file_in(self.home)
        self.assertEqual(
            self.home, gui.iocontroller.attachment_folder(self.task_file)
        )

    def test_attachments_remembered(self):
        gui.iocontroller.remember_attachment_folder(
            os.path.join(self.other, "photo.png")
        )
        self.assertEqual(self.other, settings.file.lastattachmentpath)
