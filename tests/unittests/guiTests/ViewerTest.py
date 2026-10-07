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

import test
import wx
from unittests.headermouse import HeaderMouse
from taskcoachlib import gui, config, widgets, patterns, persistence
from taskcoachlib.config import settings
from taskcoachlib.domain import task, date
from wx.lib.agw import hypertreelist


class AuiManagedFrameWithDynamicCenterPane(
    widgets.AuiManagedFrameWithDynamicCenterPane
):
    def AddBalloonTip(self, *args, **kwargs):
        pass


class Window(AuiManagedFrameWithDynamicCenterPane):
    def add_pane(self, viewer, title, name="name", floating=False):
        super().add_pane(viewer, title, name, floating)


class ViewerTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.taskFile = persistence.TaskFile()
        self.task = task.Task("task")
        self.taskFile.tasks().append(self.task)
        self.window = Window(self.frame)
        self.viewerContainer = gui.viewer.ViewerContainer(self.window)
        self.viewer = self.createViewer()
        self.viewerContainer.add_viewer(self.viewer)

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def createViewer(self):
        return gui.viewer.TaskViewer(self.window, self.taskFile)

    def test_decimal_time_change_redraws(self):
        redraws = []
        self.viewer.refresh = lambda: redraws.append(True)
        settings.view.statusbar = False  # Another setting changed
        settings.feature.decimal_time = True
        self.assertEqual([True], redraws)

    def record_row_refreshes(self):
        refreshed = []
        self.viewer.widget.RefreshItems = lambda *items: refreshed.append(
            set(items)
        )
        return refreshed

    def send_style_changes(self):
        for event_type in task.Task.effective_style_event_types():
            patterns.Event(event_type, self.task, None).send()

    def test_a_change_refreshes_its_row_at_once(self):
        refreshed = self.record_row_refreshes()
        self.send_style_changes()
        self.assertEqual(4, len(refreshed))

    def test_a_scheduler_pass_refreshes_its_rows_once_after_it(self):
        # A pass can change every row (a file merged, the theme changed)
        refreshed = self.record_row_refreshes()
        patterns.Event("scheduler.aboutToPass", self).send()
        self.send_style_changes()
        self.assertEqual([], refreshed)
        patterns.Event("scheduler.pass", self).send()
        self.assertEqual([{self.task}], refreshed)

    def test_rows_changed_while_a_file_is_read_are_not_redrawn_again(self):
        # The first pass runs as the file is read: the redraw after the
        # read draws its rows, the next pass does not again
        refreshed = self.record_row_refreshes()
        patterns.Event("taskfile.aboutToRead", self.taskFile).send()
        self.send_style_changes()
        patterns.Event("taskfile.justRead", self.taskFile).send()
        patterns.Event("scheduler.aboutToPass", self).send()
        patterns.Event("scheduler.pass", self).send()
        self.assertEqual([], refreshed)

    def test_a_bulk_change_refreshes_its_rows_once_after_it(self):
        refreshed = self.record_row_refreshes()
        patterns.Event("command.aboutToBulkModify", self).send()
        self.send_style_changes()
        self.assertEqual([], refreshed)
        patterns.Event("command.justBulkModified", self).send()
        self.assertEqual([{self.task}], refreshed)

    def test_select_all_via_widget(self):
        self.viewer.widget.select_all()
        self.viewer.updateSelection()
        self.assertEqual([self.task], self.viewer.curselection())

    def test_select_all_via_widget_with_multiple_items(self):
        self.taskFile.tasks().append(task.Task("second"))
        self.viewer.widget.select_all()
        self.viewer.updateSelection()
        self.assertEqual(2, len(self.viewer.curselection()))

    def test_select_all(self):
        self.viewer.select_all()
        self.viewer.end_of_select_all()
        self.assertEqual([self.task], self.viewer.curselection())

    def test_select_all_with_multiple_items(self):
        self.taskFile.tasks().append(task.Task("second"))
        self.viewer.select_all()
        self.viewer.end_of_select_all()
        self.assertEqual(2, len(self.viewer.curselection()))

    def test_select_next_item_after_deleting_selection(self):
        second_task = task.Task("second")
        self.taskFile.tasks().append(second_task)
        self.viewer.select([self.task])
        self.taskFile.tasks().remove(self.task)
        self.assertEqual([second_task], self.viewer.curselection())

    def test_deleting_an_only_child_selects_the_next_row(self):
        # Rows: task, child, second; the old rule took the parent
        second_task = task.Task("second")
        self.taskFile.tasks().append(second_task)
        child = task.Task("child")
        self.task.addChild(child)
        child.set_parent(self.task)
        self.taskFile.tasks().append(child)
        self.viewer.select([child])
        self.taskFile.tasks().remove(child)
        self.assertEqual([second_task], self.viewer.curselection())

    def add_tasks(self, *subjects, parent=None):
        added = [task.Task(subject) for subject in subjects]
        for each in added:
            if parent:
                parent.addChild(each)
                each.set_parent(parent)
        self.taskFile.tasks().extend(added)
        return added

    def delete_selected(self, item):
        """Select an item and delete it; return the new selection."""
        self.viewer.select([item])
        self.taskFile.tasks().remove(item)
        return self.viewer.curselection()

    def test_deleting_selects_the_row_moving_into_its_place(self):
        # Rows: a, b, c, task (docs/LIST_MANAGEMENT.md, Which Row Gets
        # Selected)
        a, b, c = self.add_tasks("a", "b", "c")
        self.assertEqual([c], self.delete_selected(b))

    def test_deleting_the_last_child_selects_the_next_row(self):
        # Rows: a parent, b1, b2, c next, task
        parent, next_task = self.add_tasks("a parent", "c next")
        first, last = self.add_tasks("b1", "b2", parent=parent)
        self.assertEqual([next_task], self.delete_selected(last))

    def test_deleting_a_parent_selects_the_row_after_its_children(self):
        parent, next_task = self.add_tasks("a parent", "c next")
        self.add_tasks("b1", "b2", parent=parent)
        self.assertEqual([next_task], self.delete_selected(parent))

    def test_dont_change_selection_after_deleting_an_item_that_is_not_selected(
        self,
    ):
        second_task = task.Task("second")
        self.taskFile.tasks().append(second_task)
        child = task.Task("child")
        self.task.addChild(child)
        child.set_parent(self.task)
        self.taskFile.tasks().append(child)
        self.viewer.select([second_task])
        self.taskFile.tasks().remove(child)
        self.assertEqual([second_task], self.viewer.curselection())

    def test_first_viewer_instance_settings_section(self):
        self.assertEqual(
            self.viewer.__class__.__name__.lower(),
            self.viewer.settingsSection(),
        )

    def test_second_viewer_instance_has_another_settings_section(self):
        viewer2 = self.createViewer()
        self.assertEqual(
            self.viewer.settingsSection() + "1", viewer2.settingsSection()
        )

    def test_title(self):
        self.assertEqual(self.viewer.defaultTitle, self.viewer.title())

    def test_set_title(self):
        self.viewer.set_title("New title")
        self.assertEqual("New title", self.viewer.title())

    def test_set_title_saves_title_in_settings(self):
        self.viewer.set_title("New title")
        self.assertEqual(
            "New title",
            settings.get(self.viewer.settingsSection(), "title"),
        )

    def test_set_title_does_not_save_default_title(
        self,
    ):
        self.viewer.set_title(self.viewer.defaultTitle)
        self.assertEqual(
            "", settings.get(self.viewer.settingsSection(), "title")
        )

    def test_set_title_changes_tab_title(self):
        self.viewer.set_title("New title")
        self.assertEqual(
            "New title", self.window.manager.GetPane(self.viewer).caption
        )

    def test_get_item_tooltip_data(self):
        self.task.setDescription("Description")
        test.styled(self.task)
        expected_data = [
            ("taskcoach_actions_led_grey_icon", ["task"]),
            ("nuvola_places_folder-downloads", []),
            ("nuvola_status_mail-attachment", []),
            (None, ["Description"]),
        ]
        self.assertEqual(
            expected_data, self.viewer.getItemTooltipData(self.task)
        )


