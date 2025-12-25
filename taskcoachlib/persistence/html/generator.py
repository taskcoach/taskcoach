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

import wx, html, io
from taskcoachlib.domain import task

# pylint: disable=W0142

css = """
body {
    color: #333;
    background-color: white;
    font: 11px verdana, arial, helvetica, sans-serif;
}

/* Styles for the title and table caption */
h1, caption {
    text-align: center;
    font-size: 18px;
    font-weight: 900;
    color: #778;
}

/* Styles for the whole table */
#table {
    border-collapse: collapse;
    border: 2px solid #ebedff;
    margin: 10px;
    padding: 0;
}

/* Styles for the header row */
.header {
    font: bold 12px/14px verdana, arial, helvetica, sans-serif;
    color: #07a;
    background-color: #ebedff;
}

/* Mark the column that is sorted on */
#sorted {
    text-decoration: underline;
}

/* Styles for a specific column */
.subject {
    font-weight: bold;
}

/* Styles for regular table cells */
td {
    padding: 5px;
    border: 2px solid #ebedff;
}

/* Styles for table header cells */
th {
    padding: 5px;
    border: 2px solid #ebedff;
}
"""


def viewer2html(
    viewer, settings, cssFilename=None, selectionOnly=False, columns=None
):
    converter = Viewer2HTMLConverter(viewer, settings)
    columns = columns or viewer.visibleColumns()
    return converter(cssFilename, columns, selectionOnly)


