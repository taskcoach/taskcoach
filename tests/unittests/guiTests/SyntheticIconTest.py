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

from unittest import mock

import test
import wx
from taskcoachlib.gui.icons import icon_library
from taskcoachlib.gui.icons.synthetic_icon_generator import (
    SyntheticIconGenerator,
)

SIZE = 16


def image(colour, alpha):
    picture = wx.Image(SIZE, SIZE)
    picture.SetData(bytes(colour) * SIZE * SIZE)
    picture.InitAlpha()
    picture.SetAlpha(bytes([alpha]) * SIZE * SIZE)
    return picture.ConvertToBitmap()


class StatusFilterIconTest(test.wxTestCase):
    """A status filter button's icon: its status icon with an error
    badge over the bottom right quarter."""

    def setUp(self):
        super().setUp()
        base, badge = image((255, 0, 0), 100), image((0, 0, 255), 200)
        icons = {"nuvola_status_dialog-error": badge}
        with mock.patch.object(
            icon_library.icon_catalog,
            "get_bitmap",
            lambda icon_id, size: icons.get(icon_id, base),
        ):
            bitmap = SyntheticIconGenerator("synthetic_hide_late")
            self.icon = bitmap.render_bitmap(SIZE).ConvertToImage()

    def alpha(self, x, y):
        return self.icon.GetAlpha(x, y)

    def test_outside_the_badge_the_status_icons_transparency(self):
        for x, y in ((0, 0), (15, 0), (0, 15), (7, 7), (7, 8), (8, 7)):
            self.assertEqual(100, self.alpha(x, y))

    def test_under_the_badge_opaque_where_either_is(self):
        for x, y in ((8, 8), (15, 15), (8, 15), (15, 8)):
            self.assertGreaterEqual(self.alpha(x, y), 200)

    def test_the_badge_drawn_over_its_corner(self):
        red, green, blue = self.colour(12, 12)
        self.assertGreater(blue, red)  # Over the status icon, blended
        self.assertEqual((255, 0, 0), self.colour(3, 3))

    def colour(self, x, y):
        return (
            self.icon.GetRed(x, y),
            self.icon.GetGreen(x, y),
            self.icon.GetBlue(x, y),
        )
