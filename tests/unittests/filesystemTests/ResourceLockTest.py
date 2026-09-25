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

import errno
import os
import shutil
import socket
import subprocess
import sys
import tempfile

import test
from taskcoachlib.filesystem import resourcelock

# A second process that holds a lock until its stdin closes, the way
# another running Task Coach would
HOLD_NEW_LOCK = """
import sys
from taskcoachlib.filesystem import resourcelock
resourcelock.acquire(sys.argv[1], "task file")
print("locked", flush=True)
sys.stdin.read()
"""

# A second process that holds a lock the way Task Coach 2.0.2.23 and
# older did (fasteners: open in append mode, lock at the file position)
HOLD_OLD_LOCK = """
import os, sys
lock_file = open(sys.argv[1] + ".lock", "a")
if os.name == "nt":
    import msvcrt
    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
else:
    import fcntl
    fcntl.lockf(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
print("locked", flush=True)
sys.stdin.read()
"""


class ResourceLockTest(test.TestCase):
    def setUp(self):
        super().setUp()
        self.directory = tempfile.mkdtemp()
        self.path = os.path.join(self.directory, "tasks.tsk")
        self.lock_path = self.path + ".lock"
        self.others = []

    def tearDown(self):
        for process in self.others:
            process.stdin.close()
            process.wait()
        for lock in list(resourcelock._held_locks.values()):
            lock.release()
        shutil.rmtree(self.directory)
        super().tearDown()

    def hold_in_other_process(self, script):
        source_root = os.path.dirname(
            os.path.dirname(os.path.abspath(resourcelock.__file__))
        )
        environment = dict(os.environ)
        environment["PYTHONPATH"] = os.path.dirname(source_root)
        process = subprocess.Popen(
            [sys.executable, "-c", script, self.path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env=environment,
        )
        self.others.append(process)
        # Skip the other process's log lines up to its "locked" line
        for line in process.stdout:
            if line == b"locked\n":
                break
        else:
            self.fail("the other process could not take the lock")
        return process

    def read_lock_file(self):
        with open(self.lock_path, "rb") as lock_file:
            return lock_file.read()

    def test_acquire_writes_owner_record(self):
        lock = resourcelock.acquire(self.path, "task file")
        self.assertEqual("os", lock.mode)
        self.assertIn(b"pid=%d" % os.getpid(), self.read_lock_file())

    def test_release_blanks_record_and_keeps_file(self):
        resourcelock.acquire(self.path, "task file").release()
        self.assertEqual(b"", self.read_lock_file())

    def test_same_process_gets_the_held_lock(self):
        first = resourcelock.acquire(self.path, "task file")
        self.assertIs(first, resourcelock.acquire(self.path, "task file"))

    def test_holding_releases_a_lock_it_took(self):
        with resourcelock.holding(self.path, "task file") as lock:
            self.assertIn(b"pid=%d" % os.getpid(), self.read_lock_file())
        self.assertEqual(b"", self.read_lock_file())
        self.assertIsNot(lock, resourcelock.acquire(self.path, "task file"))

    def test_holding_keeps_a_lock_already_held(self):
        held = resourcelock.acquire(self.path, "task file")
        with resourcelock.holding(self.path, "task file") as lock:
            self.assertIs(held, lock)
        self.assertIs(held, resourcelock.acquire(self.path, "task file"))
        self.assertIn(b"pid=%d" % os.getpid(), self.read_lock_file())

    def test_holding_a_lock_in_use_elsewhere_runs_nothing(self):
        self.hold_in_other_process(HOLD_NEW_LOCK)
        with self.assertRaises(resourcelock.LockInUse):
            with resourcelock.holding(self.path, "task file"):
                self.fail("ran without the lock")

    def test_lock_held_by_other_process_is_in_use(self):
        other = self.hold_in_other_process(HOLD_NEW_LOCK)
        with self.assertRaises(resourcelock.LockInUse) as context:
            resourcelock.acquire(self.path, "task file")
        self.assertEqual(str(other.pid), context.exception.owner["pid"])

    def test_lock_of_crashed_process_is_taken_over(self):
        other = self.hold_in_other_process(HOLD_NEW_LOCK)
        other.kill()
        other.wait()
        self.others.remove(other)
        lock = resourcelock.acquire(self.path, "task file")
        self.assertIn(b"pid=%d" % os.getpid(), self.read_lock_file())
        lock.release()

    def test_leftover_lock_of_old_version_is_converted(self):
        open(self.lock_path, "w").close()
        resourcelock.acquire(self.path, "task file")
        self.assertIn(b"pid=%d" % os.getpid(), self.read_lock_file())

    def test_running_old_version_blocks(self):
        self.hold_in_other_process(HOLD_OLD_LOCK)
        with self.assertRaises(resourcelock.LockInUse) as context:
            resourcelock.acquire(self.path, "task file")
        self.assertEqual({}, context.exception.owner)

    def test_old_version_started_later_is_blocked(self):
        resourcelock.acquire(self.path, "task file")
        process = subprocess.run(
            [sys.executable, "-c", HOLD_OLD_LOCK, self.path],
            input=b"",
            capture_output=True,
        )
        self.assertNotEqual(0, process.returncode)

    def test_lock_folder_of_version_1_is_converted(self):
        os.mkdir(self.lock_path)
        open(os.path.join(self.lock_path, "host.-1a2b1234"), "w").close()
        lock = resourcelock.acquire(self.path, "task file")
        self.assertEqual("os", lock.mode)
        self.assertTrue(os.path.isfile(self.lock_path))

    def test_hard_link_lock_of_version_1_is_removed(self):
        # Linux and macOS 1.x: name.lock is a hard link to a file next
        # to it named after the host, thread and process
        unique_name = os.path.join(self.directory, "host-7f3a.1234567")
        open(unique_name, "w").close()
        os.link(unique_name, self.lock_path)
        lock = resourcelock.acquire(self.path, "task file")
        self.assertEqual("os", lock.mode)
        self.assertFalse(os.path.exists(unique_name))
        self.assertEqual(1, os.stat(self.lock_path).st_nlink)
        self.assertIn(b"pid=%d" % os.getpid(), self.read_lock_file())

    def test_unwritable_location_is_used_unlocked(self):
        if os.name == "nt" or os.geteuid() == 0:
            self.skipTest("needs POSIX permissions, which root ignores")
        os.chmod(self.directory, 0o500)
        try:
            lock = resourcelock.acquire(self.path, "task file")
            self.assertEqual("none", lock.mode)
        finally:
            os.chmod(self.directory, 0o700)

    def write_record(self, pid, host=None):
        host = socket.gethostname() if host is None else host
        with open(self.lock_path, "w") as lock_file:
            lock_file.write("\npid=%s\nhost=%s\n" % (pid, host))

    def without_os_locks(self):
        """Simulate a file system that does not support OS locks."""
        original = resourcelock._lock

        def unsupported(fd):
            raise OSError(errno.ENOLCK, "No locks available")

        resourcelock._lock = unsupported
        self.addCleanup(setattr, resourcelock, "_lock", original)

    def running_process(self):
        process = subprocess.Popen(
            [sys.executable, "-c", "import sys; sys.stdin.read()"],
            stdin=subprocess.PIPE,
        )
        self.others.append(process)
        return process

    def test_record_of_running_process_blocks_without_os_locks(self):
        self.without_os_locks()
        self.write_record(self.running_process().pid)
        with self.assertRaises(resourcelock.LockInUse):
            resourcelock.acquire(self.path, "task file")

    def test_record_of_ended_process_is_taken_over_without_os_locks(self):
        self.without_os_locks()
        process = self.running_process()
        process.stdin.close()
        process.wait()
        self.others.remove(process)
        self.write_record(process.pid)
        lock = resourcelock.acquire(self.path, "task file")
        self.assertEqual("record", lock.mode)
        self.assertIn(b"pid=%d" % os.getpid(), self.read_lock_file())

    def test_record_from_other_computer_is_taken_over(self):
        self.without_os_locks()
        self.write_record(self.running_process().pid, host="elsewhere")
        resourcelock.acquire(self.path, "task file")

    def test_free_os_lock_wins_over_a_copied_record(self):
        # A lock file copied from a system without OS locks, naming a
        # process that happens to run here: the free OS lock decides
        self.write_record(self.running_process().pid)
        lock = resourcelock.acquire(self.path, "task file")
        self.assertEqual("os", lock.mode)

    def test_in_use_message_names_the_process(self):
        message = resourcelock.in_use_message(
            self.path, {"pid": "4321", "since": "2026-09-23 14:05:03"}
        )
        self.assertIn("4321", message)

    def test_symlinked_lock_file_is_not_followed(self):
        if os.name == "nt":
            self.skipTest("needs POSIX symbolic links")
        target = os.path.join(self.directory, "other.txt")
        with open(target, "wb") as target_file:
            target_file.write(b"x" * 2800)
        os.symlink(target, self.lock_path)
        resourcelock.acquire(self.path, "task file").release()
        with open(target, "rb") as target_file:
            self.assertEqual(b"x" * 2800, target_file.read())

    def test_symlinked_lock_folder_is_not_emptied(self):
        if os.name == "nt":
            self.skipTest("needs POSIX symbolic links")
        folder = os.path.join(self.directory, "folder")
        os.mkdir(folder)
        kept = os.path.join(folder, "kept.txt")
        open(kept, "w").close()
        os.symlink(folder, self.lock_path)
        resourcelock.acquire(self.path, "task file")
        self.assertTrue(os.path.exists(kept))

    def test_unwritable_lock_file_held_elsewhere_is_in_use(self):
        if os.name == "nt" or os.geteuid() == 0:
            self.skipTest("needs POSIX permissions, which root ignores")
        self.hold_in_other_process(HOLD_NEW_LOCK)
        os.chmod(self.lock_path, 0o444)
        with self.assertRaises(resourcelock.LockInUse):
            resourcelock.acquire(self.path, "task file")

    def test_unwritable_free_lock_file_is_locked_read_only(self):
        if os.name == "nt" or os.geteuid() == 0:
            self.skipTest("needs POSIX permissions, which root ignores")
        resourcelock.acquire(self.path, "task file").release()
        os.chmod(self.lock_path, 0o444)
        lock = resourcelock.acquire(self.path, "task file")
        self.assertEqual("os-read-only", lock.mode)

    def test_releasing_an_old_lock_keeps_the_newer_one_registered(self):
        old = resourcelock.acquire(self.path, "task file")
        old.release()
        new = resourcelock.acquire(self.path, "task file")
        old.release()
        self.assertIs(new, resourcelock.acquire(self.path, "task file"))
