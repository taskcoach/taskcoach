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

import re

_START_TAG = re.compile(r'<([\w:]+)((?:\s+[\w:]+="[^"]*")+)(\s*/?)>')


def sorted_attributes(xml):
    """Sort each start tag's attributes: the expected fragments were
    written for Python 2, whose ElementTree sorted them."""

    def sort(match):
        attributes = re.findall(r'\s+[\w:]+="[^"]*"', match.group(2))
        return "<%s%s%s>" % (
            match.group(1),
            "".join(sorted(attributes)),
            match.group(3),
        )

    return _START_TAG.sub(sort, xml)


class TaskListAssertsMixin(object):
    def assertTaskList(self, expected):
        self.assertEqualLists(expected, self.taskList)
        self.assertAllChildrenInTaskList()

    def assertAllChildrenInTaskList(self):
        for task in self.taskList:
            for child in task.children():
                self.assertTrue(child in self.taskList)

    def assertEmptyTaskList(self):
        self.assertFalse(self.taskList)


class EffortListAssertsMixin(object):
    def assertEffortList(self, expected):
        self.assertEqualLists(expected, self.effortList)


class NoteContainerAssertsMixin(object):
    def assertNoteContainer(self, expected):
        for note in expected:
            self.assertTrue(note in self.noteContainer)
        for note in self.noteContainer:
            self.assertTrue(note in expected)


class EffortAssertsMixin(object):
    def assertEqualEfforts(self, effort1, effort2):
        self.assertEqual(effort1.task(), effort2.task())
        self.assertEqual(effort1.getStart(), effort2.getStart())
        self.assertEqual(effort1.getStop(), effort2.getStop())
        self.assertEqual(effort1.description(), effort2.description())


class TaskAssertsMixin(object):
    def failUnlessParentAndChild(self, parent, child):
        self.assertTrue(child in parent.children())
        self.assertTrue(child.parent() == parent)

    def assertTaskCopy(self, orig, copy):
        self.assertFalse(orig == copy)
        self.assertEqual(orig.subject(), copy.subject())
        self.assertEqual(orig.description(), copy.description())
        self.assertEqual(
            orig.plannedStartDateTime(), copy.plannedStartDateTime()
        )
        self.assertEqual(orig.dueDateTime(), copy.dueDateTime())
        self.assertEqual(
            orig.actualStartDateTime(), copy.actualStartDateTime()
        )
        self.assertEqual(orig.completionDateTime(), copy.completionDateTime())
        self.assertEqual(orig.recurrence(), copy.recurrence())
        self.assertEqual(orig.budget(), copy.budget())
        if orig.parent():
            self.assertFalse(copy in orig.parent().children())
        self.assertFalse(orig.id() == copy.id())
        self.assertEqual(orig.categories(), copy.categories())
        self.assertEqual(orig.priority(), copy.priority())
        self.assertEqual(orig.fixedFee(), copy.fixedFee())
        self.assertEqual(orig.hourlyFee(), copy.hourlyFee())
        # Copies are new attachments (equality is by id): compare
        # locations
        self.assertEqual(
            [each.location() for each in orig.attachments()],
            [each.location() for each in copy.attachments()],
        )
        self.assertEqual(orig.reminder(), copy.reminder())
        self.assertEqual(
            orig.shouldMarkCompletedWhenAllChildrenCompleted(),
            copy.shouldMarkCompletedWhenAllChildrenCompleted(),
        )
        self.assertEqual(len(orig.children()), len(copy.children()))
        for origChild, copyChild in zip(orig.children(), copy.children()):
            self.assertTaskCopy(origChild, copyChild)
        for origEffort, copyEffort in zip(orig.efforts(), copy.efforts()):
            self.assertEffortCopy(origEffort, copyEffort)

    def assertEffortCopy(self, orig, copy):
        self.assertFalse(orig.id() == copy.id())
        self.assertFalse(orig.task() == copy.task())
        self.assertEqual(orig.getStart(), copy.getStart())
        self.assertEqual(orig.getStop(), copy.getStop())
        self.assertEqual(orig.description(), copy.description())


class CommandAssertsMixin(object):
    def assertHistoryAndFuture(self, expectedHistory, expectedFuture):
        from taskcoachlib import patterns

        commands = patterns.CommandHistory()
        self.assertEqual(expectedHistory, commands.getHistory())
        self.assertEqual(expectedFuture, commands.getFuture())

    def assertDoUndoRedo(self, assertDone, assertUndone=None):
        if not assertUndone:
            assertUndone = assertDone
        assertDone()
        self.undo()
        assertUndone()
        self.redo()
        assertDone()


class Mixin(
    CommandAssertsMixin,
    TaskAssertsMixin,
    EffortAssertsMixin,
    TaskListAssertsMixin,
    EffortListAssertsMixin,
    NoteContainerAssertsMixin,
):
    pass
