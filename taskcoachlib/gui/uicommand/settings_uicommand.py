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

from . import base_uicommand
import wx


class SettingsCommand(base_uicommand.UICommand):  # pylint: disable=W0223
    """SettingsCommands are saved in the settings (a ConfigParser)."""

    def __init__(
        self, settings=None, setting=None, section="view", *args, **kwargs
    ):
        self.settings = settings
        self.section = section
        self.setting = setting
        super().__init__(*args, **kwargs)


class BooleanSettingsCommand(SettingsCommand):  # pylint: disable=W0223
    """Bae class for commands that change a boolean setting.
    Whenever the setting is changed, the user interface
    representation is changed as well. E.g. a menu gets
    a checkmark."""

    def __init__(self, value=None, *args, **kwargs):
        self.value = value
        super().__init__(*args, **kwargs)

    def addToMenu(self, menu, window, position=None):
        menuId = super().addToMenu(menu, window, position)
        menuItem = menu.FindItemById(menuId)
        menuItem.Check(self.isSettingChecked())
        return menuId

    def checked(self):
        return self.isSettingChecked()

    def isSettingChecked(self):
        raise NotImplementedError  # pragma: no cover


class UICheckCommand(BooleanSettingsCommand):
    def __init__(self, *args, **kwargs):
        kwargs["icon_id"] = kwargs.get("icon_id", self.getBitmap())
        super().__init__(kind=wx.ITEM_CHECK, *args, **kwargs)

    def isSettingChecked(self):
        return self.settings.getboolean(self.section, self.setting)

    def _isMenuItemChecked(self, event):
        # There's a bug in wxPython 2.8.3 on Windows XP that causes
        # event.IsChecked() to return the wrong value in the context menu.
        # The menu on the main window works fine. So we first try to access the
        # context menu to get the checked state from the menu item itself.
        # This will fail if the event is coming from the window, but in that
        # case we can event.IsChecked() expect to work so we use that.
        try:
            return (
                event.GetEventObject().FindItemById(event.GetId()).IsChecked()
            )
        except AttributeError:
            return event.IsChecked()

    def doCommand(self, event):
        self.settings.setboolean(
            self.section, self.setting, self._isMenuItemChecked(event)
        )

    def getBitmap(self):
        # Using our own bitmap for checkable menu items does not work on
        # all platforms, most notably Gtk where providing our own bitmap causes
        # "(python:8569): Gtk-CRITICAL **: gtk_check_menu_item_set_active:
        # assertion `GTK_IS_CHECK_MENU_ITEM (check_menu_item)' failed"
        return None


class UIRadioCommand(BooleanSettingsCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(kind=wx.ITEM_RADIO, icon_id="", *args, **kwargs)

    def isSettingChecked(self):
        return self.settings.get(self.section, self.setting) == str(self.value)

    def doCommand(self, event):
        self.settings.setvalue(self.section, self.setting, self.value)
