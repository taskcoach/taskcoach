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
import lockfile
from . import xml
from taskcoachlib import patterns, operating_system
from taskcoachlib.domain import base, task, category, note, effort, attachment
from taskcoachlib.syncml.config import createDefaultSyncConfig
from taskcoachlib.thirdparty.guid import generate
from taskcoachlib.changes import ChangeMonitor, ChangeSynchronizer
from taskcoachlib.filesystem import (
    FilesystemNotifier,
    FilesystemPollerNotifier,
)
from pubsub import pub


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

    def onFileChanged(self):
        self.__taskFile.onFileChanged()


class TaskCoachFilesystemPollerNotifier(FilesystemPollerNotifier):
    def __init__(self, taskFile):
        self.__taskFile = taskFile
        super().__init__()

    def onFileChanged(self):
        self.__taskFile.onFileChanged()


class SafeWriteFile(object):
    def __init__(self, filename):
        self.__filename = filename
        if self._isCloud():
            # Ideally we should create a temporary file on the same filesystem (so that
            # os.rename works) but outside the Dropbox folder...
            self.__fd = open(self.__filename, "wb")
        else:
            self.__tempFilename = self._getTemporaryFileName(
                os.path.dirname(filename)
            )
            self.__fd = open(self.__tempFilename, "wb")

    def write(self, bf):
        self.__fd.write(bf)

    def close(self):
        self.__fd.close()
        if not self._isCloud():
            if os.path.exists(self.__filename):
                os.remove(self.__filename)
            if self.__filename is not None:
                if os.path.exists(self.__filename):
                    # WTF ?
                    self.__moveFileOutOfTheWay(self.__filename)
                os.rename(self.__tempFilename, self.__filename)

    def __moveFileOutOfTheWay(self, filename):
        index = 1
        while True:
            name, ext = os.path.splitext(filename)
            newName = "%s (%d)%s" % (name, index, ext)
            if not os.path.exists(newName):
                os.rename(filename, newName)
                break
            index += 1

    def _getTemporaryFileName(self, path):
        """All functions/classes in the standard library that can generate
        a temporary file, visible on the file system, without deleting it
        when closed are deprecated (there is tempfile.NamedTemporaryFile
        but its 'delete' argument is new in Python 2.6). This is not
        secure, not thread-safe, but it works."""

        idx = 0
        while True:
            name = os.path.join(path, "tmp-%d" % idx)
            if not os.path.exists(name):
                return name
            idx += 1

    def _isCloud(self):
        return _isCloud(os.path.dirname(self.__filename))


