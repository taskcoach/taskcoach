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

import bz2
import os
import shutil
import tempfile
import test
from taskcoachlib import persistence, config
from taskcoachlib.persistence import autobackup
from taskcoachlib.domain import date, task
from taskcoachlib.filesystem import resourcelock


class DummyFile(object):
    encoding = "utf-8"
    name = "whatever.tsk"

    def close(self, *args, **kwargs):  # pylint: disable=W0613
        pass

    def write(self, *args, **kwargs):  # pylint: disable=W0613
        pass


class DummyTaskFile(persistence.TaskFile):
    def _openForRead(self, *args, **kwargs):  # pylint: disable=W0613
        return DummyFile()

    def _openForWrite(self, *args, **kwargs):  # pylint: disable=W0613
        return DummyFile()

    def _read(self, *args, **kwargs):  # pylint: disable=W0613
        content = [task.Task()], [], []
        return content, []  # No duplicate ids

    def exists(self):
        return True

    def filename(self):
        return super().filename() or "whatever.tsk"


def remove_test_data():
    """Remove the data folder LocalSettings creates."""
    shutil.rmtree(os.path.join(os.getcwd(), "testdata"), ignore_errors=True)


class LocalSettings(config.Settings):
    def __init__(self, *args, **kwargs):
        self.__path = os.path.join(os.getcwd(), "testdata")
        if os.path.exists(self.__path):
            shutil.rmtree(self.__path)
        os.mkdir(self.__path)
        super().__init__(*args, **kwargs)

    def _pathToDataDir(self, *args, **kwargs):
        return self.__path, False

    def _pathToTemplatesDir(self):
        # Existing, so migrateConfigurationFiles() leaves the user's own
        # templates folder where it is
        return self.__path, True


