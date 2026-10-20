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

import contextlib
import io
import os
from unittest import mock

import test
from taskcoachlib.gui.dialog import editor
from tools import check_editors


class EditorCheckTest(test.wxTestCase):
    """Every kind of editor opens on a display, and tabbing through
    each of its pages keeps the focus inside it, settled, with no
    error (issue #487). The builds run the same checks on their own
    platforms (tools/check_editors.py)."""

    def setUp(self):
        super().setUp()
        self.main = check_editors.MainFrame()
        self.task_file = check_editors.sample_task_file()

    def tearDown(self):
        self.task_file.close()
        self.task_file.stop()
        self.main.Destroy()
        test.settle()
        super().tearDown()

    def problems(self, name):
        for kind, open_editor, own_steps in check_editors.editors(
            self.main, self.task_file
        ):
            if kind == name:
                return check_editors.check_editor(name, open_editor, own_steps)
        self.fail("No %s editor" % name)

    def check(self, name):
        self.assertEqual([], self.problems(name), name)

    def test_an_editor_that_cannot_open_is_reported(self):
        """With its error, and its error box not shown: no one clicks
        it on a build machine."""
        with mock.patch.object(
            editor.EditBook, "add_pages", side_effect=RuntimeError("Broken")
        ):
            problems = self.problems("task")
        self.assertTrue(
            any("message box" in problem for problem in problems), problems
        )
        self.assertTrue(
            any("RuntimeError: Broken" in problem for problem in problems),
            problems,
        )

    def test_problems_show_on_a_github_run_page(self):
        output = io.StringIO()
        with mock.patch.dict(os.environ, GITHUB_ACTIONS="true"):
            with contextlib.redirect_stdout(output):
                check_editors.annotate("task editor, open: 100%\nfailed")
        self.assertEqual(
            "::error title=Editor check::task editor, open: 100%25%0Afailed\n",
            output.getvalue(),
        )

    def test_problems_show_only_in_the_log_elsewhere(self):
        output = io.StringIO()
        with mock.patch.dict(os.environ, GITHUB_ACTIONS=""):
            with contextlib.redirect_stdout(output):
                check_editors.annotate("task editor, open: failed")
        self.assertEqual("", output.getvalue())

    def test_task_editor(self):
        self.check("task")

    def test_new_task_editor(self):
        self.check("new task")

    def test_editor_of_two_tasks(self):
        self.check("two tasks")

    def test_category_editor(self):
        self.check("category")

    def test_note_editor(self):
        self.check("note")

    def test_attachment_editor(self):
        self.check("attachment")

    def test_effort_editor(self):
        self.check("effort")

    def test_task_editor_with_unreadable_saved_tabs(self):
        self.check("task, unreadable saved tabs")

    def test_task_editor_with_empty_toolbars(self):
        self.check("task, empty toolbars")
