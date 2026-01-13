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

from taskcoachlib import patterns
from taskcoachlib.domain import base, date
from pubsub import pub
from . import task
from . import tasklist


class ViewFilter(tasklist.TaskListQueryMixin, base.Filter):
    def __init__(self, *args, **kwargs):
        self.__statusesToHide = set(kwargs.pop("statusesToHide", []))
        self.__hideCompositeTasks = kwargs.pop("hideCompositeTasks", False)
        self.registerObservers()
        super().__init__(*args, **kwargs)

    def registerObservers(self):
        registerObserver = patterns.Publisher().registerObserver
        for eventType in (
            task.Task.plannedStartDateTimeChangedEventType(),
            task.Task.dueDateTimeChangedEventType(),
            task.Task.actualStartDateTimeChangedEventType(),
            task.Task.completionDateTimeChangedEventType(),
            task.Task.prerequisitesChangedEventType(),
            task.Task.appearanceChangedEventType(),  # Proxy for status changes
            task.Task.addChildEventType(),
            task.Task.removeChildEventType(),
        ):
            if eventType.startswith("pubsub"):
                pub.subscribe(self.onTaskStatusChange, eventType)
            else:
                registerObserver(
                    self.onTaskStatusChange_Deprecated, eventType=eventType
                )
        # Subscribe to global timer for midnight processing
        pub.subscribe(self._onDateChanged, 'timer.date')

    def detach(self):
        super().detach()
        patterns.Publisher().removeObserver(self.onTaskStatusChange_Deprecated)
        pub.unsubscribe(self._onDateChanged, 'timer.date')

    def _onDateChanged(self, timestamp):
        """Handle date change from global timer."""
        self.atMidnight()

    def atMidnight(self):
        """Whether tasks are included in the filter or not may change at
        midnight."""
        self.reset()

    def onTaskStatusChange(self, newValue, sender):  # pylint: disable=W0613
        self.reset()

    def onTaskStatusChange_Deprecated(
        self, event=None
    ):  # pylint: disable=W0613
        self.reset()

    def hideTaskStatus(self, status, hide=True):
        if hide:
            self.__statusesToHide.add(status)
        else:
            self.__statusesToHide.discard(status)
        self.reset()

    def hideCompositeTasks(self, hide=True):
        self.__hideCompositeTasks = hide
        self.reset()

    def filterItems(self, tasks):
        return [
            task for task in tasks if self.filterTask(task)
        ]  # pylint: disable=W0621

    def filterTask(self, task):  # pylint: disable=W0621
        result = True
        if task.status() in self.__statusesToHide:
            result = False
        elif (
            self.__hideCompositeTasks
            and not self.treeMode()
            and task.children()
        ):
            result = False  # Hide composite task
        return result

    def hasFilter(self):
        return len(self.__statusesToHide) != 0 or (
            self.__hideCompositeTasks and not self.treeMode()
        )
