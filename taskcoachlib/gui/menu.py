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

from taskcoachlib import operating_system
from taskcoachlib import patterns, persistence, help  # pylint: disable=W0622
from taskcoachlib.domain import task, base, category
from taskcoachlib.i18n import _
from pubsub import pub
from taskcoachlib.gui.newid import IdProvider
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

    def __len__(self):
        return self.GetMenuItemCount()

    def DestroyItem(self, menuItem):
        if menuItem.GetSubMenu():
            menuItem.GetSubMenu().clearMenu()
        self._window.Unbind(wx.EVT_MENU, id=menuItem.GetId())
        self._window.Unbind(wx.EVT_UPDATE_UI, id=menuItem.GetId())
        super().DestroyItem(menuItem)

    def clearMenu(self):
        """Remove all menu items."""
        for menuItem in self.MenuItems:
            self.DestroyItem(menuItem)
        for observer in self._observers:
            observer.removeInstance()
        self._observers = list()

    def accelerators(self):
        return self._accels

    def appendUICommand(self, uiCommand):
        cmd = uiCommand.addToMenu(self, self._window)
        self._accels.extend(uiCommand.accelerators())
        if isinstance(uiCommand, patterns.Observer):
            self._observers.append(uiCommand)
        return cmd

    def appendMenu(self, text, subMenu, bitmap=None):
        subMenuItem = wx.MenuItem(
            self, id=IdProvider.get(), text=text, subMenu=subMenu
        )
        if bitmap:
            subMenuItem.SetBitmap(
                wx.ArtProvider.GetBitmap(bitmap, wx.ART_MENU, (16, 16))
            )
        self._accels.extend(subMenu.accelerators())
        self.Append(subMenuItem)

    def invokeMenuItem(self, menuItem):
        """Programmatically invoke the menuItem. This is mainly for testing
        purposes."""
        self._window.ProcessEvent(
            wx.CommandEvent(
                wx.wxEVT_COMMAND_MENU_SELECTED, winid=menuItem.GetId()
            )
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

    def __init__(self, window, parentMenu=None, labelInParentMenu=""):
        """Initialize the menu. labelInParentMenu is needed to be able to
        find this menu in its parentMenu."""
        super().__init__(window)
        self._parentMenu = parentMenu
        self._labelInParentMenu = self.__GetLabelText(labelInParentMenu)
        self.registerForMenuUpdate()
        self.updateMenu()

    def registerForMenuUpdate(self):
        """Subclasses are responsible for binding an event to onUpdateMenu so
        that the menu gets a chance to update itself at the right time."""
        raise NotImplementedError

    def onUpdateMenu(self, newValue, sender):
        """This event handler should be called at the right times so that
        the menu has a chance to update itself."""
        try:  # Prepare for menu or window to be destroyed
            self.updateMenu()
        except RuntimeError:
            pass

    def onUpdateMenu_Deprecated(self, event=None):
        """This event handler should be called at the right times so that
        the menu has a chance to update itself."""
        # If this is called by wx, 'skip' the event so that other event
        # handlers get a chance too:
        if event and hasattr(event, "Skip"):
            event.Skip()
            if event.GetMenu() != self._parentMenu:
                return

        # FIXME: No RuntimeError similar classes in wxPython4, so
        # you must carefully check if the window already destroyed.
        try:  # Prepare for menu or window to be destroyed
            self.updateMenu()
        except RuntimeError:
            pass  # Menu or window may be destroyed

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
            myId = self.myId()
            if myId != wx.NOT_FOUND:
                self._parentMenu.Enable(myId, self.enabled())

    def myId(self):
        """Return the id of our menu item in the parent menu."""
        # I'd rather use wx.Menu.FindItem, but it seems that that
        # method currently does not work for menu items with accelerators
        # (wxPython 2.8.6 on Ubuntu). When that is fixed replace the 7
        # lines below with this one:
        # myId = self._parentMenu.FindItem(self._labelInParentMenu)
        for item in self._parentMenu.MenuItems:
            if (
                self.__GetLabelText(item.GetItemLabel())
                == self._labelInParentMenu
            ):
                return item.Id
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

    @staticmethod
    def __GetLabelText(menuText):
        """Remove accelerators from the menuText. This is necessary because on
        some platforms '&' is changed into '_' so menuTexts would compare
        different even though they are really the same."""
        return menuText.replace("&", "").replace("_", "")


class DynamicMenuThatGetsUICommandsFromViewer(DynamicMenu):
    def __init__(
        self, viewer, parentMenu=None, labelInParentMenu=""
    ):  # pylint: disable=W0621
        self._uiCommands = None
        super().__init__(viewer, parentMenu, labelInParentMenu)

    def registerForMenuUpdate(self):
        # Refill the menu whenever the menu is opened, because the menu might
        # depend on the status of the viewer:
        self._window.Bind(wx.EVT_MENU_OPEN, self.onUpdateMenu_Deprecated)

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
    def __init__(
        self, mainwindow, settings, iocontroller, viewerContainer, taskFile
    ):
        super().__init__()
        accels = list()
        for menu, text in [
            (
                FileMenu(mainwindow, settings, iocontroller, viewerContainer),
                _("&File"),
            ),
            (
                EditMenu(mainwindow, settings, iocontroller, viewerContainer),
                _("&Edit"),
            ),
            (
                ViewMenu(mainwindow, settings, viewerContainer, taskFile),
                _("&View"),
            ),
            (
                NewMenu(mainwindow, settings, taskFile, viewerContainer),
                _("&New"),
            ),
            (
                ActionMenu(mainwindow, settings, taskFile, viewerContainer),
                _("&Actions"),
            ),
            (HelpMenu(mainwindow, settings, iocontroller), _("&Help")),
        ]:
            self.Append(menu, text)
            accels.extend(menu.accelerators())
        mainwindow.SetAcceleratorTable(wx.AcceleratorTable(accels))


class FileMenu(Menu):
    def __init__(self, mainwindow, settings, iocontroller, viewerContainer):
        super().__init__(mainwindow)
        self.__settings = settings
        self.__iocontroller = iocontroller
        self.__recentFileUICommands = []
        self.__separator = None
        self.appendUICommands(
            uicommand.FileOpen(iocontroller=iocontroller),
            uicommand.FileMerge(iocontroller=iocontroller),
            uicommand.FileClose(iocontroller=iocontroller),
            None,
            uicommand.FileSave(iocontroller=iocontroller),
            uicommand.FileMergeDiskChanges(iocontroller=iocontroller),
            uicommand.FileSaveAs(iocontroller=iocontroller),
            uicommand.FileSaveSelection(
                iocontroller=iocontroller, viewer=viewerContainer
            ),
        )
        if not settings.getboolean("feature", "syncml"):
            self.appendUICommands(
                uicommand.FilePurgeDeletedItems(iocontroller=iocontroller)
            )
        self.appendUICommands(
            None,
            uicommand.FileSaveSelectedTaskAsTemplate(
                iocontroller=iocontroller, viewer=viewerContainer
            ),
            uicommand.FileImportTemplate(iocontroller=iocontroller),
            uicommand.FileEditTemplates(settings=settings),
            None,
            uicommand.PrintPageSetup(settings=settings),
            uicommand.PrintPreview(viewer=viewerContainer, settings=settings),
            uicommand.Print(viewer=viewerContainer, settings=settings),
            None,
        )
        self.appendMenu(_("&Import"), ImportMenu(mainwindow, iocontroller))
        self.appendMenu(
            _("&Export"),
            ExportMenu(mainwindow, iocontroller, settings),
            "export",
        )
        self.appendUICommands(
            None,
            uicommand.FileManageBackups(
                iocontroller=iocontroller, settings=settings
            ),
        )
        if settings.getboolean("feature", "syncml"):
            try:
                import taskcoachlib.syncml.core  # pylint: disable=W0612,W0404
            except ImportError:
                pass
            else:
                self.appendUICommands(
                    uicommand.FileSynchronize(
                        iocontroller=iocontroller, settings=settings
                    )
                )
        self.__recentFilesStartPosition = len(self)
        self.appendUICommands(None, uicommand.FileQuit())
        self._window.Bind(wx.EVT_MENU_OPEN, self.onOpenMenu)

    def onOpenMenu(self, event):
        if event.GetMenu() == self:
            self.__removeRecentFileMenuItems()
            self.__insertRecentFileMenuItems()
        event.Skip()

    def __insertRecentFileMenuItems(self):
        recentFiles = self.__settings.getlist("file", "recentfiles")
        if not recentFiles:
            return
        maximumNumberOfRecentFiles = self.__settings.getint(
            "file", "maxrecentfiles"
        )
        recentFiles = recentFiles[:maximumNumberOfRecentFiles]
        self.__separator = self.InsertSeparator(
            self.__recentFilesStartPosition
        )
        for index, recentFile in enumerate(recentFiles):
            recentFileNumber = (
                index + 1
            )  # Only computer nerds start counting at 0 :-)
            recentFileMenuPosition = (
                self.__recentFilesStartPosition + 1 + index
            )
            recentFileOpenUICommand = uicommand.RecentFileOpen(
                filename=recentFile,
                index=recentFileNumber,
                iocontroller=self.__iocontroller,
            )
            recentFileOpenUICommand.addToMenu(
                self, self._window, recentFileMenuPosition
            )
            self.__recentFileUICommands.append(recentFileOpenUICommand)

    def __removeRecentFileMenuItems(self):
        for recentFileUICommand in self.__recentFileUICommands:
            recentFileUICommand.removeFromMenu(self, self._window)
        self.__recentFileUICommands = []
        if self.__separator:
            self.Remove(self.__separator)
            self.__separator = None


class ExportMenu(Menu):
    def __init__(self, mainwindow, iocontroller, settings):
        super().__init__(mainwindow)
        kwargs = dict(iocontroller=iocontroller, settings=settings)
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
    def __init__(self, mainwindow, taskList, settings):
        self.settings = settings
        self.taskList = taskList
        super().__init__(mainwindow)

    def registerForMenuUpdate(self):
        pub.subscribe(self.onTemplatesSaved, "templates.saved")

    def onTemplatesSaved(self):
        self.onUpdateMenu(None, None)

    def updateMenuItems(self):
        self.clearMenu()
        self.fillMenu(self.getUICommands())

    def fillMenu(self, uiCommands):
        self.appendUICommands(*uiCommands)  # pylint: disable=W0142

    def getUICommands(self):
        path = self.settings.pathToTemplatesDir()
        commands = [
            uicommand.TaskNewFromTemplate(
                os.path.join(path, name),
                taskList=self.taskList,
                settings=self.settings,
            )
            for name in persistence.TemplateList(path).names()
        ]
        return commands


class EditMenu(Menu):
    def __init__(self, mainwindow, settings, iocontroller, viewerContainer):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.EditUndo(),
            uicommand.EditRedo(),
            None,
            uicommand.EditCut(viewer=viewerContainer, id=wx.ID_CUT),
            uicommand.EditCopy(viewer=viewerContainer, id=wx.ID_COPY),
            uicommand.EditPaste(),
            uicommand.EditPasteAsSubItem(viewer=viewerContainer),
            None,
            uicommand.Edit(viewer=viewerContainer, id=wx.ID_EDIT),
            uicommand.Delete(viewer=viewerContainer, id=wx.ID_DELETE),
            None,
        )
        # Leave sufficient room for command names in the Undo and Redo menu
        # items:
        self.appendMenu(
            _("&Select") + " " * 50, SelectMenu(mainwindow, viewerContainer)
        )
        self.appendUICommands(None, uicommand.EditPreferences(settings))
        if settings.getboolean("feature", "syncml"):
            try:
                import taskcoachlib.syncml.core  # pylint: disable=W0612,W0404
            except ImportError:
                pass
            else:
                self.appendUICommands(
                    uicommand.EditSyncPreferences(
                        mainwindow=mainwindow, iocontroller=iocontroller
                    )
                )


