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

# pylint: disable=F0401
import win32api
import win32gui
import win32con
import wx


class PowerStateMixin(PowerStateMixinBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Store handle now - can't call GetHandle() later when window is being destroyed
        self.__hWnd = self.GetHandle()
        self.__oldProc = win32gui.SetWindowLong(
            self.__hWnd, win32con.GWL_WNDPROC, self.__WndProc
        )

    def __WndProc(self, hWnd, msg, wParam, lParam):
        if msg == win32con.WM_DESTROY:
            try:
                win32api.SetWindowLong(
                    self.__hWnd, win32con.GWL_WNDPROC, self.__oldProc
                )
            except Exception:
                pass  # Window already destroyed, nothing to restore

        if msg == win32con.WM_POWERBROADCAST:
            if wParam == win32con.PBT_APMSUSPEND:
                wx.CallAfter(self.OnPowerState, self.POWEROFF)
            elif wParam == win32con.PBT_APMRESUMESUSPEND:
                wx.CallAfter(self.OnPowerState, self.POWERON)

        return win32gui.CallWindowProc(
            self.__oldProc, hWnd, msg, wParam, lParam
        )
