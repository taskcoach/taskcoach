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
from taskcoachlib.domain import date
from taskcoachlib.i18n import _
from .clipboard import Clipboard


class BaseCommand(patterns.Command):
    def __init__(
        self, list=None, items=None, *args, **kwargs
    ):  # pylint: disable=W0622
        super().__init__(*args, **kwargs)
        self.list = list
        self.items = [item for item in items] if items else []
        self.save_modification_datetimes()

    def save_modification_datetimes(self):
        self.__old_modification_datetimes = [
            (item, item.modificationDateTime())
            for item in self.modified_items()
            if item
        ]
        self.__now = date.Now()

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

    def modified_items(self):
        """Return the items that are modified by this command."""
        return self.items

    def canDo(self):
        return bool(self.items)

    def do(self):
        if self.canDo():
            super().do()
            self.do_command()

    def undo(self):
        super().undo()
        self.undo_command()

    def redo(self):
        super().redo()
        self.redo_command()

    def __tryInvokeMethodOnSuper(self, methodName, *args, **kwargs):
        try:
            method = getattr(super(), methodName)
        except AttributeError:
            return  # no 'method' in any super class
        return method(*args, **kwargs)

    def do_command(self):
        self.__tryInvokeMethodOnSuper("do_command")
        for item in self.modified_items():
            item.setModificationDateTime(self.__now)

    def undo_command(self):
        self.__tryInvokeMethodOnSuper("undo_command")
        for (
            item,
            old_modification_datetime,
        ) in self.__old_modification_datetimes:
            item.setModificationDateTime(old_modification_datetime)

    def redo_command(self):
        self.__tryInvokeMethodOnSuper("redo_command")
        for item in self.modified_items():
            item.setModificationDateTime(self.__now)


class SaveStateMixin(object):
    """Mixin class for commands that need to keep the states of objects.
    Objects should provide __getstate__ and __setstate__ methods."""

    # pylint: disable=W0201

    def saveStates(self, objects):
        self.objectsToBeSaved = objects
        self.oldStates = self.__getStates()

    @patterns.eventSource
    def undoStates(self, event=None):
        self.newStates = self.__getStates()
        self.__setStates(self.oldStates, event=event)

    @patterns.eventSource
    def redoStates(self, event=None):
        self.__setStates(self.newStates, event=event)

    def __getStates(self):
        return [
            objectToBeSaved.__getstate__()
            for objectToBeSaved in self.objectsToBeSaved
        ]

    @patterns.eventSource
    def __setStates(self, states, event=None):
        for objectToBeSaved, state in zip(self.objectsToBeSaved, states):
            objectToBeSaved.__setstate__(state, event=event)


class CompositeMixin(object):
    """Mixin class for commands that deal with composites."""

    def getAncestors(self, composites):
        ancestors = []
        for composite in composites:
            ancestors.extend(composite.ancestors())
        return ancestors

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

    def modified_items(self):
        return []

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        self.list.extend(
            self.items
        )  # Don't use the event to force this change to be notified first
        event.addSource(self, type="newitem", *self.items)

    @patterns.eventSource
    def undo_command(self, event=None):
        super().undo_command()
        self.list.removeItems(self.items, event=event)

    @patterns.eventSource
    def redo_command(self, event=None):
        super().redo_command()
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

    def modified_items(self):
        return [item.parent() for item in self.items]


class CopyCommand(BaseCommand):
    plular_name = _("Copy")
    singular_name = _('Copy "%s"')

    def do_command(self):
        self.__copies = [
            item.copy() for item in self.items
        ]  # pylint: disable=W0201
        Clipboard().put(self.__copies, self.list)

    def undo_command(self):
        Clipboard().clear()

    def redo_command(self):
        Clipboard().put(self.__copies, self.list)


