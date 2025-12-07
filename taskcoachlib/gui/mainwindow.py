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

from taskcoachlib import (
    application,
    meta,
    widgets,
    operating_system,
)  # pylint: disable=W0622
from taskcoachlib.gui import (
    viewer,
    toolbar,
    uicommand,
    remindercontroller,
    artprovider,
    windowdimensionstracker,
    idlecontroller,
)
from taskcoachlib.gui.dialog.iphone import IPhoneSyncTypeDialog
from taskcoachlib.gui.dialog.xfce4warning import XFCE4WarningDialog
from taskcoachlib.gui.dialog.editor import Editor
from taskcoachlib.gui.iphone import IPhoneSyncFrame
from taskcoachlib.i18n import _
from taskcoachlib.powermgt import PowerStateMixin
from taskcoachlib.help.balloontips import BalloonTipManager
from pubsub import pub
from taskcoachlib.config.settings import Settings
import wx.lib.agw.aui as aui
import wx, ctypes


def turn_on_double_buffering_on_windows(window):
    # This has actually an adverse effect when Aero is enabled...
    from ctypes import wintypes

    dll = ctypes.WinDLL("dwmapi.dll")
    ret = wintypes.BOOL()
    if dll.DwmIsCompositionEnabled(ctypes.pointer(ret)) == 0 and ret.value:
        return
    import win32gui, win32con  # pylint: disable=F0401

    exstyle = win32gui.GetWindowLong(window.GetHandle(), win32con.GWL_EXSTYLE)
    exstyle |= win32con.WS_EX_COMPOSITED
    win32gui.SetWindowLong(window.GetHandle(), win32con.GWL_EXSTYLE, exstyle)


