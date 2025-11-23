#!/usr/bin/env python3
"""
Test setting GTK USER_POS hint on wxPython window BEFORE Show().

The key is to set the geometry hint before the window is mapped,
so the WM knows from the start to honor our position.
"""

import wx
import time

TARGET_POS = (100, 100)

class TestFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="wx + GTK Hint Test", size=(200, 150))

        self.move_count = 0

        panel = wx.Panel(self)
        self.label = wx.StaticText(panel, label="", pos=(10, 10))

        self.Bind(wx.EVT_MOVE, self.on_move)
        self.Bind(wx.EVT_SHOW, self.on_show)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.timer.Start(100)

        self.update_position()

    def set_gtk_user_position(self):
        """Set GTK USER_POS hint before window is shown."""
        try:
            import gi
            gi.require_version('Gtk', '3.0')
            gi.require_version('Gdk', '3.0')
            from gi.repository import Gtk, Gdk, GdkX11

            handle = self.GetHandle()
            print(f"  XID handle: {handle}")

            if not handle:
                print("  No handle yet - window not realized")
                return False

            display = Gdk.Display.get_default()

            # Get the GTK window for this XID
            gdk_window = GdkX11.X11Window.foreign_new_for_display(display, handle)
            if not gdk_window:
                print("  Could not get GdkWindow")
                return False

            print(f"  Got GdkWindow: {gdk_window}")

            # Try to find the parent GtkWindow widget
            # This is the challenge - we have GdkWindow but need GtkWindow for set_geometry_hints

            # Alternative: Set position via GDK before any events
            gdk_window.move(*TARGET_POS)
            print(f"  Called gdk_window.move({TARGET_POS})")

            # Try to set the window type hint
            gdk_window.set_type_hint(Gdk.WindowTypeHint.NORMAL)

            return True

        except Exception as e:
            print(f"  GTK hint failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_position(self):
        pos = self.GetPosition()
        size = self.GetSize()
        self.label.SetLabel(f"Position: ({pos.x}, {pos.y})\nSize: ({size.width}, {size.height})\nMoves: {self.move_count}")

    def on_move(self, event):
        self.move_count += 1
        pos = event.GetPosition()
        print(f"EVT_MOVE #{self.move_count}: position=({pos.x}, {pos.y})")
        self.update_position()
        event.Skip()

    def on_show(self, event):
        pos = self.GetPosition()
        print(f"EVT_SHOW: position=({pos.x}, {pos.y}) shown={event.IsShown()}")
        event.Skip()

    def on_timer(self, event):
        self.update_position()


def main():
    print("Creating wx.App...")
    app = wx.App()

    print(f"Creating TestFrame (target={TARGET_POS})...")
    frame = TestFrame()

    # Try to set position BEFORE Show
    print("\n--- Before Show() ---")
    print("Setting position via wx.SetPosition...")
    frame.SetPosition(wx.Point(*TARGET_POS))
    pos1 = frame.GetPosition()
    print(f"After SetPosition: ({pos1.x}, {pos1.y})")

    # Force realization to get a handle
    print("\nForcing window realization...")
    frame.Show()
    frame.Hide()  # Hide immediately

    print("\nTrying to set GTK hint while hidden...")
    frame.set_gtk_user_position()

    # Now show for real
    print("\n--- Showing window ---")
    frame.SetPosition(wx.Point(*TARGET_POS))  # Set again
    frame.Show()

    pos2 = frame.GetPosition()
    print(f"After Show(): ({pos2.x}, {pos2.y})")

    print("\nStarting MainLoop...")
    app.MainLoop()

if __name__ == "__main__":
    main()
