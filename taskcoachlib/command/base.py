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
from .clipboard import Clipboard


class BaseCommand(patterns.Command):
    def __init__(
        self, list=None, items=None, *args, **kwargs
    ):  # pylint: disable=W0622
        super().__init__(*args, **kwargs)
        self.list = list
        self.items = [item for item in items] if items else []

    def __str__(self):
        return self.name()

    singular_name = "Do something with %s"  # Override in subclass
    plural_name = "Do something"  # Override in subclass

    def name(self):
        return (
            self.singular_name % self.name_subject(self.items[0])
            if len(self.items) == 1
            else self.plural_name
        )

    def name_subject(self, item):
        subject = item.subject()
        return subject if len(subject) < 60 else subject[:57] + "..."

    def items_are_new(self):
        return False

    def getItems(self):
        """The items this command operates on."""
        return self.items

    def canDo(self):
        return bool(self.items)

    def do(self):
        if self.canDo():
            super().do()


class CompositeMixin(object):
    """Mixin class for commands that deal with composites."""

    def getAllChildren(self, composites):
        allChildren = []
        for composite in composites:
            allChildren.extend(composite.children(recursive=True))
        return allChildren

    def getAllParents(self, composites):
        return [
            composite.parent()
            for composite in composites
            if composite.parent() != None
        ]


class NewItemCommand(BaseCommand):
    def name(self):
        # Override to always return the singular name without a subject. The
        # subject would be something like "New task", so not very interesting.
        return self.singular_name

    def items_are_new(self):
        return True

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        self.list.extend(
            self.items
        )  # Don't use the event to force this change to be notified first
        event.addSource(self, type="newitem", *self.items)


class NewSubItemCommand(NewItemCommand):
    def name_subject(self, subitem):
        # Override to use the subject of the parent of the new subitem instead
        # of the subject of the new subitem itself, which wouldn't be very
        # interesting because it's something like 'New subitem'.
        return subitem.parent().subject()


class CopyCommand(BaseCommand):
    plular_name = _("Copy")
    singular_name = _('Copy "%s"')

    def do_command(self):
        Clipboard().put([item.copy() for item in self.items], self.list)


class DeleteCommand(BaseCommand):
    plural_name = _("Delete")
    singular_name = _('Delete "%s"')

    def do_command(self):
        super().do_command()
        self.list.removeItems(self.items)


class CutCommandMixin(object):
    plural_name = _("Cut")
    singular_name = _('Cut "%s"')

    def do_command(self):
        Clipboard().put(self.itemsToCut(), self.sourceOfItemsToCut(), cut=True)
        super().do_command()


class CutCommand(CutCommandMixin, DeleteCommand):
    def itemsToCut(self):
        return self.items

    def sourceOfItemsToCut(self):
        return self.list


class PasteCommand(BaseCommand):
    """Command to paste items from the clipboard.

    When a destination container is provided via the constructor, items are
    pasted into that container. Otherwise, items are pasted back into the
    clipboard's source container. This allows viewers to specify a different
    destination for paste operations, such as when pasting between tasks
    in the task editor dialog.
    """

    plural_name = _("Paste")
    singular_name = _('Paste "%s"')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__itemsToPaste, self.__sourceOfItemsToPaste = (
            self.getItemsToPaste()
        )

    def canDo(self):
        return bool(self.__itemsToPaste)

    def do_command(self):
        self.setParentOfPastedItems()
        self.__sourceOfItemsToPaste.extend(self.__itemsToPaste)

    def setParentOfPastedItems(self, newParent=None):
        for item in self.__itemsToPaste:
            item.set_parent(newParent)

    def getItemsToPaste(self):
        _items, source = Clipboard().get()
        # Use provided destination container, or fall back to clipboard's source container
        target = self.list if self.list is not None else source
        return Clipboard().items_to_paste(), target


class PasteAsSubItemCommand(PasteCommand, CompositeMixin):
    plural_name = _("Paste as subitem")
    singular_name = _('Paste as subitem of "%s"')

    def setParentOfPastedItems(self):  # pylint: disable=W0221
        newParent = self.items[0]
        super().setParentOfPastedItems(newParent)


class DragAndDropCommand(BaseCommand, CompositeMixin):
    plural_name = _("Drag and drop")
    singular_name = _('Drag and drop "%s"')

    def __init__(self, *args, **kwargs):
        dropTargets = kwargs.pop("drop")
        self._itemToDropOn = dropTargets[0] if dropTargets else None
        super().__init__(*args, **kwargs)

    def canDo(self):
        return self._itemToDropOn not in (
            self.items
            + self.getAllChildren(self.items)
            + self.getAllParents(self.items)
        )

    def do_command(self):
        super().do_command()
        self.list.removeItems(self.items)
        for item in self.items:
            item.set_parent(self._itemToDropOn)
        self.list.extend(self.items)


