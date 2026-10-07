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

import math
import wx.lib.agw.piectrl
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
from taskcoachlib.gui.icons import image_list_cache
from taskcoachlib import command, widgets, render, patterns
from taskcoachlib.config import settings
from taskcoachlib.domain import task, date
from taskcoachlib.domain.base import by_style_priority
from taskcoachlib.gui import uicommand, dialog
import taskcoachlib.gui.menu
from taskcoachlib.i18n import _
from taskcoachlib.tools import wxhelper
from taskcoachlib.thirdparty.wxScheduler import (
    wxSCHEDULER_TODAY,
    wxBaseDrawer,
    wxFancyDrawer,
)
from taskcoachlib.widgets import (
    CalendarConfigDialog,
    HierarchicalCalendarConfigDialog,
)

# NOTE (Twisted Removal - 2024): Replaced deferToThread/inlineCallbacks with
# concurrent.futures ThreadPoolExecutor. This provides the same async thread
# execution without Twisted reactor dependency.
from . import base
from . import inplace_editor
from . import mixin
from . import refresher
import wx


class DueDateTimeCtrl(inplace_editor.DateTimeCtrl):
    """Inline due date editor.

    TODO: The old smartdatetimectrl had a "relative preset" dropdown that showed
    duration offsets like "+1 day", "+1 week" relative to the planned start date.
    This feature would need to be reimplemented as a separate duration field with
    duration presets in DateTimeComboCtrl. The settings key "feature.task_duration_presets"
    stores the user's custom duration choices. For now, due dates are edited as
    absolute datetime values only.
    """

    def __init__(self, parent, wx_id, item, column, owner, value, **kwargs):
        # Pass relative info for future implementation
        kwargs["relative"] = True
        kwargs["startDateTime"] = item.GetData().plannedStartDateTime()
        super().__init__(parent, wx_id, item, column, owner, value, **kwargs)


class TaskViewerStatusMessages(object):
    template1 = _("Tasks: %d selected, %d visible, %d total")
    template2 = _("Status: %d overdue, %d late, %d inactive, %d completed")

    def __init__(self, viewer):
        super().__init__()
        self.__viewer = viewer
        self.__presentation = viewer.presentation()

    def __call__(self):
        count = self.__presentation.observable(
            recursive=True
        ).nr_of_tasks_per_status()
        return self.template1 % (
            len(self.__viewer.curselection()),
            self.__viewer.nrOfVisibleTasks(),
            self.__presentation.original_length(),
        ), self.template2 % (
            count[task.status.overdue],
            count[task.status.late],
            count[task.status.inactive],
            count[task.status.completed],
        )


class BaseTaskViewer(
    mixin.SearchableViewerMixin,  # pylint: disable=W0223
    mixin.FilterableViewerForTasksMixin,
    base.CategorizableViewerMixin,
    base.WithAttachmentsViewerMixin,
    base.TreeViewer,
):
    coreObjectType = "tasks"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.statusMessages = TaskViewerStatusMessages(self)
        self.__register_for_appearance_changes()
        patterns.later.soon(self, self.__DisplayBalloon)

    def __DisplayBalloon(self):
        # Run later: the viewer may be closing by then
        if not self or self.IsBeingDeleted():
            return
        if (
            self.toolbar.getToolIdByCommand("ViewerHideTasks_completed")
            != wx.ID_ANY
            and self.toolbar.IsShownOnScreen()
            and hasattr(wx.GetTopLevelParent(self), "AddBalloonTip")
        ):
            wx.GetTopLevelParent(self).AddBalloonTip(
                "filtershiftclick",
                self.toolbar,
                get_rect=lambda: self.toolbar.GetToolRect(
                    self.toolbar.getToolIdByCommand(
                        "ViewerHideTasks_completed"
                    )
                ),
                message=_(
                    """Shift-click on a filter tool to see only tasks belonging to the corresponding status"""
                ),
            )

    def __register_for_appearance_changes(self):
        for appearance in (
            "font",
            "fgcolor",
            "bgcolor",
            "icon",
            "font_dark",
            "fgcolor_dark",
            "bgcolor_dark",
            "icon_dark",
        ):
            # Its options are the statuses
            self.registerObserver(
                self.on_appearance_setting_change,
                eventType=settings.Settings.section_changed_event_type(
                    appearance
                ),
            )
        self.registerObserver(
            self.on_appearance_setting_change,
            eventType="window.theme",
        )
        for event_type in task.Task.effective_style_event_types():
            self.registerObserver(
                self.on_attribute_changed, eventType=event_type
            )
        self.registerObserver(
            self.on_attribute_changed,
            eventType=task.Task.prerequisitesChangedEventType(),
        )
        self.registerObserver(self._on_power_on, eventType="powermgt.on")

    def _on_power_on(self, event):  # pylint: disable=W0613
        self.refresh()

    def detach(self):
        super().detach()
        self.statusMessages = None  # Break cycle

    def _render_time_spent(self, *args, **kwargs):
        kwargs.setdefault("decimal", settings.feature.decimal_time)
        return render.time_spent(*args, **kwargs)

    def _render_budget(self, *args, **kwargs):
        kwargs.setdefault("decimal", settings.feature.decimal_time)
        return render.budget(*args, **kwargs)

    def on_appearance_setting_change(self, event):  # pylint: disable=W0613
        if self:
            patterns.later.soon(
                self, self.refresh
            )  # Let domain objects update appearance first
        # Show/hide status in toolbar may change too
        self.toolbar.loadPerspective(self.toolbar.perspective(), cache=False)

    def domainObjectsToView(self):
        return self.taskFile.tasks()

    def is_showing_tasks(self):
        return True

    def createFilter(self, taskList):
        return super().createFilter(taskList)

    def nrOfVisibleTasks(self):
        # Make this overridable for viewers where the widget does not show all
        # items in the presentation, i.e. the widget does filtering on its own.
        return len(self.presentation())


