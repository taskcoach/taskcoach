#!/usr/bin/env python3
"""Test 3: SetPosition after Show"""
import wx

app = wx.App()
frame = wx.Frame(None, title="SetPosition after Show", size=(200, 150))
frame.Show()
frame.SetPosition((100, 100))
app.MainLoop()
