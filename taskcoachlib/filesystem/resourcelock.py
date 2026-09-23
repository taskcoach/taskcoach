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

The single locking standard of Task Coach, used for the settings file
(one instance per INI file) and for task files.

A resource "name" is locked through "name.lock" next to it. The lock
is an operating system lock on that file, so it is released
automatically when Task Coach exits, crashes or the computer
restarts. The file also holds an owner record (process ID, host,
user, start time, version) that is shown when the resource is in use.
A lock is only ever taken over automatically, when no running Task
Coach holds it; the user is never asked to break a lock.

Locks left by older versions are converted automatically, and a
running older version still blocks this one (and the other way
around). See docs/FILE_LOCKING.md for the full design.
"""

import datetime
import errno
import getpass
import os
import socket
import time

from taskcoachlib.meta.debug import log_step

LOCK_SUFFIX = ".lock"

# Layout of the lock file: byte 0 is a newline, bytes 1 to
# RECORD_SIZE - 1 hold the owner record, padded with spaces. The OS
# lock covers byte 0 and everything from RECORD_SIZE on, but never the
# record itself: Windows byte-range locks also block reading, and the
# record must stay readable for the "in use" message.
RECORD_SIZE = 1024

# OS lock errors that mean "another process holds the lock". Any other
# error means the file system does not support OS locks.
_BUSY_ERRNOS = {errno.EACCES, errno.EAGAIN, errno.EDEADLK}

# Windows may release the lock of a crashed process slightly late, so
# retry briefly before reporting the resource as in use.
_ATTEMPTS = 5
_RETRY_DELAY = 0.1

_held_locks = {}


class LockInUse(Exception):
    """Raised when a running Task Coach holds the lock.

    owner is the owner record as a dict, empty when the other instance
    is an older version that does not write one.
    """

    def __init__(self, path, owner):
        super().__init__("%s is in use" % path)
        self.path = path
        self.owner = owner


def acquire(path, purpose):
    """Lock path for this process and return the ResourceLock.

    Returns the existing lock when this process already holds it, so a
    lock taken early (for example at startup) is simply adopted later.
    Raises LockInUse when another running Task Coach holds it. When no
    lock can be taken at all (read-only location, no OS locking and no
    writable lock file), the returned lock has mode "none" and the
    resource is used unlocked.
    """
    key = _key(path)
    lock = _held_locks.get(key)
    if lock is None:
        lock = ResourceLock(path, purpose)
        lock.acquire()
        _held_locks[key] = lock
    return lock


def in_use_message(path, owner):
    """The message shown when path is open in another Task Coach."""
    from taskcoachlib.i18n import _

    message = _("%s is already open in another Task Coach") % path
    summary = owner_summary(owner)
    if summary:
        message += " (%s)" % summary
    return message + ".\n" + _("Close it there first, then try again.")


def owner_summary(owner):
    """Describe an owner record for messages, e.g. "process 1234,
    since 2026-09-23 14:05:03"."""
    from taskcoachlib.i18n import _

    parts = []
    if owner.get("pid"):
        parts.append(_("process %s") % owner["pid"])
    if owner.get("since"):
        parts.append(_("since %s") % owner["since"])
    if owner.get("version"):
        parts.append(_("version %s") % owner["version"])
    return ", ".join(parts)


