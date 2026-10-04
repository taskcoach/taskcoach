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

from taskcoachlib.domain import date
import test


class CommonRecurrenceTestsMixin(object):
    def testNextDateWithInfiniteDate(self):
        self.assertEqual(date.DateTime(), self.recur(date.DateTime()))

    def testCopy(self):
        copy = self.recur.copy()
        self.assertEqual(copy, self.recur)

    def testNotEqualToNone(self):
        self.assertNotEqual(None, self.recur)

    def testSetMaxRecurrenceCount(self):
        self.recur.max = 1
        self.recur(date.Now())
        self.assertFalse(self.recur)

    def testSetMaxRecurrenceCount_GetMultipleDates(self):
        self.recur.max = 1
        self.recur(date.Now(), next=False)
        self.assertTrue(self.recur)

    def testSetStopDateTime(self):
        self.recur.stop_datetime = date.Yesterday()
        self.recur(date.Now())
        self.assertFalse(self.recur)

    def testCount(self):
        self.assertEqual(0, self.recur.count)


class DailyRecurrenceCompareTestsMixin(object):
    def testCompareWithNone(self):
        self.assertTrue(self.recur < None)

    def testCompareWithNoRecurrence(self):
        self.assertTrue(self.recur < date.Recurrence())

    def testCompareWithWeeklyRecurrence(self):
        self.assertTrue(self.recur < date.Recurrence("weekly"))

    def testCompareWithMonthlyRecurrence(self):
        self.assertTrue(self.recur < date.Recurrence("monthly"))

    def testCompareWithYearlyRecurrence(self):
        self.assertTrue(self.recur < date.Recurrence("yearly"))


class WeeklyRecurrenceCompareTestsMixin(object):
    def testCompareWithNone(self):
        self.assertTrue(self.recur < None)

    def testCompareWithNoRecurrence(self):
        self.assertTrue(self.recur < date.Recurrence())

    def testCompareWithDailyRecurrence(self):
        self.assertTrue(self.recur > date.Recurrence("daily"))

    def testCompareWithMonthlyRecurrence(self):
        self.assertTrue(self.recur < date.Recurrence("monthly"))

    def testCompareWithYearlyRecurrence(self):
        self.assertTrue(self.recur < date.Recurrence("yearly"))


class MonthlyRecurrenceCompareTestsMixin(object):
    def testCompareWithNone(self):
        self.assertTrue(self.recur < None)

    def testCompareWithNoRecurrence(self):
        self.assertTrue(self.recur < date.Recurrence())

    def testCompareWithDailyRecurrence(self):
        self.assertTrue(self.recur > date.Recurrence("daily"))

    def testCompareWithWeeklyRecurrence(self):
        self.assertTrue(self.recur > date.Recurrence("weekly"))

    def testCompareWithYearlyRecurrence(self):
        self.assertTrue(self.recur < date.Recurrence("yearly"))


class YearlyRecurrenceCompareTestsMixin(object):
    def testCompareWithNone(self):
        self.assertTrue(self.recur < None)

    def testCompareWithNoRecurrence(self):
        self.assertTrue(self.recur < date.Recurrence())

    def testCompareWithDailyRecurrence(self):
        self.assertTrue(self.recur > date.Recurrence("daily"))

    def testCompareWithWeeklyRecurrence(self):
        self.assertTrue(self.recur > date.Recurrence("weekly"))

    def testCompareWithMonthlyRecurrence(self):
        self.assertTrue(self.recur > date.Recurrence("monthly"))


class NoRecurrenceTest(test.TestCase, CommonRecurrenceTestsMixin):
    def setUp(self):
        self.recur = date.Recurrence()

    def testNextDate(self):
        now = date.Now()
        self.assertEqual(now, self.recur(now))

    def testBool(self):
        self.assertFalse(self.recur)

    def testSetMaxRecurrenceCount_GetMultipleDates(self):
        # Without a recurrence there is nothing to count down
        self.recur.max = 1
        self.recur(date.Now(), next=False)
        self.assertFalse(self.recur)


