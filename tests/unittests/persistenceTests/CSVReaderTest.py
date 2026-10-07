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

import csv
import io
import os
import tempfile
import test
from unittest import mock
from taskcoachlib import persistence, config
from taskcoachlib.domain import task, category, date
from taskcoachlib.persistence.csv import reader as csv_reader

# What a French and a Japanese system's names are (glibc)
FRENCH = (
    list(
        zip(
            "janvier f\u00e9vrier mars avril mai juin juillet ao\u00fbt "
            "septembre octobre novembre d\u00e9cembre".split(),
            "janv. f\u00e9vr. mars avr. mai juin juil. ao\u00fbt sept. oct. "
            "nov. d\u00e9c.".split(),
        )
    ),
    ["", ""],
)
JAPANESE = (
    [("%d\u6708" % month,) * 2 for month in range(1, 13)],
    ["\u5348\u524d", "\u5348\u5f8c"],
)
GREEK_AMPM = ["\u03c0\u03bc", "\u03bc\u03bc"]


class CSVReaderTestCase(test.TestCase):
    def setUp(self):
        self.taskList = task.TaskList()
        self.categoryList = category.CategoryList()
        self.reader = persistence.CSVReader(self.taskList, self.categoryList)
        self.defaultReaderKwArgs = dict(
            encoding="utf-8",
            dialect="excel",
            hasHeaders=False,
            importSelectedRowsOnly=False,
            dayfirst=True,
        )

    def createCSVFile(self, contents):
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".csv", delete=False
        ) as tmp_file:
            tmp_file.write(contents)
        self.addCleanup(os.remove, tmp_file.name)
        return tmp_file.name

    def test_two_tasks_with_subject(self):
        filename = self.createCSVFile("Subject 1\nSubject 2\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            set(["Subject 1", "Subject 2"]),
            set([t.subject() for t in self.taskList]),
        )

    def test_two_tasks_with_subject_and_description(self):
        filename = self.createCSVFile(
            "Subject 1,Description 1\nSubject 2,Description 2\n"
        )
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Description"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            set(
                [
                    ("Subject 1", "Description 1\n"),
                    ("Subject 2", "Description 2\n"),
                ]
            ),
            set([(t.subject(), t.description()) for t in self.taskList]),
        )

    def test_task_with_planned_start_date(self):
        filename = self.createCSVFile("Subject,2011-6-30\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Planned start date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.DateTime(2011, 6, 30, 0, 0, 0),
            list(self.taskList)[0].plannedStartDateTime(),
        )

    def test_task_with_planned_start_date_time(self):
        filename = self.createCSVFile("Subject,2011-6-30 12:00\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Planned start date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.DateTime(2011, 6, 30, 12, 0, 0),
            list(self.taskList)[0].plannedStartDateTime(),
        )

    def test_task_with_empty_planned_start_date(self):
        filename = self.createCSVFile("Subject,\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Planned start date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.DateTime(), list(self.taskList)[0].plannedStartDateTime()
        )

    def test_task_with_actual_start_date(self):
        filename = self.createCSVFile("Subject,2011-6-30\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Actual start date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.DateTime(2011, 6, 30, 0, 0, 0),
            list(self.taskList)[0].actualStartDateTime(),
        )

    def test_task_with_actual_start_date_time(self):
        filename = self.createCSVFile("Subject,2011-6-30 12:00\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Actual start date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.DateTime(2011, 6, 30, 12, 0, 0),
            list(self.taskList)[0].actualStartDateTime(),
        )

    def test_task_with_empty_actual_start_date(self):
        filename = self.createCSVFile("Subject,\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Actual start date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.DateTime(), list(self.taskList)[0].actualStartDateTime()
        )

    def test_task_with_due_date(self):
        filename = self.createCSVFile("Subject,2011-6-30\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Due date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.DateTime(2011, 6, 30, 23, 59, 59),
            list(self.taskList)[0].dueDateTime(),
        )

    def test_task_with_due_date_time(self):
        filename = self.createCSVFile("Subject,2011-6-30 1:34:01 pm\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Due date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.DateTime(2011, 6, 30, 13, 34, 1),
            list(self.taskList)[0].dueDateTime(),
        )

    def test_task_with_completion_date(self):
        filename = self.createCSVFile("Subject,2011-6-30\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Completion date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.DateTime(2011, 6, 30, 12, 0, 0),
            list(self.taskList)[0].completionDateTime(),
        )

    def test_task_with_completion_date_time(self):
        filename = self.createCSVFile("Subject,1:33 am 2011-6-30\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Completion date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.DateTime(2011, 6, 30, 1, 33, 0),
            list(self.taskList)[0].completionDateTime(),
        )

    def test_task_with_reminder_date(self):
        filename = self.createCSVFile("Subject,2012-6-30\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Reminder date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.DateTime(2012, 6, 30, 0, 0, 0),
            list(self.taskList)[0].reminder(),
        )

    def test_task_with_reminder_date_time(self):
        filename = self.createCSVFile("Subject,12:31 2012-6-30\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Reminder date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.DateTime(2012, 6, 30, 12, 31, 0),
            list(self.taskList)[0].reminder(),
        )

    def test_task_with_hour_minute_budget(self):
        filename = self.createCSVFile("Subject,60:30\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Budget"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.TimeDelta(hours=60, minutes=30, seconds=0),
            list(self.taskList)[0].budget(),
        )

    def test_task_with_hour_minute_second_budget(self):
        filename = self.createCSVFile("Subject,60:30:15\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Budget"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.TimeDelta(hours=60, minutes=30, seconds=15),
            list(self.taskList)[0].budget(),
        )

    def test_task_with_float_budget(self):
        filename = self.createCSVFile("Subject,1.5\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Budget"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.TimeDelta(hours=1, minutes=30, seconds=0),
            list(self.taskList)[0].budget(),
        )

    def test_task_with_fixed_fee(self):
        filename = self.createCSVFile("Subject,1600\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Fixed fee"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(1600, list(self.taskList)[0].fixedFee())

    def test_task_with_hourly_fee(self):
        filename = self.createCSVFile("Subject,160\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Hourly fee"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(160, list(self.taskList)[0].hourlyFee())

    def test_task_with_50_percent_complete(self):
        filename = self.createCSVFile("Subject,50\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Percent complete"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(50, list(self.taskList)[0].percentageComplete())

    def test_task_with_100_percent_complete(self):
        filename = self.createCSVFile("Subject,100\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Percent complete"},
            **self.defaultReaderKwArgs
        )
        new_task = list(self.taskList)[0]
        self.assertEqual(100, new_task.percentageComplete())
        self.assertTrue(new_task.completed())

    def test_two_tasks_with_priority(self):
        filename = self.createCSVFile("Subject 1,123\nSubject 2,-3")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Priority"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            set([("Subject 1", 123), ("Subject 2", -3)]),
            set([(t.subject(), t.priority()) for t in self.taskList]),
        )

    def test_two_tasks_with_the_same_category(self):
        filename = self.createCSVFile(
            "Subject 1,Category\nSubject 2,Category\n"
        )
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Category"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(1, len(self.categoryList))
        new_category = list(self.categoryList)[0]
        self.assertEqual(
            [set([new_category]), set([new_category])],
            [t.categories() for t in self.taskList],
        )

    def test_two_tasks_with_category_and_subcategory(self):
        filename = self.createCSVFile(
            "Subject 1,Category -> Subcategory\nSubject 2,Category\n"
        )
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Category"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(2, len(self.categoryList))
        parent_category = [c for c in self.categoryList if not c.parent()][0]
        child_category = parent_category.children()[0]
        self.assertEqual(
            "Subject 1", list(child_category.members())[0].subject()
        )
        self.assertEqual(
            "Subject 2", list(parent_category.members())[0].subject()
        )

    def test_hierarchy(self):
        filename = self.createCSVFile(
            "Subject 1,1\nSubject 1.1,1.1\nSubject 1.2,1.2\n"
        )
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "ID"},
            **self.defaultReaderKwArgs
        )
        parent = [t for t in self.taskList if not t.parent()][0]
        self.assertEqual(2, len(parent.children()))

    def test_day_first_dates(self):
        filename = self.createCSVFile("T1,30-6-2011\nT2,1-1-2011\nT3,4-4-2011")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Due date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            set([1, 4, 6]), set(t.dueDateTime().month for t in self.taskList)
        )

    def test_month_first_dates(self):
        filename = self.createCSVFile("T1,3-6-2011\nT2,1-1-2011\nT3,4-20-2011")
        self.defaultReaderKwArgs["dayfirst"] = False
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Due date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            set([1, 3, 4]), set(t.dueDateTime().month for t in self.taskList)
        )

    def test_year_first_dates_are_year_month_day(self):
        # Whatever the day-first choice (ISO 8601)
        filename = self.createCSVFile("T1,2026-10-02\nT2,2026/10/02 14:30")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Due date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            {(10, 2)},
            {
                (t.dueDateTime().month, t.dueDateTime().day)
                for t in self.taskList
            },
        )

    def due_dates(self, *texts, dayfirst=True, names=None):
        """Import one task per text as its due date: the due dates in
        order, with the system language's names given."""
        rows = io.StringIO()
        writer = csv.writer(rows)
        for index, text in enumerate(texts):
            writer.writerow(["T%02d" % index, text])
        filename = self.createCSVFile(rows.getvalue())
        self.defaultReaderKwArgs["dayfirst"] = dayfirst
        if names:
            with mock.patch.object(
                csv_reader, "_system_names", return_value=names
            ):
                self.reader = persistence.CSVReader(
                    self.taskList, self.categoryList
                )
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Due date"},
            **self.defaultReaderKwArgs
        )
        tasks = sorted(self.taskList, key=lambda t: t.subject())
        return [t.dueDateTime() for t in tasks]

    def test_month_name_in_the_system_language(self):
        self.assertEqual(
            [date.DateTime(2026, 3, 7, 23, 59, 59)] * 2,
            self.due_dates(
                "samedi, 07 mars 2026", "7 mars 2026", names=FRENCH
            ),
        )

    def test_month_name_in_another_language_imports_no_date(self):
        # Not 2026-07-03: the day as the month, today's day as the day
        self.assertEqual(
            [date.DateTime()], self.due_dates("samedi, 07 mars 2026")
        )

    def test_english_month_names_with_the_system_language(self):
        self.assertEqual(
            [date.DateTime(2026, 3, 7, 23, 59, 59)] * 2,
            self.due_dates("Mar 7, 2026", "7 March 2026", names=FRENCH),
        )

    def test_system_language_name_that_dateutil_reads_otherwise(self):
        # "mar" as May would make English "Mar" May
        names = [(name, name) for name in "jan feb march apr mar".split()]
        names += [("m%d" % month, "m%d" % month) for month in range(6, 13)]
        self.assertEqual(
            [date.DateTime(2026, 3, 7, 23, 59, 59)],
            self.due_dates("Mar 7, 2026", names=(names, ["", ""])),
        )

    def test_am_pm_in_the_system_language(self):
        self.assertEqual(
            [date.DateTime(2026, 10, 23, 14, 30)],
            self.due_dates(
                "23/10/2026 02:30 \u03bc\u03bc",
                names=(FRENCH[0], GREEK_AMPM),
            ),
        )

    def test_own_abbreviated_form_in_the_system_language(self):
        # "mar." is Tuesday in French and March in English
        self.assertEqual(
            [
                date.DateTime(2026, 3, 7, 23, 59, 59),
                date.DateTime(2026, 1, 6, 9, 5),
            ],
            self.due_dates(
                "2026-mars-07-sam.", "2026-janv.-06-mar. 09:05", names=FRENCH
            ),
        )

    def test_own_abbreviated_form_with_a_numbered_month(self):
        self.assertEqual(
            [date.DateTime(2026, 1, 2, 14, 30)],
            self.due_dates(
                "2026- 1\u6708-02-\u91d1 02:30 \u5348\u5f8c",
                names=JAPANESE,
            ),
        )

    def test_date_without_day_or_month_imports_no_date(self):
        self.assertEqual(
            [date.DateTime()] * 5,
            self.due_dates(
                "5", "2:30 PM", "Oct 2026", "next Monday", "week 12"
            ),
        )

    def test_date_without_year_is_this_year(self):
        this_year = date.Now().year
        self.assertEqual(
            [date.DateTime(this_year, 10, 5, 23, 59, 59)],
            self.due_dates("5 Oct"),
        )

    def test_year_first_date_among_words(self):
        # Year-month-day although day first is chosen
        self.assertEqual(
            [date.DateTime(2026, 10, 5, 23, 59, 59)],
            self.due_dates("Due: 2026-10-05"),
        )

    def test_date_among_words(self):
        self.assertEqual(
            [date.DateTime(2026, 10, 5, 23, 59, 59)],
            self.due_dates("around Oct 5, 2026", dayfirst=False),
        )

    def test_too_long_number_imports_no_date(self):
        self.assertEqual(
            [date.DateTime(), date.DateTime(2026, 10, 5, 23, 59, 59)],
            self.due_dates("99999999999999999999", "2026-10-05"),
        )
