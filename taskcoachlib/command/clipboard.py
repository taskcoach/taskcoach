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


class Clipboard(metaclass=patterns.Singleton):
    def __init__(self):
        self.clear()

    def put(self, items, source, cut=False):
        # pylint: disable=W0201
        self._contents = items
        self._source = source
        # Cut items move: the first paste takes them, IDs included
        self._move_pending = cut

    def get(self):
        currentContents = self._contents
        currentSource = self._source
        return currentContents, currentSource

    def state(self):
        """What put() needs to restore the clipboard as it is."""
        return self._contents, self._source, self._move_pending

    def items_to_paste(self):
        """The items a paste inserts: the cut items themselves at the
        first paste after a cut, a move that keeps their IDs; copies,
        with new IDs, otherwise (docs/PERSISTENCE_XML.md, IDs)."""
        if self._move_pending:
            self._move_pending = False
            return list(self._contents)
        return [item.copy() for item in self._contents]

    def spend_move(self, items):
        """A redone paste inserts items again: a move of them, armed
        again by redoing their cut, is spent as at the first paste."""
        if len(items) == len(self._contents) and all(
            pasted is cut for pasted, cut in zip(items, self._contents)
        ):
            self._move_pending = False

    def peek(self):
        return self._contents

    def clear(self):
        self._contents = []
        self._source = None
        self._move_pending = False

    def __bool__(self):
        return len(self._contents) > 0
