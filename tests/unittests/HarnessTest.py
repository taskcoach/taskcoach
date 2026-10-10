"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2026 Task Coach developers

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

import test
import wx


class SwallowedErrorTest(test.wxTestCase):
    """An error inside an event handler fails the test it happens in
    (docs/TESTING.md): wx prints it and goes on, so nothing else
    would."""

    def result_of(self, body):
        class Inner(test.TestCase):
            def test_body(self):
                body()

        result = unittest.TestResult()
        Inner("test_body").run(result)
        return result

    def send_menu_event(self, handler):
        self.frame.Bind(wx.EVT_MENU, handler)
        self.addCleanup(self.frame.Unbind, wx.EVT_MENU, handler=handler)
        self.frame.GetEventHandler().ProcessEvent(
            wx.CommandEvent(wx.wxEVT_MENU)
        )

    def test_an_error_in_an_event_handler_fails_the_test(self):
        def handler(_event):
            raise ValueError("in a handler")

        result = self.result_of(lambda: self.send_menu_event(handler))
        self.assertEqual(1, len(result.errors))
        self.assertIn("ValueError: in a handler", result.errors[0][1])

    def test_a_handler_without_error_passes(self):
        result = self.result_of(lambda: self.send_menu_event(lambda event: 0))
        self.assertTrue(result.wasSuccessful())
