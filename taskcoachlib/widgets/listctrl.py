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

import contextlib

from taskcoachlib import operating_system
from taskcoachlib.config import settings
from taskcoachlib.widgets import itemctrl
import wx.lib.mixins.listctrl
from taskcoachlib import patterns


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
        edit_command=None,
        itemPopupMenu=None,
        columnPopupMenu=None,
        resizeableColumn=0,
        *args,
        **kwargs,
    ):
        super().__init__(
            parent,
            style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.BORDER_NONE,
            columns=columns,
            resizeableColumn=resizeableColumn,
            itemPopupMenu=itemPopupMenu,
            columnPopupMenu=columnPopupMenu,
            *args,
            **kwargs,
        )
        # Override GetEffectiveMinSize() which returns BestSize -
        # allows sizer to shrink widget
        self.SetMinSize((100, 50))
        self.__parent = parent
        # The rows' objects at the last refill, and each one's row: the
        # native control keeps row numbers selected, so after the
        # presentation changed the selected objects are read from here
        self.__rows = []
        self.__row_of = {}
        self.__keep_viewport = False  # stable_viewport()
        self._hover_row = -1
        self.bind_event_handlers(selectCommand, edit_command)

    def bind_event_handlers(self, selectCommand, edit_command):
        # pylint: disable=W0201
        if selectCommand:
            self.selectCommand = selectCommand
            self.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.on_select)
            self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select)
            self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_select)
        if edit_command:
            self.editCommand = edit_command
            self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        self.Bind(wx.EVT_SET_FOCUS, self.on_set_focus)
        self.Bind(wx.EVT_MOTION, self._on_hover_motion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self._on_hover_leave)
        self.Bind(wx.EVT_PAINT, self._on_paint_hover)

    def on_set_focus(self, event):  # pylint: disable=W0613
        # Send a child focus event to let the AuiManager know we received focus
        # so it will activate our pane
        wx.PostEvent(self, wx.ChildFocusEvent(self))
        event.Skip()

    def _refresh_hover_row(self, row):
        """Refresh a row with padding to cover pen bleed from hover outline."""
        try:
            rect = self.GetItemRect(row)
        except Exception:
            return
        pad = (
            settings.window.hoverlinewidth + 1
        )  # both lines inside row, small safety
        rect.Inflate(pad, pad)
        self.RefreshRect(rect)

    def _on_hover_motion(self, event):
        row, flags = super().HitTest(event.GetPosition())
        if row != self._hover_row:
            old = self._hover_row
            self._hover_row = row
            if settings.window.hoverlinewidth:
                if old >= 0:
                    self._refresh_hover_row(old)
                if row >= 0:
                    self._refresh_hover_row(row)
                patterns.later.soon(self, self._draw_hover_outline)
        event.Skip()

    def _on_hover_leave(self, event):
        if self._hover_row >= 0:
            old = self._hover_row
            self._hover_row = -1
            self._refresh_hover_row(old)
        event.Skip()

    def follow_pointer(self):
        """Rows moved under a pointer at rest (a scroll, a key, the list
        refilled): the tooltip, about the row that was there, hides,
        and the hover outline goes to the row under the pointer now
        (docs/LIST_MANAGEMENT.md, Row Hover Outline)."""
        self.cancel_tip()
        row = self.__row_under_pointer()
        if row != self._hover_row:
            old, self._hover_row = self._hover_row, row
            for each in (old, row):
                if each >= 0:
                    self._refresh_hover_row(each)

    def __row_under_pointer(self):
        # The rows' window, whose coordinates wx's HitTest takes; only
        # the generic list (GTK) has one apart from the control
        main_window = getattr(wx.ListCtrl, "GetMainWindow", None)
        rows = (main_window(self) if main_window else None) or self
        point = rows.ScreenToClient(wx.GetMousePosition())
        if not rows.GetClientRect().Contains(point):
            return -1
        return super().HitTest(point)[0]

    def _draw_hover_outline(self):
        """Two-tone hover outline: fgcolor inner + bgcolor outer."""
        pw = settings.window.hoverlinewidth
        if self._hover_row < 0 or not pw:
            return
        if self.__row_under_pointer() != self._hover_row:
            # The rows scrolled under the pointer at rest
            self.follow_pointer()
            return  # Drawn after the repaint the change asks
        try:
            outer = self.GetItemRect(self._hover_row)
        except Exception:
            return
        inner = wx.Rect(outer)
        inner.Deflate(pw, pw)
        fg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
        bg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        dc = wx.ClientDC(self)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.SetPen(wx.Pen(bg, pw))
        dc.DrawRectangle(outer)
        dc.SetPen(wx.Pen(fg, pw))
        dc.DrawRectangle(inner)

    def _on_paint_hover(self, event):
        event.Skip()
        # Only schedule a redraw when a row is actually hovered.
        # Otherwise every paint (including those on hidden,
        # never-hovered controls such as the export dialog's temporary
        # viewers) would queue a call that is due after the control is
        # destroyed.
        if self._hover_row >= 0:
            patterns.later.soon(self, self._draw_hover_outline)

    def GetMainWindow(self):
        # Override to return self for drop target support.
        # wx.ListCtrl.GetMainWindow() returns an internal Window that
        # doesn't properly receive drag/drop events.
        return self

    def get_item_with_index(self, row_index):
        return self.__parent.get_item_with_index(row_index)

    def getItemText(self, domain_object, column_index):
        return self.__parent.getItemText(domain_object, column_index)

    def getItemTooltipData(self, domain_object):
        return self.__parent.getItemTooltipData(domain_object)

    def getItemImage(self, domain_object, column_index=0):
        return self.__parent.getItemImages(domain_object, column_index)[
            wx.TreeItemIcon_Normal
        ]

    def OnGetItemText(self, row_index, column_index):
        try:
            item = self.get_item_with_index(row_index)
        except IndexError:
            return ""
        return self.getItemText(item, column_index)

    def OnGetItemImage(self, row_index):
        try:
            item = self.get_item_with_index(row_index)
        except IndexError:
            return -1
        return self.getItemImage(item)

    def OnGetItemColumnImage(self, row_index, column_index):
        try:
            item = self.get_item_with_index(row_index)
        except IndexError:
            return -1
        return self.getItemImage(item, column_index)

    def OnGetItemAttr(self, row_index):
        try:
            item = self.get_item_with_index(row_index)
        except IndexError:
            return None
        foreground_color = item.shown_fg_color()
        background_color = item.shown_bg_color()
        # wx.NullColour doesn't work correctly on Windows - it renders as
        # black instead of transparent. Use system colors to match
        # HyperTreeList's GetClassDefaultAttributes.
        if operating_system.isWindows():
            if foreground_color is None:
                foreground_color = wx.SystemSettings.GetColour(
                    wx.SYS_COLOUR_WINDOWTEXT
                )
            if background_color is None:
                background_color = wx.SystemSettings.GetColour(
                    wx.SYS_COLOUR_LISTBOX
                )

        item_attribute_arguments = [foreground_color, background_color]
        font = item.shown_font()
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

    def on_select(self, event):
        event.Skip()
        self.selectCommand(event)

    def on_item_activated(self, event):
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
        selected = self.curselection()
        self.__rows = [
            self.__parent.get_item_with_index(row) for row in range(count)
        ]
        self.__row_of = {item: row for row, item in enumerate(self.__rows)}
        self.SetItemCount(count)
        if count == 0:
            self.DeleteAllItems()
        else:
            # The VirtualListCtrl makes sure only visible items are updated
            super().RefreshItems(0, count - 1)
        rows = self.__select_rows(selected)
        if rows:
            # Keys move from the selection, not from its old row number;
            # Focus() would scroll there
            self.SetItemState(
                rows[0], wx.LIST_STATE_FOCUSED, wx.LIST_STATE_FOCUSED
            )
        self.selectCommand()
        if self._hover_row >= 0:
            # Another item may be under the pointer now
            patterns.later.soon(self, self.follow_pointer)

    def RefreshItems(self, *items):
        """Refresh specific items."""
        if len(items) <= 7:
            for item in items:
                row = self.__row_of.get(item)
                if row is not None:  # Else shown at the next refill
                    self.RefreshItem(row)
        else:
            self.RefreshAllItems(self.GetItemCount())

    def HitTest(self, xxx_todo_changeme, *args, **kwargs):
        """Always return a three-tuple (item, flag, column)."""
        x, y = xxx_todo_changeme
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

    @property
    def has_selection(self):
        return self.GetSelectedItemCount() > 0

    @property
    def has_single_selection(self):
        return self.GetSelectedItemCount() == 1

    def curselection(self):
        # Guard against deleted C++ object - can happen when a later
        # call runs after window destruction (e.g., closing nested
        # dialogs)
        try:
            # The rows' objects at the last refill, which the user sees
            # selected; rows past the end go while the list shrinks
            return [
                self.__rows[index]
                for index in self.__curselection_indices()
                if index < len(self.__rows)
            ]
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            return []

    def select(self, items):
        rows = self.__select_rows(items)
        if not rows:
            return
        if self.__keep_viewport:
            # The keyboard's row only: Focus() scrolls to it
            self.SetItemState(
                rows[0], wx.LIST_STATE_FOCUSED, wx.LIST_STATE_FOCUSED
            )
        else:
            self.Focus(rows[0])

    @contextlib.contextmanager
    def stable_viewport(self):
        """Select without scrolling while the block runs, when
        auto-scroll is off: after a delete, as the trees."""
        self.__keep_viewport = not self._auto_scroll_enabled()
        try:
            yield
        finally:
            self.__keep_viewport = False

    def __select_rows(self, items):
        """Select the rows of the shown items, and only those; return
        their rows, top first."""
        rows = {self.__row_of[item] for item in items if item in self.__row_of}
        selected = set(self.__curselection_indices())
        for row in selected - rows:
            self.Select(row, False)
        for row in rows - selected:
            self.Select(row, True)
        return sorted(rows)

    def selection_neighbours(self):
        """Return the objects shown above the topmost selected row and
        below the bottommost one, nearest row first: the rows that take
        the selection when the selected ones go."""
        try:
            rows = self.__curselection_indices()
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            return [], []
        if not rows:
            return [], []
        return self.__rows[: rows[0]][::-1], self.__rows[rows[-1] + 1 :]

    def _auto_scroll_enabled(self):
        """Whether the view may scroll by itself to follow the
        selection."""
        return settings.view.autoscrollselection

    def ensureSelectionVisible(self):
        if not self._auto_scroll_enabled():
            return
        first = self.GetFirstSelected()
        if first != -1:
            self.EnsureVisible(first)

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
