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

from taskcoachlib import operating_system
import wx
import textwrap


class ToolTipMixin(object):
    """Subclass this and override OnBeforeShowToolTip to provide
    dynamic tooltip over a control."""

    def __init__(self, *args, **kwargs):
        self.__enabled = kwargs.pop("tooltipsEnabled", True)
        super().__init__(*args, **kwargs)

        self.__timer = wx.Timer(self, wx.NewId())

        self.__tip = None
        self.__position = (0, 0)
        self.__text = None
        self.__frozen = True

        self.GetMainWindow().Bind(wx.EVT_MOTION, self.__OnMotion)
        self.GetMainWindow().Bind(wx.EVT_LEAVE_WINDOW, self.__OnLeave)
        self.Bind(wx.EVT_TIMER, self.__OnTimer, id=self.__timer.GetId())
        # Stop timer on window destruction to prevent crashes
        self.Bind(wx.EVT_WINDOW_DESTROY, self.__OnDestroy)

    def SetToolTipsEnabled(self, enabled):
        self.__enabled = enabled

    def PopupMenu(self, menu):
        self.__frozen = False
        super().PopupMenu(menu)
        self.__frozen = True

    def ShowTip(self, x, y):
        # Ensure we're not too big (in the Y direction anyway) for the
        # desktop display area. This doesn't work on Linux because
        # ClientDisplayRect() returns the whole display size, not
        # taking the taskbar into account...

        if self.__frozen:
            theDisplay = wx.Display(wx.Display.GetFromPoint(wx.Point(x, y)))
            displayX, displayY, displayWidth, displayHeight = (
                theDisplay.GetClientArea()
            )
            tipWidth, tipHeight = self.__tip.GetSize()

            if tipHeight > displayHeight:
                # Too big. Take as much space as possible.
                y = 5
                tipHeight = displayHeight - 10
            elif y + tipHeight > displayY + displayHeight:
                # Adjust y so that the whole tip is visible.
                y = displayY + displayHeight - tipHeight - 5

            if tipWidth > displayWidth:
                x = 5
            elif x + tipWidth > displayX + displayWidth:
                x = displayX + displayWidth - tipWidth - 5

            self.__tip.Show(x, y, tipWidth, tipHeight)

    def DoShowTip(self, x, y, tip):
        self.__tip = tip
        self.ShowTip(x, y)

    def HideTip(self):
        if self.__tip:
            self.__tip.Hide()

    def OnBeforeShowToolTip(self, x, y):
        """Should return a wx.Frame instance that will be displayed as
        the tooltip, or None."""
        raise NotImplementedError  # pragma: no cover

    def __OnMotion(self, event):
        x, y = event.GetPosition()

        self.__timer.Stop()

        if self.__tip is not None:
            self.HideTip()
            self.__tip = None

        if self.__enabled:
            newTip = self.OnBeforeShowToolTip(x, y)
            if newTip is not None:
                self.__tip = newTip
                self.__tip.Bind(wx.EVT_MOTION, self.__OnTipMotion)
                self.__position = (x + 20, y + 10)
                self.__timer.Start(200, True)

        event.Skip()

    def __OnTipMotion(self, event):  # pylint: disable=W0613
        self.HideTip()

    def __OnLeave(self, event):
        self.__timer.Stop()

        if self.__tip is not None:
            self.HideTip()
            self.__tip = None

        event.Skip()

    def __OnDestroy(self, event):
        """Stop timer on window destruction to prevent crashes."""
        if event.GetEventObject() == self and self.__timer.IsRunning():
            self.__timer.Stop()
        event.Skip()

    def cleanupTooltipTimer(self):
        """Stop the tooltip timer to prevent crashes during widget destruction.
        This should be called from the widget's Destroy() or cleanup method."""
        if self.__timer and self.__timer.IsRunning():
            self.__timer.Stop()

    def __OnTimer(self, event):  # pylint: disable=W0613
        self.ShowTip(*self.GetMainWindow().ClientToScreen(*self.__position))


if operating_system.isWindows():

    class ToolTipBase(wx.MiniFrame):
        def __init__(self, parent):
            style = (
                wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | wx.NO_BORDER
            )
            super().__init__(parent, wx.ID_ANY, "Tooltip", style=style)

        def Show(self, x, y, w, h):  # pylint: disable=W0221
            self.SetSize(x, y, w, h)
            super().Show()

