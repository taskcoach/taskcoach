# -*- coding: utf-8 -*-

"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2008 João Alexandre de Toledo <jtoledo@griffo.com.br>

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
import os
from taskcoachlib import meta, patterns, operating_system
from taskcoachlib.i18n import _
from taskcoachlib.domain import date, task
from pubsub import pub
import wx.adv
from . import artprovider


class TaskBarIcon(patterns.Observer, wx.adv.TaskBarIcon):
    def __init__(
        self,
        mainwindow,
        taskList,
        settings,
        defaultBitmap="taskcoach",
        tickBitmap="clock_icon",
        tackBitmap="clock_stopwatch_icon",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.__window = mainwindow
        self.__taskList = taskList
        self.__settings = settings
        self.__bitmap = self.__defaultBitmap = defaultBitmap
        self.__currentBitmap = self.__bitmap
        self.__tooltipText = ""
        self.__currentText = self.__tooltipText
        self.__tickBitmap = tickBitmap
        self.__tackBitmap = tackBitmap
        self.registerObserver(
            self.onTaskListChanged,
            eventType=taskList.addItemEventType(),
            eventSource=taskList,
        )
        self.registerObserver(
            self.onTaskListChanged,
            eventType=taskList.removeItemEventType(),
            eventSource=taskList,
        )
        pub.subscribe(
            self.onTrackingChanged, task.Task.trackingChangedEventType()
        )
        pub.subscribe(
            self.onChangeDueDateTime, task.Task.dueDateTimeChangedEventType()
        )
        # When the user chances the due soon hours preferences it may cause
        # a task to change appearance. That also means the number of due soon
        # tasks has changed, so we need to change the tool tip text.
        # Note that directly subscribing to the setting (behavior.duesoonhours)
        # is not reliable. The TaskBarIcon may get the event before the tasks
        # do. When that happens the tasks haven't changed their status yet and
        # we would use the wrong status count.
        self.registerObserver(
            self.onChangeDueDateTime_Deprecated,
            eventType=task.Task.appearanceChangedEventType(),
        )
        if operating_system.isGTK():
            events = [wx.adv.EVT_TASKBAR_LEFT_DOWN]
        elif operating_system.isWindows():
            # See http://msdn.microsoft.com/en-us/library/windows/desktop/aa511448.aspx#interaction
            events = [
                wx.adv.EVT_TASKBAR_LEFT_DOWN,
                wx.adv.EVT_TASKBAR_LEFT_DCLICK,
            ]
        else:
            events = [wx.adv.EVT_TASKBAR_LEFT_DCLICK]
        for event in events:
            self.Bind(event, self.onTaskbarClick)
        self.__setTooltipText()
        mainwindow.Bind(wx.EVT_IDLE, self.onIdle)

    # Event handlers:

    def onIdle(self, event):
        if (
            self.__currentText != self.__tooltipText
            or self.__currentBitmap != self.__bitmap
        ):
            self.__currentText = self.__tooltipText
            self.__currentBitmap = self.__bitmap
            self.__setIcon()
        if event is not None:  # Unit tests
            event.Skip()

    def onTaskListChanged(self, event):  # pylint: disable=W0613
        self.__setTooltipText()
        self.__startOrStopTicking()

    def onTrackingChanged(self, newValue, sender):
        if newValue:
            self.registerObserver(
                self.onChangeSubject,
                eventType=sender.subjectChangedEventType(),
                eventSource=sender,
            )
        else:
            self.removeObserver(
                self.onChangeSubject,
                eventType=sender.subjectChangedEventType(),
            )
        self.__setTooltipText()
        if newValue:
            self.__startTicking()
        else:
            self.__stopTicking()

    def onChangeSubject(self, event):  # pylint: disable=W0613
        self.__setTooltipText()

    def onChangeDueDateTime(self, newValue, sender):  # pylint: disable=W0613
        self.__setTooltipText()

    def onChangeDueDateTime_Deprecated(self, event):
        self.__setTooltipText()

    def onEverySecond(self):
        if (
            self.__settings.getboolean(
                "window", "blinktaskbariconwhentrackingeffort"
            )
            and not operating_system.isMacOsXMavericks_OrNewer()
        ):
            self.__toggleTrackingBitmap()
            self.__setIcon()

    def onTaskbarClick(self, event):
        if self.__window.IsIconized() or not self.__window.IsShown():
            self.__window.restore(event)
        else:
            if operating_system.isMac():
                self.__window.Raise()
            else:
                self.__window.Iconize()

    # Menu:

    def setPopupMenu(self, menu):
        self.Bind(wx.adv.EVT_TASKBAR_RIGHT_UP, self.popupTaskBarMenu)
        self.popupmenu = menu  # pylint: disable=W0201

    def popupTaskBarMenu(self, event):  # pylint: disable=W0613
        self.PopupMenu(self.popupmenu)

    # Getters:

    def tooltip(self):
        return self.__tooltipText

    def bitmap(self):
        return self.__bitmap

    def defaultBitmap(self):
        return self.__defaultBitmap

    # Private methods:

    def __startOrStopTicking(self):
        self.__startTicking()
        self.__stopTicking()

    def __startTicking(self):
        if self.__taskList.nrBeingTracked() > 0:
            self.startClock()
            self.__toggleTrackingBitmap()
            self.__setIcon()

    def startClock(self):
        date.Scheduler().schedule_interval(self.onEverySecond, seconds=1)

    def __stopTicking(self):
        if self.__taskList.nrBeingTracked() == 0:
            self.stopClock()
            self.__setDefaultBitmap()
            self.__setIcon()

    def stopClock(self):
        date.Scheduler().unschedule(self.onEverySecond)

    toolTipMessages = [
        (task.status.overdue, _("one task overdue"), _("%d tasks overdue")),
        (task.status.duesoon, _("one task due soon"), _("%d tasks due soon")),
    ]

    def __setTooltipText(self):
        """Note that Windows XP and Vista limit the text shown in the
        tool tip to 64 characters, so we cannot show everything we would
        like to and have to make choices."""
        textParts = []
        trackedTasks = self.__taskList.tasksBeingTracked()
        if trackedTasks:
            count = len(trackedTasks)
            if count == 1:
                tracking = _('tracking "%s"') % trackedTasks[0].subject()
            else:
                tracking = _("tracking effort for %d tasks") % count
            textParts.append(tracking)
        else:
            counts = self.__taskList.nrOfTasksPerStatus()
            for status, singular, plural in self.toolTipMessages:
                count = counts[status]
                if count == 1:
                    textParts.append(singular)
                elif count > 1:
                    textParts.append(plural % count)

        textPart = ", ".join(textParts)
        filename = os.path.basename(self.__window.taskFile.filename())
        namePart = "%s - %s" % (meta.name, filename) if filename else meta.name
        text = "%s\n%s" % (namePart, textPart) if textPart else namePart

        if text != self.__tooltipText:
            self.__tooltipText = text

    def __setDefaultBitmap(self):
        self.__bitmap = self.__defaultBitmap

    def __toggleTrackingBitmap(self):
        tick, tack = self.__tickBitmap, self.__tackBitmap
        self.__bitmap = tack if self.__bitmap == tick else tick

    def __setIcon(self):
        icon = artprovider.getIcon(self.__bitmap)
        try:
            self.SetIcon(icon, self.__tooltipText)
        except Exception:
            # wx assert errors on macOS but the icon still gets set... Whatever
            pass
