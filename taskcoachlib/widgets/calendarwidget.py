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
from taskcoachlib.thirdparty.wxScheduler import (
    wxScheduler,
    wxSchedule,
    EVT_SCHEDULE_ACTIVATED,
    EVT_SCHEDULE_RIGHT_CLICK,
    EVT_SCHEDULE_DCLICK,
    EVT_PERIODWIDTH_CHANGED,
    wxReportScheduler,
    wxTimeFormat,
)
from taskcoachlib.thirdparty.wxScheduler.wxSchedulerConstants import (
    wxSCHEDULER_WEEKSTART_MONDAY,
    wxSCHEDULER_WEEKSTART_SUNDAY,
)
from taskcoachlib.domain import date
from taskcoachlib.widgets import draganddrop
from taskcoachlib import command, render
from . import tooltip


class _CalendarContent(tooltip.ToolTipMixin, wxScheduler):
    def __init__(
        self,
        parent,
        taskList,
        iconProvider,
        onSelect,
        onEdit,
        onCreate,
        onChangeConfig,
        popupMenu,
        *args,
        **kwargs
    ):
        self.getItemTooltipData = parent.getItemTooltipData

        self.__onDropURLCallback = kwargs.pop("onDropURL", None)
        self.__onDropFilesCallback = kwargs.pop("onDropFiles", None)
        self.__onDropMailCallback = kwargs.pop("onDropMail", None)

        self.dropTarget = draganddrop.DropTarget(
            self.OnDropURL, self.OnDropFiles, self.OnDropMail
        )

        super().__init__(parent, wx.ID_ANY, *args, **kwargs)

        self.SetDropTarget(self.dropTarget)

        self.selectCommand = onSelect
        self.iconProvider = iconProvider
        self.editCommand = onEdit
        self.createCommand = onCreate
        self.changeConfigCb = onChangeConfig
        self.popupMenu = popupMenu

        self.__tip = tooltip.SimpleToolTip(self)
        self.__selection = []

        self.__showNoPlannedStartDate = False
        self.__showNoDueDate = False
        self.__showUnplanned = False

        self.SetShowWorkHour(False)
        self.SetResizable(True)

        self.taskList = taskList
        self.RefreshAllItems(0)

        self.Bind(EVT_SCHEDULE_ACTIVATED, self.OnActivation)
        self.Bind(EVT_SCHEDULE_RIGHT_CLICK, self.OnPopup)
        self.Bind(EVT_SCHEDULE_DCLICK, self.OnEdit)
        self.Bind(EVT_PERIODWIDTH_CHANGED, self.OnChangeConfig)

        wxTimeFormat.SetFormatFunction(self.__formatTime)

    @staticmethod
    def __formatTime(dateTime, includeMinutes=False):
        return render.time(
            TaskSchedule.tcDateTime(dateTime), minutes=includeMinutes
        )

    def _handleDrop(self, x, y, droppedObject, cb):
        if cb is not None:
            _, _, item = self._findSchedule(wx.Point(x, y))

            if item is not None:
                if isinstance(item, TaskSchedule):
                    cb(item.task, droppedObject)
                else:
                    datetime = date.DateTime(
                        item.GetYear(), item.GetMonth() + 1, item.GetDay()
                    )
                    cb(
                        None,
                        droppedObject,
                        plannedStartDateTime=datetime,
                        dueDateTime=datetime.endOfDay(),
                    )

    def GetPrintout(self, settings):
        return wxReportScheduler(
            self.GetViewType(),
            self.GetStyle(),
            self.GetDrawer(),
            self.GetDate(),
            self.GetWeekStart(),
            self.GetPeriodCount(),
            self.GetSchedules(),
        )

    def OnDropURL(self, x, y, url):
        self._handleDrop(x, y, url, self.__onDropURLCallback)

    def OnDropFiles(self, x, y, filenames):
        self._handleDrop(x, y, filenames, self.__onDropFilesCallback)

    def OnDropMail(self, x, y, mail):
        self._handleDrop(x, y, mail, self.__onDropMailCallback)

    def SetShowNoStartDate(self, doShow):
        self.__showNoPlannedStartDate = doShow
        self.RefreshAllItems(0)

    def SetShowNoDueDate(self, doShow):
        self.__showNoDueDate = doShow
        self.RefreshAllItems(0)

    def SetShowUnplanned(self, doShow):
        self.__showUnplanned = doShow
        self.RefreshAllItems(0)

    def OnChangeConfig(self, event):  # pylint: disable=W0613
        self.changeConfigCb()

    def Select(self, schedule=None):
        if self.__selection:
            self.taskMap[self.__selection[0].id()].SetSelected(False)

        if schedule is None:
            self.__selection = []
        else:
            self.__selection = [schedule.task]
            schedule.SetSelected(True)

        wx.CallAfter(self.__safeSelectCommand)

    def __safeSelectCommand(self):
        """Safely call selectCommand, guarding against deleted C++ objects."""
        try:
            if self:
                self.selectCommand()
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def SelectTask(self, task):
        if task.id() in self.taskMap:
            self.Select(self.taskMap[task.id()])

    def OnActivation(self, event):
        self.SetFocus()
        self.Select(event.schedule)

    def OnPopup(self, event):
        self.OnActivation(event)
        wx.CallAfter(self.__safePopupMenu)

    def __safePopupMenu(self):
        """Safely show popup menu, guarding against deleted C++ objects."""
        try:
            if self:
                self.PopupMenu(self.popupMenu)
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def OnEdit(self, event):
        if event.schedule is None:
            if event.date is not None:
                self.createCommand(
                    date.DateTime(
                        event.date.GetYear(),
                        event.date.GetMonth() + 1,
                        event.date.GetDay(),
                        event.date.GetHour(),
                        event.date.GetMinute(),
                        event.date.GetSecond(),
                    )
                )
        else:
            self.editCommand(event.schedule.task)

    def RefreshAllItems(self, count):  # pylint: disable=W0613
        x, y = self.GetViewStart()
        selectionId = None
        if self.__selection:
            selectionId = self.__selection[0].id()
        self.__selection = []

        self.DeleteAll()

        schedules = []
        self.taskMap = {}  # pylint: disable=W0201
        maxDateTime = date.DateTime()

        for task in self.taskList:
            if not task.isDeleted():
                if (
                    task.plannedStartDateTime() == maxDateTime
                    or not task.completed()
                ):
                    if (
                        task.plannedStartDateTime() == maxDateTime
                        and not self.__showNoPlannedStartDate
                    ):
                        continue

                    if (
                        task.dueDateTime() == maxDateTime
                        and not self.__showNoDueDate
                    ):
                        continue

                    if not self.__showUnplanned:
                        if (
                            task.plannedStartDateTime() == maxDateTime
                            and task.dueDateTime() == maxDateTime
                        ):
                            continue

                schedule = TaskSchedule(task, self.iconProvider)
                schedules.append(schedule)
                self.taskMap[task.id()] = schedule

                if task.id() == selectionId:
                    self.__selection = [task]
                    schedule.SetSelected(True)

        self.Add(schedules)
        wx.CallAfter(self.__safeSelectCommand)
        self.Scroll(x, y)

    def RefreshItems(self, *args):
        selectionId = None
        if self.__selection:
            selectionId = self.__selection[0].id()
        self.__selection = []

        for task in args:
            doShow = True

            if (
                task.plannedStartDateTime() == date.DateTime()
                and task.dueDateTime() == date.DateTime()
                and not self.__showUnplanned
            ):
                doShow = False

            if (
                task.plannedStartDateTime() == date.DateTime()
                and not self.__showNoPlannedStartDate
            ):
                doShow = False

            if (
                task.dueDateTime() == date.DateTime()
                and not self.__showNoDueDate
            ):
                doShow = False

            # Special case

            if task.isDeleted():
                doShow = False
            elif (
                task.plannedStartDateTime() != date.DateTime()
                and task.completed()
            ):
                doShow = True

            if doShow:
                if task.id() in self.taskMap:
                    schedule = self.taskMap[task.id()]
                    schedule.update()
                else:
                    schedule = TaskSchedule(task, self.iconProvider)
                    self.taskMap[task.id()] = schedule
                    self.Add([schedule])

                if task.id() == selectionId:
                    self.__selection = [task]
                    schedule.SetSelected(True)
            else:
                if task.id() in self.taskMap:
                    self.Delete(self.taskMap[task.id()])
                    del self.taskMap[task.id()]
                    if (
                        self.__selection
                        and self.__selection[0].id() == task.id()
                    ):
                        self.__selection = []
                        wx.CallAfter(self.selectCommand)

    def GetItemCount(self):
        return len(self.GetSchedules())

    def OnBeforeShowToolTip(self, x, y):
        originX, originY = self.GetViewStart()
        unitX, unitY = self.GetScrollPixelsPerUnit()

        try:
            _, _, schedule = self._findSchedule(
                wx.Point(x + originX * unitX, y + originY * unitY)
            )
        except TypeError:
            return

        if schedule and isinstance(schedule, TaskSchedule):
            item = schedule.task

            tooltipData = self.getItemTooltipData(item)
            doShow = any(data[1] for data in tooltipData)
            if doShow:
                self.__tip.SetData(tooltipData)
                return self.__tip
            else:
                return None

    def GetMainWindow(self):
        return self

    MainWindow = property(GetMainWindow)

    def curselection(self):
        return self.__selection


