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

import csv
from . import generator
from taskcoachlib.persistence.allitems import all_items


class CSVWriter(object):
    def __init__(self, fd, filename=None):
        self.__fd = fd

    def write(
        self,
        viewer,
        selectionOnly=False,
        separateDateAndTimeColumns=False,
        columns=None,
        taskFile=None,
    ):  # pylint: disable=W0613
        if isinstance(viewer, str) and viewer.startswith("ALL_"):
            items = all_items(taskFile, viewer) if taskFile else []
            if not columns:
                return 0
            row_builder = generator.RowBuilder(
                columns, False, separateDateAndTimeColumns
            )
            csv_rows = row_builder.rows(items)
        else:
            csv_rows = generator.viewer2csv(
                viewer, selectionOnly, separateDateAndTimeColumns, columns
            )
        self.__fd.write("\ufeff")  # UTF-8 BOM for Excel compatibility
        csv.writer(self.__fd).writerows(csv_rows)
        return len(csv_rows) - 1  # Don't count header row
