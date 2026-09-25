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

import wx
import test
from taskcoachlib import gui, config
from taskcoachlib.gui import uicommand
from taskcoachlib.gui.uicommand import Separator
from taskcoachlib.domain import task, category, date


class MockViewerContainer(object):
    def __init__(self):
        self.__sortBy = "subject"
        self.__ascending = True
        self.selection = []
        self.showingCategories = False

    def settingsSection(self):
        return "section"

    def curselection(self):
        return self.selection  # pragma: no cover

    def is_showing_categories(self):
        return self.showingCategories  # pragma: no cover

    def isSortable(self):
        return True

    def sortBy(self, sortKey):
        self.__sortBy = sortKey

    def isSortedBy(self, sortKey):
        return sortKey == self.__sortBy

    def isSortOrderAscending(self, *args, **kwargs):  # pylint: disable=W0613
        return self.__ascending

    def setSortOrderAscending(self, ascending=True):
        self.__ascending = ascending

    def isSortByTaskStatusFirst(self):
        return True

    def isSortCaseSensitive(self):
        return True

    def getSortUICommands(self):
        return [
            uicommand.ViewerSortOrderCommand(viewer=self),
            uicommand.ViewerSortCaseSensitive(viewer=self),
            uicommand.ViewerSortByTaskStatusFirst(viewer=self),
            Separator(),
            uicommand.ViewerSortByCommand(
                viewer=self,
                value="subject",
                menu_text="Sub&ject",
                help_text="help",
            ),
            uicommand.ViewerSortByCommand(
                viewer=self,
                value="description",
                menu_text="&Description",
                help_text="help",
            ),
        ]


class MenuTestCase(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.frame.viewer = MockViewerContainer()
        self.menu = gui.menu.Menu(self.frame)
        menuBar = wx.MenuBar()
        menuBar.Append(self.menu, "menu")
        self.frame.SetMenuBar(menuBar)


class MenuTest(MenuTestCase):
    def testLenEmptyMenu(self):
        self.assertEqual(0, len(self.menu))

    def testLenNonEmptyMenu(self):
        self.menu.AppendSeparator()
        self.assertEqual(1, len(self.menu))


class MenuWithBooleanMenuItemsTestCase(MenuTestCase):
    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)
        self.commands = self.createCommands()

    def createCommands(self):
        raise NotImplementedError  # pragma: no cover

    def assertMenuItemsChecked(self, *expectedStates):
        for command in self.commands:
            self.menu.appendUICommand(command)
        self.menu.openMenu()
        for index, shouldBeChecked in enumerate(expectedStates):
            isChecked = self.menu.FindItemByPosition(index).IsChecked()
            if shouldBeChecked:
                self.assertTrue(isChecked)
            else:
                self.assertFalse(isChecked)


class MenuWithCheckItemsTest(MenuWithBooleanMenuItemsTestCase):
    def createCommands(self):
        return [
            uicommand.UICheckCommand(
                settings=self.settings, section="view", setting="statusbar"
            )
        ]

    def testCheckedItem(self):
        self.settings.set("view", "statusbar", "True")
        self.assertMenuItemsChecked(True)

    def testUncheckedItem(self):
        self.settings.set("view", "statusbar", "False")
        self.assertMenuItemsChecked(False)


class MenuWithRadioItemsTest(MenuWithBooleanMenuItemsTestCase):
    def createCommands(self):
        return [
            uicommand.UIRadioCommand(
                settings=self.settings,
                section="view",
                setting="toolbar",
                value=value,
            )
            for value in [None, (16, 16)]
        ]

    def testRadioItem_FirstChecked(self):
        self.settings.setvalue("view", "toolbar", None)
        self.assertMenuItemsChecked(True, False)

    def testRadioItem_SecondChecked(self):
        self.settings.setvalue("view", "toolbar", (16, 16))
        self.assertMenuItemsChecked(False, True)


class MockIOController:
    def __init__(self):
        self.openCalled = False

    def open(self, *args, **kwargs):  # pylint: disable=W0613
        self.openCalled = True


class RecentFilesMenuTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.ioController = MockIOController()
        self.settings = config.Settings(load=False)
        self.initialFileMenuLength = len(self.createFileMenu())
        self.filename1 = "c:/Program Files/TaskCoach/test.tsk"
        self.filename2 = "c:/two.tsk"
        self.filenames = []

    def createFileMenu(self):
        return gui.menu.FileMenu(
            self.frame, self.settings, self.ioController, None
        )

    def setRecentFilesAndCreateMenu(self, *filenames):
        self.addRecentFiles(*filenames)
        self.menu = self.createFileMenu()  # pylint: disable=W0201

    def addRecentFiles(self, *filenames):
        self.filenames.extend(filenames)
        self.settings.set("file", "recentfiles", str(list(self.filenames)))

    def assertRecentFileMenuItems(self, *expectedFilenames):
        expectedFilenames = expectedFilenames or self.filenames
        self.openMenu()
        numberOfMenuItemsAdded = len(expectedFilenames)
        if numberOfMenuItemsAdded > 0:
            numberOfMenuItemsAdded += 1  # the extra separator
        self.assertEqual(
            self.initialFileMenuLength + numberOfMenuItemsAdded, len(self.menu)
        )
        for index, expectedFilename in enumerate(expectedFilenames):
            menuItem = self.menu.FindItemByPosition(
                self.initialFileMenuLength - 1 + index
            )
            # Apparently the '&' can also be a '_' (seen on Ubuntu)
            expectedLabel = "&%d %s" % (index + 1, expectedFilename)
            self.assertEqual(expectedLabel[1:], menuItem.GetItemLabel()[1:])

    def openMenu(self):
        pass  # The menu updates itself when the recent files change

    def testNoRecentFiles(self):
        self.setRecentFilesAndCreateMenu()
        self.assertRecentFileMenuItems()

    def testOneRecentFileWhenCreatingMenu(self):
        self.setRecentFilesAndCreateMenu(self.filename1)
        self.assertRecentFileMenuItems()

    def testTwoRecentFilesWhenCreatingMenu(self):
        self.setRecentFilesAndCreateMenu(self.filename1, self.filename2)
        self.assertRecentFileMenuItems()

    def testAddRecentFileAfterCreatingMenu(self):
        self.setRecentFilesAndCreateMenu()
        self.addRecentFiles(self.filename1)
        self.assertRecentFileMenuItems()

    def testOneRecentFileWhenCreatingMenuAndAddOneRecentFileAfterCreatingMenu(
        self,
    ):
        self.setRecentFilesAndCreateMenu(self.filename1)
        self.addRecentFiles(self.filename2)
        self.assertRecentFileMenuItems()

    def testOpenARecentFile(self):
        self.setRecentFilesAndCreateMenu(self.filename1)
        self.openMenu()
        menuItem = self.menu.FindItemByPosition(self.initialFileMenuLength - 1)
        self.menu.invokeMenuItem(menuItem)
        self.assertTrue(self.ioController.openCalled)

    def testNeverShowMoreThanTheMaximumNumberAllowed(self):
        # Read when the menu is built; it has no Preferences setting
        self.settings.set("file", "maxrecentfiles", "1")
        self.setRecentFilesAndCreateMenu(self.filename1, self.filename2)
        self.assertRecentFileMenuItems(self.filename1)


