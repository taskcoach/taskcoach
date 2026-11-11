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
import wx.lib.agw.aui as aui
import wx.lib.scrolledpanel as scrolledpanel
from taskcoachlib import patterns
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
from taskcoachlib.widgets.frame import free_with_window, is_whole_layout


class GridCursor:
    """Utility class to help when adding controls to a GridBagSizer."""

    def __init__(self, columns):
        self.__columns = columns
        self.__nextPosition = (0, 0)

    def __update_position(self, colspan):
        """Update the position of the cursor, taking colspan into account."""
        row, column = self.__nextPosition
        if column == self.__columns - colspan:
            row += 1
            column = 0
        else:
            column += colspan
        self.__nextPosition = (row, column)

    def next(self, colspan=1):
        row, column = self.__nextPosition
        self.__update_position(colspan)
        return row, column

    def max_row(self):
        row, column = self.__nextPosition
        return max(0, row - 1) if column == 0 else row


class BookPage(wx.Panel):
    """A page in a notebook."""

    # Outer margin around page content (modern UI best practice: 10-12px)
    _outer_margin = 10
    # Grid spacing - subclasses can override
    _vgap = 0
    _hgap = 5
    _border_width = 5

    def __init__(self, parent, columns, growable_column=None, *args, **kwargs):
        super().__init__(parent, style=wx.TAB_TRAVERSAL, *args, **kwargs)
        self._sizer = wx.GridBagSizer(vgap=self._vgap, hgap=self._hgap)
        self._columns = columns
        self._position = GridCursor(columns)
        if growable_column is None:
            self._growableColumn = columns - 1
        else:
            self._growableColumn = growable_column

    def fit(self):
        # Wrap GridBagSizer in outer BoxSizer with margins for proper spacing
        # Only create the outer sizer once - calling fit() multiple times is safe
        if not hasattr(self, "_outerSizer") or self._outerSizer is None:
            self._outerSizer = wx.BoxSizer(wx.VERTICAL)
            self._outerSizer.Add(
                self._sizer, 1, wx.EXPAND | wx.ALL, self._outer_margin
            )
            self.SetSizer(self._outerSizer)
        self.Layout()  # Force layout recalculation (needed on Windows for lazy-loaded pages)

    def __default_flags(self, controls):
        """Return the default flags for placing a list of controls."""
        flags = []
        for column_index in range(len(controls)):
            flag = wx.ALL | wx.ALIGN_TOP | wx.ALIGN_LEFT
            flags.append(flag)
        return flags

    def __determine_flags(self, controls, flags_passed):
        """Return a merged list of flags by overriding the default
        flags with flags passed by the caller."""
        flags_passed = flags_passed or [None] * len(controls)
        default_flags = self.__default_flags(controls)
        return [
            default_flag if flag_passed is None else flag_passed
            for flag_passed, default_flag in zip(flags_passed, default_flags)
        ]

    def add_entry(self, *controls, **kwargs):
        """Add a number of controls to the page. All controls are
        placed on one row, and together they form one entry. E.g. a
        label, a text field and an explanatory label. The default
        flags for placing the controls can be overridden by
        providing a keyword parameter 'flags'. flags should be a
        list of flags (wx.ALIGN_LEFT and the like). The list may
        contain None for controls that should be placed using the default
        flag. If the flags list is shorter than the number of
        controls it is extended with as much 'None's as needed.
        So, add_entry(aLabel, aTextCtrl, flags=[None, wx.ALIGN_LEFT])
        will place the label with the default flag and will place the
        textCtrl left aligned."""
        flags = self.__determine_flags(controls, kwargs.get("flags", None))
        controls = [
            self.__create_static_text_control_if_needed(control)
            for control in controls
            if control is not None
        ]
        last_column_index = len(controls) - 1
        for column_index, control in enumerate(controls):
            self.__add_control(
                column_index,
                control,
                flags[column_index],
                last_column=column_index == last_column_index,
            )
            if column_index > 0:
                control.MoveAfterInTabOrder(controls[column_index - 1])
        if kwargs.get("growable", False):
            self._sizer.AddGrowableRow(self._position.max_row())
        # Move growable column definition here
        # There are asserts to fail if the column is already
        # marked growable or if there is no column yet created
        if (
            self._growableColumn > -1
            and self._growableColumn >= last_column_index
        ):
            self._sizer.AddGrowableCol(self._growableColumn)
            self._growableColumn = -1

    def add_line(self):
        line = wx.StaticLine(self)
        colspan = max(self._columns, 1)
        self._sizer.Add(
            line,
            self._position.next(colspan),
            span=(1, colspan),
            flag=wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.TOP | wx.BOTTOM,
            border=5,
        )

    def __add_control(self, column_index, control, flag, last_column):
        colspan = max(self._columns - column_index, 1) if last_column else 1
        self._sizer.Add(
            control,
            self._position.next(colspan),
            span=(1, colspan),
            flag=flag,
            border=self._border_width,
        )

    def __create_static_text_control_if_needed(self, control):
        if isinstance(control, str):
            control = wx.StaticText(self, label=control)
        return control


