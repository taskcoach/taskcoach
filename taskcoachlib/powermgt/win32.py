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

from taskcoachlib.powermgt.base import PowerStateMixinBase
import wx


class PowerStateMixin(PowerStateMixinBase):
    """Windows power state handling using native wxPython events.

    Uses wx.EVT_POWER_SUSPENDED and wx.EVT_POWER_RESUME instead of
    win32 WNDPROC subclassing to avoid crashes on application exit.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Bind wxPython's native power events
        self.Bind(wx.EVT_POWER_SUSPENDED, self.__onPowerSuspended)
        self.Bind(wx.EVT_POWER_RESUME, self.__onPowerResume)

    def __onPowerSuspended(self, event):
        """Handle system suspend event."""
        self.OnPowerState(self.POWEROFF)
        event.Skip()

    def __onPowerResume(self, event):
        """Handle system resume event."""
        self.OnPowerState(self.POWERON)
        event.Skip()
