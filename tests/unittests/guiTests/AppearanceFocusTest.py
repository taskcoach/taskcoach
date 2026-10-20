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

import wx

import test
from taskcoachlib import gui, persistence
from taskcoachlib.domain import task


class AppearanceReadOnlyFocusTest(test.wxTestCase):
    """The read-only appearance displays never keep the focus.

    On the Appearance page of a task editor, the Derived and
    Effective displays take no tab focus, and focus reaching
    one by any other path moves on to an editable control
    instead of resting on, or cycling between, the displays
    (issue #487).
    """

    def setUp(self):
        super().setUp()
        self.taskFile = persistence.TaskFile()
        self.taskList = self.taskFile.tasks()
        self.task = task.Task(subject="focus")
        self.taskList.append(self.task)
        self.editor = gui.dialog.editor.TaskEditor(
            self.frame, [self.task], self.taskList, self.taskFile
        )
        self.appearance = self.editor._interior.get_page("appearance")
        interior = self.editor._interior
        index = next(
            i
            for i in range(interior.GetPageCount())
            if interior.GetPage(i) is self.appearance
        )
        self.editor.Show()
        interior.SetSelection(index)
        wx.YieldIfNeeded()

    def tearDown(self):
        wx.YieldIfNeeded()
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def __display_composites(self):
        """The read-only displays: colour pickers, font pickers,
        and icon panels with their static children."""
        appearance = self.appearance
        composites = []
        for picker in (
            appearance._derived_fg_picker,
            appearance._derived_bg_picker,
            appearance._effective_fg_picker,
            appearance._effective_bg_picker,
        ):
            composites.append((picker, [picker.GetPickerCtrl()]))
        for picker in (
            appearance._derived_font_picker,
            appearance._effective_font_picker,
        ):
            composites.append((picker, []))
        for panel in (
            appearance._derived_icon_panel,
            appearance._effective_icon_panel,
        ):
            composites.append((panel, list(panel.GetChildren())))
        return composites

    def __settle_focus(self, window, read_only_ids):
        """Focus a window, then let the deferred focus rejection
        run its course: each read-only display hands the focus to
        the next window until an editable one keeps it."""
        window.SetFocus()
        for _ in range(10):
            wx.YieldIfNeeded()
            if id(wx.Window.FindFocus()) not in read_only_ids:
                break
        return wx.Window.FindFocus()

    def test_read_only_composites_take_no_tab_focus(self):
        for composite, _children in self.__display_composites():
            self.assertFalse(
                composite.AcceptsFocusFromKeyboard(),
                "Read-only display %r takes tab focus" % (composite,),
            )

    def test_focus_reaching_a_display_moves_on(self):
        read_only_ids = set(
            id(window)
            for composite, children in self.__display_composites()
            for window in [composite] + children
        )
        focusables = [
            window
            for composite, children in self.__display_composites()
            for window in [composite] + children
            if window.AcceptsFocus()
        ]
        self.assertTrue(
            focusables, "No focusable display to hand focus on from"
        )
        for window in focusables:
            for _ in range(2):
                focused = self.__settle_focus(window, read_only_ids)
                self.assertNotIn(
                    id(focused),
                    read_only_ids,
                    "Focus rested on %r after focusing %r" % (focused, window),
                )
