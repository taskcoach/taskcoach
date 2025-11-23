#!/usr/bin/env python3
"""
Test using EVT_WINDOW_CREATE to set GTK hints at the right time.

Uses Gtk.Widget.__gtype__.pytype.from_address() to get actual GTK widget
from wx handle, then sets geometry hints with POS flag.
"""

import wx
import platform

# Only try GTK introspection on Linux
IS_LINUX = (platform.system() == "Linux")

if IS_LINUX:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk


class HintFixedFrame(wx.Frame):
    def __init__(self, pos=(100, 100), *args, **kw):
        # DO NOT set pos in wx constructor – let GTK set hints first
        super().__init__(None, *args, **kw)
        self._desired_pos = pos
        self._move_count = 0

        # Wait until the native GTK window exists
        self.Bind(wx.EVT_WINDOW_CREATE, self._on_window_create)
        self.Bind(wx.EVT_MOVE, self._on_move)

    def _on_window_create(self, evt):
        evt.Skip()
        print(f"EVT_WINDOW_CREATE fired")

        if not IS_LINUX:
            # Windows/macOS: normal wx positioning works
            self.SetPosition(self._desired_pos)
            return

        # ---- LINUX/GTK: Apply geometry hints ----

        # Get the underlying GtkWindow
        gtk_widget = self.GetHandle()
        print(f"  GetHandle() = {gtk_widget}")
        if gtk_widget is None:
            print("  No handle yet!")
            return  # Safety check

        try:
            gobj = Gtk.Widget.__gtype__.pytype.from_address(gtk_widget)
            print(f"  Got GTK widget: {gobj}")

            # Create geometry hints
            hints = Gdk.Geometry()
            hints.min_width = 0
            hints.min_height = 0

            # Apply ONLY the position hint
            gobj.set_geometry_hints(gobj, hints, Gdk.WindowHints.POS)
            print(f"  Set geometry hints with POS flag")

            # Now request the position
            gobj.move(self._desired_pos[0], self._desired_pos[1])
            print(f"  Called gobj.move({self._desired_pos})")

        except Exception as e:
            print(f"  GTK hint failed: {e}")
            import traceback
            traceback.print_exc()

    def _on_move(self, evt):
        self._move_count += 1
        pos = evt.GetPosition()
        print(f"EVT_MOVE #{self._move_count}: ({pos.x}, {pos.y})")
        evt.Skip()


class MyApp(wx.App):
    def OnInit(self):
        frame = HintFixedFrame(
            pos=(100, 100),
            title="Exact Position Test",
            size=(800, 600)
        )
        print(f"Before Show: {frame.GetPosition()}")
        frame.Show()
        print(f"After Show: {frame.GetPosition()}")
        return True


if __name__ == "__main__":
    print(f"Platform: {platform.system()}")
    print(f"IS_LINUX: {IS_LINUX}")
    app = MyApp(False)
    app.MainLoop()
