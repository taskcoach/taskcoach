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

import runpy
from unittest import mock

import wx

import test
from taskcoachlib import widgets
from taskcoachlib.widgets import colourpicker


class ColourPickerReadOnlyTest(test.wxTestCase):
    """A read-only picker is no tab stop; how the focus passes it by
    is tested in SkipFocusTest (issue #487)."""

    def setUp(self):
        super().setUp()
        self.picker = widgets.ColourPickerCtrl(
            self.frame, colour=wx.BLACK, read_only=True
        )

    def test_read_only_picker_is_no_tab_stop(self):
        self.assertFalse(self.picker.AcceptsFocusFromKeyboard())

    def test_editable_picker_keeps_tab_stop(self):
        picker = widgets.ColourPickerCtrl(self.frame, colour=wx.BLACK)
        self.assertTrue(picker.AcceptsFocusFromKeyboard())


class ColourPickerInvalidColourTest(test.wxTestCase):
    """An invalid colour never reaches the picker: macOS asserts
    drawing one (src/osx/core/colour.cpp, GetCGColor), which stopped
    the editor holding the picker from opening."""

    def test_an_invalid_colour_keeps_the_colour_shown(self):
        picker = widgets.ColourPickerCtrl(self.frame, colour=wx.BLACK)
        picker.SetColour(wx.NullColour)
        self.assertEqual(wx.BLACK, picker.GetColour())


class _MacPicker(wx.PickerBase):
    """wxPython 4.3.0's and 4.3.1's wx.ColourPickerCtrl on macOS, as
    far as it gets: it calls PickerBase.SetPickerCtrl(), which
    wxWidgets 3.3 dropped (wxPython #2937)."""

    def __init__(self, *args, **kwargs):
        raise AttributeError(
            "'ColourPickerCtrl' object has no attribute 'SetPickerCtrl'"
        )


class ColourPickerMacWxPythonTest(test.wxTestCase):
    """No editor with an Appearance tab opened on macOS: none of its
    pickers could be made with wxPython 4.3.1 (#487)."""

    def test_a_picker_is_made_with_wxpython_4_3_1_on_macos(self):
        with mock.patch.object(wx, "ColourPickerCtrl", _MacPicker):
            module = runpy.run_path(colourpicker.__file__)
        picker = module["ColourPickerCtrl"](self.frame, colour=wx.RED)
        self.assertEqual(wx.RED, picker.GetColour())
