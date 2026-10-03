# -*- coding: utf-8 -*-

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

import contextlib
from taskcoachlib import patterns
from taskcoachlib.domain import task, effort, date
from taskcoachlib.i18n import _
from . import base


@contextlib.contextmanager
def _bulk_modification(command):
    """Viewers freeze while the command changes many items, and refresh
    once after."""
    patterns.Event("command.aboutToBulkModify", command).send()
    try:
        yield
    finally:
        patterns.Event("command.justBulkModified", command).send()


class EffortCommand(base.BaseCommand):  # pylint: disable=W0223
    def stopTracking(self):
        for taskToStop in self.tasksToStopTracking():
            taskToStop.stopTracking()

    def tasksToStopTracking(self):
        return self.list

    def do_command(self):
        super().do_command()
        self.stopTracking()


class DragAndDropTaskCommand(base.OrderingDragAndDropCommand):
    plural_name = _("Drag and drop tasks")

    def _isPrereqDrop(self):
        """Check if dropping on prerequisites column."""
        return self.dropColumnName == "prerequisites"

    def _isDepDrop(self):
        """Check if dropping on dependencies column."""
        return self.dropColumnName == "dependencies"

    def do_command(self):
        if self._isPrereqDrop():
            # Dropped on prerequisites column: make dragged items prerequisites of drop target
            self._itemToDropOn.add_prerequisites(self.items)
            self._itemToDropOn.addTaskAsDependencyOf(self.items)
        elif self._isDepDrop():
            # Dropped on dependencies column: make drop target a prerequisite of dragged items
            for item in self.items:
                item.add_prerequisites([self._itemToDropOn])
                item.addTaskAsDependencyOf([self._itemToDropOn])
        else:
            # Drop on other columns: make child (change parent)
            super().do_command()


class DeleteTaskCommand(base.DeleteCommand, EffortCommand):
    plural_name = _("Delete tasks")
    singular_name = _('Delete task "%s"')

    def tasksToStopTracking(self):
        return self.items

    def do_command(self):
        super().do_command()
        self.stopTracking()
        self.__removePrerequisites()

    def __removePrerequisites(self):
        for eachTask in self.items:
            prerequisites, dependencies = (
                eachTask.prerequisites(),
                eachTask.dependencies(),
            )
            eachTask.removeTaskAsDependencyOf(prerequisites)
            eachTask.removeTaskAsPrerequisiteOf(dependencies)
            eachTask.set_prerequisites([])
            eachTask.set_dependencies([])


class NewTaskCommand(base.NewItemCommand):
    singular_name = _("New task")

    def __init__(self, *args, **kwargs):
        subject = kwargs.pop("subject", _("New task"))
        super().__init__(*args, **kwargs)
        self.items = [task.Task(subject=subject, **kwargs)]

    @patterns.eventSource
    def do_command(self, event=None):
        super().do_command(event=event)
        self.addDependenciesAndPrerequisites()

    def addDependenciesAndPrerequisites(self):
        for eachTask in self.items:
            for prerequisite in eachTask.prerequisites():
                prerequisite.add_dependencies([eachTask])
            for dependency in eachTask.dependencies():
                dependency.add_prerequisites([eachTask])


class NewSubTaskCommand(base.NewSubItemCommand):
    plural_name = _("New subtasks")
    singular_name = _('New subtask of "%s"')
    # pylint: disable=E1101

    def __init__(self, *args, **kwargs):
        subject = kwargs.pop("subject", _("New subtask"))
        plannedStartDateTime = kwargs.pop(
            "plannedStartDateTime", date.DateTime()
        )
        dueDateTime = kwargs.pop("dueDateTime", date.DateTime())
        super().__init__(*args, **kwargs)
        self.items = [
            parent.newChild(
                subject=subject,
                plannedStartDateTime=max(
                    [parent.plannedStartDateTime(), plannedStartDateTime]
                ),
                dueDateTime=min([parent.dueDateTime(), dueDateTime]),
                **kwargs
            )
            for parent in self.items
        ]


class MarkCompletedCommand(EffortCommand):
    plural_name = _("Mark tasks completed")
    singular_name = _('Mark "%s" completed')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items = [
            item
            for item in self.items
            if item.completionDateTime() > date.Now()
        ]

    def do_command(self):
        with _bulk_modification(self):
            super().do_command()
            for item in self.items:
                item.set_completion_date_time(
                    task.Task.suggestedCompletionDateTime()
                )

    def tasksToStopTracking(self):
        return self.items


