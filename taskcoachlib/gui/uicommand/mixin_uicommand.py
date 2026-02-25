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

from taskcoachlib.i18n import _
import wx


class PopupButtonMixin(object):
    """Mix this with a UICommand for a toolbar pop-up menu."""

    def do_command(self, event):  # pylint: disable=W0613
        try:
            args = [self.__menu]
        except AttributeError:
            self.__menu = self.createPopupMenu()  # pylint: disable=W0201
            args = [self.__menu]

        # Check if menu has any items
        if self.__menu.GetMenuItemCount() == 0:
            wx.MessageBox(
                _("No templates available. Create a template first by saving a task as a template."),
                _("No Templates"),
                wx.OK | wx.ICON_INFORMATION,
                self.main_window()
            )
            return

        if self.toolbar:
            args.append(self.menuXY())
        self.main_window().PopupMenu(*args)  # pylint: disable=W0142

    def menuXY(self):
        """Location to pop up the menu."""
        return self.main_window().ScreenToClient((self.menuX(), self.menuY()))

    def menuX(self):
        # Get the tool's position in the toolbar
        toolRect = self.toolbar.GetToolRect(self.id)
        if toolRect is not None:
            # Convert toolbar-local position to screen coordinates
            toolbarScreenPos = self.toolbar.GetScreenPosition()
            # Align to the left edge of the button
            return toolbarScreenPos[0] + toolRect[0]
        else:
            # Fallback to mouse position if tool rect not available
            buttonWidth = self.toolbar.GetToolSize()[0]
            mouseX = wx.GetMousePosition()[0]
            return mouseX - 0.5 * buttonWidth

    def menuY(self):
        toolbarY = self.toolbar.GetScreenPosition()[1]
        toolbarHeight = self.toolbar.GetSize()[1]
        return toolbarY + toolbarHeight

    def createPopupMenu(self):
        raise NotImplementedError  # pragma: no cover
