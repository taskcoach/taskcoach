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


def _log_monitor_info():
    """Log information about all monitors."""
    num_monitors = wx.Display.GetCount()
    _log_debug(f"Monitor configuration: {num_monitors} monitors")
    for i in range(num_monitors):
        display = wx.Display(i)
        geom = display.GetGeometry()
        _log_debug(f"  Monitor {i}: x={geom.x}, y={geom.y}, w={geom.width}, h={geom.height}")


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
    3. Cache position to protect against GTK bugs that corrupt GetPosition()
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

        # Cache last known good position (protects against GTK bugs)
        self._cached_position = None
        self._cached_size = None

        # Position monitor state
        self._target_position = None
        self._position_monitor_count = 0

        # Check for Wayland
        self._on_wayland = os.environ.get('XDG_SESSION_TYPE') == 'wayland' or \
                          os.environ.get('WAYLAND_DISPLAY') is not None
        if self._on_wayland:
            _log_debug("Running on Wayland - window positioning blocked by compositor")

        # Log monitor configuration
        _log_monitor_info()

        # Set minimum size
        if isinstance(self._window, wx.Dialog):
            self._window.SetMinSize((400, 300))
        else:
            self._window.SetMinSize((600, 400))

        # Restore dimensions from settings
        self._restore_dimensions()

        # Track position changes to maintain cache
        self._window.Bind(wx.EVT_MOVE, self._on_move)
        self._window.Bind(wx.EVT_SIZE, self._on_size)
        self._window.Bind(wx.EVT_MAXIMIZE, self._on_maximize)

    def _on_move(self, event):
        """Track position changes to cache last known good position."""
        if not self._window.IsIconized() and not self._window.IsMaximized():
            pos = event.GetPosition()
            # Only cache if position looks valid (not near origin which is often GTK bug)
            if pos.x > 50 or pos.y > 30:
                self._cached_position = (pos.x, pos.y)
                _log_debug(f"_on_move: cached position ({pos.x}, {pos.y})")
        event.Skip()

    def _on_size(self, event):
        """Track size changes to cache last known good size."""
        if not self._window.IsIconized() and not self._window.IsMaximized():
            size = event.GetSize()
            if size.width > 100 and size.height > 100:
                self._cached_size = (size.width, size.height)
        event.Skip()

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
                   f"maximized={maximized} saved_monitor={saved_monitor}")

        # Enforce minimum size
        min_w, min_h = self._window.GetMinSize()
        width = max(width, min_w) if width > 0 else min_w
        height = max(height, min_h) if height > 0 else min_h

        # Handle position
        if x == -1 and y == -1:
            # No saved position - center on primary monitor
            _log_debug("  No saved position, centering on primary")
            self._window.SetSize(width, height)
            self._window.Center()
        else:
            # Use saved position directly - it's already absolute screen coordinates
            _log_debug(f"  Setting position directly: ({x}, {y})")
            self._window.SetSize(x, y, width, height)

            # Validate the position is on SOME visible display
            self._ensure_visible_on_screen(width, height)

        if operating_system.isMac():
            self._window.SetClientSize((width, height))

        # Handle maximized state
        if maximized:
            self._window.Maximize()
            self._is_maximized = True

        # Initialize cache with restored position
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        self._cached_position = (pos.x, pos.y)
        self._cached_size = (size.width, size.height)
        _log_debug(f"  Applied: pos=({pos.x}, {pos.y}) size=({size.width}, {size.height})")
        _log_debug(f"  Cache initialized: pos={self._cached_position}")

    def _ensure_visible_on_screen(self, width, height):
        """Ensure at least part of the window is visible on some display."""
        window_rect = self._window.GetRect()
        _log_debug(f"  Checking visibility: window at ({window_rect.x}, {window_rect.y})")

        # Check if window center is on any display
        center_x = window_rect.x + window_rect.width // 2
        center_y = window_rect.y + window_rect.height // 2
        display_at_center = wx.Display.GetFromPoint(wx.Point(center_x, center_y))

        if display_at_center != wx.NOT_FOUND:
            _log_debug(f"  Window center is on display {display_at_center}")
            return  # Window is visible, nothing to do

        # Window is off-screen - center on primary display
        _log_debug("  Window is off-screen, centering on primary")
        primary = wx.Display(0)
        rect = primary.GetGeometry()
        x = rect.x + (rect.width - width) // 2
        y = rect.y + (rect.height - height) // 2
        self._window.SetPosition(wx.Point(x, y))

    def apply_position_after_show(self):
        """Re-apply position after Show() for GTK/X11 compatibility.

        On GTK/X11, SetPosition() before Show() may be ignored due to
        asynchronous window operations. This re-applies the saved position
        after the window is visible.
        """
        x, y = self.get_setting("position")
        maximized = self.get_setting("maximized")

        if maximized or x == -1 or y == -1:
            _log_debug("apply_position_after_show: Nothing to re-apply (maximized or no saved pos)")
            return

        current = self._window.GetPosition()
        _log_debug(f"apply_position_after_show: current=({current.x}, {current.y}) target=({x}, {y})")

        # Re-apply saved position
        self._window.SetPosition(wx.Point(x, y))

        # Verify and cache the final position
        final = self._window.GetPosition()
        _log_debug(f"  Final position: ({final.x}, {final.y})")

        # Update cache with final position
        self._cached_position = (final.x, final.y)
        _log_debug(f"  Cache updated: pos={self._cached_position}")

        if abs(final.x - x) > 50 or abs(final.y - y) > 50:
            if self._on_wayland:
                _log_debug("  Position differs from target (expected on Wayland)")
            else:
                _log_debug("  WARNING: Position differs from target")

        # Start position monitor to detect if something moves the window later
        self._target_position = (x, y)
        self._position_monitor_count = 0
        self._start_position_monitor()

    def _start_position_monitor(self):
        """Monitor position for a few seconds to detect unwanted moves."""
        if self._position_monitor_count >= 10:  # Monitor for 5 seconds (10 x 500ms)
            _log_debug("Position monitor: stopping")
            return

        self._position_monitor_count += 1
        pos = self._window.GetPosition()
        target = self._target_position

        if pos.x != target[0] or pos.y != target[1]:
            _log_debug(f"Position monitor #{self._position_monitor_count}: "
                      f"MOVED from target ({target[0]}, {target[1]}) to ({pos.x}, {pos.y})")
            # Re-apply position
            _log_debug(f"  Re-applying target position ({target[0]}, {target[1]})")
            self._window.SetPosition(wx.Point(target[0], target[1]))
            final = self._window.GetPosition()
            _log_debug(f"  After re-apply: ({final.x}, {final.y})")
            self._cached_position = (final.x, final.y)
        else:
            _log_debug(f"Position monitor #{self._position_monitor_count}: OK at ({pos.x}, {pos.y})")

        # Schedule next check
        wx.CallLater(500, self._start_position_monitor)

    def save_state(self):
        """Save the current window state. Call when window is about to close."""
        maximized = self._window.IsMaximized() or self._is_maximized
        iconized = self._window.IsIconized()

        # Get current position from window
        current_pos = self._window.GetPosition()
        current_size = self._window.GetSize()
        monitor = wx.Display.GetFromWindow(self._window)

        _log_debug(f"SAVE: maximized={maximized} iconized={iconized} monitor={monitor}")
        _log_debug(f"  GetPosition()=({current_pos.x}, {current_pos.y}) GetSize()=({current_size.width}, {current_size.height})")
        _log_debug(f"  Cached: pos={self._cached_position} size={self._cached_size}")

        # Detect GTK bug: position near origin when it shouldn't be
        # Use cached position if current position looks corrupted
        if current_pos.x < 100 and current_pos.y < 50:
            if self._cached_position and (self._cached_position[0] > 100 or self._cached_position[1] > 50):
                _log_debug(f"  GTK BUG DETECTED: Using cached position instead of ({current_pos.x}, {current_pos.y})")
                save_pos = self._cached_position
            else:
                save_pos = (current_pos.x, current_pos.y)
        else:
            save_pos = (current_pos.x, current_pos.y)

        # Use cached size if available and current looks wrong
        if self._cached_size and current_size.width > 100 and current_size.height > 100:
            save_size = (current_size.width, current_size.height)
        elif self._cached_size:
            save_size = self._cached_size
        else:
            save_size = (current_size.width, current_size.height)

        _log_debug(f"  SAVING: pos={save_pos} size={save_size}")

        self.set_setting("maximized", maximized)

        if not iconized:
            self.set_setting("position", save_pos)

            # Determine monitor from saved position
            pos_monitor = wx.Display.GetFromPoint(wx.Point(save_pos[0], save_pos[1]))
            if pos_monitor != wx.NOT_FOUND:
                self.set_setting("monitor_index", pos_monitor)
                _log_debug(f"  Saved monitor_index={pos_monitor}")

            if not maximized:
                if operating_system.isMac():
                    save_size = (self._window.GetClientSize().width, self._window.GetClientSize().height)
                self.set_setting("size", save_size)


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
