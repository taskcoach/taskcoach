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


class _IconVListBox(wx.VListBox):
    """Virtual list box with icon, label, and hints columns."""

    ICON_SIZE = 16
    ITEM_HEIGHT = 24
    PADDING = 4

    def __init__(self, parent):
        super().__init__(parent, style=wx.BORDER_NONE | wx.WANTS_CHARS | wx.TAB_TRAVERSAL | wx.VSCROLL)
        self._items = []
        self._all_items = []
        self._on_select_callback = None
        self._max_label_width = 100
        self._max_hints_width = 100
        self._total_width = 300
        self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOX))
        self.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
        self.Bind(wx.EVT_LEFT_DCLICK, self._on_left_dclick)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)
        self.Bind(wx.EVT_MOTION, self._on_motion)

    def SetItems(self, items):
        """Set items: list of (key, label, bitmap, hints, enabled) tuples."""
        self._all_items = list(items)
        self._items = list(items)
        self._calculate_column_widths()
        self.SetItemCount(len(self._items))
        self.Refresh()

    def _calculate_column_widths(self):
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        max_label = 0
        max_hints = 0
        for item in self._all_items:
            label_width = dc.GetTextExtent(item[1])[0]
            hints_width = dc.GetTextExtent(item[3])[0] if item[3] else 0
            max_label = max(max_label, label_width)
            max_hints = max(max_hints, hints_width)
        self._max_label_width = max_label + 10
        self._max_hints_width = max_hints + 10
        self._total_width = (self.PADDING + self.ICON_SIZE + self.PADDING +
                             self._max_label_width + self.PADDING +
                             self._max_hints_width + self.PADDING)

    def GetPreferredWidth(self):
        return self._total_width

    def FilterItems(self, filter_text):
        if not filter_text:
            self._items = list(self._all_items)
        else:
            lower = filter_text.lower()
            self._items = [
                item for item in self._all_items
                if lower in item[1].lower() or lower in item[3].lower()
            ]
        self.SetItemCount(len(self._items))
        for i, item in enumerate(self._items):
            if item[4]:  # enabled
                self.SetSelection(i)
                break
        else:
            self.SetSelection(wx.NOT_FOUND)
        self.RefreshAll()

    def GetSelectedItem(self):
        sel = self.GetSelection()
        if sel != wx.NOT_FOUND and 0 <= sel < len(self._items):
            return self._items[sel]
        return None

    def SelectByKey(self, key):
        for i, item in enumerate(self._items):
            if item[0] == key:
                self.SetSelection(i)
                return

    def SetSelectCallback(self, callback):
        self._on_select_callback = callback

    def _find_next_enabled(self, start, direction=1):
        i = start
        while 0 <= i < len(self._items):
            if self._items[i][4]:  # enabled is index 4 now
                return i
            i += direction
        return None

    def OnMeasureItem(self, n):
        return self.ITEM_HEIGHT

    def OnDrawItem(self, dc, rect, n):
        if n < 0 or n >= len(self._items):
            return
        key, label, bmp, hints, enabled = self._items[n]
        is_selected = self.IsSelected(n)

        # Get theme colors based on state
        if not enabled:
            text_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
            hints_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        elif is_selected:
            text_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
            hints_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        else:
            text_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOXTEXT)
            hints_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)

        # Draw icon
        x = rect.x + self.PADDING
        if bmp and bmp.IsOk():
            bmp_y = rect.y + (rect.height - bmp.GetHeight()) // 2
            if not enabled:
                img = bmp.ConvertToImage().ConvertToGreyscale()
                dc.DrawBitmap(img.ConvertToBitmap(), x, bmp_y, True)
            else:
                dc.DrawBitmap(bmp, x, bmp_y, True)

        # Draw label
        label_x = x + self.ICON_SIZE + self.PADDING
        text_y = rect.y + (rect.height - dc.GetCharHeight()) // 2
        dc.SetTextForeground(text_color)
        display_label = wx.Control.Ellipsize(label, dc, wx.ELLIPSIZE_END, self._max_label_width)
        dc.DrawText(display_label, label_x, text_y)

        # Draw hints (grey, after label column)
        if hints:
            hints_x = label_x + self._max_label_width + self.PADDING
            dc.SetTextForeground(hints_color)
            display_hints = wx.Control.Ellipsize(hints, dc, wx.ELLIPSIZE_END, self._max_hints_width)
            dc.DrawText(display_hints, hints_x, text_y)

    def OnDrawBackground(self, dc, rect, n):
        if n < 0 or n >= len(self._items):
            return
        is_selected = self.IsSelected(n)
        bg_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOX)
        dc.SetBrush(wx.Brush(bg_color))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(rect)
        if is_selected:
            highlight = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
            dc.SetBrush(wx.Brush(highlight))
            dc.DrawRectangle(rect)

    def _on_left_down(self, event):
        item_idx = self.VirtualHitTest(event.GetPosition().y)
        if item_idx != wx.NOT_FOUND and 0 <= item_idx < len(self._items):
            item = self._items[item_idx]
            if item[4]:  # enabled
                self.SetSelection(item_idx)
                if self._on_select_callback:
                    self._on_select_callback(*item)
        event.Skip()

    def _on_left_dclick(self, event):
        self._on_left_down(event)

    def _on_key_down(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_RETURN or key == wx.WXK_NUMPAD_ENTER:
            sel = self.GetSelection()
            if sel != wx.NOT_FOUND and 0 <= sel < len(self._items):
                item = self._items[sel]
                if item[4] and self._on_select_callback:
                    self._on_select_callback(*item)
        elif key == wx.WXK_DOWN:
            sel = self.GetSelection()
            next_idx = self._find_next_enabled(sel + 1 if sel != wx.NOT_FOUND else 0, 1)
            if next_idx is not None:
                self.SetSelection(next_idx)
                self.Refresh()
        elif key == wx.WXK_UP:
            sel = self.GetSelection()
            if sel == wx.NOT_FOUND:
                sel = len(self._items)
            prev_idx = self._find_next_enabled(sel - 1, -1)
            if prev_idx is not None:
                self.SetSelection(prev_idx)
                self.Refresh()
        else:
            event.Skip()

    def _on_motion(self, event):
        item_idx = self.VirtualHitTest(event.GetPosition().y)
        if item_idx != wx.NOT_FOUND and 0 <= item_idx < len(self._items):
            if self._items[item_idx][4]:  # enabled
                if item_idx != self.GetSelection():
                    self.SetSelection(item_idx)
                    self.Refresh()
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

        self._listbox = _IconVListBox(panel)
        self._listbox.SetItems(items)
        self._listbox.SetSelectCallback(self._on_item_selected)
        sizer.Add(self._listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        panel.SetSizer(sizer)

        # Dialog layout: panel (search + list) + button bar
        dlgSizer = wx.BoxSizer(wx.VERTICAL)
        dlgSizer.Add(panel, 1, wx.EXPAND)
        btnSizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        if btnSizer:
            dlgSizer.Add(btnSizer, 0, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(dlgSizer)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

        # Calculate dialog size - show all items, limited by screen height
        list_height = len(items) * _IconVListBox.ITEM_HEIGHT
        search_height = self._search.GetBestSize().GetHeight() + 12
        btn_height = 40  # OK/Cancel button bar + padding
        content_width = self._listbox.GetPreferredWidth() + 24
        total_height = search_height + list_height + btn_height + 16

        # Limit to 75% of screen height
        display = wx.Display(wx.Display.GetFromWindow(parent))
        screen_height = display.GetClientArea().GetHeight()
        max_height = int(screen_height * 0.75)
        total_height = min(total_height, max_height)

        self._desired_size = wx.Size(content_width, total_height)

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

        # Create transparent placeholder bitmap for "No icon" state.
        # Required because GenBitmapButton.SetBitmapLabel() calls ConvertToImage()
        # which fails on wx.NullBitmap with "invalid bitmap" assertion.
        self._empty_bmp = wx.Bitmap(self.ICON_SIZE, self.ICON_SIZE, 32)
        self._empty_bmp.UseAlpha()
        dc = wx.MemoryDC(self._empty_bmp)
        dc.SetBackground(wx.Brush(wx.Colour(0, 0, 0, 0)))
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)

        # Initialize with placeholder bitmap
        super().__init__(parent, wx.ID_ANY, self._empty_bmp, "", style=wx.BORDER_NONE)
        self.SetUseFocusIndicator(True)

        self._load_icons()
        self._setSelectionByValue(currentIcon or "")
        self._previous_key = self._current_key

        self.Bind(wx.EVT_BUTTON, self._on_click)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

    def _load_icons(self):
        """Load icons from artprovider.

        If noIcon=True, "No icon" is added as the first item with key="".
        """
        # Import here to avoid circular import (widgets <- gui <- widgets)
        from taskcoachlib.gui import artprovider

        # Add "No icon" as first item if enabled
        if self._noIcon:
            no_icon_item = ("", self.NO_ICON_LABEL, self._empty_bmp, "", True)
            self._items.append(no_icon_item)
            self._items_dict[""] = no_icon_item

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
            # Use placeholder bitmap for "No icon" - required by GenBitmapButton
            self.SetBitmapLabel(self._empty_bmp)
        if not self._fixedWidth:
            self.InvalidateBestSize()
            self.SetInitialSize()
            parent = self.GetParent()
            while parent and not isinstance(parent, wx.TopLevelWindow):
                parent.Layout()
                parent = parent.GetParent()
        self.Refresh()

    def DrawLabel(self, dc, width, height, dx=0, dy=0):
        # Always reserve ICON_SIZE space for consistent layout
        bmp = self.bmpLabel
        has_valid_bmp = bmp is not None and bmp.IsOk()

        if has_valid_bmp:
            if self.bmpDisabled and not self.IsEnabled():
                bmp = self.bmpDisabled
            if self.bmpFocus and self.hasFocus:
                bmp = self.bmpFocus
            if self.bmpSelected and not self.up:
                bmp = self.bmpSelected
            bw, bh = bmp.GetWidth(), bmp.GetHeight()
            hasMask = bmp.GetMask() is not None
        else:
            # No icon, but still reserve space for consistent layout
            bw, bh = self.ICON_SIZE, self.ICON_SIZE
            hasMask = False

        if not self.up:
            dx = dy = self.labelDelta

        dc.SetFont(self.GetFont())
        if self.IsEnabled():
            dc.SetTextForeground(self.GetForegroundColour())
        else:
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        label = self.GetLabel()
        available_width = width - bw - self.PADDING * 3
        if available_width > 0:
            label = wx.Control.Ellipsize(label, dc, wx.ELLIPSIZE_END, available_width)

        tw, th = dc.GetTextExtent(label)

        # Draw icon if present
        pos_x = self.PADDING + dx
        if has_valid_bmp:
            dc.DrawBitmap(bmp, pos_x, (height - bh) // 2 + dy, hasMask)
        # Always advance past icon space for consistent text positioning
        pos_x += bw + self.PADDING

        dc.DrawText(label, pos_x, (height - th) // 2 + dy)

    def DoGetBestSize(self):
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        label = self.GetLabel()
        tw, th = dc.GetTextExtent(label)
        # Always include ICON_SIZE for consistent button size
        bw, bh = self.ICON_SIZE, self.ICON_SIZE
        if self.bmpLabel and self.bmpLabel.IsOk():
            bw, bh = self.bmpLabel.GetWidth(), self.bmpLabel.GetHeight()
        height = max(th, bh) + self.PADDING * 2
        if self._fixedWidth:
            return wx.Size(self._fixedWidth, height)
        width = self.PADDING + bw + self.PADDING + tw + self.PADDING
        return wx.Size(width, height)

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
        if newValue in self._items_dict:
            self._set_current(self._items_dict[newValue])
        elif self._items:
            self._set_current(self._items[0])


def _(text):
    """Placeholder for i18n - will use the actual translation function."""
    return text
