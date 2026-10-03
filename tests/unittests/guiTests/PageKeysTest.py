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

from unittest import mock

import test
import wx
from wx.lib.agw import aui
from taskcoachlib import widgets
from taskcoachlib.gui import pagekeys


class Views:
    """The main window's viewer container, as far as the keys use it."""

    def __init__(self):
        self.turns = []

    def advance_selection(self, forward):
        self.turns.append(forward)


class PageKeysTest(test.wxTestCase):
    """Ctrl+PgDn and Ctrl+PgUp turn the page of the window the focus is
    in, before any control sees them
    (docs/MENUS.md#pages-ctrlpgdn-and-ctrlpgup)."""

    def setUp(self):
        super().setUp()
        self.main = wx.Frame(None)
        self.addCleanup(self.main.Destroy)
        self.main.viewer = Views()
        self.list = wx.ListCtrl(self.main)

    def press(self, window, code=wx.WXK_PAGEDOWN, modifiers=wx.MOD_CONTROL):
        """The key as the application's char hook gets it; whether it
        was taken."""
        event = mock.Mock(
            GetKeyCode=lambda: code,
            GetModifiers=lambda: modifiers,
            GetEventObject=lambda: window,
        )
        pagekeys._on_char_hook(event)
        return not event.Skip.called

    def dialog_with_tabs(self, pages=2, parent=None):
        dialog = wx.Dialog(parent or self.main)
        self.addCleanup(dialog.Destroy)
        book = widgets.Notebook(dialog)
        for index in range(pages):
            book.AddPage(wx.Panel(book), "page %d" % index)
        return dialog, book

    def test_in_the_main_window_the_next_view(self):
        # A list takes it as Page Down otherwise
        self.assertTrue(self.press(self.list))
        self.assertEqual([True], self.main.viewer.turns)

    def test_ctrl_page_up_the_previous_view(self):
        self.press(self.list, wx.WXK_PAGEUP)
        self.assertEqual([False], self.main.viewer.turns)

    def test_in_a_floating_view_the_main_windows_views(self):
        # A view floats in a frame of its own, the main window's child
        manager = aui.AuiManager()
        pane = aui.AuiPaneInfo().Name("view").Float()
        floating = aui.AuiFloatingFrame(self.main, manager, pane)
        self.addCleanup(floating.Destroy)
        # First: its manager is pushed onto it (docs/AUI.md)
        self.addCleanup(floating._mgr.UnInit)
        self.press(wx.Panel(floating))
        self.assertEqual([True], self.main.viewer.turns)

    def test_in_an_editor_its_tabs(self):
        # Its parent is the main window, whose views stay
        dialog, book = self.dialog_with_tabs()
        field = wx.TextCtrl(book.GetPage(0))
        self.assertTrue(self.press(field))
        self.assertEqual(1, book.GetSelection())
        self.assertEqual([], self.main.viewer.turns)

    def test_from_a_dialog_button_the_dialogs_tabs(self):
        dialog, book = self.dialog_with_tabs()
        self.press(wx.Button(dialog))
        self.assertEqual(1, book.GetSelection())

    def test_a_dialog_with_one_tab_leaves_the_key(self):
        dialog, book = self.dialog_with_tabs(pages=1)
        self.assertFalse(self.press(book.GetPage(0)))

    def test_page_down_alone_is_the_controls(self):
        self.assertFalse(self.press(self.list, modifiers=wx.MOD_NONE))
        self.assertEqual([], self.main.viewer.turns)

    def test_ctrl_shift_page_down_is_the_controls(self):
        modifiers = wx.MOD_CONTROL | wx.MOD_SHIFT
        self.assertFalse(self.press(self.list, modifiers=modifiers))

    def test_other_keys_are_the_controls(self):
        self.assertFalse(self.press(self.list, ord("A")))
