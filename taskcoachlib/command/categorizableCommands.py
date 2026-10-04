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

from taskcoachlib.i18n import _
from taskcoachlib import patterns
from . import base


class ToggleCategoryCommand(base.BaseCommand):
    plural_name = _("Toggle category")
    singular_name = _('Toggle category of "%s"')

    def __init__(self, *args, **kwargs):
        self.category = kwargs.pop("category")
        super().__init__(*args, **kwargs)
        # When some items are in the category and some are not, only toggle
        # the items that are not in the category.
        items_not_in_category = [
            item
            for item in self.items
            if self.category not in item.categories()
        ]
        if 0 < len(items_not_in_category) < len(self.items):
            self.items = items_not_in_category

    def do_command(self):
        super().do_command()
        self.toggle_category()

    @patterns.eventSource
    def toggle_category(self, event=None):
        for categorizable in self.items:
            if self.category in categorizable.categories():
                self.unlink_category(self.category, categorizable, event)
            else:
                self.link_category(self.category, categorizable, event)
                self.unlink_previous_categories(categorizable, event)

    def unlink_previous_categories(self, categorizable, event):
        """Remove categorizable from any mutually exclusive categories it might
        belong to."""
        if self.category.isMutualExclusive():
            parent = self.category.parent()
            if (
                parent in categorizable.categories()
                and not parent.isMutualExclusive()
            ):
                self.unlink_category(parent, categorizable, event)
            else:
                self.unlink_previous_mutual_exclusive_category(
                    self.category.siblings(recursive=True),
                    categorizable,
                    event,
                )
        if self.category.hasExclusiveSubcategories():
            self.unlink_previous_mutual_exclusive_category(
                self.category.children(), categorizable, event
            )

    def unlink_previous_mutual_exclusive_category(
        self, categories, categorizable, event
    ):
        """Look for the category that categorizable belongs to and remove
        categorizable from it."""
        for category in categories:
            if category in categorizable.categories():
                self.unlink_category(category, categorizable, event)

    def link_category(self, category, categorizable, event):
        """Make categorizable belong to category."""
        categorizable.addCategory(category, event=event)

    def unlink_category(self, category, categorizable, event):
        """Make categorizable no longer belong to category."""
        categorizable.removeCategory(category, event=event)


class LinkCategoriesCommand(base.BaseCommand):
    """Link every category to every item, or unlink them (the editor's
    Check all and Uncheck all), as one action."""

    plural_name = _("Toggle category")
    singular_name = _('Toggle category of "%s"')

    def __init__(self, *args, **kwargs):
        categories = kwargs.pop("categories")
        self.__link = kwargs.pop("link", True)
        super().__init__(*args, **kwargs)
        # The pairs this action changes; undo reverses exactly these
        self.__pairs = [
            (category, item)
            for category in categories
            for item in self.items
            if (category in item.categories()) != self.__link
        ]

    def can_do(self):
        return bool(self.__pairs)

    @patterns.eventSource
    def __apply(self, link, event=None):
        for category, item in self.__pairs:
            if link:
                item.addCategory(category, event=event)
            else:
                item.removeCategory(category, event=event)

    def do_command(self):
        super().do_command()
        self.__apply(self.__link)
