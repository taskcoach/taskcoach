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
from taskcoachlib.i18n import _
from taskcoachlib.domain import category
from . import base


class NewCategoryCommand(base.NewItemCommand):
    singular_name = _("New category")

    def __init__(self, *args, **kwargs):
        subject = kwargs.pop("subject", _("New category"))
        description = kwargs.pop("description", "")
        attachments = kwargs.pop("attachments", [])
        super().__init__(*args, **kwargs)
        self.items = self.createNewCategories(
            subject=subject, description=description, attachments=attachments
        )

    def createNewCategories(self, **kwargs):
        return [category.Category(**kwargs)]


class NewSubCategoryCommand(base.NewSubItemCommand):
    plural_name = _("New subcategories")
    singular_name = _('New subcategory of "%s"')

    def __init__(self, *args, **kwargs):
        subject = kwargs.pop("subject", _("New subcategory"))
        description = kwargs.pop("description", "")
        attachments = kwargs.pop("attachments", [])
        super().__init__(*args, **kwargs)
        self.items = self.createNewCategories(
            subject=subject, description=description, attachments=attachments
        )
        self.save_modification_datetimes()

    def createNewCategories(self, **kwargs):
        return [parent.newChild(**kwargs) for parent in self.items]


class EditExclusiveSubcategoriesCommand(base.BaseCommand):
    plural_name = _("Edit exclusive subcategories")
    singular_name = _('Edit exclusive subcategories of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newExclusivity = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldExclusivities = [
            item.hasExclusiveSubcategories() for item in self.items
        ]

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        for item in self.items:
            item.makeSubcategoriesExclusive(self.__newExclusivity, event=event)

    @patterns.eventSource
    def undo_command(self, event=None):
        super().undo_command()
        for item, oldExclusivity in zip(self.items, self.__oldExclusivities):
            item.makeSubcategoriesExclusive(oldExclusivity, event=event)

    def redo_command(self):
        self.do_command()


class EditStylePriorityCommand(base.BaseCommand):
    plural_name = _("Edit style priority")
    singular_name = _('Edit style priority of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newPriority = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldPriorities = [
            item.stylePriority() for item in self.items
        ]

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command()
        for item in self.items:
            item.setStylePriority(self.__newPriority, event=event)

    @patterns.eventSource
    def undo_command(self, event=None):
        super().undo_command()
        for item, oldPriority in zip(self.items, self.__oldPriorities):
            item.setStylePriority(oldPriority, event=event)

    def redo_command(self):
        self.do_command()


class DeleteCategoryCommand(base.DeleteCommand):
    plural_name = _("Delete categories")
    singular_name = _('Delete category "%s"')


class DragAndDropCategoryCommand(base.OrderingDragAndDropCommand):
    plural_name = _("Drag and drop categories")
