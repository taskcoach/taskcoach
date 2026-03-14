# -*- coding: utf-8 -*-

"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2008 Rob McMullen <rob.mcmullen@gmail.com>
Copyright (C) 2008 Thomas Sonne Olesen <tpo@sonnet.dk>

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

import wx
from taskcoachlib import command, widgets
from taskcoachlib.domain import category
from taskcoachlib.i18n import _
from taskcoachlib.gui import uicommand, dialog
from taskcoachlib.gui.icons import image_list_cache
import taskcoachlib.gui.menu
from . import base
from . import mixin
from . import inplace_editor


class BaseCategoryViewer(
    mixin.AttachmentDropTargetMixin,  # pylint: disable=W0223
    mixin.FilterableViewerMixin,
    mixin.SortableViewerForCategoriesMixin,
    mixin.SearchableViewerMixin,
    base.WithAttachmentsViewerMixin,
    mixin.NoteColumnMixin,
    mixin.AttachmentColumnMixin,
    base.SortableViewerWithColumns,
    base.TreeViewer,
):
    SorterClass = category.CategorySorter
    defaultTitle = _("Categories")
    defaultBitmap = "nuvola_places_folder-downloads"
    coreObjectType = "categories"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("settingsSection", "categoryviewer")
        super().__init__(*args, **kwargs)
        for eventType in [
            category.Category.subjectChangedEventType(),
            category.Category.appearanceChangedEventType(),
            category.Category.exclusiveSubcategoriesChangedEventType(),
            category.Category.filterChangedEventType(),
        ]:
            self.registerObserver(
                self.onAttributeChanged_Deprecated, eventType
            )

    def domainObjectsToView(self):
        return self.taskFile.categories()

    def getSupportedPasteTypes(self):
        return (category.Category,)

    def createWidget(self):
        imageList = self.createImageList()  # Has side-effects
        self._columns = self._createColumns()
        itemPopupMenu = self.createCategoryPopupMenu()
        columnPopupMenu = taskcoachlib.gui.menu.ColumnPopupMenu(self)
        self._popupMenus.extend([itemPopupMenu, columnPopupMenu])
        widget = widgets.CheckTreeCtrl(
            self,
            self._columns,
            self.onSelect,
            self.onCheck,
            uicommand.Edit(viewer=self),
            uicommand.CategoryDragAndDrop(
                viewer=self, categories=self.presentation()
            ),
            itemPopupMenu,
            columnPopupMenu,
            resizeableColumn=1 if self.hasOrderingColumn() else 0,
            validateDrag=self.validateDrag,
            **self.widgetCreationKeywordArguments()
        )
        if self.hasOrderingColumn():
            widget.SetMainColumn(1)
        widget.SetImageList(imageList)  # pylint: disable=E1101
        return widget

    def createCategoryPopupMenu(self, localOnly=False):
        return taskcoachlib.gui.menu.CategoryPopupMenu(
            self.parent, self.settings, self.taskFile, self, localOnly
        )

    def _createColumns(self):
        # pylint: disable=W0142,E1101
        kwargs = dict(resizeCallback=self.onResizeColumn)
        columns = [
            widgets.Column(
                "ordering",
                "",
                category.Category.orderingChangedEventType(),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self, value="ordering"
                ),
                imageIndicesCallback=self.orderingImageIndices,
                renderCallback=lambda category: "",
                width=self.getColumnWidth("ordering"),
            ),
            widgets.Column(
                "subject",
                _("Subject"),
                category.Category.subjectChangedEventType(),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self, value="subject"
                ),
                imageIndicesCallback=self.subjectImageIndices,
                width=self.getColumnWidth("subject"),
                editCallback=self.onEditSubject,
                editControl=inplace_editor.SubjectCtrl,
                **kwargs
            ),
            widgets.Column(
                "description",
                _("Description"),
                category.Category.descriptionChangedEventType(),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self, value="description"
                ),
                renderCallback=lambda category: category.description(),
                width=self.getColumnWidth("description"),
                editCallback=self.onEditDescription,
                editControl=inplace_editor.DescriptionCtrl,
                **kwargs
            ),
            widgets.Column(
                "attachments",
                _("Attachments"),
                category.Category.attachmentsChangedEventType(),  # pylint: disable=E1101
                width=self.getColumnWidth("attachments"),
                alignment=wx.LIST_FORMAT_LEFT,
                imageIndicesCallback=self.attachmentImageIndices,
                headerImageIndex=image_list_cache.get_index("nuvola_status_mail-attachment"),
                renderCallback=lambda category: "",
                **kwargs
            ),
        ]
        columns.append(
            widgets.Column(
                "notes",
                _("Notes"),
                category.Category.notesChangedEventType(),  # pylint: disable=E1101
                width=self.getColumnWidth("notes"),
                alignment=wx.LIST_FORMAT_LEFT,
                imageIndicesCallback=self.noteImageIndices,
                headerImageIndex=image_list_cache.get_index("nuvola_apps_knotes"),
                renderCallback=lambda category: "",
                **kwargs
            )
        )
        columns.append(
            widgets.Column(
                "creationDateTime",
                _("Creation date"),
                width=self.getColumnWidth("creationDateTime"),
                renderCallback=self.renderCreationDateTime,
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self, value="creationDateTime"
                ),
                **kwargs
            )
        )
        columns.append(
            widgets.Column(
                "modificationDateTime",
                _("Modification date"),
                width=self.getColumnWidth("modificationDateTime"),
                renderCallback=self.renderModificationDateTime,
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self, value="modificationDateTime"
                ),
                *category.Category.modificationEventTypes(),
                **kwargs
            )
        )
        columns.append(
            widgets.Column(
                "id",
                _("ID"),
                width=self.getColumnWidth("id"),
                renderCallback=lambda category: category.id(),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self, value="id"
                ),
                **kwargs
            )
        )
        return columns

    def createCreationToolBarUICommands(self):
        return (
            uicommand.CategoryNew(
                categories=self.presentation(), settings=self.settings
            ),
            uicommand.NewSubItem(viewer=self),
        )

    def check_all_categories(self):
        """Set all categories to filtered (checked) state."""
        for cat in self.presentation():
            cat.setFiltered(True)
        self.refresh()

    def uncheck_all_categories(self):
        """Set all categories to unfiltered (unchecked) state."""
        for cat in self.presentation():
            cat.setFiltered(False)
        self.refresh()

    def createColumnUICommands(self):
        commands = [
            uicommand.ToggleAutoColumnResizing(
                viewer=self, settings=self.settings
            ),
            uicommand.Separator(),
            uicommand.ViewColumn(
                menu_text=_("&Manual ordering"),
                help_text=_("Show/hide the manual ordering column"),
                setting="ordering",
                viewer=self,
            ),
            uicommand.ViewColumn(
                menu_text=_("&Description"),
                help_text=_("Show/hide description column"),
                setting="description",
                viewer=self,
            ),
            uicommand.ViewColumn(
                menu_text=_("&Attachments"),
                help_text=_("Show/hide attachments column"),
                setting="attachments",
                viewer=self,
            ),
        ]
        commands.append(
            uicommand.ViewColumn(
                menu_text=_("&Notes"),
                help_text=_("Show/hide notes column"),
                setting="notes",
                viewer=self,
            )
        )
        commands.append(
            uicommand.ViewColumn(
                menu_text=_("&Creation date"),
                help_text=_("Show/hide creation date column"),
                setting="creationDateTime",
                viewer=self,
            )
        )
        commands.append(
            uicommand.ViewColumn(
                menu_text=_("&Modification date"),
                help_text=_("Show/hide last modification date column"),
                setting="modificationDateTime",
                viewer=self,
            )
        )
        commands.append(
            uicommand.ViewColumn(
                menu_text=_("&ID"),
                help_text=_("Show/hide ID column"),
                setting="id",
                viewer=self,
            )
        )
        return commands

    def onAttributeChanged(self, newValue, sender):
        super().onAttributeChanged(newValue, sender)

    def onAttributeChanged_Deprecated(self, event):
        if (
            category.Category.exclusiveSubcategoriesChangedEventType()
            in event.types()
        ):
            # We need to refresh the children of the changed item as well
            # because they have to use radio buttons instead of checkboxes, or
            # vice versa:
            items = event.sources()
            for item in items.copy():
                items |= set(item.children())
            self.widget.RefreshItems(*items)  # pylint: disable=W0142
        else:
            super().onAttributeChanged_Deprecated(event)

    def onCheck(self, event, final):
        categoryToFilter = self.widget.GetItemPyData(event.GetItem())
        categoryToFilter.setFiltered(event.GetItem().IsChecked())
        self.send_viewer_status_event()  # Notify status observers like the status bar

    def get_is_item_checked(self, item):
        if isinstance(item, category.Category):
            return item.isFiltered()
        return False

    def get_item_parent_has_exclusive_children(self, item):
        parent = item.parent()
        return parent and parent.hasExclusiveSubcategories()

    def is_showing_categories(self):
        return True

    def statusMessages(self):
        status1 = _("Categories: %d selected, %d total") % (
            len(self.curselection()),
            len(self.presentation()),
        )
        filteredCategories = self.presentation().filteredCategories()
        status2 = _("Status: %d filtered") % len(filteredCategories)
        return status1, status2

    def itemEditorClass(self):
        return dialog.editor.CategoryEditor

    def newItemCommandClass(self):
        return command.NewCategoryCommand

    def newSubItemCommandClass(self):
        return command.NewSubCategoryCommand

    def deleteItemCommandClass(self):
        return command.DeleteCategoryCommand


class CategoryViewer(BaseCategoryViewer):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filterUICommand.set_choice(
            self.settings.getboolean("view", "categoryfiltermatchall")
        )

    def createModeToolBarUICommands(self):
        # pylint: disable=W0201
        self.filterUICommand = uicommand.CategoryViewerFilterChoice(
            settings=self.settings
        )
        return super().createModeToolBarUICommands() + (self.filterUICommand,)
