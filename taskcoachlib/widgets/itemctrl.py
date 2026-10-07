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

# Base classes for controls with items, such as ListCtrl, TreeCtrl,
# and TreeListCtrl.


import wx, inspect
from . import draganddrop, autowidth, tooltip
from wx.lib.agw import hypertreelist
from taskcoachlib import patterns


class _CtrlWithItemsMixin(object):
    """Base class for controls with items, such as ListCtrl, TreeCtrl,
    TreeListCtrl, etc."""

    def _itemIsOk(self, item):
        try:
            return item.IsOk()  # for Tree(List)Ctrl
        except AttributeError:
            return item != wx.NOT_FOUND  # for ListCtrl

    def _objectBelongingTo(self, item):
        if not self._itemIsOk(item):
            return None
        try:
            return self.GetItemPyData(item)  # TreeListCtrl
        except AttributeError:
            return self.get_item_with_index(item)  # ListCtrl

    def SelectItem(self, item, *args, **kwargs):
        try:
            # Tree(List)Ctrl:
            super().SelectItem(item, *args, **kwargs)
        except AttributeError:
            # ListCtrl:
            select = kwargs.get("select", True)
            new_state = wx.LIST_STATE_SELECTED
            if not select:
                new_state = ~new_state
            self.SetItemState(item, new_state, wx.LIST_STATE_SELECTED)


class _CtrlWithPopupMenuMixin(_CtrlWithItemsMixin):
    """Base class for controls with popupmenu's."""

    @staticmethod
    def _attachPopupMenu(eventSource, event_types, eventHandler):
        for event_type in event_types:
            eventSource.Bind(event_type, eventHandler)


