"""
Task Coach - Your friendly task manager
Copyright (C) 2011 Task Coach developers <developers@taskcoach.org>

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
from taskcoachlib.i18n import _


class KeychainPasswordWidget(wx.Dialog):
    def __init__(self, domain, username, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.domain = domain.encode("UTF-8")
        self.username = username.encode("UTF-8")

        pnl = wx.Panel(self, wx.ID_ANY)
        hsz = wx.BoxSizer(wx.HORIZONTAL)
        hsz.Add(wx.StaticText(pnl, wx.ID_ANY, _("Password:")), 0, wx.ALL, 3)

        from keyring import get_password

        password = get_password(self.domain, self.username)
        self.password = (password or "").decode("UTF-8")
        self.passwordField = wx.TextCtrl(
            pnl, wx.ID_ANY, self.password, style=wx.TE_PASSWORD
        )
        hsz.Add(self.passwordField, 1, wx.ALL, 3)

        vsz = wx.BoxSizer(wx.VERTICAL)
        vsz.Add(hsz, 0, wx.ALL | wx.EXPAND, 3)
        self.keepInKeychain = wx.CheckBox(
            pnl, wx.ID_ANY, _("Store in keychain")
        )
        self.keepInKeychain.SetValue(bool(password))
        vsz.Add(self.keepInKeychain, 0, wx.ALL | wx.EXPAND, 3)

        hsz = wx.BoxSizer(wx.HORIZONTAL)
        btnOK = wx.Button(pnl, wx.ID_ANY, _("OK"))
        hsz.Add(btnOK, 0, wx.ALL, 3)
        btnCancel = wx.Button(pnl, wx.ID_ANY, _("Cancel"))
        hsz.Add(btnCancel, 0, wx.ALL, 3)
        vsz.Add(hsz, 0, wx.ALL | wx.ALIGN_CENTRE, 3)

        pnl.SetSizer(vsz)

        sz = wx.BoxSizer(wx.HORIZONTAL)
        sz.Add(pnl, 1, wx.EXPAND | wx.ALL, 3)
        self.SetSizer(sz)
        self.Fit()

        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)

        self.SetDefaultItem(btnOK)
        wx.CallAfter(self.RequestUserAttention)

    def OnOK(self, event):
        self.password = self.passwordField.GetValue()
        from keyring import set_password

        if self.keepInKeychain.GetValue():
            set_password(
                self.domain, self.username, self.password.encode("UTF-8")
            )
        else:
            set_password(self.domain, self.username, "")
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)


_PASSWORDCACHE = None


def _GetCachedPassword(domain, username, reset):
    global _PASSWORDCACHE

    if _PASSWORDCACHE is None:
        import io, traceback

        bf = io.StringIO()
        traceback.print_exc(file=bf)
        wx.MessageBox(
            _(
                "There was a problem trying to find out your system's keychain.\nPlease file a bug report (see the Help menu) and attach a screenshot of this message.\nError was:\n\n%s"
            )
            % bf.getvalue(),
            _("Error"),
            wx.OK,
        )
        _PASSWORDCACHE = dict()
    if (domain, username) in _PASSWORDCACHE and reset:
        del _PASSWORDCACHE[(domain, username)]
    if (domain, username) not in _PASSWORDCACHE:
        pwd = wx.GetPasswordFromUser(_("Please enter your password."), domain)
        if not pwd:
            return None
        _PASSWORDCACHE[(domain, username)] = pwd
    return _PASSWORDCACHE[(domain, username)]


def GetPassword(domain, username, reset=False):
    try:
        from keyring import set_password, get_password
    except ImportError:
        # Keychain unavailable.
        return _GetCachedPassword(domain, username, reset)

    try:
        if reset:
            set_password(domain.encode("UTF-8"), username.encode("UTF-8"), "")
        else:
            pwd = get_password(
                domain.encode("UTF-8"), username.encode("UTF-8")
            )
            if pwd:
                return pwd.decode("UTF-8")
    except ImportError:
        # Bug seen on Ubuntu 13.10: secretstorage cannot import ._gi
        return _GetCachedPassword(domain, username, reset)

    dlg = KeychainPasswordWidget(
        domain,
        username,
        None,
        wx.ID_ANY,
        _("Please enter your password"),
        style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP,
    )
    try:
        dlg.CentreOnScreen()
        if dlg.ShowModal() == wx.ID_OK:
            return dlg.password
    finally:
        dlg.Destroy()
