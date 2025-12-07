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
from wx.lib.agw import customtreectrl as customtree, hypertreelist
from taskcoachlib.widgets import itemctrl, draganddrop
import wx


# pylint: disable=E1101,E1103


class BaseHyperTreeList(hypertreelist.HyperTreeList):
    def __init__(
        self,
        parent,
        id=wx.ID_ANY,
        pos=wx.DefaultPosition,
        size=wx.DefaultSize,
        style=0,
        agwStyle=wx.TR_DEFAULT_STYLE,
        validator=wx.DefaultValidator,
        name="HyperTreeList",
        *args,
        **kwargs
    ):
        super().__init__(
            parent, id, pos, size, style, agwStyle, validator, name
        )


class HyperTreeList(draganddrop.TreeCtrlDragAndDropMixin, BaseHyperTreeList):
    # pylint: disable=W0223

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        BaseHyperTreeList.__init__(self, *args, **kwargs)

        if operating_system.isGTK():
            self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.__on_item_collapsed)

    def __on_item_collapsed(self, event):
        event.Skip()
        # On Ubuntu, when the user has scrolled to the bottom of the tree
        # and collapses an item, the tree is not redrawn correctly. Refreshing
        # solves this. See http://trac.wxwidgets.org/ticket/11704
        wx.CallAfter(self.__safeRefresh)

    def __safeRefresh(self):
        """Safely refresh the main window, guarding against deleted C++ objects."""
        try:
            if self.MainWindow:
                self.MainWindow.Refresh()
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def GetSelections(self):  # pylint: disable=C0103
        """If the root item is hidden, it should never be selected.
        Unfortunately, CustomTreeCtrl and HyperTreeList allow it to be
        selected. Override GetSelections to fix that."""
        selections = super().GetSelections()
        if self.HasFlag(wx.TR_HIDE_ROOT):
            root_item = self.GetRootItem()
            if root_item and root_item in selections:
                selections.remove(root_item)
        return selections

    def GetMainWindow(self, *args, **kwargs):  # pylint: disable=C0103
        """Have a local GetMainWindow so we can create a MainWindow
        property."""
        return super().GetMainWindow(*args, **kwargs)

    MainWindow = property(fget=GetMainWindow)

    def HitTest(self, point):  # pylint: disable=W0221, C0103
        """Always return a three-tuple (item, flags, column)."""
        if type(point) == type(()):
            point = wx.Point(point[0], point[1])
        hit_test_result = super().HitTest(point)
        if len(hit_test_result) == 2:
            hit_test_result += (0,)
        if hit_test_result[0] is None:
            hit_test_result = (wx.TreeItemId(),) + hit_test_result[1:]
        return hit_test_result

    def isClickablePartOfNodeClicked(self, event):
        """Return whether the user double clicked some part of the node that
        can also receive regular mouse clicks."""
        return self.__is_collapse_expand_button_clicked(event)

    def __is_collapse_expand_button_clicked(self, event):
        flags = self.HitTest(event.GetPosition())[1]
        return flags & wx.TREE_HITTEST_ONITEMBUTTON

    def select(self, selection):
        """Select items whose PyData is in the selection list.
        Returns the first selected tree item (for scrolling).

        Note: UnselectAll() is required before SelectItem() after a tree rebuild.
        This appears to be a HyperTreeList quirk/bug - SelectItem() silently fails
        without it, even though DoSelectItem has unselect_others=True by default.
        See: https://github.com/wxWidgets/Phoenix/issues/1164 for related issues."""
        first_selected_item = None
        self.UnselectAll()
        for item in self.GetItemChildren(recursively=True):
            pydata = self.GetItemPyData(item)
            if pydata in selection:
                self.SelectItem(item, True)
                if first_selected_item is None:
                    first_selected_item = item
        return first_selected_item

    def clear_selection(self):
        self.UnselectAll()
        self.selectCommand()

    def select_all(self):
        if self.GetItemCount() > 0:
            self.SelectAll()
        self.selectCommand()

    def isAnyItemCollapsable(self):
        for item in self.GetItemChildren():
            if self.__is_item_collapsable(item):
                return True
        return False

    def isAnyItemExpandable(self):
        for item in self.GetItemChildren():
            if self.__is_item_expandable(item):
                return True
        return False

    def __is_item_expandable(self, item):
        return self.ItemHasChildren(item) and not self.IsExpanded(item)

    def __is_item_collapsable(self, item):
        return self.ItemHasChildren(item) and self.IsExpanded(item)

    def IsLabelBeingEdited(self):
        return bool(self.GetLabelTextCtrl())

    def StopEditing(self):
        if self.IsLabelBeingEdited():
            self.GetLabelTextCtrl().StopEditing()

    def GetLabelTextCtrl(self):
        return self.GetMainWindow()._editCtrl  # pylint: disable=W0212

    def GetItemCount(self):
        root_item = self.GetRootItem()
        return (
            self.GetChildrenCount(root_item, recursively=True)
            if root_item
            else 0
        )


