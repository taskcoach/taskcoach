# Task Status Sorting in TaskCoach

## Core Concept

When "Sort by status first" is enabled (the default), tasks organize by status regardless of the primary sort column.

## Current Implementation

The current system uses a numeric priority system where each status has a distinct sort priority via the `statusSortPriority` attribute:

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

### Sort Key Construction

Each `TaskStatus` object has a `statusSortPriority` attribute. The sorter uses:

```python
sort_key = [-status.statusSortPriority] + [column_sort_key]  # ascending
sort_key = [status.statusSortPriority] + [column_sort_key]   # descending
```

For ascending sort, priority is negated to maintain urgency-first ordering.

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

- `taskcoachlib/domain/task/sorter.py` - Composite key logic
- `taskcoachlib/domain/task/status.py` - Status definitions with statusSortPriority
- `taskcoachlib/domain/task/task.py` - Status computation methods
