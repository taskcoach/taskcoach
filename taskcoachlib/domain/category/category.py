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

from weakref import WeakSet

from taskcoachlib import patterns
from taskcoachlib.domain import base, note, attachment


class Category(
    attachment.AttachmentOwner, note.NoteOwner, base.CompositeObject
):
    """Category class for organizing tasks and notes.

    Appearance (derived and effective values) is handled by the base class
    and the master loop. No explicit calls needed.
    """

    def __init__(
        self,
        subject,
        members=None,
        children=None,
        filtered=False,
        parent=None,
        description="",
        exclusiveSubcategories=False,
        stylePriority=0,
        *args,
        **kwargs
    ):
        super().__init__(
            subject=subject,
            children=children or [],
            parent=parent,
            description=description,
            *args,
            **kwargs
        )
        # Membership is the items' own data, their categories; this is
        # its index, kept by them alone (docs/ATTRIBUTE_PATTERN.md,
        # Modification Date). Every item that claims the category, in
        # the file or not (a copy, a deleted item kept for undo)
        self.__members = WeakSet()
        # Outside the file (a copy, a deleted category), the members
        # that rejoin it when it enters
        self.__rejoining = list(members or [])
        self.__filtered = filtered
        self.__exclusiveSubcategories = base.Attribute(
            exclusiveSubcategories,
            self,
            self._on_exclusive_subcategories_changed,
        )
        self.__stylePriority = base.Attribute(
            stylePriority, self, self.stylePriorityChangedEvent
        )
        # Note: Effective appearance is computed by the master loop

    @classmethod
    def filterChangedEventType(class_):
        """Event type to notify observers that the items belonging to
        this category are filtered or not."""
        return "category.filter"

    @classmethod
    def member_added_event_type(cls):
        """An item's categories now hold this one."""
        return "category.member.added"

    @classmethod
    def member_removed_event_type(cls):
        """An item's categories no longer hold this one."""
        return "category.member.removed"

    @classmethod
    def exclusiveSubcategoriesChangedEventType(class_):
        """Event type to notify observers that subcategories have become
        exclusive (or vice versa)."""
        return "category.exclusiveSubcategories"

    @classmethod
    def stylePriorityChangedEventType(class_):
        """Event type to notify observers that style priority has changed."""
        return "category.stylePriority"

    @classmethod
    def modificationEventTypes(class_):
        eventTypes = super(Category, class_).modificationEventTypes()
        return eventTypes + [
            class_.filterChangedEventType(),
            class_.member_added_event_type(),
            class_.member_removed_event_type(),
            class_.exclusiveSubcategoriesChangedEventType(),
            class_.stylePriorityChangedEventType(),
        ]

    def __getstate__(self):
        state = super().__getstate__()
        state.update(
            dict(
                filtered=self.__filtered,
                stylePriority=self.stylePriority(),
            ),
            exclusiveSubcategories=self.hasExclusiveSubcategories(),
        )
        return state

    @patterns.eventSource
    def __setstate__(self, state, event=None):
        super().__setstate__(state, event=event)
        self.setFiltered(state["filtered"], event=event)
        self.makeSubcategoriesExclusive(
            state["exclusiveSubcategories"], event=event
        )
        self.setStylePriority(state.get("stylePriority", 0), event=event)

    def __getcopystate__(self):
        state = super().__getcopystate__()
        state.update(
            dict(
                # A copy's members join it when it is pasted
                members=list(self.__members) + self.__rejoining,
                filtered=self.__filtered,
                stylePriority=self.stylePriority(),
            )
        )
        return state

    def subjectChangedEvent(self, event):
        super().subjectChangedEvent(event)
        self.categorySubjectChangedEvent(event)

    def categorySubjectChangedEvent(self, event):
        subject = self.subject()
        for member in self.members(recursive=True):
            member.categorySubjectChangedEvent(event, subject)

    def members(self, recursive=False):
        """The items that claim this category (their categories hold
        it); whether each is in the file is the file's to say."""
        result = set(self.__members)
        if recursive:
            for child in self.children():
                result |= child.members(recursive)
        return result

    def member_joined(self, item, event=None):
        """Called by an item whose categories now hold it."""
        self.__members.add(item)
        if event is not None:
            self.member_added_event(event, item)

    def member_left(self, item, event=None):
        """Called by an item whose categories no longer hold it."""
        self.__members.discard(item)
        if event is not None:
            self.member_removed_event(event, item)

    def leave_file(self, event=None):
        """Deleted or cut: the members lose it, and it remembers them
        to rejoin if it comes back (undo, paste)."""
        self.__rejoining = list(self.__members)
        for each in self.__rejoining:
            each.removeCategory(self, event=event)

    def enter_file(self, event=None):
        """Added (paste, undo of a delete): the members it remembers,
        a copy's too, rejoin it."""
        rejoining, self.__rejoining = self.__rejoining, []
        for each in rejoining:
            each.addCategory(self, event=event)

    def member_added_event(self, event, *members):
        event.addSource(self, *members, type=self.member_added_event_type())

    def member_removed_event(self, event, *members):
        event.addSource(self, *members, type=self.member_removed_event_type())

    def isFiltered(self):
        return self.__filtered

    @patterns.eventSource
    def setFiltered(self, filtered=True, event=None):
        if filtered == self.__filtered:
            return
        self.__filtered = filtered
        self.filterChangedEvent(event)

    def filterChangedEvent(self, event):
        event.addSource(
            self, self.isFiltered(), type=self.filterChangedEventType()
        )

    def _on_effective_icon_changed(self, event):
        """Its items show this icon in their Category icons column, so
        the event names them too."""
        super()._on_effective_icon_changed(event)
        for member in self.members():
            event.addSource(
                member, type=member.effectiveIconChangedEventType()
            )

    def hasExclusiveSubcategories(self):
        return self.__exclusiveSubcategories.get()

    def isMutualExclusive(self):
        parent = self.parent()
        return parent and parent.hasExclusiveSubcategories()

    def makeSubcategoriesExclusive(self, exclusive=True, event=None):
        self.__exclusiveSubcategories.set(exclusive, event=event)

    def _on_exclusive_subcategories_changed(self, event):
        self.exclusiveSubcategoriesEvent(event)
        for child in self.children():
            child.setFiltered(False, event=event)

    def exclusiveSubcategoriesEvent(self, event):
        event.addSource(
            self,
            self.hasExclusiveSubcategories(),
            type=self.exclusiveSubcategoriesChangedEventType(),
        )

    # Style Priority - determines which category's style wins when a task has multiple categories
    # Higher priority wins. Default is 0.

    def stylePriority(self):
        """Return the style priority for this category."""
        return self.__stylePriority.get()

    def setStylePriority(self, priority, event=None):
        """Set the style priority for this category."""
        self.__stylePriority.set(priority, event=event)

    def stylePriorityChangedEvent(self, event):
        event.addSource(
            self,
            self.stylePriority(),
            type=self.stylePriorityChangedEventType(),
        )
