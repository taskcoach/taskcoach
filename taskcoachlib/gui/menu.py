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

from taskcoachlib import patterns, persistence, help  # pylint: disable=W0622
from taskcoachlib.meta.debug import log_step
from taskcoachlib.domain import category
from taskcoachlib.i18n import _
from taskcoachlib.gui.newid import IdProvider
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
from taskcoachlib.config import settings
from taskcoachlib.config.defaults import (
    MAIN_TOOLBAR_ICON_SIZE_SMALL,
    MAIN_TOOLBAR_ICON_SIZE_MEDIUM,
    MAIN_TOOLBAR_ICON_SIZE_LARGE,
)
from . import uicommand
import taskcoachlib.gui.viewer
import wx
import os


class Menu(wx.Menu, uicommand.UICommandContainerMixin):
    def __init__(self, window):
        super().__init__()
        self._window = window
        self._accels = list()
        self._observers = list()
        # Commands shown only while their visible() says so, with the
        # place they take: [(command, position)]
        self._optional = list()

    def __len__(self):
        return self.GetMenuItemCount()

    def DestroyItem(self, menuItem):
        submenu = menuItem.GetSubMenu()
        if submenu:
            submenu.clearMenu()
            # Its own subscriptions end with it, like a window's
            patterns.Publisher().remove_observers_of(submenu)
        self._window.Unbind(wx.EVT_MENU, id=menuItem.GetId())
        self._window.Unbind(wx.EVT_UPDATE_UI, id=menuItem.GetId())
        super().DestroyItem(menuItem)

    def Destroy(self):
        patterns.Publisher().remove_observers_of(self)
        return super().Destroy()

    def clearMenu(self):
        """Remove all menu items."""
        for menuItem in self.MenuItems:
            self.DestroyItem(menuItem)
        for observer in self._observers:
            observer.removeInstance()
        self._observers = list()

    def accelerators(self):
        return self._accels

    def show_visible_items(self):
        """Add or remove the commands shown only while visible() says
        so; called before the menu pops up."""
        hidden = 0
        for ui_command, position in self._optional:
            shown = any(
                item.GetMenu() == self for item in ui_command.menu_items
            )
            visible = ui_command.visible()
            if visible and not shown:
                ui_command.add_to_menu(self, self._window, position - hidden)
            elif shown and not visible:
                ui_command.remove_from_menu(self, self._window)
            if not visible:
                hidden += 1

    def append_ui_command(self, ui_command):
        if hasattr(ui_command, "visible"):
            # Placed when the menu pops up (show_visible_items()):
            # what it depends on may not exist yet
            self._optional.append((ui_command, self.GetMenuItemCount()))
            ui_command.menu = self
            return None
        cmd = ui_command.add_to_menu(self, self._window)
        ui_command.menu = self
        self._accels.extend(ui_command.accelerators())
        if isinstance(ui_command, patterns.Observer):
            self._observers.append(ui_command)
        return cmd

    # Keep old name as alias
    appendUICommand = append_ui_command

    def appendMenu(self, text, subMenu, icon_id=None):
        subMenuItem = wx.MenuItem(
            self, id=IdProvider.get(), text=text, subMenu=subMenu
        )
        if icon_id:
            subMenuItem.SetBitmap(
                icon_catalog.get_bitmap(icon_id, LIST_ICON_SIZE)
            )
        self._accels.extend(subMenu.accelerators())
        self.Append(subMenuItem)

    def invokeMenuItem(self, menuItem):
        """Programmatically invoke the menuItem. This is mainly for testing
        purposes."""
        self._window.ProcessEvent(
            wx.CommandEvent(wx.wxEVT_COMMAND_MENU_SELECTED, menuItem.GetId())
        )

    def openMenu(self):
        """Programmatically open the menu. This is mainly for testing
        purposes."""
        # On Mac OSX, an explicit UpdateWindowUI is needed to ensure that
        # menu items are updated before the menu is opened. This is not needed
        # on other platforms, but it doesn't hurt either.
        self._window.UpdateWindowUI()
        self._window.ProcessEvent(wx.MenuEvent(wx.wxEVT_MENU_OPEN, menu=self))


