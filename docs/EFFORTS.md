# Efforts

The time spent on tasks: what an effort is, the views that show
efforts, what they filter, and how tracking starts and stops. Editing
an effort's period and its entry modes:
[DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md#edit-effort-window).

## Table of Contents

1. [To Do](#to-do)
2. [What an Effort Is](#what-an-effort-is)
3. [Views](#views)
4. [Filters](#filters)
5. [Tracking](#tracking)
6. [Code](#code)
7. [History](#history)

---

## To Do

Nothing to do.

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

Added up, a row is one task's time in the period. A parent task whose
time in the period is all its subtasks' has a row only while the
"Total time spent" or "Total revenue" column is shown: that is where
such a row has a value. Without them it would be an empty copy of its
subtask's row.

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

Several tasks track at once, **ruled by designer 2026-11-27**, in
place of one task at a time (ruled 2026-10-04): starting a task never
ends another, and Stop is two commands, Stop all and Stop selected.
The one Stop before stopped the selection when it held a tracked
task, else all, else resumed; the designer's words: "that is an
action with too many conditions and will confuse users ... split as a
stop-all and stop-selected, and we will clearly separate these
action".

- **Start tracking** (Ctrl+T; the Actions menu, a task's or an effort
  row's menu, a view's toolbar): one task, the selected one or an
  effort row's; off with several tasks selected, and for a task
  completed or already tracked. The main toolbar's and the tray's
  task menus start the task picked. The tracked tasks go on; a task
  tracked already is not started again, or the same time would count
  twice. A view's Start button greys out as soon as the selected task
  is tracked and comes back as soon as it stops, however it was
  started or stopped ([MENUS.md](MENUS.md#migrated-commands)).
- **Stop tracking all** (Shift+Ctrl+T; the main toolbar's clock
  button, the Actions menu, the tray): ends every tracked effort, all
  at one moment. With none tracked it is **Resume tracking *task***
  (or "multiple tasks"): it tracks again, with new efforts, the tasks
  whose efforts end latest, at the same second, as one Stop ends
  them (`EffortList.tasks_to_resume()`); the tray's line leaves
  completed tasks out, as it did.
  Nothing is remembered, so a past effort typed in to end later, or
  one ending in the future, decides what is resumed. Its toolbar
  button is pressed in while tracking. Its menu line stays as
  released, **ruled by designer 2026-11-27** ("These things should
  not be changing"): on Linux a check box, ticked on Resume; on
  Windows and macOS the check state picks its stop or resume icon
  (`UICommand.add_bitmap_to_menu_item()`).
- **Stop tracking selected** (a view's toolbar, a task's and an effort
  row's menus): ends only the tracked efforts of
  the selected rows: a task's own, an effort, or those a row of an
  effort view adds up per period; off when none is tracked. It never
  stops all and never resumes: Start is beside it.
- **A reminder's clock button** stops or starts its own task.
- **New effort**: one task (in a task view, one selected). The new
  effort starts now with no end, so it is tracked; it opens in the
  effort editor.
- **The effort editor**: an effort given no stop (Implicit mode) is
  tracked.
- **Copies**: a tracked effort is copied stopped at that moment; the
  copy holds the time spent so far, as tracked it would count the
  same time twice.
- **Idle time:** after a time away, Task Coach asks what to do with
  each tracked effort ([IDLE.md](IDLE.md)).

A button's tooltip and its status-bar text follow its menu text:
"Stop tracking all" and "Stop tracking effort for all tracked tasks";
"Stop tracking selected" and "Stop tracking effort for the selected
tasks". Saved toolbars find a button by its command's name
(`ToolBar._filter_commands()`): Stop selected keeps the views'
`EffortStop`, and the main toolbar's saved `EffortStop` becomes
`EffortStopAll` when the settings load (`settings._upgraded()`).

## Tracking Several Tasks: Other Applications

Researched 2026-10-04, before tracking several tasks was asked:

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

Task Coach tracks any number, with no limit to set, and its Stop all
and Stop selected are two commands ([Tracking](#tracking)).

## Code

- Domain: `domain/effort/` (`Effort`, `EffortList`, the aggregator
  per day, week and month, `ParentRowFilter`).
- Views: `gui/viewer/effort.py` (`EffortViewer`,
  `EffortViewerForSelectedTasks`); the editor's tab:
  `LocalEffortViewer` and `EffortPage` (`gui/dialog/editor.py`).
- The category filter: `FilterableViewerForCategorizablesMixin`
  (`gui/viewer/mixin.py`), skipped when `is_filterable()` is false.
- Tracking: `EffortStart`, `EffortStartForEffort`, `EffortStop` (Stop
  selected), `EffortStopAll`, `EffortNew`
  (`gui/uicommand/uicommand.py`); `StartEffortCommand`,
  `StopEffortCommand`, and `EffortCommand.stop_tracking()` for the
  commands that end tracking (`command/taskCommands.py`); what Resume
  tracks: `EffortList.tasks_to_resume()`; the tray's lines:
  `AppIndicatorTaskBarIcon._stop_or_resume_lines()`.
- Tests: `EffortViewerTest.py` (`EffortViewsUnderCategoryFilterTest`,
  `ParentRowsTestMixin`, `test_stop_effort_tracking`),
  `UICommandTest.py` (`EffortStopAllTest`, `EffortStopSelectedTest`,
  `TrackingSeveralTasksTest`), `TaskFileTest.py`
  (`SeveralTrackedTasksTest`), `EffortListTest.py` (resume),
  `EffortTest.py` (`TrackedEffortCopyTest`), `TaskBarIconTest.py`
  (the tray's Stop all and Resume), `ReminderDialogTest.py`.

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
- 2010-11-20 (3d7137f8e, Frank Niessink): "Also show tasks that only
  have recursive effort in the effort viewer", for the total columns
  brought back the day before (23d251f39).
- 2011-02-09, release 1.2.10 (3bd519e76, Frank Niessink): "Efforts are
  filtered by categories like tasks and notes", added to
  `EffortViewer` itself, so the editor's tab took it too.
- 2011-02-12 (28cda14d8, Frank Niessink): Stop resumes the last
  tracked task when nothing is tracked; "Stop tracking multiple tasks"
  names the case of several tracked.
- 2013-02-24, release 1.3.25 (98fc8ea89, Jérôme Laheurte): "Make
  the effort stop menu a bit more contextual": Stop ends the selected
  tracked efforts, or all when none selected is tracked.
- 2014-05-24 (9a307d550, Jérôme Laheurte): "Effort for one task"
  becomes Effort for selected task(s).
- 2026-10-04: the editor's tab without the category filter (#157);
  one task tracked at a time (#40).
- 2026-11-08: a parent task with only its subtasks' time has a row
  only while a total column is shown.
- 2026-11-27, release 2.0.3.12: several tasks tracked at once; Stop
  all and Stop selected; Resume tracks the tasks stopped together.