class SelectMenu(Menu):
    def __init__(self, mainwindow, viewerContainer):
        super().__init__(mainwindow)
        kwargs = dict(viewer=viewerContainer)
        # pylint: disable=W0142
        self.appendUICommands(
            uicommand.SelectAll(**kwargs), uicommand.ClearSelection(**kwargs)
        )


activateNextViewerId = wx.NewId()
activatePreviousViewerId = wx.NewId()


class ViewMenu(Menu):
    def __init__(self, mainwindow, settings, viewerContainer, taskFile):
        super().__init__(mainwindow)
        self.appendMenu(
            _("&New viewer"),
            ViewViewerMenu(mainwindow, settings, viewerContainer, taskFile),
            "viewnewviewer",
        )
        activateNextViewer = uicommand.ActivateViewer(
            viewer=viewerContainer,
            menuText=_("&Activate next viewer\tCtrl+PgDn"),
            helpText=help.viewNextViewer,
            forward=True,
            bitmap="activatenextviewer",
            id=activateNextViewerId,
        )
        activatePreviousViewer = uicommand.ActivateViewer(
            viewer=viewerContainer,
            menuText=_("Activate &previous viewer\tCtrl+PgUp"),
            helpText=help.viewPreviousViewer,
            forward=False,
            bitmap="activatepreviousviewer",
            id=activatePreviousViewerId,
        )
        self.appendUICommands(
            activateNextViewer,
            activatePreviousViewer,
            uicommand.RenameViewer(viewer=viewerContainer),
            None,
        )
        self.appendMenu(_("&Mode"), ModeMenu(mainwindow, self, _("&Mode")))
        self.appendMenu(
            _("&Filter"), FilterMenu(mainwindow, self, _("&Filter"))
        )
        self.appendMenu(_("&Sort"), SortMenu(mainwindow, self, _("&Sort")))
        self.appendMenu(
            _("&Columns"), ColumnMenu(mainwindow, self, _("&Columns"))
        )
        self.appendMenu(
            _("&Rounding"), RoundingMenu(mainwindow, self, _("&Rounding"))
        )
        self.appendUICommands(None)
        self.appendMenu(
            _("&Tree options"),
            ViewTreeOptionsMenu(mainwindow, viewerContainer),
            "treeview",
        )
        self.appendUICommands(None)
        self.appendMenu(_("T&oolbar"), ToolBarMenu(mainwindow, settings))
        self.appendUICommands(
            uicommand.UICheckCommand(
                settings=settings,
                menuText=_("Status&bar"),
                helpText=_("Show/hide status bar"),
                setting="statusbar",
            )
        )


