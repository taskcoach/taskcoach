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
import urllib.request, urllib.parse, urllib.error
from taskcoachlib.mailer import thunderbird, outlook
from taskcoachlib.i18n import _


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
        onDropURLCallback,
        onDropFileCallback,
        onDropMailCallback,
        onDragOverCallback=None,
    ):
        super().__init__()
        self.__onDropURLCallback = onDropURLCallback
        self.__onDropFileCallback = onDropFileCallback
        self.__onDropMailCallback = onDropMailCallback
        self.__onDragOverCallback = onDragOverCallback
        self.reinit()

    def reinit(self):
        # pylint: disable=W0201
        self.__compositeDataObject = wx.DataObjectComposite()
        self.__urlDataObject = wx.TextDataObject()
        self.__fileDataObject = wx.FileDataObject()
        self.__thunderbirdMailDataObject = wx.CustomDataObject(
            "text/x-moz-message"
        )
        self.__urilistDataObject = wx.CustomDataObject("text/uri-list")
        self.__outlookDataObject = wx.CustomDataObject("Object Descriptor")
        # Starting with Snow Leopard, mail.app supports the message: protocol
        self.__macMailObject = wx.CustomDataObject("public.url")
        for dataObject in (
            self.__thunderbirdMailDataObject,
            self.__urilistDataObject,
            self.__macMailObject,
            self.__outlookDataObject,
            self.__urlDataObject,
            self.__fileDataObject,
        ):
            # Note: The first data object added is the preferred data object.
            # We add urlData after outlookData so that Outlook messages are not
            # interpreted as text objects.
            self.__compositeDataObject.Add(dataObject)
        self.SetDataObject(self.__compositeDataObject)

    def OnDragOver(self, x, y, result):  # pylint: disable=W0221
        if self.__onDragOverCallback is None:
            return result
        self.__onDragOverCallback(x, y, result)
        return wx.DragCopy

    def OnDrop(self, x, y):  # pylint: disable=W0613,W0221
        return True

    def OnData(self, x, y, result):  # pylint: disable=W0613
        self.GetData()
        formatType, formatId = self.getReceivedFormatTypeAndId()

        if formatId == "text/x-moz-message":
            self.onThunderbirdDrop(x, y)
        elif formatId == "text/uri-list" and formatType == wx.DF_FILENAME:
            urls = self.__urilistDataObject.GetData().strip().split("\n")
            for url in urls:
                url = url.strip()
                if url.startswith("#"):
                    continue
                if self.__tmp_mail_file_url(url) and self.__onDropMailCallback:
                    filename = urllib.parse.unquote(url[len("file://") :])
                    self.__onDropMailCallback(x, y, filename)
                elif self.__onDropURLCallback:
                    if url.startswith("file://"):
                        url = urllib.request.url2pathname(url[7:])
                    self.__onDropURLCallback(x, y, url)
        elif formatId == "Object Descriptor":
            self.onOutlookDrop(x, y)
        elif formatId == "public.url":
            url = self.__macMailObject.GetData()
            if (
                url.startswith("imap:") or url.startswith("mailbox:")
            ) and self.__onDropMailCallback:
                try:
                    self.__onDropMailCallback(x, y, thunderbird.getMail(url))
                except thunderbird.ThunderbirdCancelled:
                    pass
                except thunderbird.ThunderbirdError as e:
                    wx.MessageBox(str(e), _("Error"), wx.OK)
            elif self.__onDropURLCallback:
                self.__onDropURLCallback(x, y, url)
        elif formatType in (wx.DF_TEXT, wx.DF_UNICODETEXT):
            self.onUrlDrop(x, y)
        elif formatType == wx.DF_FILENAME:
            self.onFileDrop(x, y)

        self.reinit()
        return wx.DragCopy

    def getReceivedFormatTypeAndId(self):
        receivedFormat = self.__compositeDataObject.GetReceivedFormat()
        formatType = receivedFormat.GetType()
        try:
            formatId = receivedFormat.GetId()
        except RuntimeError:
            formatId = None  # Format ID not available
        return formatType, formatId

    @staticmethod
    def __tmp_mail_file_url(url):
        """Return whether the url is a dropped mail message."""
        return url.startswith("file:") and (
            "/.cache/evolution/tmp/drag-n-drop" in url
            or "/.claws-mail/tmp/" in url
        )

    def onThunderbirdDrop(self, x, y):
        if self.__onDropMailCallback:
            data = self.__thunderbirdMailDataObject.GetData()
            # We expect the data to be encoded with 'unicode_internal',
            # but on Fedora it can also be 'utf-16', be prepared:
            try:
                data = data.decode("unicode_internal")
            except UnicodeDecodeError:
                data = data.decode("utf-16")

            try:
                email = thunderbird.getMail(data)
            except thunderbird.ThunderbirdCancelled:
                pass
            except thunderbird.ThunderbirdError as e:
                wx.MessageBox(e.args[0], _("Error"), wx.OK | wx.ICON_ERROR)
            else:
                self.__onDropMailCallback(x, y, email)

    def onClawsDrop(self, x, y):
        if self.__onDropMailCallback:
            for filename in self.__fileDataObject.GetFilenames():
                self.__onDropMailCallback(x, y, filename)

    def onOutlookDrop(self, x, y):
        if self.__onDropMailCallback:
            for mail in outlook.getCurrentSelection():
                self.__onDropMailCallback(x, y, mail)

    def onUrlDrop(self, x, y):
        if self.__onDropURLCallback:
            url = self.__urlDataObject.GetText()
            if ":" not in url:  # No protocol; assume http
                url = "http://" + url
            self.__onDropURLCallback(x, y, url)

    def onFileDrop(self, x, y):
        if self.__onDropFileCallback:
            self.__onDropFileCallback(
                x, y, self.__fileDataObject.GetFilenames()
            )


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
        wx.CallAfter(self.__safeLateInit)

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
        tree control. `part` is 0 if the items were dropped on the middle third
        of the dropItem, -1 if they were dropped on the upper third and 1 for
        the lower third."""
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
        dropTarget = event.GetItem()
        if not dropTarget:
            dropTarget = self.GetRootItem()
        if self.IsValidDropTarget(dropTarget):
            self.UnselectAll()
            if dropTarget != self.GetRootItem():
                self.SelectItem(dropTarget)
            dummy_item, flags, dummy_column = self.HitTest(event.GetPoint())
            part = 0
            if flags & wx.TREE_HITTEST_ONITEMUPPERPART:
                part = -1
            elif flags & wx.TREE_HITTEST_ONITEMLOWERPART:
                part = 1
            self.OnDrop(dropTarget, self._dragItems, part, self._dragColumn)
        else:
            # Work around an issue with HyperTreeList. HyperTreeList will
            # restore the selection to the last item highlighted by the drag,
            # after we have processed the end drag event. That's not what we
            # want, so use wx.CallAfter to clear the selection after
            # HyperTreeList did its (wrong) thing and reselect the previously
            # dragged item.
            wx.CallAfter(self.__safeSelect, self._dragItems)
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
        item, flags = self.HitTest(wx.Point(event.GetX(), event.GetY()))[:2]
        if not item:
            item = self.GetRootItem()
        if self.IsValidDropTarget(item):
            self.SetCursorToDragging()
        else:
            self.SetCursorToDroppingImpossible()
        if flags & wx.TREE_HITTEST_ONITEMBUTTON:
            self.Expand(item)
        if self.GetSelections() != [item]:
            self.UnselectAll()
            if item != self.GetRootItem():
                self.SelectItem(item)
        event.Skip()

    def StartDragging(self):
        self.GetMainWindow().Bind(wx.EVT_MOTION, self.OnDragging)
        self.Bind(wx.EVT_TREE_END_DRAG, self.OnEndDrag)
        self.SetCursorToDragging()

    def StopDragging(self):
        self.GetMainWindow().Unbind(wx.EVT_MOTION)
        self.Unbind(wx.EVT_TREE_END_DRAG)
        self.ResetCursor()
        self.selectDraggedItems()

    def SetCursorToDragging(self):
        self.GetMainWindow().SetCursor(wx.Cursor(wx.CURSOR_HAND))

    def SetCursorToDroppingImpossible(self):
        self.GetMainWindow().SetCursor(wx.Cursor(wx.CURSOR_NO_ENTRY))

    def ResetCursor(self):
        self.GetMainWindow().SetCursor(wx.NullCursor)

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
