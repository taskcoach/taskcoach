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

from xml.etree import ElementTree
import wx
import io
import os
import base64
import sys
import test
from taskcoachlib import persistence, config, operating_system
from taskcoachlib.domain import attachment, category, date, note, task
from taskcoachlib.patterns.field import fields


class XMLTemplateReaderTestCase(test.TestCase):
    def convert(self, old_format, now=date.Now):
        return persistence.TemplateXMLReader.convert_old_format(
            old_format, now
        )

    def test_convert_now(self):
        self.assertEqual("now", self.convert("Now()"))

    def test_convert_today(self):
        self.assertEqual("00:00 AM today", self.convert("Today()"))

    def test_convert_tomorrow(self):
        self.assertEqual("11:59 PM tomorrow", self.convert("Tomorrow()"))

    def test_convert_end_of_day(self):
        self.assertEqual("11:59 PM today", self.convert("Now().endOfDay()"))

    def test_convert_tomorrow_2(self):
        self.assertEqual(
            "11:59 PM tomorrow", self.convert("Now().endOfDay() + oneDay")
        )

    def test_convert_now_and_positive_time_delta(self):
        self.assertEqual(
            "%d minutes from now" % date.TimeDelta(2, 1861, 0).minutes(),
            self.convert("Now() + TimeDelta(2, 1861, 0)"),
        )

    def test_convert_now_and_negative_time_delta(self):
        self.assertEqual(
            "%d minutes ago" % date.TimeDelta(2, 1861, 0).minutes(),
            self.convert("Now() - TimeDelta(2, 1861, 0)"),
        )

    def test_convert_today_and_positive_time_delta(self):
        now = date.Now()
        expected_date = date.Now() + date.TimeDelta(17)
        expected_date_time = date.DateTime(
            expected_date.year, expected_date.month, expected_date.day
        )
        expected_minutes = (expected_date_time - now).minutes()
        actual_minutes = int(
            self.convert("Today() + TimeDelta(17)").split(" ")[0]
        )
        self.assertTrue(abs(actual_minutes - expected_minutes) <= 1)

    def test_convert_today_and_zero_time_delta(self):
        now = date.Now()
        expected_minutes = (now - now.startOfDay()).minutes()
        actual_minutes = int(
            self.convert("Today() + TimeDelta(0)").split(" ")[0]
        )
        self.assertTrue(abs(actual_minutes - expected_minutes) <= 1)

    def test_convert_refuses_names_outside_the_date_api(self):
        for expression in (
            "__builtins__",
            "Now().__class__",
            "DateTime.now.__self__",
            "open('x')",
        ):
            with self.assertRaises(ValueError):
                self.convert(expression)


class XMLReaderTestCase(test.TestCase):
    tskversion = "Subclass responsibility"

    def setUp(self):
        super().setUp()

    def writeAndRead(self, xml_contents):
        # pylint: disable=W0201
        self.fd = io.StringIO()
        self.fd.name = "testfile.tsk"
        self.reader = persistence.XMLReader(self.fd)
        all_xml = (
            '<?taskcoach release="whatever" '
            'tskversion="%d"?>\n' % self.tskversion + xml_contents
        )
        self.fd.write(all_xml)
        self.fd.seek(0)
        return self.reader.read()

    def writeAndReadTasks(self, xml_contents):
        return self.writeAndRead(xml_contents)[0]

    def writeAndReadCategories(self, xml_contents):
        return self.writeAndRead(xml_contents)[1]

    def writeAndReadNotes(self, xml_contents):
        return self.writeAndRead(xml_contents)[2]

    def writeAndReadTasksAndCategories(self, xml_contents):
        tasks, categories, _ = self.writeAndRead(xml_contents)
        return tasks, categories

    def writeAndReadTasksAndCategoriesAndNotes(self, xml_contents):
        return self.writeAndRead(xml_contents)

    def writeAndReadCategoriesAndNotes(self, xml_contents):
        _, categories, notes = self.writeAndRead(xml_contents)
        return categories, notes


class XMLReaderWithoutVersionTest(test.TestCase):
    def test_a_file_without_a_version_is_refused(self):
        fd = io.StringIO("<tasks/>")
        fd.name = "testfile.tsk"
        self.assertRaises(ValueError, persistence.XMLReader(fd).read)


class XMLReaderDoctypeTest(test.TestCase):
    """Task Coach never writes a DOCTYPE; one can define entities
    (docs/PERSISTENCE_XML.md, Expat by Package)."""

    def read(self, prolog="", subject="x"):
        fd = io.StringIO(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<?taskcoach release="2.0.3.0" tskversion="37"?>\n'
            + prolog
            + '<tasks><task id="t" subject="%s"/></tasks>\n' % subject
        )
        fd.name = "testfile.tsk"
        return persistence.XMLReader(fd).read()

    def test_a_doctype_is_refused(self):
        self.assertRaises(ValueError, self.read, "<!DOCTYPE tasks>\n")

    def test_entities_are_refused_before_they_expand(self):
        # A long chain of them crashes Expat before 2.7.0
        # (CVE-2024-8176)
        prolog = '<!DOCTYPE tasks [<!ENTITY a "x"><!ENTITY b "&a;">]>\n'
        self.assertRaises(ValueError, self.read, prolog, "&b;")

    def test_a_doctype_after_a_comment_is_refused(self):
        prolog = "<!-- a note -->\n<!DOCTYPE tasks>\n"
        self.assertRaises(ValueError, self.read, prolog)

    def test_doctype_text_in_a_field_is_read(self):
        tasks = self.read(subject="&lt;!DOCTYPE tasks&gt;")[0]
        self.assertEqual("<!DOCTYPE tasks>", tasks[0].subject())


class XMLReaderVersion6Test(XMLReaderTestCase):
    tskversion = 6

    def test_description(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task description="%s" id="foo"/>
        </tasks>\n""" % "Description")
        self.assertEqual("Description", tasks[0].description())

    def test_effort_description(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task id="foo">
                <effort start="2004-01-01 10:00:00.123000" 
                        stop="2004-01-01 10:30:00.123000" 
                        description="Yo"/>
            </task>
        </tasks>""")
        self.assertEqual("Yo", tasks[0].efforts()[0].description())


class XMLReaderDuplicateIdTest(XMLReaderTestCase):
    tskversion = 37

    def test_a_later_duplicate_id_gets_a_new_one(self):
        tasks = self.writeAndReadTasks(
            '<tasks><task id="1" subject="first"/>'
            '<task id="1" subject="second"/></tasks>'
        )
        ids = {each.subject(): each.id() for each in tasks}
        self.assertEqual(
            ("1", True), (ids["first"], ids["second"] not in ("", "1"))
        )

    def test_a_subtask_with_its_parents_id_gets_a_new_one(self):
        tasks = self.writeAndReadTasks(
            '<tasks><task id="1"><task id="1"/></task></tasks>'
        )
        self.assertNotEqual("1", tasks[0].children()[0].id())

    def test_a_prerequisite_on_a_duplicate_id_is_the_first_task(self):
        tasks = self.writeAndReadTasks(
            '<tasks><task id="1" subject="first"/>'
            '<task id="1" subject="second"/>'
            '<task id="2" subject="waiting" prerequisites="1"/></tasks>'
        )
        by_subject = {each.subject(): each for each in tasks}
        self.assertEqual(
            [by_subject["first"]], list(by_subject["waiting"].prerequisites())
        )

    def test_duplicate_ids_are_reported(self):
        self.writeAndReadTasks(
            '<tasks><task id="1"/><task id="1"/><task id="2"/></tasks>'
        )
        self.assertEqual(["1"], list(self.reader.get_duplicate_ids()))


class XMLReaderVersion8Test(XMLReaderTestCase):
    tskversion = 8

    def test_read_task_without_priority(self):
        tasks = self.writeAndReadTasks('<tasks><task id="foo"/></tasks>')
        self.assertEqual(0, tasks[0].priority())


class XMLReaderVersion9Test(XMLReaderTestCase):
    tskversion = 9

    def test_read_task_without_id(self):
        tasks = self.writeAndReadTasks('<tasks><task id="foo"/></tasks>')
        self.assertTrue(tasks[0].id())


class XMLReaderVersion10Test(XMLReaderTestCase):
    tskversion = 10

    def test_read_task_without_fee(self):
        tasks = self.writeAndReadTasks('<tasks><task id="foo"/></tasks>')
        self.assertEqual(0, tasks[0].hourlyFee())
        self.assertEqual(0, tasks[0].fixedFee())


class XMLReaderVersion11Test(XMLReaderTestCase):
    tskversion = 11

    def test_read_task_without_reminder(self):
        tasks = self.writeAndReadTasks('<tasks><task id="foo"/></tasks>')
        self.assertEqual(date.DateTime(), tasks[0].reminder())


class XMLReaderVersion12Test(XMLReaderTestCase):
    tskversion = 12

    def test_read_task_without_mark_parent_completed_setting(
        self,
    ):
        tasks = self.writeAndReadTasks('<tasks><task id="foo"/></tasks>')
        self.assertEqual(
            None, tasks[0].shouldMarkCompletedWhenAllChildrenCompleted()
        )