class ViewMenuTestCase(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)
        self.viewerContainer = MockViewerContainer()
        self.menuBar = wx.MenuBar()
        self.parentMenu = wx.Menu()
        self.menuBar.Append(self.parentMenu, "parentMenu")
        self.menu = self.createMenu()
        self.parentMenu.AppendSubMenu(self.menu, "menu")
        self.frame.SetMenuBar(self.menuBar)

    def createMenu(self):
        self.frame.viewer = self.viewerContainer
        menu = gui.menu.SortMenu(self.frame, self.parentMenu, "menu")
        menu.updateMenu()
        return menu

    def open_menu(self):
        # What MainMenu does on EVT_MENU_OPEN
        self.menu._update_menu_state()

    def testSortOrderAscending(self):
        self.viewerContainer.setSortOrderAscending(True)
        self.open_menu()
        self.assertTrue(self.menu.FindItemByPosition(0).IsChecked())

    def testSortOrderDescending(self):
        self.viewerContainer.setSortOrderAscending(False)
        self.open_menu()
        self.assertFalse(self.menu.FindItemByPosition(0).IsChecked())

    def testSortBySubject(self):
        self.viewerContainer.sortBy("subject")
        self.open_menu()
        self.assertTrue(self.menu.FindItemByPosition(4).IsChecked())
        self.assertFalse(self.menu.FindItemByPosition(5).IsChecked())

    def testSortByDescription(self):
        self.viewerContainer.sortBy("description")
        self.open_menu()
        self.assertFalse(self.menu.FindItemByPosition(4).IsChecked())
        self.assertTrue(self.menu.FindItemByPosition(5).IsChecked())


