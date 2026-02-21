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
from taskcoachlib.meta.debug import log_step
from taskcoachlib.i18n import _
from taskcoachlib.domain import date, task
from pubsub import pub
import wx.adv
from .icons.icon_library import icon_catalog, LIST_ICON_SIZE

TRAY_ICON_SIZE_MACOS = 128

# Check for AppIndicator availability on Linux/GTK
# AppIndicator is only used when wx.adv.TaskBarIcon is not available (e.g., Wayland).
# On X11, wx.adv.TaskBarIcon is preferred because it supports left-click events.
_APPINDICATOR_MODULE = None
_APPINDICATOR_AVAILABLE = False

# Pre-load AppIndicator module on GTK systems (for potential fallback)
if operating_system.isGTK():
    try:
        from . import appindicator as _APPINDICATOR_MODULE
        _APPINDICATOR_AVAILABLE = _APPINDICATOR_MODULE.APPINDICATOR_AVAILABLE
    except ImportError as e:
        logging.getLogger(__name__).debug(
            f"AppIndicator module not available: {e}"
        )


class TaskBarIcon(patterns.Observer, wx.adv.TaskBarIcon):
    def __init__(
        self,
        mainwindow,
        taskList,
        settings,
        default_icon_id="nuvola_apps_korganizer",
        tick_icon_id="nuvola_apps_clock",
        tack_icon_id="nuvola_apps_ktimer",
        *args,
        **kwargs
    ):
        log_step("TaskBarIcon.__init__ started (wx.adv.TaskBarIcon)", prefix="TRAY")
        super().__init__(*args, **kwargs)
        self.__window = mainwindow
        self.__taskList = taskList
        self.__settings = settings
        self.__icon_id = self.__default_icon_id = default_icon_id
        self.__current_icon_id = self.__icon_id
        self.__tooltipText = ""
        self.__currentText = self.__tooltipText
        self.__tick_icon_id = tick_icon_id
        self.__tack_icon_id = tack_icon_id
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
            log_step("GTK: binding EVT_TASKBAR_LEFT_DOWN for left-click", prefix="TRAY")
        elif operating_system.isWindows():
            # See http://msdn.microsoft.com/en-us/library/windows/desktop/aa511448.aspx#interaction
            events = [
                wx.adv.EVT_TASKBAR_LEFT_DOWN,
                wx.adv.EVT_TASKBAR_LEFT_DCLICK,
            ]
            log_step("Windows: binding LEFT_DOWN and LEFT_DCLICK", prefix="TRAY")
        else:
            events = [wx.adv.EVT_TASKBAR_LEFT_DCLICK]
            log_step("Other OS: binding EVT_TASKBAR_LEFT_DCLICK", prefix="TRAY")
        for event in events:
            self.Bind(event, self.onTaskbarClick)
            log_step("Bound event", event, "to onTaskbarClick", prefix="TRAY")
        self.__setTooltipText()
        mainwindow.Bind(wx.EVT_IDLE, self.onIdle)
        log_step("TaskBarIcon.__init__ completed", prefix="TRAY")

    # Event handlers:

    def onIdle(self, event):
        if (
            self.__currentText != self.__tooltipText
            or self.__current_icon_id != self.__icon_id
        ):
            self.__currentText = self.__tooltipText
            self.__current_icon_id = self.__icon_id
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
            self.__toggle_tracking_icon()
            self.__setIcon()

    def onTaskbarClick(self, event):
        log_step("LEFT-CLICK on taskbar icon, event:", event, prefix="TRAY")
        if self.__window.IsIconized() or not self.__window.IsShown():
            log_step("Window is iconized/hidden, restoring", prefix="TRAY")
            self.__window.restore(event)
        else:
            if operating_system.isMac():
                log_step("Mac: raising window", prefix="TRAY")
                self.__window.Raise()
            else:
                log_step("Iconizing window", prefix="TRAY")
                self.__window.Iconize()

    # Menu:

    def setPopupMenu(self, menu):
        log_step("setPopupMenu called, binding EVT_TASKBAR_RIGHT_UP", prefix="TRAY")
        self.Bind(wx.adv.EVT_TASKBAR_RIGHT_UP, self.popupTaskBarMenu)
        self.popupmenu = menu  # pylint: disable=W0201
        log_step("setPopupMenu completed, menu:", menu, prefix="TRAY")

    def popupTaskBarMenu(self, event):  # pylint: disable=W0613
        log_step("RIGHT-CLICK on taskbar icon, showing popup menu", prefix="TRAY")
        log_step("popupmenu object:", self.popupmenu, prefix="TRAY")
        self.PopupMenu(self.popupmenu)
        log_step("PopupMenu() returned", prefix="TRAY")

    # Getters:

    def tooltip(self):
        return self.__tooltipText

    def icon_id(self):
        return self.__icon_id

    def default_icon_id(self):
        return self.__default_icon_id

    # Private methods:

    def __startOrStopTicking(self):
        self.__startTicking()
        self.__stopTicking()

    def __startTicking(self):
        if self.__taskList.nr_being_tracked() > 0:
            self.startClock()
            self.__toggle_tracking_icon()
            self.__setIcon()

    def startClock(self):
        if not getattr(self, '_clockRunning', False):
            pub.subscribe(self._onTimerSecond, 'timer.second')
            self._clockRunning = True

    def __stopTicking(self):
        if self.__taskList.nr_being_tracked() == 0:
            self.stopClock()
            self.__set_default_icon()
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
        trackedTasks = self.__taskList.tasks_being_tracked()
        if trackedTasks:
            count = len(trackedTasks)
            if count == 1:
                tracking = _('tracking "%s"') % trackedTasks[0].subject()
            else:
                tracking = _("tracking effort for %d tasks") % count
            textParts.append(tracking)
        else:
            counts = self.__taskList.nr_of_tasks_per_status()
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

    def __set_default_icon(self):
        self.__icon_id = self.__default_icon_id

    def __toggle_tracking_icon(self):
        tick, tack = self.__tick_icon_id, self.__tack_icon_id
        self.__icon_id = tack if self.__icon_id == tick else tick

    def __setIcon(self):
        if operating_system.isMac():
            size = TRAY_ICON_SIZE_MACOS
        else:
            size = LIST_ICON_SIZE
        icon = icon_catalog.get_wx_icon(self.__icon_id, size)
        if not icon:
            return
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
        default_icon_id="nuvola_apps_korganizer",
        tick_icon_id="nuvola_apps_clock",
        tack_icon_id="nuvola_apps_ktimer",
        *args,
        **kwargs
    ):
        super().__init__()
        self.__window = mainwindow
        self.__taskList = taskList
        self.__settings = settings
        self.__icon_id = self.__default_icon_id = default_icon_id
        self.__tooltipText = ""
        self.__tick_icon_id = tick_icon_id
        self.__tack_icon_id = tack_icon_id
        self.__popupmenu = None
        self._clockRunning = False

        # Create the AppIndicator
        self.__indicator = _APPINDICATOR_MODULE.AppIndicatorIcon(
            app_id="taskcoach",
            icon_path=icon_catalog.get_path(default_icon_id, TRAY_ICON_SIZE_MACOS),
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
        self._rebuildGtkMenu()  # Update menu with new task list

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
        self._rebuildGtkMenu()  # Update menu with tracking state

    def onChangeSubject(self, event):  # pylint: disable=W0613
        self.__setTooltipText()
        self._rebuildGtkMenu()  # Update menu with new task subject

    def onChangeDueDateTime(self, newValue, sender):  # pylint: disable=W0613
        self.__setTooltipText()

    def onChangeDueDateTime_Deprecated(self, event):
        self.__setTooltipText()

    def onEverySecond(self):
        if self.__settings.getboolean(
            "window", "blinktaskbariconwhentrackingeffort"
        ):
            self.__toggle_tracking_icon()
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

    def _rebuildGtkMenu(self):
        """Rebuild the GTK menu to reflect current state.

        Called when task list, tracking state, or task subjects change.
        Uses wx.CallAfter to ensure it runs on the main thread.
        """
        if self.__indicator:  # Only rebuild if indicator still exists
            wx.CallAfter(self._buildGtkMenu)

    def _buildGtkMenu(self):
        """Build a GTK menu for the AppIndicator."""
        if not _APPINDICATOR_MODULE:
            return

        # Check if indicator still exists (may be destroyed during shutdown)
        if not self.__indicator:
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

        # New task from template submenu
        template_submenu = self._buildTemplateSubmenu(Gtk)
        if template_submenu:
            template_item = Gtk.MenuItem(label=_("New task from template"))
            template_item.set_submenu(template_submenu)
            menu.append(template_item)

        menu.append(Gtk.SeparatorMenuItem())

        # New Effort
        new_effort_item = Gtk.MenuItem(label=_("New effort..."))
        new_effort_item.connect('activate', self._onNewEffort)
        menu.append(new_effort_item)

        # New Category
        new_category_item = Gtk.MenuItem(label=_("New category..."))
        new_category_item.connect('activate', self._onNewCategory)
        menu.append(new_category_item)

        # New Note
        new_note_item = Gtk.MenuItem(label=_("New note..."))
        new_note_item.connect('activate', self._onNewNote)
        menu.append(new_note_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Start tracking effort submenu
        tracking_submenu = self._buildStartTrackingSubmenu(Gtk)
        if tracking_submenu:
            tracking_item = Gtk.MenuItem(label=_("Start tracking effort"))
            tracking_item.set_submenu(tracking_submenu)
            menu.append(tracking_item)

        # Stop/Resume tracking - dynamic based on state
        trackedTasks = self.__taskList.tasks_being_tracked()
        if trackedTasks:
            # Currently tracking - show Stop
            if len(trackedTasks) == 1:
                label = _("Stop tracking %s") % trackedTasks[0].subject()
            else:
                label = _("Stop tracking %d tasks") % len(trackedTasks)
            stop_item = Gtk.MenuItem(label=label)
            stop_item.connect('activate', self._onStopTracking)
            menu.append(stop_item)
        else:
            # Not tracking - check if we can resume
            mostRecent = self._getMostRecentTrackedTask()
            if mostRecent:
                label = _("Resume tracking %s") % mostRecent.subject()
                stop_item = Gtk.MenuItem(label=label)
                stop_item.connect('activate',
                    lambda w, t=mostRecent: wx.CallAfter(self._doStartTracking, t))
                menu.append(stop_item)
            # If no recent task, don't show the item at all

        menu.append(Gtk.SeparatorMenuItem())

        # Quit
        quit_item = Gtk.MenuItem(label=_("Quit"))
        quit_item.connect('activate', lambda w: wx.CallAfter(self.__window.Close))
        menu.append(quit_item)

        menu.show_all()
        self.__indicator.set_gtk_menu(menu)

    def _buildTemplateSubmenu(self, Gtk):
        """Build submenu for task templates."""
        from taskcoachlib import persistence

        path = self.__settings.pathToTemplatesDir()
        try:
            templateList = persistence.TemplateList(path)
            templates = list(zip(templateList.tasks(), templateList.names()))
        except Exception:
            templates = []

        if not templates:
            return None

        submenu = Gtk.Menu()
        # Sort by subject (display name) rather than filename
        templates.sort(key=lambda t: t[0].subject().lower())
        for task, filename in templates:
            template_path = os.path.join(path, filename)
            subject = task.subject() or filename  # Fallback to filename if no subject
            item = Gtk.MenuItem(label=subject)
            # Use default argument to capture template_path in closure
            item.connect('activate',
                lambda w, p=template_path: wx.CallAfter(self._doNewTaskFromTemplate, p))
            submenu.append(item)

        return submenu

    def _buildStartTrackingSubmenu(self, Gtk):
        """Build submenu for starting effort tracking on tasks."""
        # Get trackable tasks (not completed, not deleted)
        trackable_tasks = [
            t for t in self.__taskList
            if not t.completed() and not getattr(t, 'isDeleted', lambda: False)()
        ]

        if not trackable_tasks:
            return None

        submenu = Gtk.Menu()
        # Get root tasks (tasks without parent or parent not in list)
        root_tasks = [
            t for t in trackable_tasks
            if t.parent() is None or t.parent() not in trackable_tasks
        ]
        root_tasks.sort(key=lambda t: t.subject().lower())

        for task_item in root_tasks:
            self._addTaskToTrackingMenu(Gtk, submenu, task_item, trackable_tasks)

        return submenu

    def _addTaskToTrackingMenu(self, Gtk, menu, task_item, trackable_tasks):
        """Add a task (and its children) to the tracking submenu."""
        # Get trackable children
        trackable_children = [
            child for child in task_item.children()
            if child in trackable_tasks
        ]

        if trackable_children:
            # Task has children - create a submenu
            item = Gtk.MenuItem(label=task_item.subject())
            child_menu = Gtk.Menu()

            # Add item to start tracking this task
            start_item = Gtk.MenuItem(label=_("Track this task"))
            start_item.connect('activate',
                lambda w, t=task_item: wx.CallAfter(self._doStartTracking, t))
            child_menu.append(start_item)
            child_menu.append(Gtk.SeparatorMenuItem())

            # Add children
            trackable_children.sort(key=lambda t: t.subject().lower())
            for child in trackable_children:
                self._addTaskToTrackingMenu(Gtk, child_menu, child, trackable_tasks)

            item.set_submenu(child_menu)
            menu.append(item)
        else:
            # No children - simple menu item
            item = Gtk.MenuItem(label=task_item.subject())
            item.connect('activate',
                lambda w, t=task_item: wx.CallAfter(self._doStartTracking, t))
            menu.append(item)

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
        for trackedTask in self.__taskList.tasks_being_tracked():
            trackedTask.stopTracking()

    def _onNewCategory(self, widget):
        """Handle New Category menu item."""
        wx.CallAfter(self._doNewCategory)

    def _doNewCategory(self):
        """Create a new category (called from wx main thread)."""
        from taskcoachlib.gui import uicommand
        categories = self.__window.taskFile.categories()
        cmd = uicommand.CategoryNew(categories=categories, settings=self.__settings)
        cmd.doCommand(None)

    def _onNewNote(self, widget):
        """Handle New Note menu item."""
        wx.CallAfter(self._doNewNote)

    def _doNewNote(self):
        """Create a new note (called from wx main thread)."""
        from taskcoachlib.gui import uicommand
        notes = self.__window.taskFile.notes()
        cmd = uicommand.NoteNew(notes=notes, settings=self.__settings)
        cmd.doCommand(None)

    def _doNewTaskFromTemplate(self, template_path):
        """Create a new task from template (called from wx main thread)."""
        from taskcoachlib.gui import uicommand
        tasks = self.__window.taskFile.tasks()
        cmd = uicommand.TaskNewFromTemplate(
            template_path, taskList=tasks, settings=self.__settings
        )
        cmd.doCommand(None)

    def _doStartTracking(self, task_to_track):
        """Start tracking effort for a task (called from wx main thread)."""
        from taskcoachlib import command
        tasks = self.__window.taskFile.tasks()
        cmd = command.StartEffortCommand(tasks, [task_to_track])
        cmd.do()

    def _getMostRecentTrackedTask(self):
        """Get the most recently tracked task for resume functionality.

        Returns:
            The task that was most recently tracked, or None if no efforts exist.
        """
        effortList = self.__window.taskFile.efforts()
        if not effortList:
            return None

        # Find the effort with the most recent stop time
        maxStop = None
        mostRecentTask = None
        for effort in effortList:
            stop = effort.getStop()
            if stop is not None and (maxStop is None or stop > maxStop):
                maxStop = stop
                mostRecentTask = effort.task()

        # Only return if task is not completed and not deleted
        if mostRecentTask and not mostRecentTask.completed():
            if not getattr(mostRecentTask, 'isDeleted', lambda: False)():
                return mostRecentTask
        return None

    # Getters:

    def tooltip(self):
        return self.__tooltipText

    def icon_id(self):
        return self.__icon_id

    def default_icon_id(self):
        return self.__default_icon_id

    # Private methods:

    def __startOrStopTicking(self):
        self.__startTicking()
        self.__stopTicking()

    def __startTicking(self):
        if self.__taskList.nr_being_tracked() > 0:
            self.startClock()
            self.__toggle_tracking_icon()
            self.__setIcon()

    def startClock(self):
        if not self._clockRunning:
            pub.subscribe(self._onTimerSecond, 'timer.second')
            self._clockRunning = True

    def __stopTicking(self):
        if self.__taskList.nr_being_tracked() == 0:
            self.stopClock()
            self.__set_default_icon()
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
        trackedTasks = self.__taskList.tasks_being_tracked()
        if trackedTasks:
            count = len(trackedTasks)
            if count == 1:
                tracking = _('tracking "%s"') % trackedTasks[0].subject()
            else:
                tracking = _("tracking effort for %d tasks") % count
            textParts.append(tracking)
        else:
            counts = self.__taskList.nr_of_tasks_per_status()
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

    def __set_default_icon(self):
        self.__icon_id = self.__default_icon_id

    def __toggle_tracking_icon(self):
        tick, tack = self.__tick_icon_id, self.__tack_icon_id
        self.__icon_id = tack if self.__icon_id == tick else tick

    def __setIcon(self):
        """Update the indicator icon."""
        if self.__indicator:
            path = icon_catalog.get_path(self.__icon_id, TRAY_ICON_SIZE_MACOS)
            if path:
                self.__indicator.set_icon_full(path, self.__tooltipText)

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


def _get_desktop_environment():
    """Detect the current desktop environment."""
    # Check XDG_CURRENT_DESKTOP first (most reliable)
    xdg_desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').upper()
    if xdg_desktop:
        return xdg_desktop
    # Fall back to DESKTOP_SESSION
    return os.environ.get('DESKTOP_SESSION', '').upper()


def _needs_appindicator():
    """Check if we need to use AppIndicator instead of wx.adv.TaskBarIcon.

    wx.adv.TaskBarIcon on Linux/GTK doesn't properly receive right-click events
    on many desktop environments (LXDE, KDE, and possibly others). AppIndicator
    provides reliable menu functionality across all Linux desktops.
    """
    # Use AppIndicator on all Linux/GTK systems when available
    # because wx.adv.TaskBarIcon right-click is broken on many desktops
    if operating_system.isGTK():
        return True
    return False


def create_taskbar_icon(mainwindow, taskList, settings):
    """Factory function to create the appropriate taskbar icon.

    Uses wx.adv.TaskBarIcon when available (preferred for full click event support).
    Falls back to AppIndicator on Linux when:
    - wx.adv.TaskBarIcon is not available (e.g., Wayland)
    - Desktop environment doesn't properly support right-click (e.g., LXDE)

    Args:
        mainwindow: The main application window
        taskList: The task list
        settings: Application settings

    Returns:
        TaskBarIcon or AppIndicatorTaskBarIcon instance
    """
    log_step("create_taskbar_icon called", prefix="TRAY")

    desktop = _get_desktop_environment()
    needs_appindicator = _needs_appindicator()
    wx_taskbar_available = wx.adv.TaskBarIcon.IsAvailable()

    log_step("Desktop environment:", desktop, prefix="TRAY")
    log_step("wx.adv.TaskBarIcon.IsAvailable() =", wx_taskbar_available, prefix="TRAY")
    log_step("_APPINDICATOR_AVAILABLE =", _APPINDICATOR_AVAILABLE, prefix="TRAY")
    log_step("needs_appindicator =", needs_appindicator, prefix="TRAY")

    # Use AppIndicator if needed and available
    if needs_appindicator and _APPINDICATOR_AVAILABLE:
        log_step("Using AppIndicator (desktop requires it)", prefix="TRAY")
        return AppIndicatorTaskBarIcon(mainwindow, taskList, settings)

    # Use native wx.adv.TaskBarIcon if available
    if wx_taskbar_available:
        log_step("Using wx.adv.TaskBarIcon (native)", prefix="TRAY")
        return TaskBarIcon(mainwindow, taskList, settings)

    # Last resort: try AppIndicator on GTK
    if operating_system.isGTK() and _APPINDICATOR_AVAILABLE:
        log_step("Using AppIndicator (fallback)", prefix="TRAY")
        return AppIndicatorTaskBarIcon(mainwindow, taskList, settings)

    # No AppIndicator available, try wx.adv.TaskBarIcon anyway (may not work)
    log_step("WARNING: No good tray option available, trying wx.adv.TaskBarIcon", prefix="TRAY")
    return TaskBarIcon(mainwindow, taskList, settings)
