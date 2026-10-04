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

MasterScheduler - the master timer list and the passes.

The master timer list holds, sorted, each task's seconds at which time
alone changes it: its status rules and its reminder; a date not set
has none. A change the passes read marks the objects it concerns as
its event arrives. Each second, the due entries mark their tasks and
one pass processes the marked objects and what reads them, each once,
in a fixed order: categories, tasks, notes, attachments, parents
first. A change of what every object reads (a file read or merged, the
clock set back, the due soon hours, the status styles, the theme) runs
the full loop over every object instead. Each tick then sends the date
and minute events when they changed.

See docs/MASTER_SCHEDULER_REFACTOR.md (Incremental Pass, design and
rulings) and docs/SCHEDULERS.md.

Key Principle: ONLY MasterScheduler subscribes to timer.second for the
domain. All other modules get CALLED BY the scheduler - they do not
have their own timer subscriptions, except for local UI updates and
polls (effort tracking display, idle time, system theme, autosave
retry).
"""

import bisect
import collections
import heapq
import itertools
import os
import time


from taskcoachlib import patterns
from taskcoachlib.config import settings
from taskcoachlib.config.settings import Settings
from taskcoachlib.domain import attachment, base, category, effort, note
from taskcoachlib.domain import date as datemodule
from taskcoachlib.domain.base.appearance import computeStyles
from taskcoachlib.domain.task import Task
from taskcoachlib.meta.debug import log_step
import wx

# Set to run the full loop after every tick's pass and log each change
# it still makes: one the pass missed
# (docs/MASTER_SCHEDULER_REFACTOR.md)
_CHECK = os.environ.get("TASKCOACH_SCHEDULER_CHECK") == "1"

# The settings sections the styles read; the others (the window
# geometry, say) change often and the loop reads none of them
_APPEARANCE_SETTINGS = tuple(
    Settings.section_changed_event_type(section + theme)
    for section in ("fgcolor", "bgcolor", "font", "icon")
    for theme in ("", "_dark")
) + ("window.theme",)

# What every object reads: its change runs the full loop
_GLOBAL_EVENT_TYPES = _APPEARANCE_SETTINGS + ("system.theme_colour_changed",)

# The domain classes whose changes the passes read
_DOMAIN_CLASSES = (
    Task,
    category.Category,
    note.Note,
    effort.Effort,
    attachment.FileAttachment,
    attachment.URIAttachment,
    attachment.MailAttachment,
)

# What a pass processes, in this order: what an object reads comes
# before it
_KINDS = (category.Category, Task, note.Note, attachment.Attachment)

_EFFECTIVE = frozenset(
    getattr(base.Object, "effective%sChangedEventType" % field)()
    for field in ("FgColor", "BgColor", "Icon", "Font")
)

# The outputs of the passes, which the check mode compares
_OUTPUTS = ("derived.", "effective.")
_OUTPUT_TYPES = (
    Task.statusChangedEventType(),
    Task.reminderChangedEventType(),
)


def _data_event_types():
    """The change events the passes read: every domain modification
    except the fields no pass reads (typing in them must not run a pass
    every second), tracking, and the passes' own outputs, whose changes
    reach what reads them (docs/MASTER_SCHEDULER_REFACTOR.md). Other
    computed values (time spent, budget left, revenue, a subtree's
    priority) are not read."""
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
    return event_types


def _added_event_types(task_file):
    """The events whose values are objects added: each is computed with
    everything under it, which reads what is above it."""
    event_types = {
        collection.addItemEventType()
        for collection in (
            task_file.tasks(),
            task_file.categories(),
            task_file.notes(),
        )
    }
    for klass in (Task, category.Category, note.Note):
        event_types.add(klass.addChildEventType())
    for klass in _DOMAIN_CLASSES:
        for owned in ("notes", "attachments"):
            getter = getattr(klass, "%sChangedEventType" % owned, None)
            if getter:
                event_types.add(getter())
    return event_types


def _followers(item):
    """What reads the item's effective style or its name: its children
    and, for a category, its members (docs/MASTER_SCHEDULER_REFACTOR.md,
    Followers). Not what it owns: an owner's style reaches none of its
    notes or attachments."""
    followers = list(item.children()) if hasattr(item, "children") else []
    if isinstance(item, category.Category):
        followers.extend(item.members())
    return followers


def _owned(owner):
    """The notes and attachments the owner holds, at any depth."""
    notes = owner.notes(recursive=True) if hasattr(owner, "notes") else []
    attachments = owner.attachments() if hasattr(owner, "attachments") else []
    owned = []
    for each in list(notes) + list(attachments):
        owned.append(each)
        owned.extend(_owned(each))
    return owned


def _subtree(item):
    """The item with everything under it: its children and what they
    all own."""
    found = [item]
    if hasattr(item, "children"):
        found.extend(item.children(recursive=True))
    for each in list(found):
        found.extend(_owned(each))
    return found


def _order(item):
    """Categories, tasks, notes, attachments; parents first."""
    rank = next(
        index for index, kind in enumerate(_KINDS) if isinstance(item, kind)
    )
    depth = 0
    parent = item.parent() if hasattr(item, "parent") else None
    while parent is not None:
        depth += 1
        parent = parent.parent()
    return rank, depth


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
            parent: the window whose life the tick follows (the main
                window). The timer is its own, so no tick can reach the
                window once deleted; a tick after that is skipped
                (lazy teardown, docs/DEFERRED_CALLS.md).
        """
        self._parent = parent
        clock = self

        class Tick(wx.Timer):
            def Notify(self):  # wx override
                clock._on_tick()

        self._timer = Tick()

    def start(self):
        """Start the global timer."""
        self._timer.Start(self.INTERVAL_MS)

    def close(self):
        """Free the timer; the application's last step, once its event
        loop has ended."""
        self._timer.Stop()
        self._timer = None

    def _on_tick(self):
        if patterns.deferred.is_gone(self._parent):
            return
        now = datemodule.DateTime.now()
        patterns.Event("timer.second", self, now).send()


