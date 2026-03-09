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

from contextlib import contextmanager

import wx
import wx.lib.agw.aui as aui
from taskcoachlib import operating_system


# --- Rebuild guard: block input during list/tree rebuilds ---

# Mouse and keyboard event types to eat during rebuild
_INPUT_EVENTS = {
    wx.wxEVT_LEFT_DOWN, wx.wxEVT_LEFT_UP, wx.wxEVT_LEFT_DCLICK,
    wx.wxEVT_RIGHT_DOWN, wx.wxEVT_RIGHT_UP, wx.wxEVT_RIGHT_DCLICK,
    wx.wxEVT_MIDDLE_DOWN, wx.wxEVT_MIDDLE_UP, wx.wxEVT_MIDDLE_DCLICK,
    wx.wxEVT_MOTION, wx.wxEVT_MOUSEWHEEL,
    wx.wxEVT_ENTER_WINDOW, wx.wxEVT_LEAVE_WINDOW,
    wx.wxEVT_KEY_DOWN, wx.wxEVT_KEY_UP, wx.wxEVT_CHAR, wx.wxEVT_CHAR_HOOK,
}


class _RebuildInputFilter(wx.EventFilter):
    """Silently eat mouse and keyboard events during rebuild.

    No visual effect — no gray, no disable flicker.  Just drops
    input events so mouse movement can't drive the AUI cascade.
    Also counts events for diagnostics.
    """
    active = False
    count_motion_eaten = 0
    count_keys_eaten = 0
    count_clicks_eaten = 0
    count_paint = 0

    def FilterEvent(self, event):
        etype = event.GetEventType()
        if self.active:
            if etype == wx.wxEVT_MOTION:
                self.count_motion_eaten += 1
                return self.Event_Processed
            if etype in _INPUT_EVENTS:
                if etype in (wx.wxEVT_KEY_DOWN, wx.wxEVT_KEY_UP,
                             wx.wxEVT_CHAR, wx.wxEVT_CHAR_HOOK):
                    self.count_keys_eaten += 1
                else:
                    self.count_clicks_eaten += 1
                return self.Event_Processed
            if etype == wx.wxEVT_PAINT:
                self.count_paint += 1
        return self.Event_Skip

    def reset_counts(self):
        self.count_motion_eaten = 0
        self.count_keys_eaten = 0
        self.count_clicks_eaten = 0
        self.count_paint = 0


_input_filter = _RebuildInputFilter()
_filter_installed = False

_rebuild_guard_state = {
    'idle_bound': False,
    'widget': None,
    'acquire_time': 0.0,
    'post_dirty': False,
}


def _rebuild_guard_on_idle(event):
    """EVT_IDLE handler — stop blocking input when widget is done.

    Waits one extra idle cycle after _dirty=False because
    OnInternalIdle sets _dirty=False then calls Refresh() which
    queues a paint.  The extra cycle lets that paint process before
    we re-enable input.
    """
    import time
    st = _rebuild_guard_state
    from taskcoachlib.meta.debug import log_step

    if _input_filter.active:
        widget = st['widget']
        elapsed_ms = (time.monotonic() - st['acquire_time']) * 1000

        # Extra cycle after _dirty=False — paint from Refresh() should be done
        if st['post_dirty']:
            f = _input_filter
            log_step('EVT_IDLE — releasing  elapsed=%.0fms  '
                     'motion_eaten=%d clicks_eaten=%d keys_eaten=%d paint=%d'
                     % (elapsed_ms, f.count_motion_eaten, f.count_clicks_eaten,
                        f.count_keys_eaten, f.count_paint),
                     prefix='REBUILD_GUARD')
            _input_filter.active = False
            st['widget'] = None
            st['post_dirty'] = False
        else:
            # Check if the tree widget still has pending layout work
            dirty = False
            if widget is not None:
                main_win = getattr(widget, 'GetMainWindow', lambda: None)()
                if main_win is not None:
                    dirty = getattr(main_win, '_dirty', False)
                    log_step('EVT_IDLE — _dirty=%s  elapsed=%.0fms'
                             % (dirty, elapsed_ms), prefix='REBUILD_GUARD')
                else:
                    log_step('EVT_IDLE — no main_win (calendar?)  elapsed=%.0fms'
                             % elapsed_ms, prefix='REBUILD_GUARD')
            else:
                log_step('EVT_IDLE — no widget  elapsed=%.0fms'
                         % elapsed_ms, prefix='REBUILD_GUARD')

            if dirty:
                event.RequestMore()
                event.Skip()
                return

            # _dirty=False — wait one more cycle for paint to process
            log_step('EVT_IDLE — _dirty=False, waiting one more cycle  elapsed=%.0fms'
                     % elapsed_ms, prefix='REBUILD_GUARD')
            st['post_dirty'] = True
            event.RequestMore()
            event.Skip()
            return

    if st['idle_bound']:
        wx.GetApp().Unbind(wx.EVT_IDLE, handler=_rebuild_guard_on_idle)
        st['idle_bound'] = False
    event.Skip()