class ViewViewerMenu(Menu):
    def __init__(self, mainwindow, settings, viewerContainer, taskFile):
        super().__init__(mainwindow)
        ViewViewer = uicommand.ViewViewer
        kwargs = dict(
            viewer=viewerContainer, taskFile=taskFile, settings=settings
        )
        # pylint: disable=W0142
        viewViewerCommands = [
            ViewViewer(
                menuText=_("&Task"),
                helpText=_("Open a new tab with a viewer that displays tasks"),
                viewerClass=taskcoachlib.gui.viewer.TaskViewer,
                **kwargs
            ),
            ViewViewer(
                menuText=_("Task &statistics"),
                helpText=_(
                    "Open a new tab with a viewer that displays task statistics"
                ),
                viewerClass=taskcoachlib.gui.viewer.TaskStatsViewer,
                **kwargs
            ),
            ViewViewer(
                menuText=_("Task &square map"),
                helpText=_(
                    "Open a new tab with a viewer that displays tasks in a square map"
                ),
                viewerClass=taskcoachlib.gui.viewer.SquareTaskViewer,
                **kwargs
            ),
            ViewViewer(
                menuText=_("T&imeline"),
                helpText=_(
                    "Open a new tab with a viewer that displays a timeline of tasks and effort"
                ),
                viewerClass=taskcoachlib.gui.viewer.TimelineViewer,
                **kwargs
            ),
            ViewViewer(
                menuText=_("&Calendar"),
                helpText=_(
                    "Open a new tab with a viewer that displays tasks in a calendar"
                ),
                viewerClass=taskcoachlib.gui.viewer.CalendarViewer,
                **kwargs
            ),
            ViewViewer(
                menuText=_("&Hierarchical calendar"),
                helpText=_(
                    "Open a new tab with a viewer that displays task hierarchy in a calendar"
                ),
                viewerClass=taskcoachlib.gui.viewer.HierarchicalCalendarViewer,
                **kwargs
            ),
            ViewViewer(
                menuText=_("&Category"),
                helpText=_(
                    "Open a new tab with a viewer that displays categories"
                ),
                viewerClass=taskcoachlib.gui.viewer.CategoryViewer,
                **kwargs
            ),
            ViewViewer(
                menuText=_("&Effort"),
                helpText=_(
                    "Open a new tab with a viewer that displays efforts"
                ),
                viewerClass=taskcoachlib.gui.viewer.EffortViewer,
                **kwargs
            ),
            uicommand.ViewEffortViewerForSelectedTask(
                menuText=_("Eff&ort for selected task(s)"),
                helpText=_(
                    "Open a new tab with a viewer that displays efforts for the selected task"
                ),
                viewerClass=taskcoachlib.gui.viewer.EffortViewer,
                **kwargs
            ),
            ViewViewer(
                menuText=_("&Note"),
                helpText=_("Open a new tab with a viewer that displays notes"),
                viewerClass=taskcoachlib.gui.viewer.NoteViewer,
                **kwargs
            ),
        ]
        try:
            import igraph
        except ImportError:
            pass
        else:
            viewViewerCommands.append(
                ViewViewer(
                    menuText=_("&Dependency Graph"),
                    helpText=_(
                        "Open a new tab with a viewer that dependencies between weighted tasks over time"
                    ),
                    viewerClass=taskcoachlib.gui.viewer.TaskInterdepsViewer,
                    **kwargs
                )
            )
        self.appendUICommands(*viewViewerCommands)


