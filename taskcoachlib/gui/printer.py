"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2008 Rob McMullen <rob.mcmullen@gmail.com>

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

from taskcoachlib import persistence, patterns, operating_system
from taskcoachlib.i18n import _
import wx


# Prepare for printing. On Jolicloud, printing crashes unless we do this:

# BUT on Fedora, if we do this, TaskCoach doesn't even start. My opinion is that
# Fedora is more widely used than Jolicloud.

## if operating_system.isGTK():
##     try:
##         import gtk  # pylint: disable=F0401
##         gtk.remove_log_handlers()
##     except ImportError:
##         pass


class PrinterSettings(object, metaclass=patterns.Singleton):
    edges = ("top", "left", "bottom", "right")

    def __init__(self, settings):
        self.settings = settings
        self.printData = wx.PrintData()
        self.pageSetupData = wx.PageSetupDialogData(self.printData)
        self.__initialize_from_settings()

    def updatePageSetupData(self, data):
        self.pageSetupData = wx.PageSetupDialogData(data)
        self.__update_print_data(data.GetPrintData())
        self.__save_to_settings()

    def __update_print_data(self, printData):
        self.printData = wx.PrintData(printData)
        self.pageSetupData.SetPrintData(self.printData)

    def __getattr__(self, attr):
        try:
            return getattr(self.pageSetupData, attr)
        except AttributeError:
            return getattr(self.printData, attr)

    def __initialize_from_settings(self):
        """Load the printer settings from the user settings."""
        margin = dict()
        for edge in self.edges:
            margin[edge] = self.__get_setting("margin_" + edge)
        top_left = wx.Point(margin["left"], margin["top"])
        bottom_right = wx.Point(margin["right"], margin["bottom"])
        self.SetMarginTopLeft(top_left)
        self.SetMarginBottomRight(bottom_right)
        self.SetPaperId(self.__get_setting("paper_id"))
        self.SetOrientation(self.__get_setting("orientation"))

    def __save_to_settings(self):
        """Save the printer settings to the user settings."""
        margin = dict()
        margin["left"], margin["top"] = self.GetMarginTopLeft()
        margin["right"], margin["bottom"] = self.GetMarginBottomRight()
        for edge in self.edges:
            self.__set_setting("margin_" + edge, margin[edge])
        self.__set_setting("paper_id", self.GetPaperId())
        self.__set_setting("orientation", self.GetOrientation())

    def __get_setting(self, option):
        return self.settings.getint("printer", option)

    def __set_setting(self, option, value):
        self.settings.set("printer", option, str(value))


class HTMLPrintout(wx.html.HtmlPrintout):
    def __init__(self, html_text, settings):
        super().__init__()
        self.SetHtmlText(html_text)
        self.SetFooter(_("Page") + " @PAGENUM@/@PAGESCNT@", wx.html.PAGE_ALL)
        # Font sizes for HTML logical font sizes -2 to +4 (7 values required)
        # These are typical default sizes used by wxHtmlWindow
        default_font_sizes = [7, 8, 10, 12, 16, 22, 30]
        self.SetFonts("Arial", "Courier", default_font_sizes)
        printer_settings = PrinterSettings(settings)
        left, top = printer_settings.pageSetupData.GetMarginTopLeft()
        right, bottom = printer_settings.pageSetupData.GetMarginBottomRight()
        self.SetMargins(top, bottom, left, right)


class DCPrintout(wx.Printout):
    def __init__(self, widget):
        self.widget = widget
        super().__init__()

    def OnPrintPage(self, page):  # pylint: disable=W0613
        self.widget.Draw(self.GetDC())

    def GetPageInfo(self):  # pylint: disable=W0221
        return (1, 1, 1, 1)


def Printout(viewer, settings, printSelectionOnly=False, twoPrintouts=False):
    widget = viewer.getWidget()
    if hasattr(widget, "GetPrintout"):
        _printout = widget.GetPrintout
    elif hasattr(widget, "Draw"):

        def _printout(settings):
            return DCPrintout(widget)

    else:
        html_text = persistence.viewer2html(
            viewer, settings, selectionOnly=printSelectionOnly
        )[0]

        def _printout(settings):
            return HTMLPrintout(html_text, settings)

    result = _printout(PrinterSettings(settings))
    if twoPrintouts:
        result = (result, _printout(PrinterSettings(settings)))
    return result
