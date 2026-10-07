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

from taskcoachlib import patterns
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

    def __init__(self, container_widget, *args, **kwargs):
        self.containerWidget = container_widget
        self._notifyActiveViewer = False
        self._focus_skipped = False  # While the main window was minimized
        self.__bind_event_handlers()
        self.viewers = []
        super().__init__(*args, **kwargs)

    def components_created(self):
        self._notifyActiveViewer = True
        # Activate the first viewer (TaskViewer) as the default at startup
        if self.viewers:
            self.activate_viewer(self.viewers[0])

    def advance_selection(self, forward):
        """Activate the next viewer if forward is true else the previous
        viewer."""
        if len(self.viewers) <= 1:
            return  # Not enough viewers to advance selection
        active_viewer = self.active_viewer()
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
        self.activate_viewer(self.viewers[new_index])

    def __bind_event_handlers(self):
        """Register for pane closing, activating and floating events."""
        self.containerWidget.Bind(aui.EVT_AUI_PANE_CLOSE, self.on_page_closed)
        self.containerWidget.Bind(
            aui.EVT_AUI_PANE_ACTIVATED, self.on_page_changed
        )

    def __getitem__(self, index):
        return self.viewers[index]

    def __len__(self):
        return len(self.viewers)

    def add_viewer(self, viewer, floating=False):
        """Add a new pane with the specified viewer."""
        self.containerWidget.add_pane(
            viewer, viewer.title(), floating=floating
        )
        self.viewers.append(viewer)
        if len(self.viewers) == 1:
            self.activate_viewer(viewer)
        patterns.Publisher().registerObserver(
            self.on_status_changed,
            eventType=viewer.viewer_status_event_type(),
            eventSource=viewer,
        )

    def close_viewer(self, viewer):
        """Close the specified viewer."""
        if viewer == self.active_viewer():
            self.advance_selection(False)
        pane = self.containerWidget.manager.GetPane(viewer)
        self.containerWidget.manager.ClosePane(pane)

    def __getattr__(self, attribute):
        """Forward unknown attributes to the active viewer or the first
        viewer if there is no active viewer."""
        return getattr(self.active_viewer() or self.viewers[0], attribute)

    def active_viewer(self):
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

    def activate_viewer(self, viewer_to_activate):
        """Activate (select) the specified viewer."""
        self.containerWidget.manager.ActivatePane(viewer_to_activate)
        pane_info = self.containerWidget.manager.GetPane(viewer_to_activate)
        if pane_info.IsNotebookPage():
            self.containerWidget.manager.ShowPane(viewer_to_activate, True)
        # Its window in front for the keys to reach it: a floating
        # view's own, or the main window from a floating view
        # (docs/AUI.md, Floating Views and the Keys)
        window = wx.GetTopLevelParent(viewer_to_activate)
        if window.IsShown() and not window.IsActive():
            window.Raise()
        self.send_viewer_status_event()

    def __del__(self):
        pass  # Don't forward del to one of the viewers.

    @classmethod
    def all_viewers_status_event_type(cls):
        """A viewer's status changed: the container is the source and
        the viewer the value."""
        return "all.viewer.status"

    @classmethod
    def status_event_type(cls):
        """The active viewer's status changed, or another viewer became
        active: the container is the source."""
        return "viewer.status"

    def on_status_changed(self, event):
        for viewer in event.sources():
            if self.active_viewer() == viewer:
                self.send_viewer_status_event()
            patterns.Event(
                self.all_viewers_status_event_type(), self, viewer
            ).send()

    def on_page_changed(self, event):
        """A pane activated. Answered only for the view the main
        window's manager has active: a floating view's own frame
        reports first, while the main window still has the old view
        active, and focusing that would take the keys back from the
        view clicked; the main window reports next (docs/AUI.md,
        Floating Views and the Keys). AUI's report names no manager."""
        if not self.__is_or_holds(event.GetPane(), self.active_viewer()):
            event.Skip()
            return
        self.__ensure_active_viewer_has_focus()
        self.send_viewer_status_event()
        if self._notifyActiveViewer and self.active_viewer() is not None:
            self.active_viewer().activate()
        event.Skip()

    @staticmethod
    def __is_or_holds(window, viewer):
        """Whether the pane's window is the viewer or holds it (a
        notebook's pane is the notebook)."""
        while viewer is not None:
            if viewer is window:
                return True
            viewer = viewer.GetParent()
        return False

    def focus_skipped_viewer(self):
        """Focus the active viewer if that was skipped while the main
        window was minimized."""
        if self._focus_skipped:
            self.__ensure_active_viewer_has_focus()

    def send_viewer_status_event(self):
        patterns.Event(self.status_event_type(), self).send()

    def __ensure_active_viewer_has_focus(self):
        """Set focus on active viewer, unless a text control inside it has focus.

        Simple rule: always set focus on the active viewer EXCEPT when a text
        control (search box, etc.) inside that viewer already has focus.
        """
        viewer = self.active_viewer()
        if not viewer:
            return
        # Focusing a minimized window restores it on X11: the window
        # manager is asked to activate it
        if wx.GetTopLevelParent(viewer).IsIconized():
            self._focus_skipped = True
            return
        self._focus_skipped = False

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

    def on_page_closed(self, event):
        if event.GetPane().IsToolbar():
            return
        window = event.GetPane().window
        if hasattr(window, "GetPage"):
            # Window is a notebook, close each of its pages
            for page_index in range(window.GetPageCount()):
                self.__close_viewer(window.GetPage(page_index))
        else:
            # Window is a viewer, close it
            self.__close_viewer(window)
        # Make sure we have an active viewer
        if not self.active_viewer():
            self.activate_viewer(self.viewers[0])
        event.Skip()

    def __close_viewer(self, viewer):
        """Close the specified viewer and unsubscribe all its event
        handlers."""
        # When closing an AUI managed frame, we get two close events,
        # be prepared:
        if viewer in self.viewers:
            self.viewers.remove(viewer)
            # Unsubscribe from the viewer's status event before detaching
            patterns.Publisher().removeObserver(
                self.on_status_changed,
                eventType=viewer.viewer_status_event_type(),
            )
            viewer.detach()
