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

AppIndicator/StatusNotifierItem support for Wayland.

This module provides system tray icon support on Wayland using the
libayatana-appindicator library (StatusNotifierItem protocol), which
is required because wx.adv.TaskBarIcon relies on X11's XEmbed protocol
that doesn't work on Wayland.

References:
- https://github.com/AyatanaIndicators/libayatana-appindicator
- https://lazka.github.io/pgi-docs/AyatanaAppIndicator3-0.1/
"""

import os
import sys

# Try to import AppIndicator (Ayatana version preferred, fallback to legacy)
_appindicator = None
_gi = None
_Gtk = None
_GLib = None
APPINDICATOR_AVAILABLE = False
APPINDICATOR_ERROR = None

try:
    import gi
    _gi = gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib
    _Gtk = Gtk
    _GLib = GLib

    # Try Ayatana first (actively maintained)
    try:
        gi.require_version('AyatanaAppIndicator3', '0.1')
        from gi.repository import AyatanaAppIndicator3 as appindicator
        _appindicator = appindicator
        APPINDICATOR_AVAILABLE = True
    except (ValueError, ImportError):
        # Fallback to legacy AppIndicator3
        try:
            gi.require_version('AppIndicator3', '0.1')
            from gi.repository import AppIndicator3 as appindicator
            _appindicator = appindicator
            APPINDICATOR_AVAILABLE = True
        except (ValueError, ImportError):
            APPINDICATOR_ERROR = "Neither AyatanaAppIndicator3 nor AppIndicator3 available"
except ImportError as e:
    APPINDICATOR_ERROR = f"GObject introspection not available: {e}"
except Exception as e:
    APPINDICATOR_ERROR = f"Failed to initialize AppIndicator: {e}"


def is_wayland():
    """Check if running on Wayland."""
    return (os.environ.get('XDG_SESSION_TYPE') == 'wayland' or
            os.environ.get('WAYLAND_DISPLAY') is not None)


def get_icon_path(icon_name, size=48):
    """Get the path to an icon file.

    Args:
        icon_name: Base name of the icon (e.g., 'taskcoach', 'clock_icon')
        size: Icon size (default 48 for good visibility)

    Returns:
        Absolute path to the icon PNG file, or None if not found
    """
    # Determine base path for icons
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)

    icon_filename = f"{icon_name}{size}x{size}.png"
    icon_path = os.path.join(base_path, 'icons', icon_filename)

    if os.path.exists(icon_path):
        return icon_path

    # Try other sizes as fallback
    for fallback_size in [48, 32, 22, 16, 64, 128]:
        if fallback_size == size:
            continue
        icon_filename = f"{icon_name}{fallback_size}x{fallback_size}.png"
        icon_path = os.path.join(base_path, 'icons', icon_filename)
        if os.path.exists(icon_path):
            return icon_path

    return None


class AppIndicatorIcon:
    """System tray icon using AppIndicator/StatusNotifierItem.

    This class provides a similar interface to wx.adv.TaskBarIcon but uses
    the AppIndicator library for Wayland compatibility.
    """

    def __init__(self, app_id="taskcoach", icon_name="taskcoach",
                 category=None, tooltip="Task Coach"):
        """Initialize the AppIndicator icon.

        Args:
            app_id: Unique identifier for the indicator
            icon_name: Name of the icon (will be looked up in icons folder)
            category: AppIndicator category (defaults to APPLICATION_STATUS)
            tooltip: Tooltip text (used as title since AppIndicator has limited tooltip support)
        """
        if not APPINDICATOR_AVAILABLE:
            raise ImportError(f"AppIndicator not available: {APPINDICATOR_ERROR}")

        self._app_id = app_id
        self._icon_name = icon_name
        self._tooltip = tooltip
        self._menu = None
        self._menu_items = {}
        self._click_callback = None

        # Determine category
        if category is None:
            category = _appindicator.IndicatorCategory.APPLICATION_STATUS

        # Get icon path
        icon_path = get_icon_path(icon_name)
        if icon_path:
            # AppIndicator needs icon path without extension for theme lookup,
            # or full path for custom icons
            self._indicator = _appindicator.Indicator.new(
                app_id,
                icon_path,  # Full path to icon
                category
            )
        else:
            # Fallback to system icon
            self._indicator = _appindicator.Indicator.new(
                app_id,
                "application-default-icon",
                category
            )

        # Set title (shown in some environments)
        self._indicator.set_title(tooltip)

        # Create initial empty menu (required for indicator to show)
        self._create_empty_menu()

        # Activate the indicator
        self._indicator.set_status(_appindicator.IndicatorStatus.ACTIVE)

    def _create_empty_menu(self):
        """Create an empty GTK menu (required for indicator to display)."""
        self._menu = _Gtk.Menu()
        # Add at least one item (invisible indicators may not show)
        item = _Gtk.MenuItem(label="Loading...")
        item.set_sensitive(False)
        self._menu.append(item)
        self._menu.show_all()
        self._indicator.set_menu(self._menu)

    def SetIcon(self, icon_name, tooltip=""):
        """Set the indicator icon and tooltip.

        Args:
            icon_name: Name of the icon (or wx.Icon which will be ignored,
                      use the string name instead)
            tooltip: Tooltip text
        """
        # Handle both string icon names and wx.Icon objects
        if isinstance(icon_name, str):
            self._icon_name = icon_name
            icon_path = get_icon_path(icon_name)
            if icon_path:
                self._indicator.set_icon_full(icon_path, tooltip or self._tooltip)

        if tooltip:
            self._tooltip = tooltip
            self._indicator.set_title(tooltip)

    def set_icon_by_name(self, icon_name, tooltip=""):
        """Set icon by name (string).

        This is the preferred method when you have the icon name as a string.
        """
        self._icon_name = icon_name
        icon_path = get_icon_path(icon_name)
        if icon_path:
            self._indicator.set_icon_full(icon_path, tooltip or self._tooltip)
        if tooltip:
            self._tooltip = tooltip
            self._indicator.set_title(tooltip)

    def set_tooltip(self, tooltip):
        """Set the tooltip/title text."""
        self._tooltip = tooltip
        self._indicator.set_title(tooltip)

    def set_click_callback(self, callback):
        """Set callback for left-click on indicator.

        Note: AppIndicator doesn't support direct left-click handling in the
        same way as wx.TaskBarIcon. The callback will be triggered via a
        menu item instead.
        """
        self._click_callback = callback

    def set_menu(self, menu_builder_callback):
        """Set the menu using a builder callback.

        Args:
            menu_builder_callback: A function that takes (Gtk, menu, click_callback)
                                  and populates the menu with items
        """
        self._menu = _Gtk.Menu()
        menu_builder_callback(_Gtk, self._menu, self._click_callback)
        self._menu.show_all()
        self._indicator.set_menu(self._menu)

    def set_gtk_menu(self, menu):
        """Set a pre-built GTK menu."""
        self._menu = menu
        self._menu.show_all()
        self._indicator.set_menu(self._menu)

    def update_menu(self):
        """Trigger menu update (re-show all items)."""
        if self._menu:
            self._menu.show_all()

    def RemoveIcon(self):
        """Remove/hide the indicator."""
        self._indicator.set_status(_appindicator.IndicatorStatus.PASSIVE)

    def Destroy(self):
        """Clean up the indicator."""
        self.RemoveIcon()
        self._menu = None
        self._indicator = None

    def IsAvailable(self):
        """Check if the indicator is available and active."""
        return (self._indicator is not None and
                self._indicator.get_status() == _appindicator.IndicatorStatus.ACTIVE)

    @property
    def indicator(self):
        """Access the underlying AppIndicator object."""
        return self._indicator


def build_taskcoach_menu(Gtk, menu, mainwindow, taskFile, settings,
                         on_click_callback=None):
    """Build the Task Coach tray menu using GTK.

    This creates a GTK menu with similar items to TaskBarMenu.

    Args:
        Gtk: The Gtk module from gi.repository
        menu: The Gtk.Menu to populate
        mainwindow: The main application window
        taskFile: The task file object
        settings: Application settings
        on_click_callback: Callback for restore/iconize action
    """
    from taskcoachlib.i18n import _
    from taskcoachlib import meta

    # Show/Hide main window
    def on_show_hide(widget):
        if on_click_callback:
            on_click_callback(None)

    show_item = Gtk.MenuItem(label=_("Show/Hide Main Window"))
    show_item.connect('activate', on_show_hide)
    menu.append(show_item)

    menu.append(Gtk.SeparatorMenuItem())

    # New Task
    def on_new_task(widget):
        # Use wx.CallAfter to safely call wx code from GTK callback
        import wx
        wx.CallAfter(mainwindow.createNewTask)

    new_task_item = Gtk.MenuItem(label=_("New task"))
    new_task_item.connect('activate', on_new_task)
    menu.append(new_task_item)

    menu.append(Gtk.SeparatorMenuItem())

    # Quit
    def on_quit(widget):
        import wx
        wx.CallAfter(mainwindow.Close)

    quit_item = Gtk.MenuItem(label=_("Quit"))
    quit_item.connect('activate', on_quit)
    menu.append(quit_item)


def create_indicator_for_taskcoach(mainwindow, taskList, settings):
    """Factory function to create an AppIndicator for Task Coach.

    Args:
        mainwindow: The main application window
        taskList: The task list
        settings: Application settings

    Returns:
        AppIndicatorIcon instance, or None if not available
    """
    if not APPINDICATOR_AVAILABLE:
        return None

    try:
        indicator = AppIndicatorIcon(
            app_id="taskcoach",
            icon_name="taskcoach",
            tooltip="Task Coach"
        )
        return indicator
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"Failed to create AppIndicator: {e}"
        )
        return None
