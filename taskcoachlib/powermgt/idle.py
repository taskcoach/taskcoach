"""
Task Coach - Your friendly task manager
Copyright (C) 2011 Task Coach developers <developers@taskcoach.org>

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

import logging
import os
import select
import time

import wx

from ctypes import (
    CDLL,
    CFUNCTYPE,
    POINTER,
    Structure,
    byref,
    c_char_p,
    c_int,
    c_uint,
    c_ulong,
    sizeof,
)
from taskcoachlib import operating_system


# ==============================================================================


def _summarize_exception(exc):
    """Compact one-line description of an exception for probe logs."""
    try:
        msg = str(exc)
    except Exception:
        msg = ""
    if msg:
        return "%s: %s" % (type(exc).__name__, msg.splitlines()[0][:160])
    return type(exc).__name__


# ==============================================================================
# Linux/BSD

if operating_system.isGTK():

    class XScreenSaverInfo(Structure):
        _fields_ = [
            ("window", c_ulong),
            ("state", c_int),
            ("kind", c_int),
            ("til_or_since", c_ulong),
            ("idle", c_ulong),
            ("event_mask", c_ulong),
        ]

    class LinuxIdleQuery(object):
        """Query idle time on Linux.

        Tries multiple methods in order:
        1. DBus org.gnome.Mutter.IdleMonitor (GNOME on Wayland/X11)
        2. DBus org.freedesktop.ScreenSaver (KDE Plasma 5)
        3. ext-idle-notify-v1 Wayland protocol (KDE Plasma 6,
           wlroots, COSMIC) via pywayland
        4. X11 MIT-SCREEN-SAVER extension (legacy X11)

        Uses lazy initialization to avoid loading libraries until
        actually needed. This prevents warnings when the idle detection
        feature is disabled.
        """

        # Short timeout the ext-idle-notify-v1 backend arms its
        # notification with. The compositor only reports idle in
        # this granularity; well below any sane minidletime
        # (minutes), so it is invisible to the state machine.
        _WL_TIMEOUT_MS = 1000

        def __init__(self):
            self._initialized = False
            # 'dbus_mutter', 'dbus_screensaver', 'ext_idle_notify',
            # 'x11_mit_screensaver', or None
            self._method = None
            self._warned = False
            self._probe_log = []  # list of (name, ok, detail)
            self.dpy = None
            self._dbus_proxy = None
            self._dbus_iface = None
            # ext-idle-notify-v1 state. _idle_since is the wall-clock
            # time the compositor reported the seat went idle, or
            # None while active. The idled/resumed handlers and the
            # EVT_IDLE reader all run on the main thread (events are
            # pumped non-blockingly in get_idle_seconds), so no lock
            # is needed. The registry/seat/notifier proxies are held
            # for the life of the connection so libwayland never
            # dispatches an event against a garbage-collected proxy.
            self._idle_since = None
            self._wl_display = None
            self._wl_notification = None
            self._wl_registry = None
            self._wl_seat = None
            self._wl_notifier = None

        def _try_dbus_mutter(self):
            """Try GNOME Mutter IdleMonitor via DBus. Returns (ok, detail)."""
            try:
                import dbus
                bus = dbus.SessionBus()
                proxy = bus.get_object(
                    'org.gnome.Mutter.IdleMonitor',
                    '/org/gnome/Mutter/IdleMonitor/Core'
                )
                iface = dbus.Interface(proxy, 'org.gnome.Mutter.IdleMonitor')
                # Test that it works
                iface.GetIdletime()
                self._dbus_proxy = proxy
                self._dbus_iface = iface
                return True, None
            except Exception as e:
                return False, _summarize_exception(e)

        def _try_dbus_screensaver(self):
            """Try freedesktop ScreenSaver via DBus (KDE).

            Returns (ok, detail).
            """
            try:
                import dbus
                bus = dbus.SessionBus()
                proxy = bus.get_object(
                    'org.freedesktop.ScreenSaver',
                    '/ScreenSaver'
                )
                iface = dbus.Interface(proxy, 'org.freedesktop.ScreenSaver')
                # Test that it works
                iface.GetSessionIdleTime()
                self._dbus_proxy = proxy
                self._dbus_iface = iface
                return True, None
            except Exception as e:
                return False, _summarize_exception(e)

        def _wl_on_idled(self, notification):
            """ext-idle-notify-v1 'idled' event (main thread)."""
            self._idle_since = time.time()

        def _wl_on_resumed(self, notification):
            """ext-idle-notify-v1 'resumed' event (main thread)."""
            self._idle_since = None

        def _wl_pump(self):
            """Drain queued ext-idle-notify-v1 events without blocking.

            Called on the main thread from get_idle_seconds(); the
            idled/resumed handlers update _idle_since. dispatch(block=
            False) only dispatches already-queued events and never
            touches the fd, while pywayland's read() blocks when the fd
            has no data, so read() is guarded by a zero-timeout select.
            Any failure (compositor gone, protocol error) tears the
            connection down and degrades to no idle detection rather
            than letting a dead connection spin or crash.
            """
            display = self._wl_display
            if display is None:
                return
            try:
                display.flush()
                if select.select([display.get_fd()], [], [], 0)[0]:
                    display.read()
                display.dispatch(block=False)
            except Exception:
                self._teardown_wl()

        def _teardown_wl(self):
            """Disconnect the ext-idle-notify-v1 side connection.

            Safe to call from the main thread or __del__: no other
            thread shares the display.
            """
            display = self._wl_display
            self._wl_display = None
            self._wl_notification = None
            self._wl_registry = None
            self._wl_seat = None
            self._wl_notifier = None
            self._idle_since = None
            if display is not None:
                try:
                    display.disconnect()
                except Exception:
                    pass

        def _try_ext_idle_notify(self):
            """Try the ext-idle-notify-v1 Wayland protocol.

            Covers KDE Plasma 6 (where org.freedesktop.ScreenSaver
            GetSessionIdleTime is stubbed to NotSupported), wlroots
            compositors and COSMIC. Returns (ok, detail).

            The protocol is event-based (idled/resumed), not a
            pollable query, so a daemon thread holds a notification
            armed at a short timeout and records the idle timestamp;
            get_idle_seconds() synthesises a value from it.
            """
            if not os.environ.get("WAYLAND_DISPLAY"):
                return False, "no WAYLAND_DISPLAY (not a Wayland session)"
            try:
                from pywayland.client import Display
                from pywayland.protocol.wayland import WlSeat
                # Distro python3-pywayland ships only the core wayland
                # protocol; the ext-idle-notify-v1 binding is vendored
                # (see taskcoachlib/thirdparty/ext_idle_notify_v1).
                from taskcoachlib.thirdparty.ext_idle_notify_v1 import (
                    ExtIdleNotifierV1,
                )
            except ImportError as e:
                return False, _summarize_exception(e)

            display = None
            try:
                display = Display()
                display.connect()

                found = {"notifier": None, "seat": None}

                def registry_global(registry, id_, interface, version):
                    if interface == "ext_idle_notifier_v1":
                        found["notifier"] = registry.bind(
                            id_, ExtIdleNotifierV1, min(version, 1)
                        )
                    elif interface == "wl_seat":
                        found["seat"] = registry.bind(
                            id_, WlSeat, min(version, 1)
                        )

                registry = display.get_registry()
                registry.dispatcher["global"] = registry_global
                display.roundtrip()

                if found["notifier"] is None or found["seat"] is None:
                    return False, "ext_idle_notifier_v1 not advertised"

                notification = found["notifier"].get_idle_notification(
                    self._WL_TIMEOUT_MS, found["seat"]
                )
                notification.dispatcher["idled"] = self._wl_on_idled
                notification.dispatcher["resumed"] = self._wl_on_resumed
                display.roundtrip()
            except Exception as e:
                if display is not None:
                    try:
                        display.disconnect()
                    except Exception:
                        pass
                return False, _summarize_exception(e)

            self._wl_display = display
            self._wl_notification = notification
            self._wl_registry = registry
            self._wl_seat = found["seat"]
            self._wl_notifier = found["notifier"]
            return True, None

        def _try_x11_screensaver(self):
            """Try X11 MIT-SCREEN-SAVER extension. Returns (ok, detail)."""
            try:
                _x11 = CDLL("libX11.so.6")

                self.XOpenDisplay = CFUNCTYPE(c_ulong, c_char_p)(
                    ("XOpenDisplay", _x11)
                )
                self.XCloseDisplay = CFUNCTYPE(c_int, c_ulong)(
                    ("XCloseDisplay", _x11)
                )
                self.XRootWindow = CFUNCTYPE(c_ulong, c_ulong, c_int)(
                    ("XRootWindow", _x11)
                )
                # XQueryExtension to check if MIT-SCREEN-SAVER is available
                self.XQueryExtension = CFUNCTYPE(
                    c_int, c_ulong, c_char_p,
                    POINTER(c_int), POINTER(c_int), POINTER(c_int)
                )(("XQueryExtension", _x11))

                self.dpy = self.XOpenDisplay(None)
                if not self.dpy:
                    return False, "XOpenDisplay failed (no DISPLAY?)"

                # Check if MIT-SCREEN-SAVER extension is available
                major_opcode = c_int()
                first_event = c_int()
                first_error = c_int()
                has_extension = self.XQueryExtension(
                    self.dpy,
                    b"MIT-SCREEN-SAVER",
                    byref(major_opcode),
                    byref(first_event),
                    byref(first_error)
                )

                if not has_extension:
                    return False, "MIT-SCREEN-SAVER extension not present"

                _xss = CDLL("libXss.so.1")

                self.XScreenSaverAllocInfo = CFUNCTYPE(
                    POINTER(XScreenSaverInfo)
                )(("XScreenSaverAllocInfo", _xss))
                self.XScreenSaverQueryInfo = CFUNCTYPE(
                    c_int, c_ulong, c_ulong, POINTER(XScreenSaverInfo)
                )(("XScreenSaverQueryInfo", _xss))

                self.info = self.XScreenSaverAllocInfo()
                return True, None

            except OSError as e:
                return False, _summarize_exception(e)

        def _initialize(self):
            """Lazy initialization - try available methods in order."""
            if self._initialized:
                return
            self._initialized = True

            # Try methods in order of preference; record outcome of
            # each. x11_mit_screensaver is probed before the DBus
            # screensaver because on an X11 session it queries the X
            # server's real input idle directly, whereas KDE Plasma 6
            # answers org.freedesktop.ScreenSaver.GetSessionIdleTime
            # with a bogus non-zero value (instead of raising), which
            # would otherwise be wrongly selected and make the notice
            # fire constantly. dbus_screensaver is kept last as a
            # fallback for the few Plasma 5 setups that rely on it.
            ok, detail = self._try_dbus_mutter()
            self._probe_log.append(('dbus_mutter', ok, detail))
            if ok:
                self._method = 'dbus_mutter'
                return

            ok, detail = self._try_x11_screensaver()
            self._probe_log.append(('x11_mit_screensaver', ok, detail))
            if ok:
                self._method = 'x11_mit_screensaver'
                return

            ok, detail = self._try_ext_idle_notify()
            self._probe_log.append(('ext_idle_notify', ok, detail))
            if ok:
                self._method = 'ext_idle_notify'
                return

            ok, detail = self._try_dbus_screensaver()
            self._probe_log.append(('dbus_screensaver', ok, detail))
            if ok:
                self._method = 'dbus_screensaver'
                return

            self._method = None

        def get_backend_name(self):
            return self._method

        def get_probe_log(self):
            return list(self._probe_log)

        def __del__(self):
            if self.dpy and hasattr(self, 'XCloseDisplay'):
                self.XCloseDisplay(self.dpy)
            if getattr(self, '_wl_display', None) is not None:
                self._teardown_wl()

        def get_idle_seconds(self):
            self._initialize()

            if self._method == 'dbus_mutter':
                try:
                    # Returns milliseconds
                    return self._dbus_iface.GetIdletime() / 1000
                except Exception:
                    pass
            elif self._method == 'dbus_screensaver':
                try:
                    # Returns seconds
                    return self._dbus_iface.GetSessionIdleTime()
                except Exception:
                    pass
            elif self._method == 'ext_idle_notify':
                self._wl_pump()
                since = self._idle_since
                if since is None:
                    return 0
                # The compositor only told us once the seat had been
                # idle for _WL_TIMEOUT_MS, so add that back in.
                return (
                    (time.time() - since)
                    + (self._WL_TIMEOUT_MS / 1000.0)
                )
            elif self._method == 'x11_mit_screensaver':
                self.XScreenSaverQueryInfo(
                    self.dpy, self.XRootWindow(self.dpy, 0), self.info
                )
                return self.info.contents.idle / 1000

            # No method available - log warning once
            if not self._warned:
                self._warned = True
                logging.warning(
                    "Idle time detection unavailable on this system. "
                    "The idle time notification feature will be disabled."
                )
            return 0

    IdleQuery = LinuxIdleQuery

elif operating_system.isWindows():
    from ctypes import windll

    class LASTINPUTINFO(Structure):
        _fields_ = [("cbSize", c_uint), ("dwTime", c_uint)]

    class WindowsIdleQuery(object):
        def __init__(self):
            self.GetTickCount = windll.kernel32.GetTickCount
            self.GetLastInputInfo = windll.user32.GetLastInputInfo

            self.lastInputInfo = LASTINPUTINFO()
            self.lastInputInfo.cbSize = sizeof(self.lastInputInfo)

        def get_idle_seconds(self):
            self.GetLastInputInfo(byref(self.lastInputInfo))
            return (self.GetTickCount() - self.lastInputInfo.dwTime) / 1000

        def get_backend_name(self):
            return 'win32_GetLastInputInfo'

        def get_probe_log(self):
            return [('win32_GetLastInputInfo', True, None)]

    IdleQuery = WindowsIdleQuery

elif operating_system.isMac():
    # macOS idle time detection using IOKit via ctypes
    # Queries the HIDIdleTime property from IOHIDSystem

    from ctypes import cdll, c_void_p, c_uint32, c_int32

    class MacIdleQuery:
        """Query idle time on macOS using IOKit.

        Uses IORegistryEntryCreateCFProperty to get HIDIdleTime
        from IOHIDSystem. This is the standard way to get system
        idle time on macOS.
        """

        def __init__(self):
            self._warned = False
            self._init_error = None
            try:
                # Load IOKit and CoreFoundation frameworks
                self._iokit = cdll.LoadLibrary(
                    '/System/Library/Frameworks/IOKit.framework/IOKit'
                )
                self._cf = cdll.LoadLibrary(
                    '/System/Library/Frameworks/'
                    'CoreFoundation.framework/CoreFoundation'
                )

                # IOKit functions
                self._iokit.IOServiceGetMatchingService.restype = c_uint32
                self._iokit.IOServiceGetMatchingService.argtypes = [
                    c_uint32, c_void_p
                ]
                self._iokit.IOServiceMatching.restype = c_void_p
                self._iokit.IOServiceMatching.argtypes = [c_void_p]
                self._iokit.IORegistryEntryCreateCFProperty.restype = c_void_p
                self._iokit.IORegistryEntryCreateCFProperty.argtypes = [
                    c_uint32, c_void_p, c_void_p, c_uint32
                ]
                self._iokit.IOObjectRelease.restype = c_int32
                self._iokit.IOObjectRelease.argtypes = [c_uint32]

                # CoreFoundation functions
                self._cf.CFStringCreateWithCString.restype = c_void_p
                self._cf.CFStringCreateWithCString.argtypes = [
                    c_void_p, c_void_p, c_uint32
                ]
                self._cf.CFNumberGetValue.restype = c_int32
                self._cf.CFNumberGetValue.argtypes = [
                    c_void_p, c_int32, c_void_p
                ]
                self._cf.CFRelease.restype = None
                self._cf.CFRelease.argtypes = [c_void_p]

                # Constants
                self._kCFStringEncodingUTF8 = 0x08000100
                self._kCFNumberSInt64Type = 4
                self._kIOMasterPortDefault = 0

                # Create CFString for "HIDIdleTime"
                self._idle_key = self._cf.CFStringCreateWithCString(
                    None, b"HIDIdleTime", self._kCFStringEncodingUTF8
                )

                self._available = True

            except OSError as e:
                self._available = False
                self._init_error = _summarize_exception(e)

        def __del__(self):
            if hasattr(self, '_idle_key') and self._idle_key:
                try:
                    self._cf.CFRelease(self._idle_key)
                except Exception:
                    pass

        def get_idle_seconds(self):
            if not self._available:
                if not self._warned:
                    self._warned = True
                    logging.warning(
                        "Idle time detection unavailable on this system. "
                        "The idle time notification feature will be disabled."
                    )
                return 0

            try:
                # Get IOHIDSystem service
                hid_service = self._iokit.IOServiceGetMatchingService(
                    self._kIOMasterPortDefault,
                    self._iokit.IOServiceMatching(b"IOHIDSystem")
                )

                if not hid_service:
                    return 0

                try:
                    # Get HIDIdleTime property
                    idle_time_ref = (
                        self._iokit.IORegistryEntryCreateCFProperty(
                            hid_service, self._idle_key, None, 0
                        )
                    )

                    if not idle_time_ref:
                        return 0

                    try:
                        # Get the value as int64 (nanoseconds)
                        from ctypes import c_int64
                        idle_ns = c_int64()
                        self._cf.CFNumberGetValue(
                            idle_time_ref,
                            self._kCFNumberSInt64Type,
                            byref(idle_ns),
                        )
                        # Convert nanoseconds to seconds
                        return idle_ns.value / 1_000_000_000
                    finally:
                        self._cf.CFRelease(idle_time_ref)
                finally:
                    self._iokit.IOObjectRelease(hid_service)

            except Exception:
                return 0

        def get_backend_name(self):
            return 'iokit_HIDIdleTime' if self._available else None

        def get_probe_log(self):
            return [('iokit_HIDIdleTime', self._available, self._init_error)]

    IdleQuery = MacIdleQuery


# ==============================================================================
#


class IdleNotifier(wx.EvtHandler, IdleQuery):
    STATE_SLEEPING = 0
    STATE_AWAKE = 1

    def __init__(self):
        wx.EvtHandler.__init__(self)
        IdleQuery.__init__(self)

        self.state = self.STATE_AWAKE
        self._last_activity = time.time()
        self._gone_to_sleep = None

        self._bound = True
        wx.GetApp().Bind(wx.EVT_IDLE, self._on_idle)

    def stop(self):
        self.pause()

    def pause(self):
        if self._bound:
            wx.GetApp().Unbind(wx.EVT_IDLE, handler=self._on_idle)
            self._bound = False

    def resume(self):
        self.state = self.STATE_AWAKE
        self._last_activity = time.time()
        if not self._bound:
            wx.GetApp().Bind(wx.EVT_IDLE, self._on_idle)

    def _check(self):
        if (
            self.state == self.STATE_AWAKE
            and time.time() - self._last_activity >= self.get_min_idle_time()
        ):
            self._gone_to_sleep = self._last_activity
            self.state = self.STATE_SLEEPING
            self.sleep()
        elif (
            self.state == self.STATE_SLEEPING
            and time.time() - self._last_activity < self.get_min_idle_time()
        ):
            self.state = self.STATE_AWAKE
            self.wake(self._gone_to_sleep)

    def _on_idle(self, event):
        self._check()
        self._last_activity = time.time() - self.get_idle_seconds()
        self._check()
        event.Skip()

    def poweroff(self):
        """
        Call this when the computer goes to sleep.
        """
        if self._bound:
            wx.GetApp().Unbind(wx.EVT_IDLE, handler=self._on_idle)
            self._bound = False

    def poweron(self):
        """
        Call this when the computer resumes from sleep.
        """
        if not self._bound:
            wx.GetApp().Bind(wx.EVT_IDLE, self._on_idle)
            self._bound = True
        self._check()
        self._last_activity = time.time() - self.get_idle_seconds()
        self._check()

    def get_min_idle_time(self):
        """
        Should return the minimum time in seconds before going idle.
        """
        raise NotImplementedError

    def sleep(self):
        """
        Called when the min idle time has elapsed without any user
        input.
        """

    def wake(self, timestamp):
        """
        Called when the computer is not idle any more.
        """
