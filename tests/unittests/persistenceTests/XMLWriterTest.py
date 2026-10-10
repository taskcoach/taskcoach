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
import re
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

_DATES = re.compile(r' (?:creation|modification)DateTime="[^"]*"')


class XMLWriterTest(test.TestCase):
    def setUp(self):
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
        )
        return self.fd.getvalue().decode("utf-8")

    def expect_in_xml(self, xml_fragment):
        xml = sorted_attributes(self.__writeAndRead())
        xml_fragment = sorted_attributes(xml_fragment)
        self.assertTrue(
            xml_fragment in xml or xml_fragment in xml.replace("&apos;", "'"),
            "%s not in %s" % (xml_fragment, xml),
        )

    def expect_in_xml_without_dates(self, xml_fragment):
        """The fragment's structure, whatever the items' creation and
        modification dates."""
        xml = _DATES.sub("", sorted_attributes(self.__writeAndRead()))
        xml_fragment = _DATES.sub("", sorted_attributes(xml_fragment))
        self.assertTrue(
            xml_fragment in xml, "%s not in %s" % (xml_fragment, xml)
        )

    def expect_not_in_xml(self, xml_fragment):
        xml = sorted_attributes(self.__writeAndRead())
        xml_fragment = sorted_attributes(xml_fragment)
        self.assertFalse(xml_fragment in xml, "%s in %s" % (xml_fragment, xml))

    # tests

    def test_version(self):
        self.expect_in_xml('<?taskcoach release="%s"' % meta.data.version)

    def test_no_guid_is_written(self):
        self.expect_not_in_xml("guid")

    def test_task_subject(self):
        self.task.setSubject("Subject")
        self.expect_in_xml('subject="Subject"')

    def test_task_subject_with_unicode(self):
        self.task.setSubject("ï¬Ÿï­Žï­–")
        self.expect_in_xml('subject="ï¬Ÿï­Žï­–"')

    def test_task_description(self):
        self.task.setDescription("Description")
        self.expect_in_xml("<description>\nDescription\n</description>\n")

    def test_empty_task_description_is_not_written(self):
        self.expect_not_in_xml("<description>")

    def test_task_planned_start_date_time(self):
        self.task.set_planned_start_date_time(
            date.DateTime(2004, 1, 1, 11, 0, 0)
        )
        self.expect_in_xml(
            'plannedstartdate="%s"' % str(self.task.plannedStartDateTime())
        )

    def test_no_planned_start_date_time(self):
        self.task.set_planned_start_date_time(date.DateTime())
        self.expect_not_in_xml("plannedstartdate=")

    def test_task_actual_start_date_time(self):
        self.task.set_actual_start_date_time(
            date.DateTime(2007, 12, 31, 9, 0, 0)
        )
        self.expect_in_xml(
            'actualstartdate="%s"' % str(self.task.actualStartDateTime())
        )

    def test_no_actual_start_date_time(self):
        self.task.set_actual_start_date_time(date.DateTime())
        self.expect_not_in_xml("actualstartdate=")

    def test_task_due_date_time(self):
        self.task.set_due_date_time(date.DateTime(2004, 1, 1, 10, 5, 5))
        self.expect_in_xml('duedate="%s"' % str(self.task.dueDateTime()))

    def test_no_due_date_time(self):
        self.expect_not_in_xml("duedate=")

    def test_task_completion_date_time(self):
        self.task.set_completion_date_time(date.DateTime(2004, 1, 1, 10, 8, 4))
        self.expect_in_xml(
            'completiondate="%s"' % str(self.task.completionDateTime())
        )

    def test_no_completion_date_time(self):
        self.expect_not_in_xml("completiondate=")

    def test_child_task(self):
        self.task.addChild(task.Task(subject="child"))
        self.expect_in_xml('subject="child" />\n</task>\n<category')

    def test_effort(self):
        task_effort = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1),
            date.DateTime(2004, 1, 2),
            description="description\nline 2",
        )
        self.task.addEffort(task_effort)
        self.expect_in_xml_without_dates(
            '<effort id="%s" start="%s" stop="%s" creationDateTime="%s">\n'
            "<description>\ndescription\nline 2\n</description>\n"
            "</effort>"
            % (
                task_effort.id(),
                task_effort.getStart(),
                task_effort.getStop(),
                task_effort.creationDateTime(),
            )
        )

    def test_effort_dates_are_written(self):
        self.task.addEffort(
            effort.Effort(
                self.task,
                date.DateTime(2004, 1, 1),
                creationDateTime=date.Timestamp(2004, 1, 1, 0, 0, 0, 1),
                modificationDateTime=date.Timestamp(2005, 1, 1, 0, 0, 0, 2),
            )
        )
        self.expect_in_xml('creationDateTime="2004-01-01 00:00:00.000001"')
        self.expect_in_xml('modificationDateTime="2005-01-01 00:00:00.000002"')

    def test_that_effort_times_do_not_contain_milliseconds(self):
        self.task.addEffort(
            effort.Effort(
                self.task,
                date.DateTime(2004, 1, 1, 10, 0, 0, 123456),
                date.DateTime(2004, 1, 1, 10, 0, 10, 654310),
            )
        )
        self.expect_in_xml('start="2004-01-01 10:00:00"')
        self.expect_in_xml('stop="2004-01-01 10:00:10"')

    def test_that_effort_start_and_stop_are_not_equal(self):
        self.task.addEffort(
            effort.Effort(
                self.task,
                date.DateTime(2004, 1, 1, 10, 0, 0, 123456),
                date.DateTime(2004, 1, 1, 10, 0, 0, 654310),
            )
        )
        self.expect_in_xml('start="2004-01-01 10:00:00"')
        self.expect_in_xml('stop="2004-01-01 10:00:01"')

    def test_empty_effort_description_is_not_written(self):
        self.task.addEffort(
            effort.Effort(
                self.task, date.DateTime(2004, 1, 1), date.DateTime(2004, 1, 2)
            )
        )
        self.expect_not_in_xml("<description>")

    def test_active_effort(self):
        self.task.addEffort(
            effort.Effort(self.task, date.DateTime(2004, 1, 1))
        )
        active = self.task.efforts()[0]
        self.expect_in_xml_without_dates(
            '<effort id="%s" start="%s" creationDateTime="%s" />'
            % (active.id(), active.getStart(), active.creationDateTime())
        )

    def test_no_effort_by_default(self):
        self.expect_not_in_xml("<efforts>")

    def test_budget(self):
        self.task.set_budget(date.ONE_HOUR)
        self.expect_in_xml('budget="%s"' % str(self.task.budget()))

    def test_no_budget(self):
        self.expect_not_in_xml("budget")

    def test_budget_more_than_24_hour(self):
        self.task.set_budget(date.TimeDelta(hours=25))
        self.expect_in_xml('budget="25:00:00"')

    def test_one_category_without_task(self):
        a_category = category.Category("test", id="id")
        self.categoryContainer.append(a_category)
        self.expect_in_xml_without_dates(
            '<category creationDateTime="%s" id="id" '
            'subject="test" />' % a_category.creationDateTime()
        )

    def expect_categories(self, item, *categories):
        """The item's node lists its categories, sorted by ID
        (format 38)."""
        category_ids = " ".join(sorted(each.id() for each in categories))
        self.expect_in_xml_without_dates(
            'categories="%s" id="%s"' % (category_ids, item.id())
        )

    def test_task_with_one_category(self):
        cat = category.Category("test", [self.task])
        self.categoryContainer.append(cat)
        self.expect_categories(self.task, cat)

    def test_task_with_two_categories(self):
        cats = [category.Category(each, [self.task]) for each in "ab"]
        self.categoryContainer.extend(cats)
        self.expect_categories(self.task, *cats)

    def test_category_lists_its_members_for_older_releases(self):
        self.categoryContainer.append(
            category.Category("test", [self.task, self.note])
        )
        members = " ".join(sorted([self.task.id(), self.note.id()]))
        self.expect_in_xml('categorizables="%s"' % members)

    def test_members_outside_the_file_are_not_listed(self):
        self.categoryContainer.append(category.Category("test", [task.Task()]))
        self.expect_not_in_xml("categorizables")

    def test_both_format_versions(self):
        # tskversion: what a reader needs, which older releases check;
        # tskformat: the format written
        self.expect_in_xml('tskversion="37" tskformat="40"')

    def test_subtask_with_category(self):
        child = task.Task()
        self.taskList.append(child)
        self.task.addChild(child)
        cat = category.Category("test", [child])
        self.categoryContainer.append(cat)
        self.expect_categories(child, cat)

    def test_sub_category_without_tasks(self):
        parent = category.Category(subject="parent")
        child = category.Category(subject="child")
        parent.addChild(child)
        self.categoryContainer.extend([parent, child])
        self.expect_in_xml_without_dates(
            '<category creationDateTime="%s" id="%s" '
            'subject="parent">\n'
            '<category creationDateTime="%s" id="%s" '
            'subject="child" />\n</category>'
            % (
                parent.creationDateTime(),
                parent.id(),
                child.creationDateTime(),
                child.id(),
            )
        )

    def test_task_with_subcategory(self):
        parent = category.Category(subject="parent")
        child = category.Category(subject="child", members=[self.task])
        parent.addChild(child)
        self.categoryContainer.extend([parent, child])
        self.expect_categories(self.task, child)

    def test_filtered_category(self):
        self.categoryContainer.extend(
            [category.Category(subject="test", filtered=True)]
        )
        self.expect_in_xml('filtered="True"')

    def test_category_with_description(self):
        a_category = category.Category(
            subject="subject", description="Description", id="id"
        )
        self.categoryContainer.append(a_category)
        self.expect_in_xml_without_dates(
            '<category creationDateTime="%s" id="id" subject="subject">\n'
            "<description>\nDescription\n</description>\n"
            "</category>" % str(a_category.creationDateTime())
        )

    def test_category_with_unicode_subject(self):
        unicode_category = category.Category(subject="ï¬Ÿï­Žï­–", id="id")
        self.categoryContainer.extend([unicode_category])
        self.expect_in_xml('subject="ï¬Ÿï­Žï­–"')

    def test_no_link_to_a_category_outside_the_file(self):
        # A template or a saved selection holds only some categories
        self.task.addCategory(category.Category(subject="elsewhere"))
        self.expect_not_in_xml("categories=")

    def test_default_priority(self):
        self.expect_not_in_xml("priority")

    def test_priority(self):
        self.task.setPriority(5)
        self.expect_in_xml('priority="5"')

    def test_task_id(self):
        self.expect_in_xml('id="%s"' % self.task.id())

    def test_category_id(self):
        a_category = category.Category(subject="category")
        self.categoryContainer.append(a_category)
        self.expect_in_xml('id="%s"' % a_category.id())

    def test_note_id(self):
        self.expect_in_xml('id="%s"' % self.note.id())

    def test_two_tasks(self):
        self.task.setSubject("task 1")
        task2 = task.Task(subject="task 2")
        self.taskList.append(task2)
        self.expect_in_xml('subject="task 2"')

    def test_default_hourly_fee(self):
        self.expect_not_in_xml("hourlyFee")

    def test_hourly_fee(self):
        self.task.set_hourly_fee(100)
        self.expect_in_xml('hourlyFee="100"')

    def test_default_fixed_fee(self):
        self.expect_not_in_xml("fixedFee")

    def test_fixed_fee(self):
        self.task.set_fixed_fee(1000)
        self.expect_in_xml('fixedFee="1000"')

    def test_no_reminder(self):
        self.expect_not_in_xml("reminder")

    def test_reminder(self):
        self.task.set_reminder(date.DateTime(2005, 5, 7, 13, 15, 10))
        self.expect_in_xml('reminder="%s"' % str(self.task.reminder()))
        self.expect_not_in_xml("reminderBeforeSnooze")

    def test_snoozed_reminder(self):
        now = date.Now()
        self.task.set_reminder(now + date.TimeDelta(seconds=30))
        self.task.snooze_reminder(date.TimeDelta(seconds=120), now=lambda: now)
        self.expect_in_xml('reminder="%s"' % str(self.task.reminder()))
        self.expect_in_xml(
            'reminderBeforeSnooze="%s"'
            % str(self.task.reminder(include_snooze=False))
        )

    def test_reminder_is_none_but_snoozed_reminder_not(self):
        now = date.Now()
        self.task.set_reminder(now + date.TimeDelta(seconds=30))
        self.task.snooze_reminder(date.TimeDelta())
        self.expect_not_in_xml("reminder")

    def test_mark_completed_when_all_children_are_completed_setting_none(self):
        self.expect_not_in_xml("shouldMarkCompletedWhenAllChildrenCompleted")

    def test_mark_completed_when_all_children_are_completed_setting_true(self):
        self.task.set_should_mark_completed_when_all_children_completed(True)
        self.expect_in_xml(
            'shouldMarkCompletedWhenAllChildrenCompleted="True"'
        )

    def test_mark_completed_when_all_children_are_completed_setting_false(
        self,
    ):
        self.task.set_should_mark_completed_when_all_children_completed(False)
        self.expect_in_xml(
            'shouldMarkCompletedWhenAllChildrenCompleted="False"'
        )

    def test_note(self):
        a_note = note.Note(id="id")
        self.noteContainer.append(a_note)
        self.expect_in_xml_without_dates(
            '<note creationDateTime="%s" id="id" '
            "/>" % a_note.creationDateTime()
        )

    def test_note_with_subject(self):
        self.noteContainer.append(note.Note(subject="Note"))
        self.expect_in_xml('subject="Note"')

    def test_note_with_description(self):
        self.noteContainer.append(note.Note(description="Description"))
        self.expect_in_xml("<description>\nDescription\n</description>\n")

    def test_note_with_child(self):
        child = note.Note(id="child")
        self.note.addChild(child)
        self.noteContainer.append(child)
        self.expect_in_xml_without_dates(
            '<note creationDateTime="%s" id="%s">\n'
            '<note creationDateTime="%s" id="child" />\n'
            "</note>"
            % (
                self.note.creationDateTime(),
                self.note.id(),
                child.creationDateTime(),
            )
        )

    def test_note_with_category(self):
        cat = category.Category(subject="cat")
        self.categoryContainer.append(cat)
        self.note.addCategory(cat)
        self.expect_categories(self.note, cat)

    def test_category_foreground_color(self):
        self.categoryContainer.append(
            category.Category(subject="test", fgColor=wx.RED)
        )
        self.expect_in_xml('fgColor="(255, 0, 0, 255)"')

    def test_category_background_color(self):
        self.categoryContainer.append(
            category.Category(subject="test", bgColor=wx.RED)
        )
        self.expect_in_xml('bgColor="(255, 0, 0, 255)"')

    def test_dont_write_inherited_category_foreground_color(self):
        parent = category.Category(subject="test", fgColor=wx.RED)
        child = category.Category(subject="child", id="id")
        parent.addChild(child)
        self.categoryContainer.append(parent)
        self.expect_in_xml_without_dates(
            '<category creationDateTime="%s" id="id" '
            'subject="child" />' % child.creationDateTime()
        )

    def test_dont_write_inherited_category_background_color(self):
        parent = category.Category(subject="test", bgColor=wx.RED)
        child = category.Category(subject="child", id="id")
        parent.addChild(child)
        self.categoryContainer.append(parent)
        self.expect_in_xml_without_dates(
            '<category creationDateTime="%s" id="id" '
            'subject="child" />' % child.creationDateTime()
        )

    def test_task_foreground_color(self):
        self.task.setForegroundColor(wx.RED)
        self.expect_in_xml('fgColor="(255, 0, 0, 255)"')

    def test_task_background_color(self):
        self.task.setBackgroundColor(wx.RED)
        self.expect_in_xml('bgColor="(255, 0, 0, 255)"')

    def test_dont_write_inherited_task_foreground_color(self):
        self.task.setForegroundColor(wx.RED)
        child = task.Task(
            subject="child", id="id", plannedStartDateTime=date.DateTime()
        )
        self.task.addChild(child)
        self.taskList.append(child)
        self.expect_in_xml_without_dates(
            '<task creationDateTime="%s" id="id" '
            'subject="child" />' % child.creationDateTime()
        )

    def test_dont_write_inherited_task_background_color(self):
        self.task.setBackgroundColor(wx.RED)
        child = task.Task(
            subject="child", id="id", plannedStartDateTime=date.DateTime()
        )
        self.task.addChild(child)
        self.taskList.append(child)
        self.expect_in_xml_without_dates(
            '<task creationDateTime="%s" id="id" '
            'subject="child" />' % child.creationDateTime()
        )

    def test_note_foreground_color(self):
        self.note.setForegroundColor(wx.RED)
        self.expect_in_xml('fgColor="(255, 0, 0, 255)"')

    def test_note_background_color(self):
        self.note.setBackgroundColor(wx.RED)
        self.expect_in_xml('bgColor="(255, 0, 0, 255)"')

    def test_dont_write_inherited_note_foreground_color(self):
        parent = note.Note(fgColor=wx.RED)
        child = note.Note(subject="child", id="id")
        parent.addChild(child)
        self.noteContainer.append(parent)
        self.expect_in_xml_without_dates(
            '<note creationDateTime="%s" id="id" '
            'subject="child" />' % child.creationDateTime()
        )

    def test_dont_write_inherited_note_background_color(self):
        parent = note.Note(bgColor=wx.RED)
        child = note.Note(subject="child", id="id")
        parent.addChild(child)
        self.noteContainer.append(parent)
        self.expect_in_xml_without_dates(
            '<note creationDateTime="%s" id="id" '
            'subject="child" />' % child.creationDateTime()
        )

    def test_no_recurencce(self):
        self.expect_not_in_xml("recurrence")

    def test_daily_recurrence(self):
        self.task.set_recurrence(date.Recurrence("daily"))
        self.expect_in_xml('<recurrence unit="daily" />')

    def test_weekly_recurrence(self):
        self.task.set_recurrence(date.Recurrence("weekly"))
        self.expect_in_xml('<recurrence unit="weekly" />')

    def test_monthly_recurrence(self):
        self.task.set_recurrence(date.Recurrence("monthly"))
        self.expect_in_xml('<recurrence unit="monthly" />')

    def test_monthly_recurrence_on_same_weekday(self):
        self.task.set_recurrence(date.Recurrence("monthly", sameWeekday=True))
        self.expect_in_xml('<recurrence sameWeekday="True" unit="monthly" />')

    def test_yearly_recurrence(self):
        self.task.set_recurrence(date.Recurrence("yearly"))
        self.expect_in_xml('<recurrence unit="yearly" />')

    def test_recurrence_count(self):
        self.task.set_recurrence(date.Recurrence("daily", count=5))
        self.expect_in_xml('count="5"')

    def test_max_recurrence_count(self):
        self.task.set_recurrence(date.Recurrence("daily", maximum=5))
        self.expect_in_xml('max="5"')

    def test_recurrence_stop_date_time(self):
        stop_datetime = date.DateTime(2000, 1, 1, 10, 9, 8)
        self.task.set_recurrence(
            date.Recurrence("daily", stop_datetime=stop_datetime)
        )
        self.expect_in_xml('stop_datetime="%s"' % str(stop_datetime))

    def test_recurrence_frequency(self):
        self.task.set_recurrence(date.Recurrence("daily", amount=2))
        self.expect_in_xml('amount="2"')

    def test_recurrence_based_on_completion(self):
        self.task.set_recurrence(
            date.Recurrence("daily", recurBasedOnCompletion=True)
        )
        self.expect_in_xml('recurBasedOnCompletion="True"')

    def test_no_attachments(self):
        self.expect_not_in_xml("attachment")

    # addAttachment, addNote, etc., are dynamically generated so pylint can't
    # find them. Disable the error message.
    # pylint: disable=E1101

    def test_task_with_one_attachment(self):
        task_attachment = attachment.FileAttachment("whatever.txt", id="foo")
        self.task.addAttachments(task_attachment)
        self.expect_in_xml_without_dates(
            '<attachment creationDateTime="%s" id="foo" '
            'location="whatever.txt" '
            'subject="whatever" type="file" '
            "/>" % task_attachment.creationDateTime()
        )

    def test_object_with_attachment_with_note(self):
        att = attachment.FileAttachment("whatever.txt", id="foo")
        self.task.addAttachments(att)
        attachment_note = note.Note(subject="attnote", id="spam")
        att.addNote(attachment_note)
        self.expect_in_xml_without_dates(
            '<attachment creationDateTime="%s" id="foo" '
            'location="whatever.txt" '
            'subject="whatever" type="file">\n'
            "<note" % att.creationDateTime()
        )

    def test_mail_attachment_fields(self):
        self.task.addAttachments(
            attachment.MailAttachment(
                "mid:1@example.com",
                id="foo",
                subject="Quote",
                from_name="Alice",
                from_address="alice@example.com",
                sent_datetime=date.DateTime(2026, 9, 29, 14, 5, 0),
            )
        )
        self.expect_in_xml_without_dates(
            '<attachment fromAddress="alice@example.com" fromName="Alice" '
            'id="foo" location="mid:1@example.com" '
            'sentDateTime="2026-09-29 14:05:00" subject="Quote" type="uri"'
        )

    def test_a_mail_file_stays_a_mail(self):
        # Older releases read a mail from its file, not from a link
        self.task.addAttachments(
            attachment.MailAttachment("mail.eml", id="foo", subject="Mail")
        )
        self.expect_in_xml_without_dates(
            '<attachment id="foo" location="mail.eml" subject="Mail" '
            'type="mail"'
        )

    def test_empty_mail_fields_are_not_written(self):
        self.task.addAttachments(
            attachment.MailAttachment("mid:1@example.com", id="foo")
        )
        for name in ("fromName", "fromAddress", "sentDateTime"):
            self.expect_not_in_xml(name)

    def test_note_with_one_attachment(self):
        note_attachment = attachment.FileAttachment("whatever.txt", id="foo")
        self.note.addAttachments(note_attachment)
        self.expect_in_xml_without_dates(
            '<attachment creationDateTime="%s" id="foo" '
            'location="whatever.txt" '
            'subject="whatever" type="file" '
            "/>" % note_attachment.creationDateTime()
        )

    def test_category_with_one_attachment(self):
        cat = category.Category("cat")
        self.categoryContainer.append(cat)
        category_attachment = attachment.FileAttachment(
            "whatever.txt", id="foo"
        )
        cat.addAttachments(category_attachment)
        self.expect_in_xml_without_dates(
            '<attachment creationDateTime="%s" id="foo" '
            'location="whatever.txt" '
            'subject="whatever" type="file" '
            "/>" % category_attachment.creationDateTime()
        )

    def test_task_with_two_attachments(self):
        attachments = [
            attachment.FileAttachment("whatever.txt"),
            attachment.FileAttachment("/home/frank/attachment.doc"),
        ]
        for a in attachments:
            self.task.addAttachments(a)
        for att in attachments:
            self.expect_in_xml_without_dates(
                '<attachment creationDateTime="%s" id="%s" '
                'location="%s" subject="%s" type="file" '
                "/>"
                % (
                    att.creationDateTime(),
                    att.id(),
                    att.location(),
                    att.subject(),
                )
            )

    def test_task_with_note(self):
        self.task.addNote(self.note)
        self.expect_in_xml_without_dates(
            '>\n<note creationDateTime="%s" id="%s" '
            "/>\n</task>" % (self.note.creationDateTime(), self.note.id())
        )

    def test_task_with_notes(self):
        another_note = note.Note(subject="Another note", id="id")
        self.task.addNote(self.note)
        self.task.addNote(another_note)
        self.expect_in_xml_without_dates(
            '>\n<note creationDateTime="%s" id="%s" />\n'
            '<note creationDateTime="%s" id="id" subject="Another note" '
            "/>\n</task>"
            % (
                self.note.creationDateTime(),
                self.note.id(),
                another_note.creationDateTime(),
            )
        )

    def test_task_with_nested_notes(self):
        sub_note = note.Note(subject="Subnote", id="id")
        self.note.addChild(sub_note)
        self.task.addNote(self.note)
        self.expect_in_xml_without_dates(
            '>\n<note creationDateTime="%s" id="%s">\n'
            '<note creationDateTime="%s" id="id" subject="Subnote" '
            "/>\n</note>\n</task>"
            % (
                self.note.creationDateTime(),
                self.note.id(),
                sub_note.creationDateTime(),
            )
        )

    def test_note_of_a_task_with_category(self):
        new_note = note.Note()
        self.task.addNote(new_note)
        new_note.addCategory(self.category)
        self.expect_categories(new_note, self.category)

    def test_subnote_of_a_task_with_category(self):
        new_note = note.Note()
        new_sub_note = note.Note()
        new_note.addChild(new_sub_note)
        self.task.addNote(new_note)
        new_sub_note.addCategory(self.category)
        self.expect_categories(new_sub_note, self.category)

    def test_note_of_an_attachment_with_category(self):
        task_attachment = attachment.FileAttachment("whatever.txt")
        attachment_note = note.Note()
        task_attachment.addNote(attachment_note)
        self.task.addAttachments(task_attachment)
        attachment_note.addCategory(self.category)
        self.expect_categories(attachment_note, self.category)

    def test_category_with_note(self):
        self.category.addNote(self.note)
        self.expect_in_xml_without_dates(
            '>\n<note creationDateTime="%s" id="%s" '
            "/>\n</category>" % (self.note.creationDateTime(), self.note.id())
        )

    def test_category_with_notes(self):
        another_note = note.Note(subject="Another note", id="id")
        self.category.addNote(self.note)
        self.category.addNote(another_note)
        self.expect_in_xml_without_dates(
            '>\n<note creationDateTime="%s" id="%s" />\n'
            '<note creationDateTime="%s" id="id" subject="Another '
            'note" />\n</category>'
            % (
                self.note.creationDateTime(),
                self.note.id(),
                another_note.creationDateTime(),
            )
        )

    def test_category_with_nested_notes(self):
        sub_note = note.Note(subject="Subnote", id="id")
        self.note.addChild(sub_note)
        self.category.addNote(self.note)
        self.expect_in_xml_without_dates(
            '>\n<note creationDateTime="%s" id="%s">\n'
            '<note creationDateTime="%s" id="id" subject="Subnote" '
            "/>\n</note>\n</category>"
            % (
                self.note.creationDateTime(),
                self.note.id(),
                sub_note.creationDateTime(),
            )
        )

    def test_task_default_expansion_state(self):
        # Don't write anything if the task is not expanded:
        self.expect_not_in_xml("expandedContexts")

    def test_task_expansion_state(self):
        self.task.expand()
        self.expect_in_xml('''expandedContexts="('None',)"''')

    def test_task_expansion_state_specific_context(self):
        self.task.expand(context="Test")
        self.expect_in_xml('''expandedContexts="('Test',)"''')

    def test_task_expansion_state_multiple_contexts(self):
        self.task.expand(context="Test")
        self.task.expand(context="Another context")
        self.expect_in_xml(
            '''expandedContexts="('Another context', 'Test')"'''
        )

    def test_category_expansion_state(self):
        cat = category.Category("cat")
        self.categoryContainer.append(cat)
        cat.expand()
        self.expect_in_xml('''expandedContexts="('None',)"''')

    def test_note_expansion_state(self):
        self.note.expand()
        self.expect_in_xml('''expandedContexts="('None',)"''')

    def test_percentage_complete(self):
        self.task.setPercentageComplete(50)
        self.expect_in_xml('''percentageComplete="50"''')

    def test_percentage_complete_float(self):
        self.task.setPercentageComplete(50.0)
        self.expect_in_xml('''percentageComplete="50.0"''')

    def test_exclusive_subcategories(self):
        self.category.makeSubcategoriesExclusive()
        self.expect_in_xml('''exclusiveSubcategories="True"''')

    def test_non_exclusive_subcategories_by_default(self):
        self.expect_not_in_xml("""exclusiveSubcategories""")

    def test_style_priority(self):
        self.category.setStylePriority(3)
        self.expect_in_xml('stylePriority="3"')

    def test_no_style_priority_by_default(self):
        self.expect_not_in_xml("stylePriority")

    def test_task_font(self):
        self.task.setFont(wx.SWISS_FONT)
        self.expect_in_xml('font="%s"' % wx.SWISS_FONT.GetNativeFontInfoDesc())

    def test_no_task_font_by_default(self):
        self.expect_not_in_xml("font")

    def test_note_font(self):
        self.note.setFont(wx.SWISS_FONT)
        self.expect_in_xml('font="%s"' % wx.SWISS_FONT.GetNativeFontInfoDesc())

    def test_category_font(self):
        self.category.setFont(wx.SWISS_FONT)
        self.expect_in_xml('font="%s"' % wx.SWISS_FONT.GetNativeFontInfoDesc())

    def test_attachment_font(self):
        att = attachment.FileAttachment(
            "whatever.txt", id="foo", font=wx.SWISS_FONT
        )
        self.task.addAttachments(att)
        self.expect_in_xml('font="%s"' % wx.SWISS_FONT.GetNativeFontInfoDesc())

    def test_non_ascii_font_name(self):
        class FakeFont(object):
            def GetNativeFontInfoDesc(self):
                return "微软雅黑"

        font = FakeFont()
        self.task.setFont(font)
        self.expect_in_xml('font="微软雅黑"')

    def test_task_icon(self):
        self.task.set_icon_id("icon")
        self.expect_in_xml('icon="icon"')

    def test_no_task_icon(self):
        self.expect_not_in_xml("icon")

    def test_no_icon_override_is_a_field_older_releases_ignore(self):
        self.task.set_icon_id(base.NO_ICON)
        self.expect_in_xml('noIcon="True"')
        self.expect_not_in_xml("icon=")

    def test_preview_shown_is_a_field_older_releases_ignore(self):
        self.task.show_preview()
        self.expect_in_xml('previewShown="True"')

    def test_hidden_preview_is_left_out(self):
        self.expect_not_in_xml("previewShown")

    def test_note_icon(self):
        self.note.set_icon_id("icon")
        self.expect_in_xml('icon="icon"')

    def test_category_icon(self):
        self.category.set_icon_id("icon")
        self.expect_in_xml('icon="icon"')

    def test_attachment_icon(self):
        att = attachment.FileAttachment("whatever.txt", id="foo", icon="icon")
        self.task.addAttachments(att)
        self.expect_in_xml('icon="icon"')

    def test_prerequisite(self):
        prerequisite = task.Task(subject="prereq")
        self.taskList.append(prerequisite)
        self.task.add_prerequisites([prerequisite])
        self.expect_in_xml('prerequisites="%s"' % prerequisite.id())

    def test_multiple_prerequisites(self):
        # Written sorted by id
        prerequisites = [
            task.Task(subject="prereq2", id="id2"),
            task.Task(subject="prereq1", id="id1"),
        ]
        self.taskList.extend(prerequisites)
        self.task.add_prerequisites(prerequisites)
        self.expect_in_xml('prerequisites="id1 id2"')

    def test_encoding_attribute(self):
        self.expect_in_xml('encoding="utf-8"')

    def test_creation_date_time(self):
        self.expect_in_xml(
            'creationDateTime="%s"' % str(self.task.creationDateTime())
        )

    def test_creation_date_is_written_with_its_fraction(self):
        self.taskList.append(
            task.Task(
                creationDateTime=date.Timestamp(2013, 1, 1, 0, 0, 0, 123456)
            )
        )
        self.expect_in_xml('creationDateTime="2013-01-01 00:00:00.123456"')

    def test_do_not_write_unknown_creation_date_time(self):
        task_with_unknown_creation_datetime = task.Task(
            creationDateTime=date.DateTime.min
        )
        self.taskList.append(task_with_unknown_creation_datetime)
        self.expect_not_in_xml('creationDateTime="0001-01-01 00:00:00"')

    def test_modification_date_time(self):
        self.task.set_modification_datetime(date.DateTime(2013, 1, 1, 0, 0, 0))
        self.expect_in_xml('modificationDateTime="2013-01-01 00:00:00"')

    def test_modification_date_is_written_with_its_fraction(self):
        self.task.set_modification_datetime(
            date.Timestamp(2013, 1, 1, 0, 0, 0, 123456)
        )
        self.expect_in_xml('modificationDateTime="2013-01-01 00:00:00.123456"')

    def test_a_modification_date_equal_to_the_creation_date_is_left_out(
        self,
    ):
        self.task.set_modification_datetime(self.task.creationDateTime())
        self.expect_not_in_xml("modificationDateTime")

    def test_do_not_write_unknown_modification_date_time(self):
        task_with_unknown_modification_datetime = task.Task(
            modificationDateTime=date.DateTime.min
        )
        self.expect_not_in_xml('modificationDateTime="0001-01-01 00:00:00"')
