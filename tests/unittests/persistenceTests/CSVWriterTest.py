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
import test
from taskcoachlib import persistence, gui, config, render
from taskcoachlib.domain import task, effort, date


class CSVWriterTestCase(test.wxTestCase):
    tree_mode = "Subclass responsibility"

    def setUp(self):
        super().setUp()
        task.Task.settings = self.settings = config.Settings(load=False)
        self.fd = io.StringIO()
        self.writer = persistence.CSVWriter(self.fd)
        self.taskFile = persistence.TaskFile()
        self.task = task.Task("Task subject")
        self.taskFile.tasks().append(self.task)
        self.createViewer()

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def createViewer(self):
        self.settings.set("taskviewer", "treemode", self.tree_mode)
        # pylint: disable=W0201
        self.viewer = gui.viewer.TaskViewer(
            self.frame, self.taskFile, self.settings
        )

    def __writeAndRead(
        self, selectionOnly, separateDateAndTimeColumns, columns
    ):
        self.writer.write(
            self.viewer,
            self.settings,
            selectionOnly,
            separateDateAndTimeColumns=separateDateAndTimeColumns,
            columns=columns,
        )
        return self.fd.getvalue()

    def expectInCSV(
        self,
        csvFragment,
        selectionOnly=False,
        separateDateAndTimeColumns=False,
        columns=None,
    ):
        csv = self.__writeAndRead(
            selectionOnly, separateDateAndTimeColumns, columns
        )
        self.assertTrue(
            csvFragment in csv, "%s not in %s" % (csvFragment, csv)
        )

    def expectNotInCSV(
        self,
        csvFragment,
        selectionOnly=False,
        separateDateAndTimeColumns=False,
        columns=None,
    ):
        csv = self.__writeAndRead(
            selectionOnly, separateDateAndTimeColumns, columns
        )
        self.assertFalse(csvFragment in csv, "%s in %s" % (csvFragment, csv))

    def selectItem(self, items):
        self.viewer.select(items)


