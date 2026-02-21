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

from taskcoachlib.i18n import _
from taskcoachlib import render
from taskcoachlib.domain import date
import io


def extendedWithAncestors(selection):
    extendedSelection = selection[:]
    for item in selection:
        for ancestor in item.ancestors():
            if ancestor not in extendedSelection:
                extendedSelection.append(ancestor)
    return extendedSelection


class RowBuilder(object):
    dateAndTimeColumnHeaders = dict(
        actualStartDateTime=[_("Actual start date"), _("Actual start time")],
        plannedStartDateTime=[
            _("Planned start date"),
            _("Planned start time"),
        ],
        dueDateTime=[_("Due date"), _("Due time")],
        completionDateTime=[_("Completion date"), _("Completion time")],
        reminder=[_("Reminder date"), _("Reminder time")],
        creationDateTime=[_("Creation date"), _("Creation time")],
        period=[
            _("Period start date"),
            _("Period start time"),
            _("Period end date"),
            _("Period end time"),
        ],
    )

    def __init__(self, columns, isTree, separateDateAndTimeColumns):
        self.__columns = columns
        self.__separateDateAndTimeColumns = separateDateAndTimeColumns
        if isTree:
            self.indent = lambda item: " " * len(item.ancestors())
        else:
            self.indent = lambda item: ""

    def headerRow(self):
        headers = []
        for column in self.__columns:
            if self.shouldSplitDateAndTime(column):
                headers.extend(self.dateAndTimeColumnHeaders[column.name()])
            else:
                headers.append(column.header())
        return headers

    def itemRow(self, item):
        row = []
        for column in self.__columns:
            if self.shouldSplitDateAndTime(column):
                row.extend(self.splitDateAndTime(column, item))
            elif column.name() == "notes":

                def renderNotes(notes, indent=0):
                    bf = io.StringIO()
                    spaces = "  " * indent
                    for note in sorted(notes, key=lambda note: note.subject()):
                        bf.write(
                            "%s%s\n%s%s\n"
                            % (
                                spaces,
                                note.subject(),
                                spaces,
                                note.description(),
                            )
                        )
                        bf.write(renderNotes(note.children(), indent + 1))
                    return bf.getvalue()

                row.append(renderNotes(item.notes()))
            elif column.name() == "attachments":
                row.append(
                    "\n".join(
                        sorted(
                            [
                                attachment.subject()
                                for attachment in item.attachments()
                            ]
                        )
                    )
                )
            else:
                row.append(column.render(item, humanReadable=False))
        row[0] = self.indent(item) + row[0]
        return row

    def shouldSplitDateAndTime(self, column):
        return (
            self.__separateDateAndTimeColumns
            and column.name() in self.dateAndTimeColumnHeaders
        )

    def splitDateAndTime(self, column, item):
        if column.name() == "period":
            return self.__splitDateAndTime(
                item.getStart()
            ) + self.__splitDateAndTime(item.getStop())
        return self.__splitDateAndTime(getattr(item, column.name())())

    def __splitDateAndTime(self, dateTime):
        if dateTime == date.DateTime() or dateTime is None:
            return "", ""
        return render.date(dateTime), render.time(dateTime)

    def itemRows(self, items):
        return [self.itemRow(item) for item in items]

    def rows(self, items):
        return [self.headerRow()] + self.itemRows(items)


def viewer2csv(
    viewer, selectionOnly=False, separateDateAndTimeColumns=False, columns=None
):
    """Convert the items displayed by a viewer into a list of rows, where
    each row consists of a list of values. If the viewer is in tree mode,
    indent the first value (typically the subject of the item) to
    indicate the depth of the item in the tree."""

    isTree = viewer.is_tree_viewer()
    columns = columns or viewer.visibleColumns()
    rowBuilder = RowBuilder(columns, isTree, separateDateAndTimeColumns)
    items = viewer.visibleItems()
    if selectionOnly:
        items = [item for item in items if viewer.isselected(item)]
        if isTree:
            items = extendedWithAncestors(items)
    return rowBuilder.rows(items)
