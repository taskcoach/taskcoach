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
from taskcoachlib import persistence, gui


class Event(object):
    def Skip(self):
        pass


class DummyWidget(wx.Frame):
    def __init__(self, viewer):
        super().__init__(viewer)
        self.viewer = viewer

    def RefreshItems(self, *items):
        pass

    def curselection(self):
        return []

    def select(self, *args):
        pass

    def clear_selection(self):
        pass

    def GetItemCount(self):
        return len(self.viewer.presentation())

    def RefreshAllItems(self, *args, **kwargs):
        pass

    def IsAutoResizing(self):
        return False

    def GetMainWindow(self):
        return self

    def Bind(self, *args, **kwargs):
        pass


class DummyUICommand(gui.uicommand.UICommand):  # pylint: disable=W0223
    bitmap = "undo"
    section = "view"
    setting = "setting"

    def on_command_activate(self, event):
        self.activated = True  # pylint: disable=W0201


class ViewerWithDummyWidget(gui.viewer.base.Viewer):  # pylint: disable=W0223
    defaultTitle = "ViewerWithDummyWidget"
    defaultBitmap = ""

    def domainObjectsToView(self):
        return self.taskFile.tasks()

    def createWidget(self):
        self._columns = self._createColumns()  # pylint: disable=W0201
        return DummyWidget(self)

    def _createColumns(self):
        return []


class TaskFile(persistence.TaskFile):
    raiseError = None

    def load(self, *args, **kwargs):  # pylint: disable=W0613
        if self.raiseError:
            raise self.raiseError  # pylint: disable=E0702

    merge = save = saveas = load


class MainWindow:  # pylint: disable=W0232
    showFindDialog = None
