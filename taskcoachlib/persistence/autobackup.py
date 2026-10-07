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

# For xml...

import os, shutil, glob, math, re
from taskcoachlib.domain import date
from taskcoachlib.filesystem import resourcelock
from .taskfile import SafeWriteFile
from taskcoachlib import patterns
from taskcoachlib.config import settings
import bz2, hashlib

# Hack: indirect
from xml.etree import ElementTree as ET


def SHA(filename):
    return hashlib.sha1(filename.encode("UTF-8")).hexdigest()


def compressFile(src_name, dst_name):
    with open(src_name, "rb") as src:
        dst = bz2.BZ2File(dst_name, "w")
        try:
            shutil.copyfileobj(src, dst)
        finally:
            dst.close()


def backup_name(filename, saved=None):
    """The backup of the task file as saved on disk, named by when it
    was saved (its modification time, unless given) to the second: the
    Backup Manager lists the file as saved then
    (docs/PERSISTENCE_XML.md, Backups)."""
    if saved is None:
        saved = date.DateTime.fromtimestamp(os.path.getmtime(filename))
    return os.path.join(
        settings.backups_dir(),
        SHA(filename),
        saved.strftime("%Y%m%d%H%M%S.bak"),
    )


def back_up(filename, copyfile=compressFile):
    """Keep a copy of the task file as saved on disk, before it is
    overwritten; one kept already for that save stays. Whole or not at
    all: a copy cut short (disk full, killed) is not taken for one."""
    name = backup_name(filename)
    folder, base = os.path.split(name)
    os.makedirs(folder, exist_ok=True)
    if os.path.exists(name):
        return
    # Named so that no listing takes it for a backup
    temporary = os.path.join(folder, "." + base + ".tmp")
    try:
        copyfile(filename, temporary)
        os.replace(temporary, name)
    except BaseException:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise


class BackupManifest(object):
    def __init__(self):
        xml_name = os.path.join(settings.backups_dir(), "backups.xml")
        if os.path.exists(xml_name):
            with open(xml_name, "rb") as fp:
                root = ET.parse(fp).getroot()
                self.__files = dict(
                    [
                        (node.attrib["sha"], node.text)
                        for node in root.findall("file")
                    ]
                )
        else:
            self.__files = dict()

    def save(self):
        root = ET.Element("backupfiles")
        for sha, filename in list(self.__files.items()):
            node = ET.SubElement(root, "file")
            node.attrib["sha"] = sha
            node.text = filename
        with open(
            os.path.join(settings.backups_dir(), "backups.xml"),
            "wb",
        ) as fp:
            ET.ElementTree(root).write(fp)

    def listFiles(self):
        return sorted(self.__files.values())

    def listBackups(self, filename):
        backups = list()
        for name in os.listdir(self.backupPath(filename)):
            try:
                comp = list(
                    map(
                        int,
                        [
                            name[0:4],
                            name[4:6],
                            name[6:8],
                            name[8:10],
                            name[10:12],
                            name[12:14],
                        ],
                    )
                )
            except ValueError:
                continue
            backups.append(date.DateTime(*tuple(comp)))
        return list(reversed(sorted(backups)))

    def hasBackups(self, filename):
        return len(self.listBackups(filename)) != 0

    def backupPath(self, filename):
        path = os.path.join(settings.backups_dir(), SHA(filename))
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def addFile(self, filename):
        self.__files[SHA(filename)] = filename

    def restore_file(self, filename, date_time, dst_name):
        """Restore the backup of filename made at date_time as dst_name.
        dst_name is locked while it is written, so a file open in
        another Task Coach is never replaced (LockInUse); it is backed
        up first, so a restore can be restored back, and replaced only
        once the whole backup was read."""
        sha = SHA(filename)
        src = bz2.BZ2File(
            os.path.join(
                settings.backups_dir(),
                sha,
                date_time.strftime("%Y%m%d%H%M%S.bak"),
            ),
            "r",
        )
        try:
            with resourcelock.holding(dst_name, "task file"):
                if os.path.exists(dst_name):
                    back_up(dst_name)
                    self.addFile(dst_name)
                    self.save()
                dst = SafeWriteFile(dst_name)
                try:
                    shutil.copyfileobj(src, dst)
                except BaseException:
                    dst.discard()
                    raise
                dst.close()
        finally:
            src.close()


