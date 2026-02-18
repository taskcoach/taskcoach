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
from taskcoachlib.domain.attribute import font, color


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

    def __getstate__(self):
        state = super().__getstate__()
        state.update(dict(categories=self.categories()))
        return state

    @patterns.eventSource
    def __setstate__(self, state, event=None):
        super().__setstate__(state, event=event)
        self.setCategories(state["categories"], event=event)

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
    def categoryAddedEventType(class_):
        return "categorizable.category.add"

    def addCategory(self, *categories, **kwargs):
        return self.__categories.add(
            set(categories), event=kwargs.pop("event", None)
        )

    def addCategoryEvent(self, event, *categories):
        event.addSource(
            self, *categories, **dict(type=self.categoryAddedEventType())
        )
        for child in self.children(recursive=True):
            event.addSource(
                child, *categories, **dict(type=child.categoryAddedEventType())
            )
        if self.categoriesChangeAppearance(categories):
            self.appearanceChangedEvent(event)

    def categoriesChangeAppearance(self, categories):
        return (
            self.categoriesChangeFgColor(categories)
            or self.categoriesChangeBgColor(categories)
            or self.categoriesChangeFont(categories)
            or self.categoriesChangeIcon(categories)
        )

    def categoriesChangeFgColor(self, categories):
        return not self.foregroundColor() and any(
            category.foregroundColor(recursive=True) for category in categories
        )

    def categoriesChangeBgColor(self, categories):
        return not self.backgroundColor() and any(
            category.backgroundColor(recursive=True) for category in categories
        )

    def categoriesChangeFont(self, categories):
        return not self.font() and any(
            category.font(recursive=True) for category in categories
        )

    def categoriesChangeIcon(self, categories):
        return not self.icon_id() and any(
            category.icon_id(recursive=True) for category in categories
        )

    @classmethod
    def categoryRemovedEventType(class_):
        return "categorizable.category.remove"

    def removeCategory(self, *categories, **kwargs):
        return self.__categories.remove(
            set(categories), event=kwargs.pop("event", None)
        )

    def removeCategoryEvent(self, event, *categories):
        event.addSource(
            self, *categories, **dict(type=self.categoryRemovedEventType())
        )
        for child in self.children(recursive=True):
            event.addSource(
                child,
                *categories,
                **dict(type=child.categoryRemovedEventType())
            )
        if self.categoriesChangeAppearance(categories):
            self.appearanceChangedEvent(event)

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
            sortedCategorySubjects = sortedSubjects(categories)
            isListMode = not kwargs.get("treeMode", False)
            childCategories = (
                categorizable.categories(recursive=True, upwards=isListMode)
                - categories
            )
            sortedCategorySubjects.extend(sortedSubjects(childCategories))
            return sortedCategorySubjects

        return sortKeyFunction

    @classmethod
    def categoriesSortEventTypes(class_):
        """The event types that influence the categories sort order."""
        return (
            class_.categoryAddedEventType(),
            class_.categoryRemovedEventType(),
        )

    def foregroundColor(self, recursive=False):
        myOwnFgColor = super(
            CategorizableCompositeObject, self
        ).foregroundColor()
        if myOwnFgColor or not recursive:
            return myOwnFgColor
        categoryBasedFgColor = self._categoryForegroundColor()
        if categoryBasedFgColor:
            return categoryBasedFgColor
        else:
            return super().foregroundColor(recursive=True)

    def backgroundColor(self, recursive=False):
        myOwnBgColor = super(
            CategorizableCompositeObject, self
        ).backgroundColor()
        if myOwnBgColor or not recursive:
            return myOwnBgColor
        categoryBasedBgColor = self._categoryBackgroundColor()
        if categoryBasedBgColor:
            return categoryBasedBgColor
        else:
            return super().backgroundColor(recursive=True)

    def _categoryForegroundColor(self):
        """If a categorizable object belongs to a category that has a
        foreground color associated with it, the categorizable object is
        colored accordingly. When a categorizable object belongs to
        multiple categories, the color is mixed. If a categorizable
        composite object has no foreground color of its own, it uses its
        parent's foreground color."""
        colors = [
            category.foregroundColor(recursive=True)
            for category in self.categories()
        ]
        if not colors and self.parent():
            return self.parent()._categoryForegroundColor()
        else:
            return color.ColorMixer.mix(colors)

    def _categoryBackgroundColor(self):
        """If a categorizable object belongs to a category that has a
        background color associated with it, the categorizable object is
        colored accordingly. When a categorizable object belongs to
        multiple categories, the color is mixed. If a categorizable
        composite object has no background color of its own, it uses its
        parent's background color."""
        colors = [
            category.backgroundColor(recursive=True)
            for category in self.categories()
        ]
        if not colors and self.parent():
            return self.parent()._categoryBackgroundColor()
        else:
            return color.ColorMixer.mix(colors)

    def font(self, recursive=False):
        myFont = super().font()
        if myFont or not recursive:
            return myFont
        categoryBasedFont = self._categoryFont()
        if categoryBasedFont:
            return categoryBasedFont
        else:
            return super().font(recursive=True)

    def _categoryFont(self):
        """If a categorizable object belongs to a category that has a
        font associated with it, the categorizable object uses that font.
        When a categorizable object belongs to multiple categories, the
        font is mixed. If a categorizable composite object has no font of
        its own, it uses its parent's font."""
        fonts = [
            category.font(recursive=True) for category in self.categories()
        ]
        if not fonts and self.parent():
            return self.parent()._categoryFont()
        else:
            return font.FontMixer.mix(*fonts)  # pylint: disable=W0142

    def icon_id(self, recursive=False):
        icon_id = super().icon_id()
        if not icon_id and recursive:
            icon_id = self.category_icon_id() or super(
                CategorizableCompositeObject, self
            ).icon_id(recursive=True)
        return icon_id

    def category_icon_id(self):
        icon_id = ""
        for category in self.categories():
            icon_id = category.icon_id(recursive=True)
            if icon_id:
                return icon_id
        if self.parent():
            return self.parent().category_icon_id()
        else:
            return ""

    def selected_icon_id(self, recursive=False):
        icon_id = super().selected_icon_id()
        if not icon_id and recursive:
            icon_id = self.category_selected_icon_id() or super(
                CategorizableCompositeObject, self
            ).selected_icon_id(recursive=True)
        return icon_id

    def category_selected_icon_id(self):
        icon_id = ""
        for category in self.categories():
            icon_id = category.selected_icon_id(recursive=True)
            if icon_id:
                return icon_id
        if self.parent():
            return self.parent().category_selected_icon_id()
        else:
            return ""

    @classmethod
    def categorySubjectChangedEventType(class_):
        return "categorizable.category.subject"

    def categorySubjectChangedEvent(self, event, subject):
        for categorizable in [self] + self.children(recursive=True):
            event.addSource(
                categorizable,
                subject,
                type=categorizable.categorySubjectChangedEventType(),
            )

    @classmethod
    def modificationEventTypes(class_):
        eventTypes = super(
            CategorizableCompositeObject, class_
        ).modificationEventTypes()
        return eventTypes + [
            class_.categoryAddedEventType(),
            class_.categoryRemovedEventType(),
        ]