class TaskTestsMixin(object):
    def testTaskSubject(self):
        self.expectInCSV("Task subject,")

    def testWriteSelectionOnly(self):
        self.expectNotInCSV("Task subject", selectionOnly=True)

    def testWriteSelectionOnly_SelectedChild(self):
        child = task.Task("Child", parent=self.task)
        self.taskFile.tasks().append(child)
        self.viewer.expandAll()
        self.selectItem([child])
        self.expectInCSV("Child,", selectionOnly=True)

    def testWriteSelectionOnly_SelectedParent(self):
        child = task.Task("Child", parent=self.task)
        self.taskFile.tasks().append(child)
        self.selectItem([self.task])
        self.expectNotInCSV("Child", selectionOnly=True)

    def testWriteSeparateDateAndTimeColumns(self):
        plannedStartDateTime = date.Now()
        self.task.setPlannedStartDateTime(plannedStartDateTime)
        self.expectInCSV(
            ",".join(
                (
                    render.date(plannedStartDateTime),
                    render.time(plannedStartDateTime),
                )
            ),
            separateDateAndTimeColumns=True,
        )

    def testWriteSeparateDateAndTimeColumnsWithDateBefore1900(self):
        plannedStartDateTime = date.DateTime(1600, 1, 1, 12, 30, 0)
        self.task.setPlannedStartDateTime(plannedStartDateTime)
        self.expectInCSV(
            ",".join(
                (
                    render.date(plannedStartDateTime),
                    render.time(plannedStartDateTime),
                )
            ),
            separateDateAndTimeColumns=True,
        )

    def testDontWriteSeparateDateAndTimeColumns(self):
        plannedStartDateTime = date.Now()
        self.task.setPlannedStartDateTime(plannedStartDateTime)
        self.expectInCSV(
            " ".join(
                (
                    render.date(plannedStartDateTime),
                    render.time(plannedStartDateTime),
                )
            ),
            separateDateAndTimeColumns=False,
        )

    def testDontWriteDefaultDateTimes(self):
        defaultDateTime = date.DateTime()
        self.expectNotInCSV(
            " ".join(
                [render.date(defaultDateTime), render.time(defaultDateTime)]
            ),
            separateDateAndTimeColumns=False,
        )

    def testDontWriteDefaultDateTimesWithSeparatedDateAndTimeColumns(self):
        defaultDateTime = date.DateTime()
        self.expectNotInCSV(
            ",".join(
                [render.date(defaultDateTime), render.time(defaultDateTime)]
            ),
            separateDateAndTimeColumns=True,
        )

    def testSpecifyColumns(self):
        self.task.setPriority(999)
        self.expectInCSV("999", columns=self.viewer.columns())

    def testPlannedStartDateTimeToday(self):
        today = date.Now()
        self.viewer.showColumnByName("plannedStartDateTime")
        self.task.setPlannedStartDateTime(today)
        self.expectInCSV(render.dateTime(today, humanReadable=False))

    def testPlannedStartDateTimeYesterday(self):
        yesterday = date.Yesterday()
        self.viewer.showColumnByName("plannedStartDateTime")
        self.task.setPlannedStartDateTime(yesterday)
        self.expectInCSV(render.dateTime(yesterday, humanReadable=False))

    def testPlannedStartDateTimeTomorrow(self):
        tomorrow = date.Tomorrow()
        self.viewer.showColumnByName("plannedStartDateTime")
        self.task.setPlannedStartDateTime(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, humanReadable=False))

    def testPlannedStartDateToday(self):
        today = date.Now().startOfDay()
        self.viewer.showColumnByName("plannedStartDateTime")
        self.task.setPlannedStartDateTime(today)
        self.expectInCSV(render.dateTime(today, humanReadable=False))

    def testPlannedStartDateYesterday(self):
        yesterday = date.Yesterday().startOfDay()
        self.viewer.showColumnByName("plannedStartDateTime")
        self.task.setPlannedStartDateTime(yesterday)
        self.expectInCSV(render.dateTime(yesterday, humanReadable=False))

    def testPlannedStartDateTomorrow(self):
        tomorrow = date.Tomorrow().startOfDay()
        self.viewer.showColumnByName("plannedStartDateTime")
        self.task.setPlannedStartDateTime(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, humanReadable=False))

    def testDueDateTimeToday(self):
        today = date.Now()
        self.viewer.showColumnByName("dueDateTime")
        self.task.setDueDateTime(today)
        self.expectInCSV(render.dateTime(today, humanReadable=False))

    def testDueDateTimeYesterday(self):
        yesterday = date.Yesterday()
        self.viewer.showColumnByName("dueDateTime")
        self.task.setDueDateTime(yesterday)
        self.expectInCSV(render.dateTime(yesterday, humanReadable=False))

    def testDueDateTimeTomorrow(self):
        tomorrow = date.Tomorrow()
        self.viewer.showColumnByName("dueDateTime")
        self.task.setDueDateTime(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, humanReadable=False))

    def testDueDateToday(self):
        today = date.Now().startOfDay()
        self.viewer.showColumnByName("dueDateTime")
        self.task.setDueDateTime(today)
        self.expectInCSV(render.dateTime(today, humanReadable=False))

    def testDueDateYesterday(self):
        yesterday = date.Yesterday().startOfDay()
        self.viewer.showColumnByName("dueDateTime")
        self.task.setDueDateTime(yesterday)
        self.expectInCSV(render.dateTime(yesterday, humanReadable=False))

    def testDueDateTomorrow(self):
        tomorrow = date.Tomorrow().startOfDay()
        self.viewer.showColumnByName("dueDateTime")
        self.task.setDueDateTime(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, humanReadable=False))

    def testActualStartDateTimeToday(self):
        today = date.Now()
        self.viewer.showColumnByName("actualStartDateTime")
        self.task.setActualStartDateTime(today)
        self.expectInCSV(render.dateTime(today, humanReadable=False))

    def testActualStartDateTimeYesterday(self):
        yesterday = date.Yesterday()
        self.viewer.showColumnByName("actualStartDateTime")
        self.task.setActualStartDateTime(yesterday)
        self.expectInCSV(render.dateTime(yesterday, humanReadable=False))

    def testActualStartDateTimeTomorrow(self):
        tomorrow = date.Tomorrow()
        self.viewer.showColumnByName("actualStartDateTime")
        self.task.setActualStartDateTime(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, humanReadable=False))

    def testActualStartDateToday(self):
        today = date.Now().startOfDay()
        self.viewer.showColumnByName("actualStartDateTime")
        self.task.setActualStartDateTime(today)
        self.expectInCSV(render.dateTime(today, humanReadable=False))

    def testActualStartDateYesterday(self):
        yesterday = date.Yesterday().startOfDay()
        self.viewer.showColumnByName("actualStartDateTime")
        self.task.setActualStartDateTime(yesterday)
        self.expectInCSV(render.dateTime(yesterday, humanReadable=False))

    def testActualStartDateTomorrow(self):
        tomorrow = date.Tomorrow().startOfDay()
        self.viewer.showColumnByName("actualStartDateTime")
        self.task.setActualStartDateTime(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, humanReadable=False))

    def testCompletionDateTimeToday(self):
        today = date.Now()
        self.viewer.showColumnByName("completionDateTime")
        self.task.setCompletionDateTime(today)
        self.expectInCSV(render.dateTime(today, humanReadable=False))

    def testCompletionDateTimeYesterday(self):
        yesterday = date.Yesterday()
        self.viewer.showColumnByName("completionDateTime")
        self.task.setCompletionDateTime(yesterday)
        self.expectInCSV(render.dateTime(yesterday, humanReadable=False))

    def testCompletionDateTimeTomorrow(self):
        tomorrow = date.Tomorrow()
        self.viewer.showColumnByName("completionDateTime")
        self.task.setCompletionDateTime(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, humanReadable=False))

    def testCompletionDateToday(self):
        today = date.Now().startOfDay()
        self.viewer.showColumnByName("completionDateTime")
        self.task.setCompletionDateTime(today)
        self.expectInCSV(render.dateTime(today, humanReadable=False))

    def testCompletionDateYesterday(self):
        yesterday = date.Yesterday().startOfDay()
        self.viewer.showColumnByName("completionDateTime")
        self.task.setCompletionDateTime(yesterday)
        self.expectInCSV(render.dateTime(yesterday, humanReadable=False))

    def testCompletionDateTomorrow(self):
        tomorrow = date.Tomorrow().startOfDay()
        self.viewer.showColumnByName("completionDateTime")
        self.task.setCompletionDateTime(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, humanReadable=False))

    def testCreationDateTime(self):
        self.viewer.showColumnByName("creationDateTime")
        self.expectInCSV(
            render.dateTime(self.task.creationDateTime(), humanReadable=False)
        )

    def testMissingCreationDateTime(self):
        self.viewer.showColumnByName("creationDateTime")
        self.taskFile.tasks().append(
            task.Task(creationDateTime=date.DateTime.min)
        )
        self.taskFile.tasks().remove(self.task)
        self.expectInCSV(",,,")  # No 1/1/1 for the missing creation date

    def testModificationDateTime(self):
        self.viewer.showColumnByName("modificationDateTime")
        self.task.setModificationDateTime(date.DateTime(2013, 1, 1, 12, 0, 0))
        self.expectInCSV(
            render.dateTime(
                self.task.modificationDateTime(), humanReadable=False
            )
        )

    def testMissingModificationDateTime(self):
        self.viewer.showColumnByName("modificationDateTime")
        self.task.setModificationDateTime(date.DateTime.min)
        self.expectInCSV(",,,")  # No 1/1/1 for the missing creation date


