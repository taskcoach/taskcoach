#!/usr/bin/env python3
"""Test 2: SetPosition before Show"""
import wx

app = wx.App()
frame = wx.Frame(None, title="SetPosition before Show", size=(200, 150))
frame.SetPosition((100, 100))
frame.Show()
app.MainLoop()
