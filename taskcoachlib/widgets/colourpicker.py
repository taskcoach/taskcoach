"""
Custom ColourPickerCtrl that uses wx.ColourDialog on Linux/GTK instead of
the native GtkColorChooserDialog which has a bug where custom colours don't
open to the currently set colour.

On Windows/macOS, the native picker works correctly and is used as-is.

Supports a readOnly parameter to display a color without allowing changes.
"""

import wx


class ColourPickerCtrl(wx.ColourPickerCtrl):
    """Drop-in replacement for wx.ColourPickerCtrl.

    On Linux/GTK: intercepts all activation methods (mouse click, keyboard
    Enter/Space, double-click) and opens wx.ColourDialog instead of the
    native GtkColorChooserDialog.

    On Windows/macOS: behaves identically to wx.ColourPickerCtrl.

    Args:
        readOnly: If True, displays color but doesn't open picker on click.
    """

    def __init__(self, *args, readOnly=False, **kwargs):
        self._readOnly = readOnly
        self._dialog = None
        super().__init__(*args, **kwargs)
        target = self.GetPickerCtrl() or self
        target.Bind(wx.EVT_LEFT_DOWN, self._onIntercept)
        target.Bind(wx.EVT_LEFT_DCLICK, self._onIntercept)
        target.Bind(wx.EVT_KEY_DOWN, self._onKeyIntercept)
        target.Bind(wx.EVT_BUTTON, self._onButtonIntercept)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._onDestroy)

    def _onIntercept(self, event):
        if self._readOnly:
            return  # Swallow click when read-only
        if wx.Platform == '__WXGTK__':
            self._showColourDialog()
        else:
            event.Skip()  # Let native handle it

    def _onKeyIntercept(self, event):
        key = event.GetKeyCode()
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_SPACE):
            if self._readOnly:
                return  # Swallow when read-only
            if wx.Platform == '__WXGTK__':
                self._showColourDialog()
            else:
                event.Skip()  # Let native handle it
        else:
            event.Skip()

    def _onButtonIntercept(self, event):
        if self._readOnly:
            return  # Swallow when read-only
        if wx.Platform == '__WXGTK__':
            pass  # Swallow to prevent native GTK dialog
        else:
            event.Skip()  # Let native handle it

    def _showColourDialog(self):
        # Don't open another if one is already open
        if self._dialog:
            self._dialog.Raise()
            return
        data = wx.ColourData()
        data.SetChooseFull(True)
        data.SetColour(self.GetColour())
        self._dialog = wx.ColourDialog(self.GetTopLevelParent(), data)
        self._dialog.Bind(wx.EVT_CLOSE, self._onDialogClose)
        self._dialog.Bind(wx.EVT_BUTTON, self._onDialogButton)
        self._dialog.Show()

    def _onDialogButton(self, event):
        """Handle OK/Cancel button clicks in the dialog."""
        dlg = self._dialog
        if event.GetId() == wx.ID_OK and dlg and self:
            try:
                newColour = dlg.GetColourData().GetColour()
                self.SetColour(newColour)
                evt = wx.ColourPickerEvent(self, self.GetId(), newColour)
                wx.PostEvent(self, evt)
            except RuntimeError:
                pass
        if dlg:
            self._dialog = None  # Clear before Destroy to avoid re-entry
            dlg.Destroy()

    def _onDialogClose(self, event):
        """Handle dialog close (X button or Escape)."""
        self._dialog = None
        event.Skip()  # Let default close handling proceed

    def _onDestroy(self, event):
        """Clean up dialog if picker is destroyed while dialog is open."""
        if self._dialog:
            try:
                self._dialog.Destroy()
            except RuntimeError:
                pass
            self._dialog = None
        event.Skip()

    def SetReadOnly(self, readOnly):
        """Set whether this picker is read-only."""
        self._readOnly = readOnly

    def IsReadOnly(self):
        """Return whether this picker is read-only."""
        return self._readOnly
