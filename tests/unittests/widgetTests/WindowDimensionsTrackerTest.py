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
from taskcoachlib import gui, operating_system
from taskcoachlib.config import settings


class WindowDimensionsTrackerTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.section = "window"
        settings.set(self.section, "position", (50, 50))
        # A frame per test: the shared one keeps earlier trackers bound
        self.window = wx.Frame(self.frame)
        if operating_system.isWindows():
            self.window.Show()
        self.tracker = gui.windowdimensionstracker.WindowDimensionsTracker(
            self.window
        )

    def tearDown(self):
        self.window.Destroy()
        super().tearDown()

    def test_initial_position(self):
        self.assertEqual(
            settings.get(self.section, "position"),
            self.window.GetPosition(),
        )

    def test_initial_size(self):
        width, height = self.window.GetSize()
        self.assertEqual((width, height), settings.get(self.section, "size"))

    def test_maximize(self):
        # The window manager's answer, which a test display without one
        # never sends: the maximize event, the size event on restoring
        self.tracker.ready = True
        events = {
            True: wx.MaximizeEvent(self.window.GetId()),
            False: wx.SizeEvent(self.window.GetSize(), self.window.GetId()),
        }
        for maximized in [True, False]:
            with mock.patch.object(
                self.window, "IsMaximized", return_value=maximized
            ):
                self.window.GetEventHandler().ProcessEvent(events[maximized])
            self.tracker.save_position()
            self.assertEqual(
                maximized, settings.get(self.section, "maximized")
            )

    def test_change_size(self):
        # Once placed, a resize is kept and written on close
        self.tracker.ready = True
        self.window.SetSize((1000, 600))
        self.tracker.save_position()
        self.assertEqual((1000, 600), settings.get(self.section, "size"))

    def test_move(self):
        # Once placed, a move is kept and written on close
        self.tracker.ready = True
        self.window.SetPosition((200, 200))
        self.tracker.save_position()
        self.assertEqual((200, 200), settings.get(self.section, "position"))

    @test.skipOnPlatform("__WXMSW__", "__WXMAC__")  # Placed at once
    def test_nothing_is_kept_before_placed(self):
        # Until placed, events are the window manager's or GTK's, not
        # the user's: the saved position stays
        self.window.SetPosition((200, 200))
        self.tracker.save_position()
        self.assertEqual((50, 50), settings.get(self.section, "position"))


