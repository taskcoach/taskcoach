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

import test
from taskcoachlib.notify import notifier_universal


class NotificationCenterTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(
            setattr, notifier_universal.NotificationCenter, "_instance", None
        )
        self.center = notifier_universal.NotificationCenter()

    def test_ticks_only_while_there_are_frames(self):
        self.assertIsNone(self.center._ticks)
        self.center.notify("Title", "Message", timeout=1)
        self.assertTrue(self.center._ticks.pending)
        self.center._on_tick()  # Closes it
        self.assertFalse(self.center._ticks.pending)
