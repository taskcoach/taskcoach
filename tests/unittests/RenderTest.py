# -*- coding: utf-8 -*-

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
from taskcoachlib import render
from taskcoachlib.i18n import _
from taskcoachlib.domain import date


class RenderDateTime(test.TestCase):
    def assertRenderedDateTime(self, expected_date_time, *date_time_args):
        rendered_date_time = render.dateTime(date.DateTime(*date_time_args))
        if expected_date_time:
            rendered_parts = rendered_date_time.split(" ", 1)
            if len(rendered_parts) > 1:
                rendered_date, rendered_time = rendered_parts
                expected_date, expected_time = expected_date_time.split(" ", 1)
                self.assertEqual(expected_time, rendered_time)
            else:
                expected_date, rendered_date = (
                    expected_date_time,
                    rendered_date_time,
                )
            self.assertEqual(expected_date, rendered_date)
        else:
            self.assertEqual(expected_date_time, rendered_date_time)

    @staticmethod
    def expectedDateTime(*date_time_args):
        return render.dateTimeFunc(date.DateTime(*date_time_args))

    @staticmethod
    def expectedDate(*date_time_args):
        return render.dateFunc(date.DateTime(*date_time_args))

    def test_some_random_date_time(self):
        expected_date_time = self.expectedDateTime(2010, 4, 5, 12, 54)
        self.assertRenderedDateTime(expected_date_time, 2010, 4, 5, 12, 54, 42)

    def test_infinite_date_time(self):
        self.assertRenderedDateTime("")

    def test_start_of_day(self):
        expected_date_time = self.expectedDate(2010, 4, 5)
        self.assertRenderedDateTime(expected_date_time, 2010, 4, 5)

    def test_end_of_day(self):
        expected_date_time = self.expectedDate(2010, 4, 5)
        self.assertRenderedDateTime(expected_date_time, 2010, 4, 5, 23, 59, 59)

    def test_end_of_day_without_seconds(self):
        expected_date_time = self.expectedDate(2010, 4, 5)
        self.assertRenderedDateTime(expected_date_time, 2010, 4, 5, 23, 59)

    def test_almost_start_of_day(self):
        expected_date_time = self.expectedDateTime(2010, 4, 5, 0, 1)
        self.assertRenderedDateTime(expected_date_time, 2010, 4, 5, 0, 1, 0)

    def test_almost_end_of_day(self):
        expected_date_time = self.expectedDateTime(2010, 4, 5, 23, 58)
        self.assertRenderedDateTime(expected_date_time, 2010, 4, 5, 23, 58, 59)

    def test_eleven_o_clock(self):
        expected_date_time = self.expectedDateTime(2010, 4, 5, 23, 0)
        self.assertRenderedDateTime(expected_date_time, 2010, 4, 5, 23, 0, 0)

    def test_date_before_1900(self):
        # Don't check for '1801' since the year may be formatted on only 2
        # digits.
        result = render.dateTime(date.DateTime(1801, 4, 5, 23, 0, 0))
        self.assertTrue("01" in result, result)


class RenderDate(test.TestCase):
    def test_render_date_with_date_time(self):
        self.assertEqual(
            render.date(date.DateTime(2000, 1, 1)),
            render.date(date.DateTime(2000, 1, 1, 10, 11, 12)),
        )


class RenderTimeLeftTest(test.TestCase):
    def test_no_time_left_when_active(self):
        time_left = date.TimeDelta()
        self.assertEqual("0:00", render.timeLeft(time_left, False))

    def test_no_time_left_when_completed(self):
        self.assertEqual("", render.timeLeft(date.TimeDelta(), True))

    def test_no_time_left_when_no_due_date(self):
        self.assertEqual("", render.timeLeft(date.TimeDelta.max, False))

    def test_infinite_time_left_when_completed(self):
        self.assertEqual("", render.timeLeft(date.TimeDelta.max, True))

    def test_one_day_left_when_active(self):
        time_left = date.TimeDelta(days=1)
        self.assertEqual("1 day, 0:00", render.timeLeft(time_left, False))

    def test_one_day_left_when_completed(self):
        time_left = date.TimeDelta(days=1)
        self.assertEqual("", render.timeLeft(time_left, True))

    def test_two_days_left_when_active(self):
        time_left = date.TimeDelta(days=2)
        self.assertEqual("2 days, 0:00", render.timeLeft(time_left, False))

    def test_two_days_left_when_completed(self):
        time_left = date.TimeDelta(days=2)
        self.assertEqual("", render.timeLeft(time_left, True))

    def test_one_day_late_when_active(self):
        time_left = date.TimeDelta(days=-1)
        self.assertEqual("-1 day, 0:00", render.timeLeft(time_left, False))

    def test_one_day_late_when_completed(self):
        time_left = date.TimeDelta(days=-1)
        self.assertEqual("", render.timeLeft(time_left, True))

    def test_one_hour_late_when_active(self):
        time_left = -date.ONE_HOUR
        self.assertEqual("-1:00", render.timeLeft(time_left, False))

    def test_one_day_hour_when_completed(self):
        time_left = -date.ONE_HOUR
        self.assertEqual("", render.timeLeft(time_left, True))


