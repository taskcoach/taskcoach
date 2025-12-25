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

from taskcoachlib import operating_system
from taskcoachlib.widgets import itemctrl
import wx.lib.mixins.listctrl


class VirtualListCtrl(
    itemctrl.CtrlWithItemsMixin,
    itemctrl.CtrlWithColumnsMixin,
    itemctrl.CtrlWithToolTipMixin,
    wx.ListCtrl,
):
    def __init__(
        self,
        parent,
        columns,
        selectCommand=None,
        editCommand=None,
        itemPopupMenu=None,
        columnPopupMenu=None,
        resizeableColumn=0,
        *args,
        **kwargs
    ):
        super().__init__(
            parent,
            style=wx.LC_REPORT | wx.LC_VIRTUAL,
            columns=columns,
            resizeableColumn=resizeableColumn,
            itemPopupMenu=itemPopupMenu,
            columnPopupMenu=columnPopupMenu,
            *args,
            **kwargs
        )
        # Override GetEffectiveMinSize() which returns BestSize - allows sizer to shrink widget
        self.SetMinSize((100, 50))
        self.__parent = parent
        self.bindEventHandlers(selectCommand, editCommand)

    def bindEventHandlers(self, selectCommand, editCommand):
        # pylint: disable=W0201
        if selectCommand:
            self.selectCommand = selectCommand
            self.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.onSelect)
            self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onSelect)
            self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.onSelect)
        if editCommand:
            self.editCommand = editCommand
            self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onItemActivated)
        self.Bind(wx.EVT_SET_FOCUS, self.onSetFocus)

    def onSetFocus(self, event):  # pylint: disable=W0613
        # Send a child focus event to let the AuiManager know we received focus
        # so it will activate our pane
        wx.PostEvent(self, wx.ChildFocusEvent(self))
        event.Skip()

    def getItemWithIndex(self, rowIndex):
        return self.__parent.getItemWithIndex(rowIndex)

    def getItemText(self, domainObject, columnIndex):
        return self.__parent.getItemText(domainObject, columnIndex)

    def getItemTooltipData(self, domainObject):
        return self.__parent.getItemTooltipData(domainObject)

    def getItemImage(self, domainObject, columnIndex=0):
        return self.__parent.getItemImages(domainObject, columnIndex)[
            wx.TreeItemIcon_Normal
        ]

    def OnGetItemText(self, rowIndex, columnIndex):
        item = self.getItemWithIndex(rowIndex)
        return self.getItemText(item, columnIndex)

    def OnGetItemTooltipData(self, rowIndex, columnIndex):
        item = self.getItemWithIndex(rowIndex)
        return self.getItemTooltipData(item)

    def OnGetItemImage(self, rowIndex):
        item = self.getItemWithIndex(rowIndex)
        return self.getItemImage(item)

    def OnGetItemColumnImage(self, rowIndex, columnIndex):
        item = self.getItemWithIndex(rowIndex)
        return self.getItemImage(item, columnIndex)

    def OnGetItemAttr(self, rowIndex):
        item = self.getItemWithIndex(rowIndex)
        foreground_color = item.foregroundColor(recursive=True)
        background_color = item.backgroundColor(recursive=True)
        item_attribute_arguments = [foreground_color, background_color]
        font = item.font(recursive=True)
        if font is None:
            # FIXME: Is the right way to get the font here?
            # wxItemAttr required a font for initialization, so we give one
            font = self.GetFont()

        item_attribute_arguments.append(font)

        # We need to keep a reference to the item attribute to prevent it
        # from being garbage collected too soon:
        self.__item_attribute = wx.ItemAttr(
            *item_attribute_arguments
        )  # pylint: disable=W0142,W0201
        return self.__item_attribute

    def onSelect(self, event):
        event.Skip()
        self.selectCommand(event)

    def onItemActivated(self, event):
        """Override default behavior to attach the column clicked on
        to the event so we can use it elsewhere."""
        window = self.GetMainWindow()
        if operating_system.isMac():
            window = window.GetChildren()[0]
        mouse_position = window.ScreenToClient(wx.GetMousePosition())
        index, dummy_flags, column = self.HitTest(mouse_position)
        if index >= 0:
            # Only get the column name if the hittest returned an item,
            # otherwise the item was activated from the menu or by double
            # clicking on a portion of the tree view not containing an item.
            column = max(0, column)  # FIXME: Why can the column be -1?
            event.columnName = self._getColumn(
                column
            ).name()  # pylint: disable=E1101
        self.editCommand(event)

    def RefreshAllItems(self, count):
        self.SetItemCount(count)
        if count == 0:
            self.DeleteAllItems()
        else:
            # The VirtualListCtrl makes sure only visible items are updated
            super().RefreshItems(0, count - 1)
        self.selectCommand()

    def RefreshItems(self, *items):
        """Refresh specific items."""
        if len(items) <= 7:
            for item in items:
                self.RefreshItem(self.__parent.getIndexOfItem(item))
        else:
            self.RefreshAllItems(self.GetItemCount())

    def HitTest(self, xxx_todo_changeme, *args, **kwargs):
        """Always return a three-tuple (item, flag, column)."""
        (x, y) = xxx_todo_changeme
        index, flags = super().HitTest((x, y), *args, **kwargs)
        column = 0
        if self.InReportView():
            # Determine the column in which the user clicked
            cumulative_column_width = 0
            for column_index in range(self.GetColumnCount()):
                cumulative_column_width += self.GetColumnWidth(column_index)
                if x <= cumulative_column_width:
                    column = column_index
                    break
        return index, flags, column

    def curselection(self):
        # Guard against deleted C++ object - can happen when wx.CallAfter
        # callback executes after window destruction (e.g., closing nested dialogs)
        try:
            # Filter out None values - getItemWithIndex can return None for some indices
            return [
                item for index in self.__curselection_indices()
                if (item := self.getItemWithIndex(index)) is not None
            ]
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            return []

    def select(self, items):
        indices = [self.__parent.getIndexOfItem(item) for item in items]
        for index in range(self.GetItemCount()):
            self.Select(index, index in indices)
        if self.curselection():
            self.Focus(self.GetFirstSelected())

    def clear_selection(self):
        """Unselect all selected items."""
        for index in self.__curselection_indices():
            self.Select(index, False)

    def select_all(self):
        """Select all items."""
        for index in range(self.GetItemCount()):
            self.Select(index)

    def __curselection_indices(self):
        """Return the indices of the currently selected items."""
        return wx.lib.mixins.listctrl.getListCtrlSelection(self)
