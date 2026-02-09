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

import ast
import test
from taskcoachlib import gui, config, persistence


class PreferencesTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)
        self.preferences = gui.Preferences(
            parent=self.frame, title="Test", settings=self.settings
        )
        self.originalColor = self.settings.get("fgcolor", "activetasks")
        self.newColor = (1, 2, 29)

    # pylint: disable=W0212

    def testCancel(self):
        # Page 7 = Statuses tab; color index 8 = active tasks light fg
        self.preferences[7]._colorSettings[8][2].SetColour(self.newColor)
        self.preferences.cancel()
        self.assertEqual(
            self.originalColor, self.settings.get("fgcolor", "activetasks")
        )

    def testOk(self):
        # Page 7 = Statuses tab; color index 8 = active tasks light fg
        self.preferences[7]._colorSettings[8][2].SetColour(self.newColor)
        self.preferences.ok()
        self.assertEqual(
            self.newColor,
            ast.literal_eval(self.settings.get("fgcolor", "activetasks"))[:3],
        )
