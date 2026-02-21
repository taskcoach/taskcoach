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

import test, io, time
from taskcoachlib import persistence, gui, config, meta
from taskcoachlib.domain import task, effort, date


class UTF8StringIO(io.StringIO):
    """
    Mimic codecs.open; encodes on the fly in UTF-8
    """

    def write(self, u):
        io.StringIO.write(self, u.encode("UTF-8"))


class VCalTestCase(test.wxTestCase):
    selectionOnly = "Subclass responsibility"

    def setUp(self):
        super().setUp()
        task.Task.settings = self.settings = config.Settings(load=False)
        self.fd = UTF8StringIO()
        self.writer = persistence.iCalendarWriter(self.fd)
        self.taskFile = persistence.TaskFile()

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def writeAndRead(self):
        self.writer.write(self.viewer, self.settings, self.selectionOnly)
        return self.fd.getvalue().decode("utf-8")

    def selectItems(self, items):
        self.viewer.select(items)

    def numberOfSelectedItems(self):
        return len(self.viewer.curselection())

    def numberOfVisibleItems(self):
        return self.viewer.size()


class VCalendarCommonTestsMixin(object):
    def testStart(self):
        self.assertEqual("BEGIN:VCALENDAR", self.vcalFile.split("\r\n")[0])

    def testVersion(self):
        self.assertEqual("VERSION:2.0", self.vcalFile.split("\r\n")[1])

    def testProdId(self):
        domain = meta.url[len("http://") : -1]
        self.assertEqual(
            "PRODID:-//%s//NONSGML %s V%s//EN"
            % (domain, meta.name, meta.version),
            self.vcalFile.split("\r\n")[2],
        )

    def testEnd(self):
        self.assertEqual("END:VCALENDAR", self.vcalFile.split("\r\n")[-2])


class VCalEffortWriterTestCase(VCalTestCase):
    def setUp(self):
        super().setUp()
        self.task1 = task.Task("Task 1")
        self.effort1 = effort.Effort(
            self.task1,
            description="Description",
            start=date.DateTime(2000, 1, 1, 1, 1, 1),
            stop=date.DateTime(2000, 2, 2, 2, 2, 2),
        )
        self.effort2 = effort.Effort(self.task1)
        self.task1.addEffort(self.effort1)
        self.task1.addEffort(self.effort2)
        self.taskFile.tasks().extend([self.task1])
        self.viewer = gui.viewer.EffortViewer(
            self.frame, self.taskFile, self.settings
        )
        self.viewer.widget.select([self.effort1])
        self.viewer.updateSelection()
        self.vcalFile = self.writeAndRead()


class VCalEffortCommonTestsMixin(VCalendarCommonTestsMixin):
    def testBeginVEvent(self):
        self.assertEqual(
            self.expectedNumberOfItems(), self.vcalFile.count("BEGIN:VEVENT")
        )

    def testEndVEvent(self):
        self.assertEqual(
            self.expectedNumberOfItems(), self.vcalFile.count("END:VEVENT")
        )

    def testEffortSubject(self):
        self.assertTrue("SUMMARY:Task 1" in self.vcalFile)

    def testEffortDescription(self):
        self.assertTrue("DESCRIPTION:Description" in self.vcalFile)

    def testEffortStart(self):
        startLocal = date.DateTime(2000, 1, 1, 1, 1, 1)
        startUTC = startLocal.utcfromtimestamp(
            time.mktime(startLocal.timetuple())
        )
        self.assertTrue(
            "DTSTART:%04d%02d%02dT%02d%02d%02dZ"
            % (
                startUTC.year,
                startUTC.month,
                startUTC.day,
                startUTC.hour,
                startUTC.minute,
                startUTC.second,
            )
        )

    def testEffortEnd(self):
        endLocal = date.DateTime(2000, 2, 2, 2, 2, 2)
        endUTC = endLocal.utcfromtimestamp(time.mktime(endLocal.timetuple()))
        self.assertTrue(
            "DTEND:%04d%02d%02dT%02d%02d%02dZ"
            % (
                endUTC.year,
                endUTC.month,
                endUTC.day,
                endUTC.hour,
                endUTC.minute,
                endUTC.second,
            )
        )

    def testEffortId(self):
        self.assertTrue("UID:%s" % self.effort1.id() in self.vcalFile)


class VCalEffortWriterTest(
    VCalEffortWriterTestCase, VCalEffortCommonTestsMixin
):
    selectionOnly = False

    def expectedNumberOfItems(self):
        return self.numberOfVisibleItems()


