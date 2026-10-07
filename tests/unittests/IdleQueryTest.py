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

import unittest
from unittest import mock

import test
from taskcoachlib.powermgt import idle

try:
    from gi.repository import Gio, GLib  # noqa: F401
except ImportError:  # Off Linux: the test is skipped
    Gio = GLib = None

_MONITOR = "org.gnome.Mutter.IdleMonitor"


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
