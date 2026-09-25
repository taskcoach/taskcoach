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

import time

from pubsub import pub
import wx

from taskcoachlib import patterns
from taskcoachlib.i18n import _
from taskcoachlib.meta.debug import log_step


class AutoSaver(object):
    """AutoSaver observes task files. If a task file is changed by the user
    (gets 'dirty') and auto save is on, AutoSaver saves the task file."""

    # A failed autosave is tried again after this many seconds: the
    # file stays dirty, so no new "taskfile.dirty" message comes
    RETRY_SECONDS = 60

    def __init__(self, settings, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__settings = settings
        self.__task_files = set()
        self.__bound = False
        self.__failures = {}  # task file: failed autosaves in a row
        self.__retries = {}  # task file: time.monotonic() of next try
        pub.subscribe(self.on_task_file_dirty, "taskfile.dirty")

    def on_task_file_dirty(self, taskFile):
        """When a task file gets dirty and auto save is on, note it so
        it can be saved during idle time."""
        if self._need_save(taskFile):
            self.__task_files.add(taskFile)
        self.__save_when_idle()

    def __save_when_idle(self):
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
            if not self._need_save(task_file):
                # Saved some other way meanwhile, e.g. File > Save
                self.__failures.pop(task_file, None)
                continue
            try:
                task_file.save()
            except Exception as reason:  # pylint: disable=W0703
                self.__on_failed(task_file, reason)
            else:
                if self.__failures.pop(task_file, None):
                    log_step(
                        "autosave of %s works again" % task_file.filename(),
                        prefix="FILE",
                    )

    def __on_failed(self, task_file, reason):
        count = self.__failures.get(task_file, 0) + 1
        self.__failures[task_file] = count
        log_step(
            "autosave of %s failed (%d in a row), trying again in %d s"
            % (task_file.filename(), count, self.RETRY_SECONDS),
            prefix="FILE",
            exc=count == 1,
        )
        if count == 2:
            # Not a passing problem: tell the user, once per streak
            self._tell_user(
                _(
                    "Could not save %(filename)s automatically: "
                    "%(reason)s\nTask Coach keeps trying every minute."
                )
                % dict(filename=task_file.filename(), reason=reason)
            )
        self.__retries[task_file] = time.monotonic() + self.RETRY_SECONDS
        patterns.Publisher().registerObserver(
            self.on_second, eventType="timer.second"
        )

    def on_second(self, event):  # pylint: disable=W0613
        now = time.monotonic()
        for task_file, due in list(self.__retries.items()):
            if now >= due:
                del self.__retries[task_file]
                self.__task_files.add(task_file)
                self.__save_when_idle()
        if not self.__retries:
            patterns.Publisher().removeObserver(
                self.on_second, eventType="timer.second"
            )

    @staticmethod
    def _tell_user(message):
        # Imported here, so importing persistence does not load the gui
        from taskcoachlib.gui.icons.icon_library import (
            icon_catalog,
            NOTIFICATION_ICON_SIZE,
        )
        from taskcoachlib.notify import AbstractNotifier

        notifier = AbstractNotifier.getSimple()
        if notifier is not None:
            notifier.notify(
                _("Task Coach"),
                message,
                icon_catalog.get_bitmap(
                    "nuvola_apps_korganizer", NOTIFICATION_ICON_SIZE
                ),
            )
