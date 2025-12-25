"""
Output tee for Task Coach - mirrors stdout/stderr to log file.

This module must be imported and initialized BEFORE any other imports
that might produce output (especially wx/GTK which load native libraries).

Architecture:
- Raw copy of stdout/stderr to both console and log file (like Unix tee)
- Stderr output sets the error flag for exit popup, UNLESS it matches
  a pattern in STDERR_IGNORE_PATTERNS (known harmless messages)
- No timestamps or formatting - just raw copy

Usage (in taskcoach.py, before other imports):
    from taskcoachlib.tee import init_tee
    init_tee()
"""

import os
import sys
import threading


# Patterns in stderr that should NOT trigger the error popup.
# These are known harmless messages from GTK/libraries.
# All stderr is still logged to file - this only affects the popup.
STDERR_IGNORE_PATTERNS = (
    # GTK 3.20+ layout bug - wxWidgets #17585, harmless
    "gtk_distribute_natural_allocation",
    # wxPython calls gtk_init before gtk_disable_setlocale, harmless
    "gtk_disable_setlocale",
    # Pixman rect validation, cosmetic issue
    "pixman_region32_init_rect",
    # wxPython debug messages about duplicate handlers, harmless
    "Adding duplicate image handler",
    "Adding duplicate animation handler",
    # GTK scale factor assertion on multi-monitor setups, harmless
    "gtk_widget_get_scale_factor",
    # Idle detection unavailable on KDE Wayland (no simple DBus API available)
    "Idle time detection unavailable",
    # wx.lib.combotreebox uses deprecated methods internally, harmless
    "wxPyDeprecationWarning",
    # PlateButton popup cleanup race condition in wxPython, harmless
    "PlateButton has been deleted",
)


# Module state
_log_file = None
_original_stdout_fd = None
_original_stderr_fd = None
_stdout_thread = None
_stderr_thread = None
_stop_event = None
_has_errors = False
_has_errors_lock = threading.Lock()


def _get_log_path():
    """Get the log file path matching Settings.pathToDocumentsDir()."""
    if sys.platform == 'win32':
        # Windows: use Documents folder
        home = os.environ.get('USERPROFILE', os.environ.get('HOMEPATH', '.'))
        base = os.path.join(home, 'Documents')
    elif sys.platform == 'darwin':
        # macOS: use home directory
        base = os.path.expanduser('~')
    else:
        # Linux/Unix: use home directory (matches Settings.pathToDocumentsDir)
        base = os.path.expanduser('~')

    return os.path.join(base, 'taskcoachlog.txt')


def _get_ignore_pattern(text):
    """Return the ignore pattern that matches text, or None if no match."""
    for pattern in STDERR_IGNORE_PATTERNS:
        if pattern in text:
            return pattern
    return None


def _tee_thread(pipe_read_fd, original_fd, log_file, is_stderr):
    """Thread that reads from pipe and writes to both console and log file."""
    global _has_errors

    try:
        while not _stop_event.is_set():
            try:
                data = os.read(pipe_read_fd, 4096)
                if not data:
                    break

                # Decode for pattern matching and logging
                text = data.decode('utf-8', errors='replace')

                # Write to original console
                try:
                    os.write(original_fd, data)
                except OSError:
                    pass

                # Write to log file (raw, no formatting)
                try:
                    log_file.write(text)
                    log_file.flush()
                except Exception:
                    pass

                # Set error flag for stderr, unless it matches ignore patterns or is empty
                if is_stderr:
                    # Ignore empty/whitespace-only output
                    if not text.strip():
                        pass  # Empty line, don't flag as error
                    else:
                        ignore_pattern = _get_ignore_pattern(text)
                        if ignore_pattern:
                            # Log that we're ignoring this for the error flag
                            ignore_msg = f"[TEE] Ignored for Error Popup Flag: matched '{ignore_pattern}'\n"
                            try:
                                log_file.write(ignore_msg)
                                log_file.flush()
                            except Exception:
                                pass
                            # Also write to stdout so user can see in console
                            try:
                                if _original_stdout_fd is not None:
                                    os.write(_original_stdout_fd, ignore_msg.encode('utf-8'))
                            except Exception:
                                pass
                        else:
                            # Real error - set the flag
                            with _has_errors_lock:
                                _has_errors = True

            except OSError:
                break
            except Exception:
                pass
    finally:
        try:
            os.close(pipe_read_fd)
        except Exception:
            pass


