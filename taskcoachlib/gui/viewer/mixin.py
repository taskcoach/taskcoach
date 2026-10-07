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

from taskcoachlib import command
from taskcoachlib.config import settings
from taskcoachlib.domain import base, task, category, attachment
from taskcoachlib.gui import uicommand
from taskcoachlib.gui.icons import image_list_cache
from taskcoachlib.i18n import _
import wx
from taskcoachlib import patterns


class SearchableViewerMixin(object):
    """A viewer that is searchable. This is a mixin class."""

    def isSearchable(self):
        return True

    def createFilter(self, presentation):
        presentation = super().createFilter(presentation)
        return base.SearchFilter(presentation, **self.searchOptions())

    def searchOptions(self):
        (
            search_string,
            match_case,
            include_sub_items,
            search_description,
            regular_expression,
        ) = self.getSearchFilter()
        return dict(
            searchString=search_string,
            matchCase=match_case,
            includeSubItems=include_sub_items,
            searchDescription=search_description,
            regularExpression=regular_expression,
            tree_mode=self.is_tree_viewer(),
        )

    def setSearchFilter(
        self,
        searchString,
        matchCase=False,
        includeSubItems=False,
        searchDescription=False,
        regularExpression=False,
    ):
        options = self.options
        options.searchfilterstring = searchString
        options.searchfiltermatchcase = matchCase
        options.searchfilterincludesubitems = includeSubItems
        options.searchdescription = searchDescription
        options.regularexpression = regularExpression
        self.presentation().setSearchFilter(
            searchString,
            matchCase=matchCase,
            includeSubItems=includeSubItems,
            searchDescription=searchDescription,
            regularExpression=regularExpression,
        )

    def getSearchFilter(self):
        options = self.options
        return (
            options.searchfilterstring,
            options.searchfiltermatchcase,
            options.searchfilterincludesubitems,
            options.searchdescription,
            options.regularexpression,
        )

    def createToolBarUICommands(self):
        """UI commands to put on the toolbar of this viewer."""
        search_command = uicommand.Search(viewer=self)
        return super().createToolBarUICommands() + (
            1,
            search_command,
        )


class FilterableViewerMixin(object):
    """A viewer that is filterable. This is a mixin class."""

    def __init__(self, *args, **kwargs):
        self.__filterUICommands = None
        super().__init__(*args, **kwargs)

    def is_filterable(self):
        return True

    def getFilterUICommands(self):
        if not self.__filterUICommands:
            self.__filterUICommands = self.createFilterUICommands()
        # Recreate the category filter commands every time because the category
        # filter menu depends on what categories there are
        return (
            self.__filterUICommands[:2]
            + self.createCategoryFilterCommands()
            + self.__filterUICommands[2:]
        )

    def createFilterUICommands(self):
        return [
            uicommand.ResetFilter(viewer=self),
            uicommand.CategoryViewerFilterChoice(),
            None,
        ]

    def createToolBarUICommands(self):
        if not self.is_filterable():
            return super().createToolBarUICommands()
        clear_ui_command = uicommand.ResetFilter(viewer=self)
        return super().createToolBarUICommands() + (clear_ui_command,)

    def reset_filter(self):
        self.taskFile.categories().resetAllFilteredCategories()

    def has_filter(self):
        return self.taskFile.categories().has_category_filters

    def createCategoryFilterCommands(self):
        categories = self.taskFile.categories()
        commands = [
            _("&Categories"),
            uicommand.ResetCategoryFilter(categories=categories),
        ]
        if categories:
            commands.append(None)
            commands.extend(
                self.createToggleCategoryFilterCommands(categories.rootItems())
            )
        return [tuple(commands)]

    def createToggleCategoryFilterCommands(self, categories):
        categories = list(categories)
        categories.sort(key=lambda category: category.subject())
        commands = [
            uicommand.ToggleCategoryFilter(category=each_category)
            for each_category in categories
        ]
        categories_with_children = [
            each_category
            for each_category in categories
            if each_category.children()
        ]
        if categories_with_children:
            commands.append(None)
            for each_category in categories_with_children:
                sub_commands = [
                    _("%s (subcategories)") % each_category.subject()
                ]
                sub_commands.extend(
                    self.createToggleCategoryFilterCommands(
                        each_category.children()
                    )
                )
                commands.append(tuple(sub_commands))
        return commands