class MainWindow(
    PowerStateMixin,
    BalloonTipManager,
    widgets.AuiManagedFrameWithDynamicCenterPane,
):
    def __init__(
        self, iocontroller, taskFile, settings: Settings, *args, **kwargs
    ):
        # Initialize with valid default size to prevent GTK warnings
        # The WindowDimensionsTracker will set the actual saved size/position
        if 'size' not in kwargs:
            kwargs['size'] = (800, 600)
        super().__init__(None, -1, "", *args, **kwargs)
        # This prevents the viewers from flickering on Windows 7 when refreshed:
        if operating_system.isWindows7_OrNewer():
            turn_on_double_buffering_on_windows(self)
        self.__dimensions_tracker = (
            windowdimensionstracker.WindowDimensionsTracker(self, settings)
        )
        self.iocontroller = iocontroller
        self.taskFile = taskFile
        self.settings = settings
        self.__filename = None
        self.__dirty = False
        self.__shutdown = False
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.Bind(wx.EVT_ICONIZE, self.onIconify)
        self.Bind(wx.EVT_SIZE, self.onResize)
        self._create_window_components()  # Not private for test purposes
        self.__init_window_components()
        self.__init_window()
        self.__register_for_window_component_changes()

        if settings.getboolean("feature", "syncml"):
            try:
                import taskcoachlib.syncml.core  # pylint: disable=W0612,W0404
            except ImportError:
                if settings.getboolean("syncml", "showwarning"):
                    dlg = widgets.SyncMLWarningDialog(self)
                    try:
                        if dlg.ShowModal() == wx.ID_OK:
                            settings.setboolean("syncml", "showwarning", False)
                    finally:
                        dlg.Destroy()

        self.bonjourRegister = None
        self.bonjourAcceptor = None
        self._registerBonjour()
        pub.subscribe(self._registerBonjour, "settings.feature.iphone")

        self._idleController = idlecontroller.IdleController(
            self, self.settings, self.taskFile.efforts()
        )

        wx.CallAfter(self.checkXFCE4)

    def _registerBonjour(self, value=True):
        if self.bonjourRegister is not None:
            self.bonjourRegister.stop()
            self.bonjourAcceptor.close()
            self.bonjourRegister = self.bonjourAcceptor = None

        if self.settings.getboolean("feature", "iphone"):
            # pylint: disable=W0612,W0404,W0702
            try:
                import zeroconf  # Check if zeroconf library is available
                from taskcoachlib.iphone import (
                    IPhoneAcceptor,
                    BonjourServiceRegister,
                )

                acceptor = IPhoneAcceptor(
                    self, self.settings, self.iocontroller
                )

                def success(reader):
                    self.bonjourRegister = reader
                    self.bonjourAcceptor = acceptor

                def error(reason):
                    acceptor.close()
                    wx.MessageBox(reason.getErrorMessage(), _("Error"), wx.OK)

                BonjourServiceRegister(
                    self.settings, acceptor.port
                ).addCallbacks(success, error)
            except Exception:
                from taskcoachlib.gui.dialog.iphone import IPhoneBonjourDialog

                dlg = IPhoneBonjourDialog(self, wx.ID_ANY, _("Warning"))
                try:
                    dlg.ShowModal()
                finally:
                    dlg.Destroy()

    def checkXFCE4(self):
        if operating_system.isGTK():
            mon = application.Application().sessionMonitor
            if (
                mon is not None
                and self.settings.getboolean("feature", "usesm2")
                and self.settings.getboolean("feature", "showsmwarning")
                and mon.vendor == "xfce4-session"
            ):
                dlg = XFCE4WarningDialog(self, self.settings)
                dlg.Show()

    def setShutdownInProgress(self):
        self.__shutdown = True

    def _create_window_components(self):  # Not private for test purposes
        # Freeze to prevent flickering during viewer creation
        self.Freeze()
        try:
            self._create_viewer_container()
            viewer.addViewers(self.viewer, self.taskFile, self.settings)
            self._create_status_bar()
            self.__create_menu_bar()
            self.__create_reminder_controller()
        finally:
            self.Thaw()
        wx.CallAfter(self.viewer.componentsCreated)

    def _create_viewer_container(self):  # Not private for test purposes
        # pylint: disable=W0201
        self.viewer = viewer.ViewerContainer(self, self.settings)

    def _create_status_bar(self):
        from taskcoachlib.gui import status  # pylint: disable=W0404

        self.SetStatusBar(status.StatusBar(self, self.viewer))

    def __create_menu_bar(self):
        from taskcoachlib.gui import menu  # pylint: disable=W0404

        self.SetMenuBar(
            menu.MainMenu(
                self,
                self.settings,
                self.iocontroller,
                self.viewer,
                self.taskFile,
            )
        )

    def __create_reminder_controller(self):
        # pylint: disable=W0201
        self.reminderController = remindercontroller.ReminderController(
            self, self.taskFile.tasks(), self.taskFile.efforts(), self.settings
        )

    def addPane(self, page, caption, floating=False):  # pylint: disable=W0221
        name = page.settingsSection()
        super().addPane(page, caption, name, floating=floating)

    def __init_window(self):
        self.__filename = self.taskFile.filename()
        self.__setTitle()
        self.SetIcons(artprovider.iconBundle("taskcoach"))
        self.displayMessage(
            _("Welcome to %(name)s version %(version)s")
            % {"name": meta.name, "version": meta.version},
            pane=1,
        )

    def __init_window_components(self):
        # Freeze to prevent flickering during AUI layout restoration
        self.Freeze()

        try:
            self.showToolBar(self.settings.getvalue("view", "toolbar"))

            # We use CallAfter because otherwise the statusbar will appear at the
            # top of the window when it is initially hidden and later shown.
            wx.CallAfter(
                self.showStatusBar, self.settings.getboolean("view", "statusbar")
            )
            self.__restore_perspective()
        finally:
            self.Thaw()

        # Note: Window position/size tracking uses debouncing to handle spurious
        # events from AUI LoadPerspective() and GTK window realization.
        # Events are bound immediately in __init__, no manual start needed.

    def __restore_perspective(self):
        perspective = self.settings.get("view", "perspective")
        for viewer_type in viewer.viewerTypes():
            if self.__perspective_and_settings_viewer_count_differ(
                viewer_type
            ):
                # Different viewer counts may happen when the name of a viewer
                # is changed between versions
                perspective = ""
                break

        try:
            self.manager.LoadPerspective(perspective)
        except ValueError as reason:
            # This has been reported to happen. Don't know why. Keep going
            # if it does.
            wx.MessageBox(
                _(
                    """Couldn't restore the pane layout from TaskCoach.ini:
%s

The default pane layout will be used.

If this happens again, please make a copy of your TaskCoach.ini file """
                    """before closing the program, open a bug report, and attach the """
                    """copied TaskCoach.ini file to the bug report."""
                )
                % reason,
                _("%s settings error") % meta.name,
                style=wx.OK | wx.ICON_ERROR,
            )
            self.manager.LoadPerspective("")

        for pane in self.manager.GetAllPanes():
            # Prevent zombie panes by making sure all panes are visible
            if not pane.IsShown():
                pane.Show()
            # Ignore the titles that are saved in the perspective, they may be
            # incorrect when the user changes translation:
            if hasattr(pane.window, "title"):
                pane.Caption(pane.window.title())
        self.manager.Update()

    def __perspective_and_settings_viewer_count_differ(self, viewer_type):
        perspective = self.settings.get("view", "perspective")
        perspective_viewer_count = perspective.count("name=%s" % viewer_type)
        settings_viewer_count = self.settings.getint(
            "view", "%scount" % viewer_type
        )
        return perspective_viewer_count != settings_viewer_count

    def __register_for_window_component_changes(self):
        pub.subscribe(self.__onFilenameChanged, "taskfile.filenameChanged")
        pub.subscribe(self.__onDirtyChanged, "taskfile.dirty")
        pub.subscribe(self.__onDirtyChanged, "taskfile.clean")
        pub.subscribe(self.showStatusBar, "settings.view.statusbar")
        pub.subscribe(self.showToolBar, "settings.view.toolbar")
        self.Bind(aui.EVT_AUI_PANE_CLOSE, self.onCloseToolBar)

    def __onFilenameChanged(self, filename):
        self.__filename = filename
        self.__setTitle()

    def __onDirtyChanged(self, taskFile):
        self.__dirty = taskFile.isDirty()
        self.__setTitle()

    def __setTitle(self):
        title = meta.name
        if self.__filename:
            title += " - %s" % self.__filename
        if self.__dirty:
            title += " *"
        self.SetTitle(title)

    def displayMessage(self, message, pane=0):
        statusBar = self.GetStatusBar()
        if statusBar:
            statusBar.SetStatusText(message, pane)

    def save_settings(self):
        self.__save_viewer_counts()
        self.__save_perspective()
        self.__save_position()

    def __save_viewer_counts(self):
        """Save the number of viewers for each viewer type."""
        for viewer_type in viewer.viewerTypes():

            if hasattr(self, "viewer"):
                count = len(
                    [
                        v
                        for v in self.viewer
                        if v.__class__.__name__.lower() == viewer_type
                    ]
                )
            else:
                count = 0
            self.settings.set("view", viewer_type + "count", str(count))

    def __save_perspective(self):
        perspective = self.manager.SavePerspective()
        self.settings.set("view", "perspective", perspective)

    def __save_position(self):
        self.__dimensions_tracker.save_position()

    def closeEditors(self):
        for child in self.GetChildren():
            if isinstance(child, Editor):
                child.Close()

    def onClose(self, event):
        self.closeEditors()

        if self.__shutdown:
            # UnInit AUI manager before window destruction to avoid
            # wxAssertionError about pushed event handlers
            self.manager.UnInit()
            event.Skip()
            return
        if event.CanVeto() and self.settings.getboolean(
            "window", "hidewhenclosed"
        ):
            event.Veto()
            self.Iconize()
        else:
            if application.Application().quitApplication():
                # UnInit AUI manager before window destruction to avoid
                # wxAssertionError about pushed event handlers
                self.manager.UnInit()
                event.Skip()
                self.taskFile.stop()
                self._idleController.stop()

    def restore(self, event):  # pylint: disable=W0613
        if self.settings.getboolean("window", "maximized"):
            self.Maximize()
        self.Iconize(False)
        self.Show()
        self.Raise()
        self.Refresh()

    def onIconify(self, event):
        if event.IsIconized() and self.settings.getboolean(
            "window", "hidewheniconized"
        ):
            self.Hide()
        else:
            event.Skip()

    def onResize(self, event):
        currentToolbar = self.manager.GetPane("toolbar")
        if currentToolbar.IsOk():
            currentToolbar.window.SetSize((event.GetSize().GetWidth(), -1))
            currentToolbar.window.SetMinSize((event.GetSize().GetWidth(), 42))
        event.Skip()

    def showStatusBar(self, value=True):
        # FIXME: First hiding the statusbar, then hiding the toolbar, then
        # showing the statusbar puts it in the wrong place (only on Linux?)
        statusBar = self.GetStatusBar()
        if statusBar:
            statusBar.Show(value)
            self.SendSizeEvent()

    def createToolBarUICommands(self):
        """UI commands to put on the toolbar of this window."""
        uiCommands = [
            uicommand.FileOpen(iocontroller=self.iocontroller),
            uicommand.FileSave(iocontroller=self.iocontroller),
            uicommand.FileMergeDiskChanges(iocontroller=self.iocontroller),
            uicommand.Print(viewer=self.viewer, settings=self.settings),
            None,
            uicommand.EditUndo(),
            uicommand.EditRedo(),
        ]
        uiCommands.extend(
            [
                None,
                uicommand.EffortStartButton(taskList=self.taskFile.tasks()),
                uicommand.EffortStop(
                    viewer=self.viewer,
                    effortList=self.taskFile.efforts(),
                    taskList=self.taskFile.tasks(),
                ),
            ]
        )
        return uiCommands

    def getToolBarPerspective(self):
        return self.settings.get("view", "toolbarperspective")

    def saveToolBarPerspective(self, perspective):
        self.settings.set("view", "toolbarperspective", perspective)

    def showToolBar(self, value):
        currentToolbar = self.manager.GetPane("toolbar")
        if currentToolbar.IsOk():
            self.manager.DetachPane(currentToolbar.window)
            currentToolbar.window.Destroy()
        if value:
            bar = toolbar.MainToolBar(self, self.settings, size=value)
            self.manager.AddPane(
                bar,
                aui.AuiPaneInfo()
                .Name("toolbar")
                .Caption("Toolbar")
                .ToolbarPane()
                .Top()
                .DestroyOnClose()
                .LeftDockable(False)
                .RightDockable(False),
            )
            # Using .Gripper(False) does not work here
            wx.CallAfter(bar.SetGripperVisible, False)
        self.manager.Update()

    def onCloseToolBar(self, event):
        if event.GetPane().IsToolbar():
            self.settings.setvalue("view", "toolbar", None)
        event.Skip()

    # Viewers

    def advanceSelection(self, forward):
        self.viewer.advanceSelection(forward)

    def viewerCount(self):
        return len(self.viewer)

    # Power management

    def OnPowerState(self, state):
        pub.sendMessage(
            "powermgt.%s" % {self.POWERON: "on", self.POWEROFF: "off"}[state]
        )

    # iPhone-related methods.

    def createIPhoneProgressFrame(self):
        return IPhoneSyncFrame(
            self.settings,
            _("iPhone/iPod"),
            icon=wx.ArtProvider.GetBitmap(
                "taskcoach", wx.ART_FRAME_ICON, (16, 16)
            ),
            parent=self,
        )

    def getIPhoneSyncType(self, guid):
        if guid == self.taskFile.guid():
            return 0  # two-way

        dlg = IPhoneSyncTypeDialog(self, wx.ID_ANY, _("Synchronization type"))
        try:
            dlg.ShowModal()
            return dlg.value
        finally:
            dlg.Destroy()

    def notifyIPhoneProtocolFailed(self):
        # This should actually never happen.
        wx.MessageBox(
            _(
                """An iPhone or iPod Touch device tried to synchronize with this\n"""
                """task file, but the protocol negotiation failed. Please file a\n"""
                """bug report."""
            ),
            _("Error"),
            wx.OK,
        )

    def clearTasks(self):
        self.taskFile.clear(False)

    def restoreTasks(self, categories, tasks):
        self.taskFile.clear(False)
        self.taskFile.categories().extend(categories)
        self.taskFile.tasks().extend(tasks)

    def addIPhoneCategory(self, category):
        self.taskFile.categories().append(category)

    def removeIPhoneCategory(self, category):
        self.taskFile.categories().remove(category)

    def modifyIPhoneCategory(self, category, name):
        category.setSubject(name)

    def addIPhoneTask(self, task, categories):
        self.taskFile.tasks().append(task)
        for category in categories:
            task.addCategory(category)
            category.addCategorizable(task)

    def removeIPhoneTask(self, task):
        self.taskFile.tasks().remove(task)

    def addIPhoneEffort(self, task, effort):
        if task is not None:
            task.addEffort(effort)

    def modifyIPhoneEffort(self, effort, subject, started, ended):
        effort.setSubject(subject)
        effort.setStart(started)
        effort.setStop(ended)

    def modifyIPhoneTask(
        self,
        task,
        subject,
        description,
        plannedStartDateTime,
        dueDateTime,
        completionDateTime,
        reminderDateTime,
        recurrence,
        priority,
        categories,
    ):
        task.setSubject(subject)
        task.setDescription(description)
        task.setPlannedStartDateTime(plannedStartDateTime)
        task.setDueDateTime(dueDateTime)
        task.setCompletionDateTime(completionDateTime)
        task.setReminder(reminderDateTime)
        task.setRecurrence(recurrence)
        task.setPriority(priority)

        if categories is not None:  # Protocol v2
            for toRemove in task.categories() - categories:
                task.removeCategory(toRemove)
                toRemove.removeCategorizable(task)

            for toAdd in categories - task.categories():
                task.addCategory(toAdd)
                toAdd.addCategorizable(task)
