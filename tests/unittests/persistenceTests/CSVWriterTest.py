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
from taskcoachlib import persistence, gui, render
from taskcoachlib.domain import task, effort, date
from taskcoachlib.config import settings


class CSVWriterTestCase(test.wxTestCase):
    tree_mode = "Subclass responsibility"

    def setUp(self):
        super().setUp()
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
        settings.set("taskviewer", "treemode", self.tree_mode)
        # pylint: disable=W0201
        self.viewer = gui.viewer.TaskViewer(self.frame, self.taskFile)

    def __writeAndRead(
        self, selectionOnly, separateDateAndTimeColumns, columns
    ):
        self.writer.write(
            self.viewer,
            selectionOnly,
            separateDateAndTimeColumns=separateDateAndTimeColumns,
            columns=columns,
        )
        return self.fd.getvalue()

    def expectInCSV(
        self,
        csv_fragment,
        selectionOnly=False,
        separateDateAndTimeColumns=False,
        columns=None,
    ):
        csv = self.__writeAndRead(
            selectionOnly, separateDateAndTimeColumns, columns
        )
        self.assertTrue(
            csv_fragment in csv, "%s not in %s" % (csv_fragment, csv)
        )

    def expectNotInCSV(
        self,
        csv_fragment,
        selectionOnly=False,
        separateDateAndTimeColumns=False,
        columns=None,
    ):
        csv = self.__writeAndRead(
            selectionOnly, separateDateAndTimeColumns, columns
        )
        self.assertFalse(csv_fragment in csv, "%s in %s" % (csv_fragment, csv))

    def selectItem(self, items):
        self.viewer.select(items)


