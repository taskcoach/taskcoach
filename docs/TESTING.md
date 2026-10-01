# Testing

The unit and integration tests in `tests/` are a regression net; a
change is verified in the full app
([DEVELOPMENT.md](DEVELOPMENT.md#verifying-changes)).

## Certified Platform

The suite is written for, and passes on, one platform:

| Component | Version |
|-----------|---------|
| OS | Linux (Debian 13 trixie) |
| Display | X11, under `xvfb-run` |
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
xvfb-run -a ../.venv/bin/python test.py unittests/domainTests/TaskTest.py
```

The catalog, every test file, each in its own process as when run
alone (`run_catalog()`): one line per file, the failures' reports and
a summary.

```
xvfb-run -a ../.venv/bin/python test.py --alltests
```

Without `--alltests` it runs the unit tests; `--help` lists the parts.
`xvfb-run` keeps the test windows off the desktop.

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
