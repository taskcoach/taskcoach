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

import time

import wx

from taskcoachlib import operating_system
from taskcoachlib.meta.debug import log_step

# Windows and macOS apply position, size and maximize during the call,
# also before the first show, proven by years of use without reports
# (docs/WINDOW_GEOMETRY.md, Direct Placement). Elsewhere placement is
# observed until quiet.
_DIRECT_PLACEMENT = operating_system.isWindows() or operating_system.isMac()

# Placement steps are checked once neither position nor size changed
# for a quiet period (docs/WINDOW_GEOMETRY.md, Main Window). Startup
# is slow, so the first one is longer. Each lasts at least twice the
# platform's slowest answer so far, up to the maximum.
_FIRST_QUIET_MS = 1000
_QUIET_MS = 500
_MAX_QUIET_MS = 3000

# Attempts to get a position, size or maximized state applied before
# the platform's decision is accepted
_ATTEMPTS = 3

# A placement step ends this long after it started even if the window
# keeps changing, for instance dragged at once by the user
_STEP_LIMIT = 10.0


def fit_to_monitors(rect, monitors):
    """Fit a saved window rect (x, y, width, height) to the monitors.

    monitors holds (geometry, work_area) per monitor, each an
    (x, y, width, height) tuple. A rect whose title bar lies on a
    monitor and whose size fits that monitor's work area is kept as it
    is. Otherwise the size is reduced to the work area the rect
    overlaps most, or else the nearest one, and the rect is moved
    inside it.
    """
    x, y, width, height = rect
    for geometry, work_area in monitors:
        fits = width <= work_area[2] and height <= work_area[3]
        if fits and _title_bar_on(rect, geometry):
            return tuple(rect)
    if not monitors:
        return tuple(rect)
    ax, ay, aw, ah = _best_work_area(rect, [area for _, area in monitors])
    width, height = min(width, aw), min(height, ah)
    x = max(ax, min(x, ax + aw - width))
    y = max(ay, min(y, ay + ah - height))
    return (x, y, width, height)


def _title_bar_on(rect, geometry):
    """Whether the rect's top left, where the title bar is, lies on the
    monitor with at least 100 pixels of it showing."""
    x, y, width, _ = rect
    gx, gy, gw, gh = geometry
    return gx - width + 100 <= x <= gx + gw - 100 and gy <= y <= gy + gh - 100


def _best_work_area(rect, work_areas):
    """The work area the rect overlaps most, or else the nearest."""
    x, y, width, height = rect

    def overlap(area):
        ax, ay, aw, ah = area
        dx = min(x + width, ax + aw) - max(x, ax)
        dy = min(y + height, ay + ah) - max(y, ay)
        return max(dx, 0) * max(dy, 0)

    def distance(area):
        ax, ay, aw, ah = area
        cx, cy = x + width / 2, y + height / 2
        dx = max(ax - cx, 0, cx - (ax + aw))
        dy = max(ay - cy, 0, cy - (ay + ah))
        return dx * dx + dy * dy

    best = max(work_areas, key=overlap)
    return best if overlap(best) > 0 else min(work_areas, key=distance)