class DynamicMenu(Menu):
    """A menu that registers for events and then updates itself whenever the
    event is fired."""

    def __init__(self, window, parent_menu=None):
        """Initialize the menu. With a parent menu, the menu enables or
        disables its entry there."""
        super().__init__(window)
        self._parentMenu = parent_menu
        self.registerForMenuUpdate()
        self.updateMenu()

    def registerForMenuUpdate(self):
        """Subclasses are responsible for binding an event to
        on_update_menu so that the menu gets a chance to update itself
        at the right time."""
        raise NotImplementedError

    def on_update_menu(self, event=None):
        """This event handler should be called at the right times so that
        the menu has a chance to update itself."""
        # If this is called by wx, 'skip' the event so that other event
        # handlers get a chance too:
        if event and hasattr(event, "Skip"):
            event.Skip()
            if event.GetMenu() != self._parentMenu:
                return

        try:  # Prepare for menu or window to be destroyed
            self.updateMenu()
        except (RuntimeError, wx.wxAssertionError):
            log_step("on_update_menu: menu/window dead", prefix="DEAD-OBJ")

    def updateMenu(self):
        """Updating the menu consists of two steps: updating the menu item
        of this menu in its parent menu, e.g. to enable or disable it, and
        updating the menu items of this menu."""
        self.updateMenuItemInParentMenu()
        self.updateMenuItems()

    def updateMenuItemInParentMenu(self):
        """Enable or disable the menu item in the parent menu, depending on
        what enabled() returns."""
        if self._parentMenu:
            my_id = self.my_id()
            if my_id != wx.NOT_FOUND:
                self._parentMenu.Enable(my_id, self.enabled())

    def my_id(self):
        """The id of this menu's entry in its parent menu: the entry
        whose submenu it is."""
        for item in self._parentMenu.GetMenuItems():
            if item.GetSubMenu() is self:
                return item.GetId()
        return wx.NOT_FOUND

    def updateMenuItems(self):
        """Update the menu items of this menu."""
        pass

    def enabled(self):
        """Return a boolean indicating whether this menu should be enabled in
        its parent menu. This method is called by
        updateMenuItemInParentMenu(). It returns True by default. Override
        in a subclass as needed."""
        return True


class DynamicMenuThatGetsUICommandsFromViewer(DynamicMenu):
    def __init__(self, viewer, parent_menu=None):  # pylint: disable=W0621
        self._uiCommands = None
        super().__init__(viewer, parent_menu)

    def registerForMenuUpdate(self):
        # Refill the menu whenever the menu is opened, because the menu might
        # depend on the status of the viewer:
        self._window.Bind(wx.EVT_MENU_OPEN, self.on_update_menu)

    def updateMenuItems(self):
        newCommands = self.getUICommands()
        try:
            if newCommands == self._uiCommands:
                return
        except wx._core.PyDeadObjectError:  # pylint: disable=W0212
            pass  # Old viewer was closed
        self.clearMenu()
        self.fillMenu(newCommands)
        self._uiCommands = newCommands

    def fillMenu(self, uiCommands):
        self.appendUICommands(*uiCommands)  # pylint: disable=W0142

    def getUICommands(self):
        raise NotImplementedError


class MainMenu(wx.MenuBar):
    def __init__(self, mainwindow, iocontroller, viewer_container, task_file):
        super().__init__()
        accels = list()
        for menu, text in [
            (
                FileMenu(mainwindow, iocontroller, viewer_container),
                _("&File"),
            ),
            (
                EditMenu(mainwindow, iocontroller, viewer_container),
                _("&Edit"),
            ),
            (
                ViewMenu(mainwindow, viewer_container, task_file),
                _("&View"),
            ),
            (
                NewMenu(mainwindow, task_file, viewer_container),
                _("&New"),
            ),
            (
                ActionMenu(mainwindow, task_file, viewer_container),
                _("&Actions"),
            ),
            (HelpMenu(mainwindow, iocontroller), _("&Help")),
        ]:
            self.Append(menu, text)
            accels.extend(menu.accelerators())
        mainwindow.SetAcceleratorTable(wx.AcceleratorTable(accels))


