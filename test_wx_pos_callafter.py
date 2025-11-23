#!/usr/bin/env python3
"""Test 4: CallAfter SetPosition after Show"""
import wx

app = wx.App()
frame = wx.Frame(None, title="CallAfter SetPosition", size=(200, 150))
frame.Show()
wx.CallAfter(frame.SetPosition, (100, 100))
app.MainLoop()