class _CtrlWithItemPopupMenuMixin(_CtrlWithPopupMenuMixin):
    """Popupmenu's on items."""

    def _popup_item_menu(self):
        # Items shown only in some states (Edit in place) first
        self._itemPopupMenu.show_visible_items()
        # PopupMenu() asks the items' states first (EVT_UPDATE_UI)
        self.PopupMenu(self._itemPopupMenu)

    def __init__(self, *args, **kwargs):
        self._itemPopupMenu = kwargs.pop("itemPopupMenu")
        super().__init__(*args, **kwargs)
        if self._itemPopupMenu is not None:
            # Determine if this is a ListCtrl or tree control
            # ListCtrl has GetItemRect but not GetRootItem
            is_list_ctrl = hasattr(self, "GetItemRect") and not hasattr(
                self, "GetRootItem"
            )
            if is_list_ctrl:
                # For ListCtrl: use EVT_LIST_ITEM_RIGHT_CLICK for item clicks
                # (provides GetIndex() directly) and EVT_CONTEXT_MENU for empty space
                self._attachPopupMenu(
                    self,
                    (wx.EVT_LIST_ITEM_RIGHT_CLICK,),
                    self.on_list_item_right_click,
                )
                self._attachPopupMenu(
                    self,
                    (wx.EVT_CONTEXT_MENU,),
                    self.on_list_context_menu,
                )
            else:
                # For tree controls: use EVT_TREE_ITEM_RIGHT_CLICK and EVT_CONTEXT_MENU
                self._attachPopupMenu(
                    self,
                    (wx.EVT_TREE_ITEM_RIGHT_CLICK, wx.EVT_CONTEXT_MENU),
                    self.on_item_popup_menu,
                )
                # Also bind to MainWindow to catch right-clicks on empty space
                self.GetMainWindow().Bind(
                    wx.EVT_RIGHT_DOWN, self._onMainWindowRightDown
                )

    def _onMainWindowRightDown(self, event):
        """Handle right-click on MainWindow for tree controls.

        This catches clicks on empty space that EVT_TREE_ITEM_RIGHT_CLICK misses.
        """
        point = event.GetPosition()
        item = self.HitTest(point)[0]
        if not self._itemIsOk(item):
            # Clicked on empty space - clear selection and show popup
            self.clear_selection()
            self._popup_item_menu()
        else:
            # Clicked on an item - let normal event handling take over
            event.Skip()

    def on_item_popup_menu(self, event):
        """Handle popup menu for tree controls (EVT_TREE_ITEM_RIGHT_CLICK, EVT_CONTEXT_MENU)."""
        # Make sure the window this control is in has focus:
        try:
            window = event.GetEventObject().MainWindow
        except AttributeError:
            window = event.GetEventObject()
        window.SetFocus()
        # Get click position - GetPoint() for tree item events, GetPosition() for context menu
        point = None
        if hasattr(event, "GetPoint"):
            point = event.GetPoint()
        elif hasattr(event, "GetPosition"):
            pos = event.GetPosition()
            if pos != wx.DefaultPosition:
                # In the rows' window, as HitTest() takes it: the
                # control's own coordinates count the column header
                point = self.GetMainWindow().ScreenToClient(pos)
        if point is not None:
            # Make sure the item under the mouse is selected because that
            # is what users expect and what is most user-friendly. Not all
            # widgets do this by default, e.g. the TreeListCtrl does not.
            item = self.HitTest(point)[0]
            if not self._itemIsOk(item):
                # Clicked on empty space - clear selection so menu items
                # properly reflect no selection
                self.clear_selection()
                self._popup_item_menu()
                return
            if not self.IsSelected(item):
                self.clear_selection()
                self.SelectItem(item)
        self._popup_item_menu()

    def on_list_item_right_click(self, event):
        """Handle EVT_LIST_ITEM_RIGHT_CLICK for ListCtrl controls.

        This event fires when right-clicking on an item and provides
        GetIndex() to get the clicked item directly - the proper way
        to handle ListCtrl right-clicks.
        """
        self.SetFocus()
        # Get the clicked item index from the event
        item_index = event.GetIndex()
        # Select the item if not already selected
        if not self.IsSelected(item_index):
            self.clear_selection()
            self.Select(item_index, True)
        self._popup_item_menu()

    def on_list_context_menu(self, event):
        """Handle EVT_CONTEXT_MENU for ListCtrl controls.

        This handles right-clicks on empty space (EVT_LIST_ITEM_RIGHT_CLICK
        only fires for item clicks). Also handles keyboard context menu key.
        """
        self.SetFocus()
        pos = event.GetPosition()
        if pos != wx.DefaultPosition:
            # Mouse-triggered context menu - check if on empty space
            client_point = self.ScreenToClient(pos)
            item = self.HitTest(client_point)[0]
            if self._itemIsOk(item):
                # Click was on an item - EVT_LIST_ITEM_RIGHT_CLICK already handled it
                return
            # Click on empty space - clear selection
            self.clear_selection()
        self._popup_item_menu()


class _CtrlWithColumnPopupMenuMixin(_CtrlWithPopupMenuMixin):
    """This class enables a right-click popup menu on column headers. The
    popup menu should expect a public property columnIndex to be set so
    that the control can tell the menu which column the user clicked to
    popup the menu."""

    def __init__(self, *args, **kwargs):
        self.__popupMenu = kwargs.pop("columnPopupMenu")
        super().__init__(*args, **kwargs)
        if self.__popupMenu is not None:
            self._attachPopupMenu(
                self, [wx.EVT_LIST_COL_RIGHT_CLICK], self.on_column_popup_menu
            )

    def on_column_popup_menu(self, event):
        # We store the columnIndex in the menu, because it's near to
        # impossible for commands in the menu to determine on what column the
        # menu was popped up.
        column_index = event.GetColumn()
        self.__popupMenu.columnIndex = column_index
        # Because right-clicking on column headers does not automatically give
        # focus to the control, we force the focus:
        try:
            window = event.GetEventObject().GetMainWindow()
        except AttributeError:
            window = event.GetEventObject()
        window.SetFocus()
        # A menu built from the viewer's current state refills first
        if hasattr(self.__popupMenu, "updateMenu"):
            self.__popupMenu.updateMenu()
        self.PopupMenu(self.__popupMenu)
        event.Skip(False)


