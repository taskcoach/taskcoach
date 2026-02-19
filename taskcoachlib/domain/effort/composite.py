"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2008 Thomas Sonne Olesen <tpo@sonnet.dk>

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

from taskcoachlib import render
from taskcoachlib.domain import date
from taskcoachlib.i18n import _
from pubsub import pub
from . import base


class BaseCompositeEffort(base.BaseEffort):  # pylint: disable=W0223
    def parent(self):
        # Composite efforts don't have a parent.
        return None

    def _inPeriod(self, effort):
        return self.getStart() <= effort.getStart() <= self.getStop()

    def mayContain(self, effort):
        """Return whether effort would be contained in this composite effort
        if it existed."""
        return self._inPeriod(effort)

    def __contains__(self, effort):
        return effort in self._getEfforts()

    def __getitem__(self, index):
        return self._getEfforts()[index]

    def __len__(self):
        return len(self._getEfforts())

    def _getEfforts(self):
        raise NotImplementedError

    def markDirty(self):
        pass  # CompositeEfforts cannot be dirty

    def __doRound(self, duration, rounding, roundUp):
        if rounding:
            return duration.round(seconds=rounding, alwaysUp=roundUp)
        return duration

    def timeSpent(self, now=None):
        """Return the total time spent for this composite (no rounding).
        Required by BaseEffort.sendDurationChangedMessage()."""
        return self.totalTimeSpent()

    def totalTimeSpent(
        self, recursive=False, rounding=0, roundUp=False, consolidate=False
    ):
        if consolidate:
            totalEffort = sum(
                (
                    self.__doRound(effort.timeSpent(), 0, False)
                    for effort in self._getEfforts(recursive)
                ),
                date.TimeDelta(),
            )
            return totalEffort.round(seconds=rounding, alwaysUp=roundUp)
        return sum(
            (
                self.__doRound(effort.timeSpent(), rounding, roundUp)
                for effort in self._getEfforts(recursive)
            ),
            date.TimeDelta(),
        )

    def isBeingTracked(self, recursive=False):  # pylint: disable=W0613
        return any(effort.isBeingTracked() for effort in self._getEfforts())

    def totalTimeSpentForDay(
        self, dayOffset, rounding=0, roundUp=False, consolidate=False
    ):
        """Return the total time spent of grouped efforts on a specific day."""
        startOfDay = self.getStart() + date.TimeDelta(days=dayOffset)
        endOfDay = self.getStart() + date.TimeDelta(days=dayOffset + 1)
        if consolidate:
            totalEffort = sum(
                (
                    self.__doRound(effort.timeSpent(), 0, false)
                    for effort in self._getEfforts(recursive=False)
                    if startOfDay <= effort.getStart() <= endOfDay
                ),
                date.TimeDelta(),
            )
            return self.__doRound(totalEffort, rounding, roundUp)
        return sum(
            (
                self.__doRound(effort.timeSpent(), rounding, roundUp)
                for effort in self._getEfforts(recursive=False)
                if startOfDay <= effort.getStart() <= endOfDay
            ),
            date.TimeDelta(),
        )

    def notifyObserversOfDurationOrEmpty(self):
        if self._getEfforts():
            self.sendDurationChangedMessage()
        else:
            pub.sendMessage(self.compositeEmptyEventType(), sender=self)

    @classmethod
    def compositeEmptyEventType(class_):
        return "pubsub.effort.composite.empty"

    @classmethod
    def modificationEventTypes(class_):
        return []  # A composite effort cannot be 'dirty' since its contents
        # are determined by the contained efforts.

    def onTimeSpentChanged(self, newValue, sender):  # pylint: disable=W0613
        if self._refreshCache():
            # Only need to notify if our time spent actually changed
            self.notifyObserversOfDurationOrEmpty()

    def onRevenueChanged(self, newValue, sender):  # pylint: disable=W0613
        self.sendRevenueChangedMessage()

    def revenue(self, recursive=False):
        raise NotImplementedError  # pragma: no cover

    def _invalidateCache(self):
        """Empty the cache so that it will be filled when accessed."""
        raise NotImplementedError  # pragma: no cover

    def _refreshCache(self):
        """Refresh the cache right away and return whether the cache was
        actually changed."""
        raise NotImplementedError  # pragma: no cover