class XMLReaderVersion13Test(XMLReaderTestCase):
    tskversion = 13

    def test_one_category(self):
        tasks, categories = self.writeAndReadTasksAndCategories("""
        <tasks>
            <task id="1">
                <category>test</category>
            </task>
        </tasks>""")

        self.assertEqual("test", categories[0].subject())
        self.assertEqual(set([tasks[0]]), categories[0].members())
        self.assertEqual(set([categories[0]]), tasks[0].categories())

    def test_multiple_categories(self):
        tasks, categories = self.writeAndReadTasksAndCategories("""
        <tasks>
            <task id="1">
                <category>test</category>
                <category>another</category>
                <category>yetanother</category>
            </task>
        </tasks>""")

        for category in categories:
            self.assertEqual(set([tasks[0]]), category.members())
            self.assertTrue(category in tasks[0].categories())

    def test_sub_task_with_categories(self):
        tasks, categories = self.writeAndReadTasksAndCategories("""
        <tasks>
            <task id="1">
                <category>test</category>
                <task id="1.1">
                    <category>another</category>
                </task>
            </task>
        </tasks>""")
        test_category = categories[0]
        another_category = categories[1]
        self.assertEqual("1", list(test_category.members())[0].id())
        self.assertEqual("1.1", list(another_category.members())[0].id())
        self.assertEqual(set([test_category]), tasks[0].categories())
        self.assertEqual(
            set([another_category]), tasks[0].children()[0].categories()
        )


class XMLReaderVersion14Test(XMLReaderTestCase):
    tskversion = 14

    def test_effort_with_milliseconds(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <effort start="2004-01-01 10:00:00.123000" 
                        stop="2004-01-01 10:30:00.123000"/>
            </task>
        </tasks>""")
        self.assertEqual(1, len(tasks[0].efforts()))
        self.assertEqual(date.TimeDelta(minutes=30), tasks[0].timeSpent())
        self.assertEqual(tasks[0], tasks[0].efforts()[0].task())


class XMLReaderVersion16Text(XMLReaderTestCase):
    tskversion = 16

    def test_one_attachment_compat(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <attachment>whatever.tsk</attachment>
            </task>
        </tasks>""")
        self.assertEqual(
            ["whatever.tsk"],
            [att.location() for att in tasks[0].attachments()],
        )
        self.assertEqual(
            ["whatever.tsk"], [att.subject() for att in tasks[0].attachments()]
        )

    def test_two_attachments_compat(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <attachment>whatever.tsk</attachment>
                <attachment>another.txt</attachment>
            </task>
        </tasks>""")
        self.assertEqual(
            ["whatever.tsk", "another.txt"],
            [att.location() for att in tasks[0].attachments()],
        )
        self.assertEqual(
            ["whatever.tsk", "another.txt"],
            [att.subject() for att in tasks[0].attachments()],
        )

    def test_one_attachment(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <attachment>FILE:whatever.tsk</attachment>
            </task>
        </tasks>""")
        self.assertEqual(
            ["whatever.tsk"],
            [att.location() for att in tasks[0].attachments()],
        )
        self.assertEqual(
            ["whatever.tsk"], [att.subject() for att in tasks[0].attachments()]
        )

    def test_two_attachments(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <attachment>FILE:whatever.tsk</attachment>
                <attachment>FILE:another.txt</attachment>
            </task>
        </tasks>""")
        self.assertEqual(
            ["whatever.tsk", "another.txt"],
            [att.location() for att in tasks[0].attachments()],
        )
        self.assertEqual(
            ["whatever.tsk", "another.txt"],
            [att.subject() for att in tasks[0].attachments()],
        )


# There's no XMLReaderVersion17Test because the only difference between version
# 17 and 18 is the addition of an optional color attribute to categories in
# version 18. So the tests for version 18 test version 17 as well.


class XMLReaderVersion18Test(XMLReaderTestCase):
    tskversion = 18

    def test_last_modification_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task lastModificationTime="2004-01-01 10:00:00"/>
        </tasks>""")
        self.assertEqual(1, len(tasks))  # Ignore lastModificationTime


class XMLReaderVersion19Test(XMLReaderTestCase):
    tskversion = 19  # New in release 0.69.0?

    def test_daily_recurrence(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task recurrence="daily"/>
        </tasks>""")
        self.assertEqual("daily", tasks[0].recurrence().unit)

    def test_weekly_recurrence(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task recurrence="weekly"/>
        </tasks>""")
        self.assertEqual("weekly", tasks[0].recurrence().unit)

    def test_monthly_recurrence(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task recurrence="monthly"/>
        </tasks>""")
        self.assertEqual("monthly", tasks[0].recurrence().unit)

    def test_recurrence_count(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task recurrenceCount="10"/>
        </tasks>""")
        self.assertEqual(10, tasks[0].recurrence().count)

    def test_max_recurrence_count(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task maxRecurrenceCount="10"/>
        </tasks>""")
        self.assertEqual(10, tasks[0].recurrence().max)

    def test_recurrence_frequency(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task recurrenceFrequency="3"/>
        </tasks>""")
        self.assertEqual(3, tasks[0].recurrence().amount)


