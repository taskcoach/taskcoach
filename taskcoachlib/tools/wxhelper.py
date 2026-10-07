# -*- coding: utf-8 -*-

from typing import Union
import wx

from taskcoachlib import patterns
from taskcoachlib.meta.debug import log_step

# A window opens at most this share of its monitor's work area each
# way, its contents scrolling: room for panels the system does not
# report (docs/WINDOW_GEOMETRY.md, Decisions 10)
SIZE_SHARE = 0.8


def most_of(size, area):
    """The size, each way at most SIZE_SHARE of the area (x, y, width,
    height)."""
    return (
        min(size[0], int(area[2] * SIZE_SHARE)),
        min(size[1], int(area[3] * SIZE_SHARE)),
    )


def work_area_of(window):
    """The work area (the monitor less its panels) of the monitor the
    system reports for the window, else of the first, as (x, y, width,
    height)."""
    index = wx.Display.GetFromWindow(window) if window else -1
    return tuple(wx.Display(max(index, 0)).GetClientArea())


def fit_to_work_area(window, area):
    """Cut a window larger than SIZE_SHARE of the work area each way
    to it."""
    size = tuple(window.GetSize())
    fitted = most_of(size, area)
    if fitted != size:
        log_step(
            "%s: %dx%d cut to %d%% of the work area: %dx%d"
            % ((window.GetTitle(),) + size + (SIZE_SHARE * 100,) + fitted),
            prefix="GEOMETRY",
        )
        window.SetSize(fitted)


def centre_on_parent(window):
    """Centre a new window on its parent, also through its first show,
    at most SIZE_SHARE of the parent's monitor each way.

    Call it once the window is sized, before Show()."""
    fit_to_work_area(window, work_area_of(window.GetParent() or window))
    window.CentreOnParent()
    keep_placement_at_first_show(window)


def keep_placement_at_first_show(window):
    """Keep the window's position, and the size of its contents if it
    is fitted to them, through its first show.

    wxGTK may defer a new window's first show until the window manager
    reports its frame; it then drops the position set before, and keeps
    the outer size set without the frame, so the frame takes its height
    from the contents (docs/WINDOW_GEOMETRY.md, First Show on wxGTK).
    Both are set again at the first show, before the window is mapped.
    Called again, it keeps the window's placement then."""
    first = not hasattr(window, "_placement_to_keep")
    size = window.GetSize()
    window._placement_to_keep = (
        window.GetPosition(),
        size,
        window.GetClientSize(),
        size == window.GetBestSize(),
    )
    if first:
        window.Bind(wx.EVT_SHOW, _keep_placement)


def _keep_placement(event):
    event.Skip()
    window = event.GetEventObject()
    if not event.IsShown():
        return
    window.Unbind(wx.EVT_SHOW, handler=_keep_placement)
    position, size, client_size, fitted = window._placement_to_keep
    if (window.GetPosition(), window.GetSize()) == (position, size):
        return  # Shown as placed
    log_step(
        "%s: first show deferred, placed again at %s, %s"
        % (
            window.GetTitle(),
            tuple(position),
            "fitted" if fitted else "size kept",
        ),
        prefix="GEOMETRY",
    )
    if fitted:
        window.SetClientSize(client_size)
    if window.GetPosition() == position:
        # wx passes a position on only when it differs from its own
        window.SetPosition(position + wx.Point(1, 0))
    window.SetPosition(position)


def centre_on_app_monitor(window):
    """Centre a window on the application's monitor, also through its
    first show (keep_placement_at_first_show()).

    The monitor: the system's for the main window (also on Wayland,
    where positions read 0, 0), else the primary one.

    Call this after the window is created and sized but before Show().
    """
    app = wx.GetApp()
    target_monitor = None

    # Try to get monitor from main window (but not if we ARE the main window)
    if app:
        main_window = app.GetTopWindow()
        # Skip if main_window is the window we're trying to position
        if main_window and main_window is not window and main_window.IsShown():
            target_monitor = wx.Display.GetFromWindow(main_window)

    if target_monitor is None or target_monitor == wx.NOT_FOUND:
        target_monitor = next(
            (
                index
                for index in range(wx.Display.GetCount())
                if wx.Display(index).IsPrimary()
            ),
            0,
        )

    # Center on target monitor
    if target_monitor < wx.Display.GetCount():
        display = wx.Display(target_monitor)
        fit_to_work_area(window, tuple(display.GetClientArea()))
        display_rect = display.GetGeometry()
        window_size = window.GetSize()
        x = display_rect.x + (display_rect.width - window_size.width) // 2
        y = display_rect.y + (display_rect.height - window_size.height) // 2
        window.SetPosition(wx.Point(x, y))
    keep_placement_at_first_show(window)


def font_from_native_info(text):
    """The font a native font description gives, or None.

    A description saved on another platform can hold a zero point size,
    which wx asserts on.
    """
    if text:
        info = wx.NativeFontInfo()
        try:
            if info.FromString(text):
                return wx.Font(info)
        except wx.PyAssertionError:
            pass
    return None


def get_dialog_button(
    sizer: wx.StdDialogButtonSizer, button_id: int
) -> Union[wx.Window, None]:
    """The sizer's button with that id, found by the id alone: wxPython
    can give a button as a plain wx.Window, reusing the stale wrapper of
    a destroyed window at the same address, and a lookup by type then
    left the dialog without its buttons (P113)."""
    for child in sizer.GetChildren():
        window = child.GetWindow()
        if window is not None and window.GetId() == button_id:
            return window
    return None


def delete_with_window(handler, window, release=None):
    """Delete handler, a wx.EvtHandler made in Python that is not a
    window, once window is destroyed: the handlers bound on it keep it
    through wx, so nothing else frees it, nor what it holds
    (docs/CRASH_GUARD.md#event-handlers-that-are-not-windows).
    release(handler) runs first. Returns the destroy handler."""

    def on_destroy(event):
        event.Skip()
        # Children's destroy events come up too. A top-level window's
        # comes last, from wx, once its wrapper is already deleted.
        if patterns.deferred.is_gone(window) or (
            event.GetEventObject() is window
        ):
            patterns.later.soon(handler, _delete, handler, release)

    window.Bind(wx.EVT_WINDOW_DESTROY, on_destroy)
    return on_destroy


def _delete(handler, release):
    if release is not None:
        release(handler)
    handler.Destroy()
