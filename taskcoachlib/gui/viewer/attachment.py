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

import os, wx
from taskcoachlib import render, widgets
from taskcoachlib.domain import attachment
from taskcoachlib.i18n import _
from taskcoachlib.gui import uicommand, dialog
from taskcoachlib.gui.icons import image_list_cache
import taskcoachlib.gui.menu
from . import base, mixin


class AttachmentViewer(
    mixin.AttachmentDropTargetMixin,  # pylint: disable=W0223
    base.SortableViewerWithColumns,
    mixin.SortableViewerForAttachmentsMixin,
    mixin.SearchableViewerMixin,
    mixin.NoteColumnMixin,
    base.ListViewer,
):
    SorterClass = attachment.AttachmentSorter
    defaultTitle = _("Attachments")
    coreObjectType = "attachments"

    # Map type_ values to human-readable names
    TYPE_NAMES = {
        "file": _("File"),
        "folder": _("Folder"),
        "uri": _("Link"),
        "mail": _("Email"),
        "unknown": _("Unknown"),
    }

    def __init__(self, *args, **kwargs):
        self.attachments = kwargs.pop("attachmentsToShow")
        kwargs.setdefault("settingsSection", "attachmentviewer")
        super().__init__(*args, **kwargs)

    def _isFolderUri(self, anAttachment):
        """Check if a URI attachment points to a local folder."""
        if anAttachment.type_ != "uri":
            return False
        location = anAttachment.location()
        if location.startswith("file://"):
            import urllib.request

            try:
                path = urllib.request.url2pathname(location[7:])
                return os.path.isdir(path)
            except Exception:
                return False
        return False

    def getTypeName(self, anAttachment):
        """Return human-readable type name for an attachment."""
        if self._isFolderUri(anAttachment):
            return self.TYPE_NAMES.get("folder", _("Folder"))
        return self.TYPE_NAMES.get(anAttachment.type_, anAttachment.type_)

    def getItemTooltipData(self, item):
        """Return tooltip data showing type and location."""
        result = [
            (None, [self.getTypeName(item)]),
            (None, [item.location()]),
        ]
        if item.description():
            lines = [
                line.rstrip("\r") for line in item.description().split("\n")
            ]
            if lines and lines != [""]:
                result.append((None, lines))
        return result

    @staticmethod
    def render_sent_datetime(item, human_readable=True):
        return render.dateTime(
            item.sent_datetime(), human_readable=human_readable
        )

    def _add_attachments(self, attachments, item, **item_dialog_kwargs):
        # Don't try to add attachments to attachments.
        super()._add_attachments(attachments, None, **item_dialog_kwargs)

    def domainObjectsToView(self):
        return self.attachments

    def is_showing_attachments(self):
        return True

    def getSupportedPasteTypes(self):
        return (attachment.Attachment,)

    def createWidget(self):
        imageList = self.createImageList()
        itemPopupMenu = taskcoachlib.gui.menu.AttachmentPopupMenu(
            self.parent, self.settings, self.presentation(), self
        )
        columnPopupMenu = taskcoachlib.gui.menu.ColumnPopupMenu(self)
        self._popupMenus.extend([itemPopupMenu, columnPopupMenu])
        self._columns = self._createColumns()
        widget = widgets.VirtualListCtrl(
            self,
            self.columns(),
            self.onSelect,
            uicommand.Edit(viewer=self),
            itemPopupMenu,
            columnPopupMenu,
            resizeableColumn=1,
            **self.widgetCreationKeywordArguments(),
        )
        widget.SetColumnWidth(0, 150)
        widget.SetImageList(imageList, wx.IMAGE_LIST_SMALL)
        return widget

    def _createColumns(self):
        return [
            widgets.Column(
                "type",
                _("Type"),
                width=self.getColumnWidth("type"),
                imageIndicesCallback=self.typeImageIndices,
                renderCallback=self.getTypeName,
                resizeCallback=self.onResizeColumn,
            ),
            widgets.Column(
                "subject",
                _("Subject"),
                attachment.FileAttachment.subjectChangedEventType(),
                attachment.URIAttachment.subjectChangedEventType(),
                attachment.MailAttachment.subjectChangedEventType(),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self,
                    value="subject",
                    menu_text=_("Sub&ject"),
                    help_text=_("Sort by subject"),
                ),
                width=self.getColumnWidth("subject"),
                renderCallback=lambda item: item.subject(),
                resizeCallback=self.onResizeColumn,
            ),
            widgets.Column(
                "location",
                _("Location"),
                attachment.Attachment.locationChangedEventType(),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self,
                    value="location",
                    menu_text=_("&Location"),
                    help_text=_("Sort by location"),
                ),
                width=self.getColumnWidth("location"),
                renderCallback=lambda item: item.location(),
                resizeCallback=self.onResizeColumn,
            ),
            # A mail's fields (docs/EMAIL_ATTACHMENTS.md)
            widgets.Column(
                "fromName",
                _("From"),
                attachment.MailAttachment.mail_changed_event_type(),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self,
                    value="fromName",
                    menu_text=_("&From"),
                    help_text=_("Sort by sender"),
                ),
                width=self.getColumnWidth("fromName"),
                renderCallback=lambda item: item.from_name(),
                resizeCallback=self.onResizeColumn,
            ),
            widgets.Column(
                "fromAddress",
                _("From address"),
                attachment.MailAttachment.mail_changed_event_type(),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self,
                    value="fromAddress",
                    menu_text=_("From &address"),
                    help_text=_("Sort by sender address"),
                ),
                width=self.getColumnWidth("fromAddress"),
                renderCallback=lambda item: item.from_address(),
                resizeCallback=self.onResizeColumn,
            ),
            widgets.Column(
                "sentDateTime",
                _("Sent"),
                attachment.MailAttachment.mail_changed_event_type(),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self,
                    value="sentDateTime",
                    menu_text=_("&Sent"),
                    help_text=_("Sort by sent date"),
                ),
                width=self.getColumnWidth("sentDateTime"),
                renderCallback=self.render_sent_datetime,
                resizeCallback=self.onResizeColumn,
            ),
            widgets.Column(
                "description",
                _("Description"),
                attachment.FileAttachment.descriptionChangedEventType(),
                attachment.URIAttachment.descriptionChangedEventType(),
                attachment.MailAttachment.descriptionChangedEventType(),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self,
                    value="description",
                    menu_text=_("&Description"),
                    help_text=_("Sort by description"),
                ),
                width=self.getColumnWidth("description"),
                renderCallback=lambda item: item.description(),
                resizeCallback=self.onResizeColumn,
            ),
            widgets.Column(
                "notes",
                _("Notes"),
                attachment.FileAttachment.notesChangedEventType(),  # pylint: disable=E1101
                attachment.URIAttachment.notesChangedEventType(),  # pylint: disable=E1101
                attachment.MailAttachment.notesChangedEventType(),  # pylint: disable=E1101
                width=self.getColumnWidth("notes"),
                alignment=wx.LIST_FORMAT_LEFT,
                imageIndicesCallback=self.noteImageIndices,  # pylint: disable=E1101
                headerImageIndex=image_list_cache.get_index(
                    "nuvola_apps_knotes"
                ),
                renderCallback=lambda item: "",
                resizeCallback=self.onResizeColumn,
            ),
            widgets.Column(
                "creationDateTime",
                _("Creation date"),
                width=self.getColumnWidth("creationDateTime"),
                renderCallback=self.renderCreationDateTime,
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self,
                    value="creationDateTime",
                    menu_text=_("&Creation date"),
                    help_text=_("Sort by creation date"),
                ),
                resizeCallback=self.onResizeColumn,
            ),
            widgets.Column(
                "modificationDateTime",
                _("Modification date"),
                *[
                    each.modification_datetime_changed_event_type()
                    for each in (
                        attachment.FileAttachment,
                        attachment.URIAttachment,
                        attachment.MailAttachment,
                    )
                ],
                width=self.getColumnWidth("modificationDateTime"),
                renderCallback=self.renderModificationDateTime,
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self,
                    value="modificationDateTime",
                    menu_text=_("&Modification date"),
                    help_text=_("Sort by last modification date"),
                ),
                resizeCallback=self.onResizeColumn,
            ),
            widgets.Column(
                "id",
                _("ID"),
                width=self.getColumnWidth("id"),
                renderCallback=lambda item: item.id(),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self,
                    value="id",
                    menu_text=_("&ID"),
                    help_text=_("Sort by ID"),
                ),
                resizeCallback=self.onResizeColumn,
            ),
        ]

    def createColumnUICommands(self):
        return [
            uicommand.ToggleAutoColumnResizing(viewer=self),
            uicommand.Separator(),
            uicommand.ViewColumn(
                menu_text=_("&Location"),
                help_text=_("Show/hide location column"),
                setting="location",
                viewer=self,
            ),
            uicommand.ViewColumn(
                menu_text=_("&From"),
                help_text=_("Show/hide sender column"),
                setting="fromName",
                viewer=self,
            ),
            uicommand.ViewColumn(
                menu_text=_("From &address"),
                help_text=_("Show/hide sender address column"),
                setting="fromAddress",
                viewer=self,
            ),
            uicommand.ViewColumn(
                menu_text=_("&Sent"),
                help_text=_("Show/hide sent date column"),
                setting="sentDateTime",
                viewer=self,
            ),
            uicommand.ViewColumn(
                menu_text=_("&Description"),
                help_text=_("Show/hide description column"),
                setting="description",
                viewer=self,
            ),
            uicommand.ViewColumn(
                menu_text=_("&Notes"),
                help_text=_("Show/hide notes column"),
                setting="notes",
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

    def createCreationToolBarUICommands(self):
        return (
            uicommand.AttachmentNew(
                attachments=self.presentation(),
                viewer=self,
            ),
        ) + super().createCreationToolBarUICommands()

    def createActionToolBarUICommands(self):
        return (
            uicommand.AttachmentOpen(
                attachments=attachment.AttachmentList(),
                viewer=self,
            ),
        ) + super().createActionToolBarUICommands()

    def typeImageIndices(
        self, anAttachment, exists=os.path.exists
    ):  # pylint: disable=W0613
        if anAttachment.type_ == "file":
            attachmentBase = self.settings.get("file", "attachmentbase")
            if exists(anAttachment.normalizedLocation(attachmentBase)):
                index = image_list_cache.get_index(
                    "nuvola_mimetypes_application-x-dvi"
                )
            else:
                index = image_list_cache.get_index(
                    "taskcoach_actions_fileopen_red"
                )
        elif self._isFolderUri(anAttachment):
            # Folder URI - use folder icon
            index = image_list_cache.get_index(
                "nuvola_mimetypes_inode-directory"
            )
        else:
            try:
                index = image_list_cache.get_index(
                    {
                        "uri": "nuvola_categories_applications-internet",
                        "mail": "nuvola_apps_email",
                    }[anAttachment.type_]
                )
            except KeyError:
                index = -1
        return {wx.TreeItemIcon_Normal: index}

    def itemEditorClass(self):
        return dialog.editor.AttachmentEditor

    def newItemCommandClass(self):
        raise NotImplementedError  # pragma: no cover

    def newSubItemCommandClass(self):
        return None

    def deleteItemCommandClass(self):
        raise NotImplementedError  # pragma: no cover

    def cutItemCommandClass(self):
        raise NotImplementedError  # pragma: no cover
