# -*- coding: utf-8 -*-

import sys
import os
import inspect
import weakref

# =============================================================================
# wxPython hypertreelist Import Hook
# =============================================================================
# This import hook redirects imports of wx.lib.agw.hypertreelist to
# our bundled copy, on every wxPython version: it has the row
# background fixes that wxPython < 4.2.4 lacks (TR_FULL_ROW_HIGHLIGHT,
# TR_FILL_WHOLE_COLUMN_BACKGROUND) and Task Coach's own changes, such
# as the macOS colour checks and column resizing.
#
# The patched file is bundled at: taskcoachlib/patches/hypertreelist.py
# This works for all installation methods (pip, deb, rpm, Windows, macOS).
#
# For details, see: docs/CRITICAL_WXPYTHON_PATCH.md
# =============================================================================

from importlib.abc import MetaPathFinder
from importlib.util import spec_from_file_location


def _find_patched_hypertreelist():
    """Find the patched hypertreelist.py file.

    Returns the path to the patched file, or None if not found.
    The file is located relative to this module, so it works regardless
    of installation method (pip, deb, rpm, source, etc.).
    """
    # Path relative to this file: workarounds/ -> taskcoachlib/ -> patches/
    this_dir = os.path.dirname(os.path.abspath(__file__))
    taskcoachlib_dir = os.path.dirname(this_dir)
    patch_path = os.path.join(taskcoachlib_dir, "patches", "hypertreelist.py")

    if os.path.exists(patch_path):
        return patch_path

    return None


class HyperTreeListPatchFinder(MetaPathFinder):
    """Import hook to replace wx.lib.agw.hypertreelist with patched version."""

    def __init__(self, patched_file_path):
        self.patched_file_path = patched_file_path

    def find_spec(self, fullname, path, target=None):
        if fullname == "wx.lib.agw.hypertreelist":
            return spec_from_file_location(fullname, self.patched_file_path)
        return None


def _install_hypertreelist_hook():
    """Install the import hook if patched file is available and needed."""
    patched_path = _find_patched_hypertreelist()
    if patched_path is None:
        return  # No patched file found, use system version

    # Check if hook is already installed
    for finder in sys.meta_path:
        if isinstance(finder, HyperTreeListPatchFinder):
            return  # Already installed

    # Install the hook at position 0 (highest priority)
    sys.meta_path.insert(0, HyperTreeListPatchFinder(patched_path))


# Install the hook before wx is imported
_install_hypertreelist_hook()

# =============================================================================
# Other Monkeypatches
# =============================================================================

import wx
import wx.siplib
from collections import namedtuple
from wx.core import Window

try:
    inspect.getargspec
except AttributeError:
    ArgSpec = namedtuple("ArgSpec", "args varargs keywords defaults")

    # Workaround for getargspec() missing inspect.getargspec() for python3.11 or later
    def getargspec(func):
        """Get the names and default values of a function's parameters.

        A tuple of four things is returned: (args, varargs, keywords, defaults).
        'args' is a list of the argument names, including keyword-only argument names.
        'varargs' and 'keywords' are the names of the * and ** parameters or None.
        'defaults' is an n-tuple of the default values of the last n parameters.

        This function is deprecated, as it does not support annotations or
        keyword-only parameters and will raise ValueError if either is present
        on the supplied callable.

        For a more structured introspection API, use inspect.signature() instead.

        Alternatively, use getfullargspec() for an API with a similar namedtuple
        based interface, but full support for annotations and keyword-only
        parameters.

        Deprecated since Python 3.5, use `inspect.getfullargspec()`.
        """
        from inspect import getfullargspec

        args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, ann = (
            getfullargspec(func)
        )
        if kwonlyargs or ann:
            raise ValueError(
                "Function has keyword-only parameters or annotations"
                ", use inspect.signature() API which can support them"
            )
        return ArgSpec(args, varargs, varkw, defaults)

    inspect.getargspec = getargspec

Window_SetSizeOld = Window.SetSize


