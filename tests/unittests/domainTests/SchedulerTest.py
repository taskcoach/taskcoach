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

DESIGN NOTE (Scheduler Refactoring - 2024):
The old Scheduler class has been completely removed and replaced with a simpler
GlobalTimer architecture. See docs/SCHEDULERS.md for details.

All timing is now handled via pubsub events:
- 'timer.second': Fires every second
- 'timer.minute': Fires when minute changes
- 'timer.date': Fires when date changes (including on startup)
"""

import test
from pubsub import pub


class GlobalTimerEventTest(test.TestCase):
    """
    Tests for the new GlobalTimer pubsub event system.
    These test the subscription/publication pattern used for timing events.
    """

    def setUp(self):
        super().setUp()
        self.receivedEvents = []

    def tearDown(self):
        # Clean up any subscriptions
        for topic in ['timer.second', 'timer.minute', 'timer.date']:
            try:
                pub.unsubscribe(self._recordEvent, topic)
            except Exception:
                pass
        super().tearDown()

    def _recordEvent(self, timestamp):
        self.receivedEvents.append(timestamp)

    def testCanSubscribeToTimerSecond(self):
        """Verify subscription to timer.second works."""
        pub.subscribe(self._recordEvent, 'timer.second')
        # Just verify no errors - actual timer would need to be running
        pub.unsubscribe(self._recordEvent, 'timer.second')

    def testCanSubscribeToTimerMinute(self):
        """Verify subscription to timer.minute works."""
        pub.subscribe(self._recordEvent, 'timer.minute')
        pub.unsubscribe(self._recordEvent, 'timer.minute')

    def testCanSubscribeToTimerDate(self):
        """Verify subscription to timer.date works."""
        pub.subscribe(self._recordEvent, 'timer.date')
        pub.unsubscribe(self._recordEvent, 'timer.date')

    def testEventDelivery(self):
        """Verify events are delivered to subscribers."""
        pub.subscribe(self._recordEvent, 'timer.second')
        from taskcoachlib.domain import date
        now = date.DateTime.now()
        pub.sendMessage('timer.second', timestamp=now)
        self.assertEqual(len(self.receivedEvents), 1)
        self.assertEqual(self.receivedEvents[0], now)
        pub.unsubscribe(self._recordEvent, 'timer.second')

    def testMultipleSubscribers(self):
        """Verify multiple subscribers all receive events."""
        events1 = []
        events2 = []

        def handler1(timestamp):
            events1.append(timestamp)

        def handler2(timestamp):
            events2.append(timestamp)

        pub.subscribe(handler1, 'timer.second')
        pub.subscribe(handler2, 'timer.second')

        from taskcoachlib.domain import date
        now = date.DateTime.now()
        pub.sendMessage('timer.second', timestamp=now)

        self.assertEqual(len(events1), 1)
        self.assertEqual(len(events2), 1)

        pub.unsubscribe(handler1, 'timer.second')
        pub.unsubscribe(handler2, 'timer.second')

    def testUnsubscribeStopsEvents(self):
        """Verify unsubscribed handlers don't receive events."""
        pub.subscribe(self._recordEvent, 'timer.second')
        pub.unsubscribe(self._recordEvent, 'timer.second')

        from taskcoachlib.domain import date
        now = date.DateTime.now()
        pub.sendMessage('timer.second', timestamp=now)

        self.assertEqual(len(self.receivedEvents), 0)
