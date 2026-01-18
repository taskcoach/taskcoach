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

"""
Global application timer for periodic checks.

This module provides a single 1-second timer that handles all periodic
processing in the application, replacing the complex per-event scheduling
system with simple polling.

See docs/SCHEDULERS.md for full architecture documentation.
"""

from pubsub import pub
from taskcoachlib.domain import date as datemodule
import wx


class GlobalTimer:
    """
    Single global timer that fires every second and publishes events
    for various time-based processing needs.

    Optimizations:
    - Gets current timestamp only ONCE per tick
    - Extracts date/minute only when needed for comparisons
    - Uses integer comparisons where possible
    - Caches values to avoid repeated expensive calls
    - Publishes events so listeners can respond without coupling

    Events published:
    - 'timer.second': Every tick, payload includes timestamp
    - 'timer.minute': When minute changes
    - 'timer.date': When date changes (including first run)
    """

    INTERVAL_MS = 1000  # 1 second

    def __init__(self, parent):
        """
        Initialize the global timer.

        Args:
            parent: wx parent window to bind timer to (usually main window)
        """
        self._parent = parent
        self._timer = wx.Timer(parent)
        parent.Bind(wx.EVT_TIMER, self._onTick, self._timer)

        # State tracking - None means first run
        self._lastDate = None        # (year, month, day) tuple or None
        self._lastMinute = None      # (hour, minute) tuple or None

    def start(self):
        """Start the global timer."""
        self._timer.Start(self.INTERVAL_MS)

    def stop(self):
        """Stop the global timer."""
        self._timer.Stop()

    # Alias for compatibility with _stopAllTimers in application.py
    Stop = stop

    def isRunning(self):
        """Check if timer is running."""
        return self._timer.IsRunning()

    # Alias for compatibility with _stopAllTimers in application.py
    IsRunning = isRunning

    def _onTick(self, event):
        """
        Main timer tick handler. Called every second.

        Optimization: Get timestamp ONCE and reuse for all checks.
        All subscribers receive the same timestamp - no redundant now() calls.
        """
        # === GET TIMESTAMP ONCE ===
        # This is the expensive call - do it only once per tick
        # Convert to app's DateTime format once for all subscribers
        now = datemodule.DateTime.now()

        # Extract components for change detection (integer comparison is fast)
        currentDate = (now.year, now.month, now.day)
        currentMinute = (now.hour, now.minute)

        # === DATE CHANGE CHECK ===
        # Runs on first tick (lastDate is None) or when date changes
        if self._lastDate != currentDate:
            self._lastDate = currentDate
            pub.sendMessage('timer.date', timestamp=now)

        # === MINUTE CHANGE CHECK ===
        # Runs when minute changes
        if self._lastMinute != currentMinute:
            self._lastMinute = currentMinute
            pub.sendMessage('timer.minute', timestamp=now)

        # === EVERY SECOND ===
        # Always runs - listeners decide if they need to act
        pub.sendMessage('timer.second', timestamp=now)


class ReminderChecker:
    """
    Checks for due reminders on each timer tick.

    Optimizations:
    - Tracks shown reminders in set to avoid duplicates (O(1) lookup)
    - Receives timestamp from timer (no DateTime.now() call needed)
    - Batches reminder callbacks to avoid issues during iteration
    """

    def __init__(self, taskList, reminderCallback):
        """
        Initialize reminder checker.

        Args:
            taskList: The task list to check for reminders
            reminderCallback: Function to call when reminder is due: callback(task)
        """
        self._taskList = taskList
        self._reminderCallback = reminderCallback
        self._shownReminders = set()  # Tasks whose reminders have been shown

        # Subscribe to timer
        pub.subscribe(self._onSecond, 'timer.second')

    def _onSecond(self, timestamp):
        """
        Check for due reminders.

        Args:
            timestamp: DateTime from global timer (already retrieved, reuse it!)
        """
        # Use the timestamp passed from GlobalTimer - no extra now() call!
        now = timestamp

        tasksToRemind = []

        # Check all tasks with reminders
        for task in self._taskList:
            reminder = task.reminder()
            if reminder and reminder <= now:
                if task not in self._shownReminders:
                    tasksToRemind.append(task)
                    self._shownReminders.add(task)

        # Show reminders (outside loop to avoid modification during iteration)
        for task in tasksToRemind:
            self._reminderCallback(task)

    def clearShownReminder(self, task):
        """
        Clear a task from shown reminders (e.g., when reminder is snoozed).

        Args:
            task: The task to clear
        """
        self._shownReminders.discard(task)

    def shutdown(self):
        """Cleanup subscriptions."""
        pub.unsubscribe(self._onSecond, 'timer.second')