class MovingColumnsInTreeTest(test.wxTestCase):
    """A column moves where its header is dragged and dropped, and stays
    there; a click on a header sorts (docs/LIST_MANAGEMENT.md, Moving
    Columns; GitHub #311). Shown: subject, planned start, due date."""

    def setUp(self):
        super().setUp()
        self.task_file = persistence.TaskFile()
        self.task_file.tasks().append(task.Task("task"))
        self.window = Window(self.frame)
        self.viewer = gui.viewer.TaskViewer(self.window, self.task_file)
        self.mouse = HeaderMouse(self.viewer.widget)
        self.clicked = []
        self.viewer.widget.Bind(wx.EVT_LIST_COL_CLICK, self.on_click)

    def tearDown(self):
        super().tearDown()
        self.task_file.close()
        self.task_file.stop()

    def on_click(self, event):
        self.clicked.append(event.GetColumn())
        event.Skip()

    def names(self, viewer=None):
        return [
            each.name() for each in (viewer or self.viewer).visibleColumns()
        ]

    def test_a_column_dropped_before_the_first(self):
        self.mouse.drag(2, 1)
        self.assertEqual(
            ["dueDateTime", "subject", "plannedStartDateTime"], self.names()
        )

    def test_a_column_dropped_after_the_last(self):
        self.mouse.drag(0, self.mouse.left(3) - 1)
        self.assertEqual(
            ["plannedStartDateTime", "dueDateTime", "subject"], self.names()
        )

    def test_a_column_dropped_between_two(self):
        self.mouse.drag(2, self.mouse.left(1) + 1)
        self.assertEqual(
            ["subject", "dueDateTime", "plannedStartDateTime"], self.names()
        )

    def test_a_new_view_takes_the_saved_order(self):
        self.mouse.drag(2, 1)
        viewer = gui.viewer.TaskViewer(self.window, self.task_file)
        self.assertEqual(
            ["dueDateTime", "subject", "plannedStartDateTime"],
            self.names(viewer),
        )

    def test_the_tree_follows_the_subject(self):
        self.mouse.drag(0, self.mouse.left(3) - 1)
        main_window = self.viewer.widget.GetMainWindow()
        self.assertEqual(2, main_window.GetMainColumn())
        self.assertEqual(2, self.viewer.widget.ResizeColumn)

    def test_a_column_shown_again_takes_its_place(self):
        self.mouse.drag(2, 1)
        self.viewer.showColumnByName("dueDateTime", False)
        self.viewer.showColumnByName("dueDateTime", True)
        self.assertEqual(
            ["dueDateTime", "subject", "plannedStartDateTime"], self.names()
        )

    def test_a_click_sorts_at_the_release(self):
        self.mouse.send(wx.wxEVT_LEFT_DOWN, self.mouse.middle(1))
        self.assertEqual([], self.clicked)
        self.mouse.send(wx.wxEVT_LEFT_UP, self.mouse.middle(1))
        self.assertEqual([1], self.clicked)
        self.assertEqual(
            ["subject", "plannedStartDateTime", "dueDateTime"], self.names()
        )

    def test_a_drag_does_not_sort(self):
        self.mouse.drag(2, 1)
        self.assertEqual([], self.clicked)


