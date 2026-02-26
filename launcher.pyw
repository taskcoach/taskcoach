#!/usr/bin/env pythonw
"""
Task Coach Launcher for Windows

This launcher script ensures the proper environment is set up before starting
Task Coach. It handles:
1. Setting the correct working directory
2. Setting up Python paths for embeddable package
3. Error handling with logging for silent failures

Use this as the entry point instead of taskcoach.py when launching from
Start Menu or desktop shortcuts on Windows.
"""

import os
import sys
import traceback
from datetime import datetime

# When running with pythonw.exe, sys.stderr and sys.stdout are None.
# This causes issues with code that tries to write to them.
# Redirect to devnull to prevent crashes.
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')

# Save a duplicate of stderr's file descriptor before anything can lose it.
# When Python hits RecursionError the stack is exhausted and even resolving
# sys.stderr requires a Python frame, so the default excepthook prints
# "lost sys.stderr" instead of the traceback.  Writing to the saved fd via
# os.write() is a C-level call that needs no extra stack frames.
_stderr_fd = os.dup(sys.stderr.fileno()) if sys.stderr and hasattr(sys.stderr, 'fileno') else None

def _robust_excepthook(exc_type, exc_value, exc_tb):
    """Write tracebacks to the saved stderr fd so they survive stack exhaustion."""
    try:
        lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        text = "".join(lines)
    except Exception:
        text = f"{exc_type.__name__}: {exc_value}\n"
    if _stderr_fd is not None:
        try:
            os.write(_stderr_fd, text.encode("utf-8", errors="replace"))
            return
        except OSError:
            pass
    # Last resort: try sys.stderr normally
    try:
        sys.stderr.write(text)
    except Exception:
        pass

sys.excepthook = _robust_excepthook

def get_log_path():
    """Get path for startup log file."""
    log_dir = os.environ.get('LOCALAPPDATA', os.environ.get('TEMP', '.'))
    return os.path.join(log_dir, 'TaskCoach', 'startup.log')

def log_message(msg, log_file=None):
    """Write a message to the log file and stdout if available."""
    if log_file is None:
        log_file = get_log_path()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted = f"[{timestamp}] {msg}"
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(formatted + "\n")
    except Exception:
        pass  # Can't log if we can't write
    try:
        if sys.stdout and sys.stdout.name != os.devnull:
            print(formatted)
    except Exception:
        pass

def show_error_dialog(title, message):
    """Show a Windows message box with error details."""
    try:
        import ctypes
        MB_OK = 0x0
        MB_ICONERROR = 0x10
        ctypes.windll.user32.MessageBoxW(0, message, title, MB_OK | MB_ICONERROR)
    except Exception:
        pass  # If we can't show dialog, we've already logged

def main():
    log_path = get_log_path()

    # Clear log at startup
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"Task Coach Launcher Log\n")
            f.write(f"Started: {datetime.now()}\n")
            f.write(f"=" * 50 + "\n\n")
    except Exception:
        pass

    log_message(f"Python executable: {sys.executable}")
    log_message(f"Python version: {sys.version}")
    log_message(f"Script path: {__file__}")

    # Get the directory containing this launcher script
    # This should be the TaskCoach installation directory
    if getattr(sys, 'frozen', False):
        # Running as compiled
        app_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        app_dir = os.path.dirname(os.path.abspath(__file__))

    log_message(f"Application directory: {app_dir}")
    log_message(f"Current working directory: {os.getcwd()}")

    # Change to application directory - this is critical for relative paths
    os.chdir(app_dir)
    log_message(f"Changed working directory to: {os.getcwd()}")

    # Ensure app_dir is in Python path
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
        log_message(f"Added {app_dir} to sys.path")

    # For Windows embeddable package, ensure site-packages is processed
    if sys.platform == 'win32':
        import site
        python_dir = os.path.dirname(os.path.abspath(sys.executable))
        site_packages = os.path.join(python_dir, 'Lib', 'site-packages')
        if os.path.isdir(site_packages):
            site.addsitedir(site_packages)
            log_message(f"Added site-packages: {site_packages}")

        # Python 3.8+ needs explicit DLL directory registration
        if sys.version_info >= (3, 8) and hasattr(os, 'add_dll_directory'):
            wx_path = os.path.join(site_packages, 'wx')
            if os.path.isdir(wx_path):
                os.add_dll_directory(wx_path)
                log_message(f"Added DLL directory: {wx_path}")
            pywin32_dir = os.path.join(site_packages, 'pywin32_system32')
            if os.path.isdir(pywin32_dir):
                os.add_dll_directory(pywin32_dir)
                log_message(f"Added DLL directory: {pywin32_dir}")
            os.add_dll_directory(python_dir)
            log_message(f"Added DLL directory: {python_dir}")

    # Log sys.path for debugging
    log_message(f"sys.path: {sys.path}")

    # Try to import and run taskcoach
    try:
        log_message("Attempting to import taskcoachlib...")
        import taskcoachlib
        log_message(f"taskcoachlib imported from: {taskcoachlib.__file__}")

        log_message("Importing faulthandler...")
        import faulthandler
        faulthandler.enable(all_threads=True)
        log_message("faulthandler enabled")

        log_message("Importing taskcoachlib.workarounds.monkeypatches...")
        import taskcoachlib.workarounds.monkeypatches
        log_message("Monkeypatches applied")

        log_message("Importing config and application...")
        from taskcoachlib import config, application

        log_message("Parsing command line options...")
        # Pass through any command line arguments (e.g., .tsk file paths)
        # sys.argv[0] is launcher.pyw, rest are passed through to taskcoach
        log_message(f"sys.argv: {sys.argv}")
        options, args = config.ApplicationOptionParser().parse_args()
        log_message(f"Options parsed: {options}")
        log_message(f"Args: {args}")

        log_message("Creating application instance...")
        app = application.Application(options, args)
        log_message("Application created, starting main loop...")

        # Clear the log message since we're successfully starting
        log_message("SUCCESS: Application starting main loop")

        app.start()

    except ImportError as e:
        error_msg = f"Import error: {e}\n\n{traceback.format_exc()}"
        log_message(f"IMPORT ERROR:\n{error_msg}")
        show_error_dialog("Task Coach - Import Error",
            f"Failed to import required module:\n\n{e}\n\nSee log file:\n{log_path}")
        sys.exit(1)

    except Exception as e:
        error_msg = f"Startup error: {e}\n\n{traceback.format_exc()}"
        log_message(f"STARTUP ERROR:\n{error_msg}")
        show_error_dialog("Task Coach - Startup Error",
            f"An error occurred during startup:\n\n{e}\n\nSee log file:\n{log_path}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # Last resort error handling
        log_message(f"FATAL ERROR: {e}\n{traceback.format_exc()}")
        show_error_dialog("Task Coach - Fatal Error", str(e))
        sys.exit(1)
