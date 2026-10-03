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
from unittest import mock

import test
from taskcoachlib import config, patterns, persistence
from taskcoachlib.domain import effort, task
from taskcoachlib.gui import idlecontroller


class IdleControllerTest(test.wxTestCase):
    """The idle poll runs only while tracking with the notice on."""

    def setUp(self):
        super().setUp()
        self.settings = config.settings.current()
        self.task_file = persistence.TaskFile()
        self.controller = idlecontroller.IdleController(
            self.settings, self.task_file.efforts()
        )
        self.idle_seconds = 0
        self.controller.get_idle_seconds = lambda: self.idle_seconds
        self.slept = []
        self.woke = []
        self.controller.sleep = lambda: self.slept.append(True)
        self.controller.wake = self.woke.append
        self.task = task.Task()
        self.task_file.tasks().append(self.task)

    def tearDown(self):
        super().tearDown()
        self.task_file.close()
        self.task_file.stop()

    def enable(self, minutes=1):
        self.settings.setint("feature", "minidletime", minutes)

    def track(self):
        self.task.addEffort(effort.Effort(self.task))

    def tick(self):
        patterns.Event("timer.second", self, None).send()

    def power(self, event_type):
        # As the main window sends it when the computer sleeps or wakes
        patterns.Event(event_type, self).send()

    def logged_summaries(self, act):
        """The backend summaries act logs."""
        with mock.patch.object(idlecontroller, "log_step") as log:
            act()
        return [
            call
            for call in log.call_args_list
            if call.args[0].startswith("Probing idle backend")
        ]

    def test_turned_on_later_logs_the_backend_once(self):
        # As at startup when it is on then (docs/IDLE.md)
        self.assertEqual(1, len(self.logged_summaries(self.enable)))
        self.assertEqual([], self.logged_summaries(lambda: self.enable(2)))

    def test_turned_off_logs_nothing(self):
        self.assertEqual([], self.logged_summaries(lambda: self.enable(0)))

    def test_disabled_does_not_poll(self):
        self.track()
        self.assertFalse(self.controller.is_polling())

    def test_disabled_never_sleeps(self):
        self.track()
        self.idle_seconds = 3600
        self.tick()
        self.assertEqual([], self.slept)

    def test_not_tracking_does_not_poll(self):
        self.enable()
        self.assertFalse(self.controller.is_polling())

    def test_tracking_while_enabled_polls(self):
        self.enable()
        self.track()
        self.assertTrue(self.controller.is_polling())

    def test_stop_tracking_stops_polling(self):
        self.enable()
        self.track()
        self.task.stopTracking()
        self.assertFalse(self.controller.is_polling())

    def test_enabling_while_tracking_starts_polling(self):
        self.track()
        self.enable()
        self.assertTrue(self.controller.is_polling())

    def test_disabling_stops_polling(self):
        self.enable()
        self.track()
        self.enable(0)
        self.assertFalse(self.controller.is_polling())

    def test_poweroff_stops_polling(self):
        self.enable()
        self.track()
        self.power("powermgt.off")
        self.assertFalse(self.controller.is_polling())

    def test_poweron_restarts_polling(self):
        self.enable()
        self.track()
        self.power("powermgt.off")
        self.power("powermgt.on")
        self.assertTrue(self.controller.is_polling())

    def test_poweron_while_not_tracking_does_not_poll(self):
        self.enable()
        self.power("powermgt.off")
        self.power("powermgt.on")
        self.assertFalse(self.controller.is_polling())

    def test_wake_reports_when_idling_started(self):
        self.enable()
        self.track()
        self.idle_seconds = 120
        self.tick()
        self.assertEqual([True], self.slept)
        self.idle_seconds = 0
        self.tick()
        self.assertAlmostEqual(time.time() - 120, self.woke[0], delta=5)
