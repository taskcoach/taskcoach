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
from taskcoachlib import patterns
from taskcoachlib.domain import task


class StatusBar(wx.StatusBar):
    def __init__(self, parent, viewer):
        super().__init__(parent)
        self.SetFieldsCount(2)
        self.parent = parent
        self.viewer = viewer
        # Two waits for one display, kept apart: a temporary message
        # and the viewer's status each restart their own
        self.__status_later = patterns.later.debounced(
            self, 500, self._displayStatus
        )
        self.__message_later = patterns.later.debounced(
            self, 3000, self._displayStatus
        )
        patterns.Publisher().registerObserver(
            self.on_viewer_status_changed,
            eventType=viewer.status_event_type(),
            eventSource=viewer,
        )
        # The counts of statuses: the clock changes them too
        patterns.Publisher().registerObserver(
            self.on_viewer_status_changed,
            eventType=task.Task.statusChangedEventType(),
        )
        self.on_viewer_status_changed()
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

    def on_viewer_status_changed(self, event=None):  # pylint: disable=W0613
        # Give viewer a chance to update first and only update when the viewer
        # hasn't changed status for 0.5 seconds.
        self.__status_later()

    def _displayStatus(self):
        try:
            status1, status2 = self.viewer.statusMessages()
        except AttributeError:
            return  # Viewer container contains no viewers
        super().SetStatusText(status1, 0)
        super().SetStatusText(status2, 1)

    def SetStatusText(self, message, pane=0):  # pylint: disable=W0221
        super().SetStatusText(message, pane)
        self.__message_later()

    def Destroy(self):  # pylint: disable=W0221
        for eventType in self.wxEventTypes:
            self.parent.Unbind(eventType)
        # No callbacks after destruction
        patterns.Publisher().removeObserver(self.on_viewer_status_changed)
        super().Destroy()