def Window_SetSizeNew(self, *args, **kw):
    """
    SetSize(x, y, width, height, sizeFlags=SIZE_AUTO)
    SetSize(rect)
    SetSize(size)
    SetSize(width, height)

    Sets the size of the window in pixels.

    This monkey patch fixed the Gtk-CRITICAL **: 21:21:53.043:
    gtk_widget_set_size_request: assertion 'height >= -1' failed
    """
    if len(args) <= 1:
        arg = args[0]
        if arg is wx.Size:
            width = 0 if arg.Width < 0 else arg.Width
            height = 0 if arg.Height < 0 else arg.Height
            Window_SetSizeOld(self, width, height)
        elif arg is wx.Rect:
            width = 0 if arg.width < 0 else arg.width
            height = 0 if arg.height < 0 else arg.height
            Window_SetSizeOld(self, wx.Rect(arg.x, arg.y, width, height))
        else:
            Window_SetSizeOld(self, *args, **kw)
    elif len(args) <= 2:
        width = args[0]
        height = args[1]
        width = 0 if width < 0 else width
        height = 0 if height < 0 else height
        Window_SetSizeOld(self, width, height)
    else:
        x = args[0]
        y = args[1]
        width = args[2]
        height = args[3]
        width = 0 if width < 0 else width
        height = 0 if height < 0 else height
        Window_SetSizeOld(self, x, y, width, height, *args[4:], **kw)


Window.SetSize = Window_SetSizeNew


# =============================================================================
# wx.CallAfter Crash Guard
# =============================================================================
# wx.CallAfter schedules a callback to run in the main event loop. If the
# callback is a bound method on a wx widget that has been destroyed (C++ object
# deleted), calling it causes a segfault. This wrapper detects that situation,
# logs it, and skips the call.
#
# For details, see: docs/CRASH_GUARD.md
# =============================================================================

import traceback
from taskcoachlib.meta.debug import log_step

_wx_CallAfter_original = wx.CallAfter


def _guarded_CallAfter(callableObj, *args, **kw):
    """Wrapper around wx.CallAfter that guards against calls to dead objects.

    When a wx.CallAfter is scheduled but the target wx object is destroyed
    before the callback fires, the original wx.CallAfter would segfault.
    This wrapper captures the scheduling traceback and wraps the callback
    so it checks object validity before calling.
    """
    # Capture where the CallAfter was scheduled from (for logging). Keep a
    # deep slice so the root cause (not just the wx MainLoop wrappers) is
    # visible when the guard later fires.
    schedule_tb = traceback.format_stack(limit=25)[:-1]

    # Check if this is a bound method on a wx object
    obj = getattr(callableObj, "__self__", None)
    is_wx_obj = isinstance(obj, wx.Object)

    if is_wx_obj:
        # Wrap the call with a validity check
        def _safe_call(*a, **k):
            try:
                # bool(wxObject) returns False if C++ object is deleted
                if not obj:
                    caller = "%s.%s" % (
                        type(obj).__name__,
                        getattr(callableObj, "__name__", "?"),
                    )
                    log_step(
                        "Blocked CallAfter to destroyed object:",
                        caller,
                        prefix="CRASH_GUARD",
                    )
                    log_step(
                        "Originally scheduled from:", prefix="CRASH_GUARD"
                    )
                    for line in schedule_tb:
                        for part in line.rstrip().split("\n"):
                            log_step("  " + part, prefix="CRASH_GUARD")
                    return
                callableObj(*a, **k)
            except RuntimeError as e:
                if "C/C++ object" in str(e) or "deleted" in str(e):
                    caller = "%s.%s" % (
                        type(obj).__name__,
                        getattr(callableObj, "__name__", "?"),
                    )
                    log_step(
                        "RuntimeError calling %s:" % caller,
                        e,
                        prefix="CRASH_GUARD",
                        exc=True,
                    )
                    log_step(
                        "Originally scheduled from:", prefix="CRASH_GUARD"
                    )
                    for line in schedule_tb:
                        for part in line.rstrip().split("\n"):
                            log_step("  " + part, prefix="CRASH_GUARD")
                else:
                    raise

        _wx_CallAfter_original(_safe_call, *args, **kw)
    else:
        _wx_CallAfter_original(callableObj, *args, **kw)


wx.CallAfter = _guarded_CallAfter


# =============================================================================
# wx.Timer Owner Crash Guard
# =============================================================================
# A wx.Timer created with an owner window keeps a raw C++ pointer to
# that owner and delivers every tick to it. If the owner is destroyed
# while the timer is still running, the next tick is dispatched into
# freed memory. That crash happens entirely in C++, so the CallAfter
# guard and OnExceptionInMainLoop never see it and faulthandler shows
# only MainLoop. This guard records where each window-owned timer was
# started and, when the owner is destroyed, moves the timer to a
# harmless sink owner. wx runs later-bound handlers first, so the
# owner's own destroy handler may still stop the timer after this; only
# a tick that actually reaches the sink is logged, with the stack the
# timer was started from.
#
# For details, see: docs/CRASH_GUARD.md
# =============================================================================

