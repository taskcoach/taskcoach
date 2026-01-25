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
    def __init__(
        self,
        subject,
        categorizables=None,
        children=None,
        filtered=False,
        parent=None,
        description="",
        exclusiveSubcategories=False,
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
        # Effective appearance fields (single source of truth)
        # These are derived from own override OR parent's effective value
        self.__effective_fg_color = None
        self.__effective_bg_color = None
        self.__effective_icon = ""
        self.__effective_font = None
        self._computeEffectiveAppearance()

    @classmethod
    def monitoredAttributes(class_):
        return base.CompositeObject.monitoredAttributes() + [
            "exclusiveSubcategories"
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
    def modificationEventTypes(class_):
        eventTypes = super(Category, class_).modificationEventTypes()
        return eventTypes + [
            class_.filterChangedEventType(),
            class_.categorizableAddedEventType(),
            class_.categorizableRemovedEventType(),
            class_.exclusiveSubcategoriesChangedEventType(),
        ]

    def __getstate__(self):
        state = super().__getstate__()
        state.update(
            dict(
                categorizables=self.__categorizables.get(),
                filtered=self.__filtered,
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

    def __getcopystate__(self):
        state = super().__getcopystate__()
        state.update(
            dict(
                categorizables=self.__categorizables.get(),
                filtered=self.__filtered,
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
        """Override to include all categorizables in the event
        that belong to this category since their appearance (may)
        have changed too."""
        # Recompute effective values before propagating
        self._computeEffectiveAppearance()
        super().appearanceChangedEvent(event)
        for categorizable in self.categorizables():
            categorizable.appearanceChangedEvent(event)

    # --- Effective Appearance (Single Source of Truth) ---
    #
    # These fields store the final/effective appearance value for this category.
    # The effective value is: own override if set, otherwise parent's effective value.
    # This eliminates the need for recursive lookups at query time.
    #
    # IMPORTANT: Legacy code using recursive=True parameter is preserved for
    # backward compatibility. New code should use effectiveXxx() methods.

    def _computeEffectiveAppearance(self):
        """Compute effective appearance from own override or parent's effective value.

        Called on init and when appearance changes (via appearanceChangedEvent).
        Parent changes propagate automatically since appearanceChangedEvent
        cascades to children.
        """
        parent = self.parent()

        # Foreground color: own override or parent's effective
        own_fg = super().foregroundColor(recursive=False)
        if own_fg:
            self.__effective_fg_color = own_fg
        elif parent and hasattr(parent, 'effectiveFgColor'):
            self.__effective_fg_color = parent.effectiveFgColor()
        else:
            self.__effective_fg_color = None

        # Background color: own override or parent's effective
        own_bg = super().backgroundColor(recursive=False)
        if own_bg:
            self.__effective_bg_color = own_bg
        elif parent and hasattr(parent, 'effectiveBgColor'):
            self.__effective_bg_color = parent.effectiveBgColor()
        else:
            self.__effective_bg_color = None

        # Icon: own override or parent's effective
        own_icon = super().icon(recursive=False)
        if own_icon:
            self.__effective_icon = own_icon
        elif parent and hasattr(parent, 'effectiveIcon'):
            self.__effective_icon = parent.effectiveIcon()
        else:
            self.__effective_icon = ""

        # Font: own override or parent's effective
        own_font = super().font(recursive=False)
        if own_font:
            self.__effective_font = own_font
        elif parent and hasattr(parent, 'effectiveFont'):
            self.__effective_font = parent.effectiveFont()
        else:
            self.__effective_font = None

    def effectiveFgColor(self):
        """Return effective foreground color (single source of truth).

        This is either the own override or the parent's effective color.
        """
        return self.__effective_fg_color

    def effectiveBgColor(self):
        """Return effective background color (single source of truth).

        This is either the own override or the parent's effective color.
        """
        return self.__effective_bg_color

    def effectiveIcon(self):
        """Return effective icon (single source of truth).

        This is either the own override or the parent's effective icon.
        """
        return self.__effective_icon

    def effectiveFont(self):
        """Return effective font (single source of truth).

        This is either the own override or the parent's effective font.
        """
        return self.__effective_font

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