elif operating_system.isMac():

    class ToolTipBase(wx.Frame):
        def __init__(self, parent):  # pylint: disable=E1003
            style = (
                wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | wx.NO_BORDER
            )
            super().__init__(parent, wx.ID_ANY, "ToolTip", style=style)

            # There are some subtleties on Mac regarding multi-monitor
            # displays...

            self.__maxWidth, self.__maxHeight = 0, 0
            for index in range(wx.Display.GetCount()):
                x, y, width, height = wx.Display(index).GetGeometry()
                self.__maxWidth = max(self.__maxWidth, x + width)
                self.__maxHeight = max(self.__maxHeight, y + height)

            self.MoveXY(self.__maxWidth, self.__maxHeight)
            super().Show()

        def Show(self, x, y, width, height):  # pylint: disable=W0221
            self.SetSize(x, y, width, height)

        def Hide(self):  # pylint: disable=W0221
            self.MoveXY(self.__maxWidth, self.__maxHeight)

else:

    class ToolTipBase(wx.PopupWindow):
        def Show(self, x, y, width, height):  # pylint: disable=E1003,W0221
            self.SetSize(x, y, width, height)
            super().Show()


class SimpleToolTip(ToolTipBase):
    def __init__(self, parent):
        super().__init__(parent)
        self.data = []
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def SetData(self, data):
        self.data = self._wrapLongLines(data)
        self.SetSize(self._calculateSize())
        self.Refresh()  # Needed on Mac OS X

    def _wrapLongLines(self, data):
        wrappedData = []
        wrapper = textwrap.TextWrapper(width=78)
        for icon, lines in data:
            wrappedLines = []
            for line in lines:
                wrappedLines.extend(wrapper.fill(line).split("\n"))
            wrappedData.append((icon, wrappedLines))
        return wrappedData

    def _calculateSize(self):
        dc = wx.ClientDC(self)
        self._setFontBrushAndPen(dc)
        width, height = 0, 0
        for sectionIndex in range(len(self.data)):
            sectionWidth, sectionHeight = self._calculateSectionSize(
                dc, sectionIndex
            )
            width = max(width, sectionWidth)
            height += sectionHeight
        return wx.Size(width + 6, height + 6)

    def _calculateSectionSize(self, dc, sectionIndex):
        icon, lines = self.data[sectionIndex]
        sectionWidth, sectionHeight = 0, 0
        for line in lines:
            lineWidth, lineHeight = self._calculateLineSize(dc, line)
            sectionHeight += lineHeight + 1
            sectionWidth = max(sectionWidth, lineWidth)
        if 0 < sectionIndex < len(self.data) - 1:
            sectionHeight += 3  # Horizontal space between sections
        if icon:
            sectionWidth += 24  # Reserve width for icon(s)
        return sectionWidth, sectionHeight

    def _calculateLineSize(self, dc, line):
        return dc.GetTextExtent(line)

    def OnPaint(self, event):  # pylint: disable=W0613
        dc = wx.PaintDC(self)
        self._setFontBrushAndPen(dc)
        self._drawBorder(dc)
        self._drawSections(dc)

    def _setFontBrushAndPen(self, dc):
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        textColour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOTEXT)
        backgroundColour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK)
        dc.SetFont(font)
        dc.SetTextForeground(textColour)
        dc.SetBrush(wx.Brush(backgroundColour))
        dc.SetPen(wx.Pen(textColour))

    def _drawBorder(self, dc):
        width, height = self.GetClientSize()
        dc.DrawRectangle(0, 0, width, height)

    def _drawSections(self, dc):
        y = 3
        for sectionIndex in range(len(self.data)):
            y = self._drawSection(dc, y, sectionIndex)

    def _drawSection(self, dc, y, sectionIndex):
        icon, lines = self.data[sectionIndex]
        if not lines:
            return y
        x = 3
        if sectionIndex != 0:
            y = self._drawSectionSeparator(dc, x, y)
        if icon:
            x = self._drawIcon(dc, icon, x, y)
        topOfSection = y
        bottomOfSection = self._drawTextLines(dc, lines, x, y)
        if icon:
            self._drawIconSeparator(dc, x - 2, topOfSection, bottomOfSection)
        return bottomOfSection

    def _drawSectionSeparator(self, dc, x, y):
        y += 1
        width = self.GetClientSize()[0]
        dc.DrawLine(x, y, width - x, y)
        return y + 2

    def _drawIcon(self, dc, icon, x, y):
        bitmap = wx.ArtProvider.GetBitmap(icon, wx.ART_FRAME_ICON, (16, 16))
        dc.DrawBitmap(bitmap, x, y, True)
        return 23  # New x

    def _drawTextLines(self, dc, textLines, x, y):
        for textLine in textLines:
            y = self._drawTextLine(dc, textLine, x, y)
        return y

    def _drawTextLine(self, dc, textLine, x, y):
        try:
            dc.DrawText(textLine, x, y)
        except Exception:
            raise RuntimeError("Could not draw text %s" % repr(textLine))
        textHeight = dc.GetTextExtent(textLine)[1]
        return y + textHeight + 1

    def _drawIconSeparator(self, dc, x, top, bottom):
        """Draw a vertical line between the icon and the text."""
        dc.DrawLine(x, top, x, bottom)
