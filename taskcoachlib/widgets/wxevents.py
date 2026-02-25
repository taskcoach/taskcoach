"""
Task Coach - Your friendly task manager
Copyright (C) 2014 Task Coach developers <developers@taskcoach.org>

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
import datetime
import math


wxEVT_EVENT_SELECTION_CHANGED = wx.NewEventType()
EVT_EVENT_SELECTION_CHANGED = wx.PyEventBinder(wxEVT_EVENT_SELECTION_CHANGED)

wxEVT_EVENT_DATES_CHANGED = wx.NewEventType()
EVT_EVENT_DATES_CHANGED = wx.PyEventBinder(wxEVT_EVENT_DATES_CHANGED)


class _HitResult(object):
    HIT_START = 0
    HIT_IN = 1
    HIT_END = 2

    def __init__(self, x, y, event, dateTime):
        self.x, self.y = x, y
        self.event = event
        self.dateTime = dateTime
        self.position = self.HIT_IN


class _Watermark(object):
    def __init__(self):
        self.__values = []

    def height(self, start, end):
        r = 0
        for ints, inte, h in self.__values:
            if not (end < ints or start >= inte):
                r = max(r, h)
        return r

    def total_height(self):
        return (
            max([h for ints, inte, h in self.__values]) if self.__values else 0
        )

    def add(self, start, end, h):
        self.__values.append((start, end, h))


def total_seconds(td):  # Method new in 2.7
    return (
        td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6
    ) / 10**6


def shorten_text(gc, text, maxW):
    shortText = text
    idx = len(text) // 2
    while True:
        w, h = gc.GetTextExtent(shortText)
        if w <= maxW:
            return shortText
        idx -= 1
        if idx == 0:
            return "\u2026"
        shortText = text[:idx] + "\u2026" + text[-idx:]


class CalendarCanvas(wx.Panel):
    _gradVal = 0.2

    MS_IDLE = 0
    MS_HOVER_LEFT = 1
    MS_HOVER_RIGHT = 2
    MS_DRAG_LEFT = 3
    MS_DRAG_RIGHT = 4
    MS_DRAG_START = 5
    MS_DRAGGING = 6

    def __init__(self, parent, start=None, end=None):
        self._start = start or datetime.datetime.combine(
            datetime.datetime.now().date(), datetime.time(0, 0, 0)
        )
        self._end = end or self._start + datetime.timedelta(days=7)
        super().__init__(parent, wx.ID_ANY, style=wx.FULL_REPAINT_ON_RESIZE)

        self._coords = (
            dict()
        )  # Event => (startIdx, endIdx, startIdxRecursive, endIdxRecursive, yMin, yMax)
        self._maxIndex = 0
        self._minSize = (0, 0)

        # Drawing attributes
        self._precision = 1  # Minutes
        self._gridSize = 15  # Minutes
        self._eventHeight = 32
        self._eventWidthMin = 0.1
        self._eventWidth = 0.1
        self._margin = 5
        self._marginTop = 22
        self._outlineColorDark = wx.Colour(180, 180, 180)
        self._outlineColorLight = wx.Colour(210, 210, 210)
        self._headerSpans = []
        self._daySpans = []
        self._selection = set()
        self._mouseState = self.MS_IDLE
        self._mouseOrigin = None
        self._mouseDragPos = None
        self._todayColor = wx.Colour(0, 0, 128)

        self._hScroll = wx.ScrollBar(self, wx.ID_ANY, style=wx.SB_HORIZONTAL)
        self._vScroll = wx.ScrollBar(self, wx.ID_ANY, style=wx.SB_VERTICAL)

        self._hScroll.Hide()
        self._vScroll.Hide()

        self._hScroll.Bind(wx.EVT_SCROLL, self._on_scroll)
        self._vScroll.Bind(wx.EVT_SCROLL, self._on_scroll)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_SIZE, self._on_resize)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_left_up)
        self.Bind(wx.EVT_RIGHT_DOWN, self._on_right_down)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self._invalidate()

    # Methods to override

    def IsWorked(self, date):
        return not date.isoweekday() in [6, 7]

    def FormatDateTime(self, dateTime):
        return dateTime.strftime("%A")

    def GetRootEvents(self):
        return list()

    def GetStart(self, event):
        raise NotImplementedError

    def GetEnd(self, event):
        raise NotImplementedError

    def GetText(self, event):
        raise NotImplementedError

    def GetChildren(self, event):
        raise NotImplementedError

    def GetBackgroundColor(self, event):
        raise NotImplementedError

    def GetForegroundColor(self, event):
        raise NotImplementedError

    def GetProgress(self, event):
        raise NotImplementedError

    def GetIcons(self, event):
        raise NotImplementedError

    def GetFont(self, event):
        raise NotImplementedError

    # Get/Set

    def GetPrecision(self):
        return self._precision

    def SetPrecision(self, precision):
        self._precision = precision
        self._invalidate()
        self.Refresh()

    def GetEventHeight(self):
        return self._eventHeight

    def SetEventHeight(self, height):
        self._eventHeight = height
        self._invalidate()
        self.Refresh()

    def GetEventWidth(self):
        return self._eventWidthMin

    def SetEventWidth(self, width):
        self._eventWidthMin = width
        self._invalidate()
        self.Refresh()

    def GetMargin(self):
        return self._margin

    def SetMargin(self, margin):
        self._margin = margin
        self._invalidate()
        self.Refresh()

    def OutlineColorDark(self):
        return self._outlineColorDark

    def SetOutlineColorDark(self, color):
        self._outlineColorDark = color
        self.Refresh()

    def OutlineColorLight(self):
        return self._outlineColorLight

    def SetOutlineColorLight(self, color):
        self._outlineColorLight = color
        self.Refresh()

    def TodayColor(self):
        return self._todayColor

    def SetTodayColor(self, color):
        self._todayColor = color
        self.Refresh()

    def ViewSpan(self):
        return (self._start, self._end)

    def SetViewSpan(self, start, end):
        self._start = start
        self._end = end
        self._invalidate()
        self.Refresh()

    def Selection(self):
        return self._selection

    def Select(self, events):
        self._selection = set(events) & set(self._coords.keys())
        e = wx.PyCommandEvent(wxEVT_EVENT_SELECTION_CHANGED)
        e.selection = set(self._selection)
        e.SetEventObject(self)
        self.ProcessEvent(e)
        self.Refresh()

    def HitTest(self, x, y):
        w, h = self.GetClientSize()

        if y <= self._marginTop:
            return None
        if self._hScroll.IsShown():
            h -= self._hScroll.GetClientSize()[1]
            if y >= h:
                return None
        if self._vScroll.IsShown():
            w -= self._vScroll.GetClientSize()[0]
            if x >= w:
                return None

        if self._hScroll.IsShown():
            x += self._hScroll.GetThumbPosition()
        if self._vScroll.IsShown():
            y += self._vScroll.GetThumbPosition()

        xIndex = int(x / self._eventWidth)
        yIndex = int(
            (y - self._marginTop) / (self._eventHeight + self._margin)
        )
        dateTime = self._start + datetime.timedelta(
            minutes=self._precision * xIndex
        )

        for event, (
            startIndex,
            endIndex,
            startIndexRecursive,
            endIndexRecursive,
            yMin,
            yMax,
        ) in list(self._coords.items()):
            if (
                xIndex >= startIndexRecursive
                and xIndex < endIndexRecursive
                and yIndex >= yMin
                and yIndex < yMax
            ):
                # May be a child
                children = []
                self._flatten(event, children)
                for candidate in reversed(children):
                    if candidate in self._coords:
                        si, ei, sir, eir, ymin, ymax = self._coords[candidate]
                        if (
                            si is not None
                            and abs(x - si * self._eventWidth) <= self._margin
                            and yIndex >= ymin
                            and yIndex < ymax
                        ):
                            result = _HitResult(x, y, candidate, dateTime)
                            result.position = result.HIT_START
                            return result
                        if (
                            ei is not None
                            and abs(x - ei * self._eventWidth) <= self._margin
                            and yIndex >= ymin
                            and yIndex < ymax
                        ):
                            result = _HitResult(x, y, candidate, dateTime)
                            result.position = result.HIT_END
                            return result
                        if (
                            xIndex >= sir
                            and xIndex < eir
                            and yIndex >= ymin
                            and yIndex < ymax
                        ):
                            result = _HitResult(x, y, candidate, dateTime)
                            result.position = result.HIT_IN
                            return result
                # Since the list contains at least 'event'...
                assert 0

        # We didn't hit any event.
        result = _HitResult(x, y, None, dateTime)
        return result

    def _flatten(self, event, result):
        result.append(event)
        for child in self.GetChildren(event):
            self._flatten(child, result)

    def _draw_event(self, gc, event):
        if event in self._coords:
            (
                startIndex,
                endIndex,
                startIndexRecursive,
                endIndexRecursive,
                yMin,
                yMax,
            ) = self._coords[event]
            if self.GetChildren(event):
                self._draw_parent(
                    gc,
                    startIndex,
                    endIndex,
                    startIndexRecursive,
                    endIndexRecursive,
                    yMin,
                    yMax,
                    event,
                    self._eventWidth,
                )
            else:
                self._draw_leaf(
                    gc,
                    startIndex,
                    endIndex,
                    yMin,
                    yMax,
                    event,
                    self._eventWidth,
                )
        for child in self.GetChildren(event):
            self._draw_event(gc, child)

    def _on_paint(self, event):
        w, h = self.GetClientSize()
        vw = max(w, self._minSize[0])
        vh = max(h, self._minSize[1])
        dx = dy = 0
        if self._hScroll.IsShown():
            vh -= self._hScroll.GetClientSize()[1]
            dx = self._hScroll.GetThumbPosition()
        if self._vScroll.IsShown():
            vw -= self._vScroll.GetClientSize()[0]
            dy = self._vScroll.GetThumbPosition()

        bmp = wx.Bitmap(vw, vh)
        memDC = wx.MemoryDC()
        memDC.SelectObject(bmp)
        try:
            memDC.SetBackground(wx.WHITE_BRUSH)
            memDC.Clear()
            gc = wx.GraphicsContext.Create(memDC)
            self._draw(gc, vw, vh, dx, dy)
            dc = wx.PaintDC(self)
            dc.Blit(0, 0, vw, vh, memDC, 0, 0)
        finally:
            memDC.SelectObject(wx.NullBitmap)

    def _draw(self, gc, vw, vh, dx, dy):
        gc.PushState()
        try:
            gc.Translate(-dx, 0.0)
            self._draw_header(gc, vw, vh)
        finally:
            gc.PopState()

        gc.PushState()
        try:
            gc.Translate(-dx, -dy)
            gc.Clip(0, self._marginTop + dy, vw, vh)
            for event in self.GetRootEvents():
                self._draw_event(gc, event)
            self._draw_now(gc, vh + dy)
            self._draw_drag_image(gc)
        finally:
            gc.PopState()

    def _draw_header(self, gc, w, h):
        gc.SetPen(wx.Pen(self._outlineColorDark))
        for startIndex, endIndex in self._daySpans:
            date = (
                self._start
                + datetime.timedelta(minutes=self._precision * startIndex)
            ).date()
            x0 = startIndex * self._eventWidth
            x1 = endIndex * self._eventWidth
            if date == datetime.datetime.now().date():
                gc.SetBrush(
                    self._gradient(
                        gc, self._todayColor, x0, self._marginTop, x1 - x0, h
                    )
                )
            elif self.IsWorked(date):
                gc.SetBrush(wx.WHITE_BRUSH)
            else:
                gc.SetBrush(
                    self._gradient(
                        gc,
                        self._outlineColorDark,
                        x0,
                        self._marginTop,
                        x1 - x0,
                        h,
                    )
                )
            gc.DrawRectangle(x0, self._marginTop, x1 - x0, h)

        gc.SetFont(wx.NORMAL_FONT, wx.BLACK)
        gc.SetPen(wx.Pen(self._outlineColorDark))
        for startIndex, endIndex in self._headerSpans:
            x0 = startIndex * self._eventWidth
            x1 = endIndex * self._eventWidth
            gc.SetBrush(
                self._gradient(
                    gc,
                    self._outlineColorLight,
                    x0,
                    0,
                    x1 - x0,
                    self._marginTop - 2,
                )
            )
            gc.DrawRectangle(x0, 0, x1 - x0, self._marginTop - 2)
            text = shorten_text(
                gc,
                self.FormatDateTime(
                    self._start
                    + datetime.timedelta(minutes=self._precision * startIndex)
                ),
                x1 - x0,
            )
            tw, th = gc.GetTextExtent(text)
            gc.DrawText(
                text, x0 + (x1 - x0 - tw) // 2, (self._marginTop - 2 - th) // 2
            )

    def _draw_now(self, gc, h):
        now = datetime.datetime.now()
        x = int(
            (now - self._start).total_seconds()
            / 60.0
            / self._precision
            * self._eventWidth
            - 0.5
        )

        gc.SetPen(wx.Pen(wx.Colour(0, 128, 0)))
        gc.SetBrush(wx.Brush(wx.Colour(0, 128, 0)))

        path = gc.CreatePath()
        path.MoveToPoint(x - 4, self._marginTop)
        path.AddLineToPoint(x + 4, self._marginTop)
        path.AddLineToPoint(x, self._marginTop + 4)
        path.AddLineToPoint(x, h + self._marginTop)
        path.AddLineToPoint(x, self._marginTop + 4)
        path.CloseSubpath()
        gc.DrawPath(path)

    def _draw_drag_image(self, gc):
        if self._mouseDragPos is not None:
            if self._mouseState in [self.MS_DRAG_LEFT, self.MS_DRAG_RIGHT]:
                d1 = self._mouseDragPos
                d2 = (
                    self.GetEnd(self._mouseOrigin.event)
                    if self._mouseState == self.MS_DRAG_LEFT
                    else self.GetStart(self._mouseOrigin.event)
                )
                d1, d2 = min(d1, d2), max(d1, d2)

                x0 = (
                    int(total_seconds(d1 - self._start) / 60 / self._precision)
                    * self._eventWidth
                )
                x1 = (
                    int(total_seconds(d2 - self._start) / 60 / self._precision)
                    * self._eventWidth
                )
                y0 = (
                    self._coords[self._mouseOrigin.event][4]
                    * (self._eventHeight + self._margin)
                    + self._marginTop
                )
                y1 = (
                    self._coords[self._mouseOrigin.event][5]
                    * (self._eventHeight + self._margin)
                    + self._marginTop
                    - self._margin
                )

                gc.SetBrush(wx.Brush(wx.Colour(0, 0, 128, 128)))
                gc.DrawRoundedRectangle(x0, y0, x1 - x0, y1 - y0, 5.0)

                gc.SetFont(wx.NORMAL_FONT, wx.RED)
                text = self._mouseDragPos.strftime("%c")
                tw, th = gc.GetTextExtent(text)
                if self._mouseState == self.MS_DRAG_LEFT:
                    tx = x0 + self._margin
                elif self._mouseState == self.MS_DRAG_RIGHT:
                    tx = x1 - self._margin - tw
                ty = y0 + (y1 - y0 - th) / 2
                gc.DrawText(text, tx, ty)
            elif self._mouseState == self.MS_DRAGGING:
                x0 = (
                    int(
                        total_seconds(self._mouseDragPos - self._start)
                        / 60
                        / self._precision
                    )
                    * self._eventWidth
                )
                x1 = (
                    int(
                        total_seconds(
                            self._mouseDragPos
                            + (
                                self.GetEnd(self._mouseOrigin.event)
                                - self.GetStart(self._mouseOrigin.event)
                            )
                            - self._start
                        )
                        / 60
                        / self._precision
                    )
                    * self._eventWidth
                )
                y0 = (
                    self._coords[self._mouseOrigin.event][4]
                    * (self._eventHeight + self._margin)
                    + self._marginTop
                )
                y1 = (
                    self._coords[self._mouseOrigin.event][5]
                    * (self._eventHeight + self._margin)
                    + self._marginTop
                    - self._margin
                )

                gc.SetBrush(wx.Brush(wx.Colour(0, 0, 128, 128)))
                gc.DrawRoundedRectangle(x0, y0, x1 - x0, y1 - y0, 5.0)

                gc.SetFont(wx.NORMAL_FONT, wx.RED)
                text = "%s -> %s" % (
                    self._mouseDragPos.strftime("%c"),
                    (
                        self._mouseDragPos
                        + (
                            self.GetEnd(self._mouseOrigin.event)
                            - self.GetStart(self._mouseOrigin.event)
                        )
                    ).strftime("%c"),
                )
                tw, th = gc.GetTextExtent(text)
                gc.DrawText(
                    text, x0 + (x1 - x0 - tw) / 2, y0 + (y1 - y0 - th) / 2
                )

    def _get_cursor_date(self):
        x, y = self.ScreenToClientXY(*wx.GetMousePosition())
        if self._hScroll.IsShown():
            x += self._hScroll.GetThumbPosition()
        return self._start + datetime.timedelta(
            minutes=int(self._precision * x / self._eventWidth)
        )

    def _on_resize(self, event=None):
        if event is None:
            w, h = self.GetClientSize()
        else:
            w, h = event.GetSize()

        _, hh = self._hScroll.GetClientSize()
        vw, _ = self._vScroll.GetClientSize()

        self._hScroll.SetSize(0, h - hh, w - vw, hh)
        self._vScroll.SetSize(
            w - vw, self._marginTop, vw, h - hh - self._marginTop
        )

        minW, minH = self._minSize

        # Not perfect, but it will do.
        if w - vw < minW:
            self._hScroll.SetScrollbar(
                self._hScroll.GetThumbPosition(), w - vw, minW, w - vw, True
            )
            self._hScroll.Show()
            h -= hh
        else:
            self._hScroll.Hide()

        if h - hh - self._marginTop < minH:
            self._vScroll.SetScrollbar(
                self._vScroll.GetThumbPosition(),
                h - hh - self._marginTop,
                minH,
                h - hh - self._marginTop,
                True,
            )
            self._vScroll.Show()
            w -= vw
        else:
            self._vScroll.Hide()

        self._eventWidth = max(
            self._eventWidthMin, max(w, minW) / self._maxIndex
        )

        if event is not None:
            event.Skip()

    def _on_left_down(self, event):
        result = self.HitTest(event.GetX(), event.GetY())
        if result is None:
            return

        if self._mouseState == self.MS_IDLE:
            changed = False
            if result.event is None:
                if self._selection:
                    changed = True
                    self._selection = set()
                    self.Refresh()
            else:
                if event.ShiftDown():
                    events = []
                    self._flatten(result.event, events)
                else:
                    events = [result.event]
                events = set(events) & set(self._coords.keys())

                if event.CmdDown():
                    for e in events:
                        if e in self._selection:
                            self._selection.remove(e)
                            changed = True
                        else:
                            self._selection.add(e)
                            changed = True
                else:
                    if self._selection != events:
                        changed = True
                        self._selection = events

                if result.position == result.HIT_IN:
                    self._mouseOrigin = result
                    self._mouseState = self.MS_DRAG_START
                self.Refresh()

            if changed:
                e = wx.PyCommandEvent(wxEVT_EVENT_SELECTION_CHANGED)
                e.selection = set(self._selection)
                e.SetEventObject(self)
                self.ProcessEvent(e)
        elif self._mouseState in [self.MS_HOVER_LEFT, self.MS_HOVER_RIGHT]:
            self.CaptureMouse()
            self._mouseState += self.MS_DRAG_LEFT - self.MS_HOVER_LEFT

    def _on_left_up(self, event):
        if self._mouseState in [self.MS_DRAG_LEFT, self.MS_DRAG_RIGHT]:
            self.ReleaseMouse()
            wx.SetCursor(wx.NullCursor)

            e = wx.PyCommandEvent(wxEVT_EVENT_DATES_CHANGED)
            e.event = self._mouseOrigin.event
            e.start = (
                self._mouseDragPos
                if self._mouseState == self.MS_DRAG_LEFT
                else self.GetStart(self._mouseOrigin.event)
            )
            e.end = (
                self._mouseDragPos
                if self._mouseState == self.MS_DRAG_RIGHT
                else self.GetEnd(self._mouseOrigin.event)
            )
            e.SetEventObject(self)
            self.ProcessEvent(e)
        elif self._mouseState == self.MS_DRAGGING:
            self.ReleaseMouse()
            wx.SetCursor(wx.NullCursor)

            e = wx.PyCommandEvent(wxEVT_EVENT_DATES_CHANGED)
            e.event = self._mouseOrigin.event
            e.start = self._mouseDragPos
            e.end = e.start + (
                self.GetEnd(self._mouseOrigin.event)
                - self.GetStart(self._mouseOrigin.event)
            )
            e.SetEventObject(self)
            self.ProcessEvent(e)

        self._mouseState = self.MS_IDLE
        self._mouseOrigin = None
        self._mouseDragPos = None
        self.Refresh()

    def _on_right_down(self, event):
        result = self.HitTest(event.GetX(), event.GetY())
        if result is None:
            return

        changed = False
        if result.event is None:
            if self._selection:
                self._selection = set()
                changed = True
                self.Refresh()
        else:
            if result.event not in self._selection:
                self._selection = set([result.event])
                changed = True
                self.Refresh()

        if changed:
            e = wx.PyCommandEvent(wxEVT_EVENT_SELECTION_CHANGED)
            e.selection = set(self._selection)
            e.SetEventObject(self)
            self.ProcessEvent(e)

    def _on_motion(self, event):
        result = self.HitTest(event.GetX(), event.GetY())

        if result is not None:
            if self._mouseState == self.MS_IDLE:
                if result.event is not None and result.position in [
                    result.HIT_START,
                    result.HIT_END,
                ]:
                    self._mouseOrigin = result
                    self._mouseState = (
                        self.MS_HOVER_LEFT
                        if result.position == result.HIT_START
                        else self.MS_HOVER_RIGHT
                    )
                    wx.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))
            elif self._mouseState in [self.MS_HOVER_LEFT, self.MS_HOVER_RIGHT]:
                if result.event is None or result.position not in [
                    result.HIT_START,
                    result.HIT_END,
                ]:
                    self._mouseOrigin = None
                    self._mouseDragPos = None
                    self._mouseState = self.MS_IDLE
                    wx.SetCursor(wx.NullCursor)

        if self._mouseState in [self.MS_DRAG_LEFT, self.MS_DRAG_RIGHT]:
            dateTime = self._get_cursor_date()
            precision = (
                self._gridSize if event.ShiftDown() else self._precision
            )
            if self._mouseState == self.MS_DRAG_LEFT:
                dateTime = self._start + datetime.timedelta(
                    seconds=math.floor(
                        total_seconds(dateTime - self._start) / 60 / precision
                    )
                    * precision
                    * 60
                )
                dateTime = min(
                    self.GetEnd(self._mouseOrigin.event)
                    - datetime.timedelta(minutes=precision),
                    dateTime,
                )
            if self._mouseState == self.MS_DRAG_RIGHT:
                dateTime = self._start + datetime.timedelta(
                    seconds=math.ceil(
                        total_seconds(dateTime - self._start) / 60 / precision
                    )
                    * precision
                    * 60
                )
                dateTime = max(
                    self.GetStart(self._mouseOrigin.event)
                    + datetime.timedelta(minutes=precision),
                    dateTime,
                )
            self._mouseDragPos = dateTime

            self.Refresh()
        elif self._mouseState == self.MS_DRAG_START:
            if (
                self.GetStart(self._mouseOrigin.event) is not None
                and self.GetEnd(self._mouseOrigin.event) is not None
            ):
                dx = abs(event.GetX() - self._mouseOrigin.x)
                dy = abs(event.GetY() - self._mouseOrigin.y)
                if (
                    dx > wx.SystemSettings.GetMetric(wx.SYS_DRAG_X) / 2
                    or dy > wx.SystemSettings.GetMetric(wx.SYS_DRAG_Y) / 2
                ):
                    self.CaptureMouse()
                    wx.SetCursor(wx.Cursor(wx.CURSOR_HAND))
                    self._mouseState = self.MS_DRAGGING
                    self.Refresh()
        elif self._mouseState == self.MS_DRAGGING:
            dx = event.GetX() - self._mouseOrigin.x
            precision = (
                self._gridSize if event.ShiftDown() else self._precision
            )
            delta = datetime.timedelta(
                minutes=math.floor(
                    dx / self._eventWidth * self._precision / precision
                )
                * precision
            )
            self._mouseDragPos = self.GetStart(self._mouseOrigin.event) + delta
            self.Refresh()

    def _on_scroll(self, event):
        self.Refresh()
        event.Skip()

    def _gradient(self, gc, color, x, y, w, h):
        r = color.Red()
        g = color.Green()
        b = color.Blue()
        return gc.CreateLinearGradientBrush(
            x,
            y,
            x + w,
            y + h,
            color,
            wx.Colour(
                int(self._gradVal * r + (1.0 - self._gradVal) * 255),
                int(self._gradVal * g + (1.0 - self._gradVal) * 255),
                int(self._gradVal * b + (1.0 - self._gradVal) * 255),
            ),
        )

    def _draw_parent(
        self,
        gc,
        startIndex,
        endIndex,
        startIndexRecursive,
        endIndexRecursive,
        y,
        yMax,
        event,
        w,
    ):
        x0 = startIndexRecursive * w
        x1 = endIndexRecursive * w - 1.0
        y0 = y * (self._eventHeight + self._margin) + self._marginTop
        y1 = y0 + self._eventHeight
        y2 = (
            yMax * (self._eventHeight + self._margin)
            + self._marginTop
            - self._margin
        )
        color = self.GetBackgroundColor(event)

        # Overall box
        self._draw_box(
            gc,
            event,
            x0 - self._margin / 3,
            y0 - self._margin / 3,
            x1 + self._margin / 3,
            y2 + self._margin / 3,
            wx.Colour(
                int((color.Red() + self._outlineColorLight[0]) / 2),
                int((color.Green() + self._outlineColorLight[1]) / 2),
                int((color.Blue() + self._outlineColorLight[2]) / 2),
            ),
        )

        if startIndex is not None:
            x0 = startIndex * w
        if endIndex is not None:
            x1 = endIndex * w - 1.0

        # Span
        path = gc.CreatePath()
        delta = self._eventHeight / 4
        path.MoveToPoint(x0, y0)
        path.AddLineToPoint(x1, y0)
        path.AddLineToPoint(x1, y1 - delta)
        path.AddLineToPoint(x1 - delta, y1)
        path.AddLineToPoint(x1 - 2 * delta, y1 - delta)
        path.AddLineToPoint(x0 + 2 * delta, y1 - delta)
        path.AddLineToPoint(x0 + delta, y1)
        path.AddLineToPoint(x0, y1 - delta)
        path.CloseSubpath()

        gc.SetBrush(self._gradient(gc, color, x0, y0, x1 - x0, y1 - y0))
        gc.FillPath(path)

        gc.SetPen(wx.Pen(wx.Colour(*self._outlineColorDark)))
        gc.DrawPath(path)

        x0 = max(0.0, x0)
        x1 = min(self._maxIndex * self._eventWidth, x1)

        # Progress
        x0, y0, x1, y1 = self._draw_progress(gc, event, x0, y0, x1, y1)

        y1 -= delta

        # Text & icons
        x0, y0, x1, y1 = self._draw_icons(gc, event, x0, y0, x1, y1)
        self._draw_text(gc, event, x0, y0, x1, y1)

    def _draw_leaf(self, gc, startIndex, endIndex, yMin, yMax, event, w):
        x0 = startIndex * w
        x1 = endIndex * w - 1.0
        y0 = yMin * (self._eventHeight + self._margin) + self._marginTop
        y1 = (
            yMax * (self._eventHeight + self._margin)
            + self._marginTop
            - self._margin
        )

        # Box
        self._draw_box(
            gc, event, x0, y0, x1, y1, self.GetBackgroundColor(event)
        )

        x0 = max(0.0, x0)
        x1 = min(self._maxIndex * self._eventWidth, x1)

        # Progress
        x0, y0, x1, y1 = self._draw_progress(gc, event, x0, y0, x1, y1)

        # Text & icons
        x0, y0, x1, y1 = self._draw_icons(gc, event, x0, y0, x1, y1)
        self._draw_text(gc, event, x0, y0, x1, y1)

    def _draw_box(self, gc, event, x0, y0, x1, y1, color):
        outline = wx.Colour(*self._outlineColorLight)

        if event in self._selection:
            outline = wx.BLUE
            color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)

        path = gc.CreatePath()
        path.AddRoundedRectangle(x0, y0, x1 - x0, y1 - y0, 5.0)
        gc.SetBrush(self._gradient(gc, color, x0, y0, x1, y1))
        gc.FillPath(path)

        gc.SetPen(wx.Pen(outline))
        gc.DrawPath(path)

    def _draw_progress(self, gc, event, x0, y0, x1, y1):
        p = self.GetProgress(event)
        if p is not None:
            px0 = x0 + self._eventHeight / 2
            px1 = x1 - self._eventHeight / 2
            py0 = y0 + (self._eventHeight / 4 - self._eventHeight / 8) / 2
            py1 = py0 + self._eventHeight / 8

            gc.SetBrush(wx.Brush(self._outlineColorDark))
            gc.DrawRectangle(px0, py0, px1 - px0, py1 - py0)

            gc.SetBrush(
                self._gradient(
                    gc, wx.BLUE, px0, py0, px0 + (px1 - px0) * p, py1
                )
            )
            gc.DrawRectangle(px0, py0, (px1 - px0) * p, py1 - py0)

            y0 = py1
        return x0, y0, x1, y1

    def _draw_text(self, gc, event, x0, y0, x1, y1):
        gc.SetFont(
            self.GetFont(event),
            (
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
                if event in self._selection
                else self.GetForegroundColor(event)
            ),
        )
        text = shorten_text(gc, self.GetText(event), x1 - x0 - self._margin * 2)
        w, h = gc.GetTextExtent(text)
        gc.DrawText(
            text,
            x0 + self._margin,
            y0
            + self._eventHeight / 3
            + (y1 - y0 - h - 2 * self._eventHeight / 3) / 2,
        )

    def _draw_icons(self, gc, event, x0, y0, x1, y1):
        cx = x0
        wx_icons = self.GetIcons(event)
        if wx_icons:
            cx += self._margin
            for wx_icon in wx_icons:
                w = wx_icon.GetWidth()
                h = wx_icon.GetHeight()
                gc.DrawIcon(wx_icon, cx, y0 + (y1 - y0 - h) / 2, w, h)
                cx += w + self._margin
        return cx, y0, x1, y1

    def _get_start_recursive(self, event):
        dt = self.GetStart(event)
        ls = [] if dt is None else [dt]
        for child in self.GetChildren(event):
            dt = self._get_start_recursive(child)
            if dt is not None:
                ls.append(dt)
        return min(ls) if ls else None

    def _get_end_recursive(self, event):
        dt = self.GetEnd(event)
        ls = [] if dt is None else [dt]
        for child in self.GetChildren(event):
            dt = self._get_end_recursive(child)
            if dt is not None:
                ls.append(dt)
        return max(ls) if ls else None

    def _invalidate(self):
        self._coords = dict()
        watermark = _Watermark()
        self._maxIndex = int(
            total_seconds(self._end - self._start) / self._precision / 60
        )

        def computeEvent(event):
            eventStart = self.GetStart(event)
            eventEnd = self.GetEnd(event)
            eventRStart = self._get_start_recursive(event)
            eventREnd = self._get_end_recursive(event)

            if (
                eventRStart is not None
                and eventREnd is not None
                and not (eventRStart >= self._end or eventREnd < self._start)
            ):
                rstart = int(
                    math.floor(
                        total_seconds(eventRStart - self._start)
                        / self._precision
                        / 60
                    )
                )
                start = (
                    None
                    if eventStart is None
                    else int(
                        math.floor(
                            total_seconds(eventStart - self._start)
                            / self._precision
                            / 60
                        )
                    )
                )
                rend = int(
                    math.floor(
                        total_seconds(eventREnd - self._start)
                        / self._precision
                        / 60
                    )
                )
                end = (
                    None
                    if eventEnd is None
                    else int(
                        math.floor(
                            total_seconds(eventEnd - self._start)
                            / self._precision
                            / 60
                        )
                    )
                )
                if rend > rstart:
                    y = watermark.height(rstart, rend)
                    watermark.add(rstart, rend, y + 1)
                    yMax = y + 1
                    for child in self.GetChildren(event):
                        child_max = computeEvent(child)
                        if child_max is not None:
                            yMax = max(yMax, child_max)
                    self._coords[event] = (start, end, rstart, rend, y, yMax)
                    return yMax

        for rootEvent in self.GetRootEvents():
            computeEvent(rootEvent)

        bmp = wx.Bitmap(10, 10)  # Don't care
        memDC = wx.MemoryDC()
        memDC.SelectObject(bmp)
        try:
            gc = wx.GraphicsContext.Create(memDC)
            gc.SetFont(wx.NORMAL_FONT, wx.BLACK)

            self._headerSpans = []
            self._daySpans = []
            startIdxHeader = 0
            startIdxDay = 0
            currentFmt = self.FormatDateTime(self._start)
            currentDay = self._start.date()
            headerWidth = gc.GetTextExtent(currentFmt)[0]
            for idx in range(1, self._maxIndex):
                dateTime = self._start + datetime.timedelta(
                    minutes=self._precision * idx
                )
                fmt = self.FormatDateTime(dateTime)
                if fmt != currentFmt:
                    headerWidth += gc.GetTextExtent(fmt)[0]
                    self._headerSpans.append((startIdxHeader, idx))
                    startIdxHeader = idx
                    currentFmt = fmt
                if dateTime.date() != currentDay:
                    self._daySpans.append((startIdxDay, idx))
                    startIdxDay = idx
                    currentDay = dateTime.date()
            self._headerSpans.append((startIdxHeader, self._maxIndex))
            self._daySpans.append((startIdxDay, self._maxIndex))
            headerWidth += self._margin * 2 * len(self._headerSpans)

            self._minSize = (
                int(max(headerWidth, self._eventWidthMin * self._maxIndex)),
                self._marginTop
                + (watermark.total_height() - 1)
                * (self._eventHeight + self._margin),
            )
            self._on_resize()
        finally:
            memDC.SelectObject(wx.NullBitmap)


class CalendarPrintout(wx.Printout):
    def __init__(self, calendar, settings, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._calendar = calendar
        self._settings = settings
        self._count = None

    def _page_count(self):
        if self._count is None:
            minW, minH = self._calendar._minSize
            dc = self.GetDC()
            dcw, dch = dc.GetSize()
            cw = minW
            ch = minW * dch // dcw
            cells = int(
                math.ceil(
                    1.0
                    * (ch - self._calendar._marginTop)
                    / (self._calendar._eventHeight + self._calendar._margin)
                )
            )
            total = (
                int(
                    math.ceil(
                        1.0
                        * (minH - self._calendar._marginTop)
                        / (
                            self._calendar._eventHeight
                            + self._calendar._margin
                        )
                    )
                )
                + 1
            )
            self._count = int(math.ceil(total / cells))
        return self._count

    def GetPageInfo(self):
        return 1, self._page_count(), 1, 1

    def HasPage(self, page):
        return page <= self._page_count()

    def OnPrintPage(self, page):
        # Cannot print with a GraphicsContext...
        minW, minH = self._calendar._minSize
        dc = self.GetDC()
        dcw, dch = dc.GetSize()
        cw = minW
        ch = minW * dch // dcw
        cells = int(
            math.ceil(
                1.0
                * (ch - self._calendar._marginTop)
                / (self._calendar._eventHeight + self._calendar._margin)
            )
        )
        dy = (
            1.0
            * cells
            * (self._calendar._eventHeight + self._calendar._margin)
            * (page - 1)
        )

        bmp = wx.Bitmap(cw, ch)
        memDC = wx.MemoryDC()
        memDC.SelectObject(bmp)
        try:
            memDC.SetBackground(wx.WHITE_BRUSH)
            memDC.Clear()

            oldWidth = self._calendar._eventWidth
            self._calendar._eventWidth = self._calendar._eventWidthMin
            try:
                gc = wx.GraphicsContext.Create(memDC)
                self._calendar._draw(gc, cw, ch, 0, dy)
            finally:
                self._calendar._eventWidth = oldWidth
            dc.SetUserScale(dcw / cw, dch / ch)
            dc.Blit(0, 0, cw, ch, memDC, 0, 0)
        finally:
            memDC.SelectObject(wx.NullBitmap)
