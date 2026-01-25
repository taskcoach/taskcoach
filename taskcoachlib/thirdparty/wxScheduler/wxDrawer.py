#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .wxSchedulerConstants import *
from .wxScheduleUtils import copyDateTime
from .wxTimeFormat import wxTimeFormat

import wx, math


class wxDrawer(object):
    """
    This class handles the actual painting of headers and schedules.
    """

    # Set this to True if you want your methods to be passed a
    # wx.GraphicsContext instead of wx.DC.
    use_gc = False

    def __init__(self, context, displayedHours):
        self.context = context
        self.displayedHours = displayedHours

    def AdjustFontForHeight(self, font, height):
        pointSize = 18
        while True:
            font.SetPointSize(pointSize)
            _, th = self.context.GetTextExtent(
                " " + wxTimeFormat.FormatTime(wx.DateTime.FromHMS(23, 59, 59))
            )
            if th <= height:
                return
            pointSize -= 1
            if pointSize == 1:
                return  # Hum

    def AdjustFontForWidth(self, font, width):
        pointSize = 18
        while True:
            font.SetPointSize(pointSize)
            self.context.SetFont(font)
            tw, _ = self.context.GetTextExtent(
                " " + wxTimeFormat.FormatTime(wx.DateTime.FromHMS(23, 59, 59))
            )
            if tw <= width:
                return
            pointSize -= 1
            if pointSize == 1:
                return  # Hum

    def DrawDayHeader(self, day, x, y, w, h, highlight=None):
        """
        Draws the header for a day. Returns the header's size.
        """
        raise NotImplementedError

    def DrawDayBackground(self, x, y, w, h, highlight=None):
        """
        Draws the background for a day.
        """
        raise NotImplementedError

    def DrawMonthHeader(self, day, x, y, w, h):
        """
        Draws the header for a month. Returns the header's size.
        """
        raise NotImplementedError

    def DrawSimpleDayHeader(self, day, x, y, w, h, highlight=None):
        """
        Draws the header for a day, in compact form. Returns
        the header's size.
        """
        raise NotImplementedError

    def DrawHours(self, x, y, w, h, direction, includeText=True):
        """
        Draws hours of the day on the left of the specified
        rectangle. Returns the days column size.
        """
        raise NotImplementedError

    def DrawSchedulesCompact(
        self, day, schedules, x, y, width, height, highlightColor,
        otherMonthColor=None,
    ):
        """
        Draws a set of schedules in compact form (vertical
        month). Returns a list of (schedule, point, point).
        """
        raise NotImplementedError

    def DrawNowHorizontal(self, x, y, w):
        """
        Draws a horizontal line showing when is now
        """
        raise NotImplementedError

    def DrawNowVertical(self, x, y, h):
        """
        Draws a vertical line showing when is now
        """
        raise NotImplementedError

    def _DrawSchedule(self, schedule, x, y, w, h):
        """
        Draws a schedule in the specified rectangle.
        """
        # Ensure coordinates are integers for wxPython compatibility
        x, y, w = int(x), int(y), int(w)
        if h is not None:
            h = int(h)

        offsetY = SCHEDULE_INSIDE_MARGIN
        offsetX = SCHEDULE_INSIDE_MARGIN

        if self.use_gc:
            if h is not None:
                pen = wx.Pen(schedule.color)
                self.context.SetPen(self.context.CreatePen(pen))

                brush = self.context.CreateLinearGradientBrush(
                    x,
                    y,
                    x + w,
                    y + h,
                    schedule.color,
                    SCHEDULER_BACKGROUND_BRUSH(),
                )
                self.context.SetBrush(brush)
                self.context.DrawRoundedRectangle(
                    x, y, w, h, SCHEDULE_INSIDE_MARGIN
                )

            if schedule.complete is not None:
                if h is not None:
                    self.context.SetPen(
                        self.context.CreatePen(
                            wx.Pen(
                                wx.SystemSettings.GetColour(
                                    wx.SYS_COLOUR_SCROLLBAR
                                )
                            )
                        )
                    )
                    self.context.SetBrush(
                        self.context.CreateBrush(
                            wx.Brush(
                                wx.SystemSettings.GetColour(
                                    wx.SYS_COLOUR_SCROLLBAR
                                )
                            )
                        )
                    )
                    self.context.DrawRoundedRectangle(
                        x + SCHEDULE_INSIDE_MARGIN,
                        y + offsetY,
                        w - 2 * SCHEDULE_INSIDE_MARGIN,
                        2 * SCHEDULE_INSIDE_MARGIN,
                        SCHEDULE_INSIDE_MARGIN,
                    )

                    if schedule.complete:
                        self.context.SetBrush(
                            self.context.CreateLinearGradientBrush(
                                x + SCHEDULE_INSIDE_MARGIN,
                                y + offsetY,
                                x
                                + (w - 2 * SCHEDULE_INSIDE_MARGIN)
                                * schedule.complete,
                                y + offsetY + 10,
                                wx.Colour(0, 0, 255),
                                wx.Colour(0, 255, 255),
                            )
                        )
                        self.context.DrawRoundedRectangle(
                            x + SCHEDULE_INSIDE_MARGIN,
                            y + offsetY,
                            (w - 2 * SCHEDULE_INSIDE_MARGIN)
                            * schedule.complete,
                            10,
                            5,
                        )

                offsetY += 10 + SCHEDULE_INSIDE_MARGIN

            if schedule.icons:
                for icon in schedule.icons:
                    if h is not None:
                        bitmap = wx.ArtProvider.GetBitmap(
                            icon, wx.ART_FRAME_ICON, (16, 16)
                        )
                        self.context.DrawBitmap(
                            bitmap, x + offsetX, y + offsetY, 16, 16
                        )
                    offsetX += 20
                    if offsetX > w - SCHEDULE_INSIDE_MARGIN:
                        offsetY += 20
                        offsetX = SCHEDULE_INSIDE_MARGIN
                        break

            font = schedule.font
            self.context.SetFont(font, schedule.foreground)
            offsetY += self._drawTextInRect(
                self.context,
                schedule.description,
                offsetX,
                x,
                y + offsetY,
                w - 2 * SCHEDULE_INSIDE_MARGIN,
                None if h is None else h - offsetY - SCHEDULE_INSIDE_MARGIN,
            )
        else:
            if h is not None:
                self.context.SetBrush(wx.Brush(schedule.color))
                self.context.DrawRectangle(x, y, w, h)

            if schedule.complete is not None:
                if h is not None:
                    self.context.SetPen(
                        wx.Pen(
                            wx.SystemSettings.GetColour(
                                wx.SYS_COLOUR_SCROLLBAR
                            )
                        )
                    )
                    self.context.SetBrush(
                        wx.Brush(
                            wx.SystemSettings.GetColour(
                                wx.SYS_COLOUR_SCROLLBAR
                            )
                        )
                    )
                    self.context.DrawRectangle(
                        x + SCHEDULE_INSIDE_MARGIN,
                        y + offsetY,
                        w - 2 * SCHEDULE_INSIDE_MARGIN,
                        10,
                    )
                    if schedule.complete:
                        self.context.SetPen(
                            wx.Pen(
                                wx.SystemSettings.GetColour(
                                    wx.SYS_COLOUR_HIGHLIGHT
                                )
                            )
                        )
                        self.context.SetBrush(
                            wx.Brush(
                                wx.SystemSettings.GetColour(
                                    wx.SYS_COLOUR_HIGHLIGHT
                                )
                            )
                        )
                        self.context.DrawRectangle(
                            x + SCHEDULE_INSIDE_MARGIN,
                            y + offsetY,
                            int(
                                (w - 2 * SCHEDULE_INSIDE_MARGIN)
                                * schedule.complete
                            ),
                            10,
                        )

                offsetY += 10 + SCHEDULE_INSIDE_MARGIN

            if schedule.icons:
                for icon in schedule.icons:
                    if h is not None:
                        bitmap = wx.ArtProvider.GetBitmap(
                            icon, wx.ART_FRAME_ICON, (16, 16)
                        )
                        self.context.DrawBitmap(
                            bitmap, x + offsetX, y + offsetY, True
                        )
                    offsetX += 20
                    if offsetX > w - SCHEDULE_INSIDE_MARGIN:
                        offsetY += 20
                        offsetX = SCHEDULE_INSIDE_MARGIN
                        break

            font = schedule.font
            self.context.SetFont(font)

            self.context.SetTextForeground(schedule.foreground)
            offsetY += self._drawTextInRect(
                self.context,
                schedule.description,
                offsetX,
                x,
                y + offsetY,
                w - 2 * SCHEDULE_INSIDE_MARGIN,
                None if h is None else h - offsetY - SCHEDULE_INSIDE_MARGIN,
            )

        if h is not None:
            schedule.clientdata.bounds = (x, y, w, h)

        return offsetY

    def DrawScheduleVertical(
        self, schedule, day, workingHours, x, y, width, height
    ):
        """Draws a schedule vertically."""

        size, position, total = self.ScheduleSize(
            schedule, workingHours, day, 1
        )

        if self.use_gc:
            font = schedule.font
            self.context.SetFont(font, schedule.color)
        else:
            font = schedule.font
            self.context.SetTextForeground(schedule.foreground)
            self.context.SetFont(font)

        y = y + position * height // total + SCHEDULE_OUTSIDE_MARGIN
        x += SCHEDULE_OUTSIDE_MARGIN
        height = height * size // total - 2 * SCHEDULE_OUTSIDE_MARGIN
        width -= 2 * SCHEDULE_OUTSIDE_MARGIN

        self._DrawSchedule(schedule, x, y, width, height)
        return (
            x - SCHEDULE_OUTSIDE_MARGIN,
            y - SCHEDULE_OUTSIDE_MARGIN,
            width + 2 * SCHEDULE_OUTSIDE_MARGIN,
            height + 2 * SCHEDULE_OUTSIDE_MARGIN,
        )

    def DrawScheduleHorizontal(
        self, schedule, day, daysCount, workingHours, x, y, width, height
    ):
        """Draws a schedule horizontally."""

        size, position, total = self.ScheduleSize(
            schedule, workingHours, day, daysCount
        )

        if self.use_gc:
            font = schedule.font
            self.context.SetFont(font, schedule.color)
        else:
            font = schedule.font
            self.context.SetTextForeground(schedule.color)
            self.context.SetFont(font)

        x = x + position * width // total + SCHEDULE_OUTSIDE_MARGIN
        width = width * size // total - 2 * SCHEDULE_OUTSIDE_MARGIN

        # Height is variable
        height = self._DrawSchedule(schedule, x, y, width, None)
        self._DrawSchedule(schedule, x, y, width, height)

        return (
            x - SCHEDULE_OUTSIDE_MARGIN,
            y - SCHEDULE_OUTSIDE_MARGIN,
            width + 2 * SCHEDULE_OUTSIDE_MARGIN,
            height + 2 * SCHEDULE_OUTSIDE_MARGIN,
        )

    def ScheduleSize(schedule, workingHours, firstDay, dayCount):
        """
        This convenience  static method computes  the position
        and size  size of the  schedule in the  direction that
        represent time,  according to a set  of working hours.
        The workingHours  parameter is  a list of  2-tuples of
        wx.DateTime  objects   defining  intervals  which  are
        indeed worked.  startPeriod and endPeriod  delimit the
        period.
        """

        totalSpan = 0
        scheduleSpan = 0
        position = 0

        totalTime = 0
        for startHour, endHour in workingHours:
            totalTime += (
                copyDateTime(endHour).Subtract(startHour).GetMinutes() / 60.0
            )

        for dayNumber in range(dayCount):
            currentDay = copyDateTime(firstDay)
            currentDay.Add(wx.DateSpan(days=dayNumber))

            for startHour, endHour in workingHours:
                startHourCopy = wx.DateTime.FromDMY(
                    currentDay.GetDay(),
                    currentDay.GetMonth(),
                    currentDay.GetYear(),
                    startHour.GetHour(),
                    startHour.GetMinute(),
                    0,
                )
                endHourCopy = wx.DateTime.FromDMY(
                    currentDay.GetDay(),
                    currentDay.GetMonth(),
                    currentDay.GetYear(),
                    endHour.GetHour(),
                    endHour.GetMinute(),
                    0,
                )

                totalSpan += endHourCopy.Subtract(startHourCopy).GetMinutes()

                localStart = copyDateTime(schedule.start)

                if localStart.IsLaterThan(endHourCopy):
                    position += endHourCopy.Subtract(
                        startHourCopy
                    ).GetMinutes()
                    continue

                if startHourCopy.IsLaterThan(localStart):
                    localStart = startHourCopy

                localEnd = copyDateTime(schedule.end)

                if startHourCopy.IsLaterThan(localEnd):
                    continue

                position += localStart.Subtract(startHourCopy).GetMinutes()

                if localEnd.IsLaterThan(endHourCopy):
                    localEnd = endHourCopy

                scheduleSpan += localEnd.Subtract(localStart).GetMinutes()

        return (
            dayCount * totalTime * scheduleSpan / totalSpan,
            dayCount * totalTime * position / totalSpan,
            totalTime * dayCount,
        )

    ScheduleSize = staticmethod(ScheduleSize)

    def _drawTextInRect(self, context, text, offsetX, x, y, w, h):
        words = text.split()
        tw, th = context.GetTextExtent(" ".join(words))

        if h is not None and th > h + SCHEDULE_INSIDE_MARGIN:
            return SCHEDULE_INSIDE_MARGIN

        if tw <= w - offsetX:
            context.DrawText(" ".join(words), x + offsetX, y)
            return th + SCHEDULE_INSIDE_MARGIN

        dpyWords = []
        remaining = w - offsetX
        totalW = 0
        spaceW, _ = context.GetTextExtent(" ")

        for idx, word in enumerate(words):
            tw, _ = context.GetTextExtent(word)
            if remaining - tw - spaceW <= 0:
                break
            totalW += tw
            remaining -= tw + spaceW
            dpyWords.append(word)

        if dpyWords:
            words = words[idx:]

            currentX = offsetX
            if len(dpyWords) > 1:
                if words:
                    spacing = ((w - offsetX) - totalW) / (len(dpyWords) - 1)
                else:
                    spacing = spaceW
            else:
                spacing = 0.0

            for word in dpyWords:
                tw, _ = context.GetTextExtent(word)
                context.DrawText(word, int(x + currentX), y)
                currentX += spacing + tw
        else:
            if offsetX == SCHEDULE_INSIDE_MARGIN:
                # Can't display anything...
                return SCHEDULE_INSIDE_MARGIN

        if words:
            ny = y + SCHEDULE_INSIDE_MARGIN + th
            if h is not None and ny > y + h:
                return SCHEDULE_INSIDE_MARGIN
            th += self._drawTextInRect(
                context,
                " ".join(words),
                SCHEDULE_INSIDE_MARGIN,
                x,
                ny,
                w,
                None if h is None else h - (ny - y),
            )

        return th + SCHEDULE_INSIDE_MARGIN

    def _shrinkText(self, dc, text, width, height):
        """
        Truncate text at desired width
        """
        MORE_SIGNAL = "..."
        SEPARATOR = " "

        textlist = list()  # List returned by this method
        words = list()  # Wordlist for itermediate elaboration

        # Split text in single words and split words when yours width is over
        # available width
        text = text.replace("\n", " ").split()

        for word in text:
            if dc.GetTextExtent(word)[0] > width:
                # Cycle trought every char until word width is minor or equal
                # to available width
                partial = ""

                for char in word:
                    if dc.GetTextExtent(partial + char)[0] > width:
                        words.append(partial)
                        partial = char
                    else:
                        partial += char
            else:
                words.append(word)

        # Create list of text lines for output
        textline = list()

        for word in words:
            if dc.GetTextExtent(SEPARATOR.join(textline + [word]))[0] > width:
                textlist.append(SEPARATOR.join(textline))
                textline = [word]

                # Break if there's no vertical space available
                if (len(textlist) * dc.GetTextExtent(SEPARATOR)[0]) > height:
                    # Must exists almost one line of description
                    if len(textlist) > 1:
                        textlist = textlist[:-1]

                    break
            else:
                textline.append(word)

        # Add remained words to text list
        if len(textline) > 0:
            textlist.append(SEPARATOR.join(textline))

        return textlist