class BaseTaskTreeViewer(BaseTaskViewer):  # pylint: disable=W0223
    defaultTitle = _("Tasks")
    defaultBitmap = "nuvola_actions_ledblue"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get("doRefresh", True):
            self.second_refresher = refresher.SecondRefresher(
                self, task.Task.trackingChangedEventType()
            )
            self.minute_refresher = refresher.MinuteRefresher(self)
        else:
            self.second_refresher = self.minute_refresher = None

    def detach(self):
        super().detach()
        if hasattr(self, "second_refresher") and self.second_refresher:
            self.second_refresher.stop_clock()
            self.second_refresher.removeInstance()
            del self.second_refresher
        if hasattr(self, "minute_refresher") and self.minute_refresher:
            self.minute_refresher.stop_clock()
            del self.minute_refresher

    def newItemDialog(self, *args, **kwargs):
        kwargs["categories"] = self.taskFile.categories().filteredCategories()
        return super().newItemDialog(*args, **kwargs)

    def editItemDialog(
        self, items, icon_id, columnName="", items_are_new=False
    ):
        if isinstance(items[0], task.Task):
            return super().editItemDialog(
                items,
                icon_id,
                columnName=columnName,
                items_are_new=items_are_new,
            )
        else:
            self.cancel_tip()
            parent = wx.GetTopLevelParent(self)
            # Same fix as base.py: if viewer is inside an Editor dialog,
            # parent to main window to avoid cascade-Destroy segfault.
            if isinstance(parent, wx.Dialog):
                parent = wx.GetApp().TopWindow
            return dialog.editor.EffortEditor(
                parent,
                items,
                self.taskFile.efforts(),
                self.taskFile,
                icon_id=icon_id,
                items_are_new=items_are_new,
            )

    def itemEditorClass(self):
        return dialog.editor.TaskEditor

    def newItemCommandClass(self):
        return command.NewTaskCommand

    def newSubItemCommandClass(self):
        return command.NewSubTaskCommand

    def newSubItemCommand(self):
        kwargs = dict()
        if self.__should_preset_planned_start_date_time():
            kwargs["plannedStartDateTime"] = (
                task.Task.suggestedPlannedStartDateTime()
            )
        if self.__should_preset_due_date_time():
            kwargs["dueDateTime"] = task.Task.suggestedDueDateTime()
        if self.__should_preset_actual_start_date_time():
            kwargs["actualStartDateTime"] = (
                task.Task.suggestedActualStartDateTime()
            )
        if self.__should_preset_reminder_date_time():
            kwargs["reminder"] = task.Task.suggestedReminderDateTime()
        # pylint: disable=W0142
        return self.newSubItemCommandClass()(
            self.presentation(), self.curselection(), **kwargs
        )

    def __should_preset_planned_start_date_time(self):
        return settings.view.defaultplannedstartdatetime.startswith("preset")

    def __should_preset_due_date_time(self):
        return settings.view.defaultduedatetime.startswith("preset")

    def __should_preset_actual_start_date_time(self):
        return settings.view.defaultactualstartdatetime.startswith("preset")

    def __should_preset_reminder_date_time(self):
        return settings.view.defaultreminderdatetime.startswith("preset")

    def deleteItemCommand(self):
        return command.DeleteTaskCommand(
            self.presentation(),
            self.curselection(),
        )

    def getSupportedPasteTypes(self):
        return (task.Task,)

    def createTaskPopupMenu(self):
        return taskcoachlib.gui.menu.TaskPopupMenu(
            self.parent,
            self.presentation(),
            self.taskFile.efforts(),
            self.taskFile.categories(),
            self,
        )

    def createCreationToolBarUICommands(self):
        return (
            uicommand.TaskNew(taskList=self.presentation()),
            uicommand.NewSubItem(viewer=self),
            uicommand.TaskNewFromTemplateButton(
                taskList=self.presentation(),
                icon_id="taskcoach_actions_newtmpl",
            ),
        ) + super().createCreationToolBarUICommands()

    def createActionToolBarUICommands(self):
        ui_commands = (
            uicommand.AddNote(viewer=self),
            uicommand.TaskMarkInactive(viewer=self),
            uicommand.TaskMarkActive(viewer=self),
            uicommand.TaskMarkCompleted(viewer=self),
        )
        ui_commands += (
            # EffortStart needs a reference to the original (task) list to
            # be able to stop tracking effort for tasks that are already
            # being tracked, but that might be filtered in the viewer's
            # presentation.
            uicommand.Separator(),
            uicommand.EffortStart(viewer=self, taskList=self.taskFile.tasks()),
            uicommand.EffortStop(
                viewer=self,
                effortList=self.taskFile.efforts(),
                taskList=self.taskFile.tasks(),
            ),
        )
        return ui_commands + super().createActionToolBarUICommands()

    def createModeToolBarUICommands(self):
        hide_ui_commands = tuple(
            [
                uicommand.ViewerHideTasks(task_status=status, viewer=self)
                for status in task.Task.possibleStatuses()
            ]
        )
        other_mode_ui_commands = super(
            BaseTaskTreeViewer, self
        ).createModeToolBarUICommands()
        separator = (None,) if other_mode_ui_commands else ()
        return (
            hide_ui_commands
            + separator
            + other_mode_ui_commands
            + (uicommand.ToggleAutoScroll(),)
        )

    def getItemTooltipData(self, task):  # pylint: disable=W0621
        result = [
            (
                task.shown_icon_id(),
                [self.getItemText(task)],
            )
        ]
        if task.notes():
            result.append(
                (
                    "nuvola_apps_knotes",
                    sorted([note.subject() for note in task.notes()]),
                )
            )
        # Note: attachments are handled by WithAttachmentsViewerMixin
        return result + super().getItemTooltipData(task)

    def label(self, task):  # pylint: disable=W0621
        return self.getItemText(task)


class RootNode(object):
    def __init__(self, tasks):
        self.tasks = tasks

    def subject(self):
        return ""

    def children(self, recursive=False):
        if recursive:
            return self.tasks[:]
        else:
            return self.tasks.rootItems()

    # pylint: disable=W0613

    def shown_fg_color(self):
        return None

    def shown_bg_color(self):
        return None

    def shown_font(self):
        return None

    def completed(self, *args, **kwargs):
        return False

    late = dueSoon = inactive = overdue = isBeingTracked = completed


class SquareMapRootNode(RootNode):
    def __getattr__(self, attr):
        def getTaskAttribute(recursive=True):
            if recursive:
                return max(
                    sum(
                        (
                            getattr(task, attr)(recursive=True)
                            for task in self.children()
                        ),
                        self.__zero,
                    ),
                    self.__zero,
                )
            else:
                return self.__zero

        self.__zero = (
            date.TimeDelta()
            if attr in ("budget", "budgetLeft", "timeSpent")
            else 0
        )  # pylint: disable=W0201
        return getTaskAttribute


class TimelineRootNode(RootNode):
    def children(self, recursive=False):
        children = super().children(recursive)
        children.sort(key=lambda task: task.plannedStartDateTime())
        return children

    def parallel_children(self, recursive=False):
        return self.children(recursive)

    def sequential_children(self):
        return []

    def plannedStartDateTime(self, recursive=False):  # pylint: disable=W0613
        planned_start_date_times = [
            item.plannedStartDateTime(recursive=True)
            for item in self.parallel_children()
        ]
        planned_start_date_times = [
            dt for dt in planned_start_date_times if dt != date.DateTime()
        ]
        if not planned_start_date_times:
            planned_start_date_times.append(date.Now())
        return min(planned_start_date_times)

    def dueDateTime(self, recursive=False):  # pylint: disable=W0613
        due_date_times = [
            item.dueDateTime(recursive=True)
            for item in self.parallel_children()
        ]
        due_date_times = [dt for dt in due_date_times if dt != date.DateTime()]
        if not due_date_times:
            due_date_times.append(date.Tomorrow())
        return max(due_date_times)


class TimelineViewer(BaseTaskTreeViewer):
    defaultTitle = _("Timeline")
    defaultBitmap = "taskcoach_actions_timelineviewer"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("settingsSection", "timelineviewer")
        super().__init__(*args, **kwargs)
        for event_type in (
            task.Task.subjectChangedEventType(),
            task.Task.plannedStartDateTimeChangedEventType(),
            task.Task.dueDateTimeChangedEventType(),
            task.Task.completionDateTimeChangedEventType(),
        ):
            self.registerObserver(self.on_attribute_changed, event_type)

    def create_widget(self):
        self.rootNode = TimelineRootNode(
            self.presentation()
        )  # pylint: disable=W0201
        item_popup_menu = self.createTaskPopupMenu()
        self._popupMenus.append(item_popup_menu)
        return widgets.Timeline(
            self, self.rootNode, self.onSelect, self.onEdit, item_popup_menu
        )

    def onEdit(self, item):
        edit = uicommand.Edit(viewer=self)
        edit(item)

    def curselection(self, force_update=False):  # pylint: disable=W0613
        # Override curselection, because there is no need to translate indices
        # back to domain objects. Our widget already returns the selected domain
        # object itself. forceUpdate is ignored since widget always returns fresh data.
        return self.widget.curselection()

    def bounds(self, item):
        times = [self.start(item), self.stop(item)]
        for child in self.parallel_children(item) + self.sequential_children(
            item
        ):
            times.extend(self.bounds(child))
        times = [time for time in times if time is not None]
        return (min(times), max(times)) if times else []

    def start(self, item, recursive=False):
        try:
            start = item.plannedStartDateTime(recursive=recursive)
            if start == date.DateTime():
                return None
        except AttributeError:
            start = item.getStart()
        return start.toordinal()

    def stop(self, item, recursive=False):
        try:
            if item.completed():
                stop = item.completionDateTime(recursive=recursive)
            else:
                stop = item.dueDateTime(recursive=recursive)
            if stop == date.DateTime():
                return None
            else:
                stop += date.ONE_DAY
        except AttributeError:
            stop = item.getStop()
            if not stop:
                return None
        return stop.toordinal()

    def sequential_children(self, item):
        try:
            return item.efforts()
        except AttributeError:
            return []

    def parallel_children(self, item, recursive=False):
        try:
            children = [
                child
                for child in item.children(recursive=recursive)
                if child in self.presentation()
            ]
            children.sort(key=lambda task: task.plannedStartDateTime())
            return children
        except AttributeError:
            return []

    def foreground_color(self, item, depth=0):  # pylint: disable=W0613
        return item.shown_fg_color()

    def background_color(self, item, depth=0):  # pylint: disable=W0613
        return item.shown_bg_color()

    def font(self, item, depth=0):  # pylint: disable=W0613
        return item.shown_font()

    def get_wx_icon(self, item, is_selected=False):  # pylint: disable=W0613
        # Empty until the master loop's first pass styles the item
        icon_id = item.shown_icon_id()
        if not icon_id:
            return None
        return icon_catalog.get_wx_icon(icon_id, LIST_ICON_SIZE)

    def now(self):
        return date.Now().toordinal()

    def nowlabel(self):
        return _("Now")

    def getItemTooltipData(self, item):
        if isinstance(item, task.Task):
            result = super().getItemTooltipData(item)
        else:
            result = [
                (
                    None,
                    [
                        render.dateTimePeriod(
                            item.getStart(),
                            item.getStop(),
                            human_readable=True,
                        )
                    ],
                )
            ]
            if item.description():
                result.append(
                    (
                        None,
                        [
                            line.rstrip("\n")
                            for line in item.description().split("\n")
                        ],
                    )
                )
        return result


