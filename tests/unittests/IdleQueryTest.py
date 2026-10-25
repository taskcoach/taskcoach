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
import sys
import unittest
import xml.etree.ElementTree as ElementTree
from unittest import mock

import test
from taskcoachlib.powermgt import idle, wayland_idle

try:
    from gi.repository import Gio, GLib  # noqa: F401
except ImportError:  # Off Linux: the test is skipped
    Gio = GLib = None

_MONITOR = "org.gnome.Mutter.IdleMonitor"
_WAYLAND_XML = "/usr/share/wayland/wayland.xml"
_IDLE_NOTIFY_XML = (
    "/usr/share/wayland-protocols/staging/ext-idle-notify/"
    "ext-idle-notify-v1.xml"
)


class FakeSessionBus:
    """GNOME's idle monitor on the session bus: each answer, in turn,
    is idle milliseconds or an error to raise."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def call_sync(self, name, path, interface, method, *args):
        self.calls.append((name, method, args[-2]))  # The timeout
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return GLib.Variant("(t)", (answer,))


@unittest.skipIf(GLib is None, "Linux only: no PyGObject")
class LinuxIdleQueryTest(test.TestCase):
    def setUp(self):
        super().setUp()
        # Neither X11's nor Wayland's reading: only the D-Bus one
        for probe in "_try_x11_screensaver", "_try_ext_idle_notify":
            patcher = mock.patch.object(
                idle.LinuxIdleQuery, probe, return_value=(False, "absent")
            )
            patcher.start()
            self.addCleanup(patcher.stop)

    def query(self, bus):
        with mock.patch.object(Gio, "bus_get_sync", return_value=bus):
            query = idle.LinuxIdleQuery()
            query.get_idle_seconds()  # Probes, then reads
        return query

    def test_gnome_reading_in_seconds(self):
        query = self.query(FakeSessionBus(1000, 1000, 30000))
        self.assertEqual(30.0, query.get_idle_seconds())

    def test_each_reading_asks_the_monitor_by_name(self):
        # Whoever owns the name now answers: a restarted GNOME Shell
        bus = FakeSessionBus(1000, 1000, 2000)
        query = self.query(bus)
        query.get_idle_seconds()
        self.assertEqual(
            [(_MONITOR, "GetIdletime")] * 3,
            [(name, method) for name, method, _ in bus.calls],
        )

    def test_a_failed_reading_does_not_end_the_readings(self):
        bus = FakeSessionBus(1000, 1000, GLib.Error("no reply"), 5000)
        query = self.query(bus)
        self.assertEqual(0, query.get_idle_seconds())
        self.assertEqual(5.0, query.get_idle_seconds())

    def test_failed_readings_logged_once_and_their_end(self):
        bus = FakeSessionBus(
            1000, 1000, GLib.Error("no reply"), GLib.Error("no reply"), 5000
        )
        query = self.query(bus)
        with mock.patch.object(idle, "log_step") as log, mock.patch.object(
            idle.logging, "warning"
        ) as warning:
            for _ in range(3):
                query.get_idle_seconds()
        failed, again = [call.args[0] for call in log.call_args_list]
        self.assertTrue(failed.startswith("GNOME idle monitor not read"))
        self.assertEqual("GNOME idle monitor read again", again)
        warning.assert_not_called()

    def test_a_reading_waits_at_most_a_second(self):
        bus = FakeSessionBus(1000, 1000)
        self.query(bus)
        self.assertEqual({1000}, {timeout for _, _, timeout in bus.calls})

    def test_without_the_monitor_the_other_readings_are_tried(self):
        query = self.query(FakeSessionBus(GLib.Error("no owner")))
        self.assertEqual(
            ["dbus_mutter", "x11_mit_screensaver", "ext_idle_notify"],
            [name for name, _, _ in query.get_probe_log()],
        )
        self.assertIsNone(query.get_backend_name())


class FakeCompositor:
    """The compositor's idle notification: each poll() delivers the
    events sent since the last one, as libwayland-client would."""

    def __init__(self):
        self.notifications = []
        self.handlers = {}
        self.sent = []
        self.connected = True
        self.closed = False
        self.version = 2  # The notifier version bound: KWin 6.4+

    def __call__(self, timeout_ms, on_idled, on_resumed):
        self.notifications.append(timeout_ms)
        self.handlers = {"idled": on_idled, "resumed": on_resumed}
        return self

    def send(self, event):
        self.sent.append(event)

    def poll(self):
        while self.sent:
            self.handlers[self.sent.pop(0)]()
        return self.connected

    def close(self):
        self.closed = True


@unittest.skipIf(GLib is None, "Linux only: no PyGObject")
class WaylandIdleQueryTest(test.TestCase):
    """KDE Plasma, wlroots desktops and COSMIC on Wayland: no GNOME
    monitor, no X11 extension (Xwayland drops it), and no Python
    Wayland binding installed, as on Kubuntu."""

    def setUp(self):
        super().setUp()
        self.compositor = FakeCompositor()
        for patcher in (
            mock.patch.object(
                idle.LinuxIdleQuery,
                "_try_dbus_mutter",
                return_value=(False, "absent"),
            ),
            mock.patch.object(
                idle.LinuxIdleQuery,
                "_try_x11_screensaver",
                return_value=(False, "absent"),
            ),
            mock.patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}),
            mock.patch.dict(sys.modules, {"pywayland": None}),
            mock.patch.object(
                wayland_idle, "IdleNotification", self.compositor
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.query = idle.LinuxIdleQuery()

    def test_the_compositor_is_read_without_a_python_binding(self):
        self.assertEqual(0, self.query.get_idle_seconds())
        self.assertEqual("ext_idle_notify", self.query.get_backend_name())

    def test_notified_after_a_second_without_input(self):
        self.query.get_idle_seconds()
        self.assertEqual([1000], self.compositor.notifications)

    def test_idle_counts_from_the_notification(self):
        self.query.get_idle_seconds()
        self.compositor.send("idled")
        # The notification comes a second after the last input
        self.assertAlmostEqual(1.0, self.query.get_idle_seconds(), delta=0.5)

    def test_input_ends_the_idle_time(self):
        self.query.get_idle_seconds()
        self.compositor.send("idled")
        self.compositor.send("resumed")
        self.assertEqual(0, self.query.get_idle_seconds())

    def test_a_lost_connection_reads_not_idle(self):
        self.query.get_idle_seconds()
        self.compositor.send("idled")
        self.query.get_idle_seconds()
        self.compositor.connected = False
        self.assertEqual(0, self.query.get_idle_seconds())
        self.assertTrue(self.compositor.closed)


def _protocol_messages(element):
    """(name, signature, argument types) of each request or event, as
    wayland-scanner writes them."""
    letters = {"int": "i", "uint": "u", "string": "s", "object": "o"}
    letters["new_id"] = "n"
    messages = []
    for message in element:
        signature = message.get("since", "")
        types = []
        for argument in message.findall("arg"):
            if argument.get("allow-null") == "true":
                signature += "?"
            signature += letters[argument.get("type")]
            types.append(argument.get("interface"))
        messages.append((message.get("name"), signature, types))
    return messages


@unittest.skipUnless(
    os.path.exists(_WAYLAND_XML) and os.path.exists(_IDLE_NOTIFY_XML),
    "needs wayland.xml (libwayland-dev) and wayland-protocols",
)
class WaylandIdleProtocolTest(test.TestCase):
    """The protocol tables and requests written by hand in wayland_idle
    against the protocol files: a mistake there crashes the app."""

    def interfaces(self, path):
        root = ElementTree.parse(path).getroot()
        return {
            interface.get("name"): interface
            for interface in root.findall("interface")
        }

    def table(self, interface, count_field, array_field):
        messages = []
        for index in range(getattr(interface, count_field)):
            message = getattr(interface, array_field)[index]
            signature = message.signature.decode()
            arguments = len(signature.lstrip("0123456789").replace("?", ""))
            types = [
                (
                    message.types[i].contents.name.decode()
                    if message.types and message.types[i]
                    else None
                )
                for i in range(arguments)
            ]
            messages.append((message.name.decode(), signature, types))
        return messages

    def test_tables_as_the_protocol_file(self):
        library = wayland_idle._library()
        seat = wayland_idle.WlInterface.in_dll(library, "wl_seat_interface")
        protocol = wayland_idle._Protocol(seat)
        for interface in protocol.notifier, protocol.notification:
            element = self.interfaces(_IDLE_NOTIFY_XML)[
                interface.name.decode()
            ]
            self.assertEqual(int(element.get("version")), interface.version)
            self.assertEqual(
                _protocol_messages(element.findall("request")),
                self.table(interface, "method_count", "methods"),
            )
            self.assertEqual(
                _protocol_messages(element.findall("event")),
                self.table(interface, "event_count", "events"),
            )

    def request(self, path, interface, name):
        """The request's (version it came in, number)."""
        requests = self.interfaces(path)[interface].findall("request")
        number = [r.get("name") for r in requests].index(name)
        return int(requests[number].get("since", "1")), number

    def test_request_numbers_as_the_protocol_files(self):
        self.assertEqual(
            (1, wayland_idle._DISPLAY_GET_REGISTRY),
            self.request(_WAYLAND_XML, "wl_display", "get_registry"),
        )
        self.assertEqual(
            (1, wayland_idle._REGISTRY_BIND),
            self.request(_WAYLAND_XML, "wl_registry", "bind"),
        )

    def test_input_only_notification_where_offered(self):
        # KWin 6.4+: the request that idle inhibitors (a window playing
        # a video) do not stop, at the version it came in
        input_only = self.request(
            _IDLE_NOTIFY_XML,
            "ext_idle_notifier_v1",
            "get_input_idle_notification",
        )
        self.assertEqual(input_only, wayland_idle.notification_request(2))
        # A later version: bound at the last one whose requests we know
        self.assertEqual(input_only, wayland_idle.notification_request(3))

    def test_first_notification_on_version_1_compositors(self):
        # KWin 5.27 to 6.3, wlroots 0.18
        self.assertEqual(
            self.request(
                _IDLE_NOTIFY_XML,
                "ext_idle_notifier_v1",
                "get_idle_notification",
            ),
            wayland_idle.notification_request(1),
        )
