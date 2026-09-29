# -*- coding: utf-8 -*-

"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2010 Svetoslav Trochev <sal_electronics@hotmail.com>

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
from taskcoachlib.domain import date, categorizable, note, attachment
from taskcoachlib.domain.base.attribute import Attribute, SetAttribute
from weakref import WeakSet
from . import status
import ast
import contextlib
import wx


class Task(
    note.NoteOwner,
    attachment.AttachmentOwner,
    categorizable.CategorizableCompositeObject,
):

    maxDateTime = date.DateTime()

    # Nonzero during File > Merge, which replaces tasks by their
    # newest copies instead of editing them, so the parent rules of
    # addChild() and removeChild() do not run
    _merging = 0

    @staticmethod
    @contextlib.contextmanager
    def merging():
        Task._merging += 1
        try:
            yield
        finally:
            Task._merging -= 1

    def __init__(
        self,
        subject="",
        description="",
        dueDateTime=None,
        plannedStartDateTime=None,
        actualStartDateTime=None,
        completionDateTime=None,
        budget=None,
        plannedDuration=None,
        plannedDurationMode="implicit",  # implicit, adjdue, adjstart
        priority=0,
        id=None,
        hourlyFee=0,  # pylint: disable=W0622
        fixedFee=0,
        reminder=None,
        reminderBeforeSnooze=None,
        categories=None,
        efforts=None,
        shouldMarkCompletedWhenAllChildrenCompleted=None,
        recurrence=None,
        percentageComplete=0,
        prerequisites=None,
        dependencies=None,
        *args,
        **kwargs
    ):
        kwargs["id"] = id
        kwargs["subject"] = subject
        kwargs["description"] = description
        kwargs["categories"] = categories
        super().__init__(*args, **kwargs)
        # Single-source-of-truth fields, set by compute_stored_status()
        self.__computed_status = None
        self.__status_text = ""
        self.__status_icon_id = ""
        self.__status_source = ""  # Explanation of why task has this status
        self.__dueSoonHours = self.settings.getint(
            "behavior", "duesoonhours"
        )  # pylint: disable=E1101
        maxDateTime = self.maxDateTime
        self.__dueDateTime = Attribute(
            dueDateTime or maxDateTime, self, self._onDueDateTimeChanged
        )
        self.__plannedStartDateTime = Attribute(
            plannedStartDateTime or maxDateTime,
            self,
            self._onPlannedStartDateTimeChanged,
        )
        self.__actualStartDateTime = Attribute(
            actualStartDateTime or maxDateTime,
            self,
            self._onActualStartDateTimeChanged,
        )
        if completionDateTime is None and percentageComplete == 100:
            completionDateTime = date.Now()
        self.__completionDateTime = Attribute(
            completionDateTime or maxDateTime,
            self,
            self._onCompletionDateTimeChanged,
        )
        percentageComplete = (
            100
            if self.__completionDateTime.get() != maxDateTime
            else percentageComplete
        )
        self.__percentageComplete = Attribute(
            percentageComplete, self, self._onPercentageCompleteChanged
        )
        self.__budget = Attribute(
            budget or date.TimeDelta(), self, self._on_budget_changed
        )
        self.__plannedDuration = Attribute(
            plannedDuration or date.TimeDelta(),
            self,
            self._onPlannedDurationChanged,
        )
        # Normalize old mode values to new keys: implicit, adjdue, adjstart
        mode_map = {"todue": "adjdue", "fromstart": "adjstart"}
        self.__plannedDurationMode = Attribute(
            mode_map.get(plannedDurationMode, plannedDurationMode)
            or "implicit",
            self,
            self._onPlannedDurationModeChanged,
        )
        self._efforts = efforts or []
        self.__priority = Attribute(priority, self, self._onPriorityChanged)
        self.__hourlyFee = Attribute(
            hourlyFee, self, self._on_hourly_fee_changed
        )
        self.__fixedFee = Attribute(fixedFee, self, self._on_fixed_fee_changed)
        self.__reminder = Attribute(
            reminder or maxDateTime, self, self._on_reminder_changed
        )
        self.__reminder_before_snooze = (
            reminderBeforeSnooze or self.__reminder.get()
        )
        self.__recurrence = Attribute(
            date.Recurrence() if recurrence is None else recurrence,
            self,
            self._on_recurrence_changed,
        )
        self.__prerequisites = SetAttribute(
            set(prerequisites or []),
            self,
            changeEvent=self._on_prerequisites_changed,
            weak=True,
        )
        self.__dependencies = WeakSet(dependencies or [])
        self.__shouldMarkCompletedWhenAllChildrenCompleted = Attribute(
            shouldMarkCompletedWhenAllChildrenCompleted,
            self,
            self._on_should_mark_completed_changed,
        )
        for effort in self._efforts:
            effort.setTask(self)
        self.__observe_settings()

        self.compute_stored_status()
        # The effective appearance and the status transitions in time
        # (overdue, due soon, time to start) are computed by the master
        # loop (docs/MASTER_SCHEDULER_REFACTOR.md).

    @patterns.eventSource
    def __setstate__(self, state, event=None):
        super().__setstate__(state, event=event)
        self.setPlannedStartDateTime(
            state["plannedStartDateTime"], event=event
        )
        self.setActualStartDateTime(state["actualStartDateTime"], event=event)
        self.setDueDateTime(state["dueDateTime"], event=event)
        self.setCompletionDateTime(state["completionDateTime"], event=event)
        self.setPercentageComplete(state["percentageComplete"], event=event)
        self.set_recurrence(state["recurrence"], event=event)
        self.setReminder(state["reminder"], event=event)
        self.setEfforts(state["efforts"])
        self.set_budget(state["budget"], event=event)
        self.setPlannedDuration(
            state.get("plannedDuration", date.TimeDelta()), event=event
        )
        self.setPlannedDurationMode(
            state.get("plannedDurationMode", "implicit"), event=event
        )
        self.setPriority(state["priority"], event=event)
        self.set_hourly_fee(state["hourlyFee"], event=event)
        self.set_fixed_fee(state["fixedFee"], event=event)
        self.set_prerequisites(state["prerequisites"], event=event)
        self.set_dependencies(state["dependencies"], event=event)
        self.set_should_mark_completed_when_all_children_completed(
            state["shouldMarkCompletedWhenAllChildrenCompleted"], event=event
        )

    def __getstate__(self):
        state = super().__getstate__()
        state.update(
            dict(
                dueDateTime=self.__dueDateTime.get(),
                plannedStartDateTime=self.__plannedStartDateTime.get(),
                actualStartDateTime=self.__actualStartDateTime.get(),
                completionDateTime=self.__completionDateTime.get(),
                percentageComplete=self.__percentageComplete.get(),
                children=self.children(),
                parent=self.parent(),
                efforts=self._efforts,
                budget=self.__budget.get(),
                plannedDuration=self.__plannedDuration.get(),
                plannedDurationMode=self.__plannedDurationMode.get(),
                priority=self.__priority.get(),
                hourlyFee=self.hourlyFee(),
                fixedFee=self.__fixedFee.get(),
                recurrence=self.__recurrence.get().copy(),
                reminder=self.__reminder.get(),
                prerequisites=self.__prerequisites.get(),
                dependencies=set(self.__dependencies),
                shouldMarkCompletedWhenAllChildrenCompleted=(
                    self.shouldMarkCompletedWhenAllChildrenCompleted()
                ),
            )
        )
        return state

    def __getcopystate__(self):
        state = super().__getcopystate__()
        state.update(
            dict(
                plannedStartDateTime=self.__plannedStartDateTime.get(),
                dueDateTime=self.__dueDateTime.get(),
                actualStartDateTime=self.__actualStartDateTime.get(),
                completionDateTime=self.__completionDateTime.get(),
                percentageComplete=self.__percentageComplete.get(),
                efforts=[effort.copy() for effort in self._efforts],
                budget=self.__budget.get(),
                plannedDuration=self.__plannedDuration.get(),
                plannedDurationMode=self.__plannedDurationMode.get(),
                priority=self.__priority.get(),
                hourlyFee=self.hourlyFee(),
                fixedFee=self.__fixedFee.get(),
                recurrence=self.__recurrence.get().copy(),
                reminder=self.__reminder.get(),
                shouldMarkCompletedWhenAllChildrenCompleted=(
                    self.shouldMarkCompletedWhenAllChildrenCompleted()
                ),
            )
        )
        return state

    def allChildrenCompleted(self):
        """Return whether all children (non-recursively) are completed.

        Uses direct datetime check instead of computedStatus() because
        this may be called during completion event before status is recomputed.
        """
        children = self.children()
        if not children:
            return False
        return all(
            child.completionDateTime() != child.maxDateTime
            for child in children
        )

    @patterns.eventSource
    def addChild(self, child, event=None):
        if child in self.children():
            return
        wasTracking = self.isBeingTracked(recursive=True)
        super().addChild(child, event=event)
        self.childChangeEvent(child, wasTracking, event)
        if not Task._merging:
            if self.shouldBeMarkedCompleted():
                self.setCompletionDateTime(child.completionDateTime())
            elif self.completed() and not child.completed():
                self.setCompletionDateTime(self.maxDateTime)
        # Under another parent, other ancestors' prerequisites count
        child._update_status(recursive=True)

    @patterns.eventSource
    def removeChild(self, child, event=None):
        if child not in self.children():
            return
        wasTracking = self.isBeingTracked(recursive=True)
        super().removeChild(child, event=event)
        self.childChangeEvent(child, wasTracking, event)
        if not Task._merging and self.shouldBeMarkedCompleted():
            # The removed child was the last uncompleted child
            self.setCompletionDateTime(date.Now())
        child._update_status(recursive=True)

    def childChangeEvent(self, child, wasTracking, event):
        childHasTimeSpent = child.timeSpent(recursive=True)
        childHasBudget = child.budget(recursive=True)
        childHasBudgetLeft = child.budgetLeft(recursive=True)
        childHasRevenue = child.revenue(recursive=True)
        # Determine what changes due to the child being added or removed:
        if childHasTimeSpent:
            self.send_time_spent_changed()
        if childHasRevenue:
            self.send_revenue_changed()
        if childHasBudget:
            self.budget_changed_event(event)
        if childHasBudgetLeft or (
            childHasTimeSpent and (childHasBudget or self.budget())
        ):
            self.send_budget_left_changed()
        self._send_effective_priority_changed(event)
        isTracking = self.isBeingTracked(recursive=True)
        if wasTracking and not isTracking:
            self.send_tracking_changed(tracking=False)
        elif not wasTracking and isTracking:
            self.send_tracking_changed(tracking=True)

    @patterns.eventSource
    def setSubject(self, subject, event=None):
        super().setSubject(subject, event=event)
        # Linked tasks show this subject in their prerequisites and
        # dependencies
        for prerequisite in self.prerequisites():
            event.addSource(
                prerequisite, type=prerequisite.dependenciesChangedEventType()
            )
        for dependency in self.dependencies():
            event.addSource(
                dependency, type=dependency.prerequisitesChangedEventType()
            )

    def _send_to_self_and_ancestors(self, event, event_type, *value):
        """Announce a change of this task's field: its ancestors show it
        in their subtree values, so they are sources too."""
        for each_task in [self] + self.ancestors():
            event.addSource(each_task, *value, type=event_type)

    # Due date

    def dueDateTime(self, recursive=False):
        if recursive:
            childrenDueDateTimes = [
                child.dueDateTime(recursive=True)
                for child in self.children()
                if not child.completed()
            ]
            return min(childrenDueDateTimes + [self.__dueDateTime.get()])
        else:
            return self.__dueDateTime.get()

    def setDueDateTime(self, dueDateTime, event=None):
        # Not set is the latest date (docs/ATTRIBUTE_PATTERN.md)
        self.__dueDateTime.set(dueDateTime or self.maxDateTime, event=event)

    def _onDueDateTimeChanged(self, event):
        self._update_status()
        self._send_to_self_and_ancestors(
            event, self.dueDateTimeChangedEventType(), self.dueDateTime()
        )

    @classmethod
    def dueDateTimeChangedEventType(class_):
        return "task.dueDateTime"

    @staticmethod
    def dueDateTimeSortFunction(**kwargs):
        recursive = kwargs.get("tree_mode", False)
        return lambda task: task.dueDateTime(recursive=recursive)

    @classmethod
    def dueDateTimeSortEventTypes(class_):
        """The event types that influence the due date time sort order."""
        return (class_.dueDateTimeChangedEventType(),)

    # Planned start date

    def plannedStartDateTime(self, recursive=False):
        if recursive:
            childrenPlannedStartDateTimes = [
                child.plannedStartDateTime(recursive=True)
                for child in self.children()
                if not child.completed()
            ]
            return min(
                childrenPlannedStartDateTimes
                + [self.__plannedStartDateTime.get()]
            )
        else:
            return self.__plannedStartDateTime.get()

    def setPlannedStartDateTime(self, plannedStartDateTime, event=None):
        self.__plannedStartDateTime.set(
            plannedStartDateTime or self.maxDateTime, event=event
        )

    def _onPlannedStartDateTimeChanged(self, event):
        self._update_status()
        self._send_to_self_and_ancestors(
            event,
            self.plannedStartDateTimeChangedEventType(),
            self.plannedStartDateTime(),
        )

    @classmethod
    def plannedStartDateTimeChangedEventType(class_):
        return "task.plannedStartDateTime"

    @staticmethod
    def plannedStartDateTimeSortFunction(**kwargs):
        recursive = kwargs.get("tree_mode", False)
        return lambda task: task.plannedStartDateTime(recursive=recursive)

    @classmethod
    def plannedStartDateTimeSortEventTypes(class_):
        """The event types that influence the planned start date time sort
        order."""
        return (class_.plannedStartDateTimeChangedEventType(),)

    def timeLeft(self, recursive=False):
        return self.dueDateTime(recursive) - date.Now()

    @staticmethod
    def timeLeftSortFunction(**kwargs):
        recursive = kwargs.get("tree_mode", False)
        return lambda task: task.timeLeft(recursive=recursive)

    @classmethod
    def timeLeftSortEventTypes(class_):
        """The event types that influence the time left sort order."""
        return (class_.dueDateTimeChangedEventType(),)

    # Actual start date

    def actualStartDateTime(self, recursive=False):
        if recursive:
            childrenActualStartDateTimes = [
                child.actualStartDateTime(recursive=True)
                for child in self.children()
                if not child.completed()
            ]
            return min(
                childrenActualStartDateTimes
                + [self.__actualStartDateTime.get()]
            )
        else:
            return self.__actualStartDateTime.get()

    def setActualStartDateTime(
        self, actualStartDateTime, recursive=False, event=None
    ):
        if recursive:
            for child in self.children(recursive=True):
                child.setActualStartDateTime(actualStartDateTime)
        self.__actualStartDateTime.set(
            actualStartDateTime or self.maxDateTime, event=event
        )

    def _onActualStartDateTimeChanged(self, event):
        self._update_status()
        self._send_to_self_and_ancestors(
            event,
            self.actualStartDateTimeChangedEventType(),
            self.actualStartDateTime(),
        )

    @classmethod
    def actualStartDateTimeChangedEventType(class_):
        return "task.actualStartDateTime"

    @staticmethod
    def actualStartDateTimeSortFunction(**kwargs):
        recursive = kwargs.get("tree_mode", False)
        return lambda task: task.actualStartDateTime(recursive=recursive)

    @classmethod
    def actualStartDateTimeSortEventTypes(class_):
        """The event types that influence the actual start date time sort order."""
        return (class_.actualStartDateTimeChangedEventType(),)

    # Completion date

    def completionDateTime(self, recursive=False):
        if recursive:
            childrenCompletionDateTimes = [
                child.completionDateTime(recursive=True)
                for child in self.children()
                if child.completed()
            ]
            return max(
                childrenCompletionDateTimes + [self.__completionDateTime.get()]
            )
        else:
            return self.__completionDateTime.get()

    def setCompletionDateTime(self, completionDateTime=None, event=None):
        self.__completionDateTime.set(
            completionDateTime or date.Now(), event=event
        )

    def _onCompletionDateTimeChanged(self, event):
        completionDateTime = self.completionDateTime()
        isCompleted = completionDateTime != self.maxDateTime

        if isCompleted and self.recurrence():
            self.recur(completionDateTime)
            return  # recur resets completionDateTime, triggering this callback again

        if isCompleted:
            self.setReminder(None)
            self.setPercentageComplete(100)
            if self.isBeingTracked():
                self.stopTracking()

            # Parent→Children cascade: complete my incomplete children
            for child in self.children():
                if child.completionDateTime() == self.maxDateTime:
                    child.set_recurrence(event=event)  # Cleared first
                    child.setCompletionDateTime(completionDateTime)

            # Children→Parent cascade: check if parent should auto-complete
            parent = self.parent()
            if parent and parent.shouldBeMarkedCompleted():
                parent.setCompletionDateTime(completionDateTime)
        else:
            if self.percentageComplete() == 100:
                self.setPercentageComplete(0)
            # An open child reopens its completed parent, and so on up
            parent = self.parent()
            if parent and parent.completed():
                parent.setCompletionDateTime(self.maxDateTime)

        # Only open subtasks count in their parent's effective priority
        parent = self.parent()
        if parent:
            parent._send_effective_priority_changed(event)

        self._update_status()
        for dependency in self.dependencies():
            dependency._update_status(recursive=True)
        self._send_to_self_and_ancestors(
            event,
            self.completionDateTimeChangedEventType(),
            self.completionDateTime(),
        )

    @classmethod
    def completionDateTimeChangedEventType(class_):
        return "task.completionDateTime"

    def shouldBeMarkedCompleted(self):
        """Return whether this task should be marked completed. It should be
        marked completed when 1) it's not completed, 2) all of its children
        are completed, 3) its setting says it should be completed when
        all of its children are completed."""
        shouldMarkCompletedAccordingToSetting = self.settings.getboolean(
            "behavior",  # pylint: disable=E1101
            "markparentcompletedwhenallchildrencompleted",
        )
        shouldMarkCompletedAccordingToTask = (
            self.shouldMarkCompletedWhenAllChildrenCompleted()
        )
        return (
            (
                (shouldMarkCompletedAccordingToTask == True)
                or (
                    (shouldMarkCompletedAccordingToTask == None)
                    and shouldMarkCompletedAccordingToSetting
                )
            )
            and (not self.completed())
            and self.allChildrenCompleted()
        )

    @staticmethod
    def completionDateTimeSortFunction(**kwargs):
        recursive = kwargs.get("tree_mode", False)
        return lambda task: task.completionDateTime(recursive=recursive)

    @classmethod
    def completionDateTimeSortEventTypes(class_):
        """The event types that influence the completion date time sort order."""
        return (class_.completionDateTimeChangedEventType(),)

    def __observe_settings(self):
        for event_type, handler in (
            ("behavior.duesoonhours", self.on_due_soon_hours_changed),
            (
                "behavior.markparentcompletedwhenallchildrencompleted",
                self.on_mark_parent_completed_setting_changed,
            ),
        ):
            patterns.Publisher().registerObserver(
                handler, eventType=event_type, eventSource=self.settings
            )

    def on_mark_parent_completed_setting_changed(self, event=None):
        # pylint: disable=W0613
        """When the global setting changes, send a percentage completed
        changed if necessary."""
        if self.shouldMarkCompletedWhenAllChildrenCompleted() is None and any(
            [child.percentageComplete(True) for child in self.children()]
        ):
            self.percentage_complete_changed_event()

    # Task state

    def completed(self):
        """A task is completed if it has a completion date/time.

        Uses direct datetime check (SSOT) - not computedStatus() which
        is for display/reporting only and may be stale during events.
        """
        return self.completionDateTime() != self.maxDateTime

    def overdue(self):
        """A task is over due if its due date/time is in the past and it is
        not completed. Note that an over due task is also either active
        or inactive."""
        return self.computedStatus() == status.overdue

    def inactive(self):
        """A task is inactive if it is not completed and either has no planned
        start date/time or a planned start date/time in the future, and/or
        its prerequisites are not completed."""
        return self.computedStatus() == status.inactive

    def active(self):
        """A task is active if it has a planned start date/time in the past and
        it is not completed. Note that over due and due soon tasks are also
        considered to be active. So the statuses active, inactive and
        completed are disjunct, but the statuses active, due soon and over
        due are not."""
        return self.computedStatus() == status.active

    def dueSoon(self):
        """A task is due soon if it is not completed and there is still time
        left (i.e. it is not over due)."""
        return self.computedStatus() == status.duesoon

    def late(self):
        """A task is late if it is not active and its planned start date time
        is in the past."""
        return self.computedStatus() == status.late

    @classmethod
    def possibleStatuses(class_):
        return (
            status.inactive,
            status.late,
            status.active,
            status.duesoon,
            status.overdue,
            status.completed,
        )

    @classmethod
    def statusChangedEventType(class_):
        return "task.status"

    @classmethod
    def compute_status(
        cls,
        completion_dt,
        due_dt,
        actual_start_dt,
        planned_start_dt,
        due_soon_hours,
        has_incomplete_prerequisites,
        now=None,
        max_date_time=None,
    ):
        """Compute task status from date values. SINGLE SOURCE OF TRUTH.

        This is the only function that computes status. All status
        calculations must go through this method.

        Args:
            completion_dt, due_dt, actual_start_dt, planned_start_dt:
                The dates, max_date_time when not set
            due_soon_hours: Hours threshold for "due soon" status
            has_incomplete_prerequisites: Whether any prerequisite is
                not completed
            now: Current datetime (defaults to date.Now())
            max_date_time: Sentinel for unset dates (defaults to
                date.DateTime.max)

        Returns:
            (TaskStatus, source_string) tuple.
        """
        if now is None:
            now = date.Now()
        if max_date_time is None:
            max_date_time = date.DateTime.max

        # Priority order: completed > inactive(prereqs) > overdue > duesoon > active > late > inactive
        if completion_dt != max_date_time:
            return status.completed, _("Completion date is set")

        if has_incomplete_prerequisites:
            return status.inactive, _("Has incomplete prerequisites")

        if due_dt != max_date_time and due_dt < now:
            return status.overdue, _("Due date has passed")

        if due_dt != max_date_time:
            time_left = due_dt - now
            time_left_hours = time_left.total_seconds() / 3600
            if 0 <= time_left_hours < due_soon_hours:
                return (
                    status.duesoon,
                    _("Due within %d hours") % due_soon_hours,
                )

        if actual_start_dt != max_date_time and actual_start_dt <= now:
            return status.active, _("Actual start date has passed")

        if planned_start_dt != max_date_time and planned_start_dt < now:
            return status.late, _("Planned start date has passed")

        return status.inactive, _("No actual start date")

    # A reminder fires this long before its time
    REMINDER_AHEAD = date.TimeDelta(seconds=2)

    def timer_seconds(self, due_soon_hours):
        """The seconds at which time alone changes this task's status or
        fires its reminder, for the master timer list: each the first
        whole second at which a rule of compute_status() or
        processReminder() holds (docs/MASTER_SCHEDULER_REFACTOR.md).
        A date not set gives seconds at the far end, never reached."""
        latest = self.maxDateTime

        def after(moment):
            # No second exists after the latest one
            return moment + date.ONE_SECOND if moment < latest else latest

        due = self.dueDateTime()
        return [
            after(self.plannedStartDateTime()),  # Late
            self.actualStartDateTime(),  # Active
            after(due - date.TimeDelta(hours=due_soon_hours)),  # Due soon
            after(due),  # Overdue
            self.reminder() - self.REMINDER_AHEAD,  # Reminder
        ]

    def compute_stored_status(self, now=None):
        """Compute and store status fields for this task instance, at
        now: the clock by default, the master loop's tick second.

        Called from:
        - Task.__init__() — initial population on load
        - _update_status(): at once after a change of what it reads
        - the master loop, at the seconds time changes a status

        Updates __computed_status, __status_text, __status_icon_id, and __status_source.
        Fires statusChangedEventType if status actually changed.
        """
        # Check prerequisites
        has_incomplete_prereqs = any(
            prerequisite.completionDateTime() == self.maxDateTime
            for prerequisite in self.prerequisites(
                recursive=True, upwards=True
            )
        )

        # Call the single source of truth
        new_status, new_source = self.compute_status(
            completion_dt=self.completionDateTime(),
            due_dt=self.dueDateTime(),
            actual_start_dt=self.actualStartDateTime(),
            planned_start_dt=self.plannedStartDateTime(),
            due_soon_hours=self.__dueSoonHours,
            has_incomplete_prerequisites=has_incomplete_prereqs,
            now=now,
            max_date_time=self.maxDateTime,
        )

        # Update stored fields
        old_status = self.__computed_status
        self.__computed_status = new_status
        self.__status_text = (
            new_status.pluralLabel.replace(" tasks", "")
            .replace("tasks", "")
            .strip()
        )
        icon_section = self._themedSection("icon")
        self.__status_icon_id = self.settings.get(
            icon_section, "%stasks" % new_status
        )
        self.__status_source = new_source

        # Fire event if status changed
        if old_status is not None and new_status != old_status:
            patterns.Event(
                self.statusChangedEventType(), self, new_status
            ).send()

    def statusText(self):
        return self.__status_text

    def status_icon_id(self):
        return self.__status_icon_id

    def computedStatus(self, explain=False):
        """Return the computed TaskStatus object (single source of truth).

        The accessor for the status: styles, filters, sorting and the
        status bar all read it. It returns the cached TaskStatus object
        populated by compute_stored_status(), which is called:
        - On task creation/load (Task.__init__)
        - At once after a change of what it reads (_update_status)
        - The master loop, at the seconds time changes a status

        Args:
            explain: If True, return (status, source) tuple where source
                     explains why the task has this status.

        Returns:
            TaskStatus object, or (TaskStatus, source_string) if explain=True.
        """
        if explain:
            return self.__computed_status, self.__status_source
        return self.__computed_status

    # =========================================================================
    # Scheduler methods - called by the master loop
    # =========================================================================

    def processReminder(self, timestamp):
        """Process reminder state and trigger if due.

        Called by the master loop. Fires the trigger at each pass while
        the reminder is due; the controller shows its dialog once.
        """
        # Clear reminder if completed and not recurring
        if self.completed() and not self.recurrence():
            self.setReminder()
            return

        # Trigger when due; a reminder not set (the latest date) never
        # is.
        if self.reminder() <= timestamp + self.REMINDER_AHEAD:
            self.triggerReminder()

    def triggerReminder(self):
        """Trigger reminder popup for this task.

        Fires event - ReminderController subscribes and shows dialog
        if not already open. Safe to call multiple times.
        """
        patterns.Event("task.reminder.trigger", self).send()

    def on_due_soon_hours_changed(self, event=None):  # pylint: disable=W0613
        self.__dueSoonHours = self.settings.getint("behavior", "duesoonhours")
        # The status at once; the master loop moves the timer seconds
        # (docs/SCHEDULERS.md)
        self._update_status()

    # effort related methods:

    def efforts(self, recursive=False):
        childEfforts = []
        if recursive:
            for child in self.children():
                childEfforts.extend(child.efforts(recursive=True))
        return self._efforts + childEfforts

    def isBeingTracked(self, recursive=False):
        return self.activeEfforts(recursive)

    def activeEfforts(self, recursive=False):
        return [
            effort
            for effort in self.efforts(recursive)
            if effort.isBeingTracked()
        ]

    def addEffort(self, effort):
        if effort in self._efforts:
            return
        wasTracking = self.isBeingTracked()
        oldValue = self._efforts[:]
        self._efforts.append(effort)
        if effort.getStart() < self.actualStartDateTime():
            self.setActualStartDateTime(effort.getStart())
        self.__send_efforts_changed(oldValue)
        if effort.isBeingTracked() and not wasTracking:
            self.send_tracking_changed(tracking=True)
        self.send_time_spent_changed()

    @classmethod
    def effortsChangedEventType(class_):
        return "task.efforts"

    def __send_efforts_changed(self, old_efforts):
        # Tuples: event values must be hashable
        patterns.Event(
            self.effortsChangedEventType(),
            self,
            (tuple(self._efforts), tuple(old_efforts)),
        ).send()

    def __send_to_ancestors_too(self, event_type, value, ancestor_value):
        """One event for the task and its ancestors, which show the
        value too; ancestor_value(ancestor) gives theirs."""
        event = patterns.Event(event_type, self, value)
        for ancestor in self.ancestors():
            event.addSource(ancestor, ancestor_value(ancestor))
        event.send()

    def send_tracking_changed(self, tracking):
        self.__send_to_ancestors_too(
            self.trackingChangedEventType(), tracking, lambda _: tracking
        )

    def removeEffort(self, effort):
        if effort not in self._efforts:
            return
        oldValue = self._efforts[:]
        self._efforts.remove(effort)
        self.__send_efforts_changed(oldValue)
        if effort.isBeingTracked() and not self.isBeingTracked():
            self.send_tracking_changed(tracking=False)
        self.send_time_spent_changed()

    def stopTracking(self):
        for effort in self.activeEfforts():
            effort.setStop()

    def setEfforts(self, efforts):
        if efforts == self._efforts:
            return
        oldValue = self._efforts[:]
        self._efforts = efforts
        self.__send_efforts_changed(oldValue)
        self.send_time_spent_changed()

    @classmethod
    def trackingChangedEventType(class_):
        return "task.track"

    # Time spent

    def timeSpent(self, recursive=False):
        return sum(
            (effort.timeSpent() for effort in self.efforts(recursive)),
            date.TimeDelta(),
        )

    def send_time_spent_changed(self):
        self.__send_to_ancestors_too(
            self.timeSpentChangedEventType(),
            self.timeSpent(),
            lambda ancestor: ancestor.timeSpent(),
        )
        if self.budget(recursive=True):
            self.send_budget_left_changed()
        if self.hourlyFee() > 0:
            self.send_revenue_changed()

    @classmethod
    def timeSpentChangedEventType(class_):
        return "task.timeSpent"

    @staticmethod
    def timeSpentSortFunction(**kwargs):
        recursive = kwargs.get("tree_mode", False)
        return lambda task: task.timeSpent(recursive=recursive)

    @classmethod
    def timeSpentSortEventTypes(class_):
        """The event types that influence the time spent sort order."""
        return (class_.timeSpentChangedEventType(),)

    # Budget

    def budget(self, recursive=False):
        result = self.__budget.get()
        if recursive:
            for task in self.children():
                result += task.budget(recursive)
        return result

    def set_budget(self, budget, event=None):
        self.__budget.set(budget, event=event)

    def _on_budget_changed(self, event):
        self.budget_changed_event(event)
        self.send_budget_left_changed()

    def budget_changed_event(self, event):
        # Ancestors show it in their recursive budget
        event.addSource(
            self, self.budget(), type=self.budgetChangedEventType()
        )
        for ancestor in self.ancestors():
            event.addSource(
                ancestor,
                ancestor.budget(recursive=True),
                type=ancestor.budgetChangedEventType(),
            )

    @classmethod
    def budgetChangedEventType(class_):
        return "task.budget"

    @staticmethod
    def budgetSortFunction(**kwargs):
        recursive = kwargs.get("tree_mode", False)
        return lambda task: task.budget(recursive=recursive)

    @classmethod
    def budgetSortEventTypes(class_):
        """The event types that influence the budget sort order."""
        return (class_.budgetChangedEventType(),)

    # Budget left

    def budgetLeft(self, recursive=False):
        budget = self.budget(recursive)
        return budget - self.timeSpent(recursive)

    def send_budget_left_changed(self):
        self.__send_to_ancestors_too(
            self.budgetLeftChangedEventType(),
            self.budgetLeft(),
            lambda ancestor: ancestor.budgetLeft(recursive=True),
        )

    @classmethod
    def budgetLeftChangedEventType(class_):
        return "task.budgetLeft"

    @staticmethod
    def budgetLeftSortFunction(**kwargs):
        recursive = kwargs.get("tree_mode", False)
        return lambda task: task.budgetLeft(recursive=recursive)

    @classmethod
    def budgetLeftSortEventTypes(class_):
        """The event types that influence the budget left sort order."""
        return (class_.budgetLeftChangedEventType(),)

    # Planned duration

    def plannedDuration(self):
        """Return the planned duration for this task."""
        return self.__plannedDuration.get()

    def setPlannedDuration(self, plannedDuration, event=None):
        self.__plannedDuration.set(plannedDuration, event=event)

    def _onPlannedDurationChanged(self, event):
        event.addSource(
            self,
            self.plannedDuration(),
            type=self.plannedDurationChangedEventType(),
        )

    @classmethod
    def plannedDurationChangedEventType(class_):
        return "task.plannedDuration"

    @staticmethod
    def plannedDurationSortFunction(**kwargs):
        return lambda task: task.plannedDuration()

    @classmethod
    def plannedDurationSortEventTypes(class_):
        """The event types that influence the planned duration sort order."""
        return (class_.plannedDurationChangedEventType(),)

    # Planned duration mode

    def plannedDurationMode(self):
        """Return the planned duration mode: 'implicit', 'adjdue', or 'adjstart'."""
        return self.__plannedDurationMode.get()

    def setPlannedDurationMode(self, mode, event=None):
        mode_map = {"todue": "adjdue", "fromstart": "adjstart"}
        mode = mode_map.get(mode, mode) or "implicit"
        self.__plannedDurationMode.set(mode, event=event)

    def _onPlannedDurationModeChanged(self, event):
        event.addSource(
            self,
            self.plannedDurationMode(),
            type=self.plannedDurationModeChangedEventType(),
        )

    @classmethod
    def plannedDurationModeChangedEventType(class_):
        return "task.plannedDurationMode"

    # Styles by status: the effective styles' last source
    # (docs/TASK_STATUS.md, Appearance Inheritance Overview)

    def statusFgColor(self):
        return self.fgColorForStatus(self.computedStatus())

    @classmethod
    def _themedSection(class_, section):
        try:
            from taskcoachlib.config import settings2

            return (
                section + "_dark"
                if settings2.window.theme_is_dark
                else section
            )
        except Exception as e:
            from taskcoachlib.meta.debug import log_step

            log_step("_themedSection(%s): %s" % (section, e), prefix="THEME")
            return section

    @classmethod
    def fgColorForStatus(class_, taskStatus):
        section = class_._themedSection("fgcolor")
        return wx.Colour(
            *ast.literal_eval(
                class_.settings.get(section, "%stasks" % taskStatus)
            )
        )  # pylint: disable=E1101

    def statusBgColor(self):
        return self.bgColorForStatus(self.computedStatus())

    @classmethod
    def bgColorForStatus(class_, taskStatus):
        section = class_._themedSection("bgcolor")
        return wx.Colour(
            *ast.literal_eval(
                class_.settings.get(section, "%stasks" % taskStatus)
            )
        )  # pylint: disable=E1101

    def statusFont(self):
        return self.fontForStatus(self.computedStatus())

    @classmethod
    def fontForStatus(class_, taskStatus):
        section = class_._themedSection("font")
        nativeInfoString = class_.settings.get(
            section, "%stasks" % taskStatus
        )  # pylint: disable=E1101
        return (
            wx.FontFromNativeInfoString(nativeInfoString)
            if nativeInfoString
            else None
        )

    def _update_status(self, recursive=False):
        """The status at once after a change of what it reads, without
        waiting for the master loop's next tick (docs/TASK_STATUS.md,
        Immediate Updates); the styles follow at that tick."""
        self.compute_stored_status()
        if recursive:
            for child in self.children():
                child._update_status(recursive=True)

    # percentage Complete

    def percentageComplete(self, recursive=False):
        if recursive:
            if self.shouldMarkCompletedWhenAllChildrenCompleted() is None:
                # pylint: disable=E1101
                ignore_me = self.settings.getboolean(
                    "behavior", "markparentcompletedwhenallchildrencompleted"
                )
            else:
                ignore_me = self.shouldMarkCompletedWhenAllChildrenCompleted()
            percentages = []
            if self.__percentageComplete.get() > 0 or not ignore_me:
                percentages.append(self.__percentageComplete.get())
            percentages.extend(
                [
                    child.percentageComplete(recursive)
                    for child in self.children()
                ]
            )
            return sum(percentages) // len(percentages) if percentages else 0
        else:
            return self.__percentageComplete.get()

    def setPercentageComplete(self, percentage, event=None):
        self.__percentageComplete.set(percentage, event=event)

    def _onPercentageCompleteChanged(self, event):
        percentage = self.__percentageComplete.get()
        if percentage == 100 and self.completionDateTime() == self.maxDateTime:
            self.setCompletionDateTime(date.Now())
        elif (
            percentage != 100 and self.completionDateTime() != self.maxDateTime
        ):
            self.setCompletionDateTime(self.maxDateTime)
        if (
            0 < percentage < 100
            and self.actualStartDateTime() == date.DateTime()
        ):
            self.setActualStartDateTime(date.Now())
        self.percentage_complete_changed_event(event=event)

    @patterns.eventSource
    def percentage_complete_changed_event(self, event=None):
        """The percentage, and so the recursive percentages of the
        ancestors, changed."""
        event.addSource(
            self,
            self.percentageComplete(),
            type=self.percentageCompleteChangedEventType(),
        )
        for ancestor in self.ancestors():
            event.addSource(
                ancestor,
                ancestor.percentageComplete(recursive=True),
                type=ancestor.percentageCompleteChangedEventType(),
            )

    @staticmethod
    def percentageCompleteSortFunction(**kwargs):
        recursive = kwargs.get("tree_mode", False)
        return lambda task: task.percentageComplete(recursive=recursive)

    @classmethod
    def percentageCompleteSortEventTypes(class_):
        """The event types that influence the percentage complete sort order."""
        return (class_.percentageCompleteChangedEventType(),)

    @classmethod
    def percentageCompleteChangedEventType(class_):
        return "task.percentageComplete"

    # priority

    def priority(self, recursive=False):
        # recursive: the subtree value (core field, docs/TASK_FIELDS.md)
        return (
            self.effective_priority() if recursive else self.__priority.get()
        )

    def setPriority(self, priority, event=None):
        self.__priority.set(priority, event=event)

    def _onPriorityChanged(self, event):
        event.addSource(self, type=self.priorityChangedEventType())
        self._send_effective_priority_changed(event)

    @classmethod
    def priorityChangedEventType(class_):
        return "task.priority"

    @staticmethod
    def prioritySortFunction(**kwargs):
        # Core field: tree mode sorts by the subtree value
        # (docs/TASK_FIELDS.md)
        recursive = kwargs.get("tree_mode", False)
        return lambda task: task.priority(recursive=recursive)

    @classmethod
    def prioritySortEventTypes(class_):
        """The event types that influence the priority sort order."""
        return (
            class_.priorityChangedEventType(),
            class_.effective_priority_changed_event_type(),
        )

    # Direct priority (docs/TASK_FIELDS.md): the stored priority, in
    # both modes

    @staticmethod
    def directPrioritySortFunction(**kwargs):
        return lambda task: task.priority()

    @classmethod
    def directPrioritySortEventTypes(cls):
        """The event types that influence the direct priority sort
        order."""
        return (cls.priorityChangedEventType(),)

    # Effective priority (docs/TASK_FIELDS.md)

    def effective_priority(self):
        """The highest of the task's own priority and its open
        subtasks' effective priorities. Computed, not saved."""
        return max(
            [self.priority()]
            + [
                child.effective_priority()
                for child in self.children()
                if not child.completed()
            ]
        )

    def _send_effective_priority_changed(self, event):
        # The task and its ancestors are the only effective priorities
        # a change below them can move
        self._send_to_self_and_ancestors(
            event, self.effective_priority_changed_event_type()
        )

    @classmethod
    def effective_priority_changed_event_type(cls):
        return "task.effectivePriority"

    @staticmethod
    def effectivePrioritySortFunction(**kwargs):
        return lambda task: task.effective_priority()

    @classmethod
    def effectivePrioritySortEventTypes(cls):
        """The event types that influence the effective priority sort
        order."""
        return (cls.effective_priority_changed_event_type(),)

    # Hourly fee

    def hourlyFee(self, recursive=False):  # pylint: disable=W0613
        return self.__hourlyFee.get()

    def set_hourly_fee(self, hourly_fee, event=None):
        self.__hourlyFee.set(hourly_fee, event=event)

    def _on_hourly_fee_changed(self, event):
        event.addSource(
            self, self.hourlyFee(), type=self.hourlyFeeChangedEventType()
        )
        if self.timeSpent() > date.TimeDelta():
            self.send_revenue_changed()
            for effort in self.efforts():
                effort.send_revenue_changed()

    @classmethod
    def hourlyFeeChangedEventType(class_):
        return "task.hourlyFee"

    @staticmethod  # pylint: disable=W0613
    def hourlyFeeSortFunction(**kwargs):
        return lambda task: task.hourlyFee()

    @classmethod
    def hourlyFeeSortEventTypes(class_):
        """The event types that influence the hourly fee sort order."""
        return (class_.hourlyFeeChangedEventType(),)

    # Fixed fee

    def fixedFee(self, recursive=False):
        childFixedFees = (
            sum(child.fixedFee(recursive) for child in self.children())
            if recursive
            else 0
        )
        return self.__fixedFee.get() + childFixedFees

    def set_fixed_fee(self, fixed_fee, event=None):
        self.__fixedFee.set(fixed_fee, event=event)

    def _on_fixed_fee_changed(self, event):
        # Ancestors show it in their recursive fixed fee
        event.addSource(
            self, self.fixedFee(), type=self.fixedFeeChangedEventType()
        )
        for ancestor in self.ancestors():
            event.addSource(
                ancestor,
                ancestor.fixedFee(recursive=True),
                type=ancestor.fixedFeeChangedEventType(),
            )
        self.send_revenue_changed()

    @classmethod
    def fixedFeeChangedEventType(class_):
        return "task.fixedFee"

    @staticmethod
    def fixedFeeSortFunction(**kwargs):
        recursive = kwargs.get("tree_mode", False)
        return lambda task: task.fixedFee(recursive=recursive)

    @classmethod
    def fixedFeeSortEventTypes(class_):
        """The event types that influence the fixed fee sort order."""
        return (class_.fixedFeeChangedEventType(),)

    # Revenue

    def revenue(self, recursive=False):
        childRevenues = (
            sum(child.revenue(recursive) for child in self.children())
            if recursive
            else 0
        )
        return (
            self.timeSpent().hours() * self.hourlyFee()
            + self.fixedFee()
            + childRevenues
        )

    def send_revenue_changed(self):
        self.__send_to_ancestors_too(
            self.revenueChangedEventType(),
            self.revenue(),
            lambda ancestor: ancestor.revenue(recursive=True),
        )

    @classmethod
    def revenueChangedEventType(class_):
        return "task.revenue"

    @staticmethod
    def revenueSortFunction(**kwargs):
        recursive = kwargs.get("tree_mode", False)
        return lambda task: task.revenue(recursive=recursive)

    @classmethod
    def revenueSortEventTypes(class_):
        """The event types that influence the revenue sort order."""
        return (class_.revenueChangedEventType(),)

    # reminder

    def reminder(
        self, recursive=False, includeSnooze=True
    ):  # pylint: disable=W0613
        if recursive:
            reminders = [
                child.reminder(recursive=True) for child in self.children()
            ]
            return min(reminders + [self.__reminder.get()])
        else:
            return (
                self.__reminder.get()
                if includeSnooze
                else self.__reminder_before_snooze
            )

    def setReminder(self, reminder_date_time=None, event=None):
        # Not set is the latest date (docs/ATTRIBUTE_PATTERN.md)
        reminder_date_time = reminder_date_time or self.maxDateTime
        if reminder_date_time == self.__reminder.get():
            return
        self.__reminder_before_snooze = reminder_date_time
        self.__reminder.set(reminder_date_time, event=event)

    def snooze_reminder(self, time_delta, now=date.Now):
        if time_delta:
            self.__reminder.set(now() + time_delta)
        elif self.recurrence():
            self.__reminder.set(self.maxDateTime)
        else:
            self.setReminder()

    def _on_reminder_changed(self, event):
        self._send_to_self_and_ancestors(
            event, self.reminderChangedEventType(), self.reminder()
        )

    @classmethod
    def reminderChangedEventType(class_):
        return "task.reminder"

    @staticmethod
    def reminderSortFunction(**kwargs):
        recursive = kwargs.get("tree_mode", False)
        return lambda task: task.reminder(recursive=recursive)

    @classmethod
    def reminderSortEventTypes(class_):
        """The event types that influence the reminder sort order."""
        return (class_.reminderChangedEventType(),)

    # Recurrence

    def recurrence(self, recursive=False, upwards=False):
        own = self.__recurrence.get()
        if not own and recursive and upwards and self.parent():
            return self.parent().recurrence(recursive, upwards)
        elif recursive and not upwards:
            recurrences = [
                child.recurrence() for child in self.children(recursive)
            ]
            recurrences.append(own)
            recurrences = [r for r in recurrences if r]
            return min(recurrences) if recurrences else own
        else:
            return own

    def set_recurrence(self, recurrence=None, event=None):
        self.__recurrence.set(recurrence or date.Recurrence(), event=event)

    def _on_recurrence_changed(self, event):
        # Without the value: a Recurrence is mutable, so not hashable
        self._send_to_self_and_ancestors(
            event, self.recurrenceChangedEventType()
        )

    @classmethod
    def recurrenceChangedEventType(class_):
        return "task.recurrence"

    @patterns.eventSource
    def recur(self, completionDateTime=None, event=None):
        from taskcoachlib.meta.debug import log_step

        completionDateTime = completionDateTime or date.Now()
        self.setCompletionDateTime(self.maxDateTime)
        recur = self.recurrence(recursive=True, upwards=True)

        if not recur.unit:
            log_step(
                "recur() on %r: resolved recurrence has no unit"
                % self.subject(),
                prefix="RECUR",
            )

        current_due = self.dueDateTime()
        current_planned_start = self.plannedStartDateTime()

        if current_due != date.DateTime():
            basis = (
                completionDateTime
                if recur.recurBasedOnCompletion
                else current_due
            )
            next_due = recur(basis, next=False)
            next_due = next_due.replace(
                hour=current_due.hour,
                minute=current_due.minute,
                second=current_due.second,
            )
            if next_due == current_due:
                log_step(
                    "recur() on %r: date did not advance (%s)"
                    % (self.subject(), current_due),
                    prefix="RECUR",
                )
            self.setDueDateTime(next_due)

        if current_planned_start != date.DateTime():
            if date.DateTime() not in (
                current_planned_start,
                current_due,
            ):
                task_duration = current_due - current_planned_start
                next_planned_start = next_due - task_duration
            else:
                basis = (
                    completionDateTime
                    if recur.recurBasedOnCompletion
                    else current_planned_start
                )
                next_planned_start = recur(basis, next=False)
            next_planned_start = next_planned_start.replace(
                hour=current_planned_start.hour,
                minute=current_planned_start.minute,
                second=current_planned_start.second,
            )
            self.setPlannedStartDateTime(next_planned_start)

        self.setActualStartDateTime(date.DateTime())
        self.setPercentageComplete(0)
        if self.reminder(includeSnooze=False) != self.maxDateTime:
            next_reminder = recur(
                self.reminder(includeSnooze=False), next=False
            )
            self.setReminder(next_reminder)
        for child in self.children():
            if not child.recurrence():
                child.recur(completionDateTime, event=event)
        # A copy, so the Attribute sees the count change: it is saved
        if self.recurrence():
            recurrence = self.recurrence().copy()
            recurrence(next=True)
            self.set_recurrence(recurrence, event=event)

    @staticmethod
    def recurrenceSortFunction(**kwargs):
        recursive = kwargs.get("tree_mode", False)
        return lambda task: task.recurrence(recursive=recursive)

    @classmethod
    def recurrenceSortEventTypes(class_):
        """The event types that influence the recurrence sort order."""
        return (class_.recurrenceChangedEventType(),)

    # Prerequisites

    def prerequisites(self, recursive=False, upwards=False):
        prerequisites = self.__prerequisites.get()
        if recursive and upwards and self.parent() is not None:
            prerequisites |= self.parent().prerequisites(
                recursive=True, upwards=True
            )
        elif recursive and not upwards:
            for child in self.children(recursive=True):
                prerequisites |= child.prerequisites()
        return prerequisites

    def set_prerequisites(self, prerequisites, event=None):
        self.__prerequisites.set(set(prerequisites), event=event)

    def add_prerequisites(self, prerequisites, event=None):
        self.__prerequisites.add(set(prerequisites), event=event)

    def remove_prerequisites(self, prerequisites, event=None):
        self.__prerequisites.remove(set(prerequisites), event=event)

    def _on_prerequisites_changed(self, event, *prerequisites):
        self._update_status(recursive=True)
        # Without the value: a set is not hashable
        event.addSource(self, type=self.prerequisitesChangedEventType())

    def addTaskAsDependencyOf(self, prerequisites):
        for prerequisite in prerequisites:
            prerequisite.add_dependencies([self])

    def removeTaskAsDependencyOf(self, prerequisites):
        for prerequisite in prerequisites:
            prerequisite.remove_dependencies([self])

    @classmethod
    def prerequisitesChangedEventType(class_):
        return "task.prerequisites"

    @staticmethod
    def prerequisitesSortFunction(**kwargs):
        """Return a sort key for sorting by prerequisites. Since a task can
        have multiple prerequisites we first sort the prerequisites by their
        subjects. If the sorter is in tree mode, we also take the
        prerequisites of the children of the task into account, after the
        prerequisites of the task itself. If the sorter is in list
        mode we also take the prerequisites of the parent (recursively) into
        account, again after the prerequisites of the categorizable itself."""

        def sortKeyFunction(task):
            def sortedSubjects(items):
                return sorted([item.subject(recursive=True) for item in items])

            prerequisites = task.prerequisites()
            sortedPrerequisiteSubjects = sortedSubjects(prerequisites)
            isListMode = not kwargs.get("tree_mode", False)
            childPrerequisites = (
                task.prerequisites(recursive=True, upwards=isListMode)
                - prerequisites
            )
            sortedPrerequisiteSubjects.extend(
                sortedSubjects(childPrerequisites)
            )
            return sortedPrerequisiteSubjects

        return sortKeyFunction

    @classmethod
    def prerequisitesSortEventTypes(class_):
        """The event types that influence the prerequisites sort order."""
        return (class_.prerequisitesChangedEventType(),)

    # Dependencies

    def dependencies(self, recursive=False, upwards=False):
        dependencies = set(self.__dependencies)
        if recursive and upwards and self.parent() is not None:
            dependencies |= self.parent().dependencies(
                recursive=True, upwards=True
            )
        elif recursive and not upwards:
            for child in self.children(recursive=True):
                dependencies |= child.dependencies()
        return dependencies

    # The reverse of prerequisites, not saved: no modification date

    def set_dependencies(self, dependencies, event=None):
        dependencies = set(dependencies)
        if dependencies != self.dependencies():
            self.__set_dependencies(dependencies, event=event)

    def add_dependencies(self, dependencies, event=None):
        dependencies = set(dependencies)
        if not dependencies <= self.dependencies():
            self.__set_dependencies(
                self.dependencies() | dependencies, event=event
            )

    def remove_dependencies(self, dependencies, event=None):
        dependencies = set(dependencies)
        if not self.dependencies().isdisjoint(dependencies):
            self.__set_dependencies(
                self.dependencies() - dependencies, event=event
            )

    @patterns.eventSource
    def __set_dependencies(self, dependencies, event=None):
        self.__dependencies = WeakSet(dependencies)
        event.addSource(self, type=self.dependenciesChangedEventType())

    def addTaskAsPrerequisiteOf(self, dependencies):
        for dependency in dependencies:
            dependency.add_prerequisites([self])

    def removeTaskAsPrerequisiteOf(self, dependencies):
        for dependency in dependencies:
            dependency.remove_prerequisites([self])

    @classmethod
    def dependenciesChangedEventType(class_):
        return "task.dependencies"

    @staticmethod
    def dependenciesSortFunction(**kwargs):
        """Return a sort key for sorting by dependencies. Since a task can
        have multiple dependencies we first sort the dependencies by their
        subjects. If the sorter is in tree mode, we also take the
        dependencies of the children of the task into account, after the
        dependencies of the task itself. If the sorter is in list
        mode we also take the dependencies of the parent (recursively) into
        account, again after the dependencies of the categorizable itself."""

        def sortKeyFunction(task):
            def sortedSubjects(items):
                return sorted([item.subject(recursive=True) for item in items])

            dependencies = task.dependencies()
            sortedDependencySubjects = sortedSubjects(dependencies)
            isListMode = not kwargs.get("tree_mode", False)
            childDependencies = (
                task.dependencies(recursive=True, upwards=isListMode)
                - dependencies
            )
            sortedDependencySubjects.extend(sortedSubjects(childDependencies))
            return sortedDependencySubjects

        return sortKeyFunction

    @classmethod
    def dependenciesSortEventTypes(class_):
        """The event types that influence the dependencies sort order."""
        return (class_.dependenciesChangedEventType(),)

    # behavior

    def set_should_mark_completed_when_all_children_completed(
        self, value, event=None
    ):
        self.__shouldMarkCompletedWhenAllChildrenCompleted.set(
            value, event=event
        )

    def _on_should_mark_completed_changed(self, event):
        event_type = (
            self.shouldMarkCompletedWhenAllChildrenCompletedChangedEventType()
        )
        event.addSource(
            self,
            self.shouldMarkCompletedWhenAllChildrenCompleted(),
            type=event_type,
        )
        # It decides whether the recursive percentage counts this task
        self.percentage_complete_changed_event(event=event)

    @classmethod
    def shouldMarkCompletedWhenAllChildrenCompletedChangedEventType(class_):
        return "task.shouldMarkCompletedWhenAllChildrenCompleted"

    def shouldMarkCompletedWhenAllChildrenCompleted(self):
        return self.__shouldMarkCompletedWhenAllChildrenCompleted.get()

    @classmethod
    def suggestedPlannedStartDateTime(cls, now=date.Now):
        return cls.suggested_date_time("defaultplannedstartdatetime", now)

    @classmethod
    def suggestedActualStartDateTime(cls, now=date.Now):
        return cls.suggested_date_time("defaultactualstartdatetime", now)

    @classmethod
    def suggestedDueDateTime(cls, now=date.Now):
        return cls.suggested_date_time("defaultduedatetime", now)

    @classmethod
    def suggestedCompletionDateTime(cls, now=date.Now):
        return cls.suggested_date_time("defaultcompletiondatetime", now)

    @classmethod
    def suggestedReminderDateTime(cls, now=date.Now):
        return cls.suggested_date_time("defaultreminderdatetime", now)

    @classmethod
    def suggested_date_time(cls, default_date_time_setting, now=date.Now):
        # pylint: disable=E1101,W0142
        default_date_time = cls.settings.get("view", default_date_time_setting)
        dummy_prefix, default_date, default_time = default_date_time.split("_")
        date_time = now()
        current_time = dict(
            hour=date_time.hour,
            minute=date_time.minute,
            second=date_time.second,
        )
        if default_date == "tomorrow":
            date_time += date.ONE_DAY
        elif default_date == "dayaftertomorrow":
            date_time += date.ONE_DAY + date.ONE_DAY
        elif default_date == "nextfriday":
            date_time = (
                (date_time + date.ONE_DAY)
                .endOfWorkWeek()
                .replace(**current_time)
            )
        elif default_date == "nextmonday":
            date_time = (
                (date_time + date.ONE_WEEK)
                .startOfWorkWeek()
                .replace(**current_time)
            )

        if default_time == "startofday":
            return date_time.startOfDay()
        elif default_time == "startofworkingday":
            start_hour = cls.settings.getint("view", "efforthourstart")
            return date_time.replace(hour=start_hour, minute=0, second=0)
        elif default_time == "currenttime":
            return date_time
        elif default_time == "endofworkingday":
            end_hour = cls.settings.getint("view", "efforthourend")
            # 24 is how older versions said "end of day" (Preferences
            # migrates it only when saved); replace() rejects hour 24.
            if (
                cls.settings.getboolean("view", "efforthourend_endofday")
                or end_hour >= 24
            ):
                end_hour, minute, second = 23, 59, 59
            else:
                minute, second = 0, 0
            return date_time.replace(
                hour=end_hour, minute=minute, second=second
            )
        elif default_time == "endofday":
            return date_time.endOfDay()

    @classmethod
    def modificationEventTypes(class_):
        eventTypes = super(Task, class_).modificationEventTypes()
        return eventTypes + [
            class_.plannedStartDateTimeChangedEventType(),
            class_.dueDateTimeChangedEventType(),
            class_.actualStartDateTimeChangedEventType(),
            class_.completionDateTimeChangedEventType(),
            class_.effortsChangedEventType(),
            class_.budgetChangedEventType(),
            class_.percentageCompleteChangedEventType(),
            class_.priorityChangedEventType(),
            class_.hourlyFeeChangedEventType(),
            class_.fixedFeeChangedEventType(),
            class_.reminderChangedEventType(),
            class_.recurrenceChangedEventType(),
            class_.prerequisitesChangedEventType(),
            class_.dependenciesChangedEventType(),
            class_.shouldMarkCompletedWhenAllChildrenCompletedChangedEventType(),
            class_.plannedDurationChangedEventType(),
            class_.plannedDurationModeChangedEventType(),
        ]
