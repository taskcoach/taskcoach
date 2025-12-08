#!/usr/bin/env python3
"""
Minimal test case for AUI toolbar icon jitter during sash drag.

Toggle the flags below to isolate the root cause:
- USE_LIVE_RESIZE: Enable/disable live resize during sash drag
- USE_STRETCH_SPACER: Use stretch spacer vs two-toolbar approach
- ADD_ITEMS_AFTER_SPACER: Add items after the spacer
"""

VERSION = "1.5"

import wx
import wx.lib.agw.aui as aui

# === TOGGLE THESE TO TEST ===
USE_LIVE_RESIZE = True        # Try False - does jitter still happen?

# Control type for right-aligned "icon" - try each one!
# Options: "tool", "bitmapbutton", "button", "choice", "combobox", "searchctrl"
RIGHT_CONTROL_TYPE = "tool"
# ============================


class TestPanel(wx.Panel):
    """A panel with a toolbar and some content."""

    def __init__(self, parent, name):
        super().__init__(parent)
        self.name = name

        self.toolbar = aui.AuiToolBar(self, agwStyle=aui.AUI_TB_DEFAULT_STYLE)

        # Left icon - always a tool
        self.toolbar.AddSimpleTool(
            wx.ID_ANY, "Left",
            wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR, (16, 16)),
            "Left icon"
        )

        self.toolbar.AddStretchSpacer(1)

        # Middle - TextCtrl (known to not jitter)
        text_ctrl = wx.TextCtrl(self.toolbar, wx.ID_ANY, "Search", size=(100, -1))
        self.toolbar.AddControl(text_ctrl)

        # Right "icon" - try different control types
        if RIGHT_CONTROL_TYPE == "tool":
            # Standard tool - JITTERS
            self.toolbar.AddSimpleTool(
                wx.ID_ANY, "Right",
                wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR, (16, 16)),
                "Right icon (tool)"
            )
        elif RIGHT_CONTROL_TYPE == "bitmapbutton":
            # BitmapButton control
            btn = wx.BitmapButton(
                self.toolbar, wx.ID_ANY,
                wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR, (16, 16))
            )
            self.toolbar.AddControl(btn)
        elif RIGHT_CONTROL_TYPE == "button":
            # Regular button with label
            btn = wx.Button(self.toolbar, wx.ID_ANY, "Save", size=(50, -1))
            self.toolbar.AddControl(btn)
        elif RIGHT_CONTROL_TYPE == "choice":
            # Choice dropdown
            choice = wx.Choice(self.toolbar, wx.ID_ANY, choices=["Option1", "Option2", "Option3"])
            choice.SetSelection(0)
            self.toolbar.AddControl(choice)
        elif RIGHT_CONTROL_TYPE == "combobox":
            # ComboBox
            combo = wx.ComboBox(self.toolbar, wx.ID_ANY, "Select", choices=["A", "B", "C"], size=(80, -1))
            self.toolbar.AddControl(combo)
        elif RIGHT_CONTROL_TYPE == "searchctrl":
            # SearchCtrl
            search = wx.SearchCtrl(self.toolbar, wx.ID_ANY, size=(100, -1))
            self.toolbar.AddControl(search)

        self.toolbar.Realize()

        # Create content
        content = wx.TextCtrl(
            self, wx.ID_ANY,
            f"Panel: {name}\nControl type: {RIGHT_CONTROL_TYPE}\n\nDrag the sash and observe if the right control jitters.",
            style=wx.TE_MULTILINE
        )

        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.toolbar, flag=wx.EXPAND)
        sizer.Add(content, proportion=1, flag=wx.EXPAND)
        self.SetSizer(sizer)


class MainFrame(wx.Frame):
    """Main frame with AUI manager."""

    def __init__(self):
        super().__init__(None, title=f"AUI Toolbar Jitter Test v{VERSION}", size=(800, 600))

        # Build AUI manager flags
        agwStyle = aui.AUI_MGR_DEFAULT
        if USE_LIVE_RESIZE:
            agwStyle |= aui.AUI_MGR_LIVE_RESIZE

        self.manager = aui.AuiManager(self, agwStyle)

        # Create center panel
        center_panel = TestPanel(self, "Center")
        self.manager.AddPane(
            center_panel,
            aui.AuiPaneInfo().Name("center").Caption("Center Panel").Center().CloseButton(False)
        )

        # Create right panel
        right_panel = TestPanel(self, "Right")
        self.manager.AddPane(
            right_panel,
            aui.AuiPaneInfo().Name("right").Caption("Right Panel").Right().BestSize((250, -1))
        )

        self.manager.Update()

        self.Bind(wx.EVT_CLOSE, self.on_close)

        # Print current settings
        print(f"Version {VERSION}: LIVE_RESIZE={USE_LIVE_RESIZE}, RIGHT_CONTROL={RIGHT_CONTROL_TYPE}")

    def on_close(self, event):
        self.manager.UnInit()
        event.Skip()


class TestApp(wx.App):
    def OnInit(self):
        frame = MainFrame()
        frame.Show()
        return True


if __name__ == "__main__":
    app = TestApp()
    app.MainLoop()
