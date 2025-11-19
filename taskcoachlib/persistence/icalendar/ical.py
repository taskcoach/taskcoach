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

"""
This module defines classes and functions to handle the VCalendar
format.
"""  # pylint: disable=W0105

from taskcoachlib.domain.base import Object
from taskcoachlib.domain import date
from taskcoachlib.i18n import _

import ast
import operator
import time, calendar, datetime


def safe_eval_datetime_expr(expr, context):
    """Safely evaluate datetime expressions using AST parsing.

    Only allows safe operations: attribute access, function calls on allowed
    objects, arithmetic operations, and string operations.
    """

    # Allowed binary operators
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
    }

    # Allowed unary operators
    allowed_unary = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def eval_node(node):
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Num):  # Python 3.7 compatibility
            return node.n
        elif isinstance(node, ast.Str):  # Python 3.7 compatibility
            return node.s
        elif isinstance(node, ast.Name):
            name = node.id
            if name in context:
                return context[name]
            raise ValueError(f"Name '{name}' not allowed in expression")
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in allowed_operators:
                raise ValueError(f"Operator {type(node.op).__name__} not allowed")
            left = eval_node(node.left)
            right = eval_node(node.right)
            return allowed_operators[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            if type(node.op) not in allowed_unary:
                raise ValueError(f"Unary operator {type(node.op).__name__} not allowed")
            operand = eval_node(node.operand)
            return allowed_unary[type(node.op)](operand)
        elif isinstance(node, ast.Call):
            func = eval_node(node.func)
            args = [eval_node(arg) for arg in node.args]
            kwargs = {kw.arg: eval_node(kw.value) for kw in node.keywords}
            return func(*args, **kwargs)
        elif isinstance(node, ast.Attribute):
            value = eval_node(node.value)
            return getattr(value, node.attr)
        elif isinstance(node, ast.Tuple):
            return tuple(eval_node(elt) for elt in node.elts)
        elif isinstance(node, ast.List):
            return [eval_node(elt) for elt in node.elts]
        else:
            raise ValueError(f"Node type {type(node).__name__} not allowed")

    try:
        tree = ast.parse(expr, mode='eval')
        return eval_node(tree)
    except (SyntaxError, ValueError) as e:
        raise ValueError(f"Invalid expression '{expr}': {e}")

# { Utility functions


def parseDateTime(fulldate):
    """Parses a datetime as seen in iCalendar files into a
    L{taskcoachlib.domain.date.DateTime} object."""

    try:
        dt, tm = fulldate.split("T")
        year, month, day = int(dt[:4]), int(dt[4:6]), int(dt[6:8])
        hour, minute, second = int(tm[:2]), int(tm[2:4]), int(tm[4:6])

        if fulldate.endswith("Z"):
            # GMT. Convert this to local time.
            localTime = time.localtime(
                calendar.timegm(
                    (year, month, day, hour, minute, second, 0, 0, -1)
                )
            )
            year, month, day, hour, minute, second = localTime[:6]
    except Exception as e:
        raise ValueError("Malformed date: %s (%s)" % (fulldate, str(e)))

    return date.DateTime(year, month, day, hour, minute, second)


def fmtDateTime(dt):
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


def quoteString(s):
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

# { Parsing iCalendar files


class VCalendarParser(object):
    """Base parser class for iCalendar files. This uses the State
    pattern (in its Python incarnation, replacing the class of an
    object at runtime) in order to parse different objects in the
    VCALENDAR. Other states are

     - VTodoParser: parses VTODO objects.

    @ivar kwargs: While parsing, the keyword arguments for the
        domain object creation for the current (parsed) object.
    @ivar tasks: A list of dictionaries suitable to use as
        keyword arguments for task creation, representing all
        VTODO object in the parsed file."""  # pylint: disable=W0511

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stateMap = {
            "VCALENDAR": VCalendarParser,
            "VTODO": VTodoParser,
            "VNOTE": VNoteParser,
        }
        self.tasks = []
        self.notes = []
        self.init()

    def init(self):
        """Called after a state change."""
        self.kwargs = {}  # pylint: disable=W0201

    def setState(self, state):
        """Sets the state (class) of the parser object."""
        self.__class__ = state
        self.init()

    def parse(self, lines):
        """Actually parses the file.
        @param lines: A list of lines."""

        # TODO: avoid using indexes here, just iterate. This way the
        # method can accept a file object as argument.

        currentLine = lines[0]

        for line in lines[1:]:
            if line.startswith(" ") or line.startswith("\t"):
                currentLine += line[1:]
            else:
                if self.handleLine(currentLine):
                    return
                currentLine = line

        self.handleLine(currentLine)

    def handleLine(self, line):
        """Called by L{parse} for each line to parse. L{parse} is
        supposed to have handled the unfolding."""

        if line.startswith("BEGIN:"):
            try:
                self.setState(self.stateMap[line[6:]])
            except KeyError:
                raise TypeError("Unrecognized vcal type: %s" % line[6:])
        elif line.startswith("END:"):
            if line[4:] == "VCALENDAR":
                return True
            else:
                self.onFinish()
                self.setState(VCalendarParser)
        else:
            try:
                idx = line.index(":")
            except ValueError:
                raise RuntimeError("Malformed vcal line: %s" % line)

            details, value = line[:idx].split(";"), line[idx + 1 :]
            name, specs = details[0], details[1:]
            specs = dict([tuple(v.split("=")) for v in specs])

            if "ENCODING" in specs:
                value = value.decode(specs["ENCODING"].lower())
            if "CHARSET" in specs:
                value = value.decode(specs["CHARSET"].lower())
            else:
                # Some  servers only  specify CHARSET  when  there are
                # non-ASCII characters :)
                # More, Horde encodes in UTF-8 without specifying the charset.
                value = value.decode("UTF-8")

            # If  an item  name ends  with  'TMPL', it's  part of  the
            # template system and has to be eval()ed.

            if name.endswith("TMPL"):
                name = name[:-4]
                context = dict()
                context.update(datetime.__dict__)
                context.update(date.__dict__)
                context["_"] = _
                value = safe_eval_datetime_expr(value, context)
                if isinstance(value, datetime.datetime):
                    value = fmtDateTime(value)

            self.acceptItem(name, value)

        return False

    def onFinish(self):
        """This method is called when the current object ends."""
        raise NotImplementedError

    def acceptItem(self, name, value):
        """Called on each new 'item', i.e. key/value pair. Default
        behaviour is to store the pair in the 'kwargs' instance
        variable (which is emptied in L{init})."""
        if name in ("CREATED", "DCREATED"):
            self.kwargs["creationDateTime"] = parseDateTime(value)
        elif name == "LAST-MODIFIED":
            self.kwargs["modificationDateTime"] = parseDateTime(value)
        elif name == "SUMMARY":
            self.kwargs["subject"] = value
        elif name == "CATEGORIES":
            # Horde escapes the comma, even though it's an actual separator.
            # I didn't found any way to include an actual comma in a Horde
            # "tag".
            self.kwargs["categories"] = [
                x.rstrip("\\").lstrip() for x in value.split(",")
            ]
        elif name == "DESCRIPTION":
            self.kwargs["description"] = value.replace("\\n", "\n")
        else:
            self.kwargs[name.lower()] = value


class VTodoParser(VCalendarParser):
    """This is the state responsible for parsing VTODO objects."""  # pylint: disable=W0511

    def onFinish(self):
        if "plannedStartDateTime" not in self.kwargs:
            # This means no planned start date, but the task constructor will
            # take today by default, so force.
            self.kwargs["plannedStartDateTime"] = date.DateTime()

        if "vcardStatus" in self.kwargs:
            if (
                self.kwargs["vcardStatus"] == "COMPLETED"
                and "completionDateTime" not in self.kwargs
            ):
                # Some servers only give the status, and not the date (SW)
                if "last-modified" in self.kwargs:
                    self.kwargs["completionDateTime"] = parseDateTime(
                        self.kwargs["last-modified"]
                    )
                else:
                    self.kwargs["completionDateTime"] = date.Now()

        self.kwargs["status"] = Object.STATUS_NONE
        self.tasks.append(self.kwargs)

    def acceptItem(self, name, value):
        if name == "DTSTART":
            self.kwargs["plannedStartDateTime"] = parseDateTime(value)
        elif name == "DUE":
            self.kwargs["dueDateTime"] = parseDateTime(value)
        elif name == "COMPLETED":
            self.kwargs["completionDateTime"] = parseDateTime(value)
        elif name == "PERCENT-COMPLETE":
            self.kwargs["percentageComplete"] = int(value)
        elif name == "UID":
            self.kwargs["id"] = value.decode("UTF-8")
        elif name == "PRIORITY":
            # Okay. Seems that in vcal,  the priority ranges from 1 to
            # 3, but what it means depends on the other client...

            self.kwargs["priority"] = int(value) - 1
        elif name == "STATUS":
            self.kwargs["vcardStatus"] = value
        else:
            super().acceptItem(name, value)


class VNoteParser(VCalendarParser):
    """Parse VNote objects."""

    def onFinish(self):
        # Summary is not mandatory.
        if "subject" not in self.kwargs:
            if "description" in self.kwargs:
                self.kwargs["subject"] = self.kwargs["description"].split(
                    "\n"
                )[0]
            else:
                self.kwargs["subject"] = ""
        self.kwargs["status"] = Object.STATUS_NONE
        self.notes.append(self.kwargs)

    def acceptItem(self, name, value):
        if name == "X-IRMC-LUID":
            self.kwargs["id"] = value.decode("UTF-8")
        elif name == "BODY":
            self.kwargs["description"] = value.replace("\\n", "\n")
        elif name == "CLASS":
            pass
        else:
            super().acceptItem(name, value)


# }

# ==============================================================================
# { Generating iCalendar files.


def VCalFromTask(task, encoding=True, doFold=True):
    """This function returns a string representing the task in
    iCalendar format."""

    encoding = ";ENCODING=QUOTED-PRINTABLE;CHARSET=UTF-8" if encoding else ""
    quote = quoteString if encoding else lambda s: s

    components = []
    components.append("BEGIN:VTODO")  # pylint: disable=W0511
    components.append("UID:%s" % task.id().encode("UTF-8"))

    if task.creationDateTime() > date.DateTime.min:
        components.append("CREATED:%s" % fmtDateTime(task.creationDateTime()))

    if task.modificationDateTime() > date.DateTime.min:
        components.append(
            "LAST-MODIFIED:%s" % fmtDateTime(task.modificationDateTime())
        )

    if task.plannedStartDateTime() != date.DateTime():
        components.append(
            "DTSTART:%s" % fmtDateTime(task.plannedStartDateTime())
        )

    if task.dueDateTime() != date.DateTime():
        components.append("DUE:%s" % fmtDateTime(task.dueDateTime()))

    if task.completionDateTime() != date.DateTime():
        components.append(
            "COMPLETED:%s" % fmtDateTime(task.completionDateTime())
        )

    if task.categories(recursive=True, upwards=True):
        categories = ",".join(
            [
                quote(str(c))
                for c in task.categories(recursive=True, upwards=True)
            ]
        )
        components.append("CATEGORIES%s:%s" % (encoding, categories))

    if task.completed():
        components.append("STATUS:COMPLETED")
    elif task.active():
        components.append("STATUS:NEEDS-ACTION")
    else:
        components.append("STATUS:CANCELLED")  # Hum...

    components.append(
        "DESCRIPTION%s:%s" % (encoding, quote(task.description()))
    )
    components.append("PRIORITY:%d" % min(3, task.priority() + 1))
    components.append("PERCENT-COMPLETE:%d" % task.percentageComplete())
    components.append("SUMMARY%s:%s" % (encoding, quote(task.subject())))
    components.append("END:VTODO")  # pylint: disable=W0511
    if doFold:
        return fold(components)
    return "\r\n".join(components) + "\r\n"


def VCalFromEffort(effort, encoding=True, doFold=True):
    encoding = ";ENCODING=QUOTED-PRINTABLE;CHARSET=UTF-8" if encoding else ""
    quote = quoteString if encoding else lambda s: s
    components = []
    components.append("BEGIN:VEVENT")
    components.append("UID:%s" % effort.id().encode("UTF-8"))
    components.append("SUMMARY%s:%s" % (encoding, quote(effort.subject())))
    components.append(
        "DESCRIPTION%s:%s" % (encoding, quote(effort.description()))
    )
    components.append("DTSTART:%s" % fmtDateTime(effort.getStart()))
    if effort.getStop():
        components.append("DTEND:%s" % fmtDateTime(effort.getStop()))
    components.append("END:VEVENT")
    if doFold:
        return fold(components)
    return "\r\n".join(components) + "\r\n"


def VNoteFromNote(note, encoding=True, doFold=True):
    encoding = ";ENCODING=QUOTED-PRINTABLE;CHARSET=UTF-8" if encoding else ""
    quote = quoteString if encoding else lambda s: s
    components = []
    components.append("BEGIN:VNOTE")
    components.append("X-IRMC-LUID: %s" % note.id().encode("UTF-8"))
    components.append("SUMMARY%s: %s" % (encoding, quote(note.subject())))
    components.append("BODY%s:%s" % (encoding, quote(note.description())))
    components.append("END:VNOTE")
    if note.categories(recursive=True, upwards=True):
        categories = ",".join(
            [
                quote(str(c))
                for c in note.categories(recursive=True, upwards=True)
            ]
        )
        components.append("CATEGORIES%s:%s" % (encoding, categories))
    if doFold:
        return fold(components)
    return "\r\n".join(components) + "\r\n"


# }


def fold(components, linewidth=75, eol="\r\n", indent=" "):
    lines = []
    # The iCalendar standard doesn't clearly state whether the maximum line
    # width includes the indentation or not. We keep on the safe side:
    indentedlinewidth = linewidth - len(indent)
    for component in components:
        componentLines = component.split("\n")
        firstLine = componentLines[0]
        firstLine, remainderFirstLine = (
            firstLine[:linewidth],
            firstLine[linewidth:],
        )
        lines.append(firstLine)
        while remainderFirstLine:
            nextLine, remainderFirstLine = (
                remainderFirstLine[:indentedlinewidth],
                remainderFirstLine[indentedlinewidth:],
            )
            lines.append(indent + nextLine)
        for line in componentLines[1:]:
            nextLine, remainder = line[:linewidth], line[linewidth:]
            lines.append(indent + nextLine)
            while remainder:
                nextLine, remainder = (
                    remainder[:indentedlinewidth],
                    remainder[indentedlinewidth:],
                )
                lines.append(indent + nextLine)
    return eol.join(lines) + eol if lines else ""
