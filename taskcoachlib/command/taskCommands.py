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


from pubsub import pub
from taskcoachlib import patterns
from taskcoachlib.domain import task, effort, date
from taskcoachlib.i18n import _
from . import base
from . import noteCommands


class SaveTaskStateMixin(base.SaveStateMixin, base.CompositeMixin):
    pass


class EffortCommand(base.BaseCommand):  # pylint: disable=W0223
    def stopTracking(self):
        self.stoppedEfforts = []  # pylint: disable=W0201
        for taskToStop in self.tasksToStopTracking():
            self.stoppedEfforts.extend(taskToStop.activeEfforts())
            taskToStop.stopTracking()

    def startTracking(self):
        for stoppedEffort in self.stoppedEfforts:
            stoppedEffort.setStop(date.DateTime.max)

    def tasksToStopTracking(self):
        return self.list

    def do_command(self):
        super().do_command()
        self.stopTracking()

    def undo_command(self):
        super().undo_command()
        self.startTracking()

    def redo_command(self):
        super().redo_command()
        self.stopTracking()


class DragAndDropTaskCommand(base.OrderingDragAndDropCommand):
    plural_name = _("Drag and drop tasks")

    def getItemsToSave(self):
        toSave = super().getItemsToSave()
        if self._isPrereqOrDepDrop():
            toSave.extend(self.getSiblings())
        return list(
            set(toSave)
        )  # Because parent may have added siblings as well

    def _isPrereqOrDepDrop(self):
        """Check if this is a prerequisite or dependency column drop."""
        return self.dropColumnName in ("prerequisites", "dependencies")

    def _isPrereqDrop(self):
        """Check if dropping on prerequisites column."""
        return self.dropColumnName == "prerequisites"

    def _isDepDrop(self):
        """Check if dropping on dependencies column."""
        return self.dropColumnName == "dependencies"

    def do_command(self):
        if self._isPrereqDrop():
            # Dropped on prerequisites column: make dragged items prerequisites of drop target
            self._itemToDropOn.addPrerequisites(self.items)
            self._itemToDropOn.addTaskAsDependencyOf(self.items)
        elif self._isDepDrop():
            # Dropped on dependencies column: make drop target a prerequisite of dragged items
            for item in self.items:
                item.addPrerequisites([self._itemToDropOn])
                item.addTaskAsDependencyOf([self._itemToDropOn])
        else:
            # Drop on other columns: make child (change parent)
            super().do_command()

    def undo_command(self):
        if self._isPrereqDrop():
            self._itemToDropOn.removePrerequisites(self.items)
            self._itemToDropOn.removeTaskAsDependencyOf(self.items)
        elif self._isDepDrop():
            for item in self.items:
                item.removePrerequisites([self._itemToDropOn])
                item.removeTaskAsDependencyOf([self._itemToDropOn])
        else:
            super().undo_command()

    def redo_command(self):
        if self._isPrereqDrop():
            self._itemToDropOn.addPrerequisites(self.items)
            self._itemToDropOn.addTaskAsDependencyOf(self.items)
        elif self._isDepDrop():
            for item in self.items:
                item.addPrerequisites([self._itemToDropOn])
                item.addTaskAsDependencyOf([self._itemToDropOn])
        else:
            super().redo_command()


