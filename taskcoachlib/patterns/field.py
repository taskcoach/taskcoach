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

import weakref


class Field:
    """A stored value of an item: what a snapshot reads and undo puts
    back (docs/UNDO_REDO.md, Architecture). A computed value is not
    stored."""

    __slots__ = ()

    stored = True

    def snapshot(self):
        """A copy of the value, which later changes leave as it is."""
        raise NotImplementedError

    def restore(self, value, event=None):
        """Put the value back and tell the views, without dating the
        item: the snapshot holds its date."""
        raise NotImplementedError

    @staticmethod
    def same(value, other):
        """Whether two snapshots of the field hold the same value."""
        return value == other


def fields(item):
    """The item's stored fields, by name."""
    return {
        name: value
        for name, value in vars(item).items()
        if isinstance(value, Field) and value.stored
    }


class ListField(Field):
    """An ordered list of items, such as a parent's subitems. Its owner
    changes it in place and tells the views; a restore calls the
    owner's changed(added, removed, event=...)."""

    __slots__ = ("__values", "__owner", "__changed")

    def __init__(self, values, owner, changed=None):
        self.__values = list(values or [])
        self.__owner = weakref.ref(owner)
        self.__changed = None if changed is None else changed.__func__

    def get(self):
        """The list itself, which the owner changes in place."""
        return self.__values

    def snapshot(self):
        return tuple(self.__values)

    @staticmethod
    def same(values, others):
        # Items compare equal by ID: a copy is another item
        return len(values) == len(others) and all(
            value is other for value, other in zip(values, others)
        )

    def restore(self, values, event=None):
        if list(values) == self.__values and all(
            new is old for new, old in zip(values, self.__values)
        ):
            return
        old = {id(value) for value in self.__values}
        new = {id(value) for value in values}
        added = [value for value in values if id(value) not in old]
        removed = [value for value in self.__values if id(value) not in new]
        self.__values[:] = values
        owner = self.__owner()
        if self.__changed and owner is not None:
            self.__changed(owner, added, removed, event=event)


class LinkField(Field):
    """A link to another item, such as a subitem's parent, held weakly;
    a restore calls the owner's changed(event=...)."""

    __slots__ = ("__target", "__owner", "__changed")

    def __init__(self, target, owner, changed=None):
        self.__target = None
        self.__owner = weakref.ref(owner)
        self.__changed = None if changed is None else changed.__func__
        self.set(target)

    def get(self):
        return None if self.__target is None else self.__target()

    def set(self, target):
        self.__target = None if target is None else weakref.ref(target)

    def snapshot(self):
        return self.get()

    @staticmethod
    def same(target, other):
        return target is other

    def restore(self, target, event=None):
        if target is self.get():
            return
        self.set(target)
        owner = self.__owner()
        if self.__changed and owner is not None:
            self.__changed(owner, event=event)
