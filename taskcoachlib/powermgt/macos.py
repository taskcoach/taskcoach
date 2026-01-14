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

# macOS power state notifications
#
# Note: The original implementation used a native C extension to register
# for IOKit power notifications. This has been replaced with the base
# implementation as power notification callbacks require complex CFRunLoop
# integration that's difficult to implement purely in Python.
#
# The idle time detection (which is more important for Task Coach's
# effort tracking feature) is still fully functional using ctypes.

from taskcoachlib.powermgt.base import PowerStateMixinBase


class PowerStateMixin(PowerStateMixinBase):
    """macOS power state mixin.

    Currently uses the base implementation (no-op). Power state notifications
    on macOS require registering with IORegisterForSystemPower and running
    a CFRunLoop, which is complex to implement in pure Python.

    The related idle time detection feature works correctly via ctypes.
    """
    pass
