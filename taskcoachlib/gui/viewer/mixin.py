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
from taskcoachlib.domain import base, task, category, attachment
from taskcoachlib.gui import uicommand
import time

def _log(msg):
    print(f"[{time.time():.3f}] MIXIN: {msg}")
from taskcoachlib.i18n import _
from pubsub import pub
import ast
import wx


class SearchableViewerMixin(object):
    """A viewer that is searchable. This is a mixin class."""

    def isSearchable(self):
        return True

    def createFilter(self, presentation):
        presentation = super().createFilter(presentation)
        return base.SearchFilter(presentation, **self.searchOptions())

    def searchOptions(self):
        (
            searchString,
            matchCase,
            includeSubItems,
            searchDescription,
            regularExpression,
        ) = self.getSearchFilter()
        return dict(
            searchString=searchString,
            matchCase=matchCase,
            includeSubItems=includeSubItems,
            searchDescription=searchDescription,
            regularExpression=regularExpression,
            treeMode=self.isTreeViewer(),
        )

    def setSearchFilter(
        self,
        searchString,
        matchCase=False,
        includeSubItems=False,
        searchDescription=False,
        regularExpression=False,
    ):
        section = self.settingsSection()
        self.settings.set(section, "searchfilterstring", searchString)
        self.settings.set(section, "searchfiltermatchcase", str(matchCase))
        self.settings.set(
            section, "searchfilterincludesubitems", str(includeSubItems)
        )
        self.settings.set(section, "searchdescription", str(searchDescription))
        self.settings.set(section, "regularexpression", str(regularExpression))
        self.presentation().setSearchFilter(
            searchString,
            matchCase=matchCase,
            includeSubItems=includeSubItems,
            searchDescription=searchDescription,
            regularExpression=regularExpression,
        )

    def getSearchFilter(self):
        section = self.settingsSection()
        searchString = self.settings.get(section, "searchfilterstring")
        matchCase = self.settings.getboolean(section, "searchfiltermatchcase")
        includeSubItems = self.settings.getboolean(
            section, "searchfilterincludesubitems"
        )
        searchDescription = self.settings.getboolean(
            section, "searchdescription"
        )
        regularExpression = self.settings.getboolean(
            section, "regularexpression"
        )
        return (
            searchString,
            matchCase,
            includeSubItems,
            searchDescription,
            regularExpression,
        )

    def createToolBarUICommands(self):
        """UI commands to put on the toolbar of this viewer."""
        searchUICommand = uicommand.Search(viewer=self, settings=self.settings)
        return super().createToolBarUICommands() + (
            1,
            searchUICommand,
        )


class FilterableViewerMixin(object):
    """A viewer that is filterable. This is a mixin class."""

    def __init__(self, *args, **kwargs):
        self.__filterUICommands = None
        super().__init__(*args, **kwargs)

    def isFilterable(self):
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
            uicommand.CategoryViewerFilterChoice(settings=self.settings),
            None,
        ]

    def createToolBarUICommands(self):
        clearUICommand = uicommand.ResetFilter(viewer=self)
        return super().createToolBarUICommands() + (clearUICommand,)

    def resetFilter(self):
        self.taskFile.categories().resetAllFilteredCategories()

    def hasFilter(self):
        return bool(self.taskFile.categories().filteredCategories())

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
            uicommand.ToggleCategoryFilter(category=eachCategory)
            for eachCategory in categories
        ]
        categoriesWithChildren = [
            eachCategory
            for eachCategory in categories
            if eachCategory.children()
        ]
        if categoriesWithChildren:
            commands.append(None)
            for eachCategory in categoriesWithChildren:
                subCommands = [
                    _("%s (subcategories)") % eachCategory.subject()
                ]
                subCommands.extend(
                    self.createToggleCategoryFilterCommands(
                        eachCategory.children()
                    )
                )
                commands.append(tuple(subCommands))
        return commands


