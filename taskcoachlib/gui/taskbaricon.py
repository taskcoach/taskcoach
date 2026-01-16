# -*- coding: utf-8 -*-

"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2008 João Alexandre de Toledo <jtoledo@griffo.com.br>

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
import os
import logging
from taskcoachlib import meta, patterns, operating_system
from taskcoachlib.i18n import _
from taskcoachlib.domain import date, task
from pubsub import pub
import wx.adv
from . import artprovider

# Check for AppIndicator availability on Linux/GTK
# AppIndicator is used exclusively on Linux because:
# - It works on both Wayland (SNI protocol) and X11 (XEmbed fallback)
# - wx.adv.TaskBarIcon doesn't work on Wayland
# - Simplifies codebase with single implementation for Linux
_USE_APPINDICATOR = False
_APPINDICATOR_MODULE = None

if operating_system.isGTK():
    try:
        from . import appindicator as _APPINDICATOR_MODULE
        if _APPINDICATOR_MODULE.APPINDICATOR_AVAILABLE:
            _USE_APPINDICATOR = True
            logging.getLogger(__name__).info(
                "Linux/GTK detected - using AppIndicator for system tray"
            )
        else:
            logging.getLogger(__name__).warning(
                f"Linux/GTK detected but AppIndicator not available: "
                f"{_APPINDICATOR_MODULE.APPINDICATOR_ERROR}. "
                f"Falling back to wx.adv.TaskBarIcon."
            )
    except ImportError as e:
        logging.getLogger(__name__).warning(
            f"Linux/GTK detected but failed to import appindicator module: {e}. "
            f"Falling back to wx.adv.TaskBarIcon."
        )


