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
from taskcoachlib import config, patterns, widgets


class BaseTextCtrlTest(test.wxTestCase):
    def testRemoveAnyControlCharactersEnteredByUser(self):
        textctrl = widgets.textctrl.BaseTextCtrl(
            self.frame, "T\x02\x01est\x09"
        )
        self.assertEqual("Test\t", textctrl.GetValue())


class MultiLineTextCtrlTest(test.wxTestCase):
    def testOpenWebbrowserOnURLClick(self):
        textctrl = widgets.MultiLineTextCtrl(self.frame)
        textctrl.AppendText("test http://test.com/ test")
        # FIXME: simulate a mouseclick on the url

    def testSetInsertionPointAtStart(self):
        textctrl = widgets.MultiLineTextCtrl(self.frame, text="Hiya")
        self.assertEqual(0, textctrl.GetInsertionPoint())

    def test_squiggle_colour_follows_preferences(self):
        settings = config.Settings(load=False)
        textctrl = widgets.MultiLineTextCtrl(self.frame, settings=settings)
        for section in ("spellcheck_light", "spellcheck_dark"):
            settings.setvalue(section, "squiggle_color", (1, 2, 3))
        patterns.Event("spellcheck.colours.changed", settings).send()
        self.assertEqual(
            wx.Colour(1, 2, 3),
            textctrl._textCtrl.IndicatorGetForeground(
                widgets.textctrl.SPELLCHECK_INDICATOR
            ),
        )
