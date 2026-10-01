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

import time
from unittest import mock

import wx
import test
from taskcoachlib import gui, config, operating_system


class WindowDimensionsTrackerTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)
        self.section = "window"
        self.settings.setvalue(self.section, "position", (50, 50))
        # A frame per test: the shared one keeps earlier trackers bound
        self.window = wx.Frame(self.frame)
        if operating_system.isWindows():
            self.window.Show()
        self.tracker = gui.windowdimensionstracker.WindowDimensionsTracker(
            self.window, self.settings
        )

    def tearDown(self):
        self.window.Destroy()
        super().tearDown()

    def test_initial_position(self):
        self.assertEqual(
            self.settings.getvalue(self.section, "position"),
            self.window.GetPosition(),
        )

    def test_initial_size(self):
        width, height = self.window.GetSize()
        self.assertEqual(
            (width, height), self.settings.getvalue(self.section, "size")
        )

    @test.skipOnPlatform("__WXGTK__")
    def test_maximize(self):
        for maximized in [True, False]:
            self.window.Maximize(maximized)
            self.assertEqual(maximized, self.window.IsMaximized())
            self.tracker.save_position()
            self.assertEqual(
                maximized, self.settings.getboolean(self.section, "maximized")
            )

    def test_change_size(self):
        # Once placed, a resize is kept and written on close
        self.tracker.ready = True
        self.window.SetSize((1000, 600))
        self.tracker.save_position()
        self.assertEqual(
            (1000, 600), self.settings.getvalue(self.section, "size")
        )

    def test_move(self):
        # Once placed, a move is kept and written on close
        self.tracker.ready = True
        self.window.SetPosition((200, 200))
        self.tracker.save_position()
        self.assertEqual(
            (200, 200), self.settings.getvalue(self.section, "position")
        )

    @test.skipOnPlatform("__WXMSW__", "__WXMAC__")  # Placed at once
    def test_nothing_is_kept_before_placed(self):
        # Until placed, events are the window manager's or GTK's, not
        # the user's: the saved position stays
        self.window.SetPosition((200, 200))
        self.tracker.save_position()
        self.assertEqual(
            (50, 50), self.settings.getvalue(self.section, "position")
        )


class WindowGeometryTrackerFirstShowTest(test.wxTestCase):
    """wxGTK maps a new window at its minimum size, so the requested
    size is the minimum until the window is shown."""

    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)
        self.settings.setvalue("window", "position", (10, 10))
        self.settings.setvalue("window", "size", (620, 450))
        self.window = wx.Frame(self.frame)
        gui.windowdimensionstracker.WindowGeometryTracker(
            self.window, self.settings, "window"
        )

    def tearDown(self):
        self.window.Destroy()
        super().tearDown()

    @test.skipOnPlatform("__WXMSW__", "__WXMAC__")
    def test_requested_size_is_the_minimum_until_shown(self):
        self.assertEqual((620, 450), self.window.GetMinSize())

    @test.skipOnPlatform("__WXMSW__", "__WXMAC__")
    def test_minimum_size_returns_once_shown(self):
        self.window.ProcessEvent(wx.ShowEvent(self.window.GetId(), True))
        self.assertEqual((600, 400), self.window.GetMinSize())


class FitToMonitorsTest(test.TestCase):
    """Saved geometry is fitted to the monitors present, never dropped.
    Layout: an external monitor above a laptop monitor whose work area
    leaves out a panel on the left."""

    top = ((0, 0, 1920, 1080), (0, 0, 1920, 1080))
    laptop = ((0, 1080, 1920, 1080), (80, 1080, 1840, 1080))

    def fit(self, rect, monitors):
        return gui.windowdimensionstracker.fit_to_monitors(rect, monitors)

    def test_rect_on_a_monitor_is_kept_as_saved(self):
        rect = (510, 1332, 880, 859)  # Bottom edge a little off screen
        self.assertEqual(rect, self.fit(rect, [self.top, self.laptop]))

    def test_rect_on_a_removed_monitor_goes_to_the_nearest(self):
        rect = (510, 1332, 880, 859)
        self.assertEqual((510, 221, 880, 859), self.fit(rect, [self.top]))

    def test_rect_on_the_upper_monitor_goes_to_the_laptop(self):
        rect = (300, 200, 1000, 700)
        self.assertEqual((300, 1080, 1000, 700), self.fit(rect, [self.laptop]))

    def test_size_larger_than_the_monitor_is_reduced(self):
        rect = (100, 100, 2500, 1300)
        self.assertEqual(
            (0, 0, 1920, 1080), self.fit(rect, [self.top, self.laptop])
        )

    def test_rect_off_every_monitor_goes_inside_the_nearest(self):
        rect = (4000, 200, 880, 600)
        self.assertEqual(
            (1040, 200, 880, 600), self.fit(rect, [self.top, self.laptop])
        )

    def test_work_area_excludes_the_panel(self):
        rect = (-900, 1300, 880, 600)
        self.assertEqual(
            (80, 1300, 880, 600), self.fit(rect, [self.top, self.laptop])
        )