class FileMenu(Menu, patterns.Observer):
    """File menu with recent files list.

    DESIGN NOTE (GTK3 Dynamic Menu Item Sizing):

    Menus with dynamic items (recent files, undo/redo labels) must be
    populated at init time and updated via Publisher events when the
    underlying data changes — never during EVT_MENU_OPEN.

    GTK3 calculates menu popup size from the item count at open time.
    If items are added/removed inside EVT_MENU_OPEN, the size is wrong
    on first popup (scroll arrows appear with plenty of space). Second
    open sizes correctly because GTK caches the updated count.

    See PUBLISHER_OBSERVER.md §GTK3 Dynamic Menu Item Sizing for the
    full pattern and affected menus.
    """

    def __init__(self, mainwindow, iocontroller, viewer_container):
        super().__init__(mainwindow)
        patterns.Observer.__init__(self)
        self.__iocontroller = iocontroller
        self.__recentFileUICommands = []
        self.__separator = None
        self.appendUICommands(
            uicommand.FileOpen(iocontroller=iocontroller),
            uicommand.FileMerge(iocontroller=iocontroller),
            uicommand.FileClose(iocontroller=iocontroller),
            None,
            uicommand.FileSave(iocontroller=iocontroller),
            uicommand.FileSaveAs(iocontroller=iocontroller),
            uicommand.FileSaveSelection(
                iocontroller=iocontroller, viewer=viewer_container
            ),
        )
        self.appendUICommands(
            None,
            uicommand.FileSaveSelectedTaskAsTemplate(
                iocontroller=iocontroller, viewer=viewer_container
            ),
            uicommand.FileImportTemplate(iocontroller=iocontroller),
            uicommand.FileEditTemplates(),
            None,
            uicommand.PrintPageSetup(),
            uicommand.PrintPreview(viewer=viewer_container),
            uicommand.Print(viewer=viewer_container),
            None,
        )
        self.appendMenu(
            _("&Import"),
            ImportMenu(mainwindow, iocontroller),
            "oxygen_actions_document-import",
        )
        self.appendMenu(
            _("&Export"),
            ExportMenu(mainwindow, iocontroller),
            "oxygen_actions_document-export",
        )
        self.appendUICommands(
            None,
            uicommand.FileManageBackups(iocontroller=iocontroller),
        )
        self.__recentFilesStartPosition = len(self)
        self.appendUICommands(None, uicommand.FileQuit())

        # Populate recent files at init (fixes GTK3 dynamic menu sizing)
        self.__insertRecentFileMenuItems()

        # Update recent files when settings change
        self.registerObserver(
            self.__onRecentFilesChanged,
            eventType="file.recentfiles",
        )

    def __onRecentFilesChanged(self, event):  # pylint: disable=W0613
        """Update recent files menu when settings change."""
        self.__removeRecentFileMenuItems()
        self.__insertRecentFileMenuItems()

    def __insertRecentFileMenuItems(self):
        recent_files = settings.file.recentfiles
        if not recent_files:
            return
        max_recent = settings.file.maxrecentfiles
        recent_files = recent_files[:max_recent]
        self.__separator = self.InsertSeparator(
            self.__recentFilesStartPosition
        )
        for index, recent_file in enumerate(recent_files):
            file_number = index + 1
            menu_position = self.__recentFilesStartPosition + 1 + index
            ui_command = uicommand.RecentFileOpen(
                filename=recent_file,
                index=file_number,
                iocontroller=self.__iocontroller,
            )
            ui_command.add_to_menu(self, self._window, menu_position)
            self.__recentFileUICommands.append(ui_command)

    def __removeRecentFileMenuItems(self):
        for ui_command in self.__recentFileUICommands:
            ui_command.remove_from_menu(self, self._window)
        self.__recentFileUICommands = []
        if self.__separator:
            self.Remove(self.__separator)
            self.__separator = None

    def clearMenu(self):
        super().clearMenu()
        self.removeInstance()


class ExportMenu(Menu):
    def __init__(self, mainwindow, iocontroller):
        super().__init__(mainwindow)
        kwargs = dict(iocontroller=iocontroller)
        # pylint: disable=W0142
        self.appendUICommands(
            uicommand.FileExportAsHTML(**kwargs),
            uicommand.FileExportAsCSV(**kwargs),
            uicommand.FileExportAsICalendar(**kwargs),
            uicommand.FileExportAsTodoTxt(**kwargs),
        )


class ImportMenu(Menu):
    def __init__(self, mainwindow, iocontroller):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.FileImportCSV(iocontroller=iocontroller),
            uicommand.FileImportTodoTxt(iocontroller=iocontroller),
        )


class TaskTemplateMenu(DynamicMenu):
    """Refilled when it is about to show, so it needs no message when
    the templates change: in the menu bar when its parent menu opens,
    in the tray and on the toolbar before they pop it up."""

    def __init__(
        self,
        mainwindow,
        task_list,
        parent_menu=None,
    ):
        self.taskList = task_list
        super().__init__(mainwindow, parent_menu)

    def registerForMenuUpdate(self):
        if self._parentMenu is not None:
            # The parent's open, not our own: GTK3 sizes a menu before
            # its own EVT_MENU_OPEN handlers run
            self._window.Bind(wx.EVT_MENU_OPEN, self.on_update_menu)

    def updateMenuItems(self):
        self.clearMenu()
        self.fillMenu(self.getUICommands())

    def fillMenu(self, uiCommands):
        self.appendUICommands(*uiCommands)  # pylint: disable=W0142

    def getUICommands(self):
        path = settings.current().pathToTemplatesDir()
        commands = [
            uicommand.TaskNewFromTemplate(
                os.path.join(path, name),
                taskList=self.taskList,
            )
            for name in persistence.TemplateList(path).names()
        ]
        return commands


class EditMenu(Menu):
    def __init__(self, mainwindow, iocontroller, viewer_container):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.EditUndo(),
            uicommand.EditRedo(),
            None,
            uicommand.EditCut(viewer=viewer_container, id=wx.ID_CUT),
            uicommand.EditCopy(viewer=viewer_container, id=wx.ID_COPY),
            uicommand.EditPaste(viewer=viewer_container),
            uicommand.EditPasteAsSubItem(viewer=viewer_container),
            None,
            uicommand.Edit(viewer=viewer_container, id=wx.ID_EDIT),
            uicommand.Delete(viewer=viewer_container, id=wx.ID_DELETE),
            None,
            uicommand.SelectAll(viewer=viewer_container),
            uicommand.ClearSelection(viewer=viewer_container),
            None,
            uicommand.EditPreferences(),
        )


