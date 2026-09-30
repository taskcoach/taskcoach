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

Snapshots of the stored data and steps, what an action changed: the
undo log's one mechanism (docs/UNDO_REDO.md, Architecture).
"""

import collections
import contextlib
import weakref

from .field import ListField, fields
from .observer import Event

# Every live item and every live list of the file, by identity: items
# compare equal by ID, and a merge's copy shares its original's
_items = weakref.WeakValueDictionary()
_collections = weakref.WeakValueDictionary()

_restoring = 0


def register_item(item):
    _items[id(item)] = item


def register_collection(collection):
    """A list of the file's items, such as its tasks: which items it
    holds is stored data. It puts them back with
    restore_items(added, removed, event)."""
    _collections[id(collection)] = collection


@contextlib.contextmanager
def restoring():
    """While active, stored values are put in place, as loading a file
    does: by undo, redo and merging. That edits nothing, so no edit rule
    runs, and no command does anything."""
    global _restoring  # pylint: disable=W0603
    _restoring += 1
    try:
        yield
    finally:
        _restoring -= 1


def is_restoring():
    return _restoring > 0


def is_held(item):
    """Whether the file holds the item: a list of the file, or another
    item's list field (its parent's subitems, its owner's notes)."""
    if any(item in collection for collection in list(_collections.values())):
        return True
    for other in list(_items.values()):
        for field in fields(other).values():
            if isinstance(field, ListField) and any(
                each is item for each in field.get()
            ):
                return True
    return False


class Snapshot:
    """Every live item's stored fields, and every file list's items."""

    def __init__(self):
        self.items = {}  # id(item): (item, {field name: value})
        for item in list(_items.values()):
            self.items[id(item)] = (
                item,
                {
                    name: field.snapshot()
                    for name, field in fields(item).items()
                },
            )
        self.members = {}  # id(collection): (collection, {id(item): item})
        for collection in list(_collections.values()):
            self.members[id(collection)] = (
                collection,
                {id(item): item for item in collection},
            )


class Step:
    """What an action changed, from the snapshots taken before and after
    it: undo writes the values before back, redo the values after."""

    def __init__(self, label, before, after):
        self.label = label
        self.changes = []  # (item, field name, value before, value after)
        for key, (item, values) in after.items.items():
            earlier = before.items.get(key)
            if earlier is None or earlier[0] is not item:
                continue  # New: out of the file after undo
            item_fields = fields(item)
            for name, value in values.items():
                old = earlier[1].get(name)
                if not item_fields[name].same(old, value):
                    self.changes.append((item, name, old, value))
        self.members = []  # (collection, added items, removed items)
        for key, (collection, items) in after.members.items():
            earlier = before.members.get(key, (collection, {}))[1]
            added = [item for k, item in items.items() if k not in earlier]
            removed = [item for k, item in earlier.items() if k not in items]
            if added or removed:
                self.members.append((collection, added, removed))

    def __bool__(self):
        return bool(self.changes or self.members)

    def __str__(self):
        return self.label

    def summary(self):
        """What the step changed, for the log: field names with their
        counts, and list changes."""
        counts = collections.Counter(
            name.rsplit("__", 1)[-1]
            for _item, name, _old, _new in self.changes
        )
        fields_changed = ", ".join(
            "%s x%d" % each for each in sorted(counts.items())
        )
        return "%r: %s; %d list(s)" % (
            self.label,
            fields_changed or "no field",
            len(self.members),
        )

    def undo(self):
        self.__put_back(undo=True)

    def redo(self):
        self.__put_back(undo=False)

    def __put_back(self, undo):
        event = Event()
        with restoring():
            for collection, added, removed in self.members:
                if undo:
                    added, removed = removed, added
                collection.restore_items(added, removed, event=event)
            changes = reversed(self.changes) if undo else self.changes
            for item, name, before, after in changes:
                fields(item)[name].restore(
                    before if undo else after, event=event
                )
            # Views react to it while nothing can be done
            event.send()
