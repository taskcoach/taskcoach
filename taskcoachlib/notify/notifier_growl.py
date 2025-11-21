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
import struct
import sys
import tempfile
import wx

import gntp.notifier as Growl
from taskcoachlib import meta
from .notifier import AbstractNotifier


class GrowlNotifier(AbstractNotifier):
    def __init__(self):
        super().__init__()
        try:
            # pylint: disable=E1101
            self._notifier = Growl.GrowlNotifier(
                applicationName=meta.name, notifications=["Reminder"]
            )
            self._notifier.register()
        except Exception:
            self._available = False  # Growl registration failed
        else:
            self._available = True

    def getName(self):
        return "Growl"

    def isAvailable(self):
        return self._available

    def notify(self, title, summary, bitmap, **kwargs):
        # Not really efficient...
        fd, filename = tempfile.mkstemp(".png")
        os.close(fd)
        try:
            bitmap.SaveFile(filename, wx.BITMAP_TYPE_PNG)
            self._notifier.notify(
                noteType="Reminder",
                icon=open(filename, "rb").read(),
                title=title,
                description=summary,
                sticky=True,
            )
        finally:
            os.remove(filename)


AbstractNotifier.register(GrowlNotifier())
