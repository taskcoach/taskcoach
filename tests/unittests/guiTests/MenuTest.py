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
from taskcoachlib import gui
from taskcoachlib.gui import uicommand
from taskcoachlib.gui.uicommand import Separator
from taskcoachlib.domain import task, category, date
from taskcoachlib.config import settings


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

    def sortBy(self, sort_key):
        self.__sortBy = sort_key

    def isSortedBy(self, sort_key):
        return sort_key == self.__sortBy

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
        menu_bar = wx.MenuBar()
        menu_bar.Append(self.menu, "menu")
        self.frame.SetMenuBar(menu_bar)


class MenuTest(MenuTestCase):
    def test_len_empty_menu(self):
        self.assertEqual(0, len(self.menu))

    def test_len_non_empty_menu(self):
        self.menu.AppendSeparator()
        self.assertEqual(1, len(self.menu))


class SometimesShown(uicommand.base_uicommand.UICommand):
    """A command shown only while visible() says so, as Edit in
    place."""

    shown = False

    def visible(self):
        return self.shown

    def do_command(self, event):  # pragma: no cover
        pass


class MenuWithOptionalItemsTest(MenuTestCase):
    """A command with visible() is in the menu only while it is
    visible, in its place."""

    def setUp(self):
        super().setUp()
        self.first = uicommand.base_uicommand.UICommand(menu_text="first")
        self.optional = SometimesShown(menu_text="optional")
        self.last = uicommand.base_uicommand.UICommand(menu_text="last")
        self.menu.appendUICommands(self.first, self.optional, self.last)

    def labels(self):
        return [item.GetItemLabelText() for item in self.menu.GetMenuItems()]

    def test_hidden_while_not_visible(self):
        self.assertEqual(["first", "last"], self.labels())

    def test_not_asked_while_the_menu_is_built(self):
        # What visible() reads (a view's list) may not exist yet
        class NotYet(SometimesShown):
            def visible(self):
                raise AttributeError("no widget yet")

        gui.menu.Menu(self.frame).appendUICommands(NotYet(menu_text="x"))

    def test_shown_in_its_place_once_visible(self):
        self.optional.shown = True
        self.menu.show_visible_items()
        self.assertEqual(["first", "optional", "last"], self.labels())

    def test_hidden_again(self):
        self.optional.shown = True
        self.menu.show_visible_items()
        self.optional.shown = False
        self.menu.show_visible_items()
        self.assertEqual(["first", "last"], self.labels())


class MenuWithBooleanMenuItemsTestCase(MenuTestCase):
    def setUp(self):
        super().setUp()
        self.commands = self.createCommands()

    def createCommands(self):
        raise NotImplementedError  # pragma: no cover

    def assertMenuItemsChecked(self, *expected_states):
        for command in self.commands:
            self.menu.appendUICommand(command)
        self.menu.openMenu()
        for index, should_be_checked in enumerate(expected_states):
            is_checked = self.menu.FindItemByPosition(index).IsChecked()
            if should_be_checked:
                self.assertTrue(is_checked)
            else:
                self.assertFalse(is_checked)


class MenuWithCheckItemsTest(MenuWithBooleanMenuItemsTestCase):
    def createCommands(self):
        return [uicommand.UICheckCommand(section="view", setting="statusbar")]

    def test_checked_item(self):
        settings.set("view", "statusbar", True)
        self.assertMenuItemsChecked(True)

    def test_unchecked_item(self):
        settings.set("view", "statusbar", False)
        self.assertMenuItemsChecked(False)