class FilterableViewerForCategorizablesMixin(FilterableViewerMixin):
    def createFilter(self, items):
        items = super(
            FilterableViewerForCategorizablesMixin, self
        ).createFilter(items)
        if not self.is_filterable():
            return items
        return category.filter.CategoryFilter(
            items,
            categories=self.taskFile.categories(),
            tree_mode=self.is_tree_viewer(),
        )


class FilterableViewerForTasksMixin(FilterableViewerForCategorizablesMixin):
    def createFilter(self, taskList):
        taskList = super().createFilter(taskList)
        return task.filter.ViewFilter(
            taskList,
            tree_mode=self.is_tree_viewer(),
            **self.viewFilterOptions(),
        )

    def viewFilterOptions(self):
        return dict(
            hide_composite_tasks=self.is_hiding_composite_tasks(),
            statusesToHide=self.hidden_task_statuses(),
        )

    def hide_task_status(self, status, hide=True):
        self.__setBooleanSetting("hide%stasks" % status, hide)
        self.presentation().hide_task_status(status, hide)

    def show_only_task_status(self, status):
        for task_status in task.Task.possibleStatuses():
            self.hide_task_status(task_status, hide=status != task_status)

    def is_hiding_task_status(self, status):
        return self.__getBooleanSetting("hide%stasks" % status)

    def hidden_task_statuses(self):
        return [
            status
            for status in task.Task.possibleStatuses()
            if self.is_hiding_task_status(status)
        ]

    def hide_composite_tasks(self, hide=True):
        self.__setBooleanSetting("hidecompositetasks", hide)
        self.presentation().hide_composite_tasks(hide)

    def is_hiding_composite_tasks(self):
        return self.__getBooleanSetting("hidecompositetasks")

    def reset_filter(self):
        super().reset_filter()
        for status in task.Task.possibleStatuses():
            self.hide_task_status(status, False)
        if not self.is_tree_viewer():
            # Only reset this filter when in list mode, since it only applies
            # to list mode
            self.hide_composite_tasks(False)

    def has_filter(self):
        return super().has_filter() or self.presentation().has_filter()

    def createFilterUICommands(self):
        return (
            super().createFilterUICommands()
            + [
                uicommand.ViewerHideTasks(task_status, viewer=self)
                for task_status in task.Task.possibleStatuses()
            ]
            + [uicommand.ViewerHideCompositeTasks(viewer=self)]
        )

    def __getBooleanSetting(self, setting):
        return getattr(self.options, setting)

    def __setBooleanSetting(self, setting, boolean_value):
        setattr(self.options, setting, boolean_value)


