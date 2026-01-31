# NumPy Integration

## Table of Contents

- [Overview](#overview)
- [Usage in Task Coach](#usage-in-task-coach)
- [Subprocess Probe](#subprocess-probe)
  - [Why a Subprocess](#why-a-subprocess)
  - [Probe Flow](#probe-flow)
  - [Startup Log Output](#startup-log-output)
- [Pure-Python Fallbacks](#pure-python-fallbacks)
- [File Reference](#file-reference)
- [Related Issues](#related-issues)

---

## Overview

NumPy is an **optional dependency** used for image alpha channel operations
(icon overlay compositing). Task Coach functions correctly without it, using
pure-Python byte operations as a fallback.

NumPy is guarded by a subprocess probe at startup. If the probe fails
(missing package, incompatible CPU, broken install), all alpha operations
fall back to pure Python automatically. No user action is required.

---

## Usage in Task Coach

NumPy is used in `taskcoachlib/tools/wxhelper.py` for four image alpha
operations:

| Function | Purpose |
|----------|---------|
| `getAlphaDataFromImage()` | Read alpha channel as numpy array |
| `setAlphaDataToImage()` | Write alpha data (array, bytes, list) to image |
| `clearAlphaDataOfImage()` | Fill alpha channel with uniform value |
| `mergeImagesWithAlpha()` | Composite overlay icon onto base icon |

These are called by the icon art provider when compositing task icons
(e.g. overlaying a clock icon on a task icon during time tracking).

---

## Subprocess Probe

### Why a Subprocess

NumPy 2.4+ sets its CPU baseline to x86_64-v2 (requires SSE4.2). On older
CPUs that lack these instructions, importing numpy triggers a hardware
`ILLEGAL INSTRUCTION` fault (`SIGILL` on POSIX, `STATUS_ILLEGAL_INSTRUCTION`
/ `0xc000001d` on Windows). This is a fatal OS-level signal that **cannot be
caught** by Python's `try/except` — the process crashes before the exception
handler runs.

The only safe way to detect this is to attempt the import in a **separate
subprocess**. If the subprocess crashes, the main process remains unaffected
and disables numpy.

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
        +-- reads numpy_usable
        +-- if True:  import numpy as np
        +-- if False: np = None (use fallbacks)
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

Failed numpy (missing or incompatible):
```
[14:38:03.260] [NUMPY] Starting numpy probe
[14:38:03.260] [NUMPY] Probing numpy availability via subprocess...
[14:38:03.260] [NUMPY] Launching subprocess: import numpy; numpy.zeros(1)
[14:38:03.380] [NUMPY] Subprocess returned rc=-4
[14:38:03.380] [NUMPY] Probe FAILED (rc=-4): ...
[14:38:03.380] [NUMPY] numpy_usable = False
```

---

## Pure-Python Fallbacks

When numpy is unavailable, each function uses `bytearray`/`bytes` operations:

| Function | NumPy Path | Fallback Path |
|----------|-----------|---------------|
| `getAlphaDataFromImage()` | `np.frombuffer(data, uint8)` | Return raw bytes |
| `setAlphaDataToImage()` | `np.array` + `np.clip` + `tobytes()` | `bytearray` with pad/truncate/clip |
| `clearAlphaDataOfImage()` | `np.full(size, value, uint8)` | `bytes([value]) * size` |
| `mergeImagesWithAlpha()` | `np.maximum` on 2D arrays | Pixel loop with `max(a, b)` |

The fallback path is functionally identical but slower for large images.
For Task Coach's icon sizes (16x16, 32x32), the performance difference
is negligible.

---

## File Reference

| File | Purpose |
|------|---------|
| `taskcoachlib/tools/_numpy_probe.py` | Subprocess probe, exports `numpy_usable` |
| `taskcoachlib/tools/wxhelper.py` | Alpha operations with numpy/fallback branches |
| `taskcoachlib/application/application.py` | Early probe trigger at startup |

---

## Related Issues

- [#331 — dll loading error on Windows](https://github.com/taskcoach/taskcoach/issues/331):
  NumPy 2.4.1 crashes on AMD A6-3650 APU (SSE4a only, no SSE4.2) with
  `STATUS_ILLEGAL_INSTRUCTION` (`0xc000001d`). The x64 build fails at
  startup during numpy C-extension initialization. The x86 (32-bit) build
  and older Task Coach versions (1.4.6) are unaffected. This issue
  motivated the subprocess probe and pure-Python fallback architecture.