class ViewTreeOptionsMenu(Menu):
    def __init__(self, mainwindow, viewerContainer):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.ViewExpandAll(viewer=viewerContainer),
            uicommand.ViewCollapseAll(viewer=viewerContainer),
        )


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
    def __init__(self, mainwindow, settings):
        super().__init__(mainwindow)
        toolbarCommands = []
        for value, menuText, helpText in [
            (None, _("&Hide"), _("Hide the toolbar")),
            (
                (16, 16),
                _("&Small images"),
                _("Small images (16x16) on the toolbar"),
            ),
            (
                (22, 22),
                _("&Medium-sized images"),
                _("Medium-sized images (22x22) on the toolbar"),
            ),
            (
                (32, 32),
                _("&Large images"),
                _("Large images (32x32) on the toolbar"),
            ),
        ]:
            toolbarCommands.append(
                uicommand.UIRadioCommand(
                    settings=settings,
                    setting="toolbar",
                    value=value,
                    menuText=menuText,
                    helpText=helpText,
                )
            )
        # pylint: disable=W0142
        self.appendUICommands(*toolbarCommands)


class NewMenu(Menu):
    def __init__(self, mainwindow, settings, taskFile, viewerContainer):
        super().__init__(mainwindow)
        tasks = taskFile.tasks()
        self.appendUICommands(
            uicommand.TaskNew(taskList=tasks, settings=settings),
            uicommand.NewTaskWithSelectedTasksAsPrerequisites(
                taskList=tasks, viewer=viewerContainer, settings=settings
            ),
            uicommand.NewTaskWithSelectedTasksAsDependencies(
                taskList=tasks, viewer=viewerContainer, settings=settings
            ),
        )
        self.appendMenu(
            _("New task from &template"),
            TaskTemplateMenu(mainwindow, taskList=tasks, settings=settings),
            "newtmpl",
        )
        self.appendUICommands(
            None,
            uicommand.EffortNew(
                viewer=viewerContainer,
                effortList=taskFile.efforts(),
                taskList=tasks,
                settings=settings,
            ),
            uicommand.CategoryNew(
                categories=taskFile.categories(), settings=settings
            ),
            uicommand.NoteNew(notes=taskFile.notes(), settings=settings),
            None,
            uicommand.NewSubItem(viewer=viewerContainer),
        )