class ViewMenu(Menu):
    def __init__(self, mainwindow, viewer_container, task_file):
        super().__init__(mainwindow)
        self.appendMenu(
            _("&New viewer"),
            ViewViewerMenu(mainwindow, viewer_container, task_file),
            "nuvola_actions_tab-new-background",
        )
        activateNextViewer = uicommand.ActivateViewer(
            viewer=viewer_container,
            menu_text=_("&Activate next viewer\tCtrl+PgDn"),
            help_text=help.viewNextViewer,
            forward=True,
            icon_id="nuvola_actions_tab-duplicate",
        )
        activatePreviousViewer = uicommand.ActivateViewer(
            viewer=viewer_container,
            menu_text=_("Activate &previous viewer\tCtrl+PgUp"),
            help_text=help.viewPreviousViewer,
            forward=False,
            icon_id="taskcoach_actions_tab-duplicate-left",
        )
        self.appendUICommands(
            activateNextViewer,
            activatePreviousViewer,
            uicommand.RenameViewer(viewer=viewer_container),
            None,
        )
        self.appendMenu(_("&Mode"), ModeMenu(mainwindow, self))
        self.appendMenu(_("&Filter"), FilterMenu(mainwindow, self))
        self.appendMenu(_("&Sort"), SortMenu(mainwindow, self))
        self.appendMenu(_("&Columns"), ColumnMenu(mainwindow, self))
        self.appendMenu(_("&Rounding"), RoundingMenu(mainwindow, self))
        self.appendUICommands(
            None,
            uicommand.ViewExpandAll(viewer=viewer_container),
            uicommand.ViewCollapseAll(viewer=viewer_container),
            None,
        )
        self.appendMenu(_("T&oolbar"), ToolBarMenu(mainwindow))
        self.appendUICommands(
            uicommand.UICheckCommand(
                menu_text=_("Status&bar"),
                help_text=_("Show/hide status bar"),
                setting="statusbar",
            ),
            uicommand.ToggleAutoScroll(),
            None,
            uicommand.ResetWindowLayout(),
        )


class ViewViewerMenu(Menu):
    def __init__(self, mainwindow, viewer_container, task_file):
        super().__init__(mainwindow)
        ViewViewer = uicommand.ViewViewer
        kwargs = dict(viewer=viewer_container, taskFile=task_file)
        # pylint: disable=W0142
        viewViewerCommands = [
            ViewViewer(
                menu_text=_("&Task"),
                help_text=_(
                    "Open a new tab with a viewer that displays tasks"
                ),
                viewerClass=taskcoachlib.gui.viewer.TaskViewer,
                **kwargs
            ),
            ViewViewer(
                menu_text=_("Task &statistics"),
                help_text=_(
                    "Open a new tab with a viewer that displays task statistics"
                ),
                viewerClass=taskcoachlib.gui.viewer.TaskStatsViewer,
                **kwargs
            ),
        ]
        # Add square map viewer only if squaremap is available
        if taskcoachlib.gui.viewer.SquareTaskViewer is not None:
            viewViewerCommands.append(
                ViewViewer(
                    menu_text=_("Task &square map"),
                    help_text=_(
                        "Open a new tab with a viewer that displays tasks in a square map"
                    ),
                    viewerClass=taskcoachlib.gui.viewer.SquareTaskViewer,
                    **kwargs
                )
            )
        viewViewerCommands += [
            ViewViewer(
                menu_text=_("T&imeline"),
                help_text=_(
                    "Open a new tab with a viewer that displays a timeline of tasks and effort"
                ),
                viewerClass=taskcoachlib.gui.viewer.TimelineViewer,
                **kwargs
            ),
            ViewViewer(
                menu_text=_("&Calendar"),
                help_text=_(
                    "Open a new tab with a viewer that displays tasks in a calendar"
                ),
                viewerClass=taskcoachlib.gui.viewer.CalendarViewer,
                **kwargs
            ),
            ViewViewer(
                menu_text=_("&Hierarchical calendar"),
                help_text=_(
                    "Open a new tab with a viewer that displays task hierarchy in a calendar"
                ),
                viewerClass=taskcoachlib.gui.viewer.HierarchicalCalendarViewer,
                **kwargs
            ),
            ViewViewer(
                menu_text=_("&Category"),
                help_text=_(
                    "Open a new tab with a viewer that displays categories"
                ),
                viewerClass=taskcoachlib.gui.viewer.CategoryViewer,
                **kwargs
            ),
            ViewViewer(
                menu_text=_("&Effort"),
                help_text=_(
                    "Open a new tab with a viewer that displays efforts"
                ),
                viewerClass=taskcoachlib.gui.viewer.EffortViewer,
                **kwargs
            ),
            uicommand.ViewEffortViewerForSelectedTask(
                menu_text=_("Eff&ort for selected task(s)"),
                help_text=_(
                    "Open a new tab with a viewer that displays efforts for the selected task"
                ),
                viewerClass=taskcoachlib.gui.viewer.EffortViewer,
                **kwargs
            ),
            ViewViewer(
                menu_text=_("&Note"),
                help_text=_(
                    "Open a new tab with a viewer that displays notes"
                ),
                viewerClass=taskcoachlib.gui.viewer.NoteViewer,
                **kwargs
            ),
        ]
        self.appendUICommands(*viewViewerCommands)


