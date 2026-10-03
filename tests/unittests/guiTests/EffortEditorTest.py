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
from taskcoachlib import command, config, gui, patterns, persistence
from taskcoachlib.domain import task, effort, date
from unittests import dummy


class EditorUnderTest(gui.dialog.editor.EffortEditor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.editorClosed = False

    def onClose(self, event):  # pragma: no cover
        self.editorClosed = True
        super().onClose(event)


class EffortEditorTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.settings = config.settings.current()
        self.taskFile = persistence.TaskFile()
        self.taskList = self.taskFile.tasks()
        self.effortList = self.taskFile.efforts()
        self.task = task.Task("task")
        self.effort = effort.Effort(self.task)
        self.task.addEffort(self.effort)
        self.task2 = task.Task("task2")
        self.taskFile.tasks().extend([self.task, self.task2])
        self.editor = EditorUnderTest(
            self.frame,
            list(self.effortList),
            self.settings,
            self.taskFile.efforts(),
            self.taskFile,
            raiseDialog=False,
        )

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def createEditor(self):
        return EditorUnderTest(
            self.frame,
            list(self.taskFile.efforts()),
            self.settings,
            self.taskFile.efforts(),
            self.taskFile,
        )

    # pylint: disable=W0201,W0212

    def testCreate(self):
        self.assertEqual(
            self.task, self.editor._interior._task_entry.GetValue()
        )
        self.assertEqual(
            self.effort.getStart().date(),
            self.editor._interior._start_date_time_combo.GetValue().date(),
        )
        self.assertEqual(
            self.effort.task(), self.editor._interior._task_entry.GetValue()
        )

    def testInvalidEffort(self):
        self.editor._interior._stop_date_time_combo.SetValue(
            date.DateTime(1900, 1, 1)
        )
        self.editor._interior._stop_date_time_sync.onAttributeEdited(
            dummy.Event()
        )
        self.assertTrue(
            self.editor._interior._invalid_period_message.GetLabel()
        )

    def testChangeTask(self):
        self.editor._interior._task_entry.SetValue(self.task2)
        self.editor._interior._task_sync.onAttributeEdited(dummy.Event())
        self.assertEqual(self.task2, self.effort.task())
        self.assertFalse(self.effort in self.task.efforts())

    def testChangeTaskDoesNotCloseEditor(self):
        self.editor._interior._task_entry.SetValue(self.task2)
        self.editor._interior._task_sync.onAttributeEdited(dummy.Event())
        self.assertFalse(self.editor.editorClosed)

    def test_undo_writes_nothing_back(self):
        # A change from elsewhere is shown, not edited
        # (docs/DURATION_CALCULATIONS.md, 0.5)
        history = patterns.CommandHistory()
        start = date.DateTime(2026, 9, 30, 11, 3, 52)
        self.effort.setStart(start)
        self.effort.setStop(start + date.ONE_HOUR)
        wx.Yield()
        history.clear()
        self.addCleanup(history.clear)
        command.EditEffortStartDateTimeCommand(
            items=[self.effort], newValue=start - date.ONE_HOUR
        ).do()
        wx.Yield()
        history.undo()
        wx.Yield()
        self.assertEqual(
            (start, start + date.ONE_HOUR),
            (self.effort.getStart(), self.effort.getStop()),
        )
        self.assertTrue(history.has_future())