class _CtrlWithDropTargetMixin(_CtrlWithItemsMixin):
    """Control that accepts files, e-mails or URLs being dropped onto items."""

    def __init__(self, *args, **kwargs):
        self.__on_drop_url_callback = kwargs.pop("on_drop_url", None)
        self.__on_drop_files_callback = kwargs.pop("on_drop_files", None)
        self.__on_drop_mail_callback = kwargs.pop("on_drop_mail", None)
        self.__dropHighlightItem = None  # Track highlighted item during drag
        super().__init__(*args, **kwargs)
        if (
            self.__on_drop_url_callback
            or self.__on_drop_files_callback
            or self.__on_drop_mail_callback
        ):
            drop_target = draganddrop.DropTarget(
                self.on_drop_url,
                self.on_drop_files,
                self.on_drop_mail,
                self.on_drag_over,
                self.on_drop_end,
            )
            self.GetMainWindow().SetDropTarget(drop_target)

    def on_drop_end(self):
        """Also after a drop that adds nothing (a mail not readable)."""
        self._clearDropHighlight()
        draganddrop.hover_expander(self).stop()

    def on_drop_url(self, x, y, url):
        self._clearDropHighlight()  # Clear highlight on drop
        draganddrop.hover_expander(self).stop()
        item = self.HitTest((x, y))[0]
        if self.__on_drop_url_callback:
            self.__on_drop_url_callback(self._objectBelongingTo(item), url)

    def on_drop_files(self, x, y, filenames):
        self._clearDropHighlight()  # Clear highlight on drop
        draganddrop.hover_expander(self).stop()
        item = self.HitTest((x, y))[0]
        if self.__on_drop_files_callback:
            self.__on_drop_files_callback(
                self._objectBelongingTo(item), filenames
            )

    def on_drop_mail(self, x, y, mails):
        self._clearDropHighlight()  # Clear highlight on drop
        draganddrop.hover_expander(self).stop()
        item = self.HitTest((x, y))[0]
        if self.__on_drop_mail_callback:
            self.__on_drop_mail_callback(self._objectBelongingTo(item), mails)

    def on_drag_over(self, x, y, default_result):
        item, flags = self.HitTest((x, y))[:2]
        if self._itemIsOk(item):
            # Auto-expand collapsed items on hover (modern UX behavior)
            draganddrop.hover_expander(self).hover(item, flags)
            # Highlight the row being hovered over
            self._setDropHighlight(item)
        else:
            self._clearDropHighlight()
            draganddrop.hover_expander(self).stop()
        return default_result

    def _setDropHighlight(self, item):
        """Set visual highlight on item during drag-over."""
        if item != self.__dropHighlightItem:
            self.__dropHighlightItem = item
            # Use SetDragItem which is used by internal DnD for highlighting
            if hasattr(self, "SetDragItem"):
                self.SetDragItem(item)

    def _clearDropHighlight(self):
        """Clear any existing drop highlight."""
        if self.__dropHighlightItem is not None:
            self.__dropHighlightItem = None
            if hasattr(self, "SetDragItem"):
                try:
                    self.SetDragItem(None)
                except Exception:
                    pass  # Item may have been deleted

    def GetMainWindow(self):
        try:
            return super().GetMainWindow()
        except AttributeError:
            return self