class ModeMenu(DynamicMenuThatGetsUICommandsFromViewer):
    def enabled(self):
        return self._window.viewer.hasModes() and bool(
            self._window.viewer.getModeUICommands()
        )

    def getUICommands(self):
        return self._window.viewer.getModeUICommands()


class FilterMenu(DynamicMenuThatGetsUICommandsFromViewer):
    def enabled(self):
        return self._window.viewer.isFilterable() and bool(
            self._window.viewer.getFilterUICommands()
        )

    def getUICommands(self):
        return self._window.viewer.getFilterUICommands()


class ColumnMenu(DynamicMenuThatGetsUICommandsFromViewer):
    def enabled(self):
        return self._window.viewer.hasHideableColumns()

    def getUICommands(self):
        return self._window.viewer.getColumnUICommands()


class SortMenu(DynamicMenuThatGetsUICommandsFromViewer):
    def enabled(self):
        return self._window.viewer.isSortable()

    def getUICommands(self):
        return self._window.viewer.getSortUICommands()


class RoundingMenu(DynamicMenuThatGetsUICommandsFromViewer):
    def enabled(self):
        return self._window.viewer.supportsRounding()

    def getUICommands(self):
        return self._window.viewer.getRoundingUICommands()


class ToolBarMenu(Menu):
    def __init__(self, mainwindow):
        super().__init__(mainwindow)
        toolbarCommands = []
        _S = MAIN_TOOLBAR_ICON_SIZE_SMALL
        _M = MAIN_TOOLBAR_ICON_SIZE_MEDIUM
        _L = MAIN_TOOLBAR_ICON_SIZE_LARGE
        for value, menu_text, help_text in [
            (None, _("&Hide"), _("Hide the toolbar")),
            (
                (_S, _S),
                _("&Small images"),
                _("Small images (%dx%d) on the toolbar") % (_S, _S),
            ),
            (
                (_M, _M),
                _("&Medium-sized images"),
                _("Medium-sized images (%dx%d) on the toolbar") % (_M, _M),
            ),
            (
                (_L, _L),
                _("&Large images"),
                _("Large images (%dx%d) on the toolbar") % (_L, _L),
            ),
        ]:
            toolbarCommands.append(
                uicommand.UIRadioCommand(
                    setting="toolbar",
                    value=value,
                    menu_text=menu_text,
                    help_text=help_text,
                )
            )
        # pylint: disable=W0142
        self.appendUICommands(*toolbarCommands)


class NewMenu(Menu):
    def __init__(self, mainwindow, task_file, viewer_container):
        super().__init__(mainwindow)
        tasks = task_file.tasks()
        self.appendUICommands(
            uicommand.TaskNew(taskList=tasks),
            uicommand.NewTaskWithSelectedTasksAsPrerequisites(
                taskList=tasks, viewer=viewer_container
            ),
            uicommand.NewTaskWithSelectedTasksAsDependencies(
                taskList=tasks, viewer=viewer_container
            ),
        )
        label = _("New task from &template")
        self.appendMenu(
            label,
            TaskTemplateMenu(
                mainwindow,
                task_list=tasks,
                parent_menu=self,
            ),
            "taskcoach_actions_newtmpl",
        )
        self.appendUICommands(
            None,
            uicommand.EffortNew(
                viewer=viewer_container,
                effortList=task_file.efforts(),
                taskList=tasks,
            ),
            uicommand.CategoryNew(categories=task_file.categories()),
            uicommand.NoteNew(notes=task_file.notes()),
            None,
            uicommand.NewSubItem(viewer=viewer_container),
        )