class AutoBackupTest(test.TestCase):
    # pylint: disable=E1101,E1002,W0232
    def setUp(self):
        super().setUp()
        # Backups in the test's folder; the harness puts its settings
        # back after the test
        self.settings = LocalSettings(load=False)
        config.settings.use(self.settings)
        self.taskFile = DummyTaskFile()
        self.backup = persistence.AutoBackup(copyfile=self.on_copy_file)
        self.copy_called = False

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()
        if os.path.exists("test.tsk"):
            os.remove("test.tsk")
        remove_test_data()

    def on_copy_file(self, source, destination):  # pylint: disable=W0613
        self.copy_called = True
        open(destination, "wb").close()

    def one_backup_file(self):
        return [
            autobackup.backup_name(
                self.taskFile.filename(), date.DateTime.now()
            )
        ]

    def four_backup_files(self):
        files = [
            autobackup.backup_name(
                self.taskFile.filename(), date.DateTime.now()
            ),
            autobackup.backup_name(
                self.taskFile.filename(), date.DateTime(2001, 1, 1, 1, 1, 1)
            ),
            autobackup.backup_name(
                self.taskFile.filename(), date.DateTime(2002, 1, 1, 1, 1, 1)
            ),
            autobackup.backup_name(
                self.taskFile.filename(), date.DateTime(2000, 1, 1, 1, 1, 1)
            ),
        ]
        files.sort()
        return files

    def five_backup_files(self):
        files = [
            autobackup.backup_name(
                self.taskFile.filename(), date.DateTime.now()
            ),
            autobackup.backup_name(
                self.taskFile.filename(), date.DateTime(2001, 1, 1, 1, 1, 1)
            ),
            autobackup.backup_name(
                self.taskFile.filename(), date.DateTime(2002, 1, 1, 1, 1, 1)
            ),
            autobackup.backup_name(
                self.taskFile.filename(), date.DateTime(2002, 1, 1, 1, 1, 2)
            ),
            autobackup.backup_name(
                self.taskFile.filename(), date.DateTime(2000, 1, 1, 1, 1, 1)
            ),
        ]
        files.sort()
        return files

    def globMany(self, pattern):  # pylint: disable=W0613
        return self.many_backup_files()

    def many_backup_files(self):
        files = [
            autobackup.backup_name(
                self.taskFile.filename(), date.DateTime.now()
            )
        ] * 100 + [
            autobackup.backup_name(
                self.taskFile.filename(), date.DateTime(2000, 1, 1, 1, 1, 1)
            )
        ]
        files.sort()
        return files

    def test_backup_migration_manifest(self):
        self.taskFile.setFilename("test.tsk")
        self.backup.onTaskFileRead(self.taskFile)
        with open(
            os.path.join(self.settings.pathToBackupsDir(), "backups.xml"), "rb"
        ) as fp:
            content = fp.read()
        self.assertEqual(
            content,
            b"<backupfiles><file "
            b'sha="13cf6835565aaf4ab1f78e922b9917f9a4c7a856">'
            b"test.tsk</file></backupfiles>",
        )

    def test_backup_migration(self):
        self.taskFile.setFilename("test.tsk")
        with open("test.20140715-010203.tsk.bak", "wb") as fp:
            fp.write(b"Hello, world")
        self.backup.onTaskFileRead(self.taskFile)
        self.assertFalse(os.path.exists("test.20140715-010203.tsk.bak"))

        backup_name = os.path.join(
            self.settings.pathToBackupsDir(),
            "13cf6835565aaf4ab1f78e922b9917f9a4c7a856",
            "20140715010203.bak",
        )
        self.assertTrue(os.path.exists(backup_name))
        self.assertEqual(bz2.BZ2File(backup_name).read(), b"Hello, world")

    def test_no_backup_files(self):
        self.assertEqual(
            [], self.backup.backupFiles(self.taskFile, glob=lambda pattern: [])
        )

    def test_one_backup_file(self):
        self.assertEqual(
            ["1"],
            self.backup.backupFiles(self.taskFile, glob=lambda pattern: ["1"]),
        )

    def test_not_too_many_backup_files(self):
        self.assertEqual(
            0,
            self.backup.numberOfExtraneousBackupFiles(self.one_backup_file()),
        )

    def test_too_many_backup_files_(self):
        self.assertEqual(
            85,
            self.backup.numberOfExtraneousBackupFiles(
                self.many_backup_files()
            ),
        )

    def test_remove_extraneous_back_files(self):
        self.backup.maxNrOfBackupFilesToRemoveAtOnce = 100
        removed_files = []

        def remove(filename):
            removed_files.append(filename)

        self.backup.removeExtraneousBackupFiles(
            self.taskFile, remove=remove, glob=self.globMany
        )
        self.assertEqual(85, len(removed_files))

    def test_remove_extraneous_back_files_os_error(self):
        def remove(filename):  # pylint: disable=W0613
            raise OSError

        self.backup.removeExtraneousBackupFiles(
            self.taskFile, remove=remove, glob=self.globMany
        )

    def test_backup_filename(self):
        now = date.DateTime(2004, 1, 1)
        self.assertEqual(
            os.path.join(
                self.settings.pathToBackupsDir(),
                "c81e25c3e04922232ab8eb87be8337c806a44209",
                "20040101000000.bak",
            ),
            autobackup.backup_name(self.taskFile.filename(), now),
        )  # pylint: disable=W0212

    def test_a_backup_is_named_by_when_the_file_was_saved(self):
        # Its contents are the file as saved then
        # (docs/PERSISTENCE_XML.md)
        self.taskFile.setFilename("test.tsk")
        with open("test.tsk", "w") as task_file:
            task_file.write("saved")
        saved = date.DateTime(2026, 9, 1, 12, 34, 56)
        os.utime("test.tsk", (saved.timestamp(), saved.timestamp()))
        self.assertTrue(
            autobackup.backup_name(self.taskFile.filename()).endswith(
                "20260901123456.bak"
            )
        )

    def test_create_backup_on_save(self):
        self.taskFile.setFilename("test.tsk")
        with open("test.tsk", "w") as task_file:
            task_file.write("saved")
        self.taskFile.tasks().append(task.Task())
        self.taskFile.save()
        self.assertTrue(self.copy_called)

    def test_dont_create_backup_on_open(self):
        self.taskFile.load()
        self.assertFalse(self.copy_called)

    def test_dont_create_backup_when_setting_filename(self):
        self.taskFile.setFilename("newname.tsk")
        self.assertFalse(self.copy_called)

    def test_least_unique_backup_file_four_backup_files(self):
        self.assertEqual(
            autobackup.backup_name(
                self.taskFile.filename(), date.DateTime(2001, 1, 1, 1, 1, 1)
            ),
            self.backup.leastUniqueBackupFile(self.four_backup_files()),
        )

    def test_least_unique_backup_file_five_backup_files(self):
        self.assertEqual(
            autobackup.backup_name(
                self.taskFile.filename(), date.DateTime(2002, 1, 1, 1, 1, 1)
            ),
            self.backup.leastUniqueBackupFile(self.five_backup_files()),
        )


