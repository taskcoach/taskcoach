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

import wx, os
from taskcoachlib.persistence import BackupManifest
from taskcoachlib.i18n import _
from taskcoachlib import render


class BackupManagerDialog(wx.Dialog):
    def __init__(self, parent, settings, selectedFile=None):
        super().__init__(
            parent, wx.ID_ANY, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )

        # Create splitter for the two lists
        self.__splitter = wx.SplitterWindow(
            self, wx.ID_ANY, style=wx.SP_LIVE_UPDATE
        )

        # Left pane: Files list
        self.__files = wx.ListCtrl(
            self.__splitter, wx.ID_ANY, style=wx.LC_REPORT | wx.LC_SINGLE_SEL
        )
        self.__files.InsertColumn(0, _("File"))
        self.__files.InsertColumn(1, _("Full path"))

        # Right pane: Backups/Date list
        self.__backups = wx.ListCtrl(
            self.__splitter, wx.ID_ANY, style=wx.LC_REPORT | wx.LC_SINGLE_SEL
        )
        self.__backups.InsertColumn(0, _("Date"))
        self.__backups.Enable(False)

        # Configure splitter
        self.__splitter.SplitVertically(self.__files, self.__backups)
        self.__splitter.SetMinimumPaneSize(150)
        self.__splitter.SetSashGravity(1.0)

        # Button column
        btnPanel = wx.Panel(self)
        btnSizer = wx.BoxSizer(wx.VERTICAL)
        self.__btnRestore = wx.Button(btnPanel, wx.ID_ANY, _("Restore"))
        self.__btnRestore.Enable(False)
        btnClose = wx.Button(btnPanel, wx.ID_ANY, _("Close"))
        btnSizer.Add(self.__btnRestore, 0, wx.ALL, 3)
        btnSizer.AddStretchSpacer(1)
        btnSizer.Add(btnClose, 0, wx.ALL, 3)
        btnPanel.SetSizer(btnSizer)

        # Main horizontal layout: splitter + buttons
        mainSizer = wx.BoxSizer(wx.HORIZONTAL)
        mainSizer.Add(self.__splitter, 1, wx.EXPAND | wx.ALL, 3)
        mainSizer.Add(btnPanel, 0, wx.EXPAND | wx.ALL, 3)
        self.SetSizer(mainSizer)

        self.__filename = selectedFile
        self.__selection = (None, None)

        self.__manifest = BackupManifest(settings)
        self.__filenames = self.__manifest.listFiles()
        selection = None
        for filename in self.__filenames:
            item = self.__files.InsertItem(
                self.__files.GetItemCount(), os.path.split(filename)[-1]
            )
            self.__files.SetItem(item, 1, filename)
            if filename == selectedFile:
                selection = item

        btnClose.Bind(wx.EVT_BUTTON, self.DoClose)
        self.__files.Bind(wx.EVT_LIST_ITEM_SELECTED, self._OnSelectFile)
        self.__files.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._OnDeselectFile)
        self.__backups.Bind(wx.EVT_LIST_ITEM_SELECTED, self._OnSelectBackup)
        self.__backups.Bind(
            wx.EVT_LIST_ITEM_DESELECTED, self._OnDeselectBackup
        )
        self.__btnRestore.Bind(wx.EVT_BUTTON, self._OnRestore)

        if selection is not None:
            self.__files.SetItemState(
                selection,
                wx.LIST_STATE_FOCUSED | wx.LIST_STATE_SELECTED,
                wx.LIST_STATE_FOCUSED | wx.LIST_STATE_SELECTED,
            )
        self.__files.SetColumnWidth(0, -1)
        self.__files.SetColumnWidth(1, -1)

        # Set dialog size constrained to screen
        targetWidth, targetHeight = 800, 600
        datePaneWidth = 150
        display = wx.Display(wx.Display.GetFromWindow(parent) if parent else 0)
        screenRect = display.GetClientArea()
        width = min(targetWidth, screenRect.GetWidth() - 50)
        height = min(targetHeight, screenRect.GetHeight() - 50)
        self.SetSize(wx.Size(width, height))

        # Set sash position from right edge (negative value)
        self.__splitter.SetSashPosition(-datePaneWidth)
        self.CentreOnParent()

    def restoredFilename(self):
        return self.__filename

    def DoClose(self, event):
        self.EndModal(wx.ID_CANCEL)

    def _OnSelectFile(self, event):
        self.__backups.DeleteAllItems()
        backups = self.__manifest.listBackups(self.__filenames[event.GetIndex()])
        for index, dateTime in enumerate(backups):
            self.__backups.InsertItem(
                index, render.dateTime(dateTime, humanReadable=True)
            )
        # Size column to max of header width and content width
        self.__backups.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        headerWidth = self.__backups.GetColumnWidth(0)
        self.__backups.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        contentWidth = self.__backups.GetColumnWidth(0)
        if headerWidth > contentWidth:
            self.__backups.SetColumnWidth(0, headerWidth)
        # Force refresh to update header rendering
        self.__backups.Refresh()
        self.__backups.Update()
        self.__backups.Enable(True)
        self.__selection = (self.__filenames[event.GetIndex()], None)

    def _OnDeselectFile(self, event):
        self.__btnRestore.Enable(False)
        self.__backups.DeleteAllItems()
        self.__backups.Enable(False)
        self.__selection = (None, None)

    def _OnSelectBackup(self, event):
        self.__btnRestore.Enable(True)
        filename = self.__selection[0]
        self.__selection = (
            filename,
            self.__manifest.listBackups(filename)[event.GetIndex()],
        )

    def _OnDeselectBackup(self, event):
        self.__btnRestore.Enable(False)
        self.__selection = (self.__selection[0], None)

    def _OnRestore(self, event):
        filename, dateTime = self.__selection
        dlg = wx.FileDialog(
            self,
            _("Choose the restoration destination"),
            defaultDir=os.path.dirname(filename),
            defaultFile=os.path.split(filename)[-1],
            wildcard="*.tsk",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self.__filename = dlg.GetPath()
                self.__manifest.restoreFile(
                    filename, dateTime, self.__filename
                )
                self.EndModal(wx.ID_OK)
        finally:
            dlg.Destroy()
