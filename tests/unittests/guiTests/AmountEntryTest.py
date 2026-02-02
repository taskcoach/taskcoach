# -*- coding: UTF-8 -*-
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
from taskcoachlib.gui.dialog import entry
from taskcoachlib.widgets.numericctrl import NumericCtrl
from taskcoachlib.widgets.currencyctrl import CurrencyCtrl


class AmountEntryTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.amountEntry = entry.AmountEntry(self.frame)

    def testCreate(self):
        self.assertEqual(0.0, self.amountEntry.GetValue())

    def testSetValue(self):
        self.amountEntry.SetValue(1.0)
        self.assertEqual(1.0, self.amountEntry.GetValue())


class NumericCtrlTest(test.wxTestCase):
    """Tests for NumericCtrl base class."""

    def setUp(self):
        super().setUp()
        self.ctrl = NumericCtrl(self.frame, value=0.0, decimal_places=2,
                                decimal_char=".")

    def testCreateDefault(self):
        self.assertEqual(0.0, self.ctrl.GetValue())

    def testCreateWithValue(self):
        ctrl = NumericCtrl(self.frame, value=12.34, decimal_places=2,
                           decimal_char=".")
        self.assertEqual(12.34, ctrl.GetValue())

    def testSetValue(self):
        self.ctrl.SetValue(25.5)
        self.assertEqual(25.5, self.ctrl.GetValue())

    def testSetValueFormatsDisplay(self):
        self.ctrl.SetValue(12.3)
        self.assertEqual("12.30", wx.TextCtrl.GetValue(self.ctrl))

    def testGetValueReturnsPythonFloat(self):
        self.ctrl.SetValue(99.99)
        result = self.ctrl.GetValue()
        self.assertIsInstance(result, float)
        self.assertEqual(99.99, result)

    def testEmptyFieldReturnsZero(self):
        wx.TextCtrl.SetValue(self.ctrl, "")
        self.assertEqual(0.0, self.ctrl.GetValue())

    def testInvalidTextReturnsLastSetValue(self):
        self.ctrl.SetValue(10.0)
        # Directly set invalid text bypassing our SetValue
        wx.TextCtrl.SetValue(self.ctrl, "abc")
        self.assertEqual(10.0, self.ctrl.GetValue())

    def testBlurFormatsValidInput(self):
        """Valid input is formatted on blur."""
        self.ctrl.SetValue(0.0)
        wx.TextCtrl.SetValue(self.ctrl, "12.34")
        # Simulate blur
        event = wx.FocusEvent(wx.wxEVT_KILL_FOCUS)
        self.ctrl._onKillFocus(event)
        self.assertEqual("12.34", wx.TextCtrl.GetValue(self.ctrl))

    def testBlurRevertsInvalidInput(self):
        """Invalid input reverts to last set value on blur."""
        self.ctrl.SetValue(5.0)
        wx.TextCtrl.SetValue(self.ctrl, "12.34.56")
        event = wx.FocusEvent(wx.wxEVT_KILL_FOCUS)
        self.ctrl._onKillFocus(event)
        self.assertEqual("5.00", wx.TextCtrl.GetValue(self.ctrl))

    def testBlurRevertsGarbageInput(self):
        """Garbage text reverts to last set value on blur."""
        self.ctrl.SetValue(7.5)
        wx.TextCtrl.SetValue(self.ctrl, "abc1.00xyz")
        event = wx.FocusEvent(wx.wxEVT_KILL_FOCUS)
        self.ctrl._onKillFocus(event)
        self.assertEqual("7.50", wx.TextCtrl.GetValue(self.ctrl))

    def testBlurEmptyFieldBecomesZero(self):
        """Empty field becomes 0.00 on blur."""
        self.ctrl.SetValue(10.0)
        wx.TextCtrl.SetValue(self.ctrl, "")
        event = wx.FocusEvent(wx.wxEVT_KILL_FOCUS)
        self.ctrl._onKillFocus(event)
        self.assertEqual("0.00", wx.TextCtrl.GetValue(self.ctrl))


class NumericCtrlFloatingTest(test.wxTestCase):
    """Tests for NumericCtrl with floating decimal places (decimal_places=None)."""

    def setUp(self):
        super().setUp()
        self.ctrl = NumericCtrl(self.frame, value=0.0, decimal_places=None,
                                decimal_char=".")

    def testFloatingFormatsNoTrailingZeros(self):
        self.ctrl.SetValue(12.0)
        self.assertEqual("12", wx.TextCtrl.GetValue(self.ctrl))

    def testFloatingPreservesPrecision(self):
        self.ctrl.SetValue(12.3)
        self.assertEqual("12.3", wx.TextCtrl.GetValue(self.ctrl))

    def testFloatingFormatsSmallDecimals(self):
        self.ctrl.SetValue(0.5)
        self.assertEqual("0.5", wx.TextCtrl.GetValue(self.ctrl))


class NumericCtrlLocaleTest(test.wxTestCase):
    """Tests for NumericCtrl with non-period decimal char."""

    def setUp(self):
        super().setUp()
        self.ctrl = NumericCtrl(self.frame, value=0.0, decimal_places=2,
                                decimal_char=",")

    def testDisplayUsesLocaleDecimal(self):
        self.ctrl.SetValue(25.5)
        self.assertEqual("25,50", wx.TextCtrl.GetValue(self.ctrl))

    def testGetValueReturnsPeriodDecimal(self):
        self.ctrl.SetValue(25.5)
        self.assertEqual(25.5, self.ctrl.GetValue())

    def testBlurParsesLocaleDecimal(self):
        wx.TextCtrl.SetValue(self.ctrl, "12,34")
        event = wx.FocusEvent(wx.wxEVT_KILL_FOCUS)
        self.ctrl._onKillFocus(event)
        self.assertEqual(12.34, self.ctrl.GetValue())

    def testBlurFormatsWithLocaleDecimal(self):
        wx.TextCtrl.SetValue(self.ctrl, "12,34")
        event = wx.FocusEvent(wx.wxEVT_KILL_FOCUS)
        self.ctrl._onKillFocus(event)
        self.assertEqual("12,34", wx.TextCtrl.GetValue(self.ctrl))


class CurrencyCtrlTest(test.wxTestCase):
    """Tests for CurrencyCtrl subclass."""

    def setUp(self):
        super().setUp()
        self.ctrl = CurrencyCtrl(self.frame, value=0.0, decimal_char=".")

    def testCreate(self):
        self.assertEqual(0.0, self.ctrl.GetValue())

    def testSetValue(self):
        self.ctrl.SetValue(42.0)
        self.assertEqual(42.0, self.ctrl.GetValue())

    def testFormatsToTwoDecimalPlaces(self):
        """Default locale should give 2 decimal places."""
        self.ctrl.SetValue(5.0)
        self.assertEqual("5.00", wx.TextCtrl.GetValue(self.ctrl))
