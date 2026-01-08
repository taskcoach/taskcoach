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

# Fix DLL loading on Windows with Python 3.8+
# Python 3.8 changed DLL search behavior - PATH is no longer searched.
# We must explicitly add the wx package directory so wxPython DLLs can be found.
# This must happen BEFORE importing wx (which happens in monkeypatches).
if sys.platform == 'win32' and sys.version_info >= (3, 8):
    if hasattr(os, 'add_dll_directory'):
        # Find wx package in site-packages
        for path in sys.path:
            wx_path = os.path.join(path, 'wx')
            if os.path.isdir(wx_path):
                os.add_dll_directory(wx_path)
                break
        # Also add the python directory itself (for embeddable package)
        python_dir = os.path.dirname(sys.executable)
        if os.path.isdir(python_dir):
            os.add_dll_directory(python_dir)

# TEMPORARILY DISABLED: TEE stdout/stderr redirection to log file
# This code uses os.dup2() to redirect file descriptors to a pipe, which
# may cause issues on some systems. Until further testing, logging goes
# directly to console. Users should run Task Coach from a terminal to see output.
#
# from taskcoachlib.tee import init_tee
# init_tee()

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

# Apply runtime patches (e.g., hypertreelist, inspect.getargspec)
import taskcoachlib.workarounds.monkeypatches


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