class SquareTaskViewer(BaseTaskTreeViewer):
    defaultTitle = _("Task square map")
    defaultBitmap = "taskcoach_actions_squaremapviewer"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("settingsSection", "squaretaskviewer")
        self.__order_by = "revenue"
        self.__transform_task_attribute = lambda x: x
        self.__zero = 0
        self.renderer = dict(
            budget=self._render_budget,
            timeSpent=self._render_time_spent,
            fixedFee=render.monetaryAmount,
            revenue=render.monetaryAmount,
            priority=render.priority,
        )
        super().__init__(*args, **kwargs)
        sort_keys = self.options.sortby
        initial_key = sort_keys[0] if sort_keys else "budget"
        self._apply_order_by(initial_key.lstrip("-"))
        self.orderUICommand.set_choice(self.__order_by)
        for event_type in (
            task.Task.subjectChangedEventType(),
            task.Task.dueDateTimeChangedEventType(),
            task.Task.plannedStartDateTimeChangedEventType(),
            task.Task.completionDateTimeChangedEventType(),
        ):
            self.registerObserver(self.on_attribute_changed, event_type)

    def create_widget(self):
        item_popup_menu = self.createTaskPopupMenu()
        self._popupMenus.append(item_popup_menu)
        return widgets.TcSquareMap(
            self,
            SquareMapRootNode(self.presentation()),
            self.onSelect,
            uicommand.Edit(viewer=self),
            item_popup_menu,
        )

    def createModeToolBarUICommands(self):
        self.orderUICommand = uicommand.SquareTaskViewerOrderChoice(
            viewer=self
        )  # pylint: disable=W0201
        return super().createModeToolBarUICommands() + (self.orderUICommand,)

    def hasModes(self):
        return True

    def getModeUICommands(self):
        return [
            uicommand.DisabledLabel(_("Lay out tasks by")),
            uicommand.Separator(),
        ] + [
            uicommand.SquareTaskViewerOrderByOption(
                menu_text=menu_text,
                value=value,
                viewer=self,
            )
            for (menu_text, value) in zip(
                uicommand.SquareTaskViewerOrderChoice.choiceLabels,
                uicommand.SquareTaskViewerOrderChoice.choiceData,
            )
        ]

    @property
    def order_by(self):
        return self.__order_by

    def set_order_by(self, choice):
        """Change the order-by attribute. Called by toolbar and menu."""
        self.options.sortby = [choice]
        self._apply_order_by(choice)
        patterns.Event(self.view_settings_changed_event_type(), self).send()

    def _apply_order_by(self, choice):
        if choice == self.__order_by:
            return
        old_choice = self.__order_by
        self.__order_by = choice
        try:
            old_event_type = getattr(
                task.Task, "%sChangedEventType" % old_choice
            )()
        except AttributeError:
            old_event_type = "task.%s" % old_choice
        self.removeObserver(self.on_attribute_changed, old_event_type)
        try:
            new_event_type = getattr(
                task.Task, "%sChangedEventType" % choice
            )()
        except AttributeError:
            new_event_type = "task.%s" % choice
        self.registerObserver(self.on_attribute_changed, new_event_type)
        if choice in ("budget", "timeSpent"):
            self.__transform_task_attribute = (
                lambda timeSpent: timeSpent.milliseconds() / 1000
            )
            self.__zero = date.TimeDelta()
        else:
            self.__transform_task_attribute = lambda x: x
            self.__zero = 0
        self.refresh()

    def curselection(self, force_update=False):  # pylint: disable=W0613
        # Override curselection, because there is no need to translate indices
        # back to domain objects. Our widget already returns the selected domain
        # object itself. forceUpdate is ignored since widget always returns fresh data.
        return self.widget.curselection()

    def nrOfVisibleTasks(self):
        return len(
            [
                each_task
                for each_task in self.presentation()
                if getattr(each_task, self.__order_by)(recursive=True)
                > self.__zero
            ]
        )

    # SquareMap adapter methods:
    # pylint: disable=W0621

    def overall(self, task):
        return self.__transform_task_attribute(
            max(getattr(task, self.__order_by)(recursive=True), self.__zero)
        )

    def children_sum(self, children, parent):  # pylint: disable=W0613
        children_sum = sum(
            (
                max(
                    getattr(child, self.__order_by)(recursive=True),
                    self.__zero,
                )
                for child in children
                if child in self.presentation()
            ),
            self.__zero,
        )
        return self.__transform_task_attribute(max(children_sum, self.__zero))

    def empty(self, task):
        overall = self.overall(task)
        if overall:
            children_sum = self.children_sum(self.children(task), task)
            return max(
                self.__transform_task_attribute(self.__zero),
                (overall - children_sum),
            ) / float(overall)
        return 0

    def getItemText(self, task):
        text = super().getItemText(task)
        value = self.render(getattr(task, self.__order_by)(recursive=False))
        return "%s (%s)" % (text, value) if value else text

    def value(self, task, parent=None):  # pylint: disable=W0613
        return self.overall(task)

    def foreground_color(self, task, depth):  # pylint: disable=W0613
        return task.shown_fg_color()

    def background_color(self, task, depth):  # pylint: disable=W0613
        red = blue = 255 - (depth * 3) % 100
        green = 255 - (depth * 2) % 100
        color = wx.Colour(red, green, blue)
        return task.shown_bg_color() or color

    def font(self, task, depth):  # pylint: disable=W0613
        return task.shown_font()

    def icon(self, task, is_selected):  # pylint: disable=W0613
        icon_id = task.shown_icon_id() or "nuvola_actions_ledblue"
        return icon_catalog.get_wx_icon(icon_id, LIST_ICON_SIZE)

    # Helper methods

    def render(self, value):
        return self.renderer[self.__order_by](value)


class HierarchicalCalendarViewer(
    mixin.AttachmentDropTargetMixin,
    mixin.SortableViewerForTasksMixin,
    BaseTaskTreeViewer,
):
    defaultTitle = _("Hierarchical calendar")
    defaultBitmap = "nuvola_apps_date"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("settingsSection", "hierarchicalcalendarviewer")
        super().__init__(*args, **kwargs)

        # pylint: disable=E1101
        for event_type in (
            task.Task.subjectChangedEventType(),
            task.Task.attachmentsChangedEventType(),
            task.Task.notesChangedEventType(),
            task.Task.trackingChangedEventType(),
            task.Task.percentageCompleteChangedEventType(),
        ):
            self.registerObserver(self.on_attribute_changed, event_type)

        # Dates are treated separately: the layout may change
        # (_invalidate)
        # pylint: disable=E1101
        for event_type in (
            task.Task.plannedStartDateTimeChangedEventType(),
            task.Task.dueDateTimeChangedEventType(),
            task.Task.completionDateTimeChangedEventType(),
        ):
            self.registerObserver(self.on_layout_attribute_changed, event_type)

        self.reconfig()

        # Sent after the scheduler's processing; removed by detach()
        self.registerObserver(
            self._on_date_changed, eventType="scheduler.date"
        )
        self.registerObserver(
            self._on_minute_changed, eventType="scheduler.minute"
        )

    def _on_date_changed(self, event):  # pylint: disable=W0613
        self.at_midnight()

    def _on_minute_changed(self, event):  # pylint: disable=W0613
        self.widget.refresh_now_line()

    def needs_second_refresh(self):
        # Nothing shown changes every second while tracking
        return False

    def reconfig(self):
        self.widget.SetCalendarFormat(self.options.calendarformat)
        self.widget.SetHeaderFormat(self.options.headerformat)
        self.widget.SetDrawNow(self.options.drawnow)
        self.widget.SetTodayColor(
            list(
                map(
                    int,
                    self.options.todaycolor.split(","),
                )
            )
        )

    def configure(self):
        dialog = HierarchicalCalendarConfigDialog(
            self.settingsSection(),
            self,
            title=_("Hierarchical calendar viewer configuration"),
        )
        wxhelper.centre_on_parent(dialog)
        if dialog.ShowModal() == wx.ID_OK:
            self.reconfig()

    def createModeToolBarUICommands(self):
        return super(
            HierarchicalCalendarViewer, self
        ).createModeToolBarUICommands() + (
            uicommand.Separator(),
            uicommand.HierarchicalCalendarViewerConfigure(viewer=self),
            uicommand.HierarchicalCalendarViewerPreviousPeriod(viewer=self),
            uicommand.HierarchicalCalendarViewerToday(viewer=self),
            uicommand.HierarchicalCalendarViewerNextPeriod(viewer=self),
        )

    def at_midnight(self):
        self.widget.SetCalendarFormat(self.widget.CalendarFormat())

    def on_layout_attribute_changed(self, event):
        self.refresh()

    def is_tree_viewer(self):
        return True

    def create_widget(self):
        item_popup_menu = self.createTaskPopupMenu()
        self._popupMenus.append(item_popup_menu)
        widget = widgets.HierarchicalCalendar(
            self,
            self.presentation(),
            self.onSelect,
            self.onEdit,
            self.onCreate,
            item_popup_menu,
            **self.widgetCreationKeywordArguments()
        )
        return widget

    def onEdit(self, item):
        edit = uicommand.Edit(viewer=self)
        edit(item)

    def onCreate(self, dateTime, show=True):
        planned_start_date_time = dateTime
        due_date_time = (
            dateTime.endOfDay()
            if dateTime == dateTime.startOfDay()
            else dateTime
        )
        create = uicommand.TaskNew(
            taskList=self.presentation(),
            taskKeywords=dict(
                plannedStartDateTime=planned_start_date_time,
                dueDateTime=due_date_time,
            ),
        )
        return create(event=None, show=show)

    def GetPrintout(self, settings):
        return self.widget.GetPrintout(settings)


