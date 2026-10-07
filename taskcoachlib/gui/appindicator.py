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

import warnings

# Try to import AppIndicator (Ayatana version preferred, fallback to legacy)
_appindicator = None
_gi = None
_Gtk = None
_GLib = None
_GdkPixbuf = None
APPINDICATOR_AVAILABLE = False
APPINDICATOR_ERROR = None

try:
    import gi

    _gi = gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import Gtk, GLib, GdkPixbuf

    _Gtk = Gtk
    _GLib = GLib
    _GdkPixbuf = GdkPixbuf

    # Try Ayatana first (actively maintained)
    try:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as appindicator

        _appindicator = appindicator
        APPINDICATOR_AVAILABLE = True
    except (ValueError, ImportError):
        # Fallback to legacy AppIndicator3
        try:
            gi.require_version("AppIndicator3", "0.1")
            from gi.repository import AppIndicator3 as appindicator

            _appindicator = appindicator
            APPINDICATOR_AVAILABLE = True
        except (ValueError, ImportError):
            APPINDICATOR_ERROR = (
                "Neither AyatanaAppIndicator3 nor AppIndicator3 available"
            )
except ImportError as e:
    APPINDICATOR_ERROR = f"GObject introspection not available: {e}"
except Exception as e:
    APPINDICATOR_ERROR = f"Failed to initialize AppIndicator: {e}"


class _MenuImages:
    """The menu items' icons, each read from its file once, as the
    lists' shared image list. Where GTK draws the menu (no tray host:
    the fallback icon), an item names its icon, so the tray library
    hands over a name instead of turning every item's picture into
    image data (docs/SYSTEM_TRAY.md, Menu Icons)."""

    def __init__(self):
        self.__pixbufs = {}  # path: GdkPixbuf.Pixbuf, None if unreadable
        self.__names = {}  # path: icon name, registered with GTK

    def image(self, path, by_name):
        pixbuf = self.__pixbuf(path)
        if pixbuf is None:
            return None
        if not by_name:
            # A tray host draws the menu: it needs the picture itself
            return _Gtk.Image.new_from_pixbuf(pixbuf)
        name = self.__names.get(path)
        if name is None:
            name = "taskcoach-menu-%d" % len(self.__names)
            with warnings.catch_warnings():
                # Deprecated since GTK 3.14 for resource bundles; the
                # tray library is GTK 3's
                warnings.simplefilter("ignore", DeprecationWarning)
                _Gtk.IconTheme.add_builtin_icon(
                    name, pixbuf.get_width(), pixbuf
                )
            self.__names[path] = name
        return _Gtk.Image.new_from_icon_name(name, _Gtk.IconSize.MENU)

    def __pixbuf(self, path):
        if path not in self.__pixbufs:
            try:
                pixbuf = _GdkPixbuf.Pixbuf.new_from_file(path)
            except _GLib.Error:
                pixbuf = None
            self.__pixbufs[path] = pixbuf
        return self.__pixbufs[path]


# GTK's icon names are the process's: one set for every menu
_menu_images = _MenuImages()


class AppIndicatorIcon:
    """System tray icon using AppIndicator/StatusNotifierItem.

    This class provides a similar interface to wx.adv.TaskBarIcon but uses
    the AppIndicator library for Wayland compatibility.
    """

    def __init__(
        self,
        app_id="taskcoach",
        icon_name=None,
        icon_theme_path=None,
        category=None,
        tooltip="Task Coach",
    ):
        """Initialize the AppIndicator icon.

        Args:
            app_id: Unique identifier for the indicator
            icon_name: Icon theme name (e.g. "taskcoach-app"), resolved via
                icon_theme_path when set; or None for system default
            icon_theme_path: Parent directory containing a hicolor/ theme with
                the icon PNGs.  Passed to set_icon_theme_path() so the SNI
                host finds our bundled icons instead of system-theme icons.
            category: AppIndicator category (defaults to APPLICATION_STATUS)
            tooltip: Tooltip text (used as title since AppIndicator has limited tooltip support)
        """
        if not APPINDICATOR_AVAILABLE:
            raise ImportError(
                f"AppIndicator not available: {APPINDICATOR_ERROR}"
            )

        self._tooltip = tooltip
        self._menu = None

        # Determine category
        if category is None:
            category = _appindicator.IndicatorCategory.APPLICATION_STATUS

        self._indicator = _appindicator.Indicator.new(
            app_id, icon_name or "application-default-icon", category
        )

        if icon_theme_path:
            self._indicator.set_icon_theme_path(icon_theme_path)

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

    def set_icon_full(self, icon_name, tooltip=""):
        """Set icon by theme name and tooltip."""
        if icon_name:
            self._indicator.set_icon_full(icon_name, tooltip or self._tooltip)
        if tooltip:
            self._tooltip = tooltip
            self._indicator.set_title(tooltip)

    def set_tooltip(self, tooltip):
        """Set the tooltip/title text."""
        self._tooltip = tooltip
        self._indicator.set_title(tooltip)

    def menu_image(self, path):
        """The Gtk.Image of a menu item's icon file, prepared once."""
        return _menu_images.image(path, by_name=not self.is_connected())

    def is_connected(self):
        """Whether a tray host draws the menu (StatusNotifierItem);
        otherwise GTK draws it in this process (the fallback icon)."""
        return bool(self._indicator.get_property("connected"))

    def on_connection_changed(self, callback):
        self._indicator.connect("connection-changed", lambda *args: callback())

    def set_gtk_menu(self, menu):
        """Set a pre-built GTK menu."""
        self._menu = menu
        self._menu.show_all()
        self._indicator.set_menu(self._menu)

    def RemoveIcon(self):
        """Remove/hide the indicator."""
        self._indicator.set_status(_appindicator.IndicatorStatus.PASSIVE)

    def Destroy(self):
        """Clean up the indicator."""
        self.RemoveIcon()
        self._menu = None
        self._indicator = None
