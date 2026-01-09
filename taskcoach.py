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

# Early startup logging for debugging pythonw.exe silent failures
def _setup_startup_log():
    """Redirect stderr to a log file for debugging when run without console."""
    if sys.platform == 'win32' and not sys.stderr.isatty():
        try:
            # Log to user's LOCALAPPDATA or temp directory
            log_dir = os.environ.get('LOCALAPPDATA', os.environ.get('TEMP', '.'))
            log_path = os.path.join(log_dir, 'TaskCoach', 'startup.log')
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            sys.stderr = open(log_path, 'w', encoding='utf-8')
            print(f"Task Coach startup log: {log_path}", file=sys.stderr)
            print(f"Python: {sys.executable}", file=sys.stderr)
            print(f"Working dir: {os.getcwd()}", file=sys.stderr)
            print(f"Script: {__file__}", file=sys.stderr)
        except Exception as e:
            pass  # Can't log if we can't create the log file

_setup_startup_log()

# Fix DLL loading on Windows with Python embeddable package
# The embeddable package doesn't process .pth files by default.
# pywin32's .pth file adds DLL directories to PATH, which is required.
# We must call site.addsitedir() to process .pth files before importing wx.
if sys.platform == 'win32':
    import site
    # Find site-packages directory and process .pth files there
    python_dir = os.path.dirname(os.path.abspath(sys.executable))
    site_packages = os.path.join(python_dir, 'Lib', 'site-packages')
    if os.path.isdir(site_packages):
        site.addsitedir(site_packages)

    # Python 3.8+ also needs explicit DLL directory registration
    if sys.version_info >= (3, 8) and hasattr(os, 'add_dll_directory'):
        # Add wx package directory for wxPython DLLs
        wx_path = os.path.join(site_packages, 'wx')
        if os.path.isdir(wx_path):
            os.add_dll_directory(wx_path)
        # Add pywin32_system32 for pywin32 DLLs
        pywin32_dir = os.path.join(site_packages, 'pywin32_system32')
        if os.path.isdir(pywin32_dir):
            os.add_dll_directory(pywin32_dir)
        # Add python directory itself
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
