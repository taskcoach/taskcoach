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

from taskcoachlib import meta
from taskcoachlib.i18n import _
from wx.lib import sized_controls
import wx


tips = [
    _(
        """%(name)s is actively developed. Although the %(name)s developers try hard to prevent them, bugs do happen. So, backing up your work on a regular basis is strongly advised."""
    )
    % meta.metaDict,
    _(
        """%(name)s has a mailing list where you can discuss usage of %(name)s with fellow users, discuss and request features and complain about bugs. Go to %(url)s and join today!"""
    )
    % meta.metaDict,
    _(
        """%(name)s has unlimited undo and redo. Any change that you make, be it editing a task description, or deleting an effort record, is undoable. Select 'Edit' -> 'Undo' and 'Edit' -> 'Redo' to go backwards and forwards through your edit history."""
    )
    % meta.metaDict,
    _(
        """%(name)s is available in a number of different languages. Select 'Edit' -> 'Preferences' to see whether your language is one of them. If your language is not available or the translation needs improvement, please consider helping with the translation of %(name)s. Visit %(url)s for more information about how you can help."""
    )
    % meta.metaDict,
    _(
        """If you enter a URL (e.g. %(url)s) in a task or effort description, it becomes a link. Clicking on the link will open the URL in your default web browser."""
    )
    % meta.metaDict,
    _(
        """You can drag and drop tasks in the tree view to rearrange parent-child relationships between tasks. The same goes for categories."""
    ),
    _(
        """You can drag files from a file browser onto a task to create attachments. Dragging the files over a tab will raise the appropriate page, dragging the files over a collapsed task (the boxed + sign) in the tree view will expand the task to show its subtasks."""
    ),
    _(
        """You can create any viewer layout you want by dragging and dropping the tabs. The layout is saved and reused in the next session."""
    ),
    _(
        """What is actually printed when you select 'File' -> 'Print' depends on the current view. If the current view shows the task list, a list of tasks will be printed, if the current view shows effort grouped by month, that will be printed. The same goes for visible columns, sort order, filtered tasks, etc."""
    ),
    _(
        """Left-click a column header to sort by that column. Click the column header again to change the sort order from ascending to descending and back again. Right-click a column header to hide that column or make additional columns visible."""
    ),
    _(
        """You can create a template from a task in order to reduce typing when repetitive patterns emerge."""
    ),
    _("""Ctrl-Tab switches between tabs in edit dialogs."""),
]


class TipProvider(object):
    def __init__(self, tip_index):
        self.__tip_index = tip_index

    def GetTip(self):
        tip = tips[self.__tip_index % len(tips)]
        self.__tip_index += 1
        if self.__tip_index >= len(tips):
            self.__tip_index = 0
        return tip

    def GetCurrentTip(self):
        return self.__tip_index


class TipDialog(sized_controls.SizedDialog):
    """Create a dialog for showing the tip of the day to the user. We don't
    use the builtin tip dialog of wxPython because that's a modal
    dialog."""

    def __init__(self, *args, **kwargs):
        self.__tip_provider = kwargs.pop("tip_provider")
        self.__settings = kwargs.pop("settings")
        super().__init__(title=_("Tip of the day"), *args, **kwargs)
        pane = self.GetContentsPane()
        pane.SetSizerType("horizontal")
        wx.StaticBitmap(
            pane,
            bitmap=wx.ArtProvider.GetBitmap(
                "nuvola_apps_ktip", wx.ART_MENU, (32, 32)
            ),
        )
        tip_pane = sized_controls.SizedPanel(pane)
        self.__tip = wx.StaticText(tip_pane)
        self.__show_tip()
        next_tip_button = wx.Button(
            tip_pane, id=wx.ID_FORWARD, label=_("Next tip")
        )
        next_tip_button.Bind(wx.EVT_BUTTON, self.on_next_tip)
        self.__check = self.__create_checkbox(tip_pane)
        button_sizer = wx.StdDialogButtonSizer()
        btn_ok = wx.Button(self, wx.ID_OK)
        btn_ok.Bind(wx.EVT_BUTTON, self.on_close)
        button_sizer.SetAffirmativeButton(btn_ok)
        button_sizer.Realize()

        self.SetButtonSizer(button_sizer)
        self.Fit()
        self.CentreOnParent()

        self.Bind(wx.EVT_CLOSE, self.on_close)

    def __show_tip(self):
        """Show the next tip."""
        self.__tip.SetLabel(self.__tip_provider.GetTip())
        self.__tip.Wrap(500)

    def __create_checkbox(self, pane):
        """Create a check box for users to indicate whether they want to
        see tips on startup."""
        checkbox = wx.CheckBox(pane, label=_("Show tips on startup"))
        checkbox.SetValue(self.__settings.getboolean("window", "tips"))
        return checkbox

    def on_next_tip(self, event):
        """Show the next tip."""
        self.__show_tip()
        self.Fit()
        event.Skip(False)

    def on_close(self, event):
        """When users close the dialog, remember whether they want to
        see tips and what the last displayed tip was."""
        event.Skip()
        self.__settings.setboolean("window", "tips", self.__check.GetValue())
        self.__settings.setint(
            "window", "tipsindex", self.__tip_provider.GetCurrentTip()
        )


def showTips(parent, settings):
    tip_provider = TipProvider(settings.getint("window", "tipsindex"))
    TipDialog(parent, tip_provider=tip_provider, settings=settings).Show()
