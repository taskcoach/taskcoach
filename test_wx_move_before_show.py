#!/usr/bin/env python3
"""
Test different wxPython methods to set position BEFORE Show().

Try various combinations to find what works on GTK.
"""

import wx
import sys
import time

TARGET_POS = (100, 100)

class TestFrame(wx.Frame):
    def __init__(self, method="constructor"):
        self.method = method
        self.move_count = 0

        if method == "constructor":
            # Method 1: Set in constructor
            super().__init__(None, title=f"Test: {method}", pos=TARGET_POS, size=(200, 150))
        else:
            super().__init__(None, title=f"Test: {method}", size=(200, 150))

        panel = wx.Panel(self)
        self.label = wx.StaticText(panel, label="", pos=(10, 10))

        self.Bind(wx.EVT_MOVE, self.on_move)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda e: self.update_label())
        self.timer.Start(100)

    def update_label(self):
        pos = self.GetPosition()
        self.label.SetLabel(f"Method: {self.method}\nPos: ({pos.x}, {pos.y})\nMoves: {self.move_count}")

    def on_move(self, event):
        self.move_count += 1
        pos = event.GetPosition()
        print(f"  EVT_MOVE #{self.move_count}: ({pos.x}, {pos.y})")
        self.update_label()
        event.Skip()


def test_method(name, setup_func):
    """Run a single test method."""
    print(f"\n{'='*50}")
    print(f"Testing: {name}")
    print('='*50)

    app = wx.App()
    frame = TestFrame(method=name)

    # Let the setup function do its thing
    setup_func(frame)

    pos_before = frame.GetPosition()
    print(f"Before Show(): ({pos_before.x}, {pos_before.y})")

    frame.Show()

    pos_after = frame.GetPosition()
    print(f"After Show(): ({pos_after.x}, {pos_after.y})")

    # Process events for 500ms to see WM moves
    start = time.time()
    while time.time() - start < 0.5:
        app.Yield()
        time.sleep(0.05)

    pos_final = frame.GetPosition()
    print(f"Final position: ({pos_final.x}, {pos_final.y})")
    print(f"Total moves: {frame.move_count}")

    success = (pos_final.x == TARGET_POS[0] and pos_final.y == TARGET_POS[1])
    # Allow for decoration offset
    close = abs(pos_final.x - TARGET_POS[0]) < 30 and abs(pos_final.y - TARGET_POS[1]) < 50

    frame.Destroy()
    app.Destroy()

    return success, close, frame.move_count


def main():
    methods = [
        ("constructor pos=", lambda f: None),
        ("SetPosition before Show", lambda f: f.SetPosition(wx.Point(*TARGET_POS))),
        ("Move before Show", lambda f: f.Move(*TARGET_POS)),
        ("SetSize 4-param", lambda f: f.SetSize(*TARGET_POS, 200, 150)),
        ("MoveXY", lambda f: f.MoveXY(*TARGET_POS)),
        ("SetRect", lambda f: f.SetRect(wx.Rect(*TARGET_POS, 200, 150))),
    ]

    results = []
    for name, setup in methods:
        try:
            success, close, moves = test_method(name, setup)
            results.append((name, success, close, moves))
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append((name, False, False, -1))

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"{'Method':<30} {'Exact?':<8} {'Close?':<8} {'Moves':<6}")
    print("-"*60)
    for name, success, close, moves in results:
        print(f"{name:<30} {'✓' if success else '✗':<8} {'✓' if close else '✗':<8} {moves:<6}")

if __name__ == "__main__":
    main()
