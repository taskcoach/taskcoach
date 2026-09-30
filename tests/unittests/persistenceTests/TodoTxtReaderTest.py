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

import test, io
from taskcoachlib import persistence, config
from taskcoachlib.domain import task, category, date


class TodoTxtReaderTestCase(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.tasks = task.TaskList()
        self.categories = category.CategoryList()
        self.reader = persistence.TodoTxtReader(self.tasks, self.categories)

    def read(self, text, **kwargs):
        self.reader.readFile(io.StringIO(text), **kwargs)

    def assertTaskSubject(self, *subjects):
        self.assertEqual(set(subjects), set(t.subject() for t in self.tasks))

    def assertCategorySubject(self, *subjects):
        self.assertEqual(
            set(subjects), set(c.subject() for c in self.categories)
        )

    def assertPriority(self, priority):
        self.assertEqual(priority, list(self.tasks)[0].priority())

    def assertStartDate(self, *dateTimeArgs):
        self.assertEqual(
            date.DateTime(*dateTimeArgs),
            list(self.tasks)[0].plannedStartDateTime(),
        )

    def assertCompletionDate(self, *dateTimeArgs, **kwargs):
        expectedDateTime = (
            kwargs["dateTime"]
            if "dateTime" in kwargs
            else date.DateTime(*dateTimeArgs)
        )
        self.assertEqual(
            expectedDateTime, list(self.tasks)[0].completionDateTime()
        )

    def assertDueDate(self, *dateTimeArgs):
        self.assertEqual(
            date.DateTime(*dateTimeArgs), list(self.tasks)[0].dueDateTime()
        )

    def assertTaskIsCompleted(self):
        self.assertTrue(list(self.tasks)[0].completed())

    def testEmptyFile(self):
        self.reader.readFile(io.StringIO())
        self.assertFalse(self.tasks)

    def testReadOneTask(self):
        self.read("Get milk\n")
        self.assertTaskSubject("Get milk")

    def testReadTwoTasks(self):
        self.read("Get milk\nDo laundry\n")
        self.assertTaskSubject("Get milk", "Do laundry")

    def testTaskWithPriority(self):
        self.read("(A) Get milk\n")
        self.assertPriority(1)
        self.assertTaskSubject("Get milk")

    def testTaskWithStartDate(self):
        self.read("2011-01-31 Get milk\n")
        self.assertStartDate(2011, 1, 31)

    def testTaskWithStartDateWithoutLeadingZero(self):
        self.read("2011-1-31 Get milk\n")
        self.assertStartDate(2011, 1, 31)

    def testTaskWithPriorityAndStartDate(self):
        self.read("(Z) 2011-01-31 Get milk\n")
        self.assertPriority(26)
        self.assertStartDate(2011, 1, 31)

    def testCompletedTaskWithoutCompletionDate(self):
        now = date.Now()
        self.read("x Do dishes\n", now=lambda: now)
        self.assertTaskIsCompleted()
        self.assertCompletionDate(dateTime=now)

    def testCompletedTaskWithCompletionDate(self):
        self.read("X 2011-02-22 Do dishes\n")
        self.assertTaskIsCompleted()
        self.assertCompletionDate(2011, 2, 22)

    def testTaskWithStartAndCompletionDate(self):
        self.read("X 2011-2-22 2011-2-21 Do dishes\n")
        self.assertTaskIsCompleted()
        self.assertCompletionDate(2011, 2, 22)
        self.assertStartDate(2011, 2, 21)

    def testTaskWithSimpleContext(self):
        self.read("Order pizza @phone\n")
        self.assertCategorySubject(("@phone"))
        phone = list(self.categories)[0]
        pizza = list(self.tasks)[0]
        self.assertEqual(set([pizza]), phone.members())
        self.assertEqual(set([phone]), pizza.categories())

    def testTaskWithSimpleProject(self):
        self.read("Order pizza +phone\n")
        self.assertCategorySubject(("+phone"))
        phone = list(self.categories)[0]
        pizza = list(self.tasks)[0]
        self.assertEqual(set([pizza]), phone.members())
        self.assertEqual(set([phone]), pizza.categories())

    def testTaskWithPlusSign(self):
        self.read("Order pizza + drink\n")
        self.assertTaskSubject("Order pizza + drink")
        self.assertFalse(self.categories)

    def testTaskWithAtSign(self):
        self.read("Mail frank@niessink.com\n")
        self.assertTaskSubject("Mail frank@niessink.com")
        self.assertFalse(self.categories)

    def testTwoTasksWithTheSameContext(self):
        self.read("Order pizza @phone\nCall mom @phone\n")
        self.assertEqual(1, len(self.categories))
        phone = list(self.categories)[0]
        self.assertEqual(set(self.tasks), phone.members())
        self.assertEqual(
            [set([phone]), set([phone])], [t.categories() for t in self.tasks]
        )

    def testTaskWithSubcategoryAsContext(self):
        self.read("Order pizza @home->phone\n")
        home = [c for c in self.categories if not c.parent()][0]
        self.assertEqual("@home", home.subject())
        phone = home.children()[0]
        self.assertEqual("phone", phone.subject())
        pizza = list(self.tasks)[0]
        self.assertEqual(set([pizza]), phone.members())
        self.assertEqual(set([phone]), pizza.categories())

    def testTwoTasksWithTheSameSubcategory(self):
        self.read("Order pizza @home->phone\nOrder flowers @home->phone\n")
        home = [c for c in self.categories if not c.parent()][0]
        self.assertEqual("@home", home.subject())
        phone = home.children()[0]
        self.assertEqual("phone", phone.subject())
        self.assertEqual(set(self.tasks), phone.members())
        for eachTask in self.tasks:
            self.assertEqual(set([phone]), eachTask.categories())

    def testTaskWithMultipleContexts(self):
        self.read("Order pizza @phone @food\n")
        self.assertEqual(2, len(self.categories))
        pizza = list(self.tasks)[0]
        self.assertEqual(set(self.categories), pizza.categories())

    def testContextBeforeTask(self):
        self.read("@phone Order pizza\n")
        self.assertEqual(1, len(self.categories))

    def testProjectBeforeTask(self):
        self.read("+phone Order pizza\n")
        self.assertEqual(1, len(self.categories))

    def testPriorityAndContextBeforeTask(self):
        self.read("(A) @phone thank Mom for the meatballs")
        self.assertEqual(1, len(self.categories))
        self.assertCategorySubject("@phone")
        phone = list(self.categories)[0]
        thankMom = list(self.tasks)[0]
        self.assertEqual(set([thankMom]), phone.members())
        self.assertEqual(set([phone]), thankMom.categories())

    def testPriorityAndProjectAndContextBeforeTask(self):
        self.read("(B) +GarageSale @phone schedule Goodwill pickup")
        self.assertEqual(2, len(self.categories))

    def testAutomaticallyCreateParentTask(self):
        self.read("Project->Activity")
        self.assertEqual(2, len(self.tasks))
        parent = [t for t in self.tasks if not t.parent()][0]
        self.assertEqual("Project", parent.subject())
        self.assertEqual("Activity", parent.children()[0].subject())

    def testAutomaticallyCreateParentTask_WithSpaces(self):
        self.read("Project -> Activity")
        self.assertEqual(2, len(self.tasks))
        parent = [t for t in self.tasks if not t.parent()][0]
        self.assertEqual("Project", parent.subject())
        self.assertEqual("Activity", parent.children()[0].subject())

    def testFirstChildAndThenParent(self):
        self.read("Project->Activity\nProject\n")
        self.assertEqual(2, len(self.tasks))
        parent = [t for t in self.tasks if not t.parent()][0]
        self.assertEqual("Project", parent.subject())
        self.assertEqual("Activity", parent.children()[0].subject())

    def testIgnoreEmptyLine(self):
        self.read("\n")
        self.assertFalse(self.tasks)

    def testDueDate(self):
        self.read("Import due date due:2011-03-05\n")
        self.assertEqual("Import due date", list(self.tasks)[0].subject())
        self.assertEqual(
            date.DateTime(2011, 3, 5, 0, 0, 0),
            list(self.tasks)[0].dueDateTime(),
        )

    def testDueDateBeforeProject(self):
        self.read("Import due date due:2011-03-05 +TaskCoach\n")
        self.assertTaskSubject("Import due date")
        self.assertDueDate(2011, 3, 5)
        self.assertCategorySubject("+TaskCoach")

    def testTrailingJunk(self):
        taskWithJunk = "Test +this_is_not_a_project due to trailing junk"
        self.read(taskWithJunk)
        self.assertTaskSubject(taskWithJunk)