class WindowGeometryTracker:
    """Track and restore window geometry (position, size, maximized).

    Rules, platform notes and known issues: docs/WINDOW_GEOMETRY.md.
    With a parent the window is an editor: it stays on the parent's
    monitor. On Windows and macOS the geometry is set before the first
    show and kept; elsewhere it is checked once the window is quiet.

    Each restore step is logged with the [GEOMETRY] prefix and the time
    since the tracker started, until the window has settled.
    """

    def __init__(self, window, settings, section, parent=None):
        self._window = window
        self._settings = settings
        self._section = section
        self._parent = parent
        # Editor sections name every tab; the type is enough to trace
        self._label = section.split("_with_")[0]

        # Desired state (persisted)
        self.position = None  # (x, y)
        self.size = None  # (w, h)
        self.maximized = False

        # Placement: "placing", then "maximizing" if saved maximized
        self.ready = False  # Placed; moves and resizes are kept from now
        self._direct = _DIRECT_PLACEMENT
        self._phase = "placing"
        self._attempts = 0
        self._quiet = None  # wx.CallLater ending the quiet period
        self._quiet_ms = _FIRST_QUIET_MS
        self._step_started = None  # Set by the first show
        self._requesting = False  # In our own SetSize() and the like
        self._requested_at = None  # Last request: show, attempt
        self._slowest_answer = 0.0  # Seconds from a request to a change
        self._requested_size = None  # Last size given to SetSize()
        self._seen = None  # Geometry at the last event
        # Placed at once but started minimized: maximize when restored
        self._maximize_on_restore = False

        # Tracing
        self._started = time.perf_counter()
        self._tracing = True
        self._resized_at = None  # Last EVT_SIZE not yet followed by idle

        # The compositor places windows and never reports positions
        self._positions_known = not operating_system.isWayland()
        if not self._positions_known:
            self._trace("Wayland: positions are neither set nor kept")

        self._min_size = (
            (400, 300) if isinstance(window, wx.Dialog) else (600, 400)
        )
        self._window.SetMinSize(self._min_size)
        self._trace("SetMinSize%s" % (self._min_size,))

        self.load()

        # wxGTK maps a new window at its minimum size (see
        # docs/WINDOW_GEOMETRY.md), so ask for the requested size as the
        # minimum until the window is shown
        self._min_size_pending = (
            not self._direct
            and self._requested_size is not None
            and not self._window.IsShown()
        )
        if self._min_size_pending:
            self._window.SetMinSize(self._requested_size)
            self._trace("SetMinSize%s until shown" % (self._requested_size,))

        self._window.Bind(wx.EVT_MOVE, self._on_move)
        self._window.Bind(wx.EVT_SIZE, self._on_size)
        self._window.Bind(wx.EVT_MAXIMIZE, self._on_maximize)
        self._window.Bind(wx.EVT_ICONIZE, self._on_iconize)
        self._window.Bind(wx.EVT_IDLE, self._on_idle)
        self._window.Bind(wx.EVT_SHOW, self._on_show)
        if self._direct:
            # Applied during the calls; traced until shown
            self.ready = True
            self._trace("placed: %s" % self._window_state())

    # === Tracing ===

    def _trace(self, message, always=False):
        """Log a restore step with the milliseconds since the start;
        only until the window has settled, unless always."""
        if not self._tracing and not always:
            return
        elapsed = (time.perf_counter() - self._started) * 1000
        log_step(
            "%s +%.0f ms: %s" % (self._label, elapsed, message),
            prefix="GEOMETRY",
        )

    def _window_state(self):
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        return "pos=(%d, %d) size=(%d, %d) shown=%s max=%s active=%s" % (
            pos.x,
            pos.y,
            size.width,
            size.height,
            self._window.IsShown(),
            self._window.IsMaximized(),
            self._window.IsActive(),
        )

    # === Settings I/O ===

    def _get_setting(self, setting):
        return self._settings.getvalue(self._section, setting)

    def _set_setting(self, setting, value):
        self._settings.setvalue(self._section, setting, value)

    # === State persistence ===

    def load(self):
        """Load the desired state from the settings and apply it."""
        x, y = self._get_setting("position")
        width, height = self._get_setting("size")
        self.maximized = self._get_setting("maximized")
        self._trace(
            "load: saved pos=(%d, %d) size=(%d, %d) maximized=%s, %s"
            % (x, y, width, height, self.maximized, self._window_state())
        )

        # Enforce minimum size
        min_w, min_h = self._min_size
        width = max(width, min_w) if width > 0 else min_w
        height = max(height, min_h) if height > 0 else min_h

        if self._parent is not None:
            self._load_dialog_geometry(x, y, width, height)
        else:
            self._load_main_window_geometry(x, y, width, height)

        if self._direct and self.maximized:
            # Applied when shown, on the monitor of the saved rect
            self._trace("request Maximize() before show")
            self._window.Maximize()

    def _set_size(self, *args):
        """SetSize() with tracing; remembers the size for the first
        show."""
        self._trace("request SetSize%s" % (args,))
        self._window.SetSize(*args)
        self._requested_size = tuple(args[-2:])
        self._trace("after SetSize: %s" % self._window_state())

    def _load_main_window_geometry(self, x, y, width, height):
        """Load geometry for the main window (any monitor)."""
        monitors = self._monitors()
        if (x == -1 and y == -1) or not self._positions_known:
            # The window manager places it, and the size it gets is kept
            # once placed; the saved maximized state is kept
            self._trace("no position to restore: the window manager places it")
            if monitors:
                area = monitors[0][1]
                rect = (area[0], area[1], width, height)
                width, height = fit_to_monitors(rect, monitors)[2:]
            self.position = None
            self.size = None
            self._set_size(width, height)
            return
        fitted = fit_to_monitors((x, y, width, height), monitors)
        if fitted != (x, y, width, height):
            self._trace("fitted to the monitors: %s" % (fitted,))
        x, y, width, height = fitted
        self.position = (x, y)
        self.size = (width, height)
        self._set_size(x, y, width, height)

    def _load_dialog_geometry(self, x, y, width, height):
        """Load geometry for an editor (on the parent's monitor).

        Rules, in order: see docs/WINDOW_GEOMETRY.md, Editors.
        """
        if not self._positions_known:
            self._trace("the compositor places it: the saved size only")
            self.size = (width, height)
            self._set_size(width, height)
            return
        parent_display_idx = self._get_parent_display_index()
        if parent_display_idx < 0:
            self._trace("parent monitor unknown: the system decides")
            self._clear_dialog_cache()
            return

        work_area = wx.Display(parent_display_idx).GetClientArea()
        self._trace(
            "parent on monitor %d, work area (%d, %d) %dx%d"
            % (
                parent_display_idx,
                work_area.x,
                work_area.y,
                work_area.width,
                work_area.height,
            )
        )

        if x == -1 or y == -1:
            self._trace("no saved position: center with the saved size")
            self._center_on_parent_with_size(width, height)
            return
        if width > work_area.width or height > work_area.height:
            self._trace("saved size larger than the monitor: system decides")
            self._clear_dialog_cache()
            return
        if not self._is_position_on_screen(x, y, width, height, work_area):
            self._trace("saved position off the monitor: center")
            self._center_on_parent_with_size(width, height)
            return
        self.position = (x, y)
        self.size = (width, height)
        self._set_size(x, y, width, height)

    def _is_position_on_screen(self, x, y, width, height, work_area):
        """Whether the editor lies entirely within the work area.

        Positions and sizes include the window decorations.
        """
        return (
            x >= work_area.x
            and y >= work_area.y
            and x + width <= work_area.x + work_area.width
            and y + height <= work_area.y + work_area.height
        )

    def _center_on_parent_with_size(self, width, height):
        """Center on the parent with this size, within its monitor."""
        parent_pos = self._parent.GetPosition()
        parent_size = self._parent.GetSize()
        x = parent_pos.x + (parent_size.width - width) // 2
        y = parent_pos.y + (parent_size.height - height) // 2

        parent_display_idx = self._get_parent_display_index()
        if parent_display_idx >= 0:
            area = wx.Display(parent_display_idx).GetClientArea()
            x = max(area.x, min(x, area.x + area.width - width))
            y = max(area.y, min(y, area.y + area.height - height))

        self.position = (x, y)
        self.size = (width, height)
        self._set_size(x, y, width, height)

    def _clear_dialog_cache(self):
        """Clear the saved editor geometry; the system decides."""
        self._set_setting("position", (-1, -1))
        self._set_setting("size", (-1, -1))
        self.position = None
        self.size = None

    def _get_parent_display_index(self):
        """Index of the monitor holding the parent's center, or -1."""
        parent_pos = self._parent.GetPosition()
        parent_size = self._parent.GetSize()
        center = wx.Point(
            parent_pos.x + parent_size.width // 2,
            parent_pos.y + parent_size.height // 2,
        )
        return wx.Display.GetFromPoint(center)

    def save(self):
        """Write the state to the settings."""
        self._trace(
            "save: pos=%s size=%s maximized=%s"
            % (self.position, self.size, self.maximized),
            always=True,
        )
        self._set_setting("maximized", self.maximized)
        if self.position:
            self._set_setting("position", self.position)
        if self.size:
            self._set_setting("size", self.size)

    # === Placement ===

    def _is_normal_state(self):
        return not self._window.IsMaximized() and not self._window.IsIconized()

    def _wait_until_quiet(self):
        """(Re)start the quiet period; the placement step is checked
        when it ends without any move or resize."""
        elapsed = time.perf_counter() - self._step_started
        if elapsed > _STEP_LIMIT and not self._window.IsIconized():
            self._trace("still moving after %.1f s: accepted" % elapsed)
            self._accept()
            return
        if self._quiet is None:
            self._quiet = wx.CallLater(self._quiet_ms, self._on_quiet)
        else:
            self._quiet.Start(self._quiet_ms)

    def _on_quiet(self):
        """Quiet for a quiet period: check the placement step."""
        if not self._window or self.ready:
            return
        self._adapt_quiet_period()
        if self._phase == "placing":
            self._check_placement()
        elif not self._window.IsIconized():
            self._check_maximized()
        # A minimized window is maximized once restored (EVT_ICONIZE)

    def _check_placement(self):
        """Correct position and size if they differ, at most _ATTEMPTS
        times; then accept what the platform applied."""
        if self._window.IsMaximized():
            # Maximized meanwhile, by the user or the window manager:
            # the saved normal geometry is kept for the un-maximize
            self._trace("maximized during placement: accepted")
            self.maximized = True
            self._finish()
            return
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        wrong_position = (
            self._positions_known
            and self.position is not None
            and (pos.x, pos.y) != self.position
        )
        wrong_size = self.size is not None and (
            (size.width, size.height) != self.size
        )
        self._trace("quiet: %s" % self._window_state())
        if wrong_position or wrong_size:
            if self._attempts < _ATTEMPTS:
                self._attempts += 1
                self._trace(
                    "attempt %d: position %s size %s"
                    % (self._attempts, self.position, self.size)
                )
                if wrong_position:
                    self._request(
                        self._window.SetPosition, wx.Point(*self.position)
                    )
                if wrong_size:
                    self._request(self._window.SetSize, *self.size)
                self._wait_until_quiet()
                return
            self._trace("not applied after %d attempts: accepted" % _ATTEMPTS)
        self._accept_placement()
        if self.maximized and not self._window.IsMaximized():
            self._phase = "maximizing"
            self._attempts = 0
            self._step_started = time.perf_counter()
            if not self._window.IsIconized():
                self._request_maximize()
            self._wait_until_quiet()
            return
        self._finish()

    def _adapt_quiet_period(self):
        """Wait at least twice the platform's slowest answer so far, so
        a slow or loaded computer gets longer quiet periods."""
        quiet_ms = min(
            max(_QUIET_MS, int(2000 * self._slowest_answer)), _MAX_QUIET_MS
        )
        if quiet_ms != self._quiet_ms:
            self._trace(
                "slowest answer %.0f ms: quiet period %d ms"
                % (1000 * self._slowest_answer, quiet_ms)
            )
            self._quiet_ms = quiet_ms

    def _request(self, method, *args):
        """Call a wx method changing the geometry. Its own events are
        ours, not the platform's answer."""
        self._requesting = True
        try:
            method(*args)
        finally:
            self._requesting = False
        self._requested_at = time.perf_counter()

    def _request_maximize(self):
        self._attempts += 1
        self._trace("attempt %d: Maximize()" % self._attempts)
        self._request(self._window.Maximize)

    def _check_maximized(self):
        """Maximize again if it did not apply, at most _ATTEMPTS times;
        then accept."""
        if self._window.IsMaximized():
            self._finish()
        elif self._attempts < _ATTEMPTS:
            self._request_maximize()
            self._wait_until_quiet()
        else:
            self._trace("maximize not applied: accepted")
            self.maximized = False
            self._finish()

    def _accept_placement(self):
        """Keep the geometry the window got, as the platform decided."""
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        if self._positions_known:
            self.position = (pos.x, pos.y)
        self.size = (size.width, size.height)

    def _accept(self):
        """End placement with what the window has now; a saved maximized
        state not tried yet is kept."""
        if self._window.IsMaximized():
            self.maximized = True
        elif self._phase == "placing":
            self._accept_placement()
        else:
            self.maximized = False
        self._finish()

    def _finish(self):
        self.ready = True
        self._trace("placed: %s" % self._window_state())
        self._tracing = False

    # === State updates from the window (after placement) ===

    def cache_from_window(self):
        """Update the state from the window; position and size only in
        the normal state. Minimized, the state to restore to is kept."""
        if self._window.IsIconized():
            return
        self.maximized = self._window.IsMaximized()
        if self._is_normal_state():
            pos = self._window.GetPosition()
            size = self._window.GetSize()
            if self._positions_known:
                self.position = (pos.x, pos.y)
            if size.width > 100 and size.height > 100:
                self.size = (size.width, size.height)

    # === Event handlers ===

    def _on_show(self, event):
        if self._tracing:
            self._trace(
                "EVT_SHOW shown=%s: %s"
                % (event.IsShown(), self._window_state())
            )
        if event.IsShown() and self._min_size_pending:
            self._resend_lost_request()
            self._min_size_pending = False
            self._window.SetMinSize(self._min_size)
            self._trace("SetMinSize%s" % (self._min_size,))
        if event.IsShown() and self._direct:
            self._tracing = False
        elif event.IsShown() and not self.ready:
            if self._step_started is None:
                self._step_started = time.perf_counter()
                self._requested_at = self._step_started
            self._wait_until_quiet()
        event.Skip()

    def _resend_lost_request(self):
        """Before its first show wxGTK may defer mapping the window and
        lose the requested position: the window manager then places it
        at its own spot. If wx reports another geometry than requested,
        send the position again while the window is not mapped yet (see
        docs/WINDOW_GEOMETRY.md). wx passes a position on only when it
        differs from its own, hence the step aside."""
        if not self._positions_known or self.position is None:
            return
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        if ((pos.x, pos.y), (size.width, size.height)) == (
            self.position,
            self._requested_size,
        ):
            return
        x, y = self.position
        self._trace("request lost before the show: position sent again")
        if (pos.x, pos.y) == (x, y):
            self._request(self._window.SetPosition, wx.Point(x + 1, y))
        self._request(self._window.SetPosition, wx.Point(x, y))

    def _on_geometry_event(self, name):
        """Moves and resizes are the platform's while placing, a change
        only restarting the quiet period; the user's once placed."""
        if self._tracing:
            self._trace("%s: %s" % (name, self._window_state()))
        if self.ready:
            self.cache_from_window()
            return
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        seen = (pos.x, pos.y, size.width, size.height)
        seen += (self._window.IsMaximized(),)
        changed, self._seen = seen != self._seen, seen
        # Not before the show, not ours, and not a layout that changed
        # nothing (SendSizeEvent())
        if self._step_started is None or self._requesting or not changed:
            return
        answer = time.perf_counter() - self._requested_at
        self._slowest_answer = max(self._slowest_answer, answer)
        self._wait_until_quiet()

    def _on_move(self, event):
        self._on_geometry_event("EVT_MOVE")
        event.Skip()

    def _on_size(self, event):
        if self._tracing:
            self._resized_at = time.perf_counter()
        self._on_geometry_event("EVT_SIZE")
        event.Skip()

    def _on_maximize(self, event):
        self._on_geometry_event("EVT_MAXIMIZE")
        event.Skip()

    def _on_iconize(self, event):
        if self._tracing:
            self._trace("EVT_ICONIZE iconized=%s" % event.IsIconized())
        if self._maximize_on_restore and not event.IsIconized():
            self._maximize_on_restore = False
            if not self._window.IsMaximized():
                self._trace("restored: Maximize()", always=True)
                self._request(self._window.Maximize)
        if not self.ready and not event.IsIconized():
            if self._step_started is not None:
                self._step_started = time.perf_counter()
                self._requested_at = self._step_started
                if self._phase == "maximizing":
                    self._request_maximize()
                self._wait_until_quiet()
        event.Skip()

    def _on_idle(self, event):
        """Trace the cost of the last resize (layout and paint)."""
        event.Skip()
        if self._tracing and self._resized_at is not None:
            self._trace(
                "idle %.0f ms after the last EVT_SIZE (layout and paint)"
                % ((time.perf_counter() - self._resized_at) * 1000)
            )
            self._resized_at = None

    # === Monitors ===

    def _monitors(self):
        """(geometry, work area) of each monitor, as tuples."""
        monitors = []
        for i in range(wx.Display.GetCount()):
            display = wx.Display(i)
            geometry = tuple(display.GetGeometry())
            work_area = tuple(display.GetClientArea())  # Excludes taskbar
            self._trace(
                "monitor %d: %s, work area %s" % (i, geometry, work_area)
            )
            monitors.append((geometry, work_area))
        return monitors


class WindowDimensionsTracker(WindowGeometryTracker):
    """Track the dimensions of the main window in the settings."""

    def __init__(self, window, settings):
        super().__init__(window, settings, "window")

        # Handle start iconized setting (Task Coach specific)
        if self._should_start_iconized():
            self._trace("start iconized: Show() then Iconize(True)")
            if operating_system.isMac() or operating_system.isGTK():
                self._window.Show()
            self._window.Iconize(True)
            # Minimizing a window not shown yet drops the Maximize()
            # asked before the show (wxMSW)
            self._maximize_on_restore = self._direct and self.maximized
            if not operating_system.isMac() and self._get_setting(
                "hidewheniconized"
            ):
                wx.CallAfter(self._window.Hide)

    def _should_start_iconized(self):
        """Return whether the window should be opened iconized."""
        start_iconized = self._settings.get("window", "starticonized")
        return start_iconized == "Always"

    def save_position(self):
        """Save the position of the window in the settings."""
        self.save()
