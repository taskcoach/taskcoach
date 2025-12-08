#!/usr/bin/env python3
"""
Minimal test case for AUI toolbar icon jitter during sash drag.

This reproduces the setup:
- Main window with AUI manager
- Center pane and right-docked pane
- Each pane has a toolbar with:
  - One icon on the left
  - Stretch spacer
  - A TextCtrl (control) on the right
  - One icon on the right

Test:
1. Drag the sash between center and right pane - observe if right-aligned icons jitter
2. Resize the outer window - observe if toolbar moves correctly
"""

import wx
import wx.lib.agw.aui as aui


class TestPanel(wx.Panel):
    """A panel with a toolbar and some content."""

    def __init__(self, parent, name):
        super().__init__(parent)
        self.name = name

        # Create toolbar with NO_AUTORESIZE to prevent AUI from resizing during sash ops
        self.toolbar = aui.AuiToolBar(self, agwStyle=aui.AUI_TB_NO_AUTORESIZE)

        # Left icon
        self.toolbar.AddSimpleTool(
            wx.ID_ANY, "Left",
            wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR, (16, 16)),
            "Left icon"
        )

        # Stretch spacer
        self.toolbar.AddStretchSpacer(1)

        # Right-aligned control (TextCtrl)
        text_ctrl = wx.TextCtrl(self.toolbar, wx.ID_ANY, "Search", size=(100, -1))
        self.toolbar.AddControl(text_ctrl)

        # Right icon
        self.toolbar.AddSimpleTool(
            wx.ID_ANY, "Right",
            wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR, (16, 16)),
            "Right icon"
        )

        self.toolbar.Realize()

        # Create content
        content = wx.TextCtrl(
            self, wx.ID_ANY, f"Content for {name}\n\nDrag the sash and observe toolbar icons.",
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
        super().__init__(None, title="AUI Toolbar Jitter Test", size=(800, 600))

        # Create AUI manager with LIVE_RESIZE for visual feedback
        self.manager = aui.AuiManager(
            self,
            aui.AUI_MGR_DEFAULT | aui.AUI_MGR_LIVE_RESIZE
        )

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
