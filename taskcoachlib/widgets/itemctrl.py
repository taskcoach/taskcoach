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

""" Base classes for controls with items, such as ListCtrl, TreeCtrl, 
    and TreeListCtrl. """  # pylint: disable=W0105


import wx, inspect
from . import draganddrop, autowidth, tooltip
from wx.lib.agw import hypertreelist


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
            return self.getItemWithIndex(item)  # ListCtrl

    def SelectItem(self, item, *args, **kwargs):
        try:
            # Tree(List)Ctrl:
            super().SelectItem(item, *args, **kwargs)
        except AttributeError:
            # ListCtrl:
            select = kwargs.get("select", True)
            newState = wx.LIST_STATE_SELECTED
            if not select:
                newState = ~newState
            self.SetItemState(item, newState, wx.LIST_STATE_SELECTED)


class _CtrlWithPopupMenuMixin(_CtrlWithItemsMixin):
    """Base class for controls with popupmenu's."""

    @staticmethod
    def _attachPopupMenu(eventSource, eventTypes, eventHandler):
        for eventType in eventTypes:
            eventSource.Bind(eventType, eventHandler)


class _CtrlWithItemPopupMenuMixin(_CtrlWithPopupMenuMixin):
    """Popupmenu's on items."""

    def __init__(self, *args, **kwargs):
        self.__popupMenu = kwargs.pop("itemPopupMenu")
        super().__init__(*args, **kwargs)
        if self.__popupMenu is not None:
            self._attachPopupMenu(
                self,
                (wx.EVT_TREE_ITEM_RIGHT_CLICK, wx.EVT_CONTEXT_MENU),
                self.onItemPopupMenu,
            )

    def onItemPopupMenu(self, event):
        # Make sure the window this control is in has focus:
        try:
            window = event.GetEventObject().MainWindow
        except AttributeError:
            window = event.GetEventObject()
        window.SetFocus()
        if hasattr(event, "GetPoint"):
            # Make sure the item under the mouse is selected because that
            # is what users expect and what is most user-friendly. Not all
            # widgets do this by default, e.g. the TreeListCtrl does not.
            item = self.HitTest(event.GetPoint())[0]
            if not self._itemIsOk(item):
                return
            if not self.IsSelected(item):
                self.UnselectAll()
                self.SelectItem(item)
        self.PopupMenu(self.__popupMenu)


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
                self, [wx.EVT_LIST_COL_RIGHT_CLICK], self.onColumnPopupMenu
            )

    def onColumnPopupMenu(self, event):
        # We store the columnIndex in the menu, because it's near to
        # impossible for commands in the menu to determine on what column the
        # menu was popped up.
        columnIndex = event.GetColumn()
        self.__popupMenu.columnIndex = columnIndex
        # Because right-clicking on column headers does not automatically give
        # focus to the control, we force the focus:
        try:
            window = event.GetEventObject().GetMainWindow()
        except AttributeError:
            window = event.GetEventObject()
        window.SetFocus()

        self.PopupMenu(self.__popupMenu)
        event.Skip(False)


class _CtrlWithDropTargetMixin(_CtrlWithItemsMixin):
    """Control that accepts files, e-mails or URLs being dropped onto items."""

    def __init__(self, *args, **kwargs):
        self.__onDropURLCallback = kwargs.pop("onDropURL", None)
        self.__onDropFilesCallback = kwargs.pop("onDropFiles", None)
        self.__onDropMailCallback = kwargs.pop("onDropMail", None)
        super().__init__(*args, **kwargs)
        if (
            self.__onDropURLCallback
            or self.__onDropFilesCallback
            or self.__onDropMailCallback
        ):
            dropTarget = draganddrop.DropTarget(
                self.onDropURL,
                self.onDropFiles,
                self.onDropMail,
                self.onDragOver,
            )
            self.GetMainWindow().SetDropTarget(dropTarget)

    def onDropURL(self, x, y, url):
        item = self.HitTest((x, y))[0]
        if self.__onDropURLCallback:
            self.__onDropURLCallback(self._objectBelongingTo(item), url)

    def onDropFiles(self, x, y, filenames):
        item = self.HitTest((x, y))[0]
        if self.__onDropFilesCallback:
            self.__onDropFilesCallback(
                self._objectBelongingTo(item), filenames
            )

    def onDropMail(self, x, y, mail):
        item = self.HitTest((x, y))[0]
        if self.__onDropMailCallback:
            self.__onDropMailCallback(self._objectBelongingTo(item), mail)

    def onDragOver(self, x, y, defaultResult):
        item, flags = self.HitTest((x, y))[:2]
        if self._itemIsOk(item):
            if flags & wx.TREE_HITTEST_ONITEMBUTTON:
                self.Expand(item)
        return defaultResult

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
        domainObject = self._objectBelongingTo(item)
        if domainObject:
            tooltipData = self.getItemTooltipData(domainObject)
            doShow = any([data[1] for data in tooltipData])
            if doShow:
                self.__tip.SetData(tooltipData)
                return self.__tip
        return None


