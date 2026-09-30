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
from taskcoachlib import config, patterns
from taskcoachlib.domain import task


class Rename(patterns.Command):
    """A command changing a stored field: the undo log records it."""

    def __init__(self, item, subject, fail=False):
        super().__init__()
        self.item, self.subject, self.fail = item, subject, fail

    def do_command(self):
        self.item.setSubject(self.subject)
        if self.fail:
            raise RuntimeError("failed")

    def __str__(self):
        return "rename"


class HistoryTest(test.TestCase, asserts.CommandAssertsMixin):
    """One step per user action, from snapshots of the stored data
    (docs/UNDO_REDO.md, Architecture)."""

    def setUp(self):
        super().setUp()
        task.Task.settings = config.Settings(load=False)
        self.commands = patterns.CommandHistory()
        self.item = task.Task(subject="Before")
        self.command = Rename(self.item, "After")

    def tearDown(self):
        self.commands.clear()
        super().tearDown()

    def testSingleton(self):
        another = patterns.CommandHistory()
        self.assertTrue(self.commands is another)

    def testClear(self):
        self.command.do()
        self.commands.clear()
        self.assertHistoryAndFuture([], [])

    def testDo(self):
        self.command.do()
        self.assertHistoryAndFuture([self.command], [])
        self.assertEqual("After", self.item.subject())

    def testUndo(self):
        self.command.do()
        self.commands.undo()
        self.assertHistoryAndFuture([], [self.command])
        self.assertEqual("Before", self.item.subject())

    def testRedo(self):
        self.command.do()
        self.commands.undo()
        self.commands.redo()
        self.assertHistoryAndFuture([self.command], [])
        self.assertEqual("After", self.item.subject())

    def test_undo_puts_back_the_modification_date(self):
        date_before = self.item.modificationDateTime()
        self.command.do()
        date_after = self.item.modificationDateTime()
        self.commands.undo()
        self.assertEqual(date_before, self.item.modificationDateTime())
        self.commands.redo()
        self.assertEqual(date_after, self.item.modificationDateTime())

    def testUndoStr_EmptyHistory(self):
        self.assertEqual("Undo", self.commands.undostr())

    def testUndoStr(self):
        self.command.do()
        self.assertEqual("Undo %s" % self.command, self.commands.undostr())

    def testRedoStr_EmptyFuture(self):
        self.assertEqual("Redo", self.commands.redostr())

    def testRedoStr(self):
        self.command.do()
        self.commands.undo()
        self.assertEqual("Redo %s" % self.command, self.commands.redostr())

    def testHasHistory(self):
        self.assertFalse(self.commands.hasHistory())
        self.command.do()
        self.assertTrue(self.commands.hasHistory())
        self.commands.undo()
        self.assertFalse(self.commands.hasHistory())

    def testHasFuture(self):
        self.command.do()
        self.assertFalse(self.commands.hasFuture())
        self.commands.undo()
        self.assertTrue(self.commands.hasFuture())
        self.commands.redo()
        self.assertFalse(self.commands.hasFuture())

    def test_an_action_is_one_step_whatever_its_commands(self):
        with self.commands.action("edit"):
            Rename(self.item, "One").do()
            Rename(self.item, "Two").do()
        self.assertEqual(
            ["edit"], [str(s) for s in self.commands.getHistory()]
        )
        self.commands.undo()
        self.assertEqual("Before", self.item.subject())

    def test_a_failed_action_is_rolled_back(self):
        with self.assertRaises(RuntimeError):
            Rename(self.item, "After", fail=True).do()
        self.assertEqual("Before", self.item.subject())
        self.assertFalse(self.commands.hasHistory())

    def test_an_action_changing_nothing_is_no_step(self):
        Rename(self.item, "Before").do()
        self.assertFalse(self.commands.hasHistory())

    def test_a_new_action_clears_the_steps_to_redo(self):
        self.command.do()
        self.commands.undo()
        Rename(self.item, "Other").do()
        self.assertFalse(self.commands.hasFuture())

    def test_nothing_is_done_while_a_step_is_put_back(self):
        self.command.do()
        # As a view reacting to the undo would
        patterns.Publisher().registerObserver(
            self.on_subject, eventType=self.item.subjectChangedEventType()
        )
        self.commands.undo()
        self.assertEqual("Before", self.item.subject())
        self.assertTrue(self.commands.hasFuture())

    def on_subject(self, event):
        Rename(self.item, "Reaction").do()
