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
import traceback
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

    GTK/Linux Position Correction:
    On GTK, the window manager ignores initial window position because wxPython
    cannot set the GDK_HINT_USER_POS hint. We handle this by:
    1. Setting target position in __init__ via _restore_size_only()
    2. Correcting position on every EVT_MOVE until EVT_ACTIVATE fires
    3. EVT_ACTIVATE signals window is ready for input - stop correcting

    Platform notes:
    - X11/GTK: Position corrected via EVT_MOVE until EVT_ACTIVATE
    - Wayland: Positioning blocked by compositor (security feature)
    - Windows/macOS: Full support (no correction needed)
    """

    def __init__(self, window, settings, section):
        super().__init__(settings, section)
        self._window = window
        self._window_activated = False  # Track when window is ready (EVT_ACTIVATE fired)

        # Target position for GTK position correction
        self._target_position = None
        self._target_size = None  # Also track target size (can be reset by AUI)

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

        # Restore SIZE and set target position for GTK correction
        self._restore_size_only()

        # Track position changes - on GTK, correct unplanned moves until EVT_ACTIVATE
        self._window.Bind(wx.EVT_MOVE, self._on_move)
        self._window.Bind(wx.EVT_SIZE, self._on_size)
        self._window.Bind(wx.EVT_MAXIMIZE, self._on_maximize)
        self._window.Bind(wx.EVT_ACTIVATE, self._on_activate)

        # Start rapid position logging
        self._start_position_logging()

    def _on_move(self, event):
        """Cache position on moves and correct unplanned GTK position changes.

        On GTK/Linux, the window manager ignores initial position and moves the
        window to its "smart placement" location. We detect this and correct it
        on every EVT_MOVE until EVT_ACTIVATE fires (window is ready for input).
        """
        pos = event.GetPosition()

        size = self._window.GetSize()

        # Correct unplanned moves until window is activated (ready for input)
        # This handles GTK/WM moving window multiple times during setup
        if not self._window_activated and self._target_position is not None:
            target_x, target_y = self._target_position
            if pos.x != target_x or pos.y != target_y:
                _log_debug(f"_on_move: UNPLANNED MOVE pos=({pos.x}, {pos.y}) size=({size.width}, {size.height}) -> correcting to ({target_x}, {target_y})")
                self._window.SetPosition(wx.Point(target_x, target_y))
                event.Skip()
                return

        # Cache position for save (only after window is activated)
        if self._window_activated and not self._window.IsIconized() and not self._window.IsMaximized():
            self._cached_position = (pos.x, pos.y)
            _log_debug(f"_on_move: pos=({pos.x}, {pos.y}) size=({size.width}, {size.height}) cached")
        event.Skip()

    def _on_size(self, event):
        """Cache size on resizes."""
        if not self._window.IsIconized() and not self._window.IsMaximized():
            size = event.GetSize()
            pos = self._window.GetPosition()
            if size.width > 100 and size.height > 100:
                self._cached_size = (size.width, size.height)
                if self._window_activated:
                    _log_debug(f"_on_size: pos=({pos.x}, {pos.y}) size=({size.width}, {size.height}) cached")
        event.Skip()

    def _on_maximize(self, event):
        """Track maximize state changes."""
        # Note: We use IsMaximized() in save_state() rather than tracking state here,
        # because EVT_MAXIMIZE only fires when maximizing, not when restoring.
        is_max = self._window.IsMaximized()
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        _log_debug(f"EVT_MAXIMIZE: IsMaximized={is_max} current_pos=({pos.x}, {pos.y}) current_size=({size.width}, {size.height})")
        _log_debug(f"  Cached (restore values): pos={self._cached_position} size={self._cached_size}")
        event.Skip()

    def _on_activate(self, event):
        """Window activated (gained focus) - stop correcting position and restore size.

        EVT_ACTIVATE with active=True signals the window is ready for user input.
        At this point, GTK/WM has finished its setup. We restore the target size
        if it was changed during initialization (e.g., by AUI).
        """
        if event.GetActive() and not self._window_activated:
            self._window_activated = True
            pos = self._window.GetPosition()
            size = self._window.GetSize()
            elapsed = time.time() - self._pos_log_start_time
            _log_debug(f"WINDOW READY [{elapsed:.2f}s]: pos=({pos.x}, {pos.y}) size=({size.width}, {size.height})")

            # Stop the position logging timer
            if self._pos_log_timer:
                self._pos_log_timer.Stop()
                self._pos_log_timer = None

            # Restore size if it was changed during initialization (e.g., by AUI)
            if self._target_size is not None:
                target_w, target_h = self._target_size
                if size.width != target_w or size.height != target_h:
                    _log_debug(f"  Size was reset to ({size.width}, {size.height}), restoring to ({target_w}, {target_h})")
                    self._window.SetSize(target_w, target_h)
                    size = self._window.GetSize()
                    _log_debug(f"  After restore: size=({size.width}, {size.height})")

            # Cache the final position and size
            if not self._window.IsIconized() and not self._window.IsMaximized():
                self._cached_position = (pos.x, pos.y)
                self._cached_size = (size.width, size.height)

            # Clear targets - no longer needed
            self._target_position = None
            self._target_size = None
        event.Skip()

    def _start_position_logging(self):
        """Start rapid position logging: 100ms for 2s, then 1s intervals."""
        self._pos_log_start_time = time.time()
        self._log_position_tick()

    def _log_position_tick(self):
        """Log current position until window is activated."""
        if not self._window:
            return

        # Stop logging once window is activated (final log is in _on_activate)
        if self._window_activated:
            self._pos_log_timer = None
            return

        elapsed = time.time() - self._pos_log_start_time
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        shown = self._window.IsShown()

        _log_debug(f"POS_LOG [{elapsed:.2f}s]: pos=({pos.x}, {pos.y}) size=({size.width}, {size.height}) shown={shown}")

        # Schedule next tick - fast initially, slower after 1 second
        if elapsed < 1.0:
            interval = 50  # 50ms for first second
        else:
            interval = 500  # 500ms after that

        # Stop after 10 seconds (failsafe if EVT_ACTIVATE never fires)
        if elapsed < 10.0:
            self._pos_log_timer = wx.CallLater(interval, self._log_position_tick)

    def _restore_size_only(self):
        """Restore size and set initial position. Final position corrected via EVT_MOVE."""
        x, y = self.get_setting("position")
        width, height = self.get_setting("size")
        maximized = self.get_setting("maximized")
        saved_monitor = self.get_setting("monitor_index")

        _log_debug(f"RESTORE: pos=({x}, {y}) size=({width}, {height}) maximized={maximized} monitor={saved_monitor}")

        # Enforce minimum size
        min_w, min_h = self._window.GetMinSize()
        width = max(width, min_w) if width > 0 else min_w
        height = max(height, min_h) if height > 0 else min_h

        # Set initial position and size. On GTK/Linux, the WM will likely ignore
        # the position (wxPython cannot set GDK_HINT_USER_POS). Position is
        # corrected via EVT_MOVE detection until EVT_ACTIVATE fires.
        if x == -1 and y == -1:
            # No saved position - just set size, let window manager place it
            self._window.SetSize(width, height)
            self._target_position = None  # No target - let WM place it
        else:
            # Validate position is on a visible monitor
            validated = self._validate_position(x, y, width, height)
            if validated is None:
                # Position invalid (monitor disconnected?) - let WM place it
                self._window.SetSize(width, height)
                self._target_position = None
            else:
                x, y = validated
                # Set initial position along with size
                self._window.SetSize(x, y, width, height)
                # Set target for GTK position correction (will correct on EVT_MOVE until EVT_ACTIVATE)
                self._target_position = (x, y)

        if operating_system.isMac():
            self._window.SetClientSize((width, height))

        # Store target size (AUI/GTK may reset it during initialization)
        self._target_size = (width, height)

        # Handle maximized state - maximize on the correct monitor
        if maximized:
            # Position window on the saved monitor before maximizing
            if saved_monitor is not None and saved_monitor != wx.NOT_FOUND:
                num_displays = wx.Display.GetCount()
                if saved_monitor < num_displays:
                    display = wx.Display(saved_monitor)
                    geometry = display.GetGeometry()
                    # Move to center of the target monitor before maximizing
                    center_x = geometry.x + (geometry.width - width) // 2
                    center_y = geometry.y + (geometry.height - height) // 2
                    _log_debug(f"  Positioning on monitor {saved_monitor} at ({center_x}, {center_y}) before maximize")
                    self._window.SetPosition(wx.Point(center_x, center_y))
            self._window.Maximize()
            self._target_position = None  # Don't correct position when maximized
            self._target_size = None  # Don't correct size when maximized

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

    def save_state(self):
        """Save the current window state. Call when window is about to close."""
        maximized = self._window.IsMaximized()
        iconized = self._window.IsIconized()

        current_pos = self._window.GetPosition()
        current_size = self._window.GetSize()
        monitor = wx.Display.GetFromWindow(self._window)

        _log_debug(f"SAVE: maximized={maximized} iconized={iconized} monitor={monitor}")
        _log_debug(f"  GetPosition()=({current_pos.x}, {current_pos.y}) GetSize()=({current_size.width}, {current_size.height})")
        _log_debug(f"  Cached: pos={self._cached_position} size={self._cached_size}")

        # When maximized, GetPosition() returns garbage - use cached position
        # Also use cache if current looks corrupted (GTK bug)
        if maximized and self._cached_position:
            _log_debug(f"  Using cached position (maximized)")
            save_pos = self._cached_position
        elif current_pos.x < 100 and current_pos.y < 50:
            if self._cached_position and (self._cached_position[0] > 100 or self._cached_position[1] > 50):
                _log_debug(f"  Using cached position (GTK bug workaround)")
                save_pos = self._cached_position
            else:
                save_pos = (current_pos.x, current_pos.y)
        elif current_pos.y < 0:
            # GTK sometimes returns negative y when maximized
            if self._cached_position:
                _log_debug(f"  Using cached position (negative y)")
                save_pos = self._cached_position
            else:
                save_pos = (current_pos.x, current_pos.y)
        else:
            save_pos = (current_pos.x, current_pos.y)

        save_size = self._cached_size if self._cached_size else (current_size.width, current_size.height)

        self.set_setting("maximized", maximized)

        if not iconized:
            # When maximized, ONLY save the monitor - preserve last non-maximized position/size
            # This is what "restore" will use when user un-maximizes
            if maximized:
                _log_debug(f"  SAVING: maximized=True monitor={monitor} (preserving non-maximized pos/size)")
                if monitor != wx.NOT_FOUND:
                    self.set_setting("monitor_index", monitor)
                    _log_debug(f"  Saved monitor_index={monitor}")
            else:
                # Only save position/size when NOT maximized
                _log_debug(f"  SAVING: pos={save_pos} size={save_size} monitor (from pos)")
                self.set_setting("position", save_pos)

                save_monitor = wx.Display.GetFromPoint(wx.Point(save_pos[0], save_pos[1]))
                if save_monitor != wx.NOT_FOUND:
                    self.set_setting("monitor_index", save_monitor)
                    _log_debug(f"  Saved monitor_index={save_monitor}")

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