class RenderTimeSpentTest(test.TestCase):
    def test_zero_time(self):
        self.assertEqual("", render.time_spent(date.TimeDelta()))

    def test_one_second(self):
        self.assertEqual("0:00:01", render.time_spent(date.ONE_SECOND))

    def test_ten_hours(self):
        self.assertEqual(
            "10:00:00", render.time_spent(date.TimeDelta(hours=10))
        )

    def test_negative_hours(self):
        self.assertEqual(
            "-1:00:00", render.time_spent(date.TimeDelta(hours=-1))
        )

    def test_negative_seconds(self):
        self.assertEqual(
            "-0:00:01", render.time_spent(date.TimeDelta(seconds=-1))
        )

    def test_decimal(self):
        self.assertEqual(
            "0.50",
            render.time_spent(date.TimeDelta(minutes=30), decimal=True),
        )

    def test_decimal_nul(self):
        self.assertEqual(
            "", render.time_spent(date.TimeDelta(hours=0), decimal=True)
        )

    def test_decimal_negative(self):
        self.assertEqual(
            "-1.25",
            render.time_spent(
                date.TimeDelta(hours=-1, minutes=-15), decimal=True
            ),
        )


class RenderWeekNumberTest(test.TestCase):
    def test_week_1(self):
        self.assertEqual(
            "2005-1", render.weekNumber(date.DateTime(2005, 1, 3))
        )

    def test_week_53(self):
        self.assertEqual(
            "2004-53", render.weekNumber(date.DateTime(2004, 12, 31))
        )


class RenderRecurrenceTest(test.TestCase):
    def test_no_recurrence(self):
        self.assertEqual("", render.recurrence(date.Recurrence()))

    def test_daily_recurrence(self):
        self.assertEqual(
            _("Daily"), render.recurrence(date.Recurrence("daily"))
        )

    def test_weekly_recurrence(self):
        self.assertEqual(
            _("Weekly"), render.recurrence(date.Recurrence("weekly"))
        )

    def test_monthly_recurrence(self):
        self.assertEqual(
            _("Monthly"), render.recurrence(date.Recurrence("monthly"))
        )

    def test_yearly_recurrence(self):
        self.assertEqual(
            _("Yearly"), render.recurrence(date.Recurrence("yearly"))
        )

    def test_every_other_day(self):
        self.assertEqual(
            _("Every other day"),
            render.recurrence(date.Recurrence("daily", amount=2)),
        )

    def test_every_other_week(self):
        self.assertEqual(
            _("Every other week"),
            render.recurrence(date.Recurrence("weekly", amount=2)),
        )

    def test_every_other_month(self):
        self.assertEqual(
            _("Every other month"),
            render.recurrence(date.Recurrence("monthly", amount=2)),
        )

    def test_every_other_year(self):
        self.assertEqual(
            _("Every other year"),
            render.recurrence(date.Recurrence("yearly", amount=2)),
        )

    def test_three_daily(self):
        self.assertEqual(
            "Every 3 days",
            render.recurrence(date.Recurrence("daily", amount=3)),
        )

    def test_three_weekly(self):
        self.assertEqual(
            "Every 3 weeks",
            render.recurrence(date.Recurrence("weekly", amount=3)),
        )

    def test_three_monthly(self):
        self.assertEqual(
            "Every 3 months", render.recurrence(date.Recurrence("monthly", 3))
        )

    def test_three_yearly(self):
        self.assertEqual(
            "Every 3 years", render.recurrence(date.Recurrence("yearly", 3))
        )


class RenderException(test.TestCase):
    def test_render_exception(self):
        instance = Exception()
        self.assertEqual(str(instance), render.exception(Exception, instance))

    def test_render_unicode_decode_error(self):
        try:
            "abc".encode("utf-16").decode("utf-8")
        except UnicodeDecodeError as instance:
            self.assertEqual(
                str(instance), render.exception(UnicodeDecodeError, instance)
            )

    def test_exception_that_cannot_be_printed(self):
        """win32all exceptions may contain localized error
        messages. But Exception.__str__ does not handle non-ASCII
        characters in the args instance variable; calling
        unicode(instance) is just like calling str(instance) and
        raises an UnicodeEncodeError."""

        e = Exception("é")
        try:
            render.exception(Exception, e)
        except UnicodeEncodeError:  # pragma: no cover
            self.fail()
