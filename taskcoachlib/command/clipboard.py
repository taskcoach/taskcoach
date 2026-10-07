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
from taskcoachlib.patterns.snapshot import held_item, is_held


def _with_subitems(item):
    """The item and its subitems, if it has any, in order."""
    children = getattr(item, "children", None)
    return [item] + (children(recursive=True) if children else [])


def copies_of(items):
    """Copies of the items, subtasks included. A copied task keeps its
    original's prerequisites: those copied with it as their copies,
    the others as they are (GitHub #169)."""
    copies = [item.copy() for item in items]
    pairs = {}
    for original, copy in zip(items, copies):
        pairs.update(zip(_with_subitems(original), _with_subitems(copy)))
    for original, copy in pairs.items():
        if hasattr(original, "prerequisites"):  # Tasks only
            copy.set_prerequisites(
                {pairs.get(each, each) for each in original.prerequisites()}
            )
    return copies


def link_pasted(items):
    """Link the pasted tasks to their prerequisites, the file's own
    items: whatever a view shows, and also when the file was closed
    and opened again since the copy. One deleted since, or in another
    file, is dropped."""
    for item in items:
        for each in _with_subitems(item):
            if not hasattr(each, "prerequisites"):
                continue
            pairs = [(p, held_item(p)) for p in each.prerequisites()]
            stale = {p for p, held in pairs if held is not p}
            if stale:
                # Items compare by ID: the old one out, the file's in
                each.remove_prerequisites(stale)
                each.add_prerequisites(
                    {
                        held
                        for p, held in pairs
                        if held is not None and held is not p
                    }
                )
            each.addTaskAsDependencyOf(
                {held for p, held in pairs if held is not None}
            )


class Clipboard(metaclass=patterns.Singleton):
    def __init__(self):
        self.clear()

    def put(self, items, source, cut=False):
        # pylint: disable=W0201
        self._contents = items
        self._source = source
        self._cut = cut

    def get(self):
        current_contents = self._contents
        current_source = self._source
        return current_contents, current_source

    def items_to_paste(self):
        """The items a paste inserts: cut items themselves while the
        file does not hold them, a move that keeps their IDs; copies,
        with new IDs, otherwise (docs/PERSISTENCE_XML.md, IDs;
        docs/UNDO_REDO.md, Design Intent)."""
        if self._cut and not any(is_held(item) for item in self._contents):
            return list(self._contents)
        return copies_of(self._contents)

    def peek(self):
        return self._contents

    def clear(self):
        self._contents = []
        self._source = None
        self._cut = False

    def __bool__(self):
        return len(self._contents) > 0