def init_tee():
    """Initialize stdout/stderr tee to log file.

    Call this as early as possible, before any imports that might
    produce output (especially wx/GTK).
    """
    global _log_file, _original_stdout_fd, _original_stderr_fd
    global _stdout_thread, _stderr_thread, _stop_event

    try:
        log_path = _get_log_path()
        _log_file = open(log_path, 'a', encoding='utf-8')
        _stop_event = threading.Event()

        # Set up stdout tee
        _original_stdout_fd = os.dup(1)
        stdout_pipe_read, stdout_pipe_write = os.pipe()
        os.dup2(stdout_pipe_write, 1)
        os.close(stdout_pipe_write)
        sys.stdout = os.fdopen(1, 'w', buffering=1)

        _stdout_thread = threading.Thread(
            target=_tee_thread,
            args=(stdout_pipe_read, _original_stdout_fd, _log_file, False),
            daemon=True
        )
        _stdout_thread.start()

        # Set up stderr tee
        _original_stderr_fd = os.dup(2)
        stderr_pipe_read, stderr_pipe_write = os.pipe()
        os.dup2(stderr_pipe_write, 2)
        os.close(stderr_pipe_write)
        sys.stderr = os.fdopen(2, 'w', buffering=1)

        _stderr_thread = threading.Thread(
            target=_tee_thread,
            args=(stderr_pipe_read, _original_stderr_fd, _log_file, True),
            daemon=True
        )
        _stderr_thread.start()

    except Exception:
        # If tee setup fails, continue without it
        pass


def shutdown_tee():
    """Shutdown the tee and return whether errors occurred."""
    global _log_file, _original_stdout_fd, _original_stderr_fd
    global _stdout_thread, _stderr_thread, _stop_event

    # Signal threads to stop
    if _stop_event is not None:
        _stop_event.set()

    # Flush and close current stdout/stderr to signal EOF to threads
    # This closes the write end of the pipes
    try:
        sys.stdout.flush()
        sys.stdout.close()
    except Exception:
        pass

    try:
        sys.stderr.flush()
        sys.stderr.close()
    except Exception:
        pass

    # Wait for threads (they should exit now that pipes are closed)
    if _stdout_thread is not None:
        _stdout_thread.join(timeout=1.0)
        _stdout_thread = None
    if _stderr_thread is not None:
        _stderr_thread.join(timeout=1.0)
        _stderr_thread = None

    # Restore original stdout
    if _original_stdout_fd is not None:
        try:
            os.dup2(_original_stdout_fd, 1)
            os.close(_original_stdout_fd)
            sys.stdout = os.fdopen(1, 'w', buffering=1)
        except Exception:
            pass
        _original_stdout_fd = None

    # Restore original stderr
    if _original_stderr_fd is not None:
        try:
            os.dup2(_original_stderr_fd, 2)
            os.close(_original_stderr_fd)
            sys.stderr = os.fdopen(2, 'w', buffering=1)
        except Exception:
            pass
        _original_stderr_fd = None

    # Close log file
    if _log_file is not None:
        try:
            _log_file.close()
        except Exception:
            pass
        _log_file = None

    # Return error status
    with _has_errors_lock:
        return _has_errors


def has_errors():
    """Check if any errors occurred (any stderr output)."""
    with _has_errors_lock:
        return _has_errors


def get_log_path():
    """Return the log file path (for error popup message)."""
    return _get_log_path()
