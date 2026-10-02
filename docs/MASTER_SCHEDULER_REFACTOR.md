# Master Scheduler Refactor

Plan to replace the full scan `MasterScheduler` runs every second.
[SCHEDULERS.md](SCHEDULERS.md) describes the scheduler as it is.

**Status:** every item done or decided but 42 and 43, 2026-09-30
([Cost After](#cost-after)); what is left: [To Do](#to-do).

## To Do

The one list for this refactor, numbered in the order found; an item
is crossed out and cut to a stub when done or decided, and new items
go at the end. Details live in the sections and documents linked.

1. ~~Whole seconds everywhere: done, only logs keep fractions.~~
   [Time Resolution](#time-resolution)
2. ~~One "not set" for every task date: done, the latest date; a
   running effort's missing stop stays `None`, outside the list.~~
   [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#dates-not-set-is-the-latest-date)
3. ~~No event for an unchanged value: done (`Attribute.set()`), a
   quarter of the tick.~~ [Cost Before](#cost-before)
4. ~~Task dates and reminder on the Publisher, the reminder an
   `Attribute`: done.~~ [Why Nothing Is Missed](#why-nothing-is-missed)
5. ~~The master timer list: done, a heap, the check each second, the
   full loop at its entries, the check mode
   (`TASKCOACH_SCHEDULER_CHECK=1`).~~ [Cost After](#cost-after)
6. ~~Changes the loop reads push the current second, parents first:
   done.~~ [Data Changes](#data-changes)
7. ~~One status: done, styles and status bar counts read
   `computedStatus()`.~~ [TASK_STATUS.md](TASK_STATUS.md#migration-path)
8. ~~SyncML leftovers (sync status flags): removed.~~
   [PYTHON3_MIGRATION_4.md](PYTHON3_MIGRATION_4.md#backwards-compatibility)
9. ~~Merging ignored the actual start: done, then moot (item 13).~~
10. ~~Reminder windows when a file opens: decided, no change.~~
    [REMINDERS.md](REMINDERS.md#overview)
11. ~~UI thread busy while statuses change: done, computed values mark
    nothing unsaved and a save no longer reads the file (98% to
    11%).~~ [Cost After](#cost-after)
12. ~~Modification date on every stored change: done.~~
    [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)
13. ~~Merging: done, no automatic merge; File > Merge a union by newest
    copy.~~ [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)
14. ~~Unsaved mark from saved data only: done.~~
15. ~~A file changed on disk: done, never replaced unasked.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#saving)
16. ~~Undo back to the saved state clears the unsaved mark: done.~~
    [UNDO_REDO.md](UNDO_REDO.md#persistence)
17. ~~View state and category ownership: decided, filter and expanded
    state set no date, the task owns its categories.~~
    [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)
18. ~~Every signal on the Publisher: done, pypubsub removed.~~
    [PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#migration-log)
19. ~~The loop's hook lists what the loop reads: done.~~
    [Data Changes](#data-changes)
20. ~~Attachments re-sorted: done.~~
21. ~~A timing-dependent `EffortViewerTest` case: done.~~
22. ~~Merge ran the parent rules: done.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)
23. ~~`.delta` files: decided, ignored.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)
24. ~~The effort list took a merged file's efforts: done, it compares
    identity.~~
25. ~~Status bar counts ignored the clock: done.~~
26. ~~Object identity: decided, one object per ID within a file, the
    file to merge held apart.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)
27. ~~Recursive priority in the loop: decided, no; by events, as it
    always did.~~
    [TASK_FIELDS.md](TASK_FIELDS.md#priority)
28. ~~Recurrence changes reached only the subtask: done.~~
    [TASK_FIELDS.md](TASK_FIELDS.md#subtree-values-in-other-columns)
29. ~~Duplicate IDs in a file: done, corrected when read, with a
    message.~~ [PERSISTENCE_XML.md](PERSISTENCE_XML.md#duplicate-ids)
30. ~~Cut and paste changed identity: done, the first paste after a cut
    is a move.~~ [PERSISTENCE_XML.md](PERSISTENCE_XML.md#ids)
31. ~~IDs carried the network (MAC) address: done, random UUIDs.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#ids)
32. ~~The unused file GUID: removed.~~
33. ~~Version: 2.0.3.0; file version 38 (to do 60).~~
34. ~~One undo log: done, snapshots of the stored data compared
    before and after each user action; the per-command undo code
    removed.~~ [UNDO_REDO.md](UNDO_REDO.md#architecture-snapshot-and-diff)
35. ~~The views on the effective styles, the legacy styles removed~~
    ([Views on the Effective Styles](#views-on-the-effective-styles)).
36. ~~Pages drawn over the editor's tabs~~
    ([AUI.md](AUI.md#page-painted-over-the-tabs)).
37. ~~Base and effective fields beside the 14 core fields~~:
    postponed, not load-bearing for this refactor
    ([TASK_FIELDS.md](TASK_FIELDS.md#postponed-base-and-effective-fields)).
38. ~~`Timestamp.now()` always later than the one before~~: removed,
    it returned made-up times; the dates are the clock's
    ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#ids)).
39. ~~Renames deferred as too wide~~: done, the task date setters,
    `set_parent()` and `set_task()` ([PEP8_MIGRATION.md](PEP8_MIGRATION.md)).
40. ~~Signal cleanup~~: subscriptions end with their window, toolbar,
    menu or editor page; the guards that became unreachable are gone,
    the others guard delayed calls and destruction
    ([PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#signaling-system-cleanup)).
41. ~~Editor text fields save on leaving the field~~: by design, not
    an issue ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#todo)).
42. The designer's desktop test of the branch, from one consolidated
    test list.
43. Squash to one commit when the designer says the pull request is
    ready (pushes before that keep the full history), version 2.0.3.0
    in the body; the release date (2026-09-28) may move.
44. ~~A traceback lost on 2026-09-28~~: both candidates fixed, the
    spell check's timer (53) and the date popup (P12); reopen if it
    shows again.
45. ~~Incremental pass~~: built 2026-09-30, **the designer's go-ahead**
    with the recommended answers: a tick processes only what changed
    and what reads it, each object once, a cascade in one pass
    ([Incremental Pass](#incremental-pass)).
46. ~~Status-first sort re-sorts on the clock's status changes~~: once
    after the loop's pass ([TASK_STATUS_SORT.md](TASK_STATUS_SORT.md#re-sorting)).
47. ~~Effort viewer's Task and Categories columns refresh~~.
48. ~~Decimal time applies at once~~ (`settings2.changed`).
49. ~~Calendar week start and gradient apply at once~~; the gradient
    drawer failed to paint under wxPython 4 and is fixed.
50. ~~Effort rows and period totals refresh on a stop change~~: they
    did not, on master either.
51. ~~Empty event type~~: gone, and `removeObserver()` reads only None
    as "any".
52. ~~Priority as it was~~: the effective priority of 2026-09-28
    undone, with 37 ([TASK_FIELDS.md](TASK_FIELDS.md#priority)).
53. ~~Deferred calls that can outlive their window~~: all through
    `patterns.later` ([DEFERRED_CALLS.md](DEFERRED_CALLS.md)).
54. ~~Lazy teardown~~: nothing stopped on close or quit; the timers
    freed after the event loop
    ([DEFERRED_CALLS.md](DEFERRED_CALLS.md#end-of-life)).
55. ~~Renames deferred as too wide~~: moved to
    [Deferred or Will Not Do](#deferred-or-will-not-do), D1.
56. ~~The macOS editor poll~~: removed 2026-09-29, **ruled by
    designer**. Its cause (Task Coach bug 1438, 2013): wxPython 2.8's
    Carbon port sent a synthetic Cancel that hid a background editor
    without a close event; that code left wxWidgets in 3.1, and Escape
    now closes an editor through `Close()` on every port. To check on
    a Mac: two editors, Escape twice, both close and save.
57. ~~The master timer list keeps stale seconds~~: done 2026-09-30,
    with 45: entries carry their task and rule and are replaced when
    its dates change; a date not set has none
    ([Stale Entries](#stale-entries)).
58. ~~Plural icons~~: removed 2026-09-29, **ruled by designer**
    ([ICON_LIBRARY.md](ICON_LIBRARY.md#removed-plural-icons), why):
    every view shows the effective icon as is; a task with subtasks
    shows its status icon, the folders stay as regular icons. One
    themed status icon, `TaskStatus.icon_id()`, replaces
    `getBitmap()`, which read the light theme's icons only.
59. ~~Wrappers left by P29~~: removed 2026-09-29, **asked by
    designer**: the tests link from the items, the empty
    `CategorizableContainer` is gone, and the category side is named
    for what it is: `Category.members()`, `member_added_event_type()`,
    `member_removed_event_type()`, the `members` argument of a copy.
    "Categorizable" names the items that can have categories.
60. ~~Category membership stored on the items in the file too~~:
    done 2026-09-29, **asked by designer**; tskversion 38, older
    files converted when read
    ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#category-membership)).
61. ~~One list of defaults for the writer and the reader~~: done
    2026-09-29, **ruled by designer**: a missing attribute is the
    default, every value written was ruled out
    ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#defaults)).
62. ~~Undo design point 4, what is not a step~~: **ruled by designer
    2026-09-30**: the program's own changes and view state, never undo
    steps in any release, stay out; so does the clipboard, although
    every release had it in undo (Copy a step, undoing a Cut restoring
    the old clipboard) ([UNDO_REDO.md](UNDO_REDO.md#design-intent)).
63. ~~Cleanup audit~~: done 2026-09-30, **asked by designer**: the
    vendored `ntlm`, the old `patches/wxpython/` copy and four unused
    tools removed; the `getargspec`, font and total-seconds shims
    replaced; dead code, Python 2 leftovers and unread settings gone
    (dropped from old INI files on load); the stale tests rewritten or,
    for removed features, deleted; the docs brought up to date.
    Decisions made 2026-09-30: P45, P46, P48, P49 done; P47, P50, P51
    deferred (D5 to D7); P43 done with 64.
64. ~~Window options "Start with the main window iconized", "Hide main
    window when iconized" and "Minimize main window when closed"~~:
    removed 2026-09-30, **ruled by designer**: Task Coach is worked in
    on screen, start iconized had not worked since December 2025
    without a complaint, and the window's Close quits, Minimize
    minimizes ([SYSTEM_TRAY.md](SYSTEM_TRAY.md#minimize-and-hide)).
    The keys are dropped from old INI files on load.
65. ~~The test catalog, certified for one platform~~: done 2026-09-30,
    **asked by designer**: `tests/test.py` runs every test file in its
    own process, after checking the versions it is certified on (it
    stops on any other); tests for one platform only will form that
    platform's part of the catalog when work is done there
    ([TESTING.md](TESTING.md)).
66. ~~Files this branch saves open in the released versions~~: done
    2026-10-01, **asked by designer**: expand and contract with two
    numbers in the file, `tskversion` 37 (needed) and `tskformat` 38
    (written); files saved as 38 only are healed on open; checked
    against 2.0.2.0 and 2.0.2.25
    ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#versions-and-compatibility)).
    Retiring the old forms: D9.
    The designer, verbatim: "Additionally, I have a slight problem with
    the prior work that we did in changing the file version. So what
    happens now is that if someone opens their file with the newest
    version of TaskCoach, they can't go back. So if uh, there's a bug
    in the newer version, then if they open it in older version, it
    doesn't work. Is there a way where we can keep the changes uh,
    duplicating data so that it still works in prior versions. I'm
    thinking of the way that the categorizable or the categories are
    stored. Maybe that needs to be saved as a dual, uh, only on save,
    but for legacy reasons, especially during the transition. So I
    just tried opening the Task Coach now on with my current version.
    That's from the main, that's the released, publicly released
    version, and it can no longer open my files. And this is a
    problem."
67. ~~Bring the bundled tree widget up to date (option C of P118)~~:
    done 2026-10-01, **asked by designer**: wxPython 4.3.1's pair with
    Task Coach's changes redone, merged against 4.3.1's selection set
    and per-row caches. After the designer's desktop test, a second
    check found a scrollbar left at the old range when a column was
    hidden (4.3.1 sets it while painting, which GTK does not show),
    fixed. In the app every step of the bundle's checks matches the
    previous bundle screen for screen, the cursor included, in a light
    and a dark theme and with 2,050 tasks, but for upstream's fixed
    type-ahead; the catalog passes. Not run on Windows, macOS or
    wxPython 4.0.7
    ([BUNDLED_TREE_WIDGET.md](BUNDLED_TREE_WIDGET.md#updating-the-bundle)).
68. ~~A Preferences option for editing in place with a slow double
    click~~: done 2026-10-02, **asked by designer**: "only a slow
    double click within specific timing parameters will open the edit.
    If not, it will be the F2 or the right click", the right-click
    item greyed on a cell that cannot be edited, F2 "only ... if we
    have a selection of a cell that's currently active" in the focused
    list, and editing leaves only its row selected. A slow double
    click is a second click on the same cell from the double-click
    time (400 ms here) to 2 s after the first, with nothing between;
    the edit box opens a double-click time later unless a third click
    makes a double click. Before (master too), a click on the row
    clicked last, however long ago, opened one after 250 ms, and F2
    edited the first selected row's subject. No Edit menu item: the
    list shows no current cell
    ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#in-place-editing),
    [SETTINGS.md](SETTINGS.md#in-place-editing-options)). Checked in
    the app, both options on: a second click 1 s later edits, 3 s
    later or after a click in Categories does not; F2 after a click on
    the subject or the planned start edits that cell, after the Down
    key nothing; the right-click item edits a subject (beside its text
    too), is greyed on an icon column, and leaves one of two selected
    rows selected; both off: no edit box and no menu item.
69. ~~A Preferences option to turn editing in place off
    altogether~~: done 2026-10-02, **asked by designer**: "Edit cells
    in place", off by default for everyone, upgrades included (the
    designer's lean; for the release notes): F2, the right-click item
    and the slow double click then do nothing. The designer, verbatim:
    "I don't use list editing ever but some people do because it goes
    faster I find it's less reliable".
70. One settings object, read directly (was P102). **Asked by
    designer 2026-10-02**: "There's supposed to be one global settings
    object ... I was creating a virtual layer over it ... we should
    make a new task to completely refactor this." Done first: no
    module but the application makes a `Settings` object (P152).
    Left: move the reads that take the object through constructors to
    `settings2`, replace `ConfigParser`, refine the refresh triggers,
    and stop viewer instance 0 sharing the template section
    ([SETTINGS.md](SETTINGS.md#todo) 1, 5, 7, 8).
71. ~~The Publisher cleans up after itself (was P153)~~: done
    2026-10-02, **asked by designer**. It held a subscription's
    source strongly and dropped a freed subscriber only when an event
    of its type and source came: an object subscribed to its own
    events stayed (P151). It now holds sources weakly too and drops a
    subscription at its next call once its source or subscriber is
    freed; sources that compare equal still share their subscriptions,
    as domain objects compare by id
    ([PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#current-state)). In
    the whole test catalog no event matched a subscription by equality
    alone. Checked in the app: marking 2,050 tasks completed costs the
    same (CPU median 2.48 s, 2.49 s before, five runs each); over 20
    editors the registry stays at 625 subscriptions, where before dead
    ones piled up (438 to 647); editors, Preferences, floating, docked
    again, tabs, quit and relaunch: no traceback.
72. ~~A held key opens a pile of editor windows~~: done 2026-10-02,
    **ruled by designer**: a command opens the same window at most
    once a second, and the keys are left as they are
    ([MENUS.md](MENUS.md#the-same-window-once-a-second), with the
    reason). Holding Enter or Space on a task, or presses queued while
    the system is busy, opened one editor per press (master too);
    under heavy load hundreds. A filter dropping a held key's repeats
    was prototyped and set aside: the designer chose not to touch the
    key stream, so a held key's characters still reach the editor
    that opens (Space replaces the selected subject). wx tells no
    repeat from a press on GTK (`IsAutoRepeat()` works on Windows,
    macOS and Qt only), so the rule does without one. Checked in the
    app: Enter held 2 s while the application was paused opened 14
    editors of one task, now one or two; Enter on two tasks within
    half a second opens both; three double-clicks on one row within a
    second open one editor, one more 4.5 s later a second.

## Deferred or Will Not Do

Moved out of the To Do list, **ruled by designer 2026-09-29**: pushed
beyond this refactor or not done, and not reported as outstanding.
Numbered D1, D2, ...

- D1. Renames too wide for this refactor, from the PEP 8 review of
  2026-09-29 ([PEP8_MIGRATION.md](PEP8_MIGRATION.md)): the domain and
  viewer methods the branch rewrote (`addChild`, `removeChild`,
  `computedStatus`, `processReminder`, the viewers' `onSelect`,
  `createWidget`, `_createColumns` and `subjectImageIndices`, the
  Publisher's `registerObserver` and `removeObserver`); keyword
  families: `taskList` and `effortList`, the export's `cssFilename`
  and `selectionOnly`. The date and time widgets' arguments were
  renamed 2026-09-30, in the audit the designer asked for.
- D2. The GTK warning at every launch
  (`gtk_distribute_natural_allocation: assertion 'extra_space >= 0'
  failed`), **ruled by designer 2026-09-29**: it comes from inside
  GTK at the main window's first show, with no Python code on the
  stack (traced under gdb with `G_DEBUG=fatal-criticals`); left in the
  logs as is.
- D3. Attachment styling, **ruled by designer 2026-09-29**: deferred,
  not in this release. Attachments keep drawing only their own style,
  as on master ([APPEARANCE_STYLES.md](APPEARANCE_STYLES.md#todo)).
- D4. One base class for the two tray icons, **ruled by designer
  2026-09-29**: will not be done; the classes are different by
  design ([SYSTEM_TRAY.md](SYSTEM_TRAY.md#code-duplication)).
- D5. `thirdparty/plasma_window_management` on KDE Plasma Wayland
  (was P47), **ruled by designer 2026-09-30**: deferred, for users on
  that desktop to test. KWin may offer its global only to a client
  whose `.desktop` file lists it in `X-KDE-Wayland-Interfaces`, which
  ours does not ([SYSTEM_TRAY.md](SYSTEM_TRAY.md)); without it the tray
  falls back to hide and show.
- D6. `workarounds/display.py`, the `wx.Display` replacement on
  Windows for monitors plugged in or out (was P50), **ruled by
  designer 2026-09-30**: deferred, for Windows users to test whether
  wxWidgets 3.1+ makes it unneeded.
- D7. ~~The wxPython 2.8 workarounds still running~~ (was P51):
  removed 2026-10-01, **ruled by designer**, once the wxWidgets source
  of every version released showed their bugs fixed (3.0.5, oldest on
  Ubuntu 22.04, to 3.3.1 on Windows, macOS and the Flatpak):
  - The checked state read from the menu item (`settings_uicommand.py`,
    `searchctrl.py`): wxMSW 2.8.3 inverted the state it sent after
    toggling the item; every version sends the new state, popup menus
    included. `event.IsChecked()` now.
  - A submenu's entry found by label (`gui/menu.py`): wx 2.8.6 on GTK
    compared labels with their shortcuts. The menu now asks for the
    entry whose submenu it is: no label (`FindItem()` would also
    search inside the submenus).
  Checked in the app: the View menu toggles, Rounding greyed out for
  the task list, the column header's menu, the search options.
- D8. What the 2026-09-30 audit found that cannot be tested here (no
  Windows, macOS, Wayland, KDE or Flatpak), deferred by the
  designer's standing rule of 2026-09-30 for users on those platforms:
  the wlroots/COSMIC tray backend and the Background portal
  ([SYSTEM_TRAY.md](SYSTEM_TRAY.md)); the Wayland items of
  [AUI_WAYLAND_ISSUES.md](AUI_WAYLAND_ISSUES.md) (a dock and float
  menu, the switch to `wx.aui`, `GDK_BACKEND=x11`); popups placed by
  the compositor on Wayland (DATETIME_CONTROLS.md says built, it was
  not: `_PopupWindow` is always a `wx.Dialog`); idle without pywayland
  on Wayland ([IDLE.md](IDLE.md)); macOS sleep and wake (a no-op),
  signing and notarization, Tahoe, Intel builds
  ([MACOS.md](MACOS.md)); the macOS mailto and notifier-focus TODOs;
  the Windows and macOS Python 3.11 builds; the wxPython 4.2.0 floor
  against Ubuntu 22.04's 4.0.7 (wxWidgets 3.0.5; PACKAGING.md said 4.1.1); the Flatpak's network and Secret
  portal; the icon picker on Windows and macOS.
- D9. Retire the forms written for releases reading `tskversion` 37
  (`persistence/xml/legacy.py`), **asked by designer 2026-10-01**: in
  place since 2.0.3.0, 2026-10-01; review between January and April
  2027 ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#to-do-retire-the-old-forms)).
- D10. The Task statistics view keeps most of a core busy while open
  (P146), **deferred by designer 2026-10-01** ("I don't use it. I
  don't know anyone that uses it. No one's complained"). Found: wx's
  pie chart refreshes its legend on every paint (`PieCtrl.Draw()`,
  `RecreateBackground()`, `Refresh()`), and on GTK 3 that repaints the
  pie, about 100 times a second; master too. Tried in a scratch copy,
  not kept: the view turning that refresh off (its legend is opaque)
  and refreshing the legend when the counts change: idle 0%, the pie
  and legend unchanged, the legend following a change.
- D11. The colours in a dark theme (P142), **ruled by designer
  2026-10-01**: the dark theme was tuned by the people who use it; no
  change to it unless the designer asks for one ("If there's issues, I
  will specifically tell you what to do with dark theme").
- D12. The reminder sound's player process (P135), **deferred by
  designer 2026-10-02**: `paplay` or `afplay` is started and Task
  Coach drops its process object while it plays
  (`sounds/__init__.py`); Python warns "subprocess is still running"
  only with developer warnings on, and the sound plays. Keeping the
  object until the player ends would silence it.

## Pre-existing Issues

Optional, **requested by designer 2026-09-29**: problems present
before this refactor (on master, or failing in the baseline test run),
found along the way. Fixing them helps stabilize this work; none is
required. Numbered apart from the To Do list, crossed out when fixed.

Test files failing in the baseline run (28 tests before this
refactor; unchanged by its steps, crossed out when fixed):

- P1 to P4. ~~The integration tests (`SaveTest.py`, `LoadTest.py`,
  `ModelAndViewerTest.py`, `LeakTest.py`, `PerformanceTest.py`, 10
  errors)~~: fixed 2026-09-29. Their mock application had fallen
  behind: it now gets its settings before `init()` and its own
  translator, as the application does, and quitting skips idle
  processing when no event loop runs. The tests also remove the lock
  files they leave.
- P5. ~~`unittests/AppTest.py`: 2 failures (language from the
  locale)~~: fixed 2026-09-29, the tests only. The app reads `LANG`
  first, so the tests took the machine's language; they now set it.
- P6. ~~`unittests/commandTests/CutCopyPasteTest.py`: paste (1 error,
  1 failure)~~: fixed 2026-09-29, the tests only. A note cut by one
  test stayed on the shared clipboard for the next (every command
  test now clears it); the effort paste passed the task list as the
  destination, which the task viewer never does.
- P7. ~~`unittests/domainTests/EffortTest.py`: 4 failures (duration
  and revenue events on a start or stop change)~~: fixed 2026-09-29,
  the tests only. An effort's duration is stored and recalculated by
  the editor's entry mode
  ([DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md#edit-effort-window)),
  so a start or stop change sends the start or stop and the task's
  time spent; the effort viewer refreshes the row on them.
- P8. ~~`unittests/domainTests/TaskTest.py`: 3 failures (budget left
  events without a budget)~~: fixed 2026-09-29, the tests only. Since
  January 2026 (#334) budget left is the budget less the time spent
  with or without a budget ([TASK_FIELDS.md](TASK_FIELDS.md)); the
  tests expected 0 without one.
- P9. ~~`unittests/domainTests/SorterTest.py`: 2 failures (tree mode
  delegation)~~: fixed 2026-09-29, the tests only. Since master's
  March 2026 change a sorter passes its tree mode to its filter, as
  in the app; the tests' stand-in was a plain task list.
- P10. ~~`unittests/widgetTests/WindowDimensionsTrackerTest.py`: 2
  failures (size, move)~~: fixed by master's window geometry work,
  merged 2026-09-29.
- P11. ~~`unittests/guiTests/MainWindowTest.py`: 1 failure~~: fixed
  2026-09-29 with the merge, the test only: the maximize comes once
  the placement is quiet; it is skipped without a window manager to
  grant the maximize.
  ~~`thirdPartySoftwareTests/wxPythonTest.py`~~: fixed 2026-09-29,
  the test only: since wxWidgets 3.2, GTK also sends no text event
  when an empty text control is cleared.
  ~~`widgetTests/DragAndDropTest.py`~~: fixed 2026-09-29, the test
  only: its tree showed its root, which a tree selects by itself, so
  a drag took the root; the app's trees hide it.

In the app:

- P12. ~~Closing an editor after using a date popup logs a
  RuntimeError~~: fixed 2026-09-29, 3 times of 3 before, 0 of 4
  after. GTK sends one more text event while the control is
  destroyed; the handler exits when its control is gone.
- P13. ~~The calendar's month view fails under wxPython 4~~: fixed
  2026-09-29. With a calendar saved in month view the app did not
  start; `wx.DateTime.GetNumberOfDays()` replaces the removed call,
  with the date's year (the old calls used the current year's
  February), an unused one is dropped, and a header bound is appended
  as one tuple.
- P14. ~~A zero-size calendar pane assertion at startup~~: closed
  2026-09-29, **ruled by designer**: not reproduced in any run, a
  calendar in month view included.
- P15. ~~A list's tooltip stays shown over an editor opened from
  it~~: fixed 2026-09-29. It hid only when the mouse moved or left
  the list; opening an editor now hides it and drops a pending one.
- P16. ~~The GTK warning at every launch~~: not an issue, moved to
  [Deferred or Will Not Do](#deferred-or-will-not-do), D2.
- P17. ~~Invalid escape sequences in three test files~~: fixed
  2026-09-29, raw strings.
- P18. ~~The dependency graph viewer's size event method outside its
  class~~: fixed 2026-09-29 (not run: igraph is not installed here).
- P19. ~~`languagetests/TranslationIntegrityTest.py` fails to
  load~~: fixed 2026-09-29, the test only. It used the compile step
  the Python 3 migration retired; it now reads the `.po` files as the
  app does ([TRANSLATIONS.md](TRANSLATIONS.md)). All placeholders
  match.
- P20. ~~Belarusian, Danish, Hungarian and Swedish, 99 to 100%
  translated, were disabled~~: enabled 2026-09-29, **ruled by
  designer**; Danish's Preferences code corrected to `da_DK`. A
  string not translated shows in English.
- P21. ~~The language from the environment read `LANG` before
  `LC_ALL`~~: fixed 2026-09-29, **ruled by designer**: POSIX order,
  the first set of `LC_ALL`, `LC_MESSAGES` and `LANG`
  ([LOCALE.md](LOCALE.md)).
- P22. ~~In the task tree, Ctrl+Enter (Mark task completed) opened
  the selected task's editor, as Enter does~~: fixed 2026-09-29; the
  same on master. The tree edits on a plain Enter only.
- P23. ~~In the task editor, pasting several notes added only the
  first~~: fixed 2026-09-29; the same on master. The command paired
  one owner with the notes.
- P24. ~~Opening the open file again (a reload) released its lock
  between the close and the load~~: fixed 2026-09-29; the same on
  master ([FILE_LOCKING.md](FILE_LOCKING.md)).
- P25. ~~The notification centre's 1 s timer ran from its first
  notification on~~: fixed 2026-09-29; the same on master. It ticks
  only while it shows or holds notifications.
- P26. ~~A task file without the taskcoach version raised an
  UnboundLocalError~~: fixed 2026-09-29; the same on master. The
  reader refuses it with a clear error; the empty `PIParser` is gone.
- P27. ~~The tests loaded the icon catalog twice and logged each icon
  as an ID conflict~~: fixed 2026-09-29; the same on master.
- P28. ~~The editor's Check all and Uncheck all categories linked
  only the task's side~~: fixed 2026-09-29; the same on master. The
  file stores the category's side, so the categories were lost on
  save; they were not undoable either. Both now go through one
  command, like a single check.
- P29. ~~Notes lost their categories on save~~: fixed 2026-09-29;
  the same on master. A pasted task's notes, a note pasted in the task
  editor and a note owned by an attachment kept them on their own side
  only; the file was written from the category's side, which paste
  did not fill and the writer's in-file check skipped for
  attachments' notes. **Ruled by designer** (2026-09-29): solved at
  the source, membership stored on the item only (option A). A
  category's members are an index the items keep (`member_joined()`,
  `member_left()`), every item that claims it; one walk,
  `categorizables_in()`, says which are in the file, for the delete
  dialog. A category leaving or entering the file (delete, undo, cut,
  paste) takes its members with it (`leave_file()`, `enter_file()`):
  why the list had stayed stored after to do 17 (commit 8b9d012a7).
  The file stores it on the items too since to do 60. Cleanup: to do
  59.
- P30. ~~The "Cannot Delete - Category In Use" dialog showed a note
  owned by an attachment without its owners~~: fixed 2026-09-29; the
  same on master. It searched only the notes of tasks and categories;
  one walk of the file, `TaskFile.owner_chains()`, now gives every
  owned item's owners: `[Task] Garden -> [Attachment] plan -> [Note]
  Tools`.
- P31. ~~Dropping an e-mail onto a task was broken end to end~~:
  fixed 2026-09-30, **ruled by designer**; the same on master. The
  drop from Thunderbird failed (a Python 2 codec, bytes read as text),
  reading most mails failed, no save worked while the dropped mail's
  temporary copy existed (Python 2 embedding), and once it was gone
  the attachment and its notes vanished on the next open. A dropped
  mail now keeps its subject, sender, sent date and a `mid:` link,
  not the mail ([EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md)).
- P32. ~~A "save changes?" question that took no clicks~~, reported
  by designer 2026-09-29 on the master release, switching files right
  after a change: closed 2026-09-30, not reproduced (2026-09-29, on
  this branch and on master b6c35ab08: a change and a switch through
  File > recent files in one burst of input; autosave saved in between
  and no question showed). Leads if it comes back: the question is a
  modal `wx.MessageBox` asked from the menu command before the current
  file closes (`IOController.open()`); autosave saves at the next idle
  moment; a due reminder opens its window as the file loads.
- P33. ~~Dropping a file from a file manager, or a mail from
  Evolution or Claws Mail, raised an AttributeError on Linux and
  attached nothing~~: fixed 2026-09-30; the same on master. With
  wxPython 4 on GTK a dropped uri-list reaches the file names object,
  never the uri-list object the drop read. Every file drop now takes
  one path, which hands those two programs' mail files to the mail
  drop (`DropTarget.on_file_drop()`).
- P34. ~~Text holding a character XML forbids (a control character
  such as a form feed or NUL, pasted from another program, or a stray
  surrogate) was saved as is, and the file then could not be
  opened~~: fixed 2026-09-30; the same on master. Stored text keeps no
  control character but tab and line breaks, one-line text none
  (ruled by designer 2026-09-30); a file that already holds them opens
  with them dropped
  ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#text)).
- P35. ~~An open editor wrote back what it was shown from elsewhere
  (undo, another window)~~: fixed 2026-09-30; master's editors have
  the same code (not reproduced there). A date field showing minutes
  wrote a reminder with seconds back rounded, and the dates logic ran
  on the change as if the user had made it; after an undo, that write
  was a new step and redo was lost.
  The field compares an edit with what it shows; the logic runs only
  for the user's edit
  ([DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md#preconditions-and-global-logic),
  0.5).
- P36. ~~A date field's change event still pending when its editor
  closed reached the closed editor (`RuntimeError`, its checkbox
  deleted)~~: fixed 2026-09-30. The date control is an event handler,
  not a window, so wx did not drop what it had posted with its
  widgets; it now sends the event through the deferred service, owned
  by its checkbox
  ([DATETIME_CONTROLS.md](DATETIME_CONTROLS.md#datetimecomboctrl-event-ownership)).
- P37. ~~A reminder window stayed open, showing the old time, after its
  reminder was changed elsewhere; closed by a deletion or completion
  elsewhere, it snoozed the task~~: fixed 2026-09-30, **asked by
  designer**: windows self-heal, changing nothing
  ([UNDO_REDO.md](UNDO_REDO.md#windows)).
- P38. ~~The test base disconnected `wx.CallAfter`'s handler after the
  first GUI test of a run, so no deferred call ran in the later ones
  and tests depending on one passed without checking it~~: fixed
  2026-09-30 (`tests/test.py`).
- P39. ~~Showing a column with icons (Attachments, Notes) showed none
  until the tree was rebuilt~~: fixed 2026-09-30; the same on master
  since March 2026 (6f5fae795). The in-place refresh kept the image
  columns of the last rebuild.
- P40. ~~File > Import > CSV failed before its first page~~: fixed
  2026-09-30; the same on master. Its wizard used wxPython 2 calls
  (the grid's selection mode, a two-number sizer, old event binding)
  and Python 2 text handling (the preview decoded text already
  decoded; Python 3's `csv` refuses an empty escape character).
  Checked in the app: the preview shows the rows, "Import only the
  selected rows" imports them (ticking it no longer reloads the
  preview, which cleared the selection), and a date starting with the
  year reads year-month-day even with "DD/MM" chosen (dateutil read
  2026-10-02 as 10 February).
- P41. ~~Reading a Thunderbird IMAP mail gave the keyring bytes, and a
  server offering NTLM raised an error~~: fixed 2026-09-30; the
  vendored `ntlm` could not run on Python 3 and was removed
  ([TODO.md](TODO.md#12-thunderbirdimap-mail-integration-review)).
- P42. ~~Strings translated before the translator existed read `LANG`
  before `LC_ALL`, and the spell check the deprecated
  `getdefaultlocale()`~~: fixed 2026-09-30, one function,
  `i18n.system_language()` ([LOCALE.md](LOCALE.md)).
- P43. ~~"Start with the main window iconized: If it was iconized last
  session", the default, behaved as Never~~: nothing wrote or read
  `window/iconized` since the fork's merge (def3832cf, December 2025);
  it had worked from 2007 (0a18a95db) to release 1.4.6 and upstream's
  Python 3 port. The option was removed 2026-09-30, **ruled by
  designer**, with the hide options (To Do 64).
- P44. ~~The reminder window's tests were skipped on Linux (a crash)
  and the leak test was a docstring~~: fixed 2026-09-30, the tests
  only: asking for attention without a window manager crashes GTK
  (mocked, as in `WindowSelfHealTest`); the file's objects are freed
  after the loop's next pass.
- P45. ~~Upstream's release tooling~~: retired 2026-09-30, **ruled by
  designer** (unused, kept in git history): `legacy/` (Makefile,
  buildbot, release.py), `changes.in/` (its history stopped at
  1.6.1.72), `tests/releasetests/`, `tests/disttests/`, and by the same
  rule `dist.in/`, `build.in/windows/`, `build.in/portableapps/`,
  `build.in/winpenpack/`, `build.in/debian/MANIFEST.in` and the old
  website generator (`website.in/`; its screenshots stay, the Flatpak
  metadata links them).
- P46. ~~The pyparsing minimum, 3.1.3 "for `pp.Tag`"~~: lowered to
  3.0.0 on 2026-09-30, **ruled by designer**: 3.0.0, 3.0.7 (Ubuntu
  22.04), 3.0.9 (Debian 12), 3.1.1 and 3.1.2 pass the template tests
  and parse 21 sample expressions alike. The builds use each distro's
  package instead of bundling it
  ([PACKAGING.md](PACKAGING.md#minimum-version-requirements)).
- P47. Deferred: D5.
- P48. ~~`thirdparty/wxScheduler` without author or licence~~: closed
  2026-09-30, no code change. Its licence was known: the wxWindows
  Library Licence (Daniele Esposti, Michele Petrazzo, Jérôme Laheurte;
  Google Code "wxscheduler" 1.3, 2014, gone since); its readme was
  dropped when the fork unpacked it in 2024 (0751ddfe4) and is back
  (`wxScheduler/README.txt`), as the licence requires. There is no
  upstream or replacement to move to, so it stays as it is, as does
  `timeline` (written for Task Coach, MIT-style). `debian/copyright`
  now lists every vendored package.
- P49. ~~Three preferences that did nothing~~: **ruled by designer
  2026-09-30**: "Icon size" and "Show Breeze icons in picker" stay for
  their planned features. "Check for new version on startup" works
  again, against GitHub: a newer release is shown once, with a link to
  it ([PACKAGING.md](PACKAGING.md#version-check)); checked in the app
  with a copy labelled 2.0.2.25.
- P50. Deferred: D6.
- P51. Deferred: D7.

Found by the audit of 2026-09-30, **asked by designer** (docs, dead
code, vendored code and dependencies, tests and CI); all testable here,
each with the recommended action, none ruled yet:

- P52. ~~Quit still stopped the file watcher, idle polling and the
  scheduler's subscriptions~~: removed 2026-09-30, **asked by
  designer**: closing the file already stops its watcher (both are
  daemon threads), and the per-second tick ends with the main window.
  Checked in the app: closing the window and Ctrl+Q while tracking,
  with either watcher, end in about a second with a clean log.
- P53. ~~Docs stale on the scheduler; a probe that no longer ran~~:
  fixed 2026-09-30, **asked by designer**: TASK_STATUS.md (immediate
  updates, `_compute_task()`, notes' sources, type icons, the
  migration path); `scheduler_diffprobe.py` retired for the unit
  test, with `allItemsSorted()`, which only it used.
- P54. ~~"Undo do something" after changing % complete of several
  tasks~~: fixed 2026-09-30, **asked by designer**; the same on master
  since 2024. `plurar_name` and Copy's `plular_name` were misspelt;
  the label for several tasks is "Change percentage complete", worded
  without a count ([TRANSLATIONS.md](TRANSLATIONS.md#counts)).
- P55. ~~A fee typed in the task list was stored wrong ("12.5" saved as
  0.50)~~: fixed 2026-09-30, **asked by designer**; the same on master.
  The fee columns' in-place editor was the masked `AmountCtrl` (each
  key filled a place of "0.00"); it is `CurrencyCtrl` now, as in the
  task editor, and the masked control is removed. Checked in the app:
  both fee columns store what is typed, Escape cancels, a click
  elsewhere accepts.
- P56. ~~Opening an editor from a cell logged "SetSelection failed" for
  every field that is not a text box~~: fixed 2026-10-01, **asked by
  designer**. One helper, not two copies, focuses the field and
  selects the text of text boxes only; the others select their value
  on focus or hold no text. Nothing changed on screen.
- P57. Norwegian locales get en_GB dates and times
  (`i18n._fixBrokenLocales()`, a wx 2.8 date picker crash of 2012;
  Linux has no such picker). Removing it changes released behaviour.
- P58. ~~`widgets/dialog.py` overrode `SetExtraStyle()` as a no-op~~:
  removed 2026-10-01, **ruled by designer**. Added in 2012 because
  wxPython 2.8's sized dialog turned on recursive validation (7 s to
  open a dialog); its constructor no longer does, and nothing called
  the override (logged while opening Preferences and a task editor).
  Checked in the app: Preferences, a task editor and the templates
  open in 0.1 to 0.4 s.
- P59. ~~Calls Python 3.14 removed or deprecates~~: replaced
  2026-10-01, **ruled by designer**; every replacement exists in every
  Python, pyparsing and wxPython released (Python 3.10, pyparsing
  3.0.7 and wxPython 4.0.7 on Ubuntu 22.04 the oldest).
  - `ast.Num`/`ast.Str`, removed in 3.14 (Arch 3.14.7, Fedora 43): old
    template dates (file format before 32) failed to convert; five
    `XMLReaderTest` tests failed on 3.14 and pass now.
  - `codecs.open()`: `open(..., newline="")` for writing, which keeps
    the iCalendar and CSV exports' own CRLF line ends byte for byte
    (plain text mode would make them CR CR LF on Windows); plain
    `open()` for reading todo.txt.
  - `utcfromtimestamp()`, `sre_constants`, `setDaemon()`, pyparsing's
    `parseString`: their current names. The iCalendar tests compare the
    exported times now (they asserted a string before).
  - `wx.NewId()`: `wx.NewIdRef()`, its reference kept. The wxPython
    wheels (Windows, macOS, the AppImage) free an id with its
    reference; Debian's wx does not track ids (they count down and
    wrap after a million). Checked in the app: menus, toolbar, right
    click and tracking menus, recent searches, the editor's Ctrl+Tab,
    Ctrl+Shift+Tab and Ctrl+E.
  Checked: the whole catalog on 3.13; the affected tests on 3.14 with
  wxPython 4.2.5 and pyparsing 3.3.3 (21 date expressions parse alike
  on pyparsing 3.1.2 and 3.3.3); in the app an invalid regular
  expression search and an iCalendar export (CRLF lines).
- P60. ~~Source tarballs dropped `build.in/debian/` (the appdata
  file)~~: fixed 2026-09-30, **asked by designer**: `/debian/
  export-ignore` excludes only the top-level folder. No build uses
  `git archive` or GitHub's archives: the Arch and RPM workflows tar
  their checkout.
- P61. The run-from-source scripts README points to fail: they check
  the removed `desktop` module, install no pyenchant;
  `test_taskcoach.sh` checks files that do not exist. Fix or retire?
- P62. PyGObject (`python3-gi`) is used (AppIndicator, the first tray
  choice on GTK) but declared in no package. Recommended: declare.
- P63. The translation test's 106 coverage tests read
  `i18n.in/messages.pot`, gitignored and from January (338 strings
  missing); regenerated as TRANSLATIONS.md says, it takes 8,700 icon
  hints and every language fails. Track the template or build it in
  the test, and keep icon hints out?
- P64. ~~Dead code~~: removed 2026-09-30, **asked by designer**: the
  plain-text GPL, `BaseTextCtrl`, `TimeDeltaEntry` (its tests now check
  `TimeDeltaCtrl`, which the in-place editor uses), `date.parseDate`,
  `po2dict`'s compile step, `PIElementTree._write`, the Windows and
  macOS time and date renderers, `Translator.locale_ok`,
  `--skipstart`, 12 calendar accessors, `AbstractNotifier.get()`,
  `workarounds/encodings.py`, `dummy.MainWindow`, about 30 attributes
  written and never read (with `IdleController`'s window argument and
  two unread columns of the iCalendar field tables), and the unused
  `meta/data.py` values with the buildbot `revision` block
  (`MetaDataTest` checks `version_full`). Checked in the app: the
  license, both iCalendar field lists, the templates dialog, a
  reminder and an actual start set in the editor.
- P65. Code only tests use (`Task.dueSoon()`, `CompositeList`,
  `getObjectById`, `Viewer.updateSelection`, `Menu.openMenu` and about
  12 more). Remove with the tests, or keep as test helpers?
- P66. ~~`DurationCtrlVerbose` (130 lines): only the demo uses it~~:
  kept 2026-10-02, **ruled by designer**: a test playground, kept with
  its demo for an option with longer, worded durations if one is ever
  asked for. Its doc section and docstring say so
  ([DATETIME_CONTROLS.md](DATETIME_CONTROLS.md#durationctrlverbose)).
- P67. `[version] python`, `wxpython`, `pythonfrozen`, `current`:
  written to the INI on every save, never read. Keep as diagnostics or
  drop?
- P68. ~~`six`~~: removed 2026-10-01: its last use went with the
  bundled tree widget (P118); no package or setup script declares it
  now, and the startup report no longer lists it.
- P69. Python 2 style in bulk: `# -*- coding` in 29 files, 93
  `object` bases, about 28 2to3 `list()` wrappers, `codecs.open`,
  `UnicodeAwareConfigParser`, metaclass docstrings. Now, or deferred
  like D1?
- P70. Stale code comments: 8 TODO/FIXME/XXX/HACK no longer true
  (`tasklist.py` rename, `autobackup.py` hack, `listctrl.py` font,
  the "-1 column" questions, ...). Recommended: delete or reword.
- P71. Pylint leftovers: `.pylintrc` (pylint 0.x), 746
  `# pylint: disable`, 61 `# pragma: no cover`; no linter or coverage
  uses them. Remove?
- P72. ~~`i18n.in/*.po`: 53 copies left by the move to
  `taskcoachlib/i18n/locales/` (11 MB)~~: removed 2026-09-30, **ruled by
  designer**; #213 copied the files and never deleted these, and the
  three English variants had already drifted. The template's folder is
  made by the command in [TRANSLATIONS.md](TRANSLATIONS.md).
- P73. `icons.in/`: `nuvola.zip` (16 MB), `splash.png`,
  `splash_inno.bmp` unused, shipped by the Windows build, which copies
  the whole directory; `gui/icons/ICON_SOURCES.json` and
  `splash_legacy.png` unused. Recommended: remove; copy only the icon.
- P74. ~~Unused files~~: removed 2026-10-01, **ruled by designer**:
  the root `thirdparty/` (a README pointing elsewhere),
  `TaskCoach.entitlements` (no build signs the app), `tools/dot.py`,
  `tools/nuvola_duplicates.txt` (the output of a script removed in
  February), `docs/proto.rst` (iPhone sync, removed in January), and
  13 `.gitignore` lines for files nothing makes; `.profile` is
  ignored. `PUBLICITY.txt` stays: a contributor keeps it.
- P75. `bugs/`: 4 of the 6 issue notes are closed on GitHub.
  Recommended: open ones into docs, the rest retired.
- P76. `test-screenshots/` (13 MB) and `icon-ideas/` (8 MB) unused but
  the README banner; `website.in/screenshots`: 26 of 28 unlinked (P45
  kept them for the Flatpak metadata, which links 2). Retire?
- P77. Three AppStream files (Debian's legacy one, the Flatpak's, the
  AppImage's inline). Recommended: one metainfo.
- P78. `distro` serves only `setup.py`'s Debian `data_files`, which
  duplicate `debian/rules`. Recommended: remove both.
- P79. `numpy` serves six status-filter icons; it costs a probe at each
  start and pins (`<2` blocks Python 3.13 pip builds). Replace with
  `wx.Image` and drop it?
- P80. Python floor: the code needs 3.10, packaging says 3.8;
  `setup.py` lists 3.8/3.9, `tests_require`, an iOS description and an
  unused Windows branch. Recommended: 3.10, metadata cleaned.
- P81. `watchdog>=3.0.0` has no recorded reason and forces bundling on
  Bookworm and Jammy. Test 2.2.1 and lower it?
- P82. `igraph` is declared nowhere, so the Dependency Graph viewer is
  hidden in every package. Declare it or retire the viewer?
- P83. `dbus-python` (3 call sites) could be Gio, already used.
  Replace?
- P84. Build inputs adrift: `scripts/build-*.sh` differ from CI; the
  spec's `Source0` names a `main` branch; PKGBUILD leftovers; an
  empty `debian/taskcoach.install`; `appimagetool` from AppImageKit.
  Recommended: align.
- P85. No CI job runs the tests. A `debian:trixie` job matches the
  certified platform ([TESTING.md](TESTING.md)). Add it?
- P86. CI install checks cannot fail (`&& echo SUCCESS` under
  `set -e`, `|| true`, PowerShell's last exit code only); 7
  `action-gh-release@v1`, `cache@v4`; `fedora:39`; `checks.yml` on
  Python 3.11, the floor being 3.10. Recommended: fix.
- P87. `AppTest.testAppProperties` skips unless the language is en_US,
  and errors there (with 6 more tests). Recommended: rewrite.
- P88. ~~Tests that checked nothing~~: fixed 2026-10-02, **asked by
  designer**. Four were skipped on GTK, so on the certified platform
  they never ran: the two column header menu tests (the menu waited
  for the user) now patch the popup and check the column the menu
  keeps; the two maximize tests (a test display without a window
  manager grants no maximize) now send the window manager's answer
  and check the saved state. `TreeListCtrlTest.testShowColumn` checks
  the column is back and filled after the refresh the viewer makes,
  and `NoRecurrenceTest` checks that a maximum count leaves no
  recurrence. Each rewritten test fails with the code it covers broken
  in a copy. The two literal asserts and the Python 2 case the audit
  listed were gone already.
- P89. `test.py --profile` runs the selection in one process and exits
  0 on failures. Recommended: per file, with the exit status.
- P90. ~~A file now and then failed to start ("Can't create a
  GtkStyleContext without a display connection", exit 133) when
  another `xvfb-run -a` started at the same moment~~: closed
  2026-10-02, not reproduced: 42 wx applications started six at a
  time under `xvfb-run -a` all started. Reopen with a failing run.
- P91. Editors first open at 400x300, tabs scrolled, fields cut off
  ([WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md), Left). Pick a first size?
- P92. Fit editors and floating AUI panes to the monitors (planned in
  WINDOW_GEOMETRY.md and AUI.md; the editors' part conflicts with
  Decision 8). Do it, or strike it?
- P93. The editor's layout is saved but not loaded (load disabled;
  only the active tab is read back). Remove the saving, or fix the
  load?
- P94. Planned in TODO.md, not started: Preferences OK/Apply enabled
  only after a change (10), a backup and restore review (4), speech
  through pyttsx3 (6), autosave on losing focus (3). Keep, defer or
  strike each?
- P95. Right and centre aligned columns truncate on the wrong side
  (the patched tree control). Fix?
- P96. Toolbar icons on the right jitter while a sash is dragged
  ("deferred to a separate branch", not ruled); its demo
  `test_aui_toolbar_jitter.py` sits at the root. Fix or defer?
- P97. `view.datestied` against the duration modes
  ([DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md) TODO 10), and
  step 1.8.1.3 "remove step?" (the code numbers steps one ahead of the
  spec from 1.7). Rule?
- P98. Date and time refactors open in their docs: presets through
  the attribute path ([DATETIME_PRESETS.md](DATETIME_PRESETS.md) 1),
  the popup out of `MaskedFieldsCtrl`, one "N/A" painter
  ([DATETIME_CONTROLS.md](DATETIME_CONTROLS.md) 8, 9). Do or defer?
- P99. ~~"Paste as subitem" changed its label as the Edit menu
  opened~~: fixed 2026-10-02, the same on master. After a click in
  Categories, the first Edit menu showed "Paste as subcategory" without
  its Shift+Ctrl+V (GTK sized the menu for the old label). It and New
  subitem now change their label when another view becomes active,
  while the menus are closed, and no label is set as a menu opens
  ([MENUS.md](MENUS.md#menu-state-update-flow)). Checked in the app:
  the first Edit menu after a click in Categories shows "Paste as
  subcategory  Shift+Ctrl+V", the New menu "New subcategory...", after
  a click in Tasks "Paste as subtask"; the right-click menu in
  Categories "Paste as subcategory"; quit clean. A view's toolbar
  button now says "New subtask..." (or subnote, subcategory) in its
  tooltip, not "New subitem...".
- P100. Lists: a selection outline (LIST_MANAGEMENT.md 1); the effort
  and attachment viewers select a different row after a delete (a
  no-op override); two open questions on AUI repaints. Rule?
- P101. Links in text fields are always `wx.BLUE`, poor on dark themes
  ([SPELLCHECKING.md](SPELLCHECKING.md), planned). Use the system link
  colour?
- P102. Moved to To Do 70.
- P103. TOOLBAR.md says the sentinel migration is done; 57 old
  sentinels and the transition aliases remain. Finish, or defer with
  D1?
- P104. Long-term items in the migration docs: Blinker or psygnal for
  the Publisher, gettext `.mo` files, the `SetSizerAndFit` review, an
  "audit all string handling". Strike or defer?
- P105. Symbolic icons ([ICON_LIBRARY.md](ICON_LIBRARY.md) 1) and the
  empty `papirus-*` placeholders. Defer, and remove the placeholders?
- P106. Window geometry left to check on LXDE: the "to test" rows, a
  resize jitter (the toolbar resized at every `EVT_SIZE`), a
  "Description" window seen once. Check?
- P107. ~~Turning the idle notice on during a session logged no
  backend summary~~: fixed 2026-10-02, **asked by designer**; the same
  on master. The summary (backend chosen, a test query) is now logged
  the first time the feature is on, at startup or later
  ([IDLE.md](IDLE.md#setting-changes-during-a-session)). Checked in
  the app: Idle time notice 0 to 1 in Preferences, OK: the summary
  (`x11_mit_screensaver` selected) at once; tracking a task then logs
  "Polling started; threshold=60s".
- P108. ~~The colour picker's workaround for GNOME bug 761005 was
  never rechecked~~: checked 2026-10-02, kept. With the workaround
  switched off in a copy, Preferences > Statuses > Late's foreground
  (purple) opens GTK's chooser with the purple selected, but its "+"
  opens the editor at #BF4040, not the purple, on GTK 3.24.49: the
  workaround's cause is still there
  ([COLOUR_PICKER.md](COLOUR_PICKER.md#the-bug--set_rgba-ignored-in-editor-mode)).
- P109. Code TODOs: the status bar's place after hiding and showing the
  toolbar (`mainwindow.py`), editor shortcuts fixed against
  translations (`editor.py`), relative due-date presets passed and
  dropped (`inplace_editor.py`). Check each?
- P110. Mail: IMAP OAuth2 and NTLM through `pyspnego` ("if wanted");
  FLATPAK.md withholds network because IMAP was "likely dead" (fixed
  in P41), yet the version check needs it. Rule?
- P111. Issue #64 (`XLIB_SKIP_ARGB_VISUALS`) waits for a user's test
  since 2025 (TODO.md). Close?
- P112. Stale doc text the audit listed (TASK_STATUS, DATETIME
  CONTROLS, the icon docs, LIST_MANAGEMENT, the Python 3 migration
  docs, the packaging docs, README). Recommended: correct in one pass.
- P113. ~~Editor tests failed now and then: a dialog's OK button not
  found, or the test process crashed~~: traced and fixed 2026-10-02,
  **asked by designer**. The list views' auto-width code kept the
  `wx.ListCtrl`'s header window, which wx creates itself: wxPython is
  not told when wx destroys it, so the kept wrapper outlived it and was
  handed out for what wx later created at its address. Caught with a
  trace in a scratch copy: an OK button came back as a plain
  `wx.Window` (`class=wxButton`, the lookup by type missed it), and two
  crashes under gdb, one creating a panel under such a parent, one
  calling `GetName()` through it. The header is now looked up each
  time, and the dialogs find their buttons by id
  (`wxhelper.get_dialog_button()`)
  ([CRASH_GUARD.md](CRASH_GUARD.md#stale-wrappers-of-wxs-own-windows)).
  `UndoWithEditorsTest` 80 times in a row: no failure, no crash
  (before, about three in 80). The app has the same list views in
  every editor's Effort and Attachments tabs and in the Effort and
  Attachments views; whether a closed editor's list outlived it there,
  as in the tests (P149), was not checked.
- P114. ~~The task list's Budget cell ignored typing ("2:30" left it at
  0:00:00; Enter saved nothing)~~: fixed 2026-09-30, **asked by
  designer**; the same on master. The cell is the task editor's
  duration field (`MaskedDurationCtrl`: Right and Left arrows move
  between days, hours, minutes and seconds); `widgets/masked.py`, its
  last user gone, is removed. Checked in the app: 2:30 stored, Escape
  cancels, a click elsewhere accepts.
- P115. ~~`TaskViewerTest` failed 21 tests in a catalog run that
  crossed midnight~~: fixed 2026-10-02, **asked by designer**; tests
  only. The 24 tests of "Today", "Yesterday" and "Tomorrow" in the date
  columns took the time from the clock: at 00:00 or 23:59 the date
  renders without the time ("Today" for "Today 00:00"), and a run
  crossing midnight changes the day between the test and the
  rendering. They now fix the clock at noon of the day
  (`CommonTestsMixin.fix_the_clock()`). Checked with the clock function
  moved to 00:00:30 and 23:59:30 in a scratch copy: 24 failures each
  before, none after (two tests that need the clock to advance fail
  with any stopped clock, at either time).
- P116. ~~A value typed in the task list's % complete or Priority cell
  was lost on a click elsewhere; Enter kept it~~: fixed 2026-10-01,
  **found and asked by designer**; the code was the same on master.
  The tree ends the edit at the click, before the focus moves, and the
  editors read focus inside them as Escape. Now one rule for every
  cell: Escape and the item's deletion cancel (`CancelEditing()`), any
  other end keeps the value. Checked in the app: % complete, priority,
  subject and a date picked from the calendar; Escape cancels.
- P117. ~~Sorting by the Status column sorted by subject~~: fixed
  2026-10-01, **asked by designer**; the same on master.
  `Task.statusSortFunction()` sorts by the status sort priorities, as
  status first does, re-sorted after the loop's pass
  ([TASK_STATUS_SORT.md](TASK_STATUS_SORT.md)).
- P118. ~~With wxPython 4.2.4 and later the tree views lost the
  selection at every rebuild~~: fixed 2026-10-01, **asked by
  designer** (option B below). A sort, a filter or search, the
  tree/list switch, a task added or renamed dropped the selection; after
  a filter or search the viewer selected the neighbouring task instead
  (GitHub #385, seen on Windows). Every build on 4.2.4 or later:
  Windows and macOS (the latest wxPython until 2026-09-23, 4.3.1
  since), Flatpak, the AppImage, Arch, Fedora 43. Cause: half a copy.
  The HyperTreeList copy (wxPython 4.2.2's, not 2014's: that header
  line is upstream's) ran on each build's installed `customtreectrl`,
  and 4.2.4 made that one track the selection in a set the copy and
  the rebuild bypass. Options, each checked with the catalog on 4.2.3
  and 4.2.5 in a scratch copy: A, patch the copy for 4.2.4's set (left
  each build on its own base); B, bundle 4.2.3's `customtreectrl.py`
  with the copy (chosen: every build runs the certified platform's
  tree code; the copy's `six` import went too); C, 4.3.1's pair with
  Task Coach's changes redone, To Do 67
  ([BUNDLED_TREE_WIDGET.md](BUNDLED_TREE_WIDGET.md),
  [THIRD_PARTY_CODE.md](THIRD_PARTY_CODE.md)).
- P119. ~~Files left open~~: fixed 2026-10-01, the same on master:
  every file the app opens is closed by a `with` block (the template
  list, the template menu, the default templates' copy, the CSV
  import, Anonymize, the exports, Thunderbird's preferences and
  mailboxes), and the IMAP reader logs out. Checked in the app with
  Python's unclosed-file warnings on; the IMAP path is not, for want
  of a server.
- P120. ~~Tests read the user's real templates folder~~: closed
  2026-10-01, **ruled by designer**: not a concern for the repo or
  this refactor; the designer handles the templates there.
- P121. ~~View > Activate next/previous viewer raised
  `AttributeError`~~: fixed 2026-10-01, the same on master. c0527e9d0
  removed `MainWindow.advanceSelection()` as unused, but the PEP 8
  rename had already changed its one caller; the command now calls the
  viewer container directly.
- P122. Ctrl+PgDn and Ctrl+PgUp (View > Activate next and previous
  viewer, also in Help) work in few places. Checked in the app
  2026-10-02 on master and this branch, by where the focus is:
  - task and category trees, docked or as tabs: taken as Page Down and
    Page Up, the selection moves a page; neither the view nor the tab
    changes.
  - the Effort list, docked or floating: nothing. A floating pane's
    own shortcuts send ids nothing is bound to (`UICommand` ignores
    its `id` argument).
  - the search box: nothing on master, where the command itself
    failed (`AttributeError`, fixed here by 56eb732e8); on this branch
    the next view becomes active. An in-place edit box: nothing on
    master; on this branch the next view becomes active and the edit
    box ends, keeping the typed text (P154).
  - calendar, hierarchical calendar, timeline, square map and
    statistics views: a click does not make them the active view, and
    a floating one does not take the focus, so the keys move the task
    view's selection a page.
  - task editor, effort editor, Preferences: nothing; Ctrl+Tab and
    Ctrl+Shift+Tab switch the tabs.
  On this branch the View menu items work (on master they fail the
  same way): they cycle the views in the order they were opened,
  docked, tabbed and floating. A rule is proposed, not ruled.
- P123. ~~Enter in the search box also opened the editor of the
  selected task~~: fixed 2026-10-01, the same on master. The viewer's
  accelerator table (Return, Ctrl+X/C/V, Ctrl+Del) took those keys
  from its toolbar's search box too, so Ctrl+C there copied the task;
  it is now on the list ([MENUS.md](MENUS.md#keyboard-shortcuts)).
  Enter and numpad Enter in the search box search at once.
- P124. ~~After a drag and drop the selection landed on another task,
  and the subject's in-place editor sometimes opened on it~~: fixed
  2026-10-01, **asked by designer**; the same on master. The move
  reaches the viewer as a removal, then an addition, and the removal
  selected the row above the dragged task's old place. The end of the
  drag also selected the drop target, making it the tree's current
  row: the button's release counted as a second click on it and
  started the editor's timer, which then opened the editor on the row
  current by then, the neighbour (traced in the app, the Categories
  tree too). That needs the press to start on the current row: it
  happens when the task dragged was already selected (click it, then
  drag it), not when the drag starts on another task; checked with
  both ways on master, the branch before To Do 67, before this fix and
  after. A drag cancelled with Escape or refused left no row
  highlighted while the status bar counted one selected (master too):
  the dragged rows were passed where `select()` takes their tasks. Now the dragged items stay selected however the drag ends,
  where they landed, and no editor opens
  ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#select-next-after-deletion)).
  Checked in the app against the build before: one task onto another
  parent, two tasks at once, onto a collapsed parent, onto the header
  (made a root task), a parent onto its own child (refused), Escape,
  and a category onto another.
- P125. On Windows the `wx.Display` replacement
  (`workarounds/display.py`, D6) has no `GetScaleFactor()`, so the
  startup report logs no scale factors there (`application.py` skips
  the line on the error).
- P126. ~~`tools/dot.py`'s invalid escape sequences~~: the file is
  gone (P74).
- P127. ~~Collapsing a parent whose child is selected left the status
  bar at "1 selected" and the selection buttons enabled~~: fixed
  2026-10-01, **ruled by designer** (option A), the same on master
  (checked in the app). The tree views announce a selection that an
  expand or collapse changed; the selection still empties as before
  ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#signal-flow)).
- P128. ~~Help > Anonymize wrote a file Task Coach cannot open~~:
  fixed 2026-10-01, the same on master (an error there, a clear
  refusal here): the standard library's ElementTree dropped the
  `<?taskcoach?>` version line; lxml keeps it.
- P129. ~~Ctrl+Z and Ctrl+Y in the search box undid and redid the
  last task change~~: fixed 2026-10-01, **ruled by designer** ("It's
  a text box. Ignore all of these shortcuts and keys"): the Edit
  commands count the search box as a text field, so Undo and Redo do
  nothing there, from the keys or the menu, and Cut, Copy, Paste,
  Delete and Select All act on its text
  ([MENUS.md](MENUS.md#keyboard-shortcuts)).
- P130. ~~A menu item disabled when its menu last opened blocked its
  shortcut until the menu opened again~~ (Ctrl+S did not save after the
  File menu was viewed with nothing to save): fixed 2026-10-01,
  **ruled by designer** ("this should be brought back to standard"),
  the same on master since 2.0.2.2 (a20c9164c replaced the menu items'
  update events with an update on menu open). Menu items answer wx's
  `EVT_UPDATE_UI` again, which every platform has wx send when a menu
  opens, before a popup menu and before a shortcut; enabled and checked
  only, labels as before (GTK3 sizing). No update events in idle time
  any more: `SetUpdateInterval(-1)` and the toolbar skipping AGW's own
  loop; idle, about 37 a second before, none after (measured). Checked
  in the app: the four shortcuts, menus identical on first open, no
  handlers left by refilled submenus ([MENUS.md](MENUS.md),
  [LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#vampire-cpu-usage)). Not
  checked: Windows, macOS, a global menu bar.
- P131. ~~Ctrl+Shift+A was both Edit > Deselect All and Actions > Add
  attachment~~: fixed 2026-10-01, **ruled by designer**: the standard
  pattern wins ("if someone asks for an attachment shortcut, we will
  add it and figure out something that doesn't conflict"). Deselect
  All keeps it: Shift+Ctrl+A in GNOME's guidelines and KDE's standard
  shortcuts. Windows and macOS have no deselect standard; Windows
  reserves no Ctrl+Shift+A, and macOS lists Shift-Command-A (Apps,
  Launchpad before Tahoe) among its Finder and system shortcuts,
  likely the Finder's only (not checked on a Mac). Add attachment has
  none; its translations and the Help's shortcut table follow.
- P132. ~~Ctrl+Z and Ctrl+Y in an editor's text field undid and redid
  task changes, not the typing~~: fixed 2026-10-01, the code the same
  on master. The editor's shortcut table gets the keys before the
  field (as in P123); its Scintilla fields now count as text fields,
  and their undo covers only the typing
  ([MENUS.md](MENUS.md#keyboard-shortcuts)).
- P133. ~~Opening a task's editor could change a file just saved~~:
  fixed 2026-10-02, **asked by designer**; the same on master. A date
  changed outside the editor (a task list cell) left the stored planned
  duration as it was; after saving, opening the task's editor without
  touching anything marked the file changed ("Change planned
  duration"): the editor's Implicit mode writes due minus start when it
  opens (DURATION_CALCULATIONS.md, Logic Flow 4.3.1.2). The task now
  keeps that duration itself in Implicit mode, in the same undo step
  as the date ([DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md#stored-duration)).
  Not in the adjust modes: there the editor moves the other date by
  the duration, which the task changing it first would stop (a test
  shows it). Old data is still corrected the first time the editor
  opens, **ruled by designer** ("correcting data on an incorrect old
  file ... seems totally normal"). Checked in the app on a Welcome.tsk
  copy: after a due date changed in the list and a save, opening and
  closing the editor leaves the file unchanged; the list edit's undo
  step carries the duration.
- P134. ~~The search box and the list's in-place editor had no
  undo~~: fixed 2026-10-01, **ruled by designer** ("the text boxes
  should all behave the same ... limited to the platforms that don't
  have it"). wxWidgets 3.2.8 leaves `Undo()` a stub on GTK (every
  text field) and macOS (single-line ones); Windows has its own.
  There Task Coach keeps each field's typing history: Ctrl+Z,
  Ctrl+Y and Ctrl+Shift+Z, and the Edit menu, in every text field
  ([MENUS.md](MENUS.md#keyboard-shortcuts)). Not checked on macOS.
- P135. Deferred: D12.
- P136. ~~"Hide this column" refused the click when its menu item lay
  over another column or pane~~: fixed 2026-10-01, **ruled by
  designer** ("whatever is under the pointer point, if I right click
  and I hide, that gets hidden"), the same on master. The command
  checked the column under the pointer when the item was clicked; it
  now takes the column the menu was opened on, as the hide always did.
- P137. Merged into P124 (the same issue), fixed.
- P138. The tree widget bundled since To Do 67 adjusts its scrollbars
  in every `CalculatePositions()`, so the Windows deferred adjustment
  after content changes and the scroll methods' own
  `AdjustMyScrollbars()` may no longer be needed
  ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#windows-scrollbar-adjustment-on-content-changes)).
  Check on Windows before removing them.
- P139. ~~A column shown or hidden left each row's icons at their old
  column positions~~: fixed 2026-10-01, **asked by designer**; on
  master the Notes column emptied when Description was shown, here
  Description showed an attachment's icon. The tree widget inserts or
  removes only the header; Task Coach's tree control now moves each
  row's per-column values with the column, and the copy's own column
  code went back to upstream's. After each of eight shows and hides,
  the ordering column included, the view matches a fresh start with
  the same columns pixel for pixel. Considered: rebuilding the rows
  instead (twice the time: 2 s against 1 s with 2,050 tasks); the
  widget's own hiding (changes what a column position means in about
  140 places) ([BUNDLED_TREE_WIDGET.md](BUNDLED_TREE_WIDGET.md#updating-the-bundle)).
- P140. ~~Opening a file of 2,050 tasks (50 parents with 40 late
  subtasks each) froze the app for 64 s~~: fixed 2026-10-01, **asked
  by designer**. The first pass's 16,400 style events each made the
  tree views walk all their rows (`RefreshItems()`), and the Effort
  view look up each task's effort rows. The viewers now gather a
  pass's changes and refresh their rows once after it, as after a
  bulk command (`scheduler.aboutToPass`, `scheduler.pass`;
  [SCHEDULERS.md](SCHEDULERS.md#event-subscribers)); the tree finds
  the rows to refresh, and which are selected, through sets. Measured
  on the virtual display, from the window shown: idle after 3 s, 64 s
  before (master: 3 s, then a quarter of a core while open); the first
  pass 1.7 s with the refresh. With the Effort view and 6,000 efforts:
  3 s, a first pass of 228 s before (master 15 s). Marking all 2,050
  tasks completed: busy 6.5 s, 83 s before (master 15 s). After each
  the screen matches the build before pixel for pixel. Also fixed:
  after a bulk command (marking tasks completed, active or inactive)
  the Task statistics view logged an error (`PieCtrl` has no
  `RefreshItems()`); it now redraws once, after the command or the
  pass.
- P141. ~~A row's tooltip stayed up after Expand all or Collapse all
  moved another row under the pointer, and the hover outline came
  back only after the pointer moved within the list again~~: fixed
  2026-10-01, **asked by designer**; the same on master. Rows moving
  under a pointer at rest send no mouse event, which the tooltip and
  the outline follow. The same with a parent collapsed or expanded by
  the keyboard, the wheel, and a key that scrolls (End): the tooltip
  stayed, and the outline stayed on the row that moved away. Task
  Coach's tree control now hides the tooltip and moves the outline to
  the row under the pointer after each of these
  ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#row-hover-outline)); the
  bundled widget is unchanged. Checked in the app: the five cases
  before and after; a tooltip still shows when the pointer moves to
  another row; drag and drop and the Welcome.tsk steps unchanged. The
  list views have their own: P148.
- P142. Will not do: D11.
- P143. ~~The "not possible" cursor was X's skull~~: fixed 2026-10-01,
  **ruled by designer** (Task Coach's own cursor from the icons it
  ships), the same on master. wx's no-entry cursor is X's skull where
  the cursor theme has no picture for it (here DMZ-White is asked for
  but not installed; Adwaita has none). A refused drop and a column
  border that cannot be dragged now show the "prohibited" sign from
  the bundled Noto emoji, made a cursor as the link and home drop
  cursors are ([ICON_DISPLAY.md](ICON_DISPLAY.md#synthetic-icons)).
- P144. ~~Rebuilding a tree view of 2,050 tasks (a sort, a filter,
  the tree/list switch) took 2.1 to 2.8 s~~: fixed 2026-10-01,
  **asked by designer**; the same on master and before To Do 67. Most
  of it was the check `RefreshAllItems()` makes before rebuilding,
  whether the rows still match the view (`_snapshot_adapter()`), and
  the rebuild's own lookups: the viewer listed a parent's children by
  comparing every task in the view with a list of them (Python
  `__eq__`, 32 million calls profiled for two sorts and the file's
  opening). It now looks each task up in a set. Busy time after the
  action, on the virtual display: a sort 3.5 s before, 0.6 s after;
  the tree/list switch 1.3 and 0.7 s; a search 1.1 and 0.85 s; the
  screens match the build before. That still scanned the view once
  per parent: with 1,000 parents of 2 subtasks each (3,000 tasks) a
  sort took 2.2 s of processor time (3.6 s before). **Asked by
  designer** ("each parent should always know its subtask"): the tree
  sorter now keeps each item's place in the sorted list, built once
  after the list changes (`TreeSorter.children_of()`), and a parent's
  own subitems are put in that order, without searching the list. A
  sort: 0.5 s on the 3,000-task file, 0.2 to 0.3 s on the 2,050 one;
  the screens match. What is left is building the rows themselves.
- P145. ~~A bulk command or a pass that changes many statuses updated
  the tray icon's tool tip once per task, each update counting every
  task's status~~: fixed 2026-10-01, **asked by designer**; master
  did the same per appearance change. The tool tip is now counted at
  once outside a burst, and once after a bulk command or a scheduler
  pass, the rule the viewers follow (P140; `_OnceAfterBursts` in
  `gui/taskbaricon.py`, for both tray classes). Marking all 2,050
  tasks completed: busy 2.8 s, 7.6 s before; the screen matches the
  build before. Checked in the app over D-Bus: the tool tip read "10
  tasks overdue" on a Welcome.tsk copy, nothing once all were marked
  completed, "10 tasks overdue" again after undo. Not covered: a
  change of the due soon hours in Preferences, where each task
  recomputes its status in its own observer of the setting, outside
  a pass.
- P146. Deferred: D10.
- P147. ~~Undoing a drag and drop left the tree showing the task under
  its new parent~~: found and fixed 2026-10-01, while fixing P124; on
  this branch only, since the undo log (To Do 34). A drag tells the
  views by taking the moved items out of the list and back; undo and
  redo put the links back alone, so the tree views neither rebuilt nor
  forgot their cached root items (a task made a root by the drop
  stayed one); master undid the drag with the list changes. A tree
  sorter now notes a change of subitems while values are put back
  and, once they all are, sorts again and tells the views, unless a
  list change told them (`after_restoring()`,
  [UNDO_REDO.md](UNDO_REDO.md#architecture-snapshot-and-diff)).
  Checked in the app: drop, undo and redo each show the task in its
  place, still selected; a merge of changes on disk moving 40
  subtasks takes as long as before and shows the same.
- P148. ~~In the list views (Effort, Attachments) a scroll moved the
  hover outline onto the column header~~: fixed 2026-10-02, **asked
  by designer**; the same on master. The list draws the outline after
  painting by row number (`VirtualListCtrl`), and nothing changed the
  number when the rows scrolled under the pointer. It now follows the
  tree views' rule (P141): after a paint where another row is under the
  pointer, and after the list is refilled, the tooltip hides and the
  outline moves to that row
  ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#row-hover-outline)).
  Checked in the app, Effort view with 6,000 efforts: the wheel and End
  leave the outline on the row under the pointer; at rest it stays.
- P149. ~~Closed editors, Preferences and floating views stayed in
  memory~~: fixed 2026-10-02; the same on master (11 MB after opening
  and closing 20 task editors). An AUI manager (in a floating view's
  window, in each tab notebook) and the editors' date and time control
  are event handlers made in Python that bind handlers to themselves:
  wx holds those, so neither was freed, nor what it held (a closed
  view with its menus, an editor's or Preferences' pages). Each is now
  deleted once its window is destroyed (`wxhelper.delete_with_window()`,
  [AUI.md](AUI.md#managers-never-freed),
  [CRASH_GUARD.md](CRASH_GUARD.md#event-handlers-that-are-not-windows)).
  Closing a floating pane also removes its window's manager first:
  Reset window layout with a floating view logged a wx assertion.
  Checked in the app: 20 editors 5 MB, live objects flat; editors,
  Preferences, a floating view closed, docked again, views as tabs,
  Reset window layout, quit and relaunch with a floating view: no
  traceback or assertion. In the unit tests, where it was found,
  editors were destroyed without being closed, so their popup menus
  kept their viewers: closed since, with P155.
- P150. ~~In the Adjust due date mode a due date changed in the task
  list was lost when the start then changed in the editor~~: fixed
  2026-10-02, **asked by designer** (option A); the same on master.
  A planned date changed outside the editor (a list cell, a calendar
  drag) now follows the task's duration mode as in the editor: in
  Adjust Due a new start moves the due date by the duration and a new
  due date sets the duration; Adjust Start mirrors it; a calendar move
  is one change of both ends. The list's "dates tied" preference
  applies only in Implicit mode
  ([DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md#stored-duration)).
  Checked in the app on a Welcome.tsk copy: after the list's due date
  2026-03-04 the editor shows a duration of 33d 08:00, and the start
  moved a day takes the due date to 2026-03-05. The calendar views
  were checked by tests only.
- P151. ~~Each task editor opened and closed kept about 6 MB in
  memory (118 MB after 20)~~: found and fixed 2026-10-02, while
  analysing P149; on this branch only, since pypubsub was removed (To
  Do 18). The date, time and amount controls each read a `Settings`
  object of their own (on master too), and each subscribed itself to
  the Publisher, which holds a subscription's source: none was freed
  (pypubsub held its listeners weakly). A change of the setting now
  calls its handler directly. Checked in the app, 20 editors with
  their pages shown: 9 MB, master 11 MB; the rest is P149.
- P152. ~~The date, time and amount controls and the lists' dates
  ignored a settings file given with `--ini`~~: fixed 2026-10-02,
  **asked by designer**; the same on master. Each control made a
  `Settings` object of its own, which read the default file from disk
  (written only when the application quits): a file given with
  `--ini` was ignored, a Preferences change reached them only after a
  restart, and each copy stayed in memory (P151). They now read the
  application's one settings object through `settings2.get()`
  ([SETTINGS.md](SETTINGS.md#reading-from-any-module)); the date and
  time formats as at start, as the lists, which Preferences says need
  a restart. A test fails if any module but the application makes a
  `Settings` object. Checked in the app: `dateformat = DMY/` in the
  `--ini` file shows 15/01/2026 in the list and the editor (master:
  2026-01-15); after Decimal separator: Comma and OK, the next editor
  shows 75,00 (master: 75.00 until a restart). First step of To Do
  70.
- P153. Moved to To Do 71.
- P154. ~~An in-place edit box stayed open, what was typed unsaved,
  when another view became active~~: fixed 2026-10-02, the same on
  master. By a click in it (master too) or, on this branch, Ctrl+PgDn
  (P122). Only the date box ended then, and it took the focus back
  from the view clicked: on master Down then moved nothing in either
  view. Every edit box now ends, keeping the typed value, once the
  focus has left it and its parts, and the focus stays where it went
  ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#in-place-editing)). Checked
  in the app on the subject, description, date (Tab inside, the
  calendar, the hour choices open), progress, priority, budget and
  hourly fee: a click in Categories saves and Down then moves the
  category selection; Ctrl+PgDn saves and Categories takes the keys; a
  right-click inside opens the text field's own menu (P157); the focus
  going to another application saves; Escape cancels,
  Enter saves; Edit > Paste from the menu bar pastes into the box,
  which stays.
- P155. ~~The test runner kept every test it had run~~: fixed
  2026-10-02. `TestResultWithTimings` keyed its timings by the test
  object, so whatever a test kept in its attributes stayed for the
  whole run; `UndoWithEditorsTest` also destroyed its editors without
  closing them (P149). The timings are now keyed by the test's name,
  and the editors closed as the user closes them. Measured in that
  file: views alive after each test 39 rising to 239 before, 3 to 5
  now; dead wx wrappers 2,660 rising to 16,868, now about 800. The
  full suite passes; wx's exit-time assertions
  ("pushed event handlers must have been removed") in
  `UICommandTest`, from frames kept until exit, are gone.
- P156. ~~Typing in an amount field printed a traceback
  (`TypeError: object of type 'float' has no len()`)~~: fixed
  2026-10-02, this branch only (04157cc82). The text undo read the
  field's value, a number for the amount fields (the hourly and fixed
  fee in the list and the task editor), and their history broke; it
  now reads the text ([MENUS.md](MENUS.md#keyboard-shortcuts)).
- P157. ~~A right-click inside an in-place edit box acted on the row
  below~~: fixed 2026-10-02, **asked by designer**; the same on master.
  F2 on "Return library books", right-click on the name in its edit
  box: the list's item menu opened and "Schedule dentist appointment",
  the row below, was selected, so Delete deleted it. The right-click
  went up to the list, which read the pointer in its outer frame's
  coordinates, the column header's height (26 px) lower; logged from
  the app: the pointer at (160, 332) inside the box (y 320 to 343).
  The box now keeps it: its text field's own menu opens and the box
  stays ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#in-place-editing)).
  Checked in the app: the subject, progress and hourly fee boxes open
  GTK's text menu (Cut, Copy, Paste, Delete, Select All, Insert
  Emoji), the selection stays and Escape returns to the box; Select
  All, Copy and Paste act on the text; the date box opens nothing and
  stays; a right-click on a row with no box open still opens the
  task's menu for that row, and Shift+F10 the menu for the selected
  row. The list now also reads a context menu's pointer in its rows'
  window (a test fails on the old reading, which picked the row below):
  on GTK no such event reaches it any more; Windows, which sends one
  when the right button is released, could not be checked here.
- P158. ~~After Enter or Escape in an in-place edit box the list took
  no keys~~: fixed 2026-10-02, **asked by designer**; the same on
  master. The row showed grey and Down moved nothing until a click in
  the list, also on coming back from another application the box was
  left for (P154). wx makes a window holding a focusable child
  unfocusable in GTK (its container code), so the list's
  `SetFocusIgnoringChildren()` while the box existed went to its
  children, found the box again, and the focus went with the box;
  `FindFocus()` still named the list. The list is now given the focus
  once the box is destroyed
  ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#in-place-editing)). Checked
  in the app: Down moves the selection after Enter, Escape, a date
  box's Enter and a return from another application; after a click in
  Categories or Ctrl+PgDn while editing, Down still moves the category
  selection.

## Views on the Effective Styles

To do 35. **Decided before this refactor**
([TASK_STATUS.md](TASK_STATUS.md#legacy-code-compatibility-resolved)):
new code reads `effectiveXxx()`, and the legacy `recursive=True` style
accessors stay only until their consumers move; the migration waited
for the effective styles to prove stable. Only the editor had moved;
every view drew from the legacy accessors, cached by
`Task.recomputeAppearance()` outside the loop, while the loop computed
the effective styles every pass for nothing but the editor.

Done 2026-09-28: every view draws `shown_fg_color()`,
`shown_bg_color()`, `shown_font()` and `shown_icon_id()`
([APPEARANCE_STYLES.md](APPEARANCE_STYLES.md#what-the-views-draw)), and
the legacy code is gone.

The two rules differ, so moving changes what some rows look like:

- Several coloured categories: the legacy rule mixes their colours and
  fonts; the effective rule takes the highest style priority's (seen
  2026-09-28: purple drawn, red effective). **Ruling, 2026-09-29:**
  equal priorities (0 by default) take the first category by name, not
  a mix ([APPEARANCE_STYLES.md](APPEARANCE_STYLES.md#category-style-priority)).
- A subtask with no colour or category of its own: legacy takes its
  parent's category colours, else its status colour; effective takes
  its parent's own or category style, else its own status. **Ruling,
  2026-09-29:** the effective rule stays, for icons too: styles set on
  a parent carry down the hierarchy; whoever wants the status icons
  sets no icons or categories.
- Styles set by categories or the status appear at the loop's next
  tick (within a second); an item's own style at once, as before.

Found on the way, fixed:

- The effective rule gave a subtask its parent's status and tracking
  styles (a completed subtask of an active task drawn active, the
  clock on every subtask of a tracked task): a task's own state is no
  longer passed down, as the views always showed (to do 35.9).
- A task's status icon never reached its effective icon: the status
  getter's name was wrong since #386.
- The effective setters sent one event per value, default and source:
  up to three refreshes per style change, now one.
- Until the loop's first pass styles a new or loaded task, its icon is
  empty; the calendar drew it as an invalid bitmap and lost tasks, the
  start tracking menu logged an invalid icon. Both skip it now, as the
  trees, tooltips and tray already did.

Scan, 2026-09-28 (sources the loop does not compute: none left after):

| Where | Legacy use | Now |
|---|---|---|
| `widgets/treectrl.py`, `widgets/listctrl.py` | Row colours, font (every tree and list view) | `shown_fg_color()`, `shown_bg_color()`, `shown_font()` |
| `widgets/hcalendar.py`, `widgets/calendarwidget.py` | Task colours, font, icon | The same, `shown_icon_id()` |
| `gui/viewer/base.py` `subjectImageIndices()`, `gui/viewer/task.py` `get_icon_id()` | Subject icons | `shown_icon_id()`: the effective icon (the plural transform removed, to do 58) |
| `gui/viewer/task.py` Timeline, Square map | Colours, font | `shown_*()` |
| `gui/viewer/task.py` task graph | `task.foregroundColor(recursive=True)` (the wrong variable: `task`, not `tsk`) | `tsk.shown_fg_color()` |
| `gui/taskbaricon.py`, `gui/uicommand/uicommand.py` (start tracking menu) | Task icons | `shown_icon_id()` |
| `persistence/html/generator.py` | Export and print row colours | `shown_fg_color()`, `shown_bg_color()` |
| `gui/dialog/editor.py` owned-item lists | Notes, efforts, attachments rows | `shown_*()` |
| `domain/effort/base.py` | An effort's colours and font: its task's legacy ones | Its task's `shown_*()` |
| Old event `appearanceChangedEventType()` | Refreshes the task, category, note and effort views, the tray, editor pages, composite efforts; the task filter uses it for status changes | The effective-style events; the filter and the tray the status event; the event stays as an item's own style change |

---

## Master Design

The old master loop scanned every category, task and note every second
([Cost Before](#cost-before)). The goal: a cheap entry point each
second, and work only for the seconds and the objects a change
reaches. Built in two steps: the timer list and the full loop at its
seconds (2026-09-27), then the incremental pass (2026-09-30,
[Incremental Pass](#incremental-pass)).

1. **One master timer list**: each task's seconds at which time alone
   changes it, one per rule, sorted (`bisect`), each entry with its
   task and rule; a date not set has none. A change of the task's
   dates replaces its entries, a deletion removes them, so the list
   holds exactly the pending seconds. An entry may lie in the past: it
   is then simply due.
2. **Whole seconds, one rule**: every date and time is a whole second
   ([Time Resolution](#time-resolution)), and each entry is the first
   whole second at which its rule holds. A rule that holds after a
   date (overdue: due `<` now) gets the second after it; a rule that
   holds from a date on (active: actual start `<=` now) gets the
   date's own second. No other case.
3. **Marks**: a change to anything the passes read marks the objects
   it concerns as its event arrives ([Data Changes](#data-changes)).
4. **Each second**: the entries at or before now mark their tasks;
   if anything is marked, one pass processes the marked objects and
   what reads them, each once, in a fixed order (categories, tasks,
   notes, attachments; parents first), so a cascade settles in the
   same pass. Otherwise nothing else runs. A reminder set in the past,
   a late tick or a jump forward (suspend, resume) all come down to
   entries at or before now.
5. **The full loop**: every object, in the same order, when what every
   object reads changed: a file read or merged, the clock set back
   (the list is rebuilt), the due soon hours, the status styles, the
   theme and the system colours.

## Time Resolution

**Ruling, 2026-09-27:** every date, time and duration Task Coach
stores, computes or compares is a whole second: task dates, reminders,
efforts, the scheduler's clock, the statuses computed from them, and
the task file. Only logs carry fractions of a second: their
timestamps stay high resolution, to show the flow in detail. Timer
delays in the UI (debounce, animation, the window geometry's quiet
periods) are not time values and are not concerned: they run in
milliseconds through `patterns.later`, apart from the master loop
([DEFERRED_CALLS.md](DEFERRED_CALLS.md)).

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
  dropped
- Kept: `log_step()` and the other log timestamps; `perf_counter()`
  durations in traces; UI timer delays in milliseconds

## Index

- [To Do](#to-do)
- [Deferred or Will Not Do](#deferred-or-will-not-do)
- [Pre-existing Issues](#pre-existing-issues)
- [Views on the Effective Styles](#views-on-the-effective-styles)
- [Master Design](#master-design)
- [Time Resolution](#time-resolution)
- [The Master Timer List](#the-master-timer-list)
  - [Stale Entries](#stale-entries)
- [What Changes the Master Timer List](#what-changes-the-master-timer-list)
- [Data Changes](#data-changes)
- [Cost Before](#cost-before)
- [Cost After](#cost-after)
- [Incremental Pass](#incremental-pass)
- [ID Review](#id-review)
- [How It Was Measured](#how-it-was-measured)
- [History: One List on the Tick, Not a Timer per Event](#history-one-list-on-the-tick-not-a-timer-per-event)

---

## The Master Timer List

The entries, per task, each the first whole second at which its rule
holds, `(second, number, task, rule)`; the number orders the entries
of one second:

| Rule | Holds when | Entry |
|---|---|---|
| Late | Planned start `<` now | The second after the planned start |
| Active | Actual start `<=` now | The actual start's second |
| Due soon | Due less the due soon hours `<` now | The second after it |
| Overdue | Due `<` now | The second after the due |
| Reminder | Reminder less 2 s `<=` now (2 s ahead, as today) | That second |

Dates are whole seconds ([Time Resolution](#time-resolution)). These
are the only time conditions in the passes: `Task.compute_status()`
(overdue, due soon, active, late, each on the task's own dates, not
its subtasks') and `processReminder()`. A date not set gives no entry:
it is never reached. Completion is not one: a completion date, even a
future one, makes the task completed at once. Styles read time only
through the status.

Completed tasks keep their entries: one rule for every task, and
completing or reopening one needs no signal. At an entry of a
completed task the pass finds nothing new.

One function gives a task's entries (`Task.timer_seconds()`, by
rule); the build, the add event and the date changes all use it. Each
task's current entries are kept with it (`_timers_of`), so a date
change replaces exactly its own and a deleted task removes its own.
A due entry leaves the list when it marks its task.

Opening a file: `TaskFile.load()` empties the task list (the list is
emptied with it), adds the file's tasks, and its read event rebuilds
the list and runs the full loop once.

The minute and day changes only tell viewers to refresh; they stay the
tick's own checks.

Size: one entry per set date and reminder. The generated 2000-task
file with dates 60 minutes around now holds about 1,500 entries; the
heap before held about 13,600 (2026-09-30).

### Stale Entries

To do 57. **Done 2026-09-30**, with the incremental pass.

The first list was a heap of seconds without their task: a change to a
task's dates pushed its five seconds again, and those of each
ancestor; the old ones stayed, since an entry without its task could
not be found to remove, and a date not set gave an entry in the year
9999, never reached. The heap grew with the edits, and a rebuild once
it doubled only bounded it. Entries now carry their task and rule, a
task knows its entries, a date change replaces them and a date not set
has none (above).

---

## What Changes the Master Timer List

For time, the list listens to these signals (the changes also mark
their objects: [Data Changes](#data-changes)):

| Signal | Today | Change to the list |
|---|---|---|
| A task's due, planned start, actual start or reminder changed | Publisher `task.<field>` from the field's change callback, the task as source ([PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#migration-log)) | Replace the task's entries |
| Tasks added to the task file's task list | Publisher add event of the task list; `extend()` includes every subtask | Their entries |
| Tasks removed | Publisher remove event of the task list | Their entries removed |
| Due soon hours changed, a file read or merged | Publisher `behavior.duesoonhours`, `taskfile.justRead`, `taskfile.merged` | Rebuilt, and the full loop |

Each ancestor is a source of the same event too; its entries are
replaced by the same ones, harmlessly.

An entry at or before now is due at the next tick: a reminder set to
a past time fires, a task pasted with a past due date is shown
overdue.

Clock changes: a tick earlier than the one before rebuilds the list
and runs the full loop ([Master Design](#master-design), 5). Jumping
forward needs nothing: the seconds passed are due.

### Why Nothing Is Missed

Checked in the code, 2026-09-27:

- **The three dates and the reminder** are private `Attribute`s. Their
  only writes are the constructor and `Attribute.set()`, which calls
  the change callback on every change; nothing reaches them another
  way (no `_Task__` access). The reminder was a plain field until step
  4, written in `set_reminder()` and both branches of
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
| Undo or redo of an edit: the fields put back, their callbacks run | Field changed |
| New task or subtask, paste, template, import, file opened, file merged, undo of a delete | Tasks added |
| Due soon hours, Preferences | Due soon hours changed |
| Delete, cut, undo of an add | Tasks removed: their entries go |
| Completed or reopened | None: completion is not a time condition, and completed tasks keep their entries |

No other change gives a task new time seconds: moving a task to
another parent, prerequisites (a task waiting for one keeps its
entries; the pass finds it inactive), categories, subjects, styles,
other settings.

---

## Data Changes

**Rule:** a change to anything the passes read marks the objects it
concerns; the next tick's pass processes them and what reads them.
Several changes in one second give one pass.

What the passes read, so what marks:

- A task's dates, completion, reminder, recurrence, prerequisites,
  categories, parent, own colours, font and icon, efforts being
  tracked, notes and attachments
- A category's or a note's colours, font, icon, parent, and a
  category's style priority
- Tasks, categories, notes and attachments added or removed
- The appearance settings (colour, font and icon per status, light and
  dark), the theme, the due soon hours: the full loop

The hook is the domain's modification events (`_data_event_types()`
in `gui/scheduler.py`), a task's tracking, and the passes' own outputs
(status, derived and effective styles), except fields that change no
status, reminder or style, such as the subject, the description, the
fees, the priority and the expanded state, so typing runs no pass.
What each event marks:

- Its sources.
- An added object with everything under it (children, owned notes and
  attachments): each reads what is above it.
- An effective style changed outside a pass (an override, undo), or a
  category's style priority: also what reads it, its children and, for
  a category, its members.
- A name: only what reads it as a style source ("[Category] Work"),
  so a leaf's name marks nothing.

Computed values the passes do not read (time spent, budget left,
revenue, the subtree values) mark nothing. The safe side decides
doubtful fields: one wrongly left in costs a pass; one wrongly left
out is a miss, which the check mode logs. Settings are the other way
round: only the sections listed above, as window and other settings
change often and the passes read none of them.

### Ruling: the Cascade Runs Through the Heap

**Superseded 2026-09-30** by the incremental pass (question 1 there): a
cascade settles in one pass, each object once in the fixed order, so
no pass runs long and none runs for nothing. Kept as it was:

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
  (item 3), and a reminder trigger is not a change: triggered again
  while its dialog is open, it is dropped
  ([Reminders](#data-changes)).
- **It settles**: styles flow one way (category to task, parent to
  child) and statuses come from the saved data, so no change feeds
  back into its cause. Today's loop settled after a file opened in
  two passes: the third changed nothing (the prototype's trace,
  2026-09-27, 200 tasks).
- **Fewer passes**: the loop visits parents first (by depth,
  `_order()` in `gui/scheduler.py`; today it visits tasks and categories in set order, so a child seen
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
not part of this plan. The viewers' refresh after it: P140
([Pre-existing Issues](#pre-existing-issues)).

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
| 2000 tasks, dates 60 minutes around now (about 25 statuses changing a minute) | UI thread busy 98%, 5 to 10 ticks a minute, autosave re-reading the file after every status change | Busy 11%, the passes; 28 to 54 ticks a minute ([To Do](#to-do), 11) |

With the incremental pass, measured 2026-09-30 on the virtual display,
the same generated files (`tools/generate_task_file.py`):

| File | Full loop at due seconds | Incremental pass |
|---|---|---|
| 2000 tasks, dates 60 minutes around now | 29 passes a minute, median 379 ms, max 786 ms; 13,618 heap entries | 20 to 22 passes a minute, median 9 to 19 ms, max 36 to 278 ms, 24 to 37 objects a minute; about 1,500 entries |
| 2000 tasks, dates 20 days around now, idle | 1 pass a minute | No pass in minutes: the next entry is later |
| First tick after opening the 60 minute file, without the interface | 1,466 ms, then 581 ms for the second pass (each due reminder fired twice) | 1,383 ms, then 14 ms (each due reminder fired once) |

In the app, the first minute is dominated by the reminder windows the
due reminders open (about 130 in these files).

Nothing missed: with `TASKCOACH_SCHEDULER_CHECK=1` the full loop runs
after every tick's pass and logs what it still changes. It logged
nothing for 3.5 minutes on the 60 minute file (2000 tasks), nor while
completing, pasting, deleting and undoing in another file.

## Incremental Pass

To do 45, with to do 57 ([Stale Entries](#stale-entries)). **Analysis
2026-09-29, verified; built 2026-09-30** (`gui/scheduler.py`), with
the designer's go-ahead for the recommended answers (questions
below).

The designer's idea (2026-09-29): a master list of the seconds, each
with its tasks; when a second lands, process its tasks and cascade
only what they change, each object once, instead of the full loop over
every object; data changes (a category's icon or priority, a move)
cascade the same way, through the Publisher events.

**Verdict: it can match the full loop exactly.** Checked by a
differential probe: after each of 300 to 400 random changes (16 kinds:
overrides, category links, priority, renames, moving tasks and
categories, tracking, dates, completion, prerequisites, new and pasted
tasks with owned notes, subnotes, delete and undelete,
state restores (then `__setstate__`, since replaced by the undo
log's snapshots), clock jumps of 1 s to 30 h), on 7 files of 167 to 714
objects, an emulated incremental pass ran, then the real full loop:
0 values left for the full loop, 0 objects out of order, 0 processed
twice; 6 to 13 objects per change. Dropping any rule below brings
misses back. The one difference in principle: the full loop triggers
a due reminder again at every pass, the incremental pass at its second
only; no action in the interface leaves a reminder due after its
dialog closes.

### Design

1. **The timer list** (to do 57): a sorted list of `(second, task,
   rule)`; each task knows its entries, so a date change replaces them
   and a deletion removes them; no entry for a date not set. A landing
   second gives its tasks: their status and reminder are computed, and
   a changed status marks the task's style.
2. **Marks from events:** each change the scheduler already hears
   ([Data Changes](#data-changes)) marks the objects that read it
   (Followers below), by identity, not ID.
3. **Settling:** the marked objects in a fixed order: categories by
   depth, then tasks by depth, then notes (global and owned) by depth,
   then attachments. A changed effective value or source marks its
   followers, which always come later in the order, so each object is
   computed once and nothing loops.
4. **Global changes keep the full loop:** a file opened, a merge
   (copies share IDs), the clock set back, the due soon hours, the
   status styles (light and dark), the theme and the system colours.
   It runs in the same fixed order, so it settles in one loop too: the
   earlier loop styled a category's owned notes right after the
   category, before a category they belong to (found by the test).
5. **Proof, kept:** the differential probe became a unit test
   (`SchedulerIncrementalTest`) that compares against the full loop;
   the check mode (`TASKCOACH_SCHEDULER_CHECK=1`) stays for the app. No
   periodic full loop (ruling below).

Rules the first sketch lacked, each needed by the probe:

- Follow the `effective.*` events wherever they are sent: a style
  change, set or put back by undo, computes the object's effective
  style at once, outside the pass (the style field's callback).
- A category's members are the items whose `categories()` hold it:
  `Category.members()`, their index since P29. A task outside the file
  (deleted, kept for undo) is not processed: its reminder must not
  fire; styling another object outside the file is harmless.
- An added object is computed with its whole subtree (children, owned
  notes and attachments): each reads what is above it, its parent and
  its categories, so it inherits their styles; the fixed order settles
  what is above first.
- A category's rename or style priority change reaches its members:
  equal priorities are ordered by name.
- An owner's style reaches none of its notes or attachments.

### Verification

The built pass, 2026-09-30: `SchedulerIncrementalTest` runs 150
random changes of the 16 kinds below on a random file, each followed
by a real tick, then the full loop, which must change nothing; with
400 changes on seeds 1 to 7, nothing either. A seed replays its run:
IDs count up and each pick follows them, since the file's collections
are sets in memory order (made so 2026-09-30, when a pick that varied
from run to run failed a test that expected a whole subtree). It found
one fault while built: the full loop's own order (Design, 4). The check mode in the
app: [Cost After](#cost-after).

The analysis before it was built, with a differential probe
(`docs/scripts/scheduler_diffprobe.py`, retired 2026-09-30 for the
unit test; in git history): 16 kinds of random change; after each,
an emulated incremental pass, then the real full loop. With the rules:
0 misses on seeds 1 to 7 (300 to 400 steps, 167 to 714 objects), 0
out of order, 0 twice, 5 to 13 objects per change. Dropping a rule:
not following effective events sent outside the pass gives 3 misses
in 200 steps (seed 3). Members from `Category.members()` gave
7 to 10 misses per 300 steps (seeds 1, 2, 4 to 7) while paste left
notes one-sided; since P29, 0 (rerun 2026-09-29). The full loop
re-triggered due reminders at nearly every step, the difference in
principle above.
The first full loop after the random file is built changes about 705
values, the second none: the loop already settles in one pass.

`docs/scripts/scheduler_claims_probe.py` checks single claims: a leaf
category's rename with a member marks it (its member shows the name as
its style source; before P29 a member linked one way was missed); fonts
from one string compare equal; an owned note and attachment ignore their
owner's style; default icons; an override changes the effective style at
once while the children wait for the pass.
`docs/scripts/category_membership_probe.py` shows P28 and P29 fixed.

### Inputs

| Result | Reads |
|---|---|
| Category style | own override; the parent category's effective value and name |
| Task style | own override; tracking (icon); its categories: their priority, name, ID and effective values; the parent task's effective value, source and name; its status and the status styles in the settings (light or dark theme) |
| Note style | own override; its categories (as a task's); the parent note's effective value and name; not its owner |
| Attachment style | own override only |
| Task status | own planned start, actual start, due and completion; the completion of the prerequisites of the task and its ancestors; the due soon hours; the clock |
| Task reminder | reminder (with snooze), completion, recurrence, the clock |

### Followers

| When this changes | Recompute |
|---|---|
| A category's effective value | its subcategories; its direct members (tasks, global and owned notes) |
| A category's name | its subcategories and direct members (source, and the winner of a tie) |
| A category's style priority | its direct members |
| A task's effective value or source | its subtasks (not when both old and new come from its own status or tracking) |
| A task's or note's name | its subtasks or subnotes (source) |
| A task's status | its own style; the filter and sorter (`scheduler.pass`) |
| A task's tracking | its own icon |
| A note's effective value | its subnotes |
| An owner's style, an attachment | nothing |

The graph has no cycles: edges run category to subcategory, category
to member, task to subtask, note to subnote, status to own style.
Prerequisites act through completion dates, at once, outside the pass
(`_update_status()`).

### Risks

How each is handled in the built pass:

- Whether a marked object is still in the file: a task is checked (a
  set lookup) and skipped when outside; an owned note or attachment
  does not know its owner, and styling one outside the file (a
  deleted item's, a copy) is harmless, so it is not checked.
- Merge: copies share IDs; a full loop (`taskfile.merged`).
- The theme can turn dark or light for up to 1 s without its event;
  the full loop follows `system.theme_colour_changed` too.
- A failing object still reaches its followers: each object runs
  isolated, and the style events it sent before failing are followed.
- Over-marking costs work, not correctness: ancestors on date and
  tracking events, a category on its members' links.

Heard by the scheduler but read by no result, so the pass ignores
them: budget, percentage complete, planned duration and its mode,
dependencies, the mark completed setting, an attachment's location, a
category's filter and exclusive subcategories, an effort's start and
entry mode, ordering, the derived styles' events.

Questions for the review:

1. ~~The cascade ruling spreads a cascade one level per second; settle
   it all at once instead?~~ **Designer's go-ahead 2026-09-30:** at
   once, each object once in the fixed order; the ruling is superseded
   ([Ruling](#ruling-the-cascade-runs-through-the-heap)).
2. ~~Keep a full loop as a safety net (once a minute, say), or only
   the check mode during development?~~ **Ruled by designer
   2026-09-29:** no periodic full loop; it would admit the pass cannot
   cover everything. A missed follower is found (the check mode) and
   fixed.
3. ~~Worth it?~~ **Built 2026-09-30, the designer's go-ahead**
   ([Cost After](#cost-after)).
4. ~~A due reminder triggered at its second only?~~ Yes, by the
   2026-09-27 ruling: the pass at the reminder's second triggers it
   once, and again only when a pass processes the task while it is
   due.
5. ~~When to settle?~~ At the next tick, as before (within a second):
   one pass per tick, bursts of changes in one pass.
6. ~~Category membership held twice (P29): store it on one side, or
   keep both with one writer?~~ **Ruled by designer 2026-09-29:** on
   the item only; the member lookup reads the category's index, less
   the items outside the file.

---

## ID Review

Checked 2026-09-28, across the repository:

- Every task, category, note, attachment and effort gets an ID when
  created (`base.new_id()`, a random UUID), keeps it for life and saves
  it. Only reading a file sets an existing ID; undo puts back the
  same objects.
- Copies get new IDs (`__getcopystate__()` leaves the ID and the
  creation date out): copy and paste, paste as subitem, the subtasks,
  notes, attachments and efforts copied with them, a task saved as a
  template and each task made from one. The first paste after a cut
  is a move: the cut items themselves, IDs kept.
- Creation and modification dates are the clock's time with
  microseconds; different items may share one.
- The same ID in two files is the same item: Save As, Save selection,
  backups; File > Merge matches items by it; Todo.txt `tcid:` updates
  the task it names (an unknown one is skipped, never created).
- A recurring task advances in place; no new task.
- Not item IDs: wx window and menu IDs (`IdProvider`), returned when
  a window closes.

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

**Tried and dropped, 2026-09-27:** one dirty flag running the full loop
only after a change. It listened to every event, and a due reminder's
trigger every second counted as a change, so the loop never skipped.
The cascade ruling keeps the idea without that fault: only the change
events push, and a trigger is not one. An uncommitted
prototype also went further than this design (entries carrying their
task, processed per object); what stays useful from it: the
`Attribute.set()` change, the once-a-minute `[SCHEDULER]` cost line,
and debug switches to profile the first ticks and to check a skipped
tick against the full loop.
