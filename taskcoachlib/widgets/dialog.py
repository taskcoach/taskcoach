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
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
from wx.lib.agw import aui
from . import notebook
import wx
import wx.html
from wx.lib import sized_controls
from ..tools import wxhelper
from taskcoachlib import patterns


class Dialog(sized_controls.SizedDialog):
    def __init__(
        self,
        parent,
        title,
        icon_id="nuvola_actions_edit",
        direction=None,
        *args,
        **kwargs
    ):
        self._buttonTypes = kwargs.get("buttonTypes", wx.OK | wx.CANCEL)
        super().__init__(
            parent,
            -1,
            title,
            style=wx.DEFAULT_DIALOG_STYLE
            | wx.RESIZE_BORDER
            | wx.MAXIMIZE_BOX
            | wx.MINIMIZE_BOX,
        )
        self.SetIcon(icon_catalog.get_wx_icon(icon_id, LIST_ICON_SIZE))

        if operating_system.isWindows():
            # Without this the window has no taskbar icon on Windows, and the focus comes back to the main
            # window instead of this one when returning to Task Coach through Alt+Tab. Which is probably not
            # what we want.
            import win32gui, win32con

            ex_style = win32gui.GetWindowLong(
                self.GetHandle(), win32con.GWL_EXSTYLE
            )
            win32gui.SetWindowLong(
                self.GetHandle(),
                win32con.GWL_EXSTYLE,
                ex_style | win32con.WS_EX_APPWINDOW,
            )

        self._panel = self.GetContentsPane()
        self._panel.SetSizerType("vertical")
        self._panel.SetSizerProps(expand=True, proportion=1)
        self._direction = direction
        self._interior = self.createInterior()
        self._interior.SetSizerProps(expand=True, proportion=1)
        self.fillInterior()
        self._buttons = self.createButtons()
        self._panel.Fit()
        self.Fit()
        self.place()
        # A size given to the interior is for the first fit only: the
        # dialog may be cut to the screen and made smaller, its
        # contents scrolling (docs/WINDOW_GEOMETRY.md, Decisions 10)
        self._interior.SetMinSize(wx.DefaultSize)
        if not operating_system.isGTK():
            patterns.later.soon(self, self.__safeRaise)
        patterns.later.soon(self, self.__safePanelSetFocus)
        # Wayland needs a size event to trigger proper initial layout
        if operating_system.isWayland():
            patterns.later.soon(self, self.__safeLayoutRefresh)

    def __safeLayoutRefresh(self):
        """Force layout refresh on Wayland where initial render may be incomplete.

        GTK3 caches widget best sizes, and when windows are laid out while hidden
        (as dialogs are during construction), the cached sizes may be wrong.
        We must invalidate all cached sizes recursively, then re-layout.
        See: https://github.com/wxWidgets/wxWidgets/issues/19053
        """
        try:
            if self and self._panel:
                self.__invalidateBestSizeRecursively(self)
                self._panel.Layout()
                self.Layout()
                self.Refresh()
        except RuntimeError:
            pass

    def __invalidateBestSizeRecursively(self, window):
        """Recursively invalidate best size cache for window and all children."""
        try:
            window.InvalidateBestSize()
            for child in window.GetChildren():
                self.__invalidateBestSizeRecursively(child)
        except RuntimeError:
            pass

    def __safeRaise(self):
        """Safely raise window, guarding against deleted C++ objects."""
        try:
            if self:
                self.Raise()
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def __safePanelSetFocus(self):
        """Safely set focus on panel, guarding against deleted C++ objects."""
        try:
            if self._panel:
                self._panel.SetFocus()
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def place(self):
        """Centre on the parent, also through the first show, at most
        80% of its monitor each way."""
        wxhelper.centre_on_parent(self)

    def createInterior(self):
        raise NotImplementedError

    def fillInterior(self):
        pass

    def createButtons(self):
        button_types = (
            wx.OK if self._buttonTypes == wx.ID_CLOSE else self._buttonTypes
        )
        button_sizer = self.CreateStdDialogButtonSizer(
            button_types
        )  # type: wx.StdDialogButtonSizer
        if self._buttonTypes & wx.OK or self._buttonTypes & wx.ID_CLOSE:
            wxhelper.get_dialog_button(button_sizer, wx.ID_OK).Bind(
                wx.EVT_BUTTON, self.ok
            )
        if self._buttonTypes & wx.CANCEL:
            wxhelper.get_dialog_button(button_sizer, wx.ID_CANCEL).Bind(
                wx.EVT_BUTTON, self.cancel
            )
        if self._buttonTypes & wx.APPLY:
            wxhelper.get_dialog_button(button_sizer, wx.ID_APPLY).Bind(
                wx.EVT_BUTTON, self.apply
            )
        if self._buttonTypes == wx.ID_CLOSE:
            wxhelper.get_dialog_button(button_sizer, wx.ID_OK).SetLabel(
                _("Close")
            )
        self.SetButtonSizer(button_sizer)
        return button_sizer

    def ok(self, event=None):
        if event:
            event.Skip()
        self.Close(True)
        self.Destroy()

    def apply(self, event=None):
        pass

    def cancel(self, event=None):
        if event:
            event.Skip()
        self.Close(True)
        self.Destroy()


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

    def apply(self, event=None):
        self.okPages()

    def okPages(self, *args, **kwargs):
        for page in self._interior:
            page.ok(*args, **kwargs)

    def addPages(self):
        raise NotImplementedError


class HtmlWindowThatUsesWebBrowserForExternalLinks(wx.html.HtmlWindow):
    def OnLinkClicked(self, link_info):  # pylint: disable=W0221
        opened_link_in_external_browser = False
        if link_info.GetTarget() == "_blank":
            import webbrowser  # pylint: disable=W0404

            try:
                webbrowser.open(link_info.GetHref())
                opened_link_in_external_browser = True
            except webbrowser.Error:
                pass
        if not opened_link_in_external_browser:
            super(
                HtmlWindowThatUsesWebBrowserForExternalLinks, self
            ).OnLinkClicked(link_info)


class HTMLDialog(Dialog):
    def __init__(self, title, html_text, parent=None, *args, **kwargs):
        self._htmlText = html_text
        super().__init__(
            parent, title, buttonTypes=wx.ID_CLOSE, *args, **kwargs
        )

    def createInterior(self):
        interior = HtmlWindowThatUsesWebBrowserForExternalLinks(
            self._panel, -1, size=(700, 550)
        )
        if self._direction:
            interior.SetLayoutDirection(self._direction)
        return interior

    def fillInterior(self):
        self._interior.AppendToPage(self._htmlText)

    def OnLinkClicked(self, link_info):
        pass


def AttachmentSelector(**caller_keyword_arguments):
    kwargs = {
        "message": _("Add attachment"),
        "wildcard": _("All files (*.*)|*"),
        "flags": wx.FD_OPEN,
    }
    kwargs.update(caller_keyword_arguments)
    return wx.FileSelector(**kwargs)  # pylint: disable=W0142
