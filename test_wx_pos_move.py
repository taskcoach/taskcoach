#!/usr/bin/env python3
"""Test 5: Move() before Show"""
import wx

app = wx.App()
frame = wx.Frame(None, title="Move before Show", size=(200, 150))
frame.Move(100, 100)
frame.Show()
app.MainLoop()
