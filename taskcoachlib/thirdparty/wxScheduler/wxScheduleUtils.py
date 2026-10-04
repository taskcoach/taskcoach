#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx


def copyDate(value):
    """Simple method for copy the date (Y,M,D)."""
    return wx.DateTime.FromDMY(
        value.GetDay(), value.GetMonth(), value.GetYear()
    )


def copyDateTime(value):
    """Return a copy of input wxDateTime object"""
    if value.IsValid():
        return wx.DateTime.FromDMY(
            value.GetDay(),
            value.GetMonth(),
            value.GetYear(),
            value.GetHour(),
            value.GetMinute(),
            value.GetSecond(),
            value.GetMillisecond(),
        )
    else:
        return wx.DateTime()


def setToWeekDayInSameWeek(day, offset, startDay=1):
    """wxDateTime's    SetToWeekDayInSameWeek   appears    to   be
    buggish. When told that the  week starts on Monday, it results
    in   the  following   'week'  on   Jan,  31st,   2010:  31/01,
    25/01-30/01..."""
    # Loop backwards until we find the start day
    while True:
        if day.GetWeekDay() == startDay:
            break
        day.Subtract(wx.DateSpan(days=1))
    day.Add(wx.DateSpan(days=offset))
    return day
