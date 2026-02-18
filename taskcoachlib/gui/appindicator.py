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



class AppIndicatorIcon:
    """System tray icon using AppIndicator/StatusNotifierItem.

    This class provides a similar interface to wx.adv.TaskBarIcon but uses
    the AppIndicator library for Wayland compatibility.
    """

    def __init__(self, app_id="taskcoach", icon_path=None,
                 category=None, tooltip="Task Coach"):
        """Initialize the AppIndicator icon.

        Args:
            app_id: Unique identifier for the indicator
            icon_path: Absolute path to icon file, or None for system default
            category: AppIndicator category (defaults to APPLICATION_STATUS)
            tooltip: Tooltip text (used as title since AppIndicator has limited tooltip support)
        """
        if not APPINDICATOR_AVAILABLE:
            raise ImportError(f"AppIndicator not available: {APPINDICATOR_ERROR}")

        self._app_id = app_id
        self._tooltip = tooltip
        self._menu = None
        self._menu_items = {}
        self._click_callback = None

        # Determine category
        if category is None:
            category = _appindicator.IndicatorCategory.APPLICATION_STATUS

        self._indicator = _appindicator.Indicator.new(
            app_id,
            icon_path or "application-default-icon",
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

    def set_icon_full(self, icon_path, tooltip=""):
        """Set icon from a file path and tooltip."""
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