class MarkActiveCommand(base.BaseCommand):
    plural_name = _("Mark task active")
    singular_name = _('Mark "%s" active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items = [
            item
            for item in self.items
            if item.actualStartDateTime() > date.Now()
            or item.completionDateTime() != date.DateTime()
        ]

    def do_command(self):
        with _bulk_modification(self):
            super().do_command()
            for item in self.items:
                item.set_actual_start_date_time(
                    task.Task.suggestedActualStartDateTime()
                )
                item.set_completion_date_time(date.DateTime())


class MarkInactiveCommand(base.BaseCommand):
    plural_name = _("Mark task inactive")
    singular_name = _('Mark "%s" inactive')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items = [
            item
            for item in self.items
            if item.actualStartDateTime() != date.DateTime()
            or item.completionDateTime() != date.DateTime()
        ]

    def do_command(self):
        with _bulk_modification(self):
            super().do_command()
            for item in self.items:
                item.set_actual_start_date_time(date.DateTime())
                item.set_completion_date_time(date.DateTime())


class StartEffortCommand(EffortCommand):
    plural_name = _("Start tracking")
    singular_name = _('Start tracking "%s"')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        start = date.DateTime.now()
        self.efforts = [effort.Effort(item, start) for item in self.items]

    def do_command(self):
        super().do_command()
        self.add_efforts()

    def add_efforts(self):
        for item, new_effort in zip(self.items, self.efforts):
            item.addEffort(new_effort)


class StopEffortCommand(EffortCommand):
    plural_name = _("Stop tracking")
    singular_name = _('Stop tracking "%s"')

    def canDo(self):
        return True  # No selected items needed.

    def tasksToStopTracking(self):
        stoppable = (
            lambda effort: effort.isBeingTracked() and not effort.isTotal()
        )
        return set(
            [
                effort.task()
                for effort in (self.items if self.items else self.list)
                if stoppable(effort)
            ]
        )  # pylint: disable=W0621


class ExtremePriorityCommand(base.BaseCommand):  # pylint: disable=W0223
    delta = "Subclass responsibility"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.oldExtremePriority = self.getOldExtremePriority()

    def getOldExtremePriority(self):
        raise NotImplementedError  # pragma: no cover

    def setNewExtremePriority(self):
        newExtremePriority = self.oldExtremePriority + self.delta
        for item in self.items:
            item.setPriority(newExtremePriority)

    def do_command(self):
        super().do_command()
        self.setNewExtremePriority()


class MaxPriorityCommand(ExtremePriorityCommand):
    plural_name = _("Maximize priority")
    singular_name = _('Maximize priority of "%s"')

    delta = +1

    def getOldExtremePriority(self):
        return self.list.max_priority()


class MinPriorityCommand(ExtremePriorityCommand):
    plural_name = _("Minimize priority")
    singular_name = _('Minimize priority of "%s"')

    delta = -1

    def getOldExtremePriority(self):
        return self.list.min_priority()


class ChangePriorityCommand(base.BaseCommand):  # pylint: disable=W0223
    delta = "Subclass responsibility"

    def changePriorities(self, delta):
        for item in self.items:
            item.setPriority(item.priority() + delta)

    def do_command(self):
        super().do_command()
        self.changePriorities(self.delta)


class IncPriorityCommand(ChangePriorityCommand):
    plural_name = _("Increase priority")
    singular_name = _('Increase priority of "%s"')
    delta = +1


class DecPriorityCommand(ChangePriorityCommand):
    plural_name = _("Decrease priority")
    singular_name = _('Decrease priority of "%s"')
    delta = -1


