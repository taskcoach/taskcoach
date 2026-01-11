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

from pubsub import pub
import weakref


class BaseEffort(object):
    def __init__(self, task, start, stop, *args, **kwargs):
        self._task = None if task is None else weakref.ref(task)
        self._start = start
        self._stop = stop
        super().__init__(*args, **kwargs)

    def task(self):
        # Access _task directly to avoid potential attribute shadowing
        return None if self._task is None else self._task()

    def parent(self):
        # Efforts don't have real parents since they are not composite.
        # However, we pretend the parent of an effort is its task for the
        # benefit of the search filter.
        return None if self._task is None else self._task()

    def getStart(self):
        return self._start

    def getStop(self):
        return self._stop

    def subject(self, *args, **kwargs):
        task = self._task() if self._task else None
        return task.subject(*args, **kwargs) if task else ""

    def categories(self, *args, **kwargs):
        task = self._task() if self._task else None
        return task.categories(*args, **kwargs) if task else set()

    def foregroundColor(self, recursive=False):
        task = self._task() if self._task else None
        return task.foregroundColor(recursive) if task else None

    def backgroundColor(self, recursive=False):
        task = self._task() if self._task else None
        return task.backgroundColor(recursive) if task else None

    def font(self, recursive=False):
        task = self._task() if self._task else None
        return task.font(recursive) if task else None

    def duration(self, recursive=False):
        raise NotImplementedError  # pragma: no cover

    def revenue(self, recursive=False):
        raise NotImplementedError  # pragma: no cover

    def isTotal(self):
        return False  # Are we a detail effort or a total effort? For sorting.

    @classmethod
    def trackingChangedEventType(class_):
        return "pubsub.effort.track"

    def sendDurationChangedMessage(self):
        pub.sendMessage(
            self.durationChangedEventType(),
            newValue=self.duration(),
            sender=self,
        )

    @classmethod
    def durationChangedEventType(class_):
        return "pubsub.effort.duration"

    def sendRevenueChangedMessage(self):
        pub.sendMessage(
            self.revenueChangedEventType(),
            newValue=self.revenue(),
            sender=self,
        )

    @classmethod
    def revenueChangedEventType(class_):
        return "pubsub.effort.revenue"
