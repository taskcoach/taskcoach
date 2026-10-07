# Task Fields

What each task field means, where it is shown, how it sorts and which
event announces its changes. Fields are added as they are reviewed;
the status has its own document ([TASK_STATUS.md](TASK_STATUS.md)).

## Index

- [Core Fields](#core-fields)
- [Priority](#priority)
- [Subtree Values in Other Columns](#subtree-values-in-other-columns)
- [Postponed: Base and Effective Fields](#postponed-base-and-effective-fields)

## Core Fields

Priority and the 13 columns under
[Subtree Values in Other Columns](#subtree-values-in-other-columns)
are the core Task Coach fields, and users rely on them as they are:
the task's own value, except on a collapsed task in tree mode, which
shows its subtree value in parentheses, and in the tree-mode sort,
which uses the subtree value. The subtree value is computed when drawn
or sorted, never saved nor read by the master loop; events keep the
view current. Expanding the tree shows every task's own value.

## Priority

The task's own priority: an integer, 0 by default, saved in the file
(`priority`, left out when 0). Its subtree priority is the highest of
the task's own and its open subtasks' subtree priorities
(`priority(recursive=True)`); completed subtasks do not count, nor do
prerequisites or dependents.

- Shown: the Priority column, the task's own priority; a collapsed
  task in tree mode shows its subtree priority in parentheses when it
  differs.
- Edited: the Priority column and the editor's Description tab.
- Sort: the task's own priority in list mode, its subtree priority in
  tree mode.
- Event: `task.priority`, the task and its ancestors as sources. A
  subtask completed or reopened names its parent; one added or removed
  names the parent when its subtree priority is above the parent's
  own. The completion event reaches every ancestor, whose rows the
  Subject column repaints.
- Data only, never time: the master loop neither reads nor computes
  it, and a priority change runs no pass
  ([SCHEDULERS.md](SCHEDULERS.md#todo)).
- Exports: iCalendar (`PRIORITY`, capped at 3), the task's own
  priority; CSV and HTML as the column shows it.
- The square map ordered by priority sizes by the subtree priority.

## Subtree Values in Other Columns

Core fields ([Core Fields](#core-fields)): these columns show a
collapsed task's subtree value in parentheses, and sorting by them in
tree mode uses it (`renderedValue()` in `gui/viewer/task.py`, the
`recursive` argument of each getter). The master loop reads none of
these subtree values: its entries and statuses use each task's own
dates.

Subtree values are computed when drawn or sorted, and kept current by
events:

- A change to a task's field names the task and all its ancestors
  (`Task._send_to_self_and_ancestors()`); recurrence did not until
  2026-09-28.
- A subtask completed or reopened sends its completion event to all
  its ancestors. The task viewer's Subject column listens to it, so
  their rows repaint, and the task sorter re-sorts on every date and
  completion event, whatever it sorts by.
- Adding, removing or moving a task (drag and drop removes and adds
  it) refreshes the viewer and re-sorts.
- Time left also changes with the clock: the viewer redraws every
  minute.

| Column | Subtree value |
|---|---|
| Planned start date | Earliest of the task's and its open subtasks' |
| Due date | Earliest of the task's and its open subtasks' |
| Actual start date | Earliest of the task's and its open subtasks' |
| Completion date | Latest of the task's and its completed subtasks' |
| Reminder | Earliest of the task's and all its subtasks' |
| Time left | The subtree due date less now |
| Recurrence | Shortest of the task's and all its descendants' |
| % complete | Average of the task's and its subtasks' (the task's left out at 0% when it completes with its subtasks) |
| Time spent | Sum over the task's and its subtasks' efforts |
| Budget | Sum of the task's and its subtasks' |
| Budget left | Subtree budget less subtree time spent |
| Fixed fee | Sum of the task's and its subtasks' |
| Revenue | Sum of the task's and its subtasks' |

## Postponed: Base and Effective Fields

**Decision by designer, 2026-09-29: postponed.** The idea: give each
core field's two values a field of their own, with a column and a
sort, beside the core column, which stays as it is:

- **Base**, the task's own value in list and tree mode alike, titled
  after the field: "Priority (base)", "Due date (base)".
- **Effective**, the subtree value in both modes: "Priority
  (effective)", "Due date (effective)".

It follows the explicit fields principle
([DEVELOPMENT.md](DEVELOPMENT.md#design)), which comes from the status
and the appearance, whose own, derived and effective values are
separate fields
([TASK_STATUS.md](TASK_STATUS.md#appearance-inheritance-overview)).

How it went:

1. 2026-02-11 (#374): a TODO in SCHEDULERS.md proposed computing the
   subtree priority in the master loop and storing it, as the status.
2. 2026-09-28: decided no. Priority depends on data, never on time;
   computed by the loop it would lag a tick behind each edit and climb
   one level per pass, as the loop visits parents first. It stays
   computed when asked and kept current by events
   ([SCHEDULERS.md](SCHEDULERS.md#todo)).
3. 2026-09-28: the designer asked for an effective priority as a field
   of its own, so sorting could use it or not. Added (8355f0f29) with
   the Priority column changed to the task's own value only, which
   broke saved views sorted by priority in tree mode, and exports.
4. 2026-09-29: the Priority column restored as it was; the new pair
   named base and effective, for all 14 core fields.
5. 2026-09-29: postponed, and the priority changes undone: the fields
   are as they were before step 3.

Why postponed:

- Not load-bearing for the master scheduler refactor: the loop reads
  no subtree value, and none is saved, dated or merged.
- Scope: 28 columns and sorts in one change, beside a refactor still
  under way.
- Limited reach: the subtree value shows only on collapsed tasks in
  tree mode and sorts only in tree mode; expanding the tree shows
  every task's own value.

When resumed: new column and sort keys, so saved views keep the core
fields' behaviour; every field's event already names the task and its
ancestors, so the new columns can listen to the core ones' events.
Open then: editor lines, and where the 28 sorts go in View > Sort by.