class RestoreBackupTest(test.TestCase):
    def setUp(self):
        super().setUp()
        self.directory = tempfile.mkdtemp()
        self.filename = os.path.join(self.directory, "tasks.tsk")
        self.write(self.filename, b"current")
        config.settings.use(LocalSettings(load=False))
        self.manifest = persistence.BackupManifest()
        self.backup_time = date.DateTime(2026, 9, 1, 12, 0, 0)
        self.backup = os.path.join(
            self.manifest.backupPath(self.filename),
            self.backup_time.strftime("%Y%m%d%H%M%S.bak"),
        )
        with bz2.BZ2File(self.backup, "w") as backup:
            backup.write(b"backup")

    def tearDown(self):
        shutil.rmtree(self.directory)
        remove_test_data()
        super().tearDown()

    @staticmethod
    def write(filename, content):
        with open(filename, "wb") as output:
            output.write(content)

    def content(self):
        with open(self.filename, "rb") as restored:
            return restored.read()

    def restore(self):
        self.manifest.restore_file(
            self.filename, self.backup_time, self.filename
        )

    def test_restore_keeps_the_replaced_file_as_a_backup(self):
        # A wrong restore can be restored back: no save is lost
        saved = date.DateTime(2026, 10, 6, 23, 4, 25)
        os.utime(self.filename, (saved.timestamp(), saved.timestamp()))
        self.restore()
        self.assertIn(saved, self.manifest.listBackups(self.filename))
        kept_name = autobackup.backup_name(self.filename, saved)
        with bz2.BZ2File(kept_name) as kept:
            self.assertEqual(b"current", kept.read())

    def test_a_restore_that_cannot_keep_the_replaced_file_keeps_it(self):
        def fail(filename):
            raise OSError("disk full")

        original = autobackup.back_up
        autobackup.back_up = fail
        self.addCleanup(setattr, autobackup, "back_up", original)
        with self.assertRaises(OSError):
            self.restore()
        self.assertEqual(b"current", self.content())

    def test_a_backup_cut_short_is_made_again(self):
        def cut_short(source, destination):
            with open(destination, "wb") as partial:
                partial.write(b"BZ")
            raise OSError("disk full")

        with self.assertRaises(OSError):
            autobackup.back_up(self.filename, copyfile=cut_short)
        autobackup.back_up(self.filename)
        with bz2.BZ2File(autobackup.backup_name(self.filename)) as kept:
            self.assertEqual(b"current", kept.read())

    def test_a_version_kept_already_is_not_copied_again(self):
        copies = []

        def copy(source, destination):
            copies.append(destination)
            autobackup.compressFile(source, destination)

        autobackup.back_up(self.filename, copyfile=copy)
        autobackup.back_up(self.filename, copyfile=copy)
        self.assertEqual(1, len(copies))

    def test_restore_replaces_the_file_and_releases_the_lock(self):
        self.restore()
        self.assertEqual(b"backup", self.content())
        with open(self.filename + ".lock", "rb") as lock_file:
            self.assertEqual(b"", lock_file.read())

    def test_restore_keeps_the_lock_of_the_open_file(self):
        held = resourcelock.acquire(self.filename, "task file")
        self.addCleanup(held.release)
        self.restore()
        self.assertEqual(b"backup", self.content())
        self.assertIs(held, resourcelock.acquire(self.filename, "task file"))

    def test_restore_onto_a_file_open_elsewhere_is_refused(self):
        def in_use(path, purpose):
            raise resourcelock.LockInUse(path, {"pid": "4321"})

        original = resourcelock.acquire
        resourcelock.acquire = in_use
        self.addCleanup(setattr, resourcelock, "acquire", original)
        with self.assertRaises(resourcelock.LockInUse):
            self.restore()
        self.assertEqual(b"current", self.content())

    def test_unreadable_backup_keeps_the_file(self):
        self.write(self.backup, b"not bz2")
        with self.assertRaises(OSError):
            self.restore()
        self.assertEqual(b"current", self.content())
        self.assertEqual(
            ["tasks.tsk", "tasks.tsk.lock"], sorted(os.listdir(self.directory))
        )
