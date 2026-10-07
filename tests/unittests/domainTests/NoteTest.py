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

import test, wx
from taskcoachlib import patterns
from taskcoachlib.domain import note, date, base


class NoteTest(test.TestCase):
    def setUp(self):
        self.note = note.Note()
        self.child = note.Note()
        self.events = []

    def onEvent(self, event):
        self.events.append(event)

    def test_default_subject(self):
        self.assertEqual("", self.note.subject())

    def test_given_subject(self):
        a_note = note.Note(subject="Note")
        self.assertEqual("Note", a_note.subject())

    def test_set_subject(self):
        self.note.setSubject("Note")
        self.assertEqual("Note", self.note.subject())

    def test_subject_change_notification(self):
        patterns.Publisher().registerObserver(
            self.onEvent, self.note.subjectChangedEventType()
        )
        self.note.setSubject("Note")
        self.assertEqual(
            patterns.Event(
                self.note.subjectChangedEventType(), self.note, "Note"
            ),
            self.events[0],
        )

    def test_default_description(self):
        self.assertEqual("", self.note.description())

    def test_given_description(self):
        a_note = note.Note(description="Description")
        self.assertEqual("Description", a_note.description())

    def test_set_description(self):
        self.note.setDescription("Description")
        self.assertEqual("Description", self.note.description())

    def test_description_change_notification(self):
        patterns.Publisher().registerObserver(
            self.onEvent, self.note.descriptionChangedEventType()
        )
        self.note.setDescription("Description")
        self.assertEqual(
            patterns.Event(
                self.note.descriptionChangedEventType(),
                self.note,
                "Description",
            ),
            self.events[0],
        )

    def test_add_child(self):
        self.note.addChild(self.child)
        self.assertEqual([self.child], self.note.children())

    def test_remove_child(self):
        self.note.addChild(self.child)
        self.note.removeChild(self.child)
        self.assertEqual([], self.note.children())

    def test_add_child_notification(self):
        patterns.Publisher().registerObserver(
            self.onEvent, note.Note.addChildEventType()
        )
        self.note.addChild(self.child)
        self.assertEqual(
            patterns.Event(
                note.Note.addChildEventType(), self.note, self.child
            ),
            self.events[0],
        )

    def test_remove_child_notification(self):
        patterns.Publisher().registerObserver(
            self.onEvent, note.Note.removeChildEventType()
        )
        self.note.addChild(self.child)
        self.note.removeChild(self.child)
        self.assertEqual(
            patterns.Event(
                note.Note.removeChildEventType(), self.note, self.child
            ),
            self.events[0],
        )

    def test_new_child(self):
        child = self.note.newChild(subject="child")
        self.assertEqual("child", child.subject())  # pylint: disable=E1101


class NoteOwnerUnderTest(note.NoteOwner, base.Object):
    pass


class NoteOwnerTest(test.TestCase):
    def setUp(self):
        self.note = note.Note(subject="Note")
        self.noteOwner = NoteOwnerUnderTest()
        self.events = []

    def onEvent(self, event):
        self.events.append(event)

    # pylint: disable=E1101

    def registerObserver(self):  # pylint: disable=W0221
        patterns.Publisher().registerObserver(
            self.onEvent, NoteOwnerUnderTest.notesChangedEventType()
        )

    def test_add_note(self):
        self.noteOwner.addNote(self.note)
        self.assertEqual([self.note], self.noteOwner.notes())

    def test_add_notes(self):
        self.noteOwner.addNotes(self.note)
        self.assertEqual([self.note], self.noteOwner.notes())

    def test_add_note_notification(self):
        self.registerObserver()
        self.noteOwner.addNote(self.note)
        self.assertEqual(
            patterns.Event(
                NoteOwnerUnderTest.notesChangedEventType(),
                self.noteOwner,
                self.note,
            ),
            self.events[0],
        )

    def test_remove_note(self):
        self.noteOwner.addNote(self.note)
        self.noteOwner.removeNote(self.note)
        self.assertFalse(self.noteOwner.notes())

    def test_remove_notes(self):
        self.noteOwner.addNote(self.note)
        self.noteOwner.removeNotes(self.note)
        self.assertFalse(self.noteOwner.notes())

    def test_remove_note_notification(self):
        self.noteOwner.addNote(self.note)
        self.registerObserver()
        self.noteOwner.removeNote(self.note)
        self.assertEqual(
            [
                patterns.Event(
                    NoteOwnerUnderTest.notesChangedEventType(),
                    self.noteOwner,
                    self.note,
                )
            ],
            self.events,
        )

    def test_initialize_notes_via_constructor(self):
        note_owner = NoteOwnerUnderTest(notes=[self.note])
        self.assertEqual([self.note], note_owner.notes())

    def test_copy(self):
        self.noteOwner.addNote(self.note)
        copy = NoteOwnerUnderTest(**self.noteOwner.__getcopystate__())
        self.assertNotEqual(copy.notes()[0].id(), self.note.id())
        self.assertEqual(copy.notes()[0].subject(), self.note.subject())

    def test_copy_note_owner_with_note_with_sub_note(self):
        child = note.Note(subject="child")
        self.note.addChild(child)
        self.noteOwner.addNote(self.note)
        copy = NoteOwnerUnderTest(**self.noteOwner.__getcopystate__())
        child_copy = copy.notes()[0].children()[0]
        self.assertNotEqual(child_copy.id(), child.id())
        self.assertEqual(child_copy.subject(), child.subject())
