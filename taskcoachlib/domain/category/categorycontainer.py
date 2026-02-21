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

from taskcoachlib.domain import base
from taskcoachlib import patterns


class CategoryList(base.Collection):
    @patterns.eventSource
    def extend(self, categories, event=None):
        super().extend(categories, event=event)
        for category in self._compositesAndAllChildren(categories):
            for categorizable in category.categorizables():
                categorizable.addCategory(category, event=event, modify=False)

    @patterns.eventSource
    def removeItems(self, categories, event=None):
        super().removeItems(categories, event=event)
        for category in self._compositesAndAllChildren(categories):
            for categorizable in category.categorizables():
                categorizable.removeCategory(category, event=event)

    def findCategoryByName(self, name):
        for category in self:
            recursive = " -> " in name
            if category.subject(recursive=recursive) == name:
                return category
        return None

    @property
    def has_category_filters(self):
        return bool(self.filteredCategories())

    def filteredCategories(self):
        return [category for category in self if category.isFiltered()]

    @patterns.eventSource
    def resetAllFilteredCategories(self, event=None):
        for category in self:
            category.setFiltered(False, event=event)