class Calendar(wx.Panel):
    def __init__(
        self,
        parent,
        taskList,
        iconProvider,
        onSelect,
        onEdit,
        onCreate,
        popupMenu,
        *args,
        **kwargs
    ):
        self.getItemTooltipData = parent.getItemTooltipData

        super().__init__(parent)

        self._headers = wx.Panel(self)
        self._content = _CalendarContent(
            self,
            taskList,
            iconProvider,
            onSelect,
            onEdit,
            onCreate,
            popupMenu,
            *args,
            **kwargs
        )

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._headers, 0, wx.EXPAND)
        sizer.Add(self._content, 1, wx.EXPAND)
        self.SetSizer(sizer)

        # Must wx.CallAfter because SetDrawerClass is called this way.
        wx.CallAfter(self._content.SetHeaderPanel, self._headers)

    def Draw(self, dc):
        self._content.Draw(dc)

    def SetShowNoStartDate(self, doShow):
        self._content.SetShowNoStartDate(doShow)

    def SetShowNoDueDate(self, doShow):
        self._content.SetShowNoDueDate(doShow)

    def SetShowUnplanned(self, doShow):
        self._content.SetShowUnplanned(doShow)

    def SetWeekStartMonday(self):
        self._content.SetWeekStart(wxSCHEDULER_WEEKSTART_MONDAY)

    def SetWeekStartSunday(self):
        self._content.SetWeekStart(wxSCHEDULER_WEEKSTART_SUNDAY)

    def RefreshAllItems(self, count):
        self._content.RefreshAllItems(count)

    def RefreshItems(self, *args):
        self._content.RefreshItems(*args)

    def GetItemCount(self):
        return self._content.GetItemCount()

    def curselection(self):
        return self._content.curselection()

    def isAnyItemCollapsable(self):
        return False

    def select(self, tasks):
        if len(tasks) == 1:
            self._content.SelectTask(tasks[0])
        else:
            self._content.Select(None)

    def __getattr__(self, name):
        return getattr(self._content, name)


