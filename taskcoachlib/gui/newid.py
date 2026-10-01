"""
Task Coach - Your friendly task manager
Copyright (C) 2019 Task Coach developers <developers@taskcoach.org>

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


class IdProvider:
    """Ids for menu items and tools, reused once given back: menus
    rebuilt at each change, such as the tracking menu, would otherwise
    run out of ids. Where wx tracks ids (the wxPython wheels), an id
    stays reserved only while its WindowIDRef lives, so the provider
    keeps the reference of every id it hands out, and takes back only
    those."""

    def __init__(self):
        self.__refs = {}  # The reference of each id handed out
        self.__free = set()

    def get(self):
        if self.__free:
            return self.__free.pop()
        ref = wx.NewIdRef()
        self.__refs[int(ref)] = ref
        return int(ref)

    def put(self, id_):
        if id_ in self.__refs:
            self.__free.add(id_)


IdProvider = IdProvider()
