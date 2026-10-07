# Task Status Sorting in TaskCoach

## Core Concept

When "Sort by status first" is enabled (the default), tasks organize by status regardless of the primary sort column.

## Current Implementation

The system uses a numeric priority system where each status has a distinct sort priority, read with `TaskStatus.get_sort_priority(settings)`. These priorities are **user-configurable** via the Preferences > Statuses tab.

### Default Priorities

| Priority | Status    |
|----------|-----------|
| 6        | overdue   |
| 5        | duesoon   |
| 4        | late      |
| 3        | active    |
| 2        | inactive  |
| 1        | completed |

Higher priority values sort first (descending), ensuring:
- **Overdue** tasks always appear at the top (most urgent)
- **Due soon** tasks follow (approaching deadline)
- **Late** tasks next (should have started)
- **Active** tasks in the middle (normal work in progress)
- **Inactive** tasks lower (future work)
- **Completed** tasks at the bottom

### User Configuration

Priorities can be changed in Preferences > Statuses using the "Sort Priority" dropdown (1-6) for each status. When a priority is changed, all other priorities are automatically adjusted using insert-before semantics to ensure no duplicates:

- **Moving up** (e.g., 6 to 2): all priorities in [2, 6) shift up by 1
- **Moving down** (e.g., 1 to 4): all priorities in (1, 4] shift down by 1

Priorities are stored in the `[statussortpriority]` section of the settings file; `get_sort_priority()` reads them on each call.

### Sort Key Construction

The sorter uses:

```python
sort_key = [-status.get_sort_priority(settings)] + [column_sort_key]  # ascending
sort_key = [status.get_sort_priority(settings)] + [column_sort_key]   # descending
```

For ascending sort, priority is negated to maintain urgency-first ordering.

The Status column sorts by the same key (`Task.statusSortFunction()`,
since 2026-10-01: until then it sorted by subject).

### Re-sorting

With "Sort by status first", or sorted by the Status column, an edit
of a date, the completion or the prerequisites re-sorts at once. A status the clock changes (a planned
start or due time passing, the due soon hours changed) re-sorts once
after the master loop's pass (`scheduler.pass`), not for each task
([SCHEDULERS.md](SCHEDULERS.md)).

### Ties

Items with equal sort keys keep their creation order, then their ID
(`_tie_break_key()` in `domain/base/sorter.py`), so the order is
deterministic. The tie-break was the ID alone until 2026-09-28, which
followed creation order only while IDs were time-based
([PERSISTENCE_XML.md](PERSISTENCE_XML.md#ids)).

## Tree Mode

Analysed 2026-10-05 (GitHub #48 and #321; P202 and P206 in
[REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md#pre-existing-issues)),
the same on master:

- The sorter orders the tasks the view shows by `[status priority,
  column value]` (the status part only with "Sort by status first",
  on by default); the tree shows each level in that order
  (`TreeSorter.rootItems()`, `children_of()`).
- The status is the task's own: its dates and prerequisites, its
  ancestors' prerequisites included, never its subtasks'
  (`Task.compute_status()`). An inactive parent with a subtask due
  soon sorts with the inactive tasks (#321).
- The column value is the subtree value in tree mode
  ([TASK_FIELDS.md](TASK_FIELDS.md#core-fields)): the task's and its
  subtasks', from the tasks themselves, so whether a filter hides a
  subtask or not. A collapsed parent shows the same value in
  parentheses, so the order follows what it shows; a hidden subtask
  shows there and moves it (#48).
- Pinned by `TaskSorterTreeModeTest` (a subtask's due date and
  priority move its parent); nothing pins a filter or the status part
  in the tree.

**Ruled by designer 2026-10-05: kept as released** ("Option A
please"). Behaviours other than these, if wanted, come as new opt-in
sort keys beside the core ones, so saved views keep theirs
([TASK_FIELDS.md](TASK_FIELDS.md#postponed-base-and-effective-fields)).

## Legacy Sort Algorithm

The previous implementation used a binary bucket approach with composite sort keys:

```python
sort_key = [completed(), inactive()] + [column_sort_key]
```

Since Python evaluates tuples element-by-element and `False < True`, this created three status buckets:

| Status Bucket | Position | Details |
|---------------|----------|---------|
| Active/Overdue/Late/Due Soon | 1st | Non-completed, non-inactive tasks |
| Inactive | 2nd | Inactive but incomplete tasks |
| Completed | 3rd | Finished tasks |

### Limitations of Legacy Approach

- Finer status distinctions (overdue vs due-soon vs active) only affected color coding, not sort position
- All "active" states sorted together regardless of urgency
- No way to prioritize overdue tasks above merely active ones

### Legacy Descending Implementation

For descending sort, booleans were negated to preserve bucket stability:

```python
sort_key = [not completed(), not inactive()] + [column_sort_key]
```

## Core Files

- `taskcoachlib/domain/task/sorter.py` - Composite key logic, subscribes to priority changes
- `taskcoachlib/domain/task/status.py` - Status definitions, `get_sort_priority(settings)`
- `taskcoachlib/domain/task/task.py` - Status computation methods
- `taskcoachlib/config/defaults.py` - Default priorities in `statussortpriority` section
- `taskcoachlib/gui/dialog/preferences.py` - Statuses tab with priority dropdowns
