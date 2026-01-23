"""
Demo: Searchable Icon Chooser with proper scrollbar

Best practice approach:
    wx.ComboCtrl + wx.ComboPopup containing:
        - wx.SearchCtrl (substring filter)
        - Custom wx.VListBox (virtual scrollable list with bitmap+text drawing)

This gives:
    - Real scrollbar (VListBox has native scrolling)
    - Substring search
    - Custom bitmap+text rendering via OnDrawItem
    - Good performance (virtual list, no per-item widgets)

References:
    - wx.VListBox: https://docs.wxpython.org/wx.VListBox.html
    - wx.ComboCtrl: https://docs.wxpython.org/wx.ComboCtrl.html
    - wx.ComboPopup: https://docs.wxpython.org/wx.ComboPopup.html
    - Phoenix VListBox demo: https://github.com/wxWidgets/Phoenix/blob/master/demo/VListBox.py

Run from the taskcoach root:
    python3 dev_demos/icon_chooser_demo.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wx
import wx.adv


# --- Helpers ---

def get_icons_dir():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "taskcoachlib", "gui", "icons"
    )


def load_icon_data():
    """Load chooseable icon names and their 16x16 bitmaps."""
    icons_dir = get_icons_dir()
    icon_labels = {
        "arrow_down_icon": "Arrow - Down",
        "arrow_forward_icon": "Arrow - Forward",
        "arrows_looped_blue_icon": "Arrows looped - Blue",
        "arrows_looped_green_icon": "Arrows looped - Green",
        "arrow_up_icon": "Arrow - Up",
        "bell_icon": "Bell",
        "bomb_icon": "Bomb",
        "book_icon": "Book",
        "books_icon": "Books",
        "box_icon": "Box",
        "bug_icon": "Ladybug",
        "cake_icon": "Cake",
        "calculator_icon": "Calculator",
        "calendar_icon": "Calendar",
        "camera_icon": "Camera",
        "cat_icon": "Cat",
        "cd_icon": "Compact disc (CD)",
        "charts_icon": "Charts",
        "chat_icon": "Chat",
        "checkmark_green_icon": "Check mark",
        "checkmark_green_icon_multiple": "Check marks",
        "clock_icon": "Clock",
        "clock_alarm_icon": "Clock - Alarm",
        "clock_stopwatch_icon": "Clock - Stopwatch",
        "cogwheel_icon": "Cogwheel",
        "cogwheels_icon": "Cogwheels",
        "computer_desktop_icon": "Computer - Desktop",
        "computer_laptop_icon": "Computer - Laptop",
        "computer_handheld_icon": "Computer - Handheld",
        "cross_red_icon": "Cross - Red",
        "die_icon": "Die",
        "document_icon": "Document",
        "earth_blue_icon": "Earth - Blue",
        "earth_green_icon": "Earth - Green",
        "envelope_icon": "Envelope",
        "envelopes_icon": "Envelopes",
        "folder_blue_icon": "Folder - Blue",
        "folder_blue_light_icon": "Folder - Light blue",
        "folder_green_icon": "Folder - Green",
        "folder_grey_icon": "Folder - Grey",
        "folder_orange_icon": "Folder - Orange",
        "folder_purple_icon": "Folder - Purple",
        "folder_red_icon": "Folder - Red",
        "folder_yellow_icon": "Folder - Yellow",
        "folder_blue_arrow_icon": "Folder - Blue with arrow",
        "heart_icon": "Heart",
        "hearts_icon": "Hearts",
        "house_green_icon": "House - Green",
        "house_red_icon": "House - Red",
        "key_icon": "Key",
        "keys_icon": "Keys",
        "lamp_icon": "Lamp",
        "led_blue_icon": "LED - Blue",
        "led_blue_light_icon": "LED - Light blue",
        "led_grey_icon": "LED - Grey",
        "led_green_icon": "LED - Green",
        "led_green_light_icon": "LED - Light green",
        "led_orange_icon": "LED - Orange",
        "led_purple_icon": "LED - Purple",
        "led_red_icon": "LED - Red",
        "led_yellow_icon": "LED - Yellow",
        "life_ring_icon": "Life ring",
        "lock_locked_icon": "Lock - Locked",
        "lock_unlocked_icon": "Lock - Unlocked",
        "magnifier_glass_icon": "Magnifier glass",
        "music_piano_icon": "Music - Piano",
        "music_note_icon": "Music - Note",
        "note_icon": "Note",
        "palette_icon": "Palette",
        "paperclip_icon": "Paperclip",
        "pencil_icon": "Pencil",
        "person_icon": "Person",
        "persons_icon": "People",
        "person_id_icon": "Person - ID",
        "person_talking_icon": "Person - Talking",
        "science_icon": "Science",
        "sign_important_icon": "Sign - Important",
        "symbol_minus_icon": "Symbol - Minus",
        "symbol_plus_icon": "Symbol - Plus",
        "star_red_icon": "Star - Red",
        "star_yellow_icon": "Star - Yellow",
        "terminal_icon": "Terminal",
        "trafficlight_icon": "Traffic light",
        "trashcan_icon": "Trashcan",
        "weather_lightning_icon": "Weather - Lightning",
        "weather_umbrella_icon": "Weather - Umbrella",
        "weather_sunny_icon": "Weather - Partly sunny",
        "wizard_icon": "Wizard",
        "wrench_icon": "Wrench",
    }

    items = []  # list of (key, label, bitmap)
    sorted_keys = sorted(icon_labels, key=lambda k: icon_labels[k])
    for key in sorted_keys:
        label = icon_labels[key]
        path = os.path.join(icons_dir, f"{key}16x16.png")
        if os.path.exists(path):
            img = wx.Image(path)
            if img.IsOk():
                bmp = img.ConvertToBitmap()
            else:
                bmp = wx.NullBitmap
        else:
            bmp = wx.NullBitmap
        items.append((key, label, bmp))
    return items


# --- Custom VListBox with bitmap + text ---

class BitmapVListBox(wx.VListBox):
    """Virtual list box that draws bitmap + text for each item."""

    ITEM_HEIGHT = 22
    ICON_SIZE = 16
    ICON_PADDING = 4
    TEXT_PADDING = 6

    def __init__(self, parent):
        super().__init__(parent, style=wx.BORDER_SIMPLE | wx.WANTS_CHARS)
        self._items = []  # (key, label, bitmap) - currently visible/filtered
        self._all_items = []  # All items unfiltered
        self.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
        self.Bind(wx.EVT_LEFT_DCLICK, self._on_left_down)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)
        self._on_select_callback = None

    def SetItems(self, items):
        """Set items to display. items = list of (key, label, bitmap)."""
        self._all_items = list(items)
        self._items = list(items)
        self.SetItemCount(len(self._items))
        self.Refresh()

    def FilterItems(self, filter_text):
        """Filter items by substring match on label."""
        if not filter_text:
            self._items = list(self._all_items)
        else:
            lower = filter_text.lower()
            self._items = [
                (k, l, b) for k, l, b in self._all_items
                if lower in l.lower()
            ]
        self.SetItemCount(len(self._items))
        if self._items:
            self.SetSelection(0)
        self.RefreshAll()

    def GetSelectedItem(self):
        """Return (key, label, bitmap) of selected item, or None."""
        sel = self.GetSelection()
        if sel != wx.NOT_FOUND and 0 <= sel < len(self._items):
            return self._items[sel]
        return None

    def SelectByKey(self, key):
        """Select item by key name."""
        for i, (k, l, b) in enumerate(self._items):
            if k == key:
                self.SetSelection(i)
                return

    def SetSelectCallback(self, callback):
        """Set callback(key, label, bitmap) called on selection."""
        self._on_select_callback = callback

    # --- VListBox overrides ---

    def OnMeasureItem(self, n):
        return self.ITEM_HEIGHT

    def OnDrawItem(self, dc, rect, n):
        if n < 0 or n >= len(self._items):
            return
        key, label, bmp = self._items[n]

        # Background is handled by OnDrawBackground (default works fine)
        # Set text color based on selection
        if self.IsSelected(n):
            dc.SetTextForeground(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
            )
        else:
            dc.SetTextForeground(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOXTEXT)
            )

        # Draw bitmap
        x = rect.x + self.ICON_PADDING
        if bmp and bmp.IsOk():
            bmp_y = rect.y + (rect.height - bmp.GetHeight()) // 2
            dc.DrawBitmap(bmp, x, bmp_y, True)

        # Draw text
        text_x = x + self.ICON_SIZE + self.TEXT_PADDING
        text_y = rect.y + (rect.height - dc.GetCharHeight()) // 2
        dc.DrawText(label, text_x, text_y)

    def OnDrawBackground(self, dc, rect, n):
        if self.IsSelected(n):
            color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
        else:
            color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOX)
        dc.SetBrush(wx.Brush(color))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(rect)

    # --- Event handlers ---

    def _on_left_down(self, event):
        item = self.VirtualHitTest(event.GetPosition().y)
        if item != wx.NOT_FOUND:
            self.SetSelection(item)
            if self._on_select_callback and 0 <= item < len(self._items):
                self._on_select_callback(*self._items[item])
        event.Skip()

    def _on_key_down(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_RETURN or key == wx.WXK_NUMPAD_ENTER:
            sel = self.GetSelection()
            if self._on_select_callback and 0 <= sel < len(self._items):
                self._on_select_callback(*self._items[sel])
        else:
            event.Skip()


# --- ComboPopup with SearchCtrl + VListBox ---

class SearchableIconPopup(wx.ComboPopup):
    """Popup containing a search field and a scrollable VListBox with icons."""

    def __init__(self, items):
        super().__init__()
        self._items = items  # (key, label, bitmap)
        self._selected_key = items[0][0] if items else ""
        self._selected_label = items[0][1] if items else ""

    def Create(self, parent):
        self._panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Search field
        self._search = wx.SearchCtrl(self._panel, style=wx.TE_PROCESS_ENTER)
        self._search.SetDescriptiveText("Search icons...")
        self._search.ShowCancelButton(True)
        sizer.Add(self._search, 0, wx.EXPAND | wx.ALL, 2)

        # VListBox with custom bitmap+text drawing
        self._listbox = BitmapVListBox(self._panel)
        self._listbox.SetItems(self._items)
        self._listbox.SetSelectCallback(self._on_item_selected)
        sizer.Add(self._listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 2)

        self._panel.SetSizer(sizer)

        # Bind events
        self._search.Bind(wx.EVT_TEXT, self._on_search_text)
        self._search.Bind(wx.EVT_TEXT_ENTER, self._on_search_enter)
        self._search.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self._on_search_cancel)
        self._search.Bind(wx.EVT_KEY_DOWN, self._on_search_key)

        return True

    def GetControl(self):
        return self._panel

    def GetAdjustedSize(self, minWidth, prefHeight, maxHeight):
        # Show enough items to be useful, up to maxHeight
        item_count = min(len(self._items), 15)
        list_height = item_count * BitmapVListBox.ITEM_HEIGHT
        search_height = self._search.GetBestSize().GetHeight() + 8
        total = search_height + list_height + 8
        return wx.Size(max(minWidth, 280), min(total, maxHeight))

    def SetStringValue(self, val):
        self._selected_label = val
        for key, label, bmp in self._items:
            if label == val:
                self._selected_key = key
                break

    def GetStringValue(self):
        return self._selected_label

    def GetSelectedKey(self):
        return self._selected_key

    def OnPopup(self):
        # Reset search and focus it when popup opens
        if self._search:
            self._search.SetValue("")
            self._listbox.FilterItems("")
            self._listbox.SelectByKey(self._selected_key)
            wx.CallAfter(self._search.SetFocus)

    def _on_search_text(self, event):
        self._listbox.FilterItems(self._search.GetValue())

    def _on_search_cancel(self, event):
        self._search.SetValue("")
        self._listbox.FilterItems("")

    def _on_search_enter(self, event):
        item = self._listbox.GetSelectedItem()
        if item:
            self._on_item_selected(*item)
        elif self._listbox._items:
            self._on_item_selected(*self._listbox._items[0])

    def _on_search_key(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_DOWN:
            # Move focus to listbox
            sel = self._listbox.GetSelection()
            if sel == wx.NOT_FOUND and self._listbox._items:
                self._listbox.SetSelection(0)
            elif sel < len(self._listbox._items) - 1:
                self._listbox.SetSelection(sel + 1)
            self._listbox.Refresh()
        elif key == wx.WXK_UP:
            sel = self._listbox.GetSelection()
            if sel > 0:
                self._listbox.SetSelection(sel - 1)
            self._listbox.Refresh()
        elif key == wx.WXK_ESCAPE:
            self.Dismiss()
        else:
            event.Skip()

    def _on_item_selected(self, key, label, bmp):
        self._selected_key = key
        self._selected_label = label
        self.Dismiss()


# --- The actual ComboCtrl widget ---

class SearchableIconCombo(wx.ComboCtrl):
    """A combo control with a searchable icon popup."""

    def __init__(self, parent, items, current_key=""):
        super().__init__(parent, style=wx.CB_READONLY)

        self._popup = SearchableIconPopup(items)
        self.SetPopupControl(self._popup)

        # Set initial value
        if current_key:
            for key, label, bmp in items:
                if key == current_key:
                    self.SetValue(label)
                    break
        elif items:
            self.SetValue(items[0][1])

        # Set popup height
        self.SetPopupMaxHeight(350)

    def GetSelectedKey(self):
        return self._popup.GetSelectedKey()


# --- For comparison: Current BitmapComboBox ---

class CurrentBitmapCombo(wx.Panel):
    def __init__(self, parent, items):
        super().__init__(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(
            wx.StaticText(self, label="CURRENT: wx.adv.BitmapComboBox (CB_READONLY)"),
            0, wx.ALL, 5
        )
        sizer.Add(
            wx.StaticText(self, label="  Problems: thin scroll arrows (GTK), no search"),
            0, wx.LEFT | wx.BOTTOM, 5
        )
        combo = wx.adv.BitmapComboBox(self, style=wx.CB_READONLY)
        for key, label, bmp in items:
            combo.Append(label, bmp, key)
        combo.SetSelection(0)
        sizer.Add(combo, 0, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)


# --- Main Frame ---

class DemoFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Icon Chooser: Searchable VListBox Demo",
                         size=(520, 420))
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        items = load_icon_data()
        status = wx.StaticText(panel,
                               label=f"Loaded {len(items)} icons. Compare the two approaches:")
        sizer.Add(status, 0, wx.ALL, 8)

        # Current approach (for comparison)
        sizer.Add(CurrentBitmapCombo(panel, items), 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.ALL, 5)

        # New approach
        sizer.Add(
            wx.StaticText(panel, label="NEW: ComboCtrl + SearchCtrl + VListBox"),
            0, wx.ALL, 5
        )
        sizer.Add(
            wx.StaticText(panel, label="  Real scrollbar, substring search, bitmap+text, keyboard nav"),
            0, wx.LEFT | wx.BOTTOM, 5
        )
        self._new_combo = SearchableIconCombo(panel, items, current_key="bell_icon")
        sizer.Add(self._new_combo, 0, wx.EXPAND | wx.ALL, 5)

        # Show selected
        self._status = wx.StaticText(panel, label="Selected: bell_icon")
        sizer.Add(self._status, 0, wx.ALL, 8)
        self._new_combo.Bind(wx.EVT_COMBOBOX_CLOSEUP, self._on_combo_close)

        panel.SetSizer(sizer)
        self.Centre()

    def _on_combo_close(self, event):
        key = self._new_combo.GetSelectedKey()
        label = self._new_combo.GetValue()
        self._status.SetLabel(f"Selected: {key} ({label})")


def main():
    app = wx.App()
    frame = DemoFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
