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
from taskcoachlib.domain.base.attribute import Attribute
from taskcoachlib.patterns.field import LinkField


class BaseEffort(object):
    def __init__(self, task, start, stop, *args, **kwargs):
        # A stored field (docs/UNDO_REDO.md, Architecture)
        self._task = LinkField(task, self, self._task_restored)
        self._start = Attribute(start, self, self._on_start_changed)
        self._stop = Attribute(stop, self, self._on_stop_changed)
        super().__init__(*args, **kwargs)

    @patterns.eventSource
    def _task_restored(self, event=None):
        pass  # An effort of the file tells its observers

    def _on_start_changed(self, event):
        pass

    def _on_stop_changed(self, event):
        pass

    def task(self):
        return self._task.get()

    def parent(self):
        # Efforts don't have real parents since they are not composite.
        # However, we pretend the parent of an effort is its task for the
        # benefit of the search filter.
        return self.task()

    def getStart(self):
        return self._start.get()

    def getStop(self):
        return self._stop.get()

    def subject(self, *args, **kwargs):
        task = self.task()
        return task.subject(*args, **kwargs) if task else ""

    def categories(self, *args, **kwargs):
        task = self.task()
        return task.categories(*args, **kwargs) if task else set()

    # An effort is drawn in its task's styles

    def shown_fg_color(self):
        task = self.task()
        return task.shown_fg_color() if task else None

    def shown_bg_color(self):
        task = self.task()
        return task.shown_bg_color() if task else None

    def shown_font(self):
        task = self.task()
        return task.shown_font() if task else None

    def revenue(self, recursive=False):
        raise NotImplementedError  # pragma: no cover

    def isTotal(self):
        return False  # Are we a detail effort or a total effort? For sorting.

    @classmethod
    def trackingChangedEventType(class_):
        return "effort.track"

    def send_duration_changed(self):
        patterns.Event(
            self.durationChangedEventType(), self, self.timeSpent()
        ).send()

    @classmethod
    def durationChangedEventType(class_):
        return "effort.duration"

    def send_revenue_changed(self):
        patterns.Event(
            self.revenueChangedEventType(), self, self.revenue()
        ).send()

    @classmethod
    def revenueChangedEventType(class_):
        return "effort.revenue"
