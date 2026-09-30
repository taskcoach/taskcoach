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

import io
import logging
import os
import shutil
import stat
from . import xml
from .merge import merge_into
from taskcoachlib import patterns
from taskcoachlib.domain import attachment, categorizable, category, effort
from taskcoachlib.domain import note, task
from taskcoachlib.meta.debug import log_step
from taskcoachlib.filesystem import (
    FilesystemNotifier,
    FilesystemPollerNotifier,
    resourcelock,
)


class ChangedOnDiskError(Exception):
    """Saving would replace changes another program made to the file:
    merge them in, reload, or save under another name first
    (docs/PERSISTENCE_XML.md, Saving)."""


def _isCloud(path):
    path = os.path.abspath(path)
    while True:
        for name in [".dropbox.cache", ".csync_journal.db"]:
            if os.path.exists(os.path.join(path, name)):
                return True
        path, name = os.path.split(path)
        if name == "":
            return False


class TaskCoachFilesystemNotifier(FilesystemNotifier):
    def __init__(self, taskFile):
        self.__taskFile = taskFile
        super().__init__()

    def on_file_changed(self):
        self.__taskFile.on_file_changed()


class TaskCoachFilesystemPollerNotifier(FilesystemPollerNotifier):
    def __init__(self, taskFile):
        self.__taskFile = taskFile
        super().__init__()

    def on_file_changed(self):
        self.__taskFile.on_file_changed()


def _discard(fd):
    """Close a file from _openForWrite after a failed write, so a
    partial write never replaces the file on disk."""
    getattr(fd, "discard", fd.close)()


def _move_aside(path):
    """Move path to a new name in its folder and return that name. The
    name is short: appending to path could pass the Windows path
    length limit."""
    aside, placeholder = SafeWriteFile._create_temporary_file(
        os.path.dirname(path)
    )
    placeholder.close()
    try:
        os.replace(path, aside)
    except BaseException:
        os.remove(aside)
        raise
    return aside


def _remove(path):
    try:
        os.remove(path)
    except PermissionError:
        # Windows refuses to remove a read-only file
        os.chmod(path, stat.S_IWRITE)
        os.remove(path)


class SafeWriteFile(object):
    """Write to a temporary file and move it over the file on close(),
    so a failed write leaves the file intact."""

    def __init__(self, filename):
        # Write the file a link points to, so the link stays a link
        if os.path.islink(filename):
            filename = os.path.realpath(filename)
        self.__filename = filename
        # Decided once: it must not change between open and close
        self.__cloud = self._isCloud()
        if self.__cloud:
            # A temporary file would be synced too, so write in place,
            # but only on close(): buffering in memory means a failure
            # before that (e.g. while generating the XML) leaves the
            # file intact. A failure during the final write still
            # truncates it.
            self.__fd = io.BytesIO()
        else:
            self.__tempFilename, self.__fd = self._create_temporary_file(
                os.path.dirname(self.__filename)
            )

    def write(self, bf):
        self.__fd.write(bf)

    def discard(self):
        """Close without replacing the target file."""
        try:
            self.__fd.close()
        except OSError:
            pass  # e.g. the flush on a full disk; the caller re-raises
        if not self.__cloud:
            self.__remove_temporary_file()

    def close(self):
        if self.__cloud:
            data = self.__fd.getvalue()
            self.__fd.close()
            with open(self.__filename, "wb") as target:
                target.write(data)
            return
        try:
            self.__fd.close()  # Flushes, which fails on a full disk
        except BaseException:
            self.__remove_temporary_file()
            raise
        try:
            # Keep who may read it, e.g. a private file stays private.
            # Windows keeps permissions in ACLs, which the mode does not
            # carry.
            if os.name != "nt" and os.path.exists(self.__filename):
                try:
                    shutil.copymode(self.__filename, self.__tempFilename)
                except OSError:
                    log_step(
                        "cannot copy the mode of %s" % self.__filename,
                        prefix="FILE",
                        exc=True,
                    )
            # One step, so the file is never missing
            os.replace(self.__tempFilename, self.__filename)
        except BaseException:
            self.__remove_temporary_file()
            raise

    def __remove_temporary_file(self):
        try:
            os.remove(self.__tempFilename)
        except OSError:
            pass

    @staticmethod
    def _create_temporary_file(path):
        # Created exclusively, so another Task Coach saving in the same
        # folder gets another name; close() copies the mode of the file
        # it replaces
        flags = (
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        )
        index = 0
        while True:
            name = os.path.join(path, "tmp-%d" % index)
            try:
                fd = os.open(name, flags, 0o666)
            except FileExistsError:
                index += 1
                continue
            return name, os.fdopen(fd, "wb")

    def _isCloud(self):
        return _isCloud(os.path.dirname(self.__filename))


