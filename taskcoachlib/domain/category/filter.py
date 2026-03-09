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
from taskcoachlib.domain import base
from .category import Category


class CategoryFilter(base.Filter):
    def __init__(self, *args, **kwargs):
        self.__categories = kwargs.pop("categories")
        self.__settings = kwargs.pop("settings")
        self.__filterOnlyWhenAllCategoriesMatch = kwargs.pop(
            "filterOnlyWhenAllCategoriesMatch", False
        )
        for event_type in (
            self.__categories.addItemEventType(),
            self.__categories.removeItemEventType(),
        ):
            patterns.Publisher().registerObserver(
                self.onCategoryChanged,
                eventType=event_type,
                eventSource=self.__categories,
            )
        event_types = (
            Category.categorizableAddedEventType(),
            Category.categorizableRemovedEventType(),
            Category.filterChangedEventType(),
        )
        for event_type in event_types:
            patterns.Publisher().registerObserver(
                self.onCategoryChanged, eventType=event_type
            )
        patterns.Publisher().registerObserver(
            self.onFilterMatchingChanged,
            eventType="view.categoryfiltermatchall",
            eventSource=self.__settings,
        )
        super().__init__(*args, **kwargs)

    def detach(self):
        super().detach()
        self.removeObserver(self.onCategoryChanged)

    def filter_items(self, categorizables):
        filtered_categories = self.__categories.filteredCategories()
        if not filtered_categories:
            return categorizables

        if self.__filterOnlyWhenAllCategoriesMatch:
            filtered_categorizables = set(categorizables)
            for category in filtered_categories:
                filtered_categorizables &= (
                    self.__categorizablesBelongingToCategory(category)
                )
        else:
            filtered_categorizables = set()
            for category in filtered_categories:
                filtered_categorizables |= (
                    self.__categorizablesBelongingToCategory(category)
                )

        filtered_categorizables &= self.observable()
        return filtered_categorizables

    @staticmethod
    def __categorizablesBelongingToCategory(category):
        categorizables = category.categorizables(recursive=True)
        for categorizable in categorizables.copy():
            categorizables |= set(categorizable.children(recursive=True))
        return categorizables

    def onFilterMatchingChanged(self, event):  # pylint: disable=W0613
        self.__filterOnlyWhenAllCategoriesMatch = \
            self.__settings.getboolean("view", "categoryfiltermatchall")
        self.reset()

    def onCategoryChanged(self, event):  # pylint: disable=W0613
        self.reset()
