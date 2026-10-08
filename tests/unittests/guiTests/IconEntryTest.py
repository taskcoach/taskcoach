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
from taskcoachlib.domain.base import NO_ICON
from taskcoachlib.gui.dialog import entry


class IconEntryTest(test.wxTestCase):
    """The Appearance tab's icon override: unticked none, ticked the
    icon picked, "No icon" too (docs/APPEARANCE_STYLES.md, No Icon)."""

    def icon_entry(self, icon_id=""):
        return entry.IconEntry(self.frame, icon_id)

    def shown(self, icon_entry):
        return (
            icon_entry._icon_check_box.IsChecked(),
            icon_entry._icon_picker.GetValue(),
        )

    def test_unticked_is_no_override(self):
        self.assertEqual("", self.icon_entry().GetValue())

    def test_ticked_on_no_icon_is_the_no_icon_override(self):
        icon_entry = self.icon_entry()
        icon_entry._icon_check_box.SetValue(True)
        self.assertEqual(NO_ICON, icon_entry.GetValue())

    def test_picking_no_icon_keeps_the_tick(self):
        icon_entry = self.icon_entry("nuvola_apps_kpackage")
        icon_entry._icon_picker.SetValue("")
        icon_entry.on_icon_picked(mock.Mock())
        self.assertEqual(NO_ICON, icon_entry.GetValue())

    def test_the_no_icon_override_shows_ticked_on_no_icon(self):
        self.assertEqual((True, ""), self.shown(self.icon_entry(NO_ICON)))

    def test_set_value_shows_the_no_icon_override(self):
        icon_entry = self.icon_entry("nuvola_apps_kpackage")
        icon_entry.SetValue(NO_ICON)
        self.assertEqual((True, ""), self.shown(icon_entry))

    def test_a_picked_icon(self):
        self.assertEqual(
            "nuvola_apps_kpackage",
            self.icon_entry("nuvola_apps_kpackage").GetValue(),
        )
