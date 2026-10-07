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

from taskcoachlib import command, widgets
from taskcoachlib.domain import note
from taskcoachlib.gui import uicommand, dialog
from taskcoachlib.gui.icons import image_list_cache
import taskcoachlib.gui.menu
from taskcoachlib.i18n import _
from . import base
from . import mixin
from . import inplace_editor
import wx


class BaseNoteViewer(
    mixin.AttachmentDropTargetMixin,  # pylint: disable=W0223
    mixin.SearchableViewerMixin,
    mixin.SortableViewerForNotesMixin,
    mixin.AttachmentColumnMixin,
    base.CategorizableViewerMixin,
    base.WithAttachmentsViewerMixin,
    base.SortableViewerWithColumns,
    base.TreeViewer,
):
    SorterClass = note.NoteSorter
    defaultTitle = _("Notes")
    defaultBitmap = "nuvola_apps_knotes"
    coreObjectType = "notes"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("settingsSection", "noteviewer")
        self.notesToShow = kwargs.get("notesToShow", None)
        super().__init__(*args, **kwargs)
        for event_type in (
            note.Note.subjectChangedEventType(),
            *note.Note.effective_style_event_types(),
        ):
            self.registerObserver(self.on_attribute_changed, event_type)

    def domainObjectsToView(self):
        return (
            self.taskFile.notes()
            if self.notesToShow is None
            else self.notesToShow
        )

    def getSupportedPasteTypes(self):
        return (note.Note,)

    def create_widget(self):
        image_list = self.createImageList()  # Has side-effects
        self._columns = self.ordered_columns(self._createColumns())
        item_popup_menu = taskcoachlib.gui.menu.NotePopupMenu(
            self.parent,
            self.taskFile.categories(),
            self,
            notes=self.taskFile.notes(),
        )
        column_popup_menu = taskcoachlib.gui.menu.ColumnPopupMenu(self)
        self._popupMenus.extend([item_popup_menu, column_popup_menu])
        widget = widgets.TreeListCtrl(
            self,
            self.columns(),
            self.onSelect,
            uicommand.Edit(viewer=self),
            uicommand.NoteDragAndDrop(viewer=self, notes=self.presentation()),
            item_popup_menu,
            column_popup_menu,
            resizeableColumn=0,  # The subject's place once shown
            validate_drag=self.validate_drag,
            **self.widgetCreationKeywordArguments()
        )
        widget.SetImageList(image_list)  # pylint: disable=E1101
        return widget

    def createFilter(self, notes):
        return super().createFilter(notes)

    def createCreationToolBarUICommands(self):
        return (
            uicommand.NoteNew(notes=self.presentation(), viewer=self),
            uicommand.NewSubItem(viewer=self),
        ) + super().createCreationToolBarUICommands()

    def createColumnUICommands(self):
        return [
            uicommand.ToggleAutoColumnResizing(viewer=self),
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
            uicommand.ViewColumn(
                menu_text=_("&Categories"),
                help_text=_("Show/hide categories column"),
                setting="categories",
                viewer=self,
            ),
            uicommand.ViewColumn(
                menu_text=_("&Creation date"),
                help_text=_("Show/hide creation date column"),
                setting="creationDateTime",
                viewer=self,
            ),
            uicommand.ViewColumn(
                menu_text=_("&Modification date"),
                help_text=_("Show/hide last modification date column"),
                setting="modificationDateTime",
                viewer=self,
            ),
            uicommand.ViewColumn(
                menu_text=_("&ID"),
                help_text=_("Show/hide ID column"),
                setting="id",
                viewer=self,
            ),
        ]

    def _createColumns(self):
        ordering_column = widgets.Column(
            "ordering",
            "",
            width=self.getColumnWidth("ordering"),
            resizeCallback=self.onResizeColumn,
            renderCallback=lambda note: "",
            imageIndicesCallback=self.orderingImageIndices,
            sortCallback=uicommand.ViewerSortByCommand(
                viewer=self,
                value="ordering",
                menu_text=_("&Manual ordering"),
                help_text=_("Sort notes manually"),
            ),
        )
        # XXXCHECK editCallback & co
        subject_column = widgets.Column(
            "subject",
            _("Subject"),
            width=self.getColumnWidth("subject"),
            resizeCallback=self.onResizeColumn,
            renderCallback=lambda note: note.subject(),
            sortCallback=uicommand.ViewerSortByCommand(
                viewer=self,
                value="subject",
                menu_text=_("&Subject"),
                help_text=_("Sort notes by subject"),
            ),
            imageIndicesCallback=self.subjectImageIndices,
            editCallback=self.onEditSubject,
            editControl=inplace_editor.SubjectCtrl,
        )
        description_column = widgets.Column(
            "description",
            _("Description"),
            note.Note.descriptionChangedEventType(),
            width=self.getColumnWidth("description"),
            resizeCallback=self.onResizeColumn,
            renderCallback=lambda note: note.description(),
            sortCallback=uicommand.ViewerSortByCommand(
                viewer=self,
                value="description",
                menu_text=_("&Description"),
                help_text=_("Sort notes by description"),
            ),
            editCallback=self.onEditDescription,
            editControl=inplace_editor.DescriptionCtrl,
        )
        attachments_column = widgets.Column(
            "attachments",
            _("Attachments"),
            note.Note.attachmentsChangedEventType(),  # pylint: disable=E1101
            width=self.getColumnWidth("attachments"),
            alignment=wx.LIST_FORMAT_LEFT,
            imageIndicesCallback=self.attachmentImageIndices,  # pylint: disable=E1101
            headerImageIndex=image_list_cache.get_index(
                "nuvola_status_mail-attachment"
            ),
            renderCallback=lambda note: "",
        )
        categories_column = widgets.Column(
            "categories",
            _("Categories"),
            note.Note.categoryAddedEventType(),
            note.Note.categoryRemovedEventType(),
            note.Note.categorySubjectChangedEventType(),
            note.Note.expansionChangedEventType(),
            width=self.getColumnWidth("categories"),
            resizeCallback=self.onResizeColumn,
            renderCallback=self.renderCategories,
            sortCallback=uicommand.ViewerSortByCommand(
                viewer=self,
                value="categories",
                menu_text=_("&Categories"),
                help_text=_("Sort notes by categories"),
            ),
        )
        creation_date_time_column = widgets.Column(
            "creationDateTime",
            _("Creation date"),
            width=self.getColumnWidth("creationDateTime"),
            resizeCallback=self.onResizeColumn,
            renderCallback=self.renderCreationDateTime,
            sortCallback=uicommand.ViewerSortByCommand(
                viewer=self,
                value="creationDateTime",
                menu_text=_("&Creation date"),
                help_text=_("Sort notes by creation date"),
            ),
        )
        modification_date_time_column = widgets.Column(
            "modificationDateTime",
            _("Modification date"),
            note.Note.modification_datetime_changed_event_type(),
            width=self.getColumnWidth("modificationDateTime"),
            resizeCallback=self.onResizeColumn,
            renderCallback=self.renderModificationDateTime,
            sortCallback=uicommand.ViewerSortByCommand(
                viewer=self,
                value="modificationDateTime",
                menu_text=_("&Modification date"),
                help_text=_("Sort notes by last modification date"),
            ),
        )
        id_column = widgets.Column(
            "id",
            _("ID"),
            width=self.getColumnWidth("id"),
            resizeCallback=self.onResizeColumn,
            renderCallback=lambda note: note.id(),
            sortCallback=uicommand.ViewerSortByCommand(
                viewer=self,
                value="id",
                menu_text=_("&ID"),
                help_text=_("Sort notes by ID"),
            ),
        )
        return [
            ordering_column,
            subject_column,
            description_column,
            attachments_column,
            categories_column,
            creation_date_time_column,
            modification_date_time_column,
            id_column,
        ]

    def is_showing_notes(self):
        return True

    def statusMessages(self):
        status1 = _("Notes: %d selected, %d total") % (
            len(self.curselection()),
            len(self.presentation()),
        )
        status2 = _("Status: n/a")
        return status1, status2

    def newItemDialog(self, *args, **kwargs):
        kwargs["categories"] = self.taskFile.categories().filteredCategories()
        return super().newItemDialog(*args, **kwargs)

    def deleteItemCommand(self):
        return command.DeleteNoteCommand(
            self.presentation(),
            self.curselection(),
        )

    def itemEditorClass(self):
        return dialog.editor.NoteEditor

    def newItemCommandClass(self):
        return command.NewNoteCommand

    def newSubItemCommandClass(self):
        return command.NewSubNoteCommand


class NoteViewer(
    mixin.FilterableViewerForCategorizablesMixin, BaseNoteViewer
):  # pylint: disable=W0223
    pass