class DailyRecurrenceTest(
    test.TestCase, CommonRecurrenceTestsMixin, DailyRecurrenceCompareTestsMixin
):
    def setUp(self):
        self.recur = date.Recurrence("daily")
        self.now = date.Now()

    def testNextDate(self):
        self.assertEqual(self.now + date.ONE_DAY, self.recur(self.now))

    def testMultipleNextDates(self):
        self.assertEqual(
            (self.now + date.ONE_DAY, self.now),
            self.recur(self.now, self.now - date.ONE_DAY),
        )

    def testNextDateTwice(self):
        now = self.recur(self.now - date.ONE_DAY)
        self.assertEqual(self.now + date.ONE_DAY, self.recur(now))

    def testCompareWithBiDailyRecurrence(self):
        self.assertTrue(self.recur < date.Recurrence("daily", amount=2))


class BiDailyRecurrenceTest(
    test.TestCase, CommonRecurrenceTestsMixin, DailyRecurrenceCompareTestsMixin
):
    def setUp(self):
        self.recur = date.Recurrence("daily", amount=2)
        self.now = date.Now()

    def testEveryOtherDay(self):
        self.assertEqual(
            self.now + date.ONE_DAY, self.recur(self.now - date.ONE_DAY)
        )


class TriDailyRecurrenceTest(
    test.TestCase, CommonRecurrenceTestsMixin, DailyRecurrenceCompareTestsMixin
):
    def setUp(self):
        self.recur = date.Recurrence("daily", amount=3)

    def testEveryThirdDay(self):
        self.assertEqual(
            date.DateTime(2000, 1, 4), self.recur(date.DateTime(2000, 1, 1))
        )


class WeeklyRecurrenceTest(
    test.TestCase,
    CommonRecurrenceTestsMixin,
    WeeklyRecurrenceCompareTestsMixin,
):
    def setUp(self):
        self.January1 = date.DateTime(2000, 1, 1)
        self.January8 = date.DateTime(2000, 1, 8)
        self.January15 = date.DateTime(2000, 1, 15)
        self.recur = date.Recurrence("weekly")

    def testNextDate(self):
        self.assertEqual(self.January8, self.recur(self.January1))

    def testNextDateTwice(self):
        January8 = self.recur(self.January1)
        self.assertEqual(self.January15, self.recur(January8))

    def testCompareWithBiWeeklyRecurrence(self):
        self.assertTrue(self.recur < date.Recurrence("weekly", amount=2))


class BiWeeklyRecurrenceTest(
    test.TestCase,
    CommonRecurrenceTestsMixin,
    WeeklyRecurrenceCompareTestsMixin,
):
    def setUp(self):
        self.recur = date.Recurrence("weekly", amount=2)

    def testEveryOtherWeek(self):
        self.assertEqual(
            date.DateTime(2000, 1, 15, 12, 0, 0),
            self.recur(date.DateTime(2000, 1, 1, 12, 0, 0)),
        )


class MonthlyRecurrenceTest(
    test.TestCase,
    CommonRecurrenceTestsMixin,
    MonthlyRecurrenceCompareTestsMixin,
):
    def setUp(self):
        self.recur = date.Recurrence("monthly")

    def testFirstDayOf31DayMonth(self):
        self.assertEqual(
            date.DateTime(2000, 2, 1), self.recur(date.DateTime(2000, 1, 1))
        )

    def testFirstDayOf30DayMonth(self):
        self.assertEqual(
            date.DateTime(2000, 5, 1), self.recur(date.DateTime(2000, 4, 1))
        )

    def testFirstDayOfDecember(self):
        self.assertEqual(
            date.DateTime(2001, 1, 1), self.recur(date.DateTime(2000, 12, 1))
        )

    def testLastDayOf31DayMonth(self):
        self.assertEqual(
            date.DateTime(2000, 4, 30), self.recur(date.DateTime(2000, 3, 31))
        )

    def testLastDayOf30DayMonth(self):
        self.assertEqual(
            date.DateTime(2000, 5, 30), self.recur(date.DateTime(2000, 4, 30))
        )


