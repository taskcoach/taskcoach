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
from taskcoachlib.domain import date, task
from pubsub import pub
from . import composite
from . import effortlist
from . import effort


class EffortAggregator(
    patterns.SetDecorator, effortlist.EffortUICommandNamesMixin
):
    """This class observes an TaskList and aggregates the individual effort
    records to CompositeEfforts, e.g. per day or per week. Whenever a
    CompositeEffort becomes empty, for example because effort is deleted,
    it sends an 'empty' event so that the aggregator can remove the
    (now empty) CompositeEffort from itself."""

    def __init__(self, *args, **kwargs):
        self.__composites = {}
        self.__trackedComposites = set()
        aggregation = kwargs.pop("aggregation")
        assert aggregation in ("day", "week", "month")
        aggregation = aggregation.capitalize()
        self.__start_of_period = getattr(
            date.DateTime, "startOf%s" % aggregation
        )
        self.__end_of_period = getattr(date.DateTime, "endOf%s" % aggregation)
        super().__init__(*args, **kwargs)
        pub.subscribe(
            self.onCompositeEmpty,
            composite.CompositeEffort.compositeEmptyEventType(),
        )
        pub.subscribe(
            self.onTaskEffortChanged, task.Task.effortsChangedEventType()
        )
        patterns.Publisher().registerObserver(
            self.onChildAddedToTask, eventType=task.Task.addChildEventType()
        )
        patterns.Publisher().registerObserver(
            self.onChildRemovedFromTask,
            eventType=task.Task.removeChildEventType(),
        )
        patterns.Publisher().registerObserver(
            self.onTaskRemoved,
            self.observable().removeItemEventType(),
            eventSource=self.observable(),
        )
        pub.subscribe(
            self.onEffortStartChanged, effort.Effort.startChangedEventType()
        )
        pub.subscribe(
            self.onRevenueChanged, task.Task.hourlyFeeChangedEventType()
        )

    def detach(self):
        super().detach()
        patterns.Publisher().removeObserver(self.onChildAddedToTask)
        patterns.Publisher().removeObserver(self.onChildRemovedFromTask)
        patterns.Publisher().removeObserver(self.onTaskRemoved)

    def extend(self, efforts):  # pylint: disable=W0221
        for effort in efforts:
            effort.task().addEffort(effort)

    def removeItems(self, efforts):  # pylint: disable=W0221
        for effort in efforts:
            effort.task().removeEffort(effort)

    @patterns.eventSource
    def extendSelf(self, tasks, event=None):
        """extendSelf is called when an item is added to the observed
        list. The default behavior of extendSelf is to add the item
        to the observing list (i.e. this list) unchanged. We override
        the default behavior to first get the efforts from the task
        and then group the efforts by time period."""
        new_composites = []
        for task in tasks:  # pylint: disable=W0621
            new_composites.extend(
                self.__create_composites(task, task.efforts())
            )
        self.__extend_self_with_composites(new_composites, event=event)

    @patterns.eventSource
    def __extend_self_with_composites(self, new_composites, event=None):
        """Add composites to the aggregator."""
        super().extendSelf(new_composites, event=event)
        for new_composite in new_composites:
            if new_composite.isBeingTracked():
                self.__trackedComposites.add(new_composite)
                pub.sendMessage(
                    effort.Effort.trackingChangedEventType(),
                    newValue=True,
                    sender=new_composite,
                )

    @patterns.eventSource
    def removeItemsFromSelf(self, tasks, event=None):
        """removeItemsFromSelf is called when an item is removed from the
        observed list. The default behavior of removeItemsFromSelf is to
        remove the item from the observing list (i.e. this list)
        unchanged. We override the default behavior to remove the
        tasks' efforts from the CompositeEfforts they are part of."""
        composites_to_remove = []
        for task in tasks:  # pylint: disable=W0621
            composites_to_remove.extend(self.__composites_to_remove(task))
        self.__remove_composites_from_self(composites_to_remove, event=event)

    @patterns.eventSource
    def __remove_composites_from_self(self, composites_to_remove, event=None):
        """Remove composites from the aggregator."""
        self.__trackedComposites.difference_update(set(composites_to_remove))
        super().removeItemsFromSelf(composites_to_remove, event=event)

    def onTaskRemoved(self, event):
        """Whenever tasks are removed, find the composites that
        (did) contain effort of those tasks and update them."""
        affected_composites = self.__get_composites_for_tasks(
            list(event.values())
        )
        for affected_composite in affected_composites:
            affected_composite._invalidateCache()
            affected_composite.notifyObserversOfDurationOrEmpty()

    def onTaskEffortChanged(self, newValue, sender):
        if sender not in self.observable():
            return
        new_composites = []
        newValue, oldValue = newValue
        efforts_added = [
            effort for effort in newValue if effort not in oldValue
        ]
        efforts_removed = [
            effort for effort in oldValue if effort not in newValue
        ]
        new_composites.extend(self.__create_composites(sender, efforts_added))
        self.__extend_self_with_composites(new_composites)
        for affected_composite in self.__get_composites_for_efforts(
            efforts_added + efforts_removed
        ):
            is_tracked = affected_composite.isBeingTracked()
            was_tracked = affected_composite in self.__trackedComposites
            if is_tracked and not was_tracked:
                self.__trackedComposites.add(affected_composite)
            elif not is_tracked and was_tracked:
                self.__trackedComposites.remove(affected_composite)
            affected_composite.onTimeSpentChanged(newValue, sender)

    def onChildAddedToTask(self, event):
        new_composites = []
        for task in event.sources():  # pylint: disable=W0621
            if task in self.observable():
                child = event.value(task)
                new_composites.extend(
                    self.__create_composites(
                        task, child.efforts(recursive=True)
                    )
                )
        self.__extend_self_with_composites(new_composites)

    def onChildRemovedFromTask(self, event):
        affected_composites = self.__get_composites_for_tasks(
            event.sources() | set(event.values())
        )
        for affected_composite in affected_composites:
            affected_composite._invalidateCache()
            affected_composite.notifyObserversOfDurationOrEmpty()

    def onCompositeEmpty(self, sender):
        # pylint: disable=W0621
        if sender not in self:
            return
        key = self.__key_for_composite(sender)
        if key in self.__composites:
            # A composite may already have been removed, e.g. when a
            # parent and child task have effort in the same period
            del self.__composites[key]
        self.__remove_composites_from_self([sender])

    def onEffortStartChanged(self, newValue, sender):  # pylint: disable=W0613
        new_composites = []
        key = self.__key_for_effort(sender)
        task = sender.task()  # pylint: disable=W0621
        if (task in self.observable()) and (key not in self.__composites):
            new_composites.extend(self.__create_composites(task, [sender]))
        self.__extend_self_with_composites(new_composites)
        for affected_composite in self.__get_composites_for_efforts([sender]):
            is_tracked = affected_composite.isBeingTracked()
            was_tracked = affected_composite in self.__trackedComposites
            if is_tracked and not was_tracked:
                self.__trackedComposites.add(affected_composite)
            elif not is_tracked and was_tracked:
                self.__trackedComposites.remove(affected_composite)
            affected_composite.onTimeSpentChanged(newValue, sender)

    def onRevenueChanged(self, newValue, sender):
        for affected_composite in self.__get_composites_for_tasks([sender]):
            affected_composite.onRevenueChanged(newValue, sender)

    def __get_composites_for_tasks(self, tasks):
        tasks = set(tasks)
        return [
            each_composite
            for each_composite in self
            if each_composite.task() in tasks
            or (
                each_composite.task().__class__.__name__ == "Total"
                and tasks & each_composite.tasks()
            )
        ]

    def __get_composites_for_efforts(self, efforts):
        efforts = set(efforts)
        return [
            each_composite
            for each_composite in self
            if set(each_composite._getEfforts()) & efforts
        ]

    def __create_composites(self, task, efforts):  # pylint: disable=W0621
        new_composites = []
        for effort in efforts:
            new_composites.extend(
                self.__create_composites_for_task(effort, task)
            )
            new_composites.extend(self.__create_composite_for_period(effort))
        return new_composites

    def __create_composites_for_task(
        self, an_effort, task
    ):  # pylint: disable=W0621
        new_composites = []
        for each_task in [task] + task.ancestors():
            key = self.__key_for_effort(an_effort, each_task)
            if key in self.__composites:
                self.__composites[key].addEffort(an_effort)
                continue
            new_composite = composite.CompositeEffort(
                *key
            )  # pylint: disable=W0142
            new_composite.addEffort(an_effort)
            self.__composites[key] = new_composite
            new_composites.append(new_composite)
        return new_composites

    def __create_composite_for_period(self, an_effort):
        key = self.__key_for_period(an_effort)
        if key in self.__composites:
            self.__composites[key].addEffort(an_effort)
            return []
        new_composite_per_period = composite.CompositeEffortPerPeriod(
            key[0], key[1], self.observable(), an_effort
        )
        self.__composites[key] = new_composite_per_period
        return [new_composite_per_period]

    def __composites_to_remove(self, task):  # pylint: disable=W0621
        efforts = task.efforts()
        task_and_ancestors = [task] + task.ancestors()
        composites_to_remove = []
        for effort in efforts:
            for task in task_and_ancestors:
                composites_to_remove.extend(
                    self.__composite_to_remove(effort, task)
                )
        return composites_to_remove

    def __composite_to_remove(
        self, an_effort, task
    ):  # pylint: disable=W0613,W0621
        key = self.__key_for_effort(an_effort, task)
        # A composite may already have been removed, e.g. when a
        # parent and child task have effort in the same period
        return [self.__composites.pop(key)] if key in self.__composites else []

    def maxDateTime(self):
        stop_times = [
            effort.getStop()
            for composite_effort in self
            for effort in composite_effort
            if effort.getStop() is not None
        ]
        return max(stop_times) if stop_times else None

    @staticmethod
    def __key_for_composite(composite_effort):
        if composite_effort.task().__class__.__name__ == "Total":
            return (composite_effort.getStart(), composite_effort.getStop())
        else:
            return (
                composite_effort.task(),
                composite_effort.getStart(),
                composite_effort.getStop(),
            )

    def __key_for_effort(self, effort, task=None):  # pylint: disable=W0621
        task = task or effort.task()
        effort_start = effort.getStart()
        return (
            task,
            self.__start_of_period(effort_start),
            self.__end_of_period(effort_start),
        )

    def __key_for_period(self, effort):
        key = self.__key_for_effort(effort)
        return key[1], key[2]
