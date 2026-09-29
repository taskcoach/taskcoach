# Master Scheduler Refactor

Plan to replace the full scan `MasterScheduler` runs every second.
[SCHEDULERS.md](SCHEDULERS.md) describes the scheduler as it is.

**Status:** items 1 to 33 done or decided, 2026-09-28
([Cost After](#cost-after)); what is left: [To Do](#to-do).

## To Do

The one list for this refactor, numbered in the order found; an item
is crossed out and cut to a stub when done or decided, and new items
go at the end. Details live in the sections and documents linked.

1. ~~Whole seconds everywhere: done, only logs keep fractions.~~
   [Time Resolution](#time-resolution)
2. ~~One "not set" for every task date: done, the latest date; a
   running effort's missing stop stays `None`, outside the list.~~
   [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#dates-not-set-is-the-latest-date)
3. ~~No event for an unchanged value: done (`Attribute.set()`), a
   quarter of the tick.~~ [Cost Before](#cost-before)
4. ~~Task dates and reminder on the Publisher, the reminder an
   `Attribute`: done.~~ [Why Nothing Is Missed](#why-nothing-is-missed)
5. ~~The master timer list: done, a heap, the check each second, the
   full loop at its entries, the check mode
   (`TASKCOACH_SCHEDULER_CHECK=1`).~~ [Cost After](#cost-after)
6. ~~Changes the loop reads push the current second, parents first:
   done.~~ [Data Changes](#data-changes)
7. ~~One status: done, styles and status bar counts read
   `computedStatus()`.~~ [TASK_STATUS.md](TASK_STATUS.md#migration-path)
8. ~~SyncML leftovers (sync status flags): removed.~~
   [PYTHON3_MIGRATION_4.md](PYTHON3_MIGRATION_4.md#backwards-compatibility)
9. ~~Merging ignored the actual start: done, then moot (item 13).~~
10. ~~Reminder windows when a file opens: decided, no change.~~
    [REMINDERS.md](REMINDERS.md#overview)
11. ~~UI thread busy while statuses change: done, computed values mark
    nothing unsaved and a save no longer reads the file (98% to
    11%).~~ [Cost After](#cost-after)
12. ~~Modification date on every stored change: done.~~
    [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)
13. ~~Merging: done, no automatic merge; File > Merge a union by newest
    copy.~~ [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)
14. ~~Unsaved mark from saved data only: done.~~
15. ~~A file changed on disk: done, never replaced unasked.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#saving)
16. ~~Undo back to the saved state clears the unsaved mark: done.~~
    [UNDO_REDO.md](UNDO_REDO.md#persistence)
17. ~~View state and category ownership: decided, filter and expanded
    state set no date, the task owns its categories.~~
    [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)
18. ~~Every signal on the Publisher: done, pypubsub removed.~~
    [PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#migration-log)
19. ~~The loop's hook lists what the loop reads: done.~~
    [Data Changes](#data-changes)
20. ~~Attachments re-sorted: done.~~
21. ~~A timing-dependent `EffortViewerTest` case: done.~~
22. ~~Merge ran the parent rules: done.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)
23. ~~`.delta` files: decided, ignored.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)
24. ~~The effort list took a merged file's efforts: done, it compares
    identity.~~
25. ~~Status bar counts ignored the clock: done.~~
26. ~~Object identity: decided, one object per ID within a file, the
    file to merge held apart.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)
27. ~~Recursive priority in the loop: decided, no; the effective
    priority, by events.~~
    [TASK_FIELDS.md](TASK_FIELDS.md#effective-priority)
28. ~~Recurrence changes reached only the subtask: done.~~
    [TASK_FIELDS.md](TASK_FIELDS.md#subtree-values-in-other-columns)
29. ~~Duplicate IDs in a file: done, corrected when read, with a
    message.~~ [PERSISTENCE_XML.md](PERSISTENCE_XML.md#duplicate-ids)
30. ~~Cut and paste changed identity: done, the first paste after a cut
    is a move.~~ [PERSISTENCE_XML.md](PERSISTENCE_XML.md#ids)
31. ~~IDs carried the network (MAC) address: done, random UUIDs.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#ids)
32. ~~The unused file GUID: removed.~~
33. ~~Version: 2.0.3.0.~~
34. The undo log as object versions keyed by the modification date:
    step 1 done, steps 2 to 5 open
    ([UNDO_REDO.md](UNDO_REDO.md#todo-one-undo-log), option C).
35. The views on the effective styles, the legacy styles removed
    (why, the scan and what was found:
    [Views on the Effective Styles](#views-on-the-effective-styles)):
    1. ~~Views read the effective styles~~: `shown_*()`.
    2. ~~Listeners on the effective-style events~~.
    3. ~~`recomputeAppearance()` callers keep only the immediate
       status~~: `_update_status()`.
    4. ~~The selected (open folder) icon removed~~.
    5. ~~Legacy style code removed~~.
    6. ~~Tests on the effective styles~~: `test.styled()` runs the
       loop's pass.
    7. ~~Docs~~.
    8. ~~Checked in the app, every view; the full suite~~ (the task
       dependency graph not opened: igraph not installed here).
    9. ~~A subtask does not take its parent's status or tracking
       style~~: no ruling needed, it keeps what the views always showed
       (each task its own status).
36. The task editor's Progress tab: a second percentage control and
    slider drawn over the tab labels, seen only under Xvfb; to check on
    a real display.
37. Effective fields for the 13 other subtree values, one at a time;
    none is read by the loop (what each is:
    [TASK_FIELDS.md](TASK_FIELDS.md#subtree-values-in-other-columns)):
    1. Planned start date.
    2. Due date.
    3. Actual start date.
    4. Completion date.
    5. Reminder.
    6. Time left.
    7. Recurrence.
    8. % complete.
    9. Time spent.
    10. Budget.
    11. Budget left.
    12. Fixed fee.
    13. Revenue.
38. ~~`Timestamp.now()` always later than the one before~~: removed,
    it returned made-up times; the dates are the clock's
    ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#ids)).
39. Renames deferred as too wide, each its own change: the task date
    setters (`setReminder()`, `setDueDateTime()`,
    `setPlannedStartDateTime()`, `setActualStartDateTime()`,
    `setCompletionDateTime()`, about 465 calls), `setParent()` (65) and
    `setTask()` (25), with name-coupled callers such as `merge.py`
    (`"set" + kind`) in lockstep ([PEP8_MIGRATION.md](PEP8_MIGRATION.md)).
40. Signal cleanup: views, toolbars, menus and dialogs drop their
    subscriptions when destroyed, then the dead-window guards go
    ([PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#todo)).
41. Editor text fields (subject, description, attachment location)
    commit only on focus loss
    ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#todo)).
42. The designer's desktop test of the branch, from one consolidated
    test list.
43. Squash to one commit before pushing, version 2.0.3.0 in the body;
    the release date (2026-09-28) may move.
44. One app run on 2026-09-28 logged a traceback (log lost, not
    reproduced in four runs of the same steps): watch for it.
45. Not planned: the reason for each entry
    ([Later](#later-the-reason-for-each-entry)).

## Views on the Effective Styles

To do 35. **Decided before this refactor**
([TASK_STATUS.md](TASK_STATUS.md#legacy-code-compatibility-resolved)):
new code reads `effectiveXxx()`, and the legacy `recursive=True` style
accessors stay only until their consumers move; the migration waited
for the effective styles to prove stable. Only the editor had moved;
every view drew from the legacy accessors, cached by
`Task.recomputeAppearance()` outside the loop, while the loop computed
the effective styles every pass for nothing but the editor.

Done 2026-09-28: every view draws `shown_fg_color()`,
`shown_bg_color()`, `shown_font()` and `shown_icon_id()`
([APPEARANCE_STYLES.md](APPEARANCE_STYLES.md#what-the-views-draw)), and
the legacy code is gone.

The two rules differ, so moving changes what some rows look like:

- Several coloured categories: the legacy rule mixes their colours and
  fonts; the effective rule takes the highest style priority's (seen
  2026-09-28: purple drawn, red effective).
- A subtask with no colour or category of its own: legacy takes its
  parent's category colours, else its status colour; effective takes
  its parent's own or category style, else its own status.
- Styles set by categories or the status appear at the loop's next
  tick (within a second); an item's own style at once, as before.

Found on the way, fixed:

- The effective rule gave a subtask its parent's status and tracking
  styles (a completed subtask of an active task drawn active, the
  clock on every subtask of a tracked task): a task's own state is no
  longer passed down, as the views always showed (to do 35.9).
- A task's status icon never reached its effective icon: the status
  getter's name was wrong since #386.
- The effective setters sent one event per value, default and source:
  up to three refreshes per style change, now one.
- Until the loop's first pass styles a new or loaded task, its icon is
  empty; the calendar drew it as an invalid bitmap and lost tasks, the
  start tracking menu logged an invalid icon. Both skip it now, as the
  trees, tooltips and tray already did.

Scan, 2026-09-28 (sources the loop does not compute: none left after):

| Where | Legacy use | Now |
|---|---|---|
| `widgets/treectrl.py`, `widgets/listctrl.py` | Row colours, font (every tree and list view) | `shown_fg_color()`, `shown_bg_color()`, `shown_font()` |
| `widgets/hcalendar.py`, `widgets/calendarwidget.py` | Task colours, font, icon | The same, `shown_icon_id()` |
| `gui/viewer/base.py` `subjectImageIndices()`, `gui/viewer/task.py` `get_icon_id()` | Subject icons | `shown_icon_id()`: the effective icon with the plural/singular transform |
| `gui/viewer/task.py` Timeline, Square map | Colours, font | `shown_*()` |
| `gui/viewer/task.py` task graph | `task.foregroundColor(recursive=True)` (the wrong variable: `task`, not `tsk`) | `tsk.shown_fg_color()` |
| `gui/taskbaricon.py`, `gui/uicommand/uicommand.py` (start tracking menu) | Task icons | `shown_icon_id()` |
| `persistence/html/generator.py` | Export and print row colours | `shown_fg_color()`, `shown_bg_color()` |
| `gui/dialog/editor.py` owned-item lists | Notes, efforts, attachments rows | `shown_*()` |
| `domain/effort/base.py` | An effort's colours and font: its task's legacy ones | Its task's `shown_*()` |
| Old event `appearanceChangedEventType()` | Refreshes the task, category, note and effort views, the tray, editor pages, composite efforts; the task filter uses it for status changes | The effective-style events; the filter and the tray the status event; the event stays as an item's own style change |

---

## Master Design

The old master loop scanned every category, task and note every second
([Cost Before](#cost-before)). The goal is a cheap entry point each
second, and the full scan only at the seconds when time or data
changes something: instead of every second, only when a second
matters.

1. **One master timer list**: every second not processed yet at which
   something changes, in a binary heap (`heapq`). Seconds are only ever
   added, on every change; they leave only when processed. An entry
   may lie in the past: it is then simply due.
2. **Whole seconds, one rule**: every date and time is a whole second
   ([Time Resolution](#time-resolution)), and each entry is the first
   whole second at which its rule holds. A rule that holds after a
   date (overdue: due `<` now) gets the second after it; a rule that
   holds from a date on (active: actual start `<=` now) gets the
   date's own second. No other case.
3. **Each second**: if the smallest entry is at or before now, pop
   every entry up to now and run the full loop once, however many
   were due. Otherwise nothing else runs. A reminder set in the past,
   a file just opened, a late tick or a jump forward (suspend, resume)
   all come down to entries at or before now.
4. **The full loop**: run the full master loop, as today, with the
   statuses computed at the current second: every status, reminder and
   style, in one place. This is how the recursive updates stay
   manageable: subtasks, categories, prerequisites. **The cascade runs
   through the heap** (ruling below): one pass per second, never a
   loop inside a tick.
5. **Clock set back** (a time change): rebuild the heap from the tasks.
   The seconds between the new time and the old one are future again;
   the ones before it are due, so the full loop runs at once.
6. **Data changes**: a change to anything the full loop reads (an edit,
   a task added, a category's colour, an appearance setting) pushes
   the current second, so the loop at the next tick recomputes the
   styles and the cascades through the hierarchy
   ([Data Changes](#data-changes)).

## Time Resolution

**Ruling, 2026-09-27:** every date, time and duration Task Coach
stores, computes or compares is a whole second: task dates, reminders,
efforts, the scheduler's clock, the statuses computed from them, and
the task file. Only logs carry fractions of a second: their
timestamps stay high resolution, to show the flow in detail. Timer
delays in the UI (debounce, animation, the window geometry's quiet
periods) are not time values and are not concerned.

**Amended, 2026-09-27:** the creation and modification dates are
logging data, not functional data: they keep the logs' precision
(microseconds, `date.Timestamp`), in memory and in the file, so
changes within one second stay ordered when merging keeps the newest
copy ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)).
A file written in whole seconds reads as whole seconds.

Why: the master timer list works in seconds, with one rule for every
entry. A fraction of a second would add cases (rounding up or down,
equal or not) and has no meaning for a user. One consequence: a task
planned to start "now" becomes late the second after, not a few
microseconds after.

How: `DateTime` and `TimeDelta` drop the microseconds whenever one is
made: the clock (`date.Now()`), parsing a file or an import,
arithmetic, `replace()`, `fromtimestamp()`, `fromDateTime()`. Every
value goes through them, so no path needs its own rounding. A file
written before keeps loading: its fractions are dropped on reading and
not written again.

**Ruling, 2026-09-27: the unset date is the infinite date.** A date
not set is the latest whole second, 9999-12-31 23:59:59 (canon, with
its reasons:
[ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#dates-not-set-is-the-latest-date)).
For the master timer list, an unset date is simply the last possible
second of the schedule: the entries it gives sit at the very end of
the list and are in practice never reached, so the list needs no "is
it set?" case. The "second after" rule stops at the latest second, as
no later one exists.

Sweep, to leave nothing behind in this branch:

- [x] `DateTime` and `TimeDelta` constructors drop the microseconds;
  whole-second tests for every way of making one
  (`WholeSecondsTest`, `TimeDeltaTest`)
- [x] The unset date (`DateTime()`, `DateTime.max`) is 9999-12-31
  23:59:59; `endOfDay()` is 23:59:59
- [x] XML reader: end of day 23:59:59, start of day 00:00:00, no
  microsecond defaults
- [x] Recurrence, suggested dates and date helpers no longer copy or
  set microseconds
- [x] The date control's default "now" and the effort editor's "Stop
  now" are whole seconds (starting tracking and snoozing use
  `date.Now()`)
- [x] `TimeDelta.max` and `min` in whole seconds, as `DateTime.max`:
  "time left" of a task without a due date still shows as infinite
- [x] Tests no longer pass fractions, except those checking they are
  dropped
- Kept: `log_step()` and the other log timestamps; `perf_counter()`
  durations in traces; UI timer delays in milliseconds

## Index

- [To Do](#to-do)
- [Views on the Effective Styles](#views-on-the-effective-styles)
- [Master Design](#master-design)
- [Time Resolution](#time-resolution)
- [The Master Timer List](#the-master-timer-list)
- [What Changes the Master Timer List](#what-changes-the-master-timer-list)
- [Data Changes](#data-changes)
- [Cost Before](#cost-before)
- [Cost After](#cost-after)
- [Later: the Reason for Each Entry](#later-the-reason-for-each-entry)
- [ID Review](#id-review)
- [How It Was Measured](#how-it-was-measured)
- [History: One List on the Tick, Not a Timer per Event](#history-one-list-on-the-tick-not-a-timer-per-event)

---

## The Master Timer List

The entries, per task, each the first whole second at which its rule
holds:

| Rule | Holds when | Entry |
|---|---|---|
| Late | Planned start `<` now | The second after the planned start |
| Active | Actual start `<=` now | The actual start's second |
| Due soon | Due less the due soon hours `<` now | The second after it |
| Overdue | Due `<` now | The second after the due |
| Reminder | Reminder less 2 s `<=` now (2 s ahead, as today) | That second |

Dates are whole seconds ([Time Resolution](#time-resolution)). These
are the only time conditions in the loop: `Task.compute_status()`
(overdue, due soon, active, late, each on the task's own dates, not
its subtasks') and `processReminder()`.
Completion is not one: a completion date, even a future one, makes the
task completed at once. Styles read time only through the status.

Completed tasks get entries too: one rule for every task, and
completing or reopening one needs no signal. At an entry of a
completed task the full loop finds nothing new.

One function gives a task's entries; the build, the add event and the
field changes all use it.

The entries are seconds only, without their task: the full loop needs
no more. A date changed or a task deleted leaves its old second in the
heap; at that second the full loop runs, finds nothing new, and the
second is gone with the others popped. Removing it earlier would need
its task and the reason it was added (which rule, or which change to
cascade): the whole analysis over again
([Later](#later-the-reason-for-each-entry)). Entries leave the heap
only when popped, or when it is emptied or rebuilt.

The due entries are popped before the loop runs, not after: a second
pushed during the loop at or before now stays and runs the loop at the
next tick.

Every change pushes its seconds, duplicates included: identical
seconds are popped together and give one loop. Tasks added (a file
opened, a paste, an import) push their seconds one by one (25,000
into an empty heap: 4.7 ms); a rebuild
(the clock set back, the due soon hours changed) collects every task's
seconds and calls `heapify()` once.

Opening a file: `TaskFile.load()` empties the task list, then adds the
file's tasks in one add event. The heap is emptied with the task list
(its remove event leaving it empty), so the file's tasks fill an empty
heap; their past seconds are due, so the next tick runs the full loop
once and pops them.

The minute and day changes only tell viewers to refresh; they stay the
tick's own checks.

Size and cost, measured with `heapq` on `datetime`s: 5000 tasks give
at most 25,000 entries, about 1.4 MB. Building the heap takes 1.1 ms,
a push and a pop 0.4 us, the check each second (the smallest entry)
0.06 us. After the first loop only the future entries remain.

---

## What Changes the Master Timer List

For time, the list listens to three signals, each pushing the
seconds of the tasks concerned (data changes push the current second
as well: [Data Changes](#data-changes)):

| Signal | Today | Change to the list |
|---|---|---|
| A task's due, planned start, actual start or reminder changed | Publisher `task.<field>` from the field's change callback, the task as source ([PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#migration-log)) | Push the task's seconds |
| Tasks added to the task file's task list | Publisher add event of the task list; `extend()` includes every subtask | Push their seconds |
| Due soon hours changed | Publisher `behavior.duesoonhours`, the settings as source | Push every task's due soon second |

Each ancestor is a source of the same event too; it pushes the
ancestor's own seconds again, a harmless duplicate.

A second pushed at or before now is due at the next tick: a
reminder set to a past time fires, a task pasted with a past due date
is shown overdue.

Clock changes: a tick earlier than the one before rebuilds the heap
([Master Design](#master-design), 5). Jumping forward needs nothing:
the seconds passed are due.

### Why Nothing Is Missed

Checked in the code, 2026-09-27:

- **The three dates and the reminder** are private `Attribute`s. Their
  only writes are the constructor and `Attribute.set()`, which calls
  the change callback on every change; nothing reaches them another
  way (no `_Task__` access). The reminder was a plain field until step
  4, written in `setReminder()` and both branches of
  `snooze_reminder()`.
- **The constructor** sends no change: the add event covers it. Every
  way a task enters the task file ends in `extend()` or `append()` on
  its task list: new task or subtask, paste, template, undo of a
  delete, file opened or merged, CSV and Todo.txt import. Commands given a
  viewer's list pass through to the task file's.
- **The due soon hours** are the only setting in the time conditions;
  the reminder's 2 s is a constant.

Which signal covers each action:

| Action | Signal |
|---|---|
| Date set, changed or cleared: editor, viewer, calendar or timeline drag, presets, planned duration, start tracking setting an empty actual start, effort commands, Mark active or inactive | Field changed |
| Recurring task completed: `recur()` reopens it and moves its dates and reminder | Field changed |
| Reminder set, changed, snoozed or cleared: editor, reminder dialog, completion of a non-recurring task | Field changed (reminder) |
| Undo or redo of an edit: `__setstate__()` calls the setters | Field changed |
| New task or subtask, paste, template, import, file opened, file merged, undo of a delete | Tasks added |
| Due soon hours, Preferences | Due soon hours changed |
| Delete, cut, undo of an add | None: the old seconds stay, find nothing and are removed when processed |
| Completed or reopened | None: completion is not a time condition, and completed tasks keep their entries |

No other change gives a task new time seconds: moving a task to
another parent, prerequisites (a task waiting for one keeps its
entries; the full loop finds it inactive), categories, subjects,
styles, other settings.

---

## Data Changes

**Rule:** a change to anything the full loop reads pushes the current
second. The loop at the next tick recomputes every status, style and
cascade through the hierarchy, as it does today every second. Several
changes in one second are popped together: one loop.

What the loop reads, so what pushes the current second:

- A task's dates, completion, reminder, recurrence, prerequisites,
  categories, parent, own colours, font and icon, efforts being
  tracked, notes and attachments
- A category's or a note's colours, font, icon, parent, and a
  category's style priority
- Tasks, categories, notes and attachments added or removed
- The appearance settings (colour, font and icon per status, light and
  dark), the theme, the due soon hours

The hook is the domain's modification events (`_data_event_types()`
in `gui/scheduler.py`), a task's tracking, and the loop's own outputs
(status, derived and effective styles), except fields that change no
status, reminder or style, such as the subject, the description, the
fees, the priority and the expanded state, so typing does not run the
loop every second. Computed values the loop does not read (time
spent, budget left, revenue, the effective priority) run nothing.

The safe side decides doubtful fields: one wrongly left in costs a
loop; one wrongly left out is a miss, which the check mode of item 5
logs. Settings are the other way round: only the sections listed
above, as window and other settings change often and the loop reads
none of them.

### Ruling: the Cascade Runs Through the Heap

**Ruling, 2026-09-27 (design intent).** When the heap has a due entry,
the full loop runs once over all objects. Every change it makes (a
status, a style, a reminder cleared) is a change like any other: it
pushes the current second, or the task's new seconds, into the heap.
The next second, the heap is due again and the loop runs again. So the
cascade through the hierarchy needs no logic of its own: it settles
one pass per second, like today's loop, but only while something still
changes.

- **No freeze**: one pass per tick at most, never a loop inside a
  tick; the UI runs between passes.
- **No pass for nothing**: a pass that changes nothing pushes nothing,
  so the next second runs nothing. Unchanged values send no event
  (item 3), and a reminder trigger is not a change: triggered again
  while its dialog is open, it is dropped
  ([Reminders](#data-changes)).
- **It settles**: styles flow one way (category to task, parent to
  child) and statuses come from the saved data, so no change feeds
  back into its cause. Today's loop settled after a file opened in
  two passes: the third changed nothing (the prototype's trace,
  2026-09-27, 200 tasks).
- **Fewer passes**: the loop visits parents first (`allItemsSorted()`;
  today it visits tasks and categories in set order, so a child seen
  before its parent took the parent's old style), so most cascades
  settle in the first pass and the second only finds nothing.

The only dates a pass writes are reminders: a completed task's
reminder cleared by `processReminder()`. Its change pushes the task's
seconds (the unset date's, at the end of the heap) and the current
second, like any other change.

**Reminders** follow the design: the full loop at the reminder's second
triggers it once. The trigger every second while a reminder is due goes
away: the controller drops a trigger only while the task's dialog is
open, and no dialog action leaves a reminder due (closing snoozes or
clears it, marking completed clears or advances it, a deleted task
closes it).

---

## Cost Before

Time of one tick, measured 2026-09-27 in the real app on the desktop
(Debian 13, wxPython 4.2.3), with the `[SCHEDULER]` trace line of the
prototype (median and maximum of 60 ticks, idle, first minute after
loading left out) and files from `tools/generate_task_file.py`
(parents with 9 subtasks, 20 categories, 50 notes, dates 20 days and
reminders 2 days around now):

| Tasks | Today | Without events for unchanged values |
|-------|-------|-------------------------------------|
| 200 | 39 ms, max 70 | 30 ms, max 57 |
| 2000 | 258 ms, max 439 | 197 ms, max 280 |
| 5000 | 620 to 670 ms, max 1000 | 472 ms, max 575 |

It runs on the UI thread every second: with 2000 tasks the UI is
blocked a quarter of the time, with 5000 two thirds, so typing,
scrolling and window resizing stutter.

The first full loop after a file is opened is slower (15 s with 2000
tasks, 57 s with 5000); the refactor runs it the same way, so it is
not part of this plan.

The earlier profile (a scratch copy under Xvfb, 2000 tasks):
`computeStyles` 69%, `compute_stored_status` 17%,
`recomputeLegacyStatus` 8%. Nearly all of it recomputes unchanged
values; `Attribute.set()` created and sent an empty `Event` for each of
about 40,000 unchanged values per tick (the second column removes
that).

---

## Cost After

Measured 2026-09-27 in the real app on the desktop with the
`[SCHEDULER]` minute line ([SCHEDULERS.md](SCHEDULERS.md#masterscheduler-processing-flow)):

| File | Before | After |
|---|---|---|
| 2000 tasks, dates 20 days around now, idle | 258 ms every second | 1 pass a minute, 213 ms; 59 of 60 ticks do nothing |
| 200 tasks, dates 60 minutes around now | 39 ms every second | 2 to 4 passes a minute, about 50 ms each |
| 2000 tasks, dates 60 minutes around now (about 25 statuses changing a minute) | UI thread busy 98%, 5 to 10 ticks a minute, autosave re-reading the file after every status change | Busy 11%, the passes; 28 to 54 ticks a minute ([To Do](#to-do), 11) |

Nothing missed: with `TASKCOACH_SCHEDULER_CHECK=1` the full loop ran
every second as well for 3 minutes with 200 tasks and with 2000, dates
within 60 minutes (about 25 statuses changing a minute), and made no
change at a second the heap did not call for.

Each due second costs its pass and one more that finds nothing (the
[cascade ruling](#ruling-the-cascade-runs-through-the-heap)).

---

## Later: the Reason for Each Entry

To do, not planned yet: record for each entry its task and the exact
reason it was added (which rule, or which change to cascade). That
would allow removing entries that no longer apply and processing only
the tasks concerned instead of every task. It is coupled to the
cascade through the hierarchy (categories, parents, prerequisites),
which is what makes it complicated; whether it is worth it is decided
then, with the costs measured after items 5 and 6.

---

## ID Review

Checked 2026-09-28, across the repository:

- Every task, category, note, attachment and effort gets an ID when
  created (`base.new_id()`, a random UUID), keeps it for life and saves
  it. Only reading a file and undo (each object's own state) set an
  existing ID.
- Copies get new IDs (`__getcopystate__()` leaves the ID and the
  creation date out): copy and paste, paste as subitem, the subtasks,
  notes, attachments and efforts copied with them, a task saved as a
  template and each task made from one. The first paste after a cut
  is a move: the cut items themselves, IDs kept.
- Creation and modification dates are the clock's time with
  microseconds; different items may share one.
- The same ID in two files is the same item: Save As, Save selection,
  backups; File > Merge matches items by it; Todo.txt `tcid:` updates
  the task it names (an unknown one is skipped, never created).
- A recurring task advances in place; no new task.
- Not item IDs: wx window and menu IDs (`IdProvider`), returned when
  a window closes.

---

## How It Was Measured

`tools/generate_task_file.py TASKS FILE [MINUTES]` writes the task
files; with MINUTES every date falls within that many minutes of now,
so statuses change and reminders fire while the file is open. The app
runs from the repository on the desktop with its own `--ini` settings,
`XDG_CONFIG_HOME`/`XDG_DATA_HOME` and a copy of the file, closed after
a few minutes; the `[SCHEDULER]` trace line gives the tick cost once a
minute. Each variant runs from its own `git worktree`, so edits made
meanwhile cannot leak into a run. The earlier numbers came from a
scratch copy of the app under Xvfb.

---

## History: One List on the Tick, Not a Timer per Event

A timer per event is the same idea, and it was tried: the scheduler
removed in January 2026 kept a sorted job list with one `wx.CallLater`
for the next job (see [SCHEDULERS.md](SCHEDULERS.md#historical-context)). The
list on the tick avoids its failures:

- The list holds seconds, not bound methods, so no unschedule can
  miss.
- A task's entries are taken from its fields whenever they change,
  never adjusted in each setter. The old setters missed cases: tasks
  loaded from a file bypass the setters ([DATETIME_PRESETS.md](DATETIME_PRESETS.md#reminder-scheduling-on-load)).
- No timer of its own, so nothing fires while dialogs are created or
  destroyed, and no timer outlives its owner
  ([CRASH_GUARD.md](CRASH_GUARD.md)).
- Comparing wall-clock time each tick handles suspend and clock
  changes; a relative timer fires at the wrong wall time.
- The list can be logged.

**Tried and dropped, 2026-09-27:** one dirty flag running the full loop
only after a change. It listened to every event, and a due reminder's
trigger every second counted as a change, so the loop never skipped.
The cascade ruling keeps the idea without that fault: only the change
events push, and a trigger is not one. An uncommitted
prototype also went further than this design (entries carrying their
task, processed per object); what stays useful from it: the
`Attribute.set()` change, the once-a-minute `[SCHEDULER]` cost line,
and debug switches to profile the first ticks and to check a skipped
tick against the full loop.
