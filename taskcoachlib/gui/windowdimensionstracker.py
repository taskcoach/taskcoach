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
    """Log debug message with timestamp including milliseconds."""
    if _DEBUG_WINDOW_TRACKING:
        now = time.time()
        timestamp = time.strftime("%H:%M:%S", time.localtime(now))
        ms = int((now % 1) * 1000)
        print(f"[{timestamp}.{ms:03d}] WindowTracker: {msg}")


class WindowGeometryTracker:
    """Track and restore window geometry (position, size, maximized state).

    Single source of truth for DESIRED window state. While not ready, we keep
    trying to make the actual window match the desired state.

    State (desired, persisted):
        position: (x, y) - desired restore position
        size: (w, h) - desired restore size
        maximized: bool - desired maximize state

    State (in-memory):
        ready: bool - window matches desired state
        activated: bool - EVT_ACTIVATE has fired

    Rules:
        - While not ready: keep trying to achieve desired state
        - After ready: cache window changes back to state
        - Only cache position/size when not maximized and not iconized
    """

    def __init__(self, window, settings, section):
        self._window = window
        self._settings = settings
        self._section = section

        # === Desired state (persisted) ===
        self.position = None    # (x, y)
        self.size = None        # (w, h)
        self.maximized = False  # True if should be maximized

        # === In-memory state ===
        self.ready = False      # Window matches desired state
        self.activated = False  # EVT_ACTIVATE has fired

        # Position logging timer
        self._pos_log_timer = None
        self._pos_log_start_time = None

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

        # Load desired state from file and apply to window
        self.load()

        # Bind event handlers
        self._window.Bind(wx.EVT_MOVE, self._on_move)
        self._window.Bind(wx.EVT_SIZE, self._on_size)
        self._window.Bind(wx.EVT_MAXIMIZE, self._on_maximize)
        self._window.Bind(wx.EVT_ACTIVATE, self._on_activate)

        # Start position logging for debugging
        self._start_position_logging()

    # === Settings I/O ===

    def _get_setting(self, setting):
        """Get value from settings file."""
        return self._settings.getvalue(self._section, setting)

    def _set_setting(self, setting, value):
        """Set value in settings file."""
        self._settings.setvalue(self._section, setting, value)

    # === State persistence ===

    def load(self):
        """Load desired state from settings file and apply to window."""
        x, y = self._get_setting("position")
        width, height = self._get_setting("size")
        self.maximized = self._get_setting("maximized")

        _log_debug(f"LOAD: pos=({x}, {y}) size=({width}, {height}) maximized={self.maximized}")

        # Enforce minimum size
        min_w, min_h = self._window.GetMinSize()
        width = max(width, min_w) if width > 0 else min_w
        height = max(height, min_h) if height > 0 else min_h

        # Validate geometry against current monitors
        if x == -1 and y == -1:
            # No saved position - let WM place it, clear state
            _log_debug(f"  No saved position, clearing state, letting WM place window")
            self._clear_state()
            self._window.SetSize(width, height)
        else:
            validated = self._validate_geometry(x, y, width, height)
            if validated is None:
                # Geometry invalid - let WM place it, clear state
                _log_debug(f"  Geometry invalid, clearing state, letting WM place window")
                self._clear_state()
                self._window.SetSize(min_w, min_h)
            else:
                # Geometry valid - set desired state
                x, y, width, height = validated
                self.position = (x, y)
                self.size = (width, height)
                self._window.SetSize(x, y, width, height)
                _log_debug(f"  Set desired: pos={self.position} size={self.size} maximized={self.maximized}")

        if operating_system.isMac():
            self._window.SetClientSize((width, height))

    def _clear_state(self):
        """Clear all state - let WM decide, normal caching will capture new values."""
        self.position = None
        self.size = None
        self.maximized = False
        _log_debug(f"  State cleared: pos=None size=None maximized=False")

    def save(self):
        """Save current state to settings file."""
        _log_debug(f"SAVE: pos={self.position} size={self.size} maximized={self.maximized}")

        self._set_setting("maximized", self.maximized)

        if self.position:
            self._set_setting("position", self.position)

        if self.size:
            self._set_setting("size", self.size)

    # === Window correction ===

    def _is_normal_state(self):
        """Return True if window is in normal state (not maximized, not iconized)."""
        return not self._window.IsMaximized() and not self._window.IsIconized()

    def check_and_correct(self):
        """Try to make window match desired state. Called while not ready."""
        if self.ready:
            return

        is_max = self._window.IsMaximized()
        is_icon = self._window.IsIconized()

        # ERROR: Window is iconized before we're ready
        if is_icon:
            _log_debug(f"ERROR: Window is iconized before ready!")
            _log_debug(f"  Cannot set restore position/size - OS/WM opened window iconized")
            _log_debug(f"  Desired state was: pos={self.position} size={self.size} maximized={self.maximized}")
            return  # Can't do anything while iconized

        # ERROR: Window is maximized before we're ready
        if is_max:
            _log_debug(f"ERROR: Window is maximized before ready!")
            _log_debug(f"  Cannot set restore position/size - OS/WM opened window maximized")
            _log_debug(f"  Desired state was: pos={self.position} size={self.size} maximized={self.maximized}")
            _log_debug(f"  Restore geometry will be wrong when user un-maximizes")
            self._mark_ready()  # Nothing we can do
            return

        # Window is in normal state - try to achieve desired state
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        pos_ok = self._check_position(pos)
        size_ok = self._check_size(size)

        if pos_ok and size_ok and self.activated:
            if self.maximized:
                # Position/size correct, now maximize
                _log_debug(f"check_and_correct: position/size correct, now maximizing")
                self._window.Maximize()
            else:
                self._mark_ready()

    def _check_position(self, pos):
        """Check and correct position. Returns True if position is OK."""
        if self.position is None:
            return True

        target_x, target_y = self.position
        if pos.x != target_x or pos.y != target_y:
            _log_debug(f"_check_position: ({pos.x}, {pos.y}) != target ({target_x}, {target_y}), correcting")
            self._window.SetPosition(wx.Point(target_x, target_y))
            return False
        return True

    def _check_size(self, size):
        """Check and correct size. Returns True if size is OK."""
        if self.size is None:
            return True

        target_w, target_h = self.size
        if size.width != target_w or size.height != target_h:
            _log_debug(f"_check_size: ({size.width}, {size.height}) != target ({target_w}, {target_h}), correcting")
            self._window.SetSize(target_w, target_h)
            return False
        return True

    def _mark_ready(self):
        """Mark window as ready - it now matches desired state."""
        elapsed = time.time() - self._pos_log_start_time

        self.ready = True
        _log_debug(f"WINDOW READY [{elapsed:.2f}s]: maximized={self.maximized} pos={self.position} size={self.size}")

        # Stop position logging
        if self._pos_log_timer:
            self._pos_log_timer.Stop()
            self._pos_log_timer = None

        # If not maximized, update state with actual final values
        if not self.maximized:
            pos = self._window.GetPosition()
            size = self._window.GetSize()
            self.position = (pos.x, pos.y)
            self.size = (size.width, size.height)
            _log_debug(f"  Final state: pos={self.position} size={self.size}")

    # === State updates from window (after ready) ===

    def cache_from_window(self):
        """Update state from window (only when in normal state)."""
        if self._is_normal_state():
            pos = self._window.GetPosition()
            size = self._window.GetSize()
            self.position = (pos.x, pos.y)
            if size.width > 100 and size.height > 100:
                self.size = (size.width, size.height)
            self.maximized = False
            _log_debug(f"cache_from_window: pos={self.position} size={self.size}")
        elif self._window.IsMaximized():
            self.maximized = True
            _log_debug(f"cache_from_window: maximized=True (restore values unchanged)")

    # === Event handlers ===

    def _on_move(self, event):
        """Handle window move."""
        if not self.ready:
            self.check_and_correct()
        else:
            self.cache_from_window()
        event.Skip()

    def _on_size(self, event):
        """Handle window resize."""
        if not self.ready:
            self.check_and_correct()
        else:
            self.cache_from_window()
        event.Skip()

    def _on_maximize(self, event):
        """Handle maximize/restore."""
        _log_debug(f"EVT_MAXIMIZE: IsMaximized={self._window.IsMaximized()}")
        if not self.ready:
            self.check_and_correct()
        else:
            self.cache_from_window()
        event.Skip()

    def _on_activate(self, event):
        """Handle window activation."""
        if event.GetActive() and not self.activated:
            self.activated = True
            _log_debug(f"EVT_ACTIVATE: Window activated")
            self.check_and_correct()
        event.Skip()

    # === Geometry validation ===

    def _validate_geometry(self, x, y, width, height):
        """Validate position and size fit on a monitor. Returns (x, y, w, h) or None."""
        num_displays = wx.Display.GetCount()
        _log_debug(f"_validate_geometry: checking pos=({x}, {y}) size=({width}, {height}) against {num_displays} monitors")

        for i in range(num_displays):
            display = wx.Display(i)
            geometry = display.GetGeometry()
            work_area = display.GetClientArea()  # Excludes taskbar
            _log_debug(f"  Monitor {i}: geometry={geometry.width}x{geometry.height} work_area={work_area.width}x{work_area.height}")

            # Check if position is reasonably within this monitor
            if (geometry.x - width + 100 <= x <= geometry.x + geometry.width - 100 and
                geometry.y <= y <= geometry.y + geometry.height - 100):

                # Check if size fits on this monitor's work area
                if width > work_area.width or height > work_area.height:
                    _log_debug(f"  Size ({width}x{height}) too big for monitor {i} work area ({work_area.width}x{work_area.height})")
                    return None  # Size doesn't fit - clear state

                _log_debug(f"  Geometry valid for monitor {i}")
                return (x, y, width, height)

        _log_debug(f"  Position ({x}, {y}) not valid for any monitor")
        return None

    # === Debug logging ===

    def _start_position_logging(self):
        """Start position logging for debugging."""
        self._pos_log_start_time = time.time()
        self._log_position_tick()

    def _log_position_tick(self):
        """Log current position until ready."""
        if not self._window or self.ready:
            self._pos_log_timer = None
            return

        elapsed = time.time() - self._pos_log_start_time
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        is_max = self._window.IsMaximized()

        _log_debug(f"POS_LOG [{elapsed:.2f}s]: pos=({pos.x}, {pos.y}) size=({size.width}, {size.height}) max={is_max}")

        # Schedule next tick
        interval = 50 if elapsed < 1.0 else 500
        if elapsed < 10.0:
            self._pos_log_timer = wx.CallLater(interval, self._log_position_tick)


class WindowDimensionsTracker(WindowGeometryTracker):
    """Track the dimensions of the main window in the settings."""

    def __init__(self, window, settings):
        super().__init__(window, settings, "window")

        # Handle start iconized setting (Task Coach specific)
        if self._should_start_iconized():
            if operating_system.isMac() or operating_system.isGTK():
                self._window.Show()
            self._window.Iconize(True)
            if not operating_system.isMac() and self._get_setting("hidewheniconized"):
                wx.CallAfter(self._window.Hide)

    def _should_start_iconized(self):
        """Return whether the window should be opened iconized."""
        start_iconized = self._settings.get("window", "starticonized")
        return start_iconized == "Always"

    def save_position(self):
        """Save the position of the window in the settings."""
        self.save()
