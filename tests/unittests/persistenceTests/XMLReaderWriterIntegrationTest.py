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

import io, wx
import test
from taskcoachlib import persistence
from taskcoachlib import config
from taskcoachlib.domain import task, category, effort, date, note, attachment


class IntegrationTestCase(test.TestCase):
    def setUp(self):
        self.fd = io.BytesIO()  # The app writes UTF-8 bytes (SafeWriteFile)
        self.fd.name = "testfile.tsk"
        self.writer = persistence.XMLWriter(self.fd)
        self.taskList = task.TaskList()
        self.categories = category.CategoryList()
        self.notes = note.NoteContainer()
        self.fillContainers()
        tasks, categories, notes = self.readAndWrite()
        self.tasksWrittenAndRead = task.TaskList(tasks)
        self.categoriesWrittenAndRead = category.CategoryList(categories)
        self.notesWrittenAndRead = note.NoteContainer(notes)

    def fillContainers(self):
        pass

    def readAndWrite(self):
        self.fd.seek(0)
        self.writer.write(
            self.taskList,
            self.categories,
            self.notes,
        )
        # The app reads the file back as text (TaskFile._openForRead)
        written = io.BytesIO(self.fd.getvalue())
        written.name = self.fd.name
        return persistence.XMLReader(
            io.TextIOWrapper(written, encoding="utf-8")
        ).read()


class IntegrationTest_EmptyList(IntegrationTestCase):
    def test_empty_task_list(self):
        self.assertEqual([], self.tasksWrittenAndRead)

    def test_no_categories(self):
        self.assertEqual([], self.categoriesWrittenAndRead)


