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

import taskcoachlib.gui.menu
from pubsub import pub
import wx.lib.agw.aui as aui
import wx


class ViewerContainer(object):
    """ViewerContainer is a container of viewers. It has a containerWidget
    that displays the viewers. The containerWidget is assumed to be
    an AUI managed frame. The ViewerContainer knows which of its viewers
    is active and dispatches method calls to the active viewer or to the
    first viewer that can handle the method. This allows other GUI
    components, e.g. menu's, to talk to the ViewerContainer as were
    it a regular viewer."""

    def __init__(self, containerWidget, settings, *args, **kwargs):
        self.containerWidget = containerWidget
        self._notifyActiveViewer = False
        self.__bind_event_handlers()
        self._settings = settings
        self.viewers = []
        super().__init__(*args, **kwargs)

    def componentsCreated(self):
        self._notifyActiveViewer = True
        # Activate the first viewer (TaskViewer) as the default at startup
        if self.viewers:
            self.activateViewer(self.viewers[0])

    def advanceSelection(self, forward):
        """Activate the next viewer if forward is true else the previous
        viewer."""
        if len(self.viewers) <= 1:
            return  # Not enough viewers to advance selection
        active_viewer = self.activeViewer()
        current_index = (
            self.viewers.index(active_viewer) if active_viewer else 0
        )
        minimum_index, maximum_index = 0, len(self.viewers) - 1
        if forward:
            new_index = (
                current_index + 1
                if minimum_index <= current_index < maximum_index
                else minimum_index
            )
        else:
            new_index = (
                current_index - 1
                if minimum_index < current_index <= maximum_index
                else maximum_index
            )
        self.activateViewer(self.viewers[new_index])

    def isViewerContainer(self):
        """Return whether this is a viewer container or an actual viewer."""
        return True

    def __bind_event_handlers(self):
        """Register for pane closing, activating and floating events."""
        self.containerWidget.Bind(aui.EVT_AUI_PANE_CLOSE, self.onPageClosed)
        self.containerWidget.Bind(
            aui.EVT_AUI_PANE_ACTIVATED, self.onPageChanged
        )
        self.containerWidget.Bind(aui.EVT_AUI_PANE_FLOATED, self.onPageFloated)

    def __getitem__(self, index):
        return self.viewers[index]

    def __len__(self):
        return len(self.viewers)

    def addViewer(self, viewer, floating=False):
        """Add a new pane with the specified viewer."""
        self.containerWidget.addPane(viewer, viewer.title(), floating=floating)
        self.viewers.append(viewer)
        if len(self.viewers) == 1:
            self.activateViewer(viewer)
        pub.subscribe(self.onStatusChanged, viewer.viewerStatusEventType())

    def closeViewer(self, viewer):
        """Close the specified viewer."""
        if viewer == self.activeViewer():
            self.advanceSelection(False)
        pane = self.containerWidget.manager.GetPane(viewer)
        self.containerWidget.manager.ClosePane(pane)

    def __getattr__(self, attribute):
        """Forward unknown attributes to the active viewer or the first
        viewer if there is no active viewer."""
        return getattr(self.activeViewer() or self.viewers[0], attribute)

    def activeViewer(self):
        """Return the active (selected) viewer."""
        all_panes = self.containerWidget.manager.GetAllPanes()
        for pane in all_panes:
            if pane.IsToolbar():
                continue
            if pane.HasFlag(pane.optionActive):
                if pane.IsNotebookControl():
                    notebook = aui.GetNotebookRoot(all_panes, pane.notebook_id)
                    return notebook.window.GetCurrentPage()
                else:
                    return pane.window
        return None

    def activateViewer(self, viewer_to_activate):
        """Activate (select) the specified viewer."""
        self.containerWidget.manager.ActivatePane(viewer_to_activate)
        paneInfo = self.containerWidget.manager.GetPane(viewer_to_activate)
        if paneInfo.IsNotebookPage():
            self.containerWidget.manager.ShowPane(viewer_to_activate, True)
        self.sendViewerStatusEvent()

    def __del__(self):
        pass  # Don't forward del to one of the viewers.

    def onStatusChanged(self, viewer):
        if self.activeViewer() == viewer:
            self.sendViewerStatusEvent()
        pub.sendMessage("all.viewer.status", viewer=viewer)

    def onPageChanged(self, event):
        """Handle pane activation events from AUI."""
        self.__ensure_active_viewer_has_focus()
        self.sendViewerStatusEvent()
        if self._notifyActiveViewer and self.activeViewer() is not None:
            self.activeViewer().activate()
        event.Skip()

    def sendViewerStatusEvent(self):
        pub.sendMessage("viewer.status")

    def __ensure_active_viewer_has_focus(self):
        """Set focus on active viewer, unless a text control inside it has focus.

        Simple rule: always set focus on the active viewer EXCEPT when a text
        control (search box, etc.) inside that viewer already has focus.
        """
        viewer = self.activeViewer()
        if not viewer:
            return

        # Check if a text control inside the active viewer has focus
        window = wx.Window.FindFocus()
        if isinstance(window, (wx.TextCtrl, wx.SearchCtrl, wx.ComboBox)):
            # Walk up to see if this text control is inside the active viewer
            parent = window
            while parent:
                if parent == viewer:
                    return  # Text control is in active viewer, don't steal focus
                parent = parent.GetParent()

        # Set focus on the viewer
        try:
            viewer.SetFocus()
        except RuntimeError:
            pass

    def onPageClosed(self, event):
        if event.GetPane().IsToolbar():
            return
        window = event.GetPane().window
        if hasattr(window, "GetPage"):
            # Window is a notebook, close each of its pages
            for pageIndex in range(window.GetPageCount()):
                self.__close_viewer(window.GetPage(pageIndex))
        else:
            # Window is a viewer, close it
            self.__close_viewer(window)
        # Make sure we have an active viewer
        if not self.activeViewer():
            self.activateViewer(self.viewers[0])
        event.Skip()

    def __close_viewer(self, viewer):
        """Close the specified viewer and unsubscribe all its event
        handlers."""
        # When closing an AUI managed frame, we get two close events,
        # be prepared:
        if viewer in self.viewers:
            self.viewers.remove(viewer)
            # Unsubscribe from the viewer's status event before detaching
            try:
                pub.unsubscribe(self.onStatusChanged, viewer.viewerStatusEventType())
            except Exception:
                pass  # May already be unsubscribed
            viewer.detach()

    @staticmethod
    def onPageFloated(event):
        """Give floating pane accelerator keys for activating next and previous
        viewer."""
        viewer = event.GetPane().window
        table = wx.AcceleratorTable(
            [
                (
                    wx.ACCEL_CTRL,
                    wx.WXK_PAGEDOWN,
                    taskcoachlib.gui.menu.activateNextViewerId,
                ),
                (
                    wx.ACCEL_CTRL,
                    wx.WXK_PAGEUP,
                    taskcoachlib.gui.menu.activatePreviousViewerId,
                ),
            ]
        )
        viewer.SetAcceleratorTable(table)