class DeleteCommand(BaseCommand, SaveStateMixin):
    plural_name = _("Delete")
    singular_name = _('Delete "%s"')

    def __init__(self, *args, **kwargs):
        self.__shadow = kwargs.pop("shadow", False)
        super().__init__(*args, **kwargs)

    def modified_items(self):
        return [item.parent() for item in self.items if item.parent()]

    def do_command(self):
        super().do_command()
        if self.__shadow:
            self.saveStates(self.items)

            for item in self.items:
                item.markDeleted()
        else:
            self.list.removeItems(self.items)

    def undo_command(self):
        super().undo_command()
        if self.__shadow:
            self.undoStates()
        else:
            self.list.extend(self.items)

    def redo_command(self):
        super().redo_command()
        if self.__shadow:
            self.redoStates()
        else:
            self.list.removeItems(self.items)


class CutCommandMixin(object):
    plural_name = _("Cut")
    singular_name = _('Cut "%s"')

    def __putItemsOnClipboard(self):
        cb = Clipboard()
        self.__previousClipboardContents = cb.get()  # pylint: disable=W0201
        cb.put(self.itemsToCut(), self.sourceOfItemsToCut())

    def __removeItemsFromClipboard(self):
        cb = Clipboard()
        cb.put(*self.__previousClipboardContents)

    def do_command(self):
        self.__putItemsOnClipboard()
        super().do_command()

    def undo_command(self):
        self.__removeItemsFromClipboard()
        super().undo_command()

    def redo_command(self):
        self.__putItemsOnClipboard()
        super().redo_command()


class CutCommand(CutCommandMixin, DeleteCommand):
    def itemsToCut(self):
        return self.items

    def sourceOfItemsToCut(self):
        return self.list


class PasteCommand(BaseCommand, SaveStateMixin):
    plural_name = _("Paste")
    singular_name = _('Paste "%s"')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__itemsToPaste, self.__sourceOfItemsToPaste = (
            self.getItemsToPaste()
        )
        self.saveStates(self.getItemsToSave())

    def getItemsToSave(self):
        return self.__itemsToPaste

    def canDo(self):
        return bool(self.__itemsToPaste)

    def do_command(self):
        self.setParentOfPastedItems()
        self.__sourceOfItemsToPaste.extend(self.__itemsToPaste)

    def undo_command(self):
        self.__sourceOfItemsToPaste.removeItems(self.__itemsToPaste)
        self.undoStates()

    def redo_command(self):
        self.redoStates()
        self.__sourceOfItemsToPaste.extend(self.__itemsToPaste)

    def setParentOfPastedItems(self, newParent=None):
        for item in self.__itemsToPaste:
            item.setParent(newParent)

    def getItemsToPaste(self):
        items, source = Clipboard().get()
        return [item.copy() for item in items], source


class PasteAsSubItemCommand(PasteCommand, CompositeMixin):
    plural_name = _("Paste as subitem")
    singular_name = _('Paste as subitem of "%s"')

    def setParentOfPastedItems(self):  # pylint: disable=W0221
        newParent = self.items[0]
        super().setParentOfPastedItems(newParent)

    def getItemsToSave(self):
        return self.getAncestors([self.items[0]]) + super().getItemsToSave()


