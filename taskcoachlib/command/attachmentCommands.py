# -*- coding: utf-8 -*-

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
from taskcoachlib.domain import attachment
from . import base, noteCommands


class EditAttachmentLocationCommand(base.BaseCommand):
    plural_name = _("Edit location of attachments")
    singular_name = _('Edit attachment "%s" location')

    def __init__(self, *args, **kwargs):
        self.__newLocation = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldLocations = [item.location() for item in self.items]

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        for item in self.items:
            item.setLocation(self.__newLocation)

    @patterns.eventSource
    def undo_command(self, event=None):
        super().undo_command()
        for item, oldLocation in zip(self.items, self.__oldLocations):
            item.setLocation(oldLocation)

    def redo_command(self):
        self.do_command()


class AddAttachmentCommand(base.BaseCommand):
    plural_name = _("Add attachment")
    singular_name = _('Add attachment to "%s"')

    def __init__(self, *args, **kwargs):
        self.owners = []
        self.__attachments = kwargs.get(
            "attachments",
            [attachment.FileAttachment("", subject=_("New attachment"))],
        )
        super().__init__(*args, **kwargs)
        self.owners = self.items
        self.items = self.__attachments

    @patterns.eventSource
    def addAttachments(self, event=None):
        kwargs = dict(event=event)
        for owner in self.owners:
            owner.addAttachments(
                *self.__attachments, **kwargs
            )  # pylint: disable=W0142

    @patterns.eventSource
    def removeAttachments(self, event=None):
        kwargs = dict(event=event)
        for owner in self.owners:
            owner.removeAttachments(
                *self.__attachments, **kwargs
            )  # pylint: disable=W0142

    def do_command(self):
        super().do_command()
        self.addAttachments()

    def undo_command(self):
        super().undo_command()
        self.removeAttachments()

    def redo_command(self):
        super().redo_command()
        base.Clipboard().spend_move(self.__attachments)
        self.addAttachments()


class RemoveAttachmentCommand(base.BaseCommand):
    plural_name = _("Remove attachment")
    singular_name = _('Remove attachment to "%s"')

    def __init__(self, *args, **kwargs):
        self._attachments = kwargs.pop("attachments")
        super().__init__(*args, **kwargs)

    @patterns.eventSource
    def addAttachments(self, event=None):
        kwargs = dict(event=event)
        for item in self.items:
            item.addAttachments(
                *self._attachments, **kwargs
            )  # pylint: disable=W0142

    @patterns.eventSource
    def removeAttachments(self, event=None):
        kwargs = dict(event=event)
        for item in self.items:
            item.removeAttachments(
                *self._attachments, **kwargs
            )  # pylint: disable=W0142

    def do_command(self):
        super().do_command()
        self.removeAttachments()

    def undo_command(self):
        super().undo_command()
        self.addAttachments()

    def redo_command(self):
        super().redo_command()
        self.removeAttachments()


class CutAttachmentCommand(base.CutCommandMixin, RemoveAttachmentCommand):
    def itemsToCut(self):
        return self._attachments

    def sourceOfItemsToCut(self):
        class Wrapper(object):
            def __init__(self, items):
                self.__items = items

            def extend(self, attachments):
                for item in self.__items:
                    item.addAttachments(*attachments)

            def removeItems(self, attachments):
                for item in self.__items:
                    item.removeAttachments(*attachments)

        return Wrapper(self.items)