class ActionMenu(Menu):
    def __init__(self, mainwindow, task_file, viewer_container):
        super().__init__(mainwindow)
        tasks = task_file.tasks()
        efforts = task_file.efforts()
        categories = task_file.categories()
        # Generic actions, applicable to all/most domain objects:
        self.appendUICommands(
            uicommand.AddAttachment(viewer=viewer_container),
            uicommand.OpenAllAttachments(viewer=viewer_container),
            None,
            uicommand.AddNote(viewer=viewer_container),
            uicommand.OpenAllNotes(viewer=viewer_container),
            None,
            uicommand.Mail(viewer=viewer_container),
            None,
        )
        self.appendMenu(
            _("&Toggle category"),
            ToggleCategoryMenu(
                mainwindow, categories=categories, viewer=viewer_container
            ),
            "nuvola_places_folder-downloads",
        )
        # Start of task specific actions:
        self.appendUICommands(
            None,
            uicommand.TaskMarkInactive(viewer=viewer_container),
            uicommand.TaskMarkActive(viewer=viewer_container),
            uicommand.TaskMarkCompleted(viewer=viewer_container),
            None,
        )
        uicommand.TaskPriorityParentMenu(viewer=viewer_container).add_to_menu(
            self,
            self._window,
            sub_menu=TaskPriorityMenu(mainwindow, tasks, viewer_container),
        )
        self.appendUICommands(
            None,
            uicommand.EffortStart(viewer=viewer_container, taskList=tasks),
            uicommand.EffortStop(
                viewer=viewer_container, effortList=efforts, taskList=tasks
            ),
            uicommand.EditTrackedTasks(taskList=tasks),
        )


class TaskPriorityMenu(Menu):
    def __init__(self, mainwindow, task_list, viewer):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.TaskIncPriority(taskList=task_list, viewer=viewer),
            uicommand.TaskDecPriority(taskList=task_list, viewer=viewer),
            uicommand.TaskMaxPriority(taskList=task_list, viewer=viewer),
            uicommand.TaskMinPriority(taskList=task_list, viewer=viewer),
        )


class HelpMenu(Menu):
    def __init__(self, mainwindow, iocontroller):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.Help(),
            uicommand.FAQ(),
            uicommand.Tips(),
            uicommand.Anonymize(iocontroller=iocontroller),
            None,
            uicommand.RequestSupport(),
            uicommand.ReportBug(),
            uicommand.RequestFeature(),
            None,
            uicommand.HelpTranslate(),
            None,
        )
        self.appendUICommands(
            uicommand.HelpAbout(),
            uicommand.CheckForUpdate(),
            uicommand.HelpLicense(),
        )


class TaskBarMenu(Menu):
    def __init__(self, task_bar_icon, task_file, viewer):
        super().__init__(task_bar_icon)
        tasks = task_file.tasks()
        efforts = task_file.efforts()
        self.appendUICommands(uicommand.TaskNew(taskList=tasks))
        self.appendMenu(
            _("New task from &template"),
            TaskTemplateMenu(task_bar_icon, task_list=tasks),
            "taskcoach_actions_newtmpl",
        )
        self.appendUICommands(None)  # Separator
        self.appendUICommands(
            uicommand.EffortNew(effortList=efforts, taskList=tasks),
            uicommand.CategoryNew(categories=task_file.categories()),
            uicommand.NoteNew(notes=task_file.notes()),
        )
        self.appendUICommands(None)  # Separator
        label = _("&Start tracking effort")
        self.appendMenu(
            label,
            StartEffortForTaskMenu(task_bar_icon, tasks, self),
            "nuvola_apps_clock",
        )
        self.appendUICommands(
            uicommand.EffortStop(
                viewer=viewer, effortList=efforts, taskList=tasks
            )
        )
        self.appendUICommands(
            None, uicommand.MainWindowRestore(), uicommand.FileQuit()
        )


class ToggleCategoryMenu(DynamicMenu):
    def __init__(
        self, mainwindow, categories, viewer
    ):  # pylint: disable=W0621
        self.categories = categories
        self.viewer = viewer
        super().__init__(mainwindow)

    def registerForMenuUpdate(self):
        for eventType in (
            self.categories.addItemEventType(),
            self.categories.removeItemEventType(),
        ):
            patterns.Publisher().registerObserver(
                self.on_update_menu,
                eventType=eventType,
                eventSource=self.categories,
            )
        patterns.Publisher().registerObserver(
            self.on_update_menu,
            eventType=category.Category.subjectChangedEventType(),
        )

    def updateMenuItems(self):
        self.clearMenu()
        rootItems = self.categories.rootItems()
        if rootItems:
            self.addMenuItemsForCategories(rootItems, self)
        else:
            menuItem = self.Append(wx.ID_ANY, _("(No categories defined yet)"))
            menuItem.Enable(False)

    def addMenuItemsForCategories(self, categories, menu):
        # pylint: disable=W0621
        categories = categories[:]
        categories.sort(key=lambda category: category.subject().lower())
        for category in categories:
            uiCommand = uicommand.ToggleCategory(
                category=category, viewer=self.viewer
            )
            uiCommand.add_to_menu(menu, self._window)
            if category.children():
                subMenu = Menu(self._window)
                self.addMenuItemsForCategories(category.children(), subMenu)
                menu.appendMenu(
                    category.subject(),
                    subMenu,
                    "taskcoach_actions_arrow_down_right",
                )

    def enabled(self):
        return bool(self.categories)