class CtrlWithToolTipMixin(_CtrlWithItemsMixin, tooltip.ToolTipMixin):
    """Control that has a different tooltip for each item"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__tip = tooltip.SimpleToolTip(self)

    def OnBeforeShowToolTip(self, x, y):
        item, _, column = self.HitTest(wx.Point(x, y))
        domain_object = self._objectBelongingTo(item)
        if domain_object:
            tooltip_data = self.getItemTooltipData(domain_object)
            do_show = any([data[1] for data in tooltip_data])
            if do_show:
                self.__tip.SetData(tooltip_data)
                return self.__tip
        return None


class CtrlWithItemsMixin(
    _CtrlWithItemPopupMenuMixin, _CtrlWithDropTargetMixin
):
    pass


class Column(object):
    def __init__(self, name, column_header, *event_types, **kwargs):
        self.__name = name
        self.__columnHeader = column_header
        self.width = kwargs.pop(
            "width", hypertreelist._DEFAULT_COL_WIDTH
        )  # pylint: disable=W0212
        # The event types to use for registering an observer that is
        # interested in changes that affect this column:
        self.__eventTypes = event_types
        self.__sortCallback = kwargs.pop("sortCallback", None)
        self.__renderCallback = kwargs.pop(
            "renderCallback", self.defaultRenderer
        )
        self.__resizeCallback = kwargs.pop("resizeCallback", None)
        self.__alignment = kwargs.pop("alignment", wx.LIST_FORMAT_LEFT)
        self.__hasImages = "imageIndicesCallback" in kwargs
        self.__imageIndicesCallback = (
            kwargs.pop("imageIndicesCallback", self.defaultImageIndices)
            or self.defaultImageIndices
        )
        self.__multiImageIndicesCallback = kwargs.pop(
            "multiImageIndicesCallback", None
        )
        # NB: because the header image is needed for sorting a fixed header
        # image cannot be combined with a sortable column
        self.__headerImageIndex = kwargs.pop("headerImageIndex", -1)
        self.__editCallback = kwargs.get("editCallback", None)
        self.__editControlClass = kwargs.get("editControl", None)
        self.__parse = kwargs.get("parse", lambda value: value)

    def name(self):
        return self.__name

    def header(self):
        return self.__columnHeader

    def headerImageIndex(self):
        return self.__headerImageIndex

    def eventTypes(self):
        return self.__eventTypes

    def setWidth(self, width):
        self.width = width
        if self.__resizeCallback:
            self.__resizeCallback(self, width)

    def sort(self, *args, **kwargs):
        if self.__sortCallback:
            self.__sortCallback(*args, **kwargs)

    @staticmethod
    def __accepted(func, kwargs):
        """The keyword arguments func takes."""
        spec = inspect.getfullargspec(func)
        names = spec.args + spec.kwonlyargs
        return {name: value for name, value in kwargs.items() if name in names}

    def render(self, *args, **kwargs):
        return self.__renderCallback(
            *args, **self.__accepted(self.__renderCallback, kwargs)
        )

    def defaultRenderer(self, *args, **kwargs):  # pylint: disable=W0613
        return str(args[0])

    def alignment(self):
        return self.__alignment

    def defaultImageIndices(self, *args, **kwargs):  # pylint: disable=W0613
        return {wx.TreeItemIcon_Normal: -1}

    def imageIndices(self, *args, **kwargs):
        return self.__imageIndicesCallback(*args, **kwargs)

    def hasImages(self):
        return self.__hasImages or self.__multiImageIndicesCallback is not None

    def hasMultiImages(self):
        return self.__multiImageIndicesCallback is not None

    def multiImageIndices(self, *args, **kwargs):
        if self.__multiImageIndicesCallback:
            return self.__multiImageIndicesCallback(*args, **kwargs)
        return []

    def isEditable(self):
        return self.__editControlClass != None and self.__editCallback != None

    def onEndEdit(self, item, newValue):
        self.__editCallback(item, newValue)

    def editControl(self, parent, item, column_index, domain_object):
        value = self.value(domain_object)
        return self.__editControlClass(
            parent, wx.ID_ANY, item, column_index, parent, value
        )

    def parse(self, value):
        return self.__parse(value)

    def value(self, domain_object):
        return getattr(domain_object, self.name())()

    def __eq__(self, other):
        return self.name() == other.name()


class _BaseCtrlWithColumnsMixin(object):
    """A base class for all controls with columns. Note that this class and
    its subclasses do not support addition or deletion of columns after
    the initial setting of columns."""

    def __init__(self, *args, **kwargs):
        self.__allColumns = kwargs.pop("columns")
        super().__init__(*args, **kwargs)
        # This  is  used to  keep  track  of  which column  has  which
        # index. The only  other way would be (and  was) find a column
        # using its header, which causes problems when several columns
        # have the same header. It's a list of (index, column) tuples.
        self.__indexMap = []
        self._setColumns()

    def _setColumns(self):
        for column_index, column in enumerate(self.__allColumns):
            self._insertColumn(column_index, column)

    def _insertColumn(self, column_index, column):
        new_map = []
        for col_index, col in self.__indexMap:
            if col_index >= column_index:
                new_map.append((col_index + 1, col))
            else:
                new_map.append((col_index, col))
        new_map.append((column_index, column))
        self.__indexMap = new_map

        self.InsertColumn(
            column_index,
            column.header() if column.headerImageIndex() == -1 else "",
            format=column.alignment(),
            width=column.width,
        )

        column_info = self.GetColumn(column_index)
        column_info.SetImage(column.headerImageIndex())
        self.SetColumn(column_index, column_info)

    def _deleteColumn(self, column_index):
        new_map = []
        for col_index, col in self.__indexMap:
            if col_index > column_index:
                new_map.append((col_index - 1, col))
            elif col_index < column_index:
                new_map.append((col_index, col))
        self.__indexMap = new_map
        self.DeleteColumn(column_index)

    def _getColumn(self, column_index):
        for col_index, col in self.__indexMap:
            if col_index == column_index:
                return col
        raise IndexError

    def all_columns(self):
        """Every column, shown or hidden, in their display order: the
        view's own list."""
        return self.__allColumns

    def _getColumnHeader(self, column_index):
        """The currently displayed column header in the column with index
        columnIndex."""
        return self.GetColumn(column_index).GetText()

    def _getColumnIndex(self, column):
        """The current column index of the column 'column'."""
        try:
            return self.__allColumns.index(column)  # Uses overriden __eq__
        except ValueError:
            raise ValueError("%s: unknown column" % column.name())


