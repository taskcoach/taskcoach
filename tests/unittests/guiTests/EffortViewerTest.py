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

from taskcoachlib import command, gui, patterns, persistence, render
from taskcoachlib.domain import category, task, effort, date
from taskcoachlib.config import settings
from unittests import dummy
from unittests.headermouse import HeaderMouse
import test
import wx


class EffortViewerUnderTest(gui.viewer.EffortViewer):  # pylint: disable=W0223
    def create_widget(self):
        return dummy.DummyWidget(self)

    def columns(self):
        return []


class EffortViewerForSpecificTasksTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.taskFile = persistence.TaskFile()
        self.task1 = task.Task("Task 1")
        self.task2 = task.Task("Task 2")
        self.taskFile.tasks().extend([self.task1, self.task2])
        self.effort1 = effort.Effort(
            self.task1, date.DateTime(2006, 1, 1), date.DateTime(2006, 1, 2)
        )
        self.task1.addEffort(self.effort1)
        self.effort2 = effort.Effort(
            self.task2, date.DateTime(2006, 1, 2), date.DateTime(2006, 1, 3)
        )
        self.task2.addEffort(self.effort2)
        self.viewer = EffortViewerUnderTest(
            self.frame,
            self.taskFile,
            tasksToShowEffortFor=task.TaskList([self.task1]),
        )

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def test_viewer_shows_only_effort_for_specified_task(self):
        self.assertEqual([self.effort1], self.viewer.presentation())

    def test_effort_editor_does_use_all_tasks(self):
        dialog = self.viewer.newItemDialog()
        self.assertEqual(
            2, len(dialog._taskFile.tasks())
        )  # pylint: disable=W0212

    def test_viewer_shows_only_tasks_efforts_after_switching_aggregation(
        self,
    ):
        self.viewer.set_aggregation("week")
        self.assertEqual(2, len(self.viewer.presentation()))

    def test_column_menu_follows_the_aggregation_when_refilled(self):
        column_menu = gui.menu.EffortViewerColumnPopupMenu(self.viewer)

        def labels():
            # What the column header does before popping it up
            column_menu.updateMenu()
            return [i.GetItemLabelText() for i in column_menu.GetMenuItems()]

        self.assertNotIn("Effort per weekday", labels())
        self.viewer.set_aggregation("week")
        self.assertIn("Effort per weekday", labels())


class LocalEffortViewerUnderTest(gui.dialog.editor.LocalEffortViewer):
    def create_widget(self):
        return dummy.DummyWidget(self)

    def columns(self):
        return []


class EffortViewsUnderCategoryFilterTest(test.wxTestCase):
    """With a category ticked, the main window's effort views show the
    efforts of tasks in it; a task's editor shows all of the task's
    (docs/EFFORTS.md, Filters; GitHub #157)."""

    def setUp(self):
        super().setUp()
        self.task_file = persistence.TaskFile()
        self.parent = task.Task("Parent")
        self.child = task.Task("In the category")
        self.other_child = task.Task("Not in the category")
        self.parent.addChild(self.child)
        self.parent.addChild(self.other_child)
        self.task_file.tasks().append(self.parent)
        work = category.Category("Work")
        self.task_file.categories().append(work)
        self.child.addCategory(work)
        work.setFiltered(True)
        self.parent_effort = self.effort(self.parent)
        self.child_effort = self.effort(self.child)
        self.other_child_effort = self.effort(self.other_child)

    def tearDown(self):
        super().tearDown()
        self.task_file.close()
        self.task_file.stop()

    @staticmethod
    def effort(of_task):
        an_effort = effort.Effort(
            of_task, date.DateTime(2026, 1, 1), date.DateTime(2026, 1, 2)
        )
        of_task.addEffort(an_effort)
        return an_effort

    def viewer(self, viewer_class):
        return viewer_class(
            self.frame,
            self.task_file,
            tasksToShowEffortFor=task.TaskList([self.parent]),
        )

    def test_effort_for_chosen_tasks_follows_the_filter(self):
        viewer = self.viewer(EffortViewerUnderTest)
        self.assertEqual([self.child_effort], list(viewer.presentation()))

    def test_the_editor_shows_every_effort_of_the_task(self):
        viewer = self.viewer(LocalEffortViewerUnderTest)
        self.assertEqual(
            {self.parent_effort, self.child_effort, self.other_child_effort},
            set(viewer.presentation()),
        )

    def test_a_new_effort_shows_in_the_editor(self):
        viewer = self.viewer(LocalEffortViewerUnderTest)
        new_effort = self.effort(self.parent)
        self.assertIn(new_effort, viewer.presentation())

    def test_the_editor_has_no_reset_filter_button(self):
        viewer = self.viewer(LocalEffortViewerUnderTest)
        self.assertFalse(
            any(
                isinstance(each, gui.uicommand.ResetFilter)
                for each in viewer.createToolBarUICommands()
            )
        )


class EffortViewerStatusMessageTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.taskFile = persistence.TaskFile()
        self.task = task.Task()
        self.taskFile.tasks().append(self.task)
        self.effort1 = effort.Effort(
            self.task, date.DateTime(2006, 1, 1), date.DateTime(2006, 1, 2)
        )
        self.effort2 = effort.Effort(
            self.task, date.DateTime(2006, 1, 2), date.DateTime(2006, 1, 3)
        )
        self.viewer = EffortViewerUnderTest(self.frame, self.taskFile)

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def assertStatusMessages(self, message1, message2):
        self.assertEqual((message1, message2), self.viewer.statusMessages())

    def test_status_message_empty_task_list(self):
        self.taskFile.tasks().clear()
        self.assertStatusMessages(
            "Effort: 0 selected, 0 visible, 0 total. Time spent: 0:00:00 selected, 0:00:00 visible, 0:00:00 total",
            "Status: 0 tracking",
        )

    def test_status_message_one_task_no_effort(self):
        self.assertStatusMessages(
            "Effort: 0 selected, 0 visible, 0 total. Time spent: 0:00:00 selected, 0:00:00 visible, 0:00:00 total",
            "Status: 0 tracking",
        )

    def test_status_message_one_task_one_effort(self):
        self.task.addEffort(self.effort1)
        self.assertStatusMessages(
            "Effort: 0 selected, 1 visible, 1 total. Time spent: 0:00:00 selected, 24:00:00 visible, 24:00:00 total",
            "Status: 0 tracking",
        )

    def test_status_message_one_task_two_efforts(self):
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.assertStatusMessages(
            "Effort: 0 selected, 2 visible, 2 total. Time spent: 0:00:00 selected, 48:00:00 visible, 48:00:00 total",
            "Status: 0 tracking",
        )

    def test_status_message_one_task_one_active_effort(self):
        self.task.addEffort(effort.Effort(self.task))
        # Just started: a second may pass before the message is made
        expected = [
            (
                "Effort: 0 selected, 1 visible, 1 total. Time spent: "
                "0:00:00 selected, %s visible, %s total" % (spent, spent),
                "Status: 1 tracking",
            )
            for spent in ("0:00:00", "0:00:01")
        ]
        self.assertIn(self.viewer.statusMessages(), expected)

    def test_status_message_in_aggregated_mode_one_task_no_effort(self):
        self.viewer.set_aggregation("day")
        self.assertStatusMessages(
            "Effort: 0 selected, 0 visible, 0 total. Time spent: 0:00:00 selected, 0:00:00 visible, 0:00:00 total",
            "Status: 0 tracking",
        )

    def test_status_message_in_aggregate_mode_one_task_one_effort(self):
        self.viewer.set_aggregation("day")
        self.task.addEffort(self.effort1)
        self.assertStatusMessages(
            "Effort: 0 selected, 2 visible, 1 total. Time spent: 0:00:00 selected, 48:00:00 visible, 24:00:00 total",
            "Status: 0 tracking",
        )

    def test_status_message_in_aggregate_mode_one_task_two_efforts(self):
        self.viewer.set_aggregation("day")
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.assertStatusMessages(
            "Effort: 0 selected, 4 visible, 2 total. Time spent: 0:00:00 selected, 96:00:00 visible, 48:00:00 total",
            "Status: 0 tracking",
        )


class EffortViewerTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.taskFile = persistence.TaskFile()
        self.task = task.Task("task")
        self.taskFile.tasks().append(self.task)
        self.effort1 = effort.Effort(
            self.task, date.DateTime(2006, 1, 1), date.DateTime(2006, 1, 2)
        )
        self.effort2 = effort.Effort(
            self.task, date.DateTime(2006, 1, 2), date.DateTime(2006, 1, 3)
        )
        self.viewer = gui.viewer.EffortViewer(self.frame, self.taskFile)

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    @test.skipOnPlatform(
        "__WXMSW__"
    )  # GetItemBackgroundColour doesn't work on Windows
    def test_effort_background_color(self):  # pragma: no cover
        self.task.setBackgroundColor(wx.RED)
        self.task.addEffort(self.effort1)
        self.assertEqual(wx.RED, self.viewer.widget.GetItemBackgroundColour(0))

    @test.skipOnPlatform(
        "__WXMSW__"
    )  # GetItemBackgroundColour doesn't work on Windows
    def test_update_effort_background_color(self):  # pragma: no cover
        self.task.addEffort(self.effort1)
        self.task.setBackgroundColor(wx.RED)
        self.assertEqual(wx.RED, self.viewer.widget.GetItemBackgroundColour(0))

    def record_refreshes(self):
        refreshed = []
        self.viewer.refreshItems = lambda *items: refreshed.extend(items)
        return refreshed

    def test_task_rename_refreshes_its_effort_rows(self):
        self.task.addEffort(self.effort1)
        refreshed = self.record_refreshes()
        self.task.setSubject("renamed")
        self.assertIn(self.effort1, refreshed)

    def test_task_category_refreshes_its_effort_rows(self):
        self.task.addEffort(self.effort1)
        refreshed = self.record_refreshes()
        self.task.addCategory(category.Category("category"))
        self.assertIn(self.effort1, refreshed)

    def test_a_pass_refreshes_its_tasks_effort_rows_once_after_it(self):
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        refreshes = []
        self.viewer.refreshItems = lambda *items: refreshes.append(set(items))
        patterns.Event("scheduler.aboutToPass", self).send()
        for event_type in task.Task.effective_style_event_types():
            patterns.Event(event_type, self.task, None).send()
        self.assertEqual([], refreshes)
        patterns.Event("scheduler.pass", self).send()
        self.assertEqual([{self.effort1, self.effort2}], refreshes)

    def test_search(self):
        self.task.addEffort(self.effort1)
        self.viewer.presentation().setSearchFilter("no such task")
        self.assertEqual(0, len(self.viewer.presentation()))
        self.viewer.presentation().setSearchFilter(self.task.subject())
        self.assertEqual(1, len(self.viewer.presentation()))

    def test_search_include_subitems(self):
        self.task.addEffort(self.effort1)
        child = task.Task("child")
        self.task.addChild(child)
        child.set_parent(self.task)
        self.taskFile.tasks().append(child)
        child.addEffort(effort.Effort(child))
        self.assertEqual(2, len(self.viewer.presentation()))
        self.viewer.presentation().setSearchFilter(self.task.subject())
        self.assertEqual(1, len(self.viewer.presentation()))
        self.viewer.presentation().setSearchFilter(
            self.task.subject(), includeSubItems=True
        )
        self.assertEqual(2, len(self.viewer.presentation()))

    def test_ascending_sort_order(self):
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.viewer.setSortOrderAscending(True)
        self.assertEqual(
            [self.effort1, self.effort2], list(self.viewer.presentation())
        )

    def test_descending_sort_order(self):
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.viewer.setSortOrderAscending(False)
        self.assertEqual(
            [self.effort2, self.effort1], list(self.viewer.presentation())
        )


class EffortViewerSelectionTest(test.wxTestCase):
    """The selected efforts stay selected while rows come, go or move;
    after a delete the selection stays on the same line, or goes up
    from the bottom (docs/LIST_MANAGEMENT.md, Which Row Gets Selected;
    P100)."""

    def setUp(self):
        super().setUp()
        self.task_file = persistence.TaskFile()
        self.task = task.Task("task")
        self.task_file.tasks().append(self.task)
        for day in (1, 2, 3, 4):
            self.add_effort(day)
        self.viewer = gui.viewer.EffortViewer(self.frame, self.task_file)
        self.rows = list(self.viewer.presentation())  # Newest first

    def tearDown(self):
        super().tearDown()
        self.task_file.close()
        self.task_file.stop()

    def add_effort(self, day):
        an_effort = effort.Effort(
            self.task,
            date.DateTime(2026, 1, day, 9, 0),
            date.DateTime(2026, 1, day, 10, 0),
        )
        self.task.addEffort(an_effort)
        return an_effort

    def delete(self, efforts):
        command.DeleteEffortCommand(self.task_file.efforts(), efforts).do()

    def test_deleting_selects_the_row_moving_into_its_place(self):
        self.viewer.select([self.rows[1]])
        self.delete([self.rows[1]])
        self.assertEqual([self.rows[2]], self.viewer.curselection())

    def test_deleting_the_last_row_selects_the_row_above(self):
        self.viewer.select([self.rows[3]])
        self.delete([self.rows[3]])
        self.assertEqual([self.rows[2]], self.viewer.curselection())

    def test_deleting_adjacent_rows_selects_the_row_below_them(self):
        self.viewer.select(self.rows[1:3])
        self.delete(self.rows[1:3])
        self.assertEqual([self.rows[3]], self.viewer.curselection())

    def test_deleting_another_row_keeps_the_selection(self):
        self.viewer.select([self.rows[2]])
        self.delete([self.rows[0]])
        self.assertEqual([self.rows[2]], self.viewer.curselection())

    def test_a_row_added_above_keeps_the_selection(self):
        self.viewer.select([self.rows[3]])
        self.add_effort(5)
        self.assertEqual([self.rows[3]], self.viewer.curselection())

    def test_sorting_keeps_the_selection(self):
        self.viewer.select([self.rows[0]])
        self.viewer.setSortOrderAscending(True)
        self.assertEqual([self.rows[0]], self.viewer.curselection())

    def test_keys_move_from_the_selected_row(self):
        self.viewer.select([self.rows[3]])
        self.add_effort(5)
        focused = self.viewer.widget.GetFocusedItem()
        self.assertEqual(
            self.rows[3], self.viewer.widget.get_item_with_index(focused)
        )