def trackable_task_tree(tasks):
    """What the start tracking menus show, as (task, trackable,
    children) for each task that can be tracked or has subtasks that
    can, sorted like the category menus. A completed task only holds
    its subtasks. tasks decides which tasks count (e.g. the
    viewer's)."""

    def nodes(candidates):
        result = []
        for each in sorted(candidates, key=lambda t: t.subject().lower()):
            children = nodes([c for c in each.children() if c in tasks])
            trackable = not each.completed()
            if trackable or children:
                result.append((each, trackable, children))
        return result

    return nodes(tasks.rootItems())


class StartEffortForTaskMenu(DynamicMenu):
    """A line per task to track, and like the category menus an arrow
    line under it with its subtasks. The tray's GTK menu shows the same
    tree (AppIndicatorTaskBarIcon)."""

    def __init__(self, task_bar_icon, tasks, parent_menu=None):
        self.tasks = tasks
        super().__init__(task_bar_icon, parent_menu)

    def registerForMenuUpdate(self):
        # Refilled before it shows (tray, toolbar button): following
        # every task change exhausted wx menu ids in recur() cascades
        pass

    def updateMenuItems(self):
        self.clearMenu()
        tree = trackable_task_tree(self.tasks)
        if not tree:
            item = self.Append(wx.ID_ANY, _("All tasks are completed!"))
            item.Enable(False)
            return
        self.__add_items(tree, self)

    def __add_items(self, nodes, menu):
        for each, trackable, children in nodes:
            if trackable:
                ui_command = uicommand.EffortStartForTask(
                    task=each, taskList=self.tasks
                )
                ui_command.add_to_menu(menu, self._window)
            if children:
                sub_menu = Menu(self._window)
                self.__add_items(children, sub_menu)
                subject = each.subject() or _("(No subject)")
                menu.appendMenu(
                    subject.replace("&", "&&"),
                    sub_menu,
                    "taskcoach_actions_arrow_down_right",
                )

    def enabled(self):
        return True


class TaskPopupMenu(Menu):
    def __init__(self, mainwindow, tasks, efforts, categories, task_viewer):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.EditCut(viewer=task_viewer),
            uicommand.EditCopy(viewer=task_viewer),
            uicommand.EditPaste(viewer=task_viewer),
            uicommand.EditPasteAsSubItem(viewer=task_viewer),
            None,
            uicommand.Edit(viewer=task_viewer),
            uicommand.EditInPlace(viewer=task_viewer),
            uicommand.Delete(viewer=task_viewer),
            None,
            uicommand.AddAttachment(viewer=task_viewer),
            uicommand.OpenAllAttachments(viewer=task_viewer),
            None,
            uicommand.AddNote(viewer=task_viewer),
            uicommand.OpenAllNotes(viewer=task_viewer),
            None,
            uicommand.Mail(viewer=task_viewer),
            None,
        )
        self.appendMenu(
            _("&Toggle category"),
            ToggleCategoryMenu(
                mainwindow, categories=categories, viewer=task_viewer
            ),
            "nuvola_places_folder-downloads",
        )
        self.appendUICommands(
            None,
            uicommand.TaskMarkInactive(viewer=task_viewer),
            uicommand.TaskMarkActive(viewer=task_viewer),
            uicommand.TaskMarkCompleted(viewer=task_viewer),
            None,
        )
        uicommand.TaskPriorityParentMenu(viewer=task_viewer).add_to_menu(
            self,
            self._window,
            sub_menu=TaskPriorityMenu(mainwindow, tasks, task_viewer),
        )
        self.appendUICommands(
            None,
            uicommand.EffortNew(
                viewer=task_viewer,
                effortList=efforts,
                taskList=tasks,
            ),
            uicommand.EffortStart(viewer=task_viewer, taskList=tasks),
            uicommand.EffortStop(
                viewer=task_viewer, effortList=efforts, taskList=tasks
            ),
            None,
            uicommand.TaskNew(taskList=tasks),
            uicommand.NewSubItem(viewer=task_viewer),
        )


class EffortPopupMenu(Menu):
    def __init__(self, mainwindow, tasks, efforts, effort_viewer):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.EditCut(viewer=effort_viewer),
            uicommand.EditCopy(viewer=effort_viewer),
            uicommand.EditPaste(viewer=effort_viewer),
            None,
            uicommand.Edit(viewer=effort_viewer),
            uicommand.Delete(viewer=effort_viewer),
            None,
            uicommand.EffortNew(
                viewer=effort_viewer,
                effortList=efforts,
                taskList=tasks,
            ),
            uicommand.EffortStartForEffort(
                viewer=effort_viewer, taskList=tasks
            ),
            uicommand.EffortStop(
                viewer=effort_viewer, effortList=efforts, taskList=tasks
            ),
        )


