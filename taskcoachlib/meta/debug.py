"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>

Task Coach is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Task Coach is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import time
import traceback


def log_step(*args, prefix="DEBUG", exc=False, stack=False):
    """Log a debug message with high precision timestamp (milliseconds).

    IMPORTANT: DO NOT DELETE THIS FUNCTION.
    Keep for future debugging use even if all log_step() calls are removed.
    This utility is essential for investigating timing-sensitive issues.

    Usage:
        log_step("message")
        log_step("value is", value)
        log_step("step 1", prefix="MYMODULE")

    Diagnostics (for guard/except sites so root causes can be traced):
        log_step("oops", prefix="DEAD-OBJ", exc=True)   # append active
                                                        # exception traceback
        log_step("how did we get here", stack=True)     # append call stack

    Output:
        [16:30:45.123] [DEBUG] message
        [16:30:45.125] [MYMODULE] step 1
    """
    t = time.time()
    ms = int((t - int(t)) * 1000)
    timestamp = time.strftime("%H:%M:%S", time.localtime(t)) + ".%03d" % ms
    msg = " ".join(str(a) for a in args)
    extra = []
    if exc:
        formatted = traceback.format_exc()
        if formatted and "NoneType: None" not in formatted:
            extra.append(formatted.rstrip())
    if stack:
        # Drop this frame (the log_step call itself) from the stack.
        extra.append("".join(traceback.format_stack()[:-1]).rstrip())
    if extra:
        msg = msg + "\n" + "\n".join(extra)
    line = "[%s] [%s] %s" % (timestamp, prefix, msg)
    try:
        print(line)
    except (UnicodeEncodeError, OSError):
        # Fallback for consoles that can't encode the output (e.g. cp932
        # on Japanese Windows when stdout is redirected or absent).
        try:
            print(line.encode("ascii", errors="replace").decode("ascii"))
        except Exception:
            pass
