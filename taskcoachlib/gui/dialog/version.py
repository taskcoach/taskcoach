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
from wx.lib.agw import hyperlink
from taskcoachlib import meta
from taskcoachlib.config import settings
from taskcoachlib.i18n import _
from wx.lib import sized_controls
from taskcoachlib.tools import wxhelper


class VersionDialog(sized_controls.SizedDialog):  # pylint: disable=R0904,R0901
    """Base class for dialogs that announce a new version (and variants
    thereof)."""

    title = ""

    def __init__(self, *args, **kwargs):
        self.message = kwargs.pop("message")
        version = kwargs.pop("version")
        super().__init__(title=self.title, *args, **kwargs)
        pane = self.GetContentsPane()
        pane.SetSizerType("vertical")
        self.messageInfo = dict(
            version=version,
            name=meta.data.name,
            currentVersion=meta.data.version_full,
        )
        self.createInterior(pane)
        self.check = wx.CheckBox(pane, label=_("Notify me of new versions."))
        self.check.SetValue(settings.version.notify)
        buttonSizer = self.CreateStdDialogButtonSizer(wx.OK)
        self.SetButtonSizer(buttonSizer)
        self.Fit()
        wxhelper.get_dialog_button(buttonSizer, wx.ID_OK).Bind(
            wx.EVT_BUTTON, self.onClose
        )
        self.Bind(wx.EVT_CLOSE, self.onClose)

    def createInterior(self, pane):
        """Create the interior parts of the dialog, i.e. the message for the
        user."""
        raise NotImplementedError

    def onClose(self, event):
        """When the user closes the dialog, remember whether (s)he wants to be
        notified of new versions."""
        event.Skip()
        settings.version.notify = self.check.GetValue()


class NewVersionDialog(VersionDialog):
    title = _("New version of %(name)s available") % dict(name=meta.data.name)

    def createInterior(self, panel):
        wx.StaticText(
            panel,
            label=_("You are using %(name)s version %(currentVersion)s.")
            % self.messageInfo,
        )
        urlPanel = sized_controls.SizedPanel(panel)
        urlPanel.SetSizerType("horizontal")
        wx.StaticText(
            urlPanel,
            label=_("Version %(version)s of %(name)s is available from")
            % self.messageInfo,
        )
        hyperlink.HyperLinkCtrl(
            urlPanel,
            label=meta.data.latest_release_url,
            URL=meta.data.latest_release_url,
        )


class VersionUpToDateDialog(VersionDialog):
    title = _("%(name)s is up to date") % dict(name=meta.data.name)

    def createInterior(self, panel):
        wx.StaticText(
            panel,
            label=_("%(name)s is up to date at version %(version)s.")
            % self.messageInfo,
        )


class NoVersionDialog(VersionDialog):
    title = _("Couldn't find out latest version")

    def createInterior(self, panel):
        wx.StaticText(
            panel,
            label=_(
                "Couldn't find out what the latest " "version of %(name)s is."
            )
            % self.messageInfo,
        )
        wx.StaticText(panel, label=self.message)


class PrereleaseVersionDialog(VersionDialog):
    title = _("Prerelease version")

    def createInterior(self, panel):
        wx.StaticText(
            panel,
            label=_(
                "You are using %(name)s prerelease "
                "version %(currentVersion)s."
            )
            % self.messageInfo,
        )
        wx.StaticText(
            panel,
            label=_(
                "The latest released version of " "%(name)s is %(version)s."
            )
            % self.messageInfo,
        )
