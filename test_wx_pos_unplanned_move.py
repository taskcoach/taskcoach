#!/usr/bin/env python3
"""Test 7: 4-param SetSize + detect unplanned move + reset position"""
import wx

TARGET = (100, 100)

class TestFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="4-param + unplanned move", size=(200, 150))
        self.position_applied = False
        self.move_count = 0

        # Set position via 4-param SetSize (provides position hint)
        self.SetSize(TARGET[0], TARGET[1], 200, 150)

        self.Bind(wx.EVT_MOVE, self.on_move)

    def on_move(self, event):
        self.move_count += 1
        pos = event.GetPosition()
        print(f"EVT_MOVE #{self.move_count}: ({pos.x}, {pos.y})")

        # Detect unplanned move (not at our target)
        if not self.position_applied and (pos.x != TARGET[0] or pos.y != TARGET[1]):
            print(f"  -> Unplanned move detected, resetting to {TARGET}")
            self.position_applied = True
            self.SetPosition(TARGET)
            print(f"  -> After reset: {self.GetPosition()}")

        event.Skip()

app = wx.App()
frame = TestFrame()
print(f"Before Show: {frame.GetPosition()}")
frame.Show()
print(f"After Show: {frame.GetPosition()}")
app.MainLoop()
