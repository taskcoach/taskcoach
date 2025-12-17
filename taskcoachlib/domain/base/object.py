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
from taskcoachlib.domain.attribute import icon
from taskcoachlib.domain.date import DateTime, Now
from pubsub import pub
from . import attribute
import functools
import sys
import uuid
import re


class SynchronizedObject(object):
    STATUS_NONE = 0
    STATUS_NEW = 1
    STATUS_CHANGED = 2
    STATUS_DELETED = 3

    def __init__(self, *args, **kwargs):
        self.__status = kwargs.pop("status", self.STATUS_NEW)
        super().__init__(*args, **kwargs)

    @classmethod
    def markDeletedEventType(class_):
        return "object.markdeleted"

    @classmethod
    def markNotDeletedEventType(class_):
        return "object.marknotdeleted"

    def __getstate__(self):
        try:
            state = super().__getstate__()
        except AttributeError:
            state = dict()

        state["status"] = self.__status
        return state

    @patterns.eventSource
    def __setstate__(self, state, event=None):
        try:
            super().__setstate__(state, event=event)
        except AttributeError:
            pass
        if state["status"] != self.__status:
            if state["status"] == self.STATUS_CHANGED:
                self.markDirty(event=event)
            elif state["status"] == self.STATUS_DELETED:
                self.markDeleted(event=event)
            elif state["status"] == self.STATUS_NEW:
                self.markNew(event=event)
            elif state["status"] == self.STATUS_NONE:
                self.cleanDirty(event=event)

    def getStatus(self):
        return self.__status

    @patterns.eventSource
    def markDirty(self, force=False, event=None):
        if not self.setStatusDirty(force):
            return
        event.addSource(
            self, self.__status, type=self.markNotDeletedEventType()
        )

    def setStatusDirty(self, force=False):
        oldStatus = self.__status
        if self.__status == self.STATUS_NONE or force:
            self.__status = self.STATUS_CHANGED
            return oldStatus == self.STATUS_DELETED
        else:
            return False

    @patterns.eventSource
    def markNew(self, event=None):
        if not self.setStatusNew():
            return
        event.addSource(
            self, self.__status, type=self.markNotDeletedEventType()
        )

    def setStatusNew(self):
        oldStatus = self.__status
        self.__status = self.STATUS_NEW
        return oldStatus == self.STATUS_DELETED

    @patterns.eventSource
    def markDeleted(self, event=None):
        self.setStatusDeleted()
        event.addSource(self, self.__status, type=self.markDeletedEventType())

    def setStatusDeleted(self):
        self.__status = self.STATUS_DELETED

    @patterns.eventSource
    def cleanDirty(self, event=None):
        if not self.setStatusNone():
            return
        event.addSource(
            self, self.__status, type=self.markNotDeletedEventType()
        )

    def setStatusNone(self):
        oldStatus = self.__status
        self.__status = self.STATUS_NONE
        return oldStatus == self.STATUS_DELETED

    def isNew(self):
        return self.__status == self.STATUS_NEW

    def isModified(self):
        return self.__status == self.STATUS_CHANGED

    def isDeleted(self):
        return self.__status == self.STATUS_DELETED


