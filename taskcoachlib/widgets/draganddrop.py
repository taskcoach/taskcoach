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
from taskcoachlib.meta.debug import log_step


def _link_cursor(window=None):
    """Get or create a link cursor for prereq/dep column drag."""
    from taskcoachlib.gui.icons.icon_library import icon_catalog

    return icon_catalog.get_cursor("synthetic_dnd_cursor_link", window)


def _home_cursor(window=None):
    """Get or create a home folder cursor for root drop locations."""
    from taskcoachlib.gui.icons.icon_library import icon_catalog

    return icon_catalog.get_cursor("synthetic_dnd_cursor_home", window)


def x11_drag_files():
    """The files the drag being dropped offers as `text/uri-list`,
    asked of its source; [] off GTK's X11 backend or without
    PyGObject. On X11 Thunderbird offers a message's URI as text before
    its .eml file, and wx takes the first format both sides know
    (docs/EMAIL_ATTACHMENTS.md, The Drop)."""
    try:
        import gi

        gi.require_version("Gdk", "3.0")
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gdk, GLib, Gtk
    except (ImportError, ValueError):
        return []
    display = Gdk.Display.get_default()
    if display is None or display.__gtype__.name != "GdkX11Display":
        return []
    drag = Gtk.Clipboard.get(Gdk.atom_intern("XdndSelection", False))
    if not drag.wait_is_uris_available():
        return []
    paths = []
    for uri in drag.wait_for_uris() or []:
        try:
            paths.append(GLib.filename_from_uri(uri)[0])
        except GLib.Error:
            pass  # Not a local file
    return paths


def not_allowed_cursor(window=None):
    """Task Coach's own "not allowed" cursor: wx's no-entry cursor is
    a skull where the cursor theme has no picture for it."""
    from taskcoachlib.gui.icons.icon_library import icon_catalog

    return icon_catalog.get_cursor("synthetic_cursor_not_allowed", window)


