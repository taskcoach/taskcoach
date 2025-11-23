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
from taskcoachlib import operating_system


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
    """Track the size and position of a window in the settings."""

    def __init__(self, window, settings, section):
        super().__init__(settings, section)
        self._window = window
        self.__set_dimensions()
        self._window.Bind(wx.EVT_SIZE, self.on_change_size)
        self._window.Bind(wx.EVT_MOVE, self.on_change_position)
        self._window.Bind(wx.EVT_MAXIMIZE, self.on_maximize)

    def on_change_size(self, event):
        """Handle a size event by saving the new size of the window in the
        settings."""
        # Ignore the EVT_SIZE when the window is maximized or iconized.
        # Note how this depends on the EVT_MAXIMIZE being sent before the
        # EVT_SIZE.
        maximized = self._window.IsMaximized()
        if not maximized and not self._window.IsIconized():
            self.set_setting(
                "size",
                (
                    self._window.GetClientSize()
                    if operating_system.isMac()
                    else event.GetSize()
                ),
            )
        # Jerome, 2008/07/12: On my system (KDE 3.5.7), EVT_MAXIMIZE
        # is not triggered, so set 'maximized' to True here as well as in
        # onMaximize:
        self.set_setting("maximized", maximized)
        event.Skip()

    def on_change_position(self, event):
        """Handle a move event by saving the new position of the window in
        the settings."""
        if not self._window.IsMaximized():
            self.set_setting("maximized", False)
            if not self._window.IsIconized():
                # Only save position when the window is not maximized
                # *and* not minimized
                pos = event.GetPosition()
                self.set_setting("position", pos)

                # For dialogs, also save offset from parent for multi-monitor support
                if isinstance(self._window, wx.Dialog):
                    parent = self._window.GetParent()
                    if parent:
                        # Use GetScreenRect for consistency with restore logic
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

                        # Only save offset if dialog is on same monitor as parent
                        # Wrapped in try/except for backward compatibility with old settings
                        try:
                            if parent_monitor != wx.NOT_FOUND and parent_monitor == dialog_monitor:
                                offset = (pos.x - parent_rect.x, pos.y - parent_rect.y)
                                self.set_setting("parent_offset", offset)
                            else:
                                # Dialog on different monitor - save null offset to force re-center
                                self.set_setting("parent_offset", (-1, -1))
                        except (configparser.NoSectionError, configparser.NoOptionError):
                            # Old settings section without parent_offset support - skip saving
                            pass
        event.Skip()

    def on_maximize(self, event):
        """Handle a maximize event by saving the window maximization state in
        the settings."""
        self.set_setting("maximized", True)
        event.Skip()

    def __set_dimensions(self):
        """Set the window position and size based on the settings."""
        x, y = self.get_setting("position")  # pylint: disable=C0103
        width, height = self.get_setting("size")

        # Enforce minimum window size to prevent GTK warnings and usability issues
        # Different minimums for dialogs vs main windows
        if isinstance(self._window, wx.Dialog):
            min_width, min_height = 400, 300
        else:
            min_width, min_height = 600, 400

        # Ensure window size meets minimum requirements and is always positive
        width = max(width, min_width)
        height = max(height, min_height)

        # Sanity check: ensure we never have zero or negative dimensions
        if width <= 0 or height <= 0:
            width, height = min_width, min_height

        # Set minimum size constraint on the window to prevent user from resizing too small
        self._window.SetMinSize((min_width, min_height))

        # Track the target monitor for validation later
        # (GetFromWindow can return wrong index before window is fully realized)
        target_monitor_for_validation = None

        # For dialogs, position relative to parent window with multi-monitor support
        if isinstance(self._window, wx.Dialog):
            parent = self._window.GetParent()
            if parent:
                # Use parent's screen rect directly for positioning
                # This works correctly across monitors (like CentreOnParent does)
                parent_rect = parent.GetScreenRect()

                # Determine which monitor the parent is on
                parent_monitor = wx.Display.GetFromPoint(
                    wx.Point(parent_rect.x + parent_rect.width // 2,
                             parent_rect.y + parent_rect.height // 2)
                )
                target_monitor_for_validation = parent_monitor

                # Try to use saved parent_offset for positioning
                try:
                    offset_x, offset_y = self.get_setting("parent_offset")
                except (KeyError, TypeError, configparser.NoSectionError, configparser.NoOptionError):
                    # Old settings without parent_offset - use centered
                    offset_x, offset_y = -1, -1

                if offset_x != -1 and offset_y != -1:
                    # Calculate proposed position from parent + offset
                    proposed_x = parent_rect.x + offset_x
                    proposed_y = parent_rect.y + offset_y

                    # Check if proposed position would place dialog on same monitor as parent
                    test_x = proposed_x + width // 2
                    test_y = proposed_y + height // 2
                    proposed_monitor = wx.Display.GetFromPoint(wx.Point(test_x, test_y))

                    if proposed_monitor != wx.NOT_FOUND and proposed_monitor == parent_monitor:
                        # Same monitor as parent - use saved offset position
                        x, y = proposed_x, proposed_y
                    else:
                        # Would be on different monitor or off-screen - center on parent
                        x = parent_rect.x + (parent_rect.width - width) // 2
                        y = parent_rect.y + (parent_rect.height - height) // 2
                else:
                    # No saved offset - center on parent's window
                    x = parent_rect.x + (parent_rect.width - width) // 2
                    y = parent_rect.y + (parent_rect.height - height) // 2
            elif x == -1 and y == -1:
                # No parent, use safe default
                x, y = 50, 50
            # else: use saved position (x, y) for dialogs without parent
        else:
            # Main window positioning with multi-monitor support
            saved_monitor = self.get_setting("monitor_index")
            num_monitors = wx.Display.GetCount()

            if x == -1 and y == -1:
                # No saved position - center on primary monitor
                primary = wx.Display(0)
                rect = primary.GetGeometry()
                x = rect.x + (rect.width - width) // 2
                y = rect.y + (rect.height - height) // 2
            elif saved_monitor == -1:
                # Monitor index unknown (first run after update or legacy settings)
                # Use saved position - validation code below will handle if invalid
                pass
            elif saved_monitor >= 0 and saved_monitor < num_monitors:
                # Saved monitor still exists - use saved position
                # (position validation happens later in this method)
                pass
            else:
                # Saved monitor no longer exists - center on primary monitor
                primary = wx.Display(0)
                rect = primary.GetGeometry()
                x = rect.x + (rect.width - width) // 2
                y = rect.y + (rect.height - height) // 2

        if operating_system.isMac():
            # Under MacOS 10.5 and 10.4, when setting the size, the actual
            # window height is increased by 40 pixels. Dunno why, but it's
            # highly annoying. This doesn't hold for dialogs though. Sigh.
            if not isinstance(self._window, wx.Dialog):
                height += 18
        self._window.SetSize(x, y, width, height)
        if operating_system.isMac():
            self._window.SetClientSize((width, height))
        if self.get_setting("maximized"):
            self._window.Maximize()

        # Check that the window is on a valid display and move if necessary
        # Use target_monitor_for_validation if set, otherwise fall back to GetFromWindow
        # (GetFromWindow can return wrong index before window is fully realized)
        if target_monitor_for_validation is not None and target_monitor_for_validation != wx.NOT_FOUND:
            display_index = target_monitor_for_validation
        elif not isinstance(self._window, wx.Dialog):
            # Main window - try to use saved_monitor
            try:
                saved_monitor = self.get_setting("monitor_index")
                num_monitors = wx.Display.GetCount()
                if saved_monitor >= 0 and saved_monitor < num_monitors:
                    display_index = saved_monitor
                else:
                    display_index = wx.Display.GetFromWindow(self._window)
            except (KeyError, TypeError, configparser.NoSectionError, configparser.NoOptionError):
                display_index = wx.Display.GetFromWindow(self._window)
        else:
            display_index = wx.Display.GetFromWindow(self._window)

        if display_index == wx.NOT_FOUND:
            # Window is completely off-screen, use safe default position
            # Not (0, 0) because on OSX this hides the window bar...
            self._window.SetSize(50, 50, width, height)
            if operating_system.isMac():
                self._window.SetClientSize((width, height))
        else:
            # Window is on a display, but check if position is reasonable
            # Ensure the window is sufficiently visible (not just barely on screen)
            display = wx.Display(display_index)
            display_rect = display.GetGeometry()
            window_rect = self._window.GetRect()

            # Check if window position is too close to display edges (less than 50px visible)
            visible_left = max(window_rect.x, display_rect.x)
            visible_top = max(window_rect.y, display_rect.y)
            visible_right = min(window_rect.x + window_rect.width, display_rect.x + display_rect.width)
            visible_bottom = min(window_rect.y + window_rect.height, display_rect.y + display_rect.height)

            visible_width = visible_right - visible_left
            visible_height = visible_bottom - visible_top

            # If less than 50px visible in either dimension, center on current display
            if visible_width < 50 or visible_height < 50:
                # Center the window on the display it's currently on
                center_x = display_rect.x + (display_rect.width - width) // 2
                center_y = display_rect.y + (display_rect.height - height) // 2
                self._window.SetSize(center_x, center_y, width, height)
                if operating_system.isMac():
                    self._window.SetClientSize((width, height))


class WindowDimensionsTracker(WindowSizeAndPositionTracker):
    """Track the dimensions of a window in the settings."""

    def __init__(self, window, settings):
        super().__init__(window, settings, "window")
        self.__settings = settings
        if self.__start_iconized():
            if operating_system.isMac() or operating_system.isGTK():
                # Need to show the window on Mac OS X first, otherwise it
                # won't be properly minimized. On wxGTK we need to show the
                # window first, otherwise clicking the task bar icon won't
                # show it.
                self._window.Show()
            self._window.Iconize(True)
            if not operating_system.isMac() and self.get_setting(
                "hidewheniconized"
            ):
                # Seems like hiding the window after it's been
                # iconized actually closes it on Mac OS...
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
        """Save the position of the window in the settings."""
        iconized = self._window.IsIconized()
        self.set_setting("iconized", iconized)
        if not iconized:
            self.set_setting("position", self._window.GetPosition())
            # Save which monitor the window is on for multi-monitor support
            monitor_index = wx.Display.GetFromWindow(self._window)
            if monitor_index != wx.NOT_FOUND:
                self.set_setting("monitor_index", monitor_index)
