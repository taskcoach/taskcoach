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

# This module is meant to be imported like this:
#   from taskcoachlib import operating_system
# so that the function calls read:
#   operating_system.isWindows(), operating_system.isMac(), etc.


def isMac():
    return isPlatform("MAC")


def isWindows():
    return isPlatform("MSW")


def isGTK():
    return isPlatform("GTK")


def isWayland():
    """Detect if running on Wayland display server.

    Note: AUI floating windows are broken on Wayland due to protocol
    limitations. See docs/WAYLAND_ISSUES.md#aui-docking for details.
    """
    return (
        os.environ.get("XDG_SESSION_TYPE") == "wayland"
        or os.environ.get("WAYLAND_DISPLAY") is not None
    )


def isPlatform(threeLetterPlatformAbbreviation, wxPlatform=wx.Platform):
    return "__WX%s__" % threeLetterPlatformAbbreviation == wxPlatform
