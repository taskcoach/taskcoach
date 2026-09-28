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

## Index

- [Priority](#priority)
- [Effective Priority](#effective-priority)
- [Subtree Values in Other Columns](#subtree-values-in-other-columns)

## Priority

The task's own priority: an integer, 0 by default, saved in the file
(`priority`, left out when 0).

- Shown and edited: the Priority column and the editor's Description
  tab.
- Sort: the task's own priority, in list and tree mode.
- Event: `task.priority`, the task as source.
- Exports: Todo.txt (a letter), iCalendar (`PRIORITY`, capped at 3),
  CSV and HTML when the column is shown.

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

Until 2026-09-28 the value had no name: the Priority column showed it
in parentheses on a collapsed task, and sorting by priority in tree
mode used it.

## Subtree Values in Other Columns

To do, one field at a time. These columns still show a collapsed
task's subtree value in parentheses, and sorting by them in tree mode
uses it (`renderedValue()` in `gui/viewer/task.py`, the `recursive`
argument of each getter). The master loop reads none of these subtree
values: its entries and statuses use each task's own dates.

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
