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
MasterScheduler - Consolidated timer and per-second processing.

All periodic processing in one place:
- Categories: style computation
- Tasks: status updates (legacy + modern), auto-completion, reminders, styles
- Notes: style computation
- Date/minute change detection and UI refresh events

See docs/SCHEDULERS.md for full architecture documentation.

Key Principle: ONLY MasterScheduler subscribes to timer.second. All other
modules get CALLED BY the scheduler - they do not have their own timer
subscriptions (except local UI updates like effort tracking display).

Performance Note:
If _onSecond() ever freezes the UI with very large task files, consider:
1. First, profile to identify bottlenecks (don't optimize blindly)
2. If loop iteration is the issue, yield to wx event loop every 100-200ms
   using wx.SafeYield() or wx.GetApp().Yield()
3. Only add yielding if there are actual cases where processing > 100-200ms
"""

from pubsub import pub
from taskcoachlib.domain import date as datemodule
from taskcoachlib.domain.base.appearance import computeStyles
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


class MasterScheduler:
    """Master scheduler for all periodic processing.

    Single source of truth for cross-task logic (parent auto-completion).
    Handles time-based status updates, reminders, and style computation.

    Processing order each second:
    1. Categories: computeStyles
    2. Tasks: status (legacy + modern), auto-complete, reminders, styles
    3. Notes (global): computeStyles
    4. UI refresh events (date/minute change)
    """

    def __init__(self, taskFile):
        """Initialize MasterScheduler.

        Args:
            taskFile: The task file to access categories, tasks, notes
        """
        self._taskFile = taskFile
        self._lastDate = None
        self._lastMinute = None
        pub.subscribe(self._onSecond, 'timer.second')

    def _onSecond(self, timestamp):
        """Master function called every second.

        See docs/SCHEDULERS.md for full architecture documentation.
        """
        if not self._taskFile:
            return

        # ═══════════════════════════════════════════════════════════════
        # TIME CHANGE DETECTION
        # ═══════════════════════════════════════════════════════════════

        dateChanged = self._checkDateChanged(timestamp)
        minuteChanged = self._checkMinuteChanged(timestamp)

        # ═══════════════════════════════════════════════════════════════
        # CATEGORIES
        # ═══════════════════════════════════════════════════════════════

        for category in self._taskFile.categories():
            computeStyles(category)

        # ═══════════════════════════════════════════════════════════════
        # TASKS
        # ═══════════════════════════════════════════════════════════════

        for task in self._taskFile.tasks():

            # --- Daily processing (midnight) ---
            if dateChanged:
                task.onDailyChange()

            # --- Every-second processing ---

            # Status updates (separate methods for legacy/modern)
            task.recomputeLegacyStatus(timestamp)  # Legacy: __status
            task.computeStoredStatus()              # Modern: __computed_status

            # Reminders
            task.processReminder(timestamp)

            # Styles
            computeStyles(task)

            # Owned notes/attachments
            for note in task.notes(recursive=True):
                computeStyles(note)
            for attachment in task.attachments():
                computeStyles(attachment)

        # ═══════════════════════════════════════════════════════════════
        # NOTES (global, not task-owned)
        # ═══════════════════════════════════════════════════════════════

        for note in self._taskFile.notes():
            computeStyles(note)
            for attachment in note.attachments():
                computeStyles(attachment)

        # ═══════════════════════════════════════════════════════════════
        # DATE/MINUTE CHANGE PROCESSING (after all data changes)
        # ═══════════════════════════════════════════════════════════════

        if dateChanged:
            pub.sendMessage('scheduler.dateChange.uiRefresh', timestamp=timestamp)
        if minuteChanged:
            pub.sendMessage('scheduler.minuteChange.uiRefresh', timestamp=timestamp)

    # ═══════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════

    def _checkDateChanged(self, timestamp):
        """Check if date changed since last tick."""
        currentDate = (timestamp.year, timestamp.month, timestamp.day)
        if self._lastDate != currentDate:
            self._lastDate = currentDate
            return True
        return False

    def _checkMinuteChanged(self, timestamp):
        """Check if minute changed since last tick."""
        currentMinute = (timestamp.hour, timestamp.minute)
        if self._lastMinute != currentMinute:
            self._lastMinute = currentMinute
            return True
        return False

    def shutdown(self):
        """Cleanup on application close."""
        pub.unsubscribe(self._onSecond, 'timer.second')
