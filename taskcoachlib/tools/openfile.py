"""
Task Coach - Your friendly task manager
Copyright (C) 2016 Task Coach developers <developers@taskcoach.org>

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

Open files with the system's default application.

This module provides cross-platform file opening using native OS mechanisms:
- Linux: xdg-open (freedesktop.org standard)
- macOS: open command
- Windows: os.startfile()
"""

import os
import platform
import subprocess


def openFile(filename):
    """Open a file with the system's default application.

    Args:
        filename: Path to the file to open

    Raises:
        OSError: If the file cannot be opened
    """
    system = platform.system()

    if system == "Windows":
        os.startfile(filename)
    elif system == "Darwin":
        result = subprocess.run(["open", filename], check=False)
        if result.returncode != 0:
            raise OSError(f'Unable to open "{filename}"')
    else:
        # Linux and other Unix-like systems use xdg-open
        result = subprocess.run(["xdg-open", filename], check=False)
        if result.returncode != 0:
            raise OSError(f'Unable to open "{filename}"')
