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

MasterScheduler - Consolidated timer and per-second processing.

All periodic processing in one place:
- Categories: style computation
- Tasks: status updates (legacy + modern), auto-completion, reminders, styles
- Notes: style computation
- Date/minute change detection and UI refresh events

See docs/SCHEDULERS.md for full architecture documentation.

Key Principle: ONLY MasterScheduler subscribes to timer.second. All other
modules get CALLED BY the scheduler - they do not have their own timer
subscriptions, except for local UI updates and polls (effort tracking
display, idle time, system theme, autosave retry).

Performance Note:
If _on_second() ever freezes the UI with very large task files,
consider:
1. First, profile to identify bottlenecks (don't optimize blindly)
2. If loop iteration is the issue, yield to wx event loop every 100-200ms
   using wx.SafeYield() or wx.GetApp().Yield()
3. Only add yielding if there are actual cases where processing > 100-200ms
"""

from taskcoachlib import patterns
from taskcoachlib.domain import date as datemodule
from taskcoachlib.domain.base.appearance import computeStyles
from taskcoachlib.meta.debug import log_step
import wx


class GlobalTimer:
    """
    Single global timer that sends the Publisher event 'timer.second'
    every second. Its source is the GlobalTimer and its value the tick
    timestamp, read once for all subscribers.

    Subscribe with registerObserver(handler, eventType='timer.second');
    the handler reads the timestamp with event.value(). Date and
    minute changes come from MasterScheduler, after the tick's
    processing ('scheduler.date', 'scheduler.minute').
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
        parent.Bind(wx.EVT_TIMER, self._on_tick, self._timer)

    def start(self):
        """Start the global timer."""
        self._timer.Start(self.INTERVAL_MS)

    def stop(self):
        """Stop the global timer."""
        self._timer.Stop()

    # Alias for compatibility with _stop_all_timers in application.py
    Stop = stop

    def is_running(self):
        """Check if timer is running."""
        return self._timer.IsRunning()

    # Alias for compatibility with _stop_all_timers in application.py
    IsRunning = is_running

    def _on_tick(self, event):
        now = datemodule.DateTime.now()
        patterns.Event("timer.second", self, now).send()


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

    def __init__(self, task_file):
        """Initialize MasterScheduler.

        Args:
            task_file: The task file to access categories, tasks, notes
        """
        self._task_file = task_file
        self._last_date = None
        self._last_minute = None
        # The day the viewers show: the one they were drawn on
        now = datemodule.DateTime.now()
        self._shown_date = (now.year, now.month, now.day)
        self._failures = {}
        patterns.Publisher().registerObserver(
            self._on_second, eventType="timer.second"
        )

    def _on_second(self, event):
        """Master function called every second.

        See docs/SCHEDULERS.md for full architecture documentation.
        """
        if not self._task_file:
            return
        timestamp = event.value()

        # ═══════════════════════════════════════════════════════════════
        # TIME CHANGE DETECTION
        # ═══════════════════════════════════════════════════════════════

        date_changed = self._check_date_changed(timestamp)
        minute_changed = self._check_minute_changed(timestamp)

        # Each item and each UI refresh runs isolated: they notify
        # listeners (viewers, dialogs), and one failing listener must
        # not skip the rest of the tick. (A pypubsub message sent during
        # the processing still stops at its first failing listener.)

        # ═══════════════════════════════════════════════════════════════
        # CATEGORIES
        # ═══════════════════════════════════════════════════════════════

        for category in self._task_file.categories():
            self._run_isolated("category", computeStyles, category)

        # ═══════════════════════════════════════════════════════════════
        # TASKS
        # ═══════════════════════════════════════════════════════════════

        for task in self._task_file.tasks():
            self._run_isolated(
                "task", self._process_task, task, timestamp, date_changed
            )

        # ═══════════════════════════════════════════════════════════════
        # NOTES (global, not task-owned)
        # ═══════════════════════════════════════════════════════════════

        for note in self._task_file.notes():
            self._run_isolated("note", self._process_note, note)

        # ═══════════════════════════════════════════════════════════════
        # DATE/MINUTE CHANGE PROCESSING (after all data changes)
        # ═══════════════════════════════════════════════════════════════

        # Publisher events, so each subscriber (viewers, filters) runs
        # isolated from the others' failures. The date event is for a
        # day the viewers do not show yet.
        if self._last_date != self._shown_date:
            self._shown_date = self._last_date
            self._run_isolated(
                "scheduler.date",
                patterns.Event("scheduler.date", self, timestamp).send,
            )
        if minute_changed:
            self._run_isolated(
                "scheduler.minute",
                patterns.Event("scheduler.minute", self, timestamp).send,
            )

    @staticmethod
    def _process_task(task, timestamp, date_changed):
        # --- Daily processing (midnight) ---
        if date_changed:
            task.onDailyChange()

        # --- Every-second processing ---

        # Status updates (separate methods for legacy/modern)
        task.recomputeLegacyStatus(timestamp)  # Legacy: __status
        task.computeStoredStatus()  # Modern: __computed_status

        # Reminders
        task.processReminder(timestamp)

        # Styles
        computeStyles(task)

        # Owned notes/attachments
        for note in task.notes(recursive=True):
            computeStyles(note)
        for attachment in task.attachments():
            computeStyles(attachment)

    @staticmethod
    def _process_note(note):
        computeStyles(note)
        for attachment in note.attachments():
            computeStyles(attachment)

    def _run_isolated(self, step, func, *args):
        """Run one step of the tick, logging a failure instead of
        raising. A failure that repeats every tick logs its traceback
        once, then a count every 100 repeats."""
        try:
            func(*args)
        except Exception as exc:
            key = (step, patterns.failure_site(exc))
            count = self._failures.get(key, 0) + 1
            self._failures[key] = count
            if count == 1 or count % 100 == 0:
                item = " for %s" % args[0].id() if args else ""
                log_step(
                    "%s failed%s, %d so far: %r" % (step, item, count, exc),
                    prefix="SCHEDULER",
                    exc=count == 1,
                )

    # ═══════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════

    def _check_date_changed(self, timestamp):
        """Check if date changed since last tick."""
        current_date = (timestamp.year, timestamp.month, timestamp.day)
        if self._last_date != current_date:
            self._last_date = current_date
            return True
        return False

    def _check_minute_changed(self, timestamp):
        """Check if minute changed since last tick."""
        current_minute = (timestamp.hour, timestamp.minute)
        if self._last_minute != current_minute:
            self._last_minute = current_minute
            return True
        return False

    def shutdown(self):
        """Cleanup on application close."""
        patterns.Publisher().removeObserver(
            self._on_second, eventType="timer.second"
        )
