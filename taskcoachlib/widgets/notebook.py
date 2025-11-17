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


class GridCursor:
    """Utility class to help when adding controls to a GridBagSizer."""

    def __init__(self, columns):
        self.__columns = columns
        self.__nextPosition = (0, 0)

    def __updatePosition(self, colspan):
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
        self.__updatePosition(colspan)
        return row, column

    def maxRow(self):
        row, column = self.__nextPosition
        return max(0, row - 1) if column == 0 else row


class BookPage(wx.Panel):
    """A page in a notebook."""

    def __init__(self, parent, columns, growableColumn=None, *args, **kwargs):
        super().__init__(parent, style=wx.TAB_TRAVERSAL, *args, **kwargs)
        self._sizer = wx.GridBagSizer(vgap=5, hgap=5)
        self._columns = columns
        self._position = GridCursor(columns)
        if growableColumn is None:
            self._growableColumn = columns - 1
        else:
            self._growableColumn = growableColumn
        self._borderWidth = 5

    def fit(self):
        self.SetSizer(self._sizer)  # Changed from SetSizerAndFit to prevent locking MinSize

    def __defaultFlags(self, controls):
        """Return the default flags for placing a list of controls."""
        labelInFirstColumn = type(controls[0]) in [type(""), type("")]
        flags = []
        for columnIndex in range(len(controls)):
            flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL
            if columnIndex == 0 and labelInFirstColumn:
                flag |= wx.ALIGN_LEFT
            else:
                flag |= wx.ALIGN_RIGHT | wx.EXPAND
            flags.append(flag)
        return flags

    def __determineFlags(self, controls, flagsPassed):
        """Return a merged list of flags by overriding the default
        flags with flags passed by the caller."""
        flagsPassed = flagsPassed or [None] * len(controls)
        defaultFlags = self.__defaultFlags(controls)
        return [
            defaultFlag if flagPassed is None else flagPassed
            for flagPassed, defaultFlag in zip(flagsPassed, defaultFlags)
        ]

    def addEntry(self, *controls, **kwargs):
        """Add a number of controls to the page. All controls are
        placed on one row, and together they form one entry. E.g. a
        label, a text field and an explanatory label. The default
        flags for placing the controls can be overridden by
        providing a keyword parameter 'flags'. flags should be a
        list of flags (wx.ALIGN_LEFT and the like). The list may
        contain None for controls that should be placed using the default
        flag. If the flags list is shorter than the number of
        controls it is extended with as much 'None's as needed.
        So, addEntry(aLabel, aTextCtrl, flags=[None, wx.ALIGN_LEFT])
        will place the label with the default flag and will place the
        textCtrl left aligned."""
        flags = self.__determineFlags(controls, kwargs.get("flags", None))
        controls = [
            self.__createStaticTextControlIfNeeded(control)
            for control in controls
            if control is not None
        ]
        lastColumnIndex = len(controls) - 1
        for columnIndex, control in enumerate(controls):
            self.__addControl(
                columnIndex,
                control,
                flags[columnIndex],
                lastColumn=columnIndex == lastColumnIndex,
            )
            if columnIndex > 0:
                control.MoveAfterInTabOrder(controls[columnIndex - 1])
        if kwargs.get("growable", False):
            self._sizer.AddGrowableRow(self._position.maxRow())
        # Move growable column definition here
        # There are asserts to fail if the column is already
        # marked growable or if there is no column yet created
        if (
            self._growableColumn > -1
            and self._growableColumn >= lastColumnIndex
        ):
            self._sizer.AddGrowableCol(self._growableColumn)
            self._growableColumn = -1

    def addLine(self):
        line = wx.StaticLine(self)
        self.__addControl(
            0, line, flag=wx.GROW | wx.ALIGN_CENTER_VERTICAL, lastColumn=True
        )

    def __addControl(self, columnIndex, control, flag, lastColumn):
        colspan = max(self._columns - columnIndex, 1) if lastColumn else 1
        self._sizer.Add(
            control,
            self._position.next(colspan),
            span=(1, colspan),
            flag=flag,
            border=self._borderWidth,
        )

    def __createStaticTextControlIfNeeded(self, control):
        if type(control) in [type(""), type("")]:
            control = wx.StaticText(self, label=control)
        return control


class BookMixin(object):
    """Mixin class for *book"""

    _bitmapSize = (16, 16)
    pageChangedEvent = "Subclass responsibility"

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, -1, *args, **kwargs)
        self.Bind(self.pageChangedEvent, self.onPageChanged)

    def __getitem__(self, index):
        """More pythonic way to get a specific page, also useful for iterating
        over all pages, e.g: for page in notebook: ..."""
        if index < self.GetPageCount():
            return self.GetPage(index)
        else:
            raise IndexError

    def onPageChanged(self, event):
        """Can be overridden in a subclass to do something useful."""
        event.Skip()

    def AddPage(self, page, name, bitmap=None):
        """Override AddPage to allow for simply specifying the bitmap name."""
        bitmap = wx.ArtProvider.GetBitmap(
            bitmap, wx.ART_MENU, self._bitmapSize
        )
        super().AddPage(page, name, bitmap=bitmap)

    def ok(self, *args, **kwargs):
        for page in self:
            page.ok(*args, **kwargs)


class Notebook(BookMixin, aui.AuiNotebook):
    pageChangedEvent = aui.EVT_AUINOTEBOOK_PAGE_CHANGED

    def __init__(self, *args, **kwargs):
        defaultStyle = kwargs.get("agwStyle", aui.AUI_NB_DEFAULT_STYLE)
        kwargs["agwStyle"] = (
            defaultStyle
            & ~aui.AUI_NB_CLOSE_ON_ACTIVE_TAB
            & ~aui.AUI_NB_MIDDLE_CLICK_CLOSE
        )
        super().__init__(*args, **kwargs)
