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

from taskcoachlib import i18n, operating_system
import wx
import webbrowser


UNICODE_CONTROL_CHARACTERS_TO_WEED = {}
for ordinal in range(0x20):
    if chr(ordinal) not in "\t\r\n":
        UNICODE_CONTROL_CHARACTERS_TO_WEED[ordinal] = None


class BaseTextCtrl(wx.TextCtrl):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, -1, *args, **kwargs)
        self.__data = None
        if operating_system.isGTK() or operating_system.isMac():
            if operating_system.isGTK():
                self.Bind(wx.EVT_KEY_DOWN, self.__on_key_down)
            self.Bind(wx.EVT_KILL_FOCUS, self.__on_kill_focus)
            self.__initial_value = self.GetValue()
            self.__undone_value = None

    def GetValue(self, *args, **kwargs):
        value = super().GetValue(*args, **kwargs)
        # Don't allow unicode control characters:
        return value.translate(UNICODE_CONTROL_CHARACTERS_TO_WEED)

    def SetValue(self, *args, **kwargs):
        super().SetValue(*args, **kwargs)
        if operating_system.isGTK() or operating_system.isMac():
            self.__initial_value = self.GetValue()

    def AppendText(self, *args, **kwargs):
        super().AppendText(*args, **kwargs)
        if operating_system.isGTK() or operating_system.isMac():
            self.__initial_value = self.GetValue()

    def SetData(self, data):
        self.__data = data

    def GetData(self):
        return self.__data

    def CanUndo(self):
        if operating_system.isMac():
            return self.__can_undo()
        return super().CanUndo()

    def Undo(self):
        if operating_system.isMac():
            self.__undo()
        else:
            super().Undo()

    def CanRedo(self):
        if operating_system.isMac():
            return self.__can_redo()
        return super().CanRedo()

    def Redo(self):
        if operating_system.isMac():
            self.__redo()
        else:
            super().Redo()

    def __on_key_down(self, event):
        """Check whether the user pressed Ctrl-Z (or Ctrl-Y) and if so,
        undo (or redo) the editing."""
        if self.__ctrl_z_pressed(event) and self.__can_undo():
            self.__undo()
        elif self.__ctrl_y_pressed(event) and self.__can_redo():
            self.__redo()
        else:
            event.Skip()

    @staticmethod
    def __ctrl_z_pressed(event):
        """Did the user press Ctrl-Z (for undo)?"""
        return event.GetKeyCode() == ord("Z") and event.ControlDown()

    def __can_undo(self):
        """Is there a change to be undone?"""
        return self.GetValue() != self.__initial_value

    def __undo(self):
        """Undo the last change."""
        insertion_point = self.GetInsertionPoint()
        self.__undone_value = self.GetValue()
        super().SetValue(self.__initial_value)
        insertion_point = min(insertion_point, self.GetLastPosition())
        self.SetInsertionPoint(insertion_point)

    @staticmethod
    def __ctrl_y_pressed(event):
        """Did the user press Ctrl-Y (for redo)?"""
        return event.GetKeyCode() == ord("Y") and event.ControlDown()

    def __can_redo(self):
        """Is there an undone change to be redone?"""
        return self.__undone_value not in (self.GetValue(), None)

    def __redo(self):
        """Redo the last undone change."""
        insertion_point = self.GetInsertionPoint()
        super().SetValue(self.__undone_value)
        self.__undone_value = None
        insertion_point = min(insertion_point, self.GetLastPosition())
        self.SetInsertionPoint(insertion_point)

    def __on_kill_focus(self, event):
        """Reset the edit history."""
        self.__initial_value = self.GetValue()
        self.__undone_value = None


class SingleLineTextCtrl(BaseTextCtrl):
    pass


class _MultiLineTextCtrlInner(BaseTextCtrl):
    """Inner text control for MultiLineTextCtrl with URL handling."""

    def __init__(self, parent, text="", *args, **kwargs):
        kwargs["style"] = kwargs.get("style", 0) | wx.TE_MULTILINE | wx.BORDER_NONE
        if not i18n.currentLanguageIsRightToLeft():
            # Using wx.TE_RICH will remove the RTL specific menu items
            # from the right-click menu in the TextCtrl, so we don't use
            # wx.TE_RICH if the language is RTL.
            kwargs["style"] |= wx.TE_RICH | wx.TE_AUTO_URL
        super().__init__(parent, *args, **kwargs)
        self.__initializeText(text)
        self.Bind(wx.EVT_TEXT_URL, self.onURLClicked)
        try:
            self.__webbrowser = webbrowser.get()
        except webbrowser.Error:
            self.__webbrowser = None

    def onURLClicked(self, event):
        mouseEvent = event.GetMouseEvent()
        if mouseEvent.ButtonDown() and self.__webbrowser:
            url = self.GetRange(event.GetURLStart(), event.GetURLEnd())
            try:
                self.__webbrowser.open(url)
            except Exception as message:
                wx.MessageBox(str(message), i18n._("Error opening URL"))

    def __initializeText(self, text):
        self.AppendText(text)
        self.SetInsertionPoint(0)