class EffortViewerForOtherTasksTest(test.wxTestCase):
    """Switched to tasks without efforts while one is selected, the view
    asks no row of the new, empty presentation (P232)."""

    class Viewer(gui.viewer.EffortViewer):  # pylint: disable=W0223
        tasks = []

        def tasksToShowEffortFor(self):
            return task.TaskList(self.tasks)

    def setUp(self):
        super().setUp()
        self.taskFile = persistence.TaskFile()
        with_effort, self.without = task.Task("one"), task.Task("two")
        self.taskFile.tasks().extend([with_effort, self.without])
        self.effort = effort.Effort(
            with_effort, date.DateTime(2026, 1, 1), date.DateTime(2026, 1, 2)
        )
        with_effort.addEffort(self.effort)
        self.Viewer.tasks = [with_effort]
        self.viewer = self.Viewer(self.frame, self.taskFile)

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def test_no_row_is_asked_of_the_new_presentation(self):
        self.viewer.select([self.effort])
        asked = []
        text = self.viewer.getItemText
        self.viewer.getItemText = lambda item, column: (
            asked.append(item) or text(item, column)
        )
        self.Viewer.tasks = [self.without]
        self.viewer._refresh(clear=True)  # pylint: disable=W0212
        self.assertNotIn(None, asked)


class MovingColumnsInListTest(test.wxTestCase):
    """The effort list's columns move as the tree's do: dragged by
    their header, a click sorting (docs/LIST_MANAGEMENT.md, Moving
    Columns)."""

    def setUp(self):
        super().setUp()
        self.task_file = persistence.TaskFile()
        a_task = task.Task("task")
        self.task_file.tasks().append(a_task)
        a_task.addEffort(
            effort.Effort(
                a_task, date.DateTime(2026, 1, 1), date.DateTime(2026, 1, 2)
            )
        )
        self.viewer = gui.viewer.EffortViewer(self.frame, self.task_file)
        self.mouse = HeaderMouse(self.viewer.widget)
        self.before = self.names()

    def tearDown(self):
        super().tearDown()
        self.task_file.close()
        self.task_file.stop()

    def names(self, viewer=None):
        viewer = viewer or self.viewer
        return [each.name() for each in viewer.visibleColumns()]

    def test_a_column_dropped_before_the_first(self):
        self.mouse.drag(1, 1)
        expected = [self.before[1], self.before[0]] + self.before[2:]
        self.assertEqual(expected, self.names())

    def test_the_fill_column_follows_the_task_column(self):
        last = len(self.before)
        self.mouse.drag(self.before.index("task"), self.mouse.left(last) - 1)
        self.assertEqual("task", self.names()[-1])
        self.assertEqual(last - 1, self.viewer.widget.ResizeColumn)

    def test_a_new_view_takes_the_saved_order(self):
        self.mouse.drag(1, 1)
        viewer = gui.viewer.EffortViewer(self.frame, self.task_file)
        self.assertEqual(self.names(), self.names(viewer))

    def test_a_click_sorts_without_moving(self):
        clicked = []
        self.viewer.widget.Bind(
            wx.EVT_LIST_COL_CLICK,
            lambda event: (clicked.append(event.GetColumn()), event.Skip()),
        )
        self.mouse.click(1)
        self.assertEqual([1], clicked)
        self.assertEqual(self.before, self.names())


