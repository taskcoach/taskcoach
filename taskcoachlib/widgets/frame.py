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


def _diagnose_aui_capabilities():
    """Diagnose AUI capabilities for debugging sash drag issues."""
    import sys
    info = []
    info.append(f"wx.Platform: {wx.Platform}")
    info.append(f"wx.PlatformInfo: {wx.PlatformInfo}")
    info.append(f"wxPython version: {wx.version()}")

    # Check what AUI flags are available
    flags_to_check = [
        'AUI_MGR_DEFAULT', 'AUI_MGR_ALLOW_FLOATING', 'AUI_MGR_ALLOW_ACTIVE_PANE',
        'AUI_MGR_TRANSPARENT_DRAG', 'AUI_MGR_TRANSPARENT_HINT', 'AUI_MGR_VENETIAN_BLINDS_HINT',
        'AUI_MGR_RECTANGLE_HINT', 'AUI_MGR_HINT_FADE', 'AUI_MGR_NO_VENETIAN_BLINDS_FADE',
        'AUI_MGR_LIVE_RESIZE', 'AUI_MGR_ANIMATE_FRAMES', 'AUI_MGR_AERO_DOCKING_GUIDES',
        'AUI_MGR_PREVIEW_MINIMIZED_PANES', 'AUI_MGR_WHIDBEY_DOCKING_GUIDES',
        'AUI_MGR_SMOOTH_DOCKING', 'AUI_MGR_USE_NATIVE_MINIFRAMES',
    ]
    info.append("AGW AUI Flags available:")
    for flag in flags_to_check:
        val = getattr(aui, flag, None)
        if val is not None:
            info.append(f"  {flag} = {val} (0x{val:04x})")

    # Check if HasLiveResize exists
    info.append(f"AuiManager has HasLiveResize: {hasattr(aui.AuiManager, 'HasLiveResize')}")
    info.append(f"AuiManager has AlwaysUsesLiveResize: {hasattr(aui.AuiManager, 'AlwaysUsesLiveResize')}")

    # Check for static function
    has_static = hasattr(aui, 'AuiManager_HasLiveResize')
    info.append(f"aui.AuiManager_HasLiveResize exists: {has_static}")

    # List all methods on AuiManager that might be related to flags or resize
    info.append("AuiManager methods containing 'flag', 'resize', 'live', 'sash':")
    for name in dir(aui.AuiManager):
        name_lower = name.lower()
        if any(x in name_lower for x in ['flag', 'resize', 'live', 'sash', 'hint', 'draw']):
            info.append(f"  {name}")

    return "\n".join(info)


def _diagnose_manager_instance(manager):
    """Diagnose a specific AuiManager instance."""
    info = []

    # Check for internal flags attribute
    for attr in ['_agwFlags', '_flags', 'agwFlags', 'flags', '_mgr_flags']:
        if hasattr(manager, attr):
            val = getattr(manager, attr)
            info.append(f"AUI: manager.{attr} = {val} (0x{val:04x})")

    # Check GetFlags and GetAGWFlags
    for method in ['GetFlags', 'GetAGWFlags', 'GetAGWWindowStyleFlag']:
        if hasattr(manager, method):
            try:
                val = getattr(manager, method)()
                info.append(f"AUI: manager.{method}() = {val} (0x{val:04x})")
                if hasattr(aui, 'AUI_MGR_LIVE_RESIZE'):
                    has_live = bool(val & aui.AUI_MGR_LIVE_RESIZE)
                    info.append(f"AUI: LIVE_RESIZE in {method}: {'YES' if has_live else 'NO'}")
            except Exception as e:
                info.append(f"AUI: manager.{method}() raised: {e}")

    # Try the static function
    if hasattr(aui, 'AuiManager_HasLiveResize'):
        try:
            result = aui.AuiManager_HasLiveResize(manager)
            info.append(f"AUI: AuiManager_HasLiveResize(manager) = {result}")
        except Exception as e:
            info.append(f"AUI: AuiManager_HasLiveResize raised: {e}")

    # Check for HasLiveResize method
    if hasattr(manager, 'HasLiveResize'):
        try:
            result = manager.HasLiveResize()
            info.append(f"AUI: manager.HasLiveResize() = {result}")
        except Exception as e:
            info.append(f"AUI: manager.HasLiveResize() raised: {e}")

    return "\n".join(info) if info else "AUI: No flag methods found on manager instance"