class XMLReaderVersion20Test(XMLReaderTestCase):
    tskversion = 20  # New in release 0.71.0

    def test_read_empty_stream(self):
        reader = persistence.XMLReader(io.StringIO())
        self.assertRaises(ElementTree.ParseError, reader.read)

    def test_no_tasks_and_no_categories(self):
        tasks, categories, notes = self.writeAndReadTasksAndCategoriesAndNotes(
            "<tasks/>\n"
        )
        self.assertEqual(([], [], []), (tasks, categories, notes))

    def test_one_task(self):
        tasks = self.writeAndReadTasks("<tasks><task/></tasks>\n")
        self.assertEqual(1, len(tasks))
        self.assertEqual("", tasks[0].subject())

    def test_two_tasks(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task subject="1"/>
            <task subject="2"/>
        </tasks>\n""")
        self.assertEqual(2, len(tasks))
        self.assertEqual("1", tasks[0].subject())
        self.assertEqual("2", tasks[1].subject())

    def test_one_task_subject(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task subject="Yo"/>
        </tasks>\n""")
        self.assertEqual("Yo", tasks[0].subject())

    def test_one_task_unicode_subject(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task subject="???"/>
        </tasks>\n""")
        self.assertEqual("???", tasks[0].subject())

    def test_budget(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task budget="4:10:10"/>
        </tasks>\n""")
        self.assertEqual(
            date.TimeDelta(hours=4, minutes=10, seconds=10), tasks[0].budget()
        )

    def test_budget_no_budget(self):
        tasks = self.writeAndReadTasks("<tasks><task/></tasks>\n")
        self.assertEqual(date.TimeDelta(), tasks[0].budget())

    def test_description(self):
        description = "Description\nline 2"
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <description>%s</description>
            </task>
        </tasks>\n""" % description)
        self.assertEqual(description, tasks[0].description())

    def test_no_children(self):
        tasks = self.writeAndReadTasks("<tasks><task/></tasks>\n")
        self.assertFalse((tasks[0].children()))

    def test_child(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <task/>
            </task>
        </tasks>\n""")
        self.assertEqual(1, len(tasks[0].children()))
        self.assertEqual(1, len(tasks))

    def test_children(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <task/>
                <task/>
            </task>
        </tasks>\n""")
        self.assertEqual(2, len(tasks[0].children()))
        self.assertEqual(1, len(tasks))

    def test_grandchild(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <task>
                    <task/>
                </task>
            </task>
        </tasks>\n""")
        self.assertEqual(1, len(tasks))
        parent = tasks[0]
        self.assertEqual(1, len(parent.children()))
        self.assertEqual(1, len(parent.children()[0].children()))

    def test_effort(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <effort start="2004-01-01 10:00:00" 
                        stop="2004-01-01 10:30:00"/>
            </task>
        </tasks>""")
        self.assertEqual(1, len(tasks[0].efforts()))
        self.assertEqual(date.TimeDelta(minutes=30), tasks[0].timeSpent())
        self.assertEqual(tasks[0], tasks[0].efforts()[0].task())

    def test_child_effort(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <task>
                    <effort start="2004-01-01 10:00:00" 
                            stop="2004-01-01 10:30:00"/>
                </task>
            </task>
        </tasks>""")
        child = tasks[0].children()[0]
        self.assertEqual(1, len(child.efforts()))
        self.assertEqual(date.TimeDelta(minutes=30), child.timeSpent())
        self.assertEqual(child, child.efforts()[0].task())

    def test_effort_description(self):
        description = "Description\nLine 2"
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <effort start="2004-01-01 10:00:00">
                    <description>%s</description>
                </effort>
            </task>
        </tasks>""" % description)
        self.assertEqual(description, tasks[0].efforts()[0].description())

    def test_active_effort(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <effort start="2004-01-01 10:00:00"/>
            </task>
        </tasks>""")
        self.assertEqual(1, len(tasks[0].efforts()))
        self.assertTrue(tasks[0].isBeingTracked())

    def test_priority(self):
        tasks = self.writeAndReadTasks('<tasks><task priority="5"/></tasks>')
        self.assertEqual(5, tasks[0].priority())

    def test_task_id(self):
        tasks = self.writeAndReadTasks('<tasks><task id="xyz"/></tasks>')
        self.assertEqual("xyz", tasks[0].id())

    def test_task_color(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task color="(255, 0, 0, 255)"/>
        </tasks>""")
        self.assertEqual(wx.RED, tasks[0].backgroundColor())

    def test_hourly_fee(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task hourlyFee="100"/>
            <task hourlyFee="5.5"/>
        </tasks>""")
        self.assertEqual(100, tasks[0].hourlyFee())
        self.assertEqual(5.5, tasks[1].hourlyFee())

    def test_fixed_fee(self):
        tasks = self.writeAndReadTasks(
            '<tasks><task fixedFee="240.50"/></tasks>'
        )
        self.assertEqual(240.5, tasks[0].fixedFee())

    def test_no_reminder(self):
        tasks = self.writeAndReadTasks(
            '<tasks><task reminder="None"/></tasks>'
        )
        self.assertEqual(date.DateTime(), tasks[0].reminder())

    def test_reminder(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task reminder="2004-01-01 10:00:00"/>
        </tasks>""")
        self.assertEqual(
            date.DateTime(2004, 1, 1, 10, 0, 0, 0), tasks[0].reminder()
        )

    def test_mark_completed_when_all_children_completed_setting_true(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task shouldMarkCompletedWhenAllChildrenCompleted="True"/>
        </tasks>""")
        self.assertEqual(
            True, tasks[0].shouldMarkCompletedWhenAllChildrenCompleted()
        )

    def test_mark_completed_when_all_children_completed_setting_false(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task shouldMarkCompletedWhenAllChildrenCompleted="False"/>
        </tasks>""")
        self.assertEqual(
            False, tasks[0].shouldMarkCompletedWhenAllChildrenCompleted()
        )

    def test_mark_completed_when_all_children_completed_setting_none(self):
        tasks = self.writeAndReadTasks("<tasks><task/></tasks>")
        self.assertEqual(
            None, tasks[0].shouldMarkCompletedWhenAllChildrenCompleted()
        )

    def test_task_without_attachments(self):
        tasks = self.writeAndReadTasks("<tasks><task/></tasks>")
        self.assertEqual([], tasks[0].attachments())

    def test_note_without_attachments(self):
        notes = self.writeAndReadNotes("<tasks><note/></tasks>")
        self.assertEqual([], notes[0].attachments())

    def test_category_without_attachments(self):
        categories = self.writeAndReadCategories("<tasks><category/></tasks>")
        self.assertEqual([], categories[0].attachments())

    def test_task_with_one_attachment(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <attachment type="file">
                    <description>whatever.tsk</description>
                    <data>whateverdata.tsk</data>
                </attachment>
            </task>
        </tasks>""")
        self.assertEqual(
            [
                os.path.join(
                    os.getcwd(), "testfile_attachments", "whateverdata.tsk"
                )
            ],
            [att.location() for att in tasks[0].attachments()],
        )
        self.assertEqual(
            ["whatever.tsk"], [att.subject() for att in tasks[0].attachments()]
        )

    def test_note_with_one_attachment(self):
        notes = self.writeAndReadNotes("""
        <tasks>
            <note>
                <attachment type="file">
                    <description>whatever.tsk</description>
                    <data>whateverdata.tsk</data>
                </attachment>
            </note>
        </tasks>""")
        self.assertEqual(
            [
                os.path.join(
                    os.getcwd(), "testfile_attachments", "whateverdata.tsk"
                )
            ],
            [att.location() for att in notes[0].attachments()],
        )
        self.assertEqual(
            ["whatever.tsk"], [att.subject() for att in notes[0].attachments()]
        )

    def test_category_with_one_attachment(self):
        categories = self.writeAndReadCategories("""
        <tasks>
            <category>
                <attachment type="file">
                    <description>whatever.tsk</description>
                    <data>whateverdata.tsk</data>
                </attachment>
            </category>
        </tasks>""")
        self.assertEqual(
            [
                os.path.join(
                    os.getcwd(), "testfile_attachments", "whateverdata.tsk"
                )
            ],
            [att.location() for att in categories[0].attachments()],
        )
        self.assertEqual(
            ["whatever.tsk"],
            [att.subject() for att in categories[0].attachments()],
        )

    def test_task_with_two_attachments(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <attachment type="file">
                   <description>whatever.tsk</description>
                   <data>whateverdata.tsk</data>
                </attachment>
                <attachment type="file">
                    <description>another.txt</description>
                    <data>anotherdata.txt</data>
                </attachment>
            </task>
        </tasks>""")
        self.assertEqual(
            [
                os.path.join(
                    os.getcwd(), "testfile_attachments", "whateverdata.tsk"
                ),
                os.path.join(
                    os.getcwd(), "testfile_attachments", "anotherdata.txt"
                ),
            ],
            [att.location() for att in tasks[0].attachments()],
        )
        self.assertEqual(
            ["whatever.tsk", "another.txt"],
            [att.subject() for att in tasks[0].attachments()],
        )

    def test_one_category(self):
        categories = self.writeAndReadCategories(
            '<tasks><category subject="cat"/></tasks>'
        )
        self.assertEqual("cat", categories[0].subject())

    def test_two_categories(self):
        categories = self.writeAndReadCategories("""
        <tasks>
            <category subject="cat1"/>
            <category subject="cat2"/>
        </tasks>""")
        self.assertEqual(
            ["cat1", "cat2"], [category.subject() for category in categories]
        )

    def test_category_id(self):
        categories = self.writeAndReadCategories("""
        <tasks>
            <category id="catId"/>
        </tasks>""")
        self.assertEqual("catId", categories[0].id())

    def test_category_with_description(self):
        categories = self.writeAndReadCategories("""
        <tasks>
            <category subject="cat">
                <description>Description</description>
            </category>
        </tasks>""")
        self.assertEqual("Description", categories[0].description())

    def test_category_color(self):
        categories = self.writeAndReadCategories("""
        <tasks>
            <category subject="cat" color="(255, 0, 0, 255)"/>
        </tasks>""")
        self.assertEqual(wx.RED, categories[0].backgroundColor())

    def test_one_task_with_category(self):
        tasks, categories = self.writeAndReadTasksAndCategories("""
        <tasks>
            <category subject="cat" categorizables="1"/>
            <task id="1"/>
        </tasks>""")
        self.assertEqual(set(tasks), categories[0].members())

    def test_two_recursive_categories(self):
        categories = self.writeAndReadCategories("""
        <tasks>
            <category subject="cat1">
                <category subject="cat1.1"/>
            </category>
        </tasks>""")
        self.assertEqual("cat1.1", categories[0].children()[0].subject())

    def test_recursive_categories_not_in_result_list(self):
        categories = self.writeAndReadCategories("""
        <tasks>
            <category subject="cat1">
                <category subject="cat1.1"/>
            </category>
        </tasks>""")
        self.assertEqual(1, len(categories))

    def test_recursive_categories_with_two_tasks(self):
        tasks, categories = self.writeAndReadTasksAndCategories("""
        <tasks>
            <category subject="cat1" categorizables="1">
                <category subject="cat1.1" categorizables="2"/>
            </category>
            <task subject="task1" id="1"/>
            <task subject="task2" id="2"/>
        </tasks>""")

        self.assertEqual(tasks[0], list(categories[0].members())[0])
        self.assertEqual(
            tasks[1], list(categories[0].children()[0].members())[0]
        )

    def test_subtask_category(self):
        tasks, categories = self.writeAndReadTasksAndCategories("""
        <tasks>
            <category subject="cat1" categorizables="1.1"/>
            <task subject="task1" id="1">
                <task subject="task2" id="1.1"/>
            </task>
        </tasks>""")
        self.assertEqual(
            tasks[0].children()[0], list(categories[0].members())[0]
        )

    def test_filtered_category(self):
        categories = self.writeAndReadCategories("""
        <tasks>
            <category filtered="True" subject="category"/>
        </tasks>""")
        self.assertTrue(categories[0].isFiltered())

    def test_category_with_deleted_tasks(self):
        """There's a bug in release 0.61.5 that causes the task file to contain
        references to deleted tasks. Ignore these when loading the task
        file."""
        categories = self.writeAndReadCategories("""
        <tasks>
            <category subject="cat" tasks="some_task_id"/>
        </tasks>""")
        self.assertFalse(categories[0].members())

    def test_note(self):
        notes = self.writeAndReadNotes("""
        <tasks>
            <note/>
        </tasks>""")
        self.assertTrue(notes)

    def test_note_subject(self):
        notes = self.writeAndReadNotes("""
        <tasks>
            <note subject="Note"/>
        </tasks>""")
        self.assertEqual("Note", notes[0].subject())

    def test_note_description(self):
        notes = self.writeAndReadNotes("""
        <tasks>
            <note>
                <description>Description</description>
            </note>
        </tasks>""")
        self.assertEqual("Description", notes[0].description())

    def test_note_child(self):
        notes = self.writeAndReadNotes("""
        <tasks>
            <note>
                <note/>
            </note>
        </tasks>""")
        self.assertEqual(1, len(notes[0].children()))

    def test_note_child_with_attachment(self):
        notes = self.writeAndReadNotes("""
        <tasks>
            <note>
                <note>
                    <attachment type="file">
                       <description>whatever.tsk</description>
                       <data>whateverdata.tsk</data>
                    </attachment>
                </note>
            </note>
        </tasks>""")
        self.assertEqual(
            [
                os.path.join(
                    os.getcwd(), "testfile_attachments", "whateverdata.tsk"
                )
            ],
            [att.location() for att in notes[0].children()[0].attachments()],
        )
        self.assertEqual(
            ["whatever.tsk"],
            [att.subject() for att in notes[0].children()[0].attachments()],
        )

    def test_note_category(self):
        categories, notes = self.writeAndReadCategoriesAndNotes("""
        <tasks>
            <note id="noteId" subject="Note"/>
            <category categorizables="noteId" subject="Category"/>
        </tasks>""")
        self.assertEqual(notes[0], list(categories[0].members())[0])

    def test_note_id(self):
        notes = self.writeAndReadNotes("""
        <tasks>
            <note id="noteId"/>
        </tasks>""")
        self.assertEqual("noteId", notes[0].id())

    def test_note_color(self):
        notes = self.writeAndReadNotes("""
        <tasks>
            <note color="(255, 0, 0, 255)"/>
        </tasks>""")
        self.assertEqual(wx.RED, notes[0].backgroundColor())

    def test_no_recurrence(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task/>
        </tasks>""")
        self.assertFalse(tasks[0].recurrence())

    def test_daily_recurrence(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task><recurrence unit="daily"/></task>
        </tasks>""")
        self.assertEqual("daily", tasks[0].recurrence().unit)

    def test_weekly_recurrence(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task><recurrence unit="weekly"/></task>
        </tasks>""")
        self.assertEqual("weekly", tasks[0].recurrence().unit)

    def test_recurrence_amount(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task><recurrence unit="daily" amount="2"/></task>
        </tasks>""")
        self.assertEqual(2, tasks[0].recurrence().amount)

    def test_recurrence_max(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task><recurrence unit="daily" max="2"/></task>
        </tasks>""")
        self.assertEqual(2, tasks[0].recurrence().max)

    def test_recurrence_count(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task><recurrence unit="daily" count="2"/></task>
        </tasks>""")
        self.assertEqual(2, tasks[0].recurrence().count)

    def test_recurrence_same_weekday(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task><recurrence unit="daily" sameWeekday="True"/></task>
        </tasks>""")
        self.assertTrue(tasks[0].recurrence().sameWeekday)

    def test_task_with_note(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <note/>
            </task> 
        </tasks>""")
        self.assertEqual(1, len(tasks[0].notes()))

    def test_task_with_notes(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <note/><note/>
            </task> 
        </tasks>""")
        self.assertEqual(2, len(tasks[0].notes()))

    def test_task_with_nested_notes(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <note>
                    <note/>
                </note>
            </task> 
        </tasks>""")
        self.assertEqual(1, len(tasks[0].notes()[0].children()))

    def test_task_notes_dont_get_added_to_overall_notes_list(self):
        notes = self.writeAndReadNotes("""
        <tasks>
            <task>
                <note/>
            </task> 
        </tasks>""")
        self.assertFalse(notes)

    def test_category_with_note(self):
        categories = self.writeAndReadCategories("""
        <tasks>
            <category>
                <note/>
            </category> 
        </tasks>""")
        self.assertEqual(1, len(categories[0].notes()))

    def test_category_with_notes(self):
        categories = self.writeAndReadCategories("""
        <tasks>
            <category>
                <note/><note/>
            </category> 
        </tasks>""")
        self.assertEqual(2, len(categories[0].notes()))

    def test_category_with_nested_notes(self):
        categories = self.writeAndReadCategories("""
        <tasks>
            <category>
                <note>
                    <note/>
                </note>
            </category> 
        </tasks>""")
        self.assertEqual(1, len(categories[0].notes()[0].children()))

    def test_category_notes_dont_get_added_to_overall_notes_list(self):
        notes = self.writeAndReadNotes("""
        <tasks>
            <category>
                <note/>
            </category> 
        </tasks>""")
        self.assertFalse(notes)

    def test_task_expansion(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task expandedContexts="('None',)"/>
        </tasks>""")
        self.assertTrue(tasks[0].isExpanded())

    def test_task_expansion_multiple_contexts(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task expandedContexts="('None','Test')"/>
        </tasks>""")
        self.assertTrue(tasks[0].isExpanded(context="Test"))

    def test_category_expansion(self):
        categories = self.writeAndReadCategories("""
        <tasks>
            <category expandedContexts="('None',)"/>
        </tasks>""")
        self.assertTrue(categories[0].isExpanded())

    def test_note_expansion(self):
        notes = self.writeAndReadNotes("""
        <tasks>
            <note expandedContexts="('None',)"/>
        </tasks>""")
        self.assertTrue(notes[0].isExpanded())


class XMLReaderVersion21Test(XMLReaderTestCase):
    tskversion = 21  # New in release 0.71.0

    def test_attachment_location(self):
        categories = self.writeAndReadCategories("""
        <tasks>
            <category>
                <attachment type="file" location="location">
                   <description>description</description>
                </attachment>
            </category>
        </tasks>""")
        self.assertEqual(
            ["location"],
            [
                os.path.split(att.location())[-1]
                for att in categories[0].attachments()
            ],
        )


class XMLReaderVersion22Test(XMLReaderTestCase):
    tskversion = 22

    def test_task_with_another_status_is_loaded(self):
        tasks = self.writeAndReadTasks(
            '<tasks><task subject="Task" status="2"></task></tasks>'
        )
        self.assertEqual(["Task"], [each.subject() for each in tasks])

    def test_task_saved_as_deleted_is_not_loaded(self):
        # Deleted with SyncML enabled, before 2026: hidden and not
        # restorable
        tasks = self.writeAndReadTasks(
            '<tasks><task subject="Kept" status="1"/>'
            '<task subject="Deleted" status="3"/></tasks>'
        )
        self.assertEqual(["Kept"], [each.subject() for each in tasks])


class XMLReaderVersion23Test(XMLReaderTestCase):
    tskversion = 23

    def test_description(self):
        tasks = self.writeAndReadTasks(
            '<tasks><task subject="Task" status="0">'
            "<description>\nDescription\n</description>"
            "</task></tasks>"
        )
        self.assertEqual("\nDescription\n", tasks[0].description())

    def test_a_file_with_a_guid_still_loads(self):
        tasks = self.writeAndReadTasks(
            '<tasks><task id="1"/><guid>GUID</guid></tasks>'
        )
        self.assertEqual(["1"], [each.id() for each in tasks])


class XMLReaderVersion24Test(XMLReaderTestCase):
    tskversion = 24  # New in release 0.72.9

    # tskversion 24 introduces newlines so that the XML is not on one long
    # line anymore. We have to be sure not to introduce new lines in
    # text nodes though.

    def test_description(self):
        tasks = self.writeAndReadTasks(
            '<tasks>\n<task subject="Task" status="0">\n'
            "<description>\nDescription\n</description>\n"
            "</task>\n</tasks>\n"
        )
        self.assertEqual("Description", tasks[0].description())

    def test_inline_attachment_data_is_not_read(self):
        # Since #378: the attachment stays, its data is lost
        tasks = self.writeAndReadTasks(
            '<tasks>\n<task status="0">\n'
            '<attachment type="mail" subject="Quote" status="0">\n'
            '<data extension="eml">\n%s\n</data>\n'
            "</attachment>\n</task>\n</tasks>\n"
            % base64.encodebytes(b"Data").decode("ascii")
        )
        mail = tasks[0].attachments()[0]
        self.assertEqual(
            ("Quote", "(embedded eml - data not migrated)"),
            (mail.subject(), mail.location()),
        )

    def test_a_file_with_legacy_syncml_nodes_still_loads(self):
        """Release 0.72.9 (and earlier?) had a bug where tags in the
        SyncML config information would be split across multiple lines.
        Fixed in release 0.72.10. SyncML is now removed but old files
        may still have these nodes.
        """
        tasks = self.writeAndReadTasks(
            '<tasks>\n<task id="1"/>\n<syncml><TaskCoach-\n'
            "0000011d209a4b6c3f9f7c32000a00b100240032\n"
            "><spds><sources><TaskCoach-\n"
            "0000011d209a4b6c3f9f7c32000a00b100240032\n"
            ".Tasks/><TaskCoach-\n"
            "0000011d209a4b6c3f9f7c32000a00b100240032\n"
            ".Notes/></sources><syncml><Auth/><Conn/></syncml></spds></TaskCoach-\n"
            "0000011d209a4b6c3f9f7c32000a00b100240032\n"
            "><TaskCoach-0000011d209a4b6c3f9f7c32000a00b100240032><spds><sources><TaskCoach-0000011d209a4b6c3f9f7c32000a00b100240032.Tasks/><TaskCoach-0000011d209a4b6c3f9f7c32000a00b100240032.Notes/></sources><syncml><Auth/><Conn/></syncml></spds></TaskCoach-0000011d209a4b6c3f9f7c32000a00b100240032></syncml><guid>\n"
            "0000011d209a4b6c3f9f7c32000a00b100240032\n"
            "</guid></tasks>"
        )
        self.assertEqual(["1"], [each.id() for each in tasks])


class XMLReaderVersion26Test(XMLReaderTestCase):
    tskversion = 26  # New in release 0.75.0

    # Release 0.75.0 introduces percentage complete for tasks

    def test_percentage_complete(self):
        tasks = self.writeAndReadTasks(
            '<tasks>\n<task subject="Task" status="0" percentageComplete="50"/>\n'
            "</tasks>\n"
        )
        self.assertEqual(50, tasks[0].percentageComplete())


class XMLReaderVersion27Test(XMLReaderTestCase):
    tskversion = 27  # New in release 0.76.0

    # Release 0.76.0 introduces exclusive subcategories

    def test_exclusive_subcategories(self):
        categories = self.writeAndReadCategories(
            "<categories>\n"
            '<category subject="Category" exclusiveSubcategories="True"'
            ' status="0"/>\n'
            "</categories>\n"
        )
        self.assertTrue(categories[0].hasExclusiveSubcategories())

    def test_no_exclusive_subcategories_by_default(self):
        categories = self.writeAndReadCategories(
            "<categories>\n"
            '<category subject="Category" status="0"/>\n'
            "</categories>\n"
        )
        self.assertFalse(categories[0].hasExclusiveSubcategories())


class XMLReaderVersion28Test(XMLReaderTestCase):
    tskversion = 28  # New in release 0.78.0

    # Release 0.78.0 introduces foreground colors and fonts that can be set per object.

    def test_task_foreground_color(self):
        tasks = self.writeAndReadTasks(
            '<tasks>\n<task subject="Task" fgColor="(255,0,0)"/>\n'
            "</tasks>\n"
        )
        self.assertEqual(wx.RED, tasks[0].foregroundColor())

    def test_color_is_read_as_a_literal_not_run(self):
        payload = "(__import__('sys').modules.setdefault('tc_injected', 0),)"
        tasks = self.writeAndReadTasks(
            '<tasks>\n<task subject="Task" fgColor="%s"/>\n'
            "</tasks>\n" % payload.replace("'", "&apos;")
        )
        self.assertNotIn("tc_injected", sys.modules)
        self.assertEqual(None, tasks[0].foregroundColor())

    def test_task_background_color(self):
        tasks = self.writeAndReadTasks(
            '<tasks>\n<task subject="Task" bgColor="(255,0,0)"/>\n'
            "</tasks>\n"
        )
        self.assertEqual(wx.RED, tasks[0].backgroundColor())

    def test_category_foreground_color(self):
        categories = self.writeAndReadCategories(
            '<categories>\n<category subject="Category" fgColor="(255,0,0)"/>\n'
            "</categories>\n"
        )
        self.assertEqual(wx.RED, categories[0].foregroundColor())

    def test_category_background_color(self):
        categories = self.writeAndReadCategories(
            '<categories>\n<category subject="Category" bgColor="(255,0,0)"/>\n'
            "</categories>\n"
        )
        self.assertEqual(wx.RED, categories[0].backgroundColor())

    def test_note_foreground_color(self):
        notes = self.writeAndReadNotes(
            '<notes>\n<note subject="Note" fgColor="(255,0,0)"/>\n'
            "</notes>\n"
        )
        self.assertEqual(wx.RED, notes[0].foregroundColor())

    def test_note_background_color(self):
        notes = self.writeAndReadNotes(
            '<notes>\n<note subject="Note" bgColor="(255,0,0)"/>\n'
            "</notes>\n"
        )
        self.assertEqual(wx.RED, notes[0].backgroundColor())

    def test_task_font(self):
        tasks = self.writeAndReadTasks(
            '<tasks>\n<task subject="Task" font="%s"/>\n'
            "</tasks>\n" % wx.NORMAL_FONT.GetNativeFontInfoDesc()
        )
        self.assertEqual(wx.NORMAL_FONT, tasks[0].font())

    def test_no_task_font(self):
        tasks = self.writeAndReadTasks(
            '<tasks>\n<task subject="Task"/>\n</tasks>\n'
        )
        self.assertEqual(None, tasks[0].font())

    def test_category_font(self):
        categories = self.writeAndReadCategories(
            '<categories>\n<category subject="Category" font="%s"/>\n'
            "</categories>\n" % wx.NORMAL_FONT.GetNativeFontInfoDesc()
        )
        self.assertEqual(wx.NORMAL_FONT, categories[0].font())

    def test_note_font(self):
        notes = self.writeAndReadNotes(
            '<notes>\n<note subject="Note" font="%s"/>\n'
            "</notes>\n" % wx.NORMAL_FONT.GetNativeFontInfoDesc()
        )
        self.assertEqual(wx.NORMAL_FONT, notes[0].font())

    def test_attachment_font(self):
        tasks = self.writeAndReadTasks(
            '<tasks>\n<task subject="Task">\n'
            '<attachment type="file" location="whatever" font="%s"/>\n'
            "</task>\n</tasks>\n" % wx.NORMAL_FONT.GetNativeFontInfoDesc()
        )
        self.assertEqual(wx.NORMAL_FONT, tasks[0].attachments()[0].font())


class XMLReaderVersion29Test(XMLReaderTestCase):
    tskversion = 29

    def test_effort_new_id(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task id="foo">
                <effort id="foobar" start="2004-01-01 10:00:00.123000" 
                        stop="2004-01-01 10:30:00.123000"
                        status="1"
                        description="Yo"/>
            </task>
        </tasks>""")
        self.assertEqual("foobar", tasks[0].efforts()[0].id())

    def test_task_icon(self):
        tasks = self.writeAndReadTasks('<tasks><task icon="icon"/></tasks>')
        self.assertEqual("icon", tasks[0].icon_id())

    def test_selected_icon_of_old_files_is_dropped(self):
        tasks = self.writeAndReadTasks(
            '<tasks><task icon="icon" selectedIcon="open_icon"/></tasks>'
        )
        self.assertEqual("icon", tasks[0].icon_id())
        self.assertFalse(
            [name for name in fields(tasks[0]) if "selected" in name.lower()]
        )

    def test_note_icon(self):
        notes = self.writeAndReadNotes('<tasks><note icon="icon"/></tasks>')
        self.assertEqual("icon", notes[0].icon_id())

    def test_category_icon(self):
        categories = self.writeAndReadCategories(
            '<tasks><category icon="icon"/></tasks>'
        )
        self.assertEqual("icon", categories[0].icon_id())

    def test_attachment_icon(self):
        tasks = self.writeAndReadTasks(
            '<tasks><task subject="Task">'
            '<attachment type="file" location="whatever" icon="icon"/>'
            "</task></tasks>"
        )
        self.assertEqual("icon", tasks[0].attachments()[0].icon_id())


