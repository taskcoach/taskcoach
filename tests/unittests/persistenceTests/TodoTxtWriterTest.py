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

import test, io
from taskcoachlib import persistence, config, gui
from taskcoachlib.domain import task, category, date


class TodoTxtWriterTestCase(test.wxTestCase):
    def setUp(self):
        self.settings = config.settings.current()
        self.file = io.StringIO()
        self.writer = persistence.TodoTxtWriter(self.file, "whatever.tsk")
        self.settings.set("taskviewer", "treemode", "False")
        self.taskFile = persistence.TaskFile()
        self.viewer = gui.viewer.TaskViewer(
            self.frame, self.taskFile, self.settings
        )

    def testNoTasksAndCategories(self):
        self.writer.write(self.viewer, False)
        self.assertEqual("", self.file.getvalue())

    def testOneTask(self):
        theTask = task.Task(subject="Get cheese")
        self.taskFile.tasks().append(theTask)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "Get cheese tcid:%s\n" % theTask.id(), self.file.getvalue()
        )

    def testTwoTasks(self):
        theTask1 = task.Task(subject="Get cheese")
        theTask2 = task.Task(subject="Paint house")
        self.taskFile.tasks().append(theTask1)
        self.taskFile.tasks().append(theTask2)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "Get cheese tcid:%s\nPaint house tcid:%s\n"
            % (theTask1.id(), theTask2.id()),
            self.file.getvalue(),
        )

    def testNonAsciiSubject(self):
        theTask = task.Task(subject="Call Jérôme")
        self.taskFile.tasks().append(theTask)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "Call Jérôme tcid:%s\n" % theTask.id(), self.file.getvalue()
        )

    def testSorting(self):
        theTask1 = task.Task(subject="Get cheese")
        theTask2 = task.Task(subject="Paint house")
        self.taskFile.tasks().append(theTask1)
        self.taskFile.tasks().append(theTask2)
        self.viewer.sortBy("subject")
        self.viewer.setSortOrderAscending(False)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "Paint house tcid:%s\nGet cheese tcid:%s\n"
            % (theTask2.id(), theTask1.id()),
            self.file.getvalue(),
        )

    def testTaskPriorityIsWrittenAsLetter(self):
        theTask = task.Task(subject="Get cheese", priority=1)
        self.taskFile.tasks().append(theTask)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "(A) Get cheese tcid:%s\n" % theTask.id(), self.file.getvalue()
        )

    def testTaskPriorityHigherThanZIsIgnored(self):
        theTask = task.Task(subject="Get cheese", priority=27)
        self.taskFile.tasks().append(theTask)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "Get cheese tcid:%s\n" % theTask.id(), self.file.getvalue()
        )

    def testStartDate(self):
        theTask = task.Task(
            subject="Get cheese",
            plannedStartDateTime=date.DateTime(2027, 1, 23, 15, 34, 12),
        )
        self.taskFile.tasks().append(theTask)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "2027-01-23 Get cheese tcid:%s\n" % theTask.id(),
            self.file.getvalue(),
        )

    def testCompletionDate(self):
        theTask = task.Task(
            subject="Get cheese",
            completionDateTime=date.DateTime(2027, 1, 23, 15, 34, 12),
        )
        self.taskFile.tasks().append(theTask)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "X 2027-01-23 Get cheese tcid:%s\n" % theTask.id(),
            self.file.getvalue(),
        )

    def testContext(self):
        phone = category.Category(subject="@phone")
        self.taskFile.categories().append(phone)
        pizza = task.Task(subject="Order pizza")
        self.taskFile.tasks().append(pizza)
        pizza.addCategory(phone)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "Order pizza @phone tcid:%s\n" % pizza.id(), self.file.getvalue()
        )

    def testContextWithSpaces(self):
        at_home = category.Category(subject="@at home")
        self.taskFile.categories().append(at_home)
        dishes = task.Task(subject="Do dishes")
        self.taskFile.tasks().append(dishes)
        dishes.addCategory(at_home)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "Do dishes @at_home tcid:%s\n" % dishes.id(), self.file.getvalue()
        )

    def testSubcontext(self):
        work = category.Category(subject="@Work")
        staff_meeting = category.Category(subject="Staff meeting")
        work.addChild(staff_meeting)
        self.taskFile.categories().append(work)
        discuss_proposal = task.Task(subject="Discuss the proposal")
        self.taskFile.tasks().append(discuss_proposal)
        discuss_proposal.addCategory(staff_meeting)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "Discuss the proposal @Work->Staff_meeting tcid:%s\n"
            % discuss_proposal.id(),
            self.file.getvalue(),
        )

    def testMultipleContexts(self):
        phone = category.Category(subject="@phone")
        food = category.Category(subject="@food")
        self.taskFile.categories().extend([phone, food])
        pizza = task.Task(subject="Order pizza")
        self.taskFile.tasks().append(pizza)
        pizza.addCategory(phone)
        pizza.addCategory(food)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "Order pizza @food @phone tcid:%s\n" % pizza.id(),
            self.file.getvalue(),
        )

    def testProject(self):
        alive = category.Category(subject="+Stay alive")
        self.taskFile.categories().append(alive)
        pizza = task.Task(subject="Order pizza")
        self.taskFile.tasks().append(pizza)
        pizza.addCategory(alive)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "Order pizza +Stay_alive tcid:%s\n" % pizza.id(),
            self.file.getvalue(),
        )

    def testIgnoreCategoriesThatAreNotAContextNorAProject(self):
        phone = category.Category(subject="phone")
        self.taskFile.categories().append(phone)
        pizza = task.Task(subject="Order pizza")
        self.taskFile.tasks().append(pizza)
        pizza.addCategory(phone)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "Order pizza tcid:%s\n" % pizza.id(), self.file.getvalue()
        )

    def testSubtask(self):
        self.viewer.sortBy("subject")
        self.viewer.setSortOrderAscending()
        project = task.Task(subject="Project")
        activity = task.Task(subject="Some activity")
        project.addChild(activity)
        self.taskFile.tasks().append(project)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "Project tcid:%s\nProject -> Some activity tcid:%s\n"
            % (project.id(), activity.id()),
            self.file.getvalue(),
        )

    def testTaskWithDueDate(self):
        theTask = task.Task(
            subject="Export due date",
            dueDateTime=date.DateTime(2011, 1, 1, 16, 50, 10),
        )
        self.taskFile.tasks().append(theTask)
        self.writer.write(self.viewer, False)
        self.assertEqual(
            "Export due date due:2011-01-01 tcid:%s\n" % theTask.id(),
            self.file.getvalue(),
        )

    def testExportSelectionOnly(self):
        cheese = task.Task(subject="Get cheese")
        self.taskFile.tasks().append(cheese)
        self.taskFile.tasks().append(task.Task(subject="Paint house"))
        self.viewer.select([cheese])
        self.writer.write(self.viewer, self.settings, True)
        self.assertEqual(
            "Get cheese tcid:%s\n" % cheese.id(), self.file.getvalue()
        )
