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

# Notices another program's change to the open task file (a sync
# client, an editor, Task Coach on another computer): the file's
# modification time and size, checked every few seconds in a thread
# that runs while a file is watched. The same on every system and on
# network shares. Every save checks the file too, so this only makes
# the question come early (docs/PERSISTENCE_XML.md#watching-the-file).

import os
import threading


class FilesystemNotifier:
    INTERVAL = 10  # Seconds between checks

    def __init__(self):
        super().__init__()
        self._filename = None
        self.stamp = None  # The file's state last seen
        self.__lock = threading.Lock()
        self.__wake = threading.Event()
        self.__thread = None

    def set_filename(self, filename):
        with self.__lock:
            self._filename = filename or None
            self.stamp = _state(self._filename)
            if self._filename and self.__thread is None:
                self.__wake.clear()
                self.__thread = threading.Thread(
                    target=self.__run, name="file watcher", daemon=True
                )
                self.__thread.start()

    def saved(self):
        """Our own save is not another program's change."""
        with self.__lock:
            self.stamp = _state(self._filename)

    def stop(self):
        with self.__lock:
            thread, self.__thread = self.__thread, None
            self.__wake.set()
        if thread is not None and thread is not threading.current_thread():
            thread.join()

    def on_file_changed(self):
        """Called from the watcher's thread."""
        raise NotImplementedError

    def __run(self):
        while not self.__wake.wait(self.INTERVAL):
            with self.__lock:
                if not self._filename:
                    self.__thread = None
                    return
                state = _state(self._filename)
                # Any change, also an older time a restored copy brings
                changed = state is not None and state != self.stamp
                if changed:
                    self.stamp = state
            if changed:
                self.on_file_changed()


def _state(filename):
    try:
        stat = os.stat(filename)
    except (OSError, TypeError):
        return None  # Not there (yet), or no file
    return stat.st_mtime_ns, stat.st_size
