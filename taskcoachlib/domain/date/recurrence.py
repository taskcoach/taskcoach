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

import calendar
from . import timedelta
from . import dateandtime as date


class Recurrence(object):
    """Class representing a recurring date."""

    units = ("daily", "weekly", "monthly", "yearly", "")

    def __init__(
        self,
        unit="",
        amount=1,
        sameWeekday=False,
        maximum=0,
        count=0,
        stop_datetime=None,
        recurBasedOnCompletion=False,
        weekdays=None,
    ):
        assert unit in self.units
        assert amount >= 1
        self.unit = unit
        self.amount = amount
        self.stop_datetime = stop_datetime or date.DateTime()
        self.sameWeekday = sameWeekday
        # Maximum number of recurrences we give out, 0 == infinite:
        self.max = maximum
        self.count = count  # Actual number of recurrences given out so far
        self.recurBasedOnCompletion = recurBasedOnCompletion
        # Weekdays for weekly recurrence (list of 0-6, where 0=Monday)
        self.weekdays = weekdays if weekdays is not None else []

    def __call__(self, *dateTimes, **kwargs):
        result = [self._nextDateTime(dateTime) for dateTime in dateTimes]
        if kwargs.get("next", True):
            # By default we expect our clients to call us once, but we allow
            # the client to tell us to expect more calls
            self.count += 1
            if self.__finished_recurring():
                self.unit = ""  # We're done with recurring
                return
        if len(result) > 1:
            return tuple(result)
        elif len(result) == 1:
            return result[0]
        else:
            return

    def __finished_recurring(self):
        """Return whether this recurrence is finished, either because the
        maximum number of recurrences has happened or because the end date
        for the reccurences has passed."""
        return (
            self.max != 0
            and self.count >= self.max
            or date.Now() > self.stop_datetime
        )

    def _nextDateTime(self, dateTime, amount=0):
        if date.DateTime() == dateTime or not self.unit:
            return dateTime
        amount = amount or self.amount
        if amount > 1:
            dateTime = self._nextDateTime(dateTime, amount - 1)
        if self.unit == "yearly":
            return self._addYear(dateTime)
        elif self.unit == "monthly":
            return self._addMonth(dateTime)
        else:
            return self._addDays(dateTime)

    def _addDays(self, dateTime):
        if self.unit == "weekly" and self.weekdays:
            # DateTime.weekday() returns isoweekday (1-7, Mon=1, Sun=7)
            # self.weekdays uses Python convention (0-6, Mon=0, Sun=6)
            # Convert stored weekdays to ISO: iso = python + 1
            current_iso = dateTime.weekday()
            iso_weekdays = sorted([wd + 1 for wd in self.weekdays])
            # Find the next weekday in the list after current
            for wd in iso_weekdays:
                if wd > current_iso:
                    days_ahead = wd - current_iso
                    return dateTime + timedelta.TimeDelta(days=days_ahead)
            # No weekday found this week, go to first selected day next week
            first_iso = iso_weekdays[0]
            days_ahead = 7 - current_iso + first_iso
            return dateTime + timedelta.TimeDelta(days=days_ahead)
        nrOfDays = dict(daily=1, weekly=7)[self.unit]
        return dateTime + timedelta.TimeDelta(days=nrOfDays)

    def _addMonth(self, dateTime):
        year, month, day = dateTime.year, dateTime.month, dateTime.day
        details = (
            dateTime.hour,
            dateTime.minute,
            dateTime.second,
            dateTime.microsecond,
        )
        if month == 12:  # If December, move to January next year
            year += 1
            month = 1
        else:
            month += 1
        if self.sameWeekday:
            weekday = dateTime.weekday()
            weekNr = min(
                3, (day - 1) / 7
            )  # In what week of the month falls aDate, allowable range 0-3
            day = (
                weekNr * 7 + 1
            )  # The earliest possible day that is on the same weekday as aDate
            result = date.DateTime(year, month, day, *details)
            while result.weekday() != weekday:
                day += 1
                result = date.DateTime(year, month, day, *details)
            return result
        else:
            while True:  # Find a valid date in the next month
                try:
                    return date.DateTime(year, month, day, *details)
                except ValueError:
                    day -= 1

    def _addYear(self, dateTime):
        if (
            calendar.isleap(dateTime.year)
            and dateTime.month <= 2
            and dateTime.day <= 28
        ) or (calendar.isleap(dateTime.year + 1) and dateTime.month >= 3):
            days = 366
        else:
            days = 365
        newDateTime = dateTime + timedelta.TimeDelta(days=days)
        if self.sameWeekday:
            # Find the nearest date in newDate's year that is on the right
            # weekday:
            weekday, year = dateTime.weekday(), newDateTime.year
            newEarlierDateTime = newLaterDateTime = newDateTime
            while newEarlierDateTime.weekday() != weekday:
                newEarlierDateTime = newEarlierDateTime - timedelta.ONE_DAY
            while newLaterDateTime.weekday() != weekday:
                newLaterDateTime = newLaterDateTime + timedelta.ONE_DAY
            if newEarlierDateTime.year != year:
                newDateTime = newLaterDateTime
            else:
                newDateTime = newEarlierDateTime
        return newDateTime

    def copy(self):
        return self.__class__(
            self.unit,
            self.amount,
            self.sameWeekday,
            self.max,
            stop_datetime=self.stop_datetime,
            recurBasedOnCompletion=self.recurBasedOnCompletion,
            weekdays=list(self.weekdays),
        )

    def __eq__(self, other):
        try:
            return (
                self.unit == other.unit
                and self.amount == other.amount
                and self.sameWeekday == other.sameWeekday
                and self.max == other.max
                and self.stop_datetime == other.stop_datetime
                and self.recurBasedOnCompletion == other.recurBasedOnCompletion
                and self.weekdays == other.weekdays
            )
        except AttributeError:
            return False

    def __lt__(self, other):
        try:
            return self.units.index(self.unit) < self.units.index(
                other.unit
            ) or (
                self.units.index(self.unit) == self.units.index(other.unit)
                and self.amount < other.amount
            )
        except AttributeError:
            return True

    def __bool__(self):
        return bool(self.unit)
