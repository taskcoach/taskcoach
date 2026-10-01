"""
Task Coach - Your friendly task manager
Copyright (C) 2011 Task Coach developers <developers@taskcoach.org>

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

import os, atexit


class NotifierBase(object):
    def __init__(self):
        super().__init__()

        self._filename = None
        self._path = None
        self.stamp = None
        atexit.register(self.__stopWhenExit)

    def __stopWhenExit(self):
        self.stop()

    def stop(self):
        pass  # Should be overloaded if needed

    def _check(self, filename):
        return self.stamp is None or (
            filename
            and os.path.exists(filename)
            and os.stat(filename).st_mtime > self.stamp
        )

    def setFilename(self, filename):
        self._filename = filename
        self.stamp = None
        if filename:
            self._path = os.path.dirname(filename)
            if os.path.exists(filename):
                self.stamp = os.stat(filename).st_mtime
        else:
            self._path = None

    def saved(self):
        if self._filename and os.path.exists(self._filename):
            self.stamp = os.stat(self._filename).st_mtime
        else:
            self.stamp = None
