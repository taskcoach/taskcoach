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
from taskcoachlib import gui, persistence, meta, operating_system
from taskcoachlib import patterns
from taskcoachlib.domain import date, task
from taskcoachlib.config import settings


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
        self.setSettings()
        self.taskFile = persistence.TaskFile()
        self.mainwindow = MainWindowUnderTest(
            DummyIOController(), self.taskFile
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
    def test_status_bar_show(self):
        settings.set("view", "statusbar", True)
        self.assertTrue(self.mainwindow.GetStatusBar().IsShown())

    def test_status_bar_hide(self):
        settings.set("view", "statusbar", False)
        self.assertFalse(self.mainwindow.GetStatusBar().IsShown())

    def test_a_task_status_change_refreshes_the_status_bar(self):
        # The status bar counts the statuses; the clock changes them
        refresh = self.mainwindow.GetStatusBar()._StatusBar__status_later
        refresh.cancel()
        patterns.Event(
            task.Task.statusChangedEventType(), task.Task(), None
        ).send()
        self.assertTrue(refresh.pending)

    def test_title_default(self):
        self.assertEqual(meta.name, self.mainwindow.GetTitle())

    def test_title_after_filename_change(self):
        self.taskFile.setFilename("New filename")
        self.assertEqual(
            "%s - %s" % (meta.name, self.taskFile.filename()),
            self.mainwindow.GetTitle(),
        )

    def test_title_after_change(self):
        self.taskFile.setFilename("New filename")
        self.taskFile.tasks().extend([task.Task()])
        self.assertEqual(
            "%s - %s *" % (meta.name, self.taskFile.filename()),
            self.mainwindow.GetTitle(),
        )

    def test_title_after_save(self):
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
        settings.set("window", "maximized", self.maximized)

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

    def test_create(self):
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
        self.assertTrue(settings.get("window", "maximized"))


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


class CallOnceDrawnTest(MainWindowTestCase):
    """The file opens once the window has painted, so the window shows
    at once however long the file takes; at the first tick if nothing
    painted by then (docs/WINDOW_GEOMETRY.md, Opening the File)."""

    def setUp(self):
        super().setUp()
        self.calls = []
        self.mainwindow.call_once_drawn(lambda: self.calls.append("open"))

    def paint(self):
        self.mainwindow.Show()
        self.mainwindow.Refresh()
        deadline = time.monotonic() + 5
        while not self.calls and time.monotonic() < deadline:
            wx.Yield()
            time.sleep(0.01)

    def tick(self):
        patterns.Event("timer.second", self, date.DateTime.now()).send()

    def test_not_before_the_window_paints(self):
        wx.Yield()
        self.assertEqual([], self.calls)

    def test_at_the_first_paint(self):
        self.paint()
        self.assertEqual(["open"], self.calls)

    def test_at_the_first_tick_if_nothing_painted(self):
        # Started minimized or on another desktop
        self.tick()
        self.assertEqual(["open"], self.calls)

    def test_once(self):
        self.paint()
        self.tick()
        self.mainwindow.Refresh()
        wx.Yield()
        self.assertEqual(["open"], self.calls)


class FloatingViewTest(MainWindowTestCase):
    """A floating view opens on the main window's monitor, once the
    main window has drawn (docs/WINDOW_GEOMETRY.md, Floating Views)."""

    def restore(self, position):
        manager = self.mainwindow.manager
        manager.GetPane("taskviewer").Float().FloatingPosition(
            position
        ).FloatingSize((300, 200))
        manager.Update()
        settings.set("view", "perspective", manager.SavePerspective())
        self.mainwindow._MainWindow__restore_perspective()
        return manager.GetPane("taskviewer")

    def test_a_floating_view_saved_off_screen_opens_on_screen(self):
        pane = self.restore((5000, 5000))
        rect = wx.Rect(pane.floating_pos, pane.floating_size)
        area = wx.Display(0).GetClientArea()
        self.assertEqual((300, 200), tuple(rect.GetSize()))
        self.assertTrue(area.Contains(rect), (rect, area))

    def test_a_floating_view_shows_once_the_window_has_drawn(self):
        pane = self.restore((100, 100))
        self.assertFalse(pane.IsShown())
        # The first tick stands for the first paint
        patterns.Event("timer.second", self, date.DateTime.now()).send()
        self.assertTrue(pane.IsShown())
