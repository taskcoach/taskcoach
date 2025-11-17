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
from wx.lib.agw import hypertreelist
from taskcoachlib import operating_system


class AutoColumnWidthMixin(object):
    """A mix-in class that automatically resizes one column to take up
    the remaining width of a control with columns (i.e. ListCtrl,
    TreeListCtrl).

    This causes the control to automatically take up the full width
    available, without either a horizontal scroll bar (unless absolutely
    necessary) or empty space to the right of the last column.

    NOTE:    When using this mixin with a ListCtrl, make sure the ListCtrl
             is in report mode.

    WARNING: If you override the EVT_SIZE event in your control, make
             sure you call event.Skip() to ensure that the mixin's
             OnResize method is called.
    """

    def __init__(self, *args, **kwargs):
        self.__is_auto_resizing = False
        self.ResizeColumn = kwargs.pop("resizeableColumn", -1)
        self.ResizeColumnMinWidth = kwargs.pop("resizeableColumnMinWidth", 50)
        super().__init__(*args, **kwargs)

    def SetResizeColumn(self, column):
        self.ResizeColumn = column

    def ToggleAutoResizing(self, on):
        if on == self.__is_auto_resizing:
            return
        self.__is_auto_resizing = on
        if on:
            self.Bind(wx.EVT_SIZE, self.OnResize)
            self.Bind(wx.EVT_LIST_COL_BEGIN_DRAG, self.OnBeginColumnDrag)
            self.Bind(wx.EVT_LIST_COL_END_DRAG, self.OnEndColumnDrag)
            self.DoResize()
        else:
            self.Unbind(wx.EVT_SIZE)
            self.Unbind(wx.EVT_LIST_COL_BEGIN_DRAG)
            self.Unbind(wx.EVT_LIST_COL_END_DRAG)

    def IsAutoResizing(self):
        return self.__is_auto_resizing

    def OnBeginColumnDrag(self, event):
        # pylint: disable=W0201
        if event.Column == self.ResizeColumn:
            self.__oldResizeColumnWidth = self.GetColumnWidth(
                self.ResizeColumn
            )
        # Temporarily unbind the EVT_SIZE to prevent resizing during dragging
        self.Unbind(wx.EVT_SIZE)
        event.Skip()  # Always skip to allow default drag handling on all platforms

    def OnEndColumnDrag(self, event):
        if event.Column == self.ResizeColumn and self.GetColumnCount() > 1:
            extra_width = self.__oldResizeColumnWidth - self.GetColumnWidth(
                self.ResizeColumn
            )
            self.DistributeWidthAcrossColumns(extra_width)
        self.Bind(wx.EVT_SIZE, self.OnResize)
        # Only auto-resize if the user dragged a different column
        # If they dragged the ResizeColumn itself, respect their manual sizing
        if event.Column != self.ResizeColumn:
            wx.CallAfter(self.DoResize)
        event.Skip()

    def OnResize(self, event):
        event.Skip()
        if operating_system.isWindows():
            wx.CallAfter(self.DoResize)
        else:
            self.DoResize()

    def DoResize(self):
        if not self:
            return  # Avoid a potential PyDeadObject error
        if not self.IsAutoResizing():
            return
        if self.GetSize().height < 32:
            return  # Avoid an endless update bug when the height is small.
        if self.GetColumnCount() <= self.ResizeColumn:
            return  # Nothing to resize.

        unused_width = max(self.AvailableWidth - self.NecessaryWidth, 0)
        resize_column_width = self.ResizeColumnMinWidth + unused_width
        self.SetColumnWidth(self.ResizeColumn, resize_column_width)

    def DistributeWidthAcrossColumns(self, extra_width):
        # When the user resizes the ResizeColumn distribute the extra available
        # space across the other columns, or get the extra needed space from
        # the other columns. The other columns are resized proportionally to
        # their previous width.
        other_columns = [
            index
            for index in range(self.GetColumnCount())
            if index != self.ResizeColumn
        ]
        total_width = float(
            sum(self.GetColumnWidth(index) for index in other_columns)
        )
        for column_index in other_columns:
            this_column_width = self.GetColumnWidth(column_index)
            this_column_width += this_column_width // total_width * extra_width
            self.SetColumnWidth(column_index, int(this_column_width))

    def GetResizeColumn(self):
        if self.__resize_column == -1:
            return self.GetColumnCount() - 1
        else:
            return self.__resize_column

    def SetResizeColumn(self, column_index):
        self.__resize_column = column_index  # pylint: disable=W0201

    ResizeColumn = property(GetResizeColumn, SetResizeColumn)

    def GetAvailableWidth(self):
        available_width = self.GetClientSize().width
        if (
            self.__is_scrollbar_visible()
            and self.__is_scrollbar_included_in_client_size()
        ):
            scrollbar_width = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
            available_width -= scrollbar_width
        return available_width

    AvailableWidth = property(GetAvailableWidth)

    def GetNecessaryWidth(self):
        necessary_width = 0
        for column_index in range(self.GetColumnCount()):
            if column_index == self.ResizeColumn:
                necessary_width += self.ResizeColumnMinWidth
            else:
                necessary_width += self.GetColumnWidth(column_index)
        return necessary_width

    NecessaryWidth = property(GetNecessaryWidth)

    # Override all methods that manipulate columns to be able to resize the
    # columns after any additions or removals.

    def InsertColumn(self, *args, **kwargs):
        """Insert the new column and then resize."""
        result = super().InsertColumn(*args, **kwargs)
        self.DoResize()
        return result

    def DeleteColumn(self, *args, **kwargs):
        """Delete the column and then resize."""
        result = super().DeleteColumn(*args, **kwargs)
        self.DoResize()
        return result

    def RemoveColumn(self, *args, **kwargs):
        """Remove the column and then resize."""
        result = super().RemoveColumn(*args, **kwargs)
        self.DoResize()
        return result

    def AddColumn(self, *args, **kwargs):
        """Add the column and then resize."""
        result = super().AddColumn(*args, **kwargs)
        self.DoResize()
        return result

    # Private helper methods:

    def __is_scrollbar_visible(self):
        return self.MainWindow.HasScrollbar(wx.VERTICAL)

    def __is_scrollbar_included_in_client_size(self):
        # NOTE: on GTK, the scrollbar is included in the client size, but on
        # Windows it is not included
        if operating_system.isWindows():
            return isinstance(self, hypertreelist.HyperTreeList)
        else:
            return True
