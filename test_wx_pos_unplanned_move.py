#!/usr/bin/env python3
"""Test: EVT_MOVE correction until EVT_ACTIVATE

   Key finding: The window manager may move the window multiple times during setup.
   Keep correcting position on every EVT_MOVE until EVT_ACTIVATE fires (window is ready).

   See WINDOW_POSITION_PERSISTENCE_ANALYSIS.md for full details."""
import wx
import time

TARGET = (100, 100)
START_TIME = None

class TestFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="EVT_MOVE until EVT_ACTIVATE", size=(200, 150))
        self.window_activated = False  # Track when window is ready for input
        self.move_count = 0
        self.idle_count = 0
        self.paint_count = 0
        self.activate_count = 0
        self.corrections_made = 0

        # Set position via 4-param SetSize (provides position hint)
        self.SetSize(TARGET[0], TARGET[1], 200, 150)

        # Bind events
        self.Bind(wx.EVT_MOVE, self.on_move)
        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_ACTIVATE, self.on_activate)
        self.Bind(wx.EVT_SHOW, self.on_show)

    def _elapsed(self):
        return f"{(time.time() - START_TIME)*1000:.0f}ms"

    def on_move(self, event):
        self.move_count += 1
        pos = event.GetPosition()

        # Check for off-screen position
        off_screen = pos.x < 0 or pos.y < 0
        off_screen_str = " [OFF-SCREEN!]" if off_screen else ""

        print(f"[{self._elapsed()}] EVT_MOVE #{self.move_count}: ({pos.x}, {pos.y}){off_screen_str}")

        # Keep correcting until window is activated (ready for input)
        if not self.window_activated and (pos.x != TARGET[0] or pos.y != TARGET[1]):
            self.corrections_made += 1
            print(f"  -> Correction #{self.corrections_made}: resetting to {TARGET}")
            self.SetPosition(TARGET)

        event.Skip()

    def on_idle(self, event):
        self.idle_count += 1
        pos = self.GetPosition()
        # Only log first few idle events to avoid spam
        if self.idle_count <= 10:
            print(f"[{self._elapsed()}] EVT_IDLE #{self.idle_count}: pos=({pos.x}, {pos.y}) - Event queue empty")
        elif self.idle_count == 11:
            print(f"[{self._elapsed()}] EVT_IDLE ... (suppressing further idle logs)")
        event.Skip()

    def on_paint(self, event):
        self.paint_count += 1
        pos = self.GetPosition()
        if self.paint_count <= 5:
            print(f"[{self._elapsed()}] EVT_PAINT #{self.paint_count}: pos=({pos.x}, {pos.y}) - Window being drawn")
        event.Skip()

    def on_activate(self, event):
        self.activate_count += 1
        pos = self.GetPosition()
        active = event.GetActive()

        if active and not self.window_activated:
            self.window_activated = True
            print(f"[{self._elapsed()}] EVT_ACTIVATE #{self.activate_count}: pos=({pos.x}, {pos.y}) active={active}")
            print(f"  -> WINDOW READY - Made {self.corrections_made} position corrections")
            print(f"  -> Stopping position corrections (unbinding EVT_MOVE)")
            # Unbind to avoid overhead after window is ready
            self.Unbind(wx.EVT_MOVE)
        else:
            ready_msg = " [READY]" if self.window_activated else ""
            print(f"[{self._elapsed()}] EVT_ACTIVATE #{self.activate_count}: pos=({pos.x}, {pos.y}) active={active}{ready_msg}")

        event.Skip()

    def on_show(self, event):
        pos = self.GetPosition()
        shown = event.IsShown()
        print(f"[{self._elapsed()}] EVT_SHOW: pos=({pos.x}, {pos.y}) shown={shown}")
        event.Skip()

START_TIME = time.time()
app = wx.App()
frame = TestFrame()
print(f"[{(time.time() - START_TIME)*1000:.0f}ms] Before Show: {frame.GetPosition()}")
frame.Show()
print(f"[{(time.time() - START_TIME)*1000:.0f}ms] After Show: {frame.GetPosition()}")
print(f"\n--- Entering MainLoop (waiting for events) ---\n")
app.MainLoop()