class _CtrlWithHideableColumnsMixin(_BaseCtrlWithColumnsMixin):
    """This class supports hiding columns."""

    def showColumn(self, column, show=True):
        """showColumn shows or hides the column for column.
        The column is actually removed or inserted into the control because
        although TreeListCtrl supports hiding columns, ListCtrl does not.
        """
        column_index = self._getColumnIndex(column)
        if show and not self.isColumnVisible(column):
            self._insertColumn(column_index, column)
        elif not show and self.isColumnVisible(column):
            self._deleteColumn(column_index)

    def isColumnVisible(self, column):
        return column in self._visibleColumns()

    def move_column(self, column, slot):
        """Move a shown column to slot, a place between the shown
        columns (0 before the first, their count after the last), and in
        the order of all columns with it; return whether it moved."""
        shown = self._visibleColumns()
        index = shown.index(column)
        if slot in (index, index + 1):
            return False
        column.setWidth(self.GetColumnWidth(index))
        columns = self.all_columns()
        columns.remove(column)
        if slot < len(shown):
            columns.insert(columns.index(shown[slot]), column)
        else:
            columns.insert(columns.index(shown[-1]) + 1, column)
        self._deleteColumn(index)
        self._insertColumn(self._getColumnIndex(column), column)
        return True

    def _getColumnIndex(self, column):
        """_getColumnIndex returns the actual columnIndex of the column if it
        is visible, or the position it would have if it were visible."""
        column_index_when_all_columns_visible = super(
            _CtrlWithHideableColumnsMixin, self
        )._getColumnIndex(column)
        for column_index, visible_column in enumerate(self._visibleColumns()):
            if (
                super()._getColumnIndex(visible_column)
                >= column_index_when_all_columns_visible
            ):
                return column_index
        return self.GetColumnCount()  # Column header not found

    def _visibleColumns(self):
        return [
            self._getColumn(column_index)
            for column_index in range(self.GetColumnCount())
        ]


