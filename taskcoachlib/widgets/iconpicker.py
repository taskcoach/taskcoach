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
from taskcoachlib.gui.icons.icon_library import LIST_ICON_SIZE


class _IconListCtrl(wx.ListCtrl):
    """List control with 5 columns: Label (with icon), Hints, Theme, Context, Key."""

    COL_ICON_ID = 4

    def __init__(self, parent):
        super().__init__(parent, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_NONE)

        # Image list for icons
        self._image_list = wx.ImageList(LIST_ICON_SIZE, LIST_ICON_SIZE)
        self.SetImageList(self._image_list, wx.IMAGE_LIST_SMALL)

        # 5 columns: Label (with icon), Hints, Theme, Context, Key
        self.InsertColumn(0, _("Label"), width=200)
        self.InsertColumn(1, _("Hints"), width=250)
        self.InsertColumn(2, _("Theme"), width=70)
        self.InsertColumn(3, _("Context"), width=80)
        self.InsertColumn(4, _("Key"), width=150)

        self._items = []
        self._all_items = []
        self._image_map = {}  # icon_id -> image list index
        self._enabled_ids = set()
        self._current_selected_row = None
        self._on_select_callback = None

        # Debounce timer for search filtering
        self._filter_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_filter_timer, self._filter_timer)
        self._pending_filter = ""

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_item_activated)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

    def SetItems(self, items, current_icon_id=""):
        """Set items: list of (icon_id, label, bitmap, hints, theme, context, enabled) tuples."""
        self._all_items = list(items)
        self._items = list(items)
        self._rebuild_list(current_icon_id)

    def _rebuild_list(self, current_icon_id=""):
        """Rebuild the list from current _items, optionally selecting current_icon_id inline."""
        self.DeleteAllItems()
        self._enabled_ids = set()
        self._current_selected_row = None

        for i, item in enumerate(self._items):
            icon_id, label, bmp, hints, theme, context, enabled = item

            if enabled:
                self._enabled_ids.add(icon_id)

            # Add bitmap to image list if not already there
            if icon_id not in self._image_map:
                if bmp and bmp.IsOk():
                    idx = self._image_list.Add(bmp)
                else:
                    idx = -1  # No image
                self._image_map[icon_id] = idx

            # Insert row: Label (with icon), Hints, Theme, Context, icon_id
            idx = self.InsertItem(i, label, self._image_map.get(icon_id, -1))
            self.SetItem(idx, 1, hints or "")
            self.SetItem(idx, 2, theme or "")
            self.SetItem(idx, 3, context or "")
            self.SetItem(idx, 4, icon_id)

            # Grey out disabled items
            if not enabled:
                self.SetItemTextColour(idx, wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

            if icon_id == current_icon_id:
                self._try_select_current(i, icon_id)

    def _try_select_current(self, row_index, icon_id):
        """Select row during _rebuild_list. Logs error on duplicate icon_id."""
        if self._current_selected_row is None:
            self.Select(row_index)
            self.EnsureVisible(row_index)
            self._current_selected_row = row_index
        else:
            log_step("ERROR: Duplicate icon_id '{}' at row {}, already selected at row {}".format(
                icon_id, row_index, self._current_selected_row), prefix="ICON")

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
            # Split into terms - ALL terms must match (AND search)
            terms = filter_text.lower().split()
            self._items = [
                item for item in self._all_items
                if self._matches_all_terms(item, terms)
            ]
        self._rebuild_list()

        # Select first enabled item
        for i, item in enumerate(self._items):
            if item[6]:  # enabled
                self.Select(i)
                self.EnsureVisible(i)
                break

    def _matches_all_terms(self, item, terms):
        """Return True if ALL terms are found in item's searchable fields (AND search).

        Searches icon_id, label, hints. Theme and context are included based on
        iconpicker preferences (search_include_theme, search_include_context).
        """
        icon_id = item[0].lower()
        label = item[1].lower()
        hints = item[3].lower()
        theme = item[4].lower()
        context = item[5].lower()

        # Build searchable string based on preferences
        searchable = icon_id + " " + label + " " + hints

        from taskcoachlib.config import settings2
        if settings2.iconpicker.search_include_theme:
            searchable += " " + theme
        if settings2.iconpicker.search_include_context:
            searchable += " " + context

        return all(term in searchable for term in terms)

    def GetSelectedIconId(self):
        """Return icon_id of selected row, "" if nothing selected, None if disabled."""
        sel = self.GetFirstSelected()
        if sel == -1:
            return ""
        icon_id = self.GetItemText(sel, self.COL_ICON_ID)
        if icon_id not in self._enabled_ids:
            return None
        return icon_id

    def SetSelectCallback(self, callback):
        """Set callback for double-click/enter selection."""
        self._on_select_callback = callback

    def _on_item_activated(self, event):
        """Handle double-click or enter on item."""
        icon_id = self.GetSelectedIconId()
        if icon_id and self._on_select_callback:
            self._on_select_callback(icon_id)

    def _on_key_down(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_RETURN or key == wx.WXK_NUMPAD_ENTER:
            icon_id = self.GetSelectedIconId()
            if icon_id and self._on_select_callback:
                self._on_select_callback(icon_id)
        else:
            event.Skip()


class _IconDialog(wx.Dialog):
    """Modal dialog with searchable icon list."""

    def __init__(self, parent, current_icon_id, exclude=None, allow_clear=True):
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        super().__init__(parent, title=_("Choose Icon"), style=style)
        self._selected_icon_id = None
        self._exclude = exclude

        panel = wx.Panel(self, style=wx.BORDER_NONE | wx.TAB_TRAVERSAL)
        panel.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))

        sizer = wx.BoxSizer(wx.VERTICAL)
        self._search = wx.SearchCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self._search.SetDescriptiveText(_("Search icons..."))
        self._search.ShowCancelButton(True)
        sizer.Add(self._search, 0, wx.EXPAND | wx.ALL, 5)

        items = self._load_icons()
        self._listbox = _IconListCtrl(panel)
        self._listbox.SetItems(items, current_icon_id)
        self._listbox.SetSelectCallback(self._on_item_selected)
        sizer.Add(self._listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        panel.SetSizer(sizer)

        # Dialog layout: panel (search + list) + button bar
        dlgSizer = wx.BoxSizer(wx.VERTICAL)
        dlgSizer.Add(panel, 1, wx.EXPAND)

        # Button bar: Clear (optional) + OK + Cancel
        btnSizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        if allow_clear:
            self._clearBtn = wx.Button(self, wx.ID_CLEAR, _("Clear"))
            # Insert Clear at the beginning (index 0)
            btnSizer.Insert(0, self._clearBtn, 0, wx.LEFT | wx.RIGHT, 5)
            btnSizer.Insert(1, (0, 0), 1)  # Stretch spacer after Clear
            self.Bind(wx.EVT_BUTTON, self._on_clear, id=wx.ID_CLEAR)
        dlgSizer.Add(btnSizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(dlgSizer)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

        # Dialog size: fixed width, 75% of screen height
        display = wx.Display(wx.Display.GetFromWindow(parent))
        screen_height = display.GetClientArea().GetHeight()
        total_height = int(screen_height * 0.75)

        self._desired_size = wx.Size(700, total_height)

        def _on_shown(evt):
            self.SetSize(self._desired_size)
            self.CentreOnParent()
            evt.Skip()
        self.Bind(wx.EVT_SHOW, _on_shown)

        self._search.Bind(wx.EVT_TEXT, lambda e: self._listbox.FilterItems(self._search.GetValue()))
        self._search.Bind(wx.EVT_TEXT_ENTER, self._on_enter)
        self._search.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self._search.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self._on_cancel)

        wx.CallAfter(self._focus_search)

    def _focus_search(self):
        if self._search and self.IsShown():
            self._search.SetFocus()
            self._search.SetInsertionPoint(0)

    def GetSelectedIconId(self):
        """Return the selected icon_id (str), or None if cancelled."""
        return self._selected_icon_id

    def _on_cancel(self, event):
        self._search.SetValue("")
        self._listbox.FilterItems("")

    def _on_enter(self, event):
        icon_id = self._listbox.GetSelectedIconId()
        if icon_id:
            self._on_item_selected(icon_id)

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
        icon_id = self._listbox.GetSelectedIconId()
        if icon_id:
            self._selected_icon_id = icon_id
            self.EndModal(wx.ID_OK)

    def _on_clear(self, event):
        """Clear button — select no icon (empty icon_id)."""
        self._selected_icon_id = ""
        self.EndModal(wx.ID_OK)

    def _on_item_selected(self, icon_id):
        self._selected_icon_id = icon_id
        self.EndModal(wx.ID_OK)

    def _get_excluded_icons(self):
        """Resolve excluded icon_ids based on self._exclude mode.

        None: no exclusion
        "status": exclude icons used in status configuration
        "data": exclude icons used by tasks, categories, and notes
        """
        if self._exclude is None:
            return set()
        app = wx.GetApp()
        settings = app.settings
        if self._exclude == "status":
            excluded = set()
            for key in ["activetasks", "latetasks", "completedtasks",
                        "overduetasks", "inactivetasks", "duesoontasks"]:
                excluded.add(settings.gettext("icon", key))
                excluded.add(settings.gettext("icon_dark", key))
            excluded.discard("")
            return excluded
        if self._exclude == "data":
            excluded = set()
            taskFile = getattr(app, "taskFile", None)
            if taskFile is None:
                return excluded
            for obj in taskFile.tasks():
                icon_id = obj.icon_id()
                if icon_id:
                    excluded.add(icon_id)
            for obj in taskFile.categories():
                icon_id = obj.icon_id()
                if icon_id:
                    excluded.add(icon_id)
            for obj in taskFile.notes():
                icon_id = obj.icon_id()
                if icon_id:
                    excluded.add(icon_id)
            return excluded
        log_step("WARNING: Unknown exclude mode '{}'".format(self._exclude), prefix="ICON")
        return set()

    def _load_icons(self):
        """Load icons from catalog, filtered by enabled themes."""
        from taskcoachlib.gui.icons.icon_library import icon_catalog

        excluded_icons = self._get_excluded_icons()

        # Get enabled themes from settings (legacy always enabled)
        from taskcoachlib.config import settings2
        enabled_themes = {"legacy"}
        if settings2.iconpicker.theme_nuvola:
            enabled_themes.add("nuvola")
        if settings2.iconpicker.theme_oxygen:
            enabled_themes.add("oxygen")
        if settings2.iconpicker.theme_papirus:
            enabled_themes.add("papirus")
        if settings2.iconpicker.theme_breeze:
            enabled_themes.add("breeze")
        if settings2.iconpicker.theme_noto_emoji:
            enabled_themes.add("noto-emoji")
        if settings2.iconpicker.theme_taskcoach:
            enabled_themes.add("taskcoach")

        # Load icons from catalog, sort by label
        icon_ids = sorted(
            icon_catalog.viewer_icon_ids(),
            key=lambda k: (icon_catalog.get_icon(k).label or k)
        )
        items = []
        for icon_id in icon_ids:
            icon = icon_catalog.get_icon(icon_id)
            if not icon or not icon.label:
                continue
            # Skip icons from disabled themes
            if icon.theme not in enabled_themes:
                continue
            bitmap = icon_catalog.get_bitmap(icon_id, LIST_ICON_SIZE)
            hints = " ".join(icon.hints)
            enabled = icon_id not in excluded_icons
            items.append((icon_id, icon.label, bitmap, hints, icon.theme_label, icon.context_label, enabled))
        return items


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
        currentIcon: Currently selected icon_id (empty string for "No icon")
        exclude: None (no exclusion), "status" (exclude status icons), "data" (exclude data icons)
        noIcon: If True, allow clearing the icon (default: True)
    """

    PADDING = 8
    NO_ICON_LABEL = _("No icon")

    def __init__(self, parent, currentIcon, exclude=None, noIcon=True, fixedWidth=None, *args, **kwargs):
        self._exclude = exclude
        self._noIcon = noIcon
        self._fixedWidth = fixedWidth
        self._current_icon_id = ""
        self._current_label = ""
        self._current_bmp = None
        self._previous_icon_id = ""

        # Initialize button - GenBitmapButton requires a bitmap in constructor,
        # but we immediately clear it. For "no icon" state, bmpLabel stays None.
        # Never call SetBitmapLabel(None) - that hits wxPython bug #2093.
        super().__init__(parent, wx.ID_ANY, wx.Bitmap(1, 1), "", style=wx.BORDER_NONE)
        self.bmpLabel = None  # Clear - start with no icon
        self.SetUseFocusIndicator(True)

        self.SetValue(currentIcon or "")
        self._previous_icon_id = self._current_icon_id

        self.Bind(wx.EVT_BUTTON, self._on_click)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

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

    def _update_button(self):
        self.SetLabel(self._current_label or self.NO_ICON_LABEL)
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
        dialog = _IconDialog(self.GetTopLevelParent(), self._current_icon_id, self._exclude, self._noIcon)
        if dialog.ShowModal() == wx.ID_OK:
            icon_id = dialog.GetSelectedIconId()
            if icon_id is not None:
                self._previous_icon_id = self._current_icon_id
                self.SetValue(icon_id)
                evt = wx.CommandEvent(wx.wxEVT_COMBOBOX, self.GetId())
                evt.SetEventObject(self)
                self.GetEventHandler().ProcessEvent(evt)
        dialog.Destroy()

    def GetValue(self):
        """Return the selected icon_id."""
        return self._current_icon_id

    def SetValue(self, icon_id):
        """Set the displayed icon by icon_id."""
        from taskcoachlib.gui.icons.icon_library import icon_catalog

        if icon_id == "":
            if self._noIcon:
                self._current_icon_id = ""
                self._current_label = self.NO_ICON_LABEL
                self._current_bmp = None
            else:
                log_step("ERROR: Received empty icon_id but noIcon=False", prefix="ICON")
                return
        else:
            icon = icon_catalog.get_icon(icon_id)
            if icon:
                self._current_icon_id = icon_id
                self._current_label = icon.label
                self._current_bmp = icon_catalog.get_bitmap(icon_id, LIST_ICON_SIZE)
            else:
                log_step("WARNING: icon_id '{}' not found".format(icon_id), prefix="ICON")
                self._current_icon_id = ""
                self._current_label = self.NO_ICON_LABEL
                self._current_bmp = None
        self._update_button()


def _(text):
    """Placeholder for i18n - will use the actual translation function."""
    return text
