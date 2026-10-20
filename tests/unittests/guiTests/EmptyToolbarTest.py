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
from taskcoachlib import persistence
from taskcoachlib.config import settings
from taskcoachlib.domain import task
from taskcoachlib.gui.dialog import editor


class EmptyToolbarTest(test.wxTestCase):
    """A toolbar customized to show nothing: its view still works. The
    effort view made its period choice only along with the visible
    tools, so with none the task editor stopped half built."""

    def setUp(self):
        super().setUp()
        self.task_file = persistence.TaskFile()
        self.task = task.Task("task")
        self.task_file.tasks().append(self.task)

    def tearDown(self):
        self.task_file.close()
        self.task_file.stop()
        super().tearDown()

    def test_task_editor_opens_with_its_views_toolbars_empty(self):
        for view in (
            "effort",
            "category",
            "note",
            "attachment",
            "prerequisite",
        ):
            settings.section(
                "%sviewerintaskeditor" % view
            ).toolbarperspective = ""
        task_editor = editor.TaskEditor(
            self.frame, [self.task], self.task_file.tasks(), self.task_file
        )
        self.assertTrue(task_editor._interior.get_page("effort"))
        task_editor.Close()
        test.settle()
