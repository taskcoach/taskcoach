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

import wx, operator
from ..thirdparty.squaremap import squaremap
from . import tooltip
from functools import reduce


class TcSquareMap(tooltip.ToolTipMixin, squaremap.SquareMap):
    def __init__(self, parent, rootNode, onSelect, onEdit, popupMenu):
        self.__selection = []
        self.getItemTooltipData = parent.getItemTooltipData
        super().__init__(
            parent, model=rootNode, adapter=parent, highlight=False
        )

        self.__tip = tooltip.SimpleToolTip(self)
        self.selectCommand = onSelect
        self.Bind(squaremap.EVT_SQUARE_SELECTED, self.onSelect)
        self.editCommand = onEdit
        self.Bind(squaremap.EVT_SQUARE_ACTIVATED, self.onEdit)
        self.popupMenu = popupMenu
        self.Bind(wx.EVT_RIGHT_DOWN, self.onPopup)

    def RefreshAllItems(self, count):  # pylint: disable=W0613
        self.UpdateDrawing()

    def RefreshItems(self, *args):  # pylint: disable=W0613
        self.UpdateDrawing()

    def onSelect(self, event):
        if event.node == self.model:
            self.__selection = []
        else:
            self.__selection = [event.node]
        wx.CallAfter(self.__safeSelectCommand)
        event.Skip()

    def __safeSelectCommand(self):
        """Safely call selectCommand, guarding against deleted C++ objects."""
        try:
            if self:
                self.selectCommand()
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def select(self, items):
        pass

    def onEdit(self, event):
        self.editCommand(event)
        event.Skip()

    def OnBeforeShowToolTip(self, x, y):
        item = squaremap.HotMapNavigator.findNodeAtPosition(
            self.hot_map, (x, y)
        )
        if item is None or item == self.model:
            return None
        tooltipData = self.getItemTooltipData(item)
        doShow = reduce(
            operator.__or__,
            list(map(bool, [data[1] for data in tooltipData])),
            False,
        )
        if doShow:
            self.__tip.SetData(tooltipData)
            return self.__tip
        else:
            return None

    def onPopup(self, event):
        self.OnClickRelease(event)  # Make sure the node is selected
        self.SetFocus()
        self.PopupMenu(self.popupMenu)

    def curselection(self):
        return self.__selection

    def GetItemCount(self):
        return 0

    def isAnyItemExpandable(self):
        return False

    isAnyItemCollapsable = isAnyItemExpandable

    def GetMainWindow(self):
        return self

    MainWindow = property(GetMainWindow)
