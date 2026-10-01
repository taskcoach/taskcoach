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
from taskcoachlib import widgets
from taskcoachlib.domain import date


class TimeDeltaCtrlTest(test.wxTestCase):
    def show(self, delta, readonly=False):
        hours, minutes, seconds = delta.hoursMinutesSeconds()
        negative = delta < date.TimeDelta()
        ctrl = widgets.masked.TimeDeltaCtrl(
            self.frame, 0, 0, 0, readonly=readonly
        )
        ctrl.set_value(hours, minutes, seconds, negative)
        return ctrl.GetValue()

    def test_default_value(self):
        ctrl = widgets.masked.TimeDeltaCtrl(self.frame, 0, 0, 0)
        self.assertEqual("        0:00:00", ctrl.GetValue())

    def test_set_value(self):
        self.assertEqual(
            "       10:00:05", self.show(date.TimeDelta(hours=10, seconds=5))
        )

    def test_overflow(self):
        self.assertEqual(
            "123456789:00:00", self.show(date.TimeDelta(hours=12345678912))
        )

    def test_negative_value_read_only(self):
        self.assertEqual(
            "      -10:20:00",
            self.show(date.TimeDelta(hours=-10, minutes=-20), readonly=True),
        )

    def test_small_negative_value_read_only(self):
        self.assertEqual(
            "       -0:00:04",
            self.show(date.TimeDelta(seconds=-4), readonly=True),
        )
