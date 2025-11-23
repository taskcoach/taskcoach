#!/usr/bin/env python3
"""Test 1: Position in constructor (standard wxPython way)"""
import wx

app = wx.App()
frame = wx.Frame(None, title="pos in constructor", pos=(100, 100), size=(200, 150))
frame.Show()
app.MainLoop()
