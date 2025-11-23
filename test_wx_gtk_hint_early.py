#!/usr/bin/env python3
"""
Set GTK USER_POS hint EARLY - before Show().

The key is to set the hint on the GtkWindow BEFORE it's mapped.
We access the underlying GTK widget right after wx.Frame creation.
"""

import wx

TARGET = (100, 100)

def set_gtk_hints_early(wx_frame):
    """Set GTK geometry hints with USER_POS before window is shown."""
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        gi.require_version('Gdk', '3.0')
        from gi.repository import Gtk, Gdk

        # wxPython creates a GtkWindow - find it by iterating toplevels
        # At this point, the wx.Frame exists but hasn't been Show()n yet
        for win in Gtk.Window.list_toplevels():
            title = win.get_title()
            if title and wx_frame.GetTitle() in title:
                print(f"Found GtkWindow: {win} title='{title}'")

                # Set geometry hints with USER_POS BEFORE showing
                geometry = Gdk.Geometry()
                geometry.min_width = 1
                geometry.min_height = 1

                # USER_POS tells WM: "user specified this position, honor it"
                win.set_geometry_hints(None, geometry, Gdk.WindowHints.USER_POS)
                print(f"Set USER_POS geometry hint")

                # Set position via GTK
                win.move(*TARGET)
                print(f"Called gtk.move({TARGET})")

                return True

        print("Could not find GtkWindow")
        return False

    except Exception as e:
        print(f"GTK hint failed: {e}")
        import traceback
        traceback.print_exc()
        return False


class TestFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="GTK Hint Early Test", size=(200, 150))
        self.move_count = 0
        self.Bind(wx.EVT_MOVE, self.on_move)

    def on_move(self, event):
        self.move_count += 1
        pos = event.GetPosition()
        print(f"EVT_MOVE #{self.move_count}: ({pos.x}, {pos.y})")
        event.Skip()


app = wx.App()
frame = TestFrame()

print(f"\nBefore GTK hint: {frame.GetPosition()}")

# Set GTK hint BEFORE Show
success = set_gtk_hints_early(frame)
print(f"GTK hint success: {success}")

print(f"Before Show: {frame.GetPosition()}")
frame.Show()
print(f"After Show: {frame.GetPosition()}")

app.MainLoop()