class FilterableViewerForCategorizablesMixin(FilterableViewerMixin):
    def createFilter(self, items):
        items = super(
            FilterableViewerForCategorizablesMixin, self
        ).createFilter(items)
        filterOnlyWhenAllCategoriesMatch = self.settings.getboolean(
            "view", "categoryfiltermatchall"
        )
        return category.filter.CategoryFilter(
            items,
            categories=self.taskFile.categories(),
            treeMode=self.isTreeViewer(),
            filterOnlyWhenAllCategoriesMatch=filterOnlyWhenAllCategoriesMatch,
        )


class FilterableViewerForTasksMixin(FilterableViewerForCategorizablesMixin):
    def createFilter(self, taskList):
        taskList = super().createFilter(taskList)
        return task.filter.ViewFilter(
            taskList, treeMode=self.isTreeViewer(), **self.viewFilterOptions()
        )

    def viewFilterOptions(self):
        return dict(
            hideCompositeTasks=self.isHidingCompositeTasks(),
            statusesToHide=self.hiddenTaskStatuses(),
        )

    def hideTaskStatus(self, status, hide=True):
        self.__setBooleanSetting("hide%stasks" % status, hide)
        self.presentation().hideTaskStatus(status, hide)

    def showOnlyTaskStatus(self, status):
        for taskStatus in task.Task.possibleStatuses():
            self.hideTaskStatus(taskStatus, hide=status != taskStatus)

    def isHidingTaskStatus(self, status):
        return self.__getBooleanSetting("hide%stasks" % status)

    def hiddenTaskStatuses(self):
        return [
            status
            for status in task.Task.possibleStatuses()
            if self.isHidingTaskStatus(status)
        ]

    def hideCompositeTasks(self, hide=True):
        self.__setBooleanSetting("hidecompositetasks", hide)
        self.presentation().hideCompositeTasks(hide)

    def isHidingCompositeTasks(self):
        return self.__getBooleanSetting("hidecompositetasks")

    def resetFilter(self):
        super().resetFilter()
        for status in task.Task.possibleStatuses():
            self.hideTaskStatus(status, False)
        if not self.isTreeViewer():
            # Only reset this filter when in list mode, since it only applies
            # to list mode
            self.hideCompositeTasks(False)

    def hasFilter(self):
        return super().hasFilter() or self.presentation().hasFilter()

    def createFilterUICommands(self):
        return (
            super().createFilterUICommands()
            + [
                uicommand.ViewerHideTasks(
                    taskStatus, viewer=self, settings=self.settings
                )
                for taskStatus in task.Task.possibleStatuses()
            ]
            + [uicommand.ViewerHideCompositeTasks(viewer=self)]
        )

    def __getBooleanSetting(self, setting):
        return self.settings.getboolean(self.settingsSection(), setting)

    def __setBooleanSetting(self, setting, booleanValue):
        self.settings.setboolean(self.settingsSection(), setting, booleanValue)


