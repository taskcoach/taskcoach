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

import ast
import test
from taskcoachlib import gui, config, widgets, persistence
from taskcoachlib.domain import task, date
from wx.lib.agw import hypertreelist


class AuiManagedFrameWithDynamicCenterPane(
    widgets.AuiManagedFrameWithDynamicCenterPane
):
    def AddBalloonTip(self, *args, **kwargs):
        pass


class Window(AuiManagedFrameWithDynamicCenterPane):
    def addPane(self, viewer, title, name="name", floating=False):
        super().addPane(viewer, title, name, floating)


class ViewerTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)
        self.taskFile = persistence.TaskFile()
        self.task = task.Task("task")
        self.taskFile.tasks().append(self.task)
        self.window = Window(self.frame)
        self.viewerContainer = gui.viewer.ViewerContainer(
            self.window, self.settings
        )
        self.viewer = self.createViewer()
        self.viewerContainer.addViewer(self.viewer)

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def createViewer(self):
        return gui.viewer.TaskViewer(self.window, self.taskFile, self.settings)

    def testSelectAllViaWidget(self):
        self.viewer.widget.select_all()
        self.viewer.updateSelection()
        self.assertEqual([self.task], self.viewer.curselection())

    def testSelectAllViaWidgetWithMultipleItems(self):
        self.taskFile.tasks().append(task.Task("second"))
        self.viewer.widget.select_all()
        self.viewer.updateSelection()
        self.assertEqual(2, len(self.viewer.curselection()))

    def testSelectAll(self):
        self.viewer.select_all()
        self.viewer.endOfSelectAll()
        self.assertEqual([self.task], self.viewer.curselection())

    def testSelectAllWithMultipleItems(self):
        self.taskFile.tasks().append(task.Task("second"))
        self.viewer.select_all()
        self.viewer.endOfSelectAll()
        self.assertEqual(2, len(self.viewer.curselection()))

    def testSelectNextItemAfterDeletingSelection(self):
        secondTask = task.Task("second")
        self.taskFile.tasks().append(secondTask)
        self.viewer.select([self.task])
        self.taskFile.tasks().remove(self.task)
        self.assertEqual([secondTask], self.viewer.curselection())

    def testSelectParentAfterDeletingSelectedChild(self):
        secondTask = task.Task("second")
        self.taskFile.tasks().append(secondTask)
        child = task.Task("child")
        self.task.addChild(child)
        child.setParent(self.task)
        self.taskFile.tasks().append(child)
        self.viewer.select([child])
        self.taskFile.tasks().remove(child)
        self.assertEqual([self.task], self.viewer.curselection())

    def testDontChangeSelectionAfterDeletingAnItemThatIsNotSelected(self):
        secondTask = task.Task("second")
        self.taskFile.tasks().append(secondTask)
        child = task.Task("child")
        self.task.addChild(child)
        child.setParent(self.task)
        self.taskFile.tasks().append(child)
        self.viewer.select([secondTask])
        self.taskFile.tasks().remove(child)
        self.assertEqual([secondTask], self.viewer.curselection())

    def testFirstViewerInstanceSettingsSection(self):
        self.assertEqual(
            self.viewer.__class__.__name__.lower(),
            self.viewer.settingsSection(),
        )

    def testSecondViewerInstanceHasAnotherSettingsSection(self):
        viewer2 = self.createViewer()
        self.assertEqual(
            self.viewer.settingsSection() + "1", viewer2.settingsSection()
        )

    def testTitle(self):
        self.assertEqual(self.viewer.defaultTitle, self.viewer.title())

    def testSetTitle(self):
        self.viewer.setTitle("New title")
        self.assertEqual("New title", self.viewer.title())

    def testSetTitleSavesTitleInSettings(self):
        self.viewer.setTitle("New title")
        self.assertEqual(
            "New title",
            self.settings.get(self.viewer.settingsSection(), "title"),
        )

    def testSetTitleDoesNotSaveTitleInSettingsWhenTitleIsDefaultTitle(self):
        self.viewer.setTitle(self.viewer.defaultTitle)
        self.assertEqual(
            "", self.settings.get(self.viewer.settingsSection(), "title")
        )

    def testSetTitleChangesTabTitle(self):
        self.viewer.setTitle("New title")
        self.assertEqual(
            "New title", self.window.manager.GetPane(self.viewer).caption
        )

    def testGetItemTooltipData(self):
        self.task.setDescription("Description")
        expectedData = [
            ("led_grey_icon", ["task"]),
            ("folder_blue_arrow_icon", []),
            ("paperclip_icon", []),
            (None, ["Description"]),
        ]
        self.assertEqual(
            expectedData, self.viewer.getItemTooltipData(self.task)
        )


