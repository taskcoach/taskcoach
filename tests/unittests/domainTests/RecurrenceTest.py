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
    def test_next_date_with_infinite_date(self):
        self.assertEqual(date.DateTime(), self.recur(date.DateTime()))

    def test_copy(self):
        copy = self.recur.copy()
        self.assertEqual(copy, self.recur)

    def test_not_equal_to_none(self):
        self.assertNotEqual(None, self.recur)

    def test_set_max_recurrence_count(self):
        self.recur.max = 1
        self.recur(date.Now())
        self.assertFalse(self.recur)

    def test_set_max_recurrence_count_get_multiple_dates(self):
        self.recur.max = 1
        self.recur(date.Now(), next=False)
        self.assertTrue(self.recur)

    def test_set_stop_date_time(self):
        self.recur.stop_datetime = date.Yesterday()
        self.recur(date.Now())
        self.assertFalse(self.recur)

    def test_count(self):
        self.assertEqual(0, self.recur.count)


class DailyRecurrenceCompareTestsMixin(object):
    def test_compare_with_none(self):
        self.assertTrue(self.recur < None)

    def test_compare_with_no_recurrence(self):
        self.assertTrue(self.recur < date.Recurrence())

    def test_compare_with_weekly_recurrence(self):
        self.assertTrue(self.recur < date.Recurrence("weekly"))

    def test_compare_with_monthly_recurrence(self):
        self.assertTrue(self.recur < date.Recurrence("monthly"))

    def test_compare_with_yearly_recurrence(self):
        self.assertTrue(self.recur < date.Recurrence("yearly"))


class WeeklyRecurrenceCompareTestsMixin(object):
    def test_compare_with_none(self):
        self.assertTrue(self.recur < None)

    def test_compare_with_no_recurrence(self):
        self.assertTrue(self.recur < date.Recurrence())

    def test_compare_with_daily_recurrence(self):
        self.assertTrue(self.recur > date.Recurrence("daily"))

    def test_compare_with_monthly_recurrence(self):
        self.assertTrue(self.recur < date.Recurrence("monthly"))

    def test_compare_with_yearly_recurrence(self):
        self.assertTrue(self.recur < date.Recurrence("yearly"))


class MonthlyRecurrenceCompareTestsMixin(object):
    def test_compare_with_none(self):
        self.assertTrue(self.recur < None)

    def test_compare_with_no_recurrence(self):
        self.assertTrue(self.recur < date.Recurrence())

    def test_compare_with_daily_recurrence(self):
        self.assertTrue(self.recur > date.Recurrence("daily"))

    def test_compare_with_weekly_recurrence(self):
        self.assertTrue(self.recur > date.Recurrence("weekly"))

    def test_compare_with_yearly_recurrence(self):
        self.assertTrue(self.recur < date.Recurrence("yearly"))


class YearlyRecurrenceCompareTestsMixin(object):
    def test_compare_with_none(self):
        self.assertTrue(self.recur < None)

    def test_compare_with_no_recurrence(self):
        self.assertTrue(self.recur < date.Recurrence())

    def test_compare_with_daily_recurrence(self):
        self.assertTrue(self.recur > date.Recurrence("daily"))

    def test_compare_with_weekly_recurrence(self):
        self.assertTrue(self.recur > date.Recurrence("weekly"))

    def test_compare_with_monthly_recurrence(self):
        self.assertTrue(self.recur > date.Recurrence("monthly"))


class NoRecurrenceTest(test.TestCase, CommonRecurrenceTestsMixin):
    def setUp(self):
        self.recur = date.Recurrence()

    def test_next_date(self):
        now = date.Now()
        self.assertEqual(now, self.recur(now))

    def test_bool(self):
        self.assertFalse(self.recur)

    def test_set_max_recurrence_count_get_multiple_dates(self):
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

    def test_next_date(self):
        self.assertEqual(self.now + date.ONE_DAY, self.recur(self.now))

    def test_multiple_next_dates(self):
        self.assertEqual(
            (self.now + date.ONE_DAY, self.now),
            self.recur(self.now, self.now - date.ONE_DAY),
        )

    def test_next_date_twice(self):
        now = self.recur(self.now - date.ONE_DAY)
        self.assertEqual(self.now + date.ONE_DAY, self.recur(now))

    def test_compare_with_bi_daily_recurrence(self):
        self.assertTrue(self.recur < date.Recurrence("daily", amount=2))


class BiDailyRecurrenceTest(
    test.TestCase, CommonRecurrenceTestsMixin, DailyRecurrenceCompareTestsMixin
):
    def setUp(self):
        self.recur = date.Recurrence("daily", amount=2)
        self.now = date.Now()

    def test_every_other_day(self):
        self.assertEqual(
            self.now + date.ONE_DAY, self.recur(self.now - date.ONE_DAY)
        )


class TriDailyRecurrenceTest(
    test.TestCase, CommonRecurrenceTestsMixin, DailyRecurrenceCompareTestsMixin
):
    def setUp(self):
        self.recur = date.Recurrence("daily", amount=3)

    def test_every_third_day(self):
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

    def test_next_date(self):
        self.assertEqual(self.January8, self.recur(self.January1))

    def test_next_date_twice(self):
        january_8 = self.recur(self.January1)
        self.assertEqual(self.January15, self.recur(january_8))

    def test_compare_with_bi_weekly_recurrence(self):
        self.assertTrue(self.recur < date.Recurrence("weekly", amount=2))


