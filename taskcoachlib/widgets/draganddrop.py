"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2011 Tobias Gradl <https://sourceforge.net/users/greentomato>

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
from taskcoachlib import mailer, patterns
from taskcoachlib.mailer import thunderbird, outlook
from taskcoachlib.mailer.outlook import OUTLOOK_FORMAT
from taskcoachlib.i18n import _


def _getLinkCursor(window=None):
    """Get or create a link cursor for prereq/dep column drag."""
    from taskcoachlib.gui.icons.icon_library import icon_catalog

    return icon_catalog.get_cursor("synthetic_dnd_cursor_link", window)


def _getHomeCursor(window=None):
    """Get or create a home folder cursor for root drop locations."""
    from taskcoachlib.gui.icons.icon_library import icon_catalog

    return icon_catalog.get_cursor("synthetic_dnd_cursor_home", window)


def not_allowed_cursor(window=None):
    """Task Coach's own "not allowed" cursor: wx's no-entry cursor is
    a skull where the cursor theme has no picture for it."""
    from taskcoachlib.gui.icons.icon_library import icon_catalog

    return icon_catalog.get_cursor("synthetic_cursor_not_allowed", window)


class FileDropTarget(wx.FileDropTarget):
    def __init__(self, onDropCallback=None, onDragOverCallback=None):
        wx.FileDropTarget.__init__(self)
        self.__onDropCallback = onDropCallback
        self.__onDragOverCallback = (
            onDragOverCallback or self.__defaultDragOverCallback
        )

    def OnDropFiles(self, x, y, filenames):  # pylint: disable=W0221
        if self.__onDropCallback:
            self.__onDropCallback(x, y, filenames)
            return True
        else:
            return False

    def OnDragOver(self, x, y, defaultResult):  # pylint: disable=W0221
        return self.__onDragOverCallback(x, y, defaultResult)

    def __defaultDragOverCallback(
        self, x, y, defaultResult
    ):  # pylint: disable=W0613
        return defaultResult


class TextDropTarget(wx.TextDropTarget):
    def __init__(self, onDropCallback):
        wx.TextDropTarget.__init__(self)
        self.__onDropCallback = onDropCallback

    def OnDropText(self, x, y, text):  # pylint: disable=W0613,W0221
        self.__onDropCallback(text)


