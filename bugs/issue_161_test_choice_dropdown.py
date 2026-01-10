#!/usr/bin/env python3
"""
Test script for wx.Choice dropdown behavior - Issue #161

GitHub Issue: https://github.com/taskcoach/taskcoach/issues/161
Bug: wx.Choice dropdowns show mini-scrollbars on KDE Plasma + Wayland

This script tests various wx.Choice and wx.ComboBox configurations to help
determine if the issue is in Task Coach code or upstream.

Tested on Kubuntu 24 with KDE Plasma + Wayland:
- wx.Choice: ALL variations show unwanted scrollbars
- wx.ComboBox: Does NOT have this issue

See bugs/ISSUE_161_CHOICE_DROPDOWN_SCROLLBARS.md for full details.

Usage:
    python3 bugs/issue_161_test_choice_dropdown.py
"""

import wx
import os


class TestFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Issue #161: wx.Choice Dropdown Test", size=(700, 700))

        # Create toolbar first
        toolbar = self.CreateToolBar()
        toolbar.AddStretchableSpace()
        self.toolbar_choice = wx.Choice(toolbar, choices=["Tree", "List"])
        self.toolbar_choice.SetSelection(0)
        toolbar.AddControl(self.toolbar_choice, "Toolbar Choice")
        toolbar.AddSeparator()
        self.toolbar_combo = wx.ComboBox(toolbar, choices=["Opt A", "Opt B"], style=wx.CB_READONLY)
        self.toolbar_combo.SetSelection(0)
        toolbar.AddControl(self.toolbar_combo, "Toolbar ComboBox")
        toolbar.AddStretchableSpace()
        toolbar.Realize()

        # Main panel with notebook for organized tests
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        notebook = wx.Notebook(panel)

        # === Tab 1: Basic Choice Tests ===
        tab1 = wx.Panel(notebook)
        sizer1 = wx.FlexGridSizer(cols=2, hgap=20, vgap=10)

        # Test 1: Basic 2 items
        sizer1.Add(wx.StaticText(tab1, label="1. Basic (2 items):"), 0, wx.ALIGN_CENTER_VERTICAL)
        c1 = wx.Choice(tab1, choices=["Tree", "List"])
        c1.SetSelection(0)
        sizer1.Add(c1, 0)

        # Test 2: 3 items
        sizer1.Add(wx.StaticText(tab1, label="2. Three items:"), 0, wx.ALIGN_CENTER_VERTICAL)
        c2 = wx.Choice(tab1, choices=["One", "Two", "Three"])
        c2.SetSelection(0)
        sizer1.Add(c2, 0)

        # Test 3: 5 items
        sizer1.Add(wx.StaticText(tab1, label="3. Five items:"), 0, wx.ALIGN_CENTER_VERTICAL)
        c3 = wx.Choice(tab1, choices=["Mon", "Tue", "Wed", "Thu", "Fri"])
        c3.SetSelection(0)
        sizer1.Add(c3, 0)

        # Test 4: 10 items (should definitely scroll)
        sizer1.Add(wx.StaticText(tab1, label="4. Ten items:"), 0, wx.ALIGN_CENTER_VERTICAL)
        c4 = wx.Choice(tab1, choices=[f"Item {i}" for i in range(1, 11)])
        c4.SetSelection(0)
        sizer1.Add(c4, 0)

        # Test 5: Very long text
        sizer1.Add(wx.StaticText(tab1, label="5. Long text items:"), 0, wx.ALIGN_CENTER_VERTICAL)
        c5 = wx.Choice(tab1, choices=["Short", "A very long option text that might affect sizing"])
        c5.SetSelection(0)
        sizer1.Add(c5, 0)

        # Test 6: Single item
        sizer1.Add(wx.StaticText(tab1, label="6. Single item:"), 0, wx.ALIGN_CENTER_VERTICAL)
        c6 = wx.Choice(tab1, choices=["Only One"])
        c6.SetSelection(0)
        sizer1.Add(c6, 0)

        # Test 7: Empty then populated
        sizer1.Add(wx.StaticText(tab1, label="7. Initially empty:"), 0, wx.ALIGN_CENTER_VERTICAL)
        c7 = wx.Choice(tab1, choices=[])
        c7.Append("Added 1")
        c7.Append("Added 2")
        c7.SetSelection(0)
        sizer1.Add(c7, 0)

        # Test 8: With CB_SORT
        sizer1.Add(wx.StaticText(tab1, label="8. With CB_SORT:"), 0, wx.ALIGN_CENTER_VERTICAL)
        c8 = wx.Choice(tab1, choices=["Zebra", "Apple", "Mango"], style=wx.CB_SORT)
        c8.SetSelection(0)
        sizer1.Add(c8, 0)

        tab1.SetSizer(wx.BoxSizer(wx.VERTICAL))
        tab1.GetSizer().Add(sizer1, 1, wx.ALL, 15)
        notebook.AddPage(tab1, "Basic Choice")

        # === Tab 2: Sizing Tests ===
        tab2 = wx.Panel(notebook)
        sizer2 = wx.FlexGridSizer(cols=2, hgap=20, vgap=10)

        # Test 9: SetMinSize
        sizer2.Add(wx.StaticText(tab2, label="9. SetMinSize(150,-1):"), 0, wx.ALIGN_CENTER_VERTICAL)
        c9 = wx.Choice(tab2, choices=["Tree", "List"])
        c9.SetMinSize((150, -1))
        c9.SetSelection(0)
        sizer2.Add(c9, 0)

        # Test 10: SetSize
        sizer2.Add(wx.StaticText(tab2, label="10. SetSize(200,30):"), 0, wx.ALIGN_CENTER_VERTICAL)
        c10 = wx.Choice(tab2, choices=["Tree", "List"])
        c10.SetSize((200, 30))
        c10.SetSelection(0)
        sizer2.Add(c10, 0)

        # Test 11: In sizer with EXPAND
        sizer2.Add(wx.StaticText(tab2, label="11. EXPAND flag:"), 0, wx.ALIGN_CENTER_VERTICAL)
        c11 = wx.Choice(tab2, choices=["Tree", "List"])
        c11.SetSelection(0)
        sizer2.Add(c11, 1, wx.EXPAND)

        # Test 12: Fixed size via sizer
        sizer2.Add(wx.StaticText(tab2, label="12. Sizer proportion=0:"), 0, wx.ALIGN_CENTER_VERTICAL)
        c12 = wx.Choice(tab2, choices=["Tree", "List"])
        c12.SetSelection(0)
        sizer2.Add(c12, 0)

        tab2.SetSizer(wx.BoxSizer(wx.VERTICAL))
        tab2.GetSizer().Add(sizer2, 1, wx.ALL | wx.EXPAND, 15)
        notebook.AddPage(tab2, "Sizing")

        # === Tab 3: ComboBox Comparison ===
        tab3 = wx.Panel(notebook)
        sizer3 = wx.FlexGridSizer(cols=2, hgap=20, vgap=10)

        # Test 13: ComboBox readonly
        sizer3.Add(wx.StaticText(tab3, label="13. ComboBox READONLY:"), 0, wx.ALIGN_CENTER_VERTICAL)
        cb1 = wx.ComboBox(tab3, choices=["Tree", "List"], style=wx.CB_READONLY)
        cb1.SetSelection(0)
        sizer3.Add(cb1, 0)

        # Test 14: ComboBox editable
        sizer3.Add(wx.StaticText(tab3, label="14. ComboBox editable:"), 0, wx.ALIGN_CENTER_VERTICAL)
        cb2 = wx.ComboBox(tab3, choices=["Tree", "List"])
        cb2.SetSelection(0)
        sizer3.Add(cb2, 0)

        # Test 15: ComboBox dropdown
        sizer3.Add(wx.StaticText(tab3, label="15. CB_DROPDOWN:"), 0, wx.ALIGN_CENTER_VERTICAL)
        cb3 = wx.ComboBox(tab3, choices=["Tree", "List"], style=wx.CB_DROPDOWN)
        cb3.SetSelection(0)
        sizer3.Add(cb3, 0)

        # Test 16: ComboBox simple (if supported)
        sizer3.Add(wx.StaticText(tab3, label="16. CB_SIMPLE:"), 0, wx.ALIGN_CENTER_VERTICAL)
        cb4 = wx.ComboBox(tab3, choices=["Tree", "List"], style=wx.CB_SIMPLE)
        cb4.SetSelection(0)
        sizer3.Add(cb4, 0)

        tab3.SetSizer(wx.BoxSizer(wx.VERTICAL))
        tab3.GetSizer().Add(sizer3, 1, wx.ALL, 15)
        notebook.AddPage(tab3, "ComboBox")

        # === Tab 4: Other Controls ===
        tab4 = wx.Panel(notebook)
        sizer4 = wx.FlexGridSizer(cols=2, hgap=20, vgap=10)

        # Test 17: ListBox (single)
        sizer4.Add(wx.StaticText(tab4, label="17. ListBox single:"), 0)
        lb1 = wx.ListBox(tab4, choices=["Tree", "List"], style=wx.LB_SINGLE, size=(100, 50))
        lb1.SetSelection(0)
        sizer4.Add(lb1, 0)

        # Test 18: RadioBox
        sizer4.Add(wx.StaticText(tab4, label="18. RadioBox:"), 0)
        rb1 = wx.RadioBox(tab4, choices=["Tree", "List"], style=wx.RA_SPECIFY_ROWS)
        sizer4.Add(rb1, 0)

        # Test 19: BitmapComboBox (if available)
        sizer4.Add(wx.StaticText(tab4, label="19. BitmapComboBox:"), 0, wx.ALIGN_CENTER_VERTICAL)
        try:
            bcb = wx.adv.BitmapComboBox(tab4, style=wx.CB_READONLY)
            bcb.Append("Tree", wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_MENU, (16, 16)))
            bcb.Append("List", wx.ArtProvider.GetBitmap(wx.ART_LIST_VIEW, wx.ART_MENU, (16, 16)))
            bcb.SetSelection(0)
            sizer4.Add(bcb, 0)
        except Exception as e:
            sizer4.Add(wx.StaticText(tab4, label=f"(not available: {e})"), 0)

        tab4.SetSizer(wx.BoxSizer(wx.VERTICAL))
        tab4.GetSizer().Add(sizer4, 1, wx.ALL, 15)
        notebook.AddPage(tab4, "Other Controls")

        # === Tab 5: Popup Menu Test ===
        tab5 = wx.Panel(notebook)
        sizer5 = wx.BoxSizer(wx.VERTICAL)

        btn_popup = wx.Button(tab5, label="20. Show Popup Menu")
        btn_popup.Bind(wx.EVT_BUTTON, self.on_popup_menu)
        sizer5.Add(btn_popup, 0, wx.ALL, 15)

        btn_popup2 = wx.Button(tab5, label="21. Show Popup Menu at (0,0)")
        btn_popup2.Bind(wx.EVT_BUTTON, self.on_popup_menu_at_origin)
        sizer5.Add(btn_popup2, 0, wx.ALL, 15)

        btn_popup3 = wx.Button(tab5, label="22. Show Popup Menu with position")
        btn_popup3.Bind(wx.EVT_BUTTON, self.on_popup_menu_with_pos)
        sizer5.Add(btn_popup3, 0, wx.ALL, 15)

        tab5.SetSizer(sizer5)
        notebook.AddPage(tab5, "Popup Menu")

        # === Tab 6: Dialog Test ===
        tab6 = wx.Panel(notebook)
        sizer6 = wx.BoxSizer(wx.VERTICAL)

        btn_dialog = wx.Button(tab6, label="23. Open Dialog with Choice")
        btn_dialog.Bind(wx.EVT_BUTTON, self.on_open_dialog)
        sizer6.Add(btn_dialog, 0, wx.ALL, 15)

        tab6.SetSizer(sizer6)
        notebook.AddPage(tab6, "Dialog")

        # === Tab 7: Search Control Tests ===
        tab7 = wx.Panel(notebook)
        sizer7 = wx.FlexGridSizer(cols=2, hgap=20, vgap=10)

        # SearchCtrl with menu - baseline (no position override)
        sizer7.Add(wx.StaticText(tab7, label="SearchCtrl (no pos):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.search1 = wx.SearchCtrl(tab7)
        menu1 = wx.Menu()
        menu1.AppendCheckItem(wx.ID_ANY, "Match case")
        menu1.AppendCheckItem(wx.ID_ANY, "Include sub items")
        self.search1.SetMenu(menu1)
        sizer7.Add(self.search1, 0, wx.EXPAND)

        # SearchCtrl - popup at (0, height)
        sizer7.Add(wx.StaticText(tab7, label="SearchCtrl (0,height):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.search2 = wx.SearchCtrl(tab7)
        menu2 = wx.Menu()
        menu2.AppendCheckItem(wx.ID_ANY, "Match case")
        menu2.AppendCheckItem(wx.ID_ANY, "Include sub items")
        self.search2.SetMenu(menu2)
        self.search2.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self.on_search2_click)
        sizer7.Add(self.search2, 0, wx.EXPAND)

        # Button to manually show menu with no position
        sizer7.Add(wx.StaticText(tab7, label="Manual PopupMenu():"), 0, wx.ALIGN_CENTER_VERTICAL)
        btn_search_menu = wx.Button(tab7, label="Show Menu (no pos)")
        btn_search_menu.Bind(wx.EVT_BUTTON, self.on_search_menu_no_pos)
        sizer7.Add(btn_search_menu, 0)

        # Button to manually show menu with position
        sizer7.Add(wx.StaticText(tab7, label="Manual PopupMenu(0,h):"), 0, wx.ALIGN_CENTER_VERTICAL)
        btn_search_menu2 = wx.Button(tab7, label="Show Menu (0,height)")
        btn_search_menu2.Bind(wx.EVT_BUTTON, self.on_search_menu_with_pos)
        sizer7.Add(btn_search_menu2, 0)

        tab7.SetSizer(wx.BoxSizer(wx.VERTICAL))
        tab7.GetSizer().Add(sizer7, 1, wx.ALL | wx.EXPAND, 15)
        notebook.AddPage(tab7, "SearchCtrl")

        # === Tab 8: Experiments (potential fixes) ===
        tab8 = wx.Panel(notebook)
        sizer8 = wx.FlexGridSizer(cols=2, hgap=20, vgap=10)

        # Baseline: Regular wx.Choice (shows the problem)
        sizer8.Add(wx.StaticText(tab8, label="BASELINE (problem):"), 0, wx.ALIGN_CENTER_VERTICAL)
        baseline = wx.Choice(tab8, choices=["Tree", "List"])
        baseline.SetSelection(0)
        sizer8.Add(baseline, 0)

        # Experiment 1: InvalidateBestSize after creation
        sizer8.Add(wx.StaticText(tab8, label="InvalidateBestSize:"), 0, wx.ALIGN_CENTER_VERTICAL)
        exp1 = wx.Choice(tab8, choices=["Tree", "List"])
        exp1.SetSelection(0)
        exp1.InvalidateBestSize()
        sizer8.Add(exp1, 0)

        # Experiment 2: InvalidateBestSize + Layout
        sizer8.Add(wx.StaticText(tab8, label="InvalidateBestSize+Layout:"), 0, wx.ALIGN_CENTER_VERTICAL)
        exp2 = wx.Choice(tab8, choices=["Tree", "List"])
        exp2.SetSelection(0)
        exp2.InvalidateBestSize()
        sizer8.Add(exp2, 0)

        # Experiment 3: CallAfter InvalidateBestSize
        sizer8.Add(wx.StaticText(tab8, label="CallAfter Invalidate:"), 0, wx.ALIGN_CENTER_VERTICAL)
        exp3 = wx.Choice(tab8, choices=["Tree", "List"])
        exp3.SetSelection(0)
        wx.CallAfter(exp3.InvalidateBestSize)
        sizer8.Add(exp3, 0)

        # Experiment 4: SetItems after creation
        sizer8.Add(wx.StaticText(tab8, label="SetItems after create:"), 0, wx.ALIGN_CENTER_VERTICAL)
        exp4 = wx.Choice(tab8)
        exp4.SetItems(["Tree", "List"])
        exp4.SetSelection(0)
        sizer8.Add(exp4, 0)

        # Experiment 5: Clear then Append
        sizer8.Add(wx.StaticText(tab8, label="Clear+Append:"), 0, wx.ALIGN_CENTER_VERTICAL)
        exp5 = wx.Choice(tab8, choices=["Dummy1", "Dummy2", "Dummy3"])
        exp5.Clear()
        exp5.Append("Tree")
        exp5.Append("List")
        exp5.SetSelection(0)
        sizer8.Add(exp5, 0)

        # Experiment 6: wx.ComboBox as replacement (known to work)
        sizer8.Add(wx.StaticText(tab8, label="ComboBox READONLY:"), 0, wx.ALIGN_CENTER_VERTICAL)
        exp6 = wx.ComboBox(tab8, choices=["Tree", "List"], style=wx.CB_READONLY)
        exp6.SetSelection(0)
        sizer8.Add(exp6, 0)

        tab8.SetSizer(wx.BoxSizer(wx.VERTICAL))
        tab8.GetSizer().Add(sizer8, 1, wx.ALL, 15)
        notebook.AddPage(tab8, "Experiments")

        main_sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 5)

        # Platform info at bottom
        main_sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.ALL, 5)

        wayland = os.environ.get('XDG_SESSION_TYPE', 'unknown')
        display = os.environ.get('WAYLAND_DISPLAY', os.environ.get('DISPLAY', 'unknown'))
        desktop = os.environ.get('XDG_CURRENT_DESKTOP', 'unknown')
        gtk_backend = os.environ.get('GDK_BACKEND', 'auto')

        info = f"wxPython: {wx.version()} | Platform: {wx.PlatformInfo[0]}\n"
        info += f"Session: {wayland} | Display: {display} | Desktop: {desktop} | GDK_BACKEND: {gtk_backend}"

        info_text = wx.StaticText(panel, label=info)
        info_text.SetFont(wx.Font(8, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        main_sizer.Add(info_text, 0, wx.ALL, 5)

        panel.SetSizer(main_sizer)
        self.Centre()

    def on_popup_menu(self, event):
        menu = wx.Menu()
        menu.Append(wx.ID_ANY, "Tree")
        menu.Append(wx.ID_ANY, "List")
        menu.AppendSeparator()
        menu.Append(wx.ID_ANY, "Option 3")
        self.PopupMenu(menu)
        menu.Destroy()

    def on_popup_menu_at_origin(self, event):
        menu = wx.Menu()
        menu.Append(wx.ID_ANY, "Tree")
        menu.Append(wx.ID_ANY, "List")
        self.PopupMenu(menu, wx.Point(0, 0))
        menu.Destroy()

    def on_popup_menu_with_pos(self, event):
        menu = wx.Menu()
        menu.Append(wx.ID_ANY, "Tree")
        menu.Append(wx.ID_ANY, "List")
        btn = event.GetEventObject()
        pos = btn.GetPosition()
        size = btn.GetSize()
        self.PopupMenu(menu, wx.Point(pos.x, pos.y + size.height))
        menu.Destroy()

    def on_open_dialog(self, event):
        dlg = TestDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def on_search2_click(self, event):
        """Show search menu at (0, height) position."""
        menu = self.search2.GetMenu()
        height = self.search2.GetSize().GetHeight()
        self.search2.PopupMenu(menu, wx.Point(0, height))

    def on_search_menu_no_pos(self, event):
        """Show a menu without position (let wxPython decide)."""
        menu = wx.Menu()
        menu.AppendCheckItem(wx.ID_ANY, "Match case")
        menu.AppendCheckItem(wx.ID_ANY, "Include sub items")
        btn = event.GetEventObject()
        btn.PopupMenu(menu)
        menu.Destroy()

    def on_search_menu_with_pos(self, event):
        """Show a menu at (0, height) relative to button."""
        menu = wx.Menu()
        menu.AppendCheckItem(wx.ID_ANY, "Match case")
        menu.AppendCheckItem(wx.ID_ANY, "Include sub items")
        btn = event.GetEventObject()
        height = btn.GetSize().GetHeight()
        btn.PopupMenu(menu, wx.Point(0, height))
        menu.Destroy()


class TestDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Dialog with Choice", size=(300, 200))

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(self, label="Choice in Dialog:"), 0, wx.ALL, 10)

        c1 = wx.Choice(self, choices=["Tree", "List"])
        c1.SetSelection(0)
        sizer.Add(c1, 0, wx.ALL, 10)

        c2 = wx.Choice(self, choices=["One", "Two", "Three", "Four", "Five"])
        c2.SetSelection(0)
        sizer.Add(c2, 0, wx.ALL, 10)

        btn = wx.Button(self, wx.ID_OK, "Close")
        sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self.SetSizer(sizer)
        self.Centre()


def main():
    app = wx.App()
    frame = TestFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