class TreeListCtrl(
    itemctrl.CtrlWithItemsMixin,
    itemctrl.CtrlWithColumnsMixin,
    itemctrl.CtrlWithToolTipMixin,
    HyperTreeList,
):
    # TreeListCtrl uses ALIGN_LEFT, ..., ListCtrl uses LIST_FORMAT_LEFT, ... for
    # specifying alignment of columns. This dictionary allows us to map from the
    # ListCtrl constants to the TreeListCtrl constants:
    alignmentMap = {
        wx.LIST_FORMAT_LEFT: wx.ALIGN_LEFT,
        wx.LIST_FORMAT_CENTRE: wx.ALIGN_CENTRE,
        wx.LIST_FORMAT_CENTER: wx.ALIGN_CENTER,
        wx.LIST_FORMAT_RIGHT: wx.ALIGN_RIGHT,
    }
    ct_type = 0

    def __init__(
        self,
        parent,
        columns,
        selectCommand,
        editCommand,
        dragAndDropCommand,
        itemPopupMenu=None,
        columnPopupMenu=None,
        *args,
        **kwargs
    ):
        self.__adapter = parent
        self.__selection = []
        self.__user_double_clicked = False
        self.__columns_with_images = []
        self.__default_font = wx.NORMAL_FONT
        self.__refreshing = False  # Flag to suppress selection events during refresh
        kwargs.setdefault("resizeableColumn", 0)
        super().__init__(
            parent,
            style=self.__get_style(),
            agwStyle=self.__get_agw_style(),
            columns=columns,
            itemPopupMenu=itemPopupMenu,
            columnPopupMenu=columnPopupMenu,
            *args,
            **kwargs
        )
        self.bindEventHandlers(selectCommand, editCommand, dragAndDropCommand)

    def bindEventHandlers(
        self, selectCommand, editCommand, dragAndDropCommand
    ):
        # pylint: disable=W0201
        self.selectCommand = selectCommand
        self.editCommand = editCommand
        self.dragAndDropCommand = dragAndDropCommand
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.onSelect)
        self.Bind(wx.EVT_TREE_KEY_DOWN, self.onKeyDown)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.onItemActivated)
        # We deal with double clicks ourselves, to prevent the default behaviour
        # of collapsing or expanding nodes on double click.
        self.GetMainWindow().Bind(wx.EVT_LEFT_DCLICK, self.onDoubleClick)
        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.onBeginEdit)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.onEndEdit)
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.onItemExpanding)
        self.Bind(wx.EVT_SET_FOCUS, self.onSetFocus)

    def onSetFocus(self, event):  # pylint: disable=W0613
        # Send a child focus event to let the AuiManager know we received focus
        # so it will activate our pane
        wx.PostEvent(self._main_win, wx.ChildFocusEvent(self._main_win))
        self.SetFocus()

    def getItemTooltipData(self, item):
        return self.__adapter.getItemTooltipData(item)

    def getItemCTType(self, item):  # pylint: disable=W0613
        return self.ct_type

    def curselection(self):
        # Guard against deleted C++ object - can happen when wx.CallAfter
        # callback executes after window destruction (e.g., closing nested dialogs)
        try:
            # Filter out None values - GetItemPyData can return None for some items
            # (e.g., root items or items without associated PyData)
            return [
                data for item in self.GetSelections()
                if (data := self.GetItemPyData(item)) is not None
            ]
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            return []

    def RefreshAllItems(self, count=0):  # pylint: disable=W0613
        self.Freeze()
        self.StopEditing()
        self.__refreshing = True  # Suppress selection events during rebuild
        self.__selection = self.curselection()
        self.DeleteAllItems()
        self.__columns_with_images = [
            index
            for index in range(self.GetColumnCount())
            if self.__adapter.hasColumnImages(index)
        ]
        root_item = self.GetRootItem()
        if not root_item:
            root_item = self.AddRoot("Hidden root")
        self._addObjectRecursively(root_item)
        self.Thaw()
        self.__refreshing = False
        # Restore selection AFTER Thaw - SelectItem doesn't work while Frozen
        selected_item = None
        if self.__selection:
            selected_item = self.select(self.__selection)
        selections = self.GetSelections()
        # Use the item returned by select() for scrolling if GetSelections fails
        scroll_target = selections[0] if selections else selected_item
        if scroll_target:
            self.GetMainWindow()._current = (
                self.GetMainWindow()._key_current
            ) = scroll_target
            self.ScrollTo(scroll_target)
        # Force immediate repaint to reduce visible flicker after rebuild
        self.GetMainWindow().Refresh(eraseBackground=False)

    def RefreshItems(self, *objects):
        self.__selection = self.curselection()
        self._refreshTargetObjects(self.GetRootItem(), *objects)

    def _refreshTargetObjects(self, parent_item, *target_objects):
        child_item, cookie = self.GetFirstChild(parent_item)
        while child_item:
            item_object = self.GetItemPyData(child_item)
            if item_object in target_objects:
                self._refreshObjectCompletely(child_item, item_object)
            self._refreshTargetObjects(child_item, *target_objects)
            child_item, cookie = self.GetNextChild(parent_item, cookie)

    def _refreshObjectCompletely(self, item, *args):
        self.__refresh_aspects(
            ("ItemType", "Columns", "Font", "Colors", "Selection"),
            item,
            check=True,
            *args
        )
        self.GetMainWindow().RefreshLine(item)

    def _addObjectRecursively(self, parent_item, parent_object=None):
        for child_object in self.__adapter.children(parent_object):
            child_item = self.AppendItem(
                parent_item,
                "",
                self.getItemCTType(child_object),
                data=child_object,
            )
            self._refreshObjectMinimally(child_item, child_object)
            expanded = self.__adapter.getItemExpanded(child_object)
            if expanded:
                self._addObjectRecursively(child_item, child_object)
                # Call Expand on the item instead of on the tree
                # (self.Expand(childItem)) to prevent lots of events
                # (EVT_TREE_ITEM_EXPANDING/EXPANDED) being sent
                child_item.Expand()
            else:
                self.SetItemHasChildren(
                    child_item, self.__adapter.children(child_object)
                )

    def _refreshObjectMinimally(self, *args, **kwargs):
        self.__refresh_aspects(
            ("Columns", "Colors", "Font", "Selection"), *args, **kwargs
        )

    def __refresh_aspects(self, aspects, *args, **kwargs):
        for aspect in aspects:
            refresh_aspect = getattr(self, "_refresh%s" % aspect)
            refresh_aspect(*args, **kwargs)

    def _refreshItemType(self, item, domain_object, check=False):
        ct_type = self.getItemCTType(domain_object)
        if not check or (check and ct_type != self.GetItemType(item)):
            self.SetItemType(item, ct_type)

    def _refreshColumns(self, item, domain_object, check=False):
        for column_index in range(self.GetColumnCount()):
            self._refreshColumn(item, domain_object, column_index, check=check)

    def _refreshColumn(self, item, domain_object, column_index, check=False):
        aspects = (
            ("Text", "Image")
            if column_index in self.__columns_with_images
            else ("Text",)
        )
        self.__refresh_aspects(
            aspects, item, domain_object, column_index, check=check
        )

    def _refreshText(self, item, domain_object, column_index, check=False):
        text = self.__adapter.getItemText(domain_object, column_index)
        if text.count("\n") > 3:
            text = "\n".join(text.split("\n")[:4]) + " ..."
        if not check or (check and text != item.GetText(column_index)):
            item.SetText(column_index, text)

    def _refreshImage(self, item, domain_object, column_index, check=False):
        images = self.__adapter.getItemImages(domain_object, column_index)
        for which, image in list(images.items()):
            image = image if image >= 0 else -1
            if not check or (
                check and image != item.GetImage(which, column_index)
            ):
                item.SetImage(column_index, image, which)

    def _refreshColors(self, item, domain_object, check=False):
        bg_color = (
            domain_object.backgroundColor(recursive=True) or wx.NullColour
        )
        if not check or (
            check and bg_color != self.GetItemBackgroundColour(item)
        ):
            self.SetItemBackgroundColour(item, bg_color)
        fg_color = (
            domain_object.foregroundColor(recursive=True) or wx.NullColour
        )
        if not check or (check and fg_color != self.GetItemTextColour(item)):
            self.SetItemTextColour(item, fg_color)

    def _refreshFont(self, item, domain_object, check=False):
        font = domain_object.font(recursive=True) or self.__default_font
        if not check or (check and font != self.GetItemFont(item)):
            self.SetItemFont(item, font)

    def _refreshSelection(self, item, domain_object, check=False):
        select = domain_object in self.__selection
        if not check or (check and select != item.IsSelected()):
            # Use SetHilight for visual highlighting during tree construction.
            # Actual selection is done via select() after tree is fully built.
            item.SetHilight(select)

    # Event handlers

    def onSelect(self, event):
        # Skip selection events during refresh to avoid spurious updates
        if self.__refreshing:
            event.Skip()
            return
        # Use CallAfter to prevent handling the select while items are
        # being deleted:
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

    def onKeyDown(self, event):
        if event.GetKeyCode() == wx.WXK_RETURN:
            self.editCommand(event)
        elif event.GetKeyCode() == wx.WXK_F2 and self.GetSelections():
            self.EditLabel(self.GetSelections()[0], column=0)
        else:
            event.Skip()

    def OnDrop(self, drop_item, drag_items, part, column):
        drop_item = (
            None
            if drop_item == self.GetRootItem()
            else self.GetItemPyData(drop_item)
        )
        drag_items = list(
            self.GetItemPyData(drag_item) for drag_item in drag_items
        )
        wx.CallAfter(
            self.__safeDragAndDropCommand, drop_item, drag_items, part, column
        )

    def __safeDragAndDropCommand(self, drop_item, drag_items, part, column):
        """Safely call dragAndDropCommand, guarding against deleted C++ objects."""
        try:
            if self:
                self.dragAndDropCommand(drop_item, drag_items, part, column)
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def onItemExpanding(self, event):
        event.Skip()
        item = event.GetItem()
        if self.GetChildrenCount(item, recursively=False) == 0:
            domain_object = self.GetItemPyData(item)
            self._addObjectRecursively(item, domain_object)

    def onDoubleClick(self, event):
        self.__user_double_clicked = True
        if self.isClickablePartOfNodeClicked(event):
            event.Skip(False)
        else:
            self.onItemActivated(event)

    def onItemActivated(self, event):
        """Attach the column clicked on to the event so we can use it
        elsewhere."""
        column_index = self.__column_under_mouse()
        if column_index >= 0:
            event.columnName = self._getColumn(column_index).name()
        self.editCommand(event)
        event.Skip(False)

    def __column_under_mouse(self):
        mouse_position = self.GetMainWindow().ScreenToClient(
            wx.GetMousePosition()
        )
        item, _, column = self.HitTest(mouse_position)
        if item:
            # Only get the column name if the hittest returned an item,
            # otherwise the item was activated from the menu or by double
            # clicking on a portion of the tree view not containing an item.
            return max(0, column)  # FIXME: Why can the column be -1?
        else:
            return -1

    # Inline editing

    def onBeginEdit(self, event):
        if self.__user_double_clicked:
            event.Veto()
            self.__user_double_clicked = False
        elif self.IsLabelBeingEdited():
            # Don't start editing another label when the user is still editing
            # a label. This prevents left-over text controls in the tree.
            event.Veto()
        else:
            event.Skip()

    def onEndEdit(self, event):
        if event._editCancelled:  # pylint: disable=W0212
            event.Skip()
            return
        event.Veto()  # Let us update the tree
        domain_object = self.GetItemPyData(event.GetItem())
        new_value = event.GetLabel()
        column = self._getColumn(event.GetInt())
        column.onEndEdit(domain_object, new_value)

    def CreateEditCtrl(self, item, column_index):
        column = self._getColumn(column_index)
        domain_object = self.GetItemPyData(item)
        return column.editControl(
            self.GetMainWindow(), item, column_index, domain_object
        )

    # Override CtrlWithColumnsMixin with TreeListCtrl specific behaviour:

    def _setColumns(self, *args, **kwargs):
        super()._setColumns(*args, **kwargs)
        self.SetMainColumn(0)
        for column_index in range(self.GetColumnCount()):
            self.SetColumnEditable(
                column_index, self._getColumn(column_index).isEditable()
            )

    # Extend TreeMixin with TreeListCtrl specific behaviour:

    @staticmethod
    def __get_style():
        # Enable horizontal scrollbar for natural column resizing
        return wx.WANTS_CHARS | wx.HSCROLL

    @staticmethod
    def __get_agw_style():
        agw_style = (
            wx.TR_DEFAULT_STYLE
            | wx.TR_HIDE_ROOT
            | wx.TR_MULTIPLE
            | wx.TR_EDIT_LABELS
            | wx.TR_HAS_BUTTONS
            | wx.TR_FULL_ROW_HIGHLIGHT
            | customtree.TR_HAS_VARIABLE_ROW_HEIGHT
        )
        if operating_system.isMac():
            agw_style |= wx.TR_NO_LINES
        agw_style &= ~hypertreelist.TR_NO_HEADER
        return agw_style

    # pylint: disable=W0221

    def DeleteColumn(self, column_index):
        self.RemoveColumn(column_index)

    def InsertColumn(self, column_index, column_header, *args, **kwargs):
        alignment = self.alignmentMap[
            kwargs.pop("format", wx.LIST_FORMAT_LEFT)
        ]
        if column_index == self.GetColumnCount():
            self.AddColumn(column_header, *args, **kwargs)
        else:
            super().InsertColumn(column_index, column_header, *args, **kwargs)
        self.SetColumnAlignment(column_index, alignment)
        self.SetColumnEditable(
            column_index, self._getColumn(column_index).isEditable()
        )

    def showColumn(self, *args, **kwargs):
        """Stop editing before we hide or show a column to prevent problems
        redrawing the tree list control contents."""
        self.StopEditing()
        super().showColumn(*args, **kwargs)


