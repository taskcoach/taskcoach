"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2026 Task Coach developers <developers@taskcoach.org>

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

import datetime
import test
from taskcoachlib.domain.date import timeexpression

# A Saturday evening
NOW = datetime.datetime(2026, 10, 3, 20, 26, 17)

# What the pyparsing grammar used before gave at NOW: its own examples,
# then the forms Task Coach writes and the Help shows
AS_BEFORE = [
    ("today", (2026, 10, 3, 0, 0, 0)),
    ("tomorrow", (2026, 10, 4, 0, 0, 0)),
    ("yesterday", (2026, 10, 2, 0, 0, 0)),
    ("in a couple of days", (2026, 10, 5, 0, 0, 0)),
    ("a couple of days from now", (2026, 10, 5, 20, 26, 17)),
    ("a couple of days from today", (2026, 10, 5, 0, 0, 0)),
    ("in a day", (2026, 10, 4, 0, 0, 0)),
    ("3 days ago", (2026, 9, 30, 0, 0, 0)),
    ("3 days from now", (2026, 10, 6, 20, 26, 17)),
    ("a day ago", (2026, 10, 2, 0, 0, 0)),
    ("now", (2026, 10, 3, 20, 26, 17)),
    ("10 minutes ago", (2026, 10, 3, 20, 16, 17)),
    ("10 minutes from now", (2026, 10, 3, 20, 36, 17)),
    ("in 10 minutes", (2026, 10, 3, 20, 36, 17)),
    ("in a minute", (2026, 10, 3, 20, 27, 17)),
    ("in a couple of minutes", (2026, 10, 3, 20, 28, 17)),
    ("20 seconds ago", (2026, 10, 3, 20, 25, 57)),
    ("in 30 seconds", (2026, 10, 3, 20, 26, 47)),
    ("20 seconds before noon", (2026, 10, 3, 11, 59, 40)),
    ("20 seconds before noon tomorrow", (2026, 10, 4, 11, 59, 40)),
    ("noon", (2026, 10, 3, 12, 0, 0)),
    ("midnight", (2026, 10, 3, 0, 0, 0)),
    ("noon tomorrow", (2026, 10, 4, 12, 0, 0)),
    ("6am tomorrow", (2026, 10, 4, 6, 0, 0)),
    ("0800 yesterday", (2026, 10, 2, 8, 0, 0)),
    ("12:15 AM today", (2026, 10, 3, 0, 15, 0)),
    ("3pm 2 days from today", (2026, 10, 5, 15, 0, 0)),
    ("a week from today", (2026, 10, 10, 0, 0, 0)),
    ("a week from now", (2026, 10, 10, 20, 26, 17)),
    ("3 weeks ago", (2026, 9, 12, 0, 0, 0)),
    ("noon next Sunday", (2026, 10, 4, 12, 0, 0)),
    ("noon Sunday", (2026, 10, 4, 12, 0, 0)),
    ("noon last Sunday", (2026, 9, 27, 12, 0, 0)),
    ("2pm next Sunday", (2026, 10, 4, 14, 0, 0)),
    ("next Sunday at 2pm", (2026, 10, 4, 14, 0, 0)),
    ("1861 minutes from now", (2026, 10, 5, 3, 27, 17)),
    ("4 minutes ago", (2026, 10, 3, 20, 22, 17)),
    ("11:59 PM today", (2026, 10, 3, 23, 59, 0)),
    ("11:59 PM tomorrow", (2026, 10, 4, 23, 59, 0)),
    ("00:00 AM today", (2026, 10, 3, 0, 0, 0)),
    ("3 pm tomorrow", (2026, 10, 4, 15, 0, 0)),
    ("next saturday", (2026, 10, 10, 0, 0, 0)),
    ("last saturday", (2026, 9, 26, 0, 0, 0)),
    ("saturday", (2026, 10, 3, 0, 0, 0)),
    ("twenty-one minutes ago", (2026, 10, 3, 20, 5, 17)),
    ("just 3 days ago", (2026, 9, 30, 0, 0, 0)),
    ("the day after tomorrow", (2026, 10, 5, 0, 0, 0)),
    ("TOMORROW", (2026, 10, 4, 0, 0, 0)),
    ("1200 hours ago", (2026, 8, 14, 20, 26, 17)),
    ("3 o'clock pm", (2026, 10, 3, 15, 0, 0)),
    ("9:05:30 am", (2026, 10, 3, 9, 5, 30)),
]


class TimeExpressionTest(test.TestCase):
    def parse(self, text):
        return timeexpression.parse(text, NOW)

    def assert_parses(self, expected, text):
        self.assertEqual(datetime.datetime(*expected), self.parse(text), text)

    def test_as_before(self):
        for text, expected in AS_BEFORE:
            self.assert_parses(expected, text)

    def test_days_before_a_weekday(self):
        # P171: the grammar took the weekday's direction for "before"
        self.assert_parses((2026, 10, 2, 0, 0, 0), "2 days before sunday")
        self.assert_parses((2026, 10, 2, 0, 0, 0), "2 days before next sunday")

    def test_days_after_or_from_last_weekday(self):
        # P171: the grammar went back from the last weekday
        self.assert_parses((2026, 9, 29, 0, 0, 0), "2 days after last sunday")
        self.assert_parses((2026, 10, 9, 0, 0, 0), "1 week from last friday")

    def test_english_weekdays_whatever_the_system_language(self):
        # P172: the grammar took the locale's names (calendar.day_name)
        self.assert_parses((2026, 10, 10, 0, 0, 0), "next saturday")
        self.assertRaises(ValueError, self.parse, "next samedi")

    def test_the_expression_at_the_start_of_the_text(self):
        # As before: the rest is ignored (P170)
        self.assert_parses((2026, 10, 4, 0, 0, 0), "tomorrow at 15:00")

    def test_no_expression(self):
        for text in ("", "banana", "15:00", "next week", "10minutes ago"):
            self.assertRaises(ValueError, self.parse, text)

    def test_no_such_time(self):
        self.assertRaises(ValueError, self.parse, "3:75 pm")

    def test_out_of_range(self):
        self.assertRaises(ValueError, self.parse, "99999999 weeks from now")

    def test_now_by_default(self):
        before = datetime.datetime.now().replace(microsecond=0)
        self.assertTrue(before <= timeexpression.parse("now"))
