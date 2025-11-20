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
from pubsub import pub


class StatusBar(wx.StatusBar):
    def __init__(self, parent, viewer):
        super().__init__(parent)
        self.SetFieldsCount(2)
        self.parent = parent
        self.viewer = viewer
        self.__timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onUpdateStatus, self.__timer)
        pub.subscribe(self.onViewerStatusChanged, "viewer.status")
        self.scheduledStatusDisplay = None
        self.onViewerStatusChanged()
        self.wxEventTypes = (wx.EVT_MENU_HIGHLIGHT_ALL, wx.EVT_TOOL_ENTER)
        for eventType in self.wxEventTypes:
            parent.Bind(eventType, self.resetStatusBar)

    def resetStatusBar(self, event):
        """Unfortunately, the menu's and toolbar don't restore the
        previous statusbar text after they have displayed their help
        text, so we have to do it by hand."""
        try:
            toolOrMenuId = (
                event.GetSelection()
            )  # for CommandEvent from the Toolbar
        except AttributeError:
            toolOrMenuId = event.GetMenuId()  # for MenuEvent
        if toolOrMenuId == -1:
            self._displayStatus()
        event.Skip()

    def onViewerStatusChanged(self):
        # Give viewer a chance to update first and only update when the viewer
        # hasn't changed status for 0.5 seconds.
        self.__timer.Start(500, oneShot=True)

    def onUpdateStatus(self, event):  # pylint: disable=W0613
        if self.__timer:
            self.__timer.Stop()
        self._displayStatus()

    def _displayStatus(self):
        try:
            status1, status2 = self.viewer.statusMessages()
        except AttributeError:
            return  # Viewer container contains no viewers
        super().SetStatusText(status1, 0)
        super().SetStatusText(status2, 1)

    def SetStatusText(
        self, message, pane=0, delay=3000
    ):  # pylint: disable=W0221
        if self.scheduledStatusDisplay:
            self.scheduledStatusDisplay.Stop()
        super().SetStatusText(message, pane)
        self.scheduledStatusDisplay = wx.CallLater(delay, self._displayStatus)

    def Destroy(self):  # pylint: disable=W0221
        for eventType in self.wxEventTypes:
            self.parent.Unbind(eventType)
        # Stop the status update timer to prevent crashes during destruction
        if self.__timer and self.__timer.IsRunning():
            self.__timer.Stop()
        if self.scheduledStatusDisplay:
            self.scheduledStatusDisplay.Stop()
        super().Destroy()