class TaskSchedule(wxSchedule):
    def __init__(self, task, iconProvider):
        super().__init__()

        self.__selected = False

        self.clientdata = task
        self.iconProvider = iconProvider
        self.update()

    def SetSelected(self, selected):
        self.Freeze()
        try:
            self.__selected = selected
            if selected:
                self.color = wx.SystemSettings.GetColour(
                    wx.SYS_COLOUR_HIGHLIGHT
                )
                # On MS Windows, the selection background is very dark. If
                # the foreground color is too dark, invert it.
                color = self.task.foregroundColor(True) or (0, 0, 0)
                if len(color) == 3:
                    r, g, b = color
                else:
                    r, g, b, a = color
                if r + g + b < 128 * 3:
                    self.foreground = wx.Colour(255 - r, 255 - g, 255 - b)
            else:
                self.color = wx.Colour(
                    *(self.task.backgroundColor(True) or (255, 255, 255))
                )
                self.foreground = wx.Colour(
                    *(self.task.foregroundColor(True) or (0, 0, 0))
                )
        finally:
            self.Thaw()

    def SetStart(self, start):
        command.EditPlannedStartDateTimeCommand(
            items=[self.task], newValue=self.tcDateTime(start)
        ).do()

    def SetEnd(self, end):
        if self.task.completed():
            command.EditCompletionDateTimeCommand(
                items=[self.task], newValue=self.tcDateTime(end)
            ).do()
        else:
            command.EditDueDateTimeCommand(
                items=[self.task], newValue=self.tcDateTime(end)
            ).do()

    def Offset(self, ts):
        kwargs = dict()
        if self.task.plannedStartDateTime() != date.DateTime():
            start = self.GetStart()
            start.AddTS(ts)
            command.EditPlannedStartDateTimeCommand(
                items=[self.task], newValue=self.tcDateTime(start)
            ).do()
        if self.task.completed():
            end = self.GetEnd()
            end.AddTS(ts)
            command.EditCompletionDateTimeCommand(
                items=[self.task], newValue=self.tcDateTime(end)
            ).do()
        elif self.task.dueDateTime() != date.DateTime():
            end = self.GetEnd()
            end.AddTS(ts)
            command.EditDueDateTimeCommand(
                items=[self.task], newValue=self.tcDateTime(end)
            ).do()

    @property
    def task(self):
        return self.clientdata

    def update(self):
        self.Freeze()
        try:
            self.description = self.task.subject()

            self.start = self.wxDateTime(
                self.task.plannedStartDateTime(),
                self.tupleFromDateTime(date.Now().startOfDay()),
            )
            end = (
                self.task.completionDateTime()
                if self.task.completed()
                else self.task.dueDateTime()
            )
            self.end = self.wxDateTime(
                end, self.tupleFromDateTime(date.Now().endOfDay())
            )

            if self.task.completed():
                self.done = True

            self.color = wx.Colour(
                *(self.task.backgroundColor(True) or (255, 255, 255))
            )
            self.foreground = wx.Colour(
                *(self.task.foregroundColor(True) or (0, 0, 0))
            )
            self.font = self.task.font(True)

            self.icons = [self.iconProvider(self.task, False)]
            if self.task.attachments():
                self.icons.append("paperclip_icon")
            if self.task.notes():
                self.icons.append("note_icon")

            if self.task.percentageComplete(recursive=True):
                # If 0, just let the default None value so the progress bar isn't drawn
                # at all
                self.complete = (
                    self.task.percentageComplete(recursive=True) / 100
                )
            else:
                self.complete = None
        finally:
            self.Thaw()

    @staticmethod
    def tupleFromDateTime(dateTime):
        return (
            dateTime.day,
            dateTime.month - 1,
            dateTime.year,
            dateTime.hour,
            dateTime.minute,
            dateTime.second,
        )

    @staticmethod
    def wxDateTime(dateTime, default):
        args = (
            default
            if dateTime == date.DateTime()
            else (
                dateTime.day,
                dateTime.month - 1,
                dateTime.year,
                dateTime.hour,
                dateTime.minute,
                dateTime.second,
            )
        )
        return wx.DateTime.FromDMY(*args)  # pylint: disable=W0142

    @staticmethod
    def tcDateTime(dateTime):
        return date.DateTime(
            dateTime.GetYear(),
            dateTime.GetMonth() + 1,
            dateTime.GetDay(),
            dateTime.GetHour(),
            dateTime.GetMinute(),
            dateTime.GetSecond(),
        )
