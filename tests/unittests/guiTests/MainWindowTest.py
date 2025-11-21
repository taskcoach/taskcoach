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

import ast
import wx, test
from taskcoachlib import gui, config, persistence, meta, operating_system
from taskcoachlib.domain import task


class MockViewer(wx.Frame):
    def title(self):
        return ""

    def settingsSection(self):
        return "taskviewer"

    def viewerStatusEventType(self):
        return "mockviewer.status"

    def curselection(self):
        return []


class MainWindowUnderTest(gui.MainWindow):
    def _create_window_components(self):
        # Create only the window components we really need for the tests
        self._create_viewer_container()
        self.viewer.addViewer(MockViewer(None))
        self._create_status_bar()


class DummyIOController(object):
    def needSave(self, *args, **kwargs):  # pylint: disable=W0613
        return False  # pragma: no cover

    def changedOnDisk(self):
        return False  # pragme: no cover


class MainWindowTestCase(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)
        self.setSettings()
        task.Task.settings = self.settings
        self.taskFile = persistence.TaskFile()
        self.mainwindow = MainWindowUnderTest(
            DummyIOController(), self.taskFile, self.settings
        )

    def setSettings(self):
        pass

    def tearDown(self):
        if operating_system.isMac():
            self.mainwindow.OnQuit()  # Stop power monitoring thread
        # Also stop idle time thread
        self.mainwindow._idleController.stop()
        self.mainwindow.Destroy()
        wx.Yield()
        del self.mainwindow
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()


class MainWindowTest(MainWindowTestCase):
    def testStatusBar_Show(self):
        self.settings.setboolean("view", "statusbar", True)
        self.assertTrue(self.mainwindow.GetStatusBar().IsShown())

    def testStatusBar_Hide(self):
        self.settings.setboolean("view", "statusbar", False)
        self.assertFalse(self.mainwindow.GetStatusBar().IsShown())

    def testTitle_Default(self):
        self.assertEqual(meta.name, self.mainwindow.GetTitle())

    def testTitle_AfterFilenameChange(self):
        self.taskFile.setFilename("New filename")
        self.assertEqual(
            "%s - %s" % (meta.name, self.taskFile.filename()),
            self.mainwindow.GetTitle(),
        )

    def testTitle_AfterChange(self):
        self.taskFile.setFilename("New filename")
        self.taskFile.tasks().extend([task.Task()])
        self.assertEqual(
            "%s - %s *" % (meta.name, self.taskFile.filename()),
            self.mainwindow.GetTitle(),
        )

    def testTitle_AfterSave(self):
        self.taskFile.setFilename("New filename")
        self.taskFile.tasks().extend([task.Task()])
        self.taskFile.save()
        self.assertEqual(
            "%s - %s" % (meta.name, self.taskFile.filename()),
            self.mainwindow.GetTitle(),
        )


class MainWindowMaximizeTestCase(MainWindowTestCase):
    maximized = "Subclass responsibility"

    def setUp(self):
        super().setUp()
        if not operating_system.isMac():
            self.mainwindow.Show()  # Or IsMaximized() returns always False...

    def setSettings(self):
        self.settings.setboolean("window", "maximized", self.maximized)


class MainWindowNotMaximizedTest(MainWindowMaximizeTestCase):
    maximized = False

    def testCreate(self):
        self.assertFalse(self.mainwindow.IsMaximized())

    @test.skipOnPlatform("__WXGTK__")
    def testMaximize(self):  # pragma: no cover
        # Skipping this test under wxGTK. I don't know how it managed
        # to pass before but according to
        # http://trac.wxwidgets.org/ticket/9167 and to my own tests,
        # EVT_MAXIMIZE is a noop under this platform.
        self.mainwindow.Maximize()
        if operating_system.isWindows():
            wx.Yield()
        self.assertTrue(self.settings.getboolean("window", "maximized"))


class MainWindowMaximizedTest(MainWindowMaximizeTestCase):
    maximized = True

    @test.skipOnPlatform("__WXMAC__")
    def testCreate(self):
        self.assertTrue(self.mainwindow.IsMaximized())  # pragma: no cover


class MainWindowIconizedTest(MainWindowTestCase):
    def setUp(self):
        super().setUp()
        if operating_system.isGTK():
            wx.SafeYield()  # pragma: no cover

    def setSettings(self):
        self.settings.set("window", "starticonized", "Always")

    def expectedHeight(self):
        height = 500
        if operating_system.isMac():
            height += 18  # pragma: no cover
        return height

    @test.skipOnPlatform(
        "__WXGTK__"
    )  # Test fails on Fedora, don't know why nor how to fix it
    def testIsIconized(self):
        self.assertTrue(self.mainwindow.IsIconized())  # pragma: no cover

    def testWindowSize(self):
        self.assertEqual(
            (900, self.expectedHeight()),
            ast.literal_eval(self.settings.get("window", "size")),
        )

    def testWindowSizeShouldnotChangeWhenReceivingChangeSizeEvent(self):
        event = wx.SizeEvent((100, 20))
        process = self.mainwindow.ProcessEvent
        if operating_system.isWindows():
            process(event)  # pragma: no cover
        else:
            wx.CallAfter(process, event)  # pragma: no cover
        self.assertEqual(
            (900, self.expectedHeight()),
            ast.literal_eval(self.settings.get("window", "size")),
        )
