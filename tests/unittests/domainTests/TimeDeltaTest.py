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

import test
from taskcoachlib.domain import date


class TimeDeltaTest(test.TestCase):
    def testHours(self):
        timedelta = date.TimeDelta(hours=2, minutes=15)
        self.assertEqual(2.25, timedelta.hours())

    def testMillisecondsInOneSecond(self):
        timedelta = date.TimeDelta(seconds=1)
        self.assertEqual(1000, timedelta.milliseconds())

    def testMillisecondsInOneHour(self):
        timedelta = date.TimeDelta(hours=1)
        self.assertEqual(60 * 60 * 1000, timedelta.milliseconds())

    def testMillisecondsInOneDay(self):
        timedelta = date.TimeDelta(days=1)
        self.assertEqual(24 * 60 * 60 * 1000, timedelta.milliseconds())

    def test_fractions_of_a_second_are_dropped(self):
        # Whole seconds only (docs/MASTER_SCHEDULER_REFACTOR.md)
        self.assertEqual(
            date.TimeDelta(seconds=1),
            date.TimeDelta(seconds=1, milliseconds=999),
        )
        self.assertEqual(0, date.TimeDelta(microseconds=500).milliseconds())

    def testRoundTo5Seconds_Down(self):
        timedelta = date.TimeDelta(seconds=1)
        self.assertEqual(date.TimeDelta(seconds=0), timedelta.round(seconds=5))

    def testRoundTo5Seconds_Up(self):
        timedelta = date.TimeDelta(seconds=3)
        self.assertEqual(date.TimeDelta(seconds=5), timedelta.round(seconds=5))

    def testRoundTo5Seconds_AlwaysUp(self):
        timedelta = date.TimeDelta(seconds=1)
        self.assertEqual(
            date.TimeDelta(seconds=5),
            timedelta.round(seconds=5, alwaysUp=True),
        )

    def testRoundTo10Seconds_Down(self):
        timedelta = date.TimeDelta(seconds=4)
        self.assertEqual(
            date.TimeDelta(seconds=0), timedelta.round(seconds=10)
        )

    def testRoundTo10Seconds_Up(self):
        timedelta = date.TimeDelta(seconds=16)
        self.assertEqual(
            date.TimeDelta(seconds=20), timedelta.round(seconds=10)
        )

    def testRoundTo10Seconds_AlwaysUp(self):
        timedelta = date.TimeDelta(seconds=11)
        self.assertEqual(
            date.TimeDelta(seconds=20),
            timedelta.round(seconds=10, alwaysUp=True),
        )

    def testRoundTo5Minutes_Down(self):
        timedelta = date.TimeDelta(minutes=10, seconds=30)
        self.assertEqual(
            date.TimeDelta(minutes=10), timedelta.round(minutes=5)
        )

    def testRoundTo5Minutes_Up(self):
        timedelta = date.TimeDelta(minutes=8, seconds=30)
        self.assertEqual(
            date.TimeDelta(minutes=10), timedelta.round(minutes=5)
        )

    def testRoundTo5Minutes_AlwaysUp(self):
        timedelta = date.TimeDelta(minutes=6, seconds=30)
        self.assertEqual(
            date.TimeDelta(minutes=10),
            timedelta.round(minutes=5, alwaysUp=True),
        )

    def testRoundTo5Minutes_Big(self):
        timedelta = date.TimeDelta(days=10, minutes=10, seconds=30)
        self.assertEqual(
            date.TimeDelta(days=10, minutes=10), timedelta.round(minutes=5)
        )

    def testRoundTo15Minutes_Down(self):
        timedelta = date.TimeDelta(days=1, hours=10, minutes=7)
        self.assertEqual(
            date.TimeDelta(days=1, hours=10), timedelta.round(minutes=15)
        )

    def testRoundTo15Minutes_AlwaysUp(self):
        timedelta = date.TimeDelta(days=1, hours=10, minutes=7)
        self.assertEqual(
            date.TimeDelta(days=1, hours=10, minutes=15),
            timedelta.round(minutes=15, alwaysUp=True),
        )

    def testRoundTo30Minutes_Up(self):
        timedelta = date.TimeDelta(days=1, hours=10, minutes=15)
        self.assertEqual(
            date.TimeDelta(days=1, hours=10, minutes=30),
            timedelta.round(minutes=30),
        )

    def testRoundTo30Minutes_AlwaysUp(self):
        timedelta = date.TimeDelta(days=1, hours=10, minutes=14)
        self.assertEqual(
            date.TimeDelta(days=1, hours=10, minutes=30),
            timedelta.round(minutes=30, alwaysUp=True),
        )

    def testRoundTo1Hour_Down(self):
        timedelta = date.TimeDelta(days=1, hours=10, minutes=7)
        self.assertEqual(
            date.TimeDelta(days=1, hours=10), timedelta.round(hours=1)
        )

    def testRoundTo1Hour_Up(self):
        timedelta = date.TimeDelta(days=1, hours=10, minutes=30)
        self.assertEqual(
            date.TimeDelta(days=1, hours=11), timedelta.round(hours=1)
        )

    def testRoundTo1Hour_AlwaysUp(self):
        timedelta = date.TimeDelta(days=1, hours=10, minutes=1)
        self.assertEqual(
            date.TimeDelta(days=1, hours=11),
            timedelta.round(hours=1, alwaysUp=True),
        )
