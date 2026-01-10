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

import wx, re, sre_constants
from taskcoachlib.widgets import tooltip
from taskcoachlib.i18n import _


class SearchCtrl(tooltip.ToolTipMixin, wx.Panel):
    """SearchCtrl wrapped in tight-fitting panel for Wayland popup compatibility.

    On Wayland, popup menus position relative to their transient parent window.
    When PopupMenu() is called on a widget nested inside containers with spacers,
    the coordinates are relative to a parent container rather than the widget.

    Solution: Wrap the wx.SearchCtrl in a tight-fitting panel and call PopupMenu()
    on the panel at (0, height). Since the panel fits exactly, its origin matches
    the SearchCtrl, positioning the menu correctly.

    See bugs/ISSUE_159_SEARCH_DROPDOWN_POSITION.md for details.
    """

    # Debounce delay in milliseconds - wait this long after user stops typing
    # before triggering the search. This prevents expensive operations on every keystroke.
    SEARCH_DEBOUNCE_DELAY_MS = 500

    def __init__(self, parent, **kwargs):
        self.__callback = kwargs.pop("callback")
        self.__matchCase = kwargs.pop("matchCase", False)
        self.__includeSubItems = kwargs.pop("includeSubItems", False)
        self.__searchDescription = kwargs.pop("searchDescription", False)
        self.__regularExpression = kwargs.pop("regularExpression", False)
        self.__bitmapSize = kwargs.pop("size", (16, 16))
        self.__debounceDelay = kwargs.pop("debounceDelay", self.SEARCH_DEBOUNCE_DELAY_MS)
        value = kwargs.pop("value", "")

        # Initialize wx.Panel first (don't use super() yet - tooltip mixin needs __searchCtrl)
        wx.Panel.__init__(self, parent)

        # Create internal SearchCtrl in tight-fitting sizer
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.__searchCtrl = wx.SearchCtrl(self, **kwargs)
        sizer.Add(self.__searchCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)

        # Delay tooltip mixin initialization until after widget is realized
        wx.CallAfter(self._initTooltipMixin)

        # Configure the search control
        self.__searchCtrl.SetSearchMenuBitmap(
            self.getBitmap("magnifier_glass_dropdown_icon")
        )
        self.__searchCtrl.SetSearchBitmap(self.getBitmap("magnifier_glass_icon"))
        self.__searchCtrl.SetCancelBitmap(self.getBitmap("cross_red_icon"))
        self.__timer = wx.Timer(self)
        self.__recentSearches = []
        self.__maxRecentSearches = 5
        self.__tooltip = tooltip.SimpleToolTip(self.__searchCtrl)
        self.createMenu()
        self.bindEventHandlers()
        self.__searchCtrl.SetValue(value)

    def _initTooltipMixin(self):
        """Initialize tooltip mixin after widget is realized."""
        tooltip.ToolTipMixin.__init__(self)

    def GetMainWindow(self):
        return self.__searchCtrl

    def getTextCtrl(self):
        textCtrl = [
            child
            for child in self.__searchCtrl.GetChildren()
            if isinstance(child, wx.TextCtrl)
        ]
        return textCtrl[0] if textCtrl else self.__searchCtrl

    def getBitmap(self, bitmap):
        return wx.ArtProvider.GetBitmap(
            bitmap, wx.ART_TOOLBAR, self.__bitmapSize
        )

    def createMenu(self):
        # pylint: disable=W0201
        menu = wx.Menu()
        self.__matchCaseMenuItem = menu.AppendCheckItem(
            wx.ID_ANY, _("&Match case"), _("Match case when filtering")
        )
        self.__matchCaseMenuItem.Check(self.__matchCase)
        self.__includeSubItemsMenuItem = menu.AppendCheckItem(
            wx.ID_ANY,
            _("&Include sub items"),
            _("Include sub items of matching items in the search results"),
        )
        self.__includeSubItemsMenuItem.Check(self.__includeSubItems)
        self.__searchDescriptionMenuItem = menu.AppendCheckItem(
            wx.ID_ANY,
            _("&Search description too"),
            _("Search both subject and description"),
        )
        self.__searchDescriptionMenuItem.Check(self.__searchDescription)
        self.__regularExpressionMenuItem = menu.AppendCheckItem(
            wx.ID_ANY,
            _("&Regular Expression"),
            _("Consider search text as a regular expression"),
        )
        self.__regularExpressionMenuItem.Check(self.__regularExpression)
        self.__searchCtrl.SetMenu(menu)

    def PopupMenu(self):  # pylint: disable=W0221
        """Show the search options menu below the control.

        Wayland fix: Call PopupMenu on this panel (tight container) at (0, height).
        This establishes the correct transient parent relationship.
        """
        if hasattr(self, 'HideTip'):
            self.HideTip()
        menu = self.__searchCtrl.GetMenu()
        if menu:
            height = self.GetSize().GetHeight()
            wx.Panel.PopupMenu(self, menu, wx.Point(0, height))

    def bindEventHandlers(self):
        # pylint: disable=W0142,W0612,W0201
        # Bind events to internal search control
        self.__searchCtrl.Bind(wx.EVT_TEXT_ENTER, self.onFind)
        self.__searchCtrl.Bind(wx.EVT_TEXT, self.onFindLater)
        self.__searchCtrl.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self.onCancel)
        self.__searchCtrl.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self._onSearchBtn)

        # Bind menu events
        self.__searchCtrl.Bind(wx.EVT_MENU, self.onMatchCaseMenuItem, self.__matchCaseMenuItem)
        self.__searchCtrl.Bind(wx.EVT_MENU, self.onIncludeSubItemsMenuItem, self.__includeSubItemsMenuItem)
        self.__searchCtrl.Bind(wx.EVT_MENU, self.onSearchDescriptionMenuItem, self.__searchDescriptionMenuItem)
        self.__searchCtrl.Bind(wx.EVT_MENU, self.onRegularExpressionMenuItem, self.__regularExpressionMenuItem)

        # Bind timer to panel
        self.Bind(wx.EVT_TIMER, self.onFind, self.__timer)

        # Precreate menu item ids for the recent searches
        self.__recentSearchMenuItemIds = [
            wx.NewId() for dummy in range(self.__maxRecentSearches)
        ]
        self.__searchCtrl.Bind(
            wx.EVT_MENU_RANGE,
            self.onRecentSearchMenuItem,
            id=self.__recentSearchMenuItemIds[0],
            id2=self.__recentSearchMenuItemIds[-1],
        )
        # Stop timer on window destruction to prevent crashes
        self.Bind(wx.EVT_WINDOW_DESTROY, self._onDestroy)

    def _onSearchBtn(self, event):
        """Intercept search button click to show menu with correct positioning."""
        self.PopupMenu()
        # Don't skip - we handle the menu ourselves

    def setMatchCase(self, matchCase):
        self.__matchCase = matchCase
        self.__matchCaseMenuItem.Check(matchCase)

    def setIncludeSubItems(self, includeSubItems):
        self.__includeSubItems = includeSubItems
        self.__includeSubItemsMenuItem.Check(includeSubItems)

    def setSearchDescription(self, searchDescription):
        self.__searchDescription = searchDescription
        self.__searchDescriptionMenuItem.Check(searchDescription)

    def setRegularExpression(self, regularExpression):
        self.__regularExpression = regularExpression
        self.__regularExpressionMenuItem.Check(regularExpression)

    def isValid(self):
        if self.__regularExpression:
            try:
                re.compile(self.__searchCtrl.GetValue())
            except sre_constants.error:
                return False
        return True

    def _onDestroy(self, event):
        """Automatically cleanup timer on window destruction."""
        if event.GetEventObject() == self:
            self.cleanup()
        event.Skip()

    def cleanup(self):
        """Stop the timer and clear callback to prevent crashes."""
        if self.__timer and self.__timer.IsRunning():
            self.__timer.Stop()
        self.__callback = lambda *args, **kwargs: None

    def onFindLater(self, event):  # pylint: disable=W0613
        """Debounce search operations using a timer."""
        self.__timer.Start(self.__debounceDelay, oneShot=True)

    def onFind(self, event):  # pylint: disable=W0613
        """Execute the actual search operation."""
        if self.__timer.IsRunning():
            self.__timer.Stop()
        if not self.IsEnabled():
            return
        if not self.isValid():
            self.__tooltip.SetData(
                [
                    (
                        None,
                        [
                            _("This is an invalid regular expression."),
                            _("Defaulting to substring search."),
                        ],
                    )
                ]
            )
            x, y = self.GetParent().ClientToScreen(*self.GetPosition())
            height = self.GetClientSize()[1]
            if hasattr(self, 'DoShowTip'):
                self.DoShowTip(x + 3, y + height + 4, self.__tooltip)
        else:
            if hasattr(self, 'HideTip'):
                self.HideTip()
        searchString = self.__searchCtrl.GetValue()
        if searchString:
            self.rememberSearchString(searchString)
        self.__searchCtrl.ShowCancelButton(bool(searchString))
        self.__callback(
            searchString,
            self.__matchCase,
            self.__includeSubItems,
            self.__searchDescription,
            self.__regularExpression,
        )

    def onCancel(self, event):
        """Handle search cancellation (clear button clicked)."""
        self.__searchCtrl.SetValue("")
        self.onFind(event)
        event.Skip()

    def onMatchCaseMenuItem(self, event):
        self.__matchCase = self._isMenuItemChecked(event)
        self.onFind(event)

    def onIncludeSubItemsMenuItem(self, event):
        self.__includeSubItems = self._isMenuItemChecked(event)
        self.onFind(event)

    def onSearchDescriptionMenuItem(self, event):
        self.__searchDescription = self._isMenuItemChecked(event)
        self.onFind(event)

    def onRegularExpressionMenuItem(self, event):
        self.__regularExpression = self._isMenuItemChecked(event)
        self.onFind(event)

    def onRecentSearchMenuItem(self, event):
        self.__searchCtrl.SetValue(
            self.__recentSearches[
                event.GetId() - self.__recentSearchMenuItemIds[0]
            ]
        )
        self.onFind(event)

    def rememberSearchString(self, searchString):
        if searchString in self.__recentSearches:
            self.__recentSearches.remove(searchString)
        self.__recentSearches.insert(0, searchString)
        if len(self.__recentSearches) > self.__maxRecentSearches:
            self.__recentSearches.pop()
        self.updateRecentSearches()

    def updateRecentSearches(self):
        menu = self.__searchCtrl.GetMenu()
        self.removeRecentSearches(menu)
        self.addRecentSearches(menu)

    def removeRecentSearches(self, menu):
        while menu.GetMenuItemCount() > 4:
            item = menu.FindItemByPosition(4)
            menu.DestroyItem(item)

    def addRecentSearches(self, menu):
        menu.AppendSeparator()
        item = menu.Append(wx.ID_ANY, _("Recent searches"))
        item.Enable(False)
        for index, searchString in enumerate(self.__recentSearches):
            menu.Append(self.__recentSearchMenuItemIds[index], searchString)

    def Enable(self, enable=True):  # pylint: disable=W0221
        """When wx.SearchCtrl is disabled it doesn't grey out the buttons."""
        self.__searchCtrl.SetValue("" if enable else _("Viewer not searchable"))
        self.__searchCtrl.Enable(enable)
        self.__searchCtrl.ShowCancelButton(enable and bool(self.__searchCtrl.GetValue()))
        self.__searchCtrl.ShowSearchButton(enable)

    def _isMenuItemChecked(self, event):
        try:
            return (
                event.GetEventObject().FindItemById(event.GetId()).IsChecked()
            )
        except AttributeError:
            return event.IsChecked()

    def OnBeforeShowToolTip(self, x, y):
        return None

    # Forward common wx.SearchCtrl methods to internal control
    def GetValue(self):
        return self.__searchCtrl.GetValue()

    def SetValue(self, value):
        return self.__searchCtrl.SetValue(value)

    def SetFocus(self):
        return self.__searchCtrl.SetFocus()

    def ShowCancelButton(self, show):
        return self.__searchCtrl.ShowCancelButton(show)

    def ShowSearchButton(self, show):
        return self.__searchCtrl.ShowSearchButton(show)

    def GetMenu(self):
        return self.__searchCtrl.GetMenu()

    def SetMenu(self, menu):
        return self.__searchCtrl.SetMenu(menu)