class MenuWithRadioItemsTest(MenuWithBooleanMenuItemsTestCase):
    def createCommands(self):
        return [
            uicommand.UIRadioCommand(
                section="view",
                setting="toolbar",
                value=value,
            )
            for value in [None, (16, 16)]
        ]

    def test_radio_item_first_checked(self):
        settings.set("view", "toolbar", None)
        self.assertMenuItemsChecked(True, False)

    def test_radio_item_second_checked(self):
        settings.set("view", "toolbar", (16, 16))
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
        self.initialFileMenuLength = len(self.createFileMenu())
        self.filename1 = "c:/Program Files/TaskCoach/test.tsk"
        self.filename2 = "c:/two.tsk"
        self.filenames = []

    def createFileMenu(self):
        return gui.menu.FileMenu(self.frame, self.ioController, None)

    def setRecentFilesAndCreateMenu(self, *filenames):
        self.addRecentFiles(*filenames)
        self.menu = self.createFileMenu()  # pylint: disable=W0201

    def addRecentFiles(self, *filenames):
        self.filenames.extend(filenames)
        settings.set("file", "recentfiles", list(self.filenames))

    def assertRecentFileMenuItems(self, *expected_filenames):
        expected_filenames = expected_filenames or self.filenames
        self.openMenu()
        number_of_menu_items_added = len(expected_filenames)
        if number_of_menu_items_added > 0:
            number_of_menu_items_added += 1  # the extra separator
        self.assertEqual(
            self.initialFileMenuLength + number_of_menu_items_added,
            len(self.menu),
        )
        for index, expected_filename in enumerate(expected_filenames):
            menu_item = self.menu.FindItemByPosition(
                self.initialFileMenuLength - 1 + index
            )
            # Apparently the '&' can also be a '_' (seen on Ubuntu)
            expected_label = "&%d %s" % (index + 1, expected_filename)
            self.assertEqual(expected_label[1:], menu_item.GetItemLabel()[1:])

    def openMenu(self):
        pass  # The menu updates itself when the recent files change

    def test_no_recent_files(self):
        self.setRecentFilesAndCreateMenu()
        self.assertRecentFileMenuItems()

    def test_one_recent_file_when_creating_menu(self):
        self.setRecentFilesAndCreateMenu(self.filename1)
        self.assertRecentFileMenuItems()

    def test_two_recent_files_when_creating_menu(self):
        self.setRecentFilesAndCreateMenu(self.filename1, self.filename2)
        self.assertRecentFileMenuItems()

    def test_add_recent_file_after_creating_menu(self):
        self.setRecentFilesAndCreateMenu()
        self.addRecentFiles(self.filename1)
        self.assertRecentFileMenuItems()

    def test_one_recent_file_before_and_one_after_creating_menu(
        self,
    ):
        self.setRecentFilesAndCreateMenu(self.filename1)
        self.addRecentFiles(self.filename2)
        self.assertRecentFileMenuItems()

    def test_open_a_recent_file(self):
        self.setRecentFilesAndCreateMenu(self.filename1)
        self.openMenu()
        menu_item = self.menu.FindItemByPosition(
            self.initialFileMenuLength - 1
        )
        self.menu.invokeMenuItem(menu_item)
        self.assertTrue(self.ioController.openCalled)

    def test_never_show_more_than_the_maximum_number_allowed(self):
        # Read when the menu is built; it has no Preferences setting
        settings.set("file", "maxrecentfiles", 1)
        self.setRecentFilesAndCreateMenu(self.filename1, self.filename2)
        self.assertRecentFileMenuItems(self.filename1)


