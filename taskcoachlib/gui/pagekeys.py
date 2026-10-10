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

# Ctrl+PgDn and Ctrl+PgUp go to the next and previous page of the
# window the focus is in, whatever control has it: the next view in the
# main window and its floating views, the next tab in an editor or
# Preferences. Before any control sees them, so a list does not take
# them as Page Down (docs/MENUS.md#pages-ctrlpgdn-and-ctrlpgup).

import wx
from wx.lib.agw import aui
from taskcoachlib.widgets.notebook import BookMixin

_FORWARD = {
    wx.WXK_PAGEDOWN: True,
    wx.WXK_NUMPAD_PAGEDOWN: True,
    wx.WXK_PAGEUP: False,
    wx.WXK_NUMPAD_PAGEUP: False,
}


def _views(window):
    """The viewer container of the main window holding the window, its
    floating views included; None outside it (an editor, a dialog)."""
    top = wx.GetTopLevelParent(window)
    if isinstance(top, aui.AuiFloatingFrame):
        top = top.GetParent()
    container = getattr(top, "viewer", None)
    return container if hasattr(container, "advance_selection") else None


def _book(window):
    """The tabs of the dialog holding the window: the ones it is on, or
    the dialog's first; None without any."""
    ancestor = window
    while ancestor is not None:
        if isinstance(ancestor, BookMixin):
            return ancestor
        if ancestor.IsTopLevel():
            break
        ancestor = ancestor.GetParent()
    windows = [wx.GetTopLevelParent(window)]
    while windows:
        each = windows.pop(0)
        if isinstance(each, BookMixin):
            return each
        windows.extend(
            child for child in each.GetChildren() if not child.IsTopLevel()
        )
    return None


def turn_page(window, forward):
    """Go to the next or previous page of the window holding window;
    whether there was one."""
    views = _views(window)
    if views is not None:
        views.advance_selection(forward)
        return True
    book = _book(window)
    if book is not None and book.GetPageCount() > 1:
        book.AdvanceSelection(forward)
        return True
    return False


def _on_char_hook(event):
    forward = _FORWARD.get(event.GetKeyCode())
    window = event.GetEventObject()
    if (
        forward is None
        or event.GetModifiers() != wx.MOD_CONTROL
        or not isinstance(window, wx.Window)
        or not turn_page(window, forward)
    ):
        event.Skip()


_installed = False


def install(app):
    """Take Ctrl+PgDn and Ctrl+PgUp for pages; once, at start."""
    global _installed  # pylint: disable=W0603
    if _installed:
        return
    _installed = True
    app.Bind(wx.EVT_CHAR_HOOK, _on_char_hook)
