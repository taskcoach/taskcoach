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

from taskcoachlib import config
from taskcoachlib.gui.dialog import version
import test


class DummyEvent(object):
    def Skip(self):
        pass


class CommonTestsMixin(object):
    def testCreateAndClose(self):
        self.dialog.onClose(DummyEvent())
        self.assertTrue(self.settings.getboolean("version", "notify"))

    def testNoMoreNotifications(self):
        self.dialog.check.SetValue(False)
        self.dialog.onClose(DummyEvent())
        self.assertFalse(self.settings.getboolean("version", "notify"))


class VersionDialogTestCase(test.TestCase):
    def setUp(self):
        self.settings = config.settings.current()
        self.dialog = self.createDialog()

    def createDialog(self):
        raise NotImplementedError  # pragma: no cover


class NewVersionDialogTest(CommonTestsMixin, VersionDialogTestCase):
    def createDialog(self):
        return version.NewVersionDialog(
            None, version="0.0", message="", settings=self.settings
        )


class VersionUpToDateDialogTest(CommonTestsMixin, VersionDialogTestCase):
    def createDialog(self):
        return version.VersionUpToDateDialog(
            None, version="0.0", message="", settings=self.settings
        )


class NoVersionDialogTest(CommonTestsMixin, VersionDialogTestCase):
    def createDialog(self):
        return version.NoVersionDialog(
            None, version="0.0", message="", settings=self.settings
        )


class PrereleaseVersionDialogTest(CommonTestsMixin, VersionDialogTestCase):
    def createDialog(self):
        return version.PrereleaseVersionDialog(
            None, version="0.0", message="", settings=self.settings
        )