class MultiLineTextCtrl(wx.Panel):
    """Multiline text control with internal padding.

    Wraps the text control in a panel with a sizer to provide consistent
    padding on all platforms (SetMargins doesn't work on GTK).
    Uses RendererNative to draw native-looking border with focus state.
    """
    _nativePadding = None  # Cached native padding value

    @classmethod
    def _getNativePadding(cls, parent):
        """Get the native TextCtrl padding by querying the GTK theme."""
        if cls._nativePadding is not None:
            return cls._nativePadding

        # Try to get padding from GTK directly via PyGObject
        if operating_system.isGTK():
            try:
                import gi
                gi.require_version('Gtk', '3.0')
                from gi.repository import Gtk

                # Create a temporary GtkEntry to get its style context
                entry = Gtk.Entry()
                style_context = entry.get_style_context()

                # Get the padding from the style context
                padding = style_context.get_padding(Gtk.StateFlags.NORMAL)

                # Use horizontal padding (left)
                if padding.left > 0:
                    cls._nativePadding = padding.left
                    return cls._nativePadding
            except Exception:
                pass

        # Fallback: try wxPython GetMargins (works on Windows)
        try:
            temp = wx.TextCtrl(parent, -1, "X", style=wx.TE_MULTILINE | wx.BORDER_DEFAULT)
            margins = temp.GetMargins()
            temp.Destroy()

            if margins.x > 0:
                cls._nativePadding = margins.x
                return cls._nativePadding
        except Exception:
            pass

        # Last fallback: use a reasonable default
        cls._nativePadding = 6
        return cls._nativePadding

    def __init__(self, parent, text="", *args, **kwargs):
        # Extract style for the panel - remove text-specific styles
        kwargs.pop("style", 0)
        super().__init__(parent, style=wx.BORDER_NONE)

        # Track focus state for border drawing
        self._hasFocus = False

        # Get native padding from theme
        self._padding = self._getNativePadding(parent)

        # Create the inner text control
        self._textCtrl = _MultiLineTextCtrlInner(self, text, *args, **kwargs)

        # Match background colors
        self.SetBackgroundColour(self._textCtrl.GetBackgroundColour())

        # Use sizer to add padding
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._textCtrl, 1, wx.EXPAND | wx.ALL, self._padding)
        self.SetSizer(sizer)

        # Bind focus events to update focus state and repaint
        self._textCtrl.Bind(wx.EVT_SET_FOCUS, self._onFocus)
        self._textCtrl.Bind(wx.EVT_KILL_FOCUS, self._onKillFocus)

        # Bind paint event to draw native border
        self.Bind(wx.EVT_PAINT, self._onPaint)

    def _onFocus(self, event):
        """Update focus state and repaint."""
        self._hasFocus = True
        self.Refresh()
        event.Skip()

    def _onKillFocus(self, event):
        """Update focus state and repaint."""
        self._hasFocus = False
        self.Refresh()
        event.Skip()

    def _onPaint(self, event):
        """Draw native TextCtrl border using RendererNative."""
        dc = wx.PaintDC(self)
        renderer = wx.RendererNative.Get()
        rect = self.GetClientRect()
        flags = wx.CONTROL_FOCUSED if self._hasFocus else 0
        renderer.DrawTextCtrl(self, dc, rect, flags)

    # Proxy common TextCtrl methods to the inner control
    def GetValue(self, *args, **kwargs):
        return self._textCtrl.GetValue(*args, **kwargs)

    def SetValue(self, *args, **kwargs):
        return self._textCtrl.SetValue(*args, **kwargs)

    def AppendText(self, *args, **kwargs):
        return self._textCtrl.AppendText(*args, **kwargs)

    def SetFont(self, *args, **kwargs):
        return self._textCtrl.SetFont(*args, **kwargs)

    def GetFont(self, *args, **kwargs):
        return self._textCtrl.GetFont(*args, **kwargs)

    def SetForegroundColour(self, *args, **kwargs):
        return self._textCtrl.SetForegroundColour(*args, **kwargs)

    def SetBackgroundColour(self, colour):
        super().SetBackgroundColour(colour)
        if hasattr(self, '_textCtrl'):
            self._textCtrl.SetBackgroundColour(colour)

    def SetData(self, data):
        return self._textCtrl.SetData(data)

    def GetData(self):
        return self._textCtrl.GetData()

    def CanUndo(self):
        return self._textCtrl.CanUndo()

    def Undo(self):
        return self._textCtrl.Undo()

    def CanRedo(self):
        return self._textCtrl.CanRedo()

    def Redo(self):
        return self._textCtrl.Redo()

    def SetInsertionPoint(self, *args, **kwargs):
        return self._textCtrl.SetInsertionPoint(*args, **kwargs)

    def GetInsertionPoint(self):
        return self._textCtrl.GetInsertionPoint()

    def GetRange(self, *args, **kwargs):
        return self._textCtrl.GetRange(*args, **kwargs)

    def SetFocus(self):
        return self._textCtrl.SetFocus()

    def Bind(self, event, handler, *args, **kwargs):
        # Bind text and focus events to inner control, others to panel
        # Focus events must go to inner control since it receives focus, not the panel
        if event in (wx.EVT_TEXT, wx.EVT_TEXT_URL, wx.EVT_TEXT_ENTER,
                     wx.EVT_SET_FOCUS, wx.EVT_KILL_FOCUS):
            return self._textCtrl.Bind(event, handler, *args, **kwargs)
        return super().Bind(event, handler, *args, **kwargs)


class StaticTextWithToolTip(wx.StaticText):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        label = kwargs["label"]
        self.SetToolTip(wx.ToolTip(label))
