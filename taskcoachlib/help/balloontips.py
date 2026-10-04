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

from taskcoachlib.config import settings
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
from taskcoachlib.widgets import balloontip


class BalloonTipManager(balloontip.BalloonTipManager):
    def AddBalloonTip(
        self, name, target, message=None, title=None, get_rect=None
    ):
        if settings.get("balloontips", name):
            super().AddBalloonTip(
                target,
                message=message,
                title=title,
                bitmap=icon_catalog.get_bitmap(
                    "nuvola_apps_ktip", LIST_ICON_SIZE
                ),
                get_rect=get_rect,
                name=name,
            )

    def on_balloon_tip_show(self, name=None):
        settings.set("balloontips", name, False)
