"""
Task Coach - Your friendly task manager
Copyright (C) 2011 Task Coach developers <developers@taskcoach.org>

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

import wx
from taskcoachlib import operating_system

if operating_system.isWindows():
    import win32api  # pylint: disable=F0401

    class Display(object):
        """
        This class replaces wx.Display on MSW; the original only
        enumerates the displays at app initialization so when people
        start unplugging/replugging monitors things go wrong. Not all
        methods are implemented.
        """

        @staticmethod
        def GetCount():
            return len(win32api.EnumDisplayMonitors(None, None))

        @staticmethod
        def GetFromPoint(p):
            for idx, (_, _, (x1, y1, x2, y2)) in enumerate(
                win32api.EnumDisplayMonitors(None, None)
            ):
                if p.x >= x1 and p.x < x2 and p.y >= y1 and p.y < y2:
                    return idx
            return wx.NOT_FOUND

        @staticmethod
        def GetFromWindow(window):
            # The window's centre: a maximized window's corner is off
            # its monitor (at -8, -8)
            x, y, width, height = window.GetRect()
            return Display.GetFromPoint(
                wx.Point(x + width // 2, y + height // 2)
            )

        def __init__(self, index):
            self.hMonitor, _, (self.x, self.y, x2, y2) = (
                win32api.EnumDisplayMonitors(None, None)[index]
            )
            self.w = x2 - self.x
            self.h = y2 - self.y

        def GetClientArea(self):
            ns = win32api.GetMonitorInfo(self.hMonitor)
            x1, y1, x2, y2 = ns["Work"]
            return wx.Rect(x1, y1, x2 - x1, y2 - y1)

        def GetGeometry(self):
            ns = win32api.GetMonitorInfo(self.hMonitor)
            x1, y1, x2, y2 = ns["Monitor"]
            return wx.Rect(x1, y1, x2 - x1, y2 - y1)

        def GetName(self):
            ns = win32api.GetMonitorInfo(self.hMonitor)
            return ns["Device"]

        def IsPrimary(self):
            ns = win32api.GetMonitorInfo(self.hMonitor)
            return bool(ns["Flags"] & 1)

    # Monkey-patching so the workaround applies to third party code as
    # well
    wx.Display = Display
