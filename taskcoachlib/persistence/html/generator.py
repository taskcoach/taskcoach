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


def viewer2html(viewer, css_filename=None, selection_only=False, columns=None):
    converter = Viewer2HTMLConverter(viewer)
    columns = columns or viewer.visibleColumns()
    return converter(css_filename, columns, selection_only)


class Viewer2HTMLConverter(object):
    """Class to convert the visible contents of a viewer into HTML."""

    docType = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">'
    metaTag = (
        '<meta http-equiv="Content-Type" content="text/html;charset=utf-8">'
    )
    cssLink = (
        '<link href="%s" rel="stylesheet" type="text/css" media="screen">'
    )

    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.count = 0

    def __call__(self, css_filename, columns, selectionOnly):
        """Create an HTML document."""
        lines = (
            [self.docType]
            + self.html(css_filename, columns, selectionOnly)
            + [""]
        )
        return "\n".join(lines), self.count

    def html(self, css_filename, columns, selectionOnly, level=0):
        """Returns all HTML, consisting of header and body."""
        printing = not css_filename
        html_content = self.html_header(
            css_filename, level + 1
        ) + self.html_body(columns, selectionOnly, printing, level + 1)
        return self.wrap(html_content, "html", level)

    def html_header(self, css_filename, level):
        """Return the HTML header <head>."""
        html_header_content = self.html_header_content(css_filename, level + 1)
        return self.wrap(html_header_content, "head", level)

    def html_header_content(self, css_filename, level):
        """Returns the HTML header section, containing meta tag, title, and
        optional link to a CSS stylesheet."""
        html_header_content = [
            self.indent(self.metaTag, level),
            self.wrap(self.viewer.title(), "title", level, one_line=True),
        ] + self.style(level, not css_filename)
        if css_filename:
            html_header_content.append(
                self.indent(self.cssLink % css_filename, level)
            )
        return html_header_content

    def style(self, level, include_all_css):
        """Add a style section that contains the alignment for the columns. If
        there is no external CSS file, we include all CSS style information
        in a HTML style section."""
        visible_columns = self.viewer.visibleColumns()
        column_alignments = [
            {
                wx.LIST_FORMAT_LEFT: "left",
                wx.LIST_FORMAT_CENTRE: "center",
                wx.LIST_FORMAT_RIGHT: "right",
            }[column.alignment()]
            for column in visible_columns
        ]
        style_content = []
        for column, alignment in zip(visible_columns, column_alignments):
            column_style = self.indent(
                ".%s {text-align: %s}" % (column.name(), alignment), level + 1
            )
            style_content.append(column_style)
        if include_all_css:
            style_content.extend(
                [self.indent(line, level + 1) for line in css.split("\n")]
            )
        return self.wrap(style_content, "style", level, type="text/css")

    def html_body(self, columns, selectionOnly, printing, level):
        """Returns the HTML body section, containing one table with all
        visible data."""
        html_body_content = []
        if printing:
            html_body_content.append(
                self.wrap(self.viewer.title(), "h1", level, one_line=True)
            )
        html_body_content.extend(
            self.table(columns, selectionOnly, printing, level + 1)
        )
        return self.wrap(html_body_content, "body", level)

    def table(self, columns, selectionOnly, printing, level):
        """Returns the table, consisting of caption, table header and table
        body."""
        table_content = [] if printing else [self.table_caption(level + 1)]
        table_content.extend(
            self.table_header(columns, printing, level + 1)
            + self.table_body(columns, selectionOnly, printing, level + 1)
        )
        attributes = dict(id="table")
        if printing:
            attributes["border"] = "1"
        return self.wrap(table_content, "table", level, **attributes)

    def table_caption(self, level):
        """Returns the table caption, based on the viewer title."""
        return self.wrap(self.viewer.title(), "caption", level, one_line=True)

    def table_header(self, columns, printing, level):
        """Returns the table header section <thead> containing the header
        row with the column headers."""
        table_header_content = self.header_row(columns, printing, level + 1)
        return self.wrap(table_header_content, "thead", level)

    def header_row(self, columns, printing, level):
        """Returns the header row <tr> for the table."""
        header_row_content = []
        for column in columns:
            header_row_content.append(
                self.header_cell(column, printing, level + 1)
            )
        return self.wrap(
            header_row_content, "tr", level, **{"class": "header"}
        )

    def header_cell(self, column, printing, level):
        """Returns a table header <th> for the specific column."""
        header = column.header() or "&nbsp;"
        name = column.name()
        attributes = {"scope": "col", "class": name}
        if self.viewer.isSortable() and self.viewer.isSortedBy(name):
            attributes["id"] = "sorted"
            if printing:
                header = self.wrap(header, "u", level + 1, one_line=True)
        return self.wrap(header, "th", level, one_line=True, **attributes)

    def table_body(self, columns, selectionOnly, printing, level):
        """Returns the table body <tbody>."""
        tree = self.viewer.is_tree_viewer()
        self.count = 0
        table_body_content = []
        for item in self.viewer.visible_items():
            if selectionOnly and not self.viewer.isselected(item):
                continue
            self.count += 1
            table_body_content.extend(
                self.body_row(item, columns, tree, printing, level + 1)
            )
        return self.wrap(table_body_content, "tbody", level)

    def body_row(self, item, columns, tree, printing, level):
        """Returns a <tr> containing the values of item for the
        visibleColumns."""
        fg_color = item.shown_fg_color()
        bg_color = item.shown_bg_color()
        if bg_color and bg_color == wx.WHITE:
            bg_color = None
        body_row_content = []
        for column in columns:
            rendered_item = self.render(
                item, column, indent=not body_row_content and tree
            )
            body_row_content.append(
                self.body_cell(rendered_item, column, printing, level + 1)
            )
        styles = []
        if fg_color:
            styles.append("color: %s" % self.css_color(fg_color))
        if bg_color:
            styles.append("background: %s" % self.css_color(bg_color))
        attributes = dict()
        if styles:
            attributes["style"] = "; ".join(styles)
        return self.wrap(body_row_content, "tr", level, **attributes)

    @staticmethod
    def css_color(wx_color):
        """Convert a wx.Colour to hex (#RRGGBB) format for HTML attributes."""
        if isinstance(wx_color, tuple):
            wx_color = wx.Colour(*wx_color)
        return "#%02x%02x%02x" % (
            wx_color.Red(),
            wx_color.Green(),
            wx_color.Blue(),
        )

    def body_cell(self, item, column, printing, level):
        """Return a <td> for the item/column combination."""
        attributes = {"class": column.name()}
        if printing and column.alignment() == wx.LIST_FORMAT_RIGHT:
            attributes["align"] = "right"
        return self.wrap(item, "td", level, one_line=True, **attributes)

    @classmethod
    def wrap(cls, lines, tag_name, level, one_line=False, **attributes):
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
        open_tag = "<%s%s>" % (tag_name, attributes)
        close_tag = "</%s>" % tag_name
        if one_line:
            return cls.indent(open_tag + lines + close_tag, level)
        else:
            return (
                [cls.indent(open_tag, level)]
                + lines
                + [cls.indent(close_tag, level)]
            )

    @staticmethod
    def indent(html_text, level=0):
        """Indent the htmlText with spaces according to the level, so that
        the resulting HTML looks nicely indented."""
        return "  " * level + html_text

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

        rendered_item = html.escape(
            column.render(item, human_readable=False)
        ).replace("\n", "<br>")
        if indent:
            # Indent the subject with whitespace
            rendered_item = (
                "&nbsp;" * len(item.ancestors()) * 3 + rendered_item
            )
        if not rendered_item:
            # Make sure the empty cell is drawn
            rendered_item = "&nbsp;"
        return rendered_item
