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

from taskcoachlib import patterns
from taskcoachlib.domain import date, base, task
from taskcoachlib.domain.base.attribute import Attribute
from . import base as baseeffort
import functools


@functools.total_ordering
class Effort(baseeffort.BaseEffort, base.Object):

    def __init__(
        self,
        task=None,
        start=None,
        stop=None,
        entryMode="standard",
        *args,
        **kwargs
    ):
        kwargs.pop("duration", None)  # computed field, not stored
        super().__init__(
            task, start or date.DateTime.now(), stop, *args, **kwargs
        )
        self.__entryMode = Attribute(
            entryMode, self, self._on_entry_mode_changed
        )
        self.__duration = Attribute(
            self._computeDuration(), self, self._on_duration_changed
        )
        # The stop the callback last saw: tracking started or stopped
        # whether it was set or put back by undo
        self.__stop_seen = self._stop.get()

    @patterns.eventSource
    def set_task(self, task, event=None):
        if self._task.get() is None:
            # We haven't been fully initialised yet, so allow setting of the
            # task, without notifying observers. Also, don't call addEffort()
            # on the new task, because we assume set_task was invoked by
            # the new task itself.
            self._task.set(task)
            return
        current_task = self.task()
        # Identity, not ==: domain objects compare equal by id, so a
        # twin read from disk would count as the current task.
        # command.PasteCommand may try to set the parent to None.
        if task is None or task is current_task:
            return
        current_task.removeEffort(self)
        self._task.set(task)
        task.addEffort(self)
        # A link, not an Attribute: its change sets the date here
        self.modified_now(event=event)
        event.addSource(self, task, type=self.taskChangedEventType())

    # FIXME: should we create a common superclass for Effort and Task?
    set_parent = set_task

    @patterns.eventSource
    def _task_restored(self, event=None):
        event.addSource(self, self.task(), type=self.taskChangedEventType())

    @classmethod
    def taskChangedEventType(cls):
        return "effort.task"

    def __str__(self):
        return "Effort(%s, %s, %s)" % (
            self.task(),
            self._start.get(),
            self._stop.get(),
        )

    __repr__ = __str__

    def __eq__(self, other):
        if not isinstance(other, Effort):
            return NotImplemented
        return self.id() == other.id()

    def __lt__(self, other):
        if not isinstance(other, Effort):
            return NotImplemented
        self_stop = (
            self._stop.get()
            if self._stop.get() is not None
            else date.DateTime.max
        )
        other_stop = (
            other._stop.get()
            if other._stop.get() is not None
            else date.DateTime.max
        )
        return (self._start.get(), self_stop, self.id()) < (
            other._start.get(),
            other_stop,
            other.id(),
        )

    def __hash__(self):
        return hash(self.id())

    def __getcopystate__(self):
        state = super().__getcopystate__()
        state.update(
            dict(
                task=self.task(),
                start=self._start.get(),
                # The time spent so far: a copy never tracks, one task
                # tracked at a time (docs/EFFORTS.md, Tracking)
                stop=self._stop.get() or date.DateTime.now(),
                entryMode=self.__entryMode.get(),
                duration=self.__duration.get(),
            )
        )
        return state

    def _computeDuration(self):
        stop = self._stop.get()
        return stop - self._start.get() if stop else None

    def _on_duration_changed(self, event):
        self.send_duration_changed()
        task = self.task()
        if task and task.hourlyFee():
            self.send_revenue_changed()

    def send_duration_changed(self):
        """Override to send stored value, not live-computed value.

        BaseEffort.send_duration_changed sends self.timeSpent(),
        now()-start while tracking. We send stored_duration() (the
        stored value) to match how start/stop send their stored values
        via getters.
        """
        patterns.Event(
            self.durationChangedEventType(), self, self.stored_duration()
        ).send()

    def timeSpent(self, now=date.DateTime.now):
        """Always compute elapsed time from start/stop."""
        stop = self._stop.get()
        if stop is not None:
            return stop - self._start.get()
        return now() - self._start.get()

    def stored_duration(self):
        """The stored duration: None while the effort is tracked."""
        return self.__duration.get()

    def setDuration(self, new_duration, event=None):
        """Setter — normalizes and delegates to Attribute."""
        if new_duration is not None and new_duration == date.TimeDelta():
            new_duration = None
        self.__duration.set(new_duration, event=event)

    def setStart(self, startDateTime, event=None):
        self._start.set(startDateTime, event=event)

    def _on_start_changed(self, event):
        event.addSource(
            self, self.getStart(), type=self.startChangedEventType()
        )
        task = self.task()
        if task:
            task.send_time_spent_changed()

    @classmethod
    def startChangedEventType(cls):
        return "effort.start"

    def setStop(self, new_stop=None, event=None):
        if new_stop is None:
            new_stop = date.DateTime.now()
        elif new_stop == date.DateTime.max or new_stop == date.DateTime():
            new_stop = None
        self._stop.set(new_stop, event=event)

    def _on_stop_changed(self, event):
        previous_stop, new_stop = self.__stop_seen, self._stop.get()
        self.__stop_seen = new_stop
        task = self.task()
        if new_stop is None:
            patterns.Event(self.trackingChangedEventType(), self, True).send()
            if task:
                task.send_tracking_changed(tracking=True)
        elif previous_stop is None:
            patterns.Event(self.trackingChangedEventType(), self, False).send()
            if task:
                task.send_tracking_changed(tracking=False)
        if task:
            task.send_time_spent_changed()
        event.addSource(self, new_stop, type=self.stopChangedEventType())

    @classmethod
    def stopChangedEventType(cls):
        return "effort.stop"

    def isBeingTracked(self, recursive=False):  # pylint: disable=W0613
        return self._stop.get() is None

    def revenue(self):
        task = self.task()
        hourly_fee = task.hourlyFee() if task else 0
        return self.timeSpent().hours() * hourly_fee

    @staticmethod
    def periodSortFunction(**kwargs):
        # Sort by start of effort first, then make sure the Total entry comes
        # first and finally sort by task subject:
        return lambda effort: (
            effort.getStart(),
            effort.isTotal(),
            effort.task().subject(recursive=True) if effort.task() else "",
        )

    @classmethod
    def periodSortEventTypes(cls):
        """The event types that influence the effort sort order."""
        return (
            cls.startChangedEventType(),
            cls.taskChangedEventType(),
            task.Task.subjectChangedEventType(),
        )

    @classmethod
    def modificationEventTypes(cls):
        event_types = super(Effort, cls).modificationEventTypes()
        return event_types + [
            cls.taskChangedEventType(),
            cls.startChangedEventType(),
            cls.stopChangedEventType(),
            cls.entryModeChangedEventType(),
        ]

    # Entry mode (standard, retroactive, or implicit)

    def entryMode(self):
        """Return the entry mode: 'standard', 'retroactive', or 'implicit'."""
        return self.__entryMode.get()

    def setEntryMode(self, mode, event=None):
        self.__entryMode.set(mode, event=event)

    def _on_entry_mode_changed(self, event):
        event.addSource(
            self, self.entryMode(), type=self.entryModeChangedEventType()
        )

    @classmethod
    def entryModeChangedEventType(cls):
        return "effort.entryMode"