class DeleteTaskCommand(base.DeleteCommand, EffortCommand):
    plural_name = _("Delete tasks")
    singular_name = _('Delete task "%s"')

    def tasksToStopTracking(self):
        return self.items

    def do_command(self):
        super().do_command()
        self.stopTracking()
        self.__removePrerequisites()

    def undo_command(self):
        super().undo_command()
        self.startTracking()
        self.__restorePrerequisites()

    def redo_command(self):
        super().redo_command()
        self.stopTracking()
        self.__removePrerequisites()

    def __removePrerequisites(self):
        self.__relationsToRestore = dict()  # pylint: disable=W0201
        for eachTask in self.items:
            prerequisites, dependencies = (
                eachTask.prerequisites(),
                eachTask.dependencies(),
            )
            self.__relationsToRestore[eachTask] = prerequisites, dependencies
            eachTask.removeTaskAsDependencyOf(prerequisites)
            eachTask.removeTaskAsPrerequisiteOf(dependencies)
            eachTask.setPrerequisites([])
            eachTask.setDependencies([])

    def __restorePrerequisites(self):
        for eachTask, (prerequisites, dependencies) in list(
            self.__relationsToRestore.items()
        ):
            eachTask.addTaskAsDependencyOf(prerequisites)
            eachTask.addTaskAsPrerequisiteOf(dependencies)
            eachTask.setPrerequisites(prerequisites)
            eachTask.setDependencies(dependencies)


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

    @patterns.eventSource
    def undo_command(self, event=None):
        super().undo_command(event=event)
        self.removeDependenciesAndPrerequisites()

    @patterns.eventSource
    def redo_command(self, event=None):
        super().redo_command(event=event)
        self.addDependenciesAndPrerequisites()

    def addDependenciesAndPrerequisites(self):
        for eachTask in self.items:
            for prerequisite in eachTask.prerequisites():
                prerequisite.addDependencies([eachTask])
            for dependency in eachTask.dependencies():
                dependency.addPrerequisites([eachTask])

    def removeDependenciesAndPrerequisites(self):
        for eachTask in self.items:
            for prerequisite in eachTask.prerequisites():
                prerequisite.removeDependencies([eachTask])
            for dependency in eachTask.dependencies():
                dependency.removePrerequisites([eachTask])


class NewSubTaskCommand(base.NewSubItemCommand, SaveTaskStateMixin):
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
        self.saveStates(self.getTasksToSave())
        self.save_modification_datetimes()

    def getTasksToSave(self):
        # FIXME: can be simplified to: return self.getAncestors(self.items) ?
        parents = [item.parent() for item in self.items if item.parent()]
        return parents + self.getAncestors(parents)

    @patterns.eventSource
    def undo_command(self, event=None):
        super().undo_command(event=event)
        self.undoStates(event=event)

    @patterns.eventSource
    def redo_command(self, event=None):
        super().redo_command(event=event)
        self.redoStates(event=event)


class MarkCompletedCommand(base.SaveStateMixin, EffortCommand):
    plural_name = _("Mark tasks completed")
    singular_name = _('Mark "%s" completed')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items = [
            item
            for item in self.items
            if item.completionDateTime() > date.Now()
        ]
        itemsToSave = set(
            [relative for item in self.items for relative in item.family()]
        )
        self.saveStates(itemsToSave)

    def do_command(self):
        pub.sendMessage("command.aboutToBulkModify")
        try:
            super().do_command()
            for item in self.items:
                item.setCompletionDateTime(task.Task.suggestedCompletionDateTime())
        finally:
            pub.sendMessage("command.justBulkModified")

    def undo_command(self):
        pub.sendMessage("command.aboutToBulkModify")
        try:
            self.undoStates()
            super().undo_command()
        finally:
            pub.sendMessage("command.justBulkModified")

    def redo_command(self):
        pub.sendMessage("command.aboutToBulkModify")
        try:
            self.redoStates()
            super().redo_command()
        finally:
            pub.sendMessage("command.justBulkModified")

    def tasksToStopTracking(self):
        return self.items


class MarkActiveCommand(base.SaveStateMixin, base.BaseCommand):
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
        itemsToSave = set(
            [relative for item in self.items for relative in item.family()]
        )
        self.saveStates(itemsToSave)

    def do_command(self):
        pub.sendMessage("command.aboutToBulkModify")
        try:
            super().do_command()
            for item in self.items:
                item.setActualStartDateTime(
                    task.Task.suggestedActualStartDateTime()
                )
                item.setCompletionDateTime(date.DateTime())
        finally:
            pub.sendMessage("command.justBulkModified")

    def undo_command(self):
        pub.sendMessage("command.aboutToBulkModify")
        try:
            self.undoStates()
            super().undo_command()
        finally:
            pub.sendMessage("command.justBulkModified")

    def redo_command(self):
        pub.sendMessage("command.aboutToBulkModify")
        try:
            self.redoStates()
            super().redo_command()
        finally:
            pub.sendMessage("command.justBulkModified")


