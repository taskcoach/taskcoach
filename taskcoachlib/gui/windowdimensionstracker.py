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

    IMPORTANT: On GTK with AUI, LoadPerspective() triggers async layout
    that moves the window AFTER Show(). We handle this by:
    1. NOT setting position in __init__ (it will be overwritten)
    2. Setting position ONCE in apply_position_after_show() after AUI settles
    3. Caching position on EVT_MOVE to protect against GTK bugs at close

    Platform notes:
    - X11/GTK: Position must be set after Show() AND after AUI settles
    - Wayland: Positioning blocked by compositor (security feature)
    - Windows/macOS: Full support
    """

    def __init__(self, window, settings, section):
        super().__init__(settings, section)
        self._window = window
        self._is_maximized = False
        self._position_applied = False

        # Cache last known good position (protects against GTK bugs at close)
        self._cached_position = None
        self._cached_size = None

        # Position logging timer
        self._pos_log_count = 0
        self._pos_log_timer = None

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

        # Restore SIZE only (position will be set after Show + AUI settles)
        self._restore_size_only()

        # Track position changes to cache last known good position
        self._window.Bind(wx.EVT_MOVE, self._on_move)
        self._window.Bind(wx.EVT_SIZE, self._on_size)
        self._window.Bind(wx.EVT_MAXIMIZE, self._on_maximize)

        # Start rapid position logging
        self._start_position_logging()

    def _on_move(self, event):
        """Cache position on moves (for save, protects against GTK bugs)."""
        if self._position_applied and not self._window.IsIconized() and not self._window.IsMaximized():
            pos = event.GetPosition()
            # Only cache if position looks valid
            if pos.x > 50 or pos.y > 30:
                self._cached_position = (pos.x, pos.y)
        event.Skip()

    def _on_size(self, event):
        """Cache size on resizes."""
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

    def _start_position_logging(self):
        """Start rapid position logging: 100ms for 2s, then 1s intervals."""
        self._pos_log_start_time = time.time()
        self._log_position_tick()

    def _log_position_tick(self):
        """Log current position and schedule next tick."""
        if not self._window:
            return

        elapsed = time.time() - self._pos_log_start_time
        pos = self._window.GetPosition()
        shown = self._window.IsShown()
        ms = int((elapsed % 1) * 1000)

        _log_debug(f"POS_LOG [{elapsed:.1f}s]: ({pos.x}, {pos.y}) shown={shown} applied={self._position_applied}")

        self._pos_log_count += 1

        # First 2 seconds: log every 100ms (20 logs)
        # After that: log every 1000ms
        if elapsed < 2.0:
            interval = 100
        else:
            interval = 1000

        # Stop after 10 seconds total
        if elapsed < 10.0:
            self._pos_log_timer = wx.CallLater(interval, self._log_position_tick)

    def _restore_size_only(self):
        """Restore size and provide position hint. Final position set after AUI."""
        x, y = self.get_setting("position")
        width, height = self.get_setting("size")
        maximized = self.get_setting("maximized")

        _log_debug(f"RESTORE: pos=({x}, {y}) size=({width}, {height}) maximized={maximized}")

        # Enforce minimum size
        min_w, min_h = self._window.GetMinSize()
        width = max(width, min_w) if width > 0 else min_w
        height = max(height, min_h) if height > 0 else min_h

        # Use 4-parameter SetSize to provide position HINT to window manager
        # GTK may not honor this before Show(), but it influences initial placement
        if x == -1 and y == -1:
            # No saved position - just set size, let window manager center
            self._window.SetSize(width, height)
        else:
            # Provide position hint along with size
            self._window.SetSize(x, y, width, height)

        if operating_system.isMac():
            self._window.SetClientSize((width, height))

        # Handle maximized state
        if maximized:
            self._window.Maximize()
            self._is_maximized = True

        # Initialize cache
        self._cached_size = (width, height)

    def _validate_position(self, x, y, width, height):
        """Validate position fits on a monitor. Returns adjusted (x, y) or None to center.

        Ensures at least 100px of the window is visible on some monitor.
        """
        # Check if position is on any monitor
        num_displays = wx.Display.GetCount()
        _log_debug(f"_validate_position: checking ({x}, {y}) against {num_displays} monitors")

        for i in range(num_displays):
            display = wx.Display(i)
            geometry = display.GetGeometry()
            _log_debug(f"  Monitor {i}: {geometry.x}, {geometry.y}, {geometry.width}x{geometry.height}")

            # Check if window top-left corner is reasonably within this monitor
            # Allow some tolerance - window should have at least 100px visible
            if (geometry.x - width + 100 <= x <= geometry.x + geometry.width - 100 and
                geometry.y <= y <= geometry.y + geometry.height - 100):
                _log_debug(f"  Position valid for monitor {i}")

                # Ensure window doesn't go below the monitor
                max_y = geometry.y + geometry.height - height - 50  # 50px margin for taskbar
                if y > max_y:
                    _log_debug(f"  Adjusting Y from {y} to {max_y} (would go below monitor)")
                    y = max(geometry.y, max_y)

                return (x, y)

        _log_debug(f"  Position ({x}, {y}) not valid for any monitor, will center")
        return None

    def apply_position_after_show(self):
        """Apply saved position after Show() and AUI has settled.

        This is called via CallLater AFTER Show(). We use EVT_IDLE to wait
        for AUI's async layout to complete before setting position.
        """
        if self._position_applied:
            return

        x, y = self.get_setting("position")
        maximized = self.get_setting("maximized")

        if maximized:
            _log_debug("apply_position_after_show: Window is maximized, skipping position")
            self._position_applied = True
            return

        if x == -1 and y == -1:
            _log_debug("apply_position_after_show: No saved position, centering")
            self._window.Center()
            self._position_applied = True
            pos = self._window.GetPosition()
            self._cached_position = (pos.x, pos.y)
            return

        # Validate position fits on a monitor
        size = self._window.GetSize()
        validated = self._validate_position(x, y, size.width, size.height)

        if validated is None:
            _log_debug("apply_position_after_show: Saved position invalid, centering")
            self._window.Center()
            self._position_applied = True
            pos = self._window.GetPosition()
            self._cached_position = (pos.x, pos.y)
            return

        x, y = validated
        _log_debug(f"apply_position_after_show: Will set position to ({x}, {y}) on next idle")

        # Use EVT_IDLE to wait for AUI to finish its async layout
        self._target_position = (x, y)
        self._idle_count = 0
        self._window.Bind(wx.EVT_IDLE, self._on_idle_set_position)

    def _on_idle_set_position(self, event):
        """Set position on idle, after AUI has settled."""
        self._idle_count += 1

        # Wait a few idle cycles for AUI to fully settle
        if self._idle_count < 3:
            event.RequestMore()  # Request more idle events
            return

        # Unbind immediately to avoid repeated calls
        self._window.Unbind(wx.EVT_IDLE, handler=self._on_idle_set_position)
        self._position_applied = True

        x, y = self._target_position
        current = self._window.GetPosition()
        _log_debug(f"_on_idle_set_position: current=({current.x}, {current.y}) target=({x}, {y})")

        # Set position
        self._window.SetPosition(wx.Point(x, y))

        # Verify
        final = self._window.GetPosition()
        _log_debug(f"  Final position: ({final.x}, {final.y})")
        self._cached_position = (final.x, final.y)

        if abs(final.x - x) > 50 or abs(final.y - y) > 50:
            if self._on_wayland:
                _log_debug("  Position differs (expected on Wayland)")
            else:
                _log_debug("  WARNING: Position differs from target")

    def save_state(self):
        """Save the current window state. Call when window is about to close."""
        maximized = self._window.IsMaximized() or self._is_maximized
        iconized = self._window.IsIconized()

        current_pos = self._window.GetPosition()
        current_size = self._window.GetSize()
        monitor = wx.Display.GetFromWindow(self._window)

        _log_debug(f"SAVE: maximized={maximized} iconized={iconized} monitor={monitor}")
        _log_debug(f"  GetPosition()=({current_pos.x}, {current_pos.y})")
        _log_debug(f"  Cached: pos={self._cached_position}")

        # Use cached position if current looks corrupted (GTK bug)
        if current_pos.x < 100 and current_pos.y < 50:
            if self._cached_position and (self._cached_position[0] > 100 or self._cached_position[1] > 50):
                _log_debug(f"  Using cached position (GTK bug workaround)")
                save_pos = self._cached_position
            else:
                save_pos = (current_pos.x, current_pos.y)
        else:
            save_pos = (current_pos.x, current_pos.y)

        save_size = self._cached_size if self._cached_size else (current_size.width, current_size.height)

        _log_debug(f"  SAVING: pos={save_pos} size={save_size}")

        self.set_setting("maximized", maximized)

        if not iconized:
            self.set_setting("position", save_pos)

            pos_monitor = wx.Display.GetFromPoint(wx.Point(save_pos[0], save_pos[1]))
            if pos_monitor != wx.NOT_FOUND:
                self.set_setting("monitor_index", pos_monitor)

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
        """Save the position of the window in the settings."""
        self.set_setting("iconized", self._window.IsIconized())
        self.save_state()