class VCalEffortWriterSelectionOnlyTest(
    VCalEffortWriterTestCase, VCalEffortCommonTestsMixin
):
    selectionOnly = True

    def expectedNumberOfItems(self):
        return self.numberOfSelectedItems()


class VCalTaskWriterTestCase(VCalTestCase):
    tree_mode = "Subclass responsibility"

    def setUp(self):
        super().setUp()
        self.task1 = task.Task(
            "Task subject 1",
            description="Task description 1",
            percentageComplete=56,
            creationDateTime=date.DateTime.min,
        )
        self.task2 = task.Task(
            "Task subject 2黑",
            description="Task description 2\nwith newline\n微软雅黑",
            modificationDateTime=date.DateTime(2012, 1, 1),
        )
        self.taskFile.tasks().extend([self.task1, self.task2])
        self.settings.set("taskviewer", "treemode", self.tree_mode)
        self.viewer = gui.viewer.TaskViewer(
            self.frame, self.taskFile, self.settings
        )
        self.selectItems([self.task2])
        self.vcalFile = self.writeAndRead()


class VCalTaskCommonTestsMixin(VCalendarCommonTestsMixin):
    def testTaskSubject(self):
        self.assertTrue("SUMMARY:Task subject 2" in self.vcalFile)

    def testTaskDescription(self):
        self.assertTrue(
            "DESCRIPTION:Task description 2\r\n with newline\r\n 微软雅黑"
            in self.vcalFile,
            self.vcalFile,
        )

    def testNumber(self):
        self.assertEqual(
            self.expectedNumberOfItems(), self.vcalFile.count("BEGIN:VTODO")
        )  # pylint: disable=W0511

    def testTaskId(self):
        self.assertTrue("UID:%s" % self.task2.id() in self.vcalFile)

    def testCreationDateTime(self):
        creation_datetime = persistence.icalendar.ical.fmtDateTime(
            self.task2.creationDateTime()
        )
        self.assertTrue("CREATED:%s" % creation_datetime in self.vcalFile)

    def testMissingCreationDateTime(self):
        self.assertEqual(1, self.vcalFile.count("CREATED:"))

    def testModificationDateTime(self):
        modification_datetime = persistence.icalendar.ical.fmtDateTime(
            date.DateTime(2012, 1, 1)
        )
        self.assertTrue(
            "LAST-MODIFIED:%s" % modification_datetime in self.vcalFile
        )

    def testMissingModificationDateTime(self):
        self.assertEqual(1, self.vcalFile.count("LAST-MODIFIED"))


class TestSelectionOnlyMixin(VCalTaskCommonTestsMixin):
    selectionOnly = True

    def expectedNumberOfItems(self):
        return self.numberOfSelectedItems()


class TestSelectionList(TestSelectionOnlyMixin, VCalTaskWriterTestCase):
    tree_mode = "False"


class TestSelectionTree(TestSelectionOnlyMixin, VCalTaskWriterTestCase):
    tree_mode = "True"


class TestNotSelectionOnlyMixin(VCalTaskCommonTestsMixin):
    selectionOnly = False

    def expectedNumberOfItems(self):
        return self.numberOfVisibleItems()

    def testPercentageComplete(self):
        self.assertTrue("PERCENT-COMPLETE:56" in self.vcalFile)


class TestNotSelectionList(TestNotSelectionOnlyMixin, VCalTaskWriterTestCase):
    tree_mode = "False"


class TestNotSelectionTree(TestNotSelectionOnlyMixin, VCalTaskWriterTestCase):
    tree_mode = "True"


class FoldTest(test.TestCase):
    def setUp(self):
        super().setUp()
        self.fold = persistence.icalendar.ical.fold

    def testEmptyText(self):
        self.assertEqual("", self.fold([]))

    def testDontFoldAShortLine(self):
        self.assertEqual("Short line\r\n", self.fold(["Short line"]))

    def testFoldALongLine(self):
        self.assertEqual(
            "Long \r\n line\r\n", self.fold(["Long line"], linewidth=5)
        )

    def testFoldAReallyLongLine(self):
        self.assertEqual(
            "Long\r\n  li\r\n ne\r\n", self.fold(["Long line"], linewidth=4)
        )

    def testFoldTwoShortLines(self):
        self.assertEqual("Short line\r\n" * 2, self.fold(["Short line"] * 2))

    def testFoldTwoLongLines(self):
        self.assertEqual(
            "Long \r\n line\r\n" * 2, self.fold(["Long line"] * 2, linewidth=5)
        )

    def testFoldALineWithNewLines(self):
        self.assertEqual(
            "Line 1\r\n Line 2\r\n", self.fold(["Line 1\nLine 2"])
        )