class DropTarget(wx.DropTarget):
    def __init__(
        self,
        on_drop_url,
        on_drop_files,
        on_drop_mail,
        onDragOverCallback=None,
    ):
        super().__init__()
        self.__on_drop_url = on_drop_url
        self.__on_drop_files = on_drop_files
        self.__on_drop_mail = on_drop_mail
        self.__onDragOverCallback = onDragOverCallback
        self.reinit()

    def reinit(self):
        # pylint: disable=W0201
        self._text_data = wx.TextDataObject()
        self._file_data = wx.FileDataObject()
        # Only Outlook drags this format (docs/EMAIL_ATTACHMENTS.md)
        self._outlook_data = wx.CustomDataObject(OUTLOOK_FORMAT)
        # A macOS drag's link: an Apple Mail or Thunderbird message
        self._url_data = wx.CustomDataObject("public.url")
        self.__composite = wx.DataObjectComposite()
        # On Windows and macOS the first format here that the source
        # offers is taken, so Outlook's comes before text; GTK takes
        # the source's first format we accept
        for data_object in (
            self._url_data,
            self._outlook_data,
            self._text_data,
            self._file_data,
        ):
            self.__composite.Add(data_object)
        self.SetDataObject(self.__composite)

    def OnDragOver(self, x, y, result):  # pylint: disable=W0221
        if self.__onDragOverCallback is None:
            return result
        self.__onDragOverCallback(x, y, result)
        return wx.DragCopy

    def OnDrop(self, x, y):  # pylint: disable=W0613,W0221
        return True

    def OnData(self, x, y, result):  # pylint: disable=W0613
        self.GetData()
        self.dispatch(x, y, *self.get_received_format_type_and_id())
        self.reinit()
        return wx.DragCopy

    def get_received_format_type_and_id(self):
        received_format = self.__composite.GetReceivedFormat()
        try:
            format_id = received_format.GetId()
        except RuntimeError:
            format_id = None  # Format ID not available
        return received_format.GetType(), format_id

    def dispatch(self, x, y, format_type, format_id):
        """Hand the dropped data, as the data objects hold it, to its
        callback: a mail program's mails, files, a link or text."""
        if format_id == OUTLOOK_FORMAT:
            self.on_outlook_drop(x, y)
        elif format_id == "public.url":
            self.on_mac_url_drop(x, y)
        elif format_type in (wx.DF_TEXT, wx.DF_UNICODETEXT):
            self.on_url_drop(x, y)
        elif format_type == wx.DF_FILENAME:
            self.on_file_drop(x, y)

    def __drop_mails(self, x, y, mails):
        if mails and self.__on_drop_mail:
            self.__on_drop_mail(x, y, mails)

    def __thunderbird_mails(self, uris):
        try:
            return [thunderbird.get_mail(uri) for uri in uris]
        except thunderbird.ThunderbirdCancelled:
            return []
        except thunderbird.ThunderbirdError as reason:
            wx.MessageBox(str(reason), _("Error"), wx.OK | wx.ICON_ERROR)
            return []

    def on_outlook_drop(self, x, y):
        self.__drop_mails(x, y, outlook.get_current_selection())

    def on_mac_url_drop(self, x, y):
        url = bytes(self._url_data.GetData()).decode("utf-8", "replace")
        url = url.strip("\x00\r\n ")
        if url.startswith(("imap:", "mailbox:")):
            # Thunderbird's message
            self.__drop_mails(x, y, self.__thunderbird_mails([url]))
        elif self.__on_drop_url:
            self.__on_drop_url(x, y, url)

    def on_url_drop(self, x, y):
        text = self._text_data.GetText()
        # Thunderbird drags its messages' URIs as text
        uris = thunderbird.message_uris(text)
        if uris:
            self.__drop_mails(x, y, self.__thunderbird_mails(uris))
        elif self.__on_drop_url:
            url = text if ":" in text else "http://" + text  # No scheme
            self.__on_drop_url(x, y, url)

    def on_file_drop(self, x, y):
        # A mail program drags its mails as files in a temporary
        # folder (docs/EMAIL_ATTACHMENTS.md, The Drop). On GTK a dropped
        # uri-list comes here too, as file names; wx refuses web links
        # in it
        filenames, mails = [], []
        for filename in self._file_data.GetFilenames():
            dropped = mailer.dropped_mails(filename)
            if dropped and self.__on_drop_mail:
                mails.extend(dropped)
            else:
                filenames.append(filename)
        self.__drop_mails(x, y, mails)
        if filenames and self.__on_drop_files:
            self.__on_drop_files(x, y, filenames)


class HoverExpander:
    """Expands the collapsed item a drag hovers over: after 500 ms, or
    at once on its expand button. One per control (hover_expander()),
    for drags within the tree and drops from outside alike."""

    def __init__(self, ctrl):
        self.__ctrl = ctrl
        self.__item = None
        self.__expand_later = patterns.later.debounced(
            ctrl, 500, self.__expand
        )

    def hover(self, item, flags):
        if flags & wx.TREE_HITTEST_ONITEMBUTTON:
            self.stop()
            self.__expand_now(item)
        elif not self.__is_expandable(item):
            self.stop()
        elif item != self.__item:
            self.__item = item
            self.__expand_later()

    def stop(self):
        self.__expand_later.cancel()
        self.__item = None

    def __is_expandable(self, item):
        ctrl = self.__ctrl
        try:
            return bool(
                item
                and item != ctrl.GetRootItem()
                and ctrl.ItemHasChildren(item)
                and not ctrl.IsExpanded(item)
            )
        except (RuntimeError, AttributeError):
            return False  # A deleted item, or a list control

    def __expand(self):
        item, self.__item = self.__item, None
        if self.__is_expandable(item):
            self.__expand_now(item)

    def __expand_now(self, item):
        try:
            self.__ctrl.Expand(item)
        except (RuntimeError, AttributeError):
            pass  # A deleted item, or a list control


def hover_expander(ctrl):
    """The control's HoverExpander, made on first use."""
    expander = getattr(ctrl, "_hover_expander", None)
    if expander is None:
        expander = ctrl._hover_expander = HoverExpander(ctrl)
    return expander


