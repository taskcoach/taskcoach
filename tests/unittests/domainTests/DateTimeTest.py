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

import test, datetime
from taskcoachlib.domain import date


class PyDateTimeTest(test.TestCase):
    def testReplaceCannotBeEasilyUsedToFindTheLastDayofTheMonth(self):
        testDate = datetime.date(2004, 4, 1)  # April 1st, 2004
        try:
            lastDayOfApril = testDate.replace(day=31)
            self.fail(
                "Surprise! datetime.date.replace works as we want!"
            )  # pragma: no cover
            self.assertEqual(
                datetime.date(2004, 4, 30), lastDayOfApril
            )  # pragma: no cover
        except ValueError:
            pass


class DateTimeTest(test.TestCase):
    def testWeekNumber(self):
        self.assertEqual(53, date.DateTime(2005, 1, 1).weeknumber())
        self.assertEqual(1, date.DateTime(2005, 1, 3).weeknumber())

    def testStartOfDay(self):
        startOfDay = date.DateTime(2005, 1, 1, 0, 0, 0, 0)
        noonish = date.DateTime(2005, 1, 1, 12, 30, 15, 400)
        self.assertEqual(startOfDay, noonish.startOfDay())

    def testEndOfDay(self):
        end_of_day = date.DateTime(2005, 1, 1, 23, 59, 59)
        noonish = date.DateTime(2005, 1, 1, 12, 30, 15, 400)
        self.assertEqual(end_of_day, noonish.endOfDay())

    def testStartOfWorkWeekOnWednesday(self):
        startOfWorkWeek = date.DateTime(2011, 7, 25, 0, 0, 0, 0)
        wednesday = date.DateTime(2011, 7, 27, 8, 39, 10)
        self.assertEqual(startOfWorkWeek, wednesday.startOfWorkWeek())

    def testStartOfWorkWeekOnMonday(self):
        startOfWorkWeek = date.DateTime(2011, 7, 25, 0, 0, 0, 0)
        monday = date.DateTime(2011, 7, 25, 8, 39, 10)
        self.assertEqual(startOfWorkWeek, monday.startOfWorkWeek())

    def testStartOfWorkWeekOnSunday(self):
        startOfWorkWeek = date.DateTime(2011, 7, 18, 0, 0, 0, 0)
        sunday = date.DateTime(2011, 7, 24, 8, 39, 10)
        self.assertEqual(startOfWorkWeek, sunday.startOfWorkWeek())

    def testEndOfWorkWeek(self):
        end_of_work_week = date.DateTime(2010, 5, 7, 23, 59, 59)
        midweek = date.DateTime(2010, 5, 5, 12, 30, 15)
        self.assertEqual(end_of_work_week, midweek.endOfWorkWeek())

    def testEndOfWorkWeek_OnSaturday(self):
        end_of_work_week = date.DateTime(2010, 5, 7, 23, 59, 59)
        midweek = date.DateTime(2010, 5, 1, 12, 30, 15)
        self.assertEqual(end_of_work_week, midweek.endOfWorkWeek())

    def testLastDayOfCurrentMonth_InFebruary2004(self):
        expected = date.DateTime(2004, 2, 29)
        actual = date.LastDayOfCurrentMonth(localtime=lambda: (2004, 2, 1))
        self.assertEqual(expected, actual)

    def testLastDayOfCurrentMonth_InDecember(self):
        expected = date.DateTime(2003, 12, 31)
        actual = date.LastDayOfCurrentMonth(localtime=lambda: (2003, 12, 1))
        self.assertEqual(expected, actual)

    def testFormat1900(self):
        self.assertEqual(
            date.DateTime(2, 5, 19, 0, 0, 0).strftime("%Y%m%d"), "20519"
        )


