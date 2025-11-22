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

import wx

# FIXME: Adding duplicate image handler for 'Windows bitmap file'
# FIXME: Adding duplicate animation handler for '1' type
# FIXME: Adding duplicate animation handler for '2' type
import wx.adv
import os
import sys
from taskcoachlib import i18n
from taskcoachlib.tools import wxhelper


def get_resource_path(relative_path):
    """Get absolute path to resource - works for development and frozen apps."""
    if getattr(sys, 'frozen', False):
        # Running as frozen executable
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS  # PyInstaller
        else:
            base_path = os.path.dirname(sys.executable)  # py2exe
    else:
        # Running in normal Python (development)
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)


class SplashScreen(wx.adv.SplashScreen):
    def __init__(self):
        # Load splash.png from icons directory
        splash_path = get_resource_path(os.path.join('icons', 'splash.png'))
        image = wx.Image(splash_path)

        if i18n.currentLanguageIsRightToLeft():
            # RTL languages cause the bitmap to be mirrored too, but because
            # the splash image is not internationalized, we have to mirror it
            # (back). Unfortunately using SetLayoutDirection() on the
            # SplashWindow doesn't work.
            bitmap = image.Mirror().ConvertToBitmap()
        else:
            bitmap = image.ConvertToBitmap()
        super().__init__(
            bitmap,
            wx.adv.SPLASH_CENTRE_ON_SCREEN | wx.adv.SPLASH_TIMEOUT,
            4000,
            None,
            -1,
        )
        # Reposition to app's monitor (uses saved monitor_index from settings)
        wxhelper.centerOnAppMonitor(self)
