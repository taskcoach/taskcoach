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
import json
import test
from taskcoachlib import config, meta


class VersionCheckerUnderTest(meta.VersionChecker):
    def __init__(self, *args, **kwargs):
        self.version = kwargs.pop("version")
        self.retrievalException = kwargs.pop("retrievalException", None)
        self.parseException = kwargs.pop("parseException", None)
        self.userNotified = False
        super().__init__(*args, **kwargs)

    def retrieve_latest_release(self):  # pylint: disable=W0221
        """GitHub's answer, as its API gives it"""
        if self.retrievalException:
            raise self.retrievalException
        return io.BytesIO(
            json.dumps({"tag_name": "v" + self.version}).encode("utf-8")
        )

    def parse_release(self, answer):  # pylint: disable=W0221
        if self.parseException:
            raise self.parseException
        return super().parse_release(answer)

    def notifyUser(self, *args, **kwargs):  # pylint: disable=W0221,W0613
        self.userNotified = True


class VersionCheckerTest(test.TestCase):
    def setUp(self):
        self.settings = config.Settings(load=False)

    def checkVersion(
        self, version, retrievalException=None, parseException=None
    ):
        checker = VersionCheckerUnderTest(
            self.settings,
            version=version,
            retrievalException=retrievalException,
            parseException=parseException,
        )
        checker.run()
        return checker

    def assertLastVersionNotified(
        self, version, retrievalException=None, parseException=None
    ):
        self.checkVersion(version, retrievalException, parseException)
        self.assertEqual(version, self.settings.get("version", "notified"))

    def testLatestVersionIsNewerThanLastVersionNotified(self):
        self.assertLastVersionNotified("99.99.99")

    def testLatestVersionEqualsLastVersionNotified(self):
        self.assertLastVersionNotified(meta.data.version_full)

    def test_error_while_asking_github(self):
        import urllib.error

        retrievalException = urllib.error.HTTPError(
            None, None, None, None, None
        )
        self.assertLastVersionNotified(
            meta.data.version_full, retrievalException
        )

    def test_unreadable_answer(self):
        self.assertLastVersionNotified(
            meta.data.version_full, parseException=ValueError
        )

    def testDontNotifyWhenCurrentVersionIsNewerThanLastVersionNotified(self):
        self.settings.set("version", "notified", "0.0")
        checker = self.checkVersion(meta.data.version_full)
        self.assertFalse(checker.userNotified)

    def test9IsNotNewerThan10(self):
        current_version = meta.data.version_full
        meta.data.version_full = "0.72.10"
        self.settings.set("version", "notified", "0.72.8")
        checker = self.checkVersion("0.72.9")
        self.assertFalse(checker.userNotified)
        meta.data.version_full = current_version

    def test_a_newer_release_is_shown(self):
        checker = self.checkVersion("99.0.0.0")
        self.assertTrue(checker.userNotified)

    def test_the_tag_is_read_without_its_v(self):
        answer = io.BytesIO(b'{"tag_name": "v2.0.2.26", "name": "x"}')
        self.assertEqual("2.0.2.26", meta.VersionChecker.parse_release(answer))

    def testShowDialog(self):
        class DummyDialog(object):
            def __init__(self, *args, **kwargs):  # pylint: disable=W0613
                self.shown = False

            def Show(self):
                self.shown = True

        checker = meta.VersionChecker(self.settings)
        dialog = checker.showDialog(DummyDialog, "1.0")
        self.assertTrue(dialog.shown)
