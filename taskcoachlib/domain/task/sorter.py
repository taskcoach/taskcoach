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

from taskcoachlib.domain import base
from pubsub import pub
from . import task


class Sorter(base.TreeSorter):
    DomainObjectClass = task.Task  # What are we sorting
    TaskStatusAttributes = (
        "prerequisites",
        "dueDateTime",
        "plannedStartDateTime",
        "actualStartDateTime",
        "completionDateTime",
    )

    def __init__(self, *args, **kwargs):
        self.__treeMode = kwargs.pop("treeMode", False)
        self.__sortByTaskStatusFirst = kwargs.pop(
            "sortByTaskStatusFirst", True
        )
        super().__init__(*args, **kwargs)
        for eventType in (
            task.Task.prerequisitesChangedEventType(),
            task.Task.dueDateTimeChangedEventType(),
            task.Task.plannedStartDateTimeChangedEventType(),
            task.Task.actualStartDateTimeChangedEventType(),
            task.Task.completionDateTimeChangedEventType(),
        ):
            pub.subscribe(self.onAttributeChanged, eventType)

    def setTreeMode(self, treeMode=True):
        self.__treeMode = treeMode
        try:
            self.observable().setTreeMode(treeMode)
        except AttributeError:
            pass
        self.reset(forceEvent=True)

    def treeMode(self):
        return self.__treeMode

    def sortByTaskStatusFirst(self, sortByTaskStatusFirst):
        self.__sortByTaskStatusFirst = sortByTaskStatusFirst
        # We don't need to invoke self.reset() here since when this property is
        # changed, the sort order also changes which in turn will cause
        # self.reset() to be called.

    def createSortKeyFunction(self, sortKey):
        statusSortKey = self.__createStatusSortKey()
        regularSortKey = super().createSortKeyFunction(sortKey)
        return lambda task: statusSortKey(task) + [regularSortKey(task)]

    def __createStatusSortKey(self):
        if self.__sortByTaskStatusFirst:
            if self.isAscending():
                # Negate priority so higher priority (more urgent) sorts first
                return lambda task: [-task.computedStatus().statusSortPriority]
            else:
                # For descending, use priority directly (higher sorts first)
                return lambda task: [task.computedStatus().statusSortPriority]
        else:
            return lambda task: []

    def _registerObserverForAttribute(self, attribute):
        # Sorter is always observing task dates and prerequisites because
        # sorting by status depends on those attributes. Hence we don't need
        # to subscribe to these attributes when they become the sort key.
        if attribute not in self.TaskStatusAttributes:
            super()._registerObserverForAttribute(attribute)

    def _removeObserverForAttribute(self, attribute):
        # See comment at _registerObserverForAttribute.
        if attribute not in self.TaskStatusAttributes:
            super()._removeObserverForAttribute(attribute)
