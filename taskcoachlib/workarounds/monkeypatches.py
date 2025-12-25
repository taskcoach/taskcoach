# -*- coding: utf-8 -*-

import sys
import os
import inspect

# =============================================================================
# wxPython hypertreelist Import Hook
# =============================================================================
# This import hook redirects imports of wx.lib.agw.hypertreelist to our bundled
# patched version. This is needed because wxPython < 4.2.4 has bugs in
# TR_FULL_ROW_HIGHLIGHT and TR_FILL_WHOLE_COLUMN_BACKGROUND that break
# background coloring in tree list widgets.
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
