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
from wx.lib.agw import aui
import wx
from . import uicommand


class _Toolbar(aui.AuiToolBar):
    def __init__(self, parent, style):
        super().__init__(parent, agwStyle=aui.AUI_TB_NO_AUTORESIZE)

    def AddLabelTool(self, id, label, bitmap1, bitmap2, kind, **kwargs):
        long_help_string = kwargs.pop("longHelp", "")
        short_help_string = kwargs.pop("shortHelp", "")
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
        return bitmap.ConvertToImage().ConvertToGreyscale().ConvertToBitmap()


class ToolBar(_Toolbar, uicommand.UICommandContainerMixin):
    def __init__(self, window, settings, size=(32, 32)):
        self.__window = window
        self.__settings = settings
        self.__visibleUICommands = list()
        self.__cache = None
        super().__init__(window, style=wx.TB_FLAT | wx.TB_NODIVIDER)
        self.SetToolBitmapSize(size)
        if operating_system.isMac():
            # Extra margin needed because the search control is too high
            self.SetMargins(0, 7)
        self.loadPerspective(window.getToolBarPerspective())

    def Clear(self):
        """The regular Clear method does not remove controls."""

        if self.__visibleUICommands:  # May be None
            for uiCommand in self.__visibleUICommands:
                if uiCommand is not None and not isinstance(uiCommand, int):
                    uiCommand.unbind(self, uiCommand.id)

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
        self.__visibleUICommands = self.__cache = None

    def getToolIdByCommand(self, commandName):
        if commandName == "EditToolBarPerspective":
            return self.__customizeId

        for uiCommand in self.__visibleUICommands:
            if (
                isinstance(uiCommand, uicommand.UICommand)
                and uiCommand.uniqueName() == commandName
            ):
                return uiCommand.id
        return wx.ID_ANY

    def _filterCommands(self, perspective, cache=True):
        commands = list()
        if perspective:
            index = dict(
                [
                    (command.uniqueName(), command)
                    for command in self.uiCommands(cache=cache)
                    if command is not None and not isinstance(command, int)
                ]
            )
            index["Separator"] = None
            index["Spacer"] = 1
            for className in perspective.split(","):
                if className in index:
                    commands.append(index[className])
        else:
            commands = list(self.uiCommands(cache=cache))
        return commands

    def loadPerspective(self, perspective, customizable=True, cache=True):
        self.Clear()

        commands = self._filterCommands(perspective, cache=cache)
        self.__visibleUICommands = commands[:]

        if customizable:
            if 1 not in commands:
                commands.append(1)
            from taskcoachlib.gui.dialog.toolbar import ToolBarEditor

            uiCommand = uicommand.EditToolBarPerspective(
                self, ToolBarEditor, settings=self.__settings
            )
            commands.append(uiCommand)
            self.__customizeId = uiCommand.id
        if operating_system.isMac():
            commands.append(None)  # Errr...

        self.appendUICommands(*commands)
        self.Realize()

    def perspective(self):
        names = list()
        for uiCommand in self.__visibleUICommands:
            if uiCommand is None:
                names.append("Separator")
            elif isinstance(uiCommand, int):
                names.append("Spacer")
            else:
                names.append(uiCommand.uniqueName())
        return ",".join(names)

    def savePerspective(self, perspective):
        self.loadPerspective(perspective)
        self.__window.saveToolBarPerspective(perspective)

    def uiCommands(self, cache=True):
        if self.__cache is None or not cache:
            self.__cache = self.__window.createToolBarUICommands()
        return self.__cache

    def visibleUICommands(self):
        return self.__visibleUICommands[:]

    def AppendSeparator(self):
        """This little adapter is needed for
        uicommand.UICommandContainerMixin.appendUICommands"""
        self.AddSeparator()

    def AppendStretchSpacer(self, proportion):
        self.AddStretchSpacer(proportion)

    def appendUICommand(self, uiCommand):
        return uiCommand.appendToToolBar(self)


class MainToolBar(ToolBar):
    """Main window toolbar for use in AUI-managed main window.

    The toolbar is docked at the top and spans full window width.
    Uses standard AUI toolbar behavior with GetBestSize() for automatic
    height calculation based on icon size.
    """
    pass
