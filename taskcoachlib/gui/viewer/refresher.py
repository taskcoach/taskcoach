"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2008 Rob McMullen <rob.mcmullen@gmail.com>
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

""" This module provides classes that implement refreshing strategies for
    viewers. """  # pylint: disable=W0105


from taskcoachlib import patterns
from pubsub import pub


class MinuteRefresher(patterns.Observer):
    """This class can be used by viewers to refresh themselves every
    minute to refresh attributes like time left. The user of this class
    is responsible for calling refresher.start_clock() and
    stop_clock()."""

    def __init__(self, viewer):
        super().__init__()
        self.__viewer = viewer

    # Registration is idempotent, so no running flag is needed.

    def start_clock(self):
        self.registerObserver(
            self._on_minute_changed, eventType="scheduler.minute"
        )

    def stop_clock(self):
        self.removeObserver(
            self._on_minute_changed, eventType="scheduler.minute"
        )

    def _on_minute_changed(self, event):  # pylint: disable=W0613
        """Handle the minute change the scheduler sends after its
        per-second processing."""
        self.on_every_minute()

    def on_every_minute(self):
        if self.__viewer:
            self.__viewer.refresh()
        else:
            self.stop_clock()


class SecondRefresher(patterns.Observer):
    """This class can be used by viewers to refresh themselves every
    second whenever items (tasks, efforts) are being tracked. It
    subscribes to the GlobalTimer tick instead of running its own timer,
    see docs/SCHEDULERS.md."""

    def __init__(self, viewer, tracking_changed_event_type):
        super().__init__()
        self.__viewer = viewer
        self.__presentation = viewer.presentation()
        self.__tracked_items = set()
        pub.subscribe(self.on_tracking_changed, tracking_changed_event_type)
        self.registerObserver(
            self.on_item_added,
            eventType=self.__presentation.addItemEventType(),
            eventSource=self.__presentation,
        )
        self.registerObserver(
            self.on_item_removed,
            eventType=self.__presentation.removeItemEventType(),
            eventSource=self.__presentation,
        )
        self.set_tracked_items(self.tracked_items(self.__presentation))

    def on_item_added(self, event):
        self.add_tracked_items(self.tracked_items(list(event.values())))

    def on_item_removed(self, event):
        self.remove_tracked_items(self.tracked_items(list(event.values())))

    def on_tracking_changed(self, newValue, sender):
        if sender not in self.__presentation:
            self.set_tracked_items(self.tracked_items(self.__presentation))
            return
        if newValue:
            self.add_tracked_items([sender])
        else:
            self.remove_tracked_items([sender])
        self.refresh_items([sender])

    def on_every_second(self, event=None):  # pylint: disable=W0613
        if self.__viewer and not self.__viewer.needs_second_refresh():
            return
        self.refresh_items(self.__tracked_items)

    def refresh_items(self, items):
        if self.__viewer:
            self.__viewer.refreshItems(*items)  # pylint: disable=W0142
        else:
            self.stop_clock()

    def set_tracked_items(self, items):
        self.__tracked_items = set(items)
        self.start_or_stop_clock()

    def update_presentation(self):
        self.__presentation = self.__viewer.presentation()
        self.set_tracked_items(self.tracked_items(self.__presentation))

    def add_tracked_items(self, items):
        if items:
            self.__tracked_items.update(items)
            self.start_or_stop_clock()

    def remove_tracked_items(self, items):
        if items:
            self.__tracked_items.difference_update(items)
            self.start_or_stop_clock()

    def start_or_stop_clock(self):
        if self.__tracked_items:
            self.start_clock()
        else:
            self.stop_clock()

    def start_clock(self):
        # Registration is idempotent, so no running flag is needed.
        self.registerObserver(self.on_every_second, eventType="timer.second")

    def stop_clock(self):
        self.removeObserver(self.on_every_second, eventType="timer.second")

    def is_clock_started(self):  # Unit tests
        return self.on_every_second in patterns.Publisher().observers(
            eventType="timer.second"
        )

    def currently_tracked_items(self):
        return list(self.__tracked_items)

    @staticmethod
    def tracked_items(items):
        return [item for item in items if item.isBeingTracked(recursive=True)]
