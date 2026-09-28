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

from taskcoachlib import patterns, command
from taskcoachlib.domain import task
from .CommandTestCase import CommandTestCase


class DeleteCommandTest(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.item = task.Task()
        self.items = patterns.List([self.item])

    def deleteItem(self, items=None):
        delete = command.DeleteCommand(self.items, items or [])
        delete.do()

    def testDeleteItem_WithoutSelection(self):
        self.deleteItem()
        self.assertDoUndoRedo(
            lambda: self.assertEqual([self.item], self.items)
        )

    def testDeleteItem_WithSelection(self):
        self.deleteItem([self.item])
        self.assertDoUndoRedo(
            lambda: self.assertEqual([], self.items),
            lambda: self.assertEqual([self.item], self.items),
        )

    def testItemsAreNotNew(self):
        self.assertFalse(command.DeleteCommand(self.items, []).items_are_new())


class EditSubjectTestCase(CommandTestCase):
    ItemClass = task.Task
    ContainerClass = task.TaskList

    def setUp(self):
        super().setUp()
        self.item1 = self.ItemClass(subject="item1")
        self.item2 = self.ItemClass(subject="item2")
        self.container = self.ContainerClass([self.item1, self.item2])

    def editSubject(self, newSubject, *items):
        editSubjectCommand = command.EditSubjectCommand(
            self.container, items, newValue=newSubject
        )
        editSubjectCommand.do()

    def testEditSubject(self):
        self.editSubject("new", self.item1)
        self.assertDoUndoRedo(
            lambda: self.assertEqual("new", self.item1.subject()),
            lambda: self.assertEqual("item1", self.item1.subject()),
        )

    def testEditMultipleSubjects(self):
        self.editSubject("new", self.item1, self.item2)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                "newnew", self.item1.subject() + self.item2.subject()
            ),
            lambda: self.assertEqual(
                "item1item2", self.item1.subject() + self.item2.subject()
            ),
        )

    def testItemsAreNotNew(self):
        self.assertFalse(
            command.EditSubjectCommand(
                self.container, [], newValue="New subject"
            ).items_are_new()
        )

    def testModificationDateTime(self):
        original = self.item1.modificationDateTime()
        self.editSubject("new", self.item1)
        changed = self.item1.modificationDateTime()
        self.assertTrue(original < changed)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                changed, self.item1.modificationDateTime()
            ),
            lambda: self.assertEqual(
                original, self.item1.modificationDateTime()
            ),
        )


class EditDescriptionTestCase(CommandTestCase):
    ItemClass = task.Task
    ContainerClass = task.TaskList

    def setUp(self):
        super().setUp()
        self.item1 = self.ItemClass(description="item1")
        self.item2 = self.ItemClass(description="item2")
        self.container = self.ContainerClass([self.item1, self.item2])

    def edit_description(self, new_description, *items):
        edit_subject = command.EditDescriptionCommand(
            self.container, items, newValue=new_description
        )
        edit_subject.do()

    def testEditSubject(self):
        self.edit_description("new", self.item1)
        self.assertDoUndoRedo(
            lambda: self.assertEqual("new", self.item1.description()),
            lambda: self.assertEqual("item1", self.item1.description()),
        )

    def testEditMultipleDescriptions(self):
        self.edit_description("new", self.item1, self.item2)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                "newnew", self.item1.description() + self.item2.description()
            ),
            lambda: self.assertEqual(
                "item1item2",
                self.item1.description() + self.item2.description(),
            ),
        )

    def testItemsAreNotNew(self):
        self.assertFalse(
            command.EditDescriptionCommand(
                self.container, [], newValue="New description"
            ).items_are_new()
        )

    def testModificationDateTime(self):
        original = self.item1.modificationDateTime()
        self.edit_description("new", self.item1)
        changed = self.item1.modificationDateTime()
        self.assertTrue(original < changed)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                changed, self.item1.modificationDateTime()
            ),
            lambda: self.assertEqual(
                original, self.item1.modificationDateTime()
            ),
        )