class XMLReaderVersion30Test(XMLReaderTestCase):
    tskversion = 30  # New in release 1.1.0.

    def test_start_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task startdate="2005-04-17 10:05:11"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 4, 17, 10, 5, 11),
            tasks[0].plannedStartDateTime(),
        )

    def test_start_date_time_without_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task startdate="2005-04-17"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 4, 17), tasks[0].plannedStartDateTime()
        )

    def test_no_start_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task />
        </tasks>\n""")
        self.assertEqual(date.DateTime(), tasks[0].plannedStartDateTime())

    def test_start_date_time_with_microseconds(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task startdate="2005-01-01 22:01:30.456"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 1, 1, 22, 1, 30, 456),
            tasks[0].plannedStartDateTime(),
        )

    def test_due_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task duedate="2005-04-17 13:05:59"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 4, 17, 13, 5, 59), tasks[0].dueDateTime()
        )

    def test_due_date_time_without_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task duedate="2005-04-17"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 4, 17, 23, 59, 59, 999999),
            tasks[0].dueDateTime(),
        )

    def test_due_date_time_without_time_when_end_hour_is_24(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task duedate="2005-04-17"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 4, 17, 23, 59, 59, 999999),
            tasks[0].dueDateTime(),
        )

    def test_no_due_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task />
        </tasks>\n""")
        self.assertEqual(date.DateTime(), tasks[0].dueDateTime())

    def test_due_date_time_with_microseconds(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task duedate="2005-01-01 22:01:30.456000"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 1, 1, 22, 1, 30, 456000),
            tasks[0].dueDateTime(),
        )

    def test_completion_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task completiondate="2005-01-01 22:01:30"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 1, 1, 22, 1, 30), tasks[0].completionDateTime()
        )
        self.assertTrue(tasks[0].completed())

    def test_completion_date_time_with_microseconds(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task completiondate="2005-01-01 22:01:30.456000"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 1, 1, 22, 1, 30, 456000),
            tasks[0].completionDateTime(),
        )
        self.assertTrue(tasks[0].completed())

    def test_no_completion_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task />
        </tasks>\n""")
        self.assertEqual(date.DateTime(), tasks[0].completionDateTime())

    def test_completion_date_time_without_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task completiondate="2005-01-01"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 1, 1, 23, 59, 59, 999999),
            tasks[0].completionDateTime(),
        )
        self.assertTrue(tasks[0].completed())

    def test_empty_font_description(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task font=""/>
        </tasks>\n""")
        self.assertEqual(None, tasks[0].font())

    def test_helvetica_mac_font(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task font="0;11;70;90;90;0;Helvetica Neue Light;0"/>
        </tasks>\n""")
        size = tasks[0].font().GetPointSize()
        if operating_system.isMac():  # pragma: no cover
            self.assertEqual(11, size)
        else:  # pragma: no cover
            self.assertTrue(size > 0)

    def test_sans_9_linux_font(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task font="Sans 9"/>
        </tasks>\n""")
        if operating_system.isMac():  # pragma: no cover
            self.assertEqual(None, tasks[0].font())
        else:  # pragma: no cover
            expected_font_size = 9 if operating_system.isGTK() else 8
            self.assertEqual(
                expected_font_size, tasks[0].font().GetPointSize()
            )