class SortableViewerTest(test.TestCase):
    def setUp(self):
        self.settings = config.Settings(load=False)
        self.viewer = self.createViewer()

    def createViewer(self):
        viewer = gui.viewer.mixin.SortableViewerMixin()
        viewer.settings = self.settings
        viewer.settingsSection = lambda: "taskviewer"
        viewer.SorterClass = task.sorter.Sorter
        presentation = viewer.createSorter(task.TaskList())
        viewer.presentation = lambda: presentation
        return viewer

    def testIsSortable(self):
        self.assertTrue(self.viewer.isSortable())

    def testSortBy(self):
        self.viewer.sortBy("subject")
        self.assertEqual(
            "subject",
            ast.literal_eval(self.settings.get(self.viewer.settingsSection(), "sortby"))[
                0
            ],
        )

    def testSortByTwiceFlipsSortOrder(self):
        self.viewer.sortBy("subject")
        self.viewer.setSortOrderAscending(True)
        self.viewer.sortBy("subject")
        self.assertFalse(self.viewer.isSortOrderAscending())

    def testIsSortedBy(self):
        self.viewer.sortBy("description")
        self.assertTrue(self.viewer.isSortedBy("description"))

    def testSortOrderAscending(self):
        self.viewer.setSortOrderAscending(True)
        self.assertTrue(self.viewer.isSortOrderAscending())

    def testSortOrderDescending(self):
        self.viewer.setSortOrderAscending(False)
        self.assertFalse(self.viewer.isSortOrderAscending())

    def testSetSortCaseSensitive(self):
        self.viewer.setSortCaseSensitive(True)
        self.assertTrue(self.viewer.isSortCaseSensitive())

    def testSetSortCaseInsensitive(self):
        self.viewer.setSortCaseSensitive(False)
        self.assertFalse(self.viewer.isSortCaseSensitive())

    def testApplySettingsWhenCreatingViewer(self):
        self.settings.set(
            self.viewer.settingsSection(), "sortby", '["description"]'
        )
        anotherViewer = self.createViewer()
        anotherViewer.presentation().extend(
            [task.Task(description="B"), task.Task(description="A")]
        )
        self.assertEqual(
            ["A", "B"], [t.description() for t in anotherViewer.presentation()]
        )


class SortableViewerForTasksTest(test.TestCase):
    def setUp(self):
        self.settings = config.Settings(load=False)

        class ViewerUnderTest(gui.viewer.mixin.SortableViewerForTasksMixin):
            viewerImages = []

        self.viewer = ViewerUnderTest()
        self.viewer.settings = self.settings
        self.viewer.settingsSection = lambda: "taskviewer"
        self.viewer.presentation = lambda: task.sorter.Sorter(task.TaskList())

    def testSetSortByTaskStatusFirst(self):
        self.viewer.setSortByTaskStatusFirst(True)
        self.assertTrue(self.viewer.isSortByTaskStatusFirst())

    def testSetNoSortByTaskStatusFirst(self):
        self.viewer.setSortByTaskStatusFirst(False)
        self.assertFalse(self.viewer.isSortByTaskStatusFirst())