@functools.total_ordering
class Object(SynchronizedObject):
    rx_attributes = re.compile(r"\[(\w+):(.+)\]")

    if sys.version_info.major == 2:
        _long_zero = int(0)
    else:
        _long_zero = 0

    def __init__(self, *args, **kwargs):
        Attribute = attribute.Attribute
        self.__creationDateTime = kwargs.pop("creationDateTime", None) or Now()
        self.__modificationDateTime = kwargs.pop(
            "modificationDateTime", DateTime.min
        )
        self.__subject = Attribute(
            kwargs.pop("subject", ""), self, self.subjectChangedEvent
        )
        self.__description = Attribute(
            kwargs.pop("description", ""), self, self.descriptionChangedEvent
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
        self.__icon = Attribute(
            kwargs.pop("icon", ""), self, self.appearanceChangedEvent
        )
        self.__selectedIcon = Attribute(
            kwargs.pop("selectedIcon", ""), self, self.appearanceChangedEvent
        )
        self.__ordering = Attribute(
            kwargs.pop("ordering", Object._long_zero),
            self,
            self.orderingChangedEvent,
        )
        self.__id = kwargs.pop("id", None) or str(uuid.uuid1())
        super().__init__(*args, **kwargs)

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

    def __getstate__(self):
        try:
            state = super().__getstate__()
        except AttributeError:
            state = dict()
        state.update(
            dict(
                id=self.__id,
                creationDateTime=self.__creationDateTime,
                modificationDateTime=self.__modificationDateTime,
                subject=self.__subject.get(),
                description=self.__description.get(),
                fgColor=self.__fgColor.get(),
                bgColor=self.__bgColor.get(),
                font=self.__font.get(),
                icon=self.__icon.get(),
                ordering=self.__ordering.get(),
                selectedIcon=self.__selectedIcon.get(),
            )
        )
        return state

    @patterns.eventSource
    def __setstate__(self, state, event=None):
        try:
            super().__setstate__(state, event=event)
        except AttributeError:
            pass
        self.__id = state["id"]
        self.setSubject(state["subject"], event=event)
        self.setDescription(state["description"], event=event)
        self.setForegroundColor(state["fgColor"], event=event)
        self.setBackgroundColor(state["bgColor"], event=event)
        self.setFont(state["font"], event=event)
        self.setIcon(state["icon"], event=event)
        self.setSelectedIcon(state["selectedIcon"], event=event)
        self.setOrdering(state["ordering"], event=event)
        self.__creationDateTime = state["creationDateTime"]
        # Set modification date/time last to overwrite changes made by the
        # setters above
        self.__modificationDateTime = state["modificationDateTime"]

    def __getcopystate__(self):
        """Return a dictionary that can be passed to __init__ when creating
        a copy of the object.

        E.g. copy = obj.__class__(**original.__getcopystate__())"""
        try:
            state = super().__getcopystate__()
        except AttributeError:
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
                icon=self.__icon.get(),
                selectedIcon=self.__selectedIcon.get(),
                ordering=self.__ordering.get(),
            )
        )
        return state

    def copy(self):
        return self.__class__(**self.__getcopystate__())

    @classmethod
    def monitoredAttributes(class_):
        return ["ordering", "subject", "description", "appearance"]

    # Id:

    def id(self):
        return self.__id

    # Custom attributes
    def customAttributes(self, sectionName):
        attributes = set()
        for line in self.description().split("\n"):
            match = self.rx_attributes.match(line.strip())
            if match and match.group(1) == sectionName:
                attributes.add(match.group(2))
        return attributes

    # Editing date/time:

    def creationDateTime(self):
        return self.__creationDateTime

    def modificationDateTime(self):
        return self.__modificationDateTime

    def setModificationDateTime(self, dateTime):
        self.__modificationDateTime = dateTime

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

    def subjectChangedEvent(self, event):
        event.addSource(
            self, self.subject(), type=self.subjectChangedEventType()
        )

    @classmethod
    def subjectChangedEventType(class_):
        return "%s.subject" % class_

    @staticmethod
    def subjectSortFunction(**kwargs):
        """Function to pass to list.sort when sorting by subject."""
        if kwargs.get("sortCaseSensitive", False):
            return lambda item: item.subject()
        else:
            return lambda item: item.subject().lower()

    @classmethod
    def subjectSortEventTypes(class_):
        """The event types that influence the subject sort order."""
        return (class_.subjectChangedEventType(),)

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
    def orderingChangedEventType(class_):
        return "%s.ordering" % class_

    @staticmethod
    def orderingSortFunction(**kwargs):
        return lambda item: item.ordering()

    @classmethod
    def orderingSortEventTypes(class_):
        return (class_.orderingChangedEventType(),)

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
    def descriptionChangedEventType(class_):
        return "%s.description" % class_

    @staticmethod
    def descriptionSortFunction(**kwargs):
        """Function to pass to list.sort when sorting by description."""
        if kwargs.get("sortCaseSensitive", False):
            return lambda item: item.description()
        else:
            return lambda item: item.description().lower()

    @classmethod
    def descriptionSortEventTypes(class_):
        """The event types that influence the description sort order."""
        return (class_.descriptionChangedEventType(),)

    # Color:

    def setForegroundColor(self, color, event=None):
        self.__fgColor.set(color, event=event)

    def foregroundColor(self, recursive=False):  # pylint: disable=W0613
        # The 'recursive' argument isn't actually used here, but some
        # code assumes composite objects where there aren't. This is
        # the simplest workaround.
        return self.__fgColor.get()

    def setBackgroundColor(self, color, event=None):
        self.__bgColor.set(color, event=event)

    def backgroundColor(self, recursive=False):  # pylint: disable=W0613
        # The 'recursive' argument isn't actually used here, but some
        # code assumes composite objects where there aren't. This is
        # the simplest workaround.
        return self.__bgColor.get()

    # Font:

    def font(self, recursive=False):  # pylint: disable=W0613
        # The 'recursive' argument isn't actually used here, but some
        # code assumes composite objects where there aren't. This is
        # the simplest workaround.
        return self.__font.get()

    def setFont(self, font, event=None):
        self.__font.set(font, event=event)

    # Icons:

    def icon(self):
        return self.__icon.get()

    def setIcon(self, icon, event=None):
        self.__icon.set(icon, event=event)

    def selectedIcon(self):
        return self.__selectedIcon.get()

    def setSelectedIcon(self, selectedIcon, event=None):
        self.__selectedIcon.set(selectedIcon, event=event)

    # Event types:

    @classmethod
    def appearanceChangedEventType(class_):
        return "%s.appearance" % class_

    def appearanceChangedEvent(self, event):
        event.addSource(self, type=self.appearanceChangedEventType())

    @classmethod
    def modificationEventTypes(class_):
        try:
            eventTypes = super(Object, class_).modificationEventTypes()
        except AttributeError:
            eventTypes = []
        return eventTypes + [
            class_.subjectChangedEventType(),
            class_.descriptionChangedEventType(),
            class_.appearanceChangedEventType(),
            class_.orderingChangedEventType(),
        ]


