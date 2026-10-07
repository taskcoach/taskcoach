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


class CheckListBox(wx.CheckListBox):
    """The wx.CheckListBox does not support client data on all platforms,
    so we do it ourselves."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__clientData = dict()

    def Append(self, item, client_data=None):
        index = super().Append(item)
        if client_data:
            self.__clientData[index] = client_data
        return index

    def Insert(self, item, position, client_data=None):
        """We don't need this at the moment."""

    def GetClientData(self, index):
        return self.__clientData[index] if index in self.__clientData else None

    def Clear(self, *args, **kwargs):
        super().Clear(*args, **kwargs)
        self.__clientData.clear()

    def Delete(self, *args, **kwargs):
        """We don't need this at the moment."""
        raise NotImplementedError