class _CtrlWithSortableColumnsMixin(_BaseCtrlWithColumnsMixin):
    """This class adds sort indicators and clickable column headers that
    trigger callbacks to (re)sort the contents of the control."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.on_column_click)
        self.__currentSortColumn = self._getColumn(0)
        self.__currentSortImageIndex = -1

    def on_column_click(self, event):
        event.Skip(False)
        # Make sure the window this control is in has focus:
        try:
            window = event.GetEventObject().GetMainWindow()
        except AttributeError:
            window = event.GetEventObject()
        window.SetFocus()
        column_index = event.GetColumn()
        if 0 <= column_index < self.GetColumnCount():
            column = self._getColumn(column_index)
            # Later, to make sure the window this control is in is
            # activated before we process the column click:
            patterns.later.soon(self, self.__safeColumnSort, column, event)

    def __safeColumnSort(self, column, event):
        """Safely call column.sort, guarding against deleted C++ objects."""
        try:
            if self:
                column.sort(event)
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def show_sort_column(self, column):
        if column != self.__currentSortColumn:
            self._clearSortImage()
        self.__currentSortColumn = column
        self._showSortImage()

    def show_sort_order(self, image_index):
        self.__currentSortImageIndex = image_index
        self._showSortImage()

    def _clearSortImage(self):
        self.__setSortColumnImage(-1)

    def _showSortImage(self):
        self.__setSortColumnImage(self.__currentSortImageIndex)

    def _currentSortColumn(self):
        return self.__currentSortColumn

    def __setSortColumnImage(self, image_index):
        column_index = self._getColumnIndex(self.__currentSortColumn)
        column_info = self.GetColumn(column_index)
        if column_info.GetImage() == image_index:
            pass  # The column is already showing the right image, so we're done
        else:
            column_info.SetImage(image_index)
            self.SetColumn(column_index, column_info)


class _CtrlWithAutoResizedColumnsMixin(autowidth.AutoColumnWidthMixin):
    """Mixin that provides auto-column-resizing and saves column widths.

    When auto-resize is enabled, one column (typically subject/tree column)
    automatically fills remaining window space. When disabled, columns use
    standard wxWidgets resize behavior.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Bind(wx.EVT_LIST_COL_END_DRAG, self.on_end_column_resize)

    def on_end_column_resize(self, event):
        """Save the column widths after the user did a resize."""
        for index, column in enumerate(self._visibleColumns()):
            column.setWidth(self.GetColumnWidth(index))
        event.Skip()


# Around a column border a press resizes the column, as in wx's headers
_BORDER = 3
# The generic list control scrolls sideways by this many pixels a step
_LIST_SCROLL_UNIT = 15