class CheckTreeCtrl(TreeListCtrl):
    def __init__(
        self,
        parent,
        columns,
        selectCommand,
        checkCommand,
        editCommand,
        dragAndDropCommand,
        itemPopupMenu=None,
        *args,
        **kwargs
    ):
        self.__checking = False
        super().__init__(
            parent,
            columns,
            selectCommand,
            editCommand,
            dragAndDropCommand,
            itemPopupMenu,
            *args,
            **kwargs
        )
        self.checkCommand = checkCommand
        self.Bind(customtree.EVT_TREE_ITEM_CHECKED, self.onItemChecked)
        self.GetMainWindow().Bind(wx.EVT_LEFT_DOWN, self.onMouseLeftDown)
        self.getIsItemCheckable = (
            parent.getIsItemCheckable
            if hasattr(parent, "getIsItemCheckable")
            else lambda item: True
        )
        self.getIsItemChecked = parent.getIsItemChecked
        self.getItemParentHasExclusiveChildren = (
            parent.getItemParentHasExclusiveChildren
        )

    def getItemCTType(self, domain_object):
        """Use radio buttons (ct_type == 2) when the object has "exclusive"
        children, meaning that only one child can be checked at a time. Use
        check boxes (ct_type == 1) otherwise."""
        if self.getIsItemCheckable(domain_object):
            return (
                2
                if self.getItemParentHasExclusiveChildren(domain_object)
                else 1
            )
        else:
            return 0

    def CheckItem(self, item, checked=True):
        if self.GetItemType(item) == 2:
            # Use UnCheckRadioParent because CheckItem always keeps at least
            # one item selected, which we don't want to enforce
            self.UnCheckRadioParent(item, checked)
        else:
            super().CheckItem(item, checked)

    def onMouseLeftDown(self, event):
        """By default, the HyperTreeList widget doesn't allow for unchecking
        a radio item. Since we do want to support unchecking a radio
        item, we look for mouse left down and uncheck the item and all of
        its children if the user clicks on an already selected radio
        item."""
        position = self.GetMainWindow().CalcUnscrolledPosition(
            event.GetPosition()
        )
        item, flags, dummy_column = self.HitTest(position)
        if (
            item
            and item.GetType() == 2
            and (flags & customtree.TREE_HITTEST_ONITEMCHECKICON)
            and self.IsItemChecked(item)
        ):
            self.__uncheck_item_recursively(item)
        else:
            event.Skip()

    def __uncheck_item_recursively(
        self, item, parent_is_expanded=True, disable_item=False
    ):
        if item.GetType():
            self.__uncheck_item(item, torefresh=parent_is_expanded)
        if disable_item:
            self.EnableItem(item, False, torefresh=parent_is_expanded)
        parent_is_expanded = item.IsExpanded()
        child, cookie = self.GetFirstChild(item)
        while child:
            self.__uncheck_item_recursively(
                child, parent_is_expanded, disable_item=True
            )
            child, cookie = self.GetNextChild(item, cookie)

    def __uncheck_item(self, item, torefresh):
        self.GetMainWindow().CheckItem2(
            item, checked=False, torefresh=torefresh
        )
        event = customtree.TreeEvent(
            customtree.wxEVT_TREE_ITEM_CHECKED, self.GetId()
        )
        event.SetItem(item)
        event.SetEventObject(self)
        self.GetEventHandler().ProcessEvent(event)

    def _refreshObjectCompletely(self, item, domain_object):
        super()._refreshObjectCompletely(item, domain_object)
        self._refreshCheckState(item, domain_object)

    def _refreshObjectMinimally(self, item, domain_object):
        super()._refreshObjectMinimally(item, domain_object)
        self._refreshCheckState(item, domain_object)

    def _refreshCheckState(self, item, domain_object):
        # Use CheckItem2 so no events get sent:
        self.CheckItem2(item, self.getIsItemChecked(domain_object))
        parent = item.GetParent()
        while parent:
            if self.GetItemType(parent) == 2:
                self.EnableItem(item, self.IsItemChecked(parent))
                break
            parent = parent.GetParent()

    def onItemChecked(self, event):
        if self.__checking:
            # Ignore checked events while we're making the tree consistent,
            # only invoke the callback:
            self.checkCommand(event, final=False)
            return
        self.__checking = True
        item = event.GetItem()
        # Uncheck mutually exclusive children:
        for child in self.GetItemChildren(item):
            if self.GetItemType(child) == 2:
                self.CheckItem(child, False)
                # Recursively uncheck children of mutually exclusive children:
                for grandchild in self.GetItemChildren(
                    child, recursively=True
                ):
                    self.CheckItem(grandchild, False)
        # If this item is mutually exclusive, recursively uncheck siblings
        # and parent:
        parent = item.GetParent()
        if parent and self.GetItemType(item) == 2:
            for child in self.GetItemChildren(parent):
                if child == item:
                    continue
                self.CheckItem(child, False)
                for grandchild in self.GetItemChildren(
                    child, recursively=True
                ):
                    self.CheckItem(grandchild, False)
            if self.GetItemType(parent) != 2:
                self.CheckItem(parent, False)
        self.__checking = False
        self.checkCommand(event, final=True)

    def onItemActivated(self, event):
        if self.__is_double_clicked(event):
            # Invoke super.onItemActivated to edit the item
            super().onItemActivated(event)
        else:
            # Item is activated, let another event handler deal with the event
            event.Skip()

    @staticmethod
    def __is_double_clicked(event):
        return hasattr(event, "LeftDClick") and event.LeftDClick()
