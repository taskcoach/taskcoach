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
import os

import test
from taskcoachlib.config import settings
from taskcoachlib.widgets import currencyctrl, maskedtimectrl, numericctrl


class ControlsReadTheApplicationSettingsTest(test.wxTestCase):
    """The date, time and amount controls read the one Settings object
    of the application (P152)."""

    @staticmethod
    def set(option, value):
        # The harness puts the settings back after each test
        setattr(settings.view, option, value)

    def test_minute_choices(self):
        self.set("effortminuteinterval", 20)
        self.assertEqual([0, 20, 40], maskedtimectrl.getDefaultMinuteChoices())

    def test_second_choices(self):
        self.set("effortsecondinterval", 30)
        self.assertEqual([0, 30], maskedtimectrl.getDefaultSecondChoices())

    def test_hour_choices(self):
        self.set("efforthourstart", 9)
        self.set("efforthourend", 11)
        self.assertEqual(
            [9, 10, 11], maskedtimectrl.get_default_hour_choices("24")
        )

    def test_decimal_separator(self):
        self.set("decimal_separator", ",")
        self.assertEqual(",", numericctrl._get_configured_decimal_char())

    def test_currency_decimal_places(self):
        self.set("currency_decimal_places", "3")
        self.assertEqual(
            3, currencyctrl._get_configured_currency_decimal_places()
        )

    def test_date_format_as_at_start(self):
        # As the lists show dates: a change applies after a restart
        at_start = maskedtimectrl.getDateFormatFromSettings()
        self.set("dateformat", "DMY/" if at_start != "DMY/" else "YMD-")
        self.assertEqual(at_start, maskedtimectrl.getDateFormatFromSettings())


class OneSettingsObjectTest(test.TestCase):
    """Only the application makes a Settings object; the rest read it
    through settings2 (docs/SETTINGS.md)."""

    def test_no_other_settings_object(self):
        root = os.path.join(
            os.path.dirname(test.__file__), "..", "taskcoachlib"
        )
        found = []
        for folder, _, files in os.walk(root):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(folder, name)
                relative = os.path.relpath(path, root)
                if relative == os.path.join("application", "application.py"):
                    continue
                with open(path, encoding="utf-8") as source:
                    tree = ast.parse(source.read(), path)
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "Settings"
                    ):
                        found.append("%s:%d" % (relative, node.lineno))
        self.assertEqual([], found)
