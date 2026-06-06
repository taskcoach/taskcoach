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

from .wxevents import (
    CalendarCanvas,
    CalendarPrintout,
    EVT_EVENT_SELECTION_CHANGED,
    EVT_EVENT_DATES_CHANGED,
)
from taskcoachlib.domain import date
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
from taskcoachlib.widgets import draganddrop
from taskcoachlib import command, render
from . import tooltip
import wx, datetime


class HierarchicalCalendar(tooltip.ToolTipMixin, CalendarCanvas):
    # Header formats (bitmask)
    HDR_WEEKNUMBER = 1
    HDR_DATE = 2

    # Calendar formats
    CAL_WEEKLY = 0
    CAL_WORKWEEKLY = 1
    CAL_MONTHLY = 2

    def __init__(
        self, parent, tasks, onSelect, onEdit, onCreate, popupMenu, **kwargs
    ):
        self.__onDropURLCallback = kwargs.pop("onDropURL", None)
        self.__onDropFilesCallback = kwargs.pop("onDropFiles", None)
        self.__onDropMailCallback = kwargs.pop("onDropMail", None)
        self.__taskList = tasks
        self.__onSelect = onSelect
        self.__onEdit = onEdit
        self.__onCreate = onCreate
        self.__popupMenu = popupMenu
        self.__calFormat = self.CAL_WEEKLY
        self.__hdrFormat = self.HDR_DATE
        self.__drawNow = True
        self.__adapter = parent
        self.getItemTooltipData = parent.getItemTooltipData
        super().__init__(parent, **kwargs)
        self.SetCalendarFormat(
            self.__calFormat
        )  # This calls _Invalidate() so no need to call SetHeaderFormat

        self.__tip = tooltip.SimpleToolTip(self)
        self.__dropTarget = draganddrop.DropTarget(
            self.OnDropURL, self.OnDropFiles, self.OnDropMail
        )
        self.SetDropTarget(self.__dropTarget)

        self.Bind(EVT_EVENT_SELECTION_CHANGED, self._OnSelectionChanged)
        self.Bind(EVT_EVENT_DATES_CHANGED, self._OnDatesChanged)
        self.Bind(wx.EVT_LEFT_DCLICK, self._OnLeftDClick)
        self.Bind(wx.EVT_RIGHT_UP, self._OnRightUp)

    def _OnSelectionChanged(self, event):
        self.__onSelect()

    def _OnDatesChanged(self, event):
        if event.start is None or event.end is None:
            return
        task = event.event
        start = date.DateTime.fromDateTime(event.start)
        end = date.DateTime.fromDateTime(event.end)

        if task.plannedStartDateTime() != start:
            command.EditPlannedStartDateTimeCommand(
                items=[task], newValue=start
            ).do()
        if task.dueDateTime() != end:
            command.EditDueDateTimeCommand(items=[task], newValue=end).do()

    def _OnLeftDClick(self, event):
        hit = self.HitTest(event.GetX(), event.GetY())
        if hit.event is None:
            self.__onCreate(date.DateTime.fromDateTime(hit.dateTime))
        else:
            self.__onEdit(hit.event)

    def _OnRightUp(self, event):
        self.PopupMenu(self.__popupMenu)

    def OnBeforeShowToolTip(self, x, y):
        hit = self.HitTest(x, y)
        if hit is None or hit.event is None:
            return None

        tooltipData = self.getItemTooltipData(hit.event)
        doShow = any(data[1] for data in tooltipData)
        if doShow:
            self.__tip.SetData(tooltipData)
            return self.__tip
        else:
            return None

    def GetMainWindow(self):
        return self

    def GetItemCount(self):
        return len(self._coords)

    def RefreshAllItems(self, count):
        self._Invalidate()
        self.Refresh()

    def RefreshItems(self, *items):
        self.Refresh()

    @property
    def has_selection(self):
        return bool(self.Selection())

    @property
    def has_single_selection(self):
        return len(list(self.Selection())) == 1

    def curselection(self):
        return list(self.Selection())

    def clear_selection(self):
        self.Select([])

    def select(self, items):
        self.Select(items)

    def select_all(self):
        items = list()
        for task in self.__taskList:
            items.append(task)
            items.extend(task.children(recursive=True))
        self.select(items)

    # Configuration

    def SetCalendarFormat(self, fmt):
        self.__calFormat = fmt
        if self.__calFormat == self.CAL_WORKWEEKLY:
            self._start = date.Now().startOfWorkWeek()
            self._end = date.Now().endOfWorkWeek()
        elif self.__calFormat == self.CAL_WEEKLY:
            self._start = date.Now().startOfWeek()
            self._end = date.Now().endOfWeek()
        elif self.__calFormat == self.CAL_MONTHLY:
            self._start = date.Now().startOfMonth()
            self._end = date.Now().endOfMonth()
        self._Invalidate()
        self.Refresh()

    def CalendarFormat(self):
        return self.__calFormat

    def SetHeaderFormat(self, fmt):
        self.__hdrFormat = fmt
        self._Invalidate()
        self.Refresh()

    def HeaderFormat(self):
        return self.__hdrFormat

    def SetDrawNow(self, drawNow):
        self.__drawNow = drawNow
        self.Refresh()

    def DrawNow(self):
        return self.__drawNow

    def SetTodayColor(self, xxx_todo_changeme):
        (r, g, b) = xxx_todo_changeme
        super().SetTodayColor(wx.Colour(r, g, b))

    def TodayColor(self):
        color = super().TodayColor()
        return color.Red(), color.Green(), color.Blue()

    # Navigation

    def Next(self):
        start, end = self.ViewSpan()
        if self.__calFormat in [self.CAL_WEEKLY, self.CAL_WORKWEEKLY]:
            ts = datetime.timedelta(days=7)
            start += ts
            end += ts
        elif self.__calFormat == self.CAL_MONTHLY:
            start = date.DateTime.fromDateTime(
                start.endOfMonth()
            ).startOfDay() + date.TimeDelta(days=1)
            end = start.endOfMonth()
        self.SetViewSpan(start, end)

    def Prev(self):
        start, end = self.ViewSpan()
        if self.__calFormat in [self.CAL_WEEKLY, self.CAL_WORKWEEKLY]:
            ts = datetime.timedelta(days=7)
            start -= ts
            end -= ts
        elif self.__calFormat == self.CAL_MONTHLY:
            start = (
                date.DateTime.fromDateTime(start) - date.TimeDelta(days=1)
            ).startOfMonth()
            end = start.endOfMonth()
        self.SetViewSpan(start, end)

    def Today(self):
        now = date.Now()
        if self.__calFormat == self.CAL_WEEKLY:
            start = now.startOfWeek()
            end = now.endOfWeek()
        elif self.__calFormat == self.CAL_WORKWEEKLY:
            start = now.startOfWorkWeek()
            end = now.endOfWorkWeek()
        else:
            start = now.startOfMonth()
            end = now.endOfMonth()
        self.SetViewSpan(start, end)

    # Overriden

    def FormatDateTime(self, dateTime):
        dateTime = date.DateTime.fromDateTime(dateTime)
        components = []
        if self.__hdrFormat & self.HDR_WEEKNUMBER:
            components.append(render.weekNumber(dateTime))
        if self.__hdrFormat & self.HDR_DATE:
            components.append(render.date(dateTime, human_readable=True))
        return " - ".join(components)

    def _DrawNow(self, gc, h):
        if self.__drawNow:
            super()._DrawNow(gc, h)

    def GetRootEvents(self):
        return self.__adapter.getRootItems()

    def GetChildren(self, task):
        return self.__adapter.children(task)

    def GetStart(self, task):
        dt = task.plannedStartDateTime()
        return None if dt == date.DateTime() else dt

    def GetEnd(self, task):
        dt = task.dueDateTime()
        return None if dt == date.DateTime() else dt

    def GetText(self, task):
        return self.__adapter.getItemText(task)

    def GetBackgroundColor(self, task):
        color = task.backgroundColor(True)
        return wx.Colour(*color) if color else wx.WHITE

    def GetForegroundColor(self, task):
        color = task.foregroundColor(True)
        return wx.Colour(*color) if color else wx.BLACK

    def GetProgress(self, task):
        p = task.percentageComplete(recursive=True)
        if p:
            return p / 100
        return None

    def GetIcons(self, task):
        icon_ids = [task.icon_id(recursive=True)]
        if task.attachments():
            icon_ids.append("nuvola_status_mail-attachment")
        if task.notes():
            icon_ids.append("nuvola_apps_knotes")
        return [
            icon_catalog.get_wx_icon(icon_id, LIST_ICON_SIZE)
            for icon_id in icon_ids
        ]

    def GetFont(self, task):
        return task.font(recursive=True) or wx.NORMAL_FONT

    def OnDropURL(self, x, y, url):
        self.__Drop(x, y, url, self.__onDropURLCallback)

    def OnDropFiles(self, x, y, filenames):
        self.__Drop(x, y, filenames, self.__onDropFilesCallback)

    def OnDropMail(self, x, y, mail):
        self.__Drop(x, y, filenames, self.__onDropMailCallback)

    def __Drop(self, x, y, objects, callback):
        if callback is not None:
            hit = self.HitTest(x, y)
            if hit.event is not None:
                callback(hit.event, objects)
            else:
                callback(
                    None,
                    objects,
                    plannedStartDateTime=date.DateTime.fromDateTime(
                        hit.dateTime
                    ).startOfDay(),
                    dueDateTime=date.DateTime.fromDateTime(
                        hit.dateTime
                    ).endOfDay(),
                )

    def GetPrintout(self, settings):
        return CalendarPrintout(self, settings, _("Tasks"))
