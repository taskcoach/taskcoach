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
    def assertRenderedDateTime(self, expectedDateTime, *dateTimeArgs):
        renderedDateTime = render.dateTime(date.DateTime(*dateTimeArgs))
        if expectedDateTime:
            renderedParts = renderedDateTime.split(" ", 1)
            if len(renderedParts) > 1:
                renderedDate, renderedTime = renderedParts
                expectedDate, expectedTime = expectedDateTime.split(" ", 1)
                self.assertEqual(expectedTime, renderedTime)
            else:
                expectedDate, renderedDate = expectedDateTime, renderedDateTime
            self.assertEqual(expectedDate, renderedDate)
        else:
            self.assertEqual(expectedDateTime, renderedDateTime)

    @staticmethod
    def expectedDateTime(*dateTimeArgs):
        return render.dateTimeFunc(date.DateTime(*dateTimeArgs))

    @staticmethod
    def expectedDate(*dateTimeArgs):
        return render.dateFunc(date.DateTime(*dateTimeArgs))

    def testSomeRandomDateTime(self):
        expectedDateTime = self.expectedDateTime(2010, 4, 5, 12, 54)
        self.assertRenderedDateTime(expectedDateTime, 2010, 4, 5, 12, 54, 42)

    def testInfiniteDateTime(self):
        self.assertRenderedDateTime("")

    def testStartOfDay(self):
        expectedDateTime = self.expectedDate(2010, 4, 5)
        self.assertRenderedDateTime(expectedDateTime, 2010, 4, 5)

    def testEndOfDay(self):
        expectedDateTime = self.expectedDate(2010, 4, 5)
        self.assertRenderedDateTime(expectedDateTime, 2010, 4, 5, 23, 59, 59)

    def testEndOfDayWithoutSeconds(self):
        expectedDateTime = self.expectedDate(2010, 4, 5)
        self.assertRenderedDateTime(expectedDateTime, 2010, 4, 5, 23, 59)

    def testAlmostStartOfDay(self):
        expectedDateTime = self.expectedDateTime(2010, 4, 5, 0, 1)
        self.assertRenderedDateTime(expectedDateTime, 2010, 4, 5, 0, 1, 0)

    def testAlmostEndOfDay(self):
        expectedDateTime = self.expectedDateTime(2010, 4, 5, 23, 58)
        self.assertRenderedDateTime(expectedDateTime, 2010, 4, 5, 23, 58, 59)

    def testElevenOClock(self):
        expectedDateTime = self.expectedDateTime(2010, 4, 5, 23, 0)
        self.assertRenderedDateTime(expectedDateTime, 2010, 4, 5, 23, 0, 0)

    def testDateBefore1900(self):
        # Don't check for '1801' since the year may be formatted on only 2
        # digits.
        result = render.dateTime(date.DateTime(1801, 4, 5, 23, 0, 0))
        self.assertTrue("01" in result, result)


class RenderDate(test.TestCase):
    def testRenderDateWithDateTime(self):
        self.assertEqual(
            render.date(date.DateTime(2000, 1, 1)),
            render.date(date.DateTime(2000, 1, 1, 10, 11, 12)),
        )


class RenderTimeLeftTest(test.TestCase):
    def testNoTimeLeftWhenActive(self):
        timeLeft = date.TimeDelta()
        self.assertEqual("0:00", render.timeLeft(timeLeft, False))

    def testNoTimeLeftWhenCompleted(self):
        self.assertEqual("", render.timeLeft(date.TimeDelta(), True))

    def testNoTimeLeftWhenNoDueDate(self):
        self.assertEqual("", render.timeLeft(date.TimeDelta.max, False))

    def testInfiniteTimeLeftWhenCompleted(self):
        self.assertEqual("", render.timeLeft(date.TimeDelta.max, True))

    def testOneDayLeftWhenActive(self):
        timeLeft = date.TimeDelta(days=1)
        self.assertEqual("1 day, 0:00", render.timeLeft(timeLeft, False))

    def testOneDayLeftWhenCompleted(self):
        timeLeft = date.TimeDelta(days=1)
        self.assertEqual("", render.timeLeft(timeLeft, True))

    def testTwoDaysLeftWhenActive(self):
        timeLeft = date.TimeDelta(days=2)
        self.assertEqual("2 days, 0:00", render.timeLeft(timeLeft, False))

    def testTwoDaysLeftWhenCompleted(self):
        timeLeft = date.TimeDelta(days=2)
        self.assertEqual("", render.timeLeft(timeLeft, True))

    def testOneDayLateWhenActive(self):
        timeLeft = date.TimeDelta(days=-1)
        self.assertEqual("-1 day, 0:00", render.timeLeft(timeLeft, False))

    def testOneDayLateWhenCompleted(self):
        timeLeft = date.TimeDelta(days=-1)
        self.assertEqual("", render.timeLeft(timeLeft, True))

    def testOneHourLateWhenActive(self):
        timeLeft = -date.ONE_HOUR
        self.assertEqual("-1:00", render.timeLeft(timeLeft, False))

    def testOneDayHourWhenCompleted(self):
        timeLeft = -date.ONE_HOUR
        self.assertEqual("", render.timeLeft(timeLeft, True))