class TaskFile(patterns.Observer):
    def __init__(self, *args, **kwargs):
        self.__filename = self.__lastFilename = ""
        self.__needSave = self.__loading = False
        self.__tasks = task.TaskList()
        self.__categories = category.CategoryList()
        self.__notes = note.NoteContainer()
        self.__efforts = effort.EffortList(self.tasks())
        self.__guid = generate()
        self.__syncMLConfig = createDefaultSyncConfig(self.__guid)
        self.__monitor = ChangeMonitor()
        self.__changes = dict()
        self.__changes[self.__monitor.guid()] = self.__monitor
        self.__changedOnDisk = False
        if kwargs.pop("poll", True):
            self.__notifier = TaskCoachFilesystemPollerNotifier(self)
        else:
            self.__notifier = TaskCoachFilesystemNotifier(self)
        self.__saving = False
        for collection in [self.__tasks, self.__categories, self.__notes]:
            self.__monitor.monitorCollection(collection)
        for domainClass in [
            task.Task,
            category.Category,
            note.Note,
            effort.Effort,
            attachment.FileAttachment,
            attachment.URIAttachment,
            attachment.MailAttachment,
        ]:
            self.__monitor.monitorClass(domainClass)
        super().__init__(*args, **kwargs)
        # Register for tasks, categories, efforts and notes being changed so we
        # can monitor when the task file needs saving (i.e. is 'dirty'):
        for container in self.tasks(), self.categories(), self.notes():
            for eventType in container.modificationEventTypes():
                self.registerObserver(
                    self.onDomainObjectAddedOrRemoved,
                    eventType,
                    eventSource=container,
                )

        for eventType in (
            base.Object.markDeletedEventType(),
            base.Object.markNotDeletedEventType(),
        ):
            self.registerObserver(self.onDomainObjectAddedOrRemoved, eventType)

        for eventType in task.Task.modificationEventTypes():
            if not eventType.startswith("pubsub"):
                self.registerObserver(self.onTaskChanged_Deprecated, eventType)
        pub.subscribe(self.onTaskChanged, "pubsub.task")
        for eventType in effort.Effort.modificationEventTypes():
            self.registerObserver(self.onEffortChanged, eventType)
        for eventType in note.Note.modificationEventTypes():
            if not eventType.startswith("pubsub"):
                self.registerObserver(self.onNoteChanged_Deprecated, eventType)
        pub.subscribe(self.onNoteChanged, "pubsub.note")
        for eventType in category.Category.modificationEventTypes():
            if not eventType.startswith("pubsub"):
                self.registerObserver(
                    self.onCategoryChanged_Deprecated, eventType
                )
        pub.subscribe(self.onCategoryChanged, "pubsub.category")
        for eventType in (
            attachment.FileAttachment.modificationEventTypes()
            + attachment.URIAttachment.modificationEventTypes()
            + attachment.MailAttachment.modificationEventTypes()
        ):
            if not eventType.startswith("pubsub"):
                self.registerObserver(
                    self.onAttachmentChanged_Deprecated, eventType
                )
        pub.subscribe(self.onAttachmentChanged, "pubsub.attachment")

    def __str__(self):
        return self.filename()

    def __contains__(self, item):
        return (
            item in self.tasks()
            or item in self.notes()
            or item in self.categories()
            or item in self.efforts()
        )

    def monitor(self):
        return self.__monitor

    def categories(self):
        return self.__categories

    def notes(self):
        return self.__notes

    def tasks(self):
        return self.__tasks

    def efforts(self):
        return self.__efforts

    def syncMLConfig(self):
        return self.__syncMLConfig

    def guid(self):
        return self.__guid

    def changes(self):
        return self.__changes

    def setSyncMLConfig(self, config):
        self.__syncMLConfig = config
        self.markDirty()

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
        self.markDirty()

    def onTaskChanged(self, newValue, sender):
        if self.__loading or self.__saving:
            return
        if sender in self.tasks():
            self.markDirty()

    def onTaskChanged_Deprecated(self, event):
        if self.__loading:
            return
        changedTasks = [
            changedTask
            for changedTask in event.sources()
            if changedTask in self.tasks()
        ]
        if changedTasks:
            self.markDirty()
            for changedTask in changedTasks:
                changedTask.markDirty()

    def onEffortChanged(self, event):
        if self.__loading or self.__saving:
            return
        changedEfforts = [
            changedEffort
            for changedEffort in event.sources()
            if changedEffort.task() in self.tasks()
        ]
        if changedEfforts:
            self.markDirty()
            for changedEffort in changedEfforts:
                changedEffort.markDirty()

    def onCategoryChanged_Deprecated(self, event):
        if self.__loading or self.__saving:
            return
        changedCategories = [
            changedCategory
            for changedCategory in event.sources()
            if changedCategory in self.categories()
        ]
        if changedCategories:
            self.markDirty()
            # Mark all categorizables belonging to the changed category dirty;
            # this is needed because in SyncML/vcard world, categories are not
            # first-class objects. Instead, each task/contact/etc has a
            # categories property which is a comma-separated list of category
            # names. So, when a category name changes, every associated
            # categorizable changes.
            for changedCategory in changedCategories:
                for categorizable in changedCategory.categorizables():
                    categorizable.markDirty()

    def onCategoryChanged(self, newValue, sender):
        if self.__loading or self.__saving:
            return
        changedCategories = [
            changedCategory
            for changedCategory in [sender]
            if changedCategory in self.categories()
        ]
        if changedCategories:
            self.markDirty()
            # Mark all categorizables belonging to the changed category dirty;
            # this is needed because in SyncML/vcard world, categories are not
            # first-class objects. Instead, each task/contact/etc has a
            # categories property which is a comma-separated list of category
            # names. So, when a category name changes, every associated
            # categorizable changes.
            for changedCategory in changedCategories:
                for categorizable in changedCategory.categorizables():
                    categorizable.markDirty()

    def onNoteChanged_Deprecated(self, event):
        if self.__loading:
            return
        # A note may be in self.notes() or it may be a note of another
        # domain object.
        self.markDirty()
        for changedNote in event.sources():
            changedNote.markDirty()

    def onNoteChanged(self, newValue, sender):
        if self.__loading:
            return
        # A note may be in self.notes() or it may be a note of another
        # domain object.
        self.markDirty()
        sender.markDirty()

    def onAttachmentChanged(self, newValue, sender):
        if self.__loading or self.__saving:
            return
        # Attachments don't know their owner, so we can't check whether the
        # attachment is actually in the task file. Assume it is.
        self.markDirty()

    def onAttachmentChanged_Deprecated(self, event):
        if self.__loading:
            return
        # Attachments don't know their owner, so we can't check whether the
        # attachment is actually in the task file. Assume it is.
        self.markDirty()
        for changedAttachment in event.sources():
            changedAttachment.markDirty()

    def setFilename(self, filename):
        if filename == self.__filename:
            return
        self.__lastFilename = filename or self.__filename
        self.__filename = filename
        self.__notifier.setFilename(filename)
        pub.sendMessage("taskfile.filenameChanged", filename=filename)

    def filename(self):
        return self.__filename

    def lastFilename(self):
        return self.__lastFilename

    def isDirty(self):
        return self.__needSave

    def markDirty(self, force=False):
        if force or not self.__needSave:
            self.__needSave = True
            pub.sendMessage("taskfile.dirty", taskFile=self)

    def markClean(self):
        if self.__needSave:
            self.__needSave = False
            pub.sendMessage("taskfile.clean", taskFile=self)

    def onFileChanged(self):
        if not self.__saving:
            import wx  # Not really clean but we're in another thread...

            self.__changedOnDisk = True
            wx.CallAfter(pub.sendMessage, "taskfile.changed", taskFile=self)

    @patterns.eventSource
    def clear(self, regenerate=True, event=None):
        pub.sendMessage("taskfile.aboutToClear", taskFile=self)
        try:
            self.tasks().clear(event=event)
            self.categories().clear(event=event)
            self.notes().clear(event=event)
            if regenerate:
                self.__guid = generate()
                self.__syncMLConfig = createDefaultSyncConfig(self.__guid)
        finally:
            pub.sendMessage("taskfile.justCleared", taskFile=self)

    def close(self):
        if os.path.exists(self.filename()):
            changes = xml.ChangesXMLReader(self.filename() + ".delta").read()
            del changes[self.__monitor.guid()]
            xml.ChangesXMLWriter(open(self.filename() + ".delta", "wb")).write(
                changes
            )

        self.setFilename("")
        self.__guid = generate()
        self.clear()
        self.__monitor.reset()
        self.markClean()
        self.__changedOnDisk = False

    def stop(self):
        self.__notifier.stop()

    def _read(self, fd):
        return xml.XMLReader(fd).read()

    def exists(self):
        return os.path.isfile(self.__filename)

    def _openForWrite(self, suffix=""):
        return SafeWriteFile(self.__filename + suffix)

    def _openForRead(self):
        return open(self.__filename, "r")

    def load(self, filename=None):
        pub.sendMessage("taskfile.aboutToRead", taskFile=self)
        self.__loading = True
        if filename:
            self.setFilename(filename)
        try:
            if self.exists():
                fd = self._openForRead()
                try:
                    tasks, categories, notes, syncMLConfig, changes, guid = (
                        self._read(fd)
                    )
                finally:
                    fd.close()
            else:
                tasks = []
                categories = []
                notes = []
                changes = dict()
                guid = generate()
                syncMLConfig = createDefaultSyncConfig(guid)
            self.clear()
            self.__monitor.reset()
            self.__changes = changes
            self.__changes[self.__monitor.guid()] = self.__monitor
            self.categories().extend(categories)
            self.tasks().extend(tasks)
            self.notes().extend(notes)

            def registerOtherObjects(objects):
                for obj in objects:
                    if isinstance(obj, base.CompositeObject):
                        registerOtherObjects(obj.children())
                    if isinstance(obj, note.NoteOwner):
                        registerOtherObjects(obj.notes())
                    if isinstance(obj, attachment.AttachmentOwner):
                        registerOtherObjects(obj.attachments())
                    if isinstance(obj, task.Task):
                        registerOtherObjects(obj.efforts())
                    if (
                        isinstance(obj, note.Note)
                        or isinstance(obj, attachment.Attachment)
                        or isinstance(obj, effort.Effort)
                    ):
                        self.__monitor.setChanges(obj.id(), set())

            registerOtherObjects(self.categories().rootItems())
            registerOtherObjects(self.tasks().rootItems())
            registerOtherObjects(self.notes().rootItems())
            self.__monitor.resetAllChanges()
            self.__syncMLConfig = syncMLConfig
            self.__guid = guid

            if os.path.exists(self.filename()):
                # We need to reset the changes on disk because we're up to date.
                xml.ChangesXMLWriter(
                    open(self.filename() + ".delta", "wb")
                ).write(self.__changes)
        except Exception:
            self.setFilename("")
            raise
        finally:
            self.__loading = False
            self.markClean()
            self.__changedOnDisk = False
            pub.sendMessage("taskfile.justRead", taskFile=self)

    def save(self):
        try:
            pub.sendMessage("taskfile.aboutToSave", taskFile=self)
        except Exception:
            pass  # Ignore errors from subscribers
        # When encountering a problem while saving (disk full,
        # computer on fire), if we were writing directly to the file,
        # it's lost. So write to a temporary file and rename it if
        # everything went OK.
        self.__saving = True
        try:
            self.mergeDiskChanges()

            if self.__needSave or not os.path.exists(self.__filename):
                fd = self._openForWrite()
                try:
                    xml.XMLWriter(fd).write(
                        self.tasks(),
                        self.categories(),
                        self.notes(),
                        self.syncMLConfig(),
                        self.guid(),
                    )
                finally:
                    fd.close()

            self.markClean()
        finally:
            self.__saving = False
            self.__notifier.saved()
            try:
                pub.sendMessage("taskfile.justSaved", taskFile=self)
            except Exception:
                pass  # Ignore errors from subscribers

    def mergeDiskChanges(self):
        self.__loading = True
        try:
            if os.path.exists(
                self.__filename
            ):  # Not using self.exists() because DummyFile.exists returns True
                # Instead of writing the content of memory, merge changes
                # with the on-disk version and save the result.
                self.__monitor.freeze()
                try:
                    fd = self._openForRead()
                    (
                        tasks,
                        categories,
                        notes,
                        syncMLConfig,
                        allChanges,
                        guid,
                    ) = self._read(fd)
                    fd.close()

                    self.__changes = allChanges

                    if self.__saving:
                        for devGUID, changes in list(self.__changes.items()):
                            if devGUID != self.__monitor.guid():
                                changes.merge(self.__monitor)

                    sync = ChangeSynchronizer(self.__monitor, allChanges)

                    sync.sync(
                        [
                            (
                                self.categories(),
                                category.CategoryList(categories),
                            ),
                            (self.tasks(), task.TaskList(tasks)),
                            (self.notes(), note.NoteContainer(notes)),
                        ]
                    )

                    self.__changes[self.__monitor.guid()] = self.__monitor
                finally:
                    self.__monitor.thaw()
            else:
                self.__changes = {self.__monitor.guid(): self.__monitor}

            self.__monitor.resetAllChanges()
            fd = self._openForWrite(".delta")
            try:
                xml.ChangesXMLWriter(fd).write(self.changes())
            finally:
                fd.close()

            self.__changedOnDisk = False
        finally:
            self.__loading = False

    def saveas(self, filename):
        if os.path.exists(filename):
            os.remove(filename)
        if os.path.exists(filename + ".delta"):
            os.remove(filename + ".delta")
        self.setFilename(filename)
        self.save()

    def merge(self, filename):
        mergeFile = self.__class__()
        mergeFile.load(filename)
        self.__loading = True
        categoryMap = dict()
        self.tasks().removeItems(
            self.objectsToOverwrite(self.tasks(), mergeFile.tasks())
        )
        self.rememberCategoryLinks(categoryMap, self.tasks())
        self.tasks().extend(mergeFile.tasks().rootItems())
        self.notes().removeItems(
            self.objectsToOverwrite(self.notes(), mergeFile.notes())
        )
        self.rememberCategoryLinks(categoryMap, self.notes())
        self.notes().extend(mergeFile.notes().rootItems())
        self.categories().removeItems(
            self.objectsToOverwrite(self.categories(), mergeFile.categories())
        )
        self.categories().extend(mergeFile.categories().rootItems())
        self.restoreCategoryLinks(categoryMap)
        mergeFile.close()
        self.__loading = False
        self.markDirty(force=True)

    def objectsToOverwrite(self, originalObjects, objectsToMerge):
        objectsToOverwrite = []
        for domainObject in objectsToMerge:
            try:
                objectsToOverwrite.append(
                    originalObjects.getObjectById(domainObject.id())
                )
            except IndexError:
                pass
        return objectsToOverwrite

    def rememberCategoryLinks(self, categoryMap, categorizables):
        for categorizable in categorizables:
            for categoryToLinkLater in categorizable.categories():
                categoryMap.setdefault(categoryToLinkLater.id(), []).append(
                    categorizable
                )

    def restoreCategoryLinks(self, categoryMap):
        categories = self.categories()
        for categoryId, categorizables in categoryMap.items():
            try:
                categoryToLink = categories.getObjectById(categoryId)
            except IndexError:
                continue  # Subcategory was removed by the merge
            for categorizable in categorizables:
                categorizable.addCategory(categoryToLink)
                categoryToLink.addCategorizable(categorizable)

    def needSave(self):
        return not self.__loading and self.__needSave

    def changedOnDisk(self):
        return self.__changedOnDisk

    def beginSync(self):
        self.__loading = True

    def endSync(self):
        self.__loading = False
        self.markDirty()


