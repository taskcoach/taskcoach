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

import os
import shutil
import tempfile
import threading

import test
from taskcoachlib.filesystem.watcher import FilesystemNotifier


class Watcher(FilesystemNotifier):
    INTERVAL = 0.02

    def __init__(self):
        super().__init__()
        self.changed = threading.Event()

    def on_file_changed(self):
        self.changed.set()


def watcher_threads():
    return [
        thread
        for thread in threading.enumerate()
        if thread.name == "file watcher"
    ]


class WatcherTest(test.TestCase):
    """Another program's change to the open file is noticed within
    seconds, on every system
    (docs/PERSISTENCE_XML.md#watching-the-file)."""

    def setUp(self):
        super().setUp()
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        self.filename = os.path.join(folder, "tasks.tsk")
        self.write("<tasks/>")
        self.watcher = Watcher()
        self.addCleanup(self.watcher.stop)

    def write(self, text):
        with open(self.filename, "w") as file:
            file.write(text)

    def noticed(self):
        return self.watcher.changed.wait(2)

    def test_a_change_in_place_is_noticed(self):
        self.watcher.set_filename(self.filename)
        self.write("<tasks>changed</tasks>")
        self.assertTrue(self.noticed())

    def test_a_copy_renamed_over_it_is_noticed(self):
        self.watcher.set_filename(self.filename)
        new = self.filename + ".new"
        with open(new, "w") as file:
            file.write("<tasks>replaced</tasks>")
        os.replace(new, self.filename)
        self.assertTrue(self.noticed())

    def test_an_older_copy_put_back_is_noticed(self):
        self.watcher.set_filename(self.filename)
        stat = os.stat(self.filename)
        os.utime(self.filename, (stat.st_atime, stat.st_mtime - 3600))
        self.assertTrue(self.noticed())

    def test_a_file_made_after_watching_started_is_noticed(self):
        os.remove(self.filename)
        self.watcher.set_filename(self.filename)
        self.write("<tasks/>")
        self.assertTrue(self.noticed())

    def test_an_unchanged_file_is_not_reported(self):
        self.watcher.set_filename(self.filename)
        self.assertFalse(self.watcher.changed.wait(0.2))

    def test_our_own_save_is_taken_as_the_files_state(self):
        self.watcher.set_filename(self.filename)
        self.write("<tasks>saved</tasks>")
        self.watcher.saved()
        stat = os.stat(self.filename)
        self.assertEqual((stat.st_mtime_ns, stat.st_size), self.watcher.stamp)

    def test_no_thread_until_a_file_is_watched(self):
        before = len(watcher_threads())
        Watcher()
        self.assertEqual(before, len(watcher_threads()))

    def test_stop_ends_its_thread(self):
        self.watcher.set_filename(self.filename)
        thread = watcher_threads()[-1]
        self.watcher.stop()
        self.assertFalse(thread.is_alive())

    def test_no_file_ends_its_thread(self):
        self.watcher.set_filename(self.filename)
        thread = watcher_threads()[-1]
        self.watcher.set_filename("")
        thread.join(2)
        self.assertFalse(thread.is_alive())
