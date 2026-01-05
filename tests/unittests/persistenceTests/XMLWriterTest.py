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

import wx, io  # We cannot use CStringIO since unicode strings are used below.
import test
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
        self.fd = io.StringIO()
        self.fd.name = "testfile.tsk"
        self.fd.encoding = "utf-8"
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
        return self.fd.getvalue().decode(self.fd.encoding)

    def expectInXML(self, xmlFragment):
        xml = self.__writeAndRead()
        self.assertTrue(
            xmlFragment in xml or xmlFragment in xml.replace("&apos;", "'"),
            "%s not in %s" % (xmlFragment, xml),
        )

    def expectNotInXML(self, xmlFragment):
        xml = self.__writeAndRead()
        self.assertFalse(xmlFragment in xml, "%s in %s" % (xmlFragment, xml))

    # tests

    def testVersion(self):
        self.expectInXML('<?taskcoach release="%s"' % meta.data.version)

    def testGUID(self):
        self.expectInXML("<guid>\nGUID\n</guid>")

    def testTaskSubject(self):
        self.task.setSubject("Subject")
        self.expectInXML('subject="Subject"')

    def testTaskMarkedDeleted(self):
        self.task.markDeleted()
        self.expectInXML('status="3"')

    def testTaskSubjectWithUnicode(self):
        self.task.setSubject("ï¬Ÿï­Žï­–")
        self.expectInXML('subject="ï¬Ÿï­Žï­–"')

    def testTaskDescription(self):
        self.task.setDescription("Description")
        self.expectInXML("<description>\nDescription\n</description>\n")

    def testEmptyTaskDescriptionIsNotWritten(self):
        self.expectNotInXML("<description>")

    def testTaskPlannedStartDateTime(self):
        self.task.setPlannedStartDateTime(date.DateTime(2004, 1, 1, 11, 0, 0))
        self.expectInXML(
            'plannedstartdate="%s"' % str(self.task.plannedStartDateTime())
        )

    def testNoPlannedStartDateTime(self):
        self.task.setPlannedStartDateTime(date.DateTime())
        self.expectNotInXML("plannedstartdate=")

    def testTaskActualStartDateTime(self):
        self.task.setActualStartDateTime(date.DateTime(2007, 12, 31, 9, 0, 0))
        self.expectInXML(
            'actualstartdate="%s"' % str(self.task.actualStartDateTime())
        )

    def testNoActualStartDateTime(self):
        self.task.setActualStartDateTime(date.DateTime())
        self.expectNotInXML("actualstartdate=")

    def testTaskDueDateTime(self):
        self.task.setDueDateTime(date.DateTime(2004, 1, 1, 10, 5, 5))
        self.expectInXML('duedate="%s"' % str(self.task.dueDateTime()))

    def testNoDueDateTime(self):
        self.expectNotInXML("duedate=")

    def testTaskCompletionDateTime(self):
        self.task.setCompletionDateTime(date.DateTime(2004, 1, 1, 10, 8, 4))
        self.expectInXML(
            'completiondate="%s"' % str(self.task.completionDateTime())
        )

    def testNoCompletionDateTime(self):
        self.expectNotInXML("completiondate=")

    def testChildTask(self):
        self.task.addChild(task.Task(subject="child"))
        self.expectInXML('subject="child" />\n</task>\n<category')

    def testEffort(self):
        taskEffort = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1),
            date.DateTime(2004, 1, 2),
            description="description\nline 2",
        )
        self.task.addEffort(taskEffort)
        self.expectInXML(
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
        self.expectInXML('start="2004-01-01 10:00:00"')
        self.expectInXML('stop="2004-01-01 10:00:10"')

    def testThatEffortStartAndStopAreNotEqual(self):
        self.task.addEffort(
            effort.Effort(
                self.task,
                date.DateTime(2004, 1, 1, 10, 0, 0, 123456),
                date.DateTime(2004, 1, 1, 10, 0, 0, 654310),
            )
        )
        self.expectInXML('start="2004-01-01 10:00:00"')
        self.expectInXML('stop="2004-01-01 10:00:01"')

    def testEmptyEffortDescriptionIsNotWritten(self):
        self.task.addEffort(
            effort.Effort(
                self.task, date.DateTime(2004, 1, 1), date.DateTime(2004, 1, 2)
            )
        )
        self.expectNotInXML("<description>")

    def testActiveEffort(self):
        self.task.addEffort(
            effort.Effort(self.task, date.DateTime(2004, 1, 1))
        )
        self.expectInXML(
            '<effort id="%s" start="%s" status="%d" />'
            % (
                self.task.efforts()[0].id(),
                self.task.efforts()[0].getStart(),
                base.SynchronizedObject.STATUS_NEW,
            )
        )

    def testNoEffortByDefault(self):
        self.expectNotInXML("<efforts>")

    def testBudget(self):
        self.task.setBudget(date.ONE_HOUR)
        self.expectInXML('budget="%s"' % str(self.task.budget()))

    def testNoBudget(self):
        self.expectNotInXML("budget")

    def testBudget_MoreThan24Hour(self):
        self.task.setBudget(date.TimeDelta(hours=25))
        self.expectInXML('budget="25:00:00"')

    def testOneCategoryWithoutTask(self):
        aCategory = category.Category("test", id="id")
        self.categoryContainer.append(aCategory)
        self.expectInXML(
            '<category creationDateTime="%s" id="id" status="1" '
            'subject="test" />' % aCategory.creationDateTime()
        )

    def testOneCategoryWithOneTask(self):
        self.categoryContainer.append(category.Category("test", [self.task]))
        self.expectInXML('categorizables="%s"' % self.task.id())

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
            self.expectInXML(expectedResult)

    def testOneCategoryWithSubTask(self):
        child = task.Task()
        self.taskList.append(child)
        self.task.addChild(child)
        self.categoryContainer.append(category.Category("test", [child]))
        self.expectInXML('categorizables="%s"' % child.id())

    def testSubCategoryWithoutTasks(self):
        parent = category.Category(subject="parent")
        child = category.Category(subject="child")
        parent.addChild(child)
        self.categoryContainer.extend([parent, child])
        self.expectInXML(
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
        self.expectInXML(
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
        self.expectInXML('filtered="True"')

    def testCategoryWithDescription(self):
        aCategory = category.Category(
            subject="subject", description="Description", id="id"
        )
        self.categoryContainer.append(aCategory)
        self.expectInXML(
            '<category creationDateTime="%s" id="id" status="1" subject="subject">\n'
            "<description>\nDescription\n</description>\n"
            "</category>" % str(aCategory.creationDateTime())
        )

    def testCategoryWithUnicodeSubject(self):
        unicodeCategory = category.Category(subject="ï¬Ÿï­Žï­–", id="id")
        self.categoryContainer.extend([unicodeCategory])
        self.expectInXML('subject="ï¬Ÿï­Žï­–"')

    def testCategoryWithDeletedTask(self):
        aCategory = category.Category(
            subject="category", categorizables=[self.task], id="id"
        )
        self.categoryContainer.append(aCategory)
        self.taskList.remove(self.task)
        self.expectInXML(
            '<category creationDateTime="%s" id="id" status="1" '
            'subject="category" />' % str(aCategory.creationDateTime())
        )

    def testDefaultPriority(self):
        self.expectNotInXML("priority")

    def testPriority(self):
        self.task.setPriority(5)
        self.expectInXML('priority="5"')

    def testTaskId(self):
        self.expectInXML('id="%s"' % self.task.id())

    def testCategoryId(self):
        aCategory = category.Category(subject="category")
        self.categoryContainer.append(aCategory)
        self.expectInXML('id="%s"' % aCategory.id())

    def testNoteId(self):
        self.expectInXML('id="%s"' % self.note.id())

    def testTwoTasks(self):
        self.task.setSubject("task 1")
        task2 = task.Task(subject="task 2")
        self.taskList.append(task2)
        self.expectInXML('subject="task 2"')

    def testDefaultHourlyFee(self):
        self.expectNotInXML("hourlyFee")

    def testHourlyFee(self):
        self.task.setHourlyFee(100)
        self.expectInXML('hourlyFee="100"')

    def testDefaultFixedFee(self):
        self.expectNotInXML("fixedFee")

    def testFixedFee(self):
        self.task.setFixedFee(1000)
        self.expectInXML('fixedFee="1000"')

    def testNoReminder(self):
        self.expectNotInXML("reminder")

    def testReminder(self):
        self.task.setReminder(date.DateTime(2005, 5, 7, 13, 15, 10))
        self.expectInXML('reminder="%s"' % str(self.task.reminder()))
        self.expectNotInXML("reminderBeforeSnooze")

    def testSnoozedReminder(self):
        now = date.Now()
        self.task.setReminder(now + date.TimeDelta(seconds=30))
        self.task.snoozeReminder(date.TimeDelta(seconds=120), now=lambda: now)
        self.expectInXML('reminder="%s"' % str(self.task.reminder()))
        self.expectInXML(
            'reminderBeforeSnooze="%s"'
            % str(self.task.reminder(includeSnooze=False))
        )

    def testReminderIsNoneButSnoozedReminderNot(self):
        now = date.Now()
        self.task.setReminder(now + date.TimeDelta(seconds=30))
        self.task.snoozeReminder(date.TimeDelta())
        self.expectNotInXML("reminder")

    def testMarkCompletedWhenAllChildrenAreCompletedSetting_None(self):
        self.expectNotInXML("shouldMarkCompletedWhenAllChildrenCompleted")

    def testMarkCompletedWhenAllChildrenAreCompletedSetting_True(self):
        self.task.setShouldMarkCompletedWhenAllChildrenCompleted(True)
        self.expectInXML('shouldMarkCompletedWhenAllChildrenCompleted="True"')

    def testMarkCompletedWhenAllChildrenAreCompletedSetting_False(self):
        self.task.setShouldMarkCompletedWhenAllChildrenCompleted(False)
        self.expectInXML('shouldMarkCompletedWhenAllChildrenCompleted="False"')

    def testNote(self):
        aNote = note.Note(id="id")
        self.noteContainer.append(aNote)
        self.expectInXML(
            '<note creationDateTime="%s" id="id" status="%d" '
            "/>"
            % (aNote.creationDateTime(), base.SynchronizedObject.STATUS_NEW)
        )

    def testNoteWithSubject(self):
        self.noteContainer.append(note.Note(subject="Note"))
        self.expectInXML('subject="Note"')

    def testNoteWithDescription(self):
        self.noteContainer.append(note.Note(description="Description"))
        self.expectInXML("<description>\nDescription\n</description>\n")

    def testNoteWithChild(self):
        child = note.Note(id="child")
        self.note.addChild(child)
        self.noteContainer.append(child)
        self.expectInXML(
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
        self.expectInXML('categorizables="%s"' % self.note.id())

    def testCategoryForegroundColor(self):
        self.categoryContainer.append(
            category.Category(subject="test", fgColor=wx.RED)
        )
        self.expectInXML('fgColor="(255, 0, 0, 255)"')

    def testCategoryBackgroundColor(self):
        self.categoryContainer.append(
            category.Category(subject="test", bgColor=wx.RED)
        )
        self.expectInXML('bgColor="(255, 0, 0, 255)"')

    def testDontWriteInheritedCategoryForegroundColor(self):
        parent = category.Category(subject="test", fgColor=wx.RED)
        child = category.Category(subject="child", id="id")
        parent.addChild(child)
        self.categoryContainer.append(parent)
        self.expectInXML(
            '<category creationDateTime="%s" id="id" status="1" '
            'subject="child" />' % child.creationDateTime()
        )

    def testDontWriteInheritedCategoryBackgroundColor(self):
        parent = category.Category(subject="test", bgColor=wx.RED)
        child = category.Category(subject="child", id="id")
        parent.addChild(child)
        self.categoryContainer.append(parent)
        self.expectInXML(
            '<category creationDateTime="%s" id="id" status="1" '
            'subject="child" />' % child.creationDateTime()
        )

    def testTaskForegroundColor(self):
        self.task.setForegroundColor(wx.RED)
        self.expectInXML('fgColor="(255, 0, 0, 255)"')

    def testTaskBackgroundColor(self):
        self.task.setBackgroundColor(wx.RED)
        self.expectInXML('bgColor="(255, 0, 0, 255)"')

    def testDontWriteInheritedTaskForegroundColor(self):
        self.task.setForegroundColor(wx.RED)
        child = task.Task(
            subject="child", id="id", plannedStartDateTime=date.DateTime()
        )
        self.task.addChild(child)
        self.taskList.append(child)
        self.expectInXML(
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
        self.expectInXML(
            '<task creationDateTime="%s" id="id" status="1" '
            'subject="child" />' % child.creationDateTime()
        )

    def testNoteForegroundColor(self):
        self.note.setForegroundColor(wx.RED)
        self.expectInXML('fgColor="(255, 0, 0, 255)"')

    def testNoteBackgroundColor(self):
        self.note.setBackgroundColor(wx.RED)
        self.expectInXML('bgColor="(255, 0, 0, 255)"')

    def testDontWriteInheritedNoteForegroundColor(self):
        parent = note.Note(fgColor=wx.RED)
        child = note.Note(subject="child", id="id")
        parent.addChild(child)
        self.noteContainer.append(parent)
        self.expectInXML(
            '<note creationDateTime="%s" id="id" status="1" '
            'subject="child" />' % child.creationDateTime()
        )

    def testDontWriteInheritedNoteBackgroundColor(self):
        parent = note.Note(bgColor=wx.RED)
        child = note.Note(subject="child", id="id")
        parent.addChild(child)
        self.noteContainer.append(parent)
        self.expectInXML(
            '<note creationDateTime="%s" id="id" status="1" '
            'subject="child" />' % child.creationDateTime()
        )

    def testNoRecurencce(self):
        self.expectNotInXML("recurrence")

    def testDailyRecurrence(self):
        self.task.setRecurrence(date.Recurrence("daily"))
        self.expectInXML('<recurrence unit="daily" />')

    def testWeeklyRecurrence(self):
        self.task.setRecurrence(date.Recurrence("weekly"))
        self.expectInXML('<recurrence unit="weekly" />')

    def testMonthlyRecurrence(self):
        self.task.setRecurrence(date.Recurrence("monthly"))
        self.expectInXML('<recurrence unit="monthly" />')

    def testMonthlyRecurrenceOnSameWeekday(self):
        self.task.setRecurrence(date.Recurrence("monthly", sameWeekday=True))
        self.expectInXML('<recurrence sameWeekday="True" unit="monthly" />')

    def testYearlyRecurrence(self):
        self.task.setRecurrence(date.Recurrence("yearly"))
        self.expectInXML('<recurrence unit="yearly" />')

    def testRecurrenceCount(self):
        self.task.setRecurrence(date.Recurrence("daily", count=5))
        self.expectInXML('count="5"')

    def testMaxRecurrenceCount(self):
        self.task.setRecurrence(date.Recurrence("daily", maximum=5))
        self.expectInXML('max="5"')

    def testRecurrenceStopDateTime(self):
        stop_datetime = date.DateTime(2000, 1, 1, 10, 9, 8)
        self.task.setRecurrence(
            date.Recurrence("daily", stop_datetime=stop_datetime)
        )
        self.expectInXML('stop_datetime="%s"' % str(stop_datetime))

    def testRecurrenceFrequency(self):
        self.task.setRecurrence(date.Recurrence("daily", amount=2))
        self.expectInXML('amount="2"')

    def testRecurrenceBasedOnCompletion(self):
        self.task.setRecurrence(
            date.Recurrence("daily", recurBasedOnCompletion=True)
        )
        self.expectInXML('recurBasedOnCompletion="True"')

    def testNoAttachments(self):
        self.expectNotInXML("attachment")

    # addAttachment, addNote, etc., are dynamically generated so pylint can't
    # find them. Disable the error message.
    # pylint: disable=E1101

    def testTaskWithOneAttachment(self):
        task_attachment = attachment.FileAttachment("whatever.txt", id="foo")
        self.task.addAttachments(task_attachment)
        self.expectInXML(
            '<attachment creationDateTime="%s" id="foo" '
            'location="whatever.txt" status="1" '
            'subject="whatever.txt" type="file" '
            "/>" % task_attachment.creationDateTime()
        )

    def testObjectWithAttachmentWithNote(self):
        att = attachment.FileAttachment("whatever.txt", id="foo")
        self.task.addAttachments(att)
        attachment_note = note.Note(subject="attnote", id="spam")
        att.addNote(attachment_note)
        self.expectInXML(
            '<attachment creationDateTime="%s" id="foo" '
            'location="whatever.txt" '
            'status="1" subject="whatever.txt" type="file">\n'
            "<note" % att.creationDateTime()
        )

    def testNoteWithOneAttachment(self):
        note_attachment = attachment.FileAttachment("whatever.txt", id="foo")
        self.note.addAttachments(note_attachment)
        self.expectInXML(
            '<attachment creationDateTime="%s" id="foo" '
            'location="whatever.txt" status="1" '
            'subject="whatever.txt" type="file" '
            "/>" % note_attachment.creationDateTime()
        )

    def testCategoryWithOneAttachment(self):
        cat = category.Category("cat")
        self.categoryContainer.append(cat)
        category_attachment = attachment.FileAttachment(
            "whatever.txt", id="foo"
        )
        cat.addAttachments(category_attachment)
        self.expectInXML(
            '<attachment creationDateTime="%s" id="foo" '
            'location="whatever.txt" status="1" '
            'subject="whatever.txt" type="file" '
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
            self.expectInXML(
                '<attachment creationDateTime="%s" id="%s" '
                'location="%s" status="1" subject="%s" type="file" '
                "/>"
                % (
                    att.creationDateTime(),
                    att.id(),
                    att.location(),
                    att.location(),
                )
            )

    def testTaskWithNote(self):
        self.task.addNote(self.note)
        self.expectInXML(
            '>\n<note creationDateTime="%s" id="%s" status="1" '
            "/>\n</task>" % (self.note.creationDateTime(), self.note.id())
        )

    def testTaskWithNotes(self):
        anotherNote = note.Note(subject="Another note", id="id")
        self.task.addNote(self.note)
        self.task.addNote(anotherNote)
        self.expectInXML(
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
        self.expectInXML(
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
        self.expectInXML('categorizables="%s"' % newNote.id())

    def testTaskWithNoteWithSubNoteWithCategory(self):
        newNote = note.Note()
        newSubNote = note.Note()
        newNote.addChild(newSubNote)
        self.task.addNote(newNote)
        newSubNote.addCategory(self.category)
        self.category.addCategorizable(newSubNote)
        self.expectInXML('categorizables="%s"' % newSubNote.id())

    def testCategoryWithNote(self):
        self.category.addNote(self.note)
        self.expectInXML(
            '>\n<note creationDateTime="%s" id="%s" status="1" '
            "/>\n</category>" % (self.note.creationDateTime(), self.note.id())
        )

    def testCategoryWithNotes(self):
        anotherNote = note.Note(subject="Another note", id="id")
        self.category.addNote(self.note)
        self.category.addNote(anotherNote)
        self.expectInXML(
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
        self.expectInXML(
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
        self.expectNotInXML("expandedContexts")

    def testTaskExpansionState(self):
        self.task.expand()
        self.expectInXML('''expandedContexts="('None',)"''')

    def testTaskExpansionState_SpecificContext(self):
        self.task.expand(context="Test")
        self.expectInXML('''expandedContexts="('Test',)"''')

    def testTaskExpansionState_MultipleContexts(self):
        self.task.expand(context="Test")
        self.task.expand(context="Another context")
        self.expectInXML('''expandedContexts="('Another context', 'Test')"''')

    def testCategoryExpansionState(self):
        cat = category.Category("cat")
        self.categoryContainer.append(cat)
        cat.expand()
        self.expectInXML('''expandedContexts="('None',)"''')

    def testNoteExpansionState(self):
        self.note.expand()
        self.expectInXML('''expandedContexts="('None',)"''')

    def testPercentageComplete(self):
        self.task.setPercentageComplete(50)
        self.expectInXML('''percentageComplete="50"''')

    def testPercentageComplete_Float(self):
        self.task.setPercentageComplete(50.0)
        self.expectInXML('''percentageComplete="50.0"''')

    def testExclusiveSubcategories(self):
        self.category.makeSubcategoriesExclusive()
        self.expectInXML('''exclusiveSubcategories="True"''')

    def testNonExclusiveSubcategoriesByDefault(self):
        self.expectNotInXML("""exclusiveSubcategories""")

    def testTaskFont(self):
        self.task.setFont(wx.SWISS_FONT)
        self.expectInXML('font="%s"' % wx.SWISS_FONT.GetNativeFontInfoDesc())

    def testNoTaskFontByDefault(self):
        self.expectNotInXML("font")

    def testNoteFont(self):
        self.note.setFont(wx.SWISS_FONT)
        self.expectInXML('font="%s"' % wx.SWISS_FONT.GetNativeFontInfoDesc())

    def testCategoryFont(self):
        self.category.setFont(wx.SWISS_FONT)
        self.expectInXML('font="%s"' % wx.SWISS_FONT.GetNativeFontInfoDesc())

    def testAttachmentFont(self):
        att = attachment.FileAttachment(
            "whatever.txt", id="foo", font=wx.SWISS_FONT
        )
        self.task.addAttachments(att)
        self.expectInXML('font="%s"' % wx.SWISS_FONT.GetNativeFontInfoDesc())

    def testNonAsciiFontName(self):
        class FakeFont(object):
            def GetNativeFontInfoDesc(self):
                return "微软雅黑"

        font = FakeFont()
        self.task.setFont(font)
        self.expectInXML('font="微软雅黑"')

    def testTaskIcon(self):
        self.task.setIcon("icon")
        self.expectInXML('icon="icon"')

    def testNoTaskIcon(self):
        self.expectNotInXML("icon")

    def testSelectedTaskIcon(self):
        self.task.setSelectedIcon("icon")
        self.expectInXML('selectedIcon="icon"')

    def testNoSelectedTaskIcon(self):
        self.expectNotInXML("selectedIcon")

    def testNoteIcon(self):
        self.note.setIcon("icon")
        self.expectInXML('icon="icon"')

    def testSelectedNoteIcon(self):
        self.note.setSelectedIcon("icon")
        self.expectInXML('selectedIcon="icon"')

    def testCategoryIcon(self):
        self.category.setIcon("icon")
        self.expectInXML('icon="icon"')

    def testSelectedCategoryIcon(self):
        self.category.setSelectedIcon("icon")
        self.expectInXML('selectedIcon="icon"')

    def testAttachmentIcon(self):
        att = attachment.FileAttachment("whatever.txt", id="foo", icon="icon")
        self.task.addAttachments(att)
        self.expectInXML('icon="icon"')

    def testSelectedAttachmentIcon(self):
        att = attachment.FileAttachment("whatever.txt", selectedIcon="icon")
        self.task.addAttachments(att)
        self.expectInXML('selectedIcon="icon"')

    def testPrerequisite(self):
        prerequisite = task.Task(subject="prereq")
        self.taskList.append(prerequisite)
        self.task.addPrerequisites([prerequisite])
        self.expectInXML('prerequisites="%s"' % prerequisite.id())

    def testMultiplePrerequisites(self):
        # Use the same id's for both prerequisites because we don't know in
        # what order they will end up in the XML.
        prerequisites = [
            task.Task(subject="prereq1", id="id"),
            task.Task(subject="prereq2", id="id"),
        ]
        self.taskList.extend(prerequisites)
        self.task.addPrerequisites(prerequisites)
        self.expectInXML('prerequisites="id id"')

    def testEncodingAttribute(self):
        self.expectInXML('encoding="utf-8"')

    def testCreationDateTime(self):
        self.expectInXML(
            'creationDateTime="%s"' % str(self.task.creationDateTime())
        )

    def testDoNotWriteUnknownCreationDateTime(self):
        task_with_unknown_creation_datetime = task.Task(
            creationDateTime=date.DateTime.min
        )
        self.taskList.append(task_with_unknown_creation_datetime)
        self.expectNotInXML('creationDateTime="0001-01-01 00:00:00"')

    def testModificationDateTime(self):
        self.task.setModificationDateTime(date.DateTime(2013, 1, 1, 0, 0, 0))
        self.expectInXML('modificationDateTime="2013-01-01 00:00:00"')

    def testDoNotWriteUnknownModificationDateTime(self):
        task_with_unknown_modification_datetime = task.Task(
            modificationDateTime=date.DateTime.min
        )
        self.expectNotInXML('modificationDateTime="0001-01-01 00:00:00"')
