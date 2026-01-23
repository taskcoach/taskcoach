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

from taskcoachlib import command, widgets, domain, render
from taskcoachlib.domain import effort, date
from taskcoachlib.domain.base import filter  # pylint: disable=W0622
from taskcoachlib.gui import uicommand, dialog
import taskcoachlib.gui.menu
from taskcoachlib.i18n import _
from pubsub import pub
from . import base
from . import mixin
from . import refresher
import wx


class EffortViewer(
    base.ListViewer,
    mixin.FilterableViewerForCategorizablesMixin,
    mixin.SortableViewerForEffortMixin,
    mixin.SearchableViewerMixin,
    base.SortableViewerWithColumns,
):
    defaultTitle = _("Effort")
    defaultBitmap = "clock_icon"
    coreObjectType = "efforts"
    SorterClass = effort.EffortSorter

    def __init__(self, parent, taskFile, settings, *args, **kwargs):
        kwargs.setdefault("settingsSection", "effortviewer")
        self.__tasksToShowEffortFor = kwargs.pop("tasksToShowEffortFor", [])
        self.aggregation = (
            "details"  # Temporary value, will be properly set below
        )
        self.__hiddenWeekdayColumns = []
        self.__hiddenTotalColumns = []
        self.__columnUICommands = None
        self.__domainObjectsToView = None
        super().__init__(parent, taskFile, settings, *args, **kwargs)
        self.secondRefresher = refresher.SecondRefresher(
            self, effort.Effort.trackingChangedEventType()
        )
        self.aggregation = settings.get(self.settingsSection(), "aggregation")
        self.__initModeToolBarUICommands()
        self.registerObserver(
            self.onAttributeChanged_Deprecated,
            eventType=effort.Effort.appearanceChangedEventType(),
        )
        pub.subscribe(
            self.onRoundingChanged,
            "settings.%s.round" % self.settingsSection(),
        )
        pub.subscribe(
            self.onRoundingChanged,
            "settings.%s.alwaysroundup" % self.settingsSection(),
        )
        pub.subscribe(
            self.onRoundingChanged,
            "settings.%s.consolidateeffortspertask" % self.settingsSection(),
        )
        pub.subscribe(
            self.on_aggregation_changed,
            "settings.%s.aggregation" % self.settingsSection(),
        )
        pub.subscribe(
            self.onHourDisplayChanged, "settings.feature.decimaltime"
        )

    def selectableColumns(self):
        columns = list()
        for column in self.columns():
            if (
                column.name().startswith("total")
                and self.aggregation == "details"
            ):
                continue
            if (
                column.name()
                in [
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ]
                and self.aggregation != "week"
            ):
                continue
            columns.append(column)
        return columns

    def tasksToShowEffortFor(self):
        return self.__tasksToShowEffortFor

    def onRoundingChanged(self, value):  # pylint: disable=W0613
        self.__initRoundingToolBarUICommands()
        self.refresh()

    def onHourDisplayChanged(self, value):
        self.refresh()

    def __initModeToolBarUICommands(self):
        self.aggregationUICommand.setChoice(self.aggregation)
        self.__initRoundingToolBarUICommands()

    def __initRoundingToolBarUICommands(self):
        aggregated = self.isShowingAggregatedEffort()
        rounding = self.__round_precision() if aggregated else 0
        self.roundingUICommand.setChoice(rounding)
        self.roundingUICommand.enable(aggregated)
        self.alwaysRoundUpUICommand.setValue(self.__always_round_up())
        self.alwaysRoundUpUICommand.enable(aggregated and rounding != 0)
        self.consolidateEffortsPerTaskUICommand.setValue(
            self.__consolidate_efforts_per_task()
        )
        self.consolidateEffortsPerTaskUICommand.enable(
            aggregated and rounding != 0
        )

    def domainObjectsToView(self):
        if self.__domainObjectsToView is None:
            if self.__displayingNewTasks():
                tasks = self.tasksToShowEffortFor()
            else:
                tasks = domain.base.SelectedItemsFilter(
                    self.taskFile.tasks(),
                    selectedItems=self.tasksToShowEffortFor(),
                )
            self.__domainObjectsToView = tasks
        return self.__domainObjectsToView

    def __displayingNewTasks(self):
        return any(
            [
                task not in self.taskFile.tasks()
                for task in self.tasksToShowEffortFor()
            ]
        )

    def detach(self):
        super().detach()
        self.secondRefresher.removeInstance()

    def isShowingEffort(self):
        return True

    def curselectionIsInstanceOf(self, class_):
        return class_ == effort.Effort

    def getSupportedPasteTypes(self):
        return (effort.Effort,)

    def pasteItemCommand(self):
        """Paste efforts from clipboard to the target task.

        When this viewer is showing efforts for a specific task (e.g., in task
        editor), pasted efforts are added to that task.
        """
        from taskcoachlib.command.clipboard import Clipboard
        items, source = Clipboard().get()
        tasks = self.tasksToShowEffortFor()
        if tasks:
            # Paste to the specific task this viewer is showing efforts for
            target_task = list(tasks)[0] if hasattr(tasks, '__iter__') else tasks
            copies = [item.copy() for item in items]
            return command.AddEffortCommand(
                None, [target_task], efforts=copies
            )
        # Fall back to generic paste when no specific target task
        return super().pasteItemCommand()

    def on_aggregation_changed(self, value):
        self.__show_effort_aggregation(value)

    def __show_effort_aggregation(self, aggregation):
        """Change the aggregation mode. Can be one of 'details', 'day', 'week'
        and 'month'."""
        assert aggregation in ("details", "day", "week", "month")
        self.aggregation = aggregation
        self._refresh()

    def _refresh(self, clear=False):
        if clear:
            self.__domainObjectsToView = None
        self.setPresentation(
            self.createSorter(self.createFilter(self.domainObjectsToView()))
        )
        self.secondRefresher.updatePresentation()
        self.registerPresentationObservers()
        # Invalidate the UICommands used for the column popup menu:
        self.__columnUICommands = None
        # Clear the selection to remove the cached selection
        self.clear_selection()
        # If the widget is auto-resizing columns, turn it off temporarily to
        # make removing/adding columns faster
        autoResizing = self.widget.IsAutoResizing()
        if autoResizing:
            self.widget.ToggleAutoResizing(False)
        # Refresh first so that the list control doesn't think there are more
        # efforts than there really are when switching from aggregate mode to
        # detail mode.
        self.refresh()
        self._showWeekdayColumns(show=self.aggregation == "week")
        self._showTotalColumns(show=self.aggregation != "details")
        if autoResizing:
            self.widget.ToggleAutoResizing(True)
        self.__initRoundingToolBarUICommands()
        pub.sendMessage("effortviewer.aggregation")

    def isShowingAggregatedEffort(self):
        return self.aggregation != "details"

    def createFilter(self, taskList):
        """Return a class that filters the original list. In this case we
        create an effort aggregator that aggregates the effort records in
        the taskList, either individually (i.e. no aggregation), per day,
        per week, or per month."""
        aggregation = self.settings.get(self.settingsSection(), "aggregation")
        deletedFilter = filter.DeletedFilter(taskList)
        categoryFilter = super().createFilter(deletedFilter)
        searchFilter = filter.SearchFilter(
            self.createAggregator(categoryFilter, aggregation)
        )
        return searchFilter

    def createAggregator(self, taskList, aggregation):
        """Return an instance of a class that aggregates the effort records
        in the taskList, either:
        - individually (aggregation == 'details'),
        - per day (aggregation == 'day'),
        - per week ('week'), or
        - per month ('month')."""
        if aggregation == "details":
            aggregator = effort.EffortList(taskList)
        else:
            aggregator = effort.EffortAggregator(
                taskList, aggregation=aggregation
            )
        return aggregator

    def createWidget(self):
        imageList = self.createImageList()  # Has side-effects
        self._columns = self._createColumns()  # pylint: disable=W0201
        itemPopupMenu = taskcoachlib.gui.menu.EffortPopupMenu(
            self.parent,
            self.taskFile.tasks(),
            self.taskFile.efforts(),
            self.settings,
            self,
        )
        columnPopupMenu = taskcoachlib.gui.menu.EffortViewerColumnPopupMenu(
            self
        )
        self._popupMenus.extend([itemPopupMenu, columnPopupMenu])
        widget = widgets.VirtualListCtrl(
            self,
            self.columns(),
            self.onSelect,
            uicommand.Edit(viewer=self),
            itemPopupMenu,
            columnPopupMenu,
            resizeableColumn=1,
            **self.widgetCreationKeywordArguments()
        )
        widget.AssignImageList(
            imageList, wx.IMAGE_LIST_SMALL
        )  # pylint: disable=E1101
        return widget

    def _createColumns(self):
        # pylint: disable=W0142
        kwargs = dict(resizeCallback=self.onResizeColumn)

        return (
            [
                widgets.Column(
                    name,
                    columnHeader,
                    eventType,
                    renderCallback=renderCallback,
                    sortCallback=sortCallback,
                    width=self.getColumnWidth(name),
                    **kwargs
                )
                for name, columnHeader, eventType, renderCallback, sortCallback in [
                    (
                        "period",
                        _("Period"),
                        effort.Effort.durationChangedEventType(),
                        self.__renderPeriod,
                        uicommand.ViewerSortByCommand(
                            viewer=self, value="period"
                        ),
                    ),
                    (
                        "task",
                        _("Task"),
                        effort.Effort.taskChangedEventType(),
                        lambda effort: effort.task().subject(recursive=True),
                        None,
                    ),
                    (
                        "description",
                        _("Description"),
                        effort.Effort.descriptionChangedEventType(),
                        lambda effort: effort.description(),
                        None,
                    ),
                ]
            ]
            + [
                widgets.Column(
                    "categories",
                    _("Categories"),
                    width=self.getColumnWidth("categories"),
                    renderCallback=self.renderCategories,
                    **kwargs
                )
            ]
            + [
                widgets.Column(
                    name,
                    columnHeader,
                    eventType,
                    width=self.getColumnWidth(name),
                    renderCallback=renderCallback,
                    alignment=wx.LIST_FORMAT_RIGHT,
                    **kwargs
                )
                for name, columnHeader, eventType, renderCallback in [
                    (
                        "timeSpent",
                        _("Time spent"),
                        effort.Effort.durationChangedEventType(),
                        self.__renderTimeSpent,
                    ),
                    (
                        "totalTimeSpent",
                        _("Total time spent"),
                        effort.Effort.durationChangedEventType(),
                        self.__renderTotalTimeSpent,
                    ),
                    (
                        "revenue",
                        _("Revenue"),
                        effort.Effort.revenueChangedEventType(),
                        self.__renderRevenue,
                    ),
                    (
                        "totalRevenue",
                        _("Total revenue"),
                        effort.Effort.revenueChangedEventType(),
                        self.__renderTotalRevenue,
                    ),
                ]
            ]
            + [
                widgets.Column(
                    name,
                    columnHeader,
                    eventType,
                    renderCallback=renderCallback,
                    alignment=wx.LIST_FORMAT_RIGHT,
                    width=self.getColumnWidth(name),
                    **kwargs
                )
                for name, columnHeader, eventType, renderCallback in [
                    (
                        "monday",
                        _("Monday"),
                        effort.Effort.durationChangedEventType(),
                        lambda effort: self.__renderTimeSpentOnDay(effort, 0),
                    ),
                    (
                        "tuesday",
                        _("Tuesday"),
                        effort.Effort.durationChangedEventType(),
                        lambda effort: self.__renderTimeSpentOnDay(effort, 1),
                    ),
                    (
                        "wednesday",
                        _("Wednesday"),
                        effort.Effort.durationChangedEventType(),
                        lambda effort: self.__renderTimeSpentOnDay(effort, 2),
                    ),
                    (
                        "thursday",
                        _("Thursday"),
                        effort.Effort.durationChangedEventType(),
                        lambda effort: self.__renderTimeSpentOnDay(effort, 3),
                    ),
                    (
                        "friday",
                        _("Friday"),
                        effort.Effort.durationChangedEventType(),
                        lambda effort: self.__renderTimeSpentOnDay(effort, 4),
                    ),
                    (
                        "saturday",
                        _("Saturday"),
                        effort.Effort.durationChangedEventType(),
                        lambda effort: self.__renderTimeSpentOnDay(effort, 5),
                    ),
                    (
                        "sunday",
                        _("Sunday"),
                        effort.Effort.durationChangedEventType(),
                        lambda effort: self.__renderTimeSpentOnDay(effort, 6),
                    ),
                ]
            ]
            + [
                widgets.Column(
                    "id",
                    _("ID"),
                    width=self.getColumnWidth("id"),
                    renderCallback=lambda effort: effort.id(),
                    sortCallback=uicommand.ViewerSortByCommand(
                        viewer=self, value="id"
                    ),
                    **kwargs
                )
            ]
        )

    def _showWeekdayColumns(self, show=True):
        if show:
            columnsToShow = self.__hiddenWeekdayColumns[:]
            self.__hiddenWeekdayColumns = []
        else:
            self.__hiddenWeekdayColumns = columnsToShow = [
                column
                for column in self.visibleColumns()
                if column.name()
                in [
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ]
            ]
        for column in columnsToShow:
            self.showColumn(column, show, refresh=False)

    def _showTotalColumns(self, show=True):
        if show:
            columnsToShow = self.__hiddenTotalColumns[:]
            self.__hiddenTotalColumns = []
        else:
            self.__hiddenTotalColumns = columnsToShow = [
                column
                for column in self.visibleColumns()
                if column.name().startswith("total")
            ]
        for column in columnsToShow:
            self.showColumn(column, show, refresh=False)

    def getColumnUICommands(self):
        # Create new UI commands every time since the UI commands depend on the
        # aggregation mode
        columnUICommands = [
            uicommand.ToggleAutoColumnResizing(
                viewer=self, settings=self.settings
            ),
            None,
            uicommand.ViewColumn(
                menuText=_("&Description"),
                helpText=_("Show/hide description column"),
                setting="description",
                viewer=self,
            ),
            uicommand.ViewColumn(
                menuText=_("&Categories"),
                helpText=_("Show/hide categories column"),
                setting="categories",
                viewer=self,
            ),
            uicommand.ViewColumn(
                menuText=_("&Time spent"),
                helpText=_("Show/hide time spent column"),
                setting="timeSpent",
                viewer=self,
            ),
            uicommand.ViewColumn(
                menuText=_("&Revenue"),
                helpText=_("Show/hide revenue column"),
                setting="revenue",
                viewer=self,
            ),
        ]
        if self.aggregation != "details":
            columnUICommands.insert(
                5,
                uicommand.ViewColumn(
                    menuText=_("&Total time spent"),
                    helpText=_("Show/hide total time spent column"),
                    setting="totalTimeSpent",
                    viewer=self,
                ),
            )
            columnUICommands.insert(
                7,
                uicommand.ViewColumn(
                    menuText=_("&Total revenue"),
                    helpText=_("Show/hide total revenue column"),
                    setting="totalRevenue",
                    viewer=self,
                ),
            )
        if self.aggregation == "week":
            columnUICommands.append(
                uicommand.ViewColumns(
                    menuText=_("Effort per weekday"),
                    helpText=_("Show/hide time spent per weekday columns"),
                    setting=[
                        "monday",
                        "tuesday",
                        "wednesday",
                        "thursday",
                        "friday",
                        "saturday",
                        "sunday",
                    ],
                    viewer=self,
                )
            )
        columnUICommands.append(
            uicommand.ViewColumn(
                menuText=_("&ID"),
                helpText=_("Show/hide ID column"),
                setting="id",
                viewer=self,
            )
        )
        return columnUICommands

    def createCreationToolBarUICommands(self):
        return (
            uicommand.EffortNew(
                viewer=self,
                effortList=self.presentation(),
                taskList=self.taskFile.tasks(),
                settings=self.settings,
            ),
        )

    def createActionToolBarUICommands(self):
        tasks = self.taskFile.tasks()
        return (
            uicommand.EffortStartForEffort(viewer=self, taskList=tasks),
            uicommand.EffortStop(
                viewer=self, effortList=self.taskFile.efforts(), taskList=tasks
            ),
        )

    def createModeToolBarUICommands(self):
        # These are instance variables so that the choice can be changed
        # programmatically
        # pylint: disable=W0201
        self.aggregationUICommand = uicommand.EffortViewerAggregationChoice(
            viewer=self, settings=self.settings
        )
        self.roundingUICommand = uicommand.RoundingPrecision(
            viewer=self, settings=self.settings
        )
        self.alwaysRoundUpUICommand = uicommand.AlwaysRoundUp(
            viewer=self, settings=self.settings
        )
        self.consolidateEffortsPerTaskUICommand = (
            uicommand.ConsolidateEffortsPerTask(
                viewer=self, settings=self.settings
            )
        )
        return (
            self.aggregationUICommand,
            self.roundingUICommand,
            self.alwaysRoundUpUICommand,
            self.consolidateEffortsPerTaskUICommand,
        )

    def supportsRounding(self):
        return True

    def getRoundingUICommands(self):
        return (
            [
                uicommand.AlwaysRoundUp(viewer=self, settings=self.settings),
                None,
            ]
            + [
                uicommand.ConsolidateEffortsPerTask(
                    viewer=self, settings=self.settings
                ),
                None,
            ]
            + [
                uicommand.RoundBy(
                    menuText=menuText,
                    value=value,
                    viewer=self,
                    settings=self.settings,
                )
                for (menuText, value) in zip(
                    uicommand.RoundingPrecision.choiceLabels,
                    uicommand.RoundingPrecision.choiceData,
                )
            ]
        )

    def hasModes(self):
        return True

    def getModeUICommands(self):
        return [_("Effort aggregation"), None] + [
            uicommand.EffortViewerAggregationOption(
                menuText=menuText,
                value=value,
                viewer=self,
                settings=self.settings,
            )
            for (menuText, value) in zip(
                uicommand.EffortViewerAggregationChoice.choiceLabels,
                uicommand.EffortViewerAggregationChoice.choiceData,
            )
        ]

    def getItemImages(self, index, column=0):  # pylint: disable=W0613
        return {wx.TreeItemIcon_Normal: -1}

    def curselection(self, forceUpdate=False):
        selection = super().curselection(forceUpdate=forceUpdate)
        if self.aggregation != "details":
            selection = [
                anEffort
                for compositeEffort in selection
                for anEffort in compositeEffort
            ]
        return selection

    def isselected(self, item):
        """When this viewer is in aggregation mode, L{curselection}
        returns the actual underlying L{Effort} objects instead of
        aggregates. This is a problem e.g. when exporting only a
        selection, since items we're iterating over (aggregates) are
        never in curselection(). This method is used instead. It just
        ignores the overridden version of curselection."""

        return item in super().curselection()

    def __sumTimeSpent(self, efforts):
        td = date.TimeDelta()
        for effort in efforts:
            td = td + effort.duration()

        sumTimeSpent = render.timeSpent(
            td,
            showSeconds=self.__show_seconds(),
            decimal=self.settings.getboolean("feature", "decimaltime"),
        )

        if sumTimeSpent == "":
            if self.settings.getboolean("feature", "decimaltime"):
                sumTimeSpent = "0.0"
            elif self.__show_seconds():
                sumTimeSpent = "0:00:00"
            else:
                sumTimeSpent = "0:00"
        return sumTimeSpent

    def statusMessages(self):
        status1 = _(
            "Effort: %d selected, %d visible, %d total. Time spent: %s selected, %s visible, %s total"
        ) % (
            len(self.curselection()),
            len(self.presentation()),
            len(self.taskFile.efforts()),
            self.__sumTimeSpent(self.curselection()),
            self.__sumTimeSpent(self.presentation()),
            self.__sumTimeSpent(self.taskFile.efforts()),
        )
        status2 = (
            _("Status: %d tracking") % self.presentation().nrBeingTracked()
        )
        return status1, status2

    def newItemDialog(self, *args, **kwargs):
        selectedTasks = kwargs.get("selectedTasks", [])
        bitmap = kwargs.get("bitmap", "new")
        if not selectedTasks:
            subjectDecoratedTaskList = [
                (task.subject(recursive=True), task)
                for task in self.tasksToShowEffortFor()
            ]
            subjectDecoratedTaskList.sort()  # Sort by subject
            selectedTasks = [subjectDecoratedTaskList[0][1]]
        return super().newItemDialog(selectedTasks, bitmap=bitmap)

    def itemEditorClass(self):
        return dialog.editor.EffortEditor

    def newItemCommandClass(self):
        return command.NewEffortCommand

    def newSubItemCommandClass(self):
        pass  # efforts are not composite.

    def deleteItemCommandClass(self):
        return command.DeleteEffortCommand

    # Rendering

    periodRenderers = dict(
        details=lambda anEffort, humanReadable=True: render.dateTimePeriod(
            anEffort.getStart(),
            anEffort.getStop(),
            humanReadable=humanReadable,
        ),
        day=lambda anEffort, humanReadable=True: render.date(
            anEffort.getStart(), humanReadable=humanReadable
        ),
        week=lambda anEffort, humanReadable=True: render.weekNumber(
            anEffort.getStart()
        ),
        month=lambda anEffort, humanReadable=True: render.month(
            anEffort.getStart()
        ),
    )

    def __renderPeriod(self, anEffort, humanReadable=True):
        """Return the period the effort belongs to. This depends on the
        current aggregation. If this period is the same as the previous
        period, an empty string is returned."""
        return (
            ""
            if self.__hasRepeatedPeriod(anEffort)
            else self.periodRenderers[self.aggregation](
                anEffort, humanReadable=humanReadable
            )
        )

    def __hasRepeatedPeriod(self, anEffort):
        """Return whether the effort has the same period as the previous
        effort record."""
        index = self.presentation().index(anEffort)
        previousEffort = index > 0 and self.presentation()[index - 1] or None
        if not previousEffort:
            return False
        if anEffort.getStart() != previousEffort.getStart():
            # Starts are not equal, so period cannot be repeated
            return False
        if self.isShowingAggregatedEffort():
            # Starts and length of period are equal, so period is repeated
            return True
        # If we get here, we are in details mode and the starts are equal
        # Period can only be repeated when the stop times are also equal
        return anEffort.getStop() == previousEffort.getStop()

    def __renderTimeSpent(self, anEffort):
        """Return a rendered version of the effort duration."""
        kwargs = dict()
        if isinstance(anEffort, effort.BaseCompositeEffort):
            kwargs["rounding"] = self.__round_precision()
            kwargs["roundUp"] = self.__always_round_up()
        duration = anEffort.duration(**kwargs)
        # Check for aggregation because we never round in details mode
        if self.isShowingAggregatedEffort():
            duration = self.__round_duration(duration)
            showSeconds = self.__show_seconds()
        else:
            showSeconds = True
        return render.timeSpent(
            duration,
            showSeconds=showSeconds,
            decimal=self.settings.getboolean("feature", "decimaltime"),
        )

    def __renderTotalTimeSpent(self, anEffort):
        """Return a rendered version of the effort total duration (of
        composite efforts)."""
        # No need to check for aggregation because this method is only used
        # in aggregated mode
        total_duration = anEffort.duration(
            recursive=True,
            rounding=self.__round_precision(),
            roundUp=self.__always_round_up(),
            consolidate=self.__consolidate_efforts_per_task(),
        )
        return render.timeSpent(
            total_duration,
            showSeconds=self.__show_seconds(),
            decimal=self.settings.getboolean("feature", "decimaltime"),
        )

    def __renderTimeSpentOnDay(self, anEffort, dayOffset):
        """Return a rendered version of the duration of the effort on a
        specific day."""
        kwargs = dict()
        if isinstance(anEffort, effort.BaseCompositeEffort):
            kwargs["rounding"] = self.__round_precision()
            kwargs["roundUp"] = self.__always_round_up()
            kwargs["consolidate"] = self.__consolidate_efforts_per_task()
        duration = (
            anEffort.durationDay(dayOffset, **kwargs)
            if self.aggregation == "week"
            else date.TimeDelta()
        )
        return render.timeSpent(
            self.__round_duration(duration),
            showSeconds=self.__show_seconds(),
            decimal=self.settings.getboolean("feature", "decimaltime"),
        )

    def getItemTooltipData(self, item):
        result = super().getItemTooltipData(item)
        if isinstance(item, effort.CompositeEffort) and len(item):
            details = [_("Details:")]
            for theEffort in item:
                details.append(
                    "%s (%s)"
                    % (
                        render.dateTimePeriod(
                            theEffort.getStart(),
                            theEffort.getStop(),
                            humanReadable=True,
                        ),
                        self.__renderTimeSpent(theEffort),
                    )
                )
            result.append((None, details))
        return result

    @staticmethod
    def __renderRevenue(anEffort):
        """Return the revenue of the effort as a monetary value."""
        return render.monetaryAmount(anEffort.revenue())

    @staticmethod
    def __renderTotalRevenue(anEffort):
        """Return the total revenue of the effort as a monetary value."""
        return render.monetaryAmount(anEffort.revenue(recursive=True))

    def __round_duration(self, duration):
        """Round a duration with the current precision and direction (i.e.
        always up or not)."""
        return duration.round(
            seconds=self.__round_precision(), alwaysUp=self.__always_round_up()
        )

    def __show_seconds(self):
        """Return whether the viewer is showing seconds as part of
        durations."""
        return self.__round_precision() == 0

    def __round_precision(self):
        """Return with what precision the viewer is rounding durations."""
        return self.settings.getint(self.settingsSection(), "round")

    def __always_round_up(self):
        """Return whether durations are always rounded up or not."""
        return self.settings.getboolean(
            self.settingsSection(), "alwaysroundup"
        )

    def __consolidate_efforts_per_task(self):
        """Return whether task efforts are consolidated before rounding."""
        return self.settings.getboolean(
            self.settingsSection(), "consolidateeffortspertask"
        )


class EffortViewerForSelectedTasks(EffortViewer):
    defaultTitle = _("Effort for selected task(s)")

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("settingsSection", "effortviewerforselectedtasks")
        self.__viewerContainer = kwargs.pop("viewerContainer")
        activeViewer = self.__viewerContainer.activeViewer()
        self.__currentTaskViewer = (
            activeViewer
            if activeViewer is not None and activeViewer.isShowingTasks()
            else None
        )
        pub.subscribe(self.onTaskSelectionChanged, "all.viewer.status")
        super().__init__(*args, **kwargs)

    def tasksToShowEffortFor(self):
        if self.__currentTaskViewer is not None:
            return domain.task.TaskList(
                self.__currentTaskViewer.curselection()
            )
        return []

    def onTaskSelectionChanged(self, viewer):
        if viewer.isShowingTasks():
            self.__currentTaskViewer = viewer
            self._refresh(clear=True)
