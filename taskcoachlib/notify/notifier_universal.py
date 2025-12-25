"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>

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

import wx
from .notifier import AbstractNotifier
from taskcoachlib import operating_system


# ==============================================================================
# Utils


class AnimatedShow(wx.Timer):
    """
    Utility class to show a frame with an animation
    """

    def __init__(self, frame, show=True):
        super().__init__()

        if frame.CanSetTransparent():
            self.__frame = frame
            self.__step = 0
            self.__show = show

            id_ = wx.NewId()
            self.SetOwner(self, id_)
            self.Bind(wx.EVT_TIMER, self.__OnTick, id=id_)
            self.Start(100)
            frame.Bind(wx.EVT_CLOSE, self.__OnClose)

            frame.SetTransparent(0)

            if show:
                frame.Show()
        else:
            frame.Show(show)

    def __OnTick(self, event):  # pylint: disable=W0613
        self.__step += 1

        if self.__show:
            alpha = int(255.0 * self.__step / 10)
        else:
            alpha = int(255.0 * (10 - (self.__step - 1)) / 10)

        self.__frame.SetTransparent(alpha)

        if self.__step == 10:
            self.Stop()

            if not self.__show:
                self.__frame.Close()

    def __OnClose(self, event):
        self.Stop()
        event.Skip()


class AnimatedMove(wx.Timer):
    """
    Utility class to move a frame with an animation
    """

    def __init__(self, frame, destination):
        super().__init__()

        self.__frame = frame
        self.__origin = frame.GetPosition()
        self.__destination = destination
        self.__step = 0

        id_ = wx.NewId()
        self.SetOwner(self, id_)
        self.Bind(wx.EVT_TIMER, self.__OnTick, id=id_)
        self.Start(100)
        frame.Bind(wx.EVT_CLOSE, self.__OnClose)

    def __OnTick(self, event):  # pylint: disable=W0613
        x0, y0 = self.__origin
        x1, y1 = self.__destination
        self.__step += 1

        curX = int(x0 + (x1 - x0) * self.__step / 10)
        curY = int(y0 + (y1 - y0) * self.__step / 10)

        self.__frame.SetPosition(wx.Point(curX, curY))

        if self.__step == 10:
            self.Stop()

    def __OnClose(self, event):
        self.Stop()
        event.Skip()


# ==============================================================================
# Notifications

if operating_system.isWindows():

    class _NotifyBase(wx.MiniFrame):
        pass

elif operating_system.isGTK():

    class _NotifyBase(wx.PopupWindow):
        def __init__(
            self, parent, id_, title, style=0
        ):  # pylint: disable=W0613,E1003
            super().__init__(parent, id_)  # No style

        def Close(self):  # pylint: disable=W0221,E1003
            # Strange...
            super().Close()
            self.Destroy()

else:

    class _NotifyBase(wx.Frame):
        """FIXME: steals focus..."""


class NotificationFrameBase(_NotifyBase):
    """
    Base class for a notification frame.

    @ivar title: The notification title
    @type title: unicode
    @ivar icon: An optional icon
    @type icon: NoneType or wx.Bitmap
    """

    def __init__(self, title, icon=None, parent=None):
        self.title = title
        self.icon = icon
        style = self.Style() | (
            wx.STAY_ON_TOP if parent is None else wx.FRAME_FLOAT_ON_PARENT
        )
        super().__init__(
            parent, wx.ID_ANY, "", style=style
        )
        self.Populate()

    def Populate(self):
        panel = wx.Panel(self, wx.ID_ANY)

        vsz = wx.BoxSizer(wx.VERTICAL)
        hsz = wx.BoxSizer(wx.HORIZONTAL)

        if self.icon is not None:
            hsz.Add(
                wx.StaticBitmap(panel, wx.ID_ANY, self.icon),
                0,
                wx.ALL | wx.ALIGN_CENTRE,
                2,
            )

        # Seems that font copy-on-write does not work sometimes...
        font = wx.FontFromNativeInfoString(
            wx.NORMAL_FONT.GetNativeFontInfoDesc()
        )
        font.SetPointSize(8)
        font.SetWeight(wx.FONTWEIGHT_BOLD)

        titleCtrl = wx.StaticText(panel, wx.ID_ANY, self.title)
        titleCtrl.SetFont(font)
        hsz.Add(titleCtrl, 1, wx.ALL | wx.ALIGN_CENTRE, 2)

        btn = self.CloseButton(panel)
        if btn is not None:
            hsz.Add(btn, 0, wx.ALL, 2)
            btn.Bind(wx.EVT_BUTTON, self.DoClose)

        vsz.Add(hsz, 0, wx.ALL | wx.EXPAND, 2)

        self.AddInnerContent(vsz, panel)

        panel.SetSizer(vsz)

        sz = wx.BoxSizer()
        sz.Add(panel, 1, wx.EXPAND)
        self.SetSizer(sz)
        self.Fit()

    def Unpopulate(self):
        self.DestroyChildren()
        self.SetSizer(None)

    def CloseButton(self, panel):
        """
        Override this to return a button instance if you want to
        customize the close button. You may also return None but if
        you do so, please provide another way for the user to dismiss
        the notification.
        """

        return wx.BitmapButton(
            panel,
            wx.ID_ANY,
            wx.ArtProvider.GetBitmap(
                "cross_red_icon", wx.ART_FRAME_ICON, (16, 16)
            ),
        )

    def AddInnerContent(self, sizer, panel):
        """
        Use this to customize the content of the frame.

        @param sizer: A vertical sizer to which you should add
            your UI elements.
        @param panel: Your parent panel.
        """

    def Style(self):
        """Return the frame's style"""

        style = wx.FRAME_NO_TASKBAR | wx.TAB_TRAVERSAL

        if operating_system.isMac():
            # style |= wx.NO_BORDER|wx.POPUP_WINDOW

            # XXXFIXME: without the POPUP_WINDOW style, the frame
            # steals the focus. But with it, when the frame is created
            # while the user is on another Space that the main
            # window's, it cannot receive user events any more, so
            # cannot be dismissed...

            style |= wx.NO_BORDER

        return style

    def DoClose(self, event=None):  # pylint: disable=W0613
        """Use this method instead of Close. Never use Close directly."""

        NotificationCenter().HideFrame(self)  # pylint: disable=E1101