class CalendarViewer(
    mixin.AttachmentDropTargetMixin,
    mixin.SortableViewerForTasksMixin,
    BaseTaskTreeViewer,
):
    defaultTitle = _("Calendar")
    defaultBitmap = "nuvola_apps_date"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("settingsSection", "calendarviewer")
        kwargs["doRefresh"] = False
        super().__init__(*args, **kwargs)

        start = self.options.viewdate
        if start:
            dt = wx.DateTime.Now()
            dt.ParseDateTime(start)
            self.widget.SetDate(dt)

        self._on_week_start_changed()
        self.widget.SetWorkHours(
            settings.view.efforthourstart,
            settings.view.efforthourend,
        )

        self.reconfig()
        self.widget.SetPeriodWidth(self.options.periodwidth)

        # pylint: disable=E1101
        for event_type in (
            task.Task.subjectChangedEventType(),
            task.Task.plannedStartDateTimeChangedEventType(),
            task.Task.dueDateTimeChangedEventType(),
            task.Task.completionDateTimeChangedEventType(),
            task.Task.attachmentsChangedEventType(),
            task.Task.notesChangedEventType(),
            task.Task.trackingChangedEventType(),
            task.Task.percentageCompleteChangedEventType(),
        ):
            self.registerObserver(self.on_attribute_changed, event_type)
        # Sent after the scheduler's processing; removed by detach()
        self.registerObserver(
            self._on_date_changed, eventType="scheduler.date"
        )
        self.registerObserver(
            self._on_minute_changed, eventType="scheduler.minute"
        )
        self.registerObserver(
            self._on_calendar_colours_changed,
            eventType="calendar.colours.changed",
        )
        # Preferences apply at once, but for the work hours
        # (docs/PUBLISHER_OBSERVER.md, Migration Log)
        self.registerObserver(
            self._on_week_start_changed,
            eventType="view.weekstart",
        )
        self.registerObserver(
            self._on_gradient_changed,
            eventType="calendarviewer.gradient",
        )

    def _on_week_start_changed(self, event=None):  # pylint: disable=W0613
        if settings.view.weekstart == "monday":
            self.widget.SetWeekStartMonday()
        else:
            self.widget.SetWeekStartSunday()

    def _on_gradient_changed(self, event):  # pylint: disable=W0613
        # The widget exists by now: set at once, unlike at creation
        self.widget.SetDrawer(
            wxFancyDrawer if settings.calendarviewer.gradient else wxBaseDrawer
        )

    def _on_date_changed(self, event):  # pylint: disable=W0613
        self.at_midnight()

    def _on_minute_changed(self, event):  # pylint: disable=W0613
        self.widget.refresh_now_line()

    def _on_calendar_colours_changed(self, event):  # pylint: disable=W0613
        self.reconfig()

    def is_tree_viewer(self):
        return False

    def at_midnight(self):
        if not self.options.viewdate:
            # User has selected the "current" date/time; it may have
            # changed now
            self.SetViewType(wxSCHEDULER_TODAY)

    def create_widget(self):
        item_popup_menu = self.createTaskPopupMenu()
        self._popupMenus.append(item_popup_menu)
        widget = widgets.Calendar(
            self,
            self.presentation(),
            self.onSelect,
            self.onEdit,
            self.onCreate,
            self.onChangeConfig,
            item_popup_menu,
            **self.widgetCreationKeywordArguments()
        )

        if settings.calendarviewer.gradient:
            # If called directly, we crash with a Cairo assert failing...
            patterns.later.soon(
                self, self.__safeSetDrawer, widget, wxFancyDrawer
            )

        return widget

    def __safeSetDrawer(self, widget, drawer):
        """Safely set the drawer on a widget, guarding against deleted C++ objects."""
        try:
            if widget:
                widget.SetDrawer(drawer)
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

        return widget

    def onChangeConfig(self):
        self.options.periodwidth = self.widget.GetPeriodWidth()

    def onEdit(self, item):
        edit = uicommand.Edit(viewer=self)
        edit(item)

    def onCreate(self, dateTime, show=True):
        planned_start = dateTime
        due = (
            dateTime.endOfDay()
            if dateTime == dateTime.startOfDay()
            else dateTime
        )
        create = uicommand.TaskNew(
            taskList=self.presentation(),
            taskKeywords=dict(
                plannedStartDateTime=planned_start,
                dueDateTime=due,
            ),
        )
        return create(event=None, show=show)

    def createModeToolBarUICommands(self):
        return super().createModeToolBarUICommands() + (
            uicommand.Separator(),
            uicommand.CalendarViewerConfigure(viewer=self),
            uicommand.CalendarViewerPreviousPeriod(viewer=self),
            uicommand.CalendarViewerToday(viewer=self),
            uicommand.CalendarViewerNextPeriod(viewer=self),
        )

    def SetViewType(self, type_):
        self.widget.SetViewType(type_)
        dt = self.widget.GetDate()
        now = wx.DateTime.Today()
        if (dt.GetYear(), dt.GetMonth(), dt.GetDay()) == (
            now.GetYear(),
            now.GetMonth(),
            now.GetDay(),
        ):
            to_save = ""
        else:
            to_save = dt.Format()
        self.options.viewdate = to_save

    def reconfig(self):
        self._do_reconfig()

    def _do_reconfig(self):
        self.widget.Freeze()
        try:
            self.widget.SetPeriodCount(self.options.periodcount)
            self.widget.SetViewType(self.options.viewtype)
            self.widget.SetStyle(self.options.vieworientation)
            self.widget.SetShowNoStartDate(self.options.shownostart)
            self.widget.SetShowNoDueDate(self.options.shownodue)
            self.widget.SetShowUnplanned(self.options.showunplanned)
            self.widget.SetShowNow(self.options.shownow)

            hcolor = self.options.highlightcolor
            if hcolor:
                highlight_color = wx.Colour(
                    *tuple([int(c) for c in hcolor.split(",")])
                )
                self.widget.SetHighlightColor(highlight_color)

            # Other month days background color
            section = (
                "calendar_dark"
                if settings.window.theme_is_dark
                else "calendar_light"
            )
            use_system = settings.get(section, "other_month_bg_system")
            if use_system:
                self.widget.SetOtherMonthColor(None)
            else:
                color_tuple = settings.get(section, "other_month_bg")
                self.widget.SetOtherMonthColor(wx.Colour(*color_tuple))

            self.widget.RefreshAllItems(0)
        finally:
            self.widget.Thaw()

    def configure(self):
        dialog = CalendarConfigDialog(
            self.settingsSection(),
            self,
            title=_("Calendar viewer configuration"),
        )
        wxhelper.centre_on_parent(dialog)
        if dialog.ShowModal() == wx.ID_OK:
            self.reconfig()

    def GetPrintout(self, settings):
        return self.widget.GetPrintout(settings)


