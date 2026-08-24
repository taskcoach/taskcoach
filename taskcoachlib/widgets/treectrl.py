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
import contextlib
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
        **kwargs,
    ):
        super().__init__(
            parent, id, pos, size, style, agwStyle, validator, name
        )
        # Bind our own size handler to fix scrollbar issues on Windows.
        # The base HyperTreeList.OnSize only calls DoHeaderLayout() which
        # repositions child windows but doesn't recalculate scrollbars.
        self.Bind(wx.EVT_SIZE, self.__on_size)

    def __on_size(self, event):
        """Handle size events to ensure scrollbars are recalculated.

        On Windows, side-docked AUI panes don't get scrollbars when the content
        exceeds the visible area because HyperTreeList's OnSize handler only
        repositions child windows without recalculating scrollbars. We fix this
        by calling AdjustMyScrollbars() after the base OnSize handler runs.
        """
        event.Skip()  # Let base class handle layout first
        # Schedule scrollbar adjustment after the layout is complete
        wx.CallAfter(self.__safe_adjust_scrollbars)

    def __safe_adjust_scrollbars(self):
        """Safely adjust scrollbars, guarding against deleted C++ objects.
        Also re-centers on selected item after resize."""
        try:
            main_win = self.GetMainWindow()
            if main_win:
                main_win.AdjustMyScrollbars()
                if hasattr(self, "scroll_to_selection_centered"):
                    self.scroll_to_selection_centered()
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            from taskcoachlib.meta.debug import log_step

            log_step(
                "__on_size failed - widget already destroyed",
                prefix="DEAD-OBJ",
            )

    def _schedule_scrollbar_adjustment(self):
        """Schedule scrollbar adjustment for after event processing completes.

        On Windows, content changes (expand/collapse/add/delete) that don't
        trigger window resize don't update scrollbars. Use wx.CallAfter to
        defer adjustment until after the event cycle completes. Other platforms
        handle this automatically through their event processing, but the
        deferred call is harmless and ensures consistency.
        """
        if operating_system.isWindows():
            wx.CallAfter(self.__safe_adjust_scrollbars_content_change)
        else:
            self.__safe_adjust_scrollbars_content_change()

    def __safe_adjust_scrollbars_content_change(self):
        """Safely adjust scrollbars after content changes without
        re-centering."""
        try:
            main_win = self.GetMainWindow()
            if main_win:
                main_win.AdjustMyScrollbars()
        except RuntimeError:
            from taskcoachlib.meta.debug import log_step

            log_step(
                "scrollbar adjustment failed - widget already destroyed",
                prefix="DEAD-OBJ",
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
        wx.CallAfter(self.__safe_refresh)

    def __safe_refresh(self):
        """Safely refresh the main window, guarding against deleted
        C++ objects."""
        try:
            if self.MainWindow:
                self.MainWindow.Refresh()
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            from taskcoachlib.meta.debug import log_step

            log_step(
                "__safe_refresh failed - widget already destroyed",
                prefix="DEAD-OBJ",
            )

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

    def is_clickable_part_of_node_clicked(self, event):
        """Return whether the user double clicked some part of the node that
        can also receive regular mouse clicks."""
        return self.__is_collapse_expand_button_clicked(event)

    def __is_collapse_expand_button_clicked(self, event):
        flags = self.HitTest(event.GetPosition())[1]
        return flags & wx.TREE_HITTEST_ONITEMBUTTON

    def select(self, selection):
        """Select items whose PyData is in the selection list.
        Returns the first selected tree item (for scrolling).

        Note: UnselectAll() is required before SelectItem() after a
        tree rebuild. This appears to be a HyperTreeList quirk/bug -
        SelectItem() silently fails without it, even though
        DoSelectItem has unselect_others=True by default. See:
        https://github.com/wxWidgets/Phoenix/issues/1164 for related
        issues.
        """
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

    def _recalculated_main_window(self):
        """Return the main window with item positions up to date.

        Item positions drive both the scrollbar range and GetY(), but
        AdjustMyScrollbars() never recalculates them; only ScrollTo()
        does, guarded on the _dirty flag. Both it and CalculatePositions()
        also return early while the window is frozen, so after a
        freeze/thaw rebuild the positions are still stale and anything
        reading them silently works off the old layout.

        The flag is deliberately left set, exactly as upstream ScrollTo()
        leaves it: customtreectrl only ever sets _dirty, it never clears
        it, so clearing it here would suppress recalculations upstream
        still expects to happen.
        """
        main = self.GetMainWindow()
        if getattr(main, "_dirty", False):
            main.CalculatePositions()
        return main

    def selection_neighbours(self):
        """Return the objects displayed around the current selection.

        The result is a tuple (above, below).  "above" holds the objects
        displayed above the topmost selected row, nearest row first;
        "below" holds the objects displayed below the bottommost
        selected row, again nearest row first.  Callers use this to pick
        a replacement selection when the selected rows disappear.

        Rows scrolled out of the viewport count as neighbours, which is
        why this walks the tree itself instead of using upstream
        GetPrevVisible/GetNextVisible: those also test whether the row
        is on screen.
        """
        try:
            selections = self.GetSelections()
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            return [], []
        if not selections:
            return [], []
        # GetY() drives the ordering, so make sure positions are current
        self._recalculated_main_window()
        rows = sorted(selections, key=lambda item: item.GetY())
        return (
            list(self.__walk_rows(rows[0], self.__row_above)),
            list(self.__walk_rows(rows[-1], self.__row_below)),
        )

    def __walk_rows(self, item, step):
        """Yield the objects of the rows reached by repeating step."""
        root_item = self.GetRootItem()
        item = step(item)
        while item is not None and item != root_item:
            data = self.GetItemPyData(item)
            if data is not None:
                yield data
            item = step(item)

    def __row_above(self, item):
        """Return the row displayed directly above item, or None."""
        sibling = self.GetPrevSibling(item)
        if sibling is None:
            parent = self.GetItemParent(item)
            return None if parent == self.GetRootItem() else parent
        # The row above a sibling is that sibling's last open descendant
        while self.IsExpanded(sibling):
            last_child = self.GetLastChild(sibling)
            if last_child is None:
                break
            sibling = last_child
        return sibling

    def __row_below(self, item):
        """Return the row displayed directly below item, or None."""
        if self.IsExpanded(item):
            first_child = self.GetFirstChild(item)[0]
            if first_child is not None:
                return first_child
        root_item = self.GetRootItem()
        while item is not None and item != root_item:
            sibling = self.GetNextSibling(item)
            if sibling is not None:
                return sibling
            item = self.GetItemParent(item)
        return None

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
    # TreeListCtrl uses ALIGN_LEFT, ..., ListCtrl uses
    # LIST_FORMAT_LEFT, ... for specifying alignment of columns. This
    # dictionary allows us to map from the ListCtrl constants to the
    # TreeListCtrl constants:
    alignment_map = {
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
        **kwargs,
    ):
        self.__adapter = parent
        self.__selection = []
        self.__user_double_clicked = False
        self.__columns_with_images = []
        self.__default_font = wx.NORMAL_FONT
        self.__refreshing = False
        kwargs.setdefault("resizeableColumn", 0)
        super().__init__(
            parent,
            style=self.__get_style(),
            agwStyle=self.__get_agw_style(),
            columns=columns,
            itemPopupMenu=itemPopupMenu,
            columnPopupMenu=columnPopupMenu,
            *args,
            **kwargs,
        )
        self.bind_event_handlers(
            selectCommand, editCommand, dragAndDropCommand
        )
        self.GetMainWindow().Bind(wx.EVT_LEAVE_WINDOW, self._on_hover_leave)

    def bind_event_handlers(
        self, selectCommand, editCommand, dragAndDropCommand
    ):
        # pylint: disable=W0201
        self.selectCommand = selectCommand
        self.editCommand = editCommand
        self.dragAndDropCommand = dragAndDropCommand
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_select)
        self.Bind(wx.EVT_TREE_KEY_DOWN, self.on_key_down)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_item_activated)
        # We deal with double clicks ourselves, to prevent the default
        # behaviour of collapsing or expanding nodes on double click.
        self.GetMainWindow().Bind(wx.EVT_LEFT_DCLICK, self.on_double_click)
        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.on_begin_edit)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.on_end_edit)
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.on_item_expanding)
        self.Bind(wx.EVT_SET_FOCUS, self.on_set_focus)

    def on_set_focus(self, event):  # pylint: disable=W0613
        # Send a child focus event to let the AuiManager know we received focus
        # so it will activate our pane
        wx.PostEvent(self, wx.ChildFocusEvent(self))
        event.Skip()

    def _on_hover_leave(self, event):
        self.GetMainWindow().SetHoverItem(None)
        event.Skip()

    def getItemTooltipData(self, item):
        return self.__adapter.getItemTooltipData(item)

    def get_item_ct_type(self, item):  # pylint: disable=W0613
        return self.ct_type

    @property
    def has_selection(self):
        return bool(self.GetSelections())

    @property
    def has_single_selection(self):
        return len(self.GetSelections()) == 1

    def curselection(self):
        # Guard against deleted C++ object - can happen when wx.CallAfter
        # callback executes after window destruction (e.g., closing
        # nested dialogs)
        try:
            # Filter out None values - GetItemPyData can return None
            # for some items
            # (e.g., root items or items without associated PyData)
            return [
                data
                for item in self.GetSelections()
                if (data := self.GetItemPyData(item)) is not None
            ]
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            return []

    def _snapshot_tree(self, parent_item):
        """Return list of object IDs in depth-first order for current tree."""
        result = []
        child_item, cookie = self.GetFirstChild(parent_item)
        while child_item:
            obj = self.GetItemPyData(child_item)
            result.append(obj.id() if obj else None)
            result.extend(self._snapshot_tree(child_item))
            child_item, cookie = self.GetNextChild(parent_item, cookie)
        return result

    def _snapshot_adapter(self, parent_object=None):
        """Return list of object IDs in depth-first order from adapter."""
        result = []
        for child_object in self.__adapter.children(parent_object):
            result.append(child_object.id())
            if self.__adapter.get_item_expanded(child_object):
                result.extend(self._snapshot_adapter(child_object))
        return result

    def RefreshAllItems(self, count=0):  # pylint: disable=W0613
        # Check if tree structure actually changed before rebuilding
        root_item = self.GetRootItem()
        if root_item:
            current = self._snapshot_tree(root_item)
            desired = self._snapshot_adapter()
            if current and current == desired:
                # Structure unchanged - refresh items in place
                self._refresh_all_items_in_place(root_item)
                return

        self._do_full_rebuild()

    def _refresh_all_items_in_place(self, parent_item):
        """Refresh text, colors, font for all items without rebuilding."""
        child_item, cookie = self.GetFirstChild(parent_item)
        while child_item:
            obj = self.GetItemPyData(child_item)
            if obj is not None:
                self._refresh_object_completely(child_item, obj)
            self._refresh_all_items_in_place(child_item)
            child_item, cookie = self.GetNextChild(parent_item, cookie)
        # After refreshing all items, ensure scrollbars reflect current content
        # on Windows where content changes may not trigger scrollbar updates
        if parent_item == self.GetRootItem():
            self._schedule_scrollbar_adjustment()

    def _do_full_rebuild(self):
        """Full delete-and-recreate rebuild of the tree.

        Synchronous: Freeze, rebuild, Thaw, Refresh.  The motion-only
        input filter in frame.py prevents the AUI cascade by blocking
        mouse motion events during and after rebuild.
        """
        from taskcoachlib.widgets.frame import (
            _input_filter,
            _ensure_filter_installed,
        )

        _ensure_filter_installed()
        _input_filter.acquire()
        auto_scroll = self._auto_scroll_enabled()
        saved_view = (
            None if auto_scroll else self.GetMainWindow().GetViewStart()
        )
        self.__refreshing = True
        self.Freeze()
        self.StopEditing()
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
        self._add_object_recursively(root_item)
        self.Thaw()
        self.__refreshing = False
        # Restore selection AFTER Thaw - SelectItem doesn't work while Frozen
        if self.__selection:
            self.select(self.__selection)
        if auto_scroll:
            self.scroll_to_selection()
        else:
            # Keep the viewport where the user left it. This also undoes
            # the implicit EnsureVisible triggered by restoring the
            # selection.
            main = self._recalculated_main_window()
            main.AdjustMyScrollbars()
            main.Scroll(*saved_view)
        # Immediate repaint - no blank screen
        self.GetMainWindow().Refresh(eraseBackground=False)
        _input_filter.release()

    def _auto_scroll_enabled(self):
        """Whether the view may scroll by itself to follow the
        selection."""
        settings = getattr(self.__adapter, "settings", None)
        if settings is None:
            return True
        return settings.getboolean("view", "autoscrollselection")

    @contextlib.contextmanager
    def stable_viewport(self):
        """Keep the viewport where it is while the block runs.

        Selecting an item makes upstream customtreectrl call
        EnsureVisible, so any programmatic selection scrolls the view.
        When auto-scroll is off the viewport has to be put back
        afterwards, the same way _do_full_rebuild does once it has
        restored its own selection.
        """
        if self._auto_scroll_enabled():
            yield
            return
        saved_view = self.GetMainWindow().GetViewStart()
        try:
            yield
        finally:
            main = self._recalculated_main_window()
            main.AdjustMyScrollbars()
            main.Scroll(*saved_view)

    def scroll_to_selection(self):
        """Scroll minimally to make first selected item visible."""
        selections = self.GetSelections()
        if selections:
            main = self.GetMainWindow()
            main.AdjustMyScrollbars()
            self.ScrollTo(selections[0])

    def scroll_to_selection_centered(self):
        """Center viewport on first selected item."""
        if not self._auto_scroll_enabled():
            return
        selections = self.GetSelections()
        if selections:
            main = self.GetMainWindow()
            main.AdjustMyScrollbars()
            item = selections[0]
            item_y = item.GetY()
            x_unit, y_unit = main.GetScrollPixelsPerUnit()
            client_h = main.GetClientSize().GetHeight()
            line_h = main.GetLineHeight(item)
            center_y = max(0, item_y - client_h // 2 + line_h // 2)
            x_pos = main.GetScrollPos(wx.HORIZONTAL)
            main.Scroll(x_pos, center_y // y_unit if y_unit > 0 else 0)

    def RefreshItems(self, *objects):
        self.__selection = self.curselection()
        self._refresh_target_objects(self.GetRootItem(), *objects)

    def _refresh_target_objects(self, parent_item, *target_objects):
        child_item, cookie = self.GetFirstChild(parent_item)
        while child_item:
            item_object = self.GetItemPyData(child_item)
            if item_object in target_objects:
                self._refresh_object_completely(child_item, item_object)
            self._refresh_target_objects(child_item, *target_objects)
            child_item, cookie = self.GetNextChild(parent_item, cookie)

    def _refresh_object_completely(self, item, *args):
        self.__refresh_aspects(
            ("item_type", "columns", "font", "colors", "selection"),
            item,
            check=True,
            *args,
        )
        self.GetMainWindow().RefreshLine(item)

    def _add_object_recursively(self, parent_item, parent_object=None):
        for child_object in self.__adapter.children(parent_object):
            child_item = self.AppendItem(
                parent_item,
                "",
                self.get_item_ct_type(child_object),
                data=child_object,
            )
            self._refresh_object_minimally(child_item, child_object)
            expanded = self.__adapter.get_item_expanded(child_object)
            if expanded:
                self._add_object_recursively(child_item, child_object)
                # Call Expand on the item instead of on the tree
                # (self.Expand(childItem)) to prevent lots of events
                # (EVT_TREE_ITEM_EXPANDING/EXPANDED) being sent
                child_item.Expand()
            else:
                self.SetItemHasChildren(
                    child_item, self.__adapter.children(child_object)
                )

    def _refresh_object_minimally(self, *args, **kwargs):
        self.__refresh_aspects(
            ("columns", "colors", "font", "selection"), *args, **kwargs
        )

    def __refresh_aspects(self, aspects, *args, **kwargs):
        for aspect in aspects:
            refresh_aspect = getattr(self, "_refresh_%s" % aspect)
            refresh_aspect(*args, **kwargs)

    def _refresh_item_type(self, item, domain_object, check=False):
        ct_type = self.get_item_ct_type(domain_object)
        if not check or (check and ct_type != self.GetItemType(item)):
            self.SetItemType(item, ct_type)

    def _refresh_columns(self, item, domain_object, check=False):
        for column_index in range(self.GetColumnCount()):
            self._refresh_column(
                item, domain_object, column_index, check=check
            )

    def _refresh_column(self, item, domain_object, column_index, check=False):
        aspects = (
            ("text", "image")
            if column_index in self.__columns_with_images
            else ("text",)
        )
        self.__refresh_aspects(
            aspects, item, domain_object, column_index, check=check
        )

    def _refresh_text(self, item, domain_object, column_index, check=False):
        text = self.__adapter.getItemText(domain_object, column_index)
        if text.count("\n") > 3:
            text = "\n".join(text.split("\n")[:4]) + " ..."
        if not check or (check and text != item.GetText(column_index)):
            item.SetText(column_index, text)

    def _refresh_image(self, item, domain_object, column_index, check=False):
        if self.__adapter.hasColumnMultiImages(column_index):
            images = self.__adapter.getItemMultiImages(
                domain_object, column_index
            )
            if not check or (check and images != item.GetImages(column_index)):
                item.SetImages(column_index, images)
            return
        images = self.__adapter.getItemImages(domain_object, column_index)
        for which, image in list(images.items()):
            image = image if image >= 0 else -1
            if not check or (
                check and image != item.GetImage(which, column_index)
            ):
                item.SetImage(column_index, image, which)

    def _refresh_colors(self, item, domain_object, check=False):
        bg_color = domain_object.backgroundColor(recursive=True)
        fg_color = domain_object.foregroundColor(recursive=True)
        if bg_color is None:
            # wx.NullColour doesn't work correctly on Windows - it renders as
            # black instead of transparent. Use system listbox color to match
            # HyperTreeList's GetClassDefaultAttributes (SYS_COLOUR_LISTBOX).
            if operating_system.isWindows():
                bg_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOX)
            else:
                bg_color = wx.NullColour
        if not check or (
            check and bg_color != self.GetItemBackgroundColour(item)
        ):
            self.SetItemBackgroundColour(item, bg_color)
        if fg_color is None:
            if operating_system.isWindows():
                fg_color = wx.SystemSettings.GetColour(
                    wx.SYS_COLOUR_WINDOWTEXT
                )
            else:
                fg_color = wx.NullColour
        if not check or (check and fg_color != self.GetItemTextColour(item)):
            self.SetItemTextColour(item, fg_color)

    def _refresh_font(self, item, domain_object, check=False):
        font = domain_object.font(recursive=True) or self.__default_font
        if not check or (check and font != self.GetItemFont(item)):
            self.SetItemFont(item, font)

    def _refresh_selection(self, item, domain_object, check=False):
        select = domain_object in self.__selection
        if not check or (check and select != item.IsSelected()):
            # Use SetHilight for visual highlighting during tree construction.
            # Actual selection is done via select() after tree is fully built.
            item.SetHilight(select)

    # Event handlers

    def on_select(self, event):
        # Skip selection events during refresh to avoid spurious updates
        if self.__refreshing:
            event.Skip()
            return
        # Use CallAfter to prevent handling the select while items are
        # being deleted:
        wx.CallAfter(self.__safe_select_command)
        event.Skip()

    def __safe_select_command(self):
        """Safely call selectCommand, guarding against deleted C++ objects."""
        try:
            if self:
                self.selectCommand()
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            from taskcoachlib.meta.debug import log_step

            log_step(
                "selectCommand() failed - widget already destroyed",
                prefix="DEAD-OBJ",
            )

    def on_key_down(self, event):
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
            self.__safe_drag_and_drop_command,
            drop_item,
            drag_items,
            part,
            column,
        )

    def __safe_drag_and_drop_command(
        self, drop_item, drag_items, part, column
    ):
        """Safely call dragAndDropCommand, guarding against deleted
        C++ objects."""
        try:
            if self:
                self.dragAndDropCommand(drop_item, drag_items, part, column)
                # Expand the drop target if items were dropped on it
                if drop_item is not None:
                    self._expand_drop_target(drop_item)
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            from taskcoachlib.meta.debug import log_step

            log_step(
                "dragAndDropCommand failed - widget already destroyed",
                prefix="DEAD-OBJ",
            )

    def _expand_drop_target(self, drop_item):
        """Expand the drop target item so the dropped children are visible."""
        # Find the tree item for the drop target
        for item in self.GetItemChildren(recursively=True):
            if self.GetItemPyData(item) == drop_item:
                if self.GetChildrenCount(
                    item, recursively=False
                ) > 0 or self.ItemHasChildren(item):
                    self.Expand(item)
                    self._schedule_scrollbar_adjustment()
                break

    def on_item_expanding(self, event):
        event.Skip()
        item = event.GetItem()
        if self.GetChildrenCount(item, recursively=False) == 0:
            domain_object = self.GetItemPyData(item)
            self._add_object_recursively(item, domain_object)
            self._schedule_scrollbar_adjustment()

    def on_double_click(self, event):
        self.__user_double_clicked = True
        if self.is_clickable_part_of_node_clicked(event):
            event.Skip(False)
        else:
            self.on_item_activated(event)

    def on_item_activated(self, event):
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

    def on_begin_edit(self, event):
        if self.__user_double_clicked:
            event.Veto()
            self.__user_double_clicked = False
        elif self.IsLabelBeingEdited():
            # Don't start editing another label when the user is still editing
            # a label. This prevents left-over text controls in the tree.
            event.Veto()
        else:
            event.Skip()

    def on_end_edit(self, event):
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
        alignment = self.alignment_map[
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
        **kwargs,
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
            **kwargs,
        )
        self.checkCommand = checkCommand
        self.Bind(customtree.EVT_TREE_ITEM_CHECKED, self.on_item_checked)
        self.GetMainWindow().Bind(wx.EVT_LEFT_DOWN, self.on_mouse_left_down)
        self.getIsItemCheckable = (
            parent.getIsItemCheckable
            if hasattr(parent, "getIsItemCheckable")
            else lambda item: True
        )
        self.get_is_item_checked = parent.get_is_item_checked
        self.get_item_parent_has_exclusive_children = (
            parent.get_item_parent_has_exclusive_children
        )

    def get_item_ct_type(self, domain_object):
        """Use radio buttons (ct_type == 2) when the object has "exclusive"
        children, meaning that only one child can be checked at a time. Use
        check boxes (ct_type == 1) otherwise."""
        if self.getIsItemCheckable(domain_object):
            return (
                2
                if self.get_item_parent_has_exclusive_children(domain_object)
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

    def on_mouse_left_down(self, event):
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

    def _refresh_object_completely(self, item, domain_object):
        super()._refresh_object_completely(item, domain_object)
        self._refresh_check_state(item, domain_object)

    def _refresh_object_minimally(self, item, domain_object):
        super()._refresh_object_minimally(item, domain_object)
        self._refresh_check_state(item, domain_object)

    def _refresh_check_state(self, item, domain_object):
        # Use CheckItem2 so no events get sent:
        checked = self.get_is_item_checked(domain_object)
        if checked is None:
            # Mixed state - enable 3-state and set undetermined
            item.Set3State(True)
            item.Set3StateValue(wx.CHK_UNDETERMINED)
        else:
            # Normal checked/unchecked state
            if item.Is3State():
                item.Set3State(False)
            self.CheckItem2(item, checked)
        parent = item.GetParent()
        while parent:
            if self.GetItemType(parent) == 2:
                self.EnableItem(item, self.IsItemChecked(parent))
                break
            parent = parent.GetParent()

    def refresh_all_check_states(self):
        """Refresh the check state of all items without rebuilding the tree."""
        for item in self.GetItemChildren(recursively=True):
            domain_object = self.GetItemPyData(item)
            if domain_object is not None:
                self._refresh_check_state(item, domain_object)

    def on_item_checked(self, event):
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

    def on_item_activated(self, event):
        if self.__is_double_clicked(event):
            # Invoke super.on_item_activated to edit the item
            super().on_item_activated(event)
        else:
            # Item is activated, let another event handler deal with the event
            event.Skip()

    @staticmethod
    def __is_double_clicked(event):
        return hasattr(event, "LeftDClick") and event.LeftDClick()
