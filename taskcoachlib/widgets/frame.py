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
import wx.lib.agw.aui as aui
from taskcoachlib import operating_system


# --- Rebuild guard: block motion events during list/tree rebuilds ---

# Motion event types to eat during rebuild.  Only motion events are
# suppressed - clicks, keyboard, and scroll are passed through so
# the app remains responsive.  Motion events drive the AUI cascade
# (OnMotion -> hover -> repaint -> repeat) and must be suppressed.
_MOTION_EVENTS = {
    wx.wxEVT_MOTION,
    wx.wxEVT_ENTER_WINDOW, wx.wxEVT_LEAVE_WINDOW,
}


class _RebuildInputFilter(wx.EventFilter):
    """Silently eat mouse motion events during rebuild.

    No visual effect - no gray, no disable flicker.  Just drops
    motion events so mouse movement can't drive the AUI cascade.
    Clicks, keyboard, and scroll events pass through normally.
    """
    active = False
    _refcount = 0
    _release_timer = None

    def FilterEvent(self, event):
        if not self.active:
            return self.Event_Skip
        if event.GetEventType() in _MOTION_EVENTS:
            return self.Event_Processed
        return self.Event_Skip

    def acquire(self):
        """Called at start of each RefreshAllItems."""
        if self._release_timer is not None:
            self._release_timer.Stop()
            self._release_timer = None
        self._refcount += 1
        self.active = True

    def release(self):
        """Called when a widget's refresh idle completes.

        Decrements refcount.  When all widgets done, schedules a
        deferred deactivation (1s) to cover the post-rebuild cascade.
        """
        self._refcount = max(0, self._refcount - 1)
        if self._refcount == 0:
            self._release_timer = wx.CallLater(
                1000, self._deferred_release,
            )

    def _deferred_release(self):
        self._release_timer = None
        if self._refcount == 0:
            self.active = False


_input_filter = _RebuildInputFilter()
_filter_installed = False


def _ensure_filter_installed():
    global _filter_installed
    if not _filter_installed:
        wx.EvtHandler.AddFilter(_input_filter)
        _filter_installed = True


def _install_sash_resize_optimization(manager):
    """Install throttling for AUI sash resize operations.

    AUI's LIVE_RESIZE mode calls Update() on every mouse move during sash drag,
    which can cause flickering due to expensive repaints (DoUpdate takes 50-190ms).
    This wrapper throttles updates to ~30fps to reduce CPU load while maintaining
    visual feedback.
    """
    import time

    original_on_motion = getattr(manager, 'OnMotion', None)
    if not original_on_motion:
        return

    # Throttle state
    min_interval = 0.033  # ~30fps max update rate
    last_update_time = 0

    # Throttle updates during sash drag
    def throttled_on_motion(event):
        nonlocal last_update_time
        action = getattr(manager, '_action', 0)
        # action 3 = actionResize (sash drag)
        if action == 3:
            now = time.time()
            if now - last_update_time < min_interval:
                return
            last_update_time = now
        return original_on_motion(event)

    manager.OnMotion = throttled_on_motion


class AuiManagedFrameWithDynamicCenterPane(wx.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Build AUI style flags with live resize for visual feedback when dragging sashes
        agw_style = (
            aui.AUI_MGR_DEFAULT
            | aui.AUI_MGR_ALLOW_ACTIVE_PANE
            | aui.AUI_MGR_LIVE_RESIZE  # Live visual feedback when dragging sashes
        )

        if not operating_system.isWindows():
            # With this style on Windows, you can't dock back floating frames
            agw_style |= aui.AUI_MGR_USE_NATIVE_MINIFRAMES

        self.manager = aui.AuiManager(self, agw_style)

        # Throttle AUI sash resize updates to ~30fps to reduce flickering
        _install_sash_resize_optimization(self.manager)

        self.manager.SetAutoNotebookStyle(
            aui.AUI_NB_TOP
            | aui.AUI_NB_CLOSE_BUTTON
            | aui.AUI_NB_SUB_NOTEBOOK
            | aui.AUI_NB_SCROLL_BUTTONS
        )
        self.bind_events()

    def bind_events(self):
        for event_type in aui.EVT_AUI_PANE_CLOSE, aui.EVT_AUI_PANE_FLOATING:
            self.manager.Bind(event_type, self.on_pane_closing_or_floating)

    def on_pane_closing_or_floating(self, event):
        pane = event.GetPane()
        docked_panes = self.docked_panes()
        if self.is_center_pane(pane) and len(docked_panes) == 1:
            event.Veto()
        else:
            event.Skip()
            if self.is_center_pane(pane):
                if pane in docked_panes:
                    docked_panes.remove(pane)
                docked_panes[0].Center()

    def add_pane(self, window, caption, name, floating=False):
        x, y = 0, 0
        if self.GetTopLevelParent().IsShown():
            x, y = window.GetPosition()
            x, y = window.ClientToScreen(x, y)
        pane_info = aui.AuiPaneInfo()
        pane_info = (
            pane_info.CloseButton(True)
            .Floatable(True)
            .Name(name)
            .Caption(caption)
            .Right()
            .FloatingSize((300, 200))
            .BestSize((200, 200))
            .FloatingPosition((x + 30, y + 30))
            .CaptionVisible()
            .MaximizeButton()
            .DestroyOnClose()
        )
        if floating:
            pane_info.Float()
        if not self.docked_panes():
            # First pane goes to center
            pane_info = pane_info.Center()
        self.manager.AddPane(window, pane_info)
        self.manager.Update()

    def set_pane_title(self, window, title):
        self.manager.GetPane(window).Caption(title)

    def docked_panes(self):
        return [
            pane
            for pane in self.manager.GetAllPanes()
            if not pane.IsToolbar()
            and not pane.IsFloating()
            and not pane.IsNotebookPage()
        ]

    def float(self, window):
        self.manager.GetPane(window).Float()

    @staticmethod
    def is_center_pane(pane):
        return pane.dock_direction_get() == aui.AUI_DOCK_CENTER
