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
import wx
from unittest import mock
from taskcoachlib.workarounds import textundo


class TextHistoryTest(test.TestCase):
    def record(self, history, *texts):
        for text in texts:
            history.record(text, len(text))

    def test_typing_on_is_one_step(self):
        history = textundo.TextHistory("", 0)
        self.record(history, "a", "ab", "abc")
        self.assertEqual(("", 0), history.undo("abc", 3))
        self.assertIsNone(history.undo("", 0))

    def test_redo_brings_the_typing_back(self):
        history = textundo.TextHistory("", 0)
        self.record(history, "a", "ab")
        history.undo("ab", 2)
        self.assertEqual(("ab", 2), history.redo("", 0))
        self.assertIsNone(history.redo("ab", 2))

    def test_redo_after_undoing_an_unrecorded_change(self):
        history = textundo.TextHistory("", 0)
        self.record(history, "a")
        history.undo("ab", 2)
        self.assertEqual(("ab", 2), history.redo("", 0))

    def test_typing_after_undo_drops_redo(self):
        history = textundo.TextHistory("", 0)
        self.record(history, "a", "ab")
        history.undo("ab", 2)
        self.record(history, "x")
        self.assertIsNone(history.redo("x", 1))

    def test_backspaces_in_a_row_are_one_step(self):
        history = textundo.TextHistory("abc", 3)
        self.record(history, "ab", "a")
        self.assertEqual(("abc", 3), history.undo("a", 1))

    def test_deletes_in_a_row_are_one_step(self):
        history = textundo.TextHistory("abc", 0)
        history.record("bc", 0)
        history.record("c", 0)
        self.assertEqual(("abc", 0), history.undo("c", 0))

    def test_typing_then_deleting_are_two_steps(self):
        history = textundo.TextHistory("", 0)
        self.record(history, "a", "ab", "a")
        self.assertEqual(("ab", 2), history.undo("a", 1))
        self.assertEqual(("", 0), history.undo("ab", 2))

    def test_typing_elsewhere_starts_a_step(self):
        history = textundo.TextHistory("ac", 1)
        history.record("abc", 2)
        history.record("abcd", 4)
        self.assertEqual(("abc", 2), history.undo("abcd", 4))
        self.assertEqual(("ac", 1), history.undo("abc", 2))

    def test_typing_over_a_selection_is_one_step(self):
        history = textundo.TextHistory("0", 1)
        self.record(history, "4", "45")
        self.assertEqual(("0", 1), history.undo("45", 2))

    def test_a_paste_is_its_own_step(self):
        history = textundo.TextHistory("", 0)
        self.record(history, "a", "a hello")
        self.assertEqual(("a", 1), history.undo("a hello", 7))

    def test_an_unrecorded_change_is_recorded_before_undo(self):
        history = textundo.TextHistory("", 0)
        self.assertEqual(("", 0), history.undo("pasted", 6))

    def test_reset_forgets_the_steps(self):
        history = textundo.TextHistory("", 0)
        self.record(history, "a", "ab")
        history.reset("loaded", 6)
        self.assertIsNone(history.undo("loaded", 6))

    def test_steps_are_capped(self):
        history = textundo.TextHistory("", 0)
        for count in range(1, textundo._MAX_STEPS + 10):
            history.record("x" * count + "!" * (count % 2), 0)
        undone = 0
        text = history.undo("", 0)
        while text is not None:
            undone += 1
            text = history.undo(*text)
        self.assertEqual(textundo._MAX_STEPS, undone)


class TextFieldUndoTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.field = wx.TextCtrl(self.frame)

    def key(self, code, shift=False):
        event = mock.Mock(
            GetEventObject=lambda: self.field,
            CmdDown=lambda: True,
            AltDown=lambda: False,
            ShiftDown=lambda: shift,
            GetKeyCode=lambda: code,
        )
        textundo._on_char_hook(event)
        return event

    def type(self, text):
        # Each key as typing inserts it: at the insertion point, not
        # through SetValue, which counts as the program's
        for character in text:
            self.key(ord(character.upper()))
            self.field.WriteText(character)

    def test_text_fields_get_their_undo_where_the_platform_has_none(self):
        expected = wx.Platform in ("__WXGTK__", "__WXMAC__")
        self.assertEqual(expected, textundo.needs_own_undo(self.field))

    def test_password_and_read_only_fields_are_left_alone(self):
        password = wx.TextCtrl(self.frame, style=wx.TE_PASSWORD)
        read_only = wx.TextCtrl(self.frame, style=wx.TE_READONLY)
        self.assertFalse(textundo.needs_own_undo(password))
        self.assertFalse(textundo.needs_own_undo(read_only))

    def test_ctrl_z_undoes_and_ctrl_y_redoes_the_typing(self):
        if not textundo.needs_own_undo(self.field):
            return
        self.type("ab")
        event = self.key(ord("Z"))
        self.assertEqual("", self.field.GetValue())
        event.Skip.assert_called_with(False)
        self.key(ord("Y"))
        self.assertEqual("ab", self.field.GetValue())
        self.key(ord("Z"))
        self.key(ord("Z"), shift=True)
        self.assertEqual("ab", self.field.GetValue())

    def test_text_the_program_set_is_not_undone(self):
        if not textundo.needs_own_undo(self.field):
            return
        textundo.install(wx.GetApp())
        self.type("ab")
        self.field.SetValue("set by the program")
        self.key(ord("Z"))
        self.assertEqual("set by the program", self.field.GetValue())

    def test_the_edit_menu_undoes_in_the_field(self):
        if not textundo.needs_own_undo(self.field):
            return
        self.type("ab")
        textundo.undo(self.field)
        self.assertEqual("", self.field.GetValue())
        textundo.redo(self.field)
        self.assertEqual("ab", self.field.GetValue())
