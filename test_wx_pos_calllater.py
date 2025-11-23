#!/usr/bin/env python3
"""Test 6: CallLater with 50ms delay"""
import wx

app = wx.App()
frame = wx.Frame(None, title="CallLater 50ms", size=(200, 150))
frame.Show()
wx.CallLater(50, frame.SetPosition, (100, 100))
app.MainLoop()
