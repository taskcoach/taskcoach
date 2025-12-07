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

# Debug logging for window position tracking (set to True to enable)
_DEBUG_WINDOW_TRACKING = False


def _log_debug(msg):
    """Log debug message with timestamp including milliseconds."""
    if _DEBUG_WINDOW_TRACKING:
        now = time.time()
        timestamp = time.strftime("%H:%M:%S", time.localtime(now))
        ms = int((now % 1) * 1000)
        print(f"[{timestamp}.{ms:03d}] WindowTracker: {msg}")


class WindowGeometryTracker:
    """Track and restore window geometry (position, size, maximized state).

    Handles two window types with different positioning rules:

    == MAIN WINDOW (parent=None) ==

    Single source of truth for DESIRED window state. While not ready, we keep
    trying to make the actual window match the desired state.

    State (desired, persisted):
        position: (x, y) - desired restore position
        size: (w, h) - desired restore size
        maximized: bool - desired maximize state

    State (in-memory):
        ready: bool - position/size achieved
        position_confirmed: bool - SetPosition() result confirmed by EVT_MOVE
        size_confirmed: bool - SetSize() result confirmed by EVT_SIZE

    Rules:
        - While not ready: keep trying to achieve desired state
        - On mismatch: set confirmed=False, send correction
        - On EVT_MOVE/EVT_SIZE: set respective confirmed=True
        - On EVT_IDLE: check ready conditions
        - Ready when: IsActive() AND position_confirmed AND size_confirmed
                      AND (state empty OR position/size achieved)
        - After ready: ONE maximize attempt (fire and forget)
        - After ready: cache window changes back to state
        - Only cache position/size when not maximized and not iconized

    == DIALOG WINDOW (parent specified) ==

    Dialogs have different positioning rules - they must stay with their parent
    window and never support maximized/iconized states.

    State (persisted):
        position: (x, y) or (-1, -1) - saved position, (-1,-1) = none saved
        size: (w, h) or (-1, -1) - saved size, (-1,-1) = let system decide

    Rules (in order):
        1. Always on parent's monitor - dialog appears on same monitor as parent
        2. Missing size (-1 value) → let system decide both, clear cache
        3. Missing position (but size valid) → keep size, center on parent
        4. Size too big for monitor → clear all cache, let system decide
        5. Position off-screen (but size OK) → keep size, center, clear position
        6. Valid size and position → use saved values

    Key Differences from Main Window:
        - Monitor: Must be on parent's monitor (not any monitor)
        - Maximized/Iconized: Never supported for dialogs
        - No saved geometry: Let system decide (main window lets WM decide)
        - Position invalid: Keep size, center on parent (main window clears all)
    """

    def __init__(self, window, settings, section, parent=None):
        self._window = window
        self._settings = settings
        self._section = section
        self._parent = parent  # Parent window for dialogs (constrains to same monitor)

        # === Desired state (persisted) ===
        self.position = None    # (x, y)
        self.size = None        # (w, h)
        self.maximized = False  # True if should be maximized

        # === In-memory state ===
        self.ready = False              # Position/size achieved
        self.position_confirmed = True  # No pending SetPosition()
        self.size_confirmed = True      # No pending SetSize()

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
        self._window.Bind(wx.EVT_IDLE, self._on_idle)

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

        # For dialogs with parent: must be on same monitor as parent
        if self._parent is not None:
            self._load_dialog_geometry(x, y, width, height, min_w, min_h)
        else:
            self._load_main_window_geometry(x, y, width, height, min_w, min_h)

        if operating_system.isMac():
            self._window.SetClientSize((width, height))

    def _load_main_window_geometry(self, x, y, width, height, min_w, min_h):
        """Load geometry for main window (can be on any monitor)."""
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

    def _load_dialog_geometry(self, x, y, width, height, min_w, min_h):
        """Load geometry for dialog (must be on same monitor as parent).

        Rules (in order):
        1. Always on parent's monitor - dialog appears on same monitor as parent
        2. Missing size (-1 value) → let system decide both, clear cache
           (Position is meaningless without size)
        3. Missing position (but size valid) → keep size, center on parent
        4. Size too big for monitor → clear all cache, let system decide
        5. Position off-screen (but size OK) → keep size, center, clear position only
        6. Valid size and position → use saved values

        Note: Never save/use maximized or iconized for dialogs.
        """
        # Get parent's monitor
        parent_display_idx = self._get_parent_display_index()
        if parent_display_idx < 0:
            _log_debug(f"  Could not determine parent monitor, letting system decide")
            self._clear_dialog_cache()
            return

        parent_display = wx.Display(parent_display_idx)
        work_area = parent_display.GetClientArea()
        _log_debug(f"  Parent on monitor {parent_display_idx}: work_area={work_area.x},{work_area.y} {work_area.width}x{work_area.height}")

        size_missing = width == -1 or height == -1
        position_missing = x == -1 or y == -1

        # Rule 2: Missing size → let system decide both (position meaningless without size)
        if size_missing:
            _log_debug(f"  Rule 2: Missing saved size, letting system decide")
            self._clear_dialog_cache()
            return

        # Rule 3: Missing position (but size valid) → center on parent with saved size
        if position_missing:
            _log_debug(f"  Rule 3: Missing saved position, centering with saved size ({width}x{height})")
            self._center_on_parent_with_size(width, height)
            return

        # Rule 4: Size too big for monitor → clear all cache, let system decide
        if width > work_area.width or height > work_area.height:
            _log_debug(f"  Rule 4: Saved size ({width}x{height}) too big for monitor ({work_area.width}x{work_area.height}), clearing cache")
            self._clear_dialog_cache()
            return

        # Rule 5: Position off-screen (but size OK) → keep size, center, clear position
        if not self._is_position_on_screen(x, y, width, height, work_area):
            _log_debug(f"  Rule 5: Saved position ({x},{y}) off-screen, centering with saved size ({width}x{height})")
            self._center_on_parent_with_size(width, height)
            self._clear_position_cache()
            return

        # Rule 6: Valid size and position → use saved values
        self.position = (x, y)
        self.size = (width, height)
        self._window.SetSize(x, y, width, height)
        _log_debug(f"  Rule 6: Using saved geometry: pos={self.position} size={self.size}")

    def _is_position_on_screen(self, x, y, width, height, work_area):
        """Check if dialog is fully visible on the parent's monitor.

        Dialog must be entirely within the work area. Positions and sizes
        already include window decorations, so no tolerance is needed.
        """
        # Check all four edges
        if x < work_area.x:
            return False  # Left edge off screen
        if y < work_area.y:
            return False  # Top edge off screen
        if x + width > work_area.x + work_area.width:
            return False  # Right edge off screen
        if y + height > work_area.y + work_area.height:
            return False  # Bottom edge off screen
        return True

    def _center_on_parent_with_size(self, width, height):
        """Center on parent with specified size. Sets position and size state."""
        if self._parent is None:
            self._window.SetSize(width, height)
            self.size = (width, height)
            return

        # Get parent geometry
        parent_pos = self._parent.GetPosition()
        parent_size = self._parent.GetSize()

        # Calculate centered position
        x = parent_pos.x + (parent_size.width - width) // 2
        y = parent_pos.y + (parent_size.height - height) // 2

        # Ensure it's on screen (on parent's monitor)
        parent_display_idx = self._get_parent_display_index()
        if parent_display_idx >= 0:
            work_area = wx.Display(parent_display_idx).GetClientArea()
            x = max(work_area.x, min(x, work_area.x + work_area.width - width))
            y = max(work_area.y, min(y, work_area.y + work_area.height - height))

        self.position = (x, y)
        self.size = (width, height)
        self._window.SetSize(x, y, width, height)
        _log_debug(f"  Centered on parent: pos={self.position} size={self.size}")

    def _clear_dialog_cache(self):
        """Clear dialog geometry cache in settings. Let system decide."""
        self._set_setting("position", (-1, -1))
        self._set_setting("size", (-1, -1))
        self.position = None
        self.size = None
        _log_debug(f"  Cleared dialog geometry cache")

    def _clear_position_cache(self):
        """Clear only position cache in settings."""
        self._set_setting("position", (-1, -1))
        _log_debug(f"  Cleared position cache")

    def _get_parent_display_index(self):
        """Get the display index where the parent window is located."""
        if self._parent is None:
            return -1
        parent_pos = self._parent.GetPosition()
        parent_size = self._parent.GetSize()
        # Use center of parent to determine its monitor
        center_x = parent_pos.x + parent_size.width // 2
        center_y = parent_pos.y + parent_size.height // 2
        return wx.Display.GetFromPoint(wx.Point(center_x, center_y))

    def _clear_state(self):
        """Clear all state - let WM decide, normal caching will capture new values."""
        self.position = None
        self.size = None
        self.maximized = False
        # Reset confirmed flags so ready check can proceed
        self.position_confirmed = True
        self.size_confirmed = True
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
        """Try to make window match desired state. Called on EVT_MOVE/EVT_SIZE.

        Rules:
        - Error (iconized, or maximized unexpectedly) → clear state only
        - On mismatch: set confirmed=False, send correction
        - Ready check happens in EVT_IDLE handler
        """
        if self.ready:
            return

        # ERROR: Window is iconized before ready
        if self._window.IsIconized():
            _log_debug(f"ERROR: Window is iconized before ready!")
            _log_debug(f"  Desired state was: pos={self.position} size={self.size} maximized={self.maximized}")
            self._clear_state()
            return

        # ERROR: Window is maximized before ready (we haven't set position/size yet)
        if self._window.IsMaximized():
            _log_debug(f"ERROR: Window is maximized before ready!")
            _log_debug(f"  Desired state was: pos={self.position} size={self.size} maximized={self.maximized}")
            self._clear_state()
            return

        # Window is in normal state - check and correct position/size
        if self.position is not None or self.size is not None:
            pos = self._window.GetPosition()
            size = self._window.GetSize()
            self._check_position(pos)
            self._check_size(size)

    def _check_position(self, pos):
        """Check and correct position. Sets position_confirmed=False if correcting."""
        if self.position is None:
            return

        target_x, target_y = self.position
        if pos.x != target_x or pos.y != target_y:
            _log_debug(f"_check_position: ({pos.x}, {pos.y}) != target ({target_x}, {target_y}), correcting")
            self.position_confirmed = False
            self._window.SetPosition(wx.Point(target_x, target_y))

    def _check_size(self, size):
        """Check and correct size. Sets size_confirmed=False if correcting."""
        if self.size is None:
            return

        target_w, target_h = self.size
        if size.width != target_w or size.height != target_h:
            _log_debug(f"_check_size: ({size.width}, {size.height}) != target ({target_w}, {target_h}), correcting")
            self.size_confirmed = False
            self._window.SetSize(target_w, target_h)

    def _mark_ready(self):
        """Mark window as ready - position/size achieved. Then maximize if needed."""
        elapsed = time.time() - self._pos_log_start_time

        self.ready = True

        # Update state with actual final position/size values
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        self.position = (pos.x, pos.y)
        self.size = (size.width, size.height)
        _log_debug(f"WINDOW READY [{elapsed:.2f}s]: pos={self.position} size={self.size}")

        # Stop position logging
        if self._pos_log_timer:
            self._pos_log_timer.Stop()
            self._pos_log_timer = None

        # After ready, ONE maximize attempt if state says maximized (fire and forget)
        if self.maximized:
            _log_debug(f"  Maximizing (fire and forget)")
            self._window.Maximize()

    # === State updates from window (after ready) ===

    def cache_from_window(self):
        """Update state from window. Only cache position/size in normal state."""
        # Always cache maximized state from window
        self.maximized = self._window.IsMaximized()

        # Only cache position/size when in normal state
        if self._is_normal_state():
            pos = self._window.GetPosition()
            size = self._window.GetSize()
            self.position = (pos.x, pos.y)
            if size.width > 100 and size.height > 100:
                self.size = (size.width, size.height)
            _log_debug(f"cache_from_window: pos={self.position} size={self.size} maximized={self.maximized}")

    # === Event handlers ===

    def _on_move(self, event):
        """Handle window move. Confirms position change."""
        if not self.ready:
            self.position_confirmed = True
            self.check_and_correct()
        else:
            self.cache_from_window()
        event.Skip()

    def _on_size(self, event):
        """Handle window resize. Confirms size change."""
        if not self.ready:
            self.size_confirmed = True
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

    def _on_idle(self, event):
        """Handle idle event. Check ready conditions here.

        Ready when: IsActive() AND position_confirmed AND size_confirmed
                    AND (state empty OR position/size achieved)
        """
        if self.ready:
            event.Skip()
            return

        # All conditions must be met
        if not self._window.IsActive():
            event.Skip()
            return
        if not self.position_confirmed or not self.size_confirmed:
            event.Skip()
            return

        # Check for errors (iconized/maximized unexpectedly)
        if self._window.IsIconized() or self._window.IsMaximized():
            event.Skip()
            return

        # Check if state empty or position/size achieved
        state_empty = self.position is None and self.size is None
        if state_empty:
            self._mark_ready()
        else:
            pos = self._window.GetPosition()
            size = self._window.GetSize()
            pos_ok = self.position is None or (pos.x == self.position[0] and pos.y == self.position[1])
            size_ok = self.size is None or (size.width == self.size[0] and size.height == self.size[1])
            if pos_ok and size_ok:
                self._mark_ready()

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