class OrderingDragAndDropCommand(DragAndDropCommand):
    def __init__(self, *args, **kwargs):
        self.column = kwargs.pop("column", None)
        self.isTreeMode = kwargs.pop("isTree", True)
        self.part = kwargs.pop("part", 0)
        self.dropColumn = kwargs.pop("dropColumn", -1)
        self.dropColumnName = kwargs.pop("dropColumnName", None)
        super().__init__(*args, **kwargs)

    def isOrdering(self):
        return self.column is not None and self.column.name() == "ordering"

    def getSiblings(self):
        siblings = []
        for item in self.list:
            if (
                item.parent() == self._itemToDropOn.parent()
                and item not in self.items
            ):
                siblings.append(item)
        return siblings

    def getOrderingSiblings(self):
        if self.isTreeMode:
            return self.getSiblings()
        # Everything, almost
        return [item for item in self.list if item not in self.items]

    def canDo(self):
        if self.isOrdering():
            return True  # Already checked when drag and droppin
        return super().canDo()

    def do_command(self):
        if self.isOrdering():
            siblings = self.getOrderingSiblings()

            orderings = [item.ordering() for item in self.items]
            minOrdering = min(orderings)
            maxOrdering = max(orderings)

            insertIndex = (
                siblings.index(self._itemToDropOn) + (self.part + 1) // 2
            )

            # Simple special cases
            if insertIndex == 0:
                minOrderingOfSiblings = min(
                    [item.ordering() for item in siblings]
                )
                for item in self.items:
                    item.setOrdering(
                        item.ordering()
                        - maxOrdering
                        + minOrderingOfSiblings
                        - 1
                    )
            elif insertIndex == len(siblings):
                maxOrderingOfSiblings = max(
                    [item.ordering() for item in siblings]
                )
                for item in self.items:
                    item.setOrdering(
                        item.ordering()
                        - minOrdering
                        + maxOrderingOfSiblings
                        + 1
                    )
            else:
                maxOrderingOfPreviousSiblings = max(
                    [
                        item.ordering()
                        for idx, item in enumerate(siblings)
                        if idx < insertIndex
                    ]
                )
                minOrderingOfNextSiblings = min(
                    [
                        item.ordering()
                        for idx, item in enumerate(siblings)
                        if idx >= insertIndex
                    ]
                )
                if insertIndex < len(siblings) // 2:
                    for item in self.items:
                        item.setOrdering(
                            item.ordering()
                            - maxOrdering
                            - 1
                            + minOrderingOfNextSiblings
                        )
                    for item in siblings[:insertIndex]:
                        item.setOrdering(
                            item.ordering()
                            - maxOrderingOfPreviousSiblings
                            - 1
                            + minOrdering
                            - maxOrdering
                            - 1
                            + minOrderingOfNextSiblings
                        )
                else:
                    for item in self.items:
                        item.setOrdering(
                            item.ordering()
                            - minOrdering
                            + 1
                            + maxOrderingOfPreviousSiblings
                        )
                    for item in siblings[insertIndex:]:
                        item.setOrdering(
                            item.ordering()
                            - minOrderingOfNextSiblings
                            + 1
                            + maxOrdering
                            - minOrdering
                            + 1
                            + maxOrderingOfPreviousSiblings
                        )
        else:
            super().do_command()


class EditSubjectCommand(BaseCommand):
    plural_name = _("Edit subjects")
    singular_name = _('Edit subject "%s"')

    def __init__(self, *args, **kwargs):
        self.__newSubject = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        for item in self.items:
            item.setSubject(self.__newSubject, event=event)


class EditDescriptionCommand(BaseCommand):
    plural_name = _("Edit descriptions")
    singular_name = _('Edit description "%s"')

    def __init__(self, *args, **kwargs):
        self.__new_description = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        for item in self.items:
            item.setDescription(self.__new_description, event=event)


class EditIconCommand(BaseCommand):
    plural_name = _("Change icons")
    singular_name = _('Change icon "%s"')

    def __init__(self, *args, **kwargs):
        self.__new_icon_id = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        for item in self.items:
            item.set_icon_id(self.__new_icon_id, event=event)


class EditFontCommand(BaseCommand):
    plural_name = _("Change fonts")
    singular_name = _('Change font "%s"')

    def __init__(self, *args, **kwargs):
        self.__newFont = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        for item in self.items:
            item.setFont(self.__newFont, event=event)


class EditColorCommand(BaseCommand):
    def __init__(self, *args, **kwargs):
        self.__newColor = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    @staticmethod
    def setItemColor(item, color, event):
        raise NotImplementedError

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        for item in self.items:
            self.setItemColor(item, self.__newColor, event)


class EditForegroundColorCommand(EditColorCommand):
    plural_name = _("Change foreground colors")
    singular_name = _('Change foreground color "%s"')

    @staticmethod
    def setItemColor(item, color, event):
        item.setForegroundColor(color, event=event)


class EditBackgroundColorCommand(EditColorCommand):
    plural_name = _("Change background colors")
    singular_name = _('Change background color "%s"')

    @staticmethod
    def setItemColor(item, color, event):
        item.setBackgroundColor(color, event=event)
