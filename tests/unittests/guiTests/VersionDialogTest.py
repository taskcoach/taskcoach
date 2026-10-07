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

from taskcoachlib.gui.dialog import version
from taskcoachlib.config import settings
import test


class DummyEvent(object):
    def Skip(self):
        pass


class CommonTestsMixin(object):
    def test_create_and_close(self):
        self.dialog.onClose(DummyEvent())
        self.assertTrue(settings.get("version", "notify"))

    def test_no_more_notifications(self):
        self.dialog.check.SetValue(False)
        self.dialog.onClose(DummyEvent())
        self.assertFalse(settings.get("version", "notify"))


class VersionDialogTestCase(test.TestCase):
    def setUp(self):
        self.dialog = self.createDialog()

    def createDialog(self):
        raise NotImplementedError  # pragma: no cover


class NewVersionDialogTest(CommonTestsMixin, VersionDialogTestCase):
    def createDialog(self):
        return version.NewVersionDialog(None, version="0.0", message="")


class VersionUpToDateDialogTest(CommonTestsMixin, VersionDialogTestCase):
    def createDialog(self):
        return version.VersionUpToDateDialog(None, version="0.0", message="")


class NoVersionDialogTest(CommonTestsMixin, VersionDialogTestCase):
    def createDialog(self):
        return version.NoVersionDialog(None, version="0.0", message="")


class PrereleaseVersionDialogTest(CommonTestsMixin, VersionDialogTestCase):
    def createDialog(self):
        return version.PrereleaseVersionDialog(None, version="0.0", message="")
