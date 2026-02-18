#!/usr/bin/env python
# -*- coding: utf-8 -*-

import warnings
import wx
import time

from .wxScheduleUtils import copyDateTime

# New event
wxEVT_COMMAND_SCHEDULE_CHANGE = wx.NewEventType()
EVT_SCHEDULE_CHANGE = wx.PyEventBinder(wxEVT_COMMAND_SCHEDULE_CHANGE)


# Constants


class wxSchedule(wx.EvtHandler):

    SCHEDULE_DEFAULT_COLOR = wx.Colour(247, 212, 57)
    SCHEDULE_DEFAULT_FOREGROUND = wx.BLACK

    CATEGORIES = {
        "Work": wx.GREEN,
        "Holiday": wx.GREEN,
        "Phone": wx.GREEN,
        "Email": wx.GREEN,
        "Birthday": wx.GREEN,
        "Ill": wx.GREEN,
        "At home": wx.GREEN,
        "Fax": wx.GREEN,
    }

    def __init__(self):
        """
        Use self.start and self.end for set the star and the end of the schedule.
        If both start and end datetime have time set to 00:00 the schedule is
        relative on entire day/days.
        """
        super().__init__()

        self._color = self.SCHEDULE_DEFAULT_COLOR
        self._font = wx.NORMAL_FONT
        self._foreground = self.SCHEDULE_DEFAULT_FOREGROUND
        self._category = "Work"
        self._description = ""
        self._notes = ""
        self._end = wx.DateTime().Now()
        self._start = wx.DateTime().Now()
        self._done = False
        self._clientdata = None
        self._icon_ids = []
        self._complete = None
        self._id = "%.f-%s" % (time.time(), id(self))

        # Need for freeze the event notification
        self._freeze = False
        self._layoutNeeded = False

    def __getattr__(self, name):
        if name[:3] in ["get", "set"]:
            warnings.warn(
                "getData() is deprecated, use GetData() instead",
                DeprecationWarning,
                stacklevel=2,
            )

            name = name[0].upper() + name[1:]

            return getattr(self, name)

        raise AttributeError(name)

    def __eq__(self, other):
        if isinstance(other, wxSchedule):
            return id(other) == id(self)
        return False

    def __hash__(self):
        return id(self)

    # Global methods
    def Freeze(self):
        # Freeze the event notification
        self._freeze = True
        self._layoutNeeded = False

    def Thaw(self):
        # Wake up the event
        self._freeze = False
        self._eventNotification(self._layoutNeeded)

    def GetData(self):
        """
        Return wxSchedule data into a dict
        """
        attributes = [
            "category",
            "color",
            "font",
            "foreground",
            "description",
            "done",
            "end",
            "notes",
            "start",
            "clientdata",
            "icon_ids",
            "complete",
            "id",
        ]
        data = dict()

        for attribute in attributes:
            data[attribute] = self.__getattribute__(attribute)

        return data

    def Clone(self):
        newSchedule = wxSchedule()
        for name, value in list(self.GetData().items()):
            setattr(newSchedule, name, value)
        # start and end should be copied as well
        newSchedule._start = copyDateTime(newSchedule._start)
        newSchedule._end = copyDateTime(newSchedule._end)
        return newSchedule

    # Internal methods

    def _eventNotification(self, layoutNeeded=False):
        """If not freeze, wake up and call the event notification"""
        if self._freeze:
            self._layoutNeeded = self._layoutNeeded or layoutNeeded
            return

        # Create the event and propagete it
        evt = wx.PyCommandEvent(wxEVT_COMMAND_SCHEDULE_CHANGE)

        evt.category = self._category
        evt.color = self._color
        evt.font = self._font
        evt.foreground = self._foreground
        evt.description = self._description
        evt.done = self._done
        evt.end = self._end
        evt.notes = self._notes
        evt.start = self._start
        evt.icon_ids = self._icon_ids
        evt.complete = self._complete
        evt.schedule = self
        evt.layoutNeeded = layoutNeeded

        evt.SetEventObject(self)

        self.ProcessEvent(evt)

    def __eq__(self, schedule):
        """
        Control if the schedule passed are equal than me
        """
        # Is not a wxSchedule
        if not isinstance(schedule, wxSchedule):
            return False

        # Check wxSchedules attributes
        return self.GetData() == schedule.GetData()

    # Properties
    def SetCategory(self, category):
        """
        Set the color
        """
        if category not in list(self.CATEGORIES.keys()):
            raise ValueError("%s is not a valid category" % category)

        self._category = category
        self._eventNotification()

    def GetCategory(self):
        """
        Return the current category
        """
        return self._category

    def SetColor(self, color):
        """
        Set the color
        """
        if not isinstance(color, wx.Colour):
            raise ValueError("Color can be only a wx.Colour value")

        self._color = color
        self._eventNotification()

    def GetColor(self):
        """
        Return the color
        """
        return self._color

    def SetFont(self, font):
        """
        Set the font
        """

        if font is None:
            self._font = wx.NORMAL_FONT
        else:
            self._font = font

        self._eventNotification()

    def GetFont(self):
        """
        Return the font
        """
        return self._font

    def SetForeground(self, color):
        """
        Sets the text color
        """
        self._foreground = color

    def GetForeground(self):
        """
        Returns the text color
        """
        return self._foreground

    def SetDescription(self, description):
        """
        Set the description
        """
        if not isinstance(description, str):
            raise ValueError("Description can be only a str value")

        self._description = description
        self._eventNotification(True)

    def GetDescription(self):
        """
        Return the description
        """
        return self._description

    def SetDone(self, done):
        """
        Are this schedule complete?
        """
        if not isinstance(done, bool):
            raise ValueError("Done can be only a bool value")

        self._done = done
        self._eventNotification()

    def GetDone(self):
        """
        Return the done value
        """
        return self._done

    def SetEnd(self, dtEnd):
        """
        Set the end
        """
        if not isinstance(dtEnd, wx.DateTime):
            raise ValueError("dateTime can be only a wx.DateTime value")

        self._end = dtEnd
        self._eventNotification(True)

    def GetEnd(self):
        """
        Return the end
        """
        return self._end

    def SetNotes(self, notes):
        """
        Set the notes
        """
        if not isinstance(notes, str):
            raise ValueError("notes can be only a str value")

        self._notes = notes
        self._eventNotification()

    def GetNotes(self):
        """
        Return the notes
        """
        return self._notes

    def SetStart(self, dtStart):
        """Set the start"""
        if not isinstance(dtStart, wx.DateTime):
            raise ValueError("dateTime can be only a wx.DateTime value")

        self._start = dtStart
        self._eventNotification(True)

    def GetStart(self):
        """
        Return the start
        """
        return self._start

    def Offset(self, ts):
        """
        Offsets the schedule by the specified time span.
        """
        self._start.Add(ts)
        self._end.Add(ts)
        self._eventNotification(True)

    def GetIconIds(self):
        return self._icon_ids

    def SetIconIds(self, icon_ids):
        layoutNeeded = (bool(icon_ids) and not bool(self._icon_ids)) or (
            bool(self._icon_ids) and not bool(icon_ids)
        )
        self._icon_ids = icon_ids

        self._eventNotification(layoutNeeded)

    def GetComplete(self):
        return self._complete

    def SetComplete(self, complete):
        layoutNeeded = (self._complete is None and complete is not None) or (
            self._complete is not None and complete is None
        )
        self._complete = complete
        self._eventNotification(layoutNeeded)

    def SetClientData(self, clientdata):
        self._clientdata = clientdata

    def GetClientData(self):
        return self._clientdata

    def SetId(self, id_):
        self._id = id_

    def GetId(self):
        return self._id

    category = property(GetCategory, SetCategory)
    color = property(GetColor, SetColor)
    font = property(GetFont, SetFont)
    foreground = property(GetForeground, SetForeground)
    description = property(GetDescription, SetDescription)
    done = property(GetDone, SetDone)
    start = property(GetStart, SetStart)
    end = property(GetEnd, SetEnd)
    notes = property(GetNotes, SetNotes)
    clientdata = property(GetClientData, SetClientData)
    icon_ids = property(GetIconIds, SetIconIds)
    complete = property(GetComplete, SetComplete)
    id = property(GetId, SetId)