class CSVListWriterTest(TaskTestsMixin, CSVWriterTestCase):
    tree_mode = "False"

    def testTaskDescription(self):
        self.task.setDescription("Task description")
        self.viewer.showColumnByName("description")
        self.expectInCSV(",Task description,")

    def testTaskDescriptionWithNewLine(self):
        self.task.setDescription("Line1\nLine2")
        self.viewer.showColumnByName("description")
        self.expectInCSV('"Line1\nLine2"')


class CSVTreeWriterTest(TaskTestsMixin, CSVWriterTestCase):
    tree_mode = "True"


class EffortWriterTest(CSVWriterTestCase):
    def setUp(self):
        super().setUp()
        now = date.DateTime.now()
        self.effort = effort.Effort(
            self.task, start=now, stop=now + date.ONE_SECOND
        )
        self.task.addEffort(self.effort)

    def createViewer(self):
        # pylint: disable=W0201
        self.viewer = gui.viewer.EffortViewer(
            self.frame, self.taskFile, self.settings
        )

    def testTaskSubject(self):
        self.expectInCSV("Task subject,")

    def testEffortDuration(self):
        self.expectInCSV(",0:00:01")

    def testEffortPerDay(self):
        self.settings.settext(
            self.viewer.settingsSection(), "aggregation", "day"
        )
        self.expectInCSV("Total")

    def testEffortPerDay_SelectionOnly_EmptySelection(self):
        self.settings.settext(
            self.viewer.settingsSection(), "aggregation", "day"
        )
        self.expectNotInCSV("Total", selectionOnly=True)

    def testEffortPerDay_SelectionOnly_SelectAll(self):
        self.settings.settext(
            self.viewer.settingsSection(), "aggregation", "day"
        )
        self.viewer.widget.select_all()
        self.viewer.updateSelection()
        self.expectInCSV("Total", selectionOnly=True)

    def testExportAllColumns_NoSplit(self):
        self.expectInCSV(
            render.dateTimePeriod(
                self.effort.getStart(), self.effort.getStop()
            ),
            columns=self.viewer.selectable_columns(),
        )

    def testExportAllColumns_Split(self):
        self.expectInCSV(
            "%s,%s,%s,%s"
            % (
                render.date(self.effort.getStart().date()),
                render.time(self.effort.getStart().time()),
                render.date(self.effort.getStop().date()),
                render.time(self.effort.getStop().time()),
            ),
            separateDateAndTimeColumns=True,
            columns=self.viewer.selectable_columns(),
        )


class EffortWriterRenderTest(CSVWriterTestCase):
    def createViewer(self):
        # pylint: disable=W0201
        self.viewer = gui.viewer.EffortViewer(
            self.frame, self.taskFile, self.settings
        )

    def testToday(self):
        midnight = date.Now().startOfDay()
        self.task.addEffort(
            effort.Effort(
                self.task, start=midnight, stop=midnight + date.TWO_HOURS
            )
        )
        self.expectNotInCSV("Today")

    def testTomorrow(self):
        midnight = date.Tomorrow().startOfDay()
        self.task.addEffort(
            effort.Effort(
                self.task, start=midnight, stop=midnight + date.TWO_HOURS
            )
        )
        self.expectNotInCSV("Tomorrow")

    def testYesterday(self):
        midnight = date.Yesterday().startOfDay()
        self.task.addEffort(
            effort.Effort(
                self.task, start=midnight, stop=midnight + date.TWO_HOURS
            )
        )
        self.expectNotInCSV("Today")