class EffortViewerAggregationTestCase(test.wxTestCase):
    aggregation = "Subclass responsibility"

    def createViewer(self):
        return gui.viewer.EffortViewer(self.frame, self.taskFile)

    def setUp(self):
        super().setUp()
        settings.set("effortviewer", "aggregation", self.aggregation)

        self.taskFile = persistence.TaskFile()
        self.viewer = self.createViewer()
        self.task = task.Task("Task")
        self.task2 = task.Task("Task2")
        self.taskFile.tasks().extend([self.task, self.task2])
        self.task.addEffort(
            effort.Effort(
                self.task,
                date.DateTime(2008, 7, 16, 10, 0, 0),
                date.DateTime(2008, 7, 16, 11, 0, 0),
            )
        )
        self.task.addEffort(
            effort.Effort(
                self.task,
                date.DateTime(2008, 7, 16, 12, 0, 0),
                date.DateTime(2008, 7, 16, 13, 0, 0),
            )
        )
        self.task.addEffort(
            effort.Effort(
                self.task,
                date.DateTime(2008, 7, 17, 1, 0, 0),
                date.DateTime(2008, 7, 17, 2, 0, 0),
            )
        )
        most_recent_period = (
            date.DateTime(2008, 7, 23, 1, 0, 0),
            date.DateTime(2008, 7, 23, 2, 0, 0),
        )
        # pylint: disable=W0142
        self.task.addEffort(effort.Effort(self.task, *most_recent_period))
        self.task2.addEffort(effort.Effort(self.task2, *most_recent_period))

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def switchAggregation(self):
        aggregations = ["details", "day", "week", "month"]
        aggregations.remove(self.aggregation)
        self.viewer.set_aggregation(aggregations[0])


class EffortViewerAggregationRoundingTestCase(test.wxTestCase):
    aggregation = "Subclass responsibility"
    roundingValue = None
    alwaysRoundUp = None
    consolidateEffortsPerTask = None

    def createViewer(self):
        return gui.viewer.EffortViewer(self.frame, self.taskFile)

    def setUp(self):
        super().setUp()
        settings.set("effortviewer", "aggregation", self.aggregation)
        settings.set("effortviewer", "round", self.roundingValue)
        settings.set("effortviewer", "alwaysroundup", self.alwaysRoundUp)
        settings.set(
            "effortviewer",
            "consolidateeffortspertask",
            self.consolidateEffortsPerTask,
        )

        self.taskFile = persistence.TaskFile()
        self.viewer = self.createViewer()
        self.viewer.showColumnByName("totalTimeSpent", True)
        self.task = task.Task("Task")
        self.taskFile.tasks().extend([self.task])
        self.task.addEffort(
            effort.Effort(
                self.task,  # 45 seconds
                date.DateTime(2013, 7, 6, 1, 0, 0),
                date.DateTime(2013, 7, 6, 1, 0, 45),
            )
        )
        self.task.addEffort(
            effort.Effort(
                self.task,  # 45 seconds
                date.DateTime(2013, 7, 6, 2, 0, 0),
                date.DateTime(2013, 7, 6, 2, 0, 45),
            )
        )
        self.task.addEffort(
            effort.Effort(
                self.task,  # 45 seconds
                date.DateTime(2013, 7, 6, 3, 0, 0),
                date.DateTime(2013, 7, 6, 3, 0, 45),
            )
        )
        self.task.addEffort(
            effort.Effort(
                self.task,  # 10 seconds
                date.DateTime(2013, 7, 6, 4, 0, 0),
                date.DateTime(2013, 7, 6, 4, 0, 10),
            )
        )


class RoundingTestsMixin(object):
    def test_render_duration(self):
        self.assertEqual(
            self.expectedPeriodRendering,
            self.viewer.widget.getItemText(
                self.viewer.widget.get_item_with_index(0), 3
            ),
        )
        if self.aggregation != "details":
            self.assertEqual(
                self.expectedTotalPeriodRendering,
                self.viewer.widget.getItemText(
                    self.viewer.widget.get_item_with_index(0), 4
                ),
            )


class EffortViewerAggregationRoundingDayTest(
    EffortViewerAggregationRoundingTestCase, RoundingTestsMixin
):
    aggregation = "day"
    roundingValue = 60
    alwaysRoundUp = False
    consolidateEffortsPerTask = False
    expectedPeriodRendering = "0:03"
    expectedTotalPeriodRendering = "0:03"


class EffortViewerAggregationRoundingDayUpTest(
    EffortViewerAggregationRoundingTestCase, RoundingTestsMixin
):
    aggregation = "day"
    roundingValue = 60
    alwaysRoundUp = True
    consolidateEffortsPerTask = False
    expectedPeriodRendering = "0:04"
    expectedTotalPeriodRendering = "0:04"


class EffortViewerAggregationRoundingWeekTest(
    EffortViewerAggregationRoundingTestCase, RoundingTestsMixin
):
    aggregation = "week"
    roundingValue = 60
    alwaysRoundUp = False
    consolidateEffortsPerTask = False
    expectedPeriodRendering = "0:03"
    expectedTotalPeriodRendering = "0:03"


