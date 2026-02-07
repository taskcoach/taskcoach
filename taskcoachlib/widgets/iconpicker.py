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
import wx.lib.buttons as buttons

from taskcoachlib.meta.debug import log_step


class _IconListCtrl(wx.ListCtrl):
    """List control with 3 columns: Name (with icon), Hints, Internal."""

    ICON_SIZE = 16

    def __init__(self, parent):
        super().__init__(parent, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_NONE)

        # Image list for icons
        self._image_list = wx.ImageList(self.ICON_SIZE, self.ICON_SIZE)
        self.SetImageList(self._image_list, wx.IMAGE_LIST_SMALL)

        # 3 columns: Name (with icon), Hints, Internal
        self.InsertColumn(0, _("Name"), width=200)
        self.InsertColumn(1, _("Hints"), width=300)
        self.InsertColumn(2, _("Internal"), width=100)

        self._items = []
        self._all_items = []
        self._image_map = {}  # key -> image list index
        self._on_select_callback = None

        # Debounce timer for search filtering
        self._filter_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_filter_timer, self._filter_timer)
        self._pending_filter = ""

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_item_activated)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

    def SetItems(self, items):
        """Set items: list of (key, label, bitmap, hints, enabled) tuples."""
        self._all_items = list(items)
        self._items = list(items)
        self._rebuild_list()

    def _rebuild_list(self):
        """Rebuild the list from current _items."""
        self.DeleteAllItems()

        for i, item in enumerate(self._items):
            key, label, bmp, hints, enabled = item

            # Add bitmap to image list if not already there
            if key not in self._image_map:
                if bmp and bmp.IsOk():
                    if not enabled:
                        # Greyscale for disabled items
                        img = bmp.ConvertToImage().ConvertToGreyscale()
                        idx = self._image_list.Add(img.ConvertToBitmap())
                    else:
                        idx = self._image_list.Add(bmp)
                else:
                    idx = -1  # No image
                self._image_map[key] = idx

            # Insert row: Name (with icon), Hints, Internal
            idx = self.InsertItem(i, label, self._image_map.get(key, -1))
            self.SetItem(idx, 1, hints or "")
            self.SetItem(idx, 2, key)

            # Grey out disabled items
            if not enabled:
                self.SetItemTextColour(idx, wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

    def FilterItems(self, filter_text):
        """Start debounced filter - waits 300ms after last keystroke."""
        self._pending_filter = filter_text
        self._filter_timer.Stop()
        self._filter_timer.Start(300, oneShot=True)

    def _on_filter_timer(self, event):
        """Execute the actual filter after debounce delay."""
        filter_text = self._pending_filter
        if not filter_text:
            self._items = list(self._all_items)
        else:
            # Split into terms - ANY term matches (OR search)
            terms = filter_text.lower().split()
            self._items = [
                item for item in self._all_items
                if self._matches_any_term(item, terms)
            ]
        self._rebuild_list()

        # Select first enabled item
        for i, item in enumerate(self._items):
            if item[4]:  # enabled
                self.Select(i)
                self.EnsureVisible(i)
                break

    def _matches_any_term(self, item, terms):
        """Return True if ANY term is found in item's label, hints, or key (OR search)."""
        key = item[0].lower()
        label = item[1].lower()
        hints = item[3].lower()
        searchable = key + " " + label + " " + hints
        return any(term in searchable for term in terms)

    def GetSelectedItem(self):
        """Return the selected item tuple, or None."""
        sel = self.GetFirstSelected()
        if sel != -1 and 0 <= sel < len(self._items):
            return self._items[sel]
        return None

    def SelectByKey(self, key):
        """Select item by key."""
        for i, item in enumerate(self._items):
            if item[0] == key:
                self.Select(i)
                self.EnsureVisible(i)
                return

    def SetSelectCallback(self, callback):
        """Set callback for double-click/enter selection."""
        self._on_select_callback = callback

    def _on_item_activated(self, event):
        """Handle double-click or enter on item."""
        item = self.GetSelectedItem()
        if item and item[4] and self._on_select_callback:  # enabled
            self._on_select_callback(*item)

    def _on_key_down(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_RETURN or key == wx.WXK_NUMPAD_ENTER:
            item = self.GetSelectedItem()
            if item and item[4] and self._on_select_callback:  # enabled
                self._on_select_callback(*item)
        else:
            event.Skip()


class _IconDialog(wx.Dialog):
    """Modal dialog with searchable icon list."""

    def __init__(self, parent, items, current_key):
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        super().__init__(parent, title=_("Choose Icon"), style=style)
        self._selected_item = None

        panel = wx.Panel(self, style=wx.BORDER_NONE | wx.TAB_TRAVERSAL)
        panel.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))

        sizer = wx.BoxSizer(wx.VERTICAL)
        self._search = wx.SearchCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self._search.SetDescriptiveText(_("Search icons..."))
        self._search.ShowCancelButton(True)
        sizer.Add(self._search, 0, wx.EXPAND | wx.ALL, 5)

        self._listbox = _IconListCtrl(panel)
        self._listbox.SetItems(items)
        self._listbox.SetSelectCallback(self._on_item_selected)
        sizer.Add(self._listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        panel.SetSizer(sizer)

        # Dialog layout: panel (search + list) + button bar
        dlgSizer = wx.BoxSizer(wx.VERTICAL)
        dlgSizer.Add(panel, 1, wx.EXPAND)

        # Button bar: Clear + OK + Cancel (all in standard sizer for consistent padding)
        btnSizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        self._clearBtn = wx.Button(self, wx.ID_CLEAR, _("Clear"))
        # Insert Clear at the beginning (index 0)
        btnSizer.Insert(0, self._clearBtn, 0, wx.LEFT | wx.RIGHT, 5)
        btnSizer.Insert(1, (0, 0), 1)  # Stretch spacer after Clear
        dlgSizer.Add(btnSizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(dlgSizer)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._on_clear, id=wx.ID_CLEAR)

        # Dialog size: fixed width, 75% of screen height
        display = wx.Display(wx.Display.GetFromWindow(parent))
        screen_height = display.GetClientArea().GetHeight()
        total_height = int(screen_height * 0.75)

        self._desired_size = wx.Size(600, total_height)

        def _on_shown(evt):
            self.SetSize(self._desired_size)
            self.CentreOnParent()
            evt.Skip()
        self.Bind(wx.EVT_SHOW, _on_shown)

        self._listbox.SelectByKey(current_key)

        self._search.Bind(wx.EVT_TEXT, lambda e: self._listbox.FilterItems(self._search.GetValue()))
        self._search.Bind(wx.EVT_TEXT_ENTER, self._on_enter)
        self._search.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self._search.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self._on_cancel)

        wx.CallAfter(self._focus_search)

    def _focus_search(self):
        if self._search and self.IsShown():
            self._search.SetFocus()
            self._search.SetInsertionPoint(0)

    def GetSelectedItem(self):
        return self._selected_item

    def _on_cancel(self, event):
        self._search.SetValue("")
        self._listbox.FilterItems("")

    def _on_enter(self, event):
        item = self._listbox.GetSelectedItem()
        if item and item[4]:  # enabled
            self._on_item_selected(*item)

    def _on_key(self, event):
        key = event.GetKeyCode()
        if key in (wx.WXK_DOWN, wx.WXK_UP):
            self._listbox._on_key_down(event)
        elif key == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
        else:
            event.Skip()

    def _on_ok(self, event):
        """OK button — confirm the currently highlighted item."""
        item = self._listbox.GetSelectedItem()
        if item and item[4]:  # enabled
            self._selected_item = item
            self.EndModal(wx.ID_OK)
        # If nothing valid selected, don't close

    def _on_clear(self, event):
        """Clear button — select no icon."""
        self._selected_item = ("", _("No icon"), None, "", True)
        self.EndModal(wx.ID_OK)

    def _on_item_selected(self, key, label, bmp, hints, enabled):
        if enabled:
            self._selected_item = (key, label, bmp, hints, enabled)
            self.EndModal(wx.ID_OK)


