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

Control focus management (docs/FOCUS_MANAGEMENT.md): in a window, only
the control with the focus shows a text selection, on every platform.
"""

import wx
import wx.stc as stc


def install(app):
    """Each time a control gets the focus, the other text controls of
    its window drop their selections. A menu or another window takes
    no control's focus here, so they keep them."""
    app.Bind(wx.EVT_CHILD_FOCUS, _on_child_focus)


def _on_child_focus(event):
    event.Skip()
    focused = wx.Window.FindFocus()
    if focused:
        drop_selections(wx.GetTopLevelParent(focused), keep=focused)


def drop_selections(window, keep):
    """Drop the text selection of every text control in the window but
    the one to keep; the windows it owns (dialogs) keep theirs."""
    for child in window.GetChildren():
        if child.IsTopLevel():
            continue
        if child is not keep:
            _drop_selection(child)
        drop_selections(child, keep)


def _drop_selection(control):
    """The caret stays where it was."""
    if isinstance(control, stc.StyledTextCtrl):
        if control.GetSelectionStart() != control.GetSelectionEnd():
            control.SetEmptySelection(control.GetCurrentPos())
    elif isinstance(control, (wx.TextEntry, wx.SearchCtrl)):
        start, end = control.GetSelection()
        if start != end:
            caret = control.GetInsertionPoint()
            control.SetSelection(caret, caret)
