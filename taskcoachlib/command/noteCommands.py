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

from taskcoachlib import patterns
from taskcoachlib.i18n import _
from taskcoachlib.domain import note
from . import base


class NewNoteCommand(base.NewItemCommand):
    singular_name = _("New note")

    def __init__(self, *args, **kwargs):
        subject = kwargs.pop("subject", _("New note"))
        description = kwargs.pop("description", "")
        attachments = kwargs.pop("attachments", [])
        categories = kwargs.get("categories", None)
        super().__init__(*args, **kwargs)
        self.items = self.notes = [
            note.Note(
                subject=subject,
                description=description,
                categories=categories,
                attachments=attachments,
            )
        ]


class NewSubNoteCommand(base.NewSubItemCommand):
    plural_name = _("New subnotes")
    singular_name = _('New subnote of "%s"')

    def __init__(self, *args, **kwargs):
        subject = kwargs.pop("subject", _("New subnote"))
        description = kwargs.pop("description", "")
        attachments = kwargs.pop("attachments", [])
        categories = kwargs.get("categories", None)
        super().__init__(*args, **kwargs)
        # Store parent notes before overwriting self.items
        self.__parents = self.items[:]
        self.items = self.notes = [
            parent.newChild(
                subject=subject,
                description=description,
                categories=categories,
                attachments=attachments,
            )
            for parent in self.__parents
        ]
        self.save_modification_datetimes()

    @patterns.eventSource
    def do_command(self, event=None):
        # Add subnotes to parent notes as children. The parent's addChild
        # handles the parent-child relationship. We also need to add to the
        # container for the viewer to see them, but CompositeCollection.extend
        # will handle both adding to the container AND calling addChild via
        # _addCompositesToParent, so we just call the parent implementation.
        base.NewItemCommand.do_command(self, event=event)

    @patterns.eventSource
    def undo_command(self, event=None):
        base.NewItemCommand.undo_command(self, event=event)

    @patterns.eventSource
    def redo_command(self, event=None):
        base.NewItemCommand.redo_command(self, event=event)


class DeleteNoteCommand(base.DeleteCommand):
    plural_name = _("Delete notes")
    singular_name = _('Delete note "%s"')


class DragAndDropNoteCommand(base.OrderingDragAndDropCommand):
    plural_name = _("Drag and drop notes")
    singular_name = _('Drag and drop note "%s"')


class AddNoteCommand(base.BaseCommand):
    plural_name = _("Add note")
    singular_name = _('Add note to "%s"')

    def __init__(self, *args, **kwargs):
        self.owners = []
        super().__init__(*args, **kwargs)
        self.owners = self.items
        self.items = self.__notes = [
            note.Note(subject=_("New note")) for dummy in self.items
        ]
        self.save_modification_datetimes()

    def modified_items(self):
        return self.owners

    def name_subject(self, newNote):  # pylint: disable=W0613
        # Override to use the subject of the owner of the new note instead
        # of the subject of the new note itself, which wouldn't be very
        # interesting because it's something like 'New note'.
        return self.owners[0].subject()

    @patterns.eventSource
    def addNotes(self, event=None):
        for owner, note in zip(
            self.owners, self.__notes
        ):  # pylint: disable=W0621
            owner.addNote(note, event=event)

    @patterns.eventSource
    def removeNotes(self, event=None):
        for owner, note in zip(
            self.owners, self.__notes
        ):  # pylint: disable=W0621
            owner.removeNote(note, event=event)

    def do_command(self):
        super().do_command()
        self.addNotes()

    def undo_command(self):
        super().undo_command()
        self.removeNotes()

    def redo_command(self):
        super().redo_command()
        self.addNotes()


class AddSubNoteCommand(base.BaseCommand):
    plural_name = _("Add subnote")
    singular_name = _('Add subnote to "%s"')

    def __init__(self, *args, **kwargs):
        self.__owner = kwargs.pop("owner")
        self.__parents = []
        super().__init__(*args, **kwargs)
        self.__parents = self.items
        self.__notes = kwargs.get(
            "notes",
            [
                note.Note(subject=_("New subnote"), parent=parent)
                for parent in self.__parents
            ],
        )
        self.items = self.__notes
        self.save_modification_datetimes()

    def modified_items(self):
        return self.__parents

    @patterns.eventSource
    def addNotes(self, event=None):
        # Only add subnotes to their parent notes, not to the owner's notes list.
        # This fixes the bug where subnotes were duplicated at root level.
        for parent, subnote in zip(self.__parents, self.__notes):
            parent.addChild(subnote, event=event)
        # Notify the owner that notes changed so the viewer refreshes.
        # The viewer will pick up the subnote from parent.children().
        self.__owner.notesChangedEvent(event, *self.__notes)

    @patterns.eventSource
    def removeNotes(self, event=None):
        for parent, subnote in zip(self.__parents, self.__notes):
            parent.removeChild(subnote, event=event)
        # Notify the owner that notes changed so the viewer refreshes.
        self.__owner.notesChangedEvent(event, *self.__notes)

    def do_command(self):
        super().do_command()
        self.addNotes()

    def undo_command(self):
        super().undo_command()
        self.removeNotes()

    def redo_command(self):
        super().redo_command()
        self.addNotes()


class RemoveNoteCommand(base.BaseCommand):
    plural_name = _("Remove note")
    singular_name = _('Remove note from "%s"')

    def __init__(self, *args, **kwargs):
        self.__notes = kwargs.pop("notes")
        super().__init__(*args, **kwargs)

    @patterns.eventSource
    def addNotes(self, event=None):
        kwargs = dict(event=event)
        for item in self.items:
            item.addNotes(*self.__notes, **kwargs)  # pylint: disable=W0142

    @patterns.eventSource
    def removeNotes(self, event=None):
        # pylint: disable=W0142
        kwargs = dict(event=event)
        for item in self.items:
            for eachNote in self.__notes:
                if eachNote.parent():
                    eachNote.parent().removeChild(eachNote, **kwargs)
            item.removeNotes(*self.__notes, **kwargs)

    def do_command(self):
        super().do_command()
        self.removeNotes()

    def undo_command(self):
        super().undo_command()
        self.addNotes()

    def redo_command(self):
        super().redo_command()
        self.removeNotes()
