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

File system monitoring module.

Uses the cross-platform watchdog library for all platforms:
- Linux: inotify
- macOS: FSEvents
- Windows: ReadDirectoryChangesW
- Other: Polling fallback
"""

import logging

from .fs_poller import *

try:
    from .fs_watchdog import *
except ImportError:
    logging.warning(
        "watchdog library not installed. File monitoring will use polling fallback "
        "(less efficient). Install watchdog for better performance: pip install watchdog"
    )

    class FilesystemNotifier(FilesystemPollerNotifier):
        pass
