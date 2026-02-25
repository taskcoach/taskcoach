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

from taskcoachlib.command import (
    NewEffortCommand,
    EditEffortStopDateTimeCommand,
)
from taskcoachlib.domain import effort, date
from taskcoachlib.i18n import _
from taskcoachlib.notify import NotificationFrameBase, NotificationCenter
from taskcoachlib.patterns import Observer
from taskcoachlib.powermgt import IdleNotifier
from pubsub import pub
from taskcoachlib import render
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
import wx


class WakeFromIdleFrame(NotificationFrameBase):
    def __init__(self, idleTime, effort, displayedEfforts, *args, **kwargs):
        self._idleTime = idleTime
        self._effort = effort
        self._displayed = displayedEfforts
        self._lastActivity = 0
        super().__init__(*args, **kwargs)

    def add_inner_content(self, sizer, panel):
        idleTimeFormatted = render.dateTime(self._idleTime)
        sizer.Add(
            wx.StaticText(
                panel,
                wx.ID_ANY,
                _(
                    "No user input since %s. The following task was\nbeing tracked:"
                )
                % idleTimeFormatted,
            )
        )
        sizer.Add(
            wx.StaticText(panel, wx.ID_ANY, self._effort.task().subject())
        )

        btnNothing = wx.Button(panel, wx.ID_ANY, _("Do nothing"))
        btnStopAt = wx.Button(
            panel, wx.ID_ANY, _("Stop it at %s") % idleTimeFormatted
        )
        btnStopResume = wx.Button(
            panel,
            wx.ID_ANY,
            _("Stop it at %s and resume now") % idleTimeFormatted,
        )

        sizer.Add(btnNothing, 0, wx.EXPAND | wx.ALL, 1)
        sizer.Add(btnStopAt, 0, wx.EXPAND | wx.ALL, 1)
        sizer.Add(btnStopResume, 0, wx.EXPAND | wx.ALL, 1)

        btnNothing.Bind(wx.EVT_BUTTON, self.DoNothing)
        btnStopAt.Bind(wx.EVT_BUTTON, self.DoStopAt)
        btnStopResume.Bind(wx.EVT_BUTTON, self.DoStopResume)

    def close_button(self, panel):
        return None

    def DoNothing(self, event):
        self._displayed.remove(self._effort)
        self.do_close()

    def DoStopAt(self, event):
        self._displayed.remove(self._effort)
        EditEffortStopDateTimeCommand(
            newValue=self._idleTime, items=[self._effort]
        ).do()
        self.do_close()

    def DoStopResume(self, event):
        self._displayed.remove(self._effort)
        EditEffortStopDateTimeCommand(
            newValue=self._idleTime, items=[self._effort]
        ).do()
        NewEffortCommand(items=[self._effort.task()]).do()
        self.do_close()


class IdleController(Observer, IdleNotifier):
    def __init__(self, mainWindow, settings, effortList):
        self._mainWindow = mainWindow
        self._settings = settings
        self._effortList = effortList
        self._displayed = set()

        super().__init__()

        self.__tracker = effort.EffortListTracker(self._effortList)
        self.__tracker.subscribe(self.__onTrackedChanged, "effortlisttracker")

        pub.subscribe(self.poweroff, "powermgt.off")
        pub.subscribe(self.poweron, "powermgt.on")

    def __onTrackedChanged(self, efforts):
        if len(efforts):
            self.resume()
        else:
            self.pause()

    def get_min_idle_time(self):
        return self._settings.getint("feature", "minidletime") * 60

    def wake(self, timestamp):
        self._lastActivity = timestamp
        self.OnWake()

    def OnWake(self):
        for effort in self.__tracker.trackedEfforts():
            if effort not in self._displayed:
                self._displayed.add(effort)
                frm = WakeFromIdleFrame(
                    date.DateTime.fromtimestamp(self._lastActivity),
                    effort,
                    self._displayed,
                    _("Notification"),
                    wx_bitmap=icon_catalog.get_bitmap(
                        "nuvola_apps_korganizer", LIST_ICON_SIZE
                    ),
                )
                NotificationCenter().notify_frame(frm)
