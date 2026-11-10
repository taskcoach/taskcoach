# Testing

The unit and integration tests in `tests/` are a regression net; a
change is verified in the full app
([DEVELOPMENT.md](DEVELOPMENT.md#verifying-changes)). The tests and
their scripts are the worker's to keep working, testing the app
completely and correctly, with no ruling asked (ruled by the decider,
[DEVELOPMENT.md](DEVELOPMENT.md#working-plan) 5).

## Certified Platform

The suite is written for, and passes on, one platform:

| Component | Version |
|-----------|---------|
| OS | Linux (Debian 13 trixie) |
| Display | X11, the run's own Xvfb |
| Python | 3.13.5 |
| wxPython | 4.2.3 |
| wxWidgets | 3.2.8 |
| GTK | 3.24.49 |

Its results certify that platform only: most tests are meant to hold
everywhere, but their expected values follow this platform's widgets,
events and timing, and no other platform has run them.

The entry point, `tests/test.py`, checks the platform before running
(`CERTIFIED`, `check_platform()`): it prints the certified platform,
or stops and lists each component that differs. A new version is
certified on purpose: run the catalog on it, fix what fails, then
change `CERTIFIED` and the table above in the same commit.

## Running

From `tests/`, one file:

```
../.venv/bin/python test.py unittests/domainTests/TaskTest.py
```

Each run starts its own X display, a private Xvfb, and stops it at the
end (`start_display()`): the tests never use the desktop's, and need
no `xvfb-run`. It stops after wx's own clean-up: `wx` is imported once
the display runs, so wx's exit handler runs first. Stopped before it,
a file run alone that used the clipboard would end with status 1 after
all its tests passed (GTK exits on the X error of the clipboard's
clean-up). Xvfb picks a free display number itself (`-displayfd`), so
runs side by side never take the same one (with `xvfb-run -a` two
could), and does not reset when its last client leaves (`-noreset`): a
reset can drop a client still connecting, the likely cause of P90
below. `TASKCOACH_TEST_DISPLAY=:61` runs on a given display instead,
to watch the tests.

The catalog, every test file, each in its own process as when run
alone (`run_catalog()`): one line per file, the failures' reports and
a summary. A file that fails before any test also gets the display's
state (`display_report()`): its socket, key and lock owner, whether
`xdpyinfo` connects, and the load; so does the runner, or a file,
when its `wx.App` finds no display, with the Xvfb's last output.
Under `xvfb-run` a file, and once the runner itself, now and then
could not reach the display (P90 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues));
it is not run again, so a cause left would show.

```
../.venv/bin/python test.py --alltests
```

Without `--alltests` it runs the unit tests; `--help` lists the parts.

`--profile` runs the files given in one process under `cProfile`, so
the report covers them together (`--help` lists its sort and limit
options). A failing test exits 1 with no report, as a run without it.

An error raised inside an event handler fails the test it happens in
(`TestCase.run()`, `HarnessTest`). wx prints such an error and goes
on, so without this the test passes, as the app shows nothing: P252
and P254 in
[REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md#found-2026-10-09).

A test that no longer matches the app and needs a rewrite is marked
`@test.stale("reason")`; `grep -rn "test.stale" tests` lists them.

Two helpers show what a run on Linux does not by itself:

- `test.TimeLimit(seconds)` fails a test whose Python code runs longer
  (a hang), also when the code catches its `TimeoutError`.
- `test.NavigateAsWindowsAndMac(focus)` makes `Navigate()` send the
  move as wx does on Windows and macOS: an event to the window's
  parent, from the focus. wxGTK's is native and sends none.

## Writing Tests

- **Test the outcome asked for**, never the call chosen to get it: a
  look by its rendered pixels against the reference element, a
  behaviour by the state the user sees. A test rewritten for a new
  approach must still fail on what the user would call broken.
- **New behaviour fails before and passes after:** run the new test
  on the old revision in a scratch copy (a `git worktree` or
  `git show REV:path`), never through `git stash`.
- **Never the user's session:** each run has its own display, XDG
  folders and no session bus (`start_display()`). A test mocks every
  keyring function the code can call, not only the one it tests: a
  real call stores into, or opens a wizard on, the desktop's keyring.

## Other Platforms

The catalog is today's shared part: `unittests/`, `integrationtests/`
and `languagetests/`, which hold for every platform. Tests that hold
on one platform only (the tray's minimize, a popup's position on
Wayland) will form that platform's part, in a directory of its own,
with its own certified versions, when work is done there; how the
parts are chosen is decided then. The existing branches for Windows
and macOS in the shared tests (`test.skipOnPlatform()`,
`operating_system` checks) never run under this entry point.

## Editor Check

`tools/check_editors.py` opens each kind of editor on a sample file,
as the app opens it, with the focus in the main window's list: a task,
a new task, two tasks, a category, a note (its preview showing), an
attachment and an effort; then a task again with saved tabs that
cannot be read, and with its views' toolbars emptied, as a long-time
user's settings may hold them. It shows each one, selects each page,
focuses each field as a click does, tabs through the fields both ways,
then closes it. A problem is an error, an editor off every display,
the focus leaving the editor or moving on by itself, or an undo step
left by looking through it; a hang prints every thread's stack and
ends the run. A message box is reported, not shown: no one clicks it
on a build machine. On GitHub Actions each problem also shows on the
run's page, which needs no sign-in, unlike its log. The sample's items
are as the app makes them: a stored value an older release left is
corrected when its editor first opens, as ruled
([DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md#stored-duration)).

The suite runs it on the certified platform (`EditorCheckTest`). The
macOS and Windows builds run a copy with the built app's own Python
and files before packaging, because some faults show on one platform
only. On macOS the run writes no bytecode cache, since a file added
to the signed app breaks its signature
([MACOS.md](MACOS.md#keeping-the-signature-valid)). Where the app has
no focus (a build machine's app in the background) the focus steps
are skipped and say so. wxGTK loses track of a choice tabbed into
inside a panel; the walk ends there and says so.

## App Checks

A change is verified in the full app
([DEVELOPMENT.md](DEVELOPMENT.md#verifying-changes)) on a display of
its own: a click on the desktop cannot change the result, and the
check cannot touch the desktop's session, settings or files.

- **The display:** `Xvfb :61 -screen 0 1600x1000x24 -nolisten tcp
  -noreset`, with a window manager on it (openbox with the desktop's
  own configuration, so the focus behaves as there). Both are stopped
  by their process IDs once the checks are done.
- **A fresh folder per launch**, outside the repository: `HOME`,
  `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME`,
  `XDG_STATE_HOME` and `XDG_RUNTIME_DIR` inside it, and a copy of the
  task file, opened by name:

  ```
  DISPLAY=:61 NO_AT_BRIDGE=1 DBUS_SESSION_BUS_ADDRESS=unix:path=<folder>/none \
      .venv/bin/python -u taskcoach.py <folder>/task.tsk
  ```

  `-u` shows the log as it is written. With the real `HOME` and no
  settings, a first run opens `~/Documents/TaskCoach/Welcome.tsk`, the
  user's own.
- **No real session bus:** the address above leads nowhere. A check
  that needs one (the tray, the keyring) starts a private bus from a
  configuration with no service directories, with `DISPLAY=:61`, so
  nothing (a keyring wizard, the portals) is started on the desktop.
- **Never a tracked `.tsk`**, nor the decider's own task file:
  autosave writes every change back. `git status -- '*.tsk'` after a
  session.
- **Driving it:** `xdotool` with `DISPLAY=:61`. The sample file opens
  a reminder at start, and again 5 minutes after a snooze: dismiss it
  first. A dialog is closed with its own button; closing its X window
  destroys it under GTK (criticals in the log). Window names match
  case-sensitively. A drag needs pauses between its moves, or the drop
  is cancelled. An export or save dialog's folder is read before Save:
  some open in `HOME`. `tools/fake_mail_drag.py` runs with `HOME` in
  the scratch folder and is stopped with a plain `kill`, which removes
  its files.
- **Stopping the app:** by its recorded process ID, `kill -9` for a
  scratch copy (a plain `kill` waits on "save changes?" when anything
  is unsaved); never by name: `pkill openbox` also stops the
  desktop's window manager. No Task Coach is left running before the
  next launch.
- **Before and after:** the old revision in a `git worktree` or a
  `git archive` copy, never `git stash`. Each copy and folder is
  deleted once its check is recorded (a temporary folder may be held
  in memory); a prototype is kept as a patch.
- **Scripts outside the repository** import the installed
  `taskcoachlib`, an older release, unless `PYTHONPATH` names the
  repository.
- **Another language** without root: `localedef -i fr_FR -f UTF-8
  <dir>/fr_FR.UTF-8`, then run with `LANG=fr_FR.UTF-8 LOCPATH=<dir>`.
- **A drawing sequence:** record the display (`ffmpeg -f x11grab
  -framerate 60 -i :61 -frames:v 180 -copyts -c:v ffv1 out.mkv`), take
  each frame's time from `ffprobe -show_entries frame=pts_time`, and
  line the frames up with the app's log
  ([RENDERING_SPEED.md](RENDERING_SPEED.md#how-it-was-measured)).
  Where the time goes: `py-spy record -p <pid> -f raw`, with no
  overhead in the app.
