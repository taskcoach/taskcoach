#!/usr/bin/env python

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

import os
import sys

# Initialize output tee FIRST, before any other imports that might
# produce output (especially wx/GTK which load native libraries).
# This captures all stdout/stderr to the log file.
from taskcoachlib.tee import init_tee
init_tee()

import faulthandler

# Enable faulthandler to get Python tracebacks on segfaults
# This helps debug crashes in wxPython/GTK C++ code by showing which
# Python code was executing when the crash occurred
faulthandler.enable(all_threads=True)


def _set_wayland_app_id():
    """Set GLib prgname for Wayland app_id matching.

    On Wayland, GNOME Shell uses the app_id (derived from GLib's prgname)
    to match running applications to their .desktop files for proper
    icon display. This must be called BEFORE wxPython imports GTK.

    On X11, wxPython's SetClassName() handles WM_CLASS which serves
    the same purpose.
    """
    if sys.platform != "linux":
        return

    try:
        import ctypes

        libglib = ctypes.CDLL("libglib-2.0.so.0")
        g_set_prgname = libglib.g_set_prgname
        g_set_prgname.argtypes = [ctypes.c_char_p]
        g_set_prgname.restype = None
        g_set_prgname(b"taskcoach")

        # Also set application name for display purposes
        g_set_application_name = libglib.g_set_application_name
        g_set_application_name.argtypes = [ctypes.c_char_p]
        g_set_application_name.restype = None
        g_set_application_name(b"Task Coach")
    except (OSError, AttributeError):
        pass  # GLib not available or function not found


# Set prgname before any wx/GTK imports
_set_wayland_app_id()

# Enable more detailed Python error reporting
sys.tracebacklimit = 100  # Show full tracebacks, not just last 10 frames

# Workaround for a bug in Ubuntu 10.10
os.environ["XLIB_SKIP_ARGB_VISUALS"] = "1"

import taskcoachlib.workarounds.monkeypatches


# This prevents a message printed to the console when wx.lib.masked
# is imported from taskcoachlib.widgets on Ubuntu 12.04 64 bits...
try:
    from mx import DateTime
except ImportError:
    pass


if not hasattr(sys, "frozen"):
    # These checks are only necessary in a non-frozen environment, i.e. we
    # skip these checks when run from a py2exe-fied application
    try:
        import wxversion

        wxversion.select(["2.8-unicode", "3.0"], optionsRequired=True)
    except ImportError:
        # There is no wxversion for py3
        pass

    try:
        import taskcoachlib  # pylint: disable=W0611
    except ImportError:
        # On Ubuntu 12.04, taskcoachlib is installed in /usr/share/pyshared,
        # but that folder is not on the python path. Don't understand why.
        # We'll add it manually so the application can find it.
        sys.path.insert(0, "/usr/share/pyshared")
        try:
            import taskcoachlib  # pylint: disable=W0611
        except ImportError:
            sys.stderr.write(
                """ERROR: cannot import the library 'taskcoachlib'.
Please see https://answers.launchpad.net/taskcoach/+faq/1063 
for more information and possible resolutions.
"""
            )
            sys.exit(1)


def start():
    """Process command line options and start the application."""

    # pylint: disable=W0404
    from taskcoachlib import config, application

    options, args = config.ApplicationOptionParser().parse_args()
    app = application.Application(options, args)
    if options.profile:
        import cProfile

        cProfile.runctx(
            "app.start()", globals(), locals(), filename=".profile"
        )
    else:
        app.start()


if __name__ == "__main__":
    start()