class NotificationFrame(NotificationFrameBase):
    """
    A simple (and ugly) notification frame that displays a message.

    @ivar message: Message to display
    @type message: unicode
    """

    def __init__(self, message, *args, **kwargs):
        self.message = message

        super().__init__(*args, **kwargs)

    def AddInnerContent(self, sizer, panel):
        sizer.Add(
            wx.StaticText(panel, wx.ID_ANY, self.message),
            1,
            wx.ALL | wx.EXPAND,
            5,
        )


class _NotificationCenter(wx.EvtHandler):
    """
    The class that handles notification frames.
    """

    framePool = []

    def __init__(self):
        super().__init__()

        self.displayedFrames = []
        self.waitingFrames = []
        self.notificationWidth = 300
        self.notificationMargin = 5

        self.__tmr = wx.Timer()
        id_ = wx.NewId()
        self.__tmr.SetOwner(self, id_)
        self.Bind(wx.EVT_TIMER, self.__OnTick, id=id_)
        self.__tmr.Start(1000)

    def NotifyFrame(self, frm, timeout=None):
        """
        Present a new notification frame.

        @param frm: The frame to show
        @param timeout: Time to display the frame before automatically
            hiding it; in seconds.
        """

        if frm.GetParent():
            dx, dy = frm.GetParent().GetPosition()
            dw, dh = frm.GetParent().GetSize()
        else:
            dx, dy, dw, dh = self.GetDisplayRect()

        w, h = frm.GetSize()
        w = w if w > self.notificationWidth else self.notificationWidth

        bottom = dy + dh - self.notificationMargin

        for otherFrame, height, tmo in self.displayedFrames:
            bottom -= height + self.notificationMargin
            if bottom - h < 0:
                self.waitingFrames.append((frm, timeout))
                return

        if frm.GetParent():
            x = min(
                self.GetDisplayRect()[2] - self.notificationMargin - w,
                dx + dw + self.notificationMargin,
            )
        else:
            x = dx + dw - w - self.notificationMargin

        frm.SetSize(x, bottom - h - self.notificationMargin, w, h)
        self.displayedFrames.append((frm, h, timeout))

        frm.Layout()

        AnimatedShow(frm)

    def CheckWaiting(self):
        waiting = self.waitingFrames
        self.waitingFrames = []
        for frm, tmo in waiting:
            self.NotifyFrame(frm, timeout=tmo)

    def Notify(self, title, msg, icon=None, timeout=None):
        """
        Present a new simple notification frame.

        @param title: Notification title
        @param msg: Notification message
        @param timeout: See L{NotifyFrame}.
        """

        frm = NotificationFrame(msg, title, icon=icon)
        self.NotifyFrame(frm, timeout=timeout)

    def HideFrame(self, frm):
        """
        Hide a notification frame.
        """

        for idx, (frame, height, tmo) in enumerate(self.displayedFrames):
            if frame == frm:
                self.displayedFrames[idx] = (frame, height, 1)
                break

        self.CheckWaiting()

    def HideAll(self):
        """
        Hide all notification frames. Call this when you want to close
        your main frame, or else the wx loop won't exit.
        """

        for idx, (frame, height, tmo) in enumerate(self.displayedFrames):
            self.displayedFrames[idx] = (frame, height, 1)
        for frame, timeout in self.waitingFrames:
            frame.Close()
        self.waitingFrames = []

    def cleanup(self):
        """Stop the notification timer to prevent crashes during app shutdown."""
        if self.__tmr and self.__tmr.IsRunning():
            self.__tmr.Stop()
        self.HideAll()

    def GetDisplayRect(self):
        """
        Returns the geometry of the main application frame's display
        """

        dpyIndex = wx.Display.GetFromWindow(wx.GetApp().GetTopWindow())
        if dpyIndex == wx.NOT_FOUND:
            return wx.ClientDisplayRect()
        return wx.Display(dpyIndex).GetClientArea()

    def __OnTick(self, event):  # pylint: disable=W0613
        s = 0
        newList = []

        for frame, height, tmo in self.displayedFrames:
            if frame.GetParent():
                dx, dy = frame.GetParent().GetPosition()
                dw, dh = frame.GetParent().GetSize()
            else:
                dx, dy, dw, dh = self.GetDisplayRect()

            bottom = dy + dh - self.notificationMargin

            if s == 0:
                if tmo == 1:
                    frame.Close()
                    s = 1
                    continue

                newList.append(
                    (frame, height, tmo - 1 if tmo is not None else None)
                )
                bottom -= height + self.notificationMargin
            else:
                if tmo == 1:
                    frame.Close()
                else:
                    newList.append(
                        (frame, height, tmo - 1 if tmo is not None else None)
                    )
                    x, y = frame.GetPosition()
                    AnimatedMove(
                        frame, (x, bottom - height - self.notificationMargin)
                    )
                    bottom -= height + self.notificationMargin

        self.displayedFrames = newList
        self.CheckWaiting()