class TaskTestsMixin(object):
    def test_task_subject(self):
        self.expectInCSV("Task subject,")

    def test_write_selection_only(self):
        self.expectNotInCSV("Task subject", selectionOnly=True)

    def test_write_selection_only_selected_child(self):
        child = task.Task("Child", parent=self.task)
        self.taskFile.tasks().append(child)
        self.viewer.expand_all()
        self.selectItem([child])
        self.expectInCSV("Child,", selectionOnly=True)

    def test_write_selection_only_selected_parent(self):
        child = task.Task("Child", parent=self.task)
        self.taskFile.tasks().append(child)
        self.selectItem([self.task])
        self.expectNotInCSV("Child", selectionOnly=True)

    def test_write_separate_date_and_time_columns(self):
        planned_start_date_time = date.Now()
        self.task.set_planned_start_date_time(planned_start_date_time)
        self.expectInCSV(
            ",".join(
                (
                    render.date(planned_start_date_time),
                    render.time(planned_start_date_time),
                )
            ),
            separateDateAndTimeColumns=True,
        )

    def test_write_separate_date_and_time_columns_with_date_before_1900(self):
        planned_start_date_time = date.DateTime(1600, 1, 1, 12, 30, 0)
        self.task.set_planned_start_date_time(planned_start_date_time)
        self.expectInCSV(
            ",".join(
                (
                    render.date(planned_start_date_time),
                    render.time(planned_start_date_time),
                )
            ),
            separateDateAndTimeColumns=True,
        )

    def test_dont_write_separate_date_and_time_columns(self):
        # Not at 23:59 or 00:00, which render as a date alone
        planned_start = date.DateTime(2026, 1, 15, 12, 30, 0)
        self.task.set_planned_start_date_time(planned_start)
        self.expectInCSV(
            " ".join(
                (
                    render.date(planned_start),
                    render.time(planned_start),
                )
            ),
            separateDateAndTimeColumns=False,
        )

    def test_dont_write_default_date_times(self):
        default_date_time = date.DateTime()
        self.expectNotInCSV(
            " ".join(
                [
                    render.date(default_date_time),
                    render.time(default_date_time),
                ]
            ),
            separateDateAndTimeColumns=False,
        )

    def test_dont_write_default_date_times_in_separate_date_time_columns(
        self,
    ):
        default_date_time = date.DateTime()
        self.expectNotInCSV(
            ",".join(
                [
                    render.date(default_date_time),
                    render.time(default_date_time),
                ]
            ),
            separateDateAndTimeColumns=True,
        )

    def test_specify_columns(self):
        self.task.setPriority(999)
        self.expectInCSV("999", columns=self.viewer.columns())

    def test_planned_start_date_time_today(self):
        today = date.Now()
        self.viewer.showColumnByName("plannedStartDateTime")
        self.task.set_planned_start_date_time(today)
        self.expectInCSV(render.dateTime(today, human_readable=False))

    def test_planned_start_date_time_yesterday(self):
        yesterday = date.Yesterday()
        self.viewer.showColumnByName("plannedStartDateTime")
        self.task.set_planned_start_date_time(yesterday)
        self.expectInCSV(render.dateTime(yesterday, human_readable=False))

    def test_planned_start_date_time_tomorrow(self):
        tomorrow = date.Tomorrow()
        self.viewer.showColumnByName("plannedStartDateTime")
        self.task.set_planned_start_date_time(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, human_readable=False))

    def test_planned_start_date_today(self):
        today = date.Now().startOfDay()
        self.viewer.showColumnByName("plannedStartDateTime")
        self.task.set_planned_start_date_time(today)
        self.expectInCSV(render.dateTime(today, human_readable=False))

    def test_planned_start_date_yesterday(self):
        yesterday = date.Yesterday().startOfDay()
        self.viewer.showColumnByName("plannedStartDateTime")
        self.task.set_planned_start_date_time(yesterday)
        self.expectInCSV(render.dateTime(yesterday, human_readable=False))

    def test_planned_start_date_tomorrow(self):
        tomorrow = date.Tomorrow().startOfDay()
        self.viewer.showColumnByName("plannedStartDateTime")
        self.task.set_planned_start_date_time(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, human_readable=False))

    def test_due_date_time_today(self):
        today = date.Now()
        self.viewer.showColumnByName("dueDateTime")
        self.task.set_due_date_time(today)
        self.expectInCSV(render.dateTime(today, human_readable=False))

    def test_due_date_time_yesterday(self):
        yesterday = date.Yesterday()
        self.viewer.showColumnByName("dueDateTime")
        self.task.set_due_date_time(yesterday)
        self.expectInCSV(render.dateTime(yesterday, human_readable=False))

    def test_due_date_time_tomorrow(self):
        tomorrow = date.Tomorrow()
        self.viewer.showColumnByName("dueDateTime")
        self.task.set_due_date_time(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, human_readable=False))

    def test_due_date_today(self):
        today = date.Now().startOfDay()
        self.viewer.showColumnByName("dueDateTime")
        self.task.set_due_date_time(today)
        self.expectInCSV(render.dateTime(today, human_readable=False))

    def test_due_date_yesterday(self):
        yesterday = date.Yesterday().startOfDay()
        self.viewer.showColumnByName("dueDateTime")
        self.task.set_due_date_time(yesterday)
        self.expectInCSV(render.dateTime(yesterday, human_readable=False))

    def test_due_date_tomorrow(self):
        tomorrow = date.Tomorrow().startOfDay()
        self.viewer.showColumnByName("dueDateTime")
        self.task.set_due_date_time(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, human_readable=False))

    def test_actual_start_date_time_today(self):
        today = date.Now()
        self.viewer.showColumnByName("actualStartDateTime")
        self.task.set_actual_start_date_time(today)
        self.expectInCSV(render.dateTime(today, human_readable=False))

    def test_actual_start_date_time_yesterday(self):
        yesterday = date.Yesterday()
        self.viewer.showColumnByName("actualStartDateTime")
        self.task.set_actual_start_date_time(yesterday)
        self.expectInCSV(render.dateTime(yesterday, human_readable=False))

    def test_actual_start_date_time_tomorrow(self):
        tomorrow = date.Tomorrow()
        self.viewer.showColumnByName("actualStartDateTime")
        self.task.set_actual_start_date_time(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, human_readable=False))

    def test_actual_start_date_today(self):
        today = date.Now().startOfDay()
        self.viewer.showColumnByName("actualStartDateTime")
        self.task.set_actual_start_date_time(today)
        self.expectInCSV(render.dateTime(today, human_readable=False))

    def test_actual_start_date_yesterday(self):
        yesterday = date.Yesterday().startOfDay()
        self.viewer.showColumnByName("actualStartDateTime")
        self.task.set_actual_start_date_time(yesterday)
        self.expectInCSV(render.dateTime(yesterday, human_readable=False))

    def test_actual_start_date_tomorrow(self):
        tomorrow = date.Tomorrow().startOfDay()
        self.viewer.showColumnByName("actualStartDateTime")
        self.task.set_actual_start_date_time(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, human_readable=False))

    def test_completion_date_time_today(self):
        today = date.Now()
        self.viewer.showColumnByName("completionDateTime")
        self.task.set_completion_date_time(today)
        self.expectInCSV(render.dateTime(today, human_readable=False))

    def test_completion_date_time_yesterday(self):
        yesterday = date.Yesterday()
        self.viewer.showColumnByName("completionDateTime")
        self.task.set_completion_date_time(yesterday)
        self.expectInCSV(render.dateTime(yesterday, human_readable=False))

    def test_completion_date_time_tomorrow(self):
        tomorrow = date.Tomorrow()
        self.viewer.showColumnByName("completionDateTime")
        self.task.set_completion_date_time(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, human_readable=False))

    def test_completion_date_today(self):
        today = date.Now().startOfDay()
        self.viewer.showColumnByName("completionDateTime")
        self.task.set_completion_date_time(today)
        self.expectInCSV(render.dateTime(today, human_readable=False))

    def test_completion_date_yesterday(self):
        yesterday = date.Yesterday().startOfDay()
        self.viewer.showColumnByName("completionDateTime")
        self.task.set_completion_date_time(yesterday)
        self.expectInCSV(render.dateTime(yesterday, human_readable=False))

    def test_completion_date_tomorrow(self):
        tomorrow = date.Tomorrow().startOfDay()
        self.viewer.showColumnByName("completionDateTime")
        self.task.set_completion_date_time(tomorrow)
        self.expectInCSV(render.dateTime(tomorrow, human_readable=False))

    def test_creation_date_time(self):
        self.viewer.showColumnByName("creationDateTime")
        self.expectInCSV(
            render.dateTime(self.task.creationDateTime(), human_readable=False)
        )

    def test_missing_creation_date_time(self):
        self.viewer.showColumnByName("creationDateTime")
        self.taskFile.tasks().append(
            task.Task(creationDateTime=date.DateTime.min)
        )
        self.taskFile.tasks().remove(self.task)
        self.expectInCSV(",,,")  # No 1/1/1 for the missing creation date

    def test_modification_date_time(self):
        self.viewer.showColumnByName("modificationDateTime")
        self.task.set_modification_datetime(
            date.DateTime(2013, 1, 1, 12, 0, 0)
        )
        self.expectInCSV(
            render.dateTime(
                self.task.modificationDateTime(), human_readable=False
            )
        )

    def test_missing_modification_date_time(self):
        self.viewer.showColumnByName("modificationDateTime")
        self.task.set_modification_datetime(date.DateTime.min)
        self.expectInCSV(",,,")  # No 1/1/1 for the missing creation date


