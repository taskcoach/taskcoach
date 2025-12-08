#!/usr/bin/env python3
"""
Minimal test case for AUI toolbar icon jitter during sash drag.

Toggle the flags below to isolate the root cause:
- USE_LIVE_RESIZE: Enable/disable live resize during sash drag
- USE_STRETCH_SPACER: Use stretch spacer vs two-toolbar approach
- ADD_ITEMS_AFTER_SPACER: Add items after the spacer
"""

VERSION = "1.4"

import wx
import wx.lib.agw.aui as aui

# === TOGGLE THESE TO TEST ===
USE_LIVE_RESIZE = True        # Try False - does jitter still happen?
USE_STRETCH_SPACER = True     # Try False - use TWO TOOLBARS instead
ADD_ITEMS_AFTER_SPACER = True # Try False - no items after spacer (only if USE_STRETCH_SPACER=True)
USE_BITMAP_BUTTONS = False    # Try True - use BitmapButton controls instead of AddSimpleTool
# ============================


class TestPanel(wx.Panel):
    """A panel with a toolbar and some content."""

    def __init__(self, parent, name):
        super().__init__(parent)
        self.name = name

        if USE_STRETCH_SPACER:
            # APPROACH 1: Single toolbar with stretch spacer
            self.toolbar = aui.AuiToolBar(self, agwStyle=aui.AUI_TB_DEFAULT_STYLE)

            # Left icon - either as tool or as BitmapButton control
            if USE_BITMAP_BUTTONS:
                left_btn = wx.BitmapButton(
                    self.toolbar, wx.ID_ANY,
                    wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR, (16, 16))
                )
                self.toolbar.AddControl(left_btn)
            else:
                self.toolbar.AddSimpleTool(
                    wx.ID_ANY, "Left",
                    wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR, (16, 16)),
                    "Left icon"
                )

            self.toolbar.AddStretchSpacer(1)

            if ADD_ITEMS_AFTER_SPACER:
                # Right-aligned control (TextCtrl)
                text_ctrl = wx.TextCtrl(self.toolbar, wx.ID_ANY, "Search", size=(100, -1))
                self.toolbar.AddControl(text_ctrl)

                # Right icon - either as tool or as BitmapButton control
                if USE_BITMAP_BUTTONS:
                    right_btn = wx.BitmapButton(
                        self.toolbar, wx.ID_ANY,
                        wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR, (16, 16))
                    )
                    self.toolbar.AddControl(right_btn)
                else:
                    self.toolbar.AddSimpleTool(
                        wx.ID_ANY, "Right",
                        wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR, (16, 16)),
                        "Right icon"
                    )

            self.toolbar.Realize()
            toolbar_sizer = self.toolbar  # Will add directly
        else:
            # APPROACH 2: Two toolbars in a horizontal sizer (no stretch spacer)
            toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)

            # Left toolbar
            left_toolbar = aui.AuiToolBar(self, agwStyle=aui.AUI_TB_DEFAULT_STYLE)
            left_toolbar.AddSimpleTool(
                wx.ID_ANY, "Left",
                wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR, (16, 16)),
                "Left icon"
            )
            left_toolbar.Realize()
            toolbar_sizer.Add(left_toolbar, proportion=1, flag=wx.EXPAND)

            # Right toolbar
            right_toolbar = aui.AuiToolBar(self, agwStyle=aui.AUI_TB_DEFAULT_STYLE)
            text_ctrl = wx.TextCtrl(right_toolbar, wx.ID_ANY, "Search", size=(100, -1))
            right_toolbar.AddControl(text_ctrl)
            right_toolbar.AddSimpleTool(
                wx.ID_ANY, "Right",
                wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR, (16, 16)),
                "Right icon"
            )
            right_toolbar.Realize()
            toolbar_sizer.Add(right_toolbar, proportion=0, flag=wx.EXPAND)

            self.toolbar = left_toolbar  # For reference

        # Create content
        flags_info = f"LIVE_RESIZE={USE_LIVE_RESIZE}, STRETCH={USE_STRETCH_SPACER}, ITEMS_AFTER={ADD_ITEMS_AFTER_SPACER}, BITMAP_BTNS={USE_BITMAP_BUTTONS}"
        content = wx.TextCtrl(
            self, wx.ID_ANY,
            f"Content for {name}\n\n{flags_info}\n\nDrag the sash and observe toolbar icons.",
            style=wx.TE_MULTILINE
        )

        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        if USE_STRETCH_SPACER:
            sizer.Add(toolbar_sizer, flag=wx.EXPAND)
        else:
            sizer.Add(toolbar_sizer, flag=wx.EXPAND)
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
        print(f"Version {VERSION}: LIVE_RESIZE={USE_LIVE_RESIZE}, STRETCH={USE_STRETCH_SPACER}, ITEMS_AFTER={ADD_ITEMS_AFTER_SPACER}, BITMAP_BTNS={USE_BITMAP_BUTTONS}")

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
