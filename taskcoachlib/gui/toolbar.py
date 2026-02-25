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

from taskcoachlib import operating_system
from taskcoachlib.config.defaults import MAIN_TOOLBAR_ICON_SIZE_DEFAULT
from taskcoachlib.gui.icons.icon_library import LIST_ICON_SIZE
from taskcoachlib.meta.debug import log_step
from wx.lib.agw import aui
import wx
from . import uicommand
from .uicommand.uicommandcontainer import _coerce_ui_command

# All toolbars use LIST_ICON_SIZE except the main toolbar, which has
# user-selectable sizes defined in config/defaults.py.
TOOLBAR_ICON_SIZE = LIST_ICON_SIZE


class _Toolbar(aui.AuiToolBar):
    def __init__(self, parent, style):
        super().__init__(parent, agwStyle=aui.AUI_TB_NO_AUTORESIZE)

    def AddLabelTool(self, id, label, bitmap1, bitmap2, kind, **kwargs):
        long_help_string = kwargs.pop("longHelp", "")
        short_help_string = kwargs.pop("shortHelp", "")
        if not bitmap1.IsOk():
            size = self.GetToolBitmapSize()
            log_step(
                f"Toolbar item '{label}' has no bitmap at size "
                f"{size[0]}x{size[1]}. Import the missing size from the "
                f"distillery. See ICON_LIBRARY.md Step 2.3.",
                prefix="ICON"
            )
            img = wx.Image(size[0], size[1])
            img.InitAlpha()
            bitmap1 = img.ConvertToBitmap()
        bitmap2 = self.MakeDisabledBitmap(bitmap1)
        super().AddTool(
            id,
            label,
            bitmap1,
            bitmap2,
            kind,
            short_help_string,
            long_help_string,
            None,
            None,
        )

    def GetToolState(self, toolid):
        return self.GetToolToggled(toolid)

    def SetToolBitmapSize(self, size):
        self.__size = size

    def GetToolBitmapSize(self):
        return self.__size

    def GetToolSize(self):
        return self.__size

    def SetMargins(self, *args):
        if len(args) == 2:
            super().SetMarginsXY(args[0], args[1])
        else:
            super().SetMargins(*args)

    def MakeDisabledBitmap(self, bitmap):
        if not bitmap.IsOk():
            size = self.GetToolBitmapSize()
            log_step(
                f"ERROR: Toolbar received NullBitmap at size {size[0]}x{size[1]}. "
                f"A toolbar icon is missing this size — import it from the "
                f"distillery and update icons.json sizes. "
                f"See ICON_LIBRARY.md Step 2.3.",
                prefix="ICON"
            )
            return bitmap
        return bitmap.ConvertToImage().ConvertToGreyscale().ConvertToBitmap()


class ToolBar(_Toolbar, uicommand.UICommandContainerMixin):
    def __init__(self, window, settings,
                 size=(MAIN_TOOLBAR_ICON_SIZE_DEFAULT,) * 2):
        self.__window = window
        self.__settings = settings
        self.__visible_ui_commands = list()
        self.__cache = None
        super().__init__(window, style=wx.TB_FLAT | wx.TB_NODIVIDER)
        self.SetToolBitmapSize(size)
        if operating_system.isMac():
            # Extra margin needed because the search control is too high
            self.SetMargins(0, 7)
        self.load_perspective(window.getToolBarPerspective())

    def Clear(self):
        """The regular Clear method does not remove controls."""

        if self.__visible_ui_commands:  # May be None
            for item in self.__visible_ui_commands:
                if item.is_command():
                    item.unbind(self, item.id)

        idx = 0
        while idx < self.GetToolCount():
            item = self.FindToolByIndex(idx)
            if item is not None and item.GetKind() == aui.ITEM_CONTROL:
                item.window.Destroy()
                self.DeleteToolByPos(idx)
            else:
                idx += 1

        super().Clear()

    def detach(self):
        self.Clear()
        self.__visible_ui_commands = self.__cache = None

    def get_tool_id_by_command(self, command_name):
        if command_name == "EditToolBarPerspective":
            return self.__customizeId

        for item in self.__visible_ui_commands:
            if item.is_command() and item.unique_name() == command_name:
                return item.id
        return wx.ID_ANY

    # Keep old name as alias for callers not yet updated
    getToolIdByCommand = get_tool_id_by_command

    def _filter_commands(self, perspective, cache=True):
        commands = list()
        if perspective:
            index = dict(
                (command.unique_name(), command)
                for command in self.uiCommands(cache=cache)
            )
            for class_name in perspective.split(","):
                if class_name in index:
                    commands.append(index[class_name])
        # If perspective is empty, return empty list (allow empty toolbars)
        return commands

    def load_perspective(self, perspective, customizable=True, cache=True):
        self.Clear()

        commands = self._filter_commands(perspective, cache=cache)
        self.__visible_ui_commands = commands[:]

        if customizable:
            if not any(c.is_spacer() for c in commands):
                commands.append(uicommand.Spacer())
            from taskcoachlib.gui.dialog.toolbar import ToolBarEditor

            ui_command = uicommand.EditToolBarPerspective(
                self, ToolBarEditor, settings=self.__settings
            )
            commands.append(ui_command)
            self.__customizeId = ui_command.id
        if operating_system.isMac():
            commands.append(uicommand.Separator())

        self.append_ui_commands(*commands)
        self.Realize()

    # Keep old name as alias
    loadPerspective = load_perspective

    def perspective(self):
        names = list()
        for item in self.__visible_ui_commands:
            names.append(item.unique_name())
        return ",".join(names)

    def save_perspective(self, perspective):
        self.load_perspective(perspective)
        self.__window.saveToolBarPerspective(perspective)

    # Keep old name as alias
    savePerspective = save_perspective

    def uiCommands(self, cache=True):
        if self.__cache is None or not cache:
            raw = self.__window.createToolBarUICommands()
            self.__cache = [_coerce_ui_command(cmd) for cmd in raw]
        return self.__cache

    def visible_ui_commands(self):
        return self.__visible_ui_commands[:]

    # Keep old name as alias
    visibleUICommands = visible_ui_commands

    def get_default_perspective(self):
        """Get the default toolbar perspective from settings."""
        if hasattr(self.__window, 'settingsSection'):
            section = self.__window.settingsSection()
        else:
            # MainWindow uses "view" section
            section = "view"
        return self.__settings.getDefault(section, "toolbarperspective")

    # Keep old name as alias
    getDefaultPerspective = get_default_perspective

    def AppendSeparator(self):
        """This little adapter is needed for
        uicommand.UICommandContainerMixin.append_ui_commands"""
        self.AddSeparator()

    def AppendStretchSpacer(self, proportion):
        self.AddStretchSpacer(proportion)

    def append_ui_command(self, ui_command):
        return ui_command.append_to_toolbar(self)

    # Keep old name as alias
    appendUICommand = append_ui_command


class MainToolBar(ToolBar):
    """Main window toolbar for use in AUI-managed main window.

    The toolbar is docked at the top and spans full window width.
    Uses standard AUI toolbar behavior with GetBestSize() for automatic
    height calculation based on icon size.
    """
    pass