class CategoryPopupMenu(Menu):
    def __init__(
        self, mainwindow, task_file, category_viewer, local_only=False
    ):
        super().__init__(mainwindow)
        categories = category_viewer.presentation()
        tasks = task_file.tasks()
        notes = task_file.notes()
        self.appendUICommands(
            uicommand.EditCut(viewer=category_viewer),
            uicommand.EditCopy(viewer=category_viewer),
            uicommand.EditPaste(viewer=category_viewer),
            uicommand.EditPasteAsSubItem(viewer=category_viewer),
            None,
            uicommand.Edit(viewer=category_viewer),
            uicommand.EditInPlace(viewer=category_viewer),
            uicommand.Delete(viewer=category_viewer),
            None,
            uicommand.AddAttachment(viewer=category_viewer),
            uicommand.OpenAllAttachments(viewer=category_viewer),
            None,
            uicommand.AddNote(viewer=category_viewer),
            uicommand.OpenAllNotes(viewer=category_viewer),
            None,
            uicommand.Mail(viewer=category_viewer),
        )
        if not local_only:
            self.appendUICommands(
                None,
                uicommand.NewTaskWithSelectedCategories(
                    taskList=tasks,
                    categories=categories,
                    viewer=category_viewer,
                ),
                uicommand.NewNoteWithSelectedCategories(
                    notes=notes,
                    categories=categories,
                    viewer=category_viewer,
                ),
            )
        self.appendUICommands(
            None,
            uicommand.CategoryNew(categories=categories),
            uicommand.NewSubItem(viewer=category_viewer),
        )


class NotePopupMenu(Menu):
    def __init__(self, mainwindow, categories, note_viewer, notes=None):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.EditCut(viewer=note_viewer),
            uicommand.EditCopy(viewer=note_viewer),
            uicommand.EditPaste(viewer=note_viewer),
            uicommand.EditPasteAsSubItem(viewer=note_viewer),
            None,
            uicommand.Edit(viewer=note_viewer),
            uicommand.EditInPlace(viewer=note_viewer),
            uicommand.Delete(viewer=note_viewer),
            None,
            uicommand.AddAttachment(viewer=note_viewer),
            uicommand.OpenAllAttachments(viewer=note_viewer),
            None,
            uicommand.Mail(viewer=note_viewer),
            None,
        )
        self.appendMenu(
            _("&Toggle category"),
            ToggleCategoryMenu(
                mainwindow, categories=categories, viewer=note_viewer
            ),
            "nuvola_places_folder-downloads",
        )
        self.appendUICommands(None)
        if notes is not None:
            self.appendUICommands(
                uicommand.NoteNew(notes=notes, viewer=note_viewer),
            )
        self.appendUICommands(uicommand.NewSubItem(viewer=note_viewer))


class ColumnPopupMenuMixin(object):
    """Mixin class for column header popup menu's. These menu's get the
    column index property set by the control popping up the menu to
    indicate which column the user clicked. See
    widgets._CtrlWithColumnPopupMenuMixin."""

    def __setColumn(self, columnIndex):
        self.__columnIndex = columnIndex  # pylint: disable=W0201

    def __getColumn(self):
        return self.__columnIndex

    columnIndex = property(__getColumn, __setColumn)

    def getUICommands(self):
        if (
            not self._window
        ):  # Prevent PyDeadObject exception when running tests
            return []
        return [
            uicommand.HideCurrentColumn(viewer=self._window, menu=self),
            None,
        ] + self._window.getColumnUICommands()


class ColumnPopupMenu(ColumnPopupMenuMixin, Menu):
    """Column header popup menu."""

    def __init__(self, window):
        super().__init__(window)
        self.appendUICommands(*self.getUICommands())


class EffortViewerColumnPopupMenu(
    ColumnPopupMenuMixin, DynamicMenuThatGetsUICommandsFromViewer
):
    """Column header popup menu. Its columns follow the viewer's
    aggregation, so the header control refills it before it pops up."""

    def registerForMenuUpdate(self):
        pass


class AttachmentPopupMenu(Menu):
    def __init__(self, mainwindow, attachments, attachment_viewer):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.EditCut(viewer=attachment_viewer),
            uicommand.EditCopy(viewer=attachment_viewer),
            uicommand.EditPaste(viewer=attachment_viewer),
            None,
            uicommand.Edit(viewer=attachment_viewer),
            uicommand.Delete(viewer=attachment_viewer),
            None,
            uicommand.AddNote(viewer=attachment_viewer),
            uicommand.OpenAllNotes(viewer=attachment_viewer),
            None,
            uicommand.AttachmentOpen(
                viewer=attachment_viewer,
                attachments=attachments,
            ),
            None,
            uicommand.AttachmentNew(
                viewer=attachment_viewer,
                attachments=attachments,
            ),
        )
