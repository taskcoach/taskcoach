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

Each run starts its own X display, a private Xvfb, and stops it at
the end (`start_display()`): the tests never use the desktop's, and
need no `xvfb-run`. Xvfb picks a free display number itself
(`-displayfd`), so runs side by side never take the same one (with
`xvfb-run -a` two could), and does not reset when its last client
leaves (`-noreset`): a reset can drop a client still connecting, the
likely cause of P90 below. `TASKCOACH_TEST_DISPLAY=:61` runs on a
given display instead, to watch the tests.

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

## Other Platforms

The catalog is today's shared part: `unittests/`, `integrationtests/`
and `languagetests/`, which hold for every platform. Tests that hold
on one platform only (the tray's minimize, a popup's position on
Wayland) will form that platform's part, in a directory of its own,
with its own certified versions, when work is done there; how the
parts are chosen is decided then. The existing branches for Windows
and macOS in the shared tests (`test.skipOnPlatform()`,
`operating_system` checks) never run under this entry point.