class WholeSecondsTest(test.TestCase):
    """Dates are whole seconds, however they are made; only logs keep
    fractions of a second (docs/MASTER_SCHEDULER_REFACTOR.md)."""

    def assert_whole(self, value):
        self.assertEqual(0, value.microsecond)
        self.assertIsInstance(value, date.DateTime)

    def test_constructor(self):
        self.assert_whole(date.DateTime(2026, 9, 27, 14, 49, 7, 659208))

    def test_keyword(self):
        self.assert_whole(
            date.DateTime(2026, 9, 27, 14, 49, 7, microsecond=659208)
        )

    def test_now(self):
        self.assert_whole(date.Now())

    def test_from_timestamp(self):
        self.assert_whole(date.DateTime.fromtimestamp(1790000000.659208))

    def test_from_date_time(self):
        value = datetime.datetime(2026, 9, 27, 14, 49, 7, 659208)
        self.assert_whole(date.DateTime.fromDateTime(value))

    def test_parse(self):
        self.assert_whole(date.parseDateTime("2026-09-27 14:49:07.659208"))

    def test_arithmetic(self):
        start = date.DateTime(2026, 9, 27, 14, 49, 7)
        self.assert_whole(start + datetime.timedelta(microseconds=659208))
        self.assert_whole(start - datetime.timedelta(microseconds=659208))

    def test_replace(self):
        start = date.DateTime(2026, 9, 27, 14, 49, 7)
        self.assert_whole(start.replace(microsecond=659208))

    def test_end_of_day_is_its_last_second(self):
        self.assertEqual(
            date.DateTime(2026, 9, 27, 23, 59, 59),
            date.DateTime(2026, 9, 27, 12).endOfDay(),
        )

    def test_timestamp_keeps_the_microseconds(self):
        # The modification date only (TimestampTest)
        self.assertEqual(
            659208,
            date.Timestamp.fromtimestamp(1790000000.659208).microsecond,
        )

    def test_unset_date_is_the_latest_second(self):
        self.assertEqual(date.DateTime.max, date.DateTime())
        self.assert_whole(date.DateTime())

    def test_difference_is_whole_seconds(self):
        self.assertEqual(
            0,
            (
                date.Now() - date.DateTime(2026, 1, 1, 0, 0, 0, 500000)
            ).microseconds,
        )


class TimestampTest(test.TestCase):
    """The modification date keeps fractions of a second, like the
    logs, so changes within one second stay ordered."""

    def test_constructor_keeps_the_microseconds(self):
        self.assertEqual(
            659208,
            date.Timestamp(2026, 9, 27, 14, 49, 7, 659208).microsecond,
        )

    def test_now_is_a_timestamp(self):
        self.assertIsInstance(date.Timestamp.now(), date.Timestamp)

    def test_now_is_always_later(self):
        moments = [date.Timestamp.now() for _ in range(1000)]
        self.assertTrue(
            all(each < later for each, later in zip(moments, moments[1:]))
        )

    def test_now_steps_past_a_repeated_clock_value(self):
        # As the clock repeats its value until it ticks (15.6 ms steps
        # on Windows before Python 3.13) or steps back
        saved = date.Timestamp._last
        date.Timestamp._last = date.Timestamp(2999, 1, 1, 0, 0, 0, 5)
        try:
            moment = date.Timestamp.now()
        finally:
            date.Timestamp._last = saved
        self.assertEqual(
            (date.Timestamp(2999, 1, 1, 0, 0, 0, 6), date.Timestamp),
            (moment, type(moment)),
        )

    def test_parse_keeps_the_fraction(self):
        self.assertEqual(
            date.Timestamp(2012, 12, 12, 12, 0, 0, 123450),
            date.Timestamp.parse("2012-12-12 12:00:00.12345"),
        )

    def test_parse_whole_seconds(self):
        self.assertEqual(
            date.Timestamp(2026, 9, 27, 21, 0, 43),
            date.Timestamp.parse("2026-09-27 21:00:43"),
        )

    def test_written_with_its_fraction(self):
        self.assertEqual(
            "2026-09-27 14:49:07.659208",
            str(date.Timestamp(2026, 9, 27, 14, 49, 7, 659208)),
        )
