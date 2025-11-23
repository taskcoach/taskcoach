#!/usr/bin/env python3
"""
Test using gi._gobject.GObject() to wrap wx handle as GTK object.

The correct way to get GtkWindow from wx handle:
  gtk_ptr = self.GetHandle()  # raw pointer
  gobj = GObject.GObject(gtk_ptr)  # wrap pointer as GObject
"""

import wx
import platform

IS_LINUX = (platform.system() == "Linux")

if IS_LINUX:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk, GObject


class HintFixedFrame(wx.Frame):
    def __init__(self, pos=(100, 100), *args, **kw):
        # DO NOT set pos in wx constructor
        super().__init__(None, *args, **kw)
        self._desired_pos = pos
        self._move_count = 0

        self.Bind(wx.EVT_WINDOW_CREATE, self._on_window_create)
        self.Bind(wx.EVT_MOVE, self._on_move)

    def _on_window_create(self, evt):
        evt.Skip()
        print(f"EVT_WINDOW_CREATE fired")

        if not IS_LINUX:
            self.SetPosition(self._desired_pos)
            return

        gtk_ptr = self.GetHandle()
        print(f"  GetHandle() = {gtk_ptr}")
        if gtk_ptr is None:
            print("  No handle yet!")
            return

        try:
            # Wrap raw pointer as GObject
            gobj = GObject.GObject(gtk_ptr)
            print(f"  Wrapped as GObject: {gobj}")

            # Create geometry hints
            hints = Gdk.Geometry()
            hints.min_width = 0
            hints.min_height = 0

            # Apply position hint
            gobj.set_geometry_hints(gobj, hints, Gdk.WindowHints.POS)
            print(f"  Set geometry hints with POS flag")

            # Request position
            gobj.move(self._desired_pos[0], self._desired_pos[1])
            print(f"  Called gobj.move({self._desired_pos})")

        except Exception as e:
            print(f"  Failed: {e}")
            import traceback
            traceback.print_exc()

    def _on_move(self, evt):
        self._move_count += 1
        pos = evt.GetPosition()
        print(f"EVT_MOVE #{self._move_count}: ({pos.x}, {pos.y})")
        evt.Skip()


if __name__ == "__main__":
    print(f"Platform: {platform.system()}")
    app = wx.App(False)
    frame = HintFixedFrame(pos=(100, 100), title="GObject Wrap Test", size=(200, 150))
    print(f"Before Show: {frame.GetPosition()}")
    frame.Show()
    print(f"After Show: {frame.GetPosition()}")
    app.MainLoop()
