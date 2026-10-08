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
from taskcoachlib.domain.date import Timestamp
from taskcoachlib.patterns.snapshot import is_restoring, register_item
from taskcoachlib.tools import text
from . import attribute
from .appearance import FIELD_DEFAULTS, FIELD_NO_VALUE_SOURCE, shown
import functools
import uuid
import re


def new_id():
    """A new item's ID: a random UUID (version 4) from the operating
    system's cryptographic source, no machine data
    (docs/PERSISTENCE_XML.md, IDs)."""
    return str(uuid.uuid4())


@functools.total_ordering
class Object:
    rx_attributes = re.compile(r"\[(\w+):(.+)\]")

    _long_zero = 0

    def __init__(self, *args, **kwargs):
        Attribute = attribute.Attribute
        self.__creationDateTime = (
            kwargs.pop("creationDateTime", None) or Timestamp.now()
        )
        # A new item was last modified when it was created. The date
        # itself dates nothing
        self.__modificationDateTime = Attribute(
            kwargs.pop("modificationDateTime", None)
            or self.__creationDateTime,
            self,
            self._on_modification_datetime_changed,
            dates=False,
        )
        self.__subject = Attribute(
            kwargs.pop("subject", ""),
            self,
            self.subject_changed_event,
            normalize=text.single_line,
        )
        self.__description = Attribute(
            kwargs.pop("description", ""),
            self,
            self.descriptionChangedEvent,
            normalize=text.multi_line,
        )
        self.__fgColor = Attribute(
            kwargs.pop("fgColor", None), self, self.appearanceChangedEvent
        )
        self.__bgColor = Attribute(
            kwargs.pop("bgColor", None), self, self.appearanceChangedEvent
        )
        self.__font = Attribute(
            kwargs.pop("font", None), self, self.appearanceChangedEvent
        )
        from taskcoachlib.gui.icons.icon_library import icon_catalog

        self.__icon_id = Attribute(
            icon_catalog.normalize_icon_id(kwargs.pop("icon", "")),
            self,
            self.appearanceChangedEvent,
        )
        self.__ordering = Attribute(
            kwargs.pop("ordering", Object._long_zero),
            self,
            self.orderingChangedEvent,
        )
        self.__id = kwargs.pop("id", None) or new_id()

        # Derived SSOT fields (value + source for each appearance type)
        self.__derivedFgColorValue = Attribute(
            None, self, self._on_derived_fg_color_changed, volatile=True
        )
        self.__derivedFgColorSource = Attribute(
            None, self, self._on_derived_fg_color_changed, volatile=True
        )
        self.__derivedBgColorValue = Attribute(
            None, self, self._on_derived_bg_color_changed, volatile=True
        )
        self.__derivedBgColorSource = Attribute(
            None, self, self._on_derived_bg_color_changed, volatile=True
        )
        self.__derivedIconValue = Attribute(
            None, self, self._on_derived_icon_changed, volatile=True
        )
        self.__derivedIconSource = Attribute(
            None, self, self._on_derived_icon_changed, volatile=True
        )
        self.__derivedFontValue = Attribute(
            None, self, self._on_derived_font_changed, volatile=True
        )
        self.__derivedFontSource = Attribute(
            None, self, self._on_derived_font_changed, volatile=True
        )

        # Effective SSOT fields (value + source + default for colors/font, value + source for icon)
        self.__effectiveFgColorValue = Attribute(
            None, self, self._on_effective_fg_color_changed, volatile=True
        )
        self.__effectiveFgColorSource = Attribute(
            None, self, self._on_effective_fg_color_changed, volatile=True
        )
        self.__effectiveFgColorDefault = Attribute(
            None, self, self._on_effective_fg_color_changed, volatile=True
        )
        self.__effectiveBgColorValue = Attribute(
            None, self, self._on_effective_bg_color_changed, volatile=True
        )
        self.__effectiveBgColorSource = Attribute(
            None, self, self._on_effective_bg_color_changed, volatile=True
        )
        self.__effectiveBgColorDefault = Attribute(
            None, self, self._on_effective_bg_color_changed, volatile=True
        )
        self.__effectiveIconValue = Attribute(
            None, self, self._on_effective_icon_changed, volatile=True
        )
        self.__effectiveIconSource = Attribute(
            None, self, self._on_effective_icon_changed, volatile=True
        )
        self.__effectiveFontValue = Attribute(
            None, self, self._on_effective_font_changed, volatile=True
        )
        self.__effectiveFontSource = Attribute(
            None, self, self._on_effective_font_changed, volatile=True
        )
        self.__effectiveFontDefault = Attribute(
            None, self, self._on_effective_font_changed, volatile=True
        )

        super().__init__(*args, **kwargs)
        # Its stored fields are in the undo log's snapshots
        register_item(self)

    def __repr__(self):
        return self.subject()

    def __eq__(self, other):
        if not isinstance(other, Object):
            return NotImplemented
        return self.id() == other.id()

    def __lt__(self, other):
        if not isinstance(other, Object):
            return NotImplemented
        return self.id() < other.id()

    def __hash__(self):
        return hash(self.id())

    def __getcopystate__(self):
        """Return a dictionary that can be passed to __init__ when creating
        a copy of the object.

        E.g. copy = obj.__class__(**original.__getcopystate__())"""
        # Only invoke super if another class in the MRO provides it
        if hasattr(super(), "__getcopystate__"):
            state = super().__getcopystate__()
        else:
            state = dict()
        # Note that we don't put the id and the creation date/time in the state
        # dict, because a copy should get a new id and a new creation date/time
        state.update(
            dict(
                subject=self.__subject.get(),
                description=self.__description.get(),
                fgColor=self.__fgColor.get(),
                bgColor=self.__bgColor.get(),
                font=self.__font.get(),
                icon=self.__icon_id.get(),
                ordering=self.__ordering.get(),
            )
        )
        return state

    def copy(self):
        state = self.__getcopystate__()
        return self.__class__(**state)

    # Id:

    def id(self):
        return self.__id

    # Custom attributes
    def customAttributes(self, section_name):
        attributes = set()
        for line in self.description().split("\n"):
            match = self.rx_attributes.match(line.strip())
            if match and match.group(1) == section_name:
                attributes.add(match.group(2))
        return attributes

    # Editing date/time:

    def creationDateTime(self):
        return self.__creationDateTime

    def modificationDateTime(self):
        return self.__modificationDateTime.get()

    def set_modification_datetime(self, date_time, event=None):
        """Set by the stored fields' Attributes when they change, and
        restored from the file when loading."""
        self.__modificationDateTime.set(date_time, event=event)

    def modified_now(self, event=None):
        """A stored field changed: the item is dated now, except while
        values are put back (undo, redo, merging), which edits
        nothing."""
        if not is_restoring():
            self.set_modification_datetime(Timestamp.now(), event=event)

    def _on_modification_datetime_changed(self, event):
        event.addSource(
            self,
            self.modificationDateTime(),
            type=self.modification_datetime_changed_event_type(),
        )

    @classmethod
    def modification_datetime_changed_event_type(cls):
        """Not a stored field's change: it does not mark the file
        unsaved."""
        return "%s.modificationDateTime" % cls

    @classmethod
    def modificationDateTimeSortEventTypes(cls):
        # Found by name, from the sort key
        # (Sorter._get_sort_event_types)
        return (cls.modification_datetime_changed_event_type(),)

    @staticmethod
    def modificationDateTimeSortFunction(**kwargs):
        return lambda item: item.modificationDateTime()

    @staticmethod
    def creationDateTimeSortFunction(**kwargs):
        return lambda item: item.creationDateTime()

    # Subject:

    def subject(self):
        return self.__subject.get()

    def setSubject(self, subject, event=None):
        self.__subject.set(subject, event=event)

    def subject_changed_event(self, event):
        event.addSource(
            self, self.subject(), type=self.subjectChangedEventType()
        )

    @classmethod
    def subjectChangedEventType(cls):
        return "%s.subject" % cls

    @staticmethod
    def subjectSortFunction(**kwargs):
        """Function to pass to list.sort when sorting by subject."""
        if kwargs.get("sortCaseSensitive", False):
            return lambda item: item.subject()
        else:
            return lambda item: item.subject().lower()

    @classmethod
    def subjectSortEventTypes(cls):
        """The event types that influence the subject sort order."""
        return (cls.subjectChangedEventType(),)

    # Ordering:

    def ordering(self):
        return self.__ordering.get()

    def setOrdering(self, ordering, event=None):
        self.__ordering.set(ordering, event=event)

    def orderingChangedEvent(self, event):
        event.addSource(
            self, self.ordering(), type=self.orderingChangedEventType()
        )

    @classmethod
    def orderingChangedEventType(cls):
        return "%s.ordering" % cls

    @staticmethod
    def orderingSortFunction(**kwargs):
        return lambda item: item.ordering()

    @classmethod
    def orderingSortEventTypes(cls):
        return (cls.orderingChangedEventType(),)

    # Description:

    def description(self):
        return self.__description.get()

    def setDescription(self, description, event=None):
        self.__description.set(description, event=event)

    def descriptionChangedEvent(self, event):
        event.addSource(
            self, self.description(), type=self.descriptionChangedEventType()
        )

    @classmethod
    def descriptionChangedEventType(cls):
        return "%s.description" % cls

    @staticmethod
    def descriptionSortFunction(**kwargs):
        """Function to pass to list.sort when sorting by description."""
        if kwargs.get("sortCaseSensitive", False):
            return lambda item: item.description()
        else:
            return lambda item: item.description().lower()

    @classmethod
    def descriptionSortEventTypes(cls):
        """The event types that influence the description sort order."""
        return (cls.descriptionChangedEventType(),)

    # Color:

    def setForegroundColor(self, color, event=None):
        self.__fgColor.set(color, event=event)

    def foregroundColor(self):
        return self.__fgColor.get()

    def setBackgroundColor(self, color, event=None):
        self.__bgColor.set(color, event=event)

    def backgroundColor(self):
        return self.__bgColor.get()

    # Font:

    def font(self):
        return self.__font.get()

    def setFont(self, font, event=None):
        self.__font.set(font, event=event)

    # Icons:

    def icon_id(self):
        return self.__icon_id.get()

    def set_icon_id(self, icon_id, event=None):
        from taskcoachlib.gui.icons.icon_library import icon_catalog

        self.__icon_id.set(
            icon_catalog.normalize_icon_id(icon_id), event=event
        )

    # Event types:

    @classmethod
    def appearanceChangedEventType(cls):
        return "%s.appearance" % cls

    def appearanceChangedEvent(self, event):
        event.addSource(self, type=self.appearanceChangedEventType())
        # What the item shows follows at once, when set and when undo
        # or redo puts a style back
        from . import appearance

        for field_type in appearance.FIELD_TYPES:
            appearance.compute_effective(self, field_type)

    # --- Derived SSOT Getters ---

    def derivedFgColor(self):
        return self.__derivedFgColorValue.get() or FIELD_DEFAULTS["fgColor"]

    def derivedFgColorSource(self):
        return (
            self.__derivedFgColorSource.get()
            or FIELD_NO_VALUE_SOURCE["fgColor"]
        )

    def derivedBgColor(self):
        return self.__derivedBgColorValue.get() or FIELD_DEFAULTS["bgColor"]

    def derivedBgColorSource(self):
        return (
            self.__derivedBgColorSource.get()
            or FIELD_NO_VALUE_SOURCE["bgColor"]
        )

    def derivedIcon(self):
        return self.__derivedIconValue.get() or FIELD_DEFAULTS["icon"]

    def derivedIconSource(self):
        return self.__derivedIconSource.get() or FIELD_NO_VALUE_SOURCE["icon"]

    def derivedFont(self):
        return self.__derivedFontValue.get() or FIELD_DEFAULTS["font"]

    def derivedFontSource(self):
        return self.__derivedFontSource.get() or FIELD_NO_VALUE_SOURCE["font"]

    # --- Derived SSOT Setters (for use by compute_derived) ---
    # Each sends one event for its value and source together

    @patterns.computed_event_source
    def setDerivedFgColor(self, value, source, event=None):
        self.__derivedFgColorValue.set(value, event=event)
        self.__derivedFgColorSource.set(source, event=event)

    @patterns.computed_event_source
    def setDerivedBgColor(self, value, source, event=None):
        self.__derivedBgColorValue.set(value, event=event)
        self.__derivedBgColorSource.set(source, event=event)

    @patterns.computed_event_source
    def setDerivedIcon(self, value, source, event=None):
        self.__derivedIconValue.set(value, event=event)
        self.__derivedIconSource.set(source, event=event)

    @patterns.computed_event_source
    def setDerivedFont(self, value, source, event=None):
        self.__derivedFontValue.set(value, event=event)
        self.__derivedFontSource.set(source, event=event)

    # --- Derived Event Handlers ---

    def _on_derived_fg_color_changed(self, event):
        event.addSource(self, type=self.derivedFgColorChangedEventType())

    def _on_derived_bg_color_changed(self, event):
        event.addSource(self, type=self.derivedBgColorChangedEventType())

    def _on_derived_icon_changed(self, event):
        event.addSource(self, type=self.derivedIconChangedEventType())

    def _on_derived_font_changed(self, event):
        event.addSource(self, type=self.derivedFontChangedEventType())

    # --- Derived Event Types ---

    @classmethod
    def derivedFgColorChangedEventType(cls):
        return "derived.fgColor"

    @classmethod
    def derivedBgColorChangedEventType(cls):
        return "derived.bgColor"

    @classmethod
    def derivedIconChangedEventType(cls):
        return "derived.icon"

    @classmethod
    def derivedFontChangedEventType(cls):
        return "derived.font"

    # --- Effective SSOT Getters ---

    def effectiveFgColor(self):
        return self.__effectiveFgColorValue.get() or FIELD_DEFAULTS["fgColor"]

    def effectiveFgColorSource(self):
        return (
            self.__effectiveFgColorSource.get()
            or FIELD_NO_VALUE_SOURCE["fgColor"]
        )

    def effectiveFgColorDefault(self):
        return (
            self.__effectiveFgColorDefault.get() or FIELD_DEFAULTS["fgColor"]
        )

    def effectiveBgColor(self):
        return self.__effectiveBgColorValue.get() or FIELD_DEFAULTS["bgColor"]

    def effectiveBgColorSource(self):
        return (
            self.__effectiveBgColorSource.get()
            or FIELD_NO_VALUE_SOURCE["bgColor"]
        )

    def effectiveBgColorDefault(self):
        return (
            self.__effectiveBgColorDefault.get() or FIELD_DEFAULTS["bgColor"]
        )

    def effectiveIcon(self):
        return self.__effectiveIconValue.get() or FIELD_DEFAULTS["icon"]

    def effectiveIconSource(self):
        return (
            self.__effectiveIconSource.get() or FIELD_NO_VALUE_SOURCE["icon"]
        )

    def effectiveFont(self):
        return self.__effectiveFontValue.get() or FIELD_DEFAULTS["font"]

    def effectiveFontSource(self):
        return (
            self.__effectiveFontSource.get() or FIELD_NO_VALUE_SOURCE["font"]
        )

    def effectiveFontDefault(self):
        return self.__effectiveFontDefault.get() or FIELD_DEFAULTS["font"]

    # --- Shown styles: what every view draws, the effective styles the
    # master loop computes (docs/MASTER_SCHEDULER_REFACTOR.md, To Do 35)

    def shown_fg_color(self):
        return shown(self.effectiveFgColor())

    def shown_bg_color(self):
        return shown(self.effectiveBgColor())

    def shown_font(self):
        return shown(self.effectiveFont())

    def shown_icon_id(self):
        return self.effectiveIcon()

    # --- Effective SSOT Setters (for use by compute_effective) ---
    # Each sends one event for its value, default and source together

    @patterns.computed_event_source
    def setEffectiveFgColor(self, value, default, source, event=None):
        self.__effectiveFgColorValue.set(value, event=event)
        self.__effectiveFgColorDefault.set(default, event=event)
        self.__effectiveFgColorSource.set(source, event=event)

    @patterns.computed_event_source
    def setEffectiveBgColor(self, value, default, source, event=None):
        self.__effectiveBgColorValue.set(value, event=event)
        self.__effectiveBgColorDefault.set(default, event=event)
        self.__effectiveBgColorSource.set(source, event=event)

    @patterns.computed_event_source
    def setEffectiveIcon(self, value, source, event=None):
        # Icon has no default
        self.__effectiveIconValue.set(value, event=event)
        self.__effectiveIconSource.set(source, event=event)

    @patterns.computed_event_source
    def setEffectiveFont(self, value, default, source, event=None):
        self.__effectiveFontValue.set(value, event=event)
        self.__effectiveFontDefault.set(default, event=event)
        self.__effectiveFontSource.set(source, event=event)

    # --- Effective Event Handlers ---

    def _on_effective_fg_color_changed(self, event):
        event.addSource(self, type=self.effectiveFgColorChangedEventType())

    def _on_effective_bg_color_changed(self, event):
        event.addSource(self, type=self.effectiveBgColorChangedEventType())

    def _on_effective_icon_changed(self, event):
        event.addSource(self, type=self.effectiveIconChangedEventType())

    def _on_effective_font_changed(self, event):
        event.addSource(self, type=self.effectiveFontChangedEventType())

    # --- Effective Event Types ---

    @classmethod
    def effectiveFgColorChangedEventType(cls):
        return "effective.fgColor"

    @classmethod
    def effectiveBgColorChangedEventType(cls):
        return "effective.bgColor"

    @classmethod
    def effectiveIconChangedEventType(cls):
        return "effective.icon"

    @classmethod
    def effectiveFontChangedEventType(cls):
        return "effective.font"

    @classmethod
    def effective_style_event_types(cls):
        """The events of the styles the views draw."""
        return (
            cls.effectiveFgColorChangedEventType(),
            cls.effectiveBgColorChangedEventType(),
            cls.effectiveFontChangedEventType(),
            cls.effectiveIconChangedEventType(),
        )

    @classmethod
    def modificationEventTypes(cls):
        # Only invoke super if another class in the MRO provides it
        parent = super(Object, cls)
        if hasattr(parent, "modificationEventTypes"):
            event_types = parent.modificationEventTypes()
        else:
            event_types = []
        return event_types + [
            cls.subjectChangedEventType(),
            cls.descriptionChangedEventType(),
            cls.appearanceChangedEventType(),
            cls.orderingChangedEventType(),
        ]


