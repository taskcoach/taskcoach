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

import wx
import test
from taskcoachlib import gui
from taskcoachlib.config import settings


class PrinterTest(test.TestCase):
    def setUp(self):
        super().setUp()
        self.margins = dict(top=1, left=2, bottom=3, right=4)
        self.printerSettings = gui.printer.PrinterSettings()
        self.pageSetupData = wx.PageSetupDialogData()

    def tearDown(self):
        super().tearDown()
        self.resetPrinterSettings()

    def resetPrinterSettings(self):
        gui.printer.PrinterSettings.deleteInstance()  # pylint: disable=E1101

    def testInitialSettings(self):
        printer_settings = self.printerSettings
        self.assertEqual(wx.Point(0, 0), printer_settings.GetMarginTopLeft())
        self.assertEqual(0, printer_settings.GetPaperId())
        self.assertEqual(wx.PORTRAIT, printer_settings.GetOrientation())

    def testSetMargin(self):
        self.pageSetupData.SetMarginTopLeft(wx.Point(10, 1))
        self.printerSettings.updatePageSetupData(self.pageSetupData)
        self.assertEqual(
            wx.Point(10, 1), self.printerSettings.GetMarginTopLeft()
        )

    def testDefaultMarginsFromSettings(self):
        for margin in self.margins:
            self.assertEqual(0, settings.get("printer", "margin_" + margin))

    def testSetPaperId(self):
        self.pageSetupData.SetPaperId(1)
        self.printerSettings.updatePageSetupData(self.pageSetupData)
        self.assertEqual(1, self.printerSettings.GetPaperId())

    def testDefaultPaperIdFromSettings(self):
        self.assertEqual(0, settings.get("printer", "paper_id"))

    def testSetOrientation(self):
        self.pageSetupData.GetPrintData().SetOrientation(wx.LANDSCAPE)
        self.printerSettings.updatePageSetupData(self.pageSetupData)
        self.assertEqual(wx.LANDSCAPE, self.printerSettings.GetOrientation())

    def testDefaultOrientationFromSettings(self):
        self.assertEqual(wx.PORTRAIT, settings.get("printer", "orientation"))

    def testUpdateMarginsInPageSetupDataUpdatesSettings(self):
        self.pageSetupData.SetMarginTopLeft(
            wx.Point(self.margins["left"], self.margins["top"])
        )
        self.pageSetupData.SetMarginBottomRight(
            wx.Point(self.margins["right"], self.margins["bottom"])
        )
        self.printerSettings.updatePageSetupData(self.pageSetupData)
        for margin in self.margins:
            self.assertEqual(
                self.margins[margin],
                settings.get("printer", "margin_" + margin),
            )

    def testUpdatePaperIdInPageSetupDataUpdatesSettings(self):
        self.pageSetupData.SetPaperId(1)
        self.printerSettings.updatePageSetupData(self.pageSetupData)
        self.assertEqual(1, settings.get("printer", "paper_id"))

    def testUpdateOrientationInPageSetupDataUpdatesSettings(self):
        self.pageSetupData.GetPrintData().SetOrientation(wx.LANDSCAPE)
        self.printerSettings.updatePageSetupData(self.pageSetupData)
        self.assertEqual(wx.LANDSCAPE, settings.get("printer", "orientation"))

    def testMarginsInPageSetupDataAreUpdatedFromSettings(self):
        self.resetPrinterSettings()
        for margin in self.margins:
            settings.set("printer", "margin_" + margin, self.margins[margin])
        printer_settings = gui.printer.PrinterSettings()
        self.assertEqual(wx.Point(2, 1), printer_settings.GetMarginTopLeft())
        self.assertEqual(
            wx.Point(4, 3), printer_settings.GetMarginBottomRight()
        )

    def testPaperIdInPageSetupDataIsUpdatedFromSettings(self):
        self.resetPrinterSettings()
        settings.set("printer", "paper_id", 1)
        printer_settings = gui.printer.PrinterSettings()
        self.assertEqual(1, printer_settings.GetPaperId())

    def testOrientationInPageSetupDataIsUpdatedFromSettings(self):
        self.resetPrinterSettings()
        settings.set("printer", "orientation", wx.LANDSCAPE)
        printer_settings = gui.printer.PrinterSettings()
        self.assertEqual(wx.LANDSCAPE, printer_settings.GetOrientation())


class HTMLPrintoutTest(test.TestCase):
    def testCreate(self):
        gui.printer.HTMLPrintout("<html></html>")