class SortableViewerMixin(object):
    """A viewer that is sortable. This is a mixin class."""

    def __init__(self, *args, **kwargs):
        self._sortUICommands = []
        super().__init__(*args, **kwargs)

    def isSortable(self):
        return True

    def registerPresentationObservers(self):
        super().registerPresentationObservers()
        pub.subscribe(
            self.onSortOrderChanged, self.presentation().sortEventType()
        )

    def detach(self):
        super().detach()
        pub.unsubscribe(
            self.onSortOrderChanged, self.presentation().sortEventType()
        )

    def onSortOrderChanged(self, sender):
        _log(f"onSortOrderChanged START")
        if sender == self.presentation():
            # For virtual lists, refresh visible area and sync count.
            if hasattr(self.widget, 'RefreshVisibleItems'):
                _log(f"onSortOrderChanged: calling RefreshVisibleItems")
                self.widget.RefreshVisibleItems(len(self.presentation()))
            else:
                _log(f"onSortOrderChanged: calling refresh()")
                self.refresh()
            # Re-sync widget selection: items may have moved to different
            # indices after sorting, so update widget with the cached selection
            _log(f"onSortOrderChanged: calling widget.select")
            self.widget.select(self.curselection())
            self.updateSelection(sendViewerStatusEvent=False)
            self.sendViewerStatusEvent()
        _log(f"onSortOrderChanged END")

    def createSorter(self, presentation):
        return self.SorterClass(presentation, **self.sorterOptions())

    def sorterOptions(self):
        return dict(
            sortBy=self.sortKey(), sortCaseSensitive=self.isSortCaseSensitive()
        )

    def sortBy(self, sortKey):
        self.presentation().sortBy(sortKey)
        self.settings.set(
            self.settingsSection(),
            "sortby",
            str(self.presentation().sortKeys()),
        )

    def isSortedBy(self, sortKey):
        sortKeys = self.presentation().sortKeys()
        return sortKeys and (
            sortKeys[0] == sortKey or sortKeys[0] == "-" + sortKey
        )

    def sortKey(self):
        return ast.literal_eval(self.settings.get(self.settingsSection(), "sortby"))

    def isSortOrderAscending(self):
        sortKeys = self.presentation().sortKeys()
        return sortKeys and not sortKeys[0].startswith("-")

    def setSortOrderAscending(self, ascending=True):
        self.presentation().sortAscending(ascending)
        self.settings.set(
            self.settingsSection(),
            "sortby",
            str(self.presentation().sortKeys()),
        )

    def isSortCaseSensitive(self):
        return self.settings.getboolean(
            self.settingsSection(), "sortcasesensitive"
        )

    def setSortCaseSensitive(self, sortCaseSensitive=True):
        self.settings.set(
            self.settingsSection(), "sortcasesensitive", str(sortCaseSensitive)
        )
        self.presentation().sortCaseSensitive(sortCaseSensitive)

    def getSortUICommands(self):
        if not self._sortUICommands:
            self.createSortUICommands()
        return self._sortUICommands

    def createSortUICommands(self):
        """(Re)Create the UICommands for sorting. These UICommands are put
        in the View->Sort menu and are used when the user clicks a column
        header."""
        self._sortUICommands = self.createSortOrderUICommands()
        sortByCommands = self.createSortByUICommands()
        if sortByCommands:
            self._sortUICommands.append(None)  # Separator
            self._sortUICommands.extend(sortByCommands)

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
                menuText=_("Sub&ject"),
                helpText=self.sortBySubjectHelpText,
            ),
            uicommand.ViewerSortByCommand(
                viewer=self,
                value="description",
                menuText=_("&Description"),
                helpText=self.sortByDescriptionHelpText,
            ),
            uicommand.ViewerSortByCommand(
                viewer=self,
                value="creationDateTime",
                menuText=_("&Creation date"),
                helpText=self.sortByCreationDateTimeHelpText,
            ),
            uicommand.ViewerSortByCommand(
                viewer=self,
                value="modificationDateTime",
                menuText=_("&Modification date"),
                helpText=self.sortByModificationDateTimeHelpText,
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
        if "sort" not in self.viewerImages:
            self.viewerImages = self.viewerImages + ["sort"]
        super().__init__(*args, **kwargs)

    def createSortByUICommands(self):
        return [
            uicommand.ViewerSortByCommand(
                viewer=self,
                value="ordering",
                menuText=_("&Manual ordering"),
                helpText=self.sortByOrderingHelpText,
            )
        ] + super().createSortByUICommands()

    def orderingImageIndices(self, item):
        index = self.imageIndex["sort"]
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
                menuText=_("&Category"),
                helpText=self.sortByCategoryHelpText,
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

    def sortBy(self, sortKey):
        # If the user clicks the same column for the third time, toggle
        # the SortyByTaskStatusFirst setting:
        if self.isSortedBy(sortKey):
            self.__sortKeyUnchangedCount += 1
        else:
            self.__sortKeyUnchangedCount = 0
        if self.__sortKeyUnchangedCount > 1:
            self.setSortByTaskStatusFirst(not self.isSortByTaskStatusFirst())
            self.__sortKeyUnchangedCount = 0
        super().sortBy(sortKey)

    def isSortByTaskStatusFirst(self):
        return self.settings.getboolean(
            self.settingsSection(), "sortbystatusfirst"
        )

    def setSortByTaskStatusFirst(self, sortByTaskStatusFirst):
        self.settings.set(
            self.settingsSection(),
            "sortbystatusfirst",
            str(sortByTaskStatusFirst),
        )
        self.presentation().sortByTaskStatusFirst(sortByTaskStatusFirst)

    def sorterOptions(self):
        options = super().sorterOptions()
        options.update(
            treeMode=self.isTreeViewer(),
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
        dependsOnEffortFeature = [
            "budget",
            "timeSpent",
            "budgetLeft",
            "hourlyFee",
            "fixedFee",
            "revenue",
        ]
        for menuText, helpText, value in [
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
            if value not in dependsOnEffortFeature or (
                value in dependsOnEffortFeature
            ):
                commands.append(
                    uicommand.ViewerSortByCommand(
                        viewer=self,
                        value=value,
                        menuText=menuText,
                        helpText=helpText,
                    )
                )
        return commands


class AttachmentDropTargetMixin(object):
    """Mixin class for viewers that are drop targets for attachments."""

    def widgetCreationKeywordArguments(self):
        kwargs = super(
            AttachmentDropTargetMixin, self
        ).widgetCreationKeywordArguments()
        kwargs["onDropURL"] = self.onDropURL
        kwargs["onDropFiles"] = self.onDropFiles
        kwargs["onDropMail"] = self.onDropMail
        return kwargs

    def _addAttachments(self, attachments, item, **itemDialogKwargs):
        """Add attachments. If item refers to an existing domain object,
        add the attachments to that object. If item is None, use the
        newItemDialog to create a new domain object and add the attachments
        to that new object."""
        if item is None:
            itemDialogKwargs["subject"] = attachments[0].subject()
            if self.settings.get(
                "view", "defaultplannedstartdatetime"
            ).startswith("preset"):
                itemDialogKwargs["plannedStartDateTime"] = (
                    task.Task.suggestedPlannedStartDateTime()
                )
            if self.settings.get("view", "defaultduedatetime").startswith(
                "preset"
            ):
                itemDialogKwargs["dueDateTime"] = (
                    task.Task.suggestedDueDateTime()
                )
            if self.settings.get(
                "view", "defaultactualstartdatetime"
            ).startswith("preset"):
                itemDialogKwargs["actualStartDateTime"] = (
                    task.Task.suggestedActualStartDateTime()
                )
            if self.settings.get(
                "view", "defaultcompletiondatetime"
            ).startswith("preset"):
                itemDialogKwargs["completionDateTime"] = (
                    task.Task.suggestedCompletionDateTime()
                )
            if self.settings.get("view", "defaultreminderdatetime").startswith(
                "preset"
            ):
                itemDialogKwargs["reminder"] = (
                    task.Task.suggestedReminderDateTime()
                )
            newItemDialog = self.newItemDialog(
                bitmap="new", attachments=attachments, **itemDialogKwargs
            )
            newItemDialog.Show()
        else:
            addAttachment = command.AddAttachmentCommand(
                self.presentation(), [item], attachments=attachments
            )
            addAttachment.do()

    def onDropURL(self, item, url, **kwargs):
        """This method is called by the widget when a URL is dropped on an
        item."""
        attachments = [attachment.URIAttachment(url)]
        self._addAttachments(attachments, item, **kwargs)

    def onDropFiles(self, item, filenames, **kwargs):
        """This method is called by the widget when one or more files
        are dropped on an item."""
        attachmentBase = self.settings.get("file", "attachmentbase")
        if attachmentBase:
            filenames = [
                attachment.getRelativePath(filename, attachmentBase)
                for filename in filenames
            ]
        attachments = [
            attachment.FileAttachment(filename) for filename in filenames
        ]
        self._addAttachments(attachments, item, **kwargs)

    def onDropMail(self, item, mail, **kwargs):
        """This method is called by the widget when a mail message is dropped
        on an item."""
        att = attachment.MailAttachment(mail)
        subject, content = att.read()
        self._addAttachments(
            [att], item, subject=subject, description=content, **kwargs
        )


class NoteColumnMixin(object):
    def noteImageIndices(self, item):
        index = self.imageIndex["note_icon"] if item.notes() else -1
        return {wx.TreeItemIcon_Normal: index}


class AttachmentColumnMixin(object):
    def attachmentImageIndices(self, item):  # pylint: disable=W0613
        index = self.imageIndex["paperclip_icon"] if item.attachments() else -1
        return {wx.TreeItemIcon_Normal: index}
