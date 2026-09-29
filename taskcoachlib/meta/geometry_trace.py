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

Geometry trace: logs where windows are and where they draw, for
layout, placement and drawing problems (docs/DEVELOPMENT.md,
"Diagnosing"). A diagnostic tool: call it from the code under
investigation, remove the call once the cause is found.

    tracer = GeometryTracer(owner, windows_fn)
    tracer.burst()   # again at each event of interest

Each tick logs the wx geometry of windows_fn()'s windows (position,
size, screen position, shown) and, on GTK 3, the GTK allocation,
visibility and position in the toplevel. A burst ticks every
FAST_MS for BURST_MS logging what changed, then a full snapshot
every SLOW_MS. On GTK 3 every allocation and every draw of a traced
widget is logged as it happens, with the drawn area in toplevel
coordinates: a stale drawing shows as a draw at the wrong place.
"""

import ctypes
import os
import traceback

import wx

from taskcoachlib.meta.debug import log_step

FAST_MS = 10
BURST_MS = 2000
SLOW_MS = 1000
PREFIX = "GEOM"


class _Rect(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
    ]


def _load_gtk():
    if "gtk3" not in wx.PlatformInfo:
        return None
    try:
        gtk = ctypes.CDLL("libgtk-3.so.0")
        gobject = ctypes.CDLL("libgobject-2.0.so.0")
        cairo = ctypes.CDLL("libcairo.so.2")
    except OSError:
        return None
    ptr, gint = ctypes.c_void_p, ctypes.c_int
    gtk.gtk_widget_get_allocation.argtypes = [ptr, ctypes.POINTER(_Rect)]
    gtk.gtk_widget_get_allocation.restype = None
    for name in (
        "get_visible",
        "get_mapped",
        "get_child_visible",
        "is_toplevel",
    ):
        func = getattr(gtk, "gtk_widget_" + name)
        func.argtypes, func.restype = [ptr], gint
    gtk.gtk_widget_get_toplevel.argtypes = [ptr]
    gtk.gtk_widget_get_toplevel.restype = ptr
    gtk.gtk_widget_translate_coordinates.argtypes = [
        ptr,
        ptr,
        gint,
        gint,
        ctypes.POINTER(gint),
        ctypes.POINTER(gint),
    ]
    gtk.gtk_widget_translate_coordinates.restype = gint
    gobject.g_signal_connect_data.argtypes = [
        ptr,
        ctypes.c_char_p,
        ptr,
        ptr,
        ptr,
        gint,
    ]
    gobject.g_signal_connect_data.restype = ctypes.c_ulong
    dbl = ctypes.POINTER(ctypes.c_double)
    cairo.cairo_user_to_device.argtypes = [ptr, dbl, dbl]
    cairo.cairo_user_to_device.restype = None
    cairo.cairo_clip_extents.argtypes = [ptr, dbl, dbl, dbl, dbl]
    cairo.cairo_clip_extents.restype = None
    return gtk, gobject, cairo


_GTK = _load_gtk()
_DRAW_CB = ctypes.CFUNCTYPE(
    ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
)
_ALLOC_CB = ctypes.CFUNCTYPE(
    None, ctypes.c_void_p, ctypes.POINTER(_Rect), ctypes.c_void_p
)
# GTK widget pointer -> label, for the signal callbacks
_labels = {}


def _on_draw(widget, cr, _data):
    try:
        cairo = _GTK[2]
        x, y = ctypes.c_double(0), ctypes.c_double(0)
        cairo.cairo_user_to_device(cr, ctypes.byref(x), ctypes.byref(y))
        c = [ctypes.c_double(0) for _ in range(4)]
        cairo.cairo_clip_extents(cr, *[ctypes.byref(v) for v in c])
        log_step(
            "draw %s at toplevel (%d,%d) clip (%d,%d %dx%d)"
            % (
                _labels.get(widget, hex(widget)),
                x.value,
                y.value,
                x.value + c[0].value,
                y.value + c[1].value,
                c[2].value - c[0].value,
                c[3].value - c[1].value,
            )
            + _caller(widget),
            prefix=PREFIX,
        )
    except Exception:
        log_step("draw callback failed", prefix=PREFIX, exc=True)
    return 0


def _caller(widget):
    """The Python calls that led to a toplevel's draw: none when the
    main loop draws, the forcing call when code paints at once."""
    if not _GTK[0].gtk_widget_is_toplevel(widget):
        return ""
    frames = traceback.extract_stack()[:-2]
    while frames and "MainLoop" not in frames[0].name:
        frames.pop(0)
    return " via " + (
        " < ".join(
            "%s:%d %s" % (os.path.basename(f.filename), f.lineno, f.name)
            for f in reversed(frames[1:][-6:])
        )
        or "main loop"
    )


def _on_allocate(widget, rect, _data):
    try:
        r = rect.contents
        log_step(
            "allocate %s (%d,%d %dx%d)"
            % (
                _labels.get(widget, hex(widget)),
                r.x,
                r.y,
                r.width,
                r.height,
            ),
            prefix=PREFIX,
        )
    except Exception:
        log_step("allocate callback failed", prefix=PREFIX, exc=True)


_draw_cb = _DRAW_CB(_on_draw)
_alloc_cb = _ALLOC_CB(_on_allocate)


def _widget(window):
    # GetHandle() is the X window id on GTK, not the widget
    return int(window.GetGtkWidget())


def _gtk_state(handle):
    gtk = _GTK[0]
    a = _Rect()
    gtk.gtk_widget_get_allocation(handle, ctypes.byref(a))
    x, y = ctypes.c_int(0), ctypes.c_int(0)
    top = gtk.gtk_widget_get_toplevel(handle)
    placed = gtk.gtk_widget_translate_coordinates(
        handle, top, 0, 0, ctypes.byref(x), ctypes.byref(y)
    )
    return "gtk=(%d,%d %dx%d) top=%s vis=%d map=%d cvis=%d" % (
        a.x,
        a.y,
        a.width,
        a.height,
        "(%d,%d)" % (x.value, y.value) if placed else "-",
        gtk.gtk_widget_get_visible(handle),
        gtk.gtk_widget_get_mapped(handle),
        gtk.gtk_widget_get_child_visible(handle),
    )


class GeometryTracer:
    def __init__(self, owner, windows_fn):
        """owner: the window whose lifetime the trace follows.
        windows_fn: returns [(label, window), ...] to log each tick."""
        self.__owner = owner
        self.__windows_fn = windows_fn
        self.__last = {}
        self.__burst_left = 0
        # Not owned by the window: its destroy event may never come
        # (AUI consumes it, docs/AUI.md), and a tick to a destroyed
        # owner crashes. Each tick checks the window instead.
        self.__timer = wx.Timer()
        self.__timer.Bind(wx.EVT_TIMER, self.__on_tick)

    def burst(self, reason=""):
        log_step("burst", reason, prefix=PREFIX)
        self.__last = {}
        self.__burst_left = BURST_MS // FAST_MS
        self.__tick()
        self.__timer.Start(FAST_MS)

    def __on_tick(self, event):
        if not self.__owner:
            self.__timer.Stop()
            self.__timer.Unbind(wx.EVT_TIMER)  # Frees the tracer
            log_step("stopped: window destroyed", prefix=PREFIX)
            return
        if self.__burst_left:
            self.__burst_left -= 1
            if not self.__burst_left:
                self.__last = {}  # A full snapshot ends the burst
                self.__timer.Start(SLOW_MS)
        else:
            self.__last = {}
        self.__tick()

    def __tick(self):
        for label, window in self.__windows_fn():
            if not window:
                continue
            state = self.__state(window)
            if self.__last.get(label) != state:
                self.__last[label] = state
                log_step(label, state, prefix=PREFIX)
            if _GTK:
                self.__hook(label, window)

    @staticmethod
    def __state(window):
        x, y = window.GetPosition()
        w, h = window.GetSize()
        sx, sy = window.GetScreenPosition()
        state = "wx=(%d,%d %dx%d) screen=(%d,%d) shown=%d onscreen=%d" % (
            x,
            y,
            w,
            h,
            sx,
            sy,
            window.IsShown(),
            window.IsShownOnScreen(),
        )
        if isinstance(window, wx.TopLevelWindow):
            state += " maximized=%d" % window.IsMaximized()
        if _GTK:
            state += " " + _gtk_state(_widget(window))
        return state

    @staticmethod
    def __hook(label, window):
        handle = _widget(window)
        if not handle or _labels.get(handle) == label:
            return
        known = handle in _labels
        _labels[handle] = label
        if known:
            return  # Relabelled: the signals are connected already
        connect = _GTK[1].g_signal_connect_data
        connect(
            handle,
            b"draw",
            ctypes.cast(_draw_cb, ctypes.c_void_p),
            None,
            None,
            0,
        )
        connect(
            handle,
            b"size-allocate",
            ctypes.cast(_alloc_cb, ctypes.c_void_p),
            None,
            None,
            0,
        )
