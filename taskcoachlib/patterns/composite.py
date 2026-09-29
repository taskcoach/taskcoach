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

from . import observer
import weakref


class Composite(object):
    def __init__(self, children=None, parent=None):
        super().__init__()
        self.__parent = parent if parent is None else weakref.ref(parent)
        self.__children = children or []
        for child in self.__children:
            child.set_parent(self)

    def __getstate__(self):
        return dict(children=self.__children[:], parent=self.parent())

    def __setstate__(self, state):
        self.__parent = (
            None if state["parent"] is None else weakref.ref(state["parent"])
        )
        self.__children = state["children"]

    def __getcopystate__(self):
        """Return the information needed to create a copy as a dict."""
        try:
            state = super().__getcopystate__()
        except AttributeError:
            state = dict()
        state.update(
            dict(
                children=[child.copy() for child in self.__children],
                parent=self.parent(),
            )
        )
        return state

    def parent(self):
        return None if self.__parent is None else self.__parent()

    def ancestors(self):
        """Return the parent, and its parent, etc., as a list."""
        parent = self.parent()
        return parent.ancestors() + [parent] if parent else []

    def family(self):
        """Return this object, its ancestors and all of its children
        (recursively)."""
        return self.ancestors() + [self] + self.children(recursive=True)

    def set_parent(self, parent):
        self.__parent = None if parent is None else weakref.ref(parent)

    def children(self, recursive=False):
        # Warning: this must satisfy the same condition as
        # allItemsSorted() below.

        if recursive:
            result = self.__children[:]
            for child in self.__children:
                result.extend(child.children(recursive=True))
            return result
        else:
            return self.__children

    def siblings(self, recursive=False):
        parent = self.parent()
        if parent:
            result = [child for child in parent.children() if child != self]
            if recursive:
                for child in result[:]:
                    result.extend(child.children(recursive=True))
            return result
        else:
            return []

    def copy(self, *args, **kwargs):
        kwargs["parent"] = self.parent()
        kwargs["children"] = [child.copy() for child in self.children()]
        return self.__class__(*args, **kwargs)

    def newChild(self, *args, **kwargs):
        kwargs["parent"] = self
        return self.__class__(*args, **kwargs)

    def addChild(self, child):
        self.__children.append(child)
        child.set_parent(self)

    def removeChild(self, child):
        self.__children.remove(child)
        # We don't reset the parent of the child, because that makes restoring
        # the parent-child relationship easier.


class ObservableComposite(Composite):
    @observer.eventSource
    def __setstate__(self, state, event=None):  # pylint: disable=W0221
        oldChildren = set(self.children())
        super().__setstate__(state)
        newChildren = set(self.children())
        childrenRemoved = oldChildren - newChildren
        # pylint: disable=W0142
        if childrenRemoved:
            self.removeChildEvent(event, *childrenRemoved)
        childrenAdded = newChildren - oldChildren
        if childrenAdded:
            self.addChildEvent(event, *childrenAdded)

    @observer.eventSource
    def addChild(self, child, event=None):  # pylint: disable=W0221
        super().addChild(child)
        self.addChildEvent(event, child)

    def addChildEvent(self, event, *children):
        event.addSource(self, *children, **dict(type=self.addChildEventType()))

    @classmethod
    def addChildEventType(class_):
        return "composite(%s).child.add" % class_

    @observer.eventSource
    def removeChild(self, child, event=None):  # pylint: disable=W0221
        super().removeChild(child)
        self.removeChildEvent(event, child)

    def removeChildEvent(self, event, *children):
        event.addSource(
            self, *children, **dict(type=self.removeChildEventType())
        )

    @classmethod
    def removeChildEventType(class_):
        return "composite(%s).child.remove" % class_

    @classmethod
    def modificationEventTypes(class_):
        try:
            eventTypes = super(
                ObservableComposite, class_
            ).modificationEventTypes()
        except AttributeError:
            eventTypes = []
        return eventTypes + [
            class_.addChildEventType(),
            class_.removeChildEventType(),
        ]


class CompositeCollection(object):
    def __init__(self, initList=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extend(initList or [])

    def append(self, composite, event=None):
        return self.extend([composite], event=event)

    @observer.eventSource
    def extend(self, composites, event=None):
        if not composites:
            return
        compositesAndAllChildren = self._compositesAndAllChildren(composites)
        super().extend(compositesAndAllChildren, event=event)
        self._addCompositesToParent(composites, event)

    def _compositesAndAllChildren(self, composites):
        compositesAndAllChildren = set(composites)
        for composite in composites:
            compositesAndAllChildren |= set(composite.children(recursive=True))
        return list(compositesAndAllChildren)

    def _addCompositesToParent(self, composites, event):
        for composite in composites:
            parent = composite.parent()
            if (
                parent
                and parent in self
                and composite not in parent.children()
            ):
                parent.addChild(composite, event=event)

    def remove(self, composite, event=None):
        return (
            self.removeItems([composite], event=event)
            if composite in self
            else event
        )

    @observer.eventSource
    def removeItems(self, composites, event=None):
        if not composites:
            return
        compositesAndAllChildren = self._compositesAndAllChildren(composites)
        super().removeItems(compositesAndAllChildren, event=event)
        self._removeCompositesFromParent(composites, event)

    def _removeCompositesFromParent(self, composites, event):
        for composite in composites:
            parent = composite.parent()
            if parent:
                parent.removeChild(composite, event=event)

    def rootItems(self):
        return [
            composite
            for composite in self
            if composite.parent() is None or composite.parent() not in self
        ]

    def allItemsSorted(self):
        """Returns a list of items and their children, so that if B is
        a child, direct or not, of A, then A will come first in the
        list."""

        result = []
        for item in self.rootItems():
            result.append(item)
            result.extend(item.children(recursive=True))
        return result


class CompositeSet(CompositeCollection, observer.ObservableSet):
    pass


class CompositeList(CompositeCollection, observer.ObservableList):
    pass