class StartEffortForTaskMenuTest(test.wxTestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.tasks = task.TaskList()
        self.menu = gui.menu.StartEffortForTaskMenu(self.frame, self.tasks)

    def addTask(self, subject="Subject"):
        newTask = task.Task(subject=subject, plannedStartDateTime=date.Now())
        self.tasks.append(newTask)
        return newTask

    def addParentAndChild(
        self, parentSubject="Subject", childSubject="Subject"
    ):
        parent = self.addTask(parentSubject)
        child = self.addTask(childSubject)
        parent.addChild(child)
        return parent, child

    def item_labels(self):
        # Rebuilt when the tray menu pops up, not on task changes
        self.menu.updateMenuItems()
        return [item.GetItemLabelText() for item in self.menu.GetMenuItems()]

    def test_placeholder_when_nothing_to_track(self):
        self.assertEqual(["All tasks are completed!"], self.item_labels())

    def testNewTasksAreAdded(self):
        self.addTask()
        self.assertEqual(["Subject"], self.item_labels())

    def testDeletedTasksAreRemoved(self):
        newTask = self.addTask()
        self.tasks.remove(newTask)
        self.assertEqual(["All tasks are completed!"], self.item_labels())

    def testNewChildTasksAreAdded(self):
        self.addParentAndChild(childSubject="Child")
        # The parent's line, then an arrow line with its subtasks
        self.assertEqual(["Subject", "Subject"], self.item_labels())
        sub_menu = self.menu.GetMenuItems()[1].GetSubMenu()
        self.assertEqual(
            ["Child"], [i.GetItemLabelText() for i in sub_menu.GetMenuItems()]
        )

    def testDeletedChildTasksAreRemoved(self):
        child = self.addParentAndChild()[1]
        self.tasks.remove(child)
        self.assertEqual(["Subject"], self.item_labels())

    def test_completed_parent_only_holds_its_open_subtasks(self):
        # Reopening a subtask reopens its parent, so build it as the
        # XML reader does, e.g. for a file from an older version
        child = task.Task(subject="Child")
        parent = task.Task(
            subject="Subject", completionDateTime=date.Now(), children=[child]
        )
        self.tasks.append(parent)
        self.assertEqual(["Subject"], self.item_labels())
        self.assertTrue(self.menu.GetMenuItems()[0].GetSubMenu())

    def test_tasks_are_sorted_ignoring_case(self):
        for subject in ("b", "A", "c"):
            self.addTask(subject)
        self.assertEqual(["A", "b", "c"], self.item_labels())

    def testTaskWithNonAsciiSubject(self):
        self.addParentAndChild("Jérôme", "Jîrôme")
        self.menu.updateMenuItems()
        self.assertEqual(2, len(self.menu))


class ToggleCategoryMenuTest(test.wxTestCase):
    def setUp(self):
        self.categories = category.CategoryList()
        self.category1 = category.Category("Category 1")
        self.category2 = category.Category("Category 2")
        self.viewerContainer = MockViewerContainer()
        self.menu = gui.menu.ToggleCategoryMenu(
            self.frame, self.categories, self.viewerContainer
        )

    def setUpSubcategories(self):
        self.category1.addChild(self.category2)
        self.categories.append(self.category1)

    def test_placeholder_when_no_categories(self):
        labels = [item.GetItemLabelText() for item in self.menu.GetMenuItems()]
        self.assertEqual(["(No categories defined yet)"], labels)

    def testOneCategory(self):
        self.categories.append(self.category1)
        self.assertEqual(1, len(self.menu))

    def testTwoCategories(self):
        self.categories.extend([self.category1, self.category2])
        self.assertEqual(2, len(self.menu))

    def testSubcategory(self):
        self.setUpSubcategories()
        # The category's toggle, then a submenu for its subcategories
        self.assertEqual(2, len(self.menu))

    def testSubcategorySubmenuLabel(self):
        self.setUpSubcategories()
        self.assertEqual(
            self.category1.subject(),
            self.menu.GetMenuItems()[1].GetItemLabelText(),
        )

    def testSubcategorySubmenuItemLabel(self):
        self.setUpSubcategories()
        sub_menu = self.menu.GetMenuItems()[1].GetSubMenu()
        label = sub_menu.GetMenuItems()[0].GetItemLabelText()
        self.assertEqual(self.category2.subject(), label)

    def testMutualExclusiveSubcategories_AreCheckItems(self):
        self.category1.makeSubcategoriesExclusive()
        self.setUpSubcategories()
        category3 = category.Category("Category 3")
        self.category1.addChild(category3)
        sub_menu = self.menu.GetMenuItems()[1].GetSubMenu()
        for sub_menu_item in sub_menu.GetMenuItems():
            self.assertEqual(wx.ITEM_CHECK, sub_menu_item.GetKind())

    def testMutualExclusiveSubcategories_NoneChecked(self):
        self.category1.makeSubcategoriesExclusive()
        self.setUpSubcategories()
        category3 = category.Category("Category 3")
        self.category1.addChild(category3)
        sub_menu_items = (
            self.menu.GetMenuItems()[1].GetSubMenu().GetMenuItems()
        )
        checked_items = [item for item in sub_menu_items if item.IsChecked()]
        self.assertFalse(checked_items)

    def testMutualExclusiveSubcategoriesWithSubcategories(self):
        self.category1.makeSubcategoriesExclusive()
        self.setUpSubcategories()
        category3 = category.Category("Category 3")
        self.category1.addChild(category3)
        category4 = category.Category("Category 4")
        category3.addChild(category4)
        sub_menu_items = (
            self.menu.GetMenuItems()[1].GetSubMenu().GetMenuItems()
        )
        checked_items = [item for item in sub_menu_items if item.IsChecked()]
        self.assertFalse(checked_items)


class TaskTemplateMenuTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.uicommands = [Separator()]  # Stands in for a template
        uicommands = self.uicommands

        class TaskTemplateMenu(gui.menu.TaskTemplateMenu):
            def getUICommands(self):
                return uicommands

        self.menu_class = TaskTemplateMenu
        self.settings = config.Settings(load=False)

    def open_menu(self, menu):
        self.frame.ProcessEvent(wx.MenuEvent(wx.wxEVT_MENU_OPEN, menu=menu))

    def test_menu_is_refilled_when_its_parent_opens(self):
        parent = wx.Menu()
        menu = self.menu_class(
            self.frame, task.TaskList(), self.settings, parent, "Templates"
        )
        parent.AppendSubMenu(menu, "Templates")
        self.uicommands.append(Separator())  # A template was added
        self.open_menu(parent)
        self.assertEqual(2, len(menu))

    def test_menu_is_not_refilled_when_another_menu_opens(self):
        parent = wx.Menu()
        menu = self.menu_class(
            self.frame, task.TaskList(), self.settings, parent, "Templates"
        )
        self.uicommands.append(Separator())
        self.open_menu(wx.Menu())
        self.assertEqual(1, len(menu))
