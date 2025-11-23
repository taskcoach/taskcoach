#!/usr/bin/env python3
"""Simple wxPython position test - the minimal working solution."""

import wx

TARGET = (100, 100)

app = wx.App()
frame = wx.Frame(None, title="Simple Test", size=(200, 150))

frame.Show()
wx.CallAfter(frame.SetPosition, wx.Point(*TARGET))

app.MainLoop()