class SortableViewerTest(test.TestCase):
    def setUp(self):
        self.viewer = self.createViewer()

    def createViewer(self):
        viewer = gui.viewer.mixin.SortableViewerMixin()
        viewer.options = config.settings.section("taskviewer")
        viewer.settingsSection = lambda: "taskviewer"
        viewer.SorterClass = task.sorter.Sorter
        presentation = viewer.create_sorter(task.TaskList())
        viewer.presentation = lambda: presentation
        return viewer

    def test_is_sortable(self):
        self.assertTrue(self.viewer.isSortable())

    def test_sort_by(self):
        self.viewer.sortBy("subject")
        self.assertEqual(
            "subject",
            settings.get(self.viewer.settingsSection(), "sortby")[0],
        )

    def test_sort_by_twice_flips_sort_order(self):
        self.viewer.sortBy("subject")
        self.viewer.setSortOrderAscending(True)
        self.viewer.sortBy("subject")
        self.assertFalse(self.viewer.isSortOrderAscending())

    def test_is_sorted_by(self):
        self.viewer.sortBy("description")
        self.assertTrue(self.viewer.isSortedBy("description"))

    def test_sort_order_ascending(self):
        self.viewer.setSortOrderAscending(True)
        self.assertTrue(self.viewer.isSortOrderAscending())

    def test_sort_order_descending(self):
        self.viewer.setSortOrderAscending(False)
        self.assertFalse(self.viewer.isSortOrderAscending())

    def test_set_sort_case_sensitive(self):
        self.viewer.setSortCaseSensitive(True)
        self.assertTrue(self.viewer.isSortCaseSensitive())

    def test_set_sort_case_insensitive(self):
        self.viewer.setSortCaseSensitive(False)
        self.assertFalse(self.viewer.isSortCaseSensitive())

    def test_apply_settings_when_creating_viewer(self):
        settings.set(self.viewer.settingsSection(), "sortby", ["description"])
        another_viewer = self.createViewer()
        another_viewer.presentation().extend(
            [task.Task(description="B"), task.Task(description="A")]
        )
        self.assertEqual(
            ["A", "B"],
            [t.description() for t in another_viewer.presentation()],
        )


