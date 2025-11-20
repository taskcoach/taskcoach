#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .wxSchedulerCore import *
import wx.lib.scrolledpanel as scrolled
import time


class wxScheduler(wxSchedulerCore, scrolled.ScrolledPanel):

    def __init__(self, *args, **kwds):
        kwds["style"] = wx.TAB_TRAVERSAL | wx.FULL_REPAINT_ON_RESIZE

        super().__init__(*args, **kwds)

        timerId = wx.NewId()
        self._sizeTimer = wx.Timer(self, timerId)

        self._frozen = False
        self._dirty = False
        self._refreshing = False

        self._showNow = True
        self._refreshTimer = wx.Timer(self, wx.NewId())
        self._refreshTimer.Start(int(1000 * (60 - (time.time() % 60))), True)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnClick)
        self.Bind(wx.EVT_LEFT_UP, self.OnClickEnd)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClick)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnDClick)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_TIMER, self.OnSizeTimer, id=timerId)
        self.Bind(
            wx.EVT_TIMER, self.OnRefreshTimer, id=self._refreshTimer.GetId()
        )
        # Stop timers on window destruction to prevent crashes
        self.Bind(wx.EVT_WINDOW_DESTROY, self._OnDestroy)

        self.SetScrollRate(10, 10)

    # Events
    def OnClick(self, evt):
        self._doClickControl(
            self._getEventCoordinates(evt), shiftDown=evt.ShiftDown()
        )

    def OnClickEnd(self, evt):
        self._doEndClickControl(self._getEventCoordinates(evt))

    def OnMotion(self, evt):
        self._doMove(self._getEventCoordinates(evt))

    def OnRightClick(self, evt):
        self._doRightClickControl(self._getEventCoordinates(evt))

    def OnDClick(self, evt):
        self._doDClickControl(self._getEventCoordinates(evt))

    def OnSize(self, evt):
        if not self._refreshing:
            self._sizeTimer.Start(250, True)
        evt.Skip()

    def OnSizeTimer(self, evt):
        self._refreshing = True
        try:
            self.InvalidateMinSize()
            self.Refresh()
            try:
                wx.Yield()
            except:
                pass
        finally:
            self._refreshing = False

    def OnRefreshTimer(self, evt):
        self.Refresh()
        self._refreshTimer.Start(60000, True)

    def _OnDestroy(self, event):
        """Stop timers on window destruction to prevent crashes."""
        if event.GetEventObject() == self:
            if self._sizeTimer and self._sizeTimer.IsRunning():
                self._sizeTimer.Stop()
            if self._refreshTimer and self._refreshTimer.IsRunning():
                self._refreshTimer.Stop()
        event.Skip()

    def Add(self, *args, **kwds):
        wxSchedulerCore.Add(self, *args, **kwds)
        self._controlBindSchedules()

    def Refresh(self):
        if self._frozen:
            self._dirty = True
        else:
            self.DrawBuffer()
            self.GetSizer().FitInside(self)
            super().Refresh()
            self._dirty = False

    def Freeze(self):
        self._frozen = True

    def Thaw(self):
        self._frozen = False
        if self._dirty:
            self.Refresh()

    def SetResizable(self, value):
        """
        Call derived method and force wxDC refresh
        """
        super().SetResizable(value)
        self.InvalidateMinSize()
        self.Refresh()

    def OnScheduleChanged(self, event):
        if self._frozen:
            self._dirty = True
        else:
            if event.layoutNeeded:
                self.Refresh()
            else:
                self.RefreshSchedule(event.schedule)

    def _controlBindSchedules(self):
        """
        Control if all the schedules into self._schedules
        have its EVT_SCHEDULE_CHANGE binded
        """
        currentSc = set(self._schedules)
        bindSc = set(self._schBind)

        for sc in currentSc - bindSc:
            sc.Bind(EVT_SCHEDULE_CHANGE, self.OnScheduleChanged)
            self._schBind.append(sc)

    def _getEventCoordinates(self, event):
        """
        Return the coordinates associated with the given mouse event.

        The coordinates have to be adjusted to allow for the current scroll
        position.
        """
        originX, originY = self.GetViewStart()
        unitX, unitY = self.GetScrollPixelsPerUnit()

        coords = wx.Point(
            event.GetX() + (originX * unitX), event.GetY() + (originY * unitY)
        )

        return coords

    def SetViewType(self, view=None):
        super().SetViewType(view)
        self.InvalidateMinSize()
        self.Refresh()

    def SetShowNow(self, show=True):
        self._showNow = show

        if show:
            self._refreshTimer.Start(
                int(1000 * (60 - (time.time() % 60))), True
            )
        else:
            self._refreshTimer.Stop()

        self.Refresh()

    def GetShowNow(self):
        return self._showNow