class EffortViewerAggregationRoundingWeekUpTest(
    EffortViewerAggregationRoundingTestCase, RoundingTestsMixin
):
    aggregation = "week"
    roundingValue = 60
    alwaysRoundUp = True
    consolidateEffortsPerTask = False
    expectedPeriodRendering = "0:04"
    expectedTotalPeriodRendering = "0:04"


class EffortViewerAggregationRoundingMonthTest(
    EffortViewerAggregationRoundingTestCase, RoundingTestsMixin
):
    aggregation = "month"
    roundingValue = 60
    alwaysRoundUp = False
    consolidateEffortsPerTask = False
    expectedPeriodRendering = "0:03"
    expectedTotalPeriodRendering = "0:03"


class EffortViewerAggregationRoundingMonthUpTest(
    EffortViewerAggregationRoundingTestCase, RoundingTestsMixin
):
    aggregation = "month"
    roundingValue = 60
    alwaysRoundUp = True
    consolidateEffortsPerTask = False
    expectedPeriodRendering = "0:04"
    expectedTotalPeriodRendering = "0:04"


class EffortViewerAggregationNoRoundingTest(
    EffortViewerAggregationRoundingTestCase, RoundingTestsMixin
):
    aggregation = "details"
    roundingValue = 60
    alwaysRoundUp = False
    consolidateEffortsPerTask = False
    expectedPeriodRendering = "0:00:10"
    expectedTotalPeriodRendering = "0:02:25"


class EffortViewerAggregationNoRoundingUpTest(
    EffortViewerAggregationRoundingTestCase, RoundingTestsMixin
):
    aggregation = "details"
    roundingValue = 60
    alwaysRoundUp = True
    consolidateEffortsPerTask = False
    expectedPeriodRendering = "0:00:10"
    expectedTotalPeriodRendering = "0:02:25"


class EffortViewerAggregationRoundingDayConsolidationTest(
    EffortViewerAggregationRoundingTestCase, RoundingTestsMixin
):
    aggregation = "day"
    roundingValue = 60
    alwaysRoundUp = False
    consolidateEffortsPerTask = True
    expectedPeriodRendering = "0:03"
    expectedTotalPeriodRendering = "0:02"


class EffortViewerAggregationRoundingDayUpConsolidationTest(
    EffortViewerAggregationRoundingTestCase, RoundingTestsMixin
):
    aggregation = "day"
    roundingValue = 60
    alwaysRoundUp = True
    consolidateEffortsPerTask = True
    expectedPeriodRendering = "0:04"
    expectedTotalPeriodRendering = "0:03"


class EffortViewerAggregationRoundingWeekConsolidationTest(
    EffortViewerAggregationRoundingTestCase, RoundingTestsMixin
):
    aggregation = "week"
    roundingValue = 60
    alwaysRoundUp = False
    consolidateEffortsPerTask = True
    expectedPeriodRendering = "0:03"
    expectedTotalPeriodRendering = "0:02"


class EffortViewerAggregationRoundingWeekUpConsolidationTest(
    EffortViewerAggregationRoundingTestCase, RoundingTestsMixin
):
    aggregation = "week"
    roundingValue = 60
    alwaysRoundUp = True
    consolidateEffortsPerTask = True
    expectedPeriodRendering = "0:04"
    expectedTotalPeriodRendering = "0:03"


class EffortViewerAggregationRoundingMonthConsolidationTest(
    EffortViewerAggregationRoundingTestCase, RoundingTestsMixin
):
    aggregation = "month"
    roundingValue = 60
    alwaysRoundUp = False
    consolidateEffortsPerTask = True
    expectedPeriodRendering = "0:03"
    expectedTotalPeriodRendering = "0:02"


class EffortViewerAggregationRoundingMonthUpConsolidationTest(
    EffortViewerAggregationRoundingTestCase, RoundingTestsMixin
):
    aggregation = "month"
    roundingValue = 60
    alwaysRoundUp = True
    consolidateEffortsPerTask = True
    expectedPeriodRendering = "0:04"
    expectedTotalPeriodRendering = "0:03"


