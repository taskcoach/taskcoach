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

import test, tempfile, os
import fasteners


class FastenersLockTest(test.TestCase):
    """Tests for the fasteners library (replacement for deprecated lockfile)."""

    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(delete=False)
        self.lock_path = self.tmpfile.name + ".lock"
        self.lock = fasteners.InterProcessLock(self.lock_path)
        self._lock_acquired = False

    def tearDown(self):
        super().tearDown()
        if self._lock_acquired:
            self.lock.release()
        self.tmpfile.close()
        # Clean up temp files
        if os.path.exists(self.tmpfile.name):
            os.unlink(self.tmpfile.name)
        if os.path.exists(self.lock_path):
            os.unlink(self.lock_path)

    def testLockCanBeAcquired(self):
        result = self.lock.acquire(blocking=False)
        self._lock_acquired = result
        self.assertTrue(result)

    def testLockCanBeReleased(self):
        self.lock.acquire(blocking=False)
        self._lock_acquired = True
        self.lock.release()
        self._lock_acquired = False
        # Should be able to acquire again after release
        result = self.lock.acquire(blocking=False)
        self._lock_acquired = result
        self.assertTrue(result)

    def testLockingWithContextManager(self):
        with self.lock:
            # Lock is held inside context
            pass
        # Lock is released after context
        # Should be able to acquire again
        result = self.lock.acquire(blocking=False)
        self._lock_acquired = result
        self.assertTrue(result)

    def testLockingTwoFiles(self):
        self.lock.acquire(blocking=False)
        self._lock_acquired = True

        tmpfile2 = tempfile.NamedTemporaryFile(delete=False)
        lock_path2 = tmpfile2.name + ".lock"
        lock2 = fasteners.InterProcessLock(lock_path2)

        try:
            result2 = lock2.acquire(blocking=False)
            self.assertTrue(result2)
            lock2.release()
        finally:
            tmpfile2.close()
            if os.path.exists(tmpfile2.name):
                os.unlink(tmpfile2.name)
            if os.path.exists(lock_path2):
                os.unlink(lock_path2)
