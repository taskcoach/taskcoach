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

from taskcoachlib import persistence, config, patterns
from taskcoachlib.domain import task, category, date
from unittests import dummy
import test


class DummyFile(object):
    name = "testfile.tsk"
    encoding = "utf-8"

    def close(self, *args, **kwargs):
        pass

    def write(self, *args, **kwargs):
        pass


class DummyTaskFile(persistence.TaskFile):
    def __init__(self, *args, **kwargs):
        self.saveCalled = 0
        self.failing_saves = 0
        self._throw = False
        super().__init__(*args, **kwargs)

    def _read(self, *args, **kwargs):  # pylint: disable=W0613,W0221
        if self._throw:
            raise IOError
        else:
            content = (
                [task.Task()],
                [category.Category("category")],
                [],
                None,
                {self.monitor().guid(): self.monitor()},
                None,
            )
            return content, []  # No duplicate ids

    def exists(self, *args, **kwargs):  # pylint: disable=W0613
        return True

    def _openForRead(self, *args, **kwargs):  # pylint: disable=W0613
        return DummyFile()

    def _openForWrite(self, *args, **kwargs):  # pylint: disable=W0613
        return DummyFile()

    def save(self, *args, **kwargs):
        if kwargs.get("doNotify", True):
            self.saveCalled += 1
        if self.failing_saves:
            self.failing_saves -= 1
            raise IOError("disk full")
        super().save(*args, **kwargs)

    def load(
        self, filename=None, throw=False, *args, **kwargs
    ):  # pylint: disable=W0221
        self._throw = throw  # pylint: disable=W0201
        return super().load(filename, *args, **kwargs)


class AutoSaverTestCase(test.TestCase):
    def setUp(self):
        task.Task.settings = self.settings = config.Settings(load=False)
        self.taskFile = DummyTaskFile()
        self.autoSaver = persistence.AutoSaver(self.settings)

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()
        del self.autoSaver  # Make sure AutoSaver is not observing task files

    def testCreate(self):
        self.assertFalse(self.taskFile.saveCalled)

    def testFileChanged_ButNoFilenameAndAutoSaveOff(self):
        self.taskFile.tasks().append(task.Task())
        self.autoSaver.on_idle(dummy.Event())
        self.assertFalse(self.taskFile.saveCalled)

    def testFileChanged_ButAutoSaveOff(self):
        self.settings.set("file", "autosave", "False")
        self.taskFile.setFilename("whatever.tsk")
        self.taskFile.tasks().append(task.Task())
        self.autoSaver.on_idle(dummy.Event())
        self.assertFalse(self.taskFile.saveCalled)

    def testFileChanged_ButNoFilename(self):
        self.settings.set("file", "autosave", "True")
        self.taskFile.tasks().append(task.Task())
        self.autoSaver.on_idle(dummy.Event())
        self.assertFalse(self.taskFile.saveCalled)

    def testFileChanged(self):
        self.settings.set("file", "autosave", "True")
        self.taskFile.setFilename("whatever.tsk")
        self.taskFile.tasks().append(task.Task())
        self.autoSaver.on_idle(dummy.Event())
        self.assertEqual(1, self.taskFile.saveCalled)

    def testSaveAsDoesNotTriggerAutoSave(self):
        self.settings.set("file", "autosave", "True")
        self.taskFile.setFilename("whatever.tsk")
        self.taskFile.saveas("newfilename.tsk")
        self.autoSaver.on_idle(dummy.Event())
        self.assertEqual(1, self.taskFile.saveCalled)

    def testCloseDoesNotTriggerAutoSave(self):
        self.settings.set("file", "autosave", "True")
        self.taskFile.setFilename("whatever.tsk")
        self.taskFile.tasks().append(task.Task())
        self.autoSaver.on_idle(dummy.Event())
        self.taskFile.close()
        self.assertEqual(1, self.taskFile.saveCalled)

    def testLoadDoesNotTriggerAutoSave(self):
        self.settings.set("file", "autosave", "True")
        self.taskFile.setFilename("whatever.tsk")
        self.taskFile.load()
        self.autoSaver.on_idle(dummy.Event())
        self.assertFalse(self.taskFile.saveCalled)

    def testLoadWithExceptionDoesNotTriggerAutoSave(self):
        self.settings.set("file", "autosave", "True")
        self.taskFile.setFilename("whatever.tsk")
        try:
            self.taskFile.load(throw=True)
        except IOError:
            pass
        self.autoSaver.on_idle(dummy.Event())
        self.assertFalse(self.taskFile.saveCalled)

    def testMergeDoesTriggerAutoSave(self):
        self.settings.set("file", "autosave", "True")
        self.taskFile.setFilename("whatever.tsk")
        self.taskFile.merge("another-non-existing-file.tsk")
        self.autoSaver.on_idle(dummy.Event())
        self.assertEqual(1, self.taskFile.saveCalled)


class AutoSaverRetryTest(test.TestCase):
    def setUp(self):
        super().setUp()
        task.Task.settings = self.settings = config.Settings(load=False)
        self.taskFile = DummyTaskFile()
        self.autoSaver = persistence.AutoSaver(self.settings)
        self.autoSaver.RETRY_SECONDS = 0
        self.messages = []
        self.autoSaver._tell_user = self.messages.append
        self.settings.set("file", "autosave", "True")
        self.taskFile.setFilename("whatever.tsk")

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def autosave(self):
        self.autoSaver.on_idle(dummy.Event())

    def next_second(self):
        # The Publisher drops events without a source
        patterns.Event("timer.second", self, date.DateTime.now()).send()
        self.autosave()

    def test_failed_autosave_is_tried_again(self):
        self.taskFile.failing_saves = 1
        self.taskFile.tasks().append(task.Task())
        self.autosave()
        self.next_second()
        self.assertEqual(2, self.taskFile.saveCalled)
        self.assertFalse(self.taskFile.need_save())

    def test_user_is_told_once_when_autosave_keeps_failing(self):
        self.taskFile.failing_saves = 3
        self.taskFile.tasks().append(task.Task())
        self.autosave()
        self.assertEqual([], self.messages)
        self.next_second()
        self.next_second()
        self.assertEqual(1, len(self.messages))
        self.assertIn("disk full", self.messages[0])

    def test_no_retry_after_saving_by_hand(self):
        self.taskFile.failing_saves = 1
        self.taskFile.tasks().append(task.Task())
        self.autosave()
        self.taskFile.save()
        self.next_second()
        self.next_second()
        self.assertEqual(2, self.taskFile.saveCalled)
