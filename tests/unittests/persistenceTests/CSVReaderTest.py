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

import os
import tempfile
import test
from taskcoachlib import persistence, config
from taskcoachlib.domain import task, category, date


class CSVReaderTestCase(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
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

    def testTwoTasksWithSubject(self):
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

    def testTwoTasksWithSubjectAndDescription(self):
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

    def testTaskWithPlannedStartDate(self):
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

    def testTaskWithPlannedStartDateTime(self):
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

    def testTaskWithEmptyPlannedStartDate(self):
        filename = self.createCSVFile("Subject,\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Planned start date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.DateTime(), list(self.taskList)[0].plannedStartDateTime()
        )

    def testTaskWithActualStartDate(self):
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

    def testTaskWithActualStartDateTime(self):
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

    def testTaskWithEmptyActualStartDate(self):
        filename = self.createCSVFile("Subject,\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Actual start date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            date.DateTime(), list(self.taskList)[0].actualStartDateTime()
        )

    def testTaskWithDueDate(self):
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

    def testTaskWithDueDateTime(self):
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

    def testTaskWithCompletionDate(self):
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

    def testTaskWithCompletionDateTime(self):
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

    def testTaskWithReminderDate(self):
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

    def testTaskWithReminderDateTime(self):
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

    def testTaskWithHourMinuteBudget(self):
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

    def testTaskWithHourMinuteSecondBudget(self):
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

    def testTaskWithFloatBudget(self):
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

    def testTaskWithFixedFee(self):
        filename = self.createCSVFile("Subject,1600\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Fixed fee"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(1600, list(self.taskList)[0].fixedFee())

    def testTaskWithHourlyFee(self):
        filename = self.createCSVFile("Subject,160\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Hourly fee"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(160, list(self.taskList)[0].hourlyFee())

    def testTaskWith50PercentComplete(self):
        filename = self.createCSVFile("Subject,50\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Percent complete"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(50, list(self.taskList)[0].percentageComplete())

    def testTaskWith100PercentComplete(self):
        filename = self.createCSVFile("Subject,100\n")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Percent complete"},
            **self.defaultReaderKwArgs
        )
        newTask = list(self.taskList)[0]
        self.assertEqual(100, newTask.percentageComplete())
        self.assertTrue(newTask.completed())

    def testTwoTasksWithPriority(self):
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

    def testTwoTasksWithTheSameCategory(self):
        filename = self.createCSVFile(
            "Subject 1,Category\nSubject 2,Category\n"
        )
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Category"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(1, len(self.categoryList))
        newCategory = list(self.categoryList)[0]
        self.assertEqual(
            [set([newCategory]), set([newCategory])],
            [t.categories() for t in self.taskList],
        )

    def testTwoTasksWithCategoryAndSubcategory(self):
        filename = self.createCSVFile(
            "Subject 1,Category -> Subcategory\nSubject 2,Category\n"
        )
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Category"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(2, len(self.categoryList))
        parentCategory = [c for c in self.categoryList if not c.parent()][0]
        childCategory = parentCategory.children()[0]
        self.assertEqual(
            "Subject 1", list(childCategory.categorizables())[0].subject()
        )
        self.assertEqual(
            "Subject 2", list(parentCategory.categorizables())[0].subject()
        )

    def testHierarchy(self):
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

    def testDayFirstDates(self):
        filename = self.createCSVFile("T1,30-6-2011\nT2,1-1-2011\nT3,4-4-2011")
        self.reader.read(
            filename=filename,
            mappings={0: "Subject", 1: "Due date"},
            **self.defaultReaderKwArgs
        )
        self.assertEqual(
            set([1, 4, 6]), set(t.dueDateTime().month for t in self.taskList)
        )

    def testMonthFirstDates(self):
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
