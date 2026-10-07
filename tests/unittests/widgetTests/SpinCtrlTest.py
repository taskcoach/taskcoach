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
from taskcoachlib import widgets


class SpinCtrlTest(test.wxTestCase):
    def test_positive_value(self):
        spin_ctrl = widgets.SpinCtrl(self.frame, value=5)
        self.assertEqual(5, spin_ctrl.GetValue())

    def test_negative_value(self):
        spin_ctrl = widgets.SpinCtrl(self.frame, value=-5)
        self.assertEqual(-5, spin_ctrl.GetValue())

    def test_min_range(self):
        spin_ctrl = widgets.SpinCtrl(self.frame, min=1)
        self.assertEqual(1, spin_ctrl.GetMin())

    def test_default_value_is_at_least_min_range(self):
        spin_ctrl = widgets.SpinCtrl(self.frame, min=1)
        self.assertEqual(1, spin_ctrl.GetValue())

    def test_max_range(self):
        spin_ctrl = widgets.SpinCtrl(self.frame, max=100)
        self.assertEqual(100, spin_ctrl.GetMax())

    def test_default_value_is_at_most_max_range(self):
        spin_ctrl = widgets.SpinCtrl(self.frame, max=-1)
        self.assertEqual(-1, spin_ctrl.GetValue())