class MarkInactiveCommand(base.SaveStateMixin, base.BaseCommand):
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
        itemsToSave = set(
            [relative for item in self.items for relative in item.family()]
        )
        self.saveStates(itemsToSave)

    def do_command(self):
        pub.sendMessage("command.aboutToBulkModify")
        try:
            super().do_command()
            for item in self.items:
                item.setActualStartDateTime(date.DateTime())
                item.setCompletionDateTime(date.DateTime())
        finally:
            pub.sendMessage("command.justBulkModified")

    def undo_command(self):
        pub.sendMessage("command.aboutToBulkModify")
        try:
            self.undoStates()
            super().undo_command()
        finally:
            pub.sendMessage("command.justBulkModified")

    def redo_command(self):
        pub.sendMessage("command.aboutToBulkModify")
        try:
            self.redoStates()
            super().redo_command()
        finally:
            pub.sendMessage("command.justBulkModified")


class StartEffortCommand(EffortCommand):
    plural_name = _("Start tracking")
    singular_name = _('Start tracking "%s"')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        start = date.DateTime.now()
        self.efforts = [effort.Effort(item, start) for item in self.items]
        self.actualStartDateTimes = [
            (
                item.actualStartDateTime()
                if start < item.actualStartDateTime()
                else None
            )
            for item in self.items
        ]

    def do_command(self):
        super().do_command()
        self.addEfforts()

    def undo_command(self):
        self.removeEfforts()
        super().undo_command()

    def redo_command(self):
        super().redo_command()
        self.addEfforts()

    def addEfforts(self):
        for item, newEffort, currentActualStartDateTime in zip(
            self.items, self.efforts, self.actualStartDateTimes
        ):
            item.addEffort(newEffort)
            if currentActualStartDateTime:
                item.setActualStartDateTime(newEffort.getStart())

    def removeEfforts(self):
        for item, newEffort, previousActualStartDateTime in zip(
            self.items, self.efforts, self.actualStartDateTimes
        ):
            item.removeEffort(newEffort)
            if previousActualStartDateTime:
                item.setActualStartDateTime(previousActualStartDateTime)


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
        self.oldPriorities = [item.priority() for item in self.items]
        self.oldExtremePriority = self.getOldExtremePriority()

    def getOldExtremePriority(self):
        raise NotImplementedError  # pragma: no cover

    def setNewExtremePriority(self):
        newExtremePriority = self.oldExtremePriority + self.delta
        for item in self.items:
            item.setPriority(newExtremePriority)

    def restorePriorities(self):
        for item, oldPriority in zip(self.items, self.oldPriorities):
            item.setPriority(oldPriority)

    def do_command(self):
        super().do_command()
        self.setNewExtremePriority()

    def undo_command(self):
        self.restorePriorities()
        super().undo_command()

    def redo_command(self):
        super().redo_command()
        self.setNewExtremePriority()


class MaxPriorityCommand(ExtremePriorityCommand):
    plural_name = _("Maximize priority")
    singular_name = _('Maximize priority of "%s"')

    delta = +1

    def getOldExtremePriority(self):
        return self.list.maxPriority()


class MinPriorityCommand(ExtremePriorityCommand):
    plural_name = _("Minimize priority")
    singular_name = _('Minimize priority of "%s"')

    delta = -1

    def getOldExtremePriority(self):
        return self.list.minPriority()


class ChangePriorityCommand(base.BaseCommand):  # pylint: disable=W0223
    delta = "Subclass responsibility"

    def changePriorities(self, delta):
        for item in self.items:
            item.setPriority(item.priority() + delta)

    def do_command(self):
        super().do_command()
        self.changePriorities(self.delta)

    def undo_command(self):
        self.changePriorities(-self.delta)
        super().undo_command()

    def redo_command(self):
        super().redo_command()
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
        self.__oldPriorities = [item.priority() for item in self.items]

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setPriority(self.__newPriority)

    def undo_command(self):
        super().undo_command()
        for item, oldPriority in zip(self.items, self.__oldPriorities):
            item.setPriority(oldPriority)

    def redo_command(self):
        self.do_command()