class TaskBarIcon(patterns.Observer, wx.adv.TaskBarIcon):
    def __init__(
        self,
        mainwindow,
        taskList,
        settings,
        defaultBitmap="taskcoach",
        tickBitmap="clock_icon",
        tackBitmap="clock_stopwatch_icon",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.__window = mainwindow
        self.__taskList = taskList
        self.__settings = settings
        self.__bitmap = self.__defaultBitmap = defaultBitmap
        self.__currentBitmap = self.__bitmap
        self.__tooltipText = ""
        self.__currentText = self.__tooltipText
        self.__tickBitmap = tickBitmap
        self.__tackBitmap = tackBitmap
        self.registerObserver(
            self.onTaskListChanged,
            eventType=taskList.addItemEventType(),
            eventSource=taskList,
        )
        self.registerObserver(
            self.onTaskListChanged,
            eventType=taskList.removeItemEventType(),
            eventSource=taskList,
        )
        pub.subscribe(
            self.onTrackingChanged, task.Task.trackingChangedEventType()
        )
        pub.subscribe(
            self.onChangeDueDateTime, task.Task.dueDateTimeChangedEventType()
        )
        # When the user chances the due soon hours preferences it may cause
        # a task to change appearance. That also means the number of due soon
        # tasks has changed, so we need to change the tool tip text.
        # Note that directly subscribing to the setting (behavior.duesoonhours)
        # is not reliable. The TaskBarIcon may get the event before the tasks
        # do. When that happens the tasks haven't changed their status yet and
        # we would use the wrong status count.
        self.registerObserver(
            self.onChangeDueDateTime_Deprecated,
            eventType=task.Task.appearanceChangedEventType(),
        )
        if operating_system.isGTK():
            events = [wx.adv.EVT_TASKBAR_LEFT_DOWN]
        elif operating_system.isWindows():
            # See http://msdn.microsoft.com/en-us/library/windows/desktop/aa511448.aspx#interaction
            events = [
                wx.adv.EVT_TASKBAR_LEFT_DOWN,
                wx.adv.EVT_TASKBAR_LEFT_DCLICK,
            ]
        else:
            events = [wx.adv.EVT_TASKBAR_LEFT_DCLICK]
        for event in events:
            self.Bind(event, self.onTaskbarClick)
        self.__setTooltipText()
        mainwindow.Bind(wx.EVT_IDLE, self.onIdle)

    # Event handlers:

    def onIdle(self, event):
        if (
            self.__currentText != self.__tooltipText
            or self.__currentBitmap != self.__bitmap
        ):
            self.__currentText = self.__tooltipText
            self.__currentBitmap = self.__bitmap
            self.__setIcon()
        if event is not None:  # Unit tests
            event.Skip()

    def onTaskListChanged(self, event):  # pylint: disable=W0613
        self.__setTooltipText()
        self.__startOrStopTicking()

    def onTrackingChanged(self, newValue, sender):
        if newValue:
            self.registerObserver(
                self.onChangeSubject,
                eventType=sender.subjectChangedEventType(),
                eventSource=sender,
            )
        else:
            self.removeObserver(
                self.onChangeSubject,
                eventType=sender.subjectChangedEventType(),
            )
        self.__setTooltipText()
        if newValue:
            self.__startTicking()
        else:
            self.__stopTicking()

    def onChangeSubject(self, event):  # pylint: disable=W0613
        self.__setTooltipText()

    def onChangeDueDateTime(self, newValue, sender):  # pylint: disable=W0613
        self.__setTooltipText()

    def onChangeDueDateTime_Deprecated(self, event):
        self.__setTooltipText()

    def onEverySecond(self):
        if self.__settings.getboolean(
            "window", "blinktaskbariconwhentrackingeffort"
        ):
            self.__toggleTrackingBitmap()
            self.__setIcon()

    def onTaskbarClick(self, event):
        if self.__window.IsIconized() or not self.__window.IsShown():
            self.__window.restore(event)
        else:
            if operating_system.isMac():
                self.__window.Raise()
            else:
                self.__window.Iconize()

    # Menu:

    def setPopupMenu(self, menu):
        self.Bind(wx.adv.EVT_TASKBAR_RIGHT_UP, self.popupTaskBarMenu)
        self.popupmenu = menu  # pylint: disable=W0201

    def popupTaskBarMenu(self, event):  # pylint: disable=W0613
        self.PopupMenu(self.popupmenu)

    # Getters:

    def tooltip(self):
        return self.__tooltipText

    def bitmap(self):
        return self.__bitmap

    def defaultBitmap(self):
        return self.__defaultBitmap

    # Private methods:

    def __startOrStopTicking(self):
        self.__startTicking()
        self.__stopTicking()

    def __startTicking(self):
        if self.__taskList.nrBeingTracked() > 0:
            self.startClock()
            self.__toggleTrackingBitmap()
            self.__setIcon()

    def startClock(self):
        if not getattr(self, '_clockRunning', False):
            pub.subscribe(self._onTimerSecond, 'timer.second')
            self._clockRunning = True

    def __stopTicking(self):
        if self.__taskList.nrBeingTracked() == 0:
            self.stopClock()
            self.__setDefaultBitmap()
            self.__setIcon()

    def stopClock(self):
        if getattr(self, '_clockRunning', False):
            pub.unsubscribe(self._onTimerSecond, 'timer.second')
            self._clockRunning = False

    def _onTimerSecond(self, timestamp):
        """Handle second tick from global timer."""
        self.onEverySecond()

    toolTipMessages = [
        (task.status.overdue, _("one task overdue"), _("%d tasks overdue")),
        (task.status.duesoon, _("one task due soon"), _("%d tasks due soon")),
    ]

    def __setTooltipText(self):
        """Note that Windows XP and Vista limit the text shown in the
        tool tip to 64 characters, so we cannot show everything we would
        like to and have to make choices."""
        textParts = []
        trackedTasks = self.__taskList.tasksBeingTracked()
        if trackedTasks:
            count = len(trackedTasks)
            if count == 1:
                tracking = _('tracking "%s"') % trackedTasks[0].subject()
            else:
                tracking = _("tracking effort for %d tasks") % count
            textParts.append(tracking)
        else:
            counts = self.__taskList.nrOfTasksPerStatus()
            for status, singular, plural in self.toolTipMessages:
                count = counts[status]
                if count == 1:
                    textParts.append(singular)
                elif count > 1:
                    textParts.append(plural % count)

        textPart = ", ".join(textParts)
        filename = os.path.basename(self.__window.taskFile.filename())
        namePart = "%s - %s" % (meta.name, filename) if filename else meta.name
        text = "%s\n%s" % (namePart, textPart) if textPart else namePart

        if text != self.__tooltipText:
            self.__tooltipText = text

    def __setDefaultBitmap(self):
        self.__bitmap = self.__defaultBitmap

    def __toggleTrackingBitmap(self):
        tick, tack = self.__tickBitmap, self.__tackBitmap
        self.__bitmap = tack if self.__bitmap == tick else tick

    def __setIcon(self):
        icon = artprovider.getIcon(self.__bitmap)
        try:
            self.SetIcon(icon, self.__tooltipText)
        except Exception:
            # wx assert errors on macOS but the icon still gets set... Whatever
            pass


class AppIndicatorTaskBarIcon(patterns.Observer):
    """TaskBarIcon implementation using AppIndicator for Linux.

    This class provides the same interface as TaskBarIcon but uses the
    libayatana-appindicator library instead of wx.adv.TaskBarIcon.

    AppIndicator is used exclusively on Linux because:
    - Works on Wayland via StatusNotifierItem (SNI) protocol
    - Works on X11 via automatic XEmbed fallback
    - Provides consistent behavior across all Linux desktop environments
    """

    def __init__(
        self,
        mainwindow,
        taskList,
        settings,
        defaultBitmap="taskcoach",
        tickBitmap="clock_icon",
        tackBitmap="clock_stopwatch_icon",
        *args,
        **kwargs
    ):
        super().__init__()
        self.__window = mainwindow
        self.__taskList = taskList
        self.__settings = settings
        self.__bitmap = self.__defaultBitmap = defaultBitmap
        self.__tooltipText = ""
        self.__tickBitmap = tickBitmap
        self.__tackBitmap = tackBitmap
        self.__popupmenu = None
        self._clockRunning = False

        # Create the AppIndicator
        self.__indicator = _APPINDICATOR_MODULE.AppIndicatorIcon(
            app_id="taskcoach",
            icon_name=defaultBitmap,
            tooltip=meta.name
        )

        # Set up observers
        self.registerObserver(
            self.onTaskListChanged,
            eventType=taskList.addItemEventType(),
            eventSource=taskList,
        )
        self.registerObserver(
            self.onTaskListChanged,
            eventType=taskList.removeItemEventType(),
            eventSource=taskList,
        )
        pub.subscribe(
            self.onTrackingChanged, task.Task.trackingChangedEventType()
        )
        pub.subscribe(
            self.onChangeDueDateTime, task.Task.dueDateTimeChangedEventType()
        )
        self.registerObserver(
            self.onChangeDueDateTime_Deprecated,
            eventType=task.Task.appearanceChangedEventType(),
        )

        self.__setTooltipText()
        self.__setIcon()

    # Event handlers:

    def onTaskListChanged(self, event):  # pylint: disable=W0613
        self.__setTooltipText()
        self.__startOrStopTicking()

    def onTrackingChanged(self, newValue, sender):
        if newValue:
            self.registerObserver(
                self.onChangeSubject,
                eventType=sender.subjectChangedEventType(),
                eventSource=sender,
            )
        else:
            self.removeObserver(
                self.onChangeSubject,
                eventType=sender.subjectChangedEventType(),
            )
        self.__setTooltipText()
        if newValue:
            self.__startTicking()
        else:
            self.__stopTicking()

    def onChangeSubject(self, event):  # pylint: disable=W0613
        self.__setTooltipText()

    def onChangeDueDateTime(self, newValue, sender):  # pylint: disable=W0613
        self.__setTooltipText()

    def onChangeDueDateTime_Deprecated(self, event):
        self.__setTooltipText()

    def onEverySecond(self):
        if self.__settings.getboolean(
            "window", "blinktaskbariconwhentrackingeffort"
        ):
            self.__toggleTrackingBitmap()
            self.__setIcon()

    def onTaskbarClick(self, event=None):
        """Handle click on indicator - show/hide main window."""
        if self.__window.IsIconized() or not self.__window.IsShown():
            self.__window.restore(event)
        else:
            self.__window.Iconize()

    # Menu:

    def setPopupMenu(self, menu):
        """Set the popup menu.

        For AppIndicator, we need to build a GTK menu instead of using
        the wx.Menu directly.
        """
        self.__popupmenu = menu
        self._buildGtkMenu()

    def _buildGtkMenu(self):
        """Build a GTK menu for the AppIndicator."""
        if not _APPINDICATOR_MODULE:
            return

        # Import GTK from the appindicator module's cached reference
        Gtk = _APPINDICATOR_MODULE._Gtk
        if not Gtk:
            return

        menu = Gtk.Menu()

        # Show/Hide main window (acts as left-click replacement)
        show_item = Gtk.MenuItem(label=_("Show/Hide Task Coach"))
        show_item.connect('activate', lambda w: wx.CallAfter(self.onTaskbarClick))
        menu.append(show_item)

        menu.append(Gtk.SeparatorMenuItem())

        # New Task
        new_task_item = Gtk.MenuItem(label=_("New task..."))
        new_task_item.connect('activate', self._onNewTask)
        menu.append(new_task_item)

        # New Effort
        new_effort_item = Gtk.MenuItem(label=_("New effort..."))
        new_effort_item.connect('activate', self._onNewEffort)
        menu.append(new_effort_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Stop tracking (if any tasks being tracked)
        stop_item = Gtk.MenuItem(label=_("Stop tracking"))
        stop_item.connect('activate', self._onStopTracking)
        menu.append(stop_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Restore window
        restore_item = Gtk.MenuItem(label=_("Restore"))
        restore_item.connect('activate', lambda w: wx.CallAfter(self.__window.restore, None))
        menu.append(restore_item)

        # Quit
        quit_item = Gtk.MenuItem(label=_("Quit"))
        quit_item.connect('activate', lambda w: wx.CallAfter(self.__window.Close))
        menu.append(quit_item)

        menu.show_all()
        self.__indicator.set_gtk_menu(menu)

    def _onNewTask(self, widget):
        """Handle New Task menu item."""
        wx.CallAfter(self._doNewTask)

    def _doNewTask(self):
        """Create a new task (called from wx main thread)."""
        from taskcoachlib.gui import uicommand
        tasks = self.__window.taskFile.tasks()
        cmd = uicommand.TaskNew(taskList=tasks, settings=self.__settings)
        cmd.doCommand(None)

    def _onNewEffort(self, widget):
        """Handle New Effort menu item."""
        wx.CallAfter(self._doNewEffort)

    def _doNewEffort(self):
        """Create a new effort (called from wx main thread)."""
        from taskcoachlib.gui import uicommand
        efforts = self.__window.taskFile.efforts()
        tasks = self.__window.taskFile.tasks()
        cmd = uicommand.EffortNew(
            effortList=efforts, taskList=tasks, settings=self.__settings
        )
        cmd.doCommand(None)

    def _onStopTracking(self, widget):
        """Handle Stop Tracking menu item."""
        wx.CallAfter(self._doStopTracking)

    def _doStopTracking(self):
        """Stop tracking all efforts (called from wx main thread)."""
        for trackedTask in self.__taskList.tasksBeingTracked():
            trackedTask.stopTracking()

    # Getters:

    def tooltip(self):
        return self.__tooltipText

    def bitmap(self):
        return self.__bitmap

    def defaultBitmap(self):
        return self.__defaultBitmap

    # Private methods:

    def __startOrStopTicking(self):
        self.__startTicking()
        self.__stopTicking()

    def __startTicking(self):
        if self.__taskList.nrBeingTracked() > 0:
            self.startClock()
            self.__toggleTrackingBitmap()
            self.__setIcon()

    def startClock(self):
        if not self._clockRunning:
            pub.subscribe(self._onTimerSecond, 'timer.second')
            self._clockRunning = True

    def __stopTicking(self):
        if self.__taskList.nrBeingTracked() == 0:
            self.stopClock()
            self.__setDefaultBitmap()
            self.__setIcon()

    def stopClock(self):
        if self._clockRunning:
            pub.unsubscribe(self._onTimerSecond, 'timer.second')
            self._clockRunning = False

    def _onTimerSecond(self, timestamp):
        """Handle second tick from global timer."""
        self.onEverySecond()

    toolTipMessages = [
        (task.status.overdue, _("one task overdue"), _("%d tasks overdue")),
        (task.status.duesoon, _("one task due soon"), _("%d tasks due soon")),
    ]

    def __setTooltipText(self):
        """Update the tooltip text based on current task status."""
        textParts = []
        trackedTasks = self.__taskList.tasksBeingTracked()
        if trackedTasks:
            count = len(trackedTasks)
            if count == 1:
                tracking = _('tracking "%s"') % trackedTasks[0].subject()
            else:
                tracking = _("tracking effort for %d tasks") % count
            textParts.append(tracking)
        else:
            counts = self.__taskList.nrOfTasksPerStatus()
            for status, singular, plural in self.toolTipMessages:
                count = counts[status]
                if count == 1:
                    textParts.append(singular)
                elif count > 1:
                    textParts.append(plural % count)

        textPart = ", ".join(textParts)
        filename = os.path.basename(self.__window.taskFile.filename())
        namePart = "%s - %s" % (meta.name, filename) if filename else meta.name
        text = "%s\n%s" % (namePart, textPart) if textPart else namePart

        if text != self.__tooltipText:
            self.__tooltipText = text
            if self.__indicator:
                self.__indicator.set_tooltip(text)

    def __setDefaultBitmap(self):
        self.__bitmap = self.__defaultBitmap

    def __toggleTrackingBitmap(self):
        tick, tack = self.__tickBitmap, self.__tackBitmap
        self.__bitmap = tack if self.__bitmap == tick else tick

    def __setIcon(self):
        """Update the indicator icon."""
        if self.__indicator:
            self.__indicator.set_icon_by_name(self.__bitmap, self.__tooltipText)

    # wx.adv.TaskBarIcon compatibility methods:

    def Bind(self, event, handler, source=None, id=wx.ID_ANY, id2=wx.ID_ANY):
        """Stub for wx.EvtHandler.Bind compatibility.

        AppIndicator uses its own GTK menu, so wx event bindings are ignored.
        This method exists only to prevent AttributeError when TaskBarMenu
        tries to bind events to its parent.
        """
        pass

    def Unbind(self, event, source=None, id=wx.ID_ANY, id2=wx.ID_ANY, handler=None):
        """Stub for wx.EvtHandler.Unbind compatibility.

        AppIndicator uses its own GTK menu, so wx event unbindings are ignored.
        """
        return True

    def ProcessEvent(self, event):
        """Stub for wx.EvtHandler.ProcessEvent compatibility.

        AppIndicator uses its own GTK menu, so wx event processing is ignored.
        This method is called by Menu.invokeMenuItem() and Menu.openMenu().
        """
        return False

    def UpdateWindowUI(self, flags=wx.UPDATE_UI_NONE):
        """Stub for wx.Window.UpdateWindowUI compatibility.

        AppIndicator uses its own GTK menu, so UI updates are ignored.
        This method is called by Menu.openMenu() before processing menu events.
        """
        pass

    def RemoveIcon(self):
        """Remove the indicator icon."""
        if self.__indicator:
            self.__indicator.RemoveIcon()

    def Destroy(self):
        """Clean up the indicator."""
        self.stopClock()
        if self.__indicator:
            self.__indicator.Destroy()
            self.__indicator = None


def create_taskbar_icon(mainwindow, taskList, settings):
    """Factory function to create the appropriate taskbar icon.

    On Linux/GTK with AppIndicator available, returns AppIndicatorTaskBarIcon.
    On Windows/macOS (or Linux without AppIndicator), returns wx.adv.TaskBarIcon.

    Args:
        mainwindow: The main application window
        taskList: The task list
        settings: Application settings

    Returns:
        TaskBarIcon or AppIndicatorTaskBarIcon instance
    """
    if _USE_APPINDICATOR:
        logging.getLogger(__name__).info("Creating AppIndicator-based taskbar icon (Linux)")
        return AppIndicatorTaskBarIcon(mainwindow, taskList, settings)
    else:
        logging.getLogger(__name__).info("Creating wx.adv.TaskBarIcon-based taskbar icon (Windows/macOS)")
        return TaskBarIcon(mainwindow, taskList, settings)