class NotificationCenter(object):
    _instance = None

    def __new__(self):
        if NotificationCenter._instance is None:
            NotificationCenter._instance = _NotificationCenter()
        return NotificationCenter._instance


class UniversalNotifier(AbstractNotifier):
    def getName(self):
        return "Task Coach"

    def isAvailable(self):
        return True

    def notify(self, title, summary, bitmap, **kwargs):
        NotificationCenter().Notify(
            title, summary, icon=bitmap
        )  # pylint: disable=E1101


AbstractNotifier.register(UniversalNotifier())


if __name__ == "__main__":

    class TestNotificationFrame(NotificationFrameBase):
        def AddInnerContent(self, sizer, panel):
            choice = wx.Choice(panel, wx.ID_ANY)
            choice.Append("One")
            choice.Append("Two")
            choice.Append("Three")
            sizer.Add(choice, 0, wx.ALL | wx.EXPAND, 5)

            hsz = wx.BoxSizer(wx.HORIZONTAL)
            hsz.Add(wx.Button(panel, wx.ID_ANY, "OK"), 1, wx.ALL, 2)
            hsz.Add(wx.Button(panel, wx.ID_ANY, "Cancel"), 1, wx.ALL, 2)
            sizer.Add(hsz, 0, wx.EXPAND | wx.ALL, 5)

        def CloseButton(self, panel):
            return None

    class TestFrame(wx.Frame):
        def __init__(self):
            super().__init__(None, wx.ID_ANY, "Test frame")
            # pylint: disable=E1101
            NotificationCenter().Notify(
                "Sample title", "Sample content", timeout=3
            )
            NotificationCenter().Notify(
                "Other sample",
                "Multi-line sample content\nfor example\nDont try this at home",
                timeout=3,
                icon=wx.ArtProvider.GetBitmap(
                    "taskcoach", wx.ART_FRAME_ICON, (16, 16)
                ),
            )
            NotificationCenter().Notify("Before last sample", "Spam!")
            NotificationCenter().NotifyFrame(
                TestNotificationFrame(
                    "Test custom",
                    icon=wx.ArtProvider.GetBitmap(
                        "taskcoach", wx.ART_FRAME_ICON, (16, 16)
                    ),
                )
            )
            NotificationCenter().Notify("Last sample", "Foobar!")

            self.Bind(wx.EVT_CLOSE, self.OnClose)

        def OnClose(self, evt):
            NotificationCenter().HideAll()  # pylint: disable=E1101
            evt.Skip()

    class App(wx.App):
        def OnInit(self):
            from taskcoachlib.gui import artprovider

            artprovider.init()
            TestFrame().Show()
            return True

    App(0).MainLoop()