class XMLReaderVersion31Test(XMLReaderTestCase):
    tskversion = 31  # New in release 1.2.0.

    def writeAndReadTasks(self, *args, **kwargs):
        tasks = super().writeAndReadTasks(*args, **kwargs)
        tasks_by_id = dict()

        def collectIds(tasks):
            for each_task in tasks:
                tasks_by_id[each_task.id()] = each_task
                collectIds(each_task.children())

        collectIds(tasks)
        return tasks_by_id

    def assertDepends(self, prerequisite, dependency):
        self.assertTrue(prerequisite in dependency.prerequisites())
        self.assertTrue(dependency in prerequisite.dependencies())

    def test_one_prerequisite(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task id="1"/>
            <task id="2" prerequisites="1"/>
        </tasks>\n""")
        self.assertDepends(tasks["1"], tasks["2"])

    def test_two_prerequisites(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task id="1"/>
            <task id="2" prerequisites="1 3"/>
            <task id="3"/>
        </tasks>\n""")
        self.assertDepends(tasks["1"], tasks["2"])
        self.assertDepends(tasks["3"], tasks["2"])

    def test_chain_of_prerequisites(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task id="1"/>
            <task id="2" prerequisites="1"/>
            <task id="3" prerequisites="2"/>
        </tasks>\n""")
        self.assertDepends(tasks["1"], tasks["2"])
        self.assertDepends(tasks["2"], tasks["3"])

    def test_sub_task_prerequisite(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task id="1">
                <task id="1.1"/>
            </task>
            <task id="2" prerequisites="1.1"/>
        </tasks>\n""")
        self.assertDepends(tasks["1.1"], tasks["2"])

    def test_inter_sub_task_prerequisite(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task id="1">
                <task id="1.1"/>
                <task id="1.2" prerequisites="1.1"/>
            </task>
        </tasks>\n""")
        self.assertDepends(tasks["1.1"], tasks["1.2"])

    def test_mutual_prerequisites(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task id="1" prerequisites="2"/>
            <task id="2" prerequisites="1"/>
        </tasks>\n""")
        self.assertDepends(tasks["1"], tasks["2"])
        self.assertDepends(tasks["2"], tasks["1"])

    def test_mutual_prerequisite_with_child(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task id="1" prerequisites="1.1">
                <task id="1.1" prerequisites="1"/>
            </task>
        </tasks>\n""")
        self.assertDepends(tasks["1"], tasks["1.1"])
        self.assertDepends(tasks["1.1"], tasks["1"])

    def test_self_prerequisite(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task id="1" prerequisites="1"/>
        </tasks>\n""")
        self.assertDepends(tasks["1"], tasks["1"])


