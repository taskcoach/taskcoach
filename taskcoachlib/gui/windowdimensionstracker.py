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

import os
import wx
import time
from taskcoachlib import operating_system

# Debug logging for window position tracking (set to False to disable)
_DEBUG_WINDOW_TRACKING = True


def _log_debug(msg):
    """Log debug message with timestamp."""
    if _DEBUG_WINDOW_TRACKING:
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] WindowTracker: {msg}")


class _Tracker:
    """Utility methods for setting and getting values from/to the settings."""

    def __init__(self, settings, section):
        self._settings = settings
        self._section = section

    def set_setting(self, setting, value):
        """Store the value for the setting in the settings."""
        self._settings.setvalue(self._section, setting, value)

    def get_setting(self, setting):
        """Get the value for the setting from the settings and return it."""
        return self._settings.getvalue(self._section, setting)


class WindowSizeAndPositionTracker(_Tracker):
    """Track the size and position of a window in the settings.

    Best practices followed:
    1. Save only on close (not on every EVT_MOVE/EVT_SIZE)
    2. Re-apply position after Show() for GTK/X11 compatibility
    3. Multi-monitor support with monitor index tracking
    4. Uses Task Coach's existing settings keys (with pre-defined defaults)

    Platform notes:
    - X11: Full positioning support, requires re-apply after Show()
    - Wayland: Positioning blocked by compositor (security feature)
    - Windows/macOS: Full support
    """

    def __init__(self, window, settings, section):
        super().__init__(settings, section)
        self._window = window
        self._is_maximized = False

        # Check for Wayland
        self._on_wayland = os.environ.get('XDG_SESSION_TYPE') == 'wayland' or \
                          os.environ.get('WAYLAND_DISPLAY') is not None
        if self._on_wayland:
            _log_debug("Running on Wayland - window positioning blocked by compositor")

        # Set minimum size
        if isinstance(self._window, wx.Dialog):
            self._window.SetMinSize((400, 300))
        else:
            self._window.SetMinSize((600, 400))

        # Restore dimensions from settings
        self._restore_dimensions()

        # Track maximize state (needed because IsMaximized() can be unreliable at close)
        self._window.Bind(wx.EVT_MAXIMIZE, self._on_maximize)

    def _on_maximize(self, event):
        """Track maximize state changes."""
        self._is_maximized = True
        _log_debug("Window maximized")
        event.Skip()

    def _restore_dimensions(self):
        """Restore window dimensions from settings."""
        x, y = self.get_setting("position")
        width, height = self.get_setting("size")
        maximized = self.get_setting("maximized")
        saved_monitor = self.get_setting("monitor_index")
        num_monitors = wx.Display.GetCount()

        _log_debug(f"RESTORE: pos=({x}, {y}) size=({width}, {height}) "
                   f"maximized={maximized} monitor={saved_monitor}/{num_monitors}")

        # Enforce minimum size
        min_w, min_h = self._window.GetMinSize()
        width = max(width, min_w) if width > 0 else min_w
        height = max(height, min_h) if height > 0 else min_h

        # Handle position
        if x == -1 and y == -1:
            # No saved position - center on primary monitor
            _log_debug("  No saved position, centering")
            self._window.SetSize(width, height)
            self._window.Center()
        else:
            # Use saved position
            self._window.SetSize(x, y, width, height)

        if operating_system.isMac():
            self._window.SetClientSize((width, height))

        # Validate position is on screen and correct monitor
        self._validate_position(saved_monitor, num_monitors)

        # Handle maximized state
        if maximized:
            self._window.Maximize()
            self._is_maximized = True

        pos = self._window.GetPosition()
        size = self._window.GetSize()
        _log_debug(f"  Applied: pos=({pos.x}, {pos.y}) size=({size.width}, {size.height})")

    def _validate_position(self, saved_monitor, num_monitors):
        """Ensure window is visible on the correct display."""
        current_display = wx.Display.GetFromWindow(self._window)

        if current_display == wx.NOT_FOUND:
            # Window is off-screen - move to saved monitor or primary
            _log_debug("  Window is off-screen")
            if saved_monitor is not None and 0 <= saved_monitor < num_monitors:
                target_display = wx.Display(saved_monitor)
            else:
                target_display = wx.Display(0)

            rect = target_display.GetGeometry()
            size = self._window.GetSize()
            x = rect.x + (rect.width - size.width) // 2
            y = rect.y + (rect.height - size.height) // 2
            _log_debug(f"  Centering on display: ({x}, {y})")
            self._window.SetPosition(wx.Point(x, y))

        elif saved_monitor is not None and saved_monitor != current_display:
            # Window on different monitor than saved
            if 0 <= saved_monitor < num_monitors:
                _log_debug(f"  Window on monitor {current_display}, should be on {saved_monitor}")
                target_display = wx.Display(saved_monitor)
                rect = target_display.GetGeometry()
                pos = self._window.GetPosition()
                size = self._window.GetSize()

                # Calculate position on target monitor (preserve relative position)
                current_rect = wx.Display(current_display).GetGeometry()
                rel_x = pos.x - current_rect.x
                rel_y = pos.y - current_rect.y
                new_x = rect.x + rel_x
                new_y = rect.y + rel_y

                # Ensure window fits on target monitor
                new_x = max(rect.x, min(new_x, rect.x + rect.width - size.width))
                new_y = max(rect.y, min(new_y, rect.y + rect.height - size.height))

                _log_debug(f"  Moving to saved monitor: ({new_x}, {new_y})")
                self._window.SetPosition(wx.Point(new_x, new_y))
            else:
                _log_debug(f"  Saved monitor {saved_monitor} no longer exists")
        else:
            # Check visibility
            display = wx.Display(current_display)
            display_rect = display.GetGeometry()
            window_rect = self._window.GetRect()

            visible_left = max(window_rect.x, display_rect.x)
            visible_right = min(window_rect.x + window_rect.width,
                               display_rect.x + display_rect.width)
            visible_top = max(window_rect.y, display_rect.y)
            visible_bottom = min(window_rect.y + window_rect.height,
                                display_rect.y + display_rect.height)

            if (visible_right - visible_left) < 50 or (visible_bottom - visible_top) < 50:
                _log_debug("  Window barely visible, centering")
                self._window.Center()

    def apply_position_after_show(self):
        """Re-apply position after Show() for GTK/X11 compatibility.

        On GTK/X11, SetPosition() before Show() may be ignored due to
        asynchronous window operations. This re-applies the saved position
        after the window is visible.
        """
        x, y = self.get_setting("position")
        maximized = self.get_setting("maximized")

        if maximized or x == -1 or y == -1:
            _log_debug("apply_position_after_show: Nothing to re-apply")
            return

        current = self._window.GetPosition()
        _log_debug(f"apply_position_after_show: current=({current.x}, {current.y}) target=({x}, {y})")

        # Only re-apply if significantly different
        if abs(current.x - x) > 20 or abs(current.y - y) > 20:
            _log_debug(f"  Re-applying position ({x}, {y})")
            self._window.SetPosition(wx.Point(x, y))

            final = self._window.GetPosition()
            _log_debug(f"  Final position: ({final.x}, {final.y})")

            if abs(final.x - x) > 50 or abs(final.y - y) > 50:
                if self._on_wayland:
                    _log_debug("  Position not applied (expected on Wayland)")
                else:
                    _log_debug("  WARNING: Position not applied correctly")

    def save_state(self):
        """Save the current window state. Call when window is about to close."""
        maximized = self._window.IsMaximized() or self._is_maximized
        iconized = self._window.IsIconized()
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        monitor = wx.Display.GetFromWindow(self._window)

        _log_debug(f"SAVE: maximized={maximized} iconized={iconized} monitor={monitor}")
        _log_debug(f"  pos=({pos.x}, {pos.y}) size=({size.width}, {size.height})")

        self.set_setting("maximized", maximized)

        if not iconized:
            self.set_setting("position", (pos.x, pos.y))
            if monitor != wx.NOT_FOUND:
                self.set_setting("monitor_index", monitor)

            if not maximized:
                save_size = (self._window.GetClientSize() if operating_system.isMac()
                            else size)
                self.set_setting("size", (save_size.width, save_size.height))


class WindowDimensionsTracker(WindowSizeAndPositionTracker):
    """Track the dimensions of the main window in the settings."""

    def __init__(self, window, settings):
        super().__init__(window, settings, "window")

        # Handle start iconized setting (Task Coach specific)
        if self._should_start_iconized():
            if operating_system.isMac() or operating_system.isGTK():
                self._window.Show()
            self._window.Iconize(True)
            if not operating_system.isMac() and self.get_setting("hidewheniconized"):
                wx.CallAfter(self._window.Hide)

    def _should_start_iconized(self):
        """Return whether the window should be opened iconized."""
        start_iconized = self._settings.get("window", "starticonized")
        if start_iconized == "Always":
            return True
        if start_iconized == "Never":
            return False
        return self.get_setting("iconized")

    def save_position(self):
        """Save the position of the window in the settings.

        Called when window is about to close.
        """
        # Save iconized state (Task Coach specific)
        self.set_setting("iconized", self._window.IsIconized())

        # Save position/size/maximized/monitor via parent
        self.save_state()
