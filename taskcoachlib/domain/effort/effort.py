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
from pubsub import pub
from . import base as baseeffort
import functools
import weakref


@functools.total_ordering
class Effort(baseeffort.BaseEffort, base.Object):

    def __init__(self, task=None, start=None, stop=None, entryMode="standard", *args, **kwargs):
        super().__init__(
            task, start or date.DateTime.now(), stop, *args, **kwargs
        )
        self.__entryMode = Attribute(
            entryMode, self, self._onEntryModeChanged
        )
        self.__duration = Attribute(self._computeDuration(), self, self._onDurationChanged)

    def __getattribute__(self, name):
        """Override to prevent methods from being shadowed by instance attributes.

        During copy/paste operations, kwargs from __getcopystate__ can end up
        as instance attributes that shadow the class methods. This override
        ensures method lookups always find the class method, not instance attrs.
        """
        # Methods that might get shadowed - check directly to avoid recursion
        _protected = (
            'id', 'task', 'subject', 'description', 'font',
            'foregroundColor', 'backgroundColor', 'icon', 'selectedIcon', 'ordering',
            'creationDateTime', 'modificationDateTime'
        )
        if name in _protected:
            # Get the method from the class, not the instance
            for cls in type(self).__mro__:
                if name in cls.__dict__:
                    method = cls.__dict__[name]
                    if callable(method):
                        # Return bound method
                        return method.__get__(self, type(self))
                    break
        return object.__getattribute__(self, name)

    def setTask(self, task):
        if self._task is None:
            # We haven't been fully initialised yet, so allow setting of the
            # task, without notifying observers. Also, don't call addEffort()
            # on the new task, because we assume setTask was invoked by the
            # new task itself.
            self._task = None if task is None else weakref.ref(task)
            return
        # Get current task by dereferencing weakref directly to avoid any
        # potential attribute lookup issues (see issue with copy/paste efforts)
        current_task = self._task() if self._task else None
        if task in (current_task, None):
            # command.PasteCommand may try to set the parent to None
            return
        event = (
            patterns.Event()
        )  # Change monitor needs one event to detect task change
        self._task().removeEffort(self)
        self._task = weakref.ref(task)
        self._task().addEffort(self)
        event.send()
        pub.sendMessage(
            self.taskChangedEventType(), newValue=task, sender=self
        )

    setParent = setTask  # FIXME: should we create a common superclass for Effort and Task?

    @classmethod
    def monitoredAttributes(class_):
        return base.Object.monitoredAttributes() + ["start", "stop"]

    # Note: task() and id() are now handled by __getattribute__ to prevent
    # attribute shadowing issues during copy/paste operations.

    @classmethod
    def taskChangedEventType(class_):
        return "pubsub.effort.task"

    def __str__(self):
        task = self._task() if self._task else None
        return "Effort(%s, %s, %s)" % (task, self._start.get(), self._stop.get())

    __repr__ = __str__

    def __eq__(self, other):
        if not isinstance(other, Effort):
            return NotImplemented
        # Access _Object__id directly to avoid potential attribute shadowing
        return self._Object__id == other._Object__id

    def __lt__(self, other):
        if not isinstance(other, Effort):
            return NotImplemented
        # Compare by start time first, then stop time, then id for total ordering
        self_stop = self._stop.get() if self._stop.get() is not None else date.DateTime.max
        other_stop = other._stop.get() if other._stop.get() is not None else date.DateTime.max
        return (self._start.get(), self_stop, self._Object__id) < (other._start.get(), other_stop, other._Object__id)

    def __hash__(self):
        return hash(self._Object__id)

    def __getstate__(self):
        state = super().__getstate__()
        task = self._task() if self._task else None
        state.update(
            dict(task=task, start=self._start.get(), stop=self._stop.get(),
                 entryMode=self.__entryMode.get(), duration=self.__duration.get())
        )
        return state

    @patterns.eventSource
    def __setstate__(self, state, event=None):
        super().__setstate__(state, event=event)
        self.setTask(state["task"])
        self.setStart(state["start"], event=event)
        self.setStop(state["stop"], event=event)
        self.setEntryMode(state.get("entryMode", "standard"), event=event)
        self.setDuration(state.get("duration"), event=event)

    def __getcopystate__(self):
        state = super().__getcopystate__()
        task = self._task() if self._task else None
        state.update(
            dict(task=task, start=self._start.get(), stop=self._stop.get(),
                 entryMode=self.__entryMode.get(), duration=self.__duration.get())
        )
        return state

    def _computeDuration(self):
        stop = self._stop.get()
        return stop - self._start.get() if stop else None

    def _onDurationChanged(self, event):
        self.sendDurationChangedMessage()
        task = self._task() if self._task else None
        if task and task.hourlyFee():
            self.sendRevenueChangedMessage()

    def sendDurationChangedMessage(self):
        """Override to send stored value, not live-computed value.

        BaseEffort.sendDurationChangedMessage sends self.duration() which
        returns now()-start when duration is None (tracking). We send
        self.__duration.get() (the stored value) to match how start/stop
        send their stored values via getters.
        """
        stored = self.__duration.get()
        from pubsub import pub
        pub.sendMessage(
            self.durationChangedEventType(),
            newValue=stored,
            sender=self,
        )

    def duration(self, now=date.DateTime.now):
        cached = self.__duration.get()
        return (now() - self._start.get()) if cached is None else cached

    def setDuration(self, newDuration, event=None):
        """Setter — normalizes and delegates to Attribute."""
        if newDuration is not None and newDuration == date.TimeDelta():
            newDuration = None
        self.__duration.set(newDuration, event=event)

    def setStart(self, startDateTime, event=None):
        self._start.set(startDateTime, event=event)

    def _onStartChanged(self, event):
        pub.sendMessage(
            self.startChangedEventType(), newValue=self.getStart(), sender=self
        )
        task = self._task() if self._task else None
        if task:
            task.sendTimeSpentChangedMessage()

    @classmethod
    def startChangedEventType(class_):
        return "pubsub.effort.start"

    def setStop(self, newStop=None, event=None):
        if newStop is None:
            newStop = date.DateTime.now()
        elif newStop == date.DateTime.max or newStop == date.DateTime():
            newStop = None
        self._previousStop = self._stop.get()
        self._stop.set(newStop, event=event)

    def _onStopChanged(self, event):
        previousStop = getattr(self, '_previousStop', None)
        newStop = self._stop.get()
        task = self._task() if self._task else None
        if newStop is None:
            pub.sendMessage(
                self.trackingChangedEventType(), newValue=True, sender=self
            )
            if task:
                task.sendTrackingChangedMessage(tracking=True)
        elif previousStop is None:
            pub.sendMessage(
                self.trackingChangedEventType(), newValue=False, sender=self
            )
            if task:
                task.sendTrackingChangedMessage(tracking=False)
        if task:
            task.sendTimeSpentChangedMessage()
        pub.sendMessage(
            self.stopChangedEventType(), newValue=newStop, sender=self
        )

    @classmethod
    def stopChangedEventType(class_):
        return "pubsub.effort.stop"

    def isBeingTracked(self, recursive=False):  # pylint: disable=W0613
        return self._stop.get() is None

    def revenue(self):
        task = self._task() if self._task else None
        hourlyFee = task.hourlyFee() if task else 0
        return self.duration().hours() * hourlyFee

    @staticmethod
    def periodSortFunction(**kwargs):
        # Sort by start of effort first, then make sure the Total entry comes
        # first and finally sort by task subject:
        return lambda effort: (
            effort.getStart(),
            effort.isTotal(),
            (effort._task().subject(recursive=True) if effort._task else ""),
        )

    @classmethod
    def periodSortEventTypes(class_):
        """The event types that influence the effort sort order."""
        return (
            class_.startChangedEventType(),
            class_.taskChangedEventType(),
            task.Task.subjectChangedEventType(),
        )

    @classmethod
    def modificationEventTypes(class_):
        eventTypes = super(Effort, class_).modificationEventTypes()
        return eventTypes + [
            class_.taskChangedEventType(),
            class_.startChangedEventType(),
            class_.stopChangedEventType(),
            class_.entryModeChangedEventType(),
        ]

    # Entry mode (standard, retroactive, or implicit)

    def entryMode(self):
        """Return the entry mode: 'standard', 'retroactive', or 'implicit'."""
        return self.__entryMode.get()

    def setEntryMode(self, mode, event=None):
        self.__entryMode.set(mode, event=event)

    def _onEntryModeChanged(self, event):
        pub.sendMessage(
            self.entryModeChangedEventType(),
            newValue=self.entryMode(),
            sender=self,
        )

    @classmethod
    def entryModeChangedEventType(class_):
        return "pubsub.effort.entryMode"