class MasterScheduler:
    """The master timer list and the passes
    (docs/MASTER_SCHEDULER_REFACTOR.md, Incremental Pass).

    Each tick: the due timer entries mark their tasks; one pass
    processes the marked objects and what reads them (a category's:
    its subcategories and members; a parent's: its children), each
    once, categories, tasks, notes and attachments, parents first:
    - Categories, notes, attachments: computeStyles
    - Tasks: status, reminder, styles
    The full loop, over every object, when what every object reads
    changed. Then the date and minute events, when they change.
    """

    def __init__(self, task_file):
        """Initialize MasterScheduler.

        Args:
            task_file: The task file to access categories, tasks, notes
        """
        self._task_file = task_file
        # (second, number, task, rule), sorted; the number orders the
        # entries of one second, so tasks are never compared
        self._timers = []
        self._timers_of = {}  # id(task): (task, its entries)
        self._numbers = itertools.count()
        self._marks = {}  # id(item): item, processed at the next tick
        self._full = True  # The full loop at the next tick
        self._running = None  # "full", "incremental" or "check"
        self._work = []  # The incremental pass's queue
        self._queued = set()
        self._added_types = set()
        self._last_tick = None
        self._last_date = None
        self._last_minute = None
        # The day the viewers show: the one they were drawn on
        now = datemodule.DateTime.now()
        self._shown_date = (now.year, now.month, now.day)
        self._failures = {}
        self._check_changes = collections.Counter()
        self._pass_costs = []  # (milliseconds, items), since the trace
        self._full_passes = 0  # Since the last trace line
        self._ticks = 0  # Since the last trace line
        if task_file:
            self._rebuild()
            self._start_observing()
        patterns.Publisher().registerObserver(
            self._on_second, eventType="timer.second"
        )

    # ═══════════════════════════════════════════════════════════════════
    # THE MASTER TIMER LIST AND THE MARKS
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
        self._added_types = _added_event_types(self._task_file)
        for collection in (
            tasks,
            self._task_file.categories(),
            self._task_file.notes(),
        ):
            for event_type in (
                collection.addItemEventType(),
                collection.removeItemEventType(),
            ):
                register(
                    self._on_change,
                    eventType=event_type,
                    eventSource=collection,
                )
        for event_type in _data_event_types():
            register(self._on_change, eventType=event_type)
        for klass in (Task, category.Category, note.Note):
            register(
                self._on_subject_changed,
                eventType=klass.subjectChangedEventType(),
            )
        for event_type in _GLOBAL_EVENT_TYPES:
            register(self._on_everything_changed, eventType=event_type)
        for event_type in ("taskfile.justRead", "taskfile.merged"):
            register(
                self._on_file_read,
                eventType=event_type,
                eventSource=self._task_file,
            )
        register(
            self._on_due_soon_hours_changed, eventType="behavior.duesoonhours"
        )

    @staticmethod
    def _due_soon_hours():
        return settings.behavior.duesoonhours

    def _rebuild(self):
        """Every task's timer entries, and the full loop at the next
        tick: what they give is not known yet."""
        self._timers = []
        self._timers_of = {}
        hours = self._due_soon_hours() if self._task_file.tasks() else 0
        for each in self._task_file.tasks():
            entries = self._entries(each, hours)
            if entries:
                self._timers_of[id(each)] = (each, entries)
                self._timers.extend(entries)
        self._timers.sort()
        self._full = True

    def _entries(self, task, hours):
        return [
            (second, next(self._numbers), task, rule)
            for rule, second in task.timer_seconds(hours).items()
        ]

    def _set_timers(self, task):
        """The task's entries: its seconds now, not the earlier."""
        self._drop_timers(task)
        entries = self._entries(task, self._due_soon_hours())
        for entry in entries:
            bisect.insort(self._timers, entry)
        if entries:
            self._timers_of[id(task)] = (task, entries)

    def _drop_timers(self, task):
        _task, entries = self._timers_of.pop(id(task), (None, ()))
        for entry in entries:
            del self._timers[bisect.bisect_left(self._timers, entry)]

    def _pop_due(self, timestamp):
        """Mark the tasks of every entry up to timestamp, past ones and
        this second's; the later ones stay. Return how many were due."""
        count = bisect.bisect_right(self._timers, (timestamp, float("inf")))
        due, self._timers[:count] = self._timers[:count], []
        for entry in due:
            task = entry[2]
            _task, entries = self._timers_of[id(task)]
            entries.remove(entry)
            if not entries:
                del self._timers_of[id(task)]
            self._mark(task)
        return count

    def _mark(self, item):
        if isinstance(item, _KINDS):
            self._marks[id(item)] = item

    def _on_task_times_changed(self, event):
        # Sources: the task and its ancestors, which is harmless. Also
        # during a pass: a reminder cleared there
        tasks = self._task_file.tasks()
        for source in event.sources():
            if isinstance(source, Task) and source in tasks:
                self._set_timers(source)

    def _on_tasks_added(self, event):
        # Created and loaded tasks send no date change: their entries
        # come from here (docs/MASTER_SCHEDULER_REFACTOR.md)
        for added in event.values():
            for each in [added] + list(added.children(recursive=True)):
                self._set_timers(each)

    def _on_tasks_removed(self, event):
        if not self._task_file.tasks():
            # Closed, or about to be filled by a file being opened
            self._timers = []
            self._timers_of = {}
            return
        for removed in event.values():
            for each in [removed] + list(removed.children(recursive=True)):
                self._drop_timers(each)

    def _on_change(self, event):
        """Outside a pass: mark what the change concerns for the next
        tick. In the incremental pass: queue what reads a style it
        changed. The full loop takes everything anyway."""
        if self._running == "full":
            return
        if self._running == "check":
            self._check_changes.update(
                event_type
                for event_type in event.types()
                if event_type.startswith(_OUTPUTS)
                or event_type in _OUTPUT_TYPES
            )
            return
        for event_type in event.types():
            sources = event.sources(event_type)
            if self._running == "incremental":
                if event_type in _EFFECTIVE:
                    for source in sources:
                        for each in _followers(source):
                            self._queue(each)
                continue
            if event_type in self._added_types:
                for source in sources:
                    for value in event.values(source, event_type):
                        if isinstance(value, _KINDS):
                            for each in _subtree(value):
                                self._mark(each)
            follow = (
                event_type in _EFFECTIVE
                or event_type
                == category.Category.stylePriorityChangedEventType()
            )
            for source in sources:
                self._mark(source)
                if follow:
                    for each in _followers(source):
                        self._mark(each)

    def _on_subject_changed(self, event):
        # A name is read only as the style source it gives other items
        # ("[Category] Work"): a category's, a parent's. A leaf's name
        # marks nothing, so typing one runs no pass
        for source in event.sources():
            for each in _followers(source):
                self._mark(each)

    def _on_everything_changed(self, event):  # pylint: disable=W0613
        self._full = True

    def _on_file_read(self, event):  # pylint: disable=W0613
        # Every object is new, or a merge replaced them by their copies
        self._rebuild()

    def _on_due_soon_hours_changed(self, event):  # pylint: disable=W0613
        # Every task's due soon second moves
        self._rebuild()

    # ═══════════════════════════════════════════════════════════════════
    # THE TICK AND THE PASSES
    # ═══════════════════════════════════════════════════════════════════

    def _on_second(self, event):
        """Called every second: runs a pass if an entry is due or an
        object marked, then sends the date and minute events.

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

        self._pop_due(timestamp)
        if self._full or self._marks or _CHECK:
            self._run_pass(timestamp)

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

    def _run_pass(self, timestamp):
        """The tick's pass: the full loop when due, else the marked
        objects and what reads them. Its cost includes its end event,
        after which the viewers refresh what it changed."""
        started = time.perf_counter()
        marked, self._marks = self._marks, {}
        # The viewers gather the pass's changes until its end
        self._run_isolated(
            "scheduler.aboutToPass",
            patterns.Event("scheduler.aboutToPass", self, timestamp).send,
        )
        try:
            if self._full:
                self._full = False
                self._full_passes += 1
                items = self._run_full(timestamp)
            else:
                items = self._run_incremental(timestamp, marked.values())
                if _CHECK:
                    self._check(timestamp)
        finally:
            # Once per pass, e.g. to re-sort by the new statuses
            self._run_isolated(
                "scheduler.pass",
                patterns.Event("scheduler.pass", self, timestamp).send,
            )
        self._pass_costs.append(
            ((time.perf_counter() - started) * 1000, items)
        )

    def _run_full(self, timestamp):
        """The full loop, once over every object; return how many."""
        self._running = "full"
        try:
            return self._full_loop(timestamp)
        finally:
            self._running = None

    def _full_loop(self, timestamp):
        """Every object once, in the fixed order: what an object reads
        is processed before it (every category before an item in it,
        wherever that item is owned), so one loop settles. Return how
        many."""
        everything = []
        for collection in (
            self._task_file.categories(),
            self._task_file.tasks(),
            self._task_file.notes(),
        ):
            for each in collection:
                everything.append(each)
                everything.extend(_owned(each))
        everything.sort(key=_order)
        for each in everything:
            self._process(each, timestamp)
        return len(everything)

    def _run_incremental(self, timestamp, marked):
        """The marked objects and what reads a style they change, each
        once, in the fixed order: what an object reads is processed
        before it, so nothing is processed twice or loops. A task not in
        the file (deleted, kept for undo) is not processed: its reminder
        must not fire. Return how many were processed."""
        self._running = "incremental"
        self._work = []
        self._queued = set()
        tasks = self._task_file.tasks()
        count = 0
        try:
            for each in marked:
                self._queue(each)
            while self._work:
                _order_key, _number, item = heapq.heappop(self._work)
                if not isinstance(item, Task) or item in tasks:
                    self._process(item, timestamp)
                    count += 1
        finally:
            self._running = None
            self._work = []
            self._queued = set()
        return count

    def _process(self, item, timestamp):
        """One object. Each runs isolated: it notifies listeners
        (viewers, dialogs), and one failing listener must not skip the
        rest."""
        if isinstance(item, Task):
            self._run_isolated("task", self._compute_task, item, timestamp)
        else:
            self._run_isolated("style", computeStyles, item)

    def _queue(self, item):
        if isinstance(item, _KINDS) and id(item) not in self._queued:
            self._queued.add(id(item))
            heapq.heappush(
                self._work, (_order(item), next(self._numbers), item)
            )

    def _check(self, timestamp):
        """The full loop after the pass: a change it still makes is one
        the pass missed (TASKCOACH_SCHEDULER_CHECK=1). It fires due
        reminders again, which the reminder controller drops."""
        self._check_changes.clear()
        self._running = "check"
        try:
            self._full_loop(timestamp)
        finally:
            self._running = None
        if self._check_changes:
            log_step(
                "missed at %s: %s" % (timestamp, dict(self._check_changes)),
                prefix="SCHEDULER",
            )

    def _trace_passes(self):
        """Log the passes of the last minute, if any ran, and the ticks:
        fewer than 60 means the UI thread was held."""
        ticks, self._ticks = self._ticks, 0
        full, self._full_passes = self._full_passes, 0
        if not self._pass_costs:
            return
        costs = sorted(cost for cost, _items in self._pass_costs)
        items = sum(each for _cost, each in self._pass_costs)
        passes = len(self._pass_costs)
        self._pass_costs = []
        log_step(
            "last minute: %d ticks, %d passes (%d full), median %.0f ms,"
            " max %.0f ms, %d objects; %d tasks, %d timer entries"
            % (
                ticks,
                passes,
                full,
                costs[len(costs) // 2],
                costs[-1],
                items,
                len(self._task_file.tasks()),
                len(self._timers),
            ),
            prefix="SCHEDULER",
        )

    @staticmethod
    def _compute_task(task, timestamp):
        # The status at the tick's second, as the timer seconds assume
        task.compute_stored_status(timestamp)
        task.processReminder(timestamp)
        computeStyles(task)

    @classmethod
    def _process_task(cls, task, timestamp):
        """A task and what it owns, as the loop would: for tests that
        compute one task's statuses and styles."""
        cls._compute_task(task, timestamp)
        for each in _owned(task):
            computeStyles(each)

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
        """Stop following events: for tests, whose schedulers outlive
        them. The app's ends with the process (lazy teardown)."""
        publisher = patterns.Publisher()
        for handler in (
            self._on_second,
            self._on_task_times_changed,
            self._on_tasks_added,
            self._on_tasks_removed,
            self._on_change,
            self._on_subject_changed,
            self._on_everything_changed,
            self._on_file_read,
            self._on_due_soon_hours_changed,
        ):
            publisher.removeObserver(handler)