class Viewer2HTMLConverter(object):
    """Class to convert the visible contents of a viewer into HTML."""

    docType = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">'
    metaTag = (
        '<meta http-equiv="Content-Type" content="text/html;charset=utf-8">'
    )
    cssLink = (
        '<link href="%s" rel="stylesheet" type="text/css" media="screen">'
    )

    def __init__(self, viewer, settings):
        super().__init__()
        self.viewer = viewer
        self.settings = settings
        self.count = 0

    def __call__(self, cssFilename, columns, selectionOnly):
        """Create an HTML document."""
        lines = (
            [self.docType]
            + self.html(cssFilename, columns, selectionOnly)
            + [""]
        )
        return "\n".join(lines), self.count

    def html(self, cssFilename, columns, selectionOnly, level=0):
        """Returns all HTML, consisting of header and body."""
        printing = not cssFilename
        htmlContent = self.htmlHeader(cssFilename, level + 1) + self.htmlBody(
            columns, selectionOnly, printing, level + 1
        )
        return self.wrap(htmlContent, "html", level)

    def htmlHeader(self, cssFilename, level):
        """Return the HTML header <head>."""
        htmlHeaderContent = self.htmlHeaderContent(cssFilename, level + 1)
        return self.wrap(htmlHeaderContent, "head", level)

    def htmlHeaderContent(self, cssFilename, level):
        """Returns the HTML header section, containing meta tag, title, and
        optional link to a CSS stylesheet."""
        htmlHeaderContent = [
            self.indent(self.metaTag, level),
            self.wrap(self.viewer.title(), "title", level, oneLine=True),
        ] + self.style(level, not cssFilename)
        if cssFilename:
            htmlHeaderContent.append(
                self.indent(self.cssLink % cssFilename, level)
            )
        return htmlHeaderContent

    def style(self, level, includeAllCSS):
        """Add a style section that contains the alignment for the columns. If
        there is no external CSS file, we include all CSS style information
        in a HTML style section."""
        visibleColumns = self.viewer.visibleColumns()
        columnAlignments = [
            {
                wx.LIST_FORMAT_LEFT: "left",
                wx.LIST_FORMAT_CENTRE: "center",
                wx.LIST_FORMAT_RIGHT: "right",
            }[column.alignment()]
            for column in visibleColumns
        ]
        styleContent = []
        for column, alignment in zip(visibleColumns, columnAlignments):
            columnStyle = self.indent(
                ".%s {text-align: %s}" % (column.name(), alignment), level + 1
            )
            styleContent.append(columnStyle)
        if self.viewer.isShowingTasks():
            for status in task.Task.possibleStatuses():
                statusColor = task.Task.fgColorForStatus(status)
                statusColor = self.cssColorSyntax(statusColor)
                statusStyle = ".%s {color: %s}" % (status, statusColor)
                styleContent.append(self.indent(statusStyle, level + 1))
        if includeAllCSS:
            styleContent.extend(
                [self.indent(line, level + 1) for line in css.split("\n")]
            )
        return self.wrap(styleContent, "style", level, type="text/css")

    def htmlBody(self, columns, selectionOnly, printing, level):
        """Returns the HTML body section, containing one table with all
        visible data."""
        htmlBodyContent = []
        if printing:
            htmlBodyContent.append(
                self.wrap(self.viewer.title(), "h1", level, oneLine=True)
            )
        htmlBodyContent.extend(
            self.table(columns, selectionOnly, printing, level + 1)
        )
        return self.wrap(htmlBodyContent, "body", level)

    def table(self, columns, selectionOnly, printing, level):
        """Returns the table, consisting of caption, table header and table
        body."""
        tableContent = [] if printing else [self.tableCaption(level + 1)]
        tableContent.extend(
            self.tableHeader(columns, printing, level + 1)
            + self.tableBody(columns, selectionOnly, printing, level + 1)
        )
        attributes = dict(id="table")
        if printing:
            attributes["border"] = "1"
        return self.wrap(tableContent, "table", level, **attributes)

    def tableCaption(self, level):
        """Returns the table caption, based on the viewer title."""
        return self.wrap(self.viewer.title(), "caption", level, oneLine=True)

    def tableHeader(self, columns, printing, level):
        """Returns the table header section <thead> containing the header
        row with the column headers."""
        tableHeaderContent = self.headerRow(columns, printing, level + 1)
        return self.wrap(tableHeaderContent, "thead", level)

    def headerRow(self, columns, printing, level):
        """Returns the header row <tr> for the table."""
        headerRowContent = []
        for column in columns:
            headerRowContent.append(
                self.headerCell(column, printing, level + 1)
            )
        return self.wrap(headerRowContent, "tr", level, **{"class": "header"})

    def headerCell(self, column, printing, level):
        """Returns a table header <th> for the specific column."""
        header = column.header() or "&nbsp;"
        name = column.name()
        attributes = {"scope": "col", "class": name}
        if self.viewer.isSortable() and self.viewer.isSortedBy(name):
            attributes["id"] = "sorted"
            if printing:
                header = self.wrap(header, "u", level + 1, oneLine=True)
        return self.wrap(header, "th", level, oneLine=True, **attributes)

    def tableBody(self, columns, selectionOnly, printing, level):
        """Returns the table body <tbody>."""
        tree = self.viewer.isTreeViewer()
        self.count = 0
        tableBodyContent = []
        for item in self.viewer.visibleItems():
            if selectionOnly and not self.viewer.isselected(item):
                continue
            self.count += 1
            tableBodyContent.extend(
                self.bodyRow(item, columns, tree, printing, level + 1)
            )
        return self.wrap(tableBodyContent, "tbody", level)

    def bodyRow(self, item, columns, tree, printing, level):
        """Returns a <tr> containing the values of item for the
        visibleColumns."""
        bodyRowContent = []
        attributes = dict()
        for column in columns:
            renderedItem = self.render(
                item, column, indent=not bodyRowContent and tree
            )
            if printing:
                itemColor = item.foregroundColor(recursive=True)
                if itemColor:
                    itemColor = self.cssColorSyntax(itemColor)
                    renderedItem = self.wrap(
                        renderedItem,
                        "font",
                        level + 1,
                        color=itemColor,
                        oneLine=True,
                    )
            bodyRowContent.append(
                self.bodyCell(renderedItem, column, printing, level + 1)
            )
        attributes.update(self.bodyRowBgColor(item, printing))
        if not printing:
            attributes.update(self.bodyRowFgColor(item))
        return self.wrap(bodyRowContent, "tr", level, **attributes)

    def bodyRowBgColor(self, item, printing):
        """Determine the background color for the item. Returns a CSS style
        specification or a HTML style specification when printing."""
        bgColor = item.backgroundColor(recursive=True)
        if bgColor and bgColor != wx.WHITE:
            bgColor = self.cssColorSyntax(bgColor)
        else:
            return dict()
        return (
            dict(bgcolor=bgColor)
            if printing
            else dict(style="background: %s" % bgColor)
        )

    def bodyRowFgColor(self, item):
        """Determine the foreground color for the item. Returns a CSS style
        specification."""
        if self.viewer.isShowingTasks():
            return {"class": item.status().statusString}
        else:
            return dict()

    def bodyCell(self, item, column, printing, level):
        """Return a <td> for the item/column combination."""
        attributes = {"class": column.name()}
        if printing and column.alignment() == wx.LIST_FORMAT_RIGHT:
            attributes["align"] = "right"
        return self.wrap(item, "td", level, oneLine=True, **attributes)

    @classmethod
    def wrap(class_, lines, tagName, level, oneLine=False, **attributes):
        """Wrap one or more lines with <tagName [optional attributes]> and
        </tagName>."""
        if attributes:
            attributes = " " + " ".join(
                sorted(
                    '%s="%s"' % (key, value)
                    for key, value in attributes.items()
                )
            )
        else:
            attributes = ""
        openTag = "<%s%s>" % (tagName, attributes)
        closeTag = "</%s>" % tagName
        if oneLine:
            return class_.indent(openTag + lines + closeTag, level)
        else:
            return (
                [class_.indent(openTag, level)]
                + lines
                + [class_.indent(closeTag, level)]
            )

    @staticmethod
    def indent(htmlText, level=0):
        """Indent the htmlText with spaces according to the level, so that
        the resulting HTML looks nicely indented."""
        return "  " * level + htmlText

    @classmethod
    def cssColorSyntax(class_, wxColor):
        """Translate the wx-color, either a wx.Colour instance or a tuple,
        into CSS syntax."""
        try:
            return wxColor.GetAsString(wx.C2S_CSS_SYNTAX)
        except AttributeError:  # color is a tuple
            return class_.cssColorSyntax(wx.Colour(*wxColor))

    @staticmethod
    def render(item, column, indent=False):
        """Render the item based on the column, escape HTML and indent
        the item with non-breaking spaces, if indent == True."""
        # Escape the rendered item and then replace newlines with <br>.
        if column.name() == "notes":

            def renderNotes(notes):
                bf = io.StringIO()
                for note in sorted(notes, key=lambda note: note.subject()):
                    bf.write("<p>\n")
                    bf.write(html.escape(note.subject()))
                    bf.write("<br />\n")
                    bf.write(html.escape(note.description()))
                    bf.write("</p>\n")
                    if note.children():
                        bf.write('<div style="padding-left: 20px;">\n')
                        bf.write(renderNotes(note.children()))
                        bf.write("</div>\n")
                return bf.getvalue()

            return renderNotes(item.notes())
        elif column.name() == "attachments":
            return "<br />".join(
                map(
                    html.escape,
                    sorted(
                        [
                            attachment.subject()
                            for attachment in item.attachments()
                        ]
                    ),
                )
            )

        renderedItem = html.escape(
            column.render(item, humanReadable=False)
        ).replace("\n", "<br>")
        if indent:
            # Indent the subject with whitespace
            renderedItem = "&nbsp;" * len(item.ancestors()) * 3 + renderedItem
        if not renderedItem:
            # Make sure the empty cell is drawn
            renderedItem = "&nbsp;"
        return renderedItem
