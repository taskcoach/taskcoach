"""
Task Coach - Your friendly task manager
Copyright (C) 2012 Task Coach developers <developers@taskcoach.org>

Task Coach is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Task Coach is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Not using agw.balloontip because it doesn't position properly and
# lacks events

import wx
from taskcoachlib import patterns


class BalloonTip(wx.Frame):
    ARROWSIZE = 16
    MAXWIDTH = 300

    def __init__(
        self,
        parent,
        target,
        message=None,
        title=None,
        bitmap=None,
        get_rect=None,
    ):
        """Baloon tip."""

        super().__init__(
            parent,
            style=wx.NO_BORDER
            | wx.FRAME_FLOAT_ON_PARENT
            | wx.FRAME_NO_TASKBAR
            | wx.FRAME_SHAPED
            | wx.POPUP_WINDOW,
        )

        wheat = wx.ColourDatabase().Find("WHEAT")
        self.SetBackgroundColour(wheat)

        self._target = target
        self._get_rect = get_rect
        self._interior = wx.Panel(self)
        self._interior.Bind(wx.EVT_LEFT_DOWN, self.DoClose)
        self._interior.SetBackgroundColour(wheat)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        if bitmap is not None:
            hsizer.Add(
                wx.StaticBitmap(self._interior, wx.ID_ANY, bitmap),
                0,
                wx.ALIGN_CENTRE | wx.ALL,
                3,
            )
        if title is not None:
            title_ctrl = wx.StaticText(self._interior, wx.ID_ANY, title)
            hsizer.Add(title_ctrl, 1, wx.ALL | wx.ALIGN_CENTRE, 3)
            title_ctrl.Bind(wx.EVT_LEFT_DOWN, self.DoClose)
        vsizer.Add(hsizer, 0, wx.EXPAND)
        if message is not None:
            msg = wx.StaticText(self._interior, wx.ID_ANY, message)
            msg.Wrap(self.MAXWIDTH)
            vsizer.Add(msg, 1, wx.EXPAND | wx.ALL, 3)
            msg.Bind(wx.EVT_LEFT_DOWN, self.DoClose)

        self._interior.SetSizer(vsizer)
        self._interior.Fit()

        class Sizer(wx.Sizer):
            def __init__(self, interior, direction, offset):
                self._interior = interior
                self._direction = direction
                self._offset = offset
                super().__init__()

            def SetDirection(self, direction):
                self._direction = direction

            def CalcMin(self):
                w, h = self._interior.GetClientSize()
                return wx.Size(w, h + self._offset)

            def RecalcSizes(self):
                if self._direction == "bottom":
                    self._interior.SetPosition((0, 0))
                else:
                    self._interior.SetPosition((0, self._offset))

        self._sizer = Sizer(self._interior, "bottom", self.ARROWSIZE)
        self.SetSizer(self._sizer)
        self.Position()
        self.Show()

        wx.GetTopLevelParent(target).Bind(wx.EVT_SIZE, self._OnDim)
        wx.GetTopLevelParent(target).Bind(wx.EVT_MOVE, self._OnDim)

    def _Unbind(self):
        wx.GetTopLevelParent(self._target).Unbind(wx.EVT_SIZE)
        wx.GetTopLevelParent(self._target).Unbind(wx.EVT_MOVE)

    def _OnDim(self, event):
        patterns.later.soon(self, self.__safePosition)
        event.Skip()

    def __safePosition(self):
        """Safely call Position, guarding against deleted C++ objects."""
        try:
            if self:
                self.Position()
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def DoClose(self, event, unbind=True):
        if unbind:
            self._Unbind()
        self.Close()

    def Position(self):
        w, h = self._interior.GetClientSize()
        h += self.ARROWSIZE
        if self._get_rect is None:
            tw, th = self._target.GetSize()
            tx, ty = 0, 0
        else:
            tx, ty, tw, th = self._get_rect()
        tx, ty = self._target.ClientToScreen(wx.Point(tx, ty))
        dpy_index = max(0, wx.Display.GetFromPoint(wx.Point(tx, ty)) or 0)
        rect = wx.Display(dpy_index).GetClientArea()

        x = max(
            rect.GetLeft(), min(rect.GetRight() - w, int(tx + tw / 2 - w / 2))
        )
        y = ty - h
        direction = "bottom"
        if y < rect.GetTop():
            y = ty + th
            direction = "top"

        mask = wx.Bitmap(w, h)
        mem_dc = wx.MemoryDC()
        mem_dc.SelectObject(mask)
        try:
            mem_dc.SetBrush(wx.BLACK_BRUSH)
            mem_dc.SetPen(wx.BLACK_PEN)
            mem_dc.DrawRectangle(0, 0, w, h)

            mem_dc.SetBrush(wx.WHITE_BRUSH)
            mem_dc.SetPen(wx.WHITE_PEN)
            if direction == "bottom":
                mem_dc.DrawPolygon(
                    [
                        (0, 0),
                        (w, 0),
                        (w, h - self.ARROWSIZE),
                        (
                            tx + int(tw / 2) - x + int(self.ARROWSIZE / 2),
                            h - self.ARROWSIZE,
                        ),
                        (tx + int(tw / 2) - x, h),
                        (
                            tx + int(tw / 2) - x - int(self.ARROWSIZE / 2),
                            h - self.ARROWSIZE,
                        ),
                        (0, h - self.ARROWSIZE),
                    ]
                )
            else:
                mem_dc.DrawPolygon(
                    [
                        (0, self.ARROWSIZE),
                        (
                            tx + int(tw / 2) - x - int(self.ARROWSIZE / 2),
                            self.ARROWSIZE,
                        ),
                        (tx + int(tw / 2) - x, 0),
                        (
                            tx + int(tw / 2) - x + int(self.ARROWSIZE / 2),
                            self.ARROWSIZE,
                        ),
                        (w, self.ARROWSIZE),
                        (w, h),
                        (0, h),
                    ]
                )
            self._sizer.SetDirection(direction)
        finally:
            mem_dc.SelectObject(wx.NullBitmap)
        self.SetSize(x, y, w, h)
        self.SetShape(wx.Region(mask, wx.Colour(0, 0, 0)))
        self.Layout()


class BalloonTipManager(object):
    """
    Use this as a mixin in the top-level window that hosts balloon tip targets, to
    avoid them appearing all at once.
    """

    def __init__(self, *args, **kwargs):
        self.__tips = list()
        self.__displaying = None
        self.__kwargs = dict()
        self.__shutdown = False
        super().__init__(*args, **kwargs)

        self.Bind(wx.EVT_CLOSE, self.__OnClose)

    def AddBalloonTip(
        self,
        target,
        message=None,
        title=None,
        bitmap=None,
        get_rect=None,
        **kwargs
    ):
        """Schedules a tip. Extra keyword arguments will be passed to
        L{on_balloon_tip_show} and L{on_balloon_tip_closed}."""
        for (
            e_target,
            e_message,
            e_title,
            e_bitmap,
            e_get_rect,
            e_args,
        ) in self.__tips:
            if (e_title, e_message) == (title, message):
                return
        self.__tips.append((target, message, title, bitmap, get_rect, kwargs))
        self.__Try()

    def __Try(self):
        if self.__tips and not self.__shutdown and self.__displaying is None:
            target, message, title, bitmap, get_rect, kwargs = self.__tips.pop(
                0
            )
            tip = BalloonTip(
                self,
                target,
                message=message,
                title=title,
                bitmap=bitmap,
                get_rect=get_rect,
            )
            self.__displaying = tip
            self.on_balloon_tip_show(**kwargs)
            self.__kwargs = kwargs
            tip.Bind(wx.EVT_CLOSE, self.__OnCloseTip)

    def __OnClose(self, event):
        self.__shutdown = True
        event.Skip()

    def __OnCloseTip(self, event):
        event.Skip()
        self.__displaying = None
        self.on_balloon_tip_closed(**self.__kwargs)
        self.__Try()

    def on_balloon_tip_show(self, **kwargs):
        pass

    def on_balloon_tip_closed(self, **kwargs):
        pass
