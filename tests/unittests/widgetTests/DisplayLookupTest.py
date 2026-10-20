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
import os
from unittest import mock

import wx

import test
from taskcoachlib.tools import wxhelper


class DisplayLookupTest(test.wxTestCase):
    """Every display lookup goes through wxhelper: wx.Display(-1)
    crashes natively (it indexes past the displays it holds), wx
    asserts on macOS for a mirrored display, and a display asleep can
    report an empty work area (#487)."""

    def primary_area(self):
        for index in range(wx.Display.GetCount()):
            if wx.Display(index).IsPrimary():
                return tuple(wx.Display(index).GetClientArea())
        return tuple(wx.Display(0).GetClientArea())

    def test_a_point_on_no_display_has_none(self):
        self.assertEqual(
            wx.NOT_FOUND, wxhelper.display_index(point=(10**6, 10**6))
        )

    def test_no_display_gives_the_primary_work_area(self):
        self.assertEqual(self.primary_area(), wxhelper.work_area(wx.NOT_FOUND))

    def test_wx_asserting_gives_no_display(self):
        with mock.patch.object(
            wx.Display, "GetFromPoint", side_effect=wx.wxAssertionError
        ):
            self.assertEqual(
                wx.NOT_FOUND, wxhelper.display_index(point=(0, 0))
            )

    def test_an_empty_work_area_gives_the_whole_display(self):
        with mock.patch.object(
            wx.Display, "GetClientArea", return_value=wx.Rect()
        ):
            area = wxhelper.work_area(0)
        self.assertEqual(tuple(wx.Display(0).GetGeometry()), area)

    def test_no_lookup_outside_the_helpers(self):
        self.assertEqual([], unguarded_lookups())


def unguarded_lookups():
    """wx.Display made, or a display looked up (also by wx's
    CentreOnParent), other than through wxhelper: only a loop over
    range(wx.Display.GetCount()) may make one itself."""
    root = os.path.join(os.path.dirname(test.__file__), "..", "taskcoachlib")
    found = []
    for folder, folders, files in os.walk(root):
        folders[:] = [f for f in folders if f not in ("thirdparty",)]
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(folder, name)
            relative = os.path.relpath(path, root)
            if relative in ("tools/wxhelper.py", "workarounds/display.py"):
                continue
            with open(path, encoding="utf-8") as source:
                tree = ast.parse(source.read())
            loop_names = _display_loop_names(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                called = ast.unparse(node.func)
                if called in (
                    "wx.Display.GetFromPoint",
                    "wx.Display.GetFromWindow",
                ) or called.endswith(".CentreOnParent"):
                    found.append("%s:%d %s" % (relative, node.lineno, called))
                elif called == "wx.Display" and not (
                    len(node.args) == 1
                    and isinstance(node.args[0], ast.Name)
                    and node.args[0].id in loop_names
                ):
                    found.append(
                        "%s:%d %s" % (relative, node.lineno, ast.unparse(node))
                    )
    return found


def _display_loop_names(tree):
    """The names bound by loops over range(wx.Display.GetCount())."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.comprehension)):
            if ast.unparse(node.iter) == "range(wx.Display.GetCount())" and (
                isinstance(node.target, ast.Name)
            ):
                names.add(node.target.id)
    return names


class WindowsDisplayTest(test.wxTestCase):
    """Windows' wx.Display replacement (workarounds/display.py, kept
    until Windows users test its removal: D6) finds a maximized
    window's monitor; it tested the corner, at -8, -8 off the monitor,
    and found none."""

    def windows_display(self):
        import importlib
        import sys
        import types

        from taskcoachlib.workarounds import display

        monitor = (0, 0, 1920, 1080)
        win32api = types.SimpleNamespace(
            EnumDisplayMonitors=lambda *args: [(1, None, monitor)],
            GetMonitorInfo=lambda handle: {
                "Monitor": monitor,
                "Work": (0, 0, 1920, 1040),
                "Flags": 1,
                "Device": "DISPLAY1",
            },
        )
        with mock.patch.dict(sys.modules, {"win32api": win32api}), mock.patch(
            "taskcoachlib.operating_system.isWindows", return_value=True
        ), mock.patch.object(wx, "Display", wx.Display):
            replacement = importlib.reload(display).Display
        importlib.reload(display)  # As on this system again
        return replacement

    def test_a_maximized_window_is_on_its_monitor(self):
        window = mock.Mock(
            GetRect=lambda: wx.Rect(-8, -8, 1936, 1056),
            GetPosition=lambda: wx.Point(-8, -8),
            GetWindowStyle=lambda: wx.RESIZE_BORDER,
        )
        with mock.patch.object(wx.SystemSettings, "GetMetric", return_value=4):
            self.assertEqual(0, self.windows_display().GetFromWindow(window))
