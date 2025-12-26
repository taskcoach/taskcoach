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

import taskcoachlib.i18n
from taskcoachlib.thirdparty import smartdatetimectrl as sdtc
from taskcoachlib.domain import date
from taskcoachlib import render, operating_system

import wx, datetime


class _SmartDateTimeCtrl(sdtc.SmartDateTimeCtrl):
    def __init__(self, *args, **kwargs):
        self.__interval = (
            kwargs.get("startHour", 8),
            kwargs.get("endHour", 18),
        )
        super().__init__(*args, **kwargs)

    def __shiftDown(self, event):
        if operating_system.isGTK():
            return ord("A") <= event.GetKeyCode() <= ord("Z")
        return event.ShiftDown()

    def HandleKey(self, event):
        if not super().HandleKey(event) and self.GetDateTime() is not None:
            startHour, endHour = self.__interval
            if event.GetKeyCode() in [ord("s"), ord("S")]:
                hour = (
                    datetime.time(startHour, 0, 0, 0)
                    if self.__shiftDown(event)
                    else datetime.time(0, 0, 0, 0)
                )
                self.SetDateTime(
                    datetime.datetime.combine(self.GetDateTime().date(), hour),
                    notify=True,
                )
                return True
            elif event.GetKeyCode() in [ord("e"), ord("E")]:
                hour = (
                    datetime.time(endHour, 0, 0, 0)
                    if self.__shiftDown(event)
                    else datetime.time(23, 59, 0, 0)
                )
                self.SetDateTime(
                    datetime.datetime.combine(self.GetDateTime().date(), hour),
                    notify=True,
                )
                return True
        return False


class DateTimeCtrl(wx.Panel):
    def __init__(
        self,
        parent,
        callback=None,
        noneAllowed=True,
        starthour=8,
        endhour=18,
        interval=15,
        showSeconds=False,
        showRelative=False,
        adjustEndOfDay=False,
        units=None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)

        self.__adjust = adjustEndOfDay
        self.__callback = callback
        self.__ctrl = _SmartDateTimeCtrl(
            self,
            enableNone=noneAllowed,
            dateFormat=render.date,
            timeFormat=lambda x: render.time(x, seconds=showSeconds),
            startHour=starthour,
            endHour=endhour,
            minuteDelta=interval,
            secondDelta=interval,
            showRelative=showRelative,
            units=units,
        )
        self.__ctrl.EnableChoices()

        # When the widget fires its event, its value has not changed yet (because it can be vetoed).
        # We need to store the new value so that GetValue() returns the right thing when called from event processing.
        self.__value = self.__ctrl.GetDateTime()

        sizer = wx.BoxSizer()
        sizer.Add(self.__ctrl, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.__ctrl.Bind(sdtc.EVT_DATETIME_CHANGE, self.__OnChange)

    def __OnChange(self, event):
        self.__value = event.GetValue()
        if self.__callback is not None:
            self.__callback()

    def EnableChoices(self, enabled=True):
        self.__ctrl.EnableChoices(enabled=enabled)

    def SetRelativeChoicesStart(self, start=None):
        self.__ctrl.SetRelativeChoicesStart(start=start)

    def HideRelativeButton(self):
        self.__ctrl.HideRelativeButton()

    def LoadChoices(self, choices):
        self.__ctrl.LoadChoices(choices)

    def GetValue(self):
        if (
            self.__value is not None
            and self.__value.time() == date.Time(23, 59, 0, 0)
            and self.__adjust
        ):
            return date.DateTime.fromDateTime(
                date.DateTime.combine(
                    self.__value.date(), date.Time(23, 59, 59, 999999)
                )
            )
        return (
            date.DateTime()
            if self.__value is None
            else date.DateTime.fromDateTime(self.__value)
        )

    def SetValue(self, dateTime):
        if dateTime == date.DateTime():
            dateTime = None
        self.__ctrl.SetDateTime(dateTime)
        self.__value = self.__ctrl.GetDateTime()

    def SetNone(self):
        self.__value = None
        self.__ctrl.SetDateTime(None)

    def setCallback(self, callback):
        self.__callback = callback

    def Cleanup(self):
        self.__ctrl.Cleanup()


class TimeEntry(wx.Panel):
    def __init__(
        self,
        parent,
        value,
        defaultValue=0,
        disabledValue=None,
        disabledMessage=None,
    ):
        super().__init__(parent)

        self.__disabledValue = disabledValue

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.__entry = sdtc.TimeEntry(
            self,
            format=lambda x: render.time(x, minutes=False),
            hour=defaultValue,
            minute=0,
            second=0,
        )
        self.__entry.EnableChoices()
        sizer.Add(self.__entry, 0, wx.ALL, 3)

        if disabledMessage is not None:
            self.__checkbox = wx.CheckBox(self, wx.ID_ANY, disabledMessage)
            self.Bind(wx.EVT_CHECKBOX, self.OnCheck)
            if value == disabledValue:
                self.__entry.SetTime(
                    date.Time(hour=defaultValue, minute=0, second=0)
                )
                self.__checkbox.SetValue(True)
                self.__entry.Enable(False)
            else:
                self.__entry.SetTime(date.Time(hour=value, minute=0, second=0))
            sizer.Add(self.__checkbox, 1, wx.ALL, 3)
        else:
            self.__entry.SetTime(date.Time(hour=value, minute=0, second=0))
            self.__checkbox = None
        self.SetSizer(sizer)

    def OnCheck(self, event):
        self.__entry.Enable(not event.IsChecked())

    def GetValue(self):
        if self.__checkbox is not None and self.__checkbox.GetValue():
            return self.__disabledValue
        return self.__entry.GetTime().hour
