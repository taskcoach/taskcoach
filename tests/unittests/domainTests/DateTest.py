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
import datetime
from taskcoachlib.domain import date


class DateTest(test.TestCase):
    def test_create_normal_date(self):
        adate = date.Date(2003, 1, 1)
        self.assertEqual(2003, adate.year)
        self.assertEqual(1, adate.month)
        self.assertEqual(1, adate.day)
        self.assertEqual("2003-01-01", str(adate))

    def test_create_invalid_date(self):
        self.assertRaises(ValueError, date.Date, 2003, 2, 31)
        self.assertRaises(ValueError, date.Date, 2003, 12, 32)
        self.assertRaises(ValueError, date.Date, 2003, 13, 1)
        self.assertRaises(ValueError, date.Date, 2003, 2, -1)
        self.assertRaises(ValueError, date.Date, 2003, 2, 0)

    def test_create_infinite_date(self):
        adate = date.Date()
        self.assertEqual(None, adate.year)
        self.assertEqual(None, adate.month)
        self.assertEqual(None, adate.day)
        self.assertEqual("", str(adate))

    def test_create_infinite_date_with_max_values(self):
        max_date = datetime.date.max
        infinite = date.Date(max_date.year, max_date.month, max_date.day)
        self.assertTrue(infinite is date.Date())

    def test_infinite_date_is_singleton(self):
        self.assertTrue(date.Date() is date.Date())

    def test_add_time_delta_to_infinite_date(self):
        self.assertEqual(date.Date(), date.Date() + date.TimeDelta(days=2))

    def test_compare_two_infinite_dates(self):
        date1 = date.Date()
        date2 = date.Date()
        self.assertEqual(date1, date2)

    def test_compare_two_normal_dates(self):
        date1 = date.Date(2003, 1, 1)
        date2 = date.Date(2003, 4, 5)
        self.assertTrue(date1 < date2)
        self.assertTrue(date2 > date1)
        self.assertFalse(date1 == date2)

    def test_compare_one_normal_date(self):
        date1 = date.Date(2003, 1, 1)
        date2 = date.Date(2003, 1, 1)
        self.assertEqual(date1, date2)

    def test_compare_normal_date_with_infinite_date(self):
        date1 = date.Date()
        date2 = date.Date(2003, 1, 1)
        self.assertTrue(date2 < date1)
        self.assertTrue(date1 > date2)

    def test_add_many_days(self):
        self.assertEqual(
            date.Date(2003, 1, 1), date.Date(2002, 1, 1) + date.ONE_YEAR
        )

    def test_substract_two_dates_zero_difference(self):
        self.assertEqual(
            date.TimeDelta(), date.Date(2004, 2, 29) - date.Date(2004, 2, 29)
        )

    def test_substract_two_dates_year_difference(self):
        self.assertEqual(
            date.TimeDelta(days=365),
            date.Date(2004, 2, 29) + date.ONE_YEAR - date.Date(2004, 2, 29),
        )

    def test_substract_two_dates_infinite(self):
        self.assertEqual(
            date.TimeDelta.max, date.Date() - date.Date(2004, 2, 29)
        )

    def test_substract_two_dates_both_infinite(self):
        self.assertEqual(date.TimeDelta(), date.Date() - date.Date())

    def test_format_1900(self):
        self.assertEqual(
            date.DateTime(2, 5, 19, 0, 0, 0).strftime("%Y%m%d"), "20519"
        )
