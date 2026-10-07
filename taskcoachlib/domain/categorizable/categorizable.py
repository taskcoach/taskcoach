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


class CategorizableCompositeObject(base.CompositeObject):
    """CategorizableCompositeObjects are composite objects that can be
    categorized by adding them to one or more categories. Examples of
    categorizable composite objects are tasks and notes."""

    def __init__(self, *args, **kwargs):
        self.__categories = base.SetAttribute(
            kwargs.pop("categories", set()),
            self,
            self.addCategoryEvent,
            self.removeCategoryEvent,
        )
        super().__init__(*args, **kwargs)
        # The one place that keeps the categories' member index
        for category in self.__categories.get():
            category.member_joined(self)

    def __getcopystate__(self):
        state = super().__getcopystate__()
        state.update(dict(categories=self.categories()))
        return state

    def categories(self, recursive=False, upwards=False):
        result = self.__categories.get()
        if recursive and upwards and self.parent() is not None:
            result |= self.parent().categories(recursive=True, upwards=True)
        elif recursive and not upwards:
            for child in self.children(recursive=True):
                result |= child.categories()
        return result

    @classmethod
    def categoryAddedEventType(cls):
        return "categorizable.category.add"

    def addCategory(self, *categories, **kwargs):
        return self.__categories.add(
            set(categories), event=kwargs.pop("event", None)
        )

    def addCategoryEvent(self, event, *categories):
        for category in categories:
            category.member_joined(self, event)
        event.addSource(
            self, *categories, **dict(type=self.categoryAddedEventType())
        )
        for child in self.children(recursive=True):
            event.addSource(
                child, *categories, **dict(type=child.categoryAddedEventType())
            )

    @classmethod
    def categoryRemovedEventType(cls):
        return "categorizable.category.remove"

    def removeCategory(self, *categories, **kwargs):
        return self.__categories.remove(
            set(categories), event=kwargs.pop("event", None)
        )

    def removeCategoryEvent(self, event, *categories):
        for category in categories:
            category.member_left(self, event)
        event.addSource(
            self, *categories, **dict(type=self.categoryRemovedEventType())
        )
        for child in self.children(recursive=True):
            event.addSource(
                child,
                *categories,
                **dict(type=child.categoryRemovedEventType())
            )

    def setCategories(self, categories, event=None):
        return self.__categories.set(set(categories), event=event)

    @staticmethod
    def categoriesSortFunction(**kwargs):
        """Return a sort key for sorting by categories. Since a categorizable
        can have multiple categories we first sort the categories by their
        subjects. If the sorter is in tree mode, we also take the categories
        of the children of the categorizable into account, after the
        categories of the categorizable itself. If the sorter is in list
        mode we also take the categories of the parent (recursively) into
        account, again after the categories of the categorizable itself."""

        def sortKeyFunction(categorizable):
            def sortedSubjects(items):
                return sorted([item.subject(recursive=True) for item in items])

            categories = categorizable.categories()
            sorted_category_subjects = sortedSubjects(categories)
            is_list_mode = not kwargs.get("tree_mode", False)
            child_categories = (
                categorizable.categories(recursive=True, upwards=is_list_mode)
                - categories
            )
            sorted_category_subjects.extend(sortedSubjects(child_categories))
            return sorted_category_subjects

        return sortKeyFunction

    @classmethod
    def categoriesSortEventTypes(cls):
        """The event types that influence the categories sort order."""
        return (
            cls.categoryAddedEventType(),
            cls.categoryRemovedEventType(),
        )

    @classmethod
    def categorySubjectChangedEventType(cls):
        return "categorizable.category.subject"

    def categorySubjectChangedEvent(self, event, subject):
        for categorizable in [self] + self.children(recursive=True):
            event.addSource(
                categorizable,
                subject,
                type=categorizable.categorySubjectChangedEventType(),
            )

    @classmethod
    def modificationEventTypes(cls):
        event_types = super(
            CategorizableCompositeObject, cls
        ).modificationEventTypes()
        return event_types + [
            cls.categoryAddedEventType(),
            cls.categoryRemovedEventType(),
        ]


def owner_chains(*collections):
    """Each note and attachment owned in a file's tasks, notes and
    categories -> its owners, from the top. They own them at any depth
    (a task's attachment's note), and an owned item does not know its
    owner."""
    chains = {}

    def walk(owner, chain):
        chain = chain + [owner]
        notes = owner.notes(recursive=True) if hasattr(owner, "notes") else []
        attachments = (
            owner.attachments() if hasattr(owner, "attachments") else []
        )
        for each in list(notes) + list(attachments):
            chains[each] = chain
            walk(each, chain)

    for collection in collections:
        for item in collection:
            walk(item, [])
    return chains


def categorizables_in(*collections):
    """Every item in a file's tasks, notes and categories that can have
    categories, owned ones included. A category's members may include
    items outside the file (a copy, a deleted item kept for undo); this
    says which are in."""
    items = [item for collection in collections for item in collection]
    return {
        each
        for each in items + list(owner_chains(*collections))
        if isinstance(each, CategorizableCompositeObject)
    }