class _CtrlWithMovableColumnsMixin(object):
    """A column moves when its header is dragged: a line shows where it
    lands, before the first column, between two or after the last
    (docs/LIST_MANAGEMENT.md, Moving Columns). The headers sort at the
    press, so a press on a label is held: dragged, it moves the column;
    released where it was, it is the click that sorts. A press on a
    border resizes, as before."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__pressed = None  # (column index, x) of the press held
        self.__dragging = False
        self.__line = None  # The drop line, while dragging
        header = self.column_header()
        if header:
            header.Bind(wx.EVT_LEFT_DOWN, self.__on_press)
            header.Bind(wx.EVT_MOTION, self.__on_motion)
            header.Bind(wx.EVT_LEFT_UP, self.__on_release)
            header.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.__on_capture_lost)

    def column_header(self):
        """The header window; looked up each time, never kept: wx
        creates the list's (docs/DEVELOPMENT.md, Design)."""
        if isinstance(self, hypertreelist.HyperTreeList):
            return self.GetHeaderWindow()
        for child in self.GetChildren():
            if child.GetName() == "wxlistctrlcolumntitles":
                return child
        return None

    def __scrolled_x(self):
        """How far the columns are scrolled to the left, in pixels."""
        if isinstance(self, hypertreelist.HyperTreeList):
            return self.GetMainWindow().CalcUnscrolledPosition(0, 0)[0]
        return self.GetScrollPos(wx.HORIZONTAL) * _LIST_SCROLL_UNIT

    def __edges(self):
        """Where each column starts, and the last one ends, in the
        header's coordinates."""
        edges = [-self.__scrolled_x()]
        for index in range(self.GetColumnCount()):
            edges.append(edges[-1] + self.GetColumnWidth(index))
        return edges

    def __on_press(self, event):
        edges = self.__edges()
        x = event.GetX()
        on_border = any(abs(x - edge) < _BORDER for edge in edges[1:])
        if on_border or not edges[0] <= x < edges[-1]:
            event.Skip()  # The header resizes, or there is no column
            return
        index = sum(1 for edge in edges[1:] if edge <= x)
        self.__pressed = (index, x)
        header = event.GetEventObject()
        # The release may come outside; a hidden window cannot take it
        if header.IsShownOnScreen() and not header.HasCapture():
            header.CaptureMouse()

    def __on_motion(self, event):
        if self.__pressed is None:
            event.Skip()
            return
        if not self.__dragging:
            threshold = max(4, wx.SystemSettings.GetMetric(wx.SYS_DRAG_X))
            if abs(event.GetX() - self.__pressed[1]) < threshold:
                return
            self.__dragging = True
            top = wx.GetTopLevelParent(self)
            top.Bind(wx.EVT_CHAR_HOOK, self.__on_key)
        self.__show_line(self.__slot_at(event.GetX()))

    def __slot_at(self, x):
        """The place between columns nearest to x: how many columns'
        middles lie left of it."""
        edges = self.__edges()
        return sum(
            1 for start, end in zip(edges, edges[1:]) if (start + end) / 2 < x
        )

    def __show_line(self, slot):
        if self.__line is None:
            self.__line = wx.Window(self, size=(2, 1))
            self.__line.SetBackgroundColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
            )
        x = min(self.__edges()[slot], self.GetClientSize().width - 2)
        self.__line.SetSize(max(0, x - 1), 0, 2, self.GetClientSize().height)
        self.__line.Show()
        self.__line.Raise()

    def __on_release(self, event):
        if self.__pressed is None:
            event.Skip()
            return
        index = self.__pressed[0]
        dragging = self.__dragging
        slot = self.__slot_at(event.GetX())
        self.__end(event.GetEventObject())
        if dragging:
            self.__column_dropped(self._getColumn(index), slot)
        else:
            self.__click(index)

    def __on_capture_lost(self, event):  # pylint: disable=W0613
        self.__end(event.GetEventObject())

    def __on_key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.__end(self.column_header())
        else:
            event.Skip()

    def __end(self, header):
        """Forget the press; take the line and the capture away."""
        if self.__dragging:
            wx.GetTopLevelParent(self).Unbind(
                wx.EVT_CHAR_HOOK, handler=self.__on_key
            )
        self.__pressed = None
        self.__dragging = False
        if self.__line is not None:
            self.__line.Destroy()
            self.__line = None
        if header and header.HasCapture():
            header.ReleaseMouse()

    def __click(self, index):
        """The header's own click at the press, held until the release:
        it sorts."""
        event = wx.ListEvent(wx.wxEVT_LIST_COL_CLICK, self.GetId())
        event.SetColumn(index)
        event.SetEventObject(self)
        self.GetEventHandler().ProcessEvent(event)

    def __column_dropped(self, column, slot):
        """The view moves the column and saves the order; without one,
        the control only."""
        move = getattr(self.GetParent(), "move_column", None) or getattr(
            self, "move_column"
        )
        move(column, slot)


class CtrlWithColumnsMixin(
    _CtrlWithMovableColumnsMixin,
    _CtrlWithAutoResizedColumnsMixin,
    _CtrlWithHideableColumnsMixin,
    _CtrlWithSortableColumnsMixin,
    _CtrlWithColumnPopupMenuMixin,
):
    """CtrlWithColumnsMixin combines the functionality of its parent
    classes: columns moved by dragging their headers, automatic resizing
    of columns, hideable columns, columns with sort indicators, and
    column popup menu's."""

    def showColumn(self, column, show=True):
        super().showColumn(column, show)
        # Show sort indicator if the column that was just made visible is being sorted on
        if show and column == self._currentSortColumn():
            self._showSortImage()

    def move_column(self, column, slot):
        moved = super().move_column(column, slot)
        if moved and column == self._currentSortColumn():
            self._showSortImage()  # Inserted again without it
        return moved

    def _clearSortImage(self):
        # Only clear the sort image if the column in question is visible
        if self.isColumnVisible(self._currentSortColumn()):
            super()._clearSortImage()

    def _showSortImage(self):
        # Only show the sort image if the column in question is visible
        if self.isColumnVisible(self._currentSortColumn()):
            super()._showSortImage()