class ResourceLock:
    """An acquired lock; use acquire() rather than creating it directly.

    mode is "os" (operating system lock, the normal case), "record"
    (the file system has no OS locks, so only the owner record and a
    process check protect the resource) or "none" (no lock file could
    be written).
    """

    def __init__(self, path, purpose):
        self.path = os.path.abspath(path)
        self.lock_path = self.path + LOCK_SUFFIX
        self.purpose = purpose
        self.mode = None
        self._fd = None

    def acquire(self):
        """Take the lock. This is the one procedure for every lock,
        whatever the file system supports:

        1. Remove a Task Coach 1.x lock, if any, then open (or create)
           the lock file. If no lock file can be written, the resource
           is used unlocked.
        2. Try the OS lock. Refused means a running Task Coach holds
           it: in use, stop here. Granted or not supported, go on.
        3. Check the owner record left in the file. It still counts
           only when all of these hold: the OS lock is not supported
           (a granted OS lock proves nobody holds it, whatever the
           record says), the record is from this computer (locks are
           not shared across computers), and its process still runs.
           Otherwise the record is stale and is taken over.
        4. Write our own owner record, keeping the OS lock if granted.
        """
        try:
            self._remove_legacy_lock()
        except OSError as reason:
            self.mode = "none"
            self._log("cannot remove 1.x lock, using unlocked: %s" % reason)
            return
        try:
            self._fd = os.open(self.lock_path, _OPEN_FLAGS, 0o666)
        except OSError as reason:
            self.mode = "none"
            self._log("cannot create lock file, using unlocked: %s" % reason)
            return
        try:
            self.mode = "os" if self._take_os_lock() else "record"
            owner = _read_record(self._fd)
            if owner.get("pid"):
                self._check_owner(owner)
        except BaseException:
            self._close()
            raise
        try:
            self._write_record()
        except OSError as reason:
            # The OS lock still protects the resource; only the owner
            # details for the "in use" message are missing
            self._log("cannot write owner record: %s" % reason)
        self._log("acquired (%s lock)" % self.mode)

    def release(self):
        """Blank the owner record, then release the lock. The lock
        file itself is kept: deleting it while another process waits
        for it would let two processes lock two different files."""
        _held_locks.pop(_key(self.path), None)
        if self._fd is None:
            return
        try:
            os.ftruncate(self._fd, 0)
        except OSError:
            pass
        if self.mode == "os":
            try:
                _unlock(self._fd)
            except OSError:
                pass
        self._close()
        self._log("released")

    def _take_os_lock(self):
        for attempt in range(_ATTEMPTS):
            try:
                _lock(self._fd)
                return True
            except OSError as reason:
                if reason.errno not in _BUSY_ERRNOS:
                    self._log(
                        "no OS locking here (%s), using owner record" % reason
                    )
                    return False
            if attempt + 1 < _ATTEMPTS:
                time.sleep(_RETRY_DELAY)
        owner = _read_record(self._fd)
        self._log("in use (OS lock held by %s)" % (_describe(owner)))
        raise LockInUse(self.path, owner)

    def _check_owner(self, owner):
        """Step 3 of acquire(): raise LockInUse if the record's owner
        still holds the lock, otherwise log why it is taken over."""
        here = owner.get("host", "").lower() == socket.gethostname().lower()
        if self.mode == "os":
            reason = "the OS lock was free"
        elif not here:
            reason = "it is from another computer"
        elif not _is_running(owner.get("pid")):
            reason = "its process no longer runs"
        else:
            self._log("in use (no OS locking; %s runs)" % _describe(owner))
            raise LockInUse(self.path, owner)
        self._log(
            "took over the lock of process %s on %s: %s"
            % (owner.get("pid"), owner.get("host", "?"), reason)
        )

    def _remove_legacy_lock(self):
        """Remove a lock of Task Coach 1.x (the lockfile library). It
        never took an OS lock, so it cannot belong to a running Task
        Coach of version 2 or later, and 1.x is assumed not to be
        running on the same file (its lock names glue the process ID
        to a thread ID, so the owner cannot be checked). Its formats:

        - Windows: a folder "name.lock" holding one file.
        - Linux and macOS: "name.lock" is a hard link to a file named
          "<host>-<thread>.<pid><hash>" next to it; both are removed.
          Later versions never hard-link the lock file.
        """
        if os.path.isdir(self.lock_path):
            for name in os.listdir(self.lock_path):
                os.remove(os.path.join(self.lock_path, name))
            os.rmdir(self.lock_path)
            self._log("removed lock folder of Task Coach 1.x")
            return
        try:
            info = os.stat(self.lock_path)
        except FileNotFoundError:
            return
        if info.st_nlink < 2:
            return
        folder = os.path.dirname(self.lock_path)
        for name in os.listdir(folder):
            other = os.path.join(folder, name)
            if other == self.lock_path:
                continue
            try:
                same = os.path.samestat(info, os.stat(other))
            except OSError:
                continue
            if same:
                os.remove(other)
        os.remove(self.lock_path)
        self._log("removed hard-link lock of Task Coach 1.x")

    def _write_record(self):
        lines = [
            "Task Coach lock file; it is released automatically.",
            "purpose=%s" % self.purpose,
            "pid=%d" % os.getpid(),
            "host=%s" % socket.gethostname(),
            "user=%s" % _user_name(),
            "since=%s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version=%s" % _version(),
        ]
        record = ("\n" + "\n".join(lines) + "\n").encode("utf-8")
        record = record[:RECORD_SIZE].ljust(RECORD_SIZE, b" ")
        os.lseek(self._fd, 0, os.SEEK_SET)
        os.write(self._fd, record)
        os.ftruncate(self._fd, RECORD_SIZE)

    def _close(self):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def _log(self, message):
        log_step("%s: %s" % (self.lock_path, message), prefix="LOCK")


