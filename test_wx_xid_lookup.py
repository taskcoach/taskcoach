#!/usr/bin/env python3
"""
Test using XID to find GdkWindow, then get GtkWindow.

GetHandle() returns XID (X11 window ID), not GtkWidget pointer.
We need to use GdkX11.X11Window.foreign_new_for_display() to get GdkWindow.
"""

import wx
import platform

IS_LINUX = (platform.system() == "Linux")

if IS_LINUX:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    gi.require_version("GdkX11", "3.0")
    from gi.repository import Gtk, Gdk, GdkX11


class HintFixedFrame(wx.Frame):
    def __init__(self, pos=(100, 100), *args, **kw):
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

        xid = self.GetHandle()
        print(f"  XID = {xid}")
        if not xid:
            print("  No XID yet!")
            return

        try:
            # Get GdkWindow from XID
            display = Gdk.Display.get_default()
            gdk_window = GdkX11.X11Window.foreign_new_for_display(display, xid)
            print(f"  GdkWindow = {gdk_window}")

            if gdk_window:
                # Move via GdkWindow
                gdk_window.move(self._desired_pos[0], self._desired_pos[1])
                print(f"  Called gdk_window.move({self._desired_pos})")

            # Also try to find parent GtkWindow and set hints
            for win in Gtk.Window.list_toplevels():
                gtk_gdk = win.get_window()
                if gtk_gdk:
                    try:
                        gtk_xid = GdkX11.X11Window.get_xid(gtk_gdk)
                        if gtk_xid == xid:
                            print(f"  Found matching GtkWindow: {win}")
                            hints = Gdk.Geometry()
                            hints.min_width = 0
                            hints.min_height = 0
                            win.set_geometry_hints(None, hints, Gdk.WindowHints.USER_POS)
                            win.move(*self._desired_pos)
                            print(f"  Set USER_POS hint + move")
                            break
                    except:
                        pass

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
    frame = HintFixedFrame(pos=(100, 100), title="XID Lookup Test", size=(200, 150))
    print(f"Before Show: {frame.GetPosition()}")
    frame.Show()
    print(f"After Show: {frame.GetPosition()}")
    app.MainLoop()
