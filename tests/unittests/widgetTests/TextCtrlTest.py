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

    def testSetInsertionPointAtStart(self):
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