class AutoBackup(object):
    """AutoBackup creates a backup copy of the task
    file before it is overwritten. To prevent the number of backups growing
    indefinitely, AutoBackup removes older backups."""

    minNrOfBackupFiles = 3  # Keep at least three backup files.
    maxNrOfBackupFilesToRemoveAtOnce = 3  # Slowly reduce the number of backups

    def __init__(self, copyfile=compressFile):
        super().__init__()
        self.__copyfile = copyfile
        register = patterns.Publisher().registerObserver
        register(
            self.on_task_file_about_to_save, eventType="taskfile.aboutToSave"
        )
        register(self.on_task_file_read, eventType="taskfile.justRead")

    def on_task_file_read(self, event):
        for task_file in event.sources():
            self.onTaskFileRead(task_file)

    def on_task_file_about_to_save(self, event):
        for task_file in event.sources():
            self.onTaskFileAboutToSave(task_file)

    def onTaskFileRead(self, taskFile):
        """Copies old-style backups (in the same dictory as the task file) to the
        user-specific backup directory. The backup directory layout is as follows:

          <backupdir>/backups.xml          List of backups
          <backupdir>/<sha>/<datetime>.bak Backup for <datetime>. <sha> is the SHA-1
                                           hash of the task file name.

        backups.xml maps the SHA to actual file names, for enumeration in the
        GUI."""

        if not taskFile.filename():
            return

        # First add the file to the XML manifest.
        man = BackupManifest()
        man.addFile(taskFile.filename())
        man.save()

        # Then copy existing backups
        rx = re.compile(r"\.(\d{8})-(\d{6})\.tsk\.bak$")
        for name in os.listdir(os.path.split(taskFile.filename())[0] or "."):
            try:
                src_name = os.path.join(
                    os.path.split(taskFile.filename())[0], name
                )
            except UnicodeDecodeError:
                # See https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=764763
                continue

            mt = rx.search(name)
            if mt:
                dst_name = os.path.join(
                    man.backupPath(taskFile.filename()),
                    "%s%s.bak" % (mt.group(1), mt.group(2)),
                )
                if os.path.exists(dst_name):
                    os.remove(dst_name)
                with open(src_name, "rb") as src:
                    dst = bz2.BZ2File(dst_name, "w")
                    try:
                        shutil.copyfileobj(src, dst)
                    finally:
                        dst.close()
                os.remove(src_name)

    def onTaskFileAboutToSave(self, taskFile):
        """Just before a task file is about to be saved, and backups are on,
        create a backup and remove extraneous backup files."""
        if taskFile.exists():
            self.create_backup(taskFile)
            self.removeExtraneousBackupFiles(taskFile)

    def create_backup(self, taskFile):
        back_up(taskFile.filename(), self.__copyfile)

    def removeExtraneousBackupFiles(
        self, taskFile, remove=os.remove, glob=glob.glob
    ):  # pylint: disable=W0621
        backup_files = self.backupFiles(taskFile, glob)
        for _ in range(
            min(
                self.maxNrOfBackupFilesToRemoveAtOnce,
                self.numberOfExtraneousBackupFiles(backup_files),
            )
        ):
            try:
                remove(self.leastUniqueBackupFile(backup_files))
            except OSError:
                pass  # Ignore errors

    def numberOfExtraneousBackupFiles(self, backup_files):
        return max(
            0, len(backup_files) - self.maxNrOfBackupFiles(backup_files)
        )

    def maxNrOfBackupFiles(self, backup_files):
        """The maximum number of backup files we keep depends on the age of
        the oldest backup file. The older the oldest backup file (that is
        never removed), the more backup files we keep."""
        if not backup_files:
            return 0
        age = date.DateTime.now() - self.backupDateTime(backup_files[0])
        age_in_minutes = age.hours() * 60
        # We keep log(ageInMinutes) backups, but at least minNrOfBackupFiles:
        return max(
            self.minNrOfBackupFiles, int(math.log(max(1, age_in_minutes)))
        )

    def leastUniqueBackupFile(self, backup_files):
        """Find the backupFile that is closest (in time) to its neighbors,
        i.e. that is the least unique. Ignore the oldest and newest
        backups."""
        assert len(backup_files) > self.minNrOfBackupFiles
        deltas = []
        for index in range(1, len(backup_files) - 1):
            delta = self.backupDateTime(
                backup_files[index + 1]
            ) - self.backupDateTime(backup_files[index - 1])
            deltas.append((delta, backup_files[index]))
        deltas.sort()
        return deltas[0][1]

    def backupFiles(self, taskFile, glob=glob.glob):  # pylint: disable=W0621
        sha = SHA(taskFile.filename())
        root = os.path.join(settings.backups_dir(), sha)
        return sorted(glob("%s.bak" % os.path.join(root, "[0-9]" * 14)))

    @staticmethod
    def backupDateTime(backup_filename):
        """Parse the date and time from the filename and return a DateTime
        instance."""
        dt = os.path.split(backup_filename)[-1][:-4]
        parts = (
            int(part)
            for part in (
                dt[0:4],
                dt[4:6],
                dt[6:8],
                dt[8:10],
                dt[10:12],
                dt[12:14],
            )
        )
        return date.DateTime(*parts)  # pylint: disable=W0142
