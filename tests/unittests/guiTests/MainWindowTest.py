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
import shutil
import tempfile
import time
from unittest import mock

import wx, test
from taskcoachlib import gui, config, persistence, meta, operating_system
from taskcoachlib import patterns
from taskcoachlib.domain import task


class MockViewer(wx.Frame):
    def title(self):
        return ""

    def settingsSection(self):
        return "taskviewer"

    def viewer_status_event_type(self):
        return "mockviewer.status"

    def curselection(self):
        return []


class MainWindowUnderTest(gui.mainwindow.MainWindow):
    def _create_window_components(self):
        # Create only the window components we really need for the tests
        self._create_viewer_container()
        self.viewer.add_viewer(MockViewer(None))
        self._create_status_bar()


class DummyIOController(object):
    def need_save(self, *args, **kwargs):  # pylint: disable=W0613
        return False  # pragma: no cover


class MainWindowTestCase(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.settings = config.settings.current()
        self.setSettings()
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
        # As MainWindow.onClose does before the window is destroyed
        self.mainwindow.manager.UnInit()
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

    def test_a_task_status_change_refreshes_the_status_bar(self):
        # The status bar counts the statuses; the clock changes them
        refresh = self.mainwindow.GetStatusBar()._StatusBar__status_later
        refresh.cancel()
        patterns.Event(
            task.Task.statusChangedEventType(), task.Task(), None
        ).send()
        self.assertTrue(refresh.pending)

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
        # Saving writes the file, its change log and its lock file
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        self.taskFile.setFilename(os.path.join(directory, "New filename"))
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

    def placed(self):
        """The window's tracker once the placement is quiet
        (docs/WINDOW_GEOMETRY.md)."""
        tracker = self.mainwindow._MainWindow__dimensions_tracker
        deadline = time.monotonic() + 5
        while not tracker.ready and time.monotonic() < deadline:
            wx.Yield()
            time.sleep(0.01)
        return tracker


class MainWindowNotMaximizedTest(MainWindowMaximizeTestCase):
    maximized = False

    def testCreate(self):
        self.assertFalse(self.mainwindow.IsMaximized())

    def test_maximize(self):
        # The window manager's answer, which a test display without one
        # never sends
        self.assertTrue(self.placed().ready)
        with mock.patch.object(
            self.mainwindow, "IsMaximized", return_value=True
        ):
            self.mainwindow.GetEventHandler().ProcessEvent(
                wx.MaximizeEvent(self.mainwindow.GetId())
            )
        self.mainwindow.save_settings()  # Geometry is written on close
        self.assertTrue(self.settings.getboolean("window", "maximized"))


class MainWindowMaximizedTest(MainWindowMaximizeTestCase):
    maximized = True

    @test.skipOnPlatform("__WXMAC__")
    def test_create(self):  # pragma: no cover
        # The maximize comes once the placement is quiet, and a window
        # manager grants it
        tracker = self.placed()
        if not tracker.maximized:
            self.skipTest("no window manager granted the maximize")
        self.assertTrue(
            self.mainwindow.IsMaximized(),
            "ready %s, phase %s, %s attempts"
            % (tracker.ready, tracker._phase, tracker._attempts),
        )
