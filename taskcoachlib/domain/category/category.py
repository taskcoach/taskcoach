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
from taskcoachlib.domain import base, note, attachment


class Category(
    attachment.AttachmentOwner, note.NoteOwner, base.CompositeObject
):
    """Category class for organizing tasks and notes.

    Appearance (derived and effective values) is handled by the base class
    and ComputeStyles polling. No explicit calls needed.
    """

    def __init__(
        self,
        subject,
        categorizables=None,
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
        self.__categorizables = base.SetAttribute(
            set(categorizables or []),
            self,
            self.categorizableAddedEvent,
            self.categorizableRemovedEvent,
            weak=True,
        )
        self.__filtered = filtered
        self.__exclusiveSubcategories = exclusiveSubcategories
        self.__stylePriority = stylePriority
        # Note: Effective appearance is computed by ComputeStyles polling

    @classmethod
    def monitoredAttributes(class_):
        return base.CompositeObject.monitoredAttributes() + [
            "exclusiveSubcategories",
            "stylePriority"
        ]

    @classmethod
    def filterChangedEventType(class_):
        """Event type to notify observers that categorizables belonging to
        this category are filtered or not."""
        return "category.filter"

    @classmethod
    def categorizableAddedEventType(class_):
        """Event type to notify observers that categorizables have been added
        to this category."""
        return "category.categorizable.added"

    @classmethod
    def categorizableRemovedEventType(class_):
        """Event type to notify observers that categorizables have been removed
        from this category."""
        return "category.categorizable.removed"

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
            class_.categorizableAddedEventType(),
            class_.categorizableRemovedEventType(),
            class_.exclusiveSubcategoriesChangedEventType(),
            class_.stylePriorityChangedEventType(),
        ]

    def __getstate__(self):
        state = super().__getstate__()
        state.update(
            dict(
                categorizables=self.__categorizables.get(),
                filtered=self.__filtered,
                stylePriority=self.__stylePriority,
            ),
            exclusiveSubcategories=self.__exclusiveSubcategories,
        )
        return state

    @patterns.eventSource
    def __setstate__(self, state, event=None):
        super().__setstate__(state, event=event)
        self.setCategorizables(state["categorizables"], event=event)
        self.setFiltered(state["filtered"], event=event)
        self.makeSubcategoriesExclusive(
            state["exclusiveSubcategories"], event=event
        )
        self.setStylePriority(state.get("stylePriority", 0), event=event)

    def __getcopystate__(self):
        state = super().__getcopystate__()
        state.update(
            dict(
                categorizables=self.__categorizables.get(),
                filtered=self.__filtered,
                stylePriority=self.__stylePriority,
            )
        )
        return state

    def subjectChangedEvent(self, event):
        super().subjectChangedEvent(event)
        self.categorySubjectChangedEvent(event)

    def categorySubjectChangedEvent(self, event):
        subject = self.subject()
        for eachCategorizable in self.categorizables(recursive=True):
            eachCategorizable.categorySubjectChangedEvent(event, subject)

    def categorizables(self, recursive=False):
        result = self.__categorizables.get()
        if recursive:
            for child in self.children():
                result |= child.categorizables(recursive)
        return result

    def addCategorizable(self, *categorizables, **kwargs):
        self.__categorizables.add(
            set(categorizables), event=kwargs.pop("event", None)
        )

    def categorizableAddedEvent(self, event, *categorizables):
        event.addSource(
            self,
            *categorizables,
            **dict(type=self.categorizableAddedEventType())
        )

    def removeCategorizable(self, *categorizables, **kwargs):
        self.__categorizables.remove(
            set(categorizables), event=kwargs.pop("event", None)
        )

    def categorizableRemovedEvent(self, event, *categorizables):
        event.addSource(
            self,
            *categorizables,
            **dict(type=self.categorizableRemovedEventType())
        )

    def setCategorizables(self, categorizables, event=None):
        self.__categorizables.set(set(categorizables), event=event)

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

    def appearanceChangedEvent(self, event):
        """Handle appearance change event.

        Notifies categorizables (tasks/notes) that belong to this category.
        Note: Effective appearance is computed by ComputeStyles polling.
        """
        super().appearanceChangedEvent(event)
        for categorizable in self.categorizables():
            categorizable.appearanceChangedEvent(event)

    def _onEffectiveIconChanged(self, event):
        """Propagate effective icon changes to categorizables (tasks/notes)."""
        super()._onEffectiveIconChanged(event)
        for categorizable in self.categorizables():
            event.addSource(categorizable, type=categorizable.effectiveIconChangedEventType())

    def hasExclusiveSubcategories(self):
        return self.__exclusiveSubcategories

    def isMutualExclusive(self):
        parent = self.parent()
        return parent and parent.hasExclusiveSubcategories()

    @patterns.eventSource
    def makeSubcategoriesExclusive(self, exclusive=True, event=None):
        if exclusive == self.hasExclusiveSubcategories():
            return
        self.__exclusiveSubcategories = exclusive
        self.exclusiveSubcategoriesEvent(event)
        for child in self.children():
            child.setFiltered(False, event=event)

    # "Conventional" naming for the monitor
    def exclusiveSubcategories(self):
        return self.hasExclusiveSubcategories()

    @patterns.eventSource
    def setExclusiveSubcategories(self, exclusive=True, event=None):
        self.makeSubcategoriesExclusive(exclusive=exclusive, event=event)

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
        return self.__stylePriority

    @patterns.eventSource
    def setStylePriority(self, priority, event=None):
        """Set the style priority for this category."""
        if priority == self.__stylePriority:
            return
        self.__stylePriority = priority
        self.stylePriorityChangedEvent(event)

    def stylePriorityChangedEvent(self, event):
        event.addSource(
            self,
            self.__stylePriority,
            type=self.stylePriorityChangedEventType(),
        )
