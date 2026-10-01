# -*- coding: utf-8 -*-

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
from taskcoachlib.gui import newid


class IdProviderTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.provider = type(newid.IdProvider)()

    def test_an_id_given_back_is_reused(self):
        first = self.provider.get()
        self.provider.put(first)
        self.assertEqual(first, self.provider.get())

    def test_ids_in_use_are_distinct(self):
        self.assertEqual(50, len({self.provider.get() for _ in range(50)}))

    def test_an_id_it_did_not_hand_out_is_not_taken(self):
        self.provider.put(12345)
        self.assertNotEqual(12345, self.provider.get())
