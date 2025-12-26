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
from taskcoachlib.i18n import _
from taskcoachlib import help
from pubsub import pub
from pubsub.core import Publisher
from taskcoachlib.domain import task
from . import effort


class MaxDateTimeMixin(object):
    def maxDateTime(self):
        stopTimes = [
            effort.getStop() for effort in self if effort.getStop() is not None
        ]
        return max(stopTimes) if stopTimes else None


class EffortUICommandNamesMixin(object):
    newItemMenuText = _("&New effort...\tCtrl+E")
    newItemHelpText = help.effortNew


class EffortList(
    patterns.SetDecorator, MaxDateTimeMixin, EffortUICommandNamesMixin
):
    """EffortList observes a TaskList and contains all effort records of
    all tasks in the underlying TaskList."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pub.subscribe(
            self.onAddEffortToOrRemoveEffortFromTask,
            task.Task.effortsChangedEventType(),
        )

    def extendSelf(self, tasks, event=None):
        """This method is called when a task is added to the observed list.
        It overrides ObservableListObserver.extendSelf whose default
        behaviour is to add the item that is added to the observed
        list to the observing list (this list) unchanged. But we want to
        add the efforts of the tasks, rather than the tasks themselves."""
        effortsToAdd = []
        for task in tasks:
            effortsToAdd.extend(task.efforts())
        super().extendSelf(effortsToAdd, event)
        # No need to send trackingChangedEventType here - the add event
        # already triggers proper refresh, and SecondRefresher.onItemAdded
        # handles tracking state.

    def removeItemsFromSelf(self, tasks, event=None):
        """This method is called when a task is removed from the observed
        list. It overrides ObservableListObserver.removeItemsFromSelf
        whose default behaviour is to remove the item that was removed
        from the observed list from the observing list (this list)
        unchanged. But we want to remove the efforts of the tasks, rather
        than the tasks themselves."""
        effortsToRemove = []
        for task in tasks:
            effortsToRemove.extend(task.efforts())
        for effort in effortsToRemove:
            if effort.getStop() is None:
                pub.sendMessage(
                    effort.trackingChangedEventType(),
                    newValue=False,
                    sender=effort,
                )
        super().removeItemsFromSelf(effortsToRemove, event)

    def onAddEffortToOrRemoveEffortFromTask(self, newValue, sender):
        if sender not in self.observable():
            return
        newValue, oldValue = newValue
        effortsToAdd = [
            effort for effort in newValue if not effort in oldValue
        ]
        effortsToRemove = [
            effort for effort in oldValue if not effort in newValue
        ]
        super().extendSelf(effortsToAdd)
        super().removeItemsFromSelf(effortsToRemove)
        # Only send trackingChangedEventType for removed efforts.
        # For added efforts, the add event already triggers proper refresh,
        # and SecondRefresher.onItemAdded handles tracking state.
        for effort in effortsToRemove:
            if effort.getStop() is None:
                pub.sendMessage(
                    effort.trackingChangedEventType(),
                    newValue=False,
                    sender=effort,
                )

    def originalLength(self):
        """Do not delegate originalLength to the underlying TaskList because
        that would return a number of tasks, and not the number of effort
        records."""
        return len(self)

    def removeItems(self, efforts):  # pylint: disable=W0221
        """We override ObservableListObserver.removeItems because the default
        implementation is to remove the arguments from the original list,
        which in this case would mean removing efforts from a task list.
        Since that wouldn't work we remove the efforts from the tasks by
        hand."""
        for effort in efforts:
            effort.task().removeEffort(effort)

    def extend(self, efforts):  # pylint: disable=W0221
        """We override ObservableListObserver.extend because the default
        implementation is to add the arguments to the original list,
        which in this case would mean adding efforts to a task list.
        Since that wouldn't work we add the efforts to the tasks by
        hand."""
        for effort in efforts:
            effort.task().addEffort(effort)

    @classmethod
    def sortEventType(class_):
        return "this event type is not used"


class EffortListTracker(patterns.Observer, Publisher):
    """EffortListTracker observes an EffortList and keeps track of
    currently tracked efforts."""

    def __init__(self, effortList, includeComposites=False):
        """@param effortList: The effort list to observe.
        @param includeComposites: if False, composite efforts will be
            ignored."""
        super().__init__()
        Publisher.__init__(self)

        self.__effortList = effortList
        self.__includeComposites = includeComposites

        # __trackedEfforts is a list and not a set because when an effort is
        # moved from one task to another task we might get the event that the
        # effort is (re)added to the effortList before the event that the effort
        # was removed from the effortList. If we would use a set, the effort
        # would be missing from the set after the removal event.
        self.__trackedEfforts = self.__filterTrackedEfforts(self.__effortList)

        self.registerObserver(
            self.onEffortAdded,
            eventType=self.__effortList.addItemEventType(),
            eventSource=self.__effortList,
        )
        self.registerObserver(
            self.onEffortRemoved,
            eventType=self.__effortList.removeItemEventType(),
            eventSource=self.__effortList,
        )
        pub.subscribe(
            self.onTrackingChanged, effort.Effort.trackingChangedEventType()
        )

    def trackedEfforts(self):
        return self.__trackedEfforts

    def onEffortAdded(self, event):
        self.__trackedEfforts.extend(
            self.__filterTrackedEfforts(list(event.values()))
        )
        self.sendMessage(
            "effortlisttracker.changed.added", efforts=self.__trackedEfforts
        )

    def onEffortRemoved(self, event):
        for effort in list(event.values()):
            if effort in self.__trackedEfforts:
                self.__trackedEfforts.remove(effort)
        self.sendMessage(
            "effortlisttracker.changed.removed", efforts=self.__trackedEfforts
        )

    def onTrackingChanged(self, newValue, sender):
        if sender.parent() is None and not self.__includeComposites:
            return
        if sender not in self.__effortList:
            return
        if newValue:
            if sender not in self.__trackedEfforts:
                self.__trackedEfforts.extend([sender])
        else:
            if sender in self.__trackedEfforts:
                self.__trackedEfforts.remove(sender)
        self.sendMessage(
            "effortlisttracker.changed", efforts=self.__trackedEfforts
        )

    @staticmethod
    def __filterTrackedEfforts(efforts):
        return [effort for effort in efforts if effort.isBeingTracked()]