class CtrlWithItemsMixin(
    _CtrlWithItemPopupMenuMixin, _CtrlWithDropTargetMixin
):
    pass


class Column(object):
    def __init__(self, name, columnHeader, *eventTypes, **kwargs):
        self.__name = name
        self.__columnHeader = columnHeader
        self.width = kwargs.pop(
            "width", hypertreelist._DEFAULT_COL_WIDTH
        )  # pylint: disable=W0212
        # The event types to use for registering an observer that is
        # interested in changes that affect this column:
        self.__eventTypes = eventTypes
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
        # NB: because the header image is needed for sorting a fixed header
        # image cannot be combined with a sortable column
        self.__headerImageIndex = kwargs.pop("headerImageIndex", -1)
        self.__editCallback = kwargs.get("editCallback", None)
        self.__editControlClass = kwargs.get("editControl", None)
        self.__parse = kwargs.get("parse", lambda value: value)
        self.__settings = kwargs.get(
            "settings", None
        )  # FIXME: Column shouldn't need to know about settings

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

    def __filterArgs(self, func, kwargs):
        actualKwargs = dict()
        argNames = inspect.getargspec(func).args
        return dict(
            [
                (name, value)
                for name, value in list(kwargs.items())
                if name in argNames
            ]
        )

    def render(self, *args, **kwargs):
        return self.__renderCallback(
            *args, **self.__filterArgs(self.__renderCallback, kwargs)
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
        return self.__hasImages

    def isEditable(self):
        return self.__editControlClass != None and self.__editCallback != None

    def onEndEdit(self, item, newValue):
        self.__editCallback(item, newValue)

    def editControl(self, parent, item, columnIndex, domainObject):
        value = self.value(domainObject)
        kwargs = dict(settings=self.__settings) if self.__settings else dict()
        # pylint: disable=W0142
        return self.__editControlClass(
            parent, wx.ID_ANY, item, columnIndex, parent, value, **kwargs
        )

    def parse(self, value):
        return self.__parse(value)

    def value(self, domainObject):
        return getattr(domainObject, self.name())()

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
        for columnIndex, column in enumerate(self.__allColumns):
            self._insertColumn(columnIndex, column)

    def _insertColumn(self, columnIndex, column):
        newMap = []
        for colIndex, col in self.__indexMap:
            if colIndex >= columnIndex:
                newMap.append((colIndex + 1, col))
            else:
                newMap.append((colIndex, col))
        newMap.append((columnIndex, column))
        self.__indexMap = newMap

        self.InsertColumn(
            columnIndex,
            column.header() if column.headerImageIndex() == -1 else "",
            format=column.alignment(),
            width=column.width,
        )

        columnInfo = self.GetColumn(columnIndex)
        columnInfo.SetImage(column.headerImageIndex())
        self.SetColumn(columnIndex, columnInfo)

    def _deleteColumn(self, columnIndex):
        newMap = []
        for colIndex, col in self.__indexMap:
            if colIndex > columnIndex:
                newMap.append((colIndex - 1, col))
            elif colIndex < columnIndex:
                newMap.append((colIndex, col))
        self.__indexMap = newMap
        self.DeleteColumn(columnIndex)

    def _allColumns(self):
        return self.__allColumns

    def _getColumn(self, columnIndex):
        for colIndex, col in self.__indexMap:
            if colIndex == columnIndex:
                return col
        raise IndexError

    def _getColumnHeader(self, columnIndex):
        """The currently displayed column header in the column with index
        columnIndex."""
        return self.GetColumn(columnIndex).GetText()

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
        columnIndex = self._getColumnIndex(column)
        if show and not self.isColumnVisible(column):
            self._insertColumn(columnIndex, column)
        elif not show and self.isColumnVisible(column):
            self._deleteColumn(columnIndex)

    def isColumnVisible(self, column):
        return column in self._visibleColumns()

    def _getColumnIndex(self, column):
        """_getColumnIndex returns the actual columnIndex of the column if it
        is visible, or the position it would have if it were visible."""
        columnIndexWhenAllColumnsVisible = super(
            _CtrlWithHideableColumnsMixin, self
        )._getColumnIndex(column)
        for columnIndex, visibleColumn in enumerate(self._visibleColumns()):
            if (
                super()._getColumnIndex(visibleColumn)
                >= columnIndexWhenAllColumnsVisible
            ):
                return columnIndex
        return self.GetColumnCount()  # Column header not found

    def _visibleColumns(self):
        return [
            self._getColumn(columnIndex)
            for columnIndex in range(self.GetColumnCount())
        ]


class _CtrlWithSortableColumnsMixin(_BaseCtrlWithColumnsMixin):
    """This class adds sort indicators and clickable column headers that
    trigger callbacks to (re)sort the contents of the control."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.onColumnClick)
        self.__currentSortColumn = self._getColumn(0)
        self.__currentSortImageIndex = -1

    def onColumnClick(self, event):
        event.Skip(False)
        # Make sure the window this control is in has focus:
        try:
            window = event.GetEventObject().GetMainWindow()
        except AttributeError:
            window = event.GetEventObject()
        window.SetFocus()
        columnIndex = event.GetColumn()
        if 0 <= columnIndex < self.GetColumnCount():
            column = self._getColumn(columnIndex)
            # Use CallAfter to make sure the window this control is in is
            # activated before we process the column click:
            wx.CallAfter(self.__safeColumnSort, column, event)

    def __safeColumnSort(self, column, event):
        """Safely call column.sort, guarding against deleted C++ objects."""
        try:
            if self:
                column.sort(event)
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def showSortColumn(self, column):
        if column != self.__currentSortColumn:
            self._clearSortImage()
        self.__currentSortColumn = column
        self._showSortImage()

    def showSortOrder(self, imageIndex):
        self.__currentSortImageIndex = imageIndex
        self._showSortImage()

    def _clearSortImage(self):
        self.__setSortColumnImage(-1)

    def _showSortImage(self):
        self.__setSortColumnImage(self.__currentSortImageIndex)

    def _currentSortColumn(self):
        return self.__currentSortColumn

    def __setSortColumnImage(self, imageIndex):
        columnIndex = self._getColumnIndex(self.__currentSortColumn)
        columnInfo = self.GetColumn(columnIndex)
        if columnInfo.GetImage() == imageIndex:
            pass  # The column is already showing the right image, so we're done
        else:
            columnInfo.SetImage(imageIndex)
            self.SetColumn(columnIndex, columnInfo)


class _CtrlWithAutoResizedColumnsMixin(autowidth.AutoColumnWidthMixin):
    """Mixin that provides auto-column-resizing and saves column widths.

    When auto-resize is enabled, one column (typically subject/tree column)
    automatically fills remaining window space. When disabled, columns use
    standard wxWidgets resize behavior.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Bind(wx.EVT_LIST_COL_END_DRAG, self.onEndColumnResize)

    def onEndColumnResize(self, event):
        """Save the column widths after the user did a resize."""
        for index, column in enumerate(self._visibleColumns()):
            column.setWidth(self.GetColumnWidth(index))
        event.Skip()


class CtrlWithColumnsMixin(
    _CtrlWithAutoResizedColumnsMixin,
    _CtrlWithHideableColumnsMixin,
    _CtrlWithSortableColumnsMixin,
    _CtrlWithColumnPopupMenuMixin,
):
    """CtrlWithColumnsMixin combines the functionality of its four parent
    classes: automatic resizing of columns, hideable columns, columns with
    sort indicators, and column popup menu's."""

    def showColumn(self, column, show=True):
        super().showColumn(column, show)
        # Show sort indicator if the column that was just made visible is being sorted on
        if show and column == self._currentSortColumn():
            self._showSortImage()

    def _clearSortImage(self):
        # Only clear the sort image if the column in question is visible
        if self.isColumnVisible(self._currentSortColumn()):
            super()._clearSortImage()

    def _showSortImage(self):
        # Only show the sort image if the column in question is visible
        if self.isColumnVisible(self._currentSortColumn()):
            super()._showSortImage()
