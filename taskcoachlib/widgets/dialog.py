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

from taskcoachlib import operating_system
from taskcoachlib.i18n import _
from wx.lib.agw import aui
from . import notebook
import wx
import wx.html
from wx.lib import sized_controls
import os
import sys
import time
from ..tools import wxhelper

def _debug_log(msg):
    """Debug logging for dialog initialization tracking."""
    timestamp = time.time()
    print(f"[DIALOG DEBUG] {timestamp:.6f} {msg}", file=sys.stderr, flush=True)


class Dialog(sized_controls.SizedDialog):
    def __init__(
        self, parent, title, bitmap="edit", direction=None, *args, **kwargs
    ):
        _debug_log(f"Dialog.__init__ START: {title}")
        self._buttonTypes = kwargs.get("buttonTypes", wx.OK | wx.CANCEL)
        _debug_log("  calling super().__init__")
        super().__init__(
            parent,
            -1,
            title,
            style=wx.DEFAULT_DIALOG_STYLE
            | wx.RESIZE_BORDER
            | wx.MAXIMIZE_BOX
            | wx.MINIMIZE_BOX,
        )
        _debug_log("  super().__init__ done")
        self.SetIcon(
            wx.ArtProvider.GetIcon(bitmap, wx.ART_FRAME_ICON, (16, 16))
        )

        if operating_system.isWindows7_OrNewer():
            # Without this the window has no taskbar icon on Windows, and the focus comes back to the main
            # window instead of this one when returning to Task Coach through Alt+Tab. Which is probably not
            # what we want.
            import win32gui, win32con

            exStyle = win32gui.GetWindowLong(
                self.GetHandle(), win32con.GWL_EXSTYLE
            )
            win32gui.SetWindowLong(
                self.GetHandle(),
                win32con.GWL_EXSTYLE,
                exStyle | win32con.WS_EX_APPWINDOW,
            )

        _debug_log("  getting contents pane")
        self._panel = self.GetContentsPane()
        self._panel.SetSizerType("vertical")
        self._panel.SetSizerProps(expand=True, proportion=1)
        self._direction = direction
        _debug_log("  calling createInterior()")
        self._interior = self.createInterior()
        _debug_log("  createInterior() done")
        self._interior.SetSizerProps(expand=True, proportion=1)
        _debug_log("  calling fillInterior()")
        self.fillInterior()
        _debug_log("  fillInterior() done")
        _debug_log("  calling createButtons()")
        self._buttons = self.createButtons()
        _debug_log("  createButtons() done")
        _debug_log("  calling Fit()")
        self._panel.Fit()
        self.Fit()
        _debug_log("  Fit() done")
        self.CentreOnParent()
        if not operating_system.isGTK():
            wx.CallAfter(self.Raise)

        def _set_focus_callback():
            _debug_log("  CallAfter SetFocus executing")
            if self._panel:
                self._panel.SetFocus()
            _debug_log("  CallAfter SetFocus done")

        wx.CallAfter(_set_focus_callback)

        # Bind EVT_CLOSE to default handler. Subclasses can override by binding
        # their own handler after calling super().__init__().
        self.Bind(wx.EVT_CLOSE, self._on_close)
        _debug_log(f"Dialog.__init__ END: {title}")

    def _on_close(self, event):
        """Default close handler. Subclasses should override this if they need
        custom cleanup before destruction."""
        _debug_log("Dialog._on_close - destroying")
        self.Destroy()

    def SetExtraStyle(self, exstyle):
        # SizedDialog's constructor calls this to set WS_EX_VALIDATE_RECURSIVELY. We don't need
        # it, it makes the dialog appear in about 7 seconds, and it makes switching focus
        # between two controls take up to 5 seconds.
        pass

    def createInterior(self):
        raise NotImplementedError

    def fillInterior(self):
        pass

    def createButtons(self):
        buttonTypes = (
            wx.OK if self._buttonTypes == wx.ID_CLOSE else self._buttonTypes
        )
        buttonSizer = self.CreateStdDialogButtonSizer(
            buttonTypes
        )  # type: wx.StdDialogButtonSizer
        if self._buttonTypes & wx.OK or self._buttonTypes & wx.ID_CLOSE:
            wxhelper.getButtonFromStdDialogButtonSizer(
                buttonSizer, wx.ID_OK
            ).Bind(wx.EVT_BUTTON, self.ok)
        if self._buttonTypes & wx.CANCEL:
            wxhelper.getButtonFromStdDialogButtonSizer(
                buttonSizer, wx.ID_CANCEL
            ).Bind(wx.EVT_BUTTON, self.cancel)
        if self._buttonTypes == wx.ID_CLOSE:
            wxhelper.getButtonFromStdDialogButtonSizer(
                buttonSizer, wx.ID_OK
            ).SetLabel(_("Close"))
        self.SetButtonSizer(buttonSizer)
        return buttonSizer

    def ok(self, event=None):
        if event:
            event.Skip()
        self.Close(True)
        # Note: Don't call Destroy() here - EVT_CLOSE handler is responsible
        # for destruction. Calling both Close() and Destroy() causes double
        # destruction which crashes on GTK.

    def cancel(self, event=None):
        if event:
            event.Skip()
        self.Close(True)
        # Note: Don't call Destroy() here - EVT_CLOSE handler is responsible
        # for destruction. Calling both Close() and Destroy() causes double
        # destruction which crashes on GTK.

    def disableOK(self):
        wxhelper.getButtonFromStdDialogButtonSizer(
            self._buttons, wx.ID_OK
        ).Disable()

    def enableOK(self):
        wxhelper.getButtonFromStdDialogButtonSizer(
            self._buttons, wx.ID_OK
        ).Enable()


