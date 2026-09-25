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

import test
from taskcoachlib import config, patterns, persistence
from taskcoachlib.domain import effort, task
from taskcoachlib.gui import idlecontroller


class IdleControllerTest(test.wxTestCase):
    """The idle poll runs only while tracking with the notice on."""

    def setUp(self):
        super().setUp()
        task.Task.settings = self.settings = config.Settings(load=False)
        self.task_file = persistence.TaskFile()
        self.controller = idlecontroller.IdleController(
            self.frame, self.settings, self.task_file.efforts()
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
