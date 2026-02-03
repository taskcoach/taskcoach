"""Subprocess probe for numpy diagnostic logging at startup.

Spawns a short-lived subprocess to test numpy import and a basic
operation. The result is logged with [NUMPY] prefix to aid
troubleshooting from user-submitted logs.

NumPy is pinned to 1.x (>=1.26,<2) in all pip-based builds, which
avoids the SSE4.2 baseline introduced in NumPy 2.4+. This probe is
therefore informational only — it does not gate any runtime behavior.

Historical context: NumPy 2.4+ requires SSE4.2 (x86_64-v2 baseline).
On older CPUs (e.g. AMD A6-3650 with SSE4a only), importing numpy 2.4+
triggers a fatal ILLEGAL INSTRUCTION fault that cannot be caught by
try/except. See issues #331 and #338.

See docs/NUMPY.md for full documentation.
"""

import sys
import subprocess
from taskcoachlib.meta.debug import log_step

_PREFIX = "NUMPY"


def _probe():
    """Test numpy in a subprocess. Returns True if functional."""
    log_step("Probing numpy availability via subprocess...", prefix=_PREFIX)
    try:
        log_step("Launching subprocess: import numpy; numpy.zeros(1)", prefix=_PREFIX)
        result = subprocess.run(
            [sys.executable, "-c",
             "import numpy; numpy.zeros(1); numpy.array([1,2,3]).sum()"],
            capture_output=True,
            timeout=10,
        )
        log_step(f"Subprocess returned rc={result.returncode}", prefix=_PREFIX)
        if result.returncode == 0:
            log_step("Probe OK — numpy is functional", prefix=_PREFIX)
            return True
        # POSIX: SIGILL gives returncode -4
        # Windows: nonzero returncode
        stderr = result.stderr.decode(errors="replace").strip()
        short = stderr[:200] if stderr else "(no stderr)"
        log_step(f"Probe FAILED (rc={result.returncode}): {short}",
                 prefix=_PREFIX)
        return False
    except subprocess.TimeoutExpired:
        log_step("Probe FAILED — subprocess timed out", prefix=_PREFIX)
        return False
    except FileNotFoundError:
        log_step("Probe FAILED — Python executable not found", prefix=_PREFIX)
        return False
    except Exception as exc:
        log_step(f"Probe FAILED — {exc}", prefix=_PREFIX)
        return False


log_step("Starting numpy probe", prefix=_PREFIX)
numpy_usable = _probe()
log_step(f"numpy_usable = {numpy_usable}", prefix=_PREFIX)