class DragAndDropCommand(BaseCommand, SaveStateMixin, CompositeMixin):
    plural_name = _("Drag and drop")
    singular_name = _('Drag and drop "%s"')

    def __init__(self, *args, **kwargs):
        dropTargets = kwargs.pop("drop")
        self._itemToDropOn = dropTargets[0] if dropTargets else None
        super().__init__(*args, **kwargs)
        self.saveStates(self.getItemsToSave())

    def getItemsToSave(self):
        toSave = self.items[:]
        if self._itemToDropOn is not None:
            toSave.insert(0, self._itemToDropOn)
        return toSave

    def modified_items(self):
        return (
            [item.parent() for item in self.items if item.parent()]
            + [self._itemToDropOn]
            if self._itemToDropOn
            else []
        )

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
            item.setParent(self._itemToDropOn)
        self.list.extend(self.items)

    def undo_command(self):
        super().undo_command()
        self.list.removeItems(self.items)
        self.undoStates()
        self.list.extend(self.items)

    def redo_command(self):
        super().redo_command()
        self.list.removeItems(self.items)
        self.redoStates()
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

    def getItemsToSave(self):
        items = super().getItemsToSave()
        if self.isOrdering():
            items.extend(self.getOrderingSiblings())
        return items

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
                minOrderingOfPreviousSiblings = min(
                    [
                        item.ordering()
                        for idx, item in enumerate(siblings)
                        if idx < insertIndex
                    ]
                )
                maxOrderingOfNextSiblings = max(
                    [
                        item.ordering()
                        for idx, item in enumerate(siblings)
                        if idx >= insertIndex
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
        self.__old_subjects = [(item, item.subject()) for item in self.items]

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        for item in self.items:
            item.setSubject(self.__newSubject, event=event)

    @patterns.eventSource
    def undo_command(self, event=None):
        super().undo_command()
        for item, old_subject in self.__old_subjects:
            item.setSubject(old_subject, event=event)

    def redo_command(self):
        self.do_command()


class EditDescriptionCommand(BaseCommand):
    plural_name = _("Edit descriptions")
    singular_name = _('Edit description "%s"')

    def __init__(self, *args, **kwargs):
        self.__new_description = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__old_descriptions = [item.description() for item in self.items]

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        for item in self.items:
            item.setDescription(self.__new_description, event=event)

    @patterns.eventSource
    def undo_command(self, event=None):
        super().undo_command()
        for item, old_description in zip(self.items, self.__old_descriptions):
            item.setDescription(old_description, event=event)

    def redo_command(self):
        self.do_command()


class EditIconCommand(BaseCommand):
    plural_name = _("Change icons")
    singular_name = _('Change icon "%s"')

    def __init__(self, *args, **kwargs):
        self.__newIcon = icon = kwargs.pop("newValue")
        self.__newSelectedIcon = (
            icon[: -len("_icon")] + "_open_icon"
            if (icon.startswith("folder") and icon.count("_") == 2)
            else icon
        )
        super().__init__(*args, **kwargs)
        self.__oldIcons = [
            (item.icon(), item.selectedIcon()) for item in self.items
        ]

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        for item in self.items:
            item.setIcon(self.__newIcon, event=event)
            item.setSelectedIcon(self.__newSelectedIcon, event=event)

    @patterns.eventSource
    def undo_command(self, event=None):
        super().undo_command()
        for item, (oldIcon, oldSelectedIcon) in zip(
            self.items, self.__oldIcons
        ):
            item.setIcon(oldIcon, event=event)
            item.setSelectedIcon(oldSelectedIcon, event=event)

    def redo_command(self):
        self.do_command()


class EditFontCommand(BaseCommand):
    plural_name = _("Change fonts")
    singular_name = _('Change font "%s"')

    def __init__(self, *args, **kwargs):
        self.__newFont = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldFonts = [item.font() for item in self.items]

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        for item in self.items:
            item.setFont(self.__newFont, event=event)

    @patterns.eventSource
    def undo_command(self, event=None):
        super().undo_command()
        for item, oldFont in zip(self.items, self.__oldFonts):
            item.setFont(oldFont, event=event)

    def redo_command(self):
        self.do_command()


class EditColorCommand(BaseCommand):
    def __init__(self, *args, **kwargs):
        self.__newColor = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldColors = [self.getItemColor(item) for item in self.items]

    @staticmethod
    def getItemColor(item):
        raise NotImplementedError

    @staticmethod
    def setItemColor(item, color, event):
        raise NotImplementedError

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        for item in self.items:
            self.setItemColor(item, self.__newColor, event)

    @patterns.eventSource
    def undo_command(self, event=None):
        super().undo_command()
        for item, oldColor in zip(self.items, self.__oldColors):
            self.setItemColor(item, oldColor, event)

    def redo_command(self):
        self.do_command()


class EditForegroundColorCommand(EditColorCommand):
    plural_name = _("Change foreground colors")
    singular_name = _('Change foreground color "%s"')

    @staticmethod
    def getItemColor(item):
        return item.foregroundColor()

    @staticmethod
    def setItemColor(item, color, event):
        item.setForegroundColor(color, event=event)


class EditBackgroundColorCommand(EditColorCommand):
    plural_name = _("Change background colors")
    singular_name = _('Change background color "%s"')

    @staticmethod
    def getItemColor(item):
        return item.backgroundColor()

    @staticmethod
    def setItemColor(item, color, event):
        item.setBackgroundColor(color, event=event)
