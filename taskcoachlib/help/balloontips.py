"""
Task Coach - Your friendly task manager
Copyright (C) 2012 Task Coach developers <developers@taskcoach.org>

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

from taskcoachlib.widgets import balloontip
import wx


class BalloonTipManager(balloontip.BalloonTipManager):
    def AddBalloonTip(
        self, settings, name, target, message=None, title=None, getRect=None
    ):
        if settings.getboolean("balloontips", name):
            super().AddBalloonTip(
                target,
                message=message,
                title=title,
                bitmap=wx.ArtProvider.GetBitmap(
                    "nuvola_apps_ktip", wx.ART_MENU, (16, 16)
                ),
                getRect=getRect,
                name=name,
                settings=settings,
            )

    def OnBalloonTipShow(self, name=None, settings=None):
        settings.setboolean("balloontips", name, False)
