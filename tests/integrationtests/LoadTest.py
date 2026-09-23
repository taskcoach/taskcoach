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
import wx
import test
import mock


class LoadTest(test.TestCase):
    def setUp(self):
        self.filename = "LoadTest.tsk"
        taskfile = open(self.filename, "w")
        taskfile.writelines(["Line 1\n", "Line 2\n"])
        taskfile.close()
        self.errorDialogCalled = False
        self.mockApp = mock.App()

        # On MacOS, wx.Yield doesn't seem to be enough, so while
        # running the tests, just short-circuit this:
        self.oldCallAfter = wx.CallAfter
        # pylint: disable=W0142
        wx.CallAfter = lambda func, *args, **kwargs: func(*args, **kwargs)

    def tearDown(self):
        wx.CallAfter = self.oldCallAfter
        self.mockApp.quit_application()
        if os.path.isfile(self.filename):
            os.remove(self.filename)
        mock.App.deleteInstance()
        super().tearDown()

    def mockErrorDialog(self, *args, **kwargs):  # pylint: disable=W0613
        self.errorDialogCalled = True

    def testLoadInvalidFileDoesNotAffectFile(self):
        self.mockApp.iocontroller.open(
            self.filename, showerror=self.mockErrorDialog
        )
        lines = open(self.filename, "r").readlines()
        self.assertTrue(self.errorDialogCalled)
        self.assertEqual(2, len(lines))
        self.assertEqual("Line 1\n", lines[0])
        self.assertEqual("Line 2\n", lines[1])

    def testLoadNonExistingFileGivesErrorMessage(self):
        self.mockApp.iocontroller.open(
            "I don't exist.tsk",
            showerror=self.mockErrorDialog,
            file_exists=lambda filename: False,
        )
        wx.GetApp().Yield()  # io.open uses wx.CallAfter
        self.assertTrue(self.errorDialogCalled)
