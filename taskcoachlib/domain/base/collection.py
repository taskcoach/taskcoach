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
from taskcoachlib.patterns.snapshot import register_collection


class Collection(patterns.CompositeSet):
    """A list of the file's items: which items it holds is stored data
    (docs/UNDO_REDO.md, Architecture)."""

    def __init__(self, *args, **kwargs):
        register_collection(self)
        super().__init__(*args, **kwargs)

    def restore_items(self, added, removed, event=None):
        """Put the items back as a snapshot holds them: the items
        only, without their subitems or links, which are their
        fields."""
        if removed:
            patterns.ObservableSet.removeItems(self, removed, event=event)
        if added:
            patterns.ObservableSet.extend(self, added, event=event)

    def getObjectById(self, domainObjectId):
        for domainObject in self:
            if domainObjectId == domainObject.id():
                return domainObject
        raise IndexError