class AddTaskNoteCommand(noteCommands.AddNoteCommand):
    plural_name = _("Add note to tasks")


class EditDateTimeCommand(base.BaseCommand):
    def __init__(self, *args, **kwargs):
        self._newDateTime = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldDateTimes = [self.getDateTime(item) for item in self.items]
        familyMembers = set()
        for item in self.items:
            for familyMember in item.family():
                if familyMember not in self.items:
                    familyMembers.add(familyMember)
        self.__oldFamilyMemberDateTimes = [
            (familyMember, self.getDateTime(familyMember))
            for familyMember in familyMembers
        ]

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

    def undo_command(self):
        super().undo_command()
        for item, oldDateTime in zip(self.items, self.__oldDateTimes):
            self.setDateTime(item, oldDateTime)
        for familyMember, oldDateTime in self.__oldFamilyMemberDateTimes:
            self.setDateTime(familyMember, oldDateTime)

    def redo_command(self):
        self.do_command()


class EditPeriodDateTimeCommand(EditDateTimeCommand):
    """Base for date/time commands that also may have to adjust the other
    end of the period. E.g., where changing the planned start date should
    also change the due date to keep the period the same length."""

    def __init__(self, *args, **kwargs):
        self.__keep_delta = kwargs.pop("keep_delta", False)
        super().__init__(*args, **kwargs)

    def do_command(self):
        self.__adjustOtherDateTime(direction=1)
        super().do_command()

    def undo_command(self):
        super().undo_command()
        self.__adjustOtherDateTime(direction=-1)

    def __adjustOtherDateTime(self, direction):
        for item in self.items:
            if self.__shouldAdjustItem(item):
                delta = direction * (
                    self._newDateTime - self.getDateTime(item)
                )
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


class EditPlannedStartDateTimeCommand(EditPeriodDateTimeCommand):
    plural_name = _("Change planned start date")
    singular_name = _('Change planned start date of "%s"')

    @staticmethod
    def getDateTime(item):
        return item.plannedStartDateTime()

    @staticmethod
    def setDateTime(item, dateTime):
        item.setPlannedStartDateTime(dateTime)

    @staticmethod
    def getOtherDateTime(item):
        return item.dueDateTime()

    @staticmethod
    def setOtherDateTime(item, dateTime):
        item.setDueDateTime(dateTime)


class EditDueDateTimeCommand(EditPeriodDateTimeCommand):
    plural_name = _("Change due date")
    singular_name = _('Change due date of "%s"')

    @staticmethod
    def getDateTime(item):
        return item.dueDateTime()

    @staticmethod
    def setDateTime(item, dateTime):
        item.setDueDateTime(dateTime)

    @staticmethod
    def getOtherDateTime(item):
        return item.plannedStartDateTime()

    @staticmethod
    def setOtherDateTime(item, dateTime):
        item.setPlannedStartDateTime(dateTime)


class EditActualStartDateTimeCommand(EditPeriodDateTimeCommand):
    plural_name = _("Change actual start date")
    singular_name = _('Change actual start date of "%s"')

    @staticmethod
    def getDateTime(item):
        return item.actualStartDateTime()

    @staticmethod
    def setDateTime(item, dateTime):
        item.setActualStartDateTime(dateTime)

    @staticmethod
    def getOtherDateTime(item):
        return item.completionDateTime()

    @staticmethod
    def setOtherDateTime(item, dateTime):
        item.setCompletionDateTime(dateTime)


class EditCompletionDateTimeCommand(EditDateTimeCommand, EffortCommand):
    plural_name = _("Change completion date")
    singular_name = _('Change completion date of "%s"')

    @staticmethod
    def getDateTime(item):
        return item.completionDateTime()

    @staticmethod
    def setDateTime(item, dateTime):
        item.setCompletionDateTime(dateTime)

    @staticmethod
    def getOtherDateTime(item):
        return item.actualStartDateTime()

    @staticmethod
    def setOtherDateTime(item, dateTime):
        item.setActualStartDateTime(dateTime)

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
        item.setReminder(dateTime)


