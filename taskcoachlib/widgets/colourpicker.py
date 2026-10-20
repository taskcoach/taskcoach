"""
Custom ColourPickerCtrl that uses wx.ColourDialog on Linux/GTK instead of
the native GtkColorChooserDialog which has a bug where custom colours don't
open to the currently set colour.

On Windows/macOS, the native picker works correctly and is used as-is.

Supports a read_only parameter to display a color without allowing
changes.
"""

import wx
from taskcoachlib.meta.debug import log_step
from taskcoachlib.widgets import skipfocus

# wxWidgets' own picker. On macOS wxPython 4.3.0 and 4.3.1 put one of
# their own in its place, which calls PickerBase.SetPickerCtrl(), gone
# in wxWidgets 3.3: no picker could be made there, so no editor with an
# Appearance tab opened (#487). wxPython 4.3.2 dropped theirs (wxPython
# #2937, docs/COLOUR_PICKER.md).
_WX_PICKER = wx._core.ColourPickerCtrl  # pylint: disable=protected-access


class ColourPickerCtrl(_WX_PICKER):
    """Drop-in replacement for wx.ColourPickerCtrl.

    On Linux/GTK: intercepts all activation methods (mouse click, keyboard
    Enter/Space, double-click) and opens wx.ColourDialog instead of the
    native GtkColorChooserDialog.

    On Windows/macOS: behaves identically to wx.ColourPickerCtrl.

    Args:
        read_only: If True, displays color but doesn't open picker on
            click.
    """

    def __init__(self, *args, read_only=False, **kwargs):
        self._read_only = read_only
        super().__init__(*args, **kwargs)
        target = self.GetPickerCtrl() or self
        if self._read_only:
            parts = () if target is self else (target,)
            skipfocus.skip_focus(self, *parts)
        target.Bind(wx.EVT_LEFT_DOWN, self._on_intercept)
        target.Bind(wx.EVT_LEFT_DCLICK, self._on_intercept)
        target.Bind(wx.EVT_KEY_DOWN, self._on_key_intercept)
        target.Bind(wx.EVT_BUTTON, self._on_button_intercept)

    def _on_intercept(self, event):
        if self._read_only:
            return  # Swallow click when read-only
        if wx.Platform == "__WXGTK__":
            self._show_colour_dialog()
        else:
            event.Skip()  # Let native handle it

    def _on_key_intercept(self, event):
        key = event.GetKeyCode()
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_SPACE):
            if self._read_only:
                return  # Swallow when read-only
            if wx.Platform == "__WXGTK__":
                self._show_colour_dialog()
            else:
                event.Skip()  # Let native handle it
        else:
            event.Skip()

    def _on_button_intercept(self, event):
        if self._read_only:
            return  # Swallow when read-only
        if wx.Platform == "__WXGTK__":
            pass  # Swallow to prevent native GTK dialog
        else:
            event.Skip()  # Let native handle it

    def _show_colour_dialog(self):
        data = wx.ColourData()
        data.SetChooseFull(True)
        data.SetColour(self.GetColour())
        dlg = wx.ColourDialog(self.GetTopLevelParent(), data)
        if dlg.ShowModal() == wx.ID_OK:
            new_colour = dlg.GetColourData().GetColour()
            self.SetColour(new_colour)
            evt = wx.ColourPickerEvent(self, self.GetId(), new_colour)
            wx.PostEvent(self, evt)
        dlg.Destroy()

    def SetColour(self, colour):  # noqa: N802 (wx's)
        """Show the colour; an invalid one is logged and not shown:
        macOS asserts drawing it (src/osx/core/colour.cpp,
        GetCGColor), which stopped the editor holding the picker
        from opening."""
        colour = wx.Colour(colour)
        if colour.IsOk():
            super().SetColour(colour)
        else:
            log_step("invalid colour not shown", prefix="APPEARANCE-BUG")

    def AcceptsFocusFromKeyboard(self):
        """Read-only pickers are display, never tab stops."""
        if self._read_only:
            return False
        return super().AcceptsFocusFromKeyboard()
