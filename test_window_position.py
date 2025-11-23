#!/usr/bin/env python3
"""
Minimal wxPython window position test.
Tests if GTK honors SetPosition/SetSize for a simple window.
"""

import wx

class TestFrame(wx.Frame):
    def __init__(self):
        # Create frame with explicit position and size
        super().__init__(None, title="Position Test", pos=(100, 100), size=(200, 150))

        # Add a panel with position info
        panel = wx.Panel(self)
        self.label = wx.StaticText(panel, label="", pos=(10, 10))

        # Update position display
        self.update_position()

        # Bind move event to track position changes
        self.Bind(wx.EVT_MOVE, self.on_move)
        self.Bind(wx.EVT_SHOW, self.on_show)

        # Timer to continuously update position
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.timer.Start(100)  # Update every 100ms

        self.move_count = 0

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

    print("Creating TestFrame at pos=(100, 100), size=(200, 150)...")
    frame = TestFrame()

    pos_before = frame.GetPosition()
    print(f"Before Show(): position=({pos_before.x}, {pos_before.y})")

    print("Calling Show()...")
    frame.Show()

    pos_after = frame.GetPosition()
    print(f"After Show(): position=({pos_after.x}, {pos_after.y})")

    print("Starting MainLoop...")
    app.MainLoop()

if __name__ == "__main__":
    main()
