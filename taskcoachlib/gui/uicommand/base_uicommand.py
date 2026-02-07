"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2008 Rob McMullen <rob.mcmullen@gmail.com>

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
from taskcoachlib import operating_system
from taskcoachlib.gui.newid import IdProvider
from taskcoachlib.meta.debug import log_step


""" User interface commands (subclasses of UICommand) are actions that can
    be invoked by the user via the user interface (menu's, toolbar, etc.).
    See the Taskmaster pattern described here: 
    http://www.objectmentor.com/resources/articles/taskmast.pdf 
"""  # pylint: disable=W0105


class UICommand(object):
    """Base user interface command. An UICommand is some action that can be
    associated with menu's and/or toolbars. It contains the menutext and
    helptext to be displayed, code to deal with wx.EVT_UPDATE_UI and
    methods to attach the command to a menu or toolbar. Subclasses should
    implement doCommand() and optionally override enabled()."""

    def __init__(
        self,
        menuText="",
        helpText="",
        bitmap=None,
        kind=wx.ITEM_NORMAL,
        id=None,
        bitmap2=None,
        *args,
        **kwargs
    ):  # pylint: disable=W0622
        super().__init__()
        menuText = menuText or "<%s>" % _("None")
        self.menuText = menuText if "&" in menuText else "&" + menuText
        self.helpText = helpText
        self.bitmap = bitmap
        self.bitmap2 = bitmap2
        self.kind = kind
        self.id = IdProvider.get()
        self.toolbar = None
        self.menuItems = []  # uiCommands can be used in multiple menu's

    def __del__(self):
        IdProvider.put(self.id)

    def __eq__(self, other):
        return self is other

    def uniqueName(self):
        return self.__class__.__name__

    def accelerators(self):
        # The ENTER and NUMPAD_ENTER keys are treated differently between platforms...
        if "\t" in self.menuText and (
            "ENTER" in self.menuText or "RETURN" in self.menuText
        ):
            flags = wx.ACCEL_NORMAL
            for key in self.menuText.split("\t")[1].split("+"):
                if key == "Ctrl":
                    flags |= (
                        wx.ACCEL_CMD
                        if operating_system.isMac()
                        else wx.ACCEL_CTRL
                    )
                elif key in ["Shift", "Alt"]:
                    flags |= dict(Shift=wx.ACCEL_SHIFT, Alt=wx.ACCEL_ALT)[key]
                else:
                    assert key in ["ENTER", "RETURN"], key
            return [(flags, wx.WXK_NUMPAD_ENTER, self.id)]
        return []

    def addToMenu(self, menu, window, position=None):
        menuItem = wx.MenuItem(
            menu, self.id, self.menuText, self.helpText, self.kind
        )
        self.menuItems.append(menuItem)
        self.addBitmapToMenuItem(menuItem)
        if position is None:
            menu.Append(menuItem)
        else:
            menu.Insert(position, menuItem)
        self.bind(window, self.id)
        return self.id

    def addBitmapToMenuItem(self, menuItem):
        if (
            self.bitmap2
            and self.kind == wx.ITEM_CHECK
            and not operating_system.isGTK()
        ):
            bitmap1 = self.__getBitmap(self.bitmap)
            bitmap2 = self.__getBitmap(self.bitmap2)
            menuItem.SetBitmaps(bitmap1, bitmap2)
        elif self.kind == wx.ITEM_NORMAL:
            if self.bitmap is None:
                return  # No icon intended - correct, do nothing

            bitmap = self.__getBitmap(self.bitmap)
            if not bitmap.IsOk():
                # TRAP: bitmap name given but invalid - this is an error
                log_step("ERROR: invalid bitmap '%s' for menu item '%s'" %
                         (self.bitmap, menuItem.GetItemLabelText()), prefix="ICON")
                return

            menuItem.SetBitmap(bitmap)

    def removeFromMenu(self, menu, window):
        for menuItem in self.menuItems:
            if menuItem.GetMenu() == menu:
                self.menuItems.remove(menuItem)
                menuId = menuItem.GetId()
                menu.Remove(menuId)
                break
        self.unbind(window, menuId)

    def appendToToolBar(self, toolbar):
        self.toolbar = toolbar
        bitmap = self.__getBitmap(
            self.bitmap, wx.ART_TOOLBAR, toolbar.GetToolBitmapSize()
        )
        toolbar.AddLabelTool(
            self.id,
            "",
            bitmap,
            wx.NullBitmap,
            self.kind,
            shortHelp=wx.MenuItem.GetLabelText(self.menuText),
            longHelp=self.helpText,
        )
        self.bind(toolbar, self.id)
        return self.id

    def bind(self, window, itemId):
        window.Bind(wx.EVT_MENU, self.onCommandActivate, id=itemId)
        window.Bind(wx.EVT_UPDATE_UI, self.onUpdateUI, id=itemId)

    def unbind(self, window, itemId):
        for eventType in [wx.EVT_MENU, wx.EVT_UPDATE_UI]:
            window.Unbind(eventType, id=itemId)

    def onCommandActivate(self, event, *args, **kwargs):
        """For Menu's and ToolBars, activating the command is not
        possible when not enabled, because menu items and toolbar
        buttons are disabled through onUpdateUI. For other controls such
        as the ListCtrl and the TreeCtrl the EVT_UPDATE_UI event is not
        sent, so we need an explicit check here. Otherwise hitting return
        on an empty selection in the ListCtrl would bring up the
        TaskEditor."""
        if self.enabled(event):
            return self.doCommand(event, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.onCommandActivate(*args, **kwargs)

    def doCommand(self, event):
        raise NotImplementedError  # pragma: no cover

    def onUpdateUI(self, event):
        event.Enable(bool(self.enabled(event)))
        if self.toolbar and (not self.helpText or self.menuText == "?"):
            self.updateToolHelp()

    def enabled(self, event):  # pylint: disable=W0613
        """Can be overridden in a subclass."""
        return True

    def updateToolHelp(self):
        if not self.toolbar:
            return  # Not attached to a toolbar or it's hidden
        shortHelp = wx.MenuItem.GetLabelText(self.getMenuText())
        if shortHelp != self.toolbar.GetToolShortHelp(self.id):
            self.toolbar.SetToolShortHelp(self.id, shortHelp)
        longHelp = self.getHelpText()
        if longHelp != self.toolbar.GetToolLongHelp(self.id):
            self.toolbar.SetToolLongHelp(self.id, longHelp)

    def updateMenuText(self, menuText):
        self.menuText = menuText
        # SetItemLabel works on all platforms in modern wxPython 4.x
        # The old Windows-specific code that deleted/inserted menu items
        # was causing access violations when popup menus were displayed.
        for menuItem in self.menuItems:
            try:
                menuItem.SetItemLabel(menuText)
            except Exception:
                pass  # Ignore errors from deleted menu items

    def mainWindow(self):
        return wx.GetApp().TopWindow

    def getMenuText(self):
        return self.menuText

    def getHelpText(self):
        return self.helpText

    def __getBitmap(
        self, bitmapName, bitmapType=wx.ART_MENU, bitmapSize=(16, 16)
    ):
        return wx.ArtProvider.GetBitmap(bitmapName, bitmapType, bitmapSize)
