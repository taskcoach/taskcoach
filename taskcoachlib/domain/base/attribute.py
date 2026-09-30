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
from taskcoachlib.domain.date import Timestamp
from taskcoachlib.patterns.field import Field
from weakref import WeakSet
import weakref


class Attribute(Field):
    """A field of a domain object, with one change callback however it
    is set. A stored field's change sets its owner's modification date;
    a volatile one, a computed value, does not, nor does the date
    itself (dates=False) (docs/ATTRIBUTE_PATTERN.md, Modification
    Date)."""

    __slots__ = ("__value", "__owner", "__set_event", "__volatile", "__dates")

    def __init__(self, value, owner, set_event, volatile=False, dates=True):
        super().__init__()
        self.__value = value
        self.__owner = weakref.ref(owner)
        self.__set_event = set_event.__func__
        self.__volatile = volatile
        self.__dates = dates and not volatile

    @property
    def stored(self):
        return not self.__volatile

    def get(self):
        return self.__value

    def snapshot(self):
        return self.__value

    def restore(self, value, event=None):
        owner = self.__owner()
        if owner is not None and value != self.__value:
            self.__change(owner, value, dates=False, event=event)

    def set(self, value, event=None):
        owner = self.__owner()
        # Checked before an event is created: the master loop sets
        # thousands of unchanged values
        # (docs/MASTER_SCHEDULER_REFACTOR.md)
        if owner is None or value == self.__value:
            return False
        return self.__change(owner, value, dates=self.__dates, event=event)

    @patterns.eventSource
    def __change(self, owner, value, dates, event=None):
        self.__value = value
        if dates:
            owner.set_modification_datetime(Timestamp.now(), event=event)
        self.__set_event(owner, event)
        return True


class SetAttribute(Field):
    """A set field of a domain object, such as its links to other
    items. A change sets its owner's modification date, as an
    Attribute's does; the reverse of links other items own does not
    (dates=False)."""

    __slots__ = (
        "__set",
        "__owner",
        "__addEvent",
        "__removeEvent",
        "__changeEvent",
        "__setClass",
        "__dates",
    )

    def __init__(
        self,
        values,
        owner,
        addEvent=None,
        removeEvent=None,
        changeEvent=None,
        weak=False,
        dates=True,
    ):
        self.__dates = dates
        self.__setClass = WeakSet if weak else set
        self.__set = self.__setClass(values) if values else self.__setClass()
        self.__owner = weakref.ref(owner)
        self.__addEvent = (addEvent or self.__nullEvent).__func__
        self.__removeEvent = (removeEvent or self.__nullEvent).__func__
        self.__changeEvent = (changeEvent or self.__nullEvent).__func__

    def get(self):
        return set(self.__set)

    def snapshot(self):
        return frozenset(self.__set)

    @staticmethod
    def same(values, others):
        # Items compare equal by ID: a copy is another item
        return {id(value) for value in values} == {
            id(other) for other in others
        }

    def restore(self, values, event=None):
        self.__assign(set(values), dates=False, event=event)

    def set(self, values, event=None):
        return self.__assign(values, dates=self.__dates, event=event)

    @patterns.eventSource
    def __assign(self, values, dates, event=None):
        owner = self.__owner()
        if owner is not None:
            if values == set(self.__set):
                return False
            added = values - set(self.__set)
            removed = set(self.__set) - values
            self.__set = self.__setClass(values)
            if dates:
                self.__set_date(owner, event)
            if added:
                self.__addEvent(owner, event, *added)  # pylint: disable=W0142
            if removed:
                self.__removeEvent(
                    owner, event, *removed
                )  # pylint: disable=W0142
            if added or removed:
                self.__changeEvent(owner, event, *set(self.__set))
            return True

    @patterns.eventSource
    def add(self, values, event=None):
        owner = self.__owner()
        if owner is not None:
            if values <= set(self.__set):
                return False
            self.__set = self.__setClass(set(self.__set) | values)
            self.__set_date(owner, event)
            self.__addEvent(owner, event, *values)  # pylint: disable=W0142
            self.__changeEvent(owner, event, *set(self.__set))
            return True

    @patterns.eventSource
    def remove(self, values, event=None):
        owner = self.__owner()
        if owner is not None:
            if values & set(self.__set) == set():
                return False
            self.__set = self.__setClass(set(self.__set) - values)
            self.__set_date(owner, event)
            self.__removeEvent(owner, event, *values)  # pylint: disable=W0142
            self.__changeEvent(owner, event, *set(self.__set))
            return True

    def __set_date(self, owner, event):
        if self.__dates:
            owner.set_modification_datetime(Timestamp.now(), event=event)

    def __nullEvent(self, *args, **kwargs):
        pass