# The saved state can no longer be reached by undo or redo
_UNREACHABLE = object()

_ATTACHMENT_CLASSES = (
    attachment.FileAttachment,
    attachment.URIAttachment,
    attachment.MailAttachment,
)


def _saved_event_types():
    """The events of saved data changing: an item's modification date,
    an item added to or removed from another, saved view state (the
    expanded state, a category's filter)."""
    composites = (task.Task, category.Category, note.Note)
    for cls in composites + (effort.Effort,) + _ATTACHMENT_CLASSES:
        yield cls.modification_datetime_changed_event_type()
    for cls in composites:
        yield cls.addChildEventType()
        yield cls.removeChildEventType()
        yield cls.expansionChangedEventType()
    for cls in (task.Task, category.Category) + _ATTACHMENT_CLASSES:
        yield cls.notesChangedEventType()
    for cls in composites:
        yield cls.attachmentsChangedEventType()
    yield task.Task.effortsChangedEventType()
    yield category.Category.filterChangedEventType()


class TaskFile(patterns.Observer):
    def __init__(self, *args, **kwargs):
        self.__filename = self.__lastFilename = ""
        self.__needSave = self.__loading = False
        self.__tasks = task.TaskList()
        self.__categories = category.CategoryList()
        self.__notes = note.NoteContainer()
        self.__efforts = effort.EffortList(self.tasks())
        self.__corrected_ids = {}
        self.__changedOnDisk = False
        # The file's (mtime, size) when last loaded or saved
        self.__saved_stat = None
        # A read-only task file (merge) sends no messages about itself
        self.__read_only = kwargs.pop("read_only", False)
        if kwargs.pop("poll", False):
            self.__notifier = TaskCoachFilesystemPollerNotifier(self)
        else:
            self.__notifier = TaskCoachFilesystemNotifier(self)
        self.__saving = False
        super().__init__(*args, **kwargs)
        # Unsaved (dirty) when saved data changes: an item's own data
        # (every change sets its modification date), an item added or
        # removed, saved view state (docs/PERSISTENCE_XML.md, Saving)
        for container in self.tasks(), self.categories(), self.notes():
            for eventType in container.modificationEventTypes():
                self.registerObserver(
                    self.onDomainObjectAddedOrRemoved,
                    eventType,
                    eventSource=container,
                )
        for event_type in _saved_event_types():
            self.registerObserver(self.on_saved_data_changed, event_type)
        self.__saved_at = None
        self.registerObserver(
            self.on_command_history_changed, "commandhistory.changed"
        )

    def __str__(self):
        return self.filename()

    def __contains__(self, item):
        return (
            item in self.tasks()
            or item in self.notes()
            or item in self.categories()
            or item in self.efforts()
        )

    def categories(self):
        return self.__categories

    def notes(self):
        return self.__notes

    def tasks(self):
        return self.__tasks

    def efforts(self):
        return self.__efforts

    def categorizables(self):
        """Every item in the file that can have categories."""
        return categorizable.categorizables_in(
            self.tasks(), self.notes(), self.categories()
        )

    def corrected_ids(self):
        """The duplicate IDs the last load corrected: ID -> the items'
        (type, path), the first kept the ID."""
        return self.__corrected_ids

    def isEmpty(self):
        return (
            0
            == len(self.categories())
            == len(self.tasks())
            == len(self.notes())
        )

    def onDomainObjectAddedOrRemoved(self, event):  # pylint: disable=W0613
        if self.__loading or self.__saving:
            return
        self.mark_dirty()

    def on_saved_data_changed(self, event):
        if self.__loading or self.__saving:
            return
        if any(self.__holds(item) for item in event.sources()):
            self.mark_dirty()

    def __holds(self, item):
        """Whether the item is this file's. Owned notes and attachments
        do not know their owner, so they are assumed to be."""
        if isinstance(item, task.Task):
            return item in self.tasks()
        if isinstance(item, category.Category):
            return item in self.categories()
        if isinstance(item, effort.Effort):
            return item.task() in self.tasks()
        return True

    def setFilename(self, filename):
        if filename == self.__filename:
            return
        self.__lastFilename = filename or self.__filename
        self.__filename = filename
        self.__notifier.setFilename(filename)
        self._publish("taskfile.filenameChanged", filename)

    def _publish(self, event_type, *value):
        """An event about this file, the file as source."""
        # A read-only task file (merge) is not the open file: events
        # about it would reach listeners of every file (backups,
        # autosave).
        if not self.__read_only:
            patterns.Event(event_type, self, *value).send()

    def filename(self):
        return self.__filename

    def lastFilename(self):
        return self.__lastFilename

    def is_dirty(self):
        return self.__needSave

    def mark_dirty(self, force=False):
        if not patterns.CommandHistory().is_running():
            # Changed outside a command: undo cannot bring back the
            # saved state
            self.__saved_at = _UNREACHABLE
        if force or not self.__needSave:
            self.__needSave = True
            self._publish("taskfile.dirty")

    def mark_clean(self):
        # The saved state is where undo and redo lead to this command
        self.__saved_at = patterns.CommandHistory().current()
        if self.__needSave:
            self.__needSave = False
            self._publish("taskfile.clean")

    def on_command_history_changed(self, event):
        """Undo or redo back to the saved state leaves nothing to
        save. A command that changed nothing (a copy) leaves the file
        as saved: the saved state moves along with it."""
        current = patterns.CommandHistory().current()
        if not self.__needSave:
            self.__saved_at = current
        elif (
            self.__saved_at is not _UNREACHABLE and current is self.__saved_at
        ):
            self.mark_clean()

    def on_file_changed(self):
        # Checked on the main thread, after any save of ours finished
        patterns.later.soon(None, self.check_disk)

    def check_disk(self, notify=True):
        """Notice a change by another program: the file differs from
        what was last loaded or saved. Without notify, the caller tells
        the user itself."""
        if self.__saving or self.__read_only or self.__changedOnDisk:
            return
        if self.__saved_stat is None:
            return  # Neither loaded nor saved yet
        stat = self.__disk_stat()
        if stat is None or stat == self.__saved_stat:
            return
        self.__changedOnDisk = True
        log_step("%s changed on disk" % self.__filename, prefix="FILE")
        if notify:
            self._publish("taskfile.changed")

    def __disk_stat(self):
        try:
            stat = os.stat(self.__filename)
        except (OSError, TypeError):
            return None
        return stat.st_mtime_ns, stat.st_size

    @patterns.eventSource
    def clear(self, event=None):
        self._publish("taskfile.aboutToClear")
        try:
            self.tasks().clear(event=event)
            self.categories().clear(event=event)
            self.notes().clear(event=event)
        finally:
            self._publish("taskfile.justCleared")

    def close(self):
        self.setFilename("")
        self.clear()
        self.mark_clean()
        self.__changedOnDisk = False
        self.__saved_stat = None

    def stop(self):
        self.__notifier.stop()

    def detach(self):
        """Stop watching the file and following changes of the domain
        objects, without clearing them: for a task file whose objects
        belong to the open file (Save selection). Otherwise it gets
        dirty, and autosaved, whenever they change later."""
        self.stop()
        self.removeInstance()

    def _read(self, fd):
        reader = xml.XMLReader(fd)
        result = reader.read()
        duplicate_ids = reader.get_duplicate_ids()
        return result, duplicate_ids

    def _log_duplicate_ids(self, duplicate_ids):
        """Log the duplicate IDs the reader corrected: the first item
        with each kept it, the others got new ones."""
        logger = logging.getLogger(__name__)
        logger.warning("=" * 70)
        logger.warning(
            "Duplicate IDs corrected in task file: %s", self.__filename
        )
        logger.warning(
            "The first item with each ID keeps it, the others got new"
        )
        logger.warning("IDs; the file is marked unsaved to keep this.")
        logger.warning("")
        logger.warning("Duplicate IDs and their locations:")
        for obj_id, locations in duplicate_ids.items():
            logger.warning("")
            logger.warning("  ID: %s", obj_id)
            for obj_type, path in locations:
                logger.warning("    - %s", path)
        logger.warning("=" * 70)

    def exists(self):
        return os.path.isfile(self.__filename)

    def _openForWrite(self, suffix=""):
        return SafeWriteFile(self.__filename + suffix)

    def _openForRead(self):
        return open(self.__filename, "r", encoding="utf-8")

    def load(self, filename=None):
        self._publish("taskfile.aboutToRead")
        self.__loading = True
        if filename:
            self.setFilename(filename)
        # Before reading: a change during the read is noticed later
        stat = self.__disk_stat()
        duplicate_ids = None
        self.__corrected_ids = {}
        try:
            if self.exists():
                fd = self._openForRead()
                try:
                    (tasks, categories, notes), duplicate_ids = self._read(fd)
                finally:
                    fd.close()
                # Log any duplicate IDs found in the file
                if duplicate_ids:
                    self._log_duplicate_ids(duplicate_ids)
                    self.__corrected_ids = duplicate_ids
            else:
                tasks = []
                categories = []
                notes = []
            self.clear()
            self.categories().extend(categories)
            self.tasks().extend(tasks)
            self.notes().extend(notes)
        except Exception:
            self.setFilename("")
            raise
        finally:
            self.__loading = False
            self.mark_clean()
            if duplicate_ids:
                # Corrected while reading: saving keeps the new IDs
                self.mark_dirty()
            self.__changedOnDisk = False
            self.__saved_stat = stat
            self._publish("taskfile.justRead")

    def save(self):
        # Also when the watcher did not report it (yet); callers check
        # first, to ask the user
        self.check_disk(notify=False)
        if self.__changedOnDisk:
            raise ChangedOnDiskError(self.__filename)
        try:
            self._publish("taskfile.aboutToSave")
        except Exception:
            pass  # Ignore errors from subscribers
        # When encountering a problem while saving (disk full,
        # computer on fire), if we were writing directly to the file,
        # it's lost. So write to a temporary file and rename it if
        # everything went OK.
        self.__saving = True
        try:
            if self.__needSave or not os.path.exists(self.__filename):
                fd = self._openForWrite()
                try:
                    xml.XMLWriter(fd).write(
                        self.tasks(),
                        self.categories(),
                        self.notes(),
                    )
                except BaseException:
                    _discard(fd)
                    raise
                fd.close()

            self.mark_clean()
            self.__saved_stat = self.__disk_stat()
        finally:
            self.__saving = False
            self.__notifier.saved()

    def merge_changes_on_disk(self):
        """Merge the file as another program changed it: the newest
        copy of each item (docs/PERSISTENCE_XML.md, Merging). Saving is
        allowed again."""
        disk_state = self.__changedOnDisk, self.__saved_stat
        # Before merging: the merge marks the file unsaved, which starts
        # an autosave. The stat is taken before reading, as in load().
        self.__changedOnDisk, self.__saved_stat = False, self.__disk_stat()
        try:
            self.merge(self.__filename)
        except BaseException:
            self.__changedOnDisk, self.__saved_stat = disk_state
            raise
        log_step(
            "merged the changes on disk of %s" % self.__filename,
            prefix="FILE",
        )

    def saveas(self, filename):
        # An existing file there is moved aside rather than replaced, so
        # a failed save puts it back, also where the file is written in
        # place (cloud folders).
        moved = []
        disk_state = self.__changedOnDisk, self.__saved_stat
        try:
            if os.path.exists(filename):
                moved.append((_move_aside(filename), filename))
            self.setFilename(filename)
            # Another program's changes to the previous file stay there
            self.__changedOnDisk, self.__saved_stat = False, None
            self.save()
        except BaseException:
            self.__changedOnDisk, self.__saved_stat = disk_state
            for aside, path in moved:
                try:
                    os.replace(aside, path)
                except OSError:
                    log_step(
                        "cannot restore %s" % path, prefix="FILE", exc=True
                    )
            raise
        for aside, _path in moved:
            try:
                _remove(aside)
            except OSError:
                # Saved already; a leftover must not fail the Save As
                log_step("cannot remove %s" % aside, prefix="FILE", exc=True)

    def merge(self, filename):
        # Merging only reads the other file, which may be open in
        # another Task Coach: take no lock on it and write nothing next
        # to it.
        merge_file = TaskFile(read_only=True)
        self.__loading = True
        try:
            merge_file.load(filename)
            merge_into(self, merge_file)
        finally:
            # Also on failure: stop its file watcher, and leave loading
            merge_file.close()
            merge_file.stop()
            self.__loading = False
        self.mark_dirty(force=True)

    def need_save(self):
        return not self.__loading and self.__needSave

    def changed_on_disk(self):
        return self.__changedOnDisk


