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

import time, string, datetime, re  # pylint: disable=W0402
from taskcoachlib import patterns
from .fix import StrftimeFix
from . import timedelta

infinite = datetime.date.max


class RealDate(StrftimeFix, datetime.date):
    def __add__(self, delta):
        newdate = super().__add__(delta)
        return RealDate(newdate.year, newdate.month, newdate.day)

    def __sub__(self, other):
        newdate = super().__sub__(other)
        if isinstance(newdate, datetime.timedelta):
            return timedelta.TimeDelta(newdate.days, newdate.seconds)
        else:
            return RealDate(newdate.year, newdate.month, newdate.day)


class InfiniteDate(datetime.date, metaclass=patterns.Singleton):
    def __new__(self):
        return super().__new__(
            InfiniteDate, infinite.year, infinite.month, infinite.day
        )

    def _getyear(self):
        return None

    year = property(_getyear)

    def _getmonth(self):
        return None

    month = property(_getmonth)

    def _getday(self):
        return None

    day = property(_getday)

    def __str__(self):
        return ""

    def __sub__(self, other):
        if isinstance(other, InfiniteDate):
            return timedelta.TimeDelta()
        else:
            return timedelta.TimeDelta.max

    def __add__(self, delta):
        # Whatever is added to InfiniteDate, we're still infinite:
        return self


# factories:


def parseDate(dateString, default=None):
    try:
        return Date(*[int(part) for part in dateString.split("-")])
    except ValueError:
        if default:
            return default
        else:
            return Date()


def Date(year=infinite.year, month=infinite.month, day=infinite.day):
    if (year, month, day) == (infinite.year, infinite.month, infinite.day):
        return InfiniteDate()
    else:
        return RealDate(year, month, day)
