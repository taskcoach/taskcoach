# -*- coding: utf-8 -*-

from typing import Union
import wx

from taskcoachlib import patterns


def centerOnAppMonitor(window):
    """Center a window on the application's monitor.

    This function determines the correct monitor by:
    1. If main window exists, use its monitor
    2. Fall back to primary monitor

    Call this after the window is created and sized but before Show().
    """
    app = wx.GetApp()
    target_monitor = None

    # Try to get monitor from main window (but not if we ARE the main window)
    if app:
        main_window = app.GetTopWindow()
        # Skip if main_window is the window we're trying to position
        if main_window and main_window is not window and main_window.IsShown():
            main_rect = main_window.GetScreenRect()
            target_monitor = wx.Display.GetFromPoint(
                wx.Point(
                    main_rect.x + main_rect.width // 2,
                    main_rect.y + main_rect.height // 2,
                )
            )

    # Fall back to primary monitor
    if target_monitor is None or target_monitor == wx.NOT_FOUND:
        target_monitor = 0

    # Center on target monitor
    if target_monitor < wx.Display.GetCount():
        display = wx.Display(target_monitor)
        display_rect = display.GetGeometry()
        window_size = window.GetSize()
        x = display_rect.x + (display_rect.width - window_size.width) // 2
        y = display_rect.y + (display_rect.height - window_size.height) // 2
        window.SetPosition(wx.Point(x, y))


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
