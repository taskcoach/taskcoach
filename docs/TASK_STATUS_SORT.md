# Status-First Task Sorting

## Overview

When "Sort by status first" is enabled (default: on), tasks are grouped by
their completion status before the selected column sort is applied.  This
ensures active tasks always appear above inactive tasks, which appear above
completed tasks — regardless of the primary sort column.

## How It Works

The sorter builds a **composite sort key** for each task:

```
sort_key = [completed(), inactive()] + [column_sort_key]
```

Python sorts tuples element-by-element, so the status booleans are evaluated
first.  `False < True`, which produces three buckets:

| completed() | inactive() | Status bucket                           | Sort position |
|-------------|------------|-----------------------------------------|---------------|
| False       | False      | Active, overdue, late, duetoday, due... | 1st (top)     |
| False       | True       | Inactive                                | 2nd           |
| True        | False      | Completed                               | 3rd (bottom)  |

Within each bucket, tasks are sorted by the selected column (subject, due
date, priority, etc.).

### Example: Planned Start column, ascending (today = 2026-02-04)

| # | completed() | inactive() | Planned Start  | Status   | Sort Key                          |
|---|-------------|------------|----------------|----------|-----------------------------------|
| 1 | False       | False      | 2026-01-15     | late     | (False, False, 2026-01-15)        |
| 2 | False       | False      | 2026-01-20     | overdue  | (False, False, 2026-01-20)        |
| 3 | False       | False      | 2026-02-01     | active   | (False, False, 2026-02-01)        |
| 4 | False       | False      | 2026-02-04     | duetoday | (False, False, 2026-02-04)        |
| 5 | False       | True       | 2026-02-10     | inactive | (False, True, 2026-02-10)         |
| 6 | False       | True       | 2026-03-01     | inactive | (False, True, 2026-03-01)         |
| 7 | True        | False      | 2026-01-10     | completed| (True, False, 2026-01-10)         |
| 8 | True        | False      | 2026-01-17     | completed| (True, False, 2026-01-17)         |

Note: active, overdue, late, duetoday, and duetomorrow are **all mixed
together** in the first bucket.  The sort does not distinguish between them —
those finer statuses only affect the task's color, not its sort position.
Within each bucket, the planned start date determines the order.

### Descending sort

The bucket order is **always** Active → Inactive → Completed, regardless of
sort direction.  Only the column sort within each bucket reverses.

Internally, the descending key negates the booleans to counteract Python's
`reverse=True`, keeping the bucket order stable.

## Key Files

| File | Role |
|------|------|
| `taskcoachlib/domain/task/sorter.py` | Composite sort key logic |
| `taskcoachlib/domain/task/task.py:620-634` | `completed()` and `inactive()` boolean projections |
| `taskcoachlib/domain/task/status.py` | `TaskStatus` enum (active, inactive, overdue, etc.) |
| `taskcoachlib/gui/viewer/mixin.py:525-551` | Viewer setting integration |
| `taskcoachlib/gui/uicommand/uicommand.py:1397` | Menu command "Sort by status first" |
| `taskcoachlib/config/defaults.py` | Default: `True` for all task viewers |

## History

The status-first sort algorithm was created in 2005 by Frank Niessink:
[`e6d0de5e` — taskcoach/taskcoachlib/task/sorter.py](https://github.com/taskcoach/taskcoach/blob/e6d0de5ee5bad37b3336bbb9dc0462772f285367/taskcoach/taskcoachlib/task/sorter.py)

It was refactored in 2014 by Jérôme Laheurte for stable sort support, but
the algorithm itself remained the same:
[`82a114b4` — taskcoach/taskcoachlib/domain/task/sorter.py](https://github.com/taskcoach/taskcoach/blob/82a114b4bdb3f5054af6628a484a1943516a5167/taskcoach/taskcoachlib/domain/task/sorter.py)

The core logic has not changed since:

```python
def __createStatusSortKey(self):
    if self.__sortByTaskStatusFirst:
        if self.isAscending():
            return lambda task: [task.completed(), task.inactive()]
        else:
            return lambda task: [not task.completed(), not task.inactive()]
    else:
        return lambda task: []
```

## Design Note

`completed()` and `inactive()` are both derived from `computedStatus()` —
a task has exactly one status at a time.  The two-boolean key is a compact
encoding that collapses all non-completed, non-inactive statuses (active,
overdue, late, duetoday, duetomorrow) into a single bucket.  This is
intentional: finer status distinctions are visual (color) only and do not
affect sort order.