class DummyViewer(object):
    def isTreeViewer(self):
        return False

    def createFilter(self, presentation):
        return presentation


class SearchableViewerUnderTest(
    gui.viewer.mixin.SearchableViewerMixin, DummyViewer
):
    pass


class SearchableViewerTest(test.TestCase):
    def setUp(self):
        self.settings = config.Settings(load=False)
        self.viewer = self.createViewer()

    def createViewer(self):
        viewer = SearchableViewerUnderTest()
        # pylint: disable=W0201
        viewer.settings = self.settings
        viewer.settingsSection = lambda: "taskviewer"
        presentation = viewer.createFilter(task.TaskList())
        viewer.presentation = lambda: presentation
        return viewer

    def testIsSearchable(self):
        self.assertTrue(self.viewer.isSearchable())

    def testDefaultSearchFilter(self):
        self.assertEqual(
            ("", False, False, False, False), self.viewer.getSearchFilter()
        )

    def testSetSearchFilterString(self):
        self.viewer.setSearchFilter("bla", matchCase=True)
        self.assertEqual(
            "bla",
            self.settings.get(
                self.viewer.settingsSection(), "searchfilterstring"
            ),
        )

    def testSetSearchFilterString_AffectsPresentation(self):
        self.viewer.presentation().append(task.Task())
        self.viewer.setSearchFilter("bla")
        self.assertFalse(self.viewer.presentation())

    def testSearchMatchCase(self):
        self.viewer.setSearchFilter("bla", matchCase=True)
        self.assertEqual(
            True,
            self.settings.getboolean(
                self.viewer.settingsSection(), "searchfiltermatchcase"
            ),
        )

    def testSearchMatchCase_AffectsPresenation(self):
        self.viewer.presentation().append(task.Task("BLA"))
        self.viewer.setSearchFilter("bla", matchCase=True)
        self.assertFalse(self.viewer.presentation())

    def testSearchIncludesSubItems(self):
        self.viewer.setSearchFilter("bla", includeSubItems=True)
        self.assertEqual(
            True,
            self.settings.getboolean(
                self.viewer.settingsSection(), "searchfilterincludesubitems"
            ),
        )

    def testSearchIncludesSubItems_AffectsPresentation(self):
        parent = task.Task("parent")
        child = task.Task("child")
        parent.addChild(child)
        self.viewer.presentation().append(parent)
        self.viewer.setSearchFilter("parent", includeSubItems=True)
        self.assertEqual(2, len(self.viewer.presentation()))

    def testSearchDescription(self):
        self.viewer.setSearchFilter("bla", searchDescription=True)
        self.assertEqual(
            True,
            self.settings.getboolean(
                self.viewer.settingsSection(), "searchdescription"
            ),
        )

    def testSearchDescription_AffectsPresentation(self):
        self.viewer.presentation().append(
            task.Task("subject", description="description")
        )
        self.viewer.setSearchFilter("descr", searchDescription=True)
        self.assertEqual(1, len(self.viewer.presentation()))

    def testApplySettingsWhenCreatingViewer(self):
        self.settings.set(
            self.viewer.settingsSection(), "searchfilterstring", "whatever"
        )
        anotherViewer = self.createViewer()
        anotherViewer.presentation().append(task.Task())
        self.assertFalse(anotherViewer.presentation())


class FilterableViewerTest(test.TestCase):
    def setUp(self):
        self.viewer = gui.viewer.mixin.FilterableViewerMixin()

    def testIsFilterable(self):
        self.assertTrue(self.viewer.isFilterable())


class FilterableViewerForTasksUnderTest(
    gui.viewer.mixin.FilterableViewerForTasksMixin, DummyViewer
):
    pass