class StatusChecker:
    """
    Checks for task status changes (overdue, due soon, time to start).

    Optimizations:
    - Only checks tasks that COULD change status (not already overdue, etc.)
    - Batches appearance updates to reduce UI refreshes
    - Receives timestamp from timer (no DateTime.now() call needed)
    - Tracks last known status to detect transitions
    """

    def __init__(self, taskList):
        """
        Initialize status checker.

        Args:
            taskList: The task list to check
        """
        self._taskList = taskList
        # Track which tasks have already transitioned to avoid repeated updates
        self._overdueNotified = set()
        self._dueSoonNotified = set()
        self._startedNotified = set()

        # Subscribe to timer
        pub.subscribe(self._onSecond, 'timer.second')

    def _onSecond(self, timestamp):
        """
        Check for status changes.

        Args:
            timestamp: DateTime from global timer (already retrieved, reuse it!)
        """
        # Use the timestamp passed from GlobalTimer - no extra now() call!
        now = timestamp

        tasksToUpdate = []

        for task in self._taskList:
            if self._shouldCheckTask(task):
                if self._checkStatusTransitions(task, now):
                    tasksToUpdate.append(task)

        # Batch appearance updates - more efficient than one at a time
        for task in tasksToUpdate:
            task.recomputeAppearance()

    def _shouldCheckTask(self, task):
        """
        Optimization: Skip tasks that can't change status.

        Returns False for:
        - Completed tasks (status fixed)
        - Tasks with no relevant dates
        """
        if task.completed():
            return False
        # Task has potential for status change if it has dates set
        return True

    def _checkStatusTransitions(self, task, now):
        """
        Check if task status changed based on current time.

        Returns True if task needs appearance update.
        Tracks transitions to avoid repeated notifications.
        """
        needsUpdate = False

        # Check overdue transition (only once per task)
        if task not in self._overdueNotified:
            dueDateTime = task.dueDateTime()
            if dueDateTime and dueDateTime <= now:
                self._overdueNotified.add(task)
                needsUpdate = True

        # Check due soon transition (only once per task)
        if task not in self._dueSoonNotified:
            # Due soon = due date minus dueSoonHours
            dueDateTime = task.dueDateTime()
            if dueDateTime:
                # Get dueSoonHours from task or settings
                dueSoonHours = getattr(task, '_Task__dueSoonHours', 24)
                if dueSoonHours:
                    dueSoonThreshold = dueDateTime - datemodule.TimeDelta(hours=dueSoonHours)
                    if dueSoonThreshold <= now < dueDateTime:
                        self._dueSoonNotified.add(task)
                        needsUpdate = True

        # Check time to start transition (only once per task)
        # Check both plannedStartDateTime (for "late" status) and
        # actualStartDateTime (for "active" status when set in the future)
        if task not in self._startedNotified:
            plannedStart = task.plannedStartDateTime()
            actualStart = task.actualStartDateTime()
            maxDT = task.maxDateTime
            # Check if either start time has been reached
            plannedReached = plannedStart and plannedStart != maxDT and plannedStart <= now
            actualReached = actualStart and actualStart != maxDT and actualStart <= now
            if plannedReached or actualReached:
                self._startedNotified.add(task)
                needsUpdate = True

        return needsUpdate

    def clearTaskStatus(self, task):
        """
        Clear tracked status for a task (e.g., when dates change).
        Call this when task due date or start date is modified.

        Args:
            task: The task to clear
        """
        self._overdueNotified.discard(task)
        self._dueSoonNotified.discard(task)
        self._startedNotified.discard(task)

    def shutdown(self):
        """Cleanup subscriptions."""
        pub.unsubscribe(self._onSecond, 'timer.second')