class ViewMenuTestCase(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.viewerContainer = MockViewerContainer()
        self.menuBar = wx.MenuBar()
        self.parentMenu = wx.Menu()
        self.menuBar.Append(self.parentMenu, "parentMenu")
        self.menu = self.createMenu()
        self.parentMenu.AppendSubMenu(self.menu, "menu")
        self.frame.SetMenuBar(self.menuBar)

    def createMenu(self):
        self.frame.viewer = self.viewerContainer
        menu = gui.menu.SortMenu(self.frame, self.parentMenu)
        menu.updateMenu()
        return menu

    def open_menu(self):
        # What wx does when the menu opens
        self.menu.UpdateUI()

    def test_sort_order_ascending(self):
        self.viewerContainer.setSortOrderAscending(True)
        self.open_menu()
        self.assertTrue(self.menu.FindItemByPosition(0).IsChecked())

    def test_sort_order_descending(self):
        self.viewerContainer.setSortOrderAscending(False)
        self.open_menu()
        self.assertFalse(self.menu.FindItemByPosition(0).IsChecked())

    def test_sort_by_subject(self):
        self.viewerContainer.sortBy("subject")
        self.open_menu()
        self.assertTrue(self.menu.FindItemByPosition(4).IsChecked())
        self.assertFalse(self.menu.FindItemByPosition(5).IsChecked())

    def test_sort_by_description(self):
        self.viewerContainer.sortBy("description")
        self.open_menu()
        self.assertFalse(self.menu.FindItemByPosition(4).IsChecked())
        self.assertTrue(self.menu.FindItemByPosition(5).IsChecked())


class StartEffortForTaskMenuTest(test.wxTestCase):
    def setUp(self):
        self.tasks = task.TaskList()
        self.menu = gui.menu.StartEffortForTaskMenu(self.frame, self.tasks)

    def addTask(self, subject="Subject"):
        new_task = task.Task(subject=subject, plannedStartDateTime=date.Now())
        self.tasks.append(new_task)
        return new_task

    def addParentAndChild(
        self, parent_subject="Subject", child_subject="Subject"
    ):
        parent = self.addTask(parent_subject)
        child = self.addTask(child_subject)
        parent.addChild(child)
        return parent, child

    def item_labels(self):
        # Rebuilt when the tray menu pops up, not on task changes
        self.menu.updateMenuItems()
        return [item.GetItemLabelText() for item in self.menu.GetMenuItems()]

    def test_placeholder_when_nothing_to_track(self):
        self.assertEqual(["All tasks are completed!"], self.item_labels())

    def test_new_tasks_are_added(self):
        self.addTask()
        self.assertEqual(["Subject"], self.item_labels())

    def test_deleted_tasks_are_removed(self):
        new_task = self.addTask()
        self.tasks.remove(new_task)
        self.assertEqual(["All tasks are completed!"], self.item_labels())

    def test_new_child_tasks_are_added(self):
        self.addParentAndChild(child_subject="Child")
        # The parent's line, then an arrow line with its subtasks
        self.assertEqual(["Subject", "Subject"], self.item_labels())
        sub_menu = self.menu.GetMenuItems()[1].GetSubMenu()
        self.assertEqual(
            ["Child"], [i.GetItemLabelText() for i in sub_menu.GetMenuItems()]
        )

    def test_deleted_child_tasks_are_removed(self):
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

    def test_task_with_non_ascii_subject(self):
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

    def test_one_category(self):
        self.categories.append(self.category1)
        self.assertEqual(1, len(self.menu))

    def test_two_categories(self):
        self.categories.extend([self.category1, self.category2])
        self.assertEqual(2, len(self.menu))

    def test_subcategory(self):
        self.setUpSubcategories()
        # The category's toggle, then a submenu for its subcategories
        self.assertEqual(2, len(self.menu))

    def test_subcategory_submenu_label(self):
        self.setUpSubcategories()
        self.assertEqual(
            self.category1.subject(),
            self.menu.GetMenuItems()[1].GetItemLabelText(),
        )

    def test_subcategory_submenu_item_label(self):
        self.setUpSubcategories()
        sub_menu = self.menu.GetMenuItems()[1].GetSubMenu()
        label = sub_menu.GetMenuItems()[0].GetItemLabelText()
        self.assertEqual(self.category2.subject(), label)

    def test_mutual_exclusive_subcategories_are_check_items(self):
        self.category1.makeSubcategoriesExclusive()
        self.setUpSubcategories()
        category3 = category.Category("Category 3")
        self.category1.addChild(category3)
        sub_menu = self.menu.GetMenuItems()[1].GetSubMenu()
        for sub_menu_item in sub_menu.GetMenuItems():
            self.assertEqual(wx.ITEM_CHECK, sub_menu_item.GetKind())

    def test_mutual_exclusive_subcategories_none_checked(self):
        self.category1.makeSubcategoriesExclusive()
        self.setUpSubcategories()
        category3 = category.Category("Category 3")
        self.category1.addChild(category3)
        sub_menu_items = (
            self.menu.GetMenuItems()[1].GetSubMenu().GetMenuItems()
        )
        checked_items = [item for item in sub_menu_items if item.IsChecked()]
        self.assertFalse(checked_items)

    def test_mutual_exclusive_subcategories_with_subcategories(self):
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


class DynamicMenuEntryTest(test.wxTestCase):
    """A dynamic menu enables or disables its entry in its parent menu,
    found as the entry whose submenu it is: not by its label, which may
    carry a mnemonic and a shortcut, and an item inside the menu may
    have the same label."""

    def test_entry_follows_whether_the_menu_is_enabled(self):
        state = dict(enabled=False)

        class Menu(gui.menu.DynamicMenu):
            def register_for_menu_update(self):
                pass

            def enabled(self):
                return state["enabled"]

        parent = wx.Menu()
        menu = Menu(self.frame, parent)
        menu.Append(wx.ID_ANY, "Menu")
        entry = parent.AppendSubMenu(menu, "&Menu\tCtrl+M")
        menu.updateMenu()
        self.assertFalse(entry.IsEnabled())
        state["enabled"] = True
        menu.updateMenu()
        self.assertTrue(entry.IsEnabled())


class TaskTemplateMenuTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.uicommands = [Separator()]  # Stands in for a template
        uicommands = self.uicommands

        class TaskTemplateMenu(gui.menu.TaskTemplateMenu):
            def getUICommands(self):
                return uicommands

        self.menu_class = TaskTemplateMenu

    def open_menu(self, menu):
        self.frame.ProcessEvent(wx.MenuEvent(wx.wxEVT_MENU_OPEN, menu=menu))

    def test_menu_is_refilled_when_its_parent_opens(self):
        parent = wx.Menu()
        menu = self.menu_class(self.frame, task.TaskList(), parent)
        parent.AppendSubMenu(menu, "Templates")
        self.uicommands.append(Separator())  # A template was added
        self.open_menu(parent)
        self.assertEqual(2, len(menu))

    def test_menu_is_not_refilled_when_another_menu_opens(self):
        parent = wx.Menu()
        menu = self.menu_class(self.frame, task.TaskList(), parent)
        self.uicommands.append(Separator())
        self.open_menu(wx.Menu())
        self.assertEqual(1, len(menu))
