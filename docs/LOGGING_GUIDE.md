# Logging Guide

How Task Coach logs, and what to read when verifying a change in the
full app ([DEVELOPMENT.md](DEVELOPMENT.md#verifying-changes)).

## Output

Everything goes to standard output: start Task Coach from a terminal
(`./taskcoach-run.sh`) to see it. Nothing writes a log file. On GTK,
wx's own log messages go to standard error instead of popup dialogs
(`Application.start()`).

- `log_step(*args, prefix="DEBUG", exc=False, stack=False)`
  (`taskcoachlib/meta/debug.py`): one line,
  `[HH:MM:SS.mmm] [PREFIX] message`. `exc=True` appends the active
  exception's traceback, `stack=True` the call stack. The millisecond
  timestamps show order and timing.
- `log_message(msg)` (`taskcoachlib/application/application.py`): a
  plain line, for the startup report (versions, platform, distro,
  locale, packages).

Log messages are ASCII only: a non-ASCII character (an em-dash, say)
fails on consoles such as cp932 on Windows.

## Verifying a change

Run the app in a terminal, exercise the change, and read the lines of
the areas it touches (below). For a UI, timing or ordering problem,
add `log_step()` calls at the points in question; for layout,
placement and drawing, call the geometry trace
(`taskcoachlib/meta/geometry_trace.py`, `[GEOM]`) from the code under
investigation. Remove both once the cause is found
([Diagnosing](DEVELOPMENT.md#diagnosing)).

## Prefixes

Always on, unless a toggle is named.

Startup:

- no prefix: the startup report.
- `[i18n]`: language and locale set up ([LOCALE.md](LOCALE.md)).
- `[DISPLAY]`: GTK version, displays and scaling.
- `[TRAY]`: tray icon and AppIndicator setup, tray clicks and menu
  ([SYSTEM_TRAY.md](SYSTEM_TRAY.md)).
- `[IDLE]`: the idle-detection backend, only while the idle notice is
  on ([IDLE.md](IDLE.md)).

Changes:

- `[UNDO]`: each step recorded, undone, redone or rolled back, with
  the fields and lists it changed; a stored change made outside a step
  ([UNDO_REDO.md](UNDO_REDO.md#actions)).
- `[SCHEDULER]`: once a minute when passes ran (ticks, passes, cost);
  a clock set back. `TASKCOACH_SCHEDULER_CHECK=1` runs the full loop
  after every pass and logs each change the pass missed
  ([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md)).
- `[GEOMETRY]`: each window's restore steps, until it has settled
  ([WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md)).
- `[FILE]`, `[LOCK]`, `[XML]`, `[TEMPLATE]`, `[SETTINGS]`: autosave,
  file locks, reading task files and templates, the INI settings.
- `[THEME]`: how the system theme was found, and its changes.
- `[COMMAND]`: a command held back because it opened the same window
  under a second ago, once per opening
  ([MENUS.md](MENUS.md#the-same-window-once-a-second)).

Guards and errors:

- `[LATER]`: a deferred call that failed, with where it was
  scheduled. `TASKCOACH_LATER_LOG=1` also logs each call skipped
  because its owner is gone ([DEFERRED_CALLS.md](DEFERRED_CALLS.md)).
- `[CRASH_GUARD]`: a `wx.CallAfter` to a destroyed object blocked, a
  timer tick that reached a destroyed owner
  ([CRASH_GUARD.md](CRASH_GUARD.md)).
- `[DEAD-OBJ]`, `[OBSERVER]`: a call reaching a destroyed window, an
  observer that raised
  ([PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md)).
- `[APPEARANCE-BUG]`: a broken invariant; each is a bug.

The other prefixes name their module and mostly log errors and
fallbacks: `[ICON]`, `[SPELL]`, `[EDITOR]`, `[SYNC]`, `[DURATION]`,
`[EFFORT]`, `[RECUR]`, `[FILTER]`, `[SORTER]`, `[RENDER]`,
`[TEXTCTRL]`, `[PREFS]`, `[AUI]`, `[MAIL]` (a Thunderbird message
dropped as its URI, [EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md#the-drop)). Find a prefix's sources with
`grep -rn 'prefix="NAME"' taskcoachlib`.