class TaskViewer(
    mixin.AttachmentDropTargetMixin,  # pylint: disable=W0223
    mixin.SortableViewerForTasksMixin,
    mixin.NoteColumnMixin,
    mixin.AttachmentColumnMixin,
    base.SortableViewerWithColumns,
    BaseTaskTreeViewer,
):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("settingsSection", "taskviewer")
        super().__init__(*args, **kwargs)
        if self.isVisibleColumnByName("timeLeft"):
            self.minute_refresher.start_clock()

    def activate(self):
        if hasattr(wx.GetTopLevelParent(self), "AddBalloonTip"):
            wx.GetTopLevelParent(self).AddBalloonTip(
                "manualordering",
                self.widget,
                title=_("Manual ordering"),
                get_rect=lambda: wx.Rect(0, 0, 28, 16),
                message=_(
                    """Show the "Manual ordering" column, then drag and drop items from this column to sort them arbitrarily."""
                ),
            )

    def is_tree_viewer(self):
        # We first ask our presentation what the mode is because
        # ConfigParser.getboolean is a relatively expensive method. However,
        # when initializing, the presentation might not be created yet. So in
        # that case we get an AttributeError and we use the settings.
        try:
            return self.presentation().tree_mode()
        except AttributeError:
            return self.options.treemode

    def showColumn(self, column, show=True, *args, **kwargs):
        if column.name() == "timeLeft":
            if show:
                self.minute_refresher.start_clock()
            else:
                self.minute_refresher.stop_clock()
        super().showColumn(column, show, *args, **kwargs)

    def create_widget(self):
        image_list = self.createImageList()  # Has side-effects
        self._columns = self.ordered_columns(self._createColumns())
        item_popup_menu = self.createTaskPopupMenu()
        column_popup_menu = self.createColumnPopupMenu()
        self._popupMenus.extend([item_popup_menu, column_popup_menu])
        widget = widgets.TreeListCtrl(
            self,
            self.columns(),
            self.onSelect,
            uicommand.Edit(viewer=self),
            uicommand.TaskDragAndDrop(
                taskList=self.presentation(), viewer=self
            ),
            item_popup_menu,
            column_popup_menu,
            resizeableColumn=0,  # The subject's place once shown
            validate_drag=self.validate_drag,
            **self.widgetCreationKeywordArguments()
        )
        widget.SetImageList(image_list)  # pylint: disable=E1101
        widget.show_expand_buttons(self.is_tree_viewer())
        widget.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.on_begin_edit)
        widget.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.on_end_edit)
        return widget

    def on_begin_edit(self, event):
        """Make sure only the non-recursive part of the subject can be
        edited inline."""
        event.Skip()
        if not self.is_tree_viewer():
            # Make sure the text control only shows the non-recursive subject
            # by temporarily changing the item text into the non-recursive
            # subject. When the editing ends, we change the item text back into
            # the recursive subject. See on_end_edit.
            tree_item = event.GetItem()
            edited_task = self.widget.GetItemPyData(tree_item)
            self.widget.SetItemText(tree_item, edited_task.subject())

    def on_end_edit(self, event):
        """Make sure only the non-recursive part of the subject can be
        edited inline."""
        event.Skip()
        if not self.is_tree_viewer():
            # Restore the recursive subject. Here we don't care whether users
            # actually changed the subject. If they did, the subject will
            # be updated via the regular notification mechanism.
            tree_item = event.GetItem()
            edited_task = self.widget.GetItemPyData(tree_item)
            self.widget.SetItemText(
                tree_item, edited_task.subject(recursive=True)
            )

    def _createColumns(self):
        kwargs = dict(resizeCallback=self.onResizeColumn)
        # pylint: disable=E1101,W0142
        columns = (
            [
                widgets.Column(
                    "ordering",
                    "",
                    task.Task.orderingChangedEventType(),
                    sortCallback=uicommand.ViewerSortByCommand(
                        viewer=self, value="ordering"
                    ),
                    renderCallback=lambda task: "",
                    imageIndicesCallback=self.orderingImageIndices,
                    width=self.getColumnWidth("ordering"),
                ),
                widgets.Column(
                    "subject",
                    _("Subject"),
                    task.Task.subjectChangedEventType(),
                    task.Task.completionDateTimeChangedEventType(),
                    task.Task.actualStartDateTimeChangedEventType(),
                    task.Task.dueDateTimeChangedEventType(),
                    task.Task.plannedStartDateTimeChangedEventType(),
                    task.Task.trackingChangedEventType(),
                    sortCallback=uicommand.ViewerSortByCommand(
                        viewer=self, value="subject"
                    ),
                    width=self.getColumnWidth("subject"),
                    imageIndicesCallback=self.subjectImageIndices,
                    renderCallback=self.renderSubject,
                    editCallback=self.onEditSubject,
                    editControl=inplace_editor.SubjectCtrl,
                    **kwargs
                ),
            ]
            + [
                widgets.Column(
                    "description",
                    _("Description"),
                    task.Task.descriptionChangedEventType(),
                    sortCallback=uicommand.ViewerSortByCommand(
                        viewer=self, value="description"
                    ),
                    renderCallback=lambda task: task.description(),
                    width=self.getColumnWidth("description"),
                    editCallback=self.onEditDescription,
                    editControl=inplace_editor.DescriptionCtrl,
                    **kwargs
                )
            ]
            + [
                widgets.Column(
                    "attachments",
                    _("Attachments"),
                    task.Task.attachmentsChangedEventType(),
                    width=self.getColumnWidth("attachments"),
                    alignment=wx.LIST_FORMAT_LEFT,
                    imageIndicesCallback=self.attachmentImageIndices,
                    headerImageIndex=image_list_cache.get_index(
                        "nuvola_status_mail-attachment"
                    ),
                    renderCallback=lambda task: "",
                    **kwargs
                )
            ]
        )
        columns.append(
            widgets.Column(
                "notes",
                _("Notes"),
                task.Task.notesChangedEventType(),
                width=self.getColumnWidth("notes"),
                alignment=wx.LIST_FORMAT_LEFT,
                imageIndicesCallback=self.noteImageIndices,
                headerImageIndex=image_list_cache.get_index(
                    "nuvola_apps_knotes"
                ),
                renderCallback=lambda task: "",
                **kwargs
            )
        )
        columns.extend(
            [
                widgets.Column(
                    "categories",
                    _("Categories"),
                    task.Task.categoryAddedEventType(),
                    task.Task.categoryRemovedEventType(),
                    task.Task.categorySubjectChangedEventType(),
                    task.Task.expansionChangedEventType(),
                    sortCallback=uicommand.ViewerSortByCommand(
                        viewer=self, value="categories"
                    ),
                    width=self.getColumnWidth("categories"),
                    renderCallback=self.renderCategories,
                    **kwargs
                ),
                widgets.Column(
                    "categoryIcons",
                    _("Category icons"),
                    task.Task.categoryAddedEventType(),
                    task.Task.categoryRemovedEventType(),
                    width=self.getColumnWidth("categoryIcons"),
                    alignment=wx.LIST_FORMAT_LEFT,
                    multiImageIndicesCallback=self.categoryIconsImageIndices,
                    renderCallback=lambda task: "",
                    **kwargs
                ),
                widgets.Column(
                    "prerequisites",
                    _("Prerequisites"),
                    task.Task.prerequisitesChangedEventType(),
                    task.Task.expansionChangedEventType(),
                    sortCallback=uicommand.ViewerSortByCommand(
                        viewer=self, value="prerequisites"
                    ),
                    renderCallback=self.renderPrerequisites,
                    width=self.getColumnWidth("prerequisites"),
                    **kwargs
                ),
                widgets.Column(
                    "dependencies",
                    _("Dependents"),
                    task.Task.dependenciesChangedEventType(),
                    task.Task.expansionChangedEventType(),
                    sortCallback=uicommand.ViewerSortByCommand(
                        viewer=self, value="dependencies"
                    ),
                    renderCallback=self.renderDependencies,
                    width=self.getColumnWidth("dependencies"),
                    **kwargs
                ),
            ]
        )

        for name, column_header, edit_ctrl, edit_callback, event_types in [
            (
                "plannedStartDateTime",
                _("Planned start date"),
                inplace_editor.DateTimeCtrl,
                self.onEditPlannedStartDateTime,
                [],
            ),
            (
                "dueDateTime",
                _("Due date"),
                DueDateTimeCtrl,
                self.onEditDueDateTime,
                [task.Task.expansionChangedEventType()],
            ),
            (
                "actualStartDateTime",
                _("Actual start date"),
                inplace_editor.DateTimeCtrl,
                self.onEditActualStartDateTime,
                [task.Task.expansionChangedEventType()],
            ),
            (
                "completionDateTime",
                _("Completion date"),
                inplace_editor.DateTimeCtrl,
                self.onEditCompletionDateTime,
                [task.Task.expansionChangedEventType()],
            ),
        ]:
            render_callback = getattr(
                self, "render%s" % (name[0].capitalize() + name[1:])
            )
            columns.append(
                widgets.Column(
                    name,
                    column_header,
                    sortCallback=uicommand.ViewerSortByCommand(
                        viewer=self, value=name
                    ),
                    renderCallback=render_callback,
                    width=self.getColumnWidth(name),
                    alignment=wx.LIST_FORMAT_RIGHT,
                    editControl=edit_ctrl,
                    editCallback=edit_callback,
                    *event_types,
                    **kwargs
                )
            )

        # Status columns (derived from dates, updated by scheduler)
        columns.append(
            widgets.Column(
                "status",
                _("Status"),
                task.Task.statusChangedEventType(),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self, value="status"
                ),
                renderCallback=lambda task: task.statusText(),
                width=self.getColumnWidth("status"),
                **kwargs
            )
        )
        columns.append(
            widgets.Column(
                "statusIcon",
                _("Status icon"),
                task.Task.statusChangedEventType(),
                width=self.getColumnWidth("statusIcon"),
                alignment=wx.LIST_FORMAT_LEFT,
                imageIndicesCallback=self.statusImageIndices,
                renderCallback=lambda task: "",
                **kwargs
            )
        )
        columns.append(
            widgets.Column(
                "statusIconText",
                _("Status combo"),
                task.Task.statusChangedEventType(),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self, value="status"
                ),
                renderCallback=lambda task: task.statusText(),
                width=self.getColumnWidth("statusIconText"),
                imageIndicesCallback=self.statusImageIndices,
                **kwargs
            )
        )

        depends_on_effort_feature = [
            "budget",
            "timeSpent",
            "budgetLeft",
            "hourlyFee",
            "fixedFee",
            "revenue",
        ]

        for name, column_header, edit_ctrl, edit_callback, event_types in [
            (
                "percentageComplete",
                _("% complete"),
                inplace_editor.PercentageCtrl,
                self.onEditPercentageComplete,
                [
                    task.Task.expansionChangedEventType(),
                    task.Task.percentageCompleteChangedEventType(),
                ],
            ),
            (
                "timeLeft",
                _("Time left"),
                None,
                None,
                [
                    task.Task.expansionChangedEventType(),
                    task.Task.dueDateTimeChangedEventType(),
                ],
            ),
            (
                "recurrence",
                _("Recurrence"),
                None,
                None,
                [
                    task.Task.expansionChangedEventType(),
                    task.Task.recurrenceChangedEventType(),
                ],
            ),
            (
                "budget",
                _("Budget"),
                inplace_editor.BudgetCtrl,
                self.onEditBudget,
                [
                    task.Task.expansionChangedEventType(),
                    task.Task.budgetChangedEventType(),
                ],
            ),
            (
                "timeSpent",
                _("Time spent"),
                None,
                None,
                [
                    task.Task.expansionChangedEventType(),
                    task.Task.timeSpentChangedEventType(),
                ],
            ),
            (
                "budgetLeft",
                _("Budget left"),
                None,
                None,
                [
                    task.Task.expansionChangedEventType(),
                    task.Task.budgetLeftChangedEventType(),
                ],
            ),
            (
                "priority",
                _("Priority"),
                inplace_editor.PriorityCtrl,
                self.onEditPriority,
                [
                    task.Task.expansionChangedEventType(),
                    task.Task.priorityChangedEventType(),
                ],
            ),
            (
                "hourlyFee",
                _("Hourly fee"),
                inplace_editor.AmountCtrl,
                self.onEditHourlyFee,
                [task.Task.hourlyFeeChangedEventType()],
            ),
            (
                "fixedFee",
                _("Fixed fee"),
                inplace_editor.AmountCtrl,
                self.onEditFixedFee,
                [
                    task.Task.expansionChangedEventType(),
                    task.Task.fixedFeeChangedEventType(),
                ],
            ),
            (
                "revenue",
                _("Revenue"),
                None,
                None,
                [
                    task.Task.expansionChangedEventType(),
                    task.Task.revenueChangedEventType(),
                ],
            ),
        ]:
            if (
                name in depends_on_effort_feature
            ) or name not in depends_on_effort_feature:
                render_callback = getattr(
                    self, "render%s" % (name[0].capitalize() + name[1:])
                )
                columns.append(
                    widgets.Column(
                        name,
                        column_header,
                        sortCallback=uicommand.ViewerSortByCommand(
                            viewer=self, value=name
                        ),
                        renderCallback=render_callback,
                        width=self.getColumnWidth(name),
                        alignment=wx.LIST_FORMAT_RIGHT,
                        editControl=edit_ctrl,
                        editCallback=edit_callback,
                        *event_types,
                        **kwargs
                    )
                )

        columns.append(
            widgets.Column(
                "reminder",
                _("Reminder"),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self, value="reminder"
                ),
                renderCallback=self.renderReminder,
                width=self.getColumnWidth("reminder"),
                alignment=wx.LIST_FORMAT_RIGHT,
                editControl=inplace_editor.DateTimeCtrl,
                editCallback=self.onEditReminderDateTime,
                *[
                    task.Task.expansionChangedEventType(),
                    task.Task.reminderChangedEventType(),
                ],
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
                task.Task.modification_datetime_changed_event_type(),
                width=self.getColumnWidth("modificationDateTime"),
                renderCallback=self.renderModificationDateTime,
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self, value="modificationDateTime"
                ),
                **kwargs
            )
        )
        columns.append(
            widgets.Column(
                "id",
                _("ID"),
                width=self.getColumnWidth("id"),
                renderCallback=lambda task: task.id(),
                sortCallback=uicommand.ViewerSortByCommand(
                    viewer=self, value="id"
                ),
                **kwargs
            )
        )
        return columns

    def createColumnUICommands(self):
        commands = [
            uicommand.ToggleAutoColumnResizing(viewer=self),
            uicommand.Separator(),
            uicommand.SubMenu(
                _("&Dates"),
                uicommand.ViewColumns(
                    menu_text=_("&All date columns"),
                    help_text=_("Show/hide all date-related columns"),
                    setting=[
                        "plannedStartDateTime",
                        "dueDateTime",
                        "timeLeft",
                        "actualStartDateTime",
                        "completionDateTime",
                        "recurrence",
                        "status",
                        "statusIcon",
                        "statusIconText",
                        "creationDateTime",
                        "modificationDateTime",
                    ],
                    viewer=self,
                ),
                uicommand.Separator(),
                uicommand.ViewColumn(
                    menu_text=_("&Planned start date"),
                    help_text=_("Show/hide planned start date column"),
                    setting="plannedStartDateTime",
                    viewer=self,
                ),
                uicommand.ViewColumn(
                    menu_text=_("&Due date"),
                    help_text=_("Show/hide due date column"),
                    setting="dueDateTime",
                    viewer=self,
                ),
                uicommand.ViewColumn(
                    menu_text=_("&Actual start date"),
                    help_text=_("Show/hide actual start date column"),
                    setting="actualStartDateTime",
                    viewer=self,
                ),
                uicommand.ViewColumn(
                    menu_text=_("&Completion date"),
                    help_text=_("Show/hide completion date column"),
                    setting="completionDateTime",
                    viewer=self,
                ),
                uicommand.ViewColumn(
                    menu_text=_("&Time left"),
                    help_text=_("Show/hide time left column"),
                    setting="timeLeft",
                    viewer=self,
                ),
                uicommand.ViewColumn(
                    menu_text=_("&Recurrence"),
                    help_text=_("Show/hide recurrence column"),
                    setting="recurrence",
                    viewer=self,
                ),
                uicommand.Separator(),
                uicommand.ViewColumn(
                    menu_text=_("&Status"),
                    help_text=_("Show/hide status text column"),
                    setting="status",
                    viewer=self,
                ),
                uicommand.ViewColumn(
                    menu_text=_("Status &icon"),
                    help_text=_("Show/hide status icon column"),
                    setting="statusIcon",
                    viewer=self,
                ),
                uicommand.ViewColumn(
                    menu_text=_("Status &combo"),
                    help_text=_(
                        "Show/hide status combo column (icon and text)"
                    ),
                    setting="statusIconText",
                    viewer=self,
                ),
                uicommand.Separator(),
                uicommand.ViewColumn(
                    menu_text=_("C&reation date"),
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
            ),
        ]
        commands.extend(
            [
                uicommand.SubMenu(
                    _("&Budget"),
                    uicommand.ViewColumns(
                        menu_text=_("&All budget columns"),
                        help_text=_("Show/hide all budget-related columns"),
                        setting=["budget", "timeSpent", "budgetLeft"],
                        viewer=self,
                    ),
                    uicommand.Separator(),
                    uicommand.ViewColumn(
                        menu_text=_("&Budget"),
                        help_text=_("Show/hide budget column"),
                        setting="budget",
                        viewer=self,
                    ),
                    uicommand.ViewColumn(
                        menu_text=_("&Time spent"),
                        help_text=_("Show/hide time spent column"),
                        setting="timeSpent",
                        viewer=self,
                    ),
                    uicommand.ViewColumn(
                        menu_text=_("&Budget left"),
                        help_text=_("Show/hide budget left column"),
                        setting="budgetLeft",
                        viewer=self,
                    ),
                ),
                uicommand.SubMenu(
                    _("&Financial"),
                    uicommand.ViewColumns(
                        menu_text=_("&All financial columns"),
                        help_text=_("Show/hide all finance-related columns"),
                        setting=["hourlyFee", "fixedFee", "revenue"],
                        viewer=self,
                    ),
                    uicommand.Separator(),
                    uicommand.ViewColumn(
                        menu_text=_("&Hourly fee"),
                        help_text=_("Show/hide hourly fee column"),
                        setting="hourlyFee",
                        viewer=self,
                    ),
                    uicommand.ViewColumn(
                        menu_text=_("&Fixed fee"),
                        help_text=_("Show/hide fixed fee column"),
                        setting="fixedFee",
                        viewer=self,
                    ),
                    uicommand.ViewColumn(
                        menu_text=_("&Revenue"),
                        help_text=_("Show/hide revenue column"),
                        setting="revenue",
                        viewer=self,
                    ),
                ),
            ]
        )
        commands.extend(
            [
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
                    menu_text=_("&Prerequisites"),
                    help_text=_("Show/hide prerequisites column"),
                    setting="prerequisites",
                    viewer=self,
                ),
                uicommand.ViewColumn(
                    menu_text=_("&Dependents"),
                    help_text=_("Show/hide dependents column"),
                    setting="dependencies",
                    viewer=self,
                ),
                uicommand.ViewColumn(
                    menu_text=_("&Percentage complete"),
                    help_text=_("Show/hide percentage complete column"),
                    setting="percentageComplete",
                    viewer=self,
                ),
                uicommand.ViewColumn(
                    menu_text=_("&Attachments"),
                    help_text=_("Show/hide attachment column"),
                    setting="attachments",
                    viewer=self,
                ),
            ]
        )
        commands.append(
            uicommand.ViewColumn(
                menu_text=_("&Notes"),
                help_text=_("Show/hide notes column"),
                setting="notes",
                viewer=self,
            )
        )
        commands.extend(
            [
                uicommand.ViewColumn(
                    menu_text=_("&Categories"),
                    help_text=_("Show/hide categories column"),
                    setting="categories",
                    viewer=self,
                ),
                uicommand.ViewColumn(
                    menu_text=_("Category &icons"),
                    help_text=_("Show/hide category icons column"),
                    setting="categoryIcons",
                    viewer=self,
                ),
                uicommand.ViewColumn(
                    menu_text=_("&Priority"),
                    help_text=_("Show/hide priority column"),
                    setting="priority",
                    viewer=self,
                ),
                uicommand.ViewColumn(
                    menu_text=_("&Reminder"),
                    help_text=_("Show/hide reminder column"),
                    setting="reminder",
                    viewer=self,
                ),
                uicommand.ViewColumn(
                    menu_text=_("&ID"),
                    help_text=_("Show/hide ID column"),
                    setting="id",
                    viewer=self,
                ),
            ]
        )
        return commands

    def createModeToolBarUICommands(self):
        tree_or_list_ui_command = uicommand.TaskViewerTreeOrListChoice(
            viewer=self
        )  # pylint: disable=W0201
        return super().createModeToolBarUICommands() + (
            tree_or_list_ui_command,
        )

    def hasModes(self):
        return True

    def getModeUICommands(self):
        return [
            uicommand.DisabledLabel(_("Show tasks as")),
            uicommand.Separator(),
        ] + [
            uicommand.TaskViewerTreeOrListOption(
                menu_text=menu_text,
                value=value,
                viewer=self,
            )
            for (menu_text, value) in zip(
                uicommand.TaskViewerTreeOrListChoice.choiceLabels,
                uicommand.TaskViewerTreeOrListChoice.choiceData,
            )
        ]

    def createColumnPopupMenu(self):
        return taskcoachlib.gui.menu.ColumnPopupMenu(self)

    def setSortByTaskStatusFirst(
        self, *args, **kwargs
    ):  # pylint: disable=W0221
        super().setSortByTaskStatusFirst(*args, **kwargs)
        self.show_sort_order()

    def get_sort_order_image(self):
        if self.isSortOrderAscending():
            if self.isSortByTaskStatusFirst():  # pylint: disable=E1101
                return "taskcoach_actions_arrow_down_with_status_icon"
            return "nuvola_actions_go-down"
        else:
            if self.isSortByTaskStatusFirst():  # pylint: disable=E1101
                return "taskcoach_actions_arrow_up_with_status_icon"
            return "nuvola_actions_go-up"

    def setSearchFilter(
        self, searchString, *args, **kwargs
    ):  # pylint: disable=W0221
        super().setSearchFilter(searchString, *args, **kwargs)
        if searchString:
            self.expand_all()  # pylint: disable=E1101

    def set_tree_mode(self, value):
        self.options.treemode = value
        self.presentation().set_tree_mode(value)
        self.widget.show_expand_buttons(value)
        # Mode switch goes through Sorter.reset() which fires a sort event
        # (not add/remove), so onPresentationChanged doesn't fire. The rebuild
        # recomputes scrollbars only through scroll_to_selection, which is
        # gated on there being a selection and runs synchronously. On Windows
        # the range must be recomputed unconditionally and after the layout
        # settles, so reuse the same deferred adjustment that fixes
        # expand/collapse/add/delete.
        if hasattr(self.widget, "_schedule_scrollbar_adjustment"):
            self.widget._schedule_scrollbar_adjustment()
        # Center on selected item explicitly (no-op if nothing is selected).
        if hasattr(self.widget, "scroll_to_selection_centered"):
            self.widget.scroll_to_selection_centered()
        patterns.Event(self.view_settings_changed_event_type(), self).send()

    # pylint: disable=W0621

    def renderSubject(self, task):
        return task.subject(recursive=not self.is_tree_viewer())

    def renderPlannedStartDateTime(self, task, human_readable=True):
        return self.renderedValue(
            task,
            task.plannedStartDateTime,
            lambda x: render.dateTime(x, human_readable=human_readable),
        )

    def renderDueDateTime(self, task, human_readable=True):
        return self.renderedValue(
            task,
            task.dueDateTime,
            lambda x: render.dateTime(x, human_readable=human_readable),
        )

    def renderActualStartDateTime(self, task, human_readable=True):
        return self.renderedValue(
            task,
            task.actualStartDateTime,
            lambda x: render.dateTime(x, human_readable=human_readable),
        )

    def renderCompletionDateTime(self, task, human_readable=True):
        return self.renderedValue(
            task,
            task.completionDateTime,
            lambda x: render.dateTime(x, human_readable=human_readable),
        )

    def renderRecurrence(self, task):
        return self.renderedValue(task, task.recurrence, render.recurrence)

    def renderPrerequisites(self, task):
        return self.renderSubjectsOfRelatedItems(task, task.prerequisites)

    def renderDependencies(self, task):
        return self.renderSubjectsOfRelatedItems(task, task.dependencies)

    def renderTimeLeft(self, task):
        return self.renderedValue(
            task, task.timeLeft, render.timeLeft, task.completed()
        )

    def renderTimeSpent(self, task):
        return self.renderedValue(
            task, task.timeSpent, self._render_time_spent
        )

    def renderBudget(self, task):
        return self.renderedValue(task, task.budget, self._render_budget)

    def renderBudgetLeft(self, task):
        return self.renderedValue(task, task.budgetLeft, self._render_budget)

    def renderRevenue(self, task):
        return self.renderedValue(task, task.revenue, render.monetaryAmount)

    def renderHourlyFee(self, task):
        # hourlyFee has no recursive value
        return render.monetaryAmount(task.hourlyFee())

    def renderFixedFee(self, task):
        return self.renderedValue(task, task.fixedFee, render.monetaryAmount)

    def renderPercentageComplete(self, task):
        return self.renderedValue(
            task, task.percentageComplete, render.percentage
        )

    def renderPriority(self, task):
        return self.renderedValue(task, task.priority, render.priority) + " "

    def renderReminder(self, task, human_readable=True):
        return self.renderedValue(
            task,
            task.reminder,
            lambda x: render.dateTime(x, human_readable=human_readable),
        )

    def renderedValue(self, item, get_value, render_value, *extra_render_args):
        value = get_value(recursive=False)
        template = "%s"
        if self.isItemCollapsed(item):
            recursive_value = get_value(recursive=True)
            if value != recursive_value:
                value = recursive_value
                template = "(%s)"
        return template % render_value(value, *extra_render_args)

    def statusImageIndices(self, task):
        """Return image index for the task's current status icon."""
        icon_id = task.status_icon_id()
        index = image_list_cache.get_index(icon_id)
        return {wx.TreeItemIcon_Normal: index}

    def categoryIconsImageIndices(self, task):
        """Return list of image indices for the task's category icons,
        in the order the categories' styles apply."""
        return [
            image_list_cache.get_index(c.effectiveIcon())
            for c in by_style_priority(task.categories())
            if c.effectiveIcon()
        ]

    def onEditPlannedStartDateTime(self, item, newValue):
        command.EditPlannedStartDateTimeCommand(
            items=[item],
            newValue=newValue,
            keep_delta=self.__dates_tied(item, "startdue"),
        ).do()

    def onEditDueDateTime(self, item, newValue):
        command.EditDueDateTimeCommand(
            items=[item],
            newValue=newValue,
            keep_delta=self.__dates_tied(item, "duestart"),
        ).do()

    def __dates_tied(self, item, tie):
        # The adjust modes decide what follows a date
        # (docs/DURATION_CALCULATIONS.md, Stored Duration)
        return (
            settings.view.datestied == tie
            and item.plannedDurationMode() == "implicit"
        )

    def onEditActualStartDateTime(self, item, newValue):
        command.EditActualStartDateTimeCommand(
            items=[item], newValue=newValue
        ).do()

    def onEditCompletionDateTime(self, item, newValue):
        command.EditCompletionDateTimeCommand(
            items=[item], newValue=newValue
        ).do()

    def onEditPercentageComplete(self, item, newValue):
        command.EditPercentageCompleteCommand(
            items=[item], newValue=newValue
        ).do()  # pylint: disable=E1101

    def onEditBudget(self, item, newValue):
        command.EditBudgetCommand(items=[item], newValue=newValue).do()

    def onEditPriority(self, item, newValue):
        command.EditPriorityCommand(items=[item], newValue=newValue).do()

    def onEditReminderDateTime(self, item, newValue):
        command.EditReminderDateTimeCommand(
            items=[item], newValue=newValue
        ).do()

    def onEditHourlyFee(self, item, newValue):
        command.EditHourlyFeeCommand(items=[item], newValue=newValue).do()

    def onEditFixedFee(self, item, newValue):
        command.EditFixedFeeCommand(items=[item], newValue=newValue).do()

    def needs_second_refresh(self):
        # Only these columns change every second while tracking
        return any(
            self.isVisibleColumnByName(column)
            for column in ("timeSpent", "budgetLeft", "revenue")
        )

    def get_root_items(self):
        """If the viewer is in tree mode, return the real root items. If the
        viewer is in list mode, return all items."""
        return (
            super().get_root_items()
            if self.is_tree_viewer()
            else self.presentation()
        )

    def get_item_parent(self, item):
        return super().get_item_parent(item) if self.is_tree_viewer() else None

    def children(self, item=None):
        return (
            super().children(item)
            if (self.is_tree_viewer() or item is None)
            else []
        )


