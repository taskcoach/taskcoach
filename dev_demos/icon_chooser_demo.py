"""
Demo: Searchable Icon Chooser with full feature set

Features:
    - Icon displayed in closed control
    - Visible SearchCtrl in popup
    - Hints column (grey, truncated) for additional search terms
    - Search filters by label AND hints
    - Disabled items (greyed out, unselectable)
    - Ellipsis for long text when using fixed width
    - Fixed width option with wide popup
    - Full theme-aware styling with all system colors
    - Proper tab sequence and focus handling

Theme parameters used:
    TextBox/Window:
        - SYS_COLOUR_WINDOW: Window/textbox background
        - SYS_COLOUR_WINDOWTEXT: Window/textbox text
        - SYS_COLOUR_WINDOWFRAME: Window frame/border
        - SYS_COLOUR_HIGHLIGHT: Selected item background
        - SYS_COLOUR_HIGHLIGHTTEXT: Selected item text
        - SYS_COLOUR_GRAYTEXT: Disabled/greyed text
        - SYS_COLOUR_HOTLIGHT: Focus/hover highlight

    Button/Control:
        - SYS_COLOUR_BTNFACE: Button face
        - SYS_COLOUR_BTNSHADOW: Button shadow/border
        - SYS_COLOUR_BTNHIGHLIGHT: Button highlight

    List:
        - SYS_COLOUR_LISTBOX: Listbox background
        - SYS_COLOUR_LISTBOXTEXT: Listbox text
        - SYS_COLOUR_LISTBOXHIGHLIGHTTEXT: Unfocused selection text

Run from the taskcoach root:
    python3 dev_demos/icon_chooser_demo.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wx
import wx.adv
import wx.lib.buttons as buttons


# --- Test data with hints ---

ICON_HINTS = {
    "bell_icon": "alarm notification alert reminder",
    "calendar_icon": "date schedule appointment event",
    "checkmark_green_icon": "done complete finished success yes",
    "clock_icon": "time hour minute watch",
    "envelope_icon": "mail email message letter",
    "folder_blue_icon": "directory storage files container",
    "heart_icon": "love favorite like health",
    "house_green_icon": "home residence building dwelling",
    "key_icon": "lock security password access",
    "led_blue_icon": "status indicator light signal online",
    "led_red_icon": "status indicator light signal error offline",
    "led_green_icon": "status indicator light signal ok active",
    "magnifier_glass_icon": "search find zoom look inspect",
    "pencil_icon": "edit write draw modify",
    "person_icon": "user account profile member contact",
    "star_yellow_icon": "favorite important priority rating bookmark",
    "trashcan_icon": "delete remove garbage bin recycle",
    "weather_lightning_icon": "storm thunder electric power urgent",
    "wrench_icon": "tool settings config repair fix maintenance",
}

DISABLED_ICONS = {"led_grey_icon", "cross_red_icon", "lock_locked_icon"}


def get_icons_dir():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "taskcoachlib", "gui", "icons"
    )


def load_icon_data():
    """Load icon data: (key, label, bitmap, hints, enabled) tuples."""
    icons_dir = get_icons_dir()
    icon_labels = {
        "arrow_down_icon": "Arrow - Down",
        "arrow_forward_icon": "Arrow - Forward",
        "bell_icon": "Bell",
        "book_icon": "Book",
        "calendar_icon": "Calendar",
        "checkmark_green_icon": "Check mark",
        "clock_icon": "Clock",
        "clock_alarm_icon": "Clock - Alarm",
        "cross_red_icon": "Cross - Red",
        "envelope_icon": "Envelope",
        "folder_blue_icon": "Folder - Blue",
        "folder_green_icon": "Folder - Green",
        "heart_icon": "Heart",
        "house_green_icon": "House - Green",
        "key_icon": "Key",
        "led_blue_icon": "LED - Blue",
        "led_green_icon": "LED - Green",
        "led_grey_icon": "LED - Grey",
        "led_red_icon": "LED - Red",
        "lock_locked_icon": "Lock - Locked",
        "lock_unlocked_icon": "Lock - Unlocked",
        "magnifier_glass_icon": "Magnifier glass",
        "pencil_icon": "Pencil",
        "person_icon": "Person",
        "star_red_icon": "Star - Red",
        "star_yellow_icon": "Star - Yellow",
        "trashcan_icon": "Trashcan",
        "weather_lightning_icon": "Weather - Lightning",
        "weather_sunny_icon": "Weather - Partly sunny",
        "wrench_icon": "Wrench",
    }

    items = []
    # Add "No icon" option first (empty key, no bitmap) - matches artprovider behavior
    items.append(("", "No icon", wx.NullBitmap, "", True))
    sorted_keys = sorted(icon_labels, key=lambda k: icon_labels[k])
    for key in sorted_keys:
        label = icon_labels[key]
        path = os.path.join(icons_dir, f"{key}16x16.png")
        if os.path.exists(path):
            img = wx.Image(path)
            bmp = img.ConvertToBitmap() if img.IsOk() else wx.NullBitmap
        else:
            bmp = wx.NullBitmap
        hints = ICON_HINTS.get(key, "")
        enabled = key not in DISABLED_ICONS
        items.append((key, label, bmp, hints, enabled))
    return items


# --- Custom VListBox ---

class IconVListBox(wx.VListBox):
    """Virtual list box with icon, label, and hints columns."""

    ICON_SIZE = 16
    ITEM_HEIGHT = 24
    PADDING = 4

    def __init__(self, parent):
        # Use BORDER_NONE - the popup panel provides the border
        super().__init__(parent, style=wx.BORDER_NONE | wx.WANTS_CHARS | wx.TAB_TRAVERSAL | wx.VSCROLL)
        self._items = []
        self._all_items = []
        self._on_select_callback = None

        # Column widths calculated from content
        self._max_label_width = 100
        self._max_hints_width = 100
        self._total_width = 300

        # Use system colors
        self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOX))

        self.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
        self.Bind(wx.EVT_LEFT_DCLICK, self._on_left_dclick)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self._on_leave)

    def SetItems(self, items):
        self._all_items = list(items)
        self._items = list(items)
        self._calculate_column_widths()
        self.SetItemCount(len(self._items))
        self.Refresh()

    def _calculate_column_widths(self):
        """Calculate column widths based on actual content."""
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())

        max_label = 0
        max_hints = 0

        for item in self._all_items:
            label_width = dc.GetTextExtent(item[1])[0]
            hints_width = dc.GetTextExtent(item[3])[0] if item[3] else 0
            max_label = max(max_label, label_width)
            max_hints = max(max_hints, hints_width)

        self._max_label_width = max_label + 10  # Small padding
        self._max_hints_width = max_hints + 10
        self._total_width = (self.PADDING + self.ICON_SIZE + self.PADDING +
                             self._max_label_width + self.PADDING +
                             self._max_hints_width + self.PADDING)

    def GetPreferredWidth(self):
        """Return preferred width based on content."""
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
            if item[4]:
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
            if self._items[i][4]:
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

        # Get theme colors based on state (hover moves selection, so no separate hover)
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
                # Greyscale for disabled
                img = bmp.ConvertToImage().ConvertToGreyscale()
                dc.DrawBitmap(img.ConvertToBitmap(), x, bmp_y, True)
            else:
                dc.DrawBitmap(bmp, x, bmp_y, True)

        # Draw label - use calculated column width
        label_x = x + self.ICON_SIZE + self.PADDING
        text_y = rect.y + (rect.height - dc.GetCharHeight()) // 2
        dc.SetTextForeground(text_color)

        display_label = wx.Control.Ellipsize(label, dc, wx.ELLIPSIZE_END, self._max_label_width)
        dc.DrawText(display_label, label_x, text_y)

        # Draw hints - positioned after label column
        if hints:
            hints_x = label_x + self._max_label_width + self.PADDING
            dc.SetTextForeground(hints_color)
            display_hints = wx.Control.Ellipsize(hints, dc, wx.ELLIPSIZE_END, self._max_hints_width)
            dc.DrawText(display_hints, hints_x, text_y)

    def OnDrawBackground(self, dc, rect, n):
        if n < 0 or n >= len(self._items):
            return
        is_selected = self.IsSelected(n)

        # Draw background
        bg_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOX)
        dc.SetBrush(wx.Brush(bg_color))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(rect)

        # Draw selection highlight (hover moves selection, so no separate hover)
        if is_selected:
            highlight = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
            dc.SetBrush(wx.Brush(highlight))
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.DrawRectangle(rect)

    def _on_left_down(self, event):
        """Single click selects item and closes popup."""
        item_idx = self.VirtualHitTest(event.GetPosition().y)
        if item_idx != wx.NOT_FOUND and 0 <= item_idx < len(self._items):
            item = self._items[item_idx]
            if item[4]:  # enabled
                self.SetSelection(item_idx)
                # Call callback to select and close popup
                if self._on_select_callback:
                    self._on_select_callback(*item)
        event.Skip()

    def _on_left_dclick(self, event):
        """Double click same as single click."""
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
        """Hover moves selection (like a menu)."""
        item_idx = self.VirtualHitTest(event.GetPosition().y)
        if item_idx != wx.NOT_FOUND and 0 <= item_idx < len(self._items):
            if self._items[item_idx][4]:  # Only select enabled items
                if item_idx != self.GetSelection():
                    self.SetSelection(item_idx)
                    self.Refresh()
        event.Skip()

    def _on_leave(self, event):
        """Mouse leave - keep current selection."""
        event.Skip()


# --- Custom Control widget (Attempt 1 - reference) ---

class SearchableIconCombo(wx.Control):
    """Custom combo control with searchable icon popup.

    Built as a wx.Control with custom painting. Kept as reference.
    Issue: Cannot perfectly match native GTK combo appearance with RendererNative.
    """

    ICON_SIZE = 16
    BTN_WIDTH = 24

    def __init__(self, parent, items, current_key="", fixed_width=None):
        super().__init__(parent, style=wx.TAB_TRAVERSAL | wx.WANTS_CHARS)

        self._items = items
        self._items_dict = {item[0]: item for item in items}
        self._current_key = ""
        self._current_label = ""
        self._current_bmp = None
        self._fixed_width = fixed_width
        self._has_focus = False
        self._is_hovered = False
        self._popup_shown = False
        self._popup_window = None

        # Calculate auto-size width
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        max_label_width = max(dc.GetTextExtent(item[1])[0] for item in items) if items else 100
        padding = 4
        self._auto_width = padding + self.ICON_SIZE + padding + max_label_width + padding + self.BTN_WIDTH

        # Set initial selection
        if current_key and current_key in self._items_dict:
            item = self._items_dict[current_key]
            self._current_key = item[0]
            self._current_label = item[1]
            self._current_bmp = item[2]
        else:
            for item in items:
                if item[4]:
                    self._current_key = item[0]
                    self._current_label = item[1]
                    self._current_bmp = item[2]
                    break

        # Get native height from a real Choice
        temp_choice = wx.Choice(parent, choices=["Temp"])
        native_height = temp_choice.GetBestSize().GetHeight()
        temp_choice.Destroy()
        self._best_height = native_height

        # Apply width
        if fixed_width:
            total = padding + self.ICON_SIZE + padding + fixed_width + self.BTN_WIDTH
            self._best_width = total
            self.SetMinSize(wx.Size(total, self._best_height))
            self.SetMaxSize(wx.Size(total, -1))
        else:
            self._best_width = self._auto_width
            self.SetMinSize(wx.Size(self._auto_width, self._best_height))

        # Bind events
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_SET_FOCUS, self._on_focus)
        self.Bind(wx.EVT_KILL_FOCUS, self._on_focus_lost)
        self.Bind(wx.EVT_ENTER_WINDOW, self._on_mouse_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self._on_mouse_leave)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

    def _on_mouse_enter(self, event):
        self._is_hovered = True
        self.Refresh()
        event.Skip()

    def _on_mouse_leave(self, event):
        self._is_hovered = False
        self.Refresh()
        event.Skip()

    def _on_left_down(self, event):
        self.SetFocus()
        self._show_popup()
        event.Skip()

    def _on_key_down(self, event):
        key = event.GetKeyCode()
        if key in (wx.WXK_SPACE, wx.WXK_DOWN, wx.WXK_UP, wx.WXK_RETURN):
            if not self._popup_shown:
                self._show_popup()
        else:
            event.Skip()

    def _on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_TAB:
            flags = wx.NavigationKeyEvent.FromTab
            if event.ShiftDown():
                flags |= wx.NavigationKeyEvent.IsBackward
            else:
                flags |= wx.NavigationKeyEvent.IsForward
            self.Navigate(flags)
        else:
            event.Skip()

    def _on_focus(self, event):
        self._has_focus = True
        self.Refresh()
        event.Skip()

    def _on_focus_lost(self, event):
        self._has_focus = False
        self.Refresh()
        event.Skip()

    def _show_popup(self):
        if self._popup_shown:
            return
        self._popup_window = SearchableIconPopupWindow(
            self, self._items, self._current_key, self._on_item_selected
        )
        pos = self.ClientToScreen(wx.Point(0, self.GetSize().GetHeight()))
        self._popup_window.Position(pos, wx.Size(0, 0))
        self._popup_shown = True
        self._popup_window.Popup()
        self.Refresh()

    def _reset_popup_state(self):
        self._popup_shown = False
        self._popup_window = None
        self.Refresh()

    def _on_item_selected(self, key, label, bmp, hints, enabled):
        if enabled:
            self._current_key = key
            self._current_label = label
            self._current_bmp = bmp
            event = wx.CommandEvent(wx.wxEVT_COMBOBOX_CLOSEUP, self.GetId())
            event.SetEventObject(self)
            self.GetEventHandler().ProcessEvent(event)
        self.Refresh()

    def _on_paint(self, event):
        dc = wx.BufferedPaintDC(self)
        rect = self.GetClientRect()
        padding = 4
        renderer = wx.RendererNative.Get()

        parent_bg = self.GetParent().GetBackgroundColour()
        dc.SetBackground(wx.Brush(parent_bg))
        dc.Clear()

        ctrl_flags = 0
        if self._popup_shown:
            ctrl_flags |= wx.CONTROL_PRESSED
        if self._is_hovered:
            ctrl_flags |= wx.CONTROL_CURRENT
        if self._has_focus:
            ctrl_flags |= wx.CONTROL_FOCUSED
        if not self.IsEnabled():
            ctrl_flags |= wx.CONTROL_DISABLED

        # Draw as button with dropdown arrow
        renderer.DrawPushButton(self, dc, rect, ctrl_flags)
        arrow_width = 16
        arrow_rect = wx.Rect(rect.width - arrow_width - 4, 0, arrow_width, rect.height)
        renderer.DrawDropArrow(self, dc, arrow_rect, ctrl_flags)

        border = 4
        content_rect = wx.Rect(rect.x + border, rect.y + border,
                               rect.width - arrow_width - border - 4,
                               rect.height - border * 2)

        x = content_rect.x
        if self._current_bmp and self._current_bmp.IsOk():
            y = content_rect.y + (content_rect.height - self._current_bmp.GetHeight()) // 2
            dc.DrawBitmap(self._current_bmp, x, y, True)

        text_x = x + self.ICON_SIZE + padding
        available_width = content_rect.width - (text_x - content_rect.x) - padding

        dc.SetFont(self.GetFont())
        text_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNTEXT)
        if not self.IsEnabled():
            text_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        dc.SetTextForeground(text_color)

        text = self._current_label
        if available_width > 10:
            if self._fixed_width:
                text = wx.Control.Ellipsize(text, dc, wx.ELLIPSIZE_END, available_width)
            text_y = content_rect.y + (content_rect.height - dc.GetCharHeight()) // 2
            dc.DrawText(text, text_x, text_y)

        if self._has_focus:
            focus_rect = wx.Rect(rect.x + 3, rect.y + 3, rect.width - 6, rect.height - 6)
            renderer.DrawFocusRect(self, dc, focus_rect, 0)

    def DoGetBestSize(self):
        return wx.Size(self._best_width, self._best_height)

    def AcceptsFocus(self):
        return True

    def AcceptsFocusFromKeyboard(self):
        return True

    def GetValue(self):
        return self._current_label

    def GetSelectedKey(self):
        return self._current_key


class SearchableIconPopupWindow(wx.PopupTransientWindow):
    """Popup window with searchable icon list.

    Used by both SearchableIconCombo and IconPickerButton.

    Implementation notes:
    - PopupTransientWindow.Dismiss() has known issues on Linux/GTK where
      the window remains visible even after Dismiss() returns
    - Solution: Use Hide() followed by Destroy() via CallAfter
    - Parent control must implement _reset_popup_state() to clear its state
    - Known issue: TextCtrl/SearchCtrl caret not visible on GTK3 (wxWidgets #18261)
    """

    def __init__(self, parent, items, current_key, on_select_callback):
        super().__init__(parent)
        self._parent_ctrl = parent
        self._items = items
        self._on_select_callback = on_select_callback
        self._current_key = current_key

        panel = wx.Panel(self, style=wx.BORDER_NONE | wx.TAB_TRAVERSAL)
        panel.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
        self.Bind(wx.EVT_PAINT, self._on_paint)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self._search = wx.SearchCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self._search.SetDescriptiveText("Search icons...")
        self._search.ShowCancelButton(True)
        sizer.Add(self._search, 0, wx.EXPAND | wx.ALL, 5)

        self._listbox = IconVListBox(panel)
        self._listbox.SetItems(items)
        self._listbox.SetSelectCallback(self._on_item_selected)
        sizer.Add(self._listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        panel.SetSizer(sizer)
        popup_sizer = wx.BoxSizer(wx.VERTICAL)
        popup_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(popup_sizer)

        # Calculate popup size - show all items, limited by screen height
        list_height = len(items) * IconVListBox.ITEM_HEIGHT
        search_height = self._search.GetBestSize().GetHeight() + 12
        content_width = self._listbox.GetPreferredWidth() + 24
        total_height = search_height + list_height + 16

        # Limit to 75% of screen height
        display = wx.Display(wx.Display.GetFromWindow(parent))
        screen_height = display.GetClientArea().GetHeight()
        max_height = int(screen_height * 0.75)
        total_height = min(total_height, max_height)

        min_width = max(parent.GetSize().GetWidth(), content_width)
        self.SetSize(wx.Size(min_width, total_height))

        self._search.Bind(wx.EVT_TEXT, self._on_text_changed)
        self._search.Bind(wx.EVT_TEXT_ENTER, self._on_enter)
        self._search.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self._search.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self._on_cancel)
        self._search.Bind(wx.EVT_SET_FOCUS, self._on_search_focus)
        self._search.Bind(wx.EVT_KILL_FOCUS, self._on_search_blur)

    def _on_text_changed(self, event):
        """Handle text changes in search control."""
        value = self._search.GetValue()
        self._listbox.FilterItems(value)
        event.Skip()

    def _on_search_focus(self, event):
        """Handle search control gaining focus."""
        event.Skip()

    def _on_search_blur(self, event):
        """Handle search control losing focus."""
        event.Skip()

    def _on_paint(self, event):
        dc = wx.PaintDC(self)
        rect = self.GetClientRect()
        border_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNSHADOW)
        dc.SetPen(wx.Pen(border_color, 1))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(rect)
        event.Skip()

    def Popup(self):
        # Check display backend (X11 vs Wayland)
        import os
        gdk_backend = os.environ.get('GDK_BACKEND', 'not set')
        wayland_display = os.environ.get('WAYLAND_DISPLAY', 'not set')
        display = os.environ.get('DISPLAY', 'not set')

        super().Popup()
        self._listbox.SelectByKey(self._current_key)
        # Focus handling for SearchCtrl caret visibility on GTK
        # Multiple attempts needed due to GTK focus quirks (wxWidgets #2043, #17820)
        self._focus_search_ctrl()

    def _focus_search_ctrl(self):
        """Set focus to search control with multiple attempts for GTK compatibility."""
        if not self._search:
            return

        def do_focus():
            if self._search and self.IsShown():
                # Set focus and position caret
                self._search.SetFocus()
                self._search.SetInsertionPoint(0)

        # Try focus with delays for GTK
        wx.CallAfter(do_focus)
        wx.CallLater(100, do_focus)

    def OnDismiss(self):
        if self._parent_ctrl:
            self._parent_ctrl._reset_popup_state()

    def _on_cancel(self, event):
        """Clear search on cancel button click."""
        self._search.SetValue("")
        self._listbox.FilterItems("")

    def _on_enter(self, event):
        item = self._listbox.GetSelectedItem()
        if item and item[4]:
            self._on_item_selected(*item)

    def _on_key(self, event):
        key = event.GetKeyCode()
        if key in (wx.WXK_DOWN, wx.WXK_UP):
            self._listbox._on_key_down(event)
        elif key == wx.WXK_ESCAPE:
            self.Dismiss()
        else:
            event.Skip()

    def _on_item_selected(self, key, label, bmp, hints, enabled):
        if enabled:
            self._on_select_callback(key, label, bmp, hints, enabled)
            wx.CallAfter(self._dismiss_popup)

    def _dismiss_popup(self):
        """Dismiss popup and reset parent state."""

        # Try multiple approaches to close the popup
        self.Hide()

        self.Show(False)

        self.Dismiss()

        if self._parent_ctrl:
            self._parent_ctrl._reset_popup_state()

        wx.CallAfter(self._destroy_popup)

    def _destroy_popup(self):
        """Actually destroy the popup window."""
        try:
            if self:
                self.Destroy()
        except RuntimeError:
            pass
        except Exception:
            pass


# --- OwnerDrawnComboBox with icons ---

class IconOwnerDrawnComboBox(wx.adv.OwnerDrawnComboBox):
    """OwnerDrawnComboBox that draws icons alongside text."""

    ICON_SIZE = 16
    PADDING = 4

    def __init__(self, parent, items):
        # Use CB_READONLY for proper appearance
        super().__init__(parent, style=wx.CB_READONLY)

        # Store items and bitmaps
        self._items = items
        self._bitmaps = {}
        for key, label, bmp, hints, enabled in items:
            self.Append(label, key)
            self._bitmaps[label] = bmp
        self.SetSelection(0)

        # Handle tab navigation manually via EVT_CHAR_HOOK
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

    def _on_char_hook(self, event):
        """Handle Tab key manually since CB_READONLY blocks it on GTK."""
        if event.GetKeyCode() == wx.WXK_TAB:
            flags = wx.NavigationKeyEvent.FromTab
            if event.ShiftDown():
                flags |= wx.NavigationKeyEvent.IsBackward
            else:
                flags |= wx.NavigationKeyEvent.IsForward
            self.Navigate(flags)
        else:
            event.Skip()

    def AcceptsFocus(self):
        return True

    def AcceptsFocusFromKeyboard(self):
        return True

    def OnDrawItem(self, dc, rect, item, flags):
        if item == wx.NOT_FOUND:
            return
        label = self.GetString(item)
        bmp = self._bitmaps.get(label)

        # Draw icon
        x = rect.x + self.PADDING
        if bmp and bmp.IsOk():
            y = rect.y + (rect.height - bmp.GetHeight()) // 2
            dc.DrawBitmap(bmp, x, y, True)

        # Draw text
        text_x = x + self.ICON_SIZE + self.PADDING
        text_y = rect.y + (rect.height - dc.GetCharHeight()) // 2
        dc.DrawText(label, text_x, text_y)

    def OnMeasureItem(self, item):
        return max(self.ICON_SIZE + 8, 24)

    def OnMeasureItemWidth(self, item):
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        label = self.GetString(item)
        text_width = dc.GetTextExtent(label)[0]
        return self.PADDING + self.ICON_SIZE + self.PADDING + text_width + self.PADDING


# --- IconListPopup for ComboCtrl demo ---

class IconListPopup(wx.ComboPopup):
    """Popup with icon list for ComboCtrl demonstration."""

    ICON_SIZE = 16
    ITEM_HEIGHT = 24
    PADDING = 4

    def __init__(self, items):
        super().__init__()
        self._items = items
        self._selected_idx = 0
        self._selected_label = items[0][1] if items else ""

    def Create(self, parent):
        self._panel = wx.ScrolledWindow(parent, style=wx.VSCROLL)
        self._panel.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOX))
        self._panel.SetScrollRate(0, self.ITEM_HEIGHT)
        self._panel.SetVirtualSize(300, len(self._items) * self.ITEM_HEIGHT)
        self._panel.Bind(wx.EVT_PAINT, self._on_paint)
        self._panel.Bind(wx.EVT_LEFT_UP, self._on_click)
        self._panel.Bind(wx.EVT_MOTION, self._on_motion)
        self._hover_idx = -1
        return True

    def GetControl(self):
        return self._panel

    def GetAdjustedSize(self, minWidth, prefHeight, maxHeight):
        height = min(len(self._items) * self.ITEM_HEIGHT, 200)
        return wx.Size(minWidth, height)

    def SetStringValue(self, val):
        self._selected_label = val
        for i, item in enumerate(self._items):
            if item[1] == val:
                self._selected_idx = i
                break

    def GetStringValue(self):
        return self._selected_label

    def _on_paint(self, event):
        dc = wx.PaintDC(self._panel)
        self._panel.DoPrepareDC(dc)
        dc.SetFont(self._panel.GetFont())

        for i, (key, label, bmp, hints, enabled) in enumerate(self._items):
            y = i * self.ITEM_HEIGHT
            rect = wx.Rect(0, y, self._panel.GetClientSize().width, self.ITEM_HEIGHT)

            # Background
            if i == self._hover_idx or i == self._selected_idx:
                dc.SetBrush(wx.Brush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)))
                dc.SetPen(wx.TRANSPARENT_PEN)
                dc.DrawRectangle(rect)
                dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
            else:
                dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOXTEXT))

            # Icon
            x = self.PADDING
            if bmp and bmp.IsOk():
                bmp_y = y + (self.ITEM_HEIGHT - bmp.GetHeight()) // 2
                dc.DrawBitmap(bmp, x, bmp_y, True)

            # Text
            text_x = x + self.ICON_SIZE + self.PADDING
            text_y = y + (self.ITEM_HEIGHT - dc.GetCharHeight()) // 2
            dc.DrawText(label, text_x, text_y)

    def _on_motion(self, event):
        y = self._panel.CalcUnscrolledPosition(event.GetPosition())[1]
        idx = y // self.ITEM_HEIGHT
        if 0 <= idx < len(self._items) and idx != self._hover_idx:
            self._hover_idx = idx
            self._panel.Refresh()
        event.Skip()

    def _on_click(self, event):
        y = self._panel.CalcUnscrolledPosition(event.GetPosition())[1]
        idx = y // self.ITEM_HEIGHT
        if 0 <= idx < len(self._items):
            self._selected_idx = idx
            self._selected_label = self._items[idx][1]
            self.Dismiss()

    def GetSelectedBitmap(self):
        """Return the bitmap of the selected item."""
        if 0 <= self._selected_idx < len(self._items):
            return self._items[self._selected_idx][2]
        return None


# --- IconComboCtrl for demo ---

class IconComboCtrl(wx.ComboCtrl):
    """ComboCtrl that displays icon in the main control area."""

    ICON_SIZE = 16
    PADDING = 4

    def __init__(self, parent, items):
        super().__init__(parent, style=wx.CB_READONLY)
        self._items = items
        self._current_bmp = items[0][2] if items else None

        # Reserve space for icon in the text control area
        self.SetCustomPaintWidth(self.ICON_SIZE + self.PADDING * 2)

        # Use alt popup window for better focus handling (must be before SetPopupControl)
        self.UseAltPopupWindow(True)

        # Create and set popup
        self._popup = IconListPopup(items)
        self.SetPopupControl(self._popup)
        self.SetValue(items[0][1] if items else "")

        # Handle tab and update icon on close
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.Bind(wx.EVT_COMBOBOX_CLOSEUP, self._on_closeup)

    def _on_char_hook(self, event):
        """Handle Tab key manually since CB_READONLY blocks it on GTK."""
        if event.GetKeyCode() == wx.WXK_TAB:
            flags = wx.NavigationKeyEvent.FromTab
            if event.ShiftDown():
                flags |= wx.NavigationKeyEvent.IsBackward
            else:
                flags |= wx.NavigationKeyEvent.IsForward
            self.Navigate(flags)
        else:
            event.Skip()

    def _on_closeup(self, event):
        """Update the icon when popup closes."""
        self._current_bmp = self._popup.GetSelectedBitmap()
        self.Refresh()
        event.Skip()

    def OnDrawItem(self, dc, rect, item, flags):
        """Draw the icon in the custom paint area."""
        if self._current_bmp and self._current_bmp.IsOk():
            x = rect.x + self.PADDING
            y = rect.y + (rect.height - self._current_bmp.GetHeight()) // 2
            dc.DrawBitmap(self._current_bmp, x, y, True)

    def AcceptsFocus(self):
        return True

    def AcceptsFocusFromKeyboard(self):
        return True


# --- Button-based Icon Picker using ThemedGenBitmapTextButton ---

class IconPickerButton(buttons.ThemedGenBitmapTextButton):
    """Button with icon and text that opens a searchable icon picker popup.

    Uses ThemedGenBitmapTextButton for native theme rendering via RendererNative.
    Overrides DrawLabel to support text ellipsis for fixed width.

    Implementation notes:
    - Uses _popup_open guard flag to prevent re-opening popup during selection
    - Fires wxEVT_COMBOBOX (not wxEVT_BUTTON) on selection to avoid triggering _on_click
    - PopupTransientWindow.Dismiss() has known issues on Linux/GTK
      (see wxPython GitHub issues #1853, #2554)
    - Solution: Use Hide() + Destroy() via CallAfter for reliable popup closing

    The button always displays with active/enabled appearance, even when
    "No icon" is selected. A transparent placeholder bitmap is required because
    GenBitmapButton.SetBitmapLabel() calls bitmap.ConvertToImage() which fails
    on wx.NullBitmap.
    """

    PADDING = 8
    ICON_SIZE = 16  # Standard icon size for layout consistency

    def __init__(self, parent, items, current_key="", fixed_width=None):
        # Set attributes BEFORE parent init (DoGetBestSize may be called)
        self._items = items
        self._items_dict = {item[0]: item for item in items}
        self._current_key = ""
        self._current_label = ""
        self._current_bmp = None
        self._fixed_width = fixed_width
        self._popup_open = False  # Guard flag to prevent re-opening during selection

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

        # Enable focus indicator (disabled by default with BORDER_NONE)
        self.SetUseFocusIndicator(True)

        # Set initial selection
        if current_key and current_key in self._items_dict:
            item = self._items_dict[current_key]
            self._set_current(item)
        else:
            for item in items:
                if item[4]:  # enabled
                    self._set_current(item)
                    break

        # Apply fixed width
        if fixed_width:
            self.SetMinSize(wx.Size(fixed_width, -1))
            self.SetMaxSize(wx.Size(fixed_width, -1))

        self.Bind(wx.EVT_BUTTON, self._on_click)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

    def _on_key_down(self, event):
        """Handle Enter key to activate button (GenButton only handles Space)."""
        key = event.GetKeyCode()
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._on_click(event)
        else:
            event.Skip()

    def DrawFocusIndicator(self, dc, w, h):
        """Draw focus indicator using RendererNative.DrawFocusRect."""
        # Inset the focus rect slightly from the button edge
        rect = wx.Rect(3, 3, w - 6, h - 6)
        wx.RendererNative.Get().DrawFocusRect(self, dc, rect)

    def _set_current(self, item):
        """Set the current selection."""
        self._current_key = item[0]
        self._current_label = item[1]
        self._current_bmp = item[2]
        self._update_button()

    def _update_button(self):
        """Update button with icon and label."""
        self.SetLabel(self._current_label)
        if self._current_bmp and self._current_bmp.IsOk():
            self.SetBitmapLabel(self._current_bmp)
        else:
            # Use 16x16 transparent placeholder for "No icon"
            # This maintains consistent active button appearance
            self.SetBitmapLabel(self._empty_bmp)
        # Resize if auto-width
        if not self._fixed_width:
            self.SetInitialSize()
            self.GetParent().Layout()
        self.Refresh()

    def DrawLabel(self, dc, width, height, dx=0, dy=0):
        """Override to add ellipsis support for fixed width."""
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

        # Calculate available width for text
        if self._fixed_width:
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

        # Draw text after icon space
        dc.DrawText(label, pos_x, (height - th) // 2 + dy)

    def DoGetBestSize(self):
        """Calculate best size based on bitmap and label."""
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())

        label = self.GetLabel()
        tw, th = dc.GetTextExtent(label)

        # Always include ICON_SIZE for consistent button size
        bw, bh = self.ICON_SIZE, self.ICON_SIZE
        if self.bmpLabel and self.bmpLabel.IsOk():
            bw, bh = self.bmpLabel.GetWidth(), self.bmpLabel.GetHeight()

        width = self.PADDING + bw + self.PADDING + tw + self.PADDING
        height = max(th, bh) + self.PADDING * 2

        if self._fixed_width:
            width = self._fixed_width

        return wx.Size(width, height)

    def _on_click(self, event):
        """Open the searchable popup."""
        if self._popup_open:
            return
        self._popup_open = True
        popup = SearchableIconPopupWindow(
            self, self._items, self._current_key, self._on_item_selected
        )
        pos = self.ClientToScreen(wx.Point(0, self.GetSize().GetHeight()))
        popup.Position(pos, wx.Size(0, 0))
        popup.Popup()

    def _on_item_selected(self, key, label, bmp, hints, enabled):
        """Handle selection from popup."""
        if enabled:
            item = (key, label, bmp, hints, enabled)
            self._set_current(item)
            # Fire a command event (not EVT_BUTTON to avoid re-triggering _on_click)
            # Use wxEVT_COMBOBOX to signal selection changed
            evt = wx.CommandEvent(wx.wxEVT_COMBOBOX, self.GetId())
            evt.SetEventObject(self)
            evt.SetString(label)
            self.GetEventHandler().ProcessEvent(evt)

    def _reset_popup_state(self):
        """Called when popup is dismissed."""
        self._popup_open = False

    def GetSelectedKey(self):
        return self._current_key

    def GetValue(self):
        return self._current_label


# --- MiniFrame-based Popup (GTK3 caret fix) ---

class MiniFrameIconPopup(wx.MiniFrame):
    """MiniFrame-based popup with searchable icon list.

    Uses wx.MiniFrame instead of PopupTransientWindow to fix GTK3 caret visibility
    (see wxWidgets issue #18261 - cursor not visible in popup windows on GTK3).

    Platform behavior:
    - Windows & GTK (Linux): Small title bar, no taskbar entry, stays on top of parent
    - macOS: Behaves like a normal frame (acceptable since caret issue is GTK-specific)

    MiniFrame with FRAME_FLOAT_ON_PARENT provides popup-like behavior with proper focus,
    allowing TextCtrl/SearchCtrl to show the caret correctly on all platforms.
    """

    def __init__(self, parent, items, current_key, on_select_callback):
        style = (wx.FRAME_FLOAT_ON_PARENT | wx.FRAME_NO_TASKBAR |
                 wx.BORDER_SIMPLE | wx.FRAME_TOOL_WINDOW)
        super().__init__(parent, title="", style=style)
        self._parent_ctrl = parent
        self._items = items
        self._on_select_callback = on_select_callback
        self._current_key = current_key

        panel = wx.Panel(self, style=wx.BORDER_NONE | wx.TAB_TRAVERSAL)
        panel.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))

        sizer = wx.BoxSizer(wx.VERTICAL)
        self._search = wx.SearchCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self._search.SetDescriptiveText("Search icons...")
        self._search.ShowCancelButton(True)
        sizer.Add(self._search, 0, wx.EXPAND | wx.ALL, 5)

        self._listbox = IconVListBox(panel)
        self._listbox.SetItems(items)
        self._listbox.SetSelectCallback(self._on_item_selected)
        sizer.Add(self._listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        panel.SetSizer(sizer)

        # Calculate popup size - show all items, limited by screen height
        list_height = len(items) * IconVListBox.ITEM_HEIGHT
        search_height = self._search.GetBestSize().GetHeight() + 12
        content_width = self._listbox.GetPreferredWidth() + 24
        total_height = search_height + list_height + 16

        # Limit to 75% of screen height
        display = wx.Display(wx.Display.GetFromWindow(parent))
        screen_height = display.GetClientArea().GetHeight()
        max_height = int(screen_height * 0.75)
        total_height = min(total_height, max_height)

        min_width = max(parent.GetSize().GetWidth(), content_width)
        self.SetSize(wx.Size(min_width, total_height))

        # Bind events
        self._search.Bind(wx.EVT_TEXT, lambda e: self._listbox.FilterItems(self._search.GetValue()))
        self._search.Bind(wx.EVT_TEXT_ENTER, self._on_enter)
        self._search.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self._search.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self._on_cancel)
        self.Bind(wx.EVT_ACTIVATE, self._on_activate)
        self.Bind(wx.EVT_KILL_FOCUS, self._on_kill_focus)

    def Popup(self):
        """Show the popup."""
        self._listbox.SelectByKey(self._current_key)
        self.Show()
        # Focus search control - should show caret with MiniFrame
        wx.CallAfter(self._focus_search)

    def _focus_search(self):
        if self._search and self.IsShown():
            self._search.SetFocus()
            self._search.SetInsertionPoint(0)

    def _on_activate(self, event):
        """Handle window activation/deactivation."""
        if not event.GetActive():
            self._dismiss()
        event.Skip()

    def _on_kill_focus(self, event):
        """Handle focus loss."""
        event.Skip()

    def _dismiss(self):
        """Close the popup."""
        if self._parent_ctrl:
            self._parent_ctrl._reset_popup_state()
            # Force refresh of the area behind the popup
            parent_frame = self._parent_ctrl.GetTopLevelParent()
            if parent_frame:
                parent_frame.Refresh()
                parent_frame.Update()
        self.Hide()
        wx.CallAfter(self.Destroy)

    def _on_cancel(self, event):
        self._search.SetValue("")
        self._listbox.FilterItems("")

    def _on_enter(self, event):
        item = self._listbox.GetSelectedItem()
        if item and item[4]:
            self._on_item_selected(*item)

    def _on_key(self, event):
        key = event.GetKeyCode()
        if key in (wx.WXK_DOWN, wx.WXK_UP):
            self._listbox._on_key_down(event)
        elif key == wx.WXK_ESCAPE:
            self._dismiss()
        else:
            event.Skip()

    def _on_item_selected(self, key, label, bmp, hints, enabled):
        if enabled:
            self._on_select_callback(key, label, bmp, hints, enabled)
            wx.CallAfter(self._dismiss)


class IconPickerButtonMF(buttons.ThemedGenBitmapTextButton):
    """Button with icon picker using MiniFrame popup (GTK3 caret fix).

    Same as IconPickerButton but uses MiniFrameIconPopup for proper
    caret visibility on GTK3 (see wxWidgets issue #18261).

    This is the recommended approach for cross-platform icon picker with
    searchable popup, as it properly shows the text caret on all platforms:
    - Windows: MiniFrame with small title bar, no taskbar entry
    - GTK/Linux: MiniFrame with proper focus and caret visibility
    - macOS: Regular frame behavior (caret works natively)

    The button always displays with active/enabled appearance, even when
    "No icon" is selected. A transparent placeholder bitmap is required because
    GenBitmapButton.SetBitmapLabel() calls bitmap.ConvertToImage() which fails
    on wx.NullBitmap.
    """

    PADDING = 8
    ARROW_WIDTH = 16  # Width reserved for dropdown arrow
    ICON_SIZE = 16    # Standard icon size for layout consistency

    def __init__(self, parent, items, current_key="", fixed_width=None):
        self._items = items
        self._items_dict = {item[0]: item for item in items}
        self._current_key = ""
        self._current_label = ""
        self._current_bmp = None
        self._fixed_width = fixed_width
        self._popup_open = False

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

        # Enable focus indicator (disabled by default with BORDER_NONE)
        self.SetUseFocusIndicator(True)

        if current_key and current_key in self._items_dict:
            item = self._items_dict[current_key]
            self._set_current(item)
        else:
            for item in items:
                if item[4]:
                    self._set_current(item)
                    break

        if fixed_width:
            self.SetMinSize(wx.Size(fixed_width, -1))
            self.SetMaxSize(wx.Size(fixed_width, -1))

        self.Bind(wx.EVT_BUTTON, self._on_click)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

    def _on_key_down(self, event):
        """Handle Enter key to activate button (GenButton only handles Space)."""
        key = event.GetKeyCode()
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._on_click(event)
        else:
            event.Skip()

    def DrawFocusIndicator(self, dc, w, h):
        """Draw focus indicator using RendererNative.DrawFocusRect."""
        # Inset the focus rect slightly from the button edge
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
        if not self._fixed_width:
            self.SetInitialSize()
            self.GetParent().Layout()
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
        # Account for arrow width in available space
        arrow_space = self.ARROW_WIDTH + self.PADDING
        if self._fixed_width:
            available_width = width - bw - self.PADDING * 3 - arrow_space
            if available_width > 0:
                label = wx.Control.Ellipsize(label, dc, wx.ELLIPSIZE_END, available_width)

        tw, th = dc.GetTextExtent(label)

        # Draw icon if present
        pos_x = self.PADDING + dx
        if has_valid_bmp:
            dc.DrawBitmap(bmp, pos_x, (height - bh) // 2 + dy, hasMask)
        # Always advance past icon space for consistent text positioning
        pos_x += bw + self.PADDING

        # Draw text (after icon space)
        dc.DrawText(label, pos_x, (height - th) // 2 + dy)

        # Draw dropdown arrow (right-aligned) using native renderer
        arrow_rect = wx.Rect(width - self.ARROW_WIDTH - self.PADDING + dx,
                             0, self.ARROW_WIDTH, height)
        flags = 0
        if not self.IsEnabled():
            flags |= wx.CONTROL_DISABLED
        wx.RendererNative.Get().DrawDropArrow(self, dc, arrow_rect, flags)

    def DoGetBestSize(self):
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        label = self.GetLabel()
        tw, th = dc.GetTextExtent(label)
        # Always include ICON_SIZE for consistent button size
        bw, bh = self.ICON_SIZE, self.ICON_SIZE
        if self.bmpLabel and self.bmpLabel.IsOk():
            bw, bh = self.bmpLabel.GetWidth(), self.bmpLabel.GetHeight()
        # Include arrow width in size calculation
        width = self.PADDING + bw + self.PADDING + tw + self.PADDING + self.ARROW_WIDTH + self.PADDING
        height = max(th, bh) + self.PADDING * 2
        if self._fixed_width:
            width = self._fixed_width
        return wx.Size(width, height)

    def _on_click(self, event):
        if self._popup_open:
            return
        self._popup_open = True
        popup = MiniFrameIconPopup(
            self, self._items, self._current_key, self._on_item_selected
        )
        pos = self.ClientToScreen(wx.Point(0, self.GetSize().GetHeight()))
        popup.SetPosition(pos)
        popup.Popup()

    def _on_item_selected(self, key, label, bmp, hints, enabled):
        if enabled:
            item = (key, label, bmp, hints, enabled)
            self._set_current(item)
            evt = wx.CommandEvent(wx.wxEVT_COMBOBOX, self.GetId())
            evt.SetEventObject(self)
            evt.SetString(label)
            self.GetEventHandler().ProcessEvent(evt)

    def _reset_popup_state(self):
        self._popup_open = False

    def GetSelectedKey(self):
        return self._current_key

    def GetValue(self):
        return self._current_label


# --- Main Demo Frame ---

class DemoFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Icon Picker Demo - Full Features", size=(750, 900))
        panel = wx.Panel(self, style=wx.TAB_TRAVERSAL)
        sizer = wx.BoxSizer(wx.VERTICAL)

        items = load_icon_data()

        # Header
        header = wx.StaticText(panel, label=f"Loaded {len(items)} icons. Test search, tab navigation, and focus!")
        header.SetFont(header.GetFont().Bold())
        sizer.Add(header, 0, wx.ALL, 10)

        # === 1. Standard Controls for Comparison ===
        section_std = wx.StaticText(panel, label="=== 1. Standard wxWidgets Controls ===")
        section_std.SetFont(section_std.GetFont().Bold())
        sizer.Add(section_std, 0, wx.LEFT | wx.TOP, 10)

        # Control 1a: wx.adv.BitmapComboBox
        sizer.Add(wx.StaticText(panel, label="1a. wx.adv.BitmapComboBox (with icons)"), 0, wx.LEFT | wx.TOP, 5)
        self._combo_bitmap = wx.adv.BitmapComboBox(panel, style=wx.CB_READONLY)
        for key, label, bmp, hints, enabled in items:
            self._combo_bitmap.Append(label, bmp, key)
        self._combo_bitmap.SetSelection(0)
        sizer.Add(self._combo_bitmap, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Control 1b: wx.adv.OwnerDrawnComboBox (with icons)
        sizer.Add(wx.StaticText(panel, label="1b. wx.adv.OwnerDrawnComboBox (with custom icon drawing)"), 0, wx.LEFT | wx.TOP, 5)
        self._combo_ownerdrawn = IconOwnerDrawnComboBox(panel, items)
        sizer.Add(self._combo_ownerdrawn, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 2)

        # === 2. Custom Searchable Controls ===
        section_custom = wx.StaticText(panel, label="=== 2. Custom Searchable Icon Picker ===")
        section_custom.SetFont(section_custom.GetFont().Bold())
        sizer.Add(section_custom, 0, wx.LEFT | wx.TOP, 10)

        # Control 2a: Stretched full width
        sizer.Add(wx.StaticText(panel, label="2a. CUSTOM (Stretched): Expands to fill width"), 0, wx.LEFT | wx.TOP, 5)
        self._combo_stretched = SearchableIconCombo(panel, items, current_key="bell_icon")
        sizer.Add(self._combo_stretched, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Control 2b: Auto-sized (natural width)
        sizer.Add(wx.StaticText(panel, label="2b. CUSTOM (Auto Size): Natural width based on longest label"), 0, wx.LEFT | wx.TOP, 5)
        self._combo_auto = SearchableIconCombo(panel, items, current_key="calendar_icon")
        sizer.Add(self._combo_auto, 0, wx.LEFT, 10)

        # Control 2c: Fixed 75px
        sizer.Add(wx.StaticText(panel, label="2c. CUSTOM (75px): Fixed narrow width with ellipsis"), 0, wx.LEFT | wx.TOP, 5)
        self._combo_narrow = SearchableIconCombo(panel, items, current_key="weather_lightning_icon", fixed_width=75)
        sizer.Add(self._combo_narrow, 0, wx.LEFT, 10)

        sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 2)

        # === 3. Button-based Icon Picker (Simple Approach) ===
        section_button = wx.StaticText(panel, label="=== 3. Button-based Icon Picker (Simple) ===")
        section_button.SetFont(section_button.GetFont().Bold())
        sizer.Add(section_button, 0, wx.LEFT | wx.TOP, 10)

        # Control 3a: Button auto width
        sizer.Add(wx.StaticText(panel, label="3a. BUTTON (Auto width): Simple button opens popup"), 0, wx.LEFT | wx.TOP, 5)
        self._btn_picker_auto = IconPickerButton(panel, items, current_key="bell_icon")
        sizer.Add(self._btn_picker_auto, 0, wx.LEFT, 10)

        # Control 3b: Button 100px
        sizer.Add(wx.StaticText(panel, label="3b. BUTTON (100px): Fixed width with ellipsis"), 0, wx.LEFT | wx.TOP, 5)
        self._btn_picker_narrow = IconPickerButton(panel, items, current_key="weather_lightning_icon", fixed_width=120)
        sizer.Add(self._btn_picker_narrow, 0, wx.LEFT, 10)

        sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 2)

        # === 4. MiniFrame-based Icon Picker (Recommended - cross-platform) ===
        section_mf = wx.StaticText(panel, label="=== 4. MiniFrame-based Icon Picker (Recommended) ===")
        section_mf.SetFont(section_mf.GetFont().Bold())
        sizer.Add(section_mf, 0, wx.LEFT | wx.TOP, 10)

        # Control 4a: MiniFrame button auto width - starts with "No icon" to test visual appearance
        sizer.Add(wx.StaticText(panel, label="4a. MINIFRAME (Auto width): Starts with 'No icon' - button should look active"), 0, wx.LEFT | wx.TOP, 5)
        self._btn_mf_auto = IconPickerButtonMF(panel, items, current_key="")
        sizer.Add(self._btn_mf_auto, 0, wx.LEFT, 10)

        # Control 4b: MiniFrame button 120px with comparison standard button
        sizer.Add(wx.StaticText(panel, label="4b. MINIFRAME (120px) + Standard Button for focus comparison:"), 0, wx.LEFT | wx.TOP, 5)
        row_4b = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_mf_narrow = IconPickerButtonMF(panel, items, current_key="weather_lightning_icon", fixed_width=120)
        row_4b.Add(self._btn_mf_narrow, 0)
        row_4b.Add((10, 0))  # Spacer
        self._btn_compare = wx.Button(panel, label="Standard Button")
        row_4b.Add(self._btn_compare, 0)
        sizer.Add(row_4b, 0, wx.LEFT, 10)

        sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 2)

        # Control 5: Test text control
        sizer.Add(wx.StaticText(panel, label="5. TextCtrl (Tab navigation test):"), 0, wx.LEFT | wx.TOP, 5)
        self._test_text = wx.TextCtrl(panel, value="Tab here to test focus")
        sizer.Add(self._test_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Status
        sizer.Add((0, 20))
        self._status = wx.StaticText(panel, label="Select an icon or Tab between controls")
        self._status.SetFont(self._status.GetFont().Bold())
        sizer.Add(self._status, 0, wx.ALL, 10)

        # Bind selection events for custom combos
        self._combo_stretched.Bind(wx.EVT_COMBOBOX_CLOSEUP, self._on_select)
        self._combo_auto.Bind(wx.EVT_COMBOBOX_CLOSEUP, self._on_select)
        self._combo_narrow.Bind(wx.EVT_COMBOBOX_CLOSEUP, self._on_select)

        panel.SetSizer(sizer)

        # Set tab order: 1a -> 1b -> 2a -> 2b -> 2c -> 3a -> 3b -> 4a -> 4b -> StdBtn -> 5
        self._combo_ownerdrawn.MoveAfterInTabOrder(self._combo_bitmap)
        self._combo_stretched.MoveAfterInTabOrder(self._combo_ownerdrawn)
        self._combo_auto.MoveAfterInTabOrder(self._combo_stretched)
        self._combo_narrow.MoveAfterInTabOrder(self._combo_auto)
        self._btn_picker_auto.MoveAfterInTabOrder(self._combo_narrow)
        self._btn_picker_narrow.MoveAfterInTabOrder(self._btn_picker_auto)
        self._btn_mf_auto.MoveAfterInTabOrder(self._btn_picker_narrow)
        self._btn_mf_narrow.MoveAfterInTabOrder(self._btn_mf_auto)
        self._btn_compare.MoveAfterInTabOrder(self._btn_mf_narrow)
        self._test_text.MoveAfterInTabOrder(self._btn_compare)

        self.Centre()

    def _on_select(self, event):
        combo = event.GetEventObject()
        key = combo.GetSelectedKey()
        label = combo.GetValue()
        self._status.SetLabel(f"Selected: {key} = \"{label}\"")
        event.Skip()


def main():
    app = wx.App()
    frame = DemoFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
