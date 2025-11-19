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
import wx.lib.agw.hyperlink as hl

from taskcoachlib.i18n import _
from taskcoachlib import operating_system


class IPhoneSyncTypeDialog(wx.Dialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        vsz = wx.BoxSizer(wx.VERTICAL)
        vsz.Add(
            wx.StaticText(
                self,
                wx.ID_ANY,
                _(
                    """An iPhone or iPod Touch device is trying
to synchronize with this task file for
the first time. What kind of synchronization
would you like to use?"""
                ),
            ),
            1,
            wx.EXPAND | wx.ALL,
            5,
        )

        hsz = wx.BoxSizer(wx.HORIZONTAL)
        btn = wx.Button(self, wx.ID_ANY, _("Refresh from desktop"))
        hsz.Add(btn, 0, wx.ALL, 3)
        btn.Bind(wx.EVT_BUTTON, self.OnType1)
        btn = wx.Button(self, wx.ID_ANY, _("Refresh from device"))
        hsz.Add(btn, 0, wx.ALL, 3)
        btn.Bind(wx.EVT_BUTTON, self.OnType2)
        btn = wx.Button(self, wx.ID_ANY, _("Cancel"))
        hsz.Add(btn, 0, wx.ALL, 3)
        btn.Bind(wx.EVT_BUTTON, self.OnCancel)
        vsz.Add(hsz, 0, wx.ALIGN_RIGHT)

        self.SetSizer(vsz)
        self.Fit()
        self.CentreOnScreen()
        self.RequestUserAttention()

        self.value = 3  # cancel

    def OnType1(self, evt):
        self.value = 1
        self.EndModal(wx.ID_OK)

    def OnType2(self, evt):
        self.value = 2
        self.EndModal(wx.ID_OK)

    def OnCancel(self, evt):
        self.EndModal(wx.ID_CANCEL)


class IPhoneBonjourDialog(wx.Dialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(
            wx.StaticText(
                self,
                wx.ID_ANY,
                _(
                    "You have enabled the iPhone synchronization feature, which\n"
                    "needs the python-zeroconf library. This library does not seem\n"
                    "to be installed on your system."
                ),
            ),
            0,
            wx.ALL,
            3,
        )
        vsizer.Add(
            wx.StaticText(
                self,
                wx.ID_ANY,
                _(
                    "Please install the zeroconf library using pip:\n\n"
                    "    pip install zeroconf\n"
                ),
            ),
            0,
            wx.ALL,
            3,
        )
        vsizer.Add(
            hl.HyperLinkCtrl(
                self,
                wx.ID_ANY,
                _("python-zeroconf on PyPI"),
                URL="https://pypi.org/project/zeroconf/",
            ),
            0,
            wx.ALL,
            3,
        )
        if not operating_system.isWindows() and not operating_system.isMac():
            # Linux may need firewall configuration
            vsizer.Add(
                wx.StaticText(
                    self,
                    wx.ID_ANY,
                    _(
                        "In addition, if you have a firewall, check that ports 4096-4100 are open."
                    ),
                ),
                0,
                wx.ALL,
                3,
            )

        btnOK = wx.Button(self, wx.ID_ANY, _("OK"))
        vsizer.Add(btnOK, 0, wx.ALIGN_CENTRE | wx.ALL, 3)

        self.SetSizer(vsizer)
        self.Fit()
        self.CentreOnScreen()

        btnOK.Bind(wx.EVT_BUTTON, self.OnDismiss)

    def OnDismiss(self, evt):
        self.EndModal(wx.ID_OK)