class IconPicker(buttons.ThemedGenBitmapTextButton):
    """Searchable icon picker button.

    A themed button that displays the selected icon and label. Clicking opens
    a modal dialog with a searchable list of all available icons.

    The button always displays with active/enabled appearance, even when
    "No icon" is selected. A transparent placeholder bitmap is required because
    GenBitmapButton.SetBitmapLabel() calls bitmap.ConvertToImage() which fails
    on wx.NullBitmap.

    Args:
        parent: Parent window
        currentIcon: Currently selected icon key (empty string for "No icon")
        excluded_icons: Set of icon keys to disable in the list
        noIcon: If True, include "No icon" as the first item (default: True)
    """

    PADDING = 8
    ICON_SIZE = 16  # Standard icon size for layout consistency
    NO_ICON_LABEL = _("No icon")

    def __init__(self, parent, currentIcon, excluded_icons=None, noIcon=True, fixedWidth=None, *args, **kwargs):
        self._excluded_icons = excluded_icons or set()
        self._noIcon = noIcon
        self._fixedWidth = fixedWidth
        self._items = []
        self._items_dict = {}
        self._current_key = ""
        self._current_label = ""
        self._current_bmp = None
        self._previous_key = ""

        # Initialize button - GenBitmapButton requires a bitmap in constructor,
        # but we immediately clear it. For "no icon" state, bmpLabel stays None.
        # Never call SetBitmapLabel(None) - that hits wxPython bug #2093.
        super().__init__(parent, wx.ID_ANY, wx.Bitmap(1, 1), "", style=wx.BORDER_NONE)
        self.bmpLabel = None  # Clear - start with no icon
        self.SetUseFocusIndicator(True)

        self._load_icons()
        self._setSelectionByValue(currentIcon or "")
        self._previous_key = self._current_key

        self.Bind(wx.EVT_BUTTON, self._on_click)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

    def _load_icons(self):
        """Load icons from artprovider."""
        # Import here to avoid circular import (widgets <- gui <- widgets)
        from taskcoachlib.gui import artprovider

        # Note: "No icon" is handled via Clear button in dialog, not in list

        # Load icons from artprovider.chooseableItems
        # Sort by name for consistent ordering
        image_names = sorted(
            artprovider.chooseableItems.keys(),
            key=lambda k: artprovider.chooseableItems[k]["name"]
        )
        size = (16, 16)
        for image_name in image_names:
            item_data = artprovider.chooseableItems[image_name]
            label = item_data["name"]
            bitmap = wx.ArtProvider.GetBitmap(image_name, wx.ART_MENU, size)
            # Join hints array into space-separated string for search
            hints = " ".join(item_data.get("hints", []))
            enabled = image_name not in self._excluded_icons
            item = (image_name, label, bitmap, hints, enabled)
            self._items.append(item)
            self._items_dict[image_name] = item

    def _on_key_down(self, event):
        key = event.GetKeyCode()
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._on_click(event)
        else:
            event.Skip()

    def DrawFocusIndicator(self, dc, w, h):
        rect = wx.Rect(3, 3, w - 6, h - 6)
        wx.RendererNative.Get().DrawFocusRect(self, dc, rect)

    def SetBitmapLabel(self, bitmap, createOthers=True):
        """Set bitmap label. Passing None/invalid bitmap is an error.

        For "no icon" state, set bmpLabel=None directly instead of calling this.
        This avoids wxPython bug #2093 where GenBitmapButton crashes on NullBitmap.
        """
        if bitmap is None or not bitmap.IsOk():
            log_step("ERROR: SetBitmapLabel called with invalid bitmap - use bmpLabel=None instead",
                     prefix="ICON")
            return  # Ignore the call, don't crash
        super().SetBitmapLabel(bitmap, createOthers)

    def _get_icon_size(self):
        """Return (width, height) of current icon, or (0, 0) if no icon."""
        if self.bmpLabel and self.bmpLabel.IsOk():
            return self.bmpLabel.GetWidth(), self.bmpLabel.GetHeight()
        return 0, 0

    def _get_layout_metrics(self):
        """Return layout metrics for button content.

        Returns (text_start_x, non_text_width, icon_size) where:
        - text_start_x: x position where text drawing starts
        - non_text_width: total width used by padding and icon (for width calculations)
        - icon_size: (width, height) of icon, or (0, 0) if none
        """
        bw, bh = self._get_icon_size()
        if bw > 0:
            text_x = self.PADDING + bw + self.PADDING
            overhead = bw + self.PADDING * 3
        else:
            text_x = self.PADDING
            overhead = self.PADDING * 2
        return text_x, overhead, (bw, bh)

    def _set_current(self, item):
        self._current_key = item[0]
        self._current_label = item[1]
        self._current_bmp = item[2]
        self._update_button()

    def _update_button(self):
        self.SetLabel(self._current_label)
        if self._current_bmp and self._current_bmp.IsOk():
            self.SetBitmapLabel(self._current_bmp)
        else:
            # No icon - set internal state directly, never call SetBitmapLabel(None)
            # This avoids wxPython bug #2093
            self.bmpLabel = None
            self.bmpDisabled = None
            self.bmpFocus = None
            self.bmpSelected = None
        if not self._fixedWidth:
            self.InvalidateBestSize()
            self.SetInitialSize()
            parent = self.GetParent()
            while parent and not isinstance(parent, wx.TopLevelWindow):
                parent.Layout()
                parent = parent.GetParent()
        self.Refresh()

    def DrawLabel(self, dc, width, height, dx=0, dy=0):
        text_x, overhead, (bw, bh) = self._get_layout_metrics()

        # Get the appropriate bitmap for current state
        bmp = self.bmpLabel
        if bmp and bmp.IsOk():
            if self.bmpDisabled and not self.IsEnabled():
                bmp = self.bmpDisabled
            if self.bmpFocus and self.hasFocus:
                bmp = self.bmpFocus
            if self.bmpSelected and not self.up:
                bmp = self.bmpSelected
            hasMask = bmp.GetMask() is not None
        else:
            hasMask = False

        if not self.up:
            dx = dy = self.labelDelta

        dc.SetFont(self.GetFont())
        if self.IsEnabled():
            dc.SetTextForeground(self.GetForegroundColour())
        else:
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        label = self.GetLabel()
        available_width = width - overhead
        if available_width > 0:
            label = wx.Control.Ellipsize(label, dc, wx.ELLIPSIZE_END, available_width)

        tw, th = dc.GetTextExtent(label)

        # Draw icon if present
        if bw > 0 and bmp:
            dc.DrawBitmap(bmp, self.PADDING + dx, (height - bh) // 2 + dy, hasMask)

        dc.DrawText(label, text_x + dx, (height - th) // 2 + dy)

    def DoGetBestSize(self):
        _, overhead, (bw, bh) = self._get_layout_metrics()
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        tw, th = dc.GetTextExtent(self.GetLabel())
        height = max(th, bh) + self.PADDING * 2 if bh > 0 else th + self.PADDING * 2
        if self._fixedWidth:
            return wx.Size(self._fixedWidth, height)
        return wx.Size(overhead + tw, height)

    def _on_click(self, event):
        dialog = _IconDialog(self.GetTopLevelParent(), self._items, self._current_key)
        if dialog.ShowModal() == wx.ID_OK:
            item = dialog.GetSelectedItem()
            if item and item[4]:  # enabled
                self._previous_key = self._current_key
                self._set_current(item)
                evt = wx.CommandEvent(wx.wxEVT_COMBOBOX, self.GetId())
                evt.SetEventObject(self)
                evt.SetString(item[1])
                self.GetEventHandler().ProcessEvent(evt)
        dialog.Destroy()

    def GetValue(self):
        """Return the selected icon key."""
        return self._current_key

    def SetValue(self, newValue):
        """Set selection by icon key."""
        self._setSelectionByValue(newValue)

    def _setSelectionByValue(self, newValue):
        if newValue == "" and self._noIcon:
            # No icon selected - create item tuple directly
            self._set_current(("", self.NO_ICON_LABEL, None, "", True))
        elif newValue in self._items_dict:
            self._set_current(self._items_dict[newValue])
        elif self._items:
            self._set_current(self._items[0])


def _(text):
    """Placeholder for i18n - will use the actual translation function."""
    return text
