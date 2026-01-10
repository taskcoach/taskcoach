#!/usr/bin/env python3
"""
Test script for SearchCtrl dropdown menu positioning - Issue #159

GitHub Issue: https://github.com/taskcoach/taskcoach/issues/159
Bug: Dropdown for search shows up always on far left of pane

Tests various fix attempts for the search dropdown positioning issue.
All search controls are RIGHT-ALIGNED to clearly show the problem.

See bugs/ISSUE_159_SEARCH_DROPDOWN_POSITION.md for full details.

Usage:
    python3 bugs/issue_159_test_search_dropdown.py
"""

import wx
from wx.lib.agw import aui
import os


class NativeSearchCtrl(wx.SearchCtrl):
    """SearchCtrl with NO interception - let wx handle everything natively."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        menu = wx.Menu()
        menu.AppendCheckItem(wx.ID_ANY, "Match case")
        menu.AppendCheckItem(wx.ID_ANY, "Include sub items")
        menu.AppendCheckItem(wx.ID_ANY, "Search description")
        self.SetMenu(menu)
        # NO event binding - let wx.SearchCtrl handle menu natively


class TightContainerSearch(wx.Panel):
    """SearchCtrl in a tight-fitting panel - popup on container at (0, height)."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.search = wx.SearchCtrl(self, size=kwargs.get('size', (200, -1)))
        menu = wx.Menu()
        menu.AppendCheckItem(wx.ID_ANY, "Match case")
        menu.AppendCheckItem(wx.ID_ANY, "Include sub items")
        menu.AppendCheckItem(wx.ID_ANY, "Search description")
        self.search.SetMenu(menu)
        sizer.Add(self.search, 1, wx.EXPAND)
        self.SetSizer(sizer)
        # Intercept menu button to popup on container
        self.search.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self._on_menu_btn)

    def _on_menu_btn(self, event):
        menu = self.search.GetMenu()
        if menu:
            height = self.GetSize().GetHeight()
            self.PopupMenu(menu, wx.Point(0, height))


