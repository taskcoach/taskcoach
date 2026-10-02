#!/usr/bin/env python3
"""
Minimal test case for AUI toolbar icon jitter during sash drag.

Toggle the flags below to isolate the root cause:
- USE_LIVE_RESIZE: Enable/disable live resize during sash drag
- USE_STRETCH_SPACER: Use stretch spacer vs two-toolbar approach
- ADD_ITEMS_AFTER_SPACER: Add items after the spacer
"""

VERSION = "1.8"

import wx
import wx.lib.agw.aui as aui
from wx.lib.platebtn import PlateButton, PB_STYLE_NOBG

# === TOGGLE TO TEST ===
USE_LIVE_RESIZE = True
# ======================


class TestPanel(wx.Panel):
    """A panel with a toolbar and some content."""

    def __init__(self, parent, name):
        super().__init__(parent)
        self.name = name

        self.toolbar = aui.AuiToolBar(self, agwStyle=aui.AUI_TB_DEFAULT_STYLE)

        # Left icon - tool (for comparison)
        self.toolbar.AddSimpleTool(
            wx.ID_ANY, "Tool1",
            wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR, (16, 16)),
            "Tool (left)"
        )

        self.toolbar.AddStretchSpacer(1)

        # === ALL CONTROLS AFTER STRETCH SPACER - compare which jitter ===

        # 1. Tool icon (AddSimpleTool) - EXPECTED TO JITTER
        self.toolbar.AddSimpleTool(
            wx.ID_ANY, "Tool2",
            wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR, (16, 16)),
            "Tool (jitters?)"
        )

        # 2. PlateButton (flat toolbar-style button with proper hover)
        plate_btn = PlateButton(
            self.toolbar, wx.ID_ANY,
            bmp=wx.ArtProvider.GetBitmap(wx.ART_PRINT, wx.ART_TOOLBAR, (16, 16)),
            style=PB_STYLE_NOBG
        )
        plate_btn.SetToolTip("PlateButton")
        self.toolbar.AddControl(plate_btn)

        # 3. Regular Button
        btn = wx.Button(self.toolbar, wx.ID_ANY, "Btn", size=(40, -1))
        self.toolbar.AddControl(btn)

        # 4. Choice dropdown
        choice = wx.Choice(self.toolbar, wx.ID_ANY, choices=["A", "B", "C"], size=(50, -1))
        choice.SetSelection(0)
        self.toolbar.AddControl(choice)

        # 5. TextCtrl
        text = wx.TextCtrl(self.toolbar, wx.ID_ANY, "Text", size=(50, -1))
        self.toolbar.AddControl(text)

        # 6. SearchCtrl
        search = wx.SearchCtrl(self.toolbar, wx.ID_ANY, size=(80, -1))
        self.toolbar.AddControl(search)

        # 7. Another Tool icon at the end
        self.toolbar.AddSimpleTool(
            wx.ID_ANY, "Tool3",
            wx.ArtProvider.GetBitmap(wx.ART_QUIT, wx.ART_TOOLBAR, (16, 16)),
            "Tool (end)"
        )

        self.toolbar.Realize()

        # Create content
        content = wx.TextCtrl(
            self, wx.ID_ANY,
            f"Panel: {name}\n\nToolbar has ALL control types after stretch spacer:\n"
            "1. Tool (save icon) - JITTERS?\n"
            "2. PlateButton (print icon) - Safari-style flat button\n"
            "3. Button ('Btn')\n"
            "4. Choice dropdown\n"
            "5. TextCtrl\n"
            "6. SearchCtrl\n"
            "7. Tool (quit icon) - JITTERS?\n\n"
            "Drag the sash and observe which controls jitter!",
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
        print(f"Version {VERSION}: LIVE_RESIZE={USE_LIVE_RESIZE} - ALL controls shown")

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