class FakeWindow:
    """A top-level window whose platform places it at (80, 0) and may
    refuse moves and resizes, or maximizing. Only the wx methods the
    tracker uses."""

    def __init__(self, refuse_moves=False, refuse_maximize=False):
        self.refuse_moves = refuse_moves
        self.refuse_maximize = refuse_maximize
        self.position = (0, 0)
        self.size = (800, 600)
        self.maximized = False
        self.iconized = False
        self.requests = []

    def Bind(self, *args, **kwargs):
        pass

    def SetMinSize(self, size):
        pass

    def IsShown(self):
        return False

    def IsActive(self):
        return True

    def IsIconized(self):
        return self.iconized

    def Show(self, show=True):
        pass

    def Hide(self):
        pass

    def Iconize(self, iconize=True):
        self.requests.append(("iconize", iconize))
        self.iconized = iconize

    def IsMaximized(self):
        return self.maximized

    def GetPosition(self):
        return wx.Point(*self.position)

    def GetSize(self):
        return wx.Size(*self.size)

    def SetSize(self, *args):
        self.requests.append(("size", args))
        if not self.refuse_moves:
            self.size = args[-2:]
            if len(args) == 4:
                self.position = args[:2]

    def SetPosition(self, point):
        self.requests.append(("position", (point.x, point.y)))
        if not self.refuse_moves:
            self.position = (point.x, point.y)

    def Maximize(self):
        self.requests.append(("maximize", None))
        if not self.refuse_maximize:
            self.maximized = True