class ScrolledBookPage(scrolledpanel.ScrolledPanel):
    """A scrollable page in a notebook. Use for pages with lots of content."""

    # Outer margin around page content
    _outer_margin = 10
    # Grid spacing - subclasses can override
    _vgap = 0
    _hgap = 5
    _border_width = 5

    def __init__(self, parent, columns, growable_column=None, *args, **kwargs):
        super().__init__(parent, style=wx.TAB_TRAVERSAL, *args, **kwargs)
        self._sizer = wx.GridBagSizer(vgap=self._vgap, hgap=self._hgap)
        self._columns = columns
        self._position = GridCursor(columns)
        if growable_column is None:
            self._growableColumn = columns - 1
        else:
            self._growableColumn = growable_column

    def fit(self):
        # Wrap GridBagSizer in outer BoxSizer with margins for proper spacing
        if not hasattr(self, "_outerSizer") or self._outerSizer is None:
            self._outerSizer = wx.BoxSizer(wx.VERTICAL)
            self._outerSizer.Add(
                self._sizer, 1, wx.EXPAND | wx.ALL, self._outer_margin
            )
            self.SetSizer(self._outerSizer)
        self.SetupScrolling(scroll_x=True, scroll_y=True)
        self.Layout()

    def __default_flags(self, controls):
        """Return the default flags for placing a list of controls."""
        flags = []
        for column_index in range(len(controls)):
            flag = wx.ALL | wx.ALIGN_TOP | wx.ALIGN_LEFT
            flags.append(flag)
        return flags

    def __determine_flags(self, controls, flags_passed):
        """Return a merged list of flags by overriding the default
        flags with flags passed by the caller."""
        flags_passed = flags_passed or [None] * len(controls)
        default_flags = self.__default_flags(controls)
        return [
            default_flag if flag_passed is None else flag_passed
            for flag_passed, default_flag in zip(flags_passed, default_flags)
        ]

    def add_entry(self, *controls, **kwargs):
        """Add controls to the page on one row."""
        flags = self.__determine_flags(controls, kwargs.get("flags", None))
        controls = [
            self.__create_static_text_control_if_needed(control)
            for control in controls
            if control is not None
        ]
        last_column_index = len(controls) - 1
        for column_index, control in enumerate(controls):
            self.__add_control(
                column_index,
                control,
                flags[column_index],
                column_index == last_column_index,
            )
        if kwargs.get("growable", False):
            self._sizer.AddGrowableRow(self._position.max_row())
        # Add growable column once, when first entry has been added
        if (
            self._growableColumn >= 0
            and self._sizer.GetItemCount() >= self._columns
        ):
            self._sizer.AddGrowableCol(self._growableColumn)
            self._growableColumn = -1

    def add_line(self):
        line = wx.StaticLine(self)
        colspan = max(self._columns, 1)
        self._sizer.Add(
            line,
            self._position.next(colspan),
            span=(1, colspan),
            flag=wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.TOP | wx.BOTTOM,
            border=5,
        )

    def __add_control(self, column_index, control, flag, last_column):
        colspan = max(self._columns - column_index, 1) if last_column else 1
        self._sizer.Add(
            control,
            self._position.next(colspan),
            span=(1, colspan),
            flag=flag,
            border=self._border_width,
        )

    def __create_static_text_control_if_needed(self, control):
        if isinstance(control, str):
            control = wx.StaticText(self, label=control)
        return control


def _whole_steps(size, step):
    """Size rounded up to whole steps of step pixels (none: as is)."""
    return -(-size // step) * step if step else size


def _paint_at_next_frame():
    """A tab row's Update() during a tab change: its Refresh() before
    has asked for the paint, at the next frame."""


class BookMixin(object):
    """Mixin class for *book"""

    _bitmap_size = (LIST_ICON_SIZE, LIST_ICON_SIZE)
    page_changed_event = "Subclass responsibility"

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, -1, *args, **kwargs)
        self.Bind(self.page_changed_event, self.on_page_changed)

    def __getitem__(self, index):
        """More pythonic way to get a specific page, also useful for iterating
        over all pages, e.g: for page in notebook: ..."""
        if index < self.GetPageCount():
            return self.GetPage(index)
        else:
            raise IndexError

    def on_page_changed(self, event):
        """Can be overridden in a subclass to do something useful."""
        event.Skip()

    def AddPage(self, page, name, icon_id=None):
        """Override AddPage to allow for simply specifying the icon_id."""
        bitmap = icon_catalog.get_bitmap(icon_id, self._bitmap_size[0])
        super().AddPage(page, name, bitmap=bitmap)

    def ok(self, *args, **kwargs):
        for page in self:
            page.ok(*args, **kwargs)