class BiMontlyRecurrenceTest(
    test.TestCase,
    CommonRecurrenceTestsMixin,
    MonthlyRecurrenceCompareTestsMixin,
):
    def setUp(self):
        self.recur = date.Recurrence("monthly", amount=2)

    def testEveryOtherMonth(self):
        self.assertEqual(
            date.DateTime(2000, 3, 1), self.recur(date.DateTime(2000, 1, 1))
        )


class MonthlySameWeekDayRecurrenceTest(
    test.TestCase,
    CommonRecurrenceTestsMixin,
    MonthlyRecurrenceCompareTestsMixin,
):
    def setUp(self):
        self.recur = date.Recurrence("monthly", sameWeekday=True)

    def testFirstSaturdayOfTheMonth(self):
        self.assertEqual(
            date.DateTime(2008, 7, 5), self.recur(date.DateTime(2008, 6, 7))
        )

    def testSecondSaturdayOfTheMonth(self):
        self.assertEqual(
            date.DateTime(2008, 7, 12), self.recur(date.DateTime(2008, 6, 14))
        )

    def testThirdSaturdayOfTheMonth(self):
        self.assertEqual(
            date.DateTime(2008, 7, 19), self.recur(date.DateTime(2008, 6, 21))
        )

    def testFourthSaturdayOfTheMonth(self):
        self.assertEqual(
            date.DateTime(2008, 7, 26), self.recur(date.DateTime(2008, 6, 28))
        )

    def testFifthSaturdayOfTheMonth_ResultsInFourthSaterdayOfTheNextMonth(
        self,
    ):
        self.assertEqual(
            date.DateTime(2008, 6, 28), self.recur(date.DateTime(2008, 5, 31))
        )


class BiMonthlySameWeekDayRecurrenceTest(
    test.TestCase,
    CommonRecurrenceTestsMixin,
    MonthlyRecurrenceCompareTestsMixin,
):
    def setUp(self):
        self.recur = date.Recurrence("monthly", amount=2, sameWeekday=True)

    def testFourthSaturdayOfTheMonth(self):
        self.assertEqual(
            date.DateTime(2008, 8, 23), self.recur(date.DateTime(2008, 6, 28))
        )


class YearlyRecurrenceTest(
    test.TestCase,
    CommonRecurrenceTestsMixin,
    YearlyRecurrenceCompareTestsMixin,
):
    def setUp(self):
        self.recur = date.Recurrence("yearly")

    def testJanuary1(self):
        self.assertEqual(
            date.DateTime(2002, 1, 1), self.recur(date.DateTime(2001, 1, 1))
        )

    def testJanuary1_LeapYear(self):
        self.assertEqual(
            date.DateTime(2001, 1, 1), self.recur(date.DateTime(2000, 1, 1))
        )

    def testMarch1_LeapYear(self):
        self.assertEqual(
            date.DateTime(2001, 3, 1), self.recur(date.DateTime(2000, 3, 1))
        )

    def testMarch1_YearBeforeLeapYear(self):
        self.assertEqual(
            date.DateTime(2004, 3, 1), self.recur(date.DateTime(2003, 3, 1))
        )

    def testFebruary1_YearBeforeLeapYear(self):
        self.assertEqual(
            date.DateTime(2004, 2, 1), self.recur(date.DateTime(2003, 2, 1))
        )

    def testFebruary28(self):
        self.assertEqual(
            date.DateTime(2003, 2, 28), self.recur(date.DateTime(2002, 2, 28))
        )

    def testFebruary28_LeapYear(self):
        self.assertEqual(
            date.DateTime(2005, 2, 28), self.recur(date.DateTime(2004, 2, 28))
        )

    def testFebruary28_YearBeforeLeapYear(self):
        self.assertEqual(
            date.DateTime(2004, 2, 28), self.recur(date.DateTime(2003, 2, 28))
        )

    def testFebruary29(self):
        self.assertEqual(
            date.DateTime(2005, 2, 28), self.recur(date.DateTime(2004, 2, 29))
        )