class CompositeObject(Object, patterns.ObservableComposite):
    def __init__(self, *args, **kwargs):
        self.__expandedContexts = set(kwargs.pop("expandedContexts", []))
        super().__init__(*args, **kwargs)

    def __getcopystate__(self):
        state = super().__getcopystate__()
        state.update(dict(expandedContexts=self.expandedContexts()))
        return state

    @classmethod
    def monitoredAttributes(class_):
        return Object.monitoredAttributes() + ["expandedContexts"]

    # Subject:

    def subject(self, recursive=False):  # pylint: disable=W0221
        subject = super().subject()
        if recursive and self.parent():
            subject = "%s -> %s" % (
                self.parent().subject(recursive=True),
                subject,
            )
        return subject

    def subjectChangedEvent(self, event):
        super().subjectChangedEvent(event)
        for child in self.children():
            child.subjectChangedEvent(event)

    @staticmethod
    def subjectSortFunction(**kwargs):
        """Function to pass to list.sort when sorting by subject."""
        recursive = kwargs.get("treeMode", False)
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
            pub.sendMessage(
                self.expansionChangedEventType(), newValue=expand, sender=self
            )

    @classmethod
    def expansionChangedEventType(cls):
        """The event type used for notifying changes in the expansion state
        of a composite object."""
        return "pubsub.%s.expandedContexts" % cls.__name__.lower()

    def expansionChangedEvent(self, event):
        event.addSource(self, type=self.expansionChangedEventType())

    # The ChangeMonitor expects this...
    @classmethod
    def expandedContextsChangedEventType(class_):
        return class_.expansionChangedEventType()

    # Appearance:

    def appearanceChangedEvent(self, event):
        super().appearanceChangedEvent(event)
        # Assume that most of the times our children change appearance too
        for child in self.children():
            child.appearanceChangedEvent(event)

    def foregroundColor(self, recursive=False):
        myFgColor = super().foregroundColor()
        if not myFgColor and recursive and self.parent():
            return self.parent().foregroundColor(recursive=True)
        else:
            return myFgColor

    def backgroundColor(self, recursive=False):
        myBgColor = super().backgroundColor()
        if not myBgColor and recursive and self.parent():
            return self.parent().backgroundColor(recursive=True)
        else:
            return myBgColor

    def font(self, recursive=False):
        myFont = super().font()
        if not myFont and recursive and self.parent():
            return self.parent().font(recursive=True)
        else:
            return myFont

    def icon(self, recursive=False):
        myIcon = super().icon()
        if not recursive:
            return myIcon
        if not myIcon and self.parent():
            myIcon = self.parent().icon(recursive=True)
        return self.pluralOrSingularIcon(myIcon, native=super().icon() == "")

    def selectedIcon(self, recursive=False):
        myIcon = super().selectedIcon()
        if not recursive:
            return myIcon
        if not myIcon and self.parent():
            myIcon = self.parent().selectedIcon(recursive=True)
        return self.pluralOrSingularIcon(
            myIcon, native=super().selectedIcon() == ""
        )

    def pluralOrSingularIcon(self, myIcon, native=True):
        hasChildren = any(
            child for child in self.children() if not child.isDeleted()
        )
        mapping = (
            icon.itemImagePlural if hasChildren else icon.itemImageSingular
        )
        # If the icon comes from the user settings, only pluralize it; this is probably
        # the Way of the Least Astonishment
        if native or hasChildren:
            return mapping.get(myIcon, myIcon)
        return myIcon

    # Event types:

    @classmethod
    def modificationEventTypes(class_):
        return super(CompositeObject, class_).modificationEventTypes() + [
            class_.expansionChangedEventType()
        ]

    # Override SynchronizedObject methods to also mark child objects

    @patterns.eventSource
    def markDeleted(self, event=None):
        super().markDeleted(event=event)
        for child in self.children():
            child.markDeleted(event=event)

    @patterns.eventSource
    def markNew(self, event=None):
        super().markNew(event=event)
        for child in self.children():
            child.markNew(event=event)

    @patterns.eventSource
    def markDirty(self, force=False, event=None):
        super().markDirty(force, event=event)
        for child in self.children():
            child.markDirty(force, event=event)

    @patterns.eventSource
    def cleanDirty(self, event=None):
        super().cleanDirty(event=event)
        for child in self.children():
            child.cleanDirty(event=event)
