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

import os, stat, atexit, tempfile
from taskcoachlib import patterns


class TempFiles(object, metaclass=patterns.Singleton):
    def __init__(self):
        self.__tempFiles = []
        atexit.register(self.cleanup)

    def register(self, filename):
        self.__tempFiles.append(filename)

    def cleanup(self):
        for name in self.__tempFiles:
            try:
                if os.name == "nt":
                    os.chmod(name, stat.S_IREAD | stat.S_IWRITE)
                os.remove(name)
            except OSError:
                pass  # File may already be deleted or inaccessible


def get_temp_file(**kwargs):
    """Return the name of a temporary file. This file will be registered
    for deletion at process termination."""

    fd, filename = tempfile.mkstemp(**kwargs)
    os.close(fd)
    TempFiles().register(filename)
    return filename
