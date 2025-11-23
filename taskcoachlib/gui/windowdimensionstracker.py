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
    """Log debug message with timestamp including milliseconds."""
    if _DEBUG_WINDOW_TRACKING:
        now = time.time()
        timestamp = time.strftime("%H:%M:%S", time.localtime(now))
        ms = int((now % 1) * 1000)
        print(f"[{timestamp}.{ms:03d}] WindowTracker: {msg}")


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

        # Target position/size for correction until window is ready
        self._target_position = None
        self._target_size = None
        self._should_maximize = False  # Maximize after window is ready

        # Window ready state
        self._activated = False  # EVT_ACTIVATE has fired
        self._window_ready = False  # Window is ready: activated AND position/size match target

        # Transition flags
        self._maximizing = False  # True between Maximize() call and EVT_MAXIMIZE
        self._restoring = False  # True during restore (un-maximize) transition
        self._was_maximized = False  # Track previous maximize state for restore detection

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
        """Handle window move - correct if needed, cache when ready."""
        if not self._window_ready:
            self._check_and_restore()
        else:
            # Window is ready - cache position (only when not maximized/iconized)
            if not self._window.IsIconized() and not self._window.IsMaximized():
                pos = self._window.GetPosition()
                self._cached_position = (pos.x, pos.y)
                _log_debug(f"_on_move: pos=({pos.x}, {pos.y}) cached")
        event.Skip()

    def _on_size(self, event):
        """Handle window resize - correct if needed, cache when ready."""
        if not self._window_ready:
            self._check_and_restore()
        else:
            # Window is ready - handle restore transition or cache
            size = event.GetSize()
            is_max = self._window.IsMaximized()
            is_icon = self._window.IsIconized()

            # Detect restore transition: was maximized, now not maximized
            if self._was_maximized and not is_max and not is_icon:
                self._restoring = True
                _log_debug(f"_on_size: RESTORE TRANSITION DETECTED")

            # Check if restore transition is complete (size matches cached)
            if self._restoring and self._cached_size:
                cached_w, cached_h = self._cached_size
                if abs(size.width - cached_w) < 10 and abs(size.height - cached_h) < 10:
                    self._restoring = False
                    self._was_maximized = False
                    _log_debug(f"_on_size: RESTORE COMPLETE size=({size.width}, {size.height})")

            # Cache size (only when not maximized/iconized/restoring)
            if not is_icon and not is_max and not self._maximizing and not self._restoring:
                if size.width > 100 and size.height > 100:
                    self._cached_size = (size.width, size.height)
                    _log_debug(f"_on_size: size=({size.width}, {size.height}) cached")
        event.Skip()

    def _check_and_restore(self):
        """Check if window matches target and restore if not. Set ready when done.

        Called from both _on_move and _on_size until window is ready.
        Corrects both position and size if they don't match target.
        Window becomes ready when: activated AND position matches AND size matches.
        Then maximizes if saved state was maximized.
        """
        if self._window_ready:
            return

        pos = self._window.GetPosition()
        size = self._window.GetSize()

        target_pos = self._target_position
        target_size = self._target_size

        pos_ok = True
        size_ok = True

        # Check and correct position
        if target_pos is not None:
            target_x, target_y = target_pos
            if pos.x != target_x or pos.y != target_y:
                pos_ok = False
                _log_debug(f"_check_and_restore: pos=({pos.x}, {pos.y}) != target=({target_x}, {target_y}), correcting")
                self._window.SetPosition(wx.Point(target_x, target_y))

        # Check and correct size
        if target_size is not None:
            target_w, target_h = target_size
            if size.width != target_w or size.height != target_h:
                size_ok = False
                _log_debug(f"_check_and_restore: size=({size.width}, {size.height}) != target=({target_w}, {target_h}), correcting")
                self._window.SetSize(target_w, target_h)

        # Check if ready: activated AND position AND size match
        if self._activated and pos_ok and size_ok:
            self._set_window_ready()

    def _set_window_ready(self):
        """Mark window as ready - stop corrections, cache values, maximize if needed."""
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        elapsed = time.time() - self._pos_log_start_time

        self._window_ready = True
        _log_debug(f"WINDOW READY [{elapsed:.2f}s]: pos=({pos.x}, {pos.y}) size=({size.width}, {size.height})")

        # Stop the position logging timer
        if self._pos_log_timer:
            self._pos_log_timer.Stop()
            self._pos_log_timer = None

        # Cache the final values (these are the restore values)
        self._cached_position = (pos.x, pos.y)
        self._cached_size = (size.width, size.height)
        _log_debug(f"  Cached restore values: pos={self._cached_position} size={self._cached_size}")

        # Clear targets - no longer needed
        self._target_position = None
        self._target_size = None

        # NOW maximize if saved state was maximized
        if self._should_maximize:
            _log_debug(f"  Maximizing now (window ready)")
            self._maximizing = True
            self._window.Maximize()
            self._should_maximize = False

    def _on_maximize(self, event):
        """Track maximize state changes."""
        # Clear maximizing flag - transition complete
        self._maximizing = False

        is_max = self._window.IsMaximized()
        pos = self._window.GetPosition()
        size = self._window.GetSize()

        # Track that we're now maximized (for restore detection)
        if is_max:
            self._was_maximized = True

        _log_debug(f"EVT_MAXIMIZE: IsMaximized={is_max} current_pos=({pos.x}, {pos.y}) current_size=({size.width}, {size.height})")
        _log_debug(f"  Cached (restore values): pos={self._cached_position} size={self._cached_size}")
        event.Skip()

    def _on_activate(self, event):
        """Window activated (gained focus) - mark activated and check if ready.

        EVT_ACTIVATE with active=True signals the window has gained focus.
        Combined with position and size matching target, this means window is ready.
        """
        if event.GetActive() and not self._activated:
            self._activated = True
            _log_debug(f"EVT_ACTIVATE: Window activated, checking if ready")
            self._check_and_restore()
        event.Skip()

    def _start_position_logging(self):
        """Start rapid position logging: 100ms for 2s, then 1s intervals."""
        self._pos_log_start_time = time.time()
        self._log_position_tick()

    def _log_position_tick(self):
        """Log current position until window is ready."""
        if not self._window:
            return

        # Stop logging once window is ready (final log is in _set_window_ready)
        if self._window_ready:
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

        # If saved state was maximized, we'll maximize AFTER EVT_ACTIVATE
        # First restore to the non-maximized position (determines which monitor)
        if maximized:
            self._should_maximize = True
            _log_debug(f"  Will maximize after EVT_ACTIVATE")

        # Non-maximized case: set position and size, enable position correction
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
        """Write window state to file. Call when window is about to close.

        Always writes cached position/size (the restore values) and maximize flag.
        Cached values are only updated when window is in normal state (not maximized/iconized),
        so they always represent the correct restore position/size.
        """
        maximized = self._window.IsMaximized()

        _log_debug(f"WRITE TO FILE: maximized={maximized}")
        _log_debug(f"  Cached (restore values): pos={self._cached_position} size={self._cached_size}")

        # Always write maximize flag
        self.set_setting("maximized", maximized)

        # Always write cached position/size (they're the restore values)
        if self._cached_position:
            self.set_setting("position", self._cached_position)
            _log_debug(f"  Written position={self._cached_position}")

        if self._cached_size:
            if operating_system.isMac():
                # Mac uses client size
                self.set_setting("size", self._cached_size)
            else:
                self.set_setting("size", self._cached_size)
            _log_debug(f"  Written size={self._cached_size}")


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
        return start_iconized == "Always"

    def save_position(self):
        """Save the position of the window in the settings."""
        self.save_state()