def _install_resize_tracing(manager):
    """Monkey-patch AuiManager to trace sash resize events with call stacks."""
    import time
    import traceback

    # Store original methods
    original_update = manager.Update if hasattr(manager, 'Update') else None
    original_do_update = manager.DoUpdate if hasattr(manager, 'DoUpdate') else None
    original_on_left_up = manager.OnLeftUp if hasattr(manager, 'OnLeftUp') else None
    original_on_left_up_resize = manager.OnLeftUp_Resize if hasattr(manager, 'OnLeftUp_Resize') else None

    state = {
        'do_update_count': 0,
        'left_up_count': 0,
        'left_up_resize_count': 0,
        'in_do_update': False,
    }

    # Trace OnLeftUp to see why it's called multiple times
    if original_on_left_up:
        def traced_on_left_up(event):
            state['left_up_count'] += 1
            count = state['left_up_count']
            action = getattr(manager, '_action', 'unknown')
            print(f"AUI TRACE: OnLeftUp #{count} _action={action}")
            return original_on_left_up(event)
        manager.OnLeftUp = traced_on_left_up

    # Trace OnLeftUp_Resize specifically
    if original_on_left_up_resize:
        def traced_on_left_up_resize(event):
            state['left_up_resize_count'] += 1
            count = state['left_up_resize_count']
            print(f"AUI TRACE: OnLeftUp_Resize #{count} called")
            stack = traceback.extract_stack()
            callers = [f"{f.filename.split('/')[-1]}:{f.lineno}:{f.name}" for f in stack[-6:-2]]
            print(f"  from: {' <- '.join(callers)}")
            return original_on_left_up_resize(event)
        manager.OnLeftUp_Resize = traced_on_left_up_resize

    if original_update:
        def traced_update():
            start = time.time()
            # Show abbreviated call stack
            if state['do_update_count'] < 20:
                stack = traceback.extract_stack()
                callers = [f"{f.filename.split('/')[-1]}:{f.lineno}:{f.name}" for f in stack[-6:-2]]
                print(f"AUI TRACE: Update() from: {' <- '.join(callers)}")
            result = original_update()
            elapsed_ms = (time.time() - start) * 1000
            if elapsed_ms > 30:
                print(f"AUI SLOW: Update() took {elapsed_ms:.1f}ms")
            return result
        manager.Update = traced_update

    if original_do_update:
        def traced_do_update():
            state['do_update_count'] += 1
            count = state['do_update_count']

            # Check for re-entrancy (cascade)
            if state['in_do_update']:
                stack = traceback.extract_stack()
                callers = [f"{f.filename.split('/')[-1]}:{f.lineno}" for f in stack[-5:-1]]
                print(f"AUI CASCADE: DoUpdate() re-entered! #{count} from: {' <- '.join(callers)}")
                return  # Skip re-entrant calls

            state['in_do_update'] = True
            start = time.time()

            try:
                result = original_do_update()
            finally:
                state['in_do_update'] = False

            elapsed_ms = (time.time() - start) * 1000
            if elapsed_ms > 20:
                print(f"AUI: DoUpdate() #{count} took {elapsed_ms:.1f}ms")
            return result
        manager.DoUpdate = traced_do_update

    print("AUI: Resize event tracing installed")


class AuiManagedFrameWithDynamicCenterPane(wx.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Diagnose AUI capabilities once
        if not hasattr(AuiManagedFrameWithDynamicCenterPane, '_aui_diagnosed'):
            AuiManagedFrameWithDynamicCenterPane._aui_diagnosed = True
            print("=" * 60)
            print("AUI DIAGNOSTIC INFO")
            print("=" * 60)
            print(_diagnose_aui_capabilities())
            print("=" * 60)

        # Build AUI style flags
        # NOTE: AUI_MGR_LIVE_RESIZE causes slow updates (50-190ms per DoUpdate)
        # which leads to dropped mouse events and flickering. Instead, we rely
        # on AGW AUI's hint/ghost line drawing during sash dragging.
        agwStyle = aui.AUI_MGR_DEFAULT | aui.AUI_MGR_ALLOW_ACTIVE_PANE

        # Explicitly set hint drawing mode for sash feedback
        # RECTANGLE_HINT should show a rectangle outline during drag
        if hasattr(aui, 'AUI_MGR_RECTANGLE_HINT'):
            agwStyle |= aui.AUI_MGR_RECTANGLE_HINT
            print(f"AUI: Enabled AUI_MGR_RECTANGLE_HINT for sash feedback")

        if not operating_system.isWindows():
            # With this style on Windows, you can't dock back floating frames
            agwStyle |= aui.AUI_MGR_USE_NATIVE_MINIFRAMES

        print(f"AUI: Final agwStyle = {agwStyle} (0x{agwStyle:04x})")
        self.manager = aui.AuiManager(self, agwStyle)

        # Comprehensive manager instance diagnostics
        print(_diagnose_manager_instance(self.manager))

        # Install event tracing to debug sash drag behavior
        _install_resize_tracing(self.manager)

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