class CommonTestsMixin(object):
    def test_stop_change_refreshes_its_row(self):
        changed = self.task.efforts()[0]
        rows = [
            each
            for each in self.viewer.presentation()
            if each is changed
            or changed in getattr(each, "_getEfforts", list)()
        ]
        refreshed = []
        self.viewer.refreshItems = lambda *items: refreshed.extend(items)
        changed.setStop(changed.getStop() + date.ONE_HOUR)
        self.assertTrue([each for each in rows if each in refreshed])

    def test_number_of_items(self):
        self.assertEqual(self.expectedNumberOfItems, self.viewer.size())

    def test_render_period(self):
        self.assertEqual(
            self.expectedPeriodRendering, self.viewer.widget.GetItemText(0)
        )

    def test_render_repeated_period(self):
        self.assertEqual("", self.viewer.widget.GetItemText(1))

    def test_switch_aggregation(self):
        self.switchAggregation()
        self.viewer.set_aggregation(self.aggregation)
        self.assertEqual(self.expectedNumberOfItems, self.viewer.size())

    def test_aggregation_is_saved_in_settings(self):
        self.assertEqual(
            self.aggregation,
            settings.get(self.viewer.settingsSection(), "aggregation"),
        )

    def test_toolbar_choice_ctrl_shows_aggegration_mode(self):
        aggregation_ui_command = self.viewer.aggregationUICommand
        index = aggregation_ui_command.choiceData.index(self.aggregation)
        expected_label = aggregation_ui_command.choiceLabels[index]
        actual_label = aggregation_ui_command.choiceCtrl.GetStringSelection()
        self.assertEqual(expected_label, actual_label)

    def test_search(self):
        self.viewer.setSearchFilter("Task2")
        self.assertEqual(1, self.viewer.size())

    def test_search_description(self):
        self.task.efforts()[0].setDescription("Description")
        self.viewer.setSearchFilter("Description", searchDescription=True)
        self.assertEqual(1, self.viewer.size())

    def test_search_with_include_subitems(self):
        self.viewer.setSearchFilter("Task2", includeSubItems=True)
        self.assertEqual(1, self.viewer.size())

    def test_delete(self):
        self.viewer.widget.Select(0)
        self.viewer.updateSelection()
        self.viewer.deleteUICommand.do_command(None)
        expected_number_of_items = self.expectedNumberOfItems - (
            1 if self.aggregation == "details" else 3
        )
        self.assertEqual(expected_number_of_items, self.viewer.size())

    def test_delete_task(self):
        self.taskFile.tasks().remove(self.task2)
        expected_number_of_items = self.expectedNumberOfItems - 1
        self.assertEqual(expected_number_of_items, self.viewer.size())

    def test_new_effort_uses_same_task_as_selected_effort(self):
        dialog = self.viewer.newItemDialog(
            selectedTasks=[self.task2], bitmap="nuvola_actions_document-new"
        )
        for new_effort in dialog._items:  # pylint: disable=W0212
            self.assertEqual(self.task2, new_effort.task())

    def test_column_ui_commands(self):
        expected_length = dict(details=7, day=9, week=10, month=9)[
            self.aggregation
        ]
        self.assertEqual(
            expected_length, len(self.viewer.getColumnUICommands())
        )

    def test_total_time_spent_column_not_in_details_mode(self):
        columns = [
            getattr(command, "setting", None)
            for command in self.viewer.getColumnUICommands()
        ]
        self.assertEqual(
            self.aggregation != "details", "totalTimeSpent" in columns
        )

    def test_total_revenue_column_not_in_details_mode(self):
        columns = [
            getattr(command, "setting", None)
            for command in self.viewer.getColumnUICommands()
        ]
        self.assertEqual(
            self.aggregation != "details", "totalRevenue" in columns
        )

    def test_default_nr_of_columns(self):
        self.assertEqual(4, self.viewer.widget.GetColumnCount())

    def test_hide_time_spent_column(self):
        self.viewer.showColumnByName("timeSpent", False)
        self.assertEqual(3, self.viewer.widget.GetColumnCount())

    def test_hide_revenue_column(self):
        self.viewer.showColumnByName("revenue", False)
        self.assertEqual(4, self.viewer.widget.GetColumnCount())

    def test_show_total_time_spent_column(self):
        self.viewer.showColumnByName("totalTimeSpent", True)
        self.assertEqual(5, self.viewer.widget.GetColumnCount())

    def test_show_total_revenue_column(self):
        self.viewer.showColumnByName("totalRevenue", True)
        self.assertEqual(5, self.viewer.widget.GetColumnCount())

    def test_total_time_spent_column_is_hidden_when_switching_to_details(self):
        self.viewer.showColumnByName("totalTimeSpent", True)
        self.switchAggregation()
        self.assertEqual(
            self.viewer.is_showing_aggregated_effort(),
            self.viewer.isVisibleColumnByName("totalTimeSpent"),
        )

    def test_total_revenue_column_is_hidden_when_switching_to_details(self):
        self.viewer.showColumnByName("totalRevenue", True)
        self.switchAggregation()
        self.assertEqual(
            self.viewer.is_showing_aggregated_effort(),
            self.viewer.isVisibleColumnByName("totalRevenue"),
        )

    def test_active_effort(self):
        self.task2.efforts()[0].setStop(date.DateTime.max)  # Make active
        self.viewer.second_refresher.on_every_second()  # Simulate clock firing
        expected_nr_of_tracked_items = (
            1 if self.aggregation == "details" else 2
        )
        self.assertEqual(
            expected_nr_of_tracked_items,
            len(self.viewer.second_refresher.currently_tracked_items()),
        )

    def test_active_effort_after_switch(self):
        self.task2.efforts()[0].setStop(date.DateTime.max)  # Make active
        self.switchAggregation()
        self.viewer.second_refresher.on_every_second()  # Simulate clock firing
        expected_nr_of_tracked_items = (
            2 if self.aggregation == "details" else 1
        )
        self.assertEqual(
            expected_nr_of_tracked_items,
            len(self.viewer.second_refresher.currently_tracked_items()),
        )

    def test_is_showing_aggregated_effort(self):
        is_aggregating = self.aggregation != "details"
        self.assertEqual(
            is_aggregating, self.viewer.is_showing_aggregated_effort()
        )

    def test_stop_effort_tracking(self):
        self.task.addEffort(effort.Effort(self.task))
        stop_ui_command = gui.uicommand.EffortStop(
            viewer=self.viewer,
            effortList=self.taskFile.efforts(),
            taskList=self.taskFile.tasks(),
        )
        stop_ui_command.do_command()
        self.assertFalse(self.task.isBeingTracked())