class NotebookDialog(Dialog):
    def createInterior(self):
        return notebook.Notebook(
            self._panel,
            agwStyle=aui.AUI_NB_DEFAULT_STYLE
            & ~aui.AUI_NB_TAB_SPLIT
            & ~aui.AUI_NB_TAB_MOVE
            & ~aui.AUI_NB_DRAW_DND_TAB,
        )

    def fillInterior(self):
        self.addPages()

    def __getitem__(self, index):
        return self._interior[index]

    def ok(self, *args, **kwargs):
        self.okPages()
        super().ok(*args, **kwargs)

    def okPages(self, *args, **kwargs):
        for page in self._interior:
            page.ok(*args, **kwargs)

    def addPages(self):
        raise NotImplementedError


class HtmlWindowThatUsesWebBrowserForExternalLinks(wx.html.HtmlWindow):
    def OnLinkClicked(self, linkInfo):  # pylint: disable=W0221
        openedLinkInExternalBrowser = False
        if linkInfo.GetTarget() == "_blank":
            import webbrowser  # pylint: disable=W0404

            try:
                webbrowser.open(linkInfo.GetHref())
                openedLinkInExternalBrowser = True
            except webbrowser.Error:
                pass
        if not openedLinkInExternalBrowser:
            super(
                HtmlWindowThatUsesWebBrowserForExternalLinks, self
            ).OnLinkClicked(linkInfo)


class HTMLDialog(Dialog):
    def __init__(self, title, htmlText, *args, **kwargs):
        self._htmlText = htmlText
        super().__init__(None, title, buttonTypes=wx.ID_CLOSE, *args, **kwargs)

    def createInterior(self):
        interior = HtmlWindowThatUsesWebBrowserForExternalLinks(
            self._panel, -1, size=(550, 400)
        )
        if self._direction:
            interior.SetLayoutDirection(self._direction)
        return interior

    def fillInterior(self):
        self._interior.AppendToPage(self._htmlText)

    def OnLinkClicked(self, linkInfo):
        pass


def AttachmentSelector(**callerKeywordArguments):
    kwargs = {
        "message": _("Add attachment"),
        "default_path": os.getcwd(),
        "wildcard": _("All files (*.*)|*"),
        "flags": wx.FD_OPEN,
    }
    kwargs.update(callerKeywordArguments)
    return wx.FileSelector(**kwargs)  # pylint: disable=W0142
