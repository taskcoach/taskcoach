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

import test
import wx
from unittest import mock
from taskcoachlib import patterns, widgets
from taskcoachlib.config import settings


class MultiLineTextCtrlTest(test.wxTestCase):
    def test_click_on_a_url_opens_it(self):
        textctrl = widgets.MultiLineTextCtrl(self.frame)
        textctrl.AppendText("test http://test.com/ test")
        inner = textctrl._textCtrl
        inner._performHighlighting()
        opened = []
        inner._StyledTextCtrl__webbrowser = mock.Mock(open=opened.append)
        point = inner.PointFromPosition(len("test http"))
        inner._onLeftClick(mock.Mock(GetPosition=lambda: point))
        self.assertEqual(["http://test.com/"], opened)

    def test_undo_keeps_the_text_loaded(self):
        textctrl = widgets.MultiLineTextCtrl(self.frame, text="Loaded")
        self.assertFalse(textctrl.CanUndo())
        textctrl.SetValue("Set by the program")
        self.assertFalse(textctrl.CanUndo())

    def test_set_insertion_point_at_start(self):
        textctrl = widgets.MultiLineTextCtrl(self.frame, text="Hiya")
        self.assertEqual(0, textctrl.GetInsertionPoint())

    def test_squiggle_colour_follows_preferences(self):
        textctrl = widgets.MultiLineTextCtrl(self.frame)
        settings.spellcheck_light.squiggle_color = (1, 2, 3)
        settings.spellcheck_dark.squiggle_color = (1, 2, 3)
        patterns.Event("spellcheck.colours.changed", settings.current()).send()
        self.assertEqual(
            wx.Colour(1, 2, 3),
            textctrl._textCtrl.IndicatorGetForeground(
                widgets.textctrl.SPELLCHECK_INDICATOR
            ),
        )

    def test_spell_checking_follows_preferences(self):
        settings.spellcheck.enabled = False
        textctrl = widgets.MultiLineTextCtrl(self.frame)
        self.assertFalse(textctrl._textCtrl._spellCheckEnabled)

    def test_preview_toggle_swaps_controls(self):
        textctrl = widgets.MultiLineTextCtrl(self.frame, text="# Title")
        self.assertFalse(textctrl.is_preview())
        textctrl.set_preview(True)
        self.assertTrue(textctrl.is_preview())
        textctrl.set_preview(False)
        self.assertFalse(textctrl.is_preview())

    def test_paint_makes_a_paint_dc_also_in_preview(self):
        """wx's documentation requires a PaintDC in every paint
        handler, also while the preview shows."""
        textctrl = widgets.MultiLineTextCtrl(self.frame, text="# Title")
        textctrl.set_preview(True)
        with mock.patch.object(widgets.textctrl.wx, "PaintDC") as paint_dc:
            textctrl._on_paint(mock.Mock())
        paint_dc.assert_called_once_with(textctrl)

    def test_preview_keeps_text_as_typed(self):
        textctrl = widgets.MultiLineTextCtrl(self.frame, text="# Title")
        textctrl.set_preview(True)
        self.assertEqual("# Title", textctrl.GetValue())
        textctrl.SetValue("## Other")
        self.assertEqual("## Other", textctrl.GetValue())
        textctrl.set_preview(False)
        self.assertEqual("## Other", textctrl.GetValue())

    def test_preview_renders_markdown(self):
        textctrl = widgets.MultiLineTextCtrl(self.frame, text="### Title")
        with mock.patch.object(
            widgets.textctrl.PreviewHtmlWindow, "SetPage"
        ) as set_page:
            textctrl.set_preview(True)
        set_page.assert_called_once()
        self.assertIn("<h3>Title</h3>", set_page.call_args[0][0])

    def test_preview_code_shade_follows_the_window_not_the_mode(self):
        # With the dark Mode chosen on a light desktop the window and
        # its text stay as they are: a dark shade made code unreadable
        settings.window.theme = "dark"
        self.assertTrue(settings.window.theme_is_dark)
        textctrl = widgets.MultiLineTextCtrl(self.frame, text="```\nx\n```")
        with mock.patch.object(
            widgets.textctrl.PreviewHtmlWindow, "SetPage"
        ) as set_page:
            textctrl.set_preview(True)
        self.assertIn('bgcolor="#f0f0f0"', set_page.call_args[0][0])

    def test_preview_code_is_copied_with_its_spaces(self):
        textctrl = widgets.MultiLineTextCtrl(
            self.frame, text="```\nls  -la\n    wc\n```"
        )
        textctrl.set_preview(True)
        self.assertEqual(
            "ls  -la\n    wc", textctrl._preview_ctrl.ToText().strip("\n")
        )

    def test_preview_opens_web_links_outside(self):
        window = widgets.textctrl.PreviewHtmlWindow(self.frame)
        link = mock.Mock(GetHref=lambda: "www.example.com/a")
        with mock.patch.object(widgets.textctrl.webbrowser, "open") as opened:
            window.OnLinkClicked(link)
        opened.assert_called_once_with("http://www.example.com/a")

    def test_preview_ignores_links_that_would_replace_the_text(self):
        window = widgets.textctrl.PreviewHtmlWindow(self.frame)
        for href in ("file:///etc/hosts", "notes.txt", "ftp://host/file"):
            link = mock.Mock(GetHref=lambda href=href: href)
            with mock.patch.object(
                widgets.textctrl.webbrowser, "open"
            ) as opened, mock.patch.object(window, "LoadPage") as load:
                window.OnLinkClicked(link)
            opened.assert_not_called()
            load.assert_not_called()

    def _f2_on(self, window):
        event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        event.SetKeyCode(wx.WXK_F2)
        event.SetEventObject(window)
        window.GetEventHandler().ProcessEvent(event)

    def test_f2_in_the_box_shows_the_preview(self):
        textctrl = widgets.MultiLineTextCtrl(self.frame, text="# Title")
        self._f2_on(textctrl._textCtrl)
        self.assertTrue(textctrl.is_preview())

    def test_f2_in_the_preview_goes_back_to_editing(self):
        textctrl = widgets.MultiLineTextCtrl(self.frame, text="# Title")
        textctrl.set_preview(True)
        self._f2_on(textctrl._preview_ctrl)
        self.assertFalse(textctrl.is_preview())

    def test_f2_posts_the_toggle_for_the_editor(self):
        textctrl = widgets.MultiLineTextCtrl(self.frame, text="# Title")
        shown = []
        textctrl.Bind(
            widgets.EVT_PREVIEW_TOGGLED,
            lambda event: shown.append(event.GetValue()),
        )
        self._f2_on(textctrl._textCtrl)
        wx.Yield()
        self.assertEqual([True], shown)

    def test_f2_with_a_modifier_leaves_the_box_alone(self):
        textctrl = widgets.MultiLineTextCtrl(self.frame, text="# Title")
        event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        event.SetKeyCode(wx.WXK_F2)
        event.SetControlDown(True)
        event.SetEventObject(textctrl._textCtrl)
        textctrl._textCtrl.GetEventHandler().ProcessEvent(event)
        self.assertFalse(textctrl.is_preview())

    def test_f2_leaves_a_single_line_box_alone(self):
        textctrl = widgets.MultiLineTextCtrl(
            self.frame, text="Subject", single_line=True
        )
        self._f2_on(textctrl._textCtrl)
        self.assertFalse(textctrl.is_preview())