class WindowGeometryTrackerFirstShowTest(test.wxTestCase):
    """wxGTK maps a new window at its minimum size, so the requested
    size is the minimum until the window is shown."""

    def setUp(self):
        super().setUp()
        settings.set("window", "position", (10, 10))
        settings.set("window", "size", (620, 450))
        self.window = wx.Frame(self.frame)
        gui.windowdimensionstracker.WindowGeometryTracker(
            self.window, "window"
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
    """Saved geometry is fitted to the monitors present, never dropped
    (docs/WINDOW_GEOMETRY.md, Decisions 2). Layout: an external monitor
    above a laptop monitor whose work area leaves out a panel on the
    left."""

    top = ((0, 0, 1920, 1080), (0, 0, 1920, 1080))
    laptop = ((0, 1080, 1920, 1080), (80, 1080, 1840, 1080))

    def fit(self, rect, monitors, primary=0):
        return gui.windowdimensionstracker.fit_to_monitors(
            rect, monitors, primary
        )

    def test_rect_whole_on_a_monitor_is_kept_as_saved(self):
        rect = (510, 1300, 880, 859)
        self.assertEqual(rect, self.fit(rect, [self.top, self.laptop]))

    def test_rect_partly_off_screen_is_centred_on_its_monitor(self):
        rect = (510, 1332, 880, 859)  # Bottom edge a little off screen
        self.assertEqual(
            (560, 1191, 880, 859), self.fit(rect, [self.top, self.laptop])
        )

    def test_rect_across_two_monitors_goes_to_the_one_it_is_most_on(self):
        rect = (500, 700, 800, 600)
        self.assertEqual(
            (560, 240, 800, 600), self.fit(rect, [self.top, self.laptop])
        )

    def test_rect_on_a_removed_monitor_goes_to_the_primary(self):
        rect = (510, 1332, 880, 859)
        self.assertEqual((520, 111, 880, 859), self.fit(rect, [self.top]))

    def test_rect_mostly_off_screen_goes_to_the_primary(self):
        rect = (1700, 100, 800, 600)
        self.assertEqual(
            (600, 1320, 800, 600),
            self.fit(rect, [self.top, self.laptop], primary=1),
        )

    def test_rect_mostly_on_a_monitor_stays_on_it(self):
        rect = (1400, 100, 800, 600)
        self.assertEqual(
            (560, 240, 800, 600),
            self.fit(rect, [self.top, self.laptop], primary=1),
        )

    def test_size_larger_than_the_monitor_is_cut_to_most_of_it(self):
        rect = (100, 100, 2500, 1300)  # 80% of 1920x1080
        self.assertEqual(
            (192, 108, 1536, 864), self.fit(rect, [self.top, self.laptop])
        )

    def test_centred_on_the_work_area_without_the_panel(self):
        rect = (-400, 1300, 880, 600)
        self.assertEqual(
            (560, 1320, 880, 600), self.fit(rect, [self.top, self.laptop])
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
        # Monitors of a known size, whatever the test display's
        for patcher in (
            mock.patch.object(
                gui.windowdimensionstracker, "_DIRECT_PLACEMENT", False
            ),
            mock.patch.object(
                gui.windowdimensionstracker.wx, "Display", FakeDisplay
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        settings.set("window", "position", (300, 200))
        settings.set("window", "size", (1000, 700))

    def place(self, window, maximized=False):
        settings.set("window", "maximized", maximized)
        tracker = gui.windowdimensionstracker.WindowGeometryTracker(
            window, "window"
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
        settings.set("window", "position", (-1, -1))
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
        settings.set("window", "position", (300, 200))
        settings.set("window", "size", (1000, 700))

    def place(self, window, maximized=False):
        settings.set("window", "maximized", maximized)
        tracker = gui.windowdimensionstracker.WindowGeometryTracker(
            window, "window"
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
        settings.set("window", "position", (-1, -1))
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

    def test_main_window_keeps_size_and_maximized(self):
        settings.set("window", "position", (300, 200))
        settings.set("window", "size", (1000, 700))
        settings.set("window", "maximized", True)
        window = FakeWindow()
        tracker = gui.windowdimensionstracker.WindowGeometryTracker(
            window, "window"
        )
        self.assertEqual(
            [("size", (1000, 700)), ("maximize", None)], window.requests
        )
        tracker.save()
        self.assertEqual((300, 200), settings.get("window", "position"))

    def test_editor_keeps_its_size_only(self):
        settings.set("effortdialog", "position", (2200, 100))
        settings.set("effortdialog", "size", (700, 500))
        parent = FakeWindow()
        editor = FakeWindow()
        with mock.patch.object(
            gui.windowdimensionstracker.wx, "Display", FakeDisplay
        ):
            tracker = gui.windowdimensionstracker.WindowGeometryTracker(
                editor, "effortdialog", parent=parent
            )
        self.assertEqual([("size", (700, 500))], editor.requests)
        tracker.save()
        self.assertEqual((2200, 100), settings.get("effortdialog", "position"))


class FakeDisplay:
    """wx.Display for two monitors side by side, 1920x1080 each, their
    work area 40 px short of the bottom (a panel)."""

    geometries = [wx.Rect(0, 0, 1920, 1080), wx.Rect(1920, 0, 1920, 1080)]
    areas = [wx.Rect(0, 0, 1920, 1040), wx.Rect(1920, 0, 1920, 1040)]
    primary = 0

    def __init__(self, index):
        self.index = index

    @classmethod
    def GetCount(cls):
        return len(cls.areas)

    def GetGeometry(self):
        return self.geometries[self.index]

    def GetClientArea(self):
        return self.areas[self.index]

    def IsPrimary(self):
        return self.index == self.primary

    @classmethod
    def GetFromPoint(cls, point):
        for index, area in enumerate(cls.areas):
            if area.Contains(point):
                return index
        return -1

    @classmethod
    def GetFromWindow(cls, window):
        x, y = window.GetPosition()
        width, height = window.GetSize()
        return cls.GetFromPoint(wx.Point(x + width // 2, y + height // 2))


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
        self.parent = FakeWindow()
        self.parent.position = (100, 100)
        self.parent.size = (1200, 800)

    def open(self, position, size, maximized=False, fitted=(800, 600)):
        settings.set("effortdialog", "position", position)
        settings.set("effortdialog", "size", size)
        settings.set("effortdialog", "maximized", maximized)
        editor = FakeWindow()
        editor.size = fitted
        self.editor = editor
        self.tracker = gui.windowdimensionstracker.WindowGeometryTracker(
            editor, "effortdialog", parent=self.parent
        )
        return editor.requests

    def saved_position(self):
        return settings.get("effortdialog", "position")

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

    def test_no_saved_size_centers_the_fitted_size(self):
        requests = self.open((-1, -1), (-1, -1))  # Fitted to 800x600
        self.assertEqual([("size", (300, 200, 800, 600))], requests)

    def test_a_fitted_size_below_the_minimum_takes_the_minimum(self):
        requests = self.open((-1, -1), (-1, -1), fitted=(226, 293))
        width, height = self.tracker._min_size
        x = 100 + (1200 - width) // 2
        y = 100 + (800 - height) // 2
        self.assertEqual([("size", (x, y, width, height))], requests)

    def test_a_large_fitted_size_is_cut_to_most_of_the_work_area(self):
        # 80% of the 1920x1040 work area
        requests = self.open((-1, -1), (-1, -1), fitted=(2500, 1500))
        self.assertEqual(
            [("size", (1536, 832)), ("size", (0, 84, 1536, 832))], requests
        )

    def test_a_fitted_size_within_most_of_the_work_area_is_kept(self):
        requests = self.open((-1, -1), (-1, -1), fitted=(1500, 800))
        self.assertEqual([("size", (0, 100, 1500, 800))], requests)

    def test_the_size_follows_the_main_windows_monitor(self):
        self.parent.position = (2020, 100)  # On monitor 1
        requests = self.open((-1, -1), (-1, -1), fitted=(2500, 1500))
        self.assertEqual(
            [("size", (1536, 832)), ("size", (1920, 84, 1536, 832))],
            requests,
        )

    def test_a_saved_size_without_position_is_cut_to_most_of_it(self):
        requests = self.open((-1, -1), (2000, 1200))
        self.assertEqual([("size", (0, 84, 1536, 832))], requests)

    def test_a_saved_size_larger_than_the_monitor_is_cut_and_centred(self):
        requests = self.open((200, 150), (2000, 900))
        self.assertEqual([("size", (0, 50, 1536, 900))], requests)
        self.tracker.save()
        self.assertEqual((0, 50), self.saved_position())

    def test_saved_rect_across_two_monitors_centers_on_the_parent(self):
        requests = self.open((1500, 150), (700, 500))
        self.assertEqual([("size", (350, 250, 700, 500))], requests)

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


class MainWindowPlacementTest(test.wxTestCase):
    """The main window opens whole on a monitor: the one it lies on
    most, the primary when most of it lies on none (docs/
    WINDOW_GEOMETRY.md, Decisions 2)."""

    def setUp(self):
        super().setUp()
        for patcher in (
            mock.patch.object(
                gui.windowdimensionstracker, "_DIRECT_PLACEMENT", True
            ),
            mock.patch.object(
                gui.windowdimensionstracker.wx, "Display", FakeDisplay
            ),
            mock.patch.object(FakeDisplay, "primary", 1),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        settings.set("window", "maximized", False)

    def open(self, position, size):
        settings.set("window", "position", position)
        settings.set("window", "size", size)
        window = FakeWindow()
        gui.windowdimensionstracker.WindowGeometryTracker(window, "window")
        return window.requests

    def test_saved_on_a_removed_monitor_opens_on_the_primary(self):
        requests = self.open((4000, 100), (1000, 700))
        self.assertEqual([("size", (2380, 170, 1000, 700))], requests)

    def test_saved_across_two_monitors_opens_on_the_one_most_on(self):
        requests = self.open((1000, 100), (1000, 700))
        self.assertEqual([("size", (460, 170, 1000, 700))], requests)

    def test_no_saved_position_cuts_a_size_too_large_for_the_primary(self):
        requests = self.open((-1, -1), (2500, 900))
        self.assertEqual([("size", (1536, 900))], requests)


class FloatingViewPlacementTest(test.TestCase):
    """A floating view opens on the main window's monitor, centred on
    the main window when saved elsewhere (docs/WINDOW_GEOMETRY.md,
    Decisions 8)."""

    main_rect = (100, 100, 1200, 800)

    def setUp(self):
        super().setUp()
        for patcher in (
            mock.patch.object(
                gui.windowdimensionstracker.wx, "Display", FakeDisplay
            ),
            mock.patch.object(FakeDisplay, "primary", 1),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def fit(self, rect, main_rect):
        return gui.windowdimensionstracker.fit_to_main_window(rect, main_rect)

    def test_whole_on_the_main_windows_monitor_is_kept(self):
        rect = (1500, 600, 400, 300)
        self.assertEqual(rect, self.fit(rect, self.main_rect))

    def test_on_another_monitor_centres_on_the_main_window(self):
        rect = (2500, 100, 400, 300)
        self.assertEqual((500, 350, 400, 300), self.fit(rect, self.main_rect))

    def test_too_large_is_cut_to_most_of_the_monitor(self):
        rect = (2500, 100, 2000, 1100)
        self.assertEqual((0, 84, 1536, 832), self.fit(rect, self.main_rect))

    def test_main_window_placed_by_the_system_means_the_primary(self):
        rect = (100, 100, 400, 300)
        self.assertEqual((2680, 370, 400, 300), self.fit(rect, None))