class FilterableViewerForTasks(test.TestCase):
    def setUp(self):
        self.settings = config.Settings(load=False)
        task.Task.settings = self.settings
        self.viewer = self.createViewer()

    def tearDown(self):
        super().tearDown()
        self.viewer.taskFile.close()
        self.viewer.taskFile.stop()

    def createViewer(self):
        viewer = FilterableViewerForTasksUnderTest()
        # pylint: disable=W0201
        viewer.taskFile = persistence.TaskFile()
        viewer.settings = self.settings
        viewer.settingsSection = lambda: "taskviewer"
        presentation = viewer.createFilter(viewer.taskFile.tasks())
        viewer.presentation = lambda: presentation
        return viewer

    def testIsNotHidingInactiveTasksByDefault(self):
        self.assertFalse(self.viewer.isHidingTaskStatus(task.status.inactive))

    def testHideInactiveTasks(self):
        self.viewer.hideTaskStatus(task.status.inactive)
        self.assertTrue(self.viewer.isHidingTaskStatus(task.status.inactive))

    def testHideInactiveTasks_SetsSetting(self):
        self.viewer.hideTaskStatus(task.status.inactive)
        self.assertTrue(
            self.settings.getboolean(
                self.viewer.settingsSection(), "hideinactivetasks"
            )
        )

    def testHideInactiveTasks_AffectsPresentation(self):
        self.viewer.presentation().append(
            task.Task(plannedStartDateTime=date.Tomorrow())
        )
        self.viewer.hideTaskStatus(task.status.inactive)
        self.assertFalse(self.viewer.presentation())

    def testUnhideInactiveTasks(self):
        self.viewer.presentation().append(
            task.Task(plannedStartDateTime=date.Tomorrow())
        )
        self.viewer.hideTaskStatus(task.status.inactive)
        self.viewer.hideTaskStatus(task.status.inactive, False)
        self.assertTrue(self.viewer.presentation())

    def testIsNotHidingLateTasksByDefault(self):
        self.assertFalse(self.viewer.isHidingTaskStatus(task.status.late))

    def testHideLateTasks(self):
        self.viewer.hideTaskStatus(task.status.late)
        self.assertTrue(self.viewer.isHidingTaskStatus(task.status.late))

    def testHideLateTasks_SetsSetting(self):
        self.viewer.hideTaskStatus(task.status.late)
        self.assertTrue(
            self.settings.getboolean(
                self.viewer.settingsSection(), "hidelatetasks"
            )
        )

    def testHideLateTasks_AffectsPresentation(self):
        self.viewer.presentation().append(
            task.Task(plannedStartDateTime=date.Yesterday())
        )
        self.viewer.hideTaskStatus(task.status.late)
        self.assertFalse(self.viewer.presentation())

    def testUnhideLateTasks(self):
        self.viewer.presentation().append(
            task.Task(plannedStartDateTime=date.Yesterday())
        )
        self.viewer.hideTaskStatus(task.status.late)
        self.viewer.hideTaskStatus(task.status.late, False)
        self.assertTrue(self.viewer.presentation())

    def testIsNotHidingDueSoonTasksByDefault(self):
        self.assertFalse(self.viewer.isHidingTaskStatus(task.status.duesoon))

    def testHideDueSoonTasks(self):
        self.viewer.hideTaskStatus(task.status.duesoon)
        self.assertTrue(self.viewer.isHidingTaskStatus(task.status.duesoon))

    def testHideDueSoonTasks_SetsSetting(self):
        self.viewer.hideTaskStatus(task.status.duesoon)
        self.assertTrue(
            self.settings.getboolean(
                self.viewer.settingsSection(), "hideduesoontasks"
            )
        )

    def testHideDueSoonTasks_AffectsPresentation(self):
        self.viewer.presentation().append(
            task.Task(dueDateTime=date.Now() + date.ONE_HOUR)
        )
        self.viewer.hideTaskStatus(task.status.duesoon)
        self.assertFalse(self.viewer.presentation())

    def testUnhideDueSoonTasks(self):
        self.viewer.presentation().append(
            task.Task(dueDateTime=date.Now() + date.ONE_HOUR)
        )
        self.viewer.hideTaskStatus(task.status.duesoon)
        self.viewer.hideTaskStatus(task.status.duesoon, False)
        self.assertTrue(self.viewer.presentation())

    def testIsNotHidingOverDueTasksByDefault(self):
        self.assertFalse(self.viewer.isHidingTaskStatus(task.status.overdue))

    def testHideOverDueTasks(self):
        self.viewer.hideTaskStatus(task.status.overdue)
        self.assertTrue(self.viewer.isHidingTaskStatus(task.status.overdue))

    def testHideOverDueTasks_SetsSetting(self):
        self.viewer.hideTaskStatus(task.status.overdue)
        self.assertTrue(
            self.settings.getboolean(
                self.viewer.settingsSection(), "hideoverduetasks"
            )
        )

    def testHideOverDueTasks_AffectsPresentation(self):
        self.viewer.presentation().append(
            task.Task(dueDateTime=date.Yesterday())
        )
        self.viewer.hideTaskStatus(task.status.overdue)
        self.assertFalse(self.viewer.presentation())

    def testUnhideOverDueTasks(self):
        self.viewer.presentation().append(
            task.Task(dueDateTime=date.Yesterday())
        )
        self.viewer.hideTaskStatus(task.status.overdue)
        self.viewer.hideTaskStatus(task.status.overdue, False)
        self.assertTrue(self.viewer.presentation())

    def testIsNotHidingCompletedTasksByDefault(self):
        self.assertFalse(self.viewer.isHidingTaskStatus(task.status.completed))

    def testHideCompletedTasks(self):
        self.viewer.hideTaskStatus(task.status.completed)
        self.assertTrue(self.viewer.isHidingTaskStatus(task.status.completed))

    def testHideCompletedTasks_SetsSetting(self):
        self.viewer.hideTaskStatus(task.status.completed)
        self.assertTrue(
            self.settings.getboolean(
                self.viewer.settingsSection(), "hidecompletedtasks"
            )
        )

    def testHideCompletedTasks_AffectsPresentation(self):
        self.viewer.presentation().append(
            task.Task(completionDateTime=date.Now())
        )
        self.viewer.hideTaskStatus(task.status.completed)
        self.assertFalse(self.viewer.presentation())

    def testUnhideCompletedTasks(self):
        self.viewer.presentation().append(
            task.Task(completionDateTime=date.Now())
        )
        self.viewer.hideTaskStatus(task.status.completed)
        self.viewer.hideTaskStatus(task.status.completed, False)
        self.assertTrue(self.viewer.presentation())

    def testIsNotHidingCompositeTasksByDefault(self):
        self.assertFalse(self.viewer.isHidingCompositeTasks())

    def testHideCompositeTasks(self):
        self.viewer.hideCompositeTasks()
        self.assertTrue(self.viewer.isHidingCompositeTasks())

    def testHideCompositeTasks_SetsSettings(self):
        self.viewer.hideCompositeTasks()
        self.assertTrue(
            self.settings.getboolean(
                self.viewer.settingsSection(), "hidecompositetasks"
            )
        )

    def testHideCompositeTasks_AffectsPresentation(self):
        self.viewer.hideCompositeTasks()
        parent = task.Task()
        child = task.Task()
        parent.addChild(child)
        self.viewer.presentation().append(parent)
        self.assertEqual([child], self.viewer.presentation())

    def testUnhideCompositeTasks(self):
        self.viewer.hideCompositeTasks()
        parent = task.Task()
        child = task.Task()
        parent.addChild(child)
        self.viewer.presentation().append(parent)
        self.viewer.hideCompositeTasks(False)
        self.assertEqual(2, len(self.viewer.presentation()))

    def testClearAllFilters(self):
        self.viewer.hideCompositeTasks()
        for status in task.Task.possibleStatuses():
            self.viewer.hideTaskStatus(status)
        self.viewer.resetFilter()
        self.assertFalse(self.viewer.isHidingCompositeTasks())
        for status in task.Task.possibleStatuses():
            self.assertFalse(self.viewer.isHidingTaskStatus(status))

    def testApplySettingsWhenCreatingViewer(self):
        self.settings.set(
            self.viewer.settingsSection(), "hidecompletedtasks", "True"
        )
        anotherViewer = self.createViewer()
        anotherViewer.presentation().append(
            task.Task(completionDateTime=date.Now())
        )
        self.assertFalse(anotherViewer.presentation())


