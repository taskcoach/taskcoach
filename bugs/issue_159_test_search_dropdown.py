#!/usr/bin/env python3
"""
Test script for SearchCtrl dropdown menu positioning - Issue #159

GitHub Issue: https://github.com/taskcoach/taskcoach/issues/159
Bug: Dropdown for search shows up always on far left of pane

This test script EXACTLY replicates TaskCoach's toolbar setup to ensure
any fix works in the actual application context.

See bugs/ISSUE_159_SEARCH_DROPDOWN_POSITION.md for full details.

Usage:
    python3 bugs/issue_159_test_search_dropdown.py
"""

import wx
from wx.lib.agw import aui
import os


# =============================================================================
# TASKCOACH-STYLE TOOLBAR (exact replica of taskcoachlib/gui/toolbar.py)
# =============================================================================

class TaskCoachToolBar(aui.AuiToolBar):
    """Exact replica of TaskCoach's _Toolbar class."""

    def __init__(self, parent):
        super().__init__(parent, agwStyle=aui.AUI_TB_NO_AUTORESIZE)
        self.__size = (16, 16)

    def SetToolBitmapSize(self, size):
        self.__size = size

    def GetToolBitmapSize(self):
        return self.__size


# =============================================================================
# SEARCH CONTROL VARIANTS
# =============================================================================

class NativeSearchCtrl(wx.SearchCtrl):
    """SearchCtrl with NO interception - let wx handle everything natively."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._setup_menu()

    def _setup_menu(self):
        menu = wx.Menu()
        menu.AppendCheckItem(wx.ID_ANY, "Match case")
        menu.AppendCheckItem(wx.ID_ANY, "Include sub items")
        menu.AppendCheckItem(wx.ID_ANY, "Search description")
        self.SetMenu(menu)


class ParentOffsetSearchCtrl(wx.SearchCtrl):
    """SearchCtrl that calls PopupMenu on parent with position offset.

    This is the approach currently in TaskCoach's searchctrl.py.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._setup_menu()
        self.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self._on_search_btn)

    def _setup_menu(self):
        menu = wx.Menu()
        menu.AppendCheckItem(wx.ID_ANY, "Match case")
        menu.AppendCheckItem(wx.ID_ANY, "Include sub items")
        menu.AppendCheckItem(wx.ID_ANY, "Search description")
        self.SetMenu(menu)

    def _on_search_btn(self, event):
        menu = self.GetMenu()
        if menu:
            pos = self.GetPosition()
            height = self.GetSize().GetHeight()
            self.GetParent().PopupMenu(menu, wx.Point(pos.x, pos.y + height))