class PreviewFocusHighlightTest(test.wxTestCase):
    """The focused preview shows the focused edit box's highlight, as
    the system theme draws it, without the box's field: read-only text,
    never an input box. Unfocused, it draws nothing. Compared pixel by
    pixel across the box's edges, so any theme is held to its own
    look; a focus mark of another kind (the theme's dashed outline)
    lost the highlight unnoticed."""

    def setUp(self):
        super().setUp()
        self.textctrl = widgets.MultiLineTextCtrl(self.frame, text="# Title")
        self.textctrl.SetSize((300, 120))
        self.background = self.textctrl._preview_window().GetBackgroundColour()

    def focus(self, window, event_type):
        event = wx.FocusEvent(event_type, window.GetId())
        window.GetEventHandler().ProcessEvent(event)

    def painted(self):
        """The pixels across the left and top edges, inside the padding,
        and the middle, as the box paints itself on the window's
        background."""
        width, height = self.textctrl.GetClientSize()
        bitmap = wx.Bitmap(width, height)
        dc = wx.MemoryDC(bitmap)
        dc.SetBackground(wx.Brush(self.background))
        dc.Clear()
        self.textctrl._paint_border(dc)
        padding = self.textctrl._padding
        edges = [dc.GetPixel(x, height // 2) for x in range(padding)]
        edges += [dc.GetPixel(width // 2, y) for y in range(padding)]
        middle = dc.GetPixel(width // 2, height // 2)
        dc.SelectObject(wx.NullBitmap)
        return edges, middle

    def test_the_focused_preview_shows_the_edit_box_highlight(self):
        self.focus(self.textctrl._textCtrl, wx.wxEVT_SET_FOCUS)
        edit, field = self.painted()
        self.textctrl.set_preview(True)
        self.focus(self.textctrl._preview_ctrl, wx.wxEVT_SET_FOCUS)
        preview, _ = self.painted()
        highlight = [colour for colour in edit if colour != field]
        self.assertTrue(highlight)  # The theme draws a frame
        expected = [self.background if c == field else c for c in edit]
        self.assertEqual(expected, preview)

    def test_the_unfocused_preview_draws_nothing(self):
        self.textctrl.set_preview(True)
        self.focus(self.textctrl._preview_ctrl, wx.wxEVT_SET_FOCUS)
        self.focus(self.textctrl._preview_ctrl, wx.wxEVT_KILL_FOCUS)
        edges, _ = self.painted()
        self.assertEqual([self.background] * len(edges), edges)

    def test_the_edit_box_keeps_the_theme_s_box(self):
        dc = mock.Mock()
        with mock.patch.object(wx.RendererNative, "Get") as get:
            self.textctrl._paint_border(dc)
        get.return_value.DrawTextCtrl.assert_called_once()


class PreviewPlacementTest(test.wxTestCase):
    """Text the preview leaves as it is stays where the edit box showed
    it: the preview inside the same padding, after Scintilla's own left
    margin, with no margin of its own. It sat 3 pixels right and 4
    lower (wx.html's border of 4)."""

    def setUp(self):
        super().setUp()
        self.textctrl = widgets.MultiLineTextCtrl(
            self.frame, text="two words\ntwo words\ntwo words"
        )
        self.textctrl.SetSize((400, 200))
        self.textctrl.Layout()

    def test_the_preview_starts_where_the_edit_box_text_starts(self):
        edit = self.textctrl._textCtrl
        start = edit.GetPosition() + wx.Point(edit.GetMarginLeft(), 0)
        self.textctrl.set_preview(True)
        self.assertEqual(start, self.textctrl._preview_ctrl.GetPosition())

    def test_the_preview_text_has_no_margin_of_its_own(self):
        self.textctrl.set_preview(True)
        # The first word's place in the page: each cell's position is
        # its parent's plus its own
        cell = self.textctrl._preview_ctrl.GetInternalRepresentation()
        x = y = 0
        while cell is not None:
            x, y = x + cell.GetPosX(), y + cell.GetPosY()
            cell = cell.GetFirstChild()
        self.assertEqual((0, 0), (x, y))

    def test_the_edit_box_fills_the_box_again_after(self):
        size = self.textctrl._textCtrl.GetSize()
        self.textctrl.set_preview(True)
        self.textctrl.set_preview(False)
        self.assertEqual(size, self.textctrl._textCtrl.GetSize())
