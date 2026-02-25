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


def _coerce_ui_command(ui_command):
    """Convert legacy sentinel values to UICommand subclass instances."""
    if ui_command is None:
        from .uicommand import Separator
        return Separator()
    elif isinstance(ui_command, int):
        from .uicommand import Spacer
        return Spacer(ui_command)
    elif isinstance(ui_command, str):
        from .uicommand import DisabledLabel
        return DisabledLabel(ui_command)
    elif isinstance(ui_command, tuple):
        from .uicommand import SubMenu
        title = ui_command[0]
        commands = ui_command[1:]
        return SubMenu(title, *commands)
    return ui_command


class UICommandContainerMixin(object):
    """Mixin with wx.Menu or wx.ToolBar (sub)class."""

    def append_ui_commands(self, *ui_commands):
        for ui_command in ui_commands:
            self.append_ui_command(_coerce_ui_command(ui_command))

    # Keep old name as alias during transition
    appendUICommands = append_ui_commands
