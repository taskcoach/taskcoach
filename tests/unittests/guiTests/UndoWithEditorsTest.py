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
from taskcoachlib import config
from taskcoachlib.domain import attachment
from taskcoachlib.gui.dialog import editor
from taskcoachlib.patterns.snapshot import Snapshot
from unittests.domainTests import UndoTest


class UndoWithEditorsTest(UndoTest.UndoTest, test.wxTestCase):
    """Every undo case again with an editor open on each item: what an
    editor shows of a change, its undo or its redo, it writes nothing
    back (docs/UNDO_REDO.md, Actions)."""

    def setUp(self):
        super().setUp()
        settings = config.settings.current()
        task_file = self.task_file
        self.editors = [
            editor.TaskEditor(
                self.frame, [each], settings, self.tasks, task_file
            )
            for each in (self.parent, self.child, self.other)
        ] + [
            editor.EffortEditor(
                self.frame,
                [self.effort],
                settings,
                task_file.efforts(),
                task_file,
            ),
            editor.CategoryEditor(
                self.frame,
                [self.category],
                settings,
                self.categories,
                task_file,
            ),
            editor.NoteEditor(
                self.frame, [self.note], settings, self.notes, task_file
            ),
            editor.AttachmentEditor(
                self.frame,
                [self.mail],
                settings,
                attachment.AttachmentList([self.mail]),
                task_file,
            ),
        ]
        self.settle()
        # What opening them did is not the case's
        self.history.clear()
        for item, _fields in Snapshot().items.values():
            item.set_modification_datetime(UndoTest.OLD)

    def tearDown(self):
        for each in self.editors:
            if each:  # Not closed by itself (docs/UNDO_REDO.md, Windows)
                # As the user closes it: its subscriptions end first
                each.Close()
        test.settle()
        super().tearDown()

    def settle(self):
        wx.Yield()