class BiYearlyRecurrenceTest(
    test.TestCase,
    CommonRecurrenceTestsMixin,
    YearlyRecurrenceCompareTestsMixin,
):
    def setUp(self):
        self.recur = date.Recurrence("yearly", amount=2)

    def testEveryOtherYear(self):
        self.assertEqual(
            date.DateTime(2004, 3, 1), self.recur(date.DateTime(2002, 3, 1))
        )


class YearlySameWeekDayRecurrenceTest(
    test.TestCase,
    CommonRecurrenceTestsMixin,
    YearlyRecurrenceCompareTestsMixin,
):
    def setUp(self):
        self.recur = date.Recurrence("yearly", sameWeekday=True)

    def testFirstTuesdayOfTheYear(self):
        self.assertEqual(
            date.DateTime(2009, 1, 6), self.recur(date.DateTime(2008, 1, 1))
        )

    def testFirstWednesdayOfTheYear(self):
        self.assertEqual(
            date.DateTime(2009, 1, 7), self.recur(date.DateTime(2008, 1, 2))
        )

    def testFirstThursdayOfTheYear(self):
        self.assertEqual(
            date.DateTime(2009, 1, 1), self.recur(date.DateTime(2008, 1, 3))
        )

    def testFirstFridayOfTheYear(self):
        self.assertEqual(
            date.DateTime(2009, 1, 2), self.recur(date.DateTime(2008, 1, 4))
        )

    def testLastWednesdayOfTheYear(self):
        self.assertEqual(
            date.DateTime(2009, 12, 30),
            self.recur(date.DateTime(2008, 12, 31)),
        )

    def testLastTuesdayOfTheYear(self):
        self.assertEqual(
            date.DateTime(2009, 12, 29),
            self.recur(date.DateTime(2008, 12, 30)),
        )

    def testLastMondayOfTheYear(self):
        self.assertEqual(
            date.DateTime(2009, 12, 28),
            self.recur(date.DateTime(2008, 12, 29)),
        )

    def testLastSundayOfTheYear(self):
        self.assertEqual(
            date.DateTime(2009, 12, 27),
            self.recur(date.DateTime(2008, 12, 28)),
        )

    def testLastSaturdayOfTheYear(self):
        self.assertEqual(
            date.DateTime(2009, 12, 26),
            self.recur(date.DateTime(2008, 12, 27)),
        )

    def testLastFridayOfTheYear(self):
        self.assertEqual(
            date.DateTime(2009, 12, 25),
            self.recur(date.DateTime(2008, 12, 26)),
        )

    def testLastThursdayOfTheYear(self):
        self.assertEqual(
            date.DateTime(2009, 12, 24),
            self.recur(date.DateTime(2008, 12, 25)),
        )


class MaxRecurrenceTest(test.TestCase, CommonRecurrenceTestsMixin):
    def setUp(self):
        self.recur = date.Recurrence("daily", maximum=4)

    def testFirst(self):
        self.assertEqual(
            date.DateTime(2000, 1, 2),
            self.recur(date.DateTime(2000, 1, 1), next=True),
        )

    def testCountAfterFirst(self):
        self.recur(date.DateTime(2000, 1, 1), next=True)
        self.assertEqual(1, self.recur.count)

    def testLast(self):
        self.recur.count = 4
        self.assertEqual(
            None, self.recur(date.DateTime(2000, 1, 1), next=True)
        )
