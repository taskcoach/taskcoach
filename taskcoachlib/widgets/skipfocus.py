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

Read-only displays the focus passes by (docs/FOCUS_MANAGEMENT.md,
Read-Only Displays).
"""

import wx

from taskcoachlib import patterns


def skip_focus(display, *parts):
    """Keep the focus off a read-only display and its parts (a
    picker's inner button): Tab passes it by, and focus reaching it
    another way moves on, as Tab would. The display answers False to
    AcceptsFocusFromKeyboard, so the traversal never stops on it."""
    for window in (display,) + parts:
        window.Bind(
            wx.EVT_NAVIGATION_KEY,
            lambda event: navigate_from(display, event.GetDirection()),
        )
        window.Bind(wx.EVT_SET_FOCUS, lambda event: _hand_on_soon(display))


def navigate_from(window, forward=True):
    """Move the focus as Tab would from window itself: to the field
    after it, or before it. On Windows and macOS not window.Navigate():
    there it moves from wherever the focus is
    (wxWindowBase::DoNavigateIn), so from a display's part it came back
    to the display's own handler without end (#487)."""
    if wx.Platform == "__WXGTK__":
        # GTK moves the focus itself: wxGTK's containers take no
        # navigation event, and its Navigate() sends none, so nothing
        # comes back here
        window.Navigate(forward)
        return
    parent = window.GetParent()
    if parent is None or window.IsTopLevel():
        return
    event = wx.NavigationKeyEvent()
    event.SetDirection(forward)
    event.SetFromTab(True)
    event.SetEventObject(window)
    event.SetCurrentFocus(window)
    parent.GetEventHandler().ProcessEvent(event)


def _hand_on_soon(display):
    forward = not wx.GetKeyState(wx.WXK_SHIFT)
    patterns.later.soon(display, _hand_on, display, forward)


def _hand_on(display, forward):
    """Only while the focus is still in the display: moved on
    meanwhile, by the user or other code, it stays where it went."""
    if _holds(display, wx.Window.FindFocus()):
        navigate_from(display, forward)


def _holds(window, focus):
    while focus is not None:
        if focus is window:
            return True
        if focus.IsTopLevel():
            return False
        focus = focus.GetParent()
    return False