class BiWeeklyRecurrenceTest(
    test.TestCase,
    CommonRecurrenceTestsMixin,
    WeeklyRecurrenceCompareTestsMixin,
):
    def setUp(self):
        self.recur = date.Recurrence("weekly", amount=2)

    def test_every_other_week(self):
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

    def test_first_day_of_31_day_month(self):
        self.assertEqual(
            date.DateTime(2000, 2, 1), self.recur(date.DateTime(2000, 1, 1))
        )

    def test_first_day_of_30_day_month(self):
        self.assertEqual(
            date.DateTime(2000, 5, 1), self.recur(date.DateTime(2000, 4, 1))
        )

    def test_first_day_of_december(self):
        self.assertEqual(
            date.DateTime(2001, 1, 1), self.recur(date.DateTime(2000, 12, 1))
        )

    def test_last_day_of_31_day_month(self):
        self.assertEqual(
            date.DateTime(2000, 4, 30), self.recur(date.DateTime(2000, 3, 31))
        )

    def test_last_day_of_30_day_month(self):
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

    def test_every_other_month(self):
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

    def test_first_saturday_of_the_month(self):
        self.assertEqual(
            date.DateTime(2008, 7, 5), self.recur(date.DateTime(2008, 6, 7))
        )

    def test_second_saturday_of_the_month(self):
        self.assertEqual(
            date.DateTime(2008, 7, 12), self.recur(date.DateTime(2008, 6, 14))
        )

    def test_third_saturday_of_the_month(self):
        self.assertEqual(
            date.DateTime(2008, 7, 19), self.recur(date.DateTime(2008, 6, 21))
        )

    def test_fourth_saturday_of_the_month(self):
        self.assertEqual(
            date.DateTime(2008, 7, 26), self.recur(date.DateTime(2008, 6, 28))
        )

    def test_fifth_saturday_of_month_results_in_fourth_saterday_of_next_month(
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

    def test_fourth_saturday_of_the_month(self):
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

    def test_january_1(self):
        self.assertEqual(
            date.DateTime(2002, 1, 1), self.recur(date.DateTime(2001, 1, 1))
        )

    def test_january_1_leap_year(self):
        self.assertEqual(
            date.DateTime(2001, 1, 1), self.recur(date.DateTime(2000, 1, 1))
        )

    def test_march_1_leap_year(self):
        self.assertEqual(
            date.DateTime(2001, 3, 1), self.recur(date.DateTime(2000, 3, 1))
        )

    def test_march_1_year_before_leap_year(self):
        self.assertEqual(
            date.DateTime(2004, 3, 1), self.recur(date.DateTime(2003, 3, 1))
        )

    def test_february_1_year_before_leap_year(self):
        self.assertEqual(
            date.DateTime(2004, 2, 1), self.recur(date.DateTime(2003, 2, 1))
        )

    def test_february_28(self):
        self.assertEqual(
            date.DateTime(2003, 2, 28), self.recur(date.DateTime(2002, 2, 28))
        )

    def test_february_28_leap_year(self):
        self.assertEqual(
            date.DateTime(2005, 2, 28), self.recur(date.DateTime(2004, 2, 28))
        )

    def test_february_28_year_before_leap_year(self):
        self.assertEqual(
            date.DateTime(2004, 2, 28), self.recur(date.DateTime(2003, 2, 28))
        )

    def test_february_29(self):
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

    def test_every_other_year(self):
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

    def test_first_tuesday_of_the_year(self):
        self.assertEqual(
            date.DateTime(2009, 1, 6), self.recur(date.DateTime(2008, 1, 1))
        )

    def test_first_wednesday_of_the_year(self):
        self.assertEqual(
            date.DateTime(2009, 1, 7), self.recur(date.DateTime(2008, 1, 2))
        )

    def test_first_thursday_of_the_year(self):
        self.assertEqual(
            date.DateTime(2009, 1, 1), self.recur(date.DateTime(2008, 1, 3))
        )

    def test_first_friday_of_the_year(self):
        self.assertEqual(
            date.DateTime(2009, 1, 2), self.recur(date.DateTime(2008, 1, 4))
        )

    def test_last_wednesday_of_the_year(self):
        self.assertEqual(
            date.DateTime(2009, 12, 30),
            self.recur(date.DateTime(2008, 12, 31)),
        )

    def test_last_tuesday_of_the_year(self):
        self.assertEqual(
            date.DateTime(2009, 12, 29),
            self.recur(date.DateTime(2008, 12, 30)),
        )

    def test_last_monday_of_the_year(self):
        self.assertEqual(
            date.DateTime(2009, 12, 28),
            self.recur(date.DateTime(2008, 12, 29)),
        )

    def test_last_sunday_of_the_year(self):
        self.assertEqual(
            date.DateTime(2009, 12, 27),
            self.recur(date.DateTime(2008, 12, 28)),
        )

    def test_last_saturday_of_the_year(self):
        self.assertEqual(
            date.DateTime(2009, 12, 26),
            self.recur(date.DateTime(2008, 12, 27)),
        )

    def test_last_friday_of_the_year(self):
        self.assertEqual(
            date.DateTime(2009, 12, 25),
            self.recur(date.DateTime(2008, 12, 26)),
        )

    def test_last_thursday_of_the_year(self):
        self.assertEqual(
            date.DateTime(2009, 12, 24),
            self.recur(date.DateTime(2008, 12, 25)),
        )


class MaxRecurrenceTest(test.TestCase, CommonRecurrenceTestsMixin):
    def setUp(self):
        self.recur = date.Recurrence("daily", maximum=4)

    def test_first(self):
        self.assertEqual(
            date.DateTime(2000, 1, 2),
            self.recur(date.DateTime(2000, 1, 1), next=True),
        )

    def test_count_after_first(self):
        self.recur(date.DateTime(2000, 1, 1), next=True)
        self.assertEqual(1, self.recur.count)

    def test_last(self):
        self.recur.count = 4
        self.assertEqual(
            None, self.recur(date.DateTime(2000, 1, 1), next=True)
        )
