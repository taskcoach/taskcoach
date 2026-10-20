"""
Task Coach - Your friendly task manager
Copyright (C) 2026 Task Coach developers <developers@taskcoach.org>

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

import datetime
import os

import wx

import test
from taskcoachlib.thirdparty.wxScheduler import wxScheduler
from taskcoachlib.widgets import wxevents


def lose_capture(window):
    """Whether the window handles losing the mouse, as wx tells it on
    Alt+Tab or a window shown mid-drag; wx raises when it does not."""
    event = wx.MouseCaptureLostEvent(window.GetId())
    event.SetEventObject(window)
    return window.GetEventHandler().ProcessEvent(event)


class Canvas(wxevents.CalendarCanvas):
    def GetStart(self, event):  # noqa: N802 (the canvas's)
        return datetime.datetime(2026, 10, 19, 9)

    def GetEnd(self, event):  # noqa: N802 (the canvas's)
        return datetime.datetime(2026, 10, 19, 10)


class CalendarCanvasCaptureTest(test.wxTestCase):
    """An event dragged in the calendar, the mouse taken away:
    unhandled, wx raised, and so did the next release, before the drag
    ended; the canvas went on dragging."""

    def setUp(self):
        super().setUp()
        self.canvas = Canvas(self.frame)
        self.canvas._mouse_state = self.canvas.MS_DRAGGING
        self.canvas._mouse_origin = wxevents._HitResult(0, 0, "event", None)
        self.canvas._mouse_drag_pos = datetime.datetime(2026, 10, 19, 11)

    def test_a_lost_mouse_ends_the_drag(self):
        self.assertTrue(lose_capture(self.canvas))
        self.assertEqual(self.canvas.MS_IDLE, self.canvas._mouse_state)

    def test_a_release_without_the_mouse_ends_the_drag(self):
        # The capture can go unannounced
        self.canvas._on_left_up(None)
        self.assertEqual(self.canvas.MS_IDLE, self.canvas._mouse_state)


class SchedulerHeaderCaptureTest(test.wxTestCase):
    """The calendar's period width dragged in its header, the mouse
    taken away: the width went on following the mouse."""

    def setUp(self):
        super().setUp()
        self.scheduler = wxScheduler(self.frame)
        self.header = wx.Panel(self.frame)
        self.scheduler.SetHeaderPanel(self.header)
        self.scheduler._headerCursorState = 1
        self.scheduler._headerDragOrigin = 10

    def test_a_lost_mouse_ends_the_drag(self):
        self.assertTrue(lose_capture(self.header))
        self.assertIsNone(self.scheduler._headerDragOrigin)

    def test_a_release_without_the_mouse_ends_the_drag(self):
        self.scheduler._OnLeftUpHeaders(None)
        self.assertIsNone(self.scheduler._headerDragOrigin)


class CaptureRuleTest(test.TestCase):
    def test_a_window_that_takes_the_mouse_handles_losing_it(self):
        root = os.path.join(os.path.dirname(test.__file__), "..")
        root = os.path.join(root, "taskcoachlib")
        unhandled = []
        for folder, folders, files in os.walk(root):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(folder, name)
                with open(path, encoding="utf-8") as source:
                    text = source.read()
                if (
                    "CaptureMouse()" in text
                    and "EVT_MOUSE_CAPTURE_LOST" not in text
                ):
                    unhandled.append(os.path.relpath(path, root))
        self.assertEqual([], unhandled)
