# NumPy Integration

## Table of Contents

- [Overview](#overview)
- [Version Pin](#version-pin)
- [Usage in Task Coach](#usage-in-task-coach)
- [Diagnostic Probe](#diagnostic-probe)
  - [Why a Subprocess](#why-a-subprocess)
  - [Probe Flow](#probe-flow)
  - [Startup Log Output](#startup-log-output)
- [File Reference](#file-reference)
- [Related Issues](#related-issues)

---

## Overview

NumPy is a **required dependency** used for image alpha channel operations
(icon overlay compositing). It is pinned to the 1.x series (`>=1.26,<2`) in
all pip-based builds to avoid the SSE4.2 CPU requirement introduced in
NumPy 2.4+.

A subprocess probe runs at startup for **diagnostic logging only** — it does
not gate any runtime behavior.

---

## Version Pin

NumPy 2.4+ raised its CPU baseline to x86_64-v2 (requires SSE4.2, SSSE3,
SSE4.1, POPCNT). On older CPUs lacking these instructions, importing
NumPy 2.4+ triggers a fatal `ILLEGAL INSTRUCTION` fault that cannot be
caught by Python's `try/except`.

NumPy 1.26.4 is the final 1.x release (February 2024). It supports
Python 3.9–3.12, has no SSE4.2 requirement, and provides identical
behavior for the uint8 array operations used by Task Coach.

The version pin is applied in the **pip-based build workflows only**:

| File | Pin |
|------|-----|
| `.github/workflows/build-windows.yml` | `"numpy>=1.26,<2"` |
| `.github/workflows/build-appimage.yml` | `"numpy>=1.26,<2"` |
| `.github/workflows/build-macos.yml` | `"numpy>=1.26,<2"` |

The pin is intentionally **not** in `setup.py` because `setup.py` dependencies
are auto-converted to RPM/deb package requirements. Distro builds use system
packages (`python3-numpy`, `python-numpy`) which are version-controlled by the
distro, and a `<2` constraint would conflict with distros shipping numpy 2.x.

---

## Usage in Task Coach

NumPy is used in `taskcoachlib/tools/wxhelper.py` for four image alpha
operations:

| Function | Purpose |
|----------|---------|
| `getAlphaDataFromImage()` | Read alpha channel as numpy uint8 array |
| `setAlphaDataToImage()` | Write alpha data (array, bytes, list) to image |
| `clearAlphaDataOfImage()` | Fill alpha channel with uniform value |
| `mergeImagesWithAlpha()` | Composite overlay icon onto base icon |

These are called by the icon art provider (`taskcoachlib/gui/artprovider.py`)
when compositing task icons (e.g. overlaying a clock icon on a task icon
during time tracking).

---

## Diagnostic Probe

### Why a Subprocess

Even though NumPy is pinned to 1.x, the probe is retained for diagnostic
traceability. It confirms numpy is functional in the deployed environment
and logs the result for troubleshooting from user-submitted logs.

Historical context: NumPy 2.4+ triggers a hardware `ILLEGAL INSTRUCTION`
fault (`SIGILL` on POSIX, `STATUS_ILLEGAL_INSTRUCTION` / `0xc000001d` on
Windows) on CPUs lacking SSE4.2. This is a fatal OS-level signal that
**cannot be caught** by Python's `try/except` — the process crashes before
the exception handler runs. The only safe way to detect this is a separate
subprocess.

### Probe Flow

```
Application startup
  |
  +-- _log_required_packages()          (logs numpy version)
  |
  +-- import _numpy_probe               (triggers probe)
  |     |
  |     +-- subprocess: python -c "import numpy; numpy.zeros(1)"
  |     |     |
  |     |     +-- exit 0  --> numpy_usable = True
  |     |     +-- crash   --> numpy_usable = False
  |     |
  |     +-- log_step(result, prefix="NUMPY")
  |
  +-- (later) wxhelper.py imported
        |
        +-- import numpy as np          (direct import, no probe check)
```

### Startup Log Output

Working numpy:
```
[14:38:03.260] [NUMPY] Starting numpy probe
[14:38:03.260] [NUMPY] Probing numpy availability via subprocess...
[14:38:03.260] [NUMPY] Launching subprocess: import numpy; numpy.zeros(1)
[14:38:03.380] [NUMPY] Subprocess returned rc=0
[14:38:03.380] [NUMPY] Probe OK — numpy is functional
[14:38:03.380] [NUMPY] numpy_usable = True
```

Failed numpy (diagnostic information for troubleshooting):
```
[14:38:03.260] [NUMPY] Starting numpy probe
[14:38:03.260] [NUMPY] Probing numpy availability via subprocess...
[14:38:03.260] [NUMPY] Launching subprocess: import numpy; numpy.zeros(1)
[14:38:03.380] [NUMPY] Subprocess returned rc=-4
[14:38:03.380] [NUMPY] Probe FAILED (rc=-4): ...
[14:38:03.380] [NUMPY] numpy_usable = False
```

---

## File Reference

| File | Purpose |
|------|---------|
| `taskcoachlib/tools/_numpy_probe.py` | Subprocess probe, diagnostic logging |
| `taskcoachlib/tools/wxhelper.py` | Alpha operations using numpy |
| `taskcoachlib/gui/artprovider.py` | Icon compositing using wxhelper + numpy |
| `taskcoachlib/application/application.py` | Triggers probe at startup |

---

## Related Issues

- [#331 — dll loading error on Windows](https://github.com/taskcoach/taskcoach/issues/331):
  NumPy 2.4.1 crashes on AMD A6-3650 APU (SSE4a only, no SSE4.2) with
  `STATUS_ILLEGAL_INSTRUCTION` (`0xc000001d`). Motivated the subprocess
  probe and the decision to pin NumPy to 1.x.

- [#338 — Refactor editor duration sync, add numpy safety probe](https://github.com/taskcoach/taskcoach/pull/338):
  Original implementation of the subprocess probe and pure-Python fallbacks.
  Fallbacks were later removed when NumPy was pinned to 1.x.
