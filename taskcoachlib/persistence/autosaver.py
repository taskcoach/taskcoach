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

from pubsub import pub
import wx


class AutoSaver(object):
    """AutoSaver observes task files. If a task file is changed by the user
    (gets 'dirty') and auto save is on, AutoSaver saves the task file."""

    def __init__(self, settings, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__settings = settings
        self.__task_files = set()
        self.__bound = False
        pub.subscribe(self.on_task_file_dirty, "taskfile.dirty")

    def on_task_file_dirty(self, taskFile):
        """When a task file gets dirty and auto save is on, note it so
        it can be saved during idle time."""
        if self._need_save(taskFile):
            self.__task_files.add(taskFile)
        if not self.__bound:
            self.__bound = True
            wx.GetApp().Bind(wx.EVT_IDLE, self.on_idle)

    def _need_save(self, task_file):
        """Return whether the task file needs to be saved."""
        return (
            task_file.filename()
            and task_file.need_save()
            and self.__settings.getboolean("file", "autosave")
        )

    def _need_load(self, taskFile):
        return taskFile.changed_on_disk() and self.__settings.getboolean(
            "file", "autoload"
        )

    def on_idle(self, event):
        """Actually save the dirty files during idle time."""
        event.Skip()
        wx.GetApp().Unbind(wx.EVT_IDLE, handler=self.on_idle)
        self.__bound = False
        while self.__task_files:
            task_file = self.__task_files.pop()
            if self._need_save(task_file):
                task_file.save()