class EditPriorityCommand(base.BaseCommand):
    plural_name = _("Change priority")
    singular_name = _('Change priority of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newPriority = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setPriority(self.__newPriority)


class EditDateTimeCommand(base.BaseCommand):
    def __init__(self, *args, **kwargs):
        self._newDateTime = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    @staticmethod
    def getDateTime(item):
        raise NotImplementedError  # pragma: no cover

    @staticmethod
    def setDateTime(item, newDateTime):
        raise NotImplementedError  # pragma: no cover

    def do_command(self):
        super().do_command()
        for item in self.items:
            self.setDateTime(item, self._newDateTime)


class EditPeriodDateTimeCommand(EditDateTimeCommand):
    """Base for date/time commands that also may have to adjust the other
    end of the period. E.g., where changing the planned start date should
    also change the due date to keep the period the same length."""

    def __init__(self, *args, **kwargs):
        self.__keep_delta = kwargs.pop("keep_delta", False)
        # Both ends given at once (a calendar drag)
        self.__other_value = kwargs.pop("other_value", None)
        super().__init__(*args, **kwargs)

    def do_command(self):
        both_ends = {
            id(item): self.__other_value is not None
            or self.__shouldAdjustItem(item)
            for item in self.items
        }
        self.__adjust_other_date_time()
        super().do_command()
        for item in self.items:
            if self.__other_value is not None:
                self.setOtherDateTime(item, self.__other_value)
            self._follow_duration_mode(item, both_ends[id(item)])

    def _follow_duration_mode(self, item, both_ends):
        """Only the planned dates have a duration mode."""

    def __adjust_other_date_time(self):
        for item in self.items:
            if self.__shouldAdjustItem(item):
                delta = self._newDateTime - self.getDateTime(item)
                newOtherDateTime = self.getOtherDateTime(item) + delta
                self.setOtherDateTime(item, newOtherDateTime)

    def __shouldAdjustItem(self, item):
        """Determine whether the other date/time of the item should be
        adjusted."""
        return self.__keep_delta and date.DateTime() not in (
            self._newDateTime,
            item.plannedStartDateTime(),
            item.dueDateTime(),
        )

    @staticmethod
    def getOtherDateTime(item):
        """Gets the date/time that represents the other end of the period."""
        raise NotImplementedError  # pragma: no cover

    @staticmethod
    def setOtherDateTime(item, newDateTime):
        """Set the date/time that represents the other end of the period."""
        raise NotImplementedError  # pragma: no cover


class PlannedPeriodMixin:
    """The planned start and due follow the task's duration mode however
    they change, as in the editor (docs/DURATION_CALCULATIONS.md, Stored
    Duration). In an adjust mode a change of the mode's input end moves
    the other end by the duration; any other change, or both ends at
    once, sets the duration to their difference. Implicit mode: the task
    keeps the duration itself."""

    input_end_of = None  # The adjust mode in which this end is the input

    def _follow_duration_mode(self, item, both_ends):
        mode = item.plannedDurationMode()
        difference = item.planned_dates_difference()
        if mode not in ("adjdue", "adjstart") or difference is None:
            return
        if mode == self.input_end_of and not both_ends:
            self.setOtherDateTime(item, self._other_end(item))
        else:
            item.setPlannedDuration(difference)


class EditPlannedStartDateTimeCommand(
    PlannedPeriodMixin, EditPeriodDateTimeCommand
):
    plural_name = _("Change planned start date")
    singular_name = _('Change planned start date of "%s"')

    @staticmethod
    def getDateTime(item):
        return item.plannedStartDateTime()

    @staticmethod
    def setDateTime(item, dateTime):
        item.set_planned_start_date_time(dateTime)

    @staticmethod
    def getOtherDateTime(item):
        return item.dueDateTime()

    @staticmethod
    def setOtherDateTime(item, dateTime):
        item.set_due_date_time(dateTime)

    input_end_of = "adjdue"

    @staticmethod
    def _other_end(item):
        return item.plannedStartDateTime() + item.plannedDuration()


class EditDueDateTimeCommand(PlannedPeriodMixin, EditPeriodDateTimeCommand):
    plural_name = _("Change due date")
    singular_name = _('Change due date of "%s"')

    @staticmethod
    def getDateTime(item):
        return item.dueDateTime()

    @staticmethod
    def setDateTime(item, dateTime):
        item.set_due_date_time(dateTime)

    @staticmethod
    def getOtherDateTime(item):
        return item.plannedStartDateTime()

    @staticmethod
    def setOtherDateTime(item, dateTime):
        item.set_planned_start_date_time(dateTime)

    input_end_of = "adjstart"

    @staticmethod
    def _other_end(item):
        return item.dueDateTime() - item.plannedDuration()


class EditActualStartDateTimeCommand(EditPeriodDateTimeCommand):
    plural_name = _("Change actual start date")
    singular_name = _('Change actual start date of "%s"')

    @staticmethod
    def getDateTime(item):
        return item.actualStartDateTime()

    @staticmethod
    def setDateTime(item, dateTime):
        item.set_actual_start_date_time(dateTime)

    @staticmethod
    def getOtherDateTime(item):
        return item.completionDateTime()

    @staticmethod
    def setOtherDateTime(item, dateTime):
        item.set_completion_date_time(dateTime)


class EditCompletionDateTimeCommand(EditDateTimeCommand, EffortCommand):
    plural_name = _("Change completion date")
    singular_name = _('Change completion date of "%s"')

    @staticmethod
    def getDateTime(item):
        return item.completionDateTime()

    @staticmethod
    def setDateTime(item, dateTime):
        item.set_completion_date_time(dateTime)

    @staticmethod
    def getOtherDateTime(item):
        return item.actualStartDateTime()

    @staticmethod
    def setOtherDateTime(item, dateTime):
        item.set_actual_start_date_time(dateTime)

    def tasksToStopTracking(self):
        return self.items


class EditReminderDateTimeCommand(EditDateTimeCommand):
    plural_name = _("Change reminder dates/times")
    singular_name = _('Change reminder date/time of "%s"')

    @staticmethod
    def getDateTime(item):
        return item.reminder()

    @staticmethod
    def setDateTime(item, dateTime):
        item.set_reminder(dateTime)


class EditRecurrenceCommand(base.BaseCommand):
    plural_name = _("Change recurrences")
    singular_name = _('Change recurrence of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newRecurrence = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    def do_command(self):
        super().do_command()
        for item in self.items:
            # Each task keeps how many times it has recurred
            recurrence = self.__newRecurrence.copy()
            recurrence.count = item.recurrence().count
            item.set_recurrence(recurrence)


class EditPercentageCompleteCommand(EffortCommand):
    plural_name = _("Change percentage complete")
    singular_name = _('Change percentage complete of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newPercentage = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setPercentageComplete(self.__newPercentage)

    def tasksToStopTracking(self):
        return self.items if self.__newPercentage == 100 else []


class EditShouldMarkCompletedCommand(base.BaseCommand):
    plural_name = _("Change when tasks are marked completed")
    singular_name = _('Change when "%s" is marked completed')

    def __init__(self, *args, **kwargs):
        self.__newShouldMarkCompleted = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.set_should_mark_completed_when_all_children_completed(
                self.__newShouldMarkCompleted
            )


class EditBudgetCommand(base.BaseCommand):
    plural_name = _("Change budgets")
    singular_name = _('Change budget of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newBudget = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.set_budget(self.__newBudget)


class EditHourlyFeeCommand(base.BaseCommand):
    plural_name = _("Change hourly fees")
    singular_name = _('Change hourly fee of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newHourlyFee = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.set_hourly_fee(self.__newHourlyFee)


class EditFixedFeeCommand(base.BaseCommand):
    plural_name = _("Change fixed fees")
    singular_name = _('Change fixed fee of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newFixedFee = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.set_fixed_fee(self.__newFixedFee)


class EditPlannedDurationCommand(base.BaseCommand):
    plural_name = _("Change planned durations")
    singular_name = _('Change planned duration of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newPlannedDuration = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setPlannedDuration(self.__newPlannedDuration)


class EditPlannedDurationModeCommand(base.BaseCommand):
    plural_name = _("Change planned duration modes")
    singular_name = _('Change planned duration mode of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newMode = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setPlannedDurationMode(self.__newMode)


class TogglePrerequisiteCommand(base.BaseCommand):
    plural_name = _("Toggle prerequisite")
    singular_name = _('Toggle prerequisite of "%s"')

    def __init__(self, *args, **kwargs):
        self.__checkedPrerequisites = set(kwargs.pop("checkedPrerequisites"))
        self.__uncheckedPrerequisites = set(
            kwargs.pop("uncheckedPrerequisites")
        )
        super().__init__(*args, **kwargs)

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.add_prerequisites(self.__checkedPrerequisites)
            item.addTaskAsDependencyOf(self.__checkedPrerequisites)
            item.remove_prerequisites(self.__uncheckedPrerequisites)
            item.removeTaskAsDependencyOf(self.__uncheckedPrerequisites)