class Notebook(BookMixin, aui.AuiNotebook):
    page_changed_event = aui.EVT_AUINOTEBOOK_PAGE_CHANGED

    def __init__(self, *args, **kwargs):
        default_style = kwargs.get("agwStyle", aui.AUI_NB_DEFAULT_STYLE)
        kwargs["agwStyle"] = (
            default_style
            & ~aui.AUI_NB_CLOSE_ON_ACTIVE_TAB
            & ~aui.AUI_NB_MIDDLE_CLICK_CLOSE
        )
        super().__init__(*args, **kwargs)
        free_with_window(self, self.GetAuiManager())
        self.__layout_queued = False
        self.GetAuiManager().Update = self.__queue_layout
        # Bind mouse wheel directly on the tab control for tab scrolling
        tab_ctrl = self.GetActiveTabCtrl()
        if tab_ctrl:
            tab_ctrl.Bind(wx.EVT_MOUSEWHEEL, self.__on_tab_mouse_wheel)
        # Disable focus on internal AUI TabFrame to prevent "lost" tab keypress
        self.__disable_tab_frame_focus()

    def __queue_layout(self):
        """AGW's Update(): one queued layout for all the requests made
        before it runs, as AGW queues a whole one for each."""
        if not self.__layout_queued:
            self.__layout_queued = True
            patterns.later.soon(self, self.__layout)

    def __layout(self):
        if self.__layout_queued:
            self.__layout_queued = False
            self.GetAuiManager().DoUpdate()

    def layout_now(self):
        """Lay out the tabs and pages before the first show, so the
        first frame drawn has them (docs/RENDERING_SPEED.md)."""
        self.__layout_queued = True
        self.__layout()

    def LoadPerspective(self, layout):  # noqa: N802 (AGW's)
        """Load a layout SavePerspective wrote; False, the tabs
        unchanged, for one that would leave a page with no tab. AGW
        takes every tab off before it reads the layout, and a page it
        does not find there gets none (#487)."""
        if not self.__shows_every_page(layout):
            return False
        return super().LoadPerspective(layout)

    def __shows_every_page(self, layout):
        """Whether AGW reads the whole layout and every page from it:
        tab lists "name=0,+1,2" joined by "|", then "@" and the frames
        (is_whole_layout)."""
        tabs, at, frames = layout.partition("@")
        if not at or not is_whole_layout(frames):
            return False
        names, pages = [], []
        for tab_list in tabs.split("|"):
            name, equals, numbers = tab_list.partition("=")
            if not equals:
                return False
            names.append(name)
            for number in numbers.split(","):
                if number[:1] in ("+", "*"):
                    number = number[1:]
                if not number.isdigit():
                    return False
                pages.append(int(number))
        return len(set(names)) == len(names) and sorted(pages) == list(
            range(self.GetPageCount())
        )

    def largest_page_size(self):
        """The size that shows each page whole: the largest page's
        content, the tabs above and the border around. Scrolled pages
        report only their margins, so each page's sizer is asked; their
        scroll bars show unless whole scroll steps fit."""
        width = height = 0
        for page in self:
            sizer = page.GetSizer()
            page_width, page_height = (
                sizer.GetMinSize() if sizer else page.GetBestSize()
            )
            if isinstance(page, scrolledpanel.ScrolledPanel):
                step_x, step_y = page.GetScrollPixelsPerUnit()
                page_width = _whole_steps(page_width, step_x)
                page_height = _whole_steps(page_height, step_y)
            width, height = max(width, page_width), max(height, page_height)
        border = 2 * self.GetAuiManager().GetArtProvider().GetMetric(
            aui.AUI_DOCKART_PANE_BORDER_SIZE
        )
        return wx.Size(
            width + border, height + self.GetTabCtrlHeight() + border
        )

    def SetSelection(self, new_page, force=False):
        # AUI shows the page, then paints its tab rows at once
        # (Update()). GTK 3 places a shown page only at the next frame,
        # so that paint drew it unplaced, over the tabs; with the
        # notebook frozen, GTK drew it empty, a blank frame at each tab
        # change. The tab rows paint at the next frame, the page placed
        # (docs/AUI.md#page-painted-over-the-tabs).
        tab_rows = [
            child
            for child in self.GetChildren()
            if isinstance(child, aui.AuiTabCtrl)
            and "Update" not in vars(child)  # Not in a change already
        ]
        for tab_row in tab_rows:
            tab_row.Update = _paint_at_next_frame
        try:
            return super().SetSelection(new_page, force)
        finally:
            for tab_row in tab_rows:
                del tab_row.Update

    def __disable_tab_frame_focus(self):
        """Disable focus on internal AUI TabFrame windows."""
        for child in self.GetChildren():
            if child.__class__.__name__ == "TabFrame":
                child.SetCanFocus(False)

    def __on_tab_mouse_wheel(self, event):
        """Handle mouse wheel scrolling on the tab bar to switch tabs."""
        rotation = event.GetWheelRotation()
        if rotation > 0:
            self.AdvanceSelection(False)  # Previous tab
        elif rotation < 0:
            self.AdvanceSelection(True)  # Next tab

    def advance_selection_forward(self):
        """Move to the next tab (wraps around)."""
        self.AdvanceSelection(True)

    def advance_selection_backward(self):
        """Move to the previous tab (wraps around)."""
        self.AdvanceSelection(False)