class SortableViewerForTasksTest(test.TestCase):
    def setUp(self):

        class ViewerUnderTest(gui.viewer.mixin.SortableViewerForTasksMixin):
            pass

        self.viewer = ViewerUnderTest()
        self.viewer.options = config.settings.section("taskviewer")
        self.viewer.settingsSection = lambda: "taskviewer"
        self.viewer.presentation = lambda: task.sorter.Sorter(task.TaskList())

    def test_set_sort_by_task_status_first(self):
        self.viewer.setSortByTaskStatusFirst(True)
        self.assertTrue(self.viewer.isSortByTaskStatusFirst())

    def test_set_no_sort_by_task_status_first(self):
        self.viewer.setSortByTaskStatusFirst(False)
        self.assertFalse(self.viewer.isSortByTaskStatusFirst())


class DummyViewer(object):
    def is_tree_viewer(self):
        return False

    def createFilter(self, presentation):
        return presentation


class SearchableViewerUnderTest(
    gui.viewer.mixin.SearchableViewerMixin, DummyViewer
):
    pass


class SearchableViewerTest(test.TestCase):
    def setUp(self):
        self.viewer = self.createViewer()

    def createViewer(self):
        viewer = SearchableViewerUnderTest()
        # pylint: disable=W0201
        viewer.options = config.settings.section("taskviewer")
        viewer.settingsSection = lambda: "taskviewer"
        presentation = viewer.createFilter(task.TaskList())
        viewer.presentation = lambda: presentation
        return viewer

    def test_is_searchable(self):
        self.assertTrue(self.viewer.isSearchable())

    def test_default_search_filter(self):
        self.assertEqual(
            ("", False, False, False, False), self.viewer.getSearchFilter()
        )

    def test_set_search_filter_string(self):
        self.viewer.setSearchFilter("bla", matchCase=True)
        self.assertEqual(
            "bla",
            settings.get(self.viewer.settingsSection(), "searchfilterstring"),
        )

    def test_set_search_filter_string_affects_presentation(self):
        self.viewer.presentation().append(task.Task())
        self.viewer.setSearchFilter("bla")
        self.assertFalse(self.viewer.presentation())

    def test_search_match_case(self):
        self.viewer.setSearchFilter("bla", matchCase=True)
        self.assertEqual(
            True,
            settings.get(
                self.viewer.settingsSection(), "searchfiltermatchcase"
            ),
        )

    def test_search_match_case_affects_presenation(self):
        self.viewer.presentation().append(task.Task("BLA"))
        self.viewer.setSearchFilter("bla", matchCase=True)
        self.assertFalse(self.viewer.presentation())

    def test_search_includes_sub_items(self):
        self.viewer.setSearchFilter("bla", includeSubItems=True)
        self.assertEqual(
            True,
            settings.get(
                self.viewer.settingsSection(), "searchfilterincludesubitems"
            ),
        )

    def test_search_includes_sub_items_affects_presentation(self):
        parent = task.Task("parent")
        child = task.Task("child")
        parent.addChild(child)
        self.viewer.presentation().append(parent)
        self.viewer.setSearchFilter("parent", includeSubItems=True)
        self.assertEqual(2, len(self.viewer.presentation()))

    def test_search_description(self):
        self.viewer.setSearchFilter("bla", searchDescription=True)
        self.assertEqual(
            True,
            settings.get(self.viewer.settingsSection(), "searchdescription"),
        )

    def test_search_description_affects_presentation(self):
        self.viewer.presentation().append(
            task.Task("subject", description="description")
        )
        self.viewer.setSearchFilter("descr", searchDescription=True)
        self.assertEqual(1, len(self.viewer.presentation()))

    def test_apply_settings_when_creating_viewer(self):
        settings.set(
            self.viewer.settingsSection(), "searchfilterstring", "whatever"
        )
        another_viewer = self.createViewer()
        another_viewer.presentation().append(task.Task())
        self.assertFalse(another_viewer.presentation())


