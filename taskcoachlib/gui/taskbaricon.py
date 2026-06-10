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
from taskcoachlib.gui.toplevelcontroller import (
    create_toplevel_controller,
)
from taskcoachlib.i18n import _
from taskcoachlib.domain import task
from pubsub import pub
import wx.adv
from .icons.icon_library import icon_catalog, LIST_ICON_SIZE

TRAY_ICON_SIZE_MACOS = 128
_TRAY_THEME_PATH = os.path.join(os.path.dirname(__file__), "icons", "tray")

# Flatpak app id. Under Flatpak the bundled tray theme (_TRAY_THEME_PATH) is
# inside the sandbox, which the StatusNotifierItem host cannot read. The
# manifest installs app-id-namespaced tray icons into the exported
# /app/share/icons instead, so the host resolves them by name. These names
# must match the icon files installed there (see build.in/flatpak/icons/).
_FLATPAK_APP_ID = "io.github.taskcoach.TaskCoach"


def _is_flatpak():
    """True when running inside a Flatpak sandbox."""
    return os.path.exists("/.flatpak-info")


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
        **kwargs,
    ):
        log_step(
            "TaskBarIcon.__init__ started (wx.adv.TaskBarIcon)", prefix="TRAY"
        )
        super().__init__(*args, **kwargs)
        self.__window = mainwindow
        self.__toplevel = None
        self.__taskList = taskList
        self.__settings = settings
        self.__icon_id = self.__default_icon_id = default_icon_id
        self.__current_icon_id = self.__icon_id
        self.__tooltipText = ""
        self.__currentText = self.__tooltipText
        self.__tick_icon_id = tick_icon_id
        self.__tack_icon_id = tack_icon_id
        self.registerObserver(
            self.on_task_list_changed,
            eventType=taskList.addItemEventType(),
            eventSource=taskList,
        )
        self.registerObserver(
            self.on_task_list_changed,
            eventType=taskList.removeItemEventType(),
            eventSource=taskList,
        )
        pub.subscribe(
            self.on_tracking_changed, task.Task.trackingChangedEventType()
        )
        pub.subscribe(
            self.on_change_due_date_time,
            task.Task.dueDateTimeChangedEventType(),
        )
        # When the user chances the due soon hours preferences it may cause
        # a task to change appearance. That also means the number of due soon
        # tasks has changed, so we need to change the tool tip text.
        # Note that directly subscribing to the setting (behavior.duesoonhours)
        # is not reliable. The TaskBarIcon may get the event before the tasks
        # do. When that happens the tasks haven't changed their status yet and
        # we would use the wrong status count.
        self.registerObserver(
            self.on_change_due_date_time_deprecated,
            eventType=task.Task.appearanceChangedEventType(),
        )
        if operating_system.isGTK():
            events = [wx.adv.EVT_TASKBAR_LEFT_DOWN]
            log_step(
                "GTK: binding EVT_TASKBAR_LEFT_DOWN for left-click",
                prefix="TRAY",
            )
        elif operating_system.isWindows():
            # See http://msdn.microsoft.com/en-us/library/windows/desktop/aa511448.aspx#interaction
            events = [
                wx.adv.EVT_TASKBAR_LEFT_DOWN,
                wx.adv.EVT_TASKBAR_LEFT_DCLICK,
            ]
            log_step(
                "Windows: binding LEFT_DOWN and LEFT_DCLICK", prefix="TRAY"
            )
        else:
            events = [wx.adv.EVT_TASKBAR_LEFT_DCLICK]
            log_step(
                "Other OS: binding EVT_TASKBAR_LEFT_DCLICK", prefix="TRAY"
            )
        for event in events:
            self.Bind(event, self.on_taskbar_click)
            log_step(
                "Bound event", event, "to on_taskbar_click", prefix="TRAY"
            )
        self.__set_tooltip_text()
        mainwindow.Bind(wx.EVT_IDLE, self.on_idle)
        log_step("TaskBarIcon.__init__ completed", prefix="TRAY")

    # Event handlers:

    def on_idle(self, event):
        if (
            self.__currentText != self.__tooltipText
            or self.__current_icon_id != self.__icon_id
        ):
            self.__currentText = self.__tooltipText
            self.__current_icon_id = self.__icon_id
            self.__set_icon()
        if event is not None:  # Unit tests
            event.Skip()

    def on_task_list_changed(self, event):  # pylint: disable=W0613
        self.__set_tooltip_text()
        self.__start_or_stop_ticking()

    def on_tracking_changed(self, newValue, sender):
        if newValue:
            self.registerObserver(
                self.on_change_subject,
                eventType=sender.subjectChangedEventType(),
                eventSource=sender,
            )
        else:
            self.removeObserver(
                self.on_change_subject,
                eventType=sender.subjectChangedEventType(),
            )
        self.__set_tooltip_text()
        if newValue:
            self.__start_ticking()
        else:
            self.__stop_ticking()

    def on_change_subject(self, event):  # pylint: disable=W0613
        self.__set_tooltip_text()

    def on_change_due_date_time(
        self, newValue, sender
    ):  # pylint: disable=W0613
        self.__set_tooltip_text()

    def on_change_due_date_time_deprecated(self, event):
        self.__set_tooltip_text()

    def on_every_second(self):
        if self.__settings.getboolean(
            "window", "blinktaskbariconwhentrackingeffort"
        ):
            self.__toggle_tracking_icon()
            self.__set_icon()

    def on_taskbar_click(self, event):
        log_step("LEFT-CLICK on taskbar icon", prefix="TRAY")
        if self.__toplevel is None:
            self.__toplevel = create_toplevel_controller(self.__window)
        controller = self.__toplevel
        if controller.is_minimized():
            log_step("restore via", controller.backend, prefix="TRAY")
            controller.restore()
        else:
            log_step("minimize via", controller.backend, prefix="TRAY")
            controller.minimize()

    # Menu:

    def set_popup_menu(self, menu):
        log_step(
            "set_popup_menu called, binding EVT_TASKBAR_RIGHT_UP",
            prefix="TRAY",
        )
        self.Bind(wx.adv.EVT_TASKBAR_RIGHT_UP, self.popup_taskbar_menu)
        self.popupmenu = menu  # pylint: disable=W0201
        log_step("set_popup_menu completed, menu:", menu, prefix="TRAY")

    def popup_taskbar_menu(self, event):  # pylint: disable=W0613
        # Update dynamic submenus (e.g. StartEffortForTaskMenu) before showing.
        # TaskBarMenu itself is a static Menu, but its DynamicMenu children
        # need refreshing since registerForMenuUpdate is a no-op.
        for item in self.popupmenu.GetMenuItems():
            submenu = item.GetSubMenu()
            if submenu and hasattr(submenu, "updateMenu"):
                submenu.updateMenu()
        # Update state-dependent labels (e.g. Hide/Restore toggle)
        for item in self.popupmenu.GetMenuItems():
            cmd = getattr(item, "_command", None)
            if cmd and hasattr(cmd, "get_menu_text"):
                item.SetItemLabel(cmd.get_menu_text())
        self.PopupMenu(self.popupmenu)

    # Getters:

    def tooltip(self):
        return self.__tooltipText

    def icon_id(self):
        return self.__icon_id

    def default_icon_id(self):
        return self.__default_icon_id

    # Private methods:

    def __start_or_stop_ticking(self):
        self.__start_ticking()
        self.__stop_ticking()

    def __start_ticking(self):
        if self.__taskList.nr_being_tracked() > 0:
            self.start_clock()
            self.__toggle_tracking_icon()
            self.__set_icon()

    def start_clock(self):
        if not getattr(self, "_clock_running", False):
            pub.subscribe(self._on_timer_second, "timer.second")
            self._clock_running = True

    def __stop_ticking(self):
        if self.__taskList.nr_being_tracked() == 0:
            self.stop_clock()
            self.__set_default_icon()
            self.__set_icon()

    def stop_clock(self):
        if getattr(self, "_clock_running", False):
            pub.unsubscribe(self._on_timer_second, "timer.second")
            self._clock_running = False

    def _on_timer_second(self, timestamp):
        """Handle second tick from global timer."""
        self.on_every_second()

    tool_tip_messages = [
        (task.status.overdue, _("one task overdue"), _("%d tasks overdue")),
        (task.status.duesoon, _("one task due soon"), _("%d tasks due soon")),
    ]

    def __set_tooltip_text(self):
        """Note that Windows XP and Vista limit the text shown in the
        tool tip to 64 characters, so we cannot show everything we would
        like to and have to make choices."""
        text_parts = []
        tracked_tasks = self.__taskList.tasks_being_tracked()
        if tracked_tasks:
            count = len(tracked_tasks)
            if count == 1:
                tracking = _('tracking "%s"') % tracked_tasks[0].subject()
            else:
                tracking = _("tracking effort for %d tasks") % count
            text_parts.append(tracking)
        else:
            counts = self.__taskList.nr_of_tasks_per_status()
            for status, singular, plural in self.tool_tip_messages:
                count = counts[status]
                if count == 1:
                    text_parts.append(singular)
                elif count > 1:
                    text_parts.append(plural % count)

        text_part = ", ".join(text_parts)
        filename = os.path.basename(self.__window.taskFile.filename())
        name_part = (
            "%s - %s" % (meta.name, filename) if filename else meta.name
        )
        text = "%s\n%s" % (name_part, text_part) if text_part else name_part

        if text != self.__tooltipText:
            self.__tooltipText = text

    def __set_default_icon(self):
        self.__icon_id = self.__default_icon_id

    def __toggle_tracking_icon(self):
        tick, tack = self.__tick_icon_id, self.__tack_icon_id
        self.__icon_id = tack if self.__icon_id == tick else tick

    def __set_icon(self):
        if operating_system.isMac():
            size = TRAY_ICON_SIZE_MACOS
        else:
            size = LIST_ICON_SIZE
        wx_icon = icon_catalog.get_wx_icon(self.__icon_id, size)
        if not wx_icon:
            return
        try:
            self.SetIcon(wx_icon, self.__tooltipText)
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
        default_tray_icon_id="taskcoach-app",
        tick_tray_icon_id="taskcoach-clock",
        tack_tray_icon_id="taskcoach-timer",
        *args,
        **kwargs,
    ):
        super().__init__()
        self.__window = mainwindow
        self.__toplevel = None
        self.__taskList = taskList
        self.__settings = settings

        # Under Flatpak the SNI host runs outside the sandbox and cannot
        # read the bundled tray theme path, so use the app-id-namespaced
        # icons the manifest installs into the exported /app/share/icons
        # theme and let the host resolve them by name (no custom theme
        # path). Elsewhere, keep using the bundled tray theme directly.
        if _is_flatpak():
            default_tray_icon_id = _FLATPAK_APP_ID
            tick_tray_icon_id = _FLATPAK_APP_ID + ".clock"
            tack_tray_icon_id = _FLATPAK_APP_ID + ".timer"
            theme_path = None
        else:
            theme_path = _TRAY_THEME_PATH

        log_step(
            "AppIndicator icons idle=%s tick=%s tack=%s theme_path=%s"
            % (
                default_tray_icon_id,
                tick_tray_icon_id,
                tack_tray_icon_id,
                theme_path,
            ),
            prefix="TRAY",
        )

        self.__tray_icon_id = self.__default_tray_icon_id = (
            default_tray_icon_id
        )
        self.__tooltipText = ""
        self.__tick_tray_icon_id = tick_tray_icon_id
        self.__tack_tray_icon_id = tack_tray_icon_id
        self.__popupmenu = None
        self._clock_running = False

        # Create the AppIndicator
        self.__indicator = _APPINDICATOR_MODULE.AppIndicatorIcon(
            app_id="taskcoach",
            icon_name=default_tray_icon_id,
            icon_theme_path=theme_path,
            tooltip=meta.name,
        )

        # Set up observers
        self.registerObserver(
            self.on_task_list_changed,
            eventType=taskList.addItemEventType(),
            eventSource=taskList,
        )
        self.registerObserver(
            self.on_task_list_changed,
            eventType=taskList.removeItemEventType(),
            eventSource=taskList,
        )
        pub.subscribe(
            self.on_tracking_changed, task.Task.trackingChangedEventType()
        )
        pub.subscribe(
            self.on_change_due_date_time,
            task.Task.dueDateTimeChangedEventType(),
        )
        self.registerObserver(
            self.on_change_due_date_time_deprecated,
            eventType=task.Task.appearanceChangedEventType(),
        )

        self.__set_tooltip_text()
        self.__set_icon()

    # Event handlers:

    def on_task_list_changed(self, event):  # pylint: disable=W0613
        self.__set_tooltip_text()
        self.__start_or_stop_ticking()
        self._rebuild_gtk_menu()  # Update menu with new task list

    def on_tracking_changed(self, newValue, sender):
        if newValue:
            self.registerObserver(
                self.on_change_subject,
                eventType=sender.subjectChangedEventType(),
                eventSource=sender,
            )
        else:
            self.removeObserver(
                self.on_change_subject,
                eventType=sender.subjectChangedEventType(),
            )
        self.__set_tooltip_text()
        if newValue:
            self.__start_ticking()
        else:
            self.__stop_ticking()
        self._rebuild_gtk_menu()  # Update menu with tracking state

    def on_change_subject(self, event):  # pylint: disable=W0613
        self.__set_tooltip_text()
        self._rebuild_gtk_menu()  # Update menu with new task subject

    def on_change_due_date_time(
        self, newValue, sender
    ):  # pylint: disable=W0613
        self.__set_tooltip_text()

    def on_change_due_date_time_deprecated(self, event):
        self.__set_tooltip_text()

    def on_every_second(self):
        if self.__settings.getboolean(
            "window", "blinktaskbariconwhentrackingeffort"
        ):
            self.__toggle_tracking_icon()
            self.__set_icon()

    def on_taskbar_click(self, event=None):
        """Show or hide the main window via the ToplevelController.

        The controller is selected once for the session (Native on
        X11/Win/macOS, KDE plasma-window-management on KDE Wayland,
        Hide/Show fallback elsewhere). It owns the
        minimize/restore mechanism so this no longer guesses window
        state with the unreliable IsIconized/IsShown/IsActive
        heuristic. See docs/SYSTEM_TRAY.md.
        """
        if self.__toplevel is None:
            self.__toplevel = create_toplevel_controller(self.__window)
        controller = self.__toplevel
        if controller.is_minimized():
            log_step("restore via", controller.backend, prefix="TRAY")
            controller.restore()
        else:
            log_step("minimize via", controller.backend, prefix="TRAY")
            controller.minimize()

    # Menu:

    def set_popup_menu(self, menu):
        """Set the popup menu.

        For AppIndicator, we need to build a GTK menu instead of using
        the wx.Menu directly.
        """
        self.__popupmenu = menu
        self._build_gtk_menu()

    def _rebuild_gtk_menu(self):
        """Rebuild the GTK menu to reflect current state.

        Called when task list, tracking state, or task subjects change.
        Uses wx.CallAfter to ensure it runs on the main thread.
        """
        if self.__indicator:  # Only rebuild if indicator still exists
            wx.CallAfter(self._build_gtk_menu)

    def _build_gtk_menu(self):
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
        show_item.connect(
            "activate", lambda w: wx.CallAfter(self.on_taskbar_click)
        )
        menu.append(show_item)

        menu.append(Gtk.SeparatorMenuItem())

        # New Task
        new_task_item = Gtk.MenuItem(label=_("New task..."))
        new_task_item.connect("activate", self._on_new_task)
        menu.append(new_task_item)

        # New task from template submenu
        template_submenu = self._build_template_submenu(Gtk)
        if template_submenu:
            template_item = Gtk.MenuItem(label=_("New task from template"))
            template_item.set_submenu(template_submenu)
            menu.append(template_item)

        menu.append(Gtk.SeparatorMenuItem())

        # New Effort
        new_effort_item = Gtk.MenuItem(label=_("New effort..."))
        new_effort_item.connect("activate", self._on_new_effort)
        menu.append(new_effort_item)

        # New Category
        new_category_item = Gtk.MenuItem(label=_("New category..."))
        new_category_item.connect("activate", self._on_new_category)
        menu.append(new_category_item)

        # New Note
        new_note_item = Gtk.MenuItem(label=_("New note..."))
        new_note_item.connect("activate", self._on_new_note)
        menu.append(new_note_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Start tracking effort submenu
        tracking_submenu = self._build_start_tracking_submenu(Gtk)
        if tracking_submenu:
            tracking_item = Gtk.MenuItem(label=_("Start tracking effort"))
            tracking_item.set_submenu(tracking_submenu)
            menu.append(tracking_item)

        # Stop/Resume tracking - dynamic based on state
        tracked_tasks = self.__taskList.tasks_being_tracked()
        if tracked_tasks:
            # Currently tracking - show Stop
            if len(tracked_tasks) == 1:
                label = _("Stop tracking %s") % tracked_tasks[0].subject()
            else:
                label = _("Stop tracking %d tasks") % len(tracked_tasks)
            stop_item = Gtk.MenuItem(label=label)
            stop_item.connect("activate", self._on_stop_tracking)
            menu.append(stop_item)
        else:
            # Not tracking - check if we can resume
            most_recent = self._get_most_recent_tracked_task()
            if most_recent:
                label = _("Resume tracking %s") % most_recent.subject()
                stop_item = Gtk.MenuItem(label=label)
                stop_item.connect(
                    "activate",
                    lambda w, t=most_recent: wx.CallAfter(
                        self._do_start_tracking, t
                    ),
                )
                menu.append(stop_item)
            # If no recent task, don't show the item at all

        menu.append(Gtk.SeparatorMenuItem())

        # Quit
        quit_item = Gtk.MenuItem(label=_("Quit"))
        quit_item.connect(
            "activate", lambda w: wx.CallAfter(self.__window.Close)
        )
        menu.append(quit_item)

        menu.show_all()
        self.__indicator.set_gtk_menu(menu)

    def _build_template_submenu(self, Gtk):
        """Build submenu for task templates."""
        from taskcoachlib import persistence

        path = self.__settings.pathToTemplatesDir()
        try:
            template_list = persistence.TemplateList(path)
            templates = list(zip(template_list.tasks(), template_list.names()))
        except Exception:
            templates = []

        if not templates:
            return None

        submenu = Gtk.Menu()
        # Sort by subject (display name) rather than filename
        templates.sort(key=lambda t: t[0].subject().lower())
        for task_item, filename in templates:
            template_path = os.path.join(path, filename)
            # Fallback to filename if no subject
            subject = task_item.subject() or filename
            item = Gtk.MenuItem(label=subject)
            # Use default argument to capture template_path in closure
            item.connect(
                "activate",
                lambda w, p=template_path: wx.CallAfter(
                    self._do_new_task_from_template, p
                ),
            )
            submenu.append(item)

        return submenu

    def _build_start_tracking_submenu(self, Gtk):
        """Build submenu for starting effort tracking on tasks."""
        # Get trackable tasks (not completed, not deleted)
        trackable_tasks = [
            t
            for t in self.__taskList
            if not t.completed()
            and not getattr(t, "isDeleted", lambda: False)()
        ]

        if not trackable_tasks:
            return None

        submenu = Gtk.Menu()
        # Get root tasks (tasks without parent or parent not in list)
        root_tasks = [
            t
            for t in trackable_tasks
            if t.parent() is None or t.parent() not in trackable_tasks
        ]
        root_tasks.sort(key=lambda t: t.subject().lower())

        for task_item in root_tasks:
            self._add_task_to_tracking_menu(
                Gtk, submenu, task_item, trackable_tasks
            )

        return submenu

    def _add_task_to_tracking_menu(
        self, Gtk, menu, task_item, trackable_tasks
    ):
        """Add a task (and its children) to the tracking submenu."""
        # Get trackable children
        trackable_children = [
            child for child in task_item.children() if child in trackable_tasks
        ]

        if trackable_children:
            # Task has children - create a submenu
            item = Gtk.MenuItem(label=task_item.subject())
            child_menu = Gtk.Menu()

            # Add item to start tracking this task
            start_item = Gtk.MenuItem(label=_("Track this task"))
            start_item.connect(
                "activate",
                lambda w, t=task_item: wx.CallAfter(
                    self._do_start_tracking, t
                ),
            )
            child_menu.append(start_item)
            child_menu.append(Gtk.SeparatorMenuItem())

            # Add children
            trackable_children.sort(key=lambda t: t.subject().lower())
            for child in trackable_children:
                self._add_task_to_tracking_menu(
                    Gtk, child_menu, child, trackable_tasks
                )

            item.set_submenu(child_menu)
            menu.append(item)
        else:
            # No children - simple menu item
            item = Gtk.MenuItem(label=task_item.subject())
            item.connect(
                "activate",
                lambda w, t=task_item: wx.CallAfter(
                    self._do_start_tracking, t
                ),
            )
            menu.append(item)

    def _on_new_task(self, widget):
        """Handle New Task menu item."""
        wx.CallAfter(self._do_new_task)

    def _do_new_task(self):
        """Create a new task (called from wx main thread)."""
        from taskcoachlib.gui import uicommand

        tasks = self.__window.taskFile.tasks()
        cmd = uicommand.TaskNew(taskList=tasks, settings=self.__settings)
        cmd.do_command(None)

    def _on_new_effort(self, widget):
        """Handle New Effort menu item."""
        wx.CallAfter(self._do_new_effort)

    def _do_new_effort(self):
        """Create a new effort (called from wx main thread)."""
        from taskcoachlib.gui import uicommand

        efforts = self.__window.taskFile.efforts()
        tasks = self.__window.taskFile.tasks()
        cmd = uicommand.EffortNew(
            effort_list=efforts, taskList=tasks, settings=self.__settings
        )
        cmd.do_command(None)

    def _on_stop_tracking(self, widget):
        """Handle Stop Tracking menu item."""
        wx.CallAfter(self._do_stop_tracking)

    def _do_stop_tracking(self):
        """Stop tracking all efforts (called from wx main thread)."""
        for tracked_task in self.__taskList.tasks_being_tracked():
            tracked_task.stopTracking()

    def _on_new_category(self, widget):
        """Handle New Category menu item."""
        wx.CallAfter(self._do_new_category)

    def _do_new_category(self):
        """Create a new category (called from wx main thread)."""
        from taskcoachlib.gui import uicommand

        categories = self.__window.taskFile.categories()
        cmd = uicommand.CategoryNew(
            categories=categories, settings=self.__settings
        )
        cmd.do_command(None)

    def _on_new_note(self, widget):
        """Handle New Note menu item."""
        wx.CallAfter(self._do_new_note)

    def _do_new_note(self):
        """Create a new note (called from wx main thread)."""
        from taskcoachlib.gui import uicommand

        notes = self.__window.taskFile.notes()
        cmd = uicommand.NoteNew(notes=notes, settings=self.__settings)
        cmd.do_command(None)

    def _do_new_task_from_template(self, template_path):
        """Create a new task from template (called from wx main thread)."""
        from taskcoachlib.gui import uicommand

        tasks = self.__window.taskFile.tasks()
        cmd = uicommand.TaskNewFromTemplate(
            template_path, taskList=tasks, settings=self.__settings
        )
        cmd.do_command(None)

    def _do_start_tracking(self, task_to_track):
        """Start tracking effort for a task (called from wx main thread)."""
        from taskcoachlib import command

        tasks = self.__window.taskFile.tasks()
        cmd = command.StartEffortCommand(tasks, [task_to_track])
        cmd.do()

    def _get_most_recent_tracked_task(self):
        """Get the most recently tracked task for resume functionality.

        Returns:
            The task that was most recently tracked, or None if no efforts exist.
        """
        effort_list = self.__window.taskFile.efforts()
        if not effort_list:
            return None

        # Find the effort with the most recent stop time
        max_stop = None
        most_recent_task = None
        for effort in effort_list:
            stop = effort.getStop()
            if stop is not None and (max_stop is None or stop > max_stop):
                max_stop = stop
                most_recent_task = effort.task()

        # Only return if task is not completed and not deleted
        if most_recent_task and not most_recent_task.completed():
            if not getattr(most_recent_task, "isDeleted", lambda: False)():
                return most_recent_task
        return None

    # Getters:

    def tooltip(self):
        return self.__tooltipText

    def tray_icon_id(self):
        return self.__tray_icon_id

    def default_tray_icon_id(self):
        return self.__default_tray_icon_id

    # Private methods:

    def __start_or_stop_ticking(self):
        self.__start_ticking()
        self.__stop_ticking()

    def __start_ticking(self):
        if self.__taskList.nr_being_tracked() > 0:
            self.start_clock()
            self.__toggle_tracking_icon()
            self.__set_icon()

    def start_clock(self):
        if not self._clock_running:
            pub.subscribe(self._on_timer_second, "timer.second")
            self._clock_running = True

    def __stop_ticking(self):
        if self.__taskList.nr_being_tracked() == 0:
            self.stop_clock()
            self.__set_default_icon()
            self.__set_icon()

    def stop_clock(self):
        if self._clock_running:
            pub.unsubscribe(self._on_timer_second, "timer.second")
            self._clock_running = False

    def _on_timer_second(self, timestamp):
        """Handle second tick from global timer."""
        self.on_every_second()

    tool_tip_messages = [
        (task.status.overdue, _("one task overdue"), _("%d tasks overdue")),
        (task.status.duesoon, _("one task due soon"), _("%d tasks due soon")),
    ]

    def __set_tooltip_text(self):
        """Update the tooltip text based on current task status."""
        text_parts = []
        tracked_tasks = self.__taskList.tasks_being_tracked()
        if tracked_tasks:
            count = len(tracked_tasks)
            if count == 1:
                tracking = _('tracking "%s"') % tracked_tasks[0].subject()
            else:
                tracking = _("tracking effort for %d tasks") % count
            text_parts.append(tracking)
        else:
            counts = self.__taskList.nr_of_tasks_per_status()
            for status, singular, plural in self.tool_tip_messages:
                count = counts[status]
                if count == 1:
                    text_parts.append(singular)
                elif count > 1:
                    text_parts.append(plural % count)

        text_part = ", ".join(text_parts)
        filename = os.path.basename(self.__window.taskFile.filename())
        name_part = (
            "%s - %s" % (meta.name, filename) if filename else meta.name
        )
        text = "%s\n%s" % (name_part, text_part) if text_part else name_part

        if text != self.__tooltipText:
            self.__tooltipText = text
            if self.__indicator:
                self.__indicator.set_tooltip(text)

    def __set_default_icon(self):
        self.__tray_icon_id = self.__default_tray_icon_id

    def __toggle_tracking_icon(self):
        tick, tack = self.__tick_tray_icon_id, self.__tack_tray_icon_id
        self.__tray_icon_id = tack if self.__tray_icon_id == tick else tick

    def __set_icon(self):
        """Update the indicator icon."""
        if self.__indicator:
            self.__indicator.set_icon_full(
                self.__tray_icon_id, self.__tooltipText
            )

    # wx.adv.TaskBarIcon compatibility methods:

    def Bind(self, event, handler, source=None, id=wx.ID_ANY, id2=wx.ID_ANY):
        """Stub for wx.EvtHandler.Bind compatibility.

        AppIndicator uses its own GTK menu, so wx event bindings are ignored.
        This method exists only to prevent AttributeError when TaskBarMenu
        tries to bind events to its parent.
        """
        pass

    def Unbind(
        self, event, source=None, id=wx.ID_ANY, id2=wx.ID_ANY, handler=None
    ):
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
        self.stop_clock()
        if self.__indicator:
            self.__indicator.Destroy()
            self.__indicator = None


def _get_desktop_environment():
    """Detect the current desktop environment."""
    # Check XDG_CURRENT_DESKTOP first (most reliable)
    xdg_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
    if xdg_desktop:
        return xdg_desktop
    # Fall back to DESKTOP_SESSION
    return os.environ.get("DESKTOP_SESSION", "").upper()


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
    log_step(
        "wx.adv.TaskBarIcon.IsAvailable() =",
        wx_taskbar_available,
        prefix="TRAY",
    )
    log_step(
        "_APPINDICATOR_AVAILABLE =", _APPINDICATOR_AVAILABLE, prefix="TRAY"
    )
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

    # No working tray backend: the native tray is unavailable (e.g. GNOME on
    # Wayland, which has no XEmbed system tray) and the AppIndicator bindings
    # are not present. Creating a wx.adv.TaskBarIcon here produces a
    # non-functional icon whose every SetIcon() trips GTK 'GTK_IS_WIDGET'
    # assertions, spamming the log once per second while tracking effort.
    # Run without a tray icon instead.
    log_step(
        "No working tray backend available (native tray unavailable and "
        "AppIndicator missing); running without a tray icon",
        prefix="TRAY",
    )
    return None
