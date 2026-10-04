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
from unittests import dummy
from taskcoachlib import gui, persistence, widgets
from taskcoachlib.i18n import _
from taskcoachlib.domain import task
from taskcoachlib import patterns
from taskcoachlib.config import settings


class DummyMainWindow(widgets.AuiManagedFrameWithDynamicCenterPane):
    count = 0

    def __init__(self):
        super().__init__(None)

    def add_pane(self, window, caption, floating=False):
        self.count += 1
        super().add_pane(window, caption, "name%d" % self.count, floating)

    def AddBalloonTip(self, *args, **kwargs):
        pass


class DummyPane(object):
    optionActive = False

    def __init__(self, window):
        self.window = window

    def IsToolbar(self):
        return False

    def IsNotebookPage(self):
        return True

    def IsNotebookControl(self):
        return False

    def HasFlag(self, flag):
        return True


class DummyEvent(object):
    def __init__(self, pane):
        self._pane = pane

    def Skip(self):
        pass

    def GetPane(self):
        return self._pane


class DummyChangeEvent(DummyEvent):
    pass


class DummyCloseEvent(DummyEvent):
    def __init__(self, window):
        super().__init__(DummyPane(window))


class ClickableWidget(dummy.DummyWidget):
    Bind = wx.Frame.Bind  # The viewer's clicks bound on it


class ViewerWithClickableWidget(dummy.ViewerWithDummyWidget):
    def create_widget(self):
        super().create_widget().Destroy()
        return ClickableWidget(self)


class ViewerContainerTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.events = 0
        self.taskFile = persistence.TaskFile()
        self.mainWindow = DummyMainWindow()
        self.container = gui.viewer.ViewerContainer(self.mainWindow)
        self.viewer1 = self.createViewer("taskviewer1")
        self.container.add_viewer(self.viewer1)
        self.viewer2 = self.createViewer("taskviewer2")
        self.container.add_viewer(self.viewer2)

    def createViewer(self, settingsSection):
        settings.add_section(settingsSection)
        return ViewerWithClickableWidget(
            self.mainWindow,
            self.taskFile,
            settingsSection=settingsSection,
        )

    def on_event(self, event):  # pylint: disable=W0613
        self.events += 1

    def testCreate(self):
        self.assertEqual(0, self.container.size())

    def testAddTask(self):
        self.taskFile.tasks().append(task.Task())
        self.assertEqual(1, self.container.size())

    def testDefaultActiveViewer(self):
        self.assertEqual(self.viewer1, self.container.active_viewer())

    def testChangePage_ChangesActiveViewer(self):
        self.container.activate_viewer(self.viewer2)
        self.assertEqual(self.viewer2, self.container.active_viewer())

    def click(self, window, event_type=wx.wxEVT_LEFT_DOWN):
        event = wx.MouseEvent(event_type)
        event.SetEventObject(window)
        window.GetEventHandler().ProcessEvent(event)
        test.settle()

    def test_a_click_in_a_views_widget_makes_it_the_active_view(self):
        # The calendars, timeline and square map take no focus
        self.click(self.viewer2.widget)
        self.assertEqual(self.viewer2, self.container.active_viewer())

    def test_a_right_click_in_a_views_widget_makes_it_the_active_view(self):
        self.click(self.viewer2.widget, wx.wxEVT_RIGHT_DOWN)
        self.assertEqual(self.viewer2, self.container.active_viewer())

    def test_a_right_click_beside_the_widget_makes_it_the_active_view(self):
        self.click(self.viewer2, wx.wxEVT_RIGHT_DOWN)
        self.assertEqual(self.viewer2, self.container.active_viewer())

    def paste_as_subitem(self, viewer):
        # The tasks and the categories viewers
        self.viewer1.coreObjectType = "tasks"
        self.viewer2.coreObjectType = "categories"
        command = gui.uicommand.EditPasteAsSubItem(viewer=viewer)
        # Its menu goes with the test
        self.addCleanup(command.removeInstance)
        return command

    def in_a_menu(self, command):
        # Kept as the main window keeps its menus: a freed menu's items
        # are gone
        self.menu = wx.Menu()
        command.add_to_menu(self.menu, self.mainWindow)
        return self.menu.FindItemById(command.id)

    def test_paste_as_subitem_names_the_items_of_the_active_viewer(self):
        command = self.paste_as_subitem(self.container)
        item = self.in_a_menu(command)
        self.container.activate_viewer(self.viewer2)
        # Before the menu opens: GTK sizes it for the label it has
        self.assertEqual(
            _("P&aste as subcategory") + "\tShift+Ctrl+V",
            item.GetItemLabel(),
        )

    def test_its_label_is_not_set_as_the_menu_opens(self):
        command = self.paste_as_subitem(self.container)
        self.in_a_menu(command)
        self.container.activate_viewer(self.viewer2)
        event = wx.UpdateUIEvent(command.id)
        command.on_menu_update_ui(event)
        self.assertFalse(event.GetSetText())

    def test_a_popup_menus_paste_as_subitem_names_its_viewers_items(self):
        command = self.paste_as_subitem(self.viewer2)
        self.container.activate_viewer(self.viewer1)
        self.assertEqual(
            _("P&aste as subcategory") + "\tShift+Ctrl+V", command.menu_text
        )

    def test_change_page_notifies_observers_about_new_active_viewer(self):
        patterns.Publisher().registerObserver(
            self.on_event, eventType=self.container.status_event_type()
        )
        self.container.on_page_changed(DummyChangeEvent(self.viewer2))
        self.assertTrue(self.events > 0)

    def testCloseViewer_RemovesViewerFromContainer(self):
        self.container.on_page_closed(DummyCloseEvent(self.viewer1))
        self.assertEqual([self.viewer2], self.container.viewers)

    def testCloseViewer_ChangesActiveViewer(self):
        self.container.on_page_changed(DummyChangeEvent(self.viewer2))
        self.container.on_page_closed(DummyCloseEvent(self.viewer2))
        self.assertEqual(self.viewer1, self.container.active_viewer())

    def test_close_viewer_notifies_observers_about_new_active_viewer(self):
        self.container.activate_viewer(self.viewer2)
        patterns.Publisher().registerObserver(
            self.on_event, eventType=self.container.status_event_type()
        )
        self.container.close_viewer(self.viewer2)
        self.assertTrue(self.events > 0)

    def test_activate_next_viewer(self):
        gui.uicommand.ActivateViewer(
            viewer=self.container, forward=True
        ).do_command(None)
        self.assertEqual(self.viewer2, self.container.active_viewer())
