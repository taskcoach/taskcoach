"""
Task Coach - Your friendly task manager
Copyright (C) 2026 Task Coach developers <developers@taskcoach.org>

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

# The compositor's idle notifications (ext-idle-notify-v1, from
# wayland-protocols staging/ext-idle-notify/ext-idle-notify-v1.xml),
# asked through libwayland-client, which GTK links on every Linux
# desktop: no Python binding to install (docs/IDLE.md).

import select
from ctypes import (
    CDLL,
    CFUNCTYPE,
    POINTER,
    Structure,
    Union,
    addressof,
    byref,
    c_char_p,
    c_int,
    c_int32,
    c_uint32,
    c_void_p,
    cast,
    pointer,
)


class WlInterface(Structure):
    """struct wl_interface (wayland-util.h)."""


class WlMessage(Structure):
    """struct wl_message (wayland-util.h)."""

    _fields_ = [
        ("name", c_char_p),
        ("signature", c_char_p),
        ("types", POINTER(POINTER(WlInterface))),
    ]


WlInterface._fields_ = [
    ("name", c_char_p),
    ("version", c_int),
    ("method_count", c_int),
    ("methods", POINTER(WlMessage)),
    ("event_count", c_int),
    ("events", POINTER(WlMessage)),
]


class WlArgument(Union):
    """union wl_argument (wayland-util.h), the members used here."""

    _fields_ = [
        ("u", c_uint32),
        ("i", c_int32),
        ("s", c_char_p),
        ("o", c_void_p),
        ("n", c_uint32),
    ]


_GLOBAL = CFUNCTYPE(None, c_void_p, c_void_p, c_uint32, c_char_p, c_uint32)
_GLOBAL_REMOVE = CFUNCTYPE(None, c_void_p, c_void_p, c_uint32)
_EVENT = CFUNCTYPE(None, c_void_p, c_void_p)


class _RegistryListener(Structure):
    _fields_ = [("global_", _GLOBAL), ("global_remove", _GLOBAL_REMOVE)]


class _NotificationListener(Structure):
    _fields_ = [("idled", _EVENT), ("resumed", _EVENT)]


# Request opcodes: their order in the protocol files
_DISPLAY_GET_REGISTRY = 1
_REGISTRY_BIND = 0
_NOTIFIER_GET_IDLE_NOTIFICATION = 1
_NOTIFIER_GET_INPUT_IDLE_NOTIFICATION = 2


def notification_request(version):
    """The notifier version to bind and the request to make, for the
    version the compositor offers. Version 2 counts input only, as idle
    readings do on every other platform; version 1 also counts idle
    inhibitors (a window playing a video), so KWin then stops the idle
    time while the user is away (docs/IDLE.md)."""
    if version >= 2:
        return 2, _NOTIFIER_GET_INPUT_IDLE_NOTIFICATION
    return 1, _NOTIFIER_GET_IDLE_NOTIFICATION


def _library():
    """libwayland-client with the calls used here typed. Raises OSError
    without the library, AttributeError before Wayland 1.20."""
    lib = CDLL("libwayland-client.so.0")
    for name, restype, argtypes in (
        ("wl_display_connect", c_void_p, [c_char_p]),
        ("wl_display_disconnect", None, [c_void_p]),
        ("wl_display_get_fd", c_int, [c_void_p]),
        ("wl_display_get_error", c_int, [c_void_p]),
        ("wl_display_roundtrip", c_int, [c_void_p]),
        ("wl_display_flush", c_int, [c_void_p]),
        ("wl_display_prepare_read", c_int, [c_void_p]),
        ("wl_display_read_events", c_int, [c_void_p]),
        ("wl_display_cancel_read", None, [c_void_p]),
        ("wl_display_dispatch_pending", c_int, [c_void_p]),
        (
            "wl_proxy_marshal_array_flags",
            c_void_p,
            [
                c_void_p,
                c_uint32,
                POINTER(WlInterface),
                c_uint32,
                c_uint32,
                POINTER(WlArgument),
            ],
        ),
        ("wl_proxy_add_listener", c_int, [c_void_p, c_void_p, c_void_p]),
        ("wl_proxy_get_version", c_uint32, [c_void_p]),
        ("wl_proxy_destroy", None, [c_void_p]),
    ):
        function = getattr(lib, name)
        function.restype = restype
        function.argtypes = argtypes
    return lib


class _Protocol:
    """ext-idle-notify-v1's two interfaces, as wayland-scanner lays
    them out from the protocol file."""

    def __init__(self, seat_interface):
        self.notifier = WlInterface()
        self.notification = WlInterface()
        self._types = (POINTER(WlInterface) * 3)(
            pointer(self.notification), None, pointer(seat_interface)
        )
        types = cast(self._types, POINTER(POINTER(WlInterface)))
        self._notifier_requests = (WlMessage * 3)(
            WlMessage(b"destroy", b"", None),
            WlMessage(b"get_idle_notification", b"nuo", types),
            WlMessage(b"get_input_idle_notification", b"2nuo", types),
        )
        self._notification_requests = (WlMessage * 1)(
            WlMessage(b"destroy", b"", None)
        )
        self._notification_events = (WlMessage * 2)(
            WlMessage(b"idled", b"", None), WlMessage(b"resumed", b"", None)
        )
        self.notifier.name = b"ext_idle_notifier_v1"
        self.notifier.version = 2
        self.notifier.method_count = 3
        self.notifier.methods = self._notifier_requests
        self.notification.name = b"ext_idle_notification_v1"
        self.notification.version = 2
        self.notification.method_count = 1
        self.notification.methods = self._notification_requests
        self.notification.event_count = 2
        self.notification.events = self._notification_events


class IdleNotification:
    """A notification from the session's compositor once the seat has
    had no input for timeout_ms (``idled``), and at the next input
    (``resumed``). The callbacks run inside poll(). ``version`` is the
    notifier version bound (notification_request). Raises OSError (no
    compositor, no notifier, a protocol error) or AttributeError
    (libwayland-client before 1.20)."""

    def __init__(self, timeout_ms, on_idled, on_resumed):
        self._lib = _library()
        self._display = None
        self._proxies = []
        self.version = None
        self._display = self._lib.wl_display_connect(None)
        if not self._display:
            raise OSError("no Wayland compositor to connect to")
        try:
            self._create(timeout_ms, on_idled, on_resumed)
        except BaseException:
            self.close()
            raise

    def _create(self, timeout_ms, on_idled, on_resumed):
        lib = self._lib
        seat_interface = WlInterface.in_dll(lib, "wl_seat_interface")
        self._protocol = protocol = _Protocol(seat_interface)
        registry = self._request(
            self._display,
            _DISPLAY_GET_REGISTRY,
            WlInterface.in_dll(lib, "wl_registry_interface"),
            lib.wl_proxy_get_version(self._display),
            [WlArgument(n=0)],
        )
        names = {}  # Interface: (global's name, its version)

        def on_global(data, proxy, name, interface, version):
            names.setdefault(interface, (name, version))

        # The C callbacks live as long as the connection
        self._callbacks = [
            _GLOBAL(on_global),
            _GLOBAL_REMOVE(lambda data, proxy, name: None),
            _EVENT(lambda data, proxy: on_idled()),
            _EVENT(lambda data, proxy: on_resumed()),
        ]
        self._registry_listener = _RegistryListener(*self._callbacks[:2])
        self._listen(registry, self._registry_listener)
        self._roundtrip()
        if b"ext_idle_notifier_v1" not in names or b"wl_seat" not in names:
            raise OSError("ext_idle_notifier_v1 not advertised")
        seat = self._bind(registry, names, b"wl_seat", seat_interface, 1)
        self.version, request = notification_request(
            names[b"ext_idle_notifier_v1"][1]
        )
        notifier = self._bind(
            registry,
            names,
            b"ext_idle_notifier_v1",
            protocol.notifier,
            self.version,
        )
        notification = self._request(
            notifier,
            request,
            protocol.notification,
            self.version,
            [WlArgument(n=0), WlArgument(u=timeout_ms), WlArgument(o=seat)],
        )
        self._notification_listener = _NotificationListener(
            *self._callbacks[2:]
        )
        self._listen(notification, self._notification_listener)
        self._roundtrip()
        self._fd = lib.wl_display_get_fd(self._display)

    def _request(self, proxy, opcode, interface, version, arguments):
        """A request creating an object: the new object's proxy."""
        new = self._lib.wl_proxy_marshal_array_flags(
            proxy,
            opcode,
            byref(interface),
            version,
            0,
            (WlArgument * len(arguments))(*arguments),
        )
        if not new:
            raise OSError("Wayland request %d failed" % opcode)
        self._proxies.append(new)
        return new

    def _bind(self, registry, names, name, interface, version):
        """The global's object, at the version given."""
        return self._request(
            registry,
            _REGISTRY_BIND,
            interface,
            version,
            [
                WlArgument(u=names[name][0]),
                WlArgument(s=name),
                WlArgument(u=version),
                WlArgument(n=0),
            ],
        )

    def _listen(self, proxy, listener):
        if self._lib.wl_proxy_add_listener(proxy, addressof(listener), None):
            raise OSError("Wayland listener not added")

    def _roundtrip(self):
        if self._lib.wl_display_roundtrip(self._display) < 0:
            raise OSError(
                "Wayland protocol error %d"
                % self._lib.wl_display_get_error(self._display)
            )

    def poll(self):
        """Run the callbacks of the events the compositor has sent,
        without waiting for more. False once the connection is lost."""
        lib, display = self._lib, self._display
        if not display:
            return False
        while lib.wl_display_prepare_read(display) != 0:
            if lib.wl_display_dispatch_pending(display) < 0:
                return False
        lib.wl_display_flush(display)
        try:
            readable = select.select([self._fd], [], [], 0)[0]
        except (OSError, ValueError):
            lib.wl_display_cancel_read(display)
            return False
        if not readable:
            lib.wl_display_cancel_read(display)
        elif lib.wl_display_read_events(display) < 0:
            return False
        return lib.wl_display_dispatch_pending(display) >= 0

    def close(self):
        """Disconnect: the compositor frees its side of every object, so
        the proxies are only freed here."""
        display = self._display
        self._display = None
        if not display:
            return
        for proxy in reversed(self._proxies):
            self._lib.wl_proxy_destroy(proxy)
        self._proxies = []
        self._lib.wl_display_disconnect(display)