class SortableViewerMixin(object):
    """A viewer that is sortable. This is a mixin class."""

    def __init__(self, *args, **kwargs):
        self._sortUICommands = []
        super().__init__(*args, **kwargs)

    def isSortable(self):
        return True

    def register_presentation_observers(self):
        super().register_presentation_observers()
        self.removeObserver(self.on_sort_order_changed)
        self.registerObserver(
            self.on_sort_order_changed,
            eventType=self.presentation().sort_event_type(),
            eventSource=self.presentation(),
        )

    def detach(self):
        super().detach()
        self.removeObserver(self.on_sort_order_changed)

    def on_sort_order_changed(self, event):
        if self.presentation() in event.sources():
            self.refresh_order()
            self.send_viewer_status_event()

    def create_sorter(self, presentation):
        return self.SorterClass(presentation, **self.sorter_options())

    def sorter_options(self):
        return dict(
            sortBy=self.sortKey(), sortCaseSensitive=self.isSortCaseSensitive()
        )

    def sortBy(self, sort_key):
        self.presentation().sort_by(sort_key)
        self.options.sortby = self.presentation().sort_keys()

    def isSortedBy(self, sort_key):
        sort_keys = self.presentation().sort_keys()
        return sort_keys and (
            sort_keys[0] == sort_key or sort_keys[0] == "-" + sort_key
        )

    def sortKey(self):
        return self.options.sortby

    def isSortOrderAscending(self):
        sort_keys = self.presentation().sort_keys()
        return sort_keys and not sort_keys[0].startswith("-")

    def setSortOrderAscending(self, ascending=True):
        self.presentation().sort_ascending(ascending)
        self.options.sortby = self.presentation().sort_keys()

    def isSortCaseSensitive(self):
        return self.options.sortcasesensitive

    def setSortCaseSensitive(self, sort_case_sensitive=True):
        self.options.sortcasesensitive = sort_case_sensitive
        self.presentation().sort_case_sensitive(sort_case_sensitive)

    def getSortUICommands(self):
        if not self._sortUICommands:
            self.createSortUICommands()
        return self._sortUICommands

    def createSortUICommands(self):
        """(Re)Create the UICommands for sorting. These UICommands are put
        in the View->Sort menu and are used when the user clicks a column
        header."""
        self._sortUICommands = self.createSortOrderUICommands()
        sort_by_commands = self.createSortByUICommands()
        if sort_by_commands:
            self._sortUICommands.append(None)  # Separator
            self._sortUICommands.extend(sort_by_commands)

    def createSortOrderUICommands(self):
        """Create the UICommands for changing sort order, like ascending/
        descending, and match case."""
        return [
            uicommand.ViewerSortOrderCommand(viewer=self),
            uicommand.ViewerSortCaseSensitive(viewer=self),
        ]

    def createSortByUICommands(self):
        """Create the UICommands for changing what the items are sorted by,
        i.e. the columns."""
        return [
            uicommand.ViewerSortByCommand(
                viewer=self,
                value="subject",
                menu_text=_("Sub&ject"),
                help_text=self.sortBySubjectHelpText,
            ),
            uicommand.ViewerSortByCommand(
                viewer=self,
                value="description",
                menu_text=_("&Description"),
                help_text=self.sortByDescriptionHelpText,
            ),
            uicommand.ViewerSortByCommand(
                viewer=self,
                value="creationDateTime",
                menu_text=_("&Creation date"),
                help_text=self.sortByCreationDateTimeHelpText,
            ),
            uicommand.ViewerSortByCommand(
                viewer=self,
                value="modificationDateTime",
                menu_text=_("&Modification date"),
                help_text=self.sortByModificationDateTimeHelpText,
            ),
        ]


class SortableViewerForEffortMixin(SortableViewerMixin):
    def createSortOrderUICommands(self):
        """Create the UICommands for changing sort order. The only
        option for efforts is ascending/descending at the moment."""
        return [uicommand.ViewerSortOrderCommand(viewer=self)]

    def createSortByUICommands(self):
        """Create the UICommands for changing what the items are sorted by,
        i.e. the columns. Currently, effort is always sorted by period."""
        return []

    def sortKey(self):
        """Efforts are always sorted by period at the moment."""
        return ["-period"]