class CheckableTaskViewer(TaskViewer):  # pylint: disable=W0223
    def create_widget(self):
        image_list = self.createImageList()  # Has side-effects
        self._columns = self.ordered_columns(self._createColumns())
        item_popup_menu = self.createTaskPopupMenu()
        column_popup_menu = self.createColumnPopupMenu()
        self._popupMenus.extend([item_popup_menu, column_popup_menu])
        widget = widgets.CheckTreeCtrl(
            self,
            self.columns(),
            self.onSelect,
            self.onCheck,
            uicommand.Edit(viewer=self),
            uicommand.TaskDragAndDrop(
                taskList=self.presentation(), viewer=self
            ),
            item_popup_menu,
            column_popup_menu,
            **self.widgetCreationKeywordArguments()
        )
        widget.SetImageList(image_list)  # pylint: disable=E1101
        # As the task view: list mode has no expanders' room
        widget.show_expand_buttons(self.is_tree_viewer())
        return widget

    def onCheck(self, event, final):
        pass

    def get_is_item_checked(self, task):  # pylint: disable=W0613,W0621
        return False

    def get_item_parent_has_exclusive_children(
        self, task
    ):  # pylint: disable=W0613,W0621
        return False


class TaskStatsViewer(BaseTaskViewer):  # pylint: disable=W0223
    defaultTitle = _("Task statistics")
    defaultBitmap = "nuvola_apps_kchart"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("settingsSection", "taskstatsviewer")
        super().__init__(*args, **kwargs)
        self.registerObserver(
            self.on_pie_chart_angle_changed,
            eventType="%s.piechartangle" % self.settingsSection(),
        )
        # The pie counts the statuses; the clock changes them too, in
        # its passes, after which the pie is redrawn once
        self.registerObserver(
            self.on_attribute_changed,
            eventType=task.Task.statusChangedEventType(),
        )

    def create_widget(self):
        widget = wx.lib.agw.piectrl.PieCtrl(self)
        widget.SetShowEdges(False)
        widget.SetHeight(20)
        self.initLegend(widget)
        for dummy in task.Task.possibleStatuses():
            widget._series.append(
                wx.lib.agw.piectrl.PiePart(1)
            )  # pylint: disable=W0212
        return widget

    def createClipboardToolBarUICommands(self):
        return ()

    def createEditToolBarUICommands(self):
        return ()

    def createCreationToolBarUICommands(self):
        return (
            uicommand.TaskNew(taskList=self.presentation()),
            uicommand.TaskNewFromTemplateButton(
                taskList=self.presentation(),
                icon_id="taskcoach_actions_newtmpl",
            ),
        )

    def createActionToolBarUICommands(self):
        return tuple(
            [
                uicommand.ViewerHideTasks(task_status=status, viewer=self)
                for status in task.Task.possibleStatuses()
            ]
        ) + (uicommand.ViewerPieChartAngle(viewer=self),)

    def initLegend(self, widget):
        legend = widget.GetLegend()
        legend.SetTransparent(False)
        legend.SetBackColour(wx.WHITE)
        legend.SetLabelFont(wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT))
        legend.Show()

    def refresh(self):
        self.widget.SetAngle(self.options.piechartangle / 180.0 * math.pi)
        self.refreshParts()
        self.widget.Refresh()

    def refreshParts(self):
        series = self.widget._series  # pylint: disable=W0212
        tasks = self.presentation()
        total = len(tasks)
        counts = tasks.nr_of_tasks_per_status()
        for part, status in zip(series, task.Task.possibleStatuses()):
            nr_tasks = counts[status]
            percentage = round(100.0 * nr_tasks / total) if total else 0
            part.SetLabel(status.count_label % (nr_tasks, percentage))
            part.SetValue(nr_tasks)
            part.SetColour(self.getFgColor(status))
        # PietCtrl can't handle empty pie charts:
        if total == 0:
            series[0].SetValue(1)

    def getFgColor(self, status):
        try:
            section = (
                "fgcolor_dark" if settings.window.theme_is_dark else "fgcolor"
            )
        except Exception:
            section = "fgcolor"
        color = wx.Colour(*settings.get(section, "%stasks" % status))
        if status == task.status.active and color == wx.BLACK:
            color = wx.BLUE
        return color

    def refreshItems(self, *args, **kwargs):  # pylint: disable=W0613
        self.refresh()

    def select(self, *args):
        pass

    def updateSelection(self, *args, **kwargs):
        pass

    def is_tree_viewer(self):
        return False

    def on_pie_chart_angle_changed(self, event):  # pylint: disable=W0613
        self.refresh()
