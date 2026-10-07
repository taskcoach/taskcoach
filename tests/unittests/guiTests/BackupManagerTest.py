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
from taskcoachlib import persistence
from taskcoachlib.gui.dialog import backupmanager


class BackupManagerTest(test.wxTestCase):
    def test_titled_as_its_menu_item(self):
        dialog = backupmanager.BackupManagerDialog(self.frame)
        self.assertEqual("Manage backups", dialog.GetTitle())

    def test_a_backup_shows_its_time_to_the_second(self):
        # Autosave keeps several a minute: they must differ in the list
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        filename = os.path.join(folder, "tasks.tsk")
        manifest = persistence.BackupManifest()
        manifest.addFile(filename)
        manifest.save()
        backup = os.path.join(
            manifest.backupPath(filename), "20260901123456.bak"
        )
        self.addCleanup(shutil.rmtree, manifest.backupPath(filename))
        with bz2.BZ2File(backup, "w") as kept:
            kept.write(b"saved")
        dialog = backupmanager.BackupManagerDialog(self.frame)
        index = manifest.listFiles().index(filename)
        dialog._OnSelectFile(_Selected(index))  # pylint: disable=W0212
        listed = dialog._BackupManagerDialog__backups  # pylint: disable=W0212
        self.assertIn("34:56", listed.GetItemText(0))


class _Selected:
    def __init__(self, index):
        self.index = index

    def GetIndex(self):
        return self.index