class ManualOrderingMixin(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def createSortByUICommands(self):
        return [
            uicommand.ViewerSortByCommand(
                viewer=self,
                value="ordering",
                menu_text=_("&Manual ordering"),
                help_text=self.sortByOrderingHelpText,
            )
        ] + super().createSortByUICommands()

    def orderingImageIndices(self, item):
        index = image_list_cache.get_index("taskcoach_actions_sort")
        return {wx.TreeItemIcon_Normal: index, wx.TreeItemIcon_Expanded: index}


class SortableViewerForCategoriesMixin(
    ManualOrderingMixin, SortableViewerMixin
):
    sortBySubjectHelpText = _("Sort categories by subject")
    sortByDescriptionHelpText = _("Sort categories by description")
    sortByCreationDateTimeHelpText = _("Sort categories by creation date")
    sortByModificationDateTimeHelpText = _(
        "Sort categories by last modification date"
    )
    sortByOrderingHelpText = _("Sort categories manually")


class SortableViewerForCategorizablesMixin(SortableViewerMixin):
    """Mixin class to create uiCommands for sorting categorizables."""

    def createSortByUICommands(self):
        commands = super(
            SortableViewerForCategorizablesMixin, self
        ).createSortByUICommands()
        commands.append(
            uicommand.ViewerSortByCommand(
                viewer=self,
                value="categories",
                menu_text=_("&Category"),
                help_text=self.sortByCategoryHelpText,
            )
        )
        return commands


class SortableViewerForAttachmentsMixin(SortableViewerForCategorizablesMixin):
    sortBySubjectHelpText = _("Sort attachments by subject")
    sortByDescriptionHelpText = _("Sort attachments by description")
    sortByCategoryHelpText = _("Sort attachments by category")
    sortByCreationDateTimeHelpText = _("Sort attachments by creation date")
    sortByModificationDateTimeHelpText = _(
        "Sort attachments by last modification date"
    )


class SortableViewerForNotesMixin(
    ManualOrderingMixin, SortableViewerForCategorizablesMixin
):
    sortBySubjectHelpText = _("Sort notes by subject")
    sortByDescriptionHelpText = _("Sort notes by description")
    sortByCategoryHelpText = _("Sort notes by category")
    sortByCreationDateTimeHelpText = _("Sort notes by creation date")
    sortByModificationDateTimeHelpText = _(
        "Sort notes by last modification date"
    )
    sortByOrderingHelpText = _("Sort notes manually")


class SortableViewerForTasksMixin(
    ManualOrderingMixin, SortableViewerForCategorizablesMixin
):
    SorterClass = task.sorter.Sorter
    sortBySubjectHelpText = _("Sort tasks by subject")
    sortByDescriptionHelpText = _("Sort tasks by description")
    sortByCategoryHelpText = _("Sort tasks by category")
    sortByCreationDateTimeHelpText = _("Sort tasks by creation date")
    sortByModificationDateTimeHelpText = _(
        "Sort tasks by last modification date"
    )
    sortByOrderingHelpText = _("Sort tasks manually")

    def __init__(self, *args, **kwargs):
        self.__sortKeyUnchangedCount = 0
        super().__init__(*args, **kwargs)

    def sortBy(self, sort_key):
        # If the user clicks the same column for the third time, toggle
        # the SortyByTaskStatusFirst setting:
        if self.isSortedBy(sort_key):
            self.__sortKeyUnchangedCount += 1
        else:
            self.__sortKeyUnchangedCount = 0
        if self.__sortKeyUnchangedCount > 1:
            self.setSortByTaskStatusFirst(not self.isSortByTaskStatusFirst())
            self.__sortKeyUnchangedCount = 0
        super().sortBy(sort_key)

    def isSortByTaskStatusFirst(self):
        return self.options.sortbystatusfirst

    def setSortByTaskStatusFirst(self, sort_by_status_first):
        self.options.sortbystatusfirst = sort_by_status_first
        self.presentation().sort_by_task_status_first(sort_by_status_first)

    def sorter_options(self):
        options = super().sorter_options()
        options.update(
            tree_mode=self.is_tree_viewer(),
            sortByTaskStatusFirst=self.isSortByTaskStatusFirst(),
        )
        return options

    def createSortOrderUICommands(self):
        commands = super(
            SortableViewerForTasksMixin, self
        ).createSortOrderUICommands()
        commands.append(uicommand.ViewerSortByTaskStatusFirst(viewer=self))
        return commands

    def createSortByUICommands(self):
        commands = super(
            SortableViewerForTasksMixin, self
        ).createSortByUICommands()
        depends_on_effort_feature = [
            "budget",
            "timeSpent",
            "budgetLeft",
            "hourlyFee",
            "fixedFee",
            "revenue",
        ]
        for menu_text, help_text, value in [
            (
                _("&Planned start date"),
                _("Sort tasks by planned start date"),
                "plannedStartDateTime",
            ),
            (_("&Due date"), _("Sort tasks by due date"), "dueDateTime"),
            (
                _("&Completion date"),
                _("Sort tasks by completion date"),
                "completionDateTime",
            ),
            (
                _("&Prerequisites"),
                _("Sort tasks by prerequisite tasks"),
                "prerequisites",
            ),
            (
                _("&Dependents"),
                _("Sort tasks by dependent tasks"),
                "dependencies",
            ),
            (_("&Time left"), _("Sort tasks by time left"), "timeLeft"),
            (
                _("&Percentage complete"),
                _("Sort tasks by percentage complete"),
                "percentageComplete",
            ),
            (_("&Recurrence"), _("Sort tasks by recurrence"), "recurrence"),
            (_("&Budget"), _("Sort tasks by budget"), "budget"),
            (_("&Time spent"), _("Sort tasks by time spent"), "timeSpent"),
            (_("Budget &left"), _("Sort tasks by budget left"), "budgetLeft"),
            (_("&Priority"), _("Sort tasks by priority"), "priority"),
            (_("&Hourly fee"), _("Sort tasks by hourly fee"), "hourlyFee"),
            (_("&Fixed fee"), _("Sort tasks by fixed fee"), "fixedFee"),
            (_("&Revenue"), _("Sort tasks by revenue"), "revenue"),
            (
                _("&Reminder"),
                _("Sort tasks by reminder date and time"),
                "reminder",
            ),
        ]:
            if value not in depends_on_effort_feature or (
                value in depends_on_effort_feature
            ):
                commands.append(
                    uicommand.ViewerSortByCommand(
                        viewer=self,
                        value=value,
                        menu_text=menu_text,
                        help_text=help_text,
                    )
                )
        return commands


class AttachmentDropTargetMixin(object):
    """Mixin class for viewers that are drop targets for attachments."""

    def widgetCreationKeywordArguments(self):
        kwargs = super(
            AttachmentDropTargetMixin, self
        ).widgetCreationKeywordArguments()
        kwargs["on_drop_url"] = self.on_drop_url
        kwargs["on_drop_files"] = self.on_drop_files
        kwargs["on_drop_mail"] = self.on_drop_mail
        return kwargs

    def _add_attachments(self, attachments, item, **item_dialog_kwargs):
        """Add attachments. If item refers to an existing domain object,
        add the attachments to that object. If item is None, use the
        newItemDialog to create a new domain object and add the attachments
        to that new object."""
        if item is None:
            item_dialog_kwargs["subject"] = attachments[0].subject()
            if settings.view.defaultplannedstartdatetime.startswith("preset"):
                item_dialog_kwargs["plannedStartDateTime"] = (
                    task.Task.suggestedPlannedStartDateTime()
                )
            if settings.view.defaultduedatetime.startswith("preset"):
                item_dialog_kwargs["dueDateTime"] = (
                    task.Task.suggestedDueDateTime()
                )
            if settings.view.defaultactualstartdatetime.startswith("preset"):
                item_dialog_kwargs["actualStartDateTime"] = (
                    task.Task.suggestedActualStartDateTime()
                )
            if settings.view.defaultreminderdatetime.startswith("preset"):
                item_dialog_kwargs["reminder"] = (
                    task.Task.suggestedReminderDateTime()
                )
            new_item_dialog = self.newItemDialog(
                icon_id="nuvola_actions_document-new",
                attachments=attachments,
                **item_dialog_kwargs,
            )
            new_item_dialog.Show()
            # Later, so the dialog has the focus once the drop completes
            patterns.later.soon(new_item_dialog, new_item_dialog.Raise)
            patterns.later.soon(new_item_dialog, new_item_dialog.SetFocus)
        else:
            add_attachment = command.AddAttachmentCommand(
                self.presentation(), [item], attachments=attachments
            )
            add_attachment.do()
            # Open the item's editor on attachments tab, then open attachment editor
            self._open_item_editor_on_attachments_tab(item, attachments)

    def _open_item_editor_on_attachments_tab(self, item, new_attachments=None):
        """Open the item's editor on the attachments tab.

        If an editor for this item is already open, bring it to front and
        switch to the attachments tab. Otherwise, create a new editor.
        If new_attachments is provided, also open the AttachmentEditor
        for them.
        """
        from taskcoachlib.gui.dialog import editor
        from taskcoachlib.domain import note

        # Determine editor class based on item type
        if isinstance(item, task.Task):
            editor_class = editor.TaskEditor
            container = self.taskFile.tasks()
        elif isinstance(item, category.Category):
            editor_class = editor.CategoryEditor
            container = self.taskFile.categories()
        elif isinstance(item, note.Note):
            editor_class = editor.NoteEditor
            container = self.taskFile.notes()
        else:
            return

        # Search for an existing open editor for this item
        existing_editor = None
        for window in wx.GetTopLevelWindows():
            if isinstance(window, editor_class):
                # Check if this editor is editing our item
                if hasattr(window, "_items") and item in window._items:
                    existing_editor = window
                    break

        if existing_editor:
            # Bring to front and switch to attachments tab
            existing_editor.Raise()
            existing_editor.SetFocus()
            if hasattr(existing_editor, "_interior"):
                existing_editor._interior.setFocus("attachments")
            item_editor = existing_editor
        else:
            # Create a new editor with columnName="attachments"
            item_editor = editor_class(
                wx.GetTopLevelParent(self),
                [item],
                container,
                self.taskFile,
                icon_id="nuvola_actions_edit",
                columnName="attachments",
            )
            item_editor.Show()
            patterns.later.soon(item_editor, item_editor.Raise)
            patterns.later.soon(item_editor, item_editor.SetFocus)

        # Also open the AttachmentEditor for the new attachments
        if new_attachments:
            # Later, once the item editor is shown
            def openAttachmentEditor():
                # Wrap attachments in AttachmentList container for Editor
                # (item.attachments() returns a plain list)
                attachment_container = attachment.AttachmentList(
                    item.attachments()
                )
                attachment_editor = editor.AttachmentEditor(
                    item_editor,  # Parent to the item editor
                    new_attachments,
                    attachment_container,
                    self.taskFile,
                    icon_id="nuvola_actions_edit",
                    columnName="subject",  # Open on Description tab, not Notes
                )
                attachment_editor.Show()
                attachment_editor.Raise()
                attachment_editor.SetFocus()

            patterns.later.soon(item_editor, openAttachmentEditor)

    def on_drop_url(self, item, url, **kwargs):
        """This method is called by the widget when a URL is dropped on an
        item."""
        attachments = [attachment.URIAttachment(url)]
        self._add_attachments(attachments, item, **kwargs)

    def on_drop_files(self, item, filenames, **kwargs):
        """This method is called by the widget when one or more files
        are dropped on an item."""
        import os
        import urllib.request

        attachment_base = settings.file.attachmentbase
        attachments = []
        for filename in filenames:
            if os.path.isdir(filename):
                # Folders become URI attachments that open in file explorer
                folder_url = "file://" + urllib.request.pathname2url(filename)
                attachments.append(attachment.URIAttachment(folder_url))
            else:
                # Regular files become file attachments
                if attachment_base:
                    filename = attachment.getRelativePath(
                        filename, attachment_base
                    )
                attachments.append(attachment.FileAttachment(filename))
        self._add_attachments(attachments, item, **kwargs)

    def on_drop_mail(self, item, mails, **kwargs):
        """Called by the widget when mails are dropped on an item, with
        each mail's fields (mailer.mail_fields())."""
        self._add_attachments(
            [attachment.MailAttachment(**mail) for mail in mails],
            item,
            **kwargs,
        )


class NoteColumnMixin(object):
    def noteImageIndices(self, item):
        index = (
            image_list_cache.get_index("nuvola_apps_knotes")
            if item.notes()
            else -1
        )
        return {wx.TreeItemIcon_Normal: index}


class AttachmentColumnMixin(object):
    def attachmentImageIndices(self, item):  # pylint: disable=W0613
        index = (
            image_list_cache.get_index("nuvola_status_mail-attachment")
            if item.attachments()
            else -1
        )
        return {wx.TreeItemIcon_Normal: index}