class XMLReaderVersion33Test(XMLReaderTestCase):
    tskversion = 33  # New in release 1.2.24.

    def test_reminder_before_snooze(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task reminder="2004-01-01 10:00:00" 
                  reminderBeforeSnooze="2004-01-01 9:00:00"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2004, 1, 1, 9, 0, 0),
            tasks[0].reminder(include_snooze=False),
        )
        self.assertEqual(
            date.DateTime(2004, 1, 1, 10, 0, 0), tasks[0].reminder()
        )

    def test_reminder(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task reminder="2004-01-01 10:00:00"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2004, 1, 1, 10, 0, 0),
            tasks[0].reminder(include_snooze=False),
        )
        self.assertEqual(
            date.DateTime(2004, 1, 1, 10, 0, 0), tasks[0].reminder()
        )

    def test_recurrence_not_based_on_completion(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task><recurrence unit="daily"/></task>
        </tasks>""")
        self.assertFalse(tasks[0].recurrence().recurBasedOnCompletion)

    def test_recurrence_based_on_completion(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <recurrence unit="daily" recurBasedOnCompletion="True"/>
            </task>
        </tasks>""")
        self.assertTrue(tasks[0].recurrence().recurBasedOnCompletion)


class XMLReaderVersion34Test(XMLReaderTestCase):
    tskversion = 34  # New in release 1.3.5.

    def test_planned_start_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task plannedstartdate="2005-04-17 10:05:11"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 4, 17, 10, 5, 11),
            tasks[0].plannedStartDateTime(),
        )

    def test_planned_start_date_time_without_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task plannedstartdate="2005-04-17"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 4, 17), tasks[0].plannedStartDateTime()
        )

    def test_no_planned_start_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task />
        </tasks>\n""")
        self.assertEqual(date.DateTime(), tasks[0].plannedStartDateTime())

    def test_planned_start_date_time_with_microseconds(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task plannedstartdate="2005-01-01 22:01:30.456"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 1, 1, 22, 1, 30, 456),
            tasks[0].plannedStartDateTime(),
        )

    def test_actual_start_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task actualstartdate="2005-04-17 10:05:11"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 4, 17, 10, 5, 11),
            tasks[0].actualStartDateTime(),
        )

    def test_actual_start_date_time_without_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task actualstartdate="2005-04-17"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 4, 17), tasks[0].actualStartDateTime()
        )

    def test_no_actual_start_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task />
        </tasks>\n""")
        self.assertEqual(date.DateTime(), tasks[0].actualStartDateTime())

    def test_actual_start_date_time_with_microseconds(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task actualstartdate="2005-01-01 22:01:30.456"/>
        </tasks>\n""")
        self.assertEqual(
            date.DateTime(2005, 1, 1, 22, 1, 30, 456),
            tasks[0].actualStartDateTime(),
        )

    def test_task_with_note_with_category(self):
        tasks, categories = self.writeAndReadTasksAndCategories("""
        <tasks>
            <task>
                <note subject="note" id="note1"/>
            </task>
            <category id="cat1" categorizables="note1"/>
        </tasks>\n""")
        self.assertEqual(
            list(tasks[0].notes())[0], list(categories[0].members())[0]
        )


class XMLReaderVersion35Test(XMLReaderTestCase):
    tskversion = 35  # New in release 1.3.19.

    def test_recurrence_stop_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task>
                <recurrence stop_datetime="2000-01-10 13:13:13"/>
            </task>
        </tasks>""")
        self.assertEqual(
            date.DateTime(2000, 1, 10, 13, 13, 13),
            tasks[0].recurrence().stop_datetime,
        )

    def test_creation_date_time_is_set_to_min_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task/>
        </tasks>""")
        self.assertEqual(date.DateTime.min, tasks[0].creationDateTime())


class XMLReaderVersion36Test(XMLReaderTestCase):
    tskversion = 36  # New in release 1.3.21

    def test_creation_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task creationDateTime="2012-12-12 12:00:00.12345"/>
        </tasks>""")
        self.assertEqual(
            date.Timestamp(2012, 12, 12, 12, 0, 0, 123450),
            tasks[0].creationDateTime(),
        )

    def test_item_never_modified_was_last_modified_when_created(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task creationDateTime="2012-12-12 12:00:00"/>
        </tasks>""")
        self.assertEqual(
            date.Timestamp(2012, 12, 12, 12, 0, 0),
            tasks[0].modificationDateTime(),
        )

    def test_item_without_dates_has_unknown_dates(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task/>
        </tasks>""")
        self.assertEqual(
            (date.DateTime.min, date.DateTime.min),
            (tasks[0].creationDateTime(), tasks[0].modificationDateTime()),
        )

    def test_creation_date_in_whole_seconds_has_no_fraction(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task creationDateTime="2012-12-12 12:00:00"/>
        </tasks>""")
        self.assertEqual(0, tasks[0].creationDateTime().microsecond)


class XMLReaderVersion37Test(XMLReaderTestCase):
    tskversion = 37  # New in release 1.3.23

    def test_items_saved_as_deleted_are_not_loaded(self):
        tasks, categories, notes = self.writeAndReadTasksAndCategoriesAndNotes(
            """
        <tasks>
            <task id="1" subject="Kept" prerequisites="2">
                <task id="1.1" subject="Deleted subtask" status="3"/>
            </task>
            <task id="2" subject="Deleted" status="3">
                <task id="2.1" subject="Subtask of deleted"/>
            </task>
            <category subject="Category" categorizables="1 2 note2"/>
            <note id="note1" subject="Kept note"/>
            <note id="note2" subject="Deleted note" status="3"/>
        </tasks>"""
        )
        self.assertEqual(["Kept"], [each.subject() for each in tasks])
        self.assertEqual([], tasks[0].children())
        self.assertEqual(set(), set(tasks[0].prerequisites()))
        self.assertEqual(set([tasks[0]]), set(categories[0].members()))
        self.assertEqual(["Kept note"], [each.subject() for each in notes])

    def test_members_are_saved_on_the_items_and_the_category(self):
        # Converted when read: the next save writes the new form, and
        # the old one for older releases (legacy.py)
        tasks, categories, notes = self.writeAndReadTasksAndCategoriesAndNotes(
            """
        <tasks>
            <task id="t1"/>
            <category id="c1" subject="Category" categorizables="t1 n1"/>
            <note id="n1"/>
        </tasks>"""
        )
        fd = io.BytesIO()
        persistence.XMLWriter(fd).write(
            task.TaskList(tasks),
            category.CategoryList(categories),
            note.NoteContainer(notes),
        )
        written = fd.getvalue().decode("utf-8")
        self.assertEqual(
            (2, True),
            (
                written.count('categories="c1"'),
                'categorizables="n1 t1"' in written,
            ),
        )

    def test_categories_are_resolved_in_one_event(self):
        # Filters reset on each event: one per item would be quadratic
        self.registerObserver(category.Category.member_added_event_type())
        self.writeAndReadTasksAndCategories("""
        <tasks>
            <task id="1"/><task id="2"/><task id="3"/>
            <category subject="Category" categorizables="1 2 3"/>
        </tasks>""")
        self.assertEqual(1, len(self.events))

    def test_effort_saved_as_deleted_is_not_loaded(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task id="1" subject="Task">
                <effort id="e1" start="2004-01-01 10:00:00"
                        stop="2004-01-01 11:00:00"/>
                <effort id="e2" start="2004-01-02 10:00:00"
                        stop="2004-01-02 11:00:00" status="3"/>
            </task>
        </tasks>""")
        self.assertEqual(["e1"], [each.id() for each in tasks[0].efforts()])

    def test_modification_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task modificationDateTime="2012-12-12 12:00:00.12345"/>
        </tasks>""")
        self.assertEqual(
            date.Timestamp(2012, 12, 12, 12, 0, 0, 123450),
            tasks[0].modificationDateTime(),
        )

    def test_modification_date_time_with_other_attributes(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task modificationDateTime="2012-12-12 12:00:00.12345"/>
        </tasks>""")
        self.assertEqual(
            date.Timestamp(2012, 12, 12, 12, 0, 0, 123450),
            tasks[0].modificationDateTime(),
        )

    def test_every_item_keeps_its_stored_modification_date(self):
        # Setting fields and links while loading sets the date to now,
        # so the stored one is restored last
        tasks, categories, notes = self.writeAndReadTasksAndCategoriesAndNotes(
            """
        <tasks>
          <task id="t1" subject="Task" priority="2" hourlyFee="10"
                fixedFee="5" budget="1:00:00" percentageComplete="50"
                plannedstartdate="2029-01-01 10:00:00"
                duedate="2030-01-01 10:00:00"
                reminder="2029-06-01 10:00:00" prerequisites="t2"
                modificationDateTime="2012-12-12 12:00:00">
            <task id="t1.1" subject="Subtask"
                  modificationDateTime="2012-12-12 12:00:00"/>
            <effort id="e1" start="2004-01-01 10:00:00"
                    stop="2004-01-01 11:00:00"
                    modificationDateTime="2012-12-12 12:00:00"/>
            <note id="n1" subject="Task note"
                  modificationDateTime="2012-12-12 12:00:00"/>
            <attachment id="a1" location="file.txt" type="file"
                        subject="Attachment"
                        modificationDateTime="2012-12-12 12:00:00"/>
            <recurrence unit="daily"/>
          </task>
          <task id="t2" subject="Prerequisite"
                modificationDateTime="2012-12-12 12:00:00"/>
          <category id="c1" subject="Category" categorizables="t1 n2"
                    stylePriority="3" filtered="True"
                    exclusiveSubcategories="True"
                    modificationDateTime="2012-12-12 12:00:00">
            <category id="c1.1" subject="Subcategory"
                      modificationDateTime="2012-12-12 12:00:00"/>
          </category>
          <note id="n2" subject="Note"
                modificationDateTime="2012-12-12 12:00:00">
            <note id="n2.1" subject="Subnote"
                  modificationDateTime="2012-12-12 12:00:00"/>
          </note>
        </tasks>"""
        )
        items = []
        for each in tasks + categories + notes:
            for item in [each] + each.children(recursive=True):
                items.append(item)
                if hasattr(item, "notes"):
                    items.extend(item.notes())
                if hasattr(item, "attachments"):
                    items.extend(item.attachments())
                if hasattr(item, "efforts"):
                    items.extend(item.efforts())
        self.assertEqual(3, categories[0].stylePriority())
        self.assertEqual(
            {"t1", "t1.1", "e1", "n1", "a1", "t2", "c1", "c1.1", "n2", "n2.1"},
            {item.id() for item in items},
        )
        self.assertEqual(
            [],
            [
                item.id()
                for item in items
                if item.modificationDateTime()
                != date.DateTime(2012, 12, 12, 12, 0, 0)
            ],
        )

    def test_adjust_due_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
          <task duedate="2012-12-12 23:59:00:000000" />
        </tasks>""")
        self.assertEqual(
            date.DateTime(2012, 12, 12, 23, 59, 59, 999999),
            tasks[0].dueDateTime(),
        )

    def test_dont_adjust_planned_start_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
          <task plannedstartdate="2012-12-12 23:59:00:000000" />
        </tasks>""")
        self.assertEqual(
            date.DateTime(2012, 12, 12, 23, 59, 0, 0),
            tasks[0].plannedStartDateTime(),
        )

    def test_dont_adjust_actual_start_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
          <task actualstartdate="2012-12-12 23:59:00:000000" />
        </tasks>""")
        self.assertEqual(
            date.DateTime(2012, 12, 12, 23, 59, 0, 0),
            tasks[0].actualStartDateTime(),
        )

    def test_dont_adjust_completion_date_time(self):
        tasks = self.writeAndReadTasks("""
        <tasks>
          <task completiondate="2012-12-12 23:59:00:000000" />
        </tasks>""")
        self.assertEqual(
            date.DateTime(2012, 12, 12, 23, 59, 0, 0),
            tasks[0].completionDateTime(),
        )

    def test_task_note_category(self):
        categories = self.writeAndReadCategories("""
        <tasks>
          <task>
            <note id="noteid" />
          </task>
          <category categorizables="noteid" />
        </tasks>""")
        self.assertTrue(
            "noteid" in [obj.id() for obj in categories[0].members()]
        )

    def test_subtask_note_category(self):
        categories = self.writeAndReadCategories("""
        <tasks>
          <task>
            <task>
              <note id="noteid" />
            </task>
          </task>
          <category categorizables="noteid" />
        </tasks>""")
        self.assertTrue(
            "noteid" in [obj.id() for obj in categories[0].members()]
        )

    def test_category_note_category(self):
        categories = self.writeAndReadCategories("""
        <tasks>
          <category categorizables="noteid">
            <note id="noteid" />
          </category>
        </tasks>""")
        self.assertTrue(
            "noteid" in [obj.id() for obj in categories[0].members()]
        )

    def test_subcategory_note_category(self):
        categories = self.writeAndReadCategories("""
        <tasks>
          <category categorizables="noteid">
            <category>
              <note id="noteid" />
            </category>

          </category>
        </tasks>""")
        self.assertTrue(
            "noteid" in [obj.id() for obj in categories[0].members()]
        )

    def test_task_attachment_note_category(self):
        categories = self.writeAndReadCategories("""
        <tasks>
          <task>
            <attachment location="test" type="file">
              <note id="noteid" />
            </attachment>
          </task>
          <category categorizables="noteid" />
        </tasks>""")
        self.assertTrue(
            "noteid" in [obj.id() for obj in categories[0].members()]
        )

    def test_subtask_attachment_note_category(self):
        categories = self.writeAndReadCategories("""
        <tasks>
          <task subject="Task">
            <task subject="Subtask">
              <attachment location="test" type="file" subject="Attachment">
                <note id="noteid" subject="Note" />
              </attachment>
            </task>
          </task>
          <category categorizables="noteid" subject="Category" />
        </tasks>""")
        self.assertTrue(
            "noteid" in [obj.id() for obj in categories[0].members()]
        )


class XMLReaderVersion38Test(XMLReaderTestCase):
    tskversion = 38  # New in release 2.0.3.0: categories on the items

    def test_task_categories(self):
        tasks, categories = self.writeAndReadTasksAndCategories("""
        <tasks>
            <task id="t1" categories="c1 c2"/>
            <category id="c1" subject="One"/>
            <category id="c2" subject="Two"/>
        </tasks>""")
        self.assertEqual(set(categories), tasks[0].categories())

    def test_subtask_with_subcategory(self):
        tasks, categories = self.writeAndReadTasksAndCategories("""
        <tasks>
            <task id="t1"><task id="t2" categories="c2"/></task>
            <category id="c1"><category id="c2"/></category>
        </tasks>""")
        self.assertEqual(
            {categories[0].children()[0]},
            tasks[0].children()[0].categories(),
        )

    def test_notes_of_every_owner_keep_their_categories(self):
        categories = self.writeAndReadCategories("""
        <tasks>
            <task id="t1">
                <note id="n1" categories="c1"/>
                <attachment location="test" type="file">
                    <note id="n2" categories="c1"/>
                </attachment>
            </task>
            <category id="c1"><note id="n3" categories="c1"/></category>
            <note id="n4"><note id="n5" categories="c1"/></note>
        </tasks>""")
        self.assertEqual(
            {"n1", "n2", "n3", "n5"},
            {each.id() for each in categories[0].members()},
        )

    def test_a_duplicate_id_keeps_its_own_categories(self):
        tasks, categories = self.writeAndReadTasksAndCategories("""
        <tasks>
            <task id="1" subject="first" categories="c1"/>
            <task id="1" subject="second" categories="c2"/>
            <category id="c1" subject="One"/>
            <category id="c2" subject="Two"/>
        </tasks>""")
        self.assertEqual(
            [["One"], ["Two"]],
            [[c.subject() for c in each.categories()] for each in tasks],
        )

    def test_other_forms_of_a_default_read_as_it(self):
        # defaults.DEFAULTS: the values after each default
        tasks = self.writeAndReadTasks("""
        <tasks>
            <task id="t1" duedate="None" plannedDurationMode="">
                <effort id="e1" start="2004-01-01 10:00:00" entryMode=""/>
            </task>
        </tasks>""")
        self.assertEqual(
            (date.DateTime(), "implicit", "standard"),
            (
                tasks[0].dueDateTime(),
                tasks[0].plannedDurationMode(),
                tasks[0].efforts()[0].entryMode(),
            ),
        )

    def test_mail_attachment_fields(self):
        mail = self.writeAndReadTasks("""
        <tasks>
            <task id="t1">
                <attachment id="a1" type="mail" location="mid:1@example.com"
                    subject="Quote" fromName="Alice"
                    fromAddress="alice@example.com"
                    sentDateTime="2026-09-29 14:05:00"/>
            </task>
        </tasks>""")[0].attachments()[0]
        self.assertEqual(
            (
                "mid:1@example.com",
                "Quote",
                "Alice",
                "alice@example.com",
                date.DateTime(2026, 9, 29, 14, 5, 0),
            ),
            (
                mail.location(),
                mail.subject(),
                mail.from_name(),
                mail.from_address(),
                mail.sent_datetime(),
            ),
        )

    def test_a_mail_whose_file_is_gone_still_loads(self):
        # Before tskversion 38, a dropped mail's location was a
        # temporary file, deleted at exit
        mail = self.writeAndReadTasks("""
        <tasks>
            <task id="t1">
                <attachment id="a1" type="mail" location="/gone/1.eml"
                    subject="Quote">
                    <description>Mail text</description>
                    <note id="n1" subject="Call back"/>
                </attachment>
            </task>
        </tasks>""")[0].attachments()[0]
        self.assertEqual(
            ("/gone/1.eml", "Quote", "Mail text", ["Call back"]),
            (
                mail.location(),
                mail.subject(),
                mail.description(),
                [each.subject() for each in mail.notes()],
            ),
        )
        self.assertEqual(
            ("", "", date.DateTime()),
            (mail.from_name(), mail.from_address(), mail.sent_datetime()),
        )

    def test_characters_xml_forbids_are_dropped(self):
        # Saved before stored text dropped them (P34), raw or referenced
        tasks = self.writeAndReadTasks(
            '<tasks><task subject="a&#12;b">'
            "<description>c\x00d&#x1f;e\tf</description>"
            "</task></tasks>"
        )
        self.assertEqual(
            ("ab", "cde\tf"), (tasks[0].subject(), tasks[0].description())
        )


class XMLReaderVersionsTest(XMLReaderTestCase):
    """Since 2.0.3.0 the PI holds two numbers: tskversion, the format a
    reader needs, and tskformat, the format written, which says how to
    read (docs/PERSISTENCE_XML.md, Versions and Compatibility)."""

    def read(self, versions, xml_contents):
        fd = io.StringIO(
            '<?taskcoach release="whatever" %s?>\n' % versions + xml_contents
        )
        fd.name = "testfile.tsk"
        self.reader = persistence.XMLReader(fd)
        return self.reader.read()

    @staticmethod
    def write(tasks, categories=(), notes=()):
        fd = io.BytesIO()
        persistence.XMLWriter(fd).write(
            task.TaskList(tasks),
            category.CategoryList(categories),
            note.NoteContainer(notes),
        )
        return fd.getvalue().decode("utf-8")

    def test_the_format_written_says_how_to_read(self):
        # Both forms of membership: the items' own is read
        tasks, categories, _ = self.read(
            'tskversion="37" tskformat="38"',
            """
        <tasks>
            <task id="t1" categories="c1"/>
            <task id="t2"/>
            <category id="c1" categorizables="t2"/>
        </tasks>""",
        )
        self.assertEqual(
            [{categories[0]}, set()], [each.categories() for each in tasks]
        )

    def test_versions_read(self):
        self.read('tskversion="37" tskformat="38"', "<tasks/>")
        self.assertEqual(
            (37, 38), (self.reader.version_needed(), self.reader.tskversion())
        )

    def test_versions_in_single_quotes(self):
        self.read("tskversion='37' tskformat='38'", "<tasks/>")
        self.assertEqual(
            (37, 38), (self.reader.version_needed(), self.reader.tskversion())
        )

    def test_the_version_line_after_another_instruction(self):
        fd = io.StringIO(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<?xml-stylesheet href="tasks.css"?>\n'
            '<?taskcoach release="whatever" tskversion="37"?>\n'
            '<tasks><task id="t1" subject="read"/></tasks>'
        )
        fd.name = "testfile.tsk"
        tasks, _, _ = persistence.XMLReader(fd).read()
        self.assertEqual(["read"], [each.subject() for each in tasks])

    def test_one_number_is_both(self):
        self.read('tskversion="38"', "<tasks/>")
        self.assertEqual(
            (38, 38), (self.reader.version_needed(), self.reader.tskversion())
        )

    def test_a_file_needing_a_newer_reader_is_refused(self):
        self.assertRaises(
            persistence.xml.reader.XMLReaderTooNewException,
            self.read,
            'tskversion="39"',
            "<tasks/>",
        )

    def test_a_newer_format_needing_no_newer_reader_is_read(self):
        tasks, _, _ = self.read(
            'tskversion="37" tskformat="39"',
            '<tasks><task id="t1" subject="Task"/></tasks>',
        )
        self.assertEqual("Task", tasks[0].subject())

    def test_a_mail_link_is_read_as_a_mail(self):
        # How older releases keep a mail: a link
        tasks, _, _ = self.read(
            'tskversion="37"',
            """
        <tasks><task id="t1">
            <attachment id="a1" type="uri" location="mid:1@example.com"/>
        </task></tasks>""",
        )
        self.assertIsInstance(
            tasks[0].attachments()[0], attachment.MailAttachment
        )

    def test_a_selected_icon_is_written_back_while_the_icon_is_unchanged(
        self,
    ):
        tasks, _, _ = self.read(
            'tskversion="37"',
            '<tasks><task id="t1" icon="nuvola_apps_clock" '
            'selectedIcon="nuvola_actions_go-next"/></tasks>',
        )
        written = self.write(tasks)
        tasks[0].set_icon_id("nuvola_actions_go-next")
        self.assertEqual(
            (True, False),
            (
                'selectedIcon="nuvola_actions_go-next"' in written,
                "selectedIcon" in self.write(tasks),
            ),
        )

    def test_a_stated_modification_date_is_written_back(self):
        # Also when equal to the creation date, which is left out
        # otherwise
        tasks, _, _ = self.read(
            'tskversion="37"',
            """
        <tasks>
            <task id="t1" creationDateTime="2026-01-01 10:00:00"
                modificationDateTime="2026-01-01 10:00:00"/>
            <task id="t2" creationDateTime="2026-01-01 10:00:00"/>
        </tasks>""",
        )
        self.assertEqual(
            1, self.write(tasks).count('modificationDateTime="2026-01-01')
        )
