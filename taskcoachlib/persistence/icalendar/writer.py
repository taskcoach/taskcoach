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

from taskcoachlib.persistence.icalendar import ical
from taskcoachlib.domain import task
from taskcoachlib import meta


def extendedWithAncestors(selection):
    extendedSelection = selection[:]
    for item in selection:
        for ancestor in item.ancestors():
            if ancestor not in extendedSelection:
                extendedSelection.append(ancestor)
    return extendedSelection


class iCalendarWriter(object):
    # Constants for "All" export options (must match export.py)
    ALL_TASKS = "ALL_TASKS"
    ALL_EFFORTS = "ALL_EFFORTS"

    def __init__(self, fd, filename=None):
        self.__fd = fd

    def write(
        self, viewer, settings, selectionOnly=False, selectedFields=None,
        taskFile=None
    ):  # pylint: disable=W0613
        """Write items to iCalendar format.

        Args:
            viewer: The viewer to export from, or ALL_TASKS/ALL_EFFORTS constant
            settings: Application settings
            selectionOnly: If True, only export selected items (ignored for ALL_*)
            selectedFields: Set of field keys to export
            taskFile: The task file (required for ALL_* export)
        """
        # Handle "All" export options
        if viewer == self.ALL_TASKS:
            if taskFile is None:
                return 0
            items = list(taskFile.tasks())
        elif viewer == self.ALL_EFFORTS:
            if taskFile is None:
                return 0
            items = list(taskFile.efforts())
        else:
            # Normal viewer-based export
            items = viewer.visibleItems()
            if selectionOnly:
                selection = viewer.curselection()
                if viewer.isTreeViewer():
                    selection = extendedWithAncestors(selection)
                items = [item for item in items if item in selection]

        return self.writeItems(items, selectedFields=selectedFields)

    def writeItems(self, items, selectedFields=None):
        """Write a list of items to iCalendar format.

        Args:
            items: List of tasks or efforts to export
            selectedFields: Set of field keys to export
        """
        self.__fd.write("BEGIN:VCALENDAR\r\n")
        self._writeMetaData()
        count = 0
        for item in items:
            if isinstance(item, task.Task):
                self.__fd.write(
                    ical.VCalFromTask(item, encoding=False, selectedFields=selectedFields)
                )
            else:
                self.__fd.write(
                    ical.VCalFromEffort(item, encoding=False, selectedFields=selectedFields)
                )
            count += 1
        self.__fd.write("END:VCALENDAR\r\n")
        return count

    def _writeMetaData(self):
        self.__fd.write("VERSION:2.0\r\n")
        domain = meta.url[len("http://") :].strip("/")
        self.__fd.write(
            "PRODID:-//%s//NONSGML %s V%s//EN\r\n"
            % (domain, meta.name, meta.version)
        )
