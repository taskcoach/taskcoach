# Efforts

The time spent on tasks: what an effort is, the views that show
efforts, what they filter, and how tracking starts and stops. Editing
an effort's period and its entry modes:
[DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md#edit-effort-window).

## Table of Contents

1. [What an Effort Is](#what-an-effort-is)
2. [Views](#views)
3. [Filters](#filters)
4. [Tracking](#tracking)
5. [Code](#code)
6. [History](#history)

---

## What an Effort Is

One period of work on one task: a start, an end and a description.
An effort with no end yet is tracked: its time grows until it is
stopped. A task's time spent is the sum of its efforts; its totals add
its subtasks'. Efforts are saved in the task file, inside their task.

## Views

| View | Opened from | Shows the efforts of |
|---|---|---|
| Effort | View > New viewer > Effort | every task |
| Effort for selected task(s) | View > New viewer > Effort for selected task(s) | the tasks selected in the task view and all their subtasks, following the selection |
| The editor's Effort tab | a task's editor | the edited tasks and all their subtasks |

Each lists every effort ("Effort details") or adds them up per day,
week or month (the toolbar's choice); added up, the time can be
rounded. Each keeps its own columns and choices: the settings sections
`effortviewer`, `effortviewerforselectedtasks` and
`effortviewerintaskeditor`.

## Filters

- **Search:** the search box, in every view.
- **Category filter** (the categories ticked in a Categories view), in
  the main window's two views: an effort shows when its task is in a
  ticked category, or a subtask of one (any ticked category, or all,
  as the filter is set). So Effort for selected task(s), with a
  project selected, shows the project's efforts in those categories.
  A task the task view shows only as the parent of a matching subtask
  does not pass itself: its own efforts stay hidden, as the task does
  in the task view's list mode.
- **The editor's Effort tab has no category filter**, **ruled by
  designer 2026-10-04** (GitHub #157): an editor shows all of an
  item's, as its Notes and Attachments tabs do. Before, the tab took
  the filter with its class: an effort added there could stay hidden,
  and its toolbar's reset button cleared the main window's filter.

## Tracking

One task is tracked at a time, **ruled by designer 2026-10-04**: "For
now, simplify to only track one task at a time" (GitHub #40).

- **Start tracking** (Ctrl+T; the Actions menu, a task's or an effort
  row's menu, the toolbar's and the tray's task menus): one task, the
  selected one or an effort row's; off with several tasks selected,
  and for a task completed or already tracked. The other tracked
  effort ends.
- **Stop or resume** (Shift+Ctrl+T; the toolbar's clock button, the
  tray menu): ends the tracked effort; with none tracked, resumes the
  task tracked last, with a new effort.
- **New effort**: one task (in a task view, one selected). The new
  effort starts now with no end, so it is tracked, and the other
  tracked effort ends; it opens in the effort editor.
- **The effort editor**: an effort given no stop (Implicit mode) is
  tracked, and the other tracked effort ends.
- **Copies**: a tracked effort is copied stopped at that moment; the
  copy holds the time spent so far.
- One rule behind all of them: when an effort of the open file starts
  being tracked, the file's other tracked efforts end
  (`TaskFile.__on_tracking_changed()`), in the same undo step. A file
  that an older release saved with several tracked efforts opens with
  them, also when a view or an editor shows one of them; Stop ends
  the tracked ones selected, or all of them when no selected one is
  tracked.
- **Idle time:** after a time away, Task Coach asks what to do with
  the tracked effort ([IDLE.md](IDLE.md)).

## Tracking Several Tasks: Other Applications

For reference, if tracking several tasks at once is wanted later
(researched 2026-10-04):

| Application | Several at once | How |
|---|---|---|
| Toggl Track | no | starting a timer stops the running one ([Toggl](https://twitter.com/toggltrack/status/591226151307186176?lang=en)) |
| Clockify | no (one per workspace) | overlapping entries added by hand ([forum](https://forum.clockify.me/t/simultaneous-task/241)) |
| TMetric | no | "at any moment, you're working on one task, not two" ([help](https://tmetric.com/help/time-tracking/time-tracking-faq/can-i-have-two-active-timers-at-the-same-time)) |
| Harvest | no | starting a timer stops the one running that day ([help](https://support.getharvest.com/hc/en-us/articles/46293697226381-Harvest-MCP)) |
| Timewarrior | no | `timew start` with other tags ends the current interval ([tutorial](https://timewarrior.net/tutorial/enhanced/)) |
| Kimai | a setting, default 1 | "Permitted number of simultaneously running time entries": 1 stops the running entry when one starts; more allows up to that number, after which one must be stopped, and the clock becomes a list ([docs](https://www.kimai.org/documentation/1.14/timesheet.html)) |
| Tyme (macOS) | a setting | "Simultaneous or single timers" ([features](https://www.tyme-app.com/en/all-features/)) |
| Task Coach before 2.0.3.1 | partly | tasks selected together were tracked together; New effort added one without ending the others, as the old project wiki advised ([wiki](https://sourceforge.net/p/taskcoach/wiki/tracking-effort/)) |

Kimai's model would fit: a preference for how many tasks may be
tracked, 1 by default; Start adds the selected task while under the
limit; Stop and Resume act on the selection; Resume brings back the
tasks stopped together.

## Code

- Domain: `domain/effort/` (`Effort`, `EffortList`, the aggregator
  per day, week and month).
- Views: `gui/viewer/effort.py` (`EffortViewer`,
  `EffortViewerForSelectedTasks`); the editor's tab:
  `LocalEffortViewer` and `EffortPage` (`gui/dialog/editor.py`).
- The category filter: `FilterableViewerForCategorizablesMixin`
  (`gui/viewer/mixin.py`), skipped when `is_filterable()` is false.
- Tracking: `EffortStart`, `EffortStartForEffort`, `EffortStop`,
  `EffortNew` (`gui/uicommand/uicommand.py`); `StartEffortCommand`,
  `StopEffortCommand` (`command/taskCommands.py`); the one-task rule:
  `TaskFile.__on_tracking_changed()` (`persistence/taskfile.py`).
- Tests: `EffortViewerTest.py` (`EffortViewsUnderCategoryFilterTest`),
  `UICommandTest.py` (`EffortStopTest`, `TrackingOneTaskTest`),
  `TaskFileTest.py` (`OneTrackedTaskTest`), `EffortTest.py`
  (`TrackedEffortCopyTest`).

## History

- 2005, release 0.23 (cc9d59fbc, Frank Niessink): one set of active
  tasks with one start time; Start tracking set it to the selected
  tasks, and Stop gave each an effort for the shared period: one
  activity, booked to the tasks selected for it. Release 0.24
  (c15719a38) gave each task its own open effort, so tracking survives
  a restart ("The tracking status of tasks is saved"); Start kept
  replacing what is tracked, hence several tasks started together, not
  one added later.
- 2008-10-30 (5878ff199, Frank Niessink): the editor's Effort tab
  shows the edited task's efforts, not all.
- 2008-11-23 (0856cac0e, Frank Niessink): the editor's notes are not
  filtered by category, its code saying "Inside the editor, all notes
  should be shown"; `BaseNoteViewer` has no filter, `NoteViewer` adds
  it.
- 2011-02-09, release 1.2.10 (3bd519e76, Frank Niessink): "Efforts are
  filtered by categories like tasks and notes", added to
  `EffortViewer` itself, so the editor's tab took it too.
- 2011-02-12 (28cda14d8, Frank Niessink): Stop resumes the last
  tracked task when nothing is tracked; "Stop tracking multiple tasks"
  names the case of several tracked.
- 2014-05-24 (9a307d550, Jérôme Laheurte): "Effort for one task"
  becomes Effort for selected task(s).
- 2026-10-04: the editor's tab without the category filter (#157);
  one task tracked at a time (#40).
