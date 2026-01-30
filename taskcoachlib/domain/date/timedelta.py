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

import datetime, math
from typing import Tuple
from .fix import round_fix


class TimeDelta(datetime.timedelta):
    millisecondsPerSecond = 1000
    millisecondsPerDay = 24 * 60 * 60 * millisecondsPerSecond
    millisecondsPerMicroSecond = 1 / 1000.0

    def hoursMinutesSeconds(self) -> Tuple[int, int, int]:
        """Return a tuple (hours, minutes, seconds). Note that the caller
        is responsible for checking whether the TimeDelta instance is
        positive or negative."""
        if self < TimeDelta():
            seconds = 3600 * 24 - self.seconds
            days = abs(self.days) - 1
        else:
            seconds = self.seconds
            days = self.days
        hours, seconds = seconds // 3600, seconds % 3600
        minutes, seconds = seconds // 60, seconds % 60
        hours += days * 24
        return hours, minutes, seconds

    def sign(self):
        return -1 if self < TimeDelta() else 1

    def hours(self):
        """Timedelta expressed in number of hours."""
        hours, minutes, seconds = self.hoursMinutesSeconds()
        return self.sign() * (hours + (minutes / 60.0) + (seconds / 3600.0))

    def minutes(self):
        """Timedelta expressed in number of minutes."""
        hours, minutes, seconds = self.hoursMinutesSeconds()
        return self.sign() * (hours * 60 + minutes + (seconds / 60.0))

    def totalSeconds(self):
        """Timedelta expressed in number of seconds."""
        hours, minutes, seconds = self.hoursMinutesSeconds()
        return self.sign() * (hours * 3600 + minutes * 60 + seconds)

    def milliseconds(self):
        """Timedelta expressed in number of milliseconds."""
        # No need to use self.sign() since self.days is negative for negative values
        return round_fix(
            (self.days * self.millisecondsPerDay)
            + (self.seconds * self.millisecondsPerSecond)
            + (self.microseconds * self.millisecondsPerMicroSecond)
        )

    def round(self, hours=0, minutes=0, seconds=0, alwaysUp=False):
        """Round the timedelta to the nearest x units."""
        assert [hours, minutes, seconds].count(0) >= 2
        roundingUnit = hours * 3600 + minutes * 60 + seconds
        if roundingUnit:
            round_ = math.ceil if alwaysUp else round_fix
            roundedSeconds = (
                round_(self.totalSeconds() / float(roundingUnit))
                * roundingUnit
            )
            return self.__class__(0, roundedSeconds)
        else:
            return self

    def __add__(self, other):
        """Make sure we return a TimeDelta instance and not a
        datetime.timedelta instance"""
        timeDelta = super().__add__(other)
        return self.__class__(
            timeDelta.days, timeDelta.seconds, timeDelta.microseconds
        )

    def __sub__(self, other):
        timeDelta = super().__sub__(other)
        return self.__class__(
            timeDelta.days, timeDelta.seconds, timeDelta.microseconds
        )

    def __neg__(self):
        timeDelta = super().__neg__()
        return self.__class__(
            timeDelta.days, timeDelta.seconds, timeDelta.microseconds
        )


ONE_SECOND = TimeDelta(seconds=1)
ONE_MINUTE = TimeDelta(minutes=1)
ONE_HOUR = TimeDelta(hours=1)
TWO_HOURS = TimeDelta(hours=2)
ONE_DAY = TimeDelta(days=1)
ONE_WEEK = TimeDelta(days=7)
ONE_YEAR = TimeDelta(days=365)


def parseTimeDelta(string):
    try:
        hours, minutes, seconds = [int(x) for x in string.split(":")]
    except ValueError:
        hours, minutes, seconds = 0, 0, 0
    return TimeDelta(hours=hours, minutes=minutes, seconds=seconds)
