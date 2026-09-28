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

MasterScheduler - the master timer list and the full loop.

The master timer list is a binary heap of the seconds not processed yet
at which something changes: each task's time rules (late, active, due
soon, overdue, reminder) and the second of each data change. Each
second, if its smallest entry is due, the due entries are popped and
the full loop runs once over all categories, tasks and notes, parents
first: statuses, reminders, styles. The loop's own changes push the
current second, so a cascade settles one pass per second. The date and
minute events are sent every second.

See docs/MASTER_SCHEDULER_REFACTOR.md (design and rulings) and
docs/SCHEDULERS.md.

Key Principle: ONLY MasterScheduler subscribes to timer.second for the
domain. All other modules get CALLED BY the scheduler - they do not
have their own timer subscriptions, except for local UI updates and
polls (effort tracking display, idle time, system theme, autosave
retry).
"""

import collections
import heapq
import os
import time


from taskcoachlib import patterns
from taskcoachlib.config.settings import Settings
from taskcoachlib.domain import attachment, base, category, effort, note
from taskcoachlib.domain import date as datemodule
from taskcoachlib.domain.base.appearance import computeStyles
from taskcoachlib.domain.task import Task
from taskcoachlib.meta.debug import log_step
import wx

# Set to run the full loop every second as well and log each change it
# makes at a second the heap did not call for: a missed signal
# (docs/MASTER_SCHEDULER_REFACTOR.md)
_CHECK = os.environ.get("TASKCOACH_SCHEDULER_CHECK") == "1"

# The settings sections the styles read; the others (the window
# geometry, say) change often and the loop reads none of them
_APPEARANCE_SETTINGS = tuple(
    Settings.section_changed_event_type(section + theme)
    for section in ("fgcolor", "bgcolor", "font", "icon")
    for theme in ("", "_dark")
) + ("window.theme",)

# The domain classes whose changes the full loop reads
_DOMAIN_CLASSES = (
    Task,
    category.Category,
    note.Note,
    effort.Effort,
    attachment.FileAttachment,
    attachment.URIAttachment,
    attachment.MailAttachment,
)


def _data_event_types():
    """The change events the full loop reads: every domain
    modification except the fields no loop step reads (typing in them
    must not run the loop every second), tracking, and the loop's own
    outputs, whose changes cascade (docs/MASTER_SCHEDULER_REFACTOR.md).
    Other computed values (time spent, budget left, revenue, the
    effective priority) are not read."""
    event_types = set()
    for klass in _DOMAIN_CLASSES:
        unread = set()
        for field in (
            "subject",
            "description",
            "expansion",
            "hourlyFee",
            "fixedFee",
            "priority",
        ):
            getter = getattr(klass, "%sChangedEventType" % field, None)
            if getter:
                unread.add(getter())
        event_types.update(
            event_type
            for event_type in klass.modificationEventTypes()
            if event_type not in unread
        )
    event_types.add(Task.trackingChangedEventType())
    event_types.add(Task.statusChangedEventType())
    for kind in ("derived", "effective"):
        for field in ("FgColor", "BgColor", "Icon", "Font"):
            name = "%s%sChangedEventType" % (kind, field)
            event_types.add(getattr(base.Object, name)())
    event_types.add("system.theme_colour_changed")
    return event_types


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
    """The master timer list and the full loop
    (docs/MASTER_SCHEDULER_REFACTOR.md).

    When the heap holds a due second, the full loop runs once, parents
    before children:
    1. Categories: computeStyles
    2. Tasks: status (legacy + modern), reminders, styles
    3. Notes (global): computeStyles
    Every second, after it: the UI refresh events (date/minute change).
    """

    def __init__(self, task_file):
        """Initialize MasterScheduler.

        Args:
            task_file: The task file to access categories, tasks, notes
        """
        self._task_file = task_file
        self._heap = []
        # The last tick's second, once pushed for a change since
        self._pushed = None
        self._last_tick = None
        self._last_date = None
        self._last_minute = None
        # The day the viewers show: the one they were drawn on
        now = datemodule.DateTime.now()
        self._shown_date = (now.year, now.month, now.day)
        self._failures = {}
        self._in_pass = False
        self._pass_changes = collections.Counter()
        self._pass_costs = []  # Milliseconds, since the last trace line
        self._ticks = 0  # Since the last trace line
        self._observing = bool(task_file)
        if self._observing:
            self._rebuild()
            self._start_observing()
        patterns.Publisher().registerObserver(
            self._on_second, eventType="timer.second"
        )

    # ═══════════════════════════════════════════════════════════════════
    # THE MASTER TIMER LIST
    # ═══════════════════════════════════════════════════════════════════

    def _start_observing(self):
        register = patterns.Publisher().registerObserver
        for event_type in (
            Task.plannedStartDateTimeChangedEventType(),
            Task.actualStartDateTimeChangedEventType(),
            Task.dueDateTimeChangedEventType(),
            Task.reminderChangedEventType(),
        ):
            register(self._on_task_times_changed, eventType=event_type)
        tasks = self._task_file.tasks()
        register(
            self._on_tasks_added,
            eventType=tasks.addItemEventType(),
            eventSource=tasks,
        )
        register(
            self._on_tasks_removed,
            eventType=tasks.removeItemEventType(),
            eventSource=tasks,
        )
        for collection in (
            self._task_file.categories(),
            self._task_file.notes(),
        ):
            for event_type in (
                collection.addItemEventType(),
                collection.removeItemEventType(),
            ):
                register(
                    self._on_data_changed,
                    eventType=event_type,
                    eventSource=collection,
                )
        for event_type in _data_event_types() | set(_APPEARANCE_SETTINGS):
            register(self._on_data_changed, eventType=event_type)
        register(
            self._on_due_soon_hours_changed, eventType="behavior.duesoonhours"
        )

    @staticmethod
    def _due_soon_hours():
        return Task.settings.getint("behavior", "duesoonhours")

    def _rebuild(self):
        """Every task's timer seconds, plus one due at once."""
        heap = [datemodule.DateTime.min]
        tasks = self._task_file.tasks()
        if tasks:
            hours = self._due_soon_hours()
            for each in tasks:
                heap.extend(each.timer_seconds(hours))
        heapq.heapify(heap)
        self._heap = heap
        self._pushed = None

    def _push_seconds(self, seconds):
        for second in seconds:
            heapq.heappush(self._heap, second)

    def _push_changed(self, event_types):
        """A change the full loop reads: its second is due at the next
        tick. The loop's own changes too: a cascade settles one pass per
        second."""
        if self._in_pass:
            self._pass_changes.update(event_types)
        # The current tick's second: already passed, so the next tick
        # takes it with every other due entry; before the first tick,
        # the earliest second, due at once
        second = self._last_tick or datemodule.DateTime.min
        if second != self._pushed:
            heapq.heappush(self._heap, second)
            self._pushed = second

    def _pop_due(self, timestamp):
        """Pop every entry up to timestamp, past ones and this second's,
        and stop at the first later one, which stays; return how many
        were popped. Popped before the loop runs: what the pass pushes
        stays for the next tick."""
        heap = self._heap
        count = 0
        while heap and heap[0] <= timestamp:
            heapq.heappop(heap)
            count += 1
        if count:
            self._pushed = None
        return count

    def _on_task_times_changed(self, event):
        # Sources: the task and its ancestors, whose seconds are already
        # there, pushed again harmlessly
        hours = self._due_soon_hours()
        for source in event.sources():
            self._push_seconds(source.timer_seconds(hours))

    def _on_tasks_added(self, event):
        # Created and loaded tasks send no date change: their seconds
        # come from here (docs/MASTER_SCHEDULER_REFACTOR.md)
        hours = self._due_soon_hours()
        for added in event.values():
            self._push_seconds(added.timer_seconds(hours))
        self._push_changed(event.types())

    def _on_tasks_removed(self, event):
        if not self._task_file.tasks():
            # Closed, or about to be filled by a file being opened
            self._heap = []
            self._pushed = None
        self._push_changed(event.types())

    def _on_data_changed(self, event):
        self._push_changed(event.types())

    def _on_due_soon_hours_changed(self, event):  # pylint: disable=W0613
        # Every task's due soon second moves
        self._rebuild()

    # ═══════════════════════════════════════════════════════════════════
    # THE TICK AND THE FULL LOOP
    # ═══════════════════════════════════════════════════════════════════

    def _on_second(self, event):
        """Called every second: runs the full loop if the heap holds a
        due second, then sends the date and minute events.

        See docs/MASTER_SCHEDULER_REFACTOR.md.
        """
        if not self._task_file:
            return
        timestamp = event.value()
        if self._last_tick is not None and timestamp < self._last_tick:
            log_step(
                "clock set back from %s to %s: timer list rebuilt"
                % (self._last_tick, timestamp),
                prefix="SCHEDULER",
            )
            self._rebuild()
        self._last_tick = timestamp
        self._ticks += 1
        self._last_date = (timestamp.year, timestamp.month, timestamp.day)
        minute_changed = self._check_minute_changed(timestamp)
        if minute_changed:
            self._trace_passes()

        due = self._pop_due(timestamp)
        if due or _CHECK:
            self._run_pass(timestamp, due)

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

    def _run_pass(self, timestamp, due):
        """The full loop, once over every object, parents first: a child
        reads its parent's style. Each item runs isolated: it notifies
        listeners (viewers, dialogs), and one failing listener must not
        skip the rest of the pass."""
        started = time.perf_counter()
        self._in_pass = True
        self._pass_changes.clear()
        try:
            for each in self._task_file.categories().allItemsSorted():
                self._run_isolated("category", computeStyles, each)
            for each in self._task_file.tasks().allItemsSorted():
                self._run_isolated("task", self._process_task, each, timestamp)
            for each in self._task_file.notes().allItemsSorted():
                self._run_isolated("note", self._process_note, each)
        finally:
            self._in_pass = False
        if _CHECK and not due and self._pass_changes:
            log_step(
                "missed at %s: %s" % (timestamp, dict(self._pass_changes)),
                prefix="SCHEDULER",
            )
        self._pass_costs.append((time.perf_counter() - started) * 1000)

    def _trace_passes(self):
        """Log the passes of the last minute, if any ran, and the ticks:
        fewer than 60 means the UI thread was held."""
        ticks, self._ticks = self._ticks, 0
        if not self._pass_costs:
            return
        costs = sorted(self._pass_costs)
        self._pass_costs = []
        log_step(
            "last minute: %d ticks, %d passes, median %.0f ms, max %.0f ms;"
            " %d tasks, %d entries waiting"
            % (
                ticks,
                len(costs),
                costs[len(costs) // 2],
                costs[-1],
                len(self._task_file.tasks()),
                len(self._heap),
            ),
            prefix="SCHEDULER",
        )

    @staticmethod
    def _process_task(task, timestamp):
        # The status at the tick's second, as the timer seconds assume
        task.compute_stored_status(timestamp)
        task.processReminder(timestamp)
        computeStyles(task)
        # Owned notes and attachments, parents first
        for owned_note in task.notes(recursive=True):
            computeStyles(owned_note)
        for owned_attachment in task.attachments():
            computeStyles(owned_attachment)

    @staticmethod
    def _process_note(note_):
        computeStyles(note_)
        for owned_attachment in note_.attachments():
            computeStyles(owned_attachment)

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

    def _check_minute_changed(self, timestamp):
        """Check if minute changed since last tick."""
        current_minute = (timestamp.hour, timestamp.minute)
        if self._last_minute != current_minute:
            self._last_minute = current_minute
            return True
        return False

    def shutdown(self):
        """Cleanup on application close."""
        publisher = patterns.Publisher()
        for handler in (
            self._on_second,
            self._on_task_times_changed,
            self._on_tasks_added,
            self._on_tasks_removed,
            self._on_data_changed,
            self._on_due_soon_hours_changed,
        ):
            publisher.removeObserver(handler)