class EffortViewerWithoutAggregationTest(
    CommonTestsMixin, EffortViewerAggregationTestCase
):
    aggregation = "details"
    expectedNumberOfItems = 5
    expectedPeriodRendering = render.dateTimePeriod(
        date.DateTime(2008, 7, 23, 1, 0), date.DateTime(2008, 7, 23, 2, 0)
    )


class EffortViewerWithAggregationPerDayTest(
    CommonTestsMixin, EffortViewerAggregationTestCase
):
    aggregation = "day"
    expectedNumberOfItems = (
        7  # 4 day/task combinations on 3 days (== 3 total rows)
    )
    expectedPeriodRendering = render.date(date.DateTime(2008, 7, 23))


class EffortViewerWithAggregationPerWeekTest(
    CommonTestsMixin, EffortViewerAggregationTestCase
):
    aggregation = "week"
    expectedNumberOfItems = (
        5  # 3 week/task combinations in 2 weeks (== 2 total rows)
    )
    expectedPeriodRendering = "2008-30"


class EffortViewerWithAggregationPerMonthTest(
    CommonTestsMixin, EffortViewerAggregationTestCase
):
    aggregation = "month"
    expectedNumberOfItems = (
        3  # 2 month/task combinations in 1 month (== 1 total row)
    )
    expectedPeriodRendering = render.month(date.DateTime(2008, 0o7, 0o1))


class EffortViewerRenderTestMixin(object):
    aggregation = "Subclass responsibility"

    def createViewer(self):
        return gui.viewer.EffortViewer(self.frame, self.taskFile)

    def setUp(self):
        super().setUp()
        settings.set("effortviewer", "aggregation", self.aggregation)

        self.taskFile = persistence.TaskFile()
        self.task = task.Task("task")
        self.taskFile.tasks().append(self.task)
        self.midnight = date.Now().startOfDay()
        self.viewer = self.createViewer()

    def test_today(self):
        the_effort = effort.Effort(
            self.task, self.midnight, self.midnight + date.TWO_HOURS
        )
        self.task.addEffort(the_effort)
        text = self.viewer.widget.GetItemText(0)
        self.assertTrue(text.startswith("Today"), '"Today" not in %s' % text)

    def test_tomorrow(self):
        the_effort = effort.Effort(
            self.task,
            self.midnight + date.ONE_DAY,
            self.midnight + date.TimeDelta(hours=2, days=1),
        )
        self.task.addEffort(the_effort)
        text = self.viewer.widget.GetItemText(0)
        self.assertTrue(
            text.startswith("Tomorrow"), '"Tomorrow" not in %s' % text
        )

    def test_yesterday(self):
        the_effort = effort.Effort(
            self.task,
            self.midnight - date.TimeDelta(days=1),
            self.midnight - date.TimeDelta(hours=22),
        )
        self.task.addEffort(the_effort)
        text = self.viewer.widget.GetItemText(0)
        self.assertTrue(
            text.startswith("Yesterday"), '"Yesterday" not in %s' % text
        )


class EffortViewerRenderDetailsTest(
    EffortViewerRenderTestMixin, test.wxTestCase
):
    aggregation = "details"


class EffortViewerRenderPerDayTest(
    EffortViewerRenderTestMixin, test.wxTestCase
):
    aggregation = "day"
