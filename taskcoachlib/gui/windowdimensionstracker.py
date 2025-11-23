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

import configparser
import wx
import time
from taskcoachlib import operating_system

# Debug logging for window position tracking (set to False to disable)
_DEBUG_WINDOW_TRACKING = True


def _log_debug(msg):
    """Log debug message with timestamp."""
    if _DEBUG_WINDOW_TRACKING:
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")


class _Tracker(object):
    """Utility methods for setting and getting values from/to the
    settings."""

    def __init__(self, settings, section):
        super().__init__()
        self.__settings = settings
        self.__section = section

    def set_setting(self, setting, value):
        """Store the value for the setting in the settings."""
        self.__settings.setvalue(self.__section, setting, value)

    def get_setting(self, setting):
        """Get the value for the setting from the settings and return it."""
        return self.__settings.getvalue(self.__section, setting)


class WindowSizeAndPositionTracker(_Tracker):
    """Track the size and position of a window in the settings.

    DESIGN NOTE: Save only on close.

    Previously, we tried to save position/size on every EVT_MOVE/EVT_SIZE event.
    This caused problems because GTK and our own code generate many spurious
    resize/move events during window initialization:

    - AUI LoadPerspective() triggers layout events
    - SendSizeEvent() in showStatusBar(), toolbar changes, etc.
    - GTK window realization sends configure events asynchronously
    - Window manager placement events

    There's no reliable way to distinguish "user-initiated" events from
    "system-initiated" events in wxWidgets/GTK.

    SOLUTION: Only save window state when the window is closed.
    - Simpler implementation (no event handlers for saving)
    - No spurious saves during initialization
    - Only saves the final stable state the user intended
    - Uses the existing save_position() method called on EVT_CLOSE

    The only event we track is EVT_MAXIMIZE to update the maximized state,
    since IsMaximized() may not be accurate if called during close.
    """

    def __init__(self, window, settings, section):
        super().__init__(settings, section)
        self._window = window
        self._section = section  # Store for logging
        self._is_maximized = False

        # Restore window dimensions from settings
        self.__set_dimensions()

        # Only track maximize state - position/size saved on close
        self._window.Bind(wx.EVT_MAXIMIZE, self._on_maximize)

    def _on_maximize(self, event):
        """Track maximize state changes."""
        self._is_maximized = True
        _log_debug("Window maximized")
        event.Skip()

    def save_state(self):
        """Save the current window state. Call when window is about to close."""
        maximized = self._window.IsMaximized() or self._is_maximized
        iconized = self._window.IsIconized()

        _log_debug(f"save_state: maximized={maximized} iconized={iconized}")

        self.set_setting("maximized", maximized)

        if not maximized and not iconized:
            # Get current position and size
            pos = self._window.GetPosition()
            size = (
                self._window.GetClientSize()
                if operating_system.isMac()
                else self._window.GetSize()
            )

            _log_debug(f"save_state: SAVING pos={pos} size={size}")
            self.set_setting("position", pos)
            self.set_setting("size", size)

            # For dialogs, save offset from parent
            if isinstance(self._window, wx.Dialog):
                self._save_dialog_offset(pos)

    def _save_dialog_offset(self, pos):
        """Save dialog offset from parent for multi-monitor support."""
        parent = self._window.GetParent()
        if not parent:
            return

        parent_rect = parent.GetScreenRect()
        parent_monitor = wx.Display.GetFromPoint(
            wx.Point(parent_rect.x + parent_rect.width // 2,
                     parent_rect.y + parent_rect.height // 2)
        )
        dialog_rect = self._window.GetScreenRect()
        dialog_monitor = wx.Display.GetFromPoint(
            wx.Point(dialog_rect.x + dialog_rect.width // 2,
                     dialog_rect.y + dialog_rect.height // 2)
        )

        try:
            if parent_monitor != wx.NOT_FOUND and parent_monitor == dialog_monitor:
                offset = (pos.x - parent_rect.x, pos.y - parent_rect.y)
                self.set_setting("parent_offset", offset)
            else:
                # Dialog on different monitor - save null offset to force re-center
                self.set_setting("parent_offset", (-1, -1))
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass  # Old settings section without parent_offset support

    def __set_dimensions(self):
        """Set the window position and size based on the settings."""
        x, y = self.get_setting("position")
        width, height = self.get_setting("size")
        _log_debug(f"RESTORING: pos=({x}, {y}) size=({width}, {height})")

        # Enforce minimum window size
        if isinstance(self._window, wx.Dialog):
            min_width, min_height = 400, 300
        else:
            min_width, min_height = 600, 400

        width = max(width, min_width)
        height = max(height, min_height)
        if width <= 0 or height <= 0:
            width, height = min_width, min_height

        self._window.SetMinSize((min_width, min_height))

        # Position the window
        x, y = self._calculate_position(x, y, width, height)

        if operating_system.isMac():
            if not isinstance(self._window, wx.Dialog):
                height += 18

        self._window.SetSize(x, y, width, height)

        if operating_system.isMac():
            self._window.SetClientSize((width, height))

        maximized = self.get_setting("maximized")
        if maximized:
            self._window.Maximize()
            self._is_maximized = True

        # Validate window is on a visible display
        self._validate_window_position(width, height)

        final_rect = self._window.GetRect()
        _log_debug(f"APPLIED: pos=({final_rect.x}, {final_rect.y}) size=({final_rect.width}, {final_rect.height})")

    def _calculate_position(self, x, y, width, height):
        """Calculate the window position, handling dialogs and multi-monitor."""
        if isinstance(self._window, wx.Dialog):
            return self._calculate_dialog_position(x, y, width, height)
        else:
            return self._calculate_main_window_position(x, y, width, height)

    def _calculate_dialog_position(self, x, y, width, height):
        """Calculate dialog position relative to parent."""
        parent = self._window.GetParent()
        if not parent:
            return (50, 50) if x == -1 and y == -1 else (x, y)

        parent_rect = parent.GetScreenRect()
        parent_monitor = wx.Display.GetFromPoint(
            wx.Point(parent_rect.x + parent_rect.width // 2,
                     parent_rect.y + parent_rect.height // 2)
        )

        try:
            offset_x, offset_y = self.get_setting("parent_offset")
        except (KeyError, TypeError, configparser.NoSectionError, configparser.NoOptionError):
            offset_x, offset_y = -1, -1

        if offset_x != -1 and offset_y != -1:
            proposed_x = parent_rect.x + offset_x
            proposed_y = parent_rect.y + offset_y
            test_x = proposed_x + width // 2
            test_y = proposed_y + height // 2
            proposed_monitor = wx.Display.GetFromPoint(wx.Point(test_x, test_y))

            if proposed_monitor != wx.NOT_FOUND and proposed_monitor == parent_monitor:
                return proposed_x, proposed_y

        # Center on parent
        return (parent_rect.x + (parent_rect.width - width) // 2,
                parent_rect.y + (parent_rect.height - height) // 2)

    def _calculate_main_window_position(self, x, y, width, height):
        """Calculate main window position with multi-monitor support."""
        saved_monitor = self.get_setting("monitor_index")
        num_monitors = wx.Display.GetCount()

        if x == -1 and y == -1:
            # No saved position - center on primary
            primary = wx.Display(0)
            rect = primary.GetGeometry()
            return (rect.x + (rect.width - width) // 2,
                    rect.y + (rect.height - height) // 2)

        if saved_monitor >= 0 and saved_monitor < num_monitors:
            # Saved monitor exists - use saved position
            return x, y

        if saved_monitor == -1:
            # Legacy settings - use saved position
            return x, y

        # Saved monitor no longer exists - center on primary
        primary = wx.Display(0)
        rect = primary.GetGeometry()
        return (rect.x + (rect.width - width) // 2,
                rect.y + (rect.height - height) // 2)

    def _validate_window_position(self, width, height):
        """Ensure window is visible on a display."""
        display_index = wx.Display.GetFromWindow(self._window)

        if display_index == wx.NOT_FOUND:
            # Window is off-screen - move to safe position
            self._window.SetSize(50, 50, width, height)
            if operating_system.isMac():
                self._window.SetClientSize((width, height))
            return

        # Check window is sufficiently visible
        display = wx.Display(display_index)
        display_rect = display.GetGeometry()
        window_rect = self._window.GetRect()

        visible_left = max(window_rect.x, display_rect.x)
        visible_top = max(window_rect.y, display_rect.y)
        visible_right = min(window_rect.x + window_rect.width,
                           display_rect.x + display_rect.width)
        visible_bottom = min(window_rect.y + window_rect.height,
                            display_rect.y + display_rect.height)

        visible_width = visible_right - visible_left
        visible_height = visible_bottom - visible_top

        if visible_width < 50 or visible_height < 50:
            # Less than 50px visible - center on display
            center_x = display_rect.x + (display_rect.width - width) // 2
            center_y = display_rect.y + (display_rect.height - height) // 2
            self._window.SetSize(center_x, center_y, width, height)
            if operating_system.isMac():
                self._window.SetClientSize((width, height))


class WindowDimensionsTracker(WindowSizeAndPositionTracker):
    """Track the dimensions of the main window in the settings."""

    def __init__(self, window, settings):
        super().__init__(window, settings, "window")
        self.__settings = settings

        if self.__start_iconized():
            if operating_system.isMac() or operating_system.isGTK():
                self._window.Show()
            self._window.Iconize(True)
            if not operating_system.isMac() and self.get_setting("hidewheniconized"):
                wx.CallAfter(self._window.Hide)

    def __start_iconized(self):
        """Return whether the window should be opened iconized."""
        start_iconized = self.__settings.get("window", "starticonized")
        if start_iconized == "Always":
            return True
        if start_iconized == "Never":
            return False
        return self.get_setting("iconized")

    def save_position(self):
        """Save the position of the window in the settings.

        Called when window is about to close.
        """
        iconized = self._window.IsIconized()
        pos = self._window.GetPosition()
        monitor_index = wx.Display.GetFromWindow(self._window)

        _log_debug(f"save_position: pos={pos} monitor={monitor_index} iconized={iconized}")

        self.set_setting("iconized", iconized)

        if not iconized:
            # Save position and monitor
            self.set_setting("position", pos)
            if monitor_index != wx.NOT_FOUND:
                self.set_setting("monitor_index", monitor_index)

            # Save size if not maximized
            if not self._window.IsMaximized() and not self._is_maximized:
                size = (
                    self._window.GetClientSize()
                    if operating_system.isMac()
                    else self._window.GetSize()
                )
                _log_debug(f"save_position: SAVING size={size}")
                self.set_setting("size", size)

        # Save maximized state
        self.set_setting("maximized", self._window.IsMaximized() or self._is_maximized)