class TreeHelperMixin(object):
    """This class provides methods that are not part of the API of any
    tree control, but are convenient to have available."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def GetItemChildren(self, item=None, recursively=False):
        """Return the children of item as a list."""
        if not item:
            item = self.GetRootItem()
            if not item:
                return []
        children = []
        child, cookie = self.GetFirstChild(item)
        while child:
            children.append(child)
            if recursively:
                children.extend(self.GetItemChildren(child, True))
            child, cookie = self.GetNextChild(item, cookie)
        return children


class TreeCtrlDragAndDropMixin(TreeHelperMixin):
    """This is a mixin class that can be used to easily implement
    dragging and dropping of tree items. It can be mixed in with
    wx.TreeCtrl, wx.gizmos.TreeListCtrl, or wx.lib.customtree.CustomTreeCtrl.

    To use it derive a new class from this class and one of the tree
    controls, e.g.:
    class MyTree(TreeCtrlDragAndDropMixin, wx.TreeCtrl):
        ...

    You *must* implement OnDrop. OnDrop is called when the user has
    dropped an item on top of another item. It's up to you to decide how
    to handle the drop. If you are using this mixin together with the
    VirtualTree mixin, it makes sense to rearrange your underlying data
    and then call RefreshItems to let the virtual tree refresh itself."""

    def __init__(self, *args, **kwargs):
        kwargs["style"] = (
            kwargs.get("style", wx.TR_DEFAULT_STYLE) | wx.TR_HIDE_ROOT
        )
        self._validateDragCallback = kwargs.pop("validateDrag", None)
        super().__init__(*args, **kwargs)
        patterns.later.soon(self, self.__safeLateInit)

    def __safeLateInit(self):
        """Safely perform late initialization, guarding against deleted C++ objects."""
        try:
            if self:
                self._lateInit()
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def _lateInit(self):
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnBeginDrag)
        self._dragStartPos = None
        self.GetMainWindow().Bind(wx.EVT_LEFT_DOWN, self._OnLeftDown)
        self._dragItems = []

    def OnDrop(self, dropItem, dragItems, part, column):
        """This function must be overloaded in the derived class. dragItems
        are the items being dragged by the user. dropItem is the item the
        dragItems are dropped on. If the user doesn't drop the dragItems
        on another item, dropItem equals the (hidden) root item of the
        tree control.

        Drop modes based on column:
        - Prerequisites column: make dragItems prerequisites of dropItem
        - Dependencies column: make dragItems dependencies of dropItem
        - Other columns: make dragItems children of dropItem
        - Drop on header: make dragItems root tasks
        """
        raise NotImplementedError

    def OnBeginDrag(self, event):
        """This method is called when the drag starts. It either allows the
        drag and starts it or it vetoes the drag when the the root item is one
        of the dragged items."""
        column = self._ColumnHitTest(self._dragStartPos)
        selections = self.GetSelections()
        self._dragItems = (
            selections[:]
            if selections
            else [event.GetItem()] if event.GetItem() else []
        )
        self._dragColumn = column
        if self._dragItems and (self.GetRootItem() not in self._dragItems):
            self.StartDragging()
            event.Allow()
        else:
            event.Veto()

    def _OnLeftDown(self, event):
        # event.GetPoint() in OnBeginDrag is totally off.
        self._dragStartPos = wx.Point(event.GetX(), event.GetY())
        event.Skip()

    def _ColumnHitTest(self, point):
        # Aaaand HitTest() returns -1 too often...
        hwin = self.GetHeaderWindow()
        x = 0
        for j in range(self.GetColumnCount()):
            if not hwin.IsColumnShown(j):
                continue
            w = hwin.GetColumnWidth(j)
            if point.x >= x and point.x < x + w:
                return j
            x += w
        return -1

    def OnEndDrag(self, event):
        self.StopDragging()
        # Use HitTest to determine actual drop target, not event.GetItem()
        # which may return the last highlighted item even when outside
        hitItem, flags, dropColumn = self.HitTest(event.GetPoint())

        # Check if drop is outside items (left, right, above, below, or nowhere)
        outside_flags = (
            wx.TREE_HITTEST_TOLEFT
            | wx.TREE_HITTEST_TORIGHT
            | wx.TREE_HITTEST_ABOVE
            | wx.TREE_HITTEST_BELOW
            | wx.TREE_HITTEST_NOWHERE
        )
        if not hitItem or (flags & outside_flags):
            # Drop outside items - make root task
            dropTarget = self.GetRootItem()
        else:
            dropTarget = hitItem

        if self.IsValidDropTarget(dropTarget):
            self.UnselectAll()
            if dropTarget != self.GetRootItem():
                self.SelectItem(dropTarget)
            part = 0
            if flags & wx.TREE_HITTEST_ONITEMUPPERPART:
                part = -1
            elif flags & wx.TREE_HITTEST_ONITEMLOWERPART:
                part = 1
            # Use _ColumnHitTest on the drop point to reliably detect the
            # target column (HitTest can return -1 for narrow columns)
            actualDropColumn = self._ColumnHitTest(event.GetPoint())
            self.OnDrop(dropTarget, self._dragItems, part, actualDropColumn)
        else:
            # Work around an issue with HyperTreeList. HyperTreeList will
            # restore the selection to the last item highlighted by the drag,
            # after we have processed the end drag event. That's not what we
            # want, so clear the selection later, after
            # HyperTreeList did its (wrong) thing and reselect the previously
            # dragged item.
            patterns.later.soon(self, self.__safeSelect, self._dragItems)
        self._dragItems = []

    def __safeSelect(self, items):
        """Safely call select, guarding against deleted C++ objects."""
        try:
            if self:
                self.select(items)
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def selectDraggedItems(self):
        self.select(reversed(self._dragItems))

    def OnDragging(self, event):
        if not event.Dragging():
            self.StopDragging()
            return
        point = wx.Point(event.GetX(), event.GetY())
        item, flags, column = self.HitTest(point)
        isRootDrop = not item or item == self.GetRootItem()
        if not item:
            item = self.GetRootItem()
        if self.IsValidDropTarget(item):
            # Use appropriate cursor based on drop location
            if isRootDrop:
                self.SetCursorToHome()
            elif self._isPrereqOrDepColumn(column):
                self.SetCursorToLink()
            else:
                self.SetCursorToDragging()
            # Update drop visual feedback
            self._UpdateDropFeedback(item, flags, column, point)
        else:
            self.SetCursorToDroppingImpossible()
            self._ClearDropFeedback()
        # Auto-expand collapsed items on hover (modern UX behavior)
        hover_expander(self).hover(item, flags)
        if self.GetSelections() != [item]:
            self.UnselectAll()
            if item != self.GetRootItem():
                self.SelectItem(item)
        event.Skip()

    def _UpdateDropFeedback(self, item, flags, column, point):
        """Update visual feedback during drag based on drop position."""
        mainWin = self.GetMainWindow()

        if not item or item == self.GetRootItem():
            mainWin.ClearDropHighlight()
            return

        # Highlight cell if on prereq/dep column
        try:
            mainWin.SetDropHighlight(item, column)
        except (AttributeError, RuntimeError):
            mainWin.ClearDropHighlight()

    def _ClearDropFeedback(self):
        """Clear all drop visual feedback."""
        mainWin = self.GetMainWindow()
        if hasattr(mainWin, "ClearDropHighlight"):
            mainWin.ClearDropHighlight()

    def StartDragging(self):
        self.GetMainWindow().Bind(wx.EVT_MOTION, self.OnDragging)
        self.GetMainWindow().Bind(wx.EVT_KEY_DOWN, self.OnKeyDuringDrag)
        self.Bind(wx.EVT_TREE_END_DRAG, self.OnEndDrag)
        # Also bind to header window for header drops
        headerWin = self.GetHeaderWindow()
        if headerWin:
            headerWin.Bind(wx.EVT_MOTION, self.OnDraggingOverHeader)
            headerWin.Bind(wx.EVT_LEFT_UP, self.OnDropOnHeader)
        self.SetCursorToDragging()

    def StopDragging(self):
        self.GetMainWindow().Unbind(wx.EVT_MOTION)
        self.GetMainWindow().Unbind(wx.EVT_KEY_DOWN)
        self.Unbind(wx.EVT_TREE_END_DRAG)
        # Unbind header events
        headerWin = self.GetHeaderWindow()
        if headerWin:
            headerWin.Unbind(wx.EVT_MOTION)
            headerWin.Unbind(wx.EVT_LEFT_UP)
        # Cancel any pending hover-expand
        hover_expander(self).stop()
        # Clean up HyperTreeList's internal drag state
        mainWin = self.GetMainWindow()
        if hasattr(mainWin, "_dragImage") and mainWin._dragImage:
            mainWin._dragImage.EndDrag()
            mainWin._dragImage = None
        if hasattr(mainWin, "_isDragging"):
            mainWin._isDragging = False
        self.ResetCursor()
        self._ResetHeaderCursor()
        self._ClearDropFeedback()
        self.selectDraggedItems()
        # Refresh to clear any visual artifacts
        mainWin.Refresh()

    def OnKeyDuringDrag(self, event):
        """Handle key presses during drag - Escape cancels the operation."""
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.StopDragging()
            self._dragItems = []
        else:
            event.Skip()

    def SetCursorToDragging(self):
        self.GetMainWindow().SetCursor(wx.Cursor(wx.CURSOR_HAND))

    def SetCursorToLink(self):
        """Set cursor to link icon when over prereq/dep columns."""
        self.GetMainWindow().SetCursor(_getLinkCursor(self.GetMainWindow()))

    def SetCursorToHome(self):
        """Set cursor to home folder icon when over root drop locations."""
        self.GetMainWindow().SetCursor(_getHomeCursor(self.GetMainWindow()))

    def SetCursorToDroppingImpossible(self):
        self.GetMainWindow().SetCursor(
            not_allowed_cursor(self.GetMainWindow())
        )

    def ResetCursor(self):
        self.GetMainWindow().SetCursor(wx.NullCursor)

    def _ResetHeaderCursor(self):
        """Reset cursor on header window."""
        headerWin = self.GetHeaderWindow()
        if headerWin:
            headerWin.SetCursor(wx.NullCursor)

    def OnDraggingOverHeader(self, event):
        """Handle mouse motion over the header window during dragging."""
        if not self._dragItems:
            event.Skip()
            return
        # Show home folder cursor when over header (indicates root drop)
        headerWin = self.GetHeaderWindow()
        if headerWin:
            headerWin.SetCursor(_getHomeCursor(headerWin))
        # Clear drop feedback in main window since we're over header
        self._ClearDropFeedback()
        event.Skip()

    def OnDropOnHeader(self, event):
        """Handle drop on the header window - makes task a root task."""
        if not self._dragItems:
            event.Skip()
            return

        # Get the column under the mouse
        headerWin = self.GetHeaderWindow()
        if not headerWin:
            event.Skip()
            return

        x, _ = self.CalcUnscrolledPosition(event.GetX(), 0)
        column = headerWin.XToCol(x)

        # Only the main column (first column, index 0) makes task a root
        # For other columns, we could add different behaviors later
        if column == 0:
            # Make tasks root tasks by dropping on hidden root
            dropTarget = self.GetRootItem()
            self.OnDrop(dropTarget, self._dragItems, 0, 0)

        self.StopDragging()
        self._dragItems = []
        event.Skip()

    def _isPrereqOrDepColumn(self, column):
        """Check if the column index is a prerequisites or dependencies column."""
        if column < 0:
            return False
        try:
            # Try to get column name via _getColumn (available in TreeListCtrl)
            if hasattr(self, "_getColumn"):
                col = self._getColumn(column)
                if hasattr(col, "name"):
                    name = col.name()
                    return name in ("prerequisites", "dependencies")
        except (IndexError, AttributeError):
            pass
        return False

    def IsValidDropTarget(self, dropTarget):
        if self._validateDragCallback is not None:
            isValid = self._validateDragCallback(
                self.GetItemPyData(dropTarget),
                [self.GetItemPyData(item) for item in self._dragItems],
                self._dragColumn,
            )
            if isValid is not None:
                return isValid

        if dropTarget:
            # Dropping on hidden root is always valid (makes items root-level)
            if dropTarget == self.GetRootItem():
                return True
            invalidDropTargets = set(self._dragItems)
            invalidDropTargets |= set(
                self.GetItemParent(item) for item in self._dragItems
            )
            for item in self._dragItems:
                invalidDropTargets |= set(
                    self.GetItemChildren(item, recursively=True)
                )
            return dropTarget not in invalidDropTargets
        else:
            return True