class FilterableViewerTest(test.TestCase):
    def setUp(self):
        self.viewer = gui.viewer.mixin.FilterableViewerMixin()

    def test_is_filterable(self):
        self.assertTrue(self.viewer.is_filterable())


class FilterableViewerForTasksUnderTest(
    gui.viewer.mixin.FilterableViewerForTasksMixin, DummyViewer
):
    pass


class FilterableViewerForTasks(test.TestCase):
    def setUp(self):
        self.viewer = self.createViewer()

    def tearDown(self):
        super().tearDown()
        self.viewer.taskFile.close()
        self.viewer.taskFile.stop()

    def createViewer(self):
        viewer = FilterableViewerForTasksUnderTest()
        # pylint: disable=W0201
        viewer.taskFile = persistence.TaskFile()
        viewer.options = config.settings.section("taskviewer")
        viewer.settingsSection = lambda: "taskviewer"
        presentation = viewer.createFilter(viewer.taskFile.tasks())
        viewer.presentation = lambda: presentation
        return viewer

    def test_is_not_hiding_inactive_tasks_by_default(self):
        self.assertFalse(
            self.viewer.is_hiding_task_status(task.status.inactive)
        )

    def test_hide_inactive_tasks(self):
        self.viewer.hide_task_status(task.status.inactive)
        self.assertTrue(
            self.viewer.is_hiding_task_status(task.status.inactive)
        )

    def test_hide_inactive_tasks_sets_setting(self):
        self.viewer.hide_task_status(task.status.inactive)
        self.assertTrue(
            settings.get(self.viewer.settingsSection(), "hideinactivetasks")
        )

    def test_hide_inactive_tasks_affects_presentation(self):
        self.viewer.presentation().append(
            task.Task(plannedStartDateTime=date.Tomorrow())
        )
        self.viewer.hide_task_status(task.status.inactive)
        self.assertFalse(self.viewer.presentation())

    def test_unhide_inactive_tasks(self):
        self.viewer.presentation().append(
            task.Task(plannedStartDateTime=date.Tomorrow())
        )
        self.viewer.hide_task_status(task.status.inactive)
        self.viewer.hide_task_status(task.status.inactive, False)
        self.assertTrue(self.viewer.presentation())

    def test_is_not_hiding_late_tasks_by_default(self):
        self.assertFalse(self.viewer.is_hiding_task_status(task.status.late))

    def test_hide_late_tasks(self):
        self.viewer.hide_task_status(task.status.late)
        self.assertTrue(self.viewer.is_hiding_task_status(task.status.late))

    def test_hide_late_tasks_sets_setting(self):
        self.viewer.hide_task_status(task.status.late)
        self.assertTrue(
            settings.get(self.viewer.settingsSection(), "hidelatetasks")
        )

    def test_hide_late_tasks_affects_presentation(self):
        self.viewer.presentation().append(
            task.Task(plannedStartDateTime=date.Yesterday())
        )
        self.viewer.hide_task_status(task.status.late)
        self.assertFalse(self.viewer.presentation())

    def test_unhide_late_tasks(self):
        self.viewer.presentation().append(
            task.Task(plannedStartDateTime=date.Yesterday())
        )
        self.viewer.hide_task_status(task.status.late)
        self.viewer.hide_task_status(task.status.late, False)
        self.assertTrue(self.viewer.presentation())

    def test_is_not_hiding_due_soon_tasks_by_default(self):
        self.assertFalse(
            self.viewer.is_hiding_task_status(task.status.duesoon)
        )

    def test_hide_due_soon_tasks(self):
        self.viewer.hide_task_status(task.status.duesoon)
        self.assertTrue(self.viewer.is_hiding_task_status(task.status.duesoon))

    def test_hide_due_soon_tasks_sets_setting(self):
        self.viewer.hide_task_status(task.status.duesoon)
        self.assertTrue(
            settings.get(self.viewer.settingsSection(), "hideduesoontasks")
        )

    def test_hide_due_soon_tasks_affects_presentation(self):
        self.viewer.presentation().append(
            task.Task(dueDateTime=date.Now() + date.ONE_HOUR)
        )
        self.viewer.hide_task_status(task.status.duesoon)
        self.assertFalse(self.viewer.presentation())

    def test_unhide_due_soon_tasks(self):
        self.viewer.presentation().append(
            task.Task(dueDateTime=date.Now() + date.ONE_HOUR)
        )
        self.viewer.hide_task_status(task.status.duesoon)
        self.viewer.hide_task_status(task.status.duesoon, False)
        self.assertTrue(self.viewer.presentation())

    def test_is_not_hiding_over_due_tasks_by_default(self):
        self.assertFalse(
            self.viewer.is_hiding_task_status(task.status.overdue)
        )

    def test_hide_over_due_tasks(self):
        self.viewer.hide_task_status(task.status.overdue)
        self.assertTrue(self.viewer.is_hiding_task_status(task.status.overdue))

    def test_hide_over_due_tasks_sets_setting(self):
        self.viewer.hide_task_status(task.status.overdue)
        self.assertTrue(
            settings.get(self.viewer.settingsSection(), "hideoverduetasks")
        )

    def test_hide_over_due_tasks_affects_presentation(self):
        self.viewer.presentation().append(
            task.Task(dueDateTime=date.Yesterday())
        )
        self.viewer.hide_task_status(task.status.overdue)
        self.assertFalse(self.viewer.presentation())

    def test_unhide_over_due_tasks(self):
        self.viewer.presentation().append(
            task.Task(dueDateTime=date.Yesterday())
        )
        self.viewer.hide_task_status(task.status.overdue)
        self.viewer.hide_task_status(task.status.overdue, False)
        self.assertTrue(self.viewer.presentation())

    def test_is_not_hiding_completed_tasks_by_default(self):
        self.assertFalse(
            self.viewer.is_hiding_task_status(task.status.completed)
        )

    def test_hide_completed_tasks(self):
        self.viewer.hide_task_status(task.status.completed)
        self.assertTrue(
            self.viewer.is_hiding_task_status(task.status.completed)
        )

    def test_hide_completed_tasks_sets_setting(self):
        self.viewer.hide_task_status(task.status.completed)
        self.assertTrue(
            settings.get(self.viewer.settingsSection(), "hidecompletedtasks")
        )

    def test_hide_completed_tasks_affects_presentation(self):
        self.viewer.presentation().append(
            task.Task(completionDateTime=date.Now())
        )
        self.viewer.hide_task_status(task.status.completed)
        self.assertFalse(self.viewer.presentation())

    def test_unhide_completed_tasks(self):
        self.viewer.presentation().append(
            task.Task(completionDateTime=date.Now())
        )
        self.viewer.hide_task_status(task.status.completed)
        self.viewer.hide_task_status(task.status.completed, False)
        self.assertTrue(self.viewer.presentation())

    def test_is_not_hiding_composite_tasks_by_default(self):
        self.assertFalse(self.viewer.is_hiding_composite_tasks())

    def test_hide_composite_tasks(self):
        self.viewer.hide_composite_tasks()
        self.assertTrue(self.viewer.is_hiding_composite_tasks())

    def test_hide_composite_tasks_sets_settings(self):
        self.viewer.hide_composite_tasks()
        self.assertTrue(
            settings.get(self.viewer.settingsSection(), "hidecompositetasks")
        )

    def test_hide_composite_tasks_affects_presentation(self):
        self.viewer.hide_composite_tasks()
        parent = task.Task()
        child = task.Task()
        parent.addChild(child)
        self.viewer.presentation().append(parent)
        self.assertEqual([child], self.viewer.presentation())

    def test_unhide_composite_tasks(self):
        self.viewer.hide_composite_tasks()
        parent = task.Task()
        child = task.Task()
        parent.addChild(child)
        self.viewer.presentation().append(parent)
        self.viewer.hide_composite_tasks(False)
        self.assertEqual(2, len(self.viewer.presentation()))

    def test_clear_all_filters(self):
        self.viewer.hide_composite_tasks()
        for status in task.Task.possibleStatuses():
            self.viewer.hide_task_status(status)
        self.viewer.reset_filter()
        self.assertFalse(self.viewer.is_hiding_composite_tasks())
        for status in task.Task.possibleStatuses():
            self.assertFalse(self.viewer.is_hiding_task_status(status))

    def test_apply_settings_when_creating_viewer(self):
        settings.set(self.viewer.settingsSection(), "hidecompletedtasks", True)
        another_viewer = self.createViewer()
        another_viewer.presentation().append(
            task.Task(completionDateTime=date.Now())
        )
        self.assertFalse(another_viewer.presentation())