_wx_timer_start_original = wx.Timer.Start
_wx_timer_set_owner_original = wx.Timer.SetOwner


def _capture_stack():
    """Capture the stack of the caller of the guarded method. Source
    lines are only looked up if the stack is logged."""
    stack = traceback.StackSummary.extract(
        traceback.walk_stack(sys._getframe(2)), limit=25, lookup_lines=False
    )
    stack.reverse()
    return stack


def _log_stack(title, stack):
    log_step(title, prefix="CRASH_GUARD")
    for line in stack.format():
        for part in line.rstrip().split("\n"):
            log_step("  " + part, prefix="CRASH_GUARD")


class _OrphanedTimerSink(wx.EvtHandler):
    """Owner of a timer whose window was destroyed. Receiving a tick
    means the timer outlived its window: stop it and log where it was
    started."""

    def __init__(self, owner_name, start_stack):
        super().__init__()
        self._owner_name = owner_name
        self._start_stack = start_stack
        self.Bind(wx.EVT_TIMER, self._on_tick)

    def _on_tick(self, event):
        timer = event.GetTimer()
        timer.Stop()
        log_step(
            "Stopped timer still running after its owner window was "
            "destroyed: owner=%s timer_id=%d"
            % (self._owner_name, timer.GetId()),
            prefix="CRASH_GUARD",
        )
        log_step(
            "Without this guard this tick would have been dispatched to "
            "the freed owner (native crash).",
            prefix="CRASH_GUARD",
        )
        _log_stack("Timer was last started from:", self._start_stack)


def _watch_timer_owner(timer, owner, owner_addr):
    """Move the timer to a sink owner when its owner window is
    destroyed. Only a weak reference to the timer is kept, so timer
    lifetimes are unchanged."""
    timer_ref = weakref.ref(timer)
    owner_name = type(owner).__name__

    def _on_owner_destroy(event):
        event.Skip()
        # Compare C++ addresses: destroy events of child windows may
        # propagate here, and the Python proxy of the event object is
        # not always the same object as the one seen at Start() time.
        try:
            destroyed_addr = wx.siplib.unwrapinstance(event.GetEventObject())
        except (TypeError, RuntimeError):
            return
        if destroyed_addr != owner_addr:
            return
        timer = timer_ref()
        if timer is None:
            return  # Timer already deleted, nothing can tick
        if getattr(timer, "_crash_guard_owner_addr", None) != owner_addr:
            return  # Timer was given another owner since
        timer._crash_guard_owner_destroyed = True
        # The sink lives as long as the timer's Python object, which
        # owns the C++ timer.
        timer._crash_guard_sink = _OrphanedTimerSink(
            owner_name, timer._crash_guard_start_stack
        )
        _wx_timer_set_owner_original(
            timer, timer._crash_guard_sink, timer.GetId()
        )

    wx.EvtHandler.Bind(owner, wx.EVT_WINDOW_DESTROY, _on_owner_destroy)


def _guarded_timer_start(self, *args, **kw):
    """Wrapper around wx.Timer.Start that watches window owners."""
    if getattr(self, "_crash_guard_owner_destroyed", False):
        # Do not call GetOwner() here: converting the dangling owner
        # pointer to a Python object would itself crash.
        log_step(
            "Blocked Start() of timer whose owner window was destroyed: "
            "timer_id=%d" % self.GetId(),
            prefix="CRASH_GUARD",
        )
        _log_stack("Start() called from:", _capture_stack())
        return False
    owner = self.GetOwner()
    if isinstance(owner, wx.Window):
        owner_addr = wx.siplib.unwrapinstance(owner)
        if getattr(self, "_crash_guard_owner_addr", None) != owner_addr:
            self._crash_guard_owner_addr = owner_addr
            _watch_timer_owner(self, owner, owner_addr)
        self._crash_guard_start_stack = _capture_stack()
    return _wx_timer_start_original(self, *args, **kw)


def _guarded_timer_start_once(self, milliseconds=-1):
    return self.Start(milliseconds, wx.TIMER_ONE_SHOT)


def _guarded_timer_set_owner(self, *args, **kw):
    """A new owner makes the timer safe to start again."""
    self._crash_guard_owner_destroyed = False
    self._crash_guard_owner_addr = None
    return _wx_timer_set_owner_original(self, *args, **kw)


wx.Timer.Start = _guarded_timer_start
wx.Timer.StartOnce = _guarded_timer_start_once
wx.Timer.SetOwner = _guarded_timer_set_owner