class CSVListWriterTest(TaskTestsMixin, CSVWriterTestCase):
    tree_mode = False

    def test_task_description(self):
        self.task.setDescription("Task description")
        self.viewer.showColumnByName("description")
        self.expectInCSV(",Task description,")

    def test_task_description_with_new_line(self):
        self.task.setDescription("Line1\nLine2")
        self.viewer.showColumnByName("description")
        self.expectInCSV('"Line1\nLine2"')


class CSVTreeWriterTest(TaskTestsMixin, CSVWriterTestCase):
    tree_mode = True


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
        self.viewer = gui.viewer.EffortViewer(self.frame, self.taskFile)

    def test_task_subject(self):
        self.expectInCSV("Task subject,")

    def test_effort_duration(self):
        self.expectInCSV(",0:00:01")

    def test_effort_per_day(self):
        self.viewer.set_aggregation("day")
        self.expectInCSV("Total")

    def test_effort_per_day_selection_only_empty_selection(self):
        self.viewer.set_aggregation("day")
        self.expectNotInCSV("Total", selectionOnly=True)

    def test_effort_per_day_selection_only_select_all(self):
        self.viewer.set_aggregation("day")
        self.viewer.widget.select_all()
        self.viewer.updateSelection()
        self.expectInCSV("Total", selectionOnly=True)

    def test_export_all_columns_no_split(self):
        self.expectInCSV(
            render.dateTimePeriod(
                self.effort.getStart(), self.effort.getStop()
            ),
            columns=self.viewer.selectable_columns(),
        )

    def test_export_all_columns_split(self):
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
        self.viewer = gui.viewer.EffortViewer(self.frame, self.taskFile)

    def test_today(self):
        midnight = date.Now().startOfDay()
        self.task.addEffort(
            effort.Effort(
                self.task, start=midnight, stop=midnight + date.TWO_HOURS
            )
        )
        self.expectNotInCSV("Today")

    def test_tomorrow(self):
        midnight = date.Tomorrow().startOfDay()
        self.task.addEffort(
            effort.Effort(
                self.task, start=midnight, stop=midnight + date.TWO_HOURS
            )
        )
        self.expectNotInCSV("Tomorrow")

    def test_yesterday(self):
        midnight = date.Yesterday().startOfDay()
        self.task.addEffort(
            effort.Effort(
                self.task, start=midnight, stop=midnight + date.TWO_HOURS
            )
        )
        self.expectNotInCSV("Today")