class CompositeObject(Object, patterns.ObservableComposite):
    def __init__(self, *args, **kwargs):
        self.__expandedContexts = set(kwargs.pop("expandedContexts", []))
        super().__init__(*args, **kwargs)

    def set_parent(self, parent):
        # The item's own link; its parent's children are the reverse.
        # Changing it sets the item's date (docs/ATTRIBUTE_PATTERN.md,
        # Modification Date)
        changed = parent is not self.parent()
        super().set_parent(parent)
        if changed:
            self.modified_now()

    def __getcopystate__(self):
        state = super().__getcopystate__()
        state.update(dict(expandedContexts=self.expandedContexts()))
        return state

    # Subject:

    def subject(self, recursive=False):  # pylint: disable=W0221
        subject = super().subject()
        if recursive and self.parent():
            subject = "%s -> %s" % (
                self.parent().subject(recursive=True),
                subject,
            )
        return subject

    def subject_changed_event(self, event):
        super().subject_changed_event(event)
        for child in self.children():
            child.subject_changed_event(event)

    @staticmethod
    def subjectSortFunction(**kwargs):
        """Function to pass to list.sort when sorting by subject."""
        recursive = kwargs.get("tree_mode", False)
        if kwargs.get("sortCaseSensitive", False):
            return lambda item: item.subject(recursive=recursive)
        else:
            return lambda item: item.subject(recursive=recursive).lower()

    # Description:

    def description(self, recursive=False):  # pylint: disable=W0221,W0613
        # Allow for the recursive flag, but ignore it
        return super().description()

    # Expansion state:

    # Note: expansion state is stored by context. A context is a simple string
    # identifier (without comma's) to distinguish between different contexts,
    # i.e. viewers. A composite object may be expanded in one context and
    # collapsed in another.

    def isExpanded(self, context="None"):
        """Returns a boolean indicating whether the composite object is
        expanded in the specified context."""
        return context in self.__expandedContexts

    def expandedContexts(self):
        """Returns a list of contexts where this composite object is
        expanded."""
        return list(self.__expandedContexts)

    def expand(self, expand=True, context="None", notify=True):
        """Expands (or collapses) the composite object in the specified
        context."""
        if expand == self.isExpanded(context):
            return
        if expand:
            self.__expandedContexts.add(context)
        else:
            self.__expandedContexts.discard(context)
        if notify:
            patterns.Event(
                self.expansionChangedEventType(), self, expand
            ).send()

    @classmethod
    def expansionChangedEventType(cls):
        """The event type used for notifying changes in the expansion state
        of a composite object."""
        return "%s.expandedContexts" % cls.__name__.lower()

    # Event types:

    @classmethod
    def modificationEventTypes(cls):
        return super(CompositeObject, cls).modificationEventTypes() + [
            cls.expansionChangedEventType()
        ]