class ViewerBaseClassTest(test.wxTestCase):
    def test_not_implemented_error(self):
        task_file = persistence.TaskFile()
        try:
            try:
                gui.viewer.base.Viewer(
                    self.frame, task_file, settingsSection="bla"
                )
                self.fail("Expected NotImplementedError")  # pragma: no cover
            except NotImplementedError:
                pass
        finally:
            task_file.close()
            task_file.stop()


class ViewerIteratorTestCase(test.wxTestCase):
    tree_mode = "Subclass responsibility"

    def createViewer(self):
        return gui.viewer.TaskViewer(self.window, self.taskFile)

    def setUp(self):
        super().setUp()
        self.taskFile = persistence.TaskFile()
        self.taskList = self.taskFile.tasks()
        self.window = AuiManagedFrameWithDynamicCenterPane(self.frame)
        self.viewer = self.createViewer()
        self.viewer.set_tree_mode(self.tree_mode == "True")
        self.viewer.sortBy("subject")

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def getItemsFromIterator(self):
        return list(self.viewer.visible_items())  # pylint: disable=E1101


class ViewerIteratorTestsMixin(object):
    def test_empty_presentation(self):
        self.assertEqual([], self.getItemsFromIterator())

    def test_one_item(self):
        self.taskList.append(task.Task())
        self.assertEqual(self.taskList, self.getItemsFromIterator())

    def test_one_parent_and_one_child(self):
        parent = task.Task("Z")
        child = task.Task("A", parent=parent)
        parent.addChild(child)
        self.taskList.append(parent)
        if self.tree_mode == "True":
            expected_parent_and_child_order = [parent, child]
        else:
            expected_parent_and_child_order = [child, parent]
        self.assertEqual(
            expected_parent_and_child_order, self.getItemsFromIterator()
        )

    def test_one_parent_one_child_and_one_grand_child(self):
        parent = task.Task("a-parent")
        child = task.Task("b-child", parent=parent)
        grand_child = task.Task("c-grandchild", parent=child)
        parent.addChild(child)
        child.addChild(grand_child)
        self.taskList.append(parent)
        self.assertEqual(
            [parent, child, grand_child], self.getItemsFromIterator()
        )

    def test_that_tasks_not_in_presentation_are_excluded(self):
        parent = task.Task("parent")
        child = task.Task("child")
        parent.addChild(child)
        self.taskList.append(parent)
        self.viewer.setSearchFilter("parent", matchCase=True)
        self.assertEqual([parent], self.getItemsFromIterator())


class TreeViewerIteratorTest(ViewerIteratorTestCase, ViewerIteratorTestsMixin):
    tree_mode = "True"


class ListViewerIteratorTest(ViewerIteratorTestCase, ViewerIteratorTestsMixin):
    tree_mode = "False"


class ViewerWithColumnsTest(test.wxTestCase):
    def setUp(self):
        self.taskFile = persistence.TaskFile()
        self.viewer = gui.viewer.TaskViewer(self.frame, self.taskFile)

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def test_default_column_width(self):
        expected_width = (
            hypertreelist._DEFAULT_COL_WIDTH
        )  # pylint: disable=W0212
        self.assertEqual(expected_width, self.viewer.getColumnWidth("subject"))