class ParentOffsetSearch(wx.SearchCtrl):
    """SearchCtrl that calls PopupMenu on parent with position offset."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        menu = wx.Menu()
        menu.AppendCheckItem(wx.ID_ANY, "Match case")
        menu.AppendCheckItem(wx.ID_ANY, "Include sub items")
        menu.AppendCheckItem(wx.ID_ANY, "Search description")
        self.SetMenu(menu)
        self.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self._on_menu_btn)

    def _on_menu_btn(self, event):
        menu = self.GetMenu()
        if menu:
            pos = self.GetPosition()
            height = self.GetSize().GetHeight()
            self.GetParent().PopupMenu(menu, wx.Point(pos.x, pos.y + height))


class CustomSearchCtrl(wx.SearchCtrl):
    """SearchCtrl with configurable PopupMenu positioning."""

    def __init__(self, parent, fix_method="none", **kwargs):
        super().__init__(parent, **kwargs)
        self.fix_method = fix_method
        self._setup_menu()
        # Bind to intercept the menu button click (except for "native" mode)
        if fix_method != "native":
            self.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self._on_search_btn)

    def _setup_menu(self):
        menu = wx.Menu()
        menu.AppendCheckItem(wx.ID_ANY, "Match case")
        menu.AppendCheckItem(wx.ID_ANY, "Include sub items")
        menu.AppendCheckItem(wx.ID_ANY, "Search description")
        self.SetMenu(menu)

    def _on_search_btn(self, event):
        """Intercept search button click to use our custom positioning."""
        self.ShowMenu()
        # Don't skip - we handle the menu ourselves

    def ShowMenu(self):
        """Override to test different positioning methods."""
        menu = self.GetMenu()
        if menu is None:
            return

        if self.fix_method == "none":
            # Baseline - no position (let wx decide)
            self.PopupMenu(menu)

        elif self.fix_method == "zero_height":
            # Position at (0, height)
            height = self.GetSize().GetHeight()
            self.PopupMenu(menu, wx.Point(0, height))

        elif self.fix_method == "client_rect":
            # Original legacy approach
            rect = self.GetClientRect()
            x, y = rect[0], rect[1] + rect[3] + 3
            self.PopupMenu(menu, wx.Point(x, y))

        elif self.fix_method == "screen_coords":
            # Convert to screen coordinates then back
            pos = self.ClientToScreen(wx.Point(0, 0))
            height = self.GetSize().GetHeight()
            screen_pos = wx.Point(pos.x, pos.y + height)
            client_pos = self.ScreenToClient(screen_pos)
            self.PopupMenu(menu, client_pos)

        elif self.fix_method == "parent_popup":
            # Popup on parent instead of self
            pos = self.GetPosition()
            height = self.GetSize().GetHeight()
            self.GetParent().PopupMenu(menu, wx.Point(pos.x, pos.y + height))

        elif self.fix_method == "toplevel_popup":
            # Popup on top-level window
            toplevel = self.GetTopLevelParent()
            screen_pos = self.ClientToScreen(wx.Point(0, self.GetSize().GetHeight()))
            client_pos = toplevel.ScreenToClient(screen_pos)
            toplevel.PopupMenu(menu, client_pos)

        elif self.fix_method == "call_after":
            # Use CallAfter
            wx.CallAfter(self._delayed_popup)

        elif self.fix_method == "call_after_screen":
            # Use CallAfter with screen coords
            wx.CallAfter(self._delayed_popup_screen)

        elif self.fix_method == "negative_x":
            # Try negative X to see if it's offset issue
            height = self.GetSize().GetHeight()
            width = self.GetSize().GetWidth()
            self.PopupMenu(menu, wx.Point(width - 50, height))

        elif self.fix_method == "button_pos":
            # Try to find the menu button position
            for child in self.GetChildren():
                if isinstance(child, wx.Button) or child.GetName() == "search menu":
                    pos = child.GetPosition()
                    height = child.GetSize().GetHeight()
                    self.PopupMenu(menu, wx.Point(pos.x, pos.y + height))
                    return
            # Fallback
            self.PopupMenu(menu)

    def _delayed_popup(self):
        menu = self.GetMenu()
        if menu:
            height = self.GetSize().GetHeight()
            self.PopupMenu(menu, wx.Point(0, height))

    def _delayed_popup_screen(self):
        menu = self.GetMenu()
        if menu:
            toplevel = self.GetTopLevelParent()
            screen_pos = self.ClientToScreen(wx.Point(0, self.GetSize().GetHeight()))
            client_pos = toplevel.ScreenToClient(screen_pos)
            toplevel.PopupMenu(menu, client_pos)


class TestFrame(wx.Frame):
    """Main test frame with AUI and various search control experiments."""

    def __init__(self):
        super().__init__(None, title="Issue #159: Search dropdown at far left of pane", size=(900, 700))

        self.mgr = aui.AuiManager(self)

        # Create toolbar with search controls (RIGHT side)
        toolbar = aui.AuiToolBar(self, agwStyle=aui.AUI_TB_NO_AUTORESIZE)
        toolbar.SetToolBitmapSize((24, 24))

        toolbar.AddStretchSpacer()  # Push everything to right
        toolbar.AddLabel(wx.ID_ANY, "Toolbar:", width=60)

        self.toolbar_search = CustomSearchCtrl(toolbar, fix_method="none", size=(150, -1))
        toolbar.AddControl(self.toolbar_search, "Search")

        toolbar.AddStretchSpacer()
        toolbar.AddLabel(wx.ID_ANY, "Tight:", width=40)
        self.toolbar_tight = TightContainerSearch(toolbar, size=(150, -1))
        toolbar.AddControl(self.toolbar_tight, "TightSearch")

        toolbar.AddStretchSpacer()
        toolbar.AddLabel(wx.ID_ANY, "Parent+:", width=50)
        self.toolbar_parent = ParentOffsetSearch(toolbar, size=(150, -1))
        toolbar.AddControl(self.toolbar_parent, "ParentSearch")
        toolbar.Realize()

        # Use regular pane (not ToolbarPane) to get full width stretching
        self.mgr.AddPane(toolbar, aui.AuiPaneInfo().Name("toolbar").
                         Top().CaptionVisible(False).CloseButton(False).
                         Floatable(False).Movable(False).PaneBorder(False))

        # Main panel with all experiments
        main_panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        main_sizer.Add(wx.StaticText(main_panel,
            label="All search controls are RIGHT-ALIGNED. Click magnifier dropdown to test."),
            0, wx.ALL, 10)

        # Grid of experiments
        grid = wx.FlexGridSizer(cols=2, hgap=20, vgap=15)
        grid.AddGrowableCol(1, 1)

        fixes = [
            ("NATIVE (no intercept):", "native"),
            ("BASELINE (no pos):", "none"),
            ("(0, height):", "zero_height"),
            ("TopLevel PopupMenu:", "toplevel_popup"),
            ("Screen coords convert:", "screen_coords"),
            ("Parent PopupMenu:", "parent_popup"),
        ]

        self.search_controls = []
        for label, fix_method in fixes:
            # Label on left
            grid.Add(wx.StaticText(main_panel, label=label), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)

            # Search control in right-aligned container
            container = wx.Panel(main_panel)
            container_sizer = wx.BoxSizer(wx.HORIZONTAL)
            container_sizer.AddStretchSpacer()  # Push to right

            search = CustomSearchCtrl(container, fix_method=fix_method, size=(200, -1))
            self.search_controls.append(search)
            container_sizer.Add(search, 0)

            container.SetSizer(container_sizer)
            grid.Add(container, 1, wx.EXPAND)

        # Add native search directly on main_panel (no container)
        grid.Add(wx.StaticText(main_panel, label="Native (no container):"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        native_direct = NativeSearchCtrl(main_panel, size=(200, -1))
        grid.Add(native_direct, 0, wx.ALIGN_RIGHT)

        # Add tight container test - SearchCtrl and popup share same tight panel
        grid.Add(wx.StaticText(main_panel, label="Tight container (0,h):"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        tight_container = TightContainerSearch(main_panel, size=(200, -1))
        grid.Add(tight_container, 0, wx.ALIGN_RIGHT)

        # Add parent offset test - popup on parent with position offset
        grid.Add(wx.StaticText(main_panel, label="Parent + offset:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        parent_offset = ParentOffsetSearch(main_panel, size=(200, -1))
        grid.Add(parent_offset, 0, wx.ALIGN_RIGHT)

        main_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 15)

        # Add manual button tests
        main_sizer.Add(wx.StaticLine(main_panel), 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(wx.StaticText(main_panel, label="Manual PopupMenu tests (buttons):"), 0, wx.ALL, 10)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()

        btn1 = wx.Button(main_panel, label="PopupMenu(menu)")
        btn1.Bind(wx.EVT_BUTTON, self.on_popup_no_pos)
        btn_sizer.Add(btn1, 0, wx.ALL, 5)

        btn2 = wx.Button(main_panel, label="PopupMenu(0,h)")
        btn2.Bind(wx.EVT_BUTTON, self.on_popup_zero_height)
        btn_sizer.Add(btn2, 0, wx.ALL, 5)

        btn3 = wx.Button(main_panel, label="TopLevel popup")
        btn3.Bind(wx.EVT_BUTTON, self.on_popup_toplevel)
        btn_sizer.Add(btn3, 0, wx.ALL, 5)

        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Platform info
        main_sizer.Add(wx.StaticLine(main_panel), 0, wx.EXPAND | wx.ALL, 5)

        wayland = os.environ.get('XDG_SESSION_TYPE', 'unknown')
        display = os.environ.get('WAYLAND_DISPLAY', os.environ.get('DISPLAY', 'unknown'))
        desktop = os.environ.get('XDG_CURRENT_DESKTOP', 'unknown')
        gtk_backend = os.environ.get('GDK_BACKEND', 'auto')

        info = f"wxPython: {wx.version()} | Platform: {wx.PlatformInfo[0]}\n"
        info += f"Session: {wayland} | Display: {display} | Desktop: {desktop} | GDK_BACKEND: {gtk_backend}"

        info_text = wx.StaticText(main_panel, label=info)
        info_text.SetFont(wx.Font(8, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        main_sizer.Add(info_text, 0, wx.ALL, 10)

        main_panel.SetSizer(main_sizer)

        self.mgr.AddPane(main_panel, aui.AuiPaneInfo().Name("center").
                         CenterPane().PaneBorder(False))

        self.mgr.Update()
        self.Centre()

    def on_popup_no_pos(self, event):
        menu = wx.Menu()
        menu.AppendCheckItem(wx.ID_ANY, "Option 1")
        menu.AppendCheckItem(wx.ID_ANY, "Option 2")
        btn = event.GetEventObject()
        btn.PopupMenu(menu)
        menu.Destroy()

    def on_popup_zero_height(self, event):
        menu = wx.Menu()
        menu.AppendCheckItem(wx.ID_ANY, "Option 1")
        menu.AppendCheckItem(wx.ID_ANY, "Option 2")
        btn = event.GetEventObject()
        height = btn.GetSize().GetHeight()
        btn.PopupMenu(menu, wx.Point(0, height))
        menu.Destroy()

    def on_popup_toplevel(self, event):
        menu = wx.Menu()
        menu.AppendCheckItem(wx.ID_ANY, "Option 1")
        menu.AppendCheckItem(wx.ID_ANY, "Option 2")
        btn = event.GetEventObject()
        toplevel = btn.GetTopLevelParent()
        screen_pos = btn.ClientToScreen(wx.Point(0, btn.GetSize().GetHeight()))
        client_pos = toplevel.ScreenToClient(screen_pos)
        toplevel.PopupMenu(menu, client_pos)
        menu.Destroy()

    def __del__(self):
        self.mgr.UnInit()


def main():
    app = wx.App()
    frame = TestFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
