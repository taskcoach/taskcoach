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

import io
import wx
import test
from unittests.asserts import sorted_attributes
from taskcoachlib import persistence, config, meta
from taskcoachlib.domain import (
    base,
    task,
    effort,
    date,
    category,
    note,
    attachment,
)


class XMLWriterTest(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.fd = io.BytesIO()  # The app writes UTF-8 bytes (SafeWriteFile)
        self.fd.name = "testfile.tsk"
        self.writer = persistence.XMLWriter(self.fd)
        self.task = task.Task()
        self.taskList = task.TaskList([self.task])
        self.category = category.Category("Category")
        self.categoryContainer = category.CategoryList([self.category])
        self.note = note.Note()
        self.noteContainer = note.NoteContainer([self.note])
        self.changes = dict()

    def __writeAndRead(self):
        self.writer.write(
            self.taskList,
            self.categoryContainer,
            self.noteContainer,
            None,  # SyncML removed
            "GUID",
        )
        return self.fd.getvalue().decode("utf-8")

    def expect_in_xml(self, xml_fragment):
        xml = sorted_attributes(self.__writeAndRead())
        xml_fragment = sorted_attributes(xml_fragment)
        self.assertTrue(
            xml_fragment in xml or xml_fragment in xml.replace("&apos;", "'"),
            "%s not in %s" % (xml_fragment, xml),
        )

    def expect_not_in_xml(self, xml_fragment):
        xml = sorted_attributes(self.__writeAndRead())
        xml_fragment = sorted_attributes(xml_fragment)
        self.assertFalse(xml_fragment in xml, "%s in %s" % (xml_fragment, xml))

    # tests

    def testVersion(self):
        self.expect_in_xml('<?taskcoach release="%s"' % meta.data.version)

    def testGUID(self):
        self.expect_in_xml("<guid>\nGUID\n</guid>")

    def testTaskSubject(self):
        self.task.setSubject("Subject")
        self.expect_in_xml('subject="Subject"')

    def testTaskMarkedDeleted(self):
        self.task.markDeleted()
        self.expect_in_xml('status="3"')

    def testTaskSubjectWithUnicode(self):
        self.task.setSubject("ï¬Ÿï­Žï­–")
        self.expect_in_xml('subject="ï¬Ÿï­Žï­–"')

    def testTaskDescription(self):
        self.task.setDescription("Description")
        self.expect_in_xml("<description>\nDescription\n</description>\n")

    def testEmptyTaskDescriptionIsNotWritten(self):
        self.expect_not_in_xml("<description>")

    def testTaskPlannedStartDateTime(self):
        self.task.setPlannedStartDateTime(date.DateTime(2004, 1, 1, 11, 0, 0))
        self.expect_in_xml(
            'plannedstartdate="%s"' % str(self.task.plannedStartDateTime())
        )

    def testNoPlannedStartDateTime(self):
        self.task.setPlannedStartDateTime(date.DateTime())
        self.expect_not_in_xml("plannedstartdate=")

    def testTaskActualStartDateTime(self):
        self.task.setActualStartDateTime(date.DateTime(2007, 12, 31, 9, 0, 0))
        self.expect_in_xml(
            'actualstartdate="%s"' % str(self.task.actualStartDateTime())
        )

    def testNoActualStartDateTime(self):
        self.task.setActualStartDateTime(date.DateTime())
        self.expect_not_in_xml("actualstartdate=")

    def testTaskDueDateTime(self):
        self.task.setDueDateTime(date.DateTime(2004, 1, 1, 10, 5, 5))
        self.expect_in_xml('duedate="%s"' % str(self.task.dueDateTime()))

    def testNoDueDateTime(self):
        self.expect_not_in_xml("duedate=")

    def testTaskCompletionDateTime(self):
        self.task.setCompletionDateTime(date.DateTime(2004, 1, 1, 10, 8, 4))
        self.expect_in_xml(
            'completiondate="%s"' % str(self.task.completionDateTime())
        )

    def testNoCompletionDateTime(self):
        self.expect_not_in_xml("completiondate=")

    def testChildTask(self):
        self.task.addChild(task.Task(subject="child"))
        self.expect_in_xml('subject="child" />\n</task>\n<category')

    def testEffort(self):
        taskEffort = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1),
            date.DateTime(2004, 1, 2),
            description="description\nline 2",
        )
        self.task.addEffort(taskEffort)
        self.expect_in_xml(
            '<effort id="%s" start="%s" status="%d" stop="%s">\n'
            "<description>\ndescription\nline 2\n</description>\n"
            "</effort>"
            % (
                taskEffort.id(),
                taskEffort.getStart(),
                base.SynchronizedObject.STATUS_NEW,
                taskEffort.getStop(),
            )
        )

    def testThatEffortTimesDoNotContainMilliseconds(self):
        self.task.addEffort(
            effort.Effort(
                self.task,
                date.DateTime(2004, 1, 1, 10, 0, 0, 123456),
                date.DateTime(2004, 1, 1, 10, 0, 10, 654310),
            )
        )
        self.expect_in_xml('start="2004-01-01 10:00:00"')
        self.expect_in_xml('stop="2004-01-01 10:00:10"')

    def testThatEffortStartAndStopAreNotEqual(self):
        self.task.addEffort(
            effort.Effort(
                self.task,
                date.DateTime(2004, 1, 1, 10, 0, 0, 123456),
                date.DateTime(2004, 1, 1, 10, 0, 0, 654310),
            )
        )
        self.expect_in_xml('start="2004-01-01 10:00:00"')
        self.expect_in_xml('stop="2004-01-01 10:00:01"')

    def testEmptyEffortDescriptionIsNotWritten(self):
        self.task.addEffort(
            effort.Effort(
                self.task, date.DateTime(2004, 1, 1), date.DateTime(2004, 1, 2)
            )
        )
        self.expect_not_in_xml("<description>")

    def testActiveEffort(self):
        self.task.addEffort(
            effort.Effort(self.task, date.DateTime(2004, 1, 1))
        )
        self.expect_in_xml(
            '<effort id="%s" start="%s" status="%d" />'
            % (
                self.task.efforts()[0].id(),
                self.task.efforts()[0].getStart(),
                base.SynchronizedObject.STATUS_NEW,
            )
        )

    def testNoEffortByDefault(self):
        self.expect_not_in_xml("<efforts>")

    def testBudget(self):
        self.task.setBudget(date.ONE_HOUR)
        self.expect_in_xml('budget="%s"' % str(self.task.budget()))

    def testNoBudget(self):
        self.expect_not_in_xml("budget")

    def testBudget_MoreThan24Hour(self):
        self.task.setBudget(date.TimeDelta(hours=25))
        self.expect_in_xml('budget="25:00:00"')

    def testOneCategoryWithoutTask(self):
        aCategory = category.Category("test", id="id")
        self.categoryContainer.append(aCategory)
        self.expect_in_xml(
            '<category creationDateTime="%s" id="id" status="1" '
            'subject="test" />' % aCategory.creationDateTime()
        )

    def testOneCategoryWithOneTask(self):
        self.categoryContainer.append(category.Category("test", [self.task]))
        self.expect_in_xml('categorizables="%s"' % self.task.id())

    def testTwoCategoriesWithOneTask(self):
        subjects = ["test", "another"]
        expectedResults = []
        for subject in subjects:
            cat = category.Category(subject, [self.task])
            self.categoryContainer.append(cat)
            expectedResults.append(
                '<category categorizables="%s" '
                'creationDateTime="%s" id="%s" status="1" '
                'subject="%s" />'
                % (self.task.id(), cat.creationDateTime(), cat.id(), subject)
            )
        for expectedResult in expectedResults:
            self.expect_in_xml(expectedResult)

    def testOneCategoryWithSubTask(self):
        child = task.Task()
        self.taskList.append(child)
        self.task.addChild(child)
        self.categoryContainer.append(category.Category("test", [child]))
        self.expect_in_xml('categorizables="%s"' % child.id())

    def testSubCategoryWithoutTasks(self):
        parent = category.Category(subject="parent")
        child = category.Category(subject="child")
        parent.addChild(child)
        self.categoryContainer.extend([parent, child])
        self.expect_in_xml(
            '<category creationDateTime="%s" id="%s" '
            'status="1" subject="parent">\n'
            '<category creationDateTime="%s" id="%s" status="1" '
            'subject="child" />\n</category>'
            % (
                parent.creationDateTime(),
                parent.id(),
                child.creationDateTime(),
                child.id(),
            )
        )

    def testSubCategoryWithOneTask(self):
        parent = category.Category(subject="parent")
        child = category.Category(subject="child", categorizables=[self.task])
        parent.addChild(child)
        self.categoryContainer.extend([parent, child])
        self.expect_in_xml(
            '<category creationDateTime="%s" id="%s" '
            'status="1" subject="parent">\n'
            '<category categorizables="%s" creationDateTime="%s" '
            'id="%s" status="1" subject="child" />\n'
            "</category>"
            % (
                parent.creationDateTime(),
                parent.id(),
                self.task.id(),
                child.creationDateTime(),
                child.id(),
            )
        )

    def testFilteredCategory(self):
        self.categoryContainer.extend(
            [category.Category(subject="test", filtered=True)]
        )
        self.expect_in_xml('filtered="True"')

    def testCategoryWithDescription(self):
        aCategory = category.Category(
            subject="subject", description="Description", id="id"
        )
        self.categoryContainer.append(aCategory)
        self.expect_in_xml(
            '<category creationDateTime="%s" id="id" status="1" subject="subject">\n'
            "<description>\nDescription\n</description>\n"
            "</category>" % str(aCategory.creationDateTime())
        )

    def testCategoryWithUnicodeSubject(self):
        unicodeCategory = category.Category(subject="ï¬Ÿï­Žï­–", id="id")
        self.categoryContainer.extend([unicodeCategory])
        self.expect_in_xml('subject="ï¬Ÿï­Žï­–"')

    def testCategoryWithDeletedTask(self):
        aCategory = category.Category(
            subject="category", categorizables=[self.task], id="id"
        )
        self.categoryContainer.append(aCategory)
        self.taskList.remove(self.task)
        self.expect_in_xml(
            '<category creationDateTime="%s" id="id" status="1" '
            'subject="category" />' % str(aCategory.creationDateTime())
        )

    def testDefaultPriority(self):
        self.expect_not_in_xml("priority")

    def testPriority(self):
        self.task.setPriority(5)
        self.expect_in_xml('priority="5"')

    def testTaskId(self):
        self.expect_in_xml('id="%s"' % self.task.id())

    def testCategoryId(self):
        aCategory = category.Category(subject="category")
        self.categoryContainer.append(aCategory)
        self.expect_in_xml('id="%s"' % aCategory.id())

    def testNoteId(self):
        self.expect_in_xml('id="%s"' % self.note.id())

    def testTwoTasks(self):
        self.task.setSubject("task 1")
        task2 = task.Task(subject="task 2")
        self.taskList.append(task2)
        self.expect_in_xml('subject="task 2"')

    def testDefaultHourlyFee(self):
        self.expect_not_in_xml("hourlyFee")

    def testHourlyFee(self):
        self.task.setHourlyFee(100)
        self.expect_in_xml('hourlyFee="100"')

    def testDefaultFixedFee(self):
        self.expect_not_in_xml("fixedFee")

    def testFixedFee(self):
        self.task.setFixedFee(1000)
        self.expect_in_xml('fixedFee="1000"')

    def testNoReminder(self):
        self.expect_not_in_xml("reminder")

    def testReminder(self):
        self.task.setReminder(date.DateTime(2005, 5, 7, 13, 15, 10))
        self.expect_in_xml('reminder="%s"' % str(self.task.reminder()))
        self.expect_not_in_xml("reminderBeforeSnooze")

    def testSnoozedReminder(self):
        now = date.Now()
        self.task.setReminder(now + date.TimeDelta(seconds=30))
        self.task.snoozeReminder(date.TimeDelta(seconds=120), now=lambda: now)
        self.expect_in_xml('reminder="%s"' % str(self.task.reminder()))
        self.expect_in_xml(
            'reminderBeforeSnooze="%s"'
            % str(self.task.reminder(includeSnooze=False))
        )

    def testReminderIsNoneButSnoozedReminderNot(self):
        now = date.Now()
        self.task.setReminder(now + date.TimeDelta(seconds=30))
        self.task.snoozeReminder(date.TimeDelta())
        self.expect_not_in_xml("reminder")

    def testMarkCompletedWhenAllChildrenAreCompletedSetting_None(self):
        self.expect_not_in_xml("shouldMarkCompletedWhenAllChildrenCompleted")

    def testMarkCompletedWhenAllChildrenAreCompletedSetting_True(self):
        self.task.setShouldMarkCompletedWhenAllChildrenCompleted(True)
        self.expect_in_xml(
            'shouldMarkCompletedWhenAllChildrenCompleted="True"'
        )

    def testMarkCompletedWhenAllChildrenAreCompletedSetting_False(self):
        self.task.setShouldMarkCompletedWhenAllChildrenCompleted(False)
        self.expect_in_xml(
            'shouldMarkCompletedWhenAllChildrenCompleted="False"'
        )

    def testNote(self):
        aNote = note.Note(id="id")
        self.noteContainer.append(aNote)
        self.expect_in_xml(
            '<note creationDateTime="%s" id="id" status="%d" '
            "/>"
            % (aNote.creationDateTime(), base.SynchronizedObject.STATUS_NEW)
        )

    def testNoteWithSubject(self):
        self.noteContainer.append(note.Note(subject="Note"))
        self.expect_in_xml('subject="Note"')

    def testNoteWithDescription(self):
        self.noteContainer.append(note.Note(description="Description"))
        self.expect_in_xml("<description>\nDescription\n</description>\n")

    def testNoteWithChild(self):
        child = note.Note(id="child")
        self.note.addChild(child)
        self.noteContainer.append(child)
        self.expect_in_xml(
            '<note creationDateTime="%s" id="%s" status="%d">\n'
            '<note creationDateTime="%s" id="child" status="%d" />\n'
            "</note>"
            % (
                self.note.creationDateTime(),
                self.note.id(),
                base.SynchronizedObject.STATUS_NEW,
                child.creationDateTime(),
                base.SynchronizedObject.STATUS_NEW,
            )
        )

    def testNoteWithCategory(self):
        cat = category.Category(subject="cat")
        self.categoryContainer.append(cat)
        self.note.addCategory(cat)
        cat.addCategorizable(self.note)
        self.expect_in_xml('categorizables="%s"' % self.note.id())

    def testCategoryForegroundColor(self):
        self.categoryContainer.append(
            category.Category(subject="test", fgColor=wx.RED)
        )
        self.expect_in_xml('fgColor="(255, 0, 0, 255)"')

    def testCategoryBackgroundColor(self):
        self.categoryContainer.append(
            category.Category(subject="test", bgColor=wx.RED)
        )
        self.expect_in_xml('bgColor="(255, 0, 0, 255)"')

    def testDontWriteInheritedCategoryForegroundColor(self):
        parent = category.Category(subject="test", fgColor=wx.RED)
        child = category.Category(subject="child", id="id")
        parent.addChild(child)
        self.categoryContainer.append(parent)
        self.expect_in_xml(
            '<category creationDateTime="%s" id="id" status="1" '
            'subject="child" />' % child.creationDateTime()
        )

    def testDontWriteInheritedCategoryBackgroundColor(self):
        parent = category.Category(subject="test", bgColor=wx.RED)
        child = category.Category(subject="child", id="id")
        parent.addChild(child)
        self.categoryContainer.append(parent)
        self.expect_in_xml(
            '<category creationDateTime="%s" id="id" status="1" '
            'subject="child" />' % child.creationDateTime()
        )

    def testTaskForegroundColor(self):
        self.task.setForegroundColor(wx.RED)
        self.expect_in_xml('fgColor="(255, 0, 0, 255)"')

    def testTaskBackgroundColor(self):
        self.task.setBackgroundColor(wx.RED)
        self.expect_in_xml('bgColor="(255, 0, 0, 255)"')

    def testDontWriteInheritedTaskForegroundColor(self):
        self.task.setForegroundColor(wx.RED)
        child = task.Task(
            subject="child", id="id", plannedStartDateTime=date.DateTime()
        )
        self.task.addChild(child)
        self.taskList.append(child)
        self.expect_in_xml(
            '<task creationDateTime="%s" id="id" status="1" '
            'subject="child" />' % child.creationDateTime()
        )

    def testDontWriteInheritedTaskBackgroundColor(self):
        self.task.setBackgroundColor(wx.RED)
        child = task.Task(
            subject="child", id="id", plannedStartDateTime=date.DateTime()
        )
        self.task.addChild(child)
        self.taskList.append(child)
        self.expect_in_xml(
            '<task creationDateTime="%s" id="id" status="1" '
            'subject="child" />' % child.creationDateTime()
        )

    def testNoteForegroundColor(self):
        self.note.setForegroundColor(wx.RED)
        self.expect_in_xml('fgColor="(255, 0, 0, 255)"')

    def testNoteBackgroundColor(self):
        self.note.setBackgroundColor(wx.RED)
        self.expect_in_xml('bgColor="(255, 0, 0, 255)"')

    def testDontWriteInheritedNoteForegroundColor(self):
        parent = note.Note(fgColor=wx.RED)
        child = note.Note(subject="child", id="id")
        parent.addChild(child)
        self.noteContainer.append(parent)
        self.expect_in_xml(
            '<note creationDateTime="%s" id="id" status="1" '
            'subject="child" />' % child.creationDateTime()
        )

    def testDontWriteInheritedNoteBackgroundColor(self):
        parent = note.Note(bgColor=wx.RED)
        child = note.Note(subject="child", id="id")
        parent.addChild(child)
        self.noteContainer.append(parent)
        self.expect_in_xml(
            '<note creationDateTime="%s" id="id" status="1" '
            'subject="child" />' % child.creationDateTime()
        )

    def testNoRecurencce(self):
        self.expect_not_in_xml("recurrence")

    def testDailyRecurrence(self):
        self.task.setRecurrence(date.Recurrence("daily"))
        self.expect_in_xml('<recurrence unit="daily" />')

    def testWeeklyRecurrence(self):
        self.task.setRecurrence(date.Recurrence("weekly"))
        self.expect_in_xml('<recurrence unit="weekly" />')

    def testMonthlyRecurrence(self):
        self.task.setRecurrence(date.Recurrence("monthly"))
        self.expect_in_xml('<recurrence unit="monthly" />')

    def testMonthlyRecurrenceOnSameWeekday(self):
        self.task.setRecurrence(date.Recurrence("monthly", sameWeekday=True))
        self.expect_in_xml('<recurrence sameWeekday="True" unit="monthly" />')

    def testYearlyRecurrence(self):
        self.task.setRecurrence(date.Recurrence("yearly"))
        self.expect_in_xml('<recurrence unit="yearly" />')

    def testRecurrenceCount(self):
        self.task.setRecurrence(date.Recurrence("daily", count=5))
        self.expect_in_xml('count="5"')

    def testMaxRecurrenceCount(self):
        self.task.setRecurrence(date.Recurrence("daily", maximum=5))
        self.expect_in_xml('max="5"')

    def testRecurrenceStopDateTime(self):
        stop_datetime = date.DateTime(2000, 1, 1, 10, 9, 8)
        self.task.setRecurrence(
            date.Recurrence("daily", stop_datetime=stop_datetime)
        )
        self.expect_in_xml('stop_datetime="%s"' % str(stop_datetime))

    def testRecurrenceFrequency(self):
        self.task.setRecurrence(date.Recurrence("daily", amount=2))
        self.expect_in_xml('amount="2"')

    def testRecurrenceBasedOnCompletion(self):
        self.task.setRecurrence(
            date.Recurrence("daily", recurBasedOnCompletion=True)
        )
        self.expect_in_xml('recurBasedOnCompletion="True"')

    def testNoAttachments(self):
        self.expect_not_in_xml("attachment")

    # addAttachment, addNote, etc., are dynamically generated so pylint can't
    # find them. Disable the error message.
    # pylint: disable=E1101

    def testTaskWithOneAttachment(self):
        task_attachment = attachment.FileAttachment("whatever.txt", id="foo")
        self.task.addAttachments(task_attachment)
        self.expect_in_xml(
            '<attachment creationDateTime="%s" id="foo" '
            'location="whatever.txt" status="1" '
            'subject="whatever" type="file" '
            "/>" % task_attachment.creationDateTime()
        )

    def testObjectWithAttachmentWithNote(self):
        att = attachment.FileAttachment("whatever.txt", id="foo")
        self.task.addAttachments(att)
        attachment_note = note.Note(subject="attnote", id="spam")
        att.addNote(attachment_note)
        self.expect_in_xml(
            '<attachment creationDateTime="%s" id="foo" '
            'location="whatever.txt" '
            'status="1" subject="whatever" type="file">\n'
            "<note" % att.creationDateTime()
        )

    def testNoteWithOneAttachment(self):
        note_attachment = attachment.FileAttachment("whatever.txt", id="foo")
        self.note.addAttachments(note_attachment)
        self.expect_in_xml(
            '<attachment creationDateTime="%s" id="foo" '
            'location="whatever.txt" status="1" '
            'subject="whatever" type="file" '
            "/>" % note_attachment.creationDateTime()
        )

    def testCategoryWithOneAttachment(self):
        cat = category.Category("cat")
        self.categoryContainer.append(cat)
        category_attachment = attachment.FileAttachment(
            "whatever.txt", id="foo"
        )
        cat.addAttachments(category_attachment)
        self.expect_in_xml(
            '<attachment creationDateTime="%s" id="foo" '
            'location="whatever.txt" status="1" '
            'subject="whatever" type="file" '
            "/>" % category_attachment.creationDateTime()
        )

    def testTaskWithTwoAttachments(self):
        attachments = [
            attachment.FileAttachment("whatever.txt"),
            attachment.FileAttachment("/home/frank/attachment.doc"),
        ]
        for a in attachments:
            self.task.addAttachments(a)
        for att in attachments:
            self.expect_in_xml(
                '<attachment creationDateTime="%s" id="%s" '
                'location="%s" status="1" subject="%s" type="file" '
                "/>"
                % (
                    att.creationDateTime(),
                    att.id(),
                    att.location(),
                    att.subject(),
                )
            )

    def testTaskWithNote(self):
        self.task.addNote(self.note)
        self.expect_in_xml(
            '>\n<note creationDateTime="%s" id="%s" status="1" '
            "/>\n</task>" % (self.note.creationDateTime(), self.note.id())
        )

    def testTaskWithNotes(self):
        anotherNote = note.Note(subject="Another note", id="id")
        self.task.addNote(self.note)
        self.task.addNote(anotherNote)
        self.expect_in_xml(
            '>\n<note creationDateTime="%s" id="%s" status="1" />\n'
            '<note creationDateTime="%s" id="id" status="1" subject="Another note" '
            "/>\n</task>"
            % (
                self.note.creationDateTime(),
                self.note.id(),
                anotherNote.creationDateTime(),
            )
        )

    def testTaskWithNestedNotes(self):
        subNote = note.Note(subject="Subnote", id="id")
        self.note.addChild(subNote)
        self.task.addNote(self.note)
        self.expect_in_xml(
            '>\n<note creationDateTime="%s" id="%s" status="1">\n'
            '<note creationDateTime="%s" id="id" status="1" subject="Subnote" '
            "/>\n</note>\n</task>"
            % (
                self.note.creationDateTime(),
                self.note.id(),
                subNote.creationDateTime(),
            )
        )

    def testTaskWithNoteWithCategory(self):
        newNote = note.Note()
        self.task.addNote(newNote)
        newNote.addCategory(self.category)
        self.category.addCategorizable(newNote)
        self.expect_in_xml('categorizables="%s"' % newNote.id())

    def testTaskWithNoteWithSubNoteWithCategory(self):
        newNote = note.Note()
        newSubNote = note.Note()
        newNote.addChild(newSubNote)
        self.task.addNote(newNote)
        newSubNote.addCategory(self.category)
        self.category.addCategorizable(newSubNote)
        self.expect_in_xml('categorizables="%s"' % newSubNote.id())

    def testCategoryWithNote(self):
        self.category.addNote(self.note)
        self.expect_in_xml(
            '>\n<note creationDateTime="%s" id="%s" status="1" '
            "/>\n</category>" % (self.note.creationDateTime(), self.note.id())
        )

    def testCategoryWithNotes(self):
        anotherNote = note.Note(subject="Another note", id="id")
        self.category.addNote(self.note)
        self.category.addNote(anotherNote)
        self.expect_in_xml(
            '>\n<note creationDateTime="%s" id="%s" status="1" />\n'
            '<note creationDateTime="%s" id="id" status="1" subject="Another '
            'note" />\n</category>'
            % (
                self.note.creationDateTime(),
                self.note.id(),
                anotherNote.creationDateTime(),
            )
        )

    def testCategoryWithNestedNotes(self):
        subNote = note.Note(subject="Subnote", id="id")
        self.note.addChild(subNote)
        self.category.addNote(self.note)
        self.expect_in_xml(
            '>\n<note creationDateTime="%s" id="%s" status="1">\n'
            '<note creationDateTime="%s" id="id" status="1" subject="Subnote" '
            "/>\n</note>\n</category>"
            % (
                self.note.creationDateTime(),
                self.note.id(),
                subNote.creationDateTime(),
            )
        )

    def testTaskDefaultExpansionState(self):
        # Don't write anything if the task is not expanded:
        self.expect_not_in_xml("expandedContexts")

    def testTaskExpansionState(self):
        self.task.expand()
        self.expect_in_xml('''expandedContexts="('None',)"''')

    def testTaskExpansionState_SpecificContext(self):
        self.task.expand(context="Test")
        self.expect_in_xml('''expandedContexts="('Test',)"''')

    def testTaskExpansionState_MultipleContexts(self):
        self.task.expand(context="Test")
        self.task.expand(context="Another context")
        self.expect_in_xml(
            '''expandedContexts="('Another context', 'Test')"'''
        )

    def testCategoryExpansionState(self):
        cat = category.Category("cat")
        self.categoryContainer.append(cat)
        cat.expand()
        self.expect_in_xml('''expandedContexts="('None',)"''')

    def testNoteExpansionState(self):
        self.note.expand()
        self.expect_in_xml('''expandedContexts="('None',)"''')

    def testPercentageComplete(self):
        self.task.setPercentageComplete(50)
        self.expect_in_xml('''percentageComplete="50"''')

    def testPercentageComplete_Float(self):
        self.task.setPercentageComplete(50.0)
        self.expect_in_xml('''percentageComplete="50.0"''')

    def testExclusiveSubcategories(self):
        self.category.makeSubcategoriesExclusive()
        self.expect_in_xml('''exclusiveSubcategories="True"''')

    def testNonExclusiveSubcategoriesByDefault(self):
        self.expect_not_in_xml("""exclusiveSubcategories""")

    def testTaskFont(self):
        self.task.setFont(wx.SWISS_FONT)
        self.expect_in_xml('font="%s"' % wx.SWISS_FONT.GetNativeFontInfoDesc())

    def testNoTaskFontByDefault(self):
        self.expect_not_in_xml("font")

    def testNoteFont(self):
        self.note.setFont(wx.SWISS_FONT)
        self.expect_in_xml('font="%s"' % wx.SWISS_FONT.GetNativeFontInfoDesc())

    def testCategoryFont(self):
        self.category.setFont(wx.SWISS_FONT)
        self.expect_in_xml('font="%s"' % wx.SWISS_FONT.GetNativeFontInfoDesc())

    def testAttachmentFont(self):
        att = attachment.FileAttachment(
            "whatever.txt", id="foo", font=wx.SWISS_FONT
        )
        self.task.addAttachments(att)
        self.expect_in_xml('font="%s"' % wx.SWISS_FONT.GetNativeFontInfoDesc())

    def testNonAsciiFontName(self):
        class FakeFont(object):
            def GetNativeFontInfoDesc(self):
                return "微软雅黑"

        font = FakeFont()
        self.task.setFont(font)
        self.expect_in_xml('font="微软雅黑"')

    def testTaskIcon(self):
        self.task.set_icon_id("icon")
        self.expect_in_xml('icon="icon"')

    def testNoTaskIcon(self):
        self.expect_not_in_xml("icon")

    def testSelectedTaskIcon(self):
        self.task.set_selected_icon_id("icon")
        self.expect_in_xml('selectedIcon="icon"')

    def testNoSelectedTaskIcon(self):
        self.expect_not_in_xml("selectedIcon")

    def testNoteIcon(self):
        self.note.set_icon_id("icon")
        self.expect_in_xml('icon="icon"')

    def testSelectedNoteIcon(self):
        self.note.set_selected_icon_id("icon")
        self.expect_in_xml('selectedIcon="icon"')

    def testCategoryIcon(self):
        self.category.set_icon_id("icon")
        self.expect_in_xml('icon="icon"')

    def testSelectedCategoryIcon(self):
        self.category.set_selected_icon_id("icon")
        self.expect_in_xml('selectedIcon="icon"')

    def testAttachmentIcon(self):
        att = attachment.FileAttachment("whatever.txt", id="foo", icon="icon")
        self.task.addAttachments(att)
        self.expect_in_xml('icon="icon"')

    def testSelectedAttachmentIcon(self):
        att = attachment.FileAttachment("whatever.txt", selectedIcon="icon")
        self.task.addAttachments(att)
        self.expect_in_xml('selectedIcon="icon"')

    def testPrerequisite(self):
        prerequisite = task.Task(subject="prereq")
        self.taskList.append(prerequisite)
        self.task.addPrerequisites([prerequisite])
        self.expect_in_xml('prerequisites="%s"' % prerequisite.id())

    def testMultiplePrerequisites(self):
        # Written sorted by id
        prerequisites = [
            task.Task(subject="prereq2", id="id2"),
            task.Task(subject="prereq1", id="id1"),
        ]
        self.taskList.extend(prerequisites)
        self.task.addPrerequisites(prerequisites)
        self.expect_in_xml('prerequisites="id1 id2"')

    def testEncodingAttribute(self):
        self.expect_in_xml('encoding="utf-8"')

    def testCreationDateTime(self):
        self.expect_in_xml(
            'creationDateTime="%s"' % str(self.task.creationDateTime())
        )

    def testDoNotWriteUnknownCreationDateTime(self):
        task_with_unknown_creation_datetime = task.Task(
            creationDateTime=date.DateTime.min
        )
        self.taskList.append(task_with_unknown_creation_datetime)
        self.expect_not_in_xml('creationDateTime="0001-01-01 00:00:00"')

    def testModificationDateTime(self):
        self.task.setModificationDateTime(date.DateTime(2013, 1, 1, 0, 0, 0))
        self.expect_in_xml('modificationDateTime="2013-01-01 00:00:00"')

    def testDoNotWriteUnknownModificationDateTime(self):
        task_with_unknown_modification_datetime = task.Task(
            modificationDateTime=date.DateTime.min
        )
        self.expect_not_in_xml('modificationDateTime="0001-01-01 00:00:00"')
