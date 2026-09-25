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

# Generate VCalendar (iCalendar) text for tasks and efforts.

from taskcoachlib.domain import date

import time

# { Utility functions


def fmt_date_time(dt):
    """Formats a L{taskcoachlib.domain.date.DateTime} object to a string
    suitable for inclusion in an iCalendar file."""
    dt = dt.utcfromtimestamp(time.mktime(dt.timetuple()))
    return "%04d%02d%02dT%02d%02d%02dZ" % (
        dt.year,
        dt.month,
        dt.day,
        dt.hour,
        dt.minute,
        dt.second,
    )


def quote_string(s):
    """The 'quoted-printable' codec doesn't encode \n, but tries to
    fold lines with \n instead of CRLF and generally does strange
    things that ScheduleWorld does not understand (me neither, to an
    extent). Same thing with \r. This function works around this."""

    s = s.encode("UTF-8").encode("quoted-printable")
    s = s.replace("=\r", "")
    s = s.replace("=\n", "")
    s = s.replace("\r", "=0D")
    s = s.replace("\n", "=0A")
    return s


# }

# ==============================================================================
# { Generating iCalendar files.


def vcal_from_task(task, encoding=True, do_fold=True, selected_fields=None):
    """This function returns a string representing the task in
    iCalendar format.

    Args:
        task: The task to export
        encoding: Whether to use quoted-printable encoding
        do_fold: Whether to fold long lines
        selected_fields: Set of field keys to export, None for all.
            Required fields (uid, dtstamp) are always exported.
    """
    # Default to all fields if not specified
    if selected_fields is None:
        selected_fields = {
            "uid",
            "dtstamp",
            "summary",
            "description",
            "dtstart",
            "due",
            "completed",
            "categories",
            "status",
            "priority",
            "percent",
            "created",
            "lastmod",
        }

    encoding_str = (
        ";ENCODING=QUOTED-PRINTABLE;CHARSET=UTF-8" if encoding else ""
    )
    quote = quote_string if encoding else lambda s: s

    components = []
    components.append("BEGIN:VTODO")  # pylint: disable=W0511

    # Required fields (always exported)
    components.append("UID:%s" % task.id())
    components.append("DTSTAMP:%s" % fmt_date_time(date.Now()))

    if (
        "created" in selected_fields
        and task.creationDateTime() > date.DateTime.min
    ):
        components.append(
            "CREATED:%s" % fmt_date_time(task.creationDateTime())
        )

    if (
        "lastmod" in selected_fields
        and task.modificationDateTime() > date.DateTime.min
    ):
        components.append(
            "LAST-MODIFIED:%s" % fmt_date_time(task.modificationDateTime())
        )

    if (
        "dtstart" in selected_fields
        and task.plannedStartDateTime() != date.DateTime()
    ):
        components.append(
            "DTSTART:%s" % fmt_date_time(task.plannedStartDateTime())
        )

    if "due" in selected_fields and task.dueDateTime() != date.DateTime():
        components.append("DUE:%s" % fmt_date_time(task.dueDateTime()))

    if (
        "completed" in selected_fields
        and task.completionDateTime() != date.DateTime()
    ):
        components.append(
            "COMPLETED:%s" % fmt_date_time(task.completionDateTime())
        )

    if "categories" in selected_fields and task.categories(
        recursive=True, upwards=True
    ):
        categories = ",".join(
            [
                quote(str(c))
                for c in task.categories(recursive=True, upwards=True)
            ]
        )
        components.append("CATEGORIES%s:%s" % (encoding_str, categories))

    if "status" in selected_fields:
        # RFC 5545 VTODO STATUS: NEEDS-ACTION, IN-PROCESS, COMPLETED, CANCELLED
        # Fixes: https://sourceforge.net/p/taskcoach/bugs/1560/
        #         https://github.com/taskcoach/taskcoach/issues/281
        if task.completed():
            components.append("STATUS:COMPLETED")
        elif task.active():
            components.append("STATUS:IN-PROCESS")
        else:
            components.append("STATUS:NEEDS-ACTION")

    if "description" in selected_fields:
        components.append(
            "DESCRIPTION%s:%s" % (encoding_str, quote(task.description()))
        )

    if "priority" in selected_fields:
        components.append("PRIORITY:%d" % min(3, task.priority() + 1))

    if "percent" in selected_fields:
        components.append("PERCENT-COMPLETE:%d" % task.percentageComplete())

    if "summary" in selected_fields:
        components.append(
            "SUMMARY%s:%s" % (encoding_str, quote(task.subject()))
        )

    components.append("END:VTODO")  # pylint: disable=W0511
    if do_fold:
        return fold(components)
    return "\r\n".join(components) + "\r\n"


def vcal_from_effort(
    effort, encoding=True, do_fold=True, selected_fields=None
):
    """This function returns a string representing the effort in
    iCalendar VEVENT format.

    Args:
        effort: The effort to export
        encoding: Whether to use quoted-printable encoding
        do_fold: Whether to fold long lines
        selected_fields: Set of field keys to export, None for all.
            Required fields (uid, dtstamp) are always exported.
    """
    # Default to all fields if not specified
    if selected_fields is None:
        selected_fields = {
            "uid",
            "dtstamp",
            "summary",
            "description",
            "dtstart",
            "dtend",
        }

    encoding_str = (
        ";ENCODING=QUOTED-PRINTABLE;CHARSET=UTF-8" if encoding else ""
    )
    quote = quote_string if encoding else lambda s: s

    components = []
    components.append("BEGIN:VEVENT")

    # Required fields (always exported)
    components.append("UID:%s" % effort.id())
    components.append("DTSTAMP:%s" % fmt_date_time(date.Now()))

    if "summary" in selected_fields:
        components.append(
            "SUMMARY%s:%s" % (encoding_str, quote(effort.subject()))
        )

    if "description" in selected_fields:
        components.append(
            "DESCRIPTION%s:%s" % (encoding_str, quote(effort.description()))
        )

    if "dtstart" in selected_fields:
        components.append("DTSTART:%s" % fmt_date_time(effort.getStart()))

    if "dtend" in selected_fields and effort.getStop():
        components.append("DTEND:%s" % fmt_date_time(effort.getStop()))

    components.append("END:VEVENT")
    if do_fold:
        return fold(components)
    return "\r\n".join(components) + "\r\n"


# }


def fold(components, linewidth=75, eol="\r\n", indent=" "):
    lines = []
    # The iCalendar standard doesn't clearly state whether the maximum line
    # width includes the indentation or not. We keep on the safe side:
    indentedlinewidth = linewidth - len(indent)
    for component in components:
        component_lines = component.split("\n")
        first_line = component_lines[0]
        first_line, remainder_first_line = (
            first_line[:linewidth],
            first_line[linewidth:],
        )
        lines.append(first_line)
        while remainder_first_line:
            next_line, remainder_first_line = (
                remainder_first_line[:indentedlinewidth],
                remainder_first_line[indentedlinewidth:],
            )
            lines.append(indent + next_line)
        for line in component_lines[1:]:
            next_line, remainder = line[:linewidth], line[linewidth:]
            lines.append(indent + next_line)
            while remainder:
                next_line, remainder = (
                    remainder[:indentedlinewidth],
                    remainder[indentedlinewidth:],
                )
                lines.append(indent + next_line)
    return eol.join(lines) + eol if lines else ""
