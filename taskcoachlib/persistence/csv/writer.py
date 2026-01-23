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

import csv, io
from . import generator


class UnicodeCSVWriter:
    """A CSV writer that writes rows to a CSV file encoded in utf-8.
    Based on http://docs.python.org/lib/csv-examples.html.
    """

    def __init__(self, fd, *args, **kwargs):
        # Redirect output to a queue
        self.queue = io.StringIO()
        self.writer = csv.writer(self.queue, *args, **kwargs)
        self.fd = fd

    def writerow(self, row):
        self.writer.writerow([cell.encode("utf-8") for cell in row])
        # Fetch UTF-8 output from the queue
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        self.fd.write(data)
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class CSVWriter(object):
    # Constants for "All" export options
    ALL_TASKS = "ALL_TASKS"
    ALL_EFFORTS = "ALL_EFFORTS"
    ALL_CATEGORIES = "ALL_CATEGORIES"
    ALL_NOTES = "ALL_NOTES"

    def __init__(self, fd, filename=None):
        self.__fd = fd

    def write(
        self,
        viewer,
        settings,
        selectionOnly=False,
        separateDateAndTimeColumns=False,
        columns=None,
        taskFile=None,
    ):  # pylint: disable=W0613
        if isinstance(viewer, str) and viewer.startswith("ALL_"):
            items = self._getAllItems(viewer, taskFile)
            if not columns:
                return 0
            rowBuilder = generator.RowBuilder(
                columns, False, separateDateAndTimeColumns
            )
            csvRows = rowBuilder.rows(items)
        else:
            csvRows = generator.viewer2csv(
                viewer, selectionOnly, separateDateAndTimeColumns, columns
            )
        UnicodeCSVWriter(self.__fd).writerows(csvRows)
        return len(csvRows) - 1  # Don't count header row

    def _getAllItems(self, viewerType, taskFile):
        """Get all items from taskFile based on type constant."""
        if taskFile is None:
            return []
        if viewerType == self.ALL_TASKS:
            return list(taskFile.tasks())
        elif viewerType == self.ALL_EFFORTS:
            return list(taskFile.efforts())
        elif viewerType == self.ALL_CATEGORIES:
            return list(taskFile.categories())
        elif viewerType == self.ALL_NOTES:
            return list(taskFile.notes())
        return []