def _describe(owner):
    if not owner:
        return "an older Task Coach without owner record"
    return "process %s on %s" % (owner.get("pid"), owner.get("host", "?"))


def _key(path):
    return os.path.normcase(os.path.abspath(path))


def _read_record(fd):
    """Read the owner record, skipping byte 0, which the owner's OS
    lock may make unreadable on Windows. An empty dict means no record,
    e.g. a lock of an older version."""
    try:
        os.lseek(fd, 1, os.SEEK_SET)
        data = os.read(fd, RECORD_SIZE - 1)
    except OSError:
        return {}
    owner = {}
    for line in data.decode("utf-8", "replace").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            owner[key.strip()] = value.strip()
    return owner


def _is_running(pid):
    """True when pid is another running process on this computer."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    return pid > 0 and pid != os.getpid() and _process_exists(pid)


def _user_name():
    try:
        return getpass.getuser()
    except Exception:
        return ""


def _version():
    from taskcoachlib import meta

    return meta.version_full


if os.name == "nt":
    import ctypes
    import msvcrt
    from ctypes import wintypes

    _OPEN_FLAGS = os.O_RDWR | os.O_CREAT | os.O_BINARY | os.O_NOINHERIT
    _TAIL_LENGTH = 0x7FFFFFFF - RECORD_SIZE

    def _lock(fd):
        # Byte 0 blocks older versions, which lock byte 0 of an empty
        # file; the tail blocks older versions started later, which
        # lock the byte at the end of the file (RECORD_SIZE).
        _lock_range(fd, 0, 1)
        try:
            _lock_range(fd, RECORD_SIZE, _TAIL_LENGTH)
        except OSError:
            _unlock_range(fd, 0, 1)
            raise

    def _unlock(fd):
        _unlock_range(fd, RECORD_SIZE, _TAIL_LENGTH)
        _unlock_range(fd, 0, 1)

    def _lock_range(fd, start, length):
        os.lseek(fd, start, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, length)

    def _unlock_range(fd, start, length):
        os.lseek(fd, start, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, length)

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.OpenProcess.argtypes = [
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    _kernel32.GetExitCodeProcess.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    ]
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    _STILL_ACTIVE = 259
    _ERROR_ACCESS_DENIED = 5

    def _process_exists(pid):
        handle = _kernel32.OpenProcess(
            _PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if not handle:
            # Access denied means the process exists but belongs to
            # another user or runs elevated.
            return ctypes.get_last_error() == _ERROR_ACCESS_DENIED
        try:
            code = wintypes.DWORD()
            if not _kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True
            return code.value == _STILL_ACTIVE
        finally:
            _kernel32.CloseHandle(handle)

else:
    import fcntl

    _OPEN_FLAGS = os.O_RDWR | os.O_CREAT | os.O_CLOEXEC

    def _lock(fd):
        # The whole file, like older versions, so each blocks the other.
        # POSIX locks are advisory, so the record stays readable. Never
        # open the lock file a second time in this process: closing any
        # handle to it drops the process's lock.
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB, 0, 0, os.SEEK_SET)

    def _unlock(fd):
        fcntl.lockf(fd, fcntl.LOCK_UN, 0, 0, os.SEEK_SET)

    def _process_exists(pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True
