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
    timer as globaltimer,
)
from taskcoachlib.gui.dialog.editor import Editor
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

        self._idleController = idlecontroller.IdleController(
            self, self.settings, self.taskFile.efforts()
        )

    def setShutdownInProgress(self):
        self.__shutdown = True

    def _create_window_components(self):  # Not private for test purposes
        # Freeze to prevent flickering during viewer creation
        self.Freeze()
        try:
            # Start global timer FIRST - other components subscribe to its events
            self._globalTimer = globaltimer.GlobalTimer(self)
            self._globalTimer.start()

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

        # Reset toolbar position after perspective is loaded
        wx.CallAfter(self._resetToolbarPosition)

        # Note: Window position/size tracking uses debouncing to handle spurious
        # events from AUI LoadPerspective() and GTK window realization.
        # Events are bound immediately in __init__, no manual start needed.

    def __restore_perspective(self):
        perspective = self.settings.get("view", "perspective")
        # Note: We intentionally do NOT validate viewer counts before loading.
        # AUI's LoadPerspective handles mismatches gracefully:
        # - Panes in perspective without matching windows are ignored
        # - Windows without matching perspective entries keep default layout
        # This allows perspective to work across version changes and with
        # any combination of viewer types and instance counts.
        # See docs/AUI.md for details.
        try:
            self.manager.LoadPerspective(perspective)
        except Exception as reason:
            # wxPython's AUI LoadPerspective can raise Exception (not ValueError)
            # with "Bad perspective string" when the saved layout is corrupt.
            # Keep going if it does.
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
            # Reset toolbar MinSize - width is derived from window, not saved.
            # Old INI files may have hard-coded widths like minw=1840.
            # Use GetBestSize() for height - toolbar calculates this in Realize()
            if pane.name == "toolbar":
                best_size = pane.window.GetBestSize()
                pane.MinSize((-1, best_size.GetHeight()))
        self.manager.Update()

    def __register_for_window_component_changes(self):
        pub.subscribe(self.__onFilenameChanged, "taskfile.filenameChanged")
        pub.subscribe(self.__onDirtyChanged, "taskfile.dirty")
        pub.subscribe(self.__onDirtyChanged, "taskfile.clean")
        pub.subscribe(self.showStatusBar, "settings.view.statusbar")
        pub.subscribe(self.showToolBar, "settings.view.toolbar")
        self.Bind(aui.EVT_AUI_PANE_CLOSE, self.onCloseToolBar)
        # Detect toolbar drag-end and float-to-dock transitions to reset position
        self.manager.Bind(aui.EVT_AUI_RENDER, self._onAuiRender)

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

    def resetWindowLayout(self):
        """Reset window layout to default as when freshly installed.

        This closes ALL viewers, resets viewer counts to defaults (1 TaskViewer,
        1 CategoryViewer), clears the saved perspective, and recreates viewers.
        """
        import wx.lib.agw.aui as aui

        # Close ALL viewers (not just floating)
        viewers_to_close = list(self.viewer.viewers)  # Copy the list
        for v in viewers_to_close:
            self.viewer.closeViewer(v)
            self.viewer.viewers.remove(v)

        # Process closures
        self.manager.Update()

        # Detach and close any remaining non-toolbar panes (e.g., notebook controls)
        leftover_panes = [
            pane for pane in self.manager.GetAllPanes()
            if not pane.IsToolbar()
        ]
        for pane in leftover_panes:
            if pane.window:
                self.manager.DetachPane(pane.window)
            self.manager.ClosePane(pane)
        self.manager.Update()

        # Reset viewer counts to fresh install defaults
        self.settings.set("view", "taskviewercount", "1")
        self.settings.set("view", "categoryviewercount", "1")
        self.settings.set("view", "noteviewercount", "0")
        self.settings.set("view", "effortviewercount", "0")
        self.settings.set("view", "effortviewerforselectedtaskscount", "0")
        self.settings.set("view", "squaretaskviewercount", "0")
        self.settings.set("view", "timelineviewercount", "0")
        self.settings.set("view", "calendarviewercount", "0")
        self.settings.set("view", "hierarchicalcalendarviewercount", "0")
        self.settings.set("view", "taskstatsviewercount", "0")
        self.settings.set("view", "taskinterdepsviewercount", "0")

        # Clear saved perspective
        self.settings.set("view", "perspective", "")

        # Recreate viewers with default counts
        viewer.addViewers(self.viewer, self.taskFile, self.settings)

        # Explicitly position the first TaskViewer in center (in case auto-positioning failed)
        for pane in self.manager.GetAllPanes():
            if pane.IsToolbar():
                continue
            name = pane.name
            if "taskviewer" in name and "stats" not in name and "interdeps" not in name:
                pane.dock_direction = aui.AUI_DOCK_CENTER
                pane.dock_layer = 0
                pane.dock_row = 0
                pane.dock_pos = 0
                break  # Only first taskviewer

        self.manager.Update()

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
            width = event.GetSize().GetWidth()
            # Get height from toolbar's GetBestSize() - calculated during Realize()
            best_size = currentToolbar.window.GetBestSize()
            height = best_size.GetHeight()
            # Set size on the window widget for current display
            currentToolbar.window.SetSize((width, -1))
            currentToolbar.window.SetMinSize((width, height))
            # Use -1 for width on pane info so SavePerspective doesn't save
            # a hard-coded width value. The toolbar width is derived from
            # window width at runtime, not a user preference to persist.
            currentToolbar.MinSize((-1, height))
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
            # Use GetBestSize() for height - toolbar calculates this during Realize()
            best_size = bar.GetBestSize()
            self.manager.AddPane(
                bar,
                aui.AuiPaneInfo()
                .Name("toolbar")
                .Caption("Toolbar")
                .ToolbarPane()
                .Top()
                .MinSize((-1, best_size.GetHeight()))
                .DestroyOnClose(),
            )
        self.manager.Update()

    def onCloseToolBar(self, event):
        if event.GetPane().IsToolbar():
            self.settings.setvalue("view", "toolbar", None)
        event.Skip()

    def _resetToolbarPosition(self):
        """Reset toolbar to position 0 to fill the dock area.

        Called on startup, drag-end, and float-to-dock transitions.
        For top/bottom docking: sticks left and fills width.
        For left/right docking: sticks up and fills height.
        Does nothing if toolbar is floating.
        """
        pane = self.manager.GetPane("toolbar")
        if not pane.IsOk() or pane.IsFloating():
            return

        direction = pane.dock_direction
        # Only handle docked positions: 1=top, 2=right, 3=bottom, 4=left
        if direction not in (1, 2, 3, 4):
            return

        if pane.dock_pos != 0:
            pane.Position(0)
            if direction in (1, 3):  # top/bottom: fill width
                pane.MinSize((self.GetSize().GetWidth(), -1))
            else:  # left/right: fill height
                pane.MinSize((-1, self.GetSize().GetHeight()))
            self.manager.Update()

    def _onAuiRender(self, event):
        """Detect toolbar drag-end and float-to-dock to reset position."""
        action = getattr(self.manager, '_action', 0)
        prev_action = getattr(self, '_prev_manager_action', 0)

        # Detect transition from dragging to idle
        if prev_action != 0 and action == 0:
            wx.CallAfter(self._resetToolbarPosition)

        # Detect floating->docked transition
        pane = self.manager.GetPane("toolbar")
        if pane.IsOk():
            was_floating = getattr(self, '_toolbar_was_floating', False)
            is_floating = pane.IsFloating()
            if was_floating and not is_floating:
                wx.CallAfter(self._resetToolbarPosition)
            self._toolbar_was_floating = is_floating

        self._prev_manager_action = action
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