class IntegrationTest(IntegrationTestCase):
    def fillContainers(self):
        # pylint: disable=W0201
        self.description = "Description\nLine 2"
        self.task = task.Task(
            subject="Subject",
            description=self.description,
            plannedStartDateTime=date.Yesterday(),
            dueDateTime=date.Tomorrow(),
            actualStartDateTime=date.Now() - date.TimeDelta(hours=4),
            completionDateTime=date.Yesterday(),
            budget=date.ONE_HOUR,
            priority=4,
            hourlyFee=100.5,
            fixedFee=1000,
            recurrence=date.Recurrence(
                "weekly",
                maximum=10,
                count=5,
                amount=2,
                stop_datetime=date.Now(),
            ),
            reminder=date.DateTime(2004, 1, 1),
            fgColor=wx.BLUE,
            bgColor=wx.RED,
            font=wx.NORMAL_FONT,
            expandedContexts=["viewer1"],
            icon="icon",
            percentageComplete=67,
            shouldMarkCompletedWhenAllChildrenCompleted=True,
        )
        self.child = task.Task()
        self.task.addChild(self.child)
        self.grandChild = task.Task()
        self.child.addChild(self.grandChild)
        self.task.addEffort(
            effort.Effort(
                self.task,
                start=date.DateTime(2004, 1, 1),
                stop=date.DateTime(2004, 1, 2),
                description=self.description,
            )
        )
        self.category = category.Category(
            "test",
            [self.task],
            filtered=True,
            description="Description",
            exclusiveSubcategories=True,
        )
        self.categories.append(self.category)
        # pylint: disable=E1101
        self.task.addAttachments(
            attachment.FileAttachment("/home/frank/whatever.txt")
        )
        self.task.addNote(note.Note(subject="Task note"))
        self.task2 = task.Task("Task 2", priority=-1954)
        self.taskList.extend([self.task, self.task2])
        self.note = note.Note(
            subject="Note",
            description="Description",
            children=[note.Note(subject="Child")],
        )
        self.notes.append(self.note)
        self.note.addCategory(self.category)
        self.task.set_modification_datetime(
            date.DateTime(2012, 1, 1, 10, 9, 8)
        )

    def getTaskWrittenAndRead(self, target_id):
        # pylint: disable=W0621
        return [
            task for task in self.tasksWrittenAndRead if task.id() == target_id
        ][0]

    def assertAttributeWrittenAndRead(self, a_task, attribute):
        task_written_and_read = self.getTaskWrittenAndRead(a_task.id())
        self.assertEqual(
            getattr(a_task, attribute)(),
            getattr(task_written_and_read, attribute)(),
        )

    def assertContainedDomainObjectsWrittenAndRead(self, a_task, attribute):
        task_written_and_read = self.getTaskWrittenAndRead(a_task.id())
        self.assertEqual(
            [obj.id() for obj in getattr(a_task, attribute)()],
            [obj.id() for obj in getattr(task_written_and_read, attribute)()],
        )

    def test_creation_date_time(self):
        self.assertAttributeWrittenAndRead(self.task, "creationDateTime")

    def test_modification_date_time(self):
        self.assertAttributeWrittenAndRead(self.task, "modificationDateTime")

    def test_subject(self):
        self.assertAttributeWrittenAndRead(self.task, "subject")

    def test_description(self):
        self.assertAttributeWrittenAndRead(self.task, "description")

    def test_foreground_color(self):
        self.assertAttributeWrittenAndRead(self.task, "foregroundColor")

    def test_background_color(self):
        self.assertAttributeWrittenAndRead(self.task, "backgroundColor")

    def test_font(self):
        self.assertAttributeWrittenAndRead(self.task, "font")

    def test_icon(self):
        self.assertAttributeWrittenAndRead(self.task, "icon_id")

    def test_expansion_state(self):
        self.assertAttributeWrittenAndRead(self.task, "isExpanded")

    def test_planned_start_date_time(self):
        self.assertAttributeWrittenAndRead(self.task, "plannedStartDateTime")

    def test_due_date_time(self):
        self.assertAttributeWrittenAndRead(self.task, "dueDateTime")

    def test_actual_start_date_time(self):
        self.assertAttributeWrittenAndRead(self.task, "actualStartDateTime")

    def test_completion_date_time(self):
        self.assertAttributeWrittenAndRead(self.task, "completionDateTime")

    def test_percentage_complete(self):
        self.assertAttributeWrittenAndRead(self.task, "percentageComplete")

    def test_budget(self):
        self.assertAttributeWrittenAndRead(self.task, "budget")

    def test_budget_more_than_24_hour(self):
        self.task.set_budget(date.TimeDelta(hours=25))
        self.tasksWrittenAndRead = task.TaskList(self.readAndWrite()[0])
        self.assertAttributeWrittenAndRead(self.task, "budget")

    def test_effort(self):
        self.assertAttributeWrittenAndRead(self.task, "timeSpent")

    def test_effort_description(self):
        self.assertEqual(
            self.task.efforts()[0].description(),
            self.getTaskWrittenAndRead(self.task.id())
            .efforts()[0]
            .description(),
        )

    def test_children(self):
        self.assertEqual(
            len(self.task.children()),
            len(self.getTaskWrittenAndRead(self.task.id()).children()),
        )

    def test_grand_children(self):
        self.assertEqual(
            len(self.task.children(recursive=True)),
            len(
                self.getTaskWrittenAndRead(self.task.id()).children(
                    recursive=True
                )
            ),
        )

    def test_category(self):
        categorizables = list(self.categoriesWrittenAndRead)[0].members()
        categorizable_ids = set([item.id() for item in categorizables])
        self.assertEqual(
            set([self.task.id(), self.note.id()]), categorizable_ids
        )

    def test_filtered_category(self):
        self.assertTrue(list(self.categoriesWrittenAndRead)[0].isFiltered())

    def test_exclusive_subcategories(self):
        self.assertTrue(
            list(self.categoriesWrittenAndRead)[0].hasExclusiveSubcategories()
        )

    def test_priority(self):
        self.assertAttributeWrittenAndRead(self.task, "priority")

    def test_negative_priority(self):
        self.assertAttributeWrittenAndRead(self.task2, "priority")

    def test_hourly_fee(self):
        self.assertAttributeWrittenAndRead(self.task, "hourlyFee")

    def test_fixed_fee(self):
        self.assertAttributeWrittenAndRead(self.task, "fixedFee")

    def test_reminder(self):
        self.assertAttributeWrittenAndRead(self.task, "reminder")

    def test_no_reminder(self):
        self.assertAttributeWrittenAndRead(self.task2, "reminder")

    def test_mark_completed_when_all_children_completed_setting_true(self):
        self.assertAttributeWrittenAndRead(
            self.task, "shouldMarkCompletedWhenAllChildrenCompleted"
        )

    def test_mark_completed_when_all_children_completed_setting_none(self):
        self.assertAttributeWrittenAndRead(
            self.task2, "shouldMarkCompletedWhenAllChildrenCompleted"
        )

    def test_attachment(self):
        self.assertAttributeWrittenAndRead(self.task, "attachments")

    def test_recurrence(self):
        self.assertAttributeWrittenAndRead(self.task, "recurrence")

    def test_note(self):
        self.assertEqual(len(self.notes), len(self.notesWrittenAndRead))

    def test_root_note(self):
        self.assertEqual(
            self.notes.rootItems()[0].subject(),
            self.notesWrittenAndRead.rootItems()[0].subject(),
        )

    def test_child_note(self):
        self.assertEqual(
            self.notes.rootItems()[0].children()[0].subject(),
            self.notesWrittenAndRead.rootItems()[0].children()[0].subject(),
        )

    def test_category_description(self):
        self.assertEqual(
            list(self.categories)[0].description(),
            list(self.categoriesWrittenAndRead)[0].description(),
        )

    def test_note_id(self):
        self.assertEqual(
            self.notes.rootItems()[0].id(),
            self.notesWrittenAndRead.rootItems()[0].id(),
        )

    def test_category_id(self):
        self.assertEqual(
            self.category.id(), list(self.categoriesWrittenAndRead)[0].id()
        )

    def test_note_with_category(self):
        self.assertTrue(
            self.notesWrittenAndRead.rootItems()[0]
            in list(self.categoriesWrittenAndRead)[0].members()
        )

    def test_task_note(self):
        self.assertContainedDomainObjectsWrittenAndRead(self.task, "notes")
