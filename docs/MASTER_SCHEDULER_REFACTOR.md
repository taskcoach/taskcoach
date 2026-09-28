# Master Scheduler Refactor

Plan to replace the full scan `MasterScheduler` runs every second.
[SCHEDULERS.md](SCHEDULERS.md) describes the scheduler as it is.

**Status:** steps 1 to 6, 8, 9 and 11 implemented, 2026-09-27
([Cost After](#cost-after)); 7 and 10 open.

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
  dropped. Two task viewer tests counted on microseconds passing
  between creating a task planned "now" and computing its status: in
  whole seconds it becomes late the second after, so their tasks are
  planned a second ago, as the other tests' tasks
- [x] The real app: a generated file with 628 dates with fractions
  loaded, autosaved (the first pass cleared the reminders of completed
  tasks) and saved without any; statuses as before; logs still in
  milliseconds
- [x] The full unit suite: the same 28 known failures as master, none
  new
- Kept: `log_step()` and the other log timestamps; `perf_counter()`
  durations in traces; UI timer delays in milliseconds

## Index

- [Master Design](#master-design)
- [Time Resolution](#time-resolution)
- [The Master Timer List](#the-master-timer-list)
- [What Changes the Master Timer List](#what-changes-the-master-timer-list)
- [Data Changes](#data-changes)
- [Cost Before](#cost-before)
- [Cost After](#cost-after)
- [Steps](#steps)
- [Later: the Reason for Each Entry](#later-the-reason-for-each-entry)
- [Open Questions and Issues Found](#open-questions-and-issues-found)
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
are the only time conditions in the loop: `Task.compute_status()` and
`recomputeLegacyStatus()` (overdue, due soon, active, late, each on the
task's own dates, not its subtasks') and `processReminder()`.
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
| Due soon hours changed | pypubsub `settings.behavior.duesoonhours` | Push every task's due soon second |

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
| Disk changes merged: changed fields | Field changed (the setters) |
| Disk changes merged: new tasks | Tasks added |
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

The hook is the domain's change messages, the ones the task file uses
to know it has unsaved changes (the Publisher modification events and
the pypubsub topics `pubsub.task`, `pubsub.note`, `pubsub.category`),
and the loop's own outputs (status, derived and effective styles),
except fields that change no status, reminder or style, such as the
subject and description, so typing does not run the loop every
second.

The safe side decides doubtful fields: one wrongly left in costs a
loop; one wrongly left out is a miss, which the debug check of step 5
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
  (step 3), and a reminder trigger is not a change: triggered again
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
| 2000 tasks, dates 60 minutes around now (about 25 statuses changing a minute) | UI thread busy 98%, 5 to 10 ticks a minute, autosave re-reading the file after every status change | Busy 11%, the passes; 28 to 54 ticks a minute ([Steps](#steps) 11) |

Nothing missed: with `TASKCOACH_SCHEDULER_CHECK=1` the full loop ran
every second as well for 3 minutes with 200 tasks and with 2000, dates
within 60 minutes (about 25 statuses changing a minute), and made no
change at a second the heap did not call for.

Each due second costs its pass and one more that finds nothing (the
[cascade ruling](#ruling-the-cascade-runs-through-the-heap)).

---

## Steps

1. Whole seconds everywhere ([Time Resolution](#time-resolution)): the
   starting point, done first.
2. One "not set" for every task date, the latest date: done. The
   reminder no longer uses `None`, and the date setters take `None` as
   "not set"; the review found no other divergence among the list's
   inputs. An effort still running keeps `None` for its missing stop,
   outside the list
   ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#dates-not-set-is-the-latest-date)).
3. No `Event` for an unchanged value (`Attribute.set()`): a quarter of
   the tick ([Cost Before](#cost-before)); done.
4. The date fields' and the reminder's change signals moved from
   pypubsub to the Publisher, the reminder made an `Attribute`
   ([Why Nothing Is Missed](#why-nothing-is-missed)): done.
5. The master timer list (a heap), the check each second, and the
   full loop at its entries, with the statuses computed at the tick's
   second, and the check mode (`TASKCOACH_SCHEDULER_CHECK=1`): done
   ([Cost After](#cost-after)). The empty `Task.onDailyChange()` went
   with it: the loop no longer runs daily.
6. Changes the loop reads, and the loop's own changes, push the
   current second, and the loop visits parents before children
   ([Data Changes](#data-changes),
   [the cascade ruling](#ruling-the-cascade-runs-through-the-heap)):
   done, with step 5.
7. The legacy status and colours: styles read `Task.status()`, which
   counts only the direct prerequisites, while `computedStatus()`
   counts those of the ancestors too
   ([TASK_STATUS.md](TASK_STATUS.md#migration-path)). Drop them once the
   results are shown to be the same.

Found along the way, 2026-09-27:

8. The objects' sync status (new, changed, deleted), left from the
   removed SyncML sync: since step 4 a task's ancestors are sources of
   its date events, so the task file's change handler flagged them as
   changed too. Removed with the rest of the SyncML leftovers
   ([PYTHON3_MIGRATION_4.md](PYTHON3_MIGRATION_4.md#backwards-compatibility)):
   done.
9. Merging changes made by another instance ignores the actual start:
   `Task.monitoredAttributes()` lacks `actualStartDateTime`, so the
   change monitor never records it: added, with a test for the merge
   and the save paths (`TaskFileTest`); done.

10. The first pass after a file opens opens one reminder window per
    due reminder, about 140 ms each: with 2000 tasks, 134 windows
    made it 19 s, against 0.7 s without them. This is the loading
    freeze. One window listing the due reminders, or windows opened
    one per tick, would end it.
11. With many statuses changing each minute (2000 tasks, dates within
    60 minutes) the UI thread was busy 98% of the time, 96% in
    autosave: a status change marked the file dirty, although the
    status is computed and not saved, and each save re-read the file
    to merge other instances' changes, where every categorized item
    sent its own event and reset the viewers' category filter
    (quadratic). Status changes no longer mark the file dirty, and the
    reader resolves categories in one event: busy 11%, the passes
    themselves; 28 then 54 ticks a minute instead of 5 to 10 (`py-spy`
    on the real app, 120 s each): done. Since item 13 a save no longer
    re-reads the file.

Chain of work, each needing the one before (2026-09-27):

12. Modification date set by the data layer on every stored change
    ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)),
    field by field; with it the stored fields' changes move from
    pypubsub to the Publisher.
13. Done: merging. The automatic merge with other instances removed,
    File > Merge a union with the newest copy of each item
    ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)); more exact as
    12 progresses.
14. The file marked unsaved only by stored fields' changes, not by
    computed values such as the status (item 11 skips the status by
    name for now); needs 12.

Tried and dropped on 2026-09-27: one dirty flag running the full loop
only after a change. It listened to every event, and a due reminder's
trigger every second counted as a change, so the loop never skipped.
The cascade ruling keeps the idea without that fault: only the change
events push, and a trigger is not one. An uncommitted
prototype also went further than this design (entries carrying their
task, processed per object); what stays useful from it: the
`Attribute.set()` change, the once-a-minute `[SCHEDULER]` cost line,
and debug switches to profile the first ticks and to check a skipped
tick against the full loop.

---

## Later: the Reason for Each Entry

To do, not planned yet: record for each entry its task and the exact
reason it was added (which rule, or which change to cascade). That
would allow removing entries that no longer apply and processing only
the tasks concerned instead of every task. It is coupled to the
cascade through the hierarchy (categories, parents, prerequisites),
which is what makes it complicated; whether it is worth it is decided
then, with the costs measured after steps 5 and 6.

---

## Open Questions and Issues Found

For later review (2026-09-27).

Questions to decide:

1. **File changed on disk.** Since item 13 nothing reacts to it: the
   watcher still runs and sends `taskfile.changed`, which nobody
   hears, and the next save replaces the file. Warn once (pointing to
   File > Merge), or remove the watcher and its `fspoll` setting?
2. **Undo back to the saved state.** Should it clear the unsaved mark
   (track the saved point)? See
   [UNDO_REDO.md](UNDO_REDO.md#persistence).
3. **View state and the modification date.** A category's filter
   state and a task's expanded state are saved but are not the item's
   data; they do not set the date today. Manual ordering does (it is
   an Attribute). One rule for all three
   ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date),
   row 11).

Issues found, not fixed:

4. The loop runs a pass on every pypubsub task, note and category
   message (the `pubsub.task` catch-all), computed ones included:
   revenue, time spent, budget left, tracking. A fee change still runs
   a pass through its revenue message. Narrow it as the stored fields
   leave pypubsub (item 14).
5. Attachment re-sorting listens under the base `Attachment` class's
   event types; file, link and mail attachments send under their own
   class names, so no change re-sorts them, whatever the column.
6. Task editor, Progress tab: a second percentage spin control and
   slider are drawn over the tab labels (seen under Xvfb with
   openbox; to check on a real display).
7. `EffortViewerTest.testStatusMessage_OneTaskOneActiveEffort` failed
   once: it expects 0:00:00 for an effort started when the test
   starts, so a second boundary fails it. Timing, not a regression.
8. File > Merge moves subtasks between parents with the normal
   operations, so the parent rules (completed when all children are,
   reopened by an open child) can run during it; the merged items
   still keep their winning copies' dates (`persistence/merge.py`).
9. A `.delta` file left by an older version next to a task file is
   ignored; nothing removes it.

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
