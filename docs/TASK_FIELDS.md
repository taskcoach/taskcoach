# Task Fields

What each task field means, where it is shown, how it sorts and which
event announces its changes. Fields are added as they are reviewed;
the status has its own document ([TASK_STATUS.md](TASK_STATUS.md)).

**Explicit fields** ([DEVELOPMENT.md](DEVELOPMENT.md#design)): a value
computed from other fields is a field of its own, with its own column,
sort and editor line, never folded into another field's display or
sort. The pattern comes from the status and the appearance, whose own,
derived and effective values are separate fields
([TASK_STATUS.md](TASK_STATUS.md#appearance-inheritance-overview)).
The core fields keep their folded behaviour
([Core Fields](#core-fields)).

## Index

- [Core Fields](#core-fields)
- [Priority](#priority)
- [Direct Priority](#direct-priority)
- [Effective Priority](#effective-priority)
- [Subtree Values in Other Columns](#subtree-values-in-other-columns)

## Core Fields

**Ruling by designer, 2026-09-29.** Priority and the 13 columns under
[Subtree Values in Other Columns](#subtree-values-in-other-columns)
are the core Task Coach fields, and users rely on them as they are:
the task's own value, except on a collapsed task in tree mode, which
shows its subtree value in parentheses, and in the tree-mode sort,
which uses the subtree value. Their column and sort keys keep that
behaviour. The explicit fields come beside them, under new names: a
direct field, the task's stored value in both modes, and an effective
field, the subtree value in both modes. Priority is the trial.

The subtree value is never saved nor read by the master loop: it is
computed when drawn or sorted, and events keep the view current, so
the core fields stay as they are while the scheduler refactor goes on
([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md)).

## Priority

A core field ([Core Fields](#core-fields)). The task's own priority is
an integer, 0 by default, saved in the file (`priority`, left out when
0); its subtree value is the [effective priority](#effective-priority).

- Shown: the Priority column, the task's own priority; a collapsed
  task in tree mode shows its effective priority in parentheses when
  it differs.
- Edited: the Priority column and the editor's Description tab, the
  task's own priority.
- Sort: the task's own priority in list mode, its effective priority
  in tree mode.
- Event: `task.priority`, the task as source. The column also redraws
  on `task.effectivePriority` and on expanding or collapsing; the
  sort follows both events.
- Exports: Todo.txt (a letter), iCalendar (`PRIORITY`, capped at 3),
  the task's own priority; CSV and HTML as the column shows it.

From 2026-09-28 to 2026-09-29 the column showed and sorted the task's
own priority only; restored as a core field.

## Direct Priority

The task's own priority, as stored, in both modes: the Priority
column without the subtree value.

- Shown and edited: the Direct priority column (hidden by default).
- Sort: View > Sort by > Direct priority, in list and tree mode.
- Event: `task.priority`.

## Effective Priority

**Canon decision by designer, 2026-09-28.** The highest of the task's
own priority and its open subtasks' effective priorities: the priority
that applies to the task given its subtree. Completed subtasks do not
count, nor do prerequisites or dependents.

- Computed when asked (`Task.effective_priority()`), not saved.
- Shown: the Effective priority column (hidden by default) and a
  read-only line under Priority in the editor.
- Sort: View > Sort by > Effective priority, in list and tree mode.
- Event: `task.effectivePriority`, sent in the event of its cause with
  the task and all its ancestors as sources, the only tasks a change
  can move. Causes: a task's own priority, a subtask completed or
  reopened, a subtask added, removed or moved. One change is one
  event however deep the tree; each listener (the task viewer, its
  sorter, an open editor) is called once with all its sources.
- Data only, never time, so the master loop neither reads nor
  computes it ([SCHEDULERS.md](SCHEDULERS.md#ssot-principle-scheduler-vs-events)).
- The square map ordered by priority sizes by it, through
  `priority(recursive=True)`.

Until 2026-09-28 the value had no name: the Priority column shows it
in parentheses on a collapsed task, and sorting by priority in tree
mode uses it, as it still does ([Priority](#priority)).

## Subtree Values in Other Columns

Core fields ([Core Fields](#core-fields)): these columns show a
collapsed task's subtree value in parentheses, and sorting by them in
tree mode uses it (`renderedValue()` in `gui/viewer/task.py`, the
`recursive` argument of each getter). Their direct and effective
fields are to do, one field at a time, after the priority trial. The
master loop reads none of these subtree values: its entries and
statuses use each task's own dates.

Subtree values are computed when drawn or sorted, and kept current by
events, like the effective priority:

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
