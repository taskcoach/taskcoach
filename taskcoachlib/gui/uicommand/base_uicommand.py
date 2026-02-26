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
from taskcoachlib import operating_system, patterns
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
from taskcoachlib.gui.newid import IdProvider
from taskcoachlib.meta.debug import log_step


""" User interface commands (subclasses of UICommand) are actions that can
    be invoked by the user via the user interface (menu's, toolbar, etc.).
    See the Taskmaster pattern described here:
    http://www.objectmentor.com/resources/articles/taskmast.pdf
"""  # pylint: disable=W0105


class MenuItem(wx.MenuItem):
    """Menu item that knows its command and can update its own enabled state."""

    def __init__(self, command, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._command = command

    def update_state(self):
        enabled = bool(self._command.enabled(None))
        self.Enable(enabled)
        new_text = self._command.current_menu_text()
        if new_text is not None:
            try:
                self.SetItemLabel(new_text)
            except Exception as e:
                log_step("MenuItem.update_state: dead menu item: %s" % e,
                         prefix="DEAD-OBJ")
        if enabled and self.IsCheckable():
            check = self._command.checked()
            if check is not None:
                self.Check(check)


class UICommand(patterns.Observer):
    """Base user interface command. An UICommand is some action that can be
    associated with menus and/or toolbars. It contains the menutext and
    helptext to be displayed and methods to attach the command to a menu
    or toolbar. Subclasses should implement do_command() and optionally
    override enabled()."""

    def __init__(
        self,
        menu_text="",
        help_text="",
        icon_id=None,
        kind=wx.ITEM_NORMAL,
        id=None,
        icon_id2=None,
        *args,
        **kwargs
    ):  # pylint: disable=W0622
        super().__init__()
        menu_text = menu_text or "<%s>" % _("None")
        self.menu_text = menu_text if "&" in menu_text else "&" + menu_text
        self.help_text = help_text
        self.icon_id = icon_id
        self.icon_id2 = icon_id2
        self.kind = kind
        self.id = IdProvider.get()
        self.toolbar = None
        self.menu_items = []  # uiCommands can be used in multiple menu's

    def __del__(self):
        IdProvider.put(self.id)

    def __eq__(self, other):
        return self is other

    def unique_name(self):
        return self.__class__.__name__

    def is_separator(self):
        return False

    def is_spacer(self):
        return False

    def is_command(self):
        return True

    def accelerators(self):
        # The ENTER and NUMPAD_ENTER keys are treated differently between platforms...
        if "\t" in self.menu_text and (
            "ENTER" in self.menu_text or "RETURN" in self.menu_text
        ):
            flags = wx.ACCEL_NORMAL
            for key in self.menu_text.split("\t")[1].split("+"):
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

    def add_to_menu(self, menu, window, position=None, sub_menu=None):
        menu_item = MenuItem(
            self, menu, self.id, self.menu_text, self.help_text, self.kind,
            subMenu=sub_menu
        )
        self.menu_items.append(menu_item)
        self.add_bitmap_to_menu_item(menu_item)
        if position is None:
            menu.Append(menu_item)
        else:
            menu.Insert(position, menu_item)
        self.bind(window, self.id)
        return self.id

    def add_bitmap_to_menu_item(self, menu_item):
        if (
            self.icon_id2
            and self.kind == wx.ITEM_CHECK
            and not operating_system.isGTK()
        ):
            bitmap1 = icon_catalog.get_bitmap(self.icon_id, LIST_ICON_SIZE)
            bitmap2 = icon_catalog.get_bitmap(self.icon_id2, LIST_ICON_SIZE)
            menu_item.SetBitmaps(bitmap1, bitmap2)
        elif self.kind == wx.ITEM_NORMAL:
            if self.icon_id is None:
                return  # No icon intended - correct, do nothing

            bitmap = icon_catalog.get_bitmap(self.icon_id, LIST_ICON_SIZE)
            if not bitmap.IsOk():
                # TRAP: icon_id given but invalid - this is an error
                log_step("ERROR: invalid icon '%s' for menu item '%s'" %
                         (self.icon_id, menu_item.GetItemLabelText()), prefix="ICON")
                return

            menu_item.SetBitmap(bitmap)

    def remove_from_menu(self, menu, window):
        menu_id = None
        for menu_item in self.menu_items:
            if menu_item.GetMenu() == menu:
                self.menu_items.remove(menu_item)
                menu_id = menu_item.GetId()
                menu.Remove(menu_id)
                break
        if menu_id is not None:
            self.unbind(window, menu_id)

    def append_to_toolbar(self, toolbar):
        self.toolbar = toolbar
        bitmap = icon_catalog.get_bitmap(
            self.icon_id, toolbar.GetToolBitmapSize()[0]
        )
        toolbar.AddLabelTool(
            self.id,
            "",
            bitmap,
            wx.NullBitmap,
            self.kind,
            shortHelp=wx.MenuItem.GetLabelText(self.menu_text),
            longHelp=self.help_text,
        )
        self.bind(toolbar, self.id)
        return self.id

    def bind(self, window, item_id):
        window.Bind(wx.EVT_MENU, self.on_command_activate, id=item_id)

    def unbind(self, window, item_id):
        window.Unbind(wx.EVT_MENU, id=item_id)

    def on_command_activate(self, event, *args, **kwargs):
        """For controls such as the ListCtrl and the TreeCtrl, activating
        the command is possible even when not enabled, so we need an
        explicit check here. Otherwise hitting return on an empty
        selection in the ListCtrl would bring up the TaskEditor."""
        if self.enabled(event):
            return self.do_command(event, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.on_command_activate(*args, **kwargs)

    def do_command(self, event):
        raise NotImplementedError  # pragma: no cover

    def enabled(self, event):  # pylint: disable=W0613
        """Can be overridden in a subclass."""
        return True

    def current_menu_text(self):
        """Return updated menu text, or None to keep current. Override in
        subclasses whose menu text changes based on context (e.g. selection
        type)."""
        return None

    def checked(self):
        """Return True/False for checkable items, or None to skip.
        Override in subclasses with ITEM_CHECK kind."""
        return None

    def update_tool_help(self):
        if not self.toolbar:
            return  # Not attached to a toolbar or it's hidden
        short_help = wx.MenuItem.GetLabelText(self.get_menu_text())
        if short_help != self.toolbar.GetToolShortHelp(self.id):
            self.toolbar.SetToolShortHelp(self.id, short_help)
        long_help = self.get_help_text()
        if long_help != self.toolbar.GetToolLongHelp(self.id):
            self.toolbar.SetToolLongHelp(self.id, long_help)

    def update_menu_text(self, menu_text):
        self.menu_text = menu_text
        # SetItemLabel works on all platforms in modern wxPython 4.x
        # The old Windows-specific code that deleted/inserted menu items
        # was causing access violations when popup menus were displayed.
        for menu_item in self.menu_items:
            try:
                menu_item.SetItemLabel(menu_text)
            except Exception as e:
                log_step("update_menu_text: dead menu item: %s" % e,
                         prefix="DEAD-OBJ")

    def main_window(self):
        return wx.GetApp().TopWindow

    def get_menu_text(self):
        return self.menu_text

    def get_help_text(self):
        return self.help_text

