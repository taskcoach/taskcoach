# Task Status Sorting in TaskCoach

## Core Concept

When "Sort by status first" is enabled (the default), tasks organize by status regardless of the primary sort column.

## Current Implementation

The system uses a numeric priority system where each status has a distinct sort priority, read with `TaskStatus.getSortPriority(settings)`. These priorities are **user-configurable** via the Preferences > Statuses tab.

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

Priorities are stored in the `[statussortpriority]` section of the settings file; `getSortPriority()` reads them on each call.

### Sort Key Construction

The sorter uses:

```python
sort_key = [-status.getSortPriority(settings)] + [column_sort_key]  # ascending
sort_key = [status.getSortPriority(settings)] + [column_sort_key]   # descending
```

For ascending sort, priority is negated to maintain urgency-first ordering.

### Re-sorting

With "Sort by status first", an edit of a date, the completion or the
prerequisites re-sorts at once. A status the clock changes (a planned
start or due time passing, the due soon hours changed) re-sorts once
after the master loop's pass (`scheduler.pass`), not for each task
([SCHEDULERS.md](SCHEDULERS.md)).

### Ties

Items with equal sort keys keep their creation order, then their ID
(`_tie_break_key()` in `domain/base/sorter.py`), so the order is
deterministic. The tie-break was the ID alone until 2026-09-28, which
followed creation order only while IDs were time-based
([PERSISTENCE_XML.md](PERSISTENCE_XML.md#ids)).

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
- `taskcoachlib/domain/task/status.py` - Status definitions, `getSortPriority(settings)`
- `taskcoachlib/domain/task/task.py` - Status computation methods
- `taskcoachlib/config/defaults.py` - Default priorities in `statussortpriority` section
- `taskcoachlib/gui/dialog/preferences.py` - Statuses tab with priority dropdowns
