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

import os
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
        self.__header_window = None
        self.__resize_cursor = wx.Cursor(wx.CURSOR_SIZEWE)
        self.__no_entry_cursor = wx.Cursor(wx.CURSOR_NO_ENTRY)
        self.__current_cursor = wx.STANDARD_CURSOR
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
            self._bindHeaderMotion()
            wx.CallAfter(self.DoResize)
        else:
            self.Unbind(wx.EVT_SIZE)
            self.Unbind(wx.EVT_LIST_COL_BEGIN_DRAG)
            self.Unbind(wx.EVT_LIST_COL_END_DRAG)
            self._unbindHeaderMotion()

    def IsAutoResizing(self):
        return self.__is_auto_resizing

    def OnBeginColumnDrag(self, event):
        # Block resizing of the auto-fill column (ResizeColumn) when auto-resize
        # is enabled. This column always fills remaining space automatically.
        # Users can resize other columns, which will take/give space from the
        # ResizeColumn. This follows modern UX patterns where auto-fill columns
        # are not directly resizable.
        if event.Column == self.ResizeColumn:
            event.Veto()
            return
        # Temporarily unbind the EVT_SIZE to prevent resizing during dragging
        self.Unbind(wx.EVT_SIZE)
        event.Skip()

    def OnEndColumnDrag(self, event):
        self.Bind(wx.EVT_SIZE, self.OnResize)
        wx.CallAfter(self.DoResize)
        event.Skip()

    def _getHeaderWindow(self):
        """Get the header window of the list control (if it exists).

        For wx.ListCtrl, the header is a child window named 'wxlistctrlcolumntitles'.
        For HyperTreeList, header cursor is handled by TreeListHeaderWindow.
        """
        if self.__header_window is not None:
            return self.__header_window
        # Only look for header in wx.ListCtrl, not HyperTreeList
        if isinstance(self, hypertreelist.HyperTreeList):
            return None
        for child in self.GetChildren():
            if child.GetName() == 'wxlistctrlcolumntitles':
                self.__header_window = child
                return child
        return None

    def _bindHeaderMotion(self):
        """Bind motion event to header window for cursor feedback."""
        header = self._getHeaderWindow()
        if header:
            header.Bind(wx.EVT_MOTION, self._onHeaderMotion)

    def _unbindHeaderMotion(self):
        """Unbind motion event from header window."""
        header = self._getHeaderWindow()
        if header:
            header.Unbind(wx.EVT_MOTION)
            # Reset cursor to default
            header.SetCursor(wx.STANDARD_CURSOR)

    def _onHeaderMotion(self, event):
        """Handle mouse motion over header to show appropriate cursor.

        Shows 'no entry' cursor when hovering over the resize border of
        the auto-fill column (ResizeColumn), since it cannot be manually resized.

        When on a non-resizable border, we don't call Skip() to prevent the
        native wx.ListCtrl header from overriding our cursor.
        """
        header = self._getHeaderWindow()
        if not header:
            event.Skip()
            return

        x = event.GetX()
        # Determine which column border (if any) the mouse is near
        column_at_border = self._getColumnBorderAtX(x)

        if column_at_border is not None and column_at_border == self.ResizeColumn:
            # This is the auto-fill column border - show no-entry cursor
            # Don't call Skip() to prevent native cursor override
            if self.__current_cursor != self.__no_entry_cursor:
                self.__current_cursor = self.__no_entry_cursor
                header.SetCursor(self.__no_entry_cursor)
        else:
            # Reset to standard cursor if we were showing no-entry
            if self.__current_cursor == self.__no_entry_cursor:
                self.__current_cursor = wx.STANDARD_CURSOR
                header.SetCursor(wx.STANDARD_CURSOR)
            # Let native handling take over for other cases
            event.Skip()

    def _getColumnBorderAtX(self, x, tolerance=3):
        """Get the column index whose right border is at x position.

        Returns column index if x is within tolerance of a column's right edge,
        or None if not near any border.
        """
        cumulative_width = 0
        for col_index in range(self.GetColumnCount()):
            cumulative_width += self.GetColumnWidth(col_index)
            if abs(x - cumulative_width) <= tolerance:
                return col_index
        return None

    def OnResize(self, event):
        event.Skip()
        # Always defer column resize to avoid cascade repaints during resize operations.
        # This is especially important during AUI sash drag where immediate column
        # recalculation can cause flickering.
        wx.CallAfter(self.DoResize)

    def DoResize(self):
        if not self:
            return  # Avoid a potential PyDeadObject error
        if not self.IsAutoResizing():
            return
        # Skip resize if widget isn't shown on screen yet or too small
        if not self.IsShownOnScreen():
            return
        if self.GetSize().height < 32:
            return  # Avoid an endless update bug when the height is small.
        if self.GetColumnCount() <= self.ResizeColumn:
            return  # Nothing to resize.

        unused_width = max(self.AvailableWidth - self.NecessaryWidth, 0)
        resize_column_width = self.ResizeColumnMinWidth + unused_width
        self.SetColumnWidth(self.ResizeColumn, resize_column_width)


    def GetResizeColumn(self):
        if self.__resize_column == -1:
            return self.GetColumnCount() - 1
        else:
            return self.__resize_column

    def SetResizeColumn(self, column_index):
        self.__resize_column = column_index  # pylint: disable=W0201

    ResizeColumn = property(GetResizeColumn, SetResizeColumn)

    def GetAvailableWidth(self):
        available_width = int(self.GetClientSize().width)
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
                necessary_width += int(self.GetColumnWidth(column_index))
        return necessary_width

    NecessaryWidth = property(GetNecessaryWidth)

    # Override all methods that manipulate columns to be able to resize the
    # columns after any additions or removals.

    def InsertColumn(self, *args, **kwargs):
        """Insert the new column and then resize."""
        result = super().InsertColumn(*args, **kwargs)
        wx.CallAfter(self.DoResize)
        return result

    def DeleteColumn(self, *args, **kwargs):
        """Delete the column and then resize."""
        result = super().DeleteColumn(*args, **kwargs)
        wx.CallAfter(self.DoResize)
        return result

    def RemoveColumn(self, *args, **kwargs):
        """Remove the column and then resize."""
        result = super().RemoveColumn(*args, **kwargs)
        wx.CallAfter(self.DoResize)
        return result

    def AddColumn(self, *args, **kwargs):
        """Add the column and then resize."""
        result = super().AddColumn(*args, **kwargs)
        wx.CallAfter(self.DoResize)
        return result

    # Private helper methods:

    def __is_scrollbar_visible(self):
        return self.MainWindow.HasScrollbar(wx.VERTICAL)

    def __is_scrollbar_included_in_client_size(self):
        """Determine if scrollbar width should be subtracted from client size.

        This depends on whether the platform uses overlay scrollbars:
        - Overlay scrollbars: render on top of content, don't take layout space
        - Fixed scrollbars: take up layout space, may be included in client size

        Returns True if we need to subtract scrollbar width from available width.
        """
        if operating_system.isWindows():
            # Windows Win32: fixed scrollbars, but only included in client size
            # for HyperTreeList widgets
            return isinstance(self, hypertreelist.HyperTreeList)

        if operating_system.isMac():
            # macOS: overlay scrollbars by default since 10.7
            # User can change in System Preferences, but overlay is the norm
            return False

        # Linux/BSD with GTK
        if self.__has_overlay_scrollbars():
            # Overlay scrollbars don't take layout space
            return False
        else:
            # Fixed scrollbars (GTK2 or GTK3 with overlay disabled)
            # are included in client size
            return True

    def __has_overlay_scrollbars(self):
        """Detect if the system uses overlay scrollbars (GTK3/GTK4 default).

        GTK3 and GTK4 use overlay scrollbars by default. This can be disabled
        by setting GTK_OVERLAY_SCROLLING=0 environment variable.
        GTK2 always uses fixed scrollbars.
        """
        # Check for GTK3 or GTK4 in wx.PlatformInfo
        platform_info = wx.PlatformInfo
        has_gtk3_or_gtk4 = 'gtk3' in platform_info or 'gtk4' in platform_info

        if not has_gtk3_or_gtk4:
            # GTK2 or unknown: no overlay scrollbars
            return False

        # GTK3/GTK4: overlay is default, but can be disabled via env var
        if os.environ.get('GTK_OVERLAY_SCROLLING') == '0':
            return False

        return True
