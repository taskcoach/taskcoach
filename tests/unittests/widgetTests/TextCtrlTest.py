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
