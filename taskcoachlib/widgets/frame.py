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

        # Install optimization for sash resize to reduce flickering
        # TEMPORARILY DISABLED for testing - uncomment to re-enable
        # _install_sash_resize_optimization(self.manager)

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
