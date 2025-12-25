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
from pubsub import pub
import bz2, hashlib

# Hack: indirect
from xml.etree import ElementTree as ET


def SHA(filename):
    return hashlib.sha1(filename.encode("UTF-8")).hexdigest()


def compressFile(srcName, dstName):
    with open(srcName, "rb") as src:
        dst = bz2.BZ2File(dstName, "w")
        try:
            shutil.copyfileobj(src, dst)
        finally:
            dst.close()


class BackupManifest(object):
    def __init__(self, settings):
        self.__settings = settings

        xmlName = os.path.join(settings.pathToBackupsDir(), "backups.xml")
        if os.path.exists(xmlName):
            with open(xmlName, "rb") as fp:
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
            os.path.join(self.__settings.pathToBackupsDir(), "backups.xml"),
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
        path = os.path.join(self.__settings.pathToBackupsDir(), SHA(filename))
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def addFile(self, filename):
        self.__files[SHA(filename)] = filename

    def removeFile(self, filename):
        sha = SHA(filename)
        if sha in self.__files:
            del self.__files[sha]

    def restoreFile(self, filename, dateTime, dstName):
        if os.path.exists(dstName):
            os.remove(dstName)
        sha = SHA(filename)
        src = bz2.BZ2File(
            os.path.join(
                self.__settings.pathToBackupsDir(),
                sha,
                dateTime.strftime("%Y%m%d%H%M%S.bak"),
            ),
            "r",
        )
        try:
            with open(dstName, "wb") as dst:
                shutil.copyfileobj(src, dst)
        finally:
            src.close()


class AutoBackup(object):
    """AutoBackup creates a backup copy of the task
    file before it is overwritten. To prevent the number of backups growing
    indefinitely, AutoBackup removes older backups."""

    minNrOfBackupFiles = 3  # Keep at least three backup files.
    maxNrOfBackupFilesToRemoveAtOnce = 3  # Slowly reduce the number of backups

    def __init__(self, settings, copyfile=compressFile):
        super().__init__()
        self.__settings = settings
        self.__copyfile = copyfile
        pub.subscribe(self.onTaskFileAboutToSave, "taskfile.aboutToSave")
        pub.subscribe(self.onTaskFileRead, "taskfile.justRead")

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
        man = BackupManifest(self.__settings)
        man.addFile(taskFile.filename())
        man.save()

        # Then copy existing backups
        rx = re.compile(r"\.(\d{8})-(\d{6})\.tsk\.bak$")
        for name in os.listdir(os.path.split(taskFile.filename())[0] or "."):
            try:
                srcName = os.path.join(
                    os.path.split(taskFile.filename())[0], name
                )
            except UnicodeDecodeError:
                # See https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=764763
                continue

            mt = rx.search(name)
            if mt:
                dstName = os.path.join(
                    man.backupPath(taskFile.filename()),
                    "%s%s.bak" % (mt.group(1), mt.group(2)),
                )
                if os.path.exists(dstName):
                    os.remove(dstName)
                with open(srcName, "rb") as src:
                    dst = bz2.BZ2File(dstName, "w")
                    try:
                        shutil.copyfileobj(src, dst)
                    finally:
                        dst.close()
                os.remove(srcName)

    def onTaskFileAboutToSave(self, taskFile):
        """Just before a task file is about to be saved, and backups are on,
        create a backup and remove extraneous backup files."""
        if taskFile.exists():
            self.createBackup(taskFile)
            self.removeExtraneousBackupFiles(taskFile)

    def createBackup(self, taskFile):
        filename = self.backupFilename(taskFile)
        path = os.path.dirname(filename)
        if not os.path.exists(path):
            os.makedirs(path)
        self.__copyfile(taskFile.filename(), filename)

    def removeExtraneousBackupFiles(
        self, taskFile, remove=os.remove, glob=glob.glob
    ):  # pylint: disable=W0621
        backupFiles = self.backupFiles(taskFile, glob)
        for _ in range(
            min(
                self.maxNrOfBackupFilesToRemoveAtOnce,
                self.numberOfExtraneousBackupFiles(backupFiles),
            )
        ):
            try:
                remove(self.leastUniqueBackupFile(backupFiles))
            except OSError:
                pass  # Ignore errors

    def numberOfExtraneousBackupFiles(self, backupFiles):
        return max(0, len(backupFiles) - self.maxNrOfBackupFiles(backupFiles))

    def maxNrOfBackupFiles(self, backupFiles):
        """The maximum number of backup files we keep depends on the age of
        the oldest backup file. The older the oldest backup file (that is
        never removed), the more backup files we keep."""
        if not backupFiles:
            return 0
        age = date.DateTime.now() - self.backupDateTime(backupFiles[0])
        ageInMinutes = age.hours() * 60
        # We keep log(ageInMinutes) backups, but at least minNrOfBackupFiles:
        return max(
            self.minNrOfBackupFiles, int(math.log(max(1, ageInMinutes)))
        )

    def leastUniqueBackupFile(self, backupFiles):
        """Find the backupFile that is closest (in time) to its neighbors,
        i.e. that is the least unique. Ignore the oldest and newest
        backups."""
        assert len(backupFiles) > self.minNrOfBackupFiles
        deltas = []
        for index in range(1, len(backupFiles) - 1):
            delta = self.backupDateTime(
                backupFiles[index + 1]
            ) - self.backupDateTime(backupFiles[index - 1])
            deltas.append((delta, backupFiles[index]))
        deltas.sort()
        return deltas[0][1]

    def backupFiles(self, taskFile, glob=glob.glob):  # pylint: disable=W0621
        sha = SHA(taskFile.filename())
        root = os.path.join(self.__settings.pathToBackupsDir(), sha)
        return sorted(glob("%s.bak" % os.path.join(root, "[0-9]" * 14)))

    def backupFilename(self, taskFile, now=date.DateTime.now):
        """Generate a backup filename for the specified date/time."""
        sha = SHA(taskFile.filename())
        return os.path.join(
            self.__settings.pathToBackupsDir(),
            sha,
            now().strftime("%Y%m%d%H%M%S.bak"),
        )

    @staticmethod
    def backupDateTime(backupFilename):
        """Parse the date and time from the filename and return a DateTime
        instance."""
        dt = os.path.split(backupFilename)[-1][:-4]
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