class DropTarget(wx.DropTarget):
    def __init__(
        self,
        on_drop_url,
        on_drop_files,
        on_drop_mail,
        on_drag_over_callback=None,
        on_drop_end=None,
    ):
        super().__init__()
        self.__on_drop_url = on_drop_url
        self.__on_drop_files = on_drop_files
        self.__on_drop_mail = on_drop_mail
        self.__on_drag_over_callback = on_drag_over_callback
        # After every drop, also one that hands nothing on
        self.__on_drop_end = on_drop_end
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
        if self.__on_drag_over_callback is None:
            return result
        self.__on_drag_over_callback(x, y, result)
        return wx.DragCopy

    def OnDrop(self, x, y):  # pylint: disable=W0613,W0221
        return True

    def OnData(self, x, y, result):  # pylint: disable=W0613
        self.GetData()
        self.dispatch(x, y, *self.get_received_format_type_and_id())
        self.reinit()
        if self.__on_drop_end:
            self.__on_drop_end()
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

    @staticmethod
    def __thunderbird_unreadable():
        # Once the drop returned: on Windows the mail program waits for
        # the drop to end
        patterns.later.soon(
            None,
            wx.MessageBox,
            thunderbird.unreadable(),
            _("Error"),
            wx.OK | wx.ICON_ERROR,
        )

    def on_outlook_drop(self, x, y):
        self.__drop_mails(x, y, outlook.get_current_selection())

    def on_mac_url_drop(self, x, y):
        url = bytes(self._url_data.GetData()).decode("utf-8", "replace")
        url = url.strip("\x00\r\n ")
        if thunderbird.is_mac_message_url(url):
            self.__thunderbird_unreadable()
        elif self.__on_drop_url:
            self.__on_drop_url(x, y, url)

    def on_url_drop(self, x, y):
        text = self._text_data.GetText()
        # Thunderbird drags its messages' URIs as text, on X11 with the
        # message's .eml file later in the drag
        if thunderbird.message_uris(text):
            mails = []
            for filename in x11_drag_files():
                mails.extend(mailer.dropped_mails(filename))
            log_step(
                "Thunderbird message dropped as its URI: %d mails read "
                "from the drag's files" % len(mails),
                prefix="MAIL",
            )
            if mails:
                self.__drop_mails(x, y, mails)
            else:
                self.__thunderbird_unreadable()
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

    def get_item_children(self, item=None, recursively=False):
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
                children.extend(self.get_item_children(child, True))
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

    You *must* implement on_drop. on_drop is called when the user has
    dropped an item on top of another item. It's up to you to decide how
    to handle the drop. If you are using this mixin together with the
    VirtualTree mixin, it makes sense to rearrange your underlying data
    and then call RefreshItems to let the virtual tree refresh itself."""

    def __init__(self, *args, **kwargs):
        kwargs["style"] = (
            kwargs.get("style", wx.TR_DEFAULT_STYLE) | wx.TR_HIDE_ROOT
        )
        self._validate_drag_callback = kwargs.pop("validate_drag", None)
        super().__init__(*args, **kwargs)
        patterns.later.soon(self, self.__safe_late_init)

    def __safe_late_init(self):
        """Safely perform late initialization, guarding against deleted C++ objects."""
        try:
            if self:
                self._late_init()
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def _late_init(self):
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.on_begin_drag)
        self._drag_start_pos = None
        self.GetMainWindow().Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
        self._drag_items = []

    def on_drop(self, drop_item, drag_items, part, column):
        """Overridden by the derived class: drag_items, the items the
        user dragged, are dropped on drop_item, the (hidden) root item
        when not dropped on another item.

        By column:
        - Prerequisites: drag_items become prerequisites of drop_item
        - Dependencies: drag_items become dependencies of drop_item
        - Others: drag_items become children of drop_item
        - The header: drag_items become root tasks
        """
        raise NotImplementedError

    def on_begin_drag(self, event):
        """This method is called when the drag starts. It either allows the
        drag and starts it or it vetoes the drag when the the root item is one
        of the dragged items."""
        column = self._column_hit_test(self._drag_start_pos)
        selections = self.GetSelections()
        self._drag_items = (
            selections[:]
            if selections
            else [event.GetItem()] if event.GetItem() else []
        )
        self._drag_column = column
        if self._drag_items and (self.GetRootItem() not in self._drag_items):
            self.start_dragging()
            event.Allow()
        else:
            event.Veto()

    def _on_left_down(self, event):
        # event.GetPoint() in on_begin_drag is totally off.
        self._drag_start_pos = wx.Point(event.GetX(), event.GetY())
        event.Skip()

    def _column_hit_test(self, point):
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

    def on_end_drag(self, event):
        self.stop_dragging()
        # Use HitTest to determine actual drop target, not event.GetItem()
        # which may return the last highlighted item even when outside
        hit_item, flags, drop_column = self.HitTest(event.GetPoint())

        # Check if drop is outside items (left, right, above, below, or nowhere)
        outside_flags = (
            wx.TREE_HITTEST_TOLEFT
            | wx.TREE_HITTEST_TORIGHT
            | wx.TREE_HITTEST_ABOVE
            | wx.TREE_HITTEST_BELOW
            | wx.TREE_HITTEST_NOWHERE
        )
        if not hit_item or (flags & outside_flags):
            # Drop outside items - make root task
            drop_target = self.GetRootItem()
        else:
            drop_target = hit_item

        if self.is_valid_drop_target(drop_target):
            # The drop target is not selected: as the current row it
            # would take the button's release for a second click on it,
            # which opens the editor of the row current by then
            part = 0
            if flags & wx.TREE_HITTEST_ONITEMUPPERPART:
                part = -1
            elif flags & wx.TREE_HITTEST_ONITEMLOWERPART:
                part = 1
            # The drop point's column: HitTest() can give -1 for
            # narrow columns
            actual_drop_column = self._column_hit_test(event.GetPoint())
            self.on_drop(
                drop_target, self._drag_items, part, actual_drop_column
            )
        else:
            # Work around an issue with HyperTreeList. HyperTreeList will
            # restore the selection to the last item highlighted by the drag,
            # after we have processed the end drag event. That's not what we
            # want, so clear the selection later, after
            # HyperTreeList did its (wrong) thing and reselect the previously
            # dragged item.
            patterns.later.soon(
                self, self.__safe_select, self.__dragged_objects()
            )
        self._drag_items = []

    def __safe_select(self, items):
        """Safely call select, guarding against deleted C++ objects."""
        try:
            if self:
                self.select(items)
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def select_dragged_items(self):
        self.select(self.__dragged_objects())

    def __dragged_objects(self):
        """The dragged rows' objects, which select() takes."""
        return [self.GetItemPyData(item) for item in self._drag_items]

    def on_dragging(self, event):
        if not event.Dragging():
            self.stop_dragging()
            return
        point = wx.Point(event.GetX(), event.GetY())
        item, flags, column = self.HitTest(point)
        is_root_drop = not item or item == self.GetRootItem()
        if not item:
            item = self.GetRootItem()
        if self.is_valid_drop_target(item):
            # Use appropriate cursor based on drop location
            if is_root_drop:
                self.set_cursor_to_home()
            elif self._is_prereq_or_dep_column(column):
                self.set_cursor_to_link()
            else:
                self.set_cursor_to_dragging()
        else:
            self.set_cursor_to_dropping_impossible()
        # Auto-expand collapsed items on hover (modern UX behavior)
        hover_expander(self).hover(item, flags)
        if self.GetSelections() != [item]:
            self.UnselectAll()
            if item != self.GetRootItem():
                self.SelectItem(item)
        event.Skip()

    def start_dragging(self):
        self.GetMainWindow().Bind(wx.EVT_MOTION, self.on_dragging)
        self.GetMainWindow().Bind(wx.EVT_KEY_DOWN, self.on_key_during_drag)
        self.Bind(wx.EVT_TREE_END_DRAG, self.on_end_drag)
        # Also bind to header window for header drops
        header_win = self.GetHeaderWindow()
        if header_win:
            header_win.Bind(wx.EVT_MOTION, self.on_dragging_over_header)
            header_win.Bind(wx.EVT_LEFT_UP, self.on_drop_on_header)
        self.set_cursor_to_dragging()

    def stop_dragging(self):
        self.GetMainWindow().Unbind(wx.EVT_MOTION)
        self.GetMainWindow().Unbind(wx.EVT_KEY_DOWN)
        self.Unbind(wx.EVT_TREE_END_DRAG)
        # Unbind the header's handlers of the drag only: the header has
        # its own, the columns' move among them
        header_win = self.GetHeaderWindow()
        if header_win:
            header_win.Unbind(
                wx.EVT_MOTION, handler=self.on_dragging_over_header
            )
            header_win.Unbind(wx.EVT_LEFT_UP, handler=self.on_drop_on_header)
        # Cancel any pending hover-expand
        hover_expander(self).stop()
        # Clean up HyperTreeList's internal drag state
        main_win = self.GetMainWindow()
        if hasattr(main_win, "_dragImage") and main_win._dragImage:
            main_win._dragImage.EndDrag()
            main_win._dragImage = None
        if hasattr(main_win, "_isDragging"):
            main_win._isDragging = False
        self.reset_cursor()
        self._reset_header_cursor()
        self.select_dragged_items()
        # Refresh to clear any visual artifacts
        main_win.Refresh()

    def on_key_during_drag(self, event):
        """Handle key presses during drag - Escape cancels the operation."""
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.stop_dragging()
            self._drag_items = []
        else:
            event.Skip()

    def set_cursor_to_dragging(self):
        self.GetMainWindow().SetCursor(wx.Cursor(wx.CURSOR_HAND))

    def set_cursor_to_link(self):
        """Set cursor to link icon when over prereq/dep columns."""
        self.GetMainWindow().SetCursor(_link_cursor(self.GetMainWindow()))

    def set_cursor_to_home(self):
        """Set cursor to home folder icon when over root drop locations."""
        self.GetMainWindow().SetCursor(_home_cursor(self.GetMainWindow()))

    def set_cursor_to_dropping_impossible(self):
        self.GetMainWindow().SetCursor(
            not_allowed_cursor(self.GetMainWindow())
        )

    def reset_cursor(self):
        self.GetMainWindow().SetCursor(wx.NullCursor)

    def _reset_header_cursor(self):
        """Reset cursor on header window."""
        header_win = self.GetHeaderWindow()
        if header_win:
            header_win.SetCursor(wx.NullCursor)

    def on_dragging_over_header(self, event):
        """Handle mouse motion over the header window during dragging."""
        if not self._drag_items:
            event.Skip()
            return
        # Show home folder cursor when over header (indicates root drop)
        header_win = self.GetHeaderWindow()
        if header_win:
            header_win.SetCursor(_home_cursor(header_win))
        event.Skip()

    def on_drop_on_header(self, event):
        """Handle drop on the header window - makes task a root task."""
        if not self._drag_items:
            event.Skip()
            return

        # Get the column under the mouse
        header_win = self.GetHeaderWindow()
        if not header_win:
            event.Skip()
            return

        x, _ = self.CalcUnscrolledPosition(event.GetX(), 0)
        column = header_win.XToCol(x)

        # Only the main column, the subject's, wherever it was moved,
        # makes the task a root task
        if column == self.GetMainWindow().GetMainColumn():
            # Make tasks root tasks by dropping on hidden root
            drop_target = self.GetRootItem()
            self.on_drop(drop_target, self._drag_items, 0, 0)

        self.stop_dragging()
        self._drag_items = []
        event.Skip()

    def _is_prereq_or_dep_column(self, column):
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

    def is_valid_drop_target(self, drop_target):
        if self._validate_drag_callback is not None:
            is_valid = self._validate_drag_callback(
                self.GetItemPyData(drop_target),
                [self.GetItemPyData(item) for item in self._drag_items],
                self._drag_column,
            )
            if is_valid is not None:
                return is_valid

        if drop_target:
            # Dropping on hidden root is always valid (makes items root-level)
            if drop_target == self.GetRootItem():
                return True
            invalid_drop_targets = set(self._drag_items)
            invalid_drop_targets |= set(
                self.GetItemParent(item) for item in self._drag_items
            )
            for item in self._drag_items:
                invalid_drop_targets |= set(
                    self.get_item_children(item, recursively=True)
                )
            return drop_target not in invalid_drop_targets
        else:
            return True