@contextmanager
def rebuild_guard(widget=None):
    """Block input during rebuild, release when widget is done.

    Activates an EventFilter that silently eats mouse and keyboard
    events.  On exit, binds EVT_IDLE and checks the widget's _dirty
    flag.  When _dirty is False + one extra idle cycle (for the paint
    from OnInternalIdle's Refresh()), re-enables input.
    No visual effect — no gray, no flicker.
    """
    import time
    st = _rebuild_guard_state
    from taskcoachlib.meta.debug import log_step
    if not _input_filter.active:
        global _filter_installed
        if not _filter_installed:
            wx.EvtHandler.AddFilter(_input_filter)
            _filter_installed = True
            log_step('EventFilter installed', prefix='REBUILD_GUARD')
        _input_filter.reset_counts()
        _input_filter.active = True
        st['acquire_time'] = time.monotonic()
        st['widget'] = widget
        log_step('Input blocked  widget=%s'
                 % (type(widget).__name__ if widget else 'None'),
                 prefix='REBUILD_GUARD')
    try:
        yield
    finally:
        if not st['idle_bound']:
            wx.GetApp().Bind(wx.EVT_IDLE, _rebuild_guard_on_idle)
            st['idle_bound'] = True
            dirty = None
            if widget is not None:
                main_win = getattr(widget, 'GetMainWindow', lambda: None)()
                if main_win is not None:
                    dirty = getattr(main_win, '_dirty', None)
            log_step('EVT_IDLE bound — _dirty=%s  waiting for widget done'
                     % dirty, prefix='REBUILD_GUARD')


def _install_sash_resize_optimization(manager):
    """Install throttling for AUI sash resize operations.

    AUI's LIVE_RESIZE mode calls Update() on every mouse move during sash drag,
    which can cause flickering due to expensive repaints (DoUpdate takes 50-190ms).
    This wrapper throttles updates to ~30fps to reduce CPU load while maintaining
    visual feedback.
    """
    import time

    original_on_motion = getattr(manager, 'OnMotion', None)

    # Throttle state
    state = {
        'last_update_time': 0,
        'min_update_interval': 0.033,  # ~30fps max update rate
    }

    # Throttle updates during sash drag
    if original_on_motion:
        def throttled_on_motion(event):
            action = getattr(manager, '_action', 0)
            # action 3 = actionResize (sash drag)
            if action == 3:
                now = time.time()
                if now - state['last_update_time'] < state['min_update_interval']:
                    # Skip this update - don't call Skip() to prevent other handlers
                    return
                state['last_update_time'] = now
            return original_on_motion(event)
        manager.OnMotion = throttled_on_motion


class AuiManagedFrameWithDynamicCenterPane(wx.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Build AUI style flags with live resize for visual feedback when dragging sashes
        agwStyle = (
            aui.AUI_MGR_DEFAULT
            | aui.AUI_MGR_ALLOW_ACTIVE_PANE
            | aui.AUI_MGR_LIVE_RESIZE  # Live visual feedback when dragging sashes
        )

        if not operating_system.isWindows():
            # With this style on Windows, you can't dock back floating frames
            agwStyle |= aui.AUI_MGR_USE_NATIVE_MINIFRAMES

        self.manager = aui.AuiManager(self, agwStyle)

        # Throttle AUI sash resize updates to ~30fps to reduce flickering
        _install_sash_resize_optimization(self.manager)

        self.manager.SetAutoNotebookStyle(
            aui.AUI_NB_TOP
            | aui.AUI_NB_CLOSE_BUTTON
            | aui.AUI_NB_SUB_NOTEBOOK
            | aui.AUI_NB_SCROLL_BUTTONS
        )
        self.bindEvents()

    def bindEvents(self):
        for eventType in aui.EVT_AUI_PANE_CLOSE, aui.EVT_AUI_PANE_FLOATING:
            self.manager.Bind(eventType, self.onPaneClosingOrFloating)

    def onPaneClosingOrFloating(self, event):
        pane = event.GetPane()
        dockedPanes = self.dockedPanes()
        if self.isCenterPane(pane) and len(dockedPanes) == 1:
            event.Veto()
        else:
            event.Skip()
            if self.isCenterPane(pane):
                if pane in dockedPanes:
                    dockedPanes.remove(pane)
                dockedPanes[0].Center()

    def addPane(self, window, caption, name, floating=False):
        x, y = 0, 0
        if self.GetTopLevelParent().IsShown():
            x, y = window.GetPosition()
            x, y = window.ClientToScreen(x, y)
        paneInfo = aui.AuiPaneInfo()
        paneInfo = (
            paneInfo.CloseButton(True)
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
            paneInfo.Float()
        if not self.dockedPanes():
            # First pane goes to center
            paneInfo = paneInfo.Center()
        self.manager.AddPane(window, paneInfo)
        self.manager.Update()

    def setPaneTitle(self, window, title):
        self.manager.GetPane(window).Caption(title)

    def dockedPanes(self):
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
    def isCenterPane(pane):
        return pane.dock_direction_get() == aui.AUI_DOCK_CENTER
