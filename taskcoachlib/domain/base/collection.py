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


class Collection(patterns.CompositeSet):
    def restore_items(self, added, removed, event=None):
        """Put the items back as a snapshot holds them: the items
        only, without their subitems or links, which are their fields.
        For the task file's lists (docs/UNDO_REDO.md, Architecture)."""
        if removed:
            patterns.ObservableSet.removeItems(self, removed, event=event)
        if added:
            patterns.ObservableSet.extend(self, added, event=event)

    def getObjectById(self, domain_object_id):
        for domain_object in self:
            if domain_object_id == domain_object.id():
                return domain_object
        raise IndexError