class BackgroundDrawerDCMixin(object):
    """
    Mixin to draw day background with a DC.
    """

    def DrawDayBackground(self, x, y, w, h, highlight=None):
        if highlight is not None:
            self.context.SetBrush(wx.Brush(highlight))
        else:
            self.context.SetBrush(wx.TRANSPARENT_BRUSH)

        self.context.SetPen(FOREGROUND_PEN)

        self.context.DrawRectangle(int(x), int(y) - 1, int(w), int(h) + 1)


class HeaderDrawerDCMixin(object):
    """
    A mixin to draw headers with a regular DC.
    """

    def _DrawHeader(
        self,
        text,
        x,
        y,
        w,
        h,
        pointSize=12,
        weight=wx.FONTWEIGHT_BOLD,
        alignRight=False,
        highlight=None,
    ):
        font = self.context.GetFont()
        font.SetPointSize(pointSize)
        font.SetWeight(weight)
        self.context.SetFont(font)

        textW, textH = self.context.GetTextExtent(text)

        if highlight is not None:
            self.context.SetBrush(wx.Brush(highlight))
        else:
            self.context.SetBrush(wx.Brush(SCHEDULER_BACKGROUND_BRUSH()))

        self.context.DrawRectangle(int(x), int(y), int(w), int(textH * 1.5))

        self.context.SetTextForeground(wx.BLACK)

        if alignRight:
            self.context.DrawText(
                text, int(x + w - textW * 1.5), int(y + textH * 0.25)
            )
        else:
            self.context.DrawText(
                text, int(x + (w - textW) // 2), int(y + textH * 0.25)
            )

        return w, int(textH * 1.5)

    def DrawSchedulesCompact(
        self, day, schedules, x, y, width, height, highlightColor,
        otherMonthColor=None,
    ):
        if day is None:
            if otherMonthColor is not None:
                self.context.SetBrush(wx.Brush(otherMonthColor))
            else:
                self.context.SetBrush(wx.LIGHT_GREY_BRUSH)
        else:
            self.context.SetBrush(wx.Brush(DAY_BACKGROUND_BRUSH()))

        self.context.DrawRectangle(int(x), int(y), int(width), int(height))

        results = []

        if day is not None:
            if day.IsSameDate(wx.DateTime.Now()):
                color = highlightColor
            else:
                color = None
            headerW, headerH = self.DrawSimpleDayHeader(
                day, x, y, width, height, highlight=color
            )
            y += headerH
            height -= headerH

            x += SCHEDULE_OUTSIDE_MARGIN
            width -= 2 * SCHEDULE_OUTSIDE_MARGIN

            y += SCHEDULE_OUTSIDE_MARGIN
            height -= 2 * SCHEDULE_OUTSIDE_MARGIN

            self.context.SetPen(FOREGROUND_PEN)

            totalHeight = 0

            for schedule in schedules:
                if schedule.start.Format("%H%M") != "0000":
                    description = "%s %s" % (
                        wxTimeFormat.FormatTime(
                            schedule.start, includeMinutes=True
                        ),
                        schedule.description,
                    )
                else:
                    description = schedule.description
                description = self._shrinkText(
                    self.context,
                    description,
                    width - 2 * SCHEDULE_INSIDE_MARGIN,
                    headerH,
                )[0]

                textW, textH = self.context.GetTextExtent(description)
                if totalHeight + textH > height:
                    break

                self.context.SetBrush(wx.Brush(schedule.color))
                self.context.DrawRectangle(int(x), int(y), int(width), int(textH * 1.2))
                results.append(
                    (
                        schedule,
                        wx.Point(int(x), int(y)),
                        wx.Point(int(x + width), int(y + textH * 1.2)),
                    )
                )

                self.context.SetTextForeground(schedule.foreground)
                self.context.DrawText(
                    description, x + SCHEDULE_INSIDE_MARGIN, y + textH * 0.1
                )

                y += textH * 1.2
                totalHeight += textH * 1.2

        return results


class BackgroundDrawerGCMixin(object):
    """
    Mixin to draw day background with a GC.
    """

    def DrawDayBackground(self, x, y, w, h, highlight=None):
        if highlight is not None:
            self.context.SetBrush(
                self.context.CreateLinearGradientBrush(
                    x,
                    y,
                    x + w,
                    y + h,
                    wx.Colour(128, 128, 128, 128),
                    wx.Colour(
                        highlight.Red(),
                        highlight.Green(),
                        highlight.Blue(),
                        128,
                    ),
                )
            )
        else:
            self.context.SetBrush(
                self.context.CreateBrush(wx.TRANSPARENT_BRUSH)
            )

        self.context.SetPen(self.context.CreatePen(FOREGROUND_PEN))

        self.context.DrawRectangle(int(x), int(y) - 1, int(w), int(h) + 1)


class HeaderDrawerGCMixin(object):
    """
    A mixin to draw headers with a GraphicsContext.
    """

    def _DrawHeader(
        self,
        text,
        x,
        y,
        w,
        h,
        pointSize=12,
        weight=wx.FONTWEIGHT_BOLD,
        alignRight=False,
        highlight=None,
    ):
        font = wx.NORMAL_FONT
        fsize = font.GetPointSize()
        fweight = font.GetWeight()

        try:
            font.SetPointSize(pointSize)
            font.SetWeight(weight)
            self.context.SetFont(font, wx.BLACK)

            textW, textH = self.context.GetTextExtent(text)

            x1 = x
            y1 = y
            x2 = x + w
            y2 = y + textH * 1.5

            if highlight is not None:
                self.context.SetBrush(
                    self.context.CreateLinearGradientBrush(
                        x1, y1, x2, y2, wx.Colour(128, 128, 128), highlight
                    )
                )
            else:
                self.context.SetBrush(
                    self.context.CreateLinearGradientBrush(
                        x1,
                        y1,
                        x2,
                        y2,
                        wx.Colour(128, 128, 128),
                        SCHEDULER_BACKGROUND_BRUSH(),
                    )
                )
            self.context.DrawRectangle(int(x1), int(y1), int(x2 - x1), int(y2 - y1))

            if alignRight:
                self.context.DrawText(
                    text, int(x + w - 1.5 * textW), int(y + textH * 0.25)
                )
            else:
                self.context.DrawText(
                    text, x + (w - textW) // 2, int(y + textH * 0.25)
                )

            return w, textH * 1.5
        finally:
            font.SetPointSize(fsize)
            font.SetWeight(fweight)

    def DrawSchedulesCompact(
        self, day, schedules, x, y, width, height, highlightColor,
        otherMonthColor=None,
    ):
        if day is None:
            gradientEnd = otherMonthColor if otherMonthColor is not None else SCHEDULER_BACKGROUND_BRUSH()
            brush = self.context.CreateLinearGradientBrush(
                x,
                y,
                x + width,
                y + height,
                wx.BLACK,
                gradientEnd,
            )
        else:
            brush = self.context.CreateLinearGradientBrush(
                x,
                y,
                x + width,
                y + height,
                wx.LIGHT_GREY,
                DAY_BACKGROUND_BRUSH(),
            )

        self.context.SetBrush(brush)
        self.context.DrawRectangle(int(x), int(y), int(width), int(height))

        font = wx.NORMAL_FONT
        fsize = font.GetPointSize()
        fweight = font.GetWeight()

        try:
            font.SetPointSize(10)
            font.SetWeight(wx.FONTWEIGHT_NORMAL)

            results = []

            if day is not None:
                if day.IsSameDate(wx.DateTime.Now()):
                    color = highlightColor
                else:
                    color = None
                headerW, headerH = self.DrawSimpleDayHeader(
                    day, x, y, width, height, highlight=color
                )
                y += headerH
                height -= headerH

                x += SCHEDULE_OUTSIDE_MARGIN
                width -= 2 * SCHEDULE_OUTSIDE_MARGIN

                y += SCHEDULE_OUTSIDE_MARGIN
                height -= 2 * SCHEDULE_OUTSIDE_MARGIN

                self.context.SetPen(FOREGROUND_PEN)

                totalHeight = 0

                for schedule in schedules:
                    if schedule.start.Format("%H%M") != "0000":
                        description = "%s %s" % (
                            wxTimeFormat.FormatTime(
                                schedule.start, includeMinutes=True
                            ),
                            schedule.description,
                        )
                    else:
                        description = schedule.description
                    description = self._shrinkText(
                        self.context,
                        description,
                        width - 2 * SCHEDULE_INSIDE_MARGIN,
                        headerH,
                    )[0]

                    textW, textH = self.context.GetTextExtent(description)
                    if totalHeight + textH > height:
                        break

                    brush = self.context.CreateLinearGradientBrush(
                        x,
                        y,
                        x + width,
                        y + height,
                        schedule.color,
                        DAY_BACKGROUND_BRUSH(),
                    )
                    self.context.SetBrush(brush)
                    self.context.DrawRoundedRectangle(
                        x, y, width, int(textH * 1.2), int(textH / 2)
                    )
                    results.append(
                        (
                            schedule,
                            wx.Point(int(x), int(y)),
                            wx.Point(int(x + width), int(y + textH * 1.2)),
                        )
                    )

                    self.context.SetFont(schedule.font, schedule.foreground)
                    self.context.DrawText(
                        description,
                        x + SCHEDULE_INSIDE_MARGIN,
                        y + textH * 0.1,
                    )

                    y += textH * 1.2
                    totalHeight += textH * 1.2

            return results
        finally:
            font.SetPointSize(fsize)
            font.SetWeight(fweight)


class HeaderDrawerMixin(object):
    """
    A mixin that draws header using the _DrawHeader method.
    """

    def DrawDayHeader(self, day, x, y, width, height, highlight=None):
        return self._DrawHeader(
            "%s %s %s"
            % (
                day.GetWeekDayName(day.GetWeekDay())[:3],
                day.GetDay(),
                day.GetMonthName(day.GetMonth()),
            ),
            x,
            y,
            width,
            height,
            highlight=highlight,
        )

    def DrawMonthHeader(self, day, x, y, w, h):
        return self._DrawHeader(
            "%s %s" % (day.GetMonthName(day.GetMonth()), day.GetYear()),
            x,
            y,
            w,
            h,
        )

    def DrawSimpleDayHeader(self, day, x, y, w, h, highlight=None):
        return self._DrawHeader(
            day.Format("%a %d"),
            x,
            y,
            w,
            h,
            weight=wx.FONTWEIGHT_NORMAL,
            alignRight=True,
            highlight=highlight,
        )


class wxBaseDrawer(
    BackgroundDrawerDCMixin, HeaderDrawerDCMixin, HeaderDrawerMixin, wxDrawer
):
    """
    Concrete subclass of wxDrawer; regular style.
    """

    def DrawHours(self, x, y, w, h, direction, includeText=True):
        if direction == wxSCHEDULER_VERTICAL:
            self.context.SetBrush(wx.Brush(SCHEDULER_BACKGROUND_BRUSH()))
            self.context.DrawRectangle(int(x), int(y), int(LEFT_COLUMN_SIZE), int(h))

        font = self.context.GetFont()
        fWeight = font.GetWeight()
        fSize = font.GetPointSize()
        try:
            font.SetWeight(wx.FONTWEIGHT_NORMAL)
            self.context.SetFont(font)
            self.context.SetTextForeground(wx.BLACK)

            if direction == wxSCHEDULER_VERTICAL:
                hourH = int(h / len(self.displayedHours))
                self.AdjustFontForHeight(font, hourH)
                hourW, _ = self.context.GetTextExtent(
                    " "
                    + wxTimeFormat.FormatTime(wx.DateTime.FromHMS(23, 59, 59))
                )
            else:
                hourW = int(w / len(self.displayedHours))
                self.AdjustFontForWidth(font, int(hourW * 2 * 0.9))
                _, hourH = self.context.GetTextExtent(
                    " "
                    + wxTimeFormat.FormatTime(wx.DateTime.FromHMS(23, 59, 59))
                )

            if not includeText:
                hourH = 0

            for i, hour in enumerate(self.displayedHours):
                if hour.GetMinute() == 0:
                    if direction == wxSCHEDULER_VERTICAL:
                        self.context.DrawLine(
                            x + LEFT_COLUMN_SIZE - hourW // 2,
                            y + i * hourH,
                            x + w,
                            y + i * hourH,
                        )
                        if includeText:
                            self.context.DrawText(
                                wxTimeFormat.FormatTime(hour),
                                x + LEFT_COLUMN_SIZE - hourW - 5,
                                y + i * hourH,
                            )
                    else:
                        self.context.DrawLine(
                            x + i * hourW,
                            int(y + hourH * 1.25),
                            x + i * hourW,
                            y + h,
                        )
                        if includeText:
                            self.context.DrawText(
                                wxTimeFormat.FormatTime(hour),
                                x + i * hourW + 5,
                                int(y + hourH * 0.25),
                            )
                else:
                    if direction == wxSCHEDULER_VERTICAL:
                        self.context.DrawLine(
                            x + LEFT_COLUMN_SIZE,
                            y + i * hourH,
                            x + w,
                            y + i * hourH,
                        )
                    else:
                        self.context.DrawLine(
                            x + i * hourW,
                            int(y + hourH * 1.4),
                            x + i * hourW,
                            y + h,
                        )

            if direction == wxSCHEDULER_VERTICAL:
                self.context.DrawLine(
                    x + LEFT_COLUMN_SIZE - 1,
                    y,
                    x + LEFT_COLUMN_SIZE - 1,
                    y + h,
                )
                return LEFT_COLUMN_SIZE, max(h, DAY_SIZE_MIN.height)
            else:
                self.context.DrawLine(
                    x,
                    int(y + hourH * 1.5 - 1),
                    x + w,
                    int(y + hourH * 1.5 - 1),
                )
                return max(w, DAY_SIZE_MIN.width), int(hourH * 1.5)
        finally:
            font.SetWeight(fWeight)
            font.SetPointSize(fSize)

    def DrawNowHorizontal(self, x, y, w):
        self.context.SetBrush(wx.Brush(wx.Colour(0, 128, 0)))
        self.context.SetPen(wx.Pen(wx.Colour(0, 128, 0)))
        self.context.DrawArc(x, y + 5, x, y - 5, x, y)
        self.context.DrawRectangle(int(x), int(y) - 1, int(w), 3)

    def DrawNowVertical(self, x, y, h):
        self.context.SetBrush(wx.Brush(wx.Colour(0, 128, 0)))
        self.context.SetPen(wx.Pen(wx.Colour(0, 128, 0)))
        self.context.DrawArc(x - 5, y, x + 5, y, x, y)
        self.context.DrawRectangle(int(x) - 1, int(y), 3, int(h))


class wxFancyDrawer(
    BackgroundDrawerGCMixin, HeaderDrawerGCMixin, HeaderDrawerMixin, wxDrawer
):
    """
    Concrete subclass of wxDrawer; fancy eye-candy using wx.GraphicsContext.
    """

    use_gc = True

    def DrawHours(self, x, y, w, h, direction, includeText=True):
        if direction == wxSCHEDULER_VERTICAL:
            brush = self.context.CreateLinearGradientBrush(
                x,
                y,
                x + w,
                y + h,
                SCHEDULER_BACKGROUND_BRUSH(),
                DAY_BACKGROUND_BRUSH(),
            )
            self.context.SetBrush(brush)
            self.context.DrawRectangle(int(x), int(y), int(LEFT_COLUMN_SIZE), int(h))

        font = wx.NORMAL_FONT
        fsize = font.GetPointSize()
        fweight = font.GetWeight()

        try:
            font.SetWeight(wx.FONTWEIGHT_NORMAL)
            self.context.SetFont(font, wx.BLACK)

            self.context.SetPen(FOREGROUND_PEN)

            if direction == wxSCHEDULER_VERTICAL:
                hourH = int(h / len(self.displayedHours))
                self.AdjustFontForHeight(font, hourH)
                hourW, _ = self.context.GetTextExtent(
                    " "
                    + wxTimeFormat.FormatTime(wx.DateTime.FromHMS(23, 59, 59))
                )
            else:
                hourW = int(w / len(self.displayedHours))
                self.AdjustFontForWidth(font, int(hourW * 2 * 0.9))
                _, hourH = self.context.GetTextExtent(
                    " "
                    + wxTimeFormat.FormatTime(wx.DateTime.FromHMS(23, 59, 59))
                )

            if not includeText:
                hourH = 0

            for i, hour in enumerate(self.displayedHours):
                if hour.GetMinute() == 0:
                    if direction == wxSCHEDULER_VERTICAL:
                        self.context.DrawLines(
                            [
                                (
                                    x + LEFT_COLUMN_SIZE - hourW // 2,
                                    y + i * hourH,
                                ),
                                (x + w, y + i * hourH),
                            ]
                        )
                        if includeText:
                            self.context.DrawText(
                                " " + wxTimeFormat.FormatTime(hour),
                                x + LEFT_COLUMN_SIZE - hourW - 10,
                                y + i * hourH,
                            )
                    else:
                        self.context.DrawLines(
                            [
                                (x + i * hourW, y + hourH * 1.25),
                                (x + i * hourW, y + h + 10),
                            ]
                        )
                        if includeText:
                            self.context.DrawText(
                                wxTimeFormat.FormatTime(hour),
                                x + i * hourW + 5,
                                y + hourH * 0.25,
                            )
                else:
                    if direction == wxSCHEDULER_VERTICAL:
                        self.context.DrawLines(
                            [
                                (x + LEFT_COLUMN_SIZE, y + i * hourH),
                                (x + w, y + i * hourH),
                            ]
                        )
                    else:
                        self.context.DrawLines(
                            [
                                (x + i * hourW, y + hourH * 1.4),
                                (x + i * hourW, y + h),
                            ]
                        )

            if direction == wxSCHEDULER_VERTICAL:
                self.context.DrawLines(
                    [
                        (x + LEFT_COLUMN_SIZE - 1, y),
                        (x + LEFT_COLUMN_SIZE - 1, y + h),
                    ]
                )
                return LEFT_COLUMN_SIZE, max(h, DAY_SIZE_MIN.height)
            else:
                self.context.DrawLines(
                    [(x, y + hourH * 1.5 - 1), (x + w, y + hourH * 1.5 - 1)]
                )
                return max(w, DAY_SIZE_MIN.width), hourH * 1.5
        finally:
            font.SetPointSize(fsize)
            font.SetWeight(fweight)

    def DrawNowHorizontal(self, x, y, w):
        brush = self.context.CreateLinearGradientBrush(
            x + 4,
            y - 1,
            x + w,
            y + 1,
            wx.Colour(0, 128, 0, 128),
            wx.Colour(0, 255, 0, 128),
        )
        self.context.SetBrush(brush)
        self.context.DrawRectangle(int(x) + 4, int(y) - 2, int(w) - 4, 3)

        brush = self.context.CreateRadialGradientBrush(
            x,
            y - 5,
            x,
            y,
            5,
            wx.Colour(0, 128, 0, 128),
            wx.Colour(0, 255, 0, 128),
        )
        self.context.SetBrush(brush)

        path = self.context.CreatePath()
        path.AddArc(x, y, 5, int(-math.pi / 2), int(math.pi / 2), True)
        self.context.FillPath(path)

    def DrawNowVertical(self, x, y, h):
        brush = self.context.CreateLinearGradientBrush(
            x - 1,
            y + 4,
            x + 1,
            y + h,
            wx.Colour(0, 128, 0, 128),
            wx.Colour(0, 255, 0, 128),
        )
        self.context.SetBrush(brush)
        self.context.DrawRectangle(int(x) - 2, int(y) + 4, 3, int(h) - 4)

        brush = self.context.CreateRadialGradientBrush(
            x - 5,
            y,
            x,
            y,
            5,
            wx.Colour(0, 128, 0, 128),
            wx.Colour(0, 255, 0, 128),
        )
        self.context.SetBrush(brush)

        path = self.context.CreatePath()
        path.AddArc(x, y, 5, 0.0, math.pi, True)
        self.context.FillPath(path)
