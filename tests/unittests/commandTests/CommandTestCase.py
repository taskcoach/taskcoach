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
from unittests import asserts
from taskcoachlib import patterns, command, config
from taskcoachlib.domain import task


class CommandTestCase(test.wxTestCase, asserts.CommandAssertsMixin):
    list = []

    def setUp(self):
        super().setUp()
        task.Task.settings = config.Settings(load=False)

    def tearDown(self):
        super().tearDown()
        patterns.CommandHistory().clear()
        command.Clipboard().clear()  # Shared: a cut must not leak

    def undo(self):
        patterns.CommandHistory().undo()

    def redo(self):
        patterns.CommandHistory().redo()

    def cut(self, items=None):
        if items == "all":
            items = list(self.list)
        command.CutCommand(self.list, items or []).do()

    def paste(self):
        command.PasteCommand(self.list).do()
