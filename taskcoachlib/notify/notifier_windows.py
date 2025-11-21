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

from .notifier import AbstractNotifier
import tempfile, os, wx
from taskcoachlib.thirdparty import snarl


class SnarlNotifier(AbstractNotifier):
    def getName(self):
        return "Snarl"

    def isAvailable(self):
        try:
            return bool(snarl.snGetVersion())
        except Exception:
            return False

    def notify(self, title, summary, bitmap, **kwargs):
        # Hum. Snarl needs a file.
        fd, filename = tempfile.mkstemp(".png")
        os.close(fd)
        bitmap.SaveFile(filename, wx.BITMAP_TYPE_PNG)
        try:
            snarl.snShowMessage(
                title.encode("UTF-8"),
                summary.encode("UTF-8"),
                iconPath=filename,
            )
        finally:
            os.remove(filename)


AbstractNotifier.register(SnarlNotifier())
