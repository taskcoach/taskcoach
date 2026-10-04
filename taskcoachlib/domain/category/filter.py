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
from taskcoachlib.config import settings
from taskcoachlib.domain import base
from .category import Category


class CategoryFilter(base.Filter):
    def __init__(self, *args, **kwargs):
        self.__categories = kwargs.pop("categories")
        for event_type in (
            self.__categories.addItemEventType(),
            self.__categories.removeItemEventType(),
        ):
            patterns.Publisher().registerObserver(
                self.onCategoryChanged,
                eventType=event_type,
                eventSource=self.__categories,
            )
        for event_type in (
            Category.member_added_event_type(),
            Category.member_removed_event_type(),
        ):
            patterns.Publisher().registerObserver(
                self.on_membership_changed, eventType=event_type
            )
        patterns.Publisher().registerObserver(
            self.onCategoryChanged, eventType=Category.filterChangedEventType()
        )
        patterns.Publisher().registerObserver(
            self.onFilterMatchingChanged,
            eventType="view.categoryfiltermatchall",
        )
        super().__init__(*args, **kwargs)

    def detach(self):
        super().detach()
        self.removeObserver(self.onCategoryChanged)
        self.removeObserver(self.on_membership_changed)

    def filter_items(self, categorizables):
        filtered_categories = self.__categories.filteredCategories()
        if not filtered_categories:
            return categorizables

        if settings.view.categoryfiltermatchall:
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
        categorizables = category.members(recursive=True)
        for categorizable in categorizables.copy():
            categorizables |= set(categorizable.children(recursive=True))
        return categorizables

    def onFilterMatchingChanged(self, event):  # pylint: disable=W0613
        self.reset()

    def onCategoryChanged(self, event):  # pylint: disable=W0613
        self.reset()

    def on_membership_changed(self, event):
        # Assigning a category filters nothing unless it, or a category
        # it is under, is filtered
        for category in event.sources():
            if any(
                each.isFiltered() for each in [category] + category.ancestors()
            ):
                self.reset()
                return