class ActionMenu(Menu):
    def __init__(self, mainwindow, settings, taskFile, viewerContainer):
        super().__init__(mainwindow)
        tasks = taskFile.tasks()
        efforts = taskFile.efforts()
        categories = taskFile.categories()
        # Generic actions, applicable to all/most domain objects:
        self.appendUICommands(
            uicommand.AddAttachment(viewer=viewerContainer, settings=settings),
            uicommand.OpenAllAttachments(
                viewer=viewerContainer, settings=settings
            ),
            None,
            uicommand.AddNote(viewer=viewerContainer, settings=settings),
            uicommand.OpenAllNotes(viewer=viewerContainer, settings=settings),
            None,
            uicommand.Mail(viewer=viewerContainer),
            None,
        )
        self.appendMenu(
            _("&Toggle category"),
            ToggleCategoryMenu(
                mainwindow, categories=categories, viewer=viewerContainer
            ),
            "folder_blue_arrow_icon",
        )
        # Start of task specific actions:
        self.appendUICommands(
            None,
            uicommand.TaskMarkInactive(
                settings=settings, viewer=viewerContainer
            ),
            uicommand.TaskMarkActive(
                settings=settings, viewer=viewerContainer
            ),
            uicommand.TaskMarkCompleted(
                settings=settings, viewer=viewerContainer
            ),
            None,
        )
        self.appendMenu(
            _("Change task &priority"),
            TaskPriorityMenu(mainwindow, tasks, viewerContainer),
            "incpriority",
        )
        self.appendUICommands(
            None,
            uicommand.EffortStart(viewer=viewerContainer, taskList=tasks),
            uicommand.EffortStop(
                viewer=viewerContainer, effortList=efforts, taskList=tasks
            ),
            uicommand.EditTrackedTasks(taskList=tasks, settings=settings),
        )