class ViewerBaseClassTest(test.wxTestCase):
    def testNotImplementedError(self):
        taskFile = persistence.TaskFile()
        try:
            try:
                gui.viewer.base.Viewer(
                    self.frame, taskFile, None, settingsSection="bla"
                )
                self.fail("Expected NotImplementedError")  # pragma: no cover
            except NotImplementedError:
                pass
        finally:
            taskFile.close()
            taskFile.stop()


class ViewerIteratorTestCase(test.wxTestCase):
    treeMode = "Subclass responsibility"

    def createViewer(self):
        return gui.viewer.TaskViewer(self.window, self.taskFile, self.settings)

    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)
        task.Task.settings = self.settings
        self.taskFile = persistence.TaskFile()
        self.taskList = self.taskFile.tasks()
        self.window = AuiManagedFrameWithDynamicCenterPane(self.frame)
        self.viewer = self.createViewer()
        self.settings.setboolean(
            self.viewer.settingsSection(), "treemode", self.treeMode == "True"
        )
        self.viewer.sortBy("subject")

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def getItemsFromIterator(self):
        return list(self.viewer.visibleItems())  # pylint: disable=E1101


class ViewerIteratorTestsMixin(object):
    def testEmptyPresentation(self):
        self.assertEqual([], self.getItemsFromIterator())

    def testOneItem(self):
        self.taskList.append(task.Task())
        self.assertEqual(self.taskList, self.getItemsFromIterator())

    def testOneParentAndOneChild(self):
        parent = task.Task("Z")
        child = task.Task("A", parent=parent)
        parent.addChild(child)
        self.taskList.append(parent)
        if self.treeMode == "True":
            expectedParentAndChildOrder = [parent, child]
        else:
            expectedParentAndChildOrder = [child, parent]
        self.assertEqual(
            expectedParentAndChildOrder, self.getItemsFromIterator()
        )

    def testOneParentOneChildAndOneGrandChild(self):
        parent = task.Task("a-parent")
        child = task.Task("b-child", parent=parent)
        grandChild = task.Task("c-grandchild", parent=child)
        parent.addChild(child)
        child.addChild(grandChild)
        self.taskList.append(parent)
        self.assertEqual(
            [parent, child, grandChild], self.getItemsFromIterator()
        )

    def testThatTasksNotInPresentationAreExcluded(self):
        parent = task.Task("parent")
        child = task.Task("child")
        parent.addChild(child)
        self.taskList.append(parent)
        self.viewer.setSearchFilter("parent", matchCase=True)
        self.assertEqual([parent], self.getItemsFromIterator())


class TreeViewerIteratorTest(ViewerIteratorTestCase, ViewerIteratorTestsMixin):
    treeMode = "True"


class ListViewerIteratorTest(ViewerIteratorTestCase, ViewerIteratorTestsMixin):
    treeMode = "False"


class ViewerWithColumnsTest(test.wxTestCase):
    def setUp(self):
        self.settings = config.Settings(load=False)
        self.taskFile = persistence.TaskFile()
        self.viewer = gui.viewer.TaskViewer(
            self.frame, self.taskFile, self.settings
        )

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def testDefaultColumnWidth(self):
        expectedWidth = (
            hypertreelist._DEFAULT_COL_WIDTH
        )  # pylint: disable=W0212
        self.assertEqual(expectedWidth, self.viewer.getColumnWidth("subject"))