class EditRecurrenceCommand(base.BaseCommand):
    plural_name = _("Change recurrences")
    singular_name = _('Change recurrence of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newRecurrence = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldRecurrences = [item.recurrence() for item in self.items]

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setRecurrence(self.__newRecurrence)

    def undo_command(self):
        super().undo_command()
        for item, oldRecurrence in zip(self.items, self.__oldRecurrences):
            item.setRecurrence(oldRecurrence)

    def redo_command(self):
        self.do_command()


class EditPercentageCompleteCommand(base.SaveStateMixin, EffortCommand):
    plurar_name = "Change percentages complete"
    singular_name = _('Change percentage complete of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newPercentage = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        itemsToSave = set(
            [relative for item in self.items for relative in item.family()]
        )
        self.saveStates(itemsToSave)

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setPercentageComplete(self.__newPercentage)

    def undo_command(self):
        self.undoStates()
        super().undo_command()

    def redo_command(self):
        self.redoStates()
        super().redo_command()

    def tasksToStopTracking(self):
        return self.items if self.__newPercentage == 100 else []


class EditShouldMarkCompletedCommand(base.BaseCommand):
    plural_name = _("Change when tasks are marked completed")
    singular_name = _('Change when "%s" is marked completed')

    def __init__(self, *args, **kwargs):
        self.__newShouldMarkCompleted = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldShouldMarkCompleted = [
            item.shouldMarkCompletedWhenAllChildrenCompleted()
            for item in self.items
        ]

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setShouldMarkCompletedWhenAllChildrenCompleted(
                self.__newShouldMarkCompleted
            )

    def undo_command(self):
        super().undo_command()
        for item, oldShouldMarkCompleted in zip(
            self.items, self.__oldShouldMarkCompleted
        ):
            item.setShouldMarkCompletedWhenAllChildrenCompleted(
                oldShouldMarkCompleted
            )

    def redo_command(self):
        self.do_command()


class EditBudgetCommand(base.BaseCommand):
    plural_name = _("Change budgets")
    singular_name = _('Change budget of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newBudget = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldBudgets = [item.budget() for item in self.items]

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setBudget(self.__newBudget)

    def undo_command(self):
        super().undo_command()
        for item, oldBudget in zip(self.items, self.__oldBudgets):
            item.setBudget(oldBudget)

    def redo_command(self):
        self.do_command()


class EditHourlyFeeCommand(base.BaseCommand):
    plural_name = _("Change hourly fees")
    singular_name = _('Change hourly fee of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newHourlyFee = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldHourlyFees = [item.hourlyFee() for item in self.items]

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setHourlyFee(self.__newHourlyFee)

    def undo_command(self):
        super().undo_command()
        for item, oldHourlyFee in zip(self.items, self.__oldHourlyFees):
            item.setHourlyFee(oldHourlyFee)

    def redo_command(self):
        self.do_command()


class EditFixedFeeCommand(base.BaseCommand):
    plural_name = _("Change fixed fees")
    singular_name = _('Change fixed fee of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newFixedFee = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldFixedFees = [item.fixedFee() for item in self.items]

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setFixedFee(self.__newFixedFee)

    def undo_command(self):
        super().undo_command()
        for item, oldFixedFee in zip(self.items, self.__oldFixedFees):
            item.setFixedFee(oldFixedFee)

    def redo_command(self):
        self.do_command()


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
            item.addPrerequisites(self.__checkedPrerequisites)
            item.addTaskAsDependencyOf(self.__checkedPrerequisites)
            item.removePrerequisites(self.__uncheckedPrerequisites)
            item.removeTaskAsDependencyOf(self.__uncheckedPrerequisites)

    def undo_command(self):
        super().undo_command()
        for item in self.items:
            item.removePrerequisites(self.__checkedPrerequisites)
            item.removeTaskAsDependencyOf(self.__checkedPrerequisites)
            item.addPrerequisites(self.__uncheckedPrerequisites)
            item.addTaskAsDependencyOf(self.__uncheckedPrerequisites)

    def redo_command(self):
        self.do_command()