class PlacementTest(test.wxTestCase):
    """Placement is checked once the window is quiet: a few attempts,
    then the platform's decision is accepted."""

    attempts = gui.windowdimensionstracker._ATTEMPTS

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(
            gui.windowdimensionstracker, "_DIRECT_PLACEMENT", False
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.settings = config.Settings(load=False)
        self.settings.setvalue("window", "position", (300, 200))
        self.settings.setvalue("window", "size", (1000, 700))

    def place(self, window, maximized=False):
        self.settings.setvalue("window", "maximized", maximized)
        tracker = gui.windowdimensionstracker.WindowGeometryTracker(
            window, self.settings, "window"
        )
        tracker._wait_until_quiet = lambda: None  # Quiet checks by hand
        window.requests = []
        window.position = (80, 0)  # Where the window manager put it
        return tracker

    def check_when_quiet(self, tracker, times):
        for _ in range(times):
            if not tracker.ready:
                tracker._on_quiet()

    def test_one_correction_places_the_window(self):
        window = FakeWindow()
        tracker = self.place(window)
        self.check_when_quiet(tracker, 2)
        self.assertTrue(tracker.ready)
        self.assertEqual((300, 200), window.position)
        self.assertEqual([("position", (300, 200))], window.requests)

    def test_refused_move_is_tried_then_accepted(self):
        window = FakeWindow(refuse_moves=True)
        tracker = self.place(window)
        self.check_when_quiet(tracker, self.attempts + 2)
        self.assertTrue(tracker.ready)
        self.assertEqual((80, 0), tracker.position)
        self.assertEqual(
            self.attempts,
            [kind for kind, _ in window.requests].count("position"),
        )

    def test_maximize_follows_the_placement(self):
        window = FakeWindow()
        tracker = self.place(window, maximized=True)
        self.check_when_quiet(tracker, 3)
        self.assertTrue(tracker.ready)
        self.assertEqual(
            [("position", (300, 200)), ("maximize", None)], window.requests
        )

    def test_refused_maximize_is_tried_then_accepted(self):
        window = FakeWindow(refuse_maximize=True)
        tracker = self.place(window, maximized=True)
        self.check_when_quiet(tracker, self.attempts + 3)
        self.assertTrue(tracker.ready)
        self.assertFalse(tracker.maximized)
        self.assertEqual(
            self.attempts,
            [kind for kind, _ in window.requests].count("maximize"),
        )

    def test_lost_position_is_sent_again_before_the_show(self):
        window = FakeWindow()
        tracker = self.place(window)
        tracker._resend_lost_request()
        self.assertEqual([("position", (300, 200))], window.requests)

    def test_lost_size_sends_the_position_again_with_a_step_aside(self):
        window = FakeWindow()
        tracker = self.place(window)
        window.position = (300, 200)
        window.size = (6, 28)  # wxGTK deferring the first show
        tracker._resend_lost_request()
        self.assertEqual(
            [("position", (301, 200)), ("position", (300, 200))],
            window.requests,
        )

    def test_request_kept_is_not_sent_again(self):
        window = FakeWindow()
        tracker = self.place(window)
        window.position = (300, 200)
        tracker._resend_lost_request()
        self.assertEqual([], window.requests)

    def shown(self, tracker):
        tracker._step_started = tracker._requested_at = time.perf_counter()

    def test_layout_without_a_change_is_not_an_answer(self):
        window = FakeWindow()
        tracker = self.place(window)
        window.position = (300, 200)
        self.shown(tracker)
        tracker._on_geometry_event("EVT_SIZE")
        slowest = tracker._slowest_answer
        tracker._on_geometry_event("EVT_SIZE")  # SendSizeEvent()
        self.assertEqual(slowest, tracker._slowest_answer)

    def test_no_saved_position_keeps_the_saved_maximized(self):
        self.settings.setvalue("window", "position", (-1, -1))
        window = FakeWindow()
        tracker = self.place(window, maximized=True)
        self.check_when_quiet(tracker, 2)
        self.assertIn(("maximize", None), window.requests)
        self.assertTrue(tracker.maximized)

    def test_maximized_during_placement_is_accepted(self):
        window = FakeWindow()
        tracker = self.place(window)
        window.maximized = True  # By the user, or the window manager
        self.check_when_quiet(tracker, 1)
        self.assertTrue(tracker.ready)
        self.assertEqual([], window.requests)
        self.assertTrue(tracker.maximized)
        # The normal geometry to return to is the saved one
        self.assertEqual((300, 200), tracker.position)
        self.assertEqual((1000, 700), tracker.size)

    def test_step_limit_keeps_a_maximized_state_not_tried_yet(self):
        window = FakeWindow()
        tracker = self.place(window, maximized=True)
        tracker._accept()  # Still moving after the step limit
        self.assertTrue(tracker.maximized)

    def test_slow_answers_lengthen_the_quiet_period(self):
        window = FakeWindow()
        tracker = self.place(window)
        window.position = (300, 200)
        self.shown(tracker)
        tracker._requested_at -= 0.8  # The platform answers after 0.8 s
        tracker._on_geometry_event("EVT_MOVE")
        tracker._on_quiet()
        self.assertTrue(1600 <= tracker._quiet_ms < 1700)


class DirectPlacementTest(test.wxTestCase):
    """Windows and macOS apply the geometry during the calls: set once
    before the first show, never checked."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(
            gui.windowdimensionstracker, "_DIRECT_PLACEMENT", True
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.settings = config.Settings(load=False)
        self.settings.setvalue("window", "position", (300, 200))
        self.settings.setvalue("window", "size", (1000, 700))

    def place(self, window, maximized=False):
        self.settings.setvalue("window", "maximized", maximized)
        tracker = gui.windowdimensionstracker.WindowGeometryTracker(
            window, self.settings, "window"
        )
        tracker._wait_until_quiet = lambda: self.fail("waited for quiet")
        return tracker

    def test_placed_before_show(self):
        window = FakeWindow()
        tracker = self.place(window)
        self.assertTrue(tracker.ready)
        self.assertEqual([("size", (300, 200, 1000, 700))], window.requests)

    def test_maximized_before_show(self):
        window = FakeWindow()
        tracker = self.place(window, maximized=True)
        self.assertTrue(tracker.ready)
        self.assertEqual(
            [("size", (300, 200, 1000, 700)), ("maximize", None)],
            window.requests,
        )

    def test_no_saved_position_keeps_the_saved_maximized(self):
        self.settings.setvalue("window", "position", (-1, -1))
        window = FakeWindow()
        self.place(window, maximized=True)
        self.assertEqual(
            [("size", (1000, 700)), ("maximize", None)], window.requests
        )


class WaylandTest(test.wxTestCase):
    """The compositor places windows: positions are neither restored
    nor saved; sizes and the maximized state are."""

    def setUp(self):
        super().setUp()
        for patcher in (
            mock.patch.object(
                gui.windowdimensionstracker, "_DIRECT_PLACEMENT", True
            ),
            mock.patch.object(
                gui.windowdimensionstracker.operating_system,
                "isWayland",
                lambda: True,
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.settings = config.Settings(load=False)

    def test_main_window_keeps_size_and_maximized(self):
        self.settings.setvalue("window", "position", (300, 200))
        self.settings.setvalue("window", "size", (1000, 700))
        self.settings.setvalue("window", "maximized", True)
        window = FakeWindow()
        tracker = gui.windowdimensionstracker.WindowGeometryTracker(
            window, self.settings, "window"
        )
        self.assertEqual(
            [("size", (1000, 700)), ("maximize", None)], window.requests
        )
        tracker.save()
        self.assertEqual(
            (300, 200), self.settings.getvalue("window", "position")
        )

    def test_editor_keeps_its_size_only(self):
        self.settings.setvalue("effortdialog", "position", (2200, 100))
        self.settings.setvalue("effortdialog", "size", (700, 500))
        parent = FakeWindow()
        editor = FakeWindow()
        tracker = gui.windowdimensionstracker.WindowGeometryTracker(
            editor, self.settings, "effortdialog", parent=parent
        )
        self.assertEqual([("size", (700, 500))], editor.requests)
        tracker.save()
        self.assertEqual(
            (2200, 100), self.settings.getvalue("effortdialog", "position")
        )


class FakeDisplay:
    """wx.Display for two monitors side by side, 1920x1080 each, their
    work area 40 px short of the bottom (a panel)."""

    areas = [wx.Rect(0, 0, 1920, 1040), wx.Rect(1920, 0, 1920, 1040)]

    def __init__(self, index):
        self.index = index

    def GetClientArea(self):
        return self.areas[self.index]

    @classmethod
    def GetFromPoint(cls, point):
        for index, area in enumerate(cls.areas):
            if area.Contains(point):
                return index
        return -1


class EditorPlacementTest(test.wxTestCase):
    """An editor opens on its parent's monitor (docs/WINDOW_GEOMETRY.md,
    Editors). The parent, 1200x800 at (100, 100), is on monitor 0."""

    def setUp(self):
        super().setUp()
        # Placed during the calls, so the requests show the decision
        for patcher in (
            mock.patch.object(
                gui.windowdimensionstracker, "_DIRECT_PLACEMENT", True
            ),
            mock.patch.object(
                gui.windowdimensionstracker.wx, "Display", FakeDisplay
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.settings = config.Settings(load=False)
        self.parent = FakeWindow()
        self.parent.position = (100, 100)
        self.parent.size = (1200, 800)

    def open(self, position, size, maximized=False):
        self.settings.setvalue("effortdialog", "position", position)
        self.settings.setvalue("effortdialog", "size", size)
        self.settings.setvalue("effortdialog", "maximized", maximized)
        editor = FakeWindow()
        self.tracker = gui.windowdimensionstracker.WindowGeometryTracker(
            editor, self.settings, "effortdialog", parent=self.parent
        )
        return editor.requests

    def saved_position(self):
        return self.settings.getvalue("effortdialog", "position")

    def test_saved_geometry_on_the_parents_monitor_is_kept(self):
        requests = self.open((200, 150), (700, 500))
        self.assertEqual([("size", (200, 150, 700, 500))], requests)

    def test_saved_position_on_another_monitor_centers_on_the_parent(self):
        requests = self.open((2200, 100), (700, 500))
        self.assertEqual([("size", (350, 250, 700, 500))], requests)
        self.tracker.save()
        self.assertEqual((350, 250), self.saved_position())

    def test_no_saved_position_centers_with_the_saved_size(self):
        requests = self.open((-1, -1), (700, 500))
        self.assertEqual([("size", (350, 250, 700, 500))], requests)

    def test_no_saved_size_centers_the_minimum_size(self):
        # The production rule, kept: see Known Issues
        requests = self.open((-1, -1), (-1, -1))
        width, height = self.tracker._min_size
        x = 100 + (1200 - width) // 2
        y = 100 + (800 - height) // 2
        self.assertEqual([("size", (x, y, width, height))], requests)

    def test_size_larger_than_the_monitor_lets_the_system_decide(self):
        requests = self.open((200, 150), (2000, 900))
        self.assertEqual([], requests)
        self.assertEqual((-1, -1), self.saved_position())

    def test_centering_stays_inside_the_parents_monitor(self):
        self.parent.position = (1500, 700)
        self.parent.size = (400, 300)
        requests = self.open((2200, 100), (700, 500))
        self.assertEqual([("size", (1220, 540, 700, 500))], requests)

    def test_saved_maximized_reopens_maximized(self):
        requests = self.open((200, 150), (700, 500), maximized=True)
        self.assertEqual(
            [("size", (200, 150, 700, 500)), ("maximize", None)], requests
        )