class LockedTaskFile(TaskFile):
    """A TaskFile that holds the Task Coach lock of the file while it is
    open, so no other Task Coach can open it at the same time.

    See taskcoachlib/filesystem/resourcelock.py and
    docs/FILE_LOCKING.md.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__lock = None

    def is_locked(self):
        """Return whether this task file holds a lock."""
        return self.__lock is not None

    def acquire_lock(self, filename):
        """Lock filename. Raises resourcelock.LockInUse when another
        running Task Coach has it open."""
        lock = resourcelock.acquire(filename, "task file")
        if self.__lock is not None and self.__lock is not lock:
            self.__lock.release()
        self.__lock = lock

    def release_lock(self):
        if self.__lock is not None:
            self.__lock.release()
            self.__lock = None

    def pass_lock(self):
        """Let go of the lock without releasing it: reopening the same
        file keeps it held through the close, and load() adopts it."""
        self.__lock = None

    def close(self):
        # Released only after closing succeeded: a failed close leaves
        # the file loaded, so it must stay locked.
        super().close()
        self.release_lock()

    def holds_lock(self, lock):
        return self.__lock is lock

    def load(self, filename=None, lock=True):  # pylint: disable=W0221
        """Lock the file and keep it locked until close() is called."""
        filename = filename or self.filename()
        if lock and filename:
            self.acquire_lock(filename)
        try:
            return super().load(filename)
        except Exception:
            self.release_lock()
            raise

    def save(self, **kwargs):
        if not self.filename():
            return super().save(**kwargs)
        return self.__with_lock_of(self.filename(), super().save, **kwargs)

    def saveas(self, filename):
        # Lock the new name first: TaskFile.saveas deletes an existing
        # file there, which must not happen to a file open elsewhere.
        previous_filename = self.filename()
        try:
            return self.__with_lock_of(filename, super().saveas, filename)
        except BaseException:
            # The previous lock is kept, so keep the previous name too
            if self.filename() != previous_filename:
                self.setFilename(previous_filename)
            raise

    def __with_lock_of(self, filename, action, *args, **kwargs):
        """Run action holding the lock of filename. When that is a new
        file, the lock of the previous file is released only after the
        action succeeds."""
        previous = self.__lock
        lock = resourcelock.acquire(filename, "task file")
        if lock is previous:
            return action(*args, **kwargs)
        self.__lock = lock
        try:
            result = action(*args, **kwargs)
        except BaseException:
            self.__lock = previous
            lock.release()
            raise
        if previous is not None:
            previous.release()
        return result