class TaskPriorityMenu(Menu):
    def __init__(self, mainwindow, taskList, viewerContainer):
        super().__init__(mainwindow)
        kwargs = dict(taskList=taskList, viewer=viewerContainer)
        # pylint: disable=W0142
        self.appendUICommands(
            uicommand.TaskIncPriority(**kwargs),
            uicommand.TaskDecPriority(**kwargs),
            uicommand.TaskMaxPriority(**kwargs),
            uicommand.TaskMinPriority(**kwargs),
        )


class HelpMenu(Menu):
    def __init__(self, mainwindow, settings, iocontroller):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.Help(),
            uicommand.FAQ(),
            uicommand.Tips(settings=settings),
            uicommand.Anonymize(iocontroller=iocontroller),
            None,
            uicommand.RequestSupport(),
            uicommand.ReportBug(),
            uicommand.RequestFeature(),
            None,
            uicommand.HelpTranslate(),
            None,
            uicommand.HelpAbout(),
            uicommand.CheckForUpdate(settings=settings),
            uicommand.HelpLicense(),
        )


class TaskBarMenu(Menu):
    def __init__(self, taskBarIcon, settings, taskFile, viewer):
        super().__init__(taskBarIcon)
        tasks = taskFile.tasks()
        efforts = taskFile.efforts()
        self.appendUICommands(
            uicommand.TaskNew(taskList=tasks, settings=settings)
        )
        self.appendMenu(
            _("New task from &template"),
            TaskTemplateMenu(taskBarIcon, taskList=tasks, settings=settings),
            "newtmpl",
        )
        self.appendUICommands(None)  # Separator
        self.appendUICommands(
            uicommand.EffortNew(
                effortList=efforts, taskList=tasks, settings=settings
            ),
            uicommand.CategoryNew(
                categories=taskFile.categories(), settings=settings
            ),
            uicommand.NoteNew(notes=taskFile.notes(), settings=settings),
        )
        self.appendUICommands(None)  # Separator
        label = _("&Start tracking effort")
        self.appendMenu(
            label,
            StartEffortForTaskMenu(
                taskBarIcon, base.filter.DeletedFilter(tasks), self, label
            ),
            "clock_icon",
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
                self.onUpdateMenu_Deprecated,
                eventType=eventType,
                eventSource=self.categories,
            )
        patterns.Publisher().registerObserver(
            self.onUpdateMenu_Deprecated,
            eventType=category.Category.subjectChangedEventType(),
        )

    def updateMenuItems(self):
        self.clearMenu()
        self.addMenuItemsForCategories(self.categories.rootItems(), self)

    def addMenuItemsForCategories(self, categories, menu):
        # pylint: disable=W0621
        categories = categories[:]
        categories.sort(key=lambda category: category.subject().lower())
        for category in categories:
            uiCommand = uicommand.ToggleCategory(
                category=category, viewer=self.viewer
            )
            uiCommand.addToMenu(menu, self._window)
        categoriesWithChildren = [
            category for category in categories if category.children()
        ]
        if categoriesWithChildren:
            menu.AppendSeparator()
            for category in categoriesWithChildren:
                subMenu = Menu(self._window)
                self.addMenuItemsForCategories(category.children(), subMenu)
                menu.AppendSubMenu(subMenu, self.subMenuLabel(category))

    @staticmethod
    def subMenuLabel(category):  # pylint: disable=W0621
        return _("%s (subcategories)") % category.subject()

    def enabled(self):
        return bool(self.categories)


