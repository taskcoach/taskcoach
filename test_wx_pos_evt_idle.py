#!/usr/bin/env python3
"""Test: EVT_IDLE approach (official wxPython recommendation)"""
import wx

TARGET = (100, 100)

class TestFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="EVT_IDLE position", size=(200, 150))
        self.position_set = False
        self.move_count = 0

        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.Bind(wx.EVT_MOVE, self.on_move)

    def on_idle(self, event):
        if not self.position_set:
            self.position_set = True
            print(f"EVT_IDLE: Setting position to {TARGET}")
            self.SetPosition(TARGET)
            print(f"EVT_IDLE: Position now {self.GetPosition()}")
        event.Skip()

    def on_move(self, event):
        self.move_count += 1
        pos = event.GetPosition()
        print(f"EVT_MOVE #{self.move_count}: ({pos.x}, {pos.y})")
        event.Skip()

app = wx.App()
frame = TestFrame()
print(f"Before Show: {frame.GetPosition()}")
frame.Show()
print(f"After Show: {frame.GetPosition()}")
app.MainLoop()