class CompositeEffort(BaseCompositeEffort):
    """CompositeEffort is a lazy list (but cached) of efforts for one task
    (and its children) and within a certain time period. The task, start
    of time period and end of time period need to be provided when
    initializing the CompositeEffort and cannot be changed
    afterwards."""

    def __init__(self, task, start, stop):  # pylint: disable=W0621
        super().__init__(task, start, stop)
        self.__hash_value = hash((task, start))
        # Effort cache: {True: [efforts recursively], False: [efforts]}
        self.__effort_cache = dict()
        """
        FIMXE! CompositeEffort does not derive from base.Object
        patterns.Publisher().registerObserver(self.onAppearanceChanged,
            eventType=task.appearanceChangedEventType(), eventSource=task)
        """

    def __hash__(self):
        return self.__hash_value

    def __repr__(self):
        return "CompositeEffort(task=%s, start=%s, stop=%s, efforts=%s)" % (
            self.task(),
            self.getStart(),
            self.getStop(),
            str([e for e in self._getEfforts()]),
        )

    def addEffort(self, anEffort):
        assert self._inPeriod(anEffort)
        self.__effort_cache.setdefault(True, set()).add(anEffort)
        if anEffort.task() == self.task():
            self.__effort_cache.setdefault(False, set()).add(anEffort)

    def revenue(self, recursive=False):
        return sum(effort.revenue() for effort in self._getEfforts(recursive))

    def _invalidateCache(self):
        self.__effort_cache = dict()

    def _refreshCache(self, recursive=None):
        recursive_values = (False, True) if recursive is None else (recursive,)
        previous_cache = self.__effort_cache.copy()
        cache_changed = False
        for recursive in recursive_values:
            cache = self.__effort_cache[recursive] = set(
                [
                    effort
                    for effort in self.task().efforts(recursive=recursive)
                    if self._inPeriod(effort)
                ]
            )
            if cache != previous_cache.get(recursive, set()):
                cache_changed = True
        return cache_changed

    def _getEfforts(self, recursive=True):  # pylint: disable=W0221
        if recursive not in self.__effort_cache:
            self._refreshCache(recursive=recursive)
        return list(self.__effort_cache[recursive])

    def mayContain(self, effort):
        """Return whether effort would be contained in this composite effort
        if it existed."""
        return effort.task() == self.task() and super(
            CompositeEffort, self
        ).mayContain(effort)

    def description(self):
        if (
            len(
                set(effort.description() for effort in self._getEfforts(False))
            )
            == 1
        ):
            return self._getEfforts(False)[0].description()
        effortDescriptions = [
            effort.description()
            for effort in sorted(
                self._getEfforts(False), key=lambda effort: effort.getStart()
            )
            if effort.description()
        ]
        return "\n".join(effortDescriptions)

    def onAppearanceChanged(self, event):
        return  # FIXME: CompositeEffort does not derive from base.Object
        # patterns.Event(self.appearanceChangedEventType(), self, event.value()).send()


class CompositeEffortPerPeriod(BaseCompositeEffort):
    class Total(object):
        # pylint: disable=W0613
        def subject(self, *args, **kwargs):
            return _("Total")

        def foregroundColor(self, *args, **kwargs):
            return None

        def backgroundColor(self, *args, **kwargs):
            return None

        def font(self, *args, **kwargs):
            return None

    total = Total()

    def __init__(self, start, stop, taskList, initialEffort=None):
        self.taskList = taskList
        super().__init__(None, start, stop)
        if initialEffort:
            assert self._inPeriod(initialEffort)
            self.__effort_cache = [initialEffort]
        else:
            self._invalidateCache()

    def addEffort(self, anEffort):
        assert self._inPeriod(anEffort)
        if anEffort not in self.__effort_cache:
            self.__effort_cache.append(anEffort)

    @classmethod
    def task(cls):
        return cls.total

    def isTotal(self):
        return True

    def description(self, *args, **kwargs):  # pylint: disable=W0613
        return _("Total for %s") % render.dateTimePeriod(
            self.getStart(), self.getStop()
        )

    def revenue(self, recursive=False):  # pylint: disable=W0613
        return sum(effort.revenue() for effort in self._getEfforts())

    def categories(self, *args, **kwargs):
        return []

    def tasks(self):
        """Return the tasks that have effort in this period."""
        return set([effort.task() for effort in self._getEfforts()])

    def __repr__(self):
        return "CompositeEffortPerPeriod(start=%s, stop=%s, efforts=%s)" % (
            self.getStart(),
            self.getStop(),
            str([e for e in self._getEfforts()]),
        )

    # Cache handling:

    def _getEfforts(self, recursive=False):  # pylint: disable=W0613,W0221
        if self.__effort_cache is None:
            self._refreshCache()
        return self.__effort_cache

    def _invalidateCache(self):
        self.__effort_cache = None

    def _refreshCache(self):
        previous_cache = (
            [] if self.__effort_cache is None else self.__effort_cache[:]
        )
        self.__effort_cache = []
        self.__add_task_effort_to_cache(self.taskList)
        return previous_cache != self.__effort_cache

    def __add_task_effort_to_cache(self, tasks):
        """Add the effort of the tasks to the cache."""
        for task in tasks:
            effort_in_period = [
                effort for effort in task.efforts() if self._inPeriod(effort)
            ]
            self.__effort_cache.extend(effort_in_period)
