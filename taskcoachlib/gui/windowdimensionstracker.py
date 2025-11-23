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

    Uses two-phase initialization to handle GTK's behavior of ignoring
    window position when set before Show(). The position is set initially
    in __set_dimensions(), then re-applied after the window is shown.
    """

    def __init__(self, window, settings, section):
        super().__init__(settings, section)
        self._window = window
        self._section = section  # Store for logging
        self._is_maximized = False
        self._position_applied = False

        # Target position/size to restore
        self._target_x = 0
        self._target_y = 0
        self._target_width = 600
        self._target_height = 400
        self._target_maximized = False

        # Restore window dimensions from settings
        self.__set_dimensions()

        # Bind events
        self._window.Bind(wx.EVT_MAXIMIZE, self._on_maximize)

    def _on_maximize(self, event):
        """Track maximize state changes."""
        self._is_maximized = True
        _log_debug("Window maximized")
        event.Skip()

    def apply_position_after_show(self):
        """Re-apply window position after Show().

        GTK ignores SetSize() position when called before Show(). Call this
        method after the window has been shown to ensure position is applied.
        """
        if self._position_applied:
            return

        self._position_applied = True

        if self._target_maximized:
            _log_debug(f"apply_position_after_show: Window should be maximized")
            self._window.Maximize()
            self._is_maximized = True
            return

        x, y = self._target_x, self._target_y
        _log_debug(f"apply_position_after_show: Setting position to ({x}, {y})")

        # Use SetPosition to apply saved position
        self._window.SetPosition(wx.Point(x, y))

        # Verify it was applied
        final_pos = self._window.GetPosition()
        _log_debug(f"apply_position_after_show: Final position is ({final_pos.x}, {final_pos.y})")

    def save_state(self):
        """Save the current window state. Call when window is about to close."""
        maximized = self._window.IsMaximized() or self._is_maximized
        iconized = self._window.IsIconized()

        _log_debug(f"save_state: maximized={maximized} iconized={iconized}")

        self.set_setting("maximized", maximized)

        if not maximized and not iconized:
            pos = self._window.GetPosition()
            size = (
                self._window.GetClientSize()
                if operating_system.isMac()
                else self._window.GetSize()
            )

            _log_debug(f"save_state: SAVING pos={pos} size={size}")
            self.set_setting("position", pos)
            self.set_setting("size", size)

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
                self.set_setting("parent_offset", (-1, -1))
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass

    def __set_dimensions(self):
        """Set the window position and size based on the settings."""
        x, y = self.get_setting("position")
        width, height = self.get_setting("size")
        saved_monitor = self.get_setting("monitor_index")
        num_monitors = wx.Display.GetCount()

        _log_debug(f"RESTORING: pos=({x}, {y}) size=({width}, {height}) "
                   f"saved_monitor={saved_monitor} num_monitors={num_monitors}")

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

        # Calculate position
        if not isinstance(self._window, wx.Dialog):
            if saved_monitor >= 0 and saved_monitor >= num_monitors:
                _log_debug(f"  Saved monitor {saved_monitor} no longer exists, centering")
                primary = wx.Display(0)
                rect = primary.GetGeometry()
                x = rect.x + (rect.width - width) // 2
                y = rect.y + (rect.height - height) // 2
            elif x == -1 and y == -1:
                _log_debug(f"  No saved position, centering on primary")
                primary = wx.Display(0)
                rect = primary.GetGeometry()
                x = rect.x + (rect.width - width) // 2
                y = rect.y + (rect.height - height) // 2
        else:
            x, y = self._calculate_dialog_position(x, y, width, height)

        if operating_system.isMac():
            if not isinstance(self._window, wx.Dialog):
                height += 18

        # Store target for re-application after Show()
        self._target_x = x
        self._target_y = y
        self._target_width = width
        self._target_height = height
        self._target_maximized = self.get_setting("maximized")

        _log_debug(f"  Setting initial size: pos=({x}, {y}) size=({width}, {height})")

        # Set size and position
        self._window.SetSize(x, y, width, height)

        if operating_system.isMac():
            self._window.SetClientSize((width, height))

        # Note: Maximize is deferred to apply_position_after_show()
        # because on GTK, maximizing before Show() can cause position issues

        # Validate window is on a visible display
        self._validate_window_position(width, height)

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

        return (parent_rect.x + (parent_rect.width - width) // 2,
                parent_rect.y + (parent_rect.height - height) // 2)

    def _validate_window_position(self, width, height):
        """Ensure window is visible on a display."""
        display_index = wx.Display.GetFromWindow(self._window)

        if display_index == wx.NOT_FOUND:
            self._window.SetSize(50, 50, width, height)
            if operating_system.isMac():
                self._window.SetClientSize((width, height))
            return

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
        maximized = self._window.IsMaximized() or self._is_maximized
        pos = self._window.GetPosition()
        monitor_index = wx.Display.GetFromWindow(self._window)

        _log_debug(f"save_position: iconized={iconized} maximized={maximized}")
        _log_debug(f"  GetPosition()={pos}")
        _log_debug(f"  monitor={monitor_index}")

        self.set_setting("iconized", iconized)

        if not iconized:
            _log_debug(f"  SAVING position={pos}")
            self.set_setting("position", pos)
            if monitor_index != wx.NOT_FOUND:
                self.set_setting("monitor_index", monitor_index)

            if not maximized:
                size = (
                    self._window.GetClientSize()
                    if operating_system.isMac()
                    else self._window.GetSize()
                )
                _log_debug(f"  SAVING size={size}")
                self.set_setting("size", size)

        self.set_setting("maximized", maximized)
