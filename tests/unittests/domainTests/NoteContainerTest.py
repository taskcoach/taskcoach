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
from taskcoachlib.domain import note, category


class NoteContainerTest(test.TestCase):
    def setUp(self):
        self.container = note.NoteContainer()
        self.note = note.Note()

    def testAddNote(self):
        self.container.append(self.note)
        self.assertEqual([self.note], self.container)

    def testAddNoteWithCategory(self):
        cat = category.Category(subject="Cat")
        self.note.addCategory(cat)
        self.container.append(self.note)
        self.assertTrue(self.note in cat.members())

    def test_removed_note_keeps_its_category(self):
        # To come back with it on undo; the file's members drop it
        cat = category.Category(subject="Cat")
        self.note.addCategory(cat)
        self.container.append(self.note)
        self.container.remove(self.note)
        self.assertEqual(
            ({cat}, {self.note}),
            (self.note.categories(), cat.members()),
        )