class PanelWrappedSearchCtrl(wx.Panel):
    """SearchCtrl wrapped in tight-fitting Panel - popup on container.

    This is the "modern best practice" approach for Wayland.
    The container panel fits exactly around the SearchCtrl, so
    calling PopupMenu on the panel at (0, height) positions correctly.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.search = wx.SearchCtrl(self, size=kwargs.get('size', (150, -1)))
        self._setup_menu()
        sizer.Add(self.search, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.search.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self._on_menu_btn)

    def _setup_menu(self):
        menu = wx.Menu()
        menu.AppendCheckItem(wx.ID_ANY, "Match case")
        menu.AppendCheckItem(wx.ID_ANY, "Include sub items")
        menu.AppendCheckItem(wx.ID_ANY, "Search description")
        self.search.SetMenu(menu)

    def _on_menu_btn(self, event):
        menu = self.search.GetMenu()
        if menu:
            height = self.GetSize().GetHeight()
            self.PopupMenu(menu, wx.Point(0, height))

    # Delegate common methods to the inner search control
    def SetMinSize(self, size):
        self.search.SetMinSize(size)
        super().SetMinSize(size)

    def GetValue(self):
        return self.search.GetValue()

    def SetValue(self, value):
        self.search.SetValue(value)


# =============================================================================
# TEST FRAME - Replicates TaskCoach viewer structure
# =============================================================================

class TestFrame(wx.Frame):
    """Test frame that replicates TaskCoach's viewer/toolbar structure."""

    def __init__(self):
        super().__init__(None, title="Issue #159: Search dropdown test (TaskCoach replica)",
                         size=(900, 700))

        self.mgr = aui.AuiManager(self)

        # Create main panel (simulates viewer)
        main_panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # =================================================================
        # TOOLBAR 1: Native SearchCtrl (baseline - expected to fail on Wayland)
        # =================================================================
        toolbar1 = TaskCoachToolBar(main_panel)
        toolbar1.SetToolBitmapSize((16, 16))
        toolbar1.AddStretchSpacer()
        toolbar1.AddLabel(wx.ID_ANY, "Native:", width=50)

        self.native_search = NativeSearchCtrl(toolbar1, size=(150, -1))
        self.native_search.SetMinSize((150, -1))
        toolbar1.AddControl(self.native_search)
        toolbar1.Realize()

        main_sizer.Add(toolbar1, 0, wx.EXPAND)
        main_sizer.Add(wx.StaticText(main_panel, label="  ^ Native wx.SearchCtrl - NO fix (baseline)"), 0, wx.LEFT, 10)
        main_sizer.Add(wx.StaticLine(main_panel), 0, wx.EXPAND | wx.ALL, 5)

        # =================================================================
        # TOOLBAR 2: Parent offset approach (current TaskCoach fix)
        # =================================================================
        toolbar2 = TaskCoachToolBar(main_panel)
        toolbar2.SetToolBitmapSize((16, 16))
        toolbar2.AddStretchSpacer()
        toolbar2.AddLabel(wx.ID_ANY, "Parent+offset:", width=80)

        self.parent_search = ParentOffsetSearchCtrl(toolbar2, size=(150, -1))
        self.parent_search.SetMinSize((150, -1))
        toolbar2.AddControl(self.parent_search)
        toolbar2.Realize()

        main_sizer.Add(toolbar2, 0, wx.EXPAND)
        main_sizer.Add(wx.StaticText(main_panel, label="  ^ Parent offset approach - calls parent.PopupMenu()"), 0, wx.LEFT, 10)
        main_sizer.Add(wx.StaticLine(main_panel), 0, wx.EXPAND | wx.ALL, 5)

        # =================================================================
        # TOOLBAR 3: Panel wrapper approach (modern best practice)
        # =================================================================
        toolbar3 = TaskCoachToolBar(main_panel)
        toolbar3.SetToolBitmapSize((16, 16))
        toolbar3.AddStretchSpacer()
        toolbar3.AddLabel(wx.ID_ANY, "Panel wrapper:", width=85)

        self.panel_search = PanelWrappedSearchCtrl(toolbar3, size=(150, -1))
        self.panel_search.SetMinSize((150, -1))
        toolbar3.AddControl(self.panel_search)
        toolbar3.Realize()

        main_sizer.Add(toolbar3, 0, wx.EXPAND)
        main_sizer.Add(wx.StaticText(main_panel, label="  ^ Panel wrapper - SearchCtrl inside tight Panel"), 0, wx.LEFT, 10)
        main_sizer.Add(wx.StaticLine(main_panel), 0, wx.EXPAND | wx.ALL, 5)

        # =================================================================
        # TEST BUTTONS - Simulate TaskCoach's multiple Realize() calls
        # =================================================================
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        btn_realize = wx.Button(main_panel, label="Call Realize() on all toolbars")
        btn_realize.Bind(wx.EVT_BUTTON, self._on_realize_all)
        btn_sizer.Add(btn_realize, 0, wx.ALL, 5)

        btn_realize_10x = wx.Button(main_panel, label="Call Realize() 10 times")
        btn_realize_10x.Bind(wx.EVT_BUTTON, self._on_realize_10x)
        btn_sizer.Add(btn_realize_10x, 0, wx.ALL, 5)

        main_sizer.Add(btn_sizer, 0, wx.ALL, 10)
        main_sizer.Add(wx.StaticText(main_panel,
            label="Click buttons above to test Realize() stability (TaskCoach calls Realize() frequently)"),
            0, wx.LEFT, 10)

        # Store toolbars for testing
        self._toolbars = [toolbar1, toolbar2, toolbar3]

        # =================================================================
        # PLATFORM INFO
        # =================================================================
        main_sizer.Add(wx.StaticLine(main_panel), 0, wx.EXPAND | wx.ALL, 10)

        wayland = os.environ.get('XDG_SESSION_TYPE', 'unknown')
        display = os.environ.get('WAYLAND_DISPLAY', os.environ.get('DISPLAY', 'unknown'))
        desktop = os.environ.get('XDG_CURRENT_DESKTOP', 'unknown')
        gtk_backend = os.environ.get('GDK_BACKEND', 'auto')

        info = f"wxPython: {wx.version()} | Platform: {wx.PlatformInfo[0]}\n"
        info += f"Session: {wayland} | Display: {display} | Desktop: {desktop} | GDK_BACKEND: {gtk_backend}"

        info_text = wx.StaticText(main_panel, label=info)
        info_text.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        main_sizer.Add(info_text, 0, wx.ALL, 10)

        main_sizer.Add(wx.StaticText(main_panel,
            label="Instructions: Click the magnifier dropdown on each search box.\n"
                  "On Wayland, Native will show menu at far left. Fixed versions should show below the control."),
            0, wx.ALL, 10)

        main_panel.SetSizer(main_sizer)

        self.mgr.AddPane(main_panel, aui.AuiPaneInfo().Name("main").CenterPane().PaneBorder(False))
        self.mgr.Update()
        self.Centre()

    def _on_realize_all(self, event):
        """Test calling Realize() on all toolbars."""
        for toolbar in self._toolbars:
            toolbar.Realize()
        wx.MessageBox("Realize() called on all toolbars successfully!", "Test Result")

    def _on_realize_10x(self, event):
        """Test calling Realize() multiple times (simulates TaskCoach behavior)."""
        for _ in range(10):
            for toolbar in self._toolbars:
                toolbar.Realize()
        wx.MessageBox("Realize() called 10 times on all toolbars successfully!", "Test Result")

    def __del__(self):
        self.mgr.UnInit()


def main():
    app = wx.App()
    frame = TestFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