class StartEffortForTaskMenu(DynamicMenu):
    def __init__(
        self, taskBarIcon, tasks, parentMenu=None, labelInParentMenu=""
    ):
        self.tasks = tasks
        super().__init__(taskBarIcon, parentMenu, labelInParentMenu)

    def registerForMenuUpdate(self):
        for eventType in (
            self.tasks.addItemEventType(),
            self.tasks.removeItemEventType(),
        ):
            patterns.Publisher().registerObserver(
                self.onUpdateMenu_Deprecated,
                eventType=eventType,
                eventSource=self.tasks,
            )
        for eventType in (
            task.Task.subjectChangedEventType(),
            task.Task.trackingChangedEventType(),
            task.Task.plannedStartDateTimeChangedEventType(),
            task.Task.dueDateTimeChangedEventType(),
            task.Task.actualStartDateTimeChangedEventType(),
            task.Task.completionDateTimeChangedEventType(),
        ):
            if eventType.startswith("pubsub"):
                pub.subscribe(self.onUpdateMenu, eventType)
            else:
                patterns.Publisher().registerObserver(
                    self.onUpdateMenu_Deprecated, eventType
                )

    def updateMenuItems(self):
        self.clearMenu()
        trackableRootTasks = self._trackableRootTasks()
        trackableRootTasks.sort(key=lambda task: task.subject())
        for trackableRootTask in trackableRootTasks:
            self.addMenuItemForTask(trackableRootTask, self)

    def addMenuItemForTask(self, task, menu):  # pylint: disable=W0621
        uiCommand = uicommand.EffortStartForTask(
            task=task, taskList=self.tasks
        )
        uiCommand.addToMenu(menu, self._window)
        trackableChildren = [
            child
            for child in task.children()
            if child in self.tasks and not child.completed()
        ]
        if trackableChildren:
            trackableChildren.sort(key=lambda child: child.subject())
            subMenu = Menu(self._window)
            for child in trackableChildren:
                self.addMenuItemForTask(child, subMenu)
            menu.AppendSubMenu(subMenu, _("%s (subtasks)") % task.subject())

    def enabled(self):
        return bool(self._trackableRootTasks())

    def _trackableRootTasks(self):
        return [
            rootTask
            for rootTask in self.tasks.rootItems()
            if not rootTask.completed()
        ]


class TaskPopupMenu(Menu):
    def __init__(
        self, mainwindow, settings, tasks, efforts, categories, taskViewer
    ):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.EditCut(viewer=taskViewer),
            uicommand.EditCopy(viewer=taskViewer),
            uicommand.EditPaste(),
            uicommand.EditPasteAsSubItem(viewer=taskViewer),
            None,
            uicommand.Edit(viewer=taskViewer),
            uicommand.Delete(viewer=taskViewer),
            None,
            uicommand.AddAttachment(viewer=taskViewer, settings=settings),
            uicommand.OpenAllAttachments(viewer=taskViewer, settings=settings),
            None,
            uicommand.AddNote(viewer=taskViewer, settings=settings),
            uicommand.OpenAllNotes(viewer=taskViewer, settings=settings),
            None,
            uicommand.Mail(viewer=taskViewer),
            None,
        )
        self.appendMenu(
            _("&Toggle category"),
            ToggleCategoryMenu(
                mainwindow, categories=categories, viewer=taskViewer
            ),
            "folder_blue_arrow_icon",
        )
        self.appendUICommands(
            None,
            uicommand.TaskMarkInactive(settings=settings, viewer=taskViewer),
            uicommand.TaskMarkActive(settings=settings, viewer=taskViewer),
            uicommand.TaskMarkCompleted(settings=settings, viewer=taskViewer),
            None,
        )
        self.appendMenu(
            _("&Priority"),
            TaskPriorityMenu(mainwindow, tasks, taskViewer),
            "incpriority",
        )
        self.appendUICommands(
            None,
            uicommand.EffortNew(
                viewer=taskViewer,
                effortList=efforts,
                taskList=tasks,
                settings=settings,
            ),
            uicommand.EffortStart(viewer=taskViewer, taskList=tasks),
            uicommand.EffortStop(
                viewer=taskViewer, effortList=efforts, taskList=tasks
            ),
            None,
            uicommand.NewSubItem(viewer=taskViewer),
        )


class EffortPopupMenu(Menu):
    def __init__(self, mainwindow, tasks, efforts, settings, effortViewer):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.EditCut(viewer=effortViewer),
            uicommand.EditCopy(viewer=effortViewer),
            uicommand.EditPaste(),
            None,
            uicommand.Edit(viewer=effortViewer),
            uicommand.Delete(viewer=effortViewer),
            None,
            uicommand.EffortNew(
                viewer=effortViewer,
                effortList=efforts,
                taskList=tasks,
                settings=settings,
            ),
            uicommand.EffortStartForEffort(
                viewer=effortViewer, taskList=tasks
            ),
            uicommand.EffortStop(
                viewer=effortViewer, effortList=efforts, taskList=tasks
            ),
        )