class DummyLockFile(object):
    def acquire(self, timeout=None):
        pass

    def release(self):
        pass

    def is_locked(self):
        return True

    def i_am_locking(self):
        return True

    def break_lock(self):
        pass


class LockedTaskFile(TaskFile):
    """LockedTaskFile adds cooperative locking to the TaskFile."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__lock = None

    def __isFuse(self, path):
        if operating_system.isGTK() and os.path.exists("/proc/mounts"):
            for line in open("/proc/mounts", "r", encoding="utf-8"):
                try:
                    location, mountPoint, fsType, options, a, b = (
                        line.strip().split()
                    )
                except ValueError:
                    pass  # Skip malformed mount lines
                if os.path.abspath(path).startswith(
                    mountPoint
                ) and fsType.startswith("fuse."):
                    return True
        return False

    def __isCloud(self, filename):
        return _isCloud(os.path.dirname(filename))

    def __createLockFile(self, filename):
        if operating_system.isWindows() and self.__isCloud(filename):
            return DummyLockFile()
        if self.__isFuse(filename):
            return lockfile.MkdirFileLock(filename)
        return lockfile.FileLock(filename)

    def is_locked(self):
        return self.__lock and self.__lock.is_locked()

    def is_locked_by_me(self):
        return self.is_locked() and self.__lock.i_am_locking()

    def release_lock(self):
        if self.is_locked_by_me():
            self.__lock.release()

    def acquire_lock(self, filename):
        if not self.is_locked_by_me():
            self.__lock = self.__createLockFile(filename)
            self.__lock.acquire(5)

    def break_lock(self, filename):
        self.__lock = self.__createLockFile(filename)
        self.__lock.break_lock()

    def close(self):
        if self.filename() and os.path.exists(self.filename()):
            self.acquire_lock(self.filename())
        try:
            super().close()
        finally:
            self.release_lock()

    def load(
        self, filename=None, lock=True, breakLock=False
    ):  # pylint: disable=W0221
        """Lock the file before we load, if not already locked."""
        filename = filename or self.filename()
        try:
            if lock and filename:
                if breakLock:
                    self.break_lock(filename)
                self.acquire_lock(filename)
            return super().load(filename)
        finally:
            self.release_lock()

    def save(self, **kwargs):
        """Lock the file before we save, if not already locked."""
        self.acquire_lock(self.filename())
        try:
            return super().save(**kwargs)
        finally:
            self.release_lock()

    def mergeDiskChanges(self):
        self.acquire_lock(self.filename())
        try:
            super().mergeDiskChanges()
        finally:
            self.release_lock()