class RenderTimeSpentTest(test.TestCase):
    def testZeroTime(self):
        self.assertEqual("", render.time_spent(date.TimeDelta()))

    def testOneSecond(self):
        self.assertEqual("0:00:01", render.time_spent(date.ONE_SECOND))

    def testTenHours(self):
        self.assertEqual(
            "10:00:00", render.time_spent(date.TimeDelta(hours=10))
        )

    def testNegativeHours(self):
        self.assertEqual(
            "-1:00:00", render.time_spent(date.TimeDelta(hours=-1))
        )

    def testNegativeSeconds(self):
        self.assertEqual(
            "-0:00:01", render.time_spent(date.TimeDelta(seconds=-1))
        )

    def testDecimal(self):
        self.assertEqual(
            "0.50",
            render.time_spent(date.TimeDelta(minutes=30), decimal=True),
        )

    def testDecimalNul(self):
        self.assertEqual(
            "", render.time_spent(date.TimeDelta(hours=0), decimal=True)
        )

    def testDecimalNegative(self):
        self.assertEqual(
            "-1.25",
            render.time_spent(
                date.TimeDelta(hours=-1, minutes=-15), decimal=True
            ),
        )


class RenderWeekNumberTest(test.TestCase):
    def testWeek1(self):
        self.assertEqual(
            "2005-1", render.weekNumber(date.DateTime(2005, 1, 3))
        )

    def testWeek53(self):
        self.assertEqual(
            "2004-53", render.weekNumber(date.DateTime(2004, 12, 31))
        )


class RenderRecurrenceTest(test.TestCase):
    def testNoRecurrence(self):
        self.assertEqual("", render.recurrence(date.Recurrence()))

    def testDailyRecurrence(self):
        self.assertEqual(
            _("Daily"), render.recurrence(date.Recurrence("daily"))
        )

    def testWeeklyRecurrence(self):
        self.assertEqual(
            _("Weekly"), render.recurrence(date.Recurrence("weekly"))
        )

    def testMonthlyRecurrence(self):
        self.assertEqual(
            _("Monthly"), render.recurrence(date.Recurrence("monthly"))
        )

    def testYearlyRecurrence(self):
        self.assertEqual(
            _("Yearly"), render.recurrence(date.Recurrence("yearly"))
        )

    def testEveryOtherDay(self):
        self.assertEqual(
            _("Every other day"),
            render.recurrence(date.Recurrence("daily", amount=2)),
        )

    def testEveryOtherWeek(self):
        self.assertEqual(
            _("Every other week"),
            render.recurrence(date.Recurrence("weekly", amount=2)),
        )

    def testEveryOtherMonth(self):
        self.assertEqual(
            _("Every other month"),
            render.recurrence(date.Recurrence("monthly", amount=2)),
        )

    def testEveryOtherYear(self):
        self.assertEqual(
            _("Every other year"),
            render.recurrence(date.Recurrence("yearly", amount=2)),
        )

    def testThreeDaily(self):
        self.assertEqual(
            "Every 3 days",
            render.recurrence(date.Recurrence("daily", amount=3)),
        )

    def testThreeWeekly(self):
        self.assertEqual(
            "Every 3 weeks",
            render.recurrence(date.Recurrence("weekly", amount=3)),
        )

    def testThreeMonthly(self):
        self.assertEqual(
            "Every 3 months", render.recurrence(date.Recurrence("monthly", 3))
        )

    def testThreeYearly(self):
        self.assertEqual(
            "Every 3 years", render.recurrence(date.Recurrence("yearly", 3))
        )


class RenderException(test.TestCase):
    def testRenderException(self):
        instance = Exception()
        self.assertEqual(str(instance), render.exception(Exception, instance))

    def testRenderUnicodeDecodeError(self):
        try:
            "abc".encode("utf-16").decode("utf-8")
        except UnicodeDecodeError as instance:
            self.assertEqual(
                str(instance), render.exception(UnicodeDecodeError, instance)
            )

    def testExceptionThatCannotBePrinted(self):
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