class CategoryPopupMenu(Menu):
    def __init__(
        self, mainwindow, settings, taskFile, categoryViewer, localOnly=False
    ):
        super().__init__(mainwindow)
        categories = categoryViewer.presentation()
        tasks = taskFile.tasks()
        notes = taskFile.notes()
        self.appendUICommands(
            uicommand.EditCut(viewer=categoryViewer),
            uicommand.EditCopy(viewer=categoryViewer),
            uicommand.EditPaste(),
            uicommand.EditPasteAsSubItem(viewer=categoryViewer),
            None,
            uicommand.Edit(viewer=categoryViewer),
            uicommand.Delete(viewer=categoryViewer),
            None,
            uicommand.AddAttachment(viewer=categoryViewer, settings=settings),
            uicommand.OpenAllAttachments(
                viewer=categoryViewer, settings=settings
            ),
            None,
            uicommand.AddNote(viewer=categoryViewer, settings=settings),
            uicommand.OpenAllNotes(viewer=categoryViewer, settings=settings),
            None,
            uicommand.Mail(viewer=categoryViewer),
        )
        if not localOnly:
            self.appendUICommands(
                None,
                uicommand.NewTaskWithSelectedCategories(
                    taskList=tasks,
                    settings=settings,
                    categories=categories,
                    viewer=categoryViewer,
                ),
                uicommand.NewNoteWithSelectedCategories(
                    notes=notes,
                    settings=settings,
                    categories=categories,
                    viewer=categoryViewer,
                ),
            )
        self.appendUICommands(
            None, uicommand.NewSubItem(viewer=categoryViewer)
        )


class NotePopupMenu(Menu):
    def __init__(self, mainwindow, settings, categories, noteViewer):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.EditCut(viewer=noteViewer),
            uicommand.EditCopy(viewer=noteViewer),
            uicommand.EditPaste(),
            uicommand.EditPasteAsSubItem(viewer=noteViewer),
            None,
            uicommand.Edit(viewer=noteViewer),
            uicommand.Delete(viewer=noteViewer),
            None,
            uicommand.AddAttachment(viewer=noteViewer, settings=settings),
            uicommand.OpenAllAttachments(viewer=noteViewer, settings=settings),
            None,
            uicommand.Mail(viewer=noteViewer),
            None,
        )
        self.appendMenu(
            _("&Toggle category"),
            ToggleCategoryMenu(
                mainwindow, categories=categories, viewer=noteViewer
            ),
            "folder_blue_arrow_icon",
        )
        self.appendUICommands(None, uicommand.NewSubItem(viewer=noteViewer))


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
            uicommand.HideCurrentColumn(viewer=self._window),
            None,
        ] + self._window.getColumnUICommands()


class ColumnPopupMenu(ColumnPopupMenuMixin, Menu):
    """Column header popup menu."""

    def __init__(self, window):
        super().__init__(window)
        wx.CallAfter(self.appendUICommands, *self.getUICommands())

    def appendUICommands(self, *args, **kwargs):
        # Prepare for PyDeadObjectError since we're called from wx.CallAfter
        try:
            super().appendUICommands(*args, **kwargs)
        except RuntimeError:
            pass


class EffortViewerColumnPopupMenu(
    ColumnPopupMenuMixin, DynamicMenuThatGetsUICommandsFromViewer
):
    """Column header popup menu."""

    def registerForMenuUpdate(self):
        pub.subscribe(self.onChangeAggregation, "effortviewer.aggregation")

    def onChangeAggregation(self):
        self.onUpdateMenu(None, None)


class AttachmentPopupMenu(Menu):
    def __init__(self, mainwindow, settings, attachments, attachmentViewer):
        super().__init__(mainwindow)
        self.appendUICommands(
            uicommand.EditCut(viewer=attachmentViewer),
            uicommand.EditCopy(viewer=attachmentViewer),
            uicommand.EditPaste(),
            None,
            uicommand.Edit(viewer=attachmentViewer),
            uicommand.Delete(viewer=attachmentViewer),
            None,
            uicommand.AddNote(viewer=attachmentViewer, settings=settings),
            uicommand.OpenAllNotes(viewer=attachmentViewer, settings=settings),
            None,
            uicommand.AttachmentOpen(
                viewer=attachmentViewer,
                attachments=attachments,
                settings=settings,
            ),
        )
