# -*- coding: utf-8 -*-

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

from taskcoachlib import meta, patterns
from taskcoachlib.meta.debug import log_step
from taskcoachlib.domain import (
    base,
    date,
    effort,
    task,
    category,
    categorizable,
    note,
    attachment,
)
from taskcoachlib.i18n import translate
from .defaults import read
from taskcoachlib.thirdparty.deltaTime import nlTimeExpression
from taskcoachlib.tools import wxhelper
import ast
import io
import operator
import os
import re
import types
import wx
from lxml import etree as ET

# What date expressions in templates saved before tskversion 32 use
OLD_TEMPLATE_NAMES = dict(
    Now=date.Now,
    Today=date.Today,
    Tomorrow=date.Tomorrow,
    Yesterday=date.Yesterday,
    DateTime=date.DateTime,
    Date=date.Date,
    TimeDelta=date.TimeDelta,
)


# Characters XML forbids, and references to them: a file saved before
# stored text dropped them (P34) holds them, and the parser refuses it
_XML_FORBIDDEN = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
_REFERENCE = re.compile("&#(x[0-9a-fA-F]+|[0-9]+);")


def _xml_forbids(code):
    return (
        code < 0x20
        and code not in (0x9, 0xA, 0xD)
        or 0xD800 <= code <= 0xDFFF
        or code in (0xFFFE, 0xFFFF)
        or code > 0x10FFFF
    )


def _without_forbidden_reference(match):
    number = match.group(1)
    code = int(number[1:], 16) if number[0] == "x" else int(number)
    return "" if _xml_forbids(code) else match.group(0)


def _without_broken_lines(content):
    """tskversion 24 may hold newlines in element tags: they go."""
    if "><spds><sources><TaskCoach-\n" not in content:
        return content
    lines = content.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.endswith(("<TaskCoach-\n", "</TaskCoach-\n")):
            lines[index] = line[:-1]
            lines[index + 1] = lines[index + 1][:-1]
    return "".join(lines)


def safe_eval_date_expr(expr, context):
    """Safely evaluate date expressions using AST parsing.

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
        elif isinstance(node, ast.Name):
            name = node.id
            if name in context:
                return context[name]
            raise ValueError(f"Name '{name}' not allowed in expression")
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in allowed_operators:
                raise ValueError(
                    f"Operator {type(node.op).__name__} not allowed"
                )
            left = eval_node(node.left)
            right = eval_node(node.right)
            return allowed_operators[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            if type(node.op) not in allowed_unary:
                raise ValueError(
                    f"Unary operator {type(node.op).__name__} not allowed"
                )
            operand = eval_node(node.operand)
            return allowed_unary[type(node.op)](operand)
        elif isinstance(node, ast.Call):
            func = eval_node(node.func)
            args = [eval_node(arg) for arg in node.args]
            kwargs = {kw.arg: eval_node(kw.value) for kw in node.keywords}
            return func(*args, **kwargs)
        elif isinstance(node, ast.Attribute):
            value = eval_node(node.value)
            # Private names and modules lead out of the date API
            if node.attr.startswith("_") or isinstance(
                value, types.ModuleType
            ):
                raise ValueError(f"Attribute '{node.attr}' not allowed")
            return getattr(value, node.attr)
        elif isinstance(node, ast.Tuple):
            return tuple(eval_node(elt) for elt in node.elts)
        elif isinstance(node, ast.List):
            return [eval_node(elt) for elt in node.elts]
        else:
            raise ValueError(f"Node type {type(node).__name__} not allowed")

    try:
        tree = ast.parse(expr, mode="eval")
        return eval_node(tree)
    except (SyntaxError, ValueError) as e:
        raise ValueError(f"Invalid expression '{expr}': {e}")


def parseAndAdjustDateTime(string, *timeDefaults):
    dateTime = date.parseDateTime(string, *timeDefaults)
    if (
        dateTime != date.DateTime()
        and dateTime is not None
        and dateTime.time() == date.Time(23, 59, 0, 0)
    ):
        dateTime = date.DateTime(
            year=dateTime.year,
            month=dateTime.month,
            day=dateTime.day,
            hour=23,
            minute=59,
            second=59,
        )
    return dateTime


class XMLReaderTooNewException(Exception):
    pass


class XMLReader(object):
    """Class for reading task files in the default XML task file format."""

    default_start_time = (0, 0, 0)
    default_end_time = (23, 59, 59)

    def __init__(self, fd):
        self.__fd = fd
        self.__default_font_size = wx.SystemSettings.GetFont(
            wx.SYS_DEFAULT_GUI_FONT
        ).GetPointSize()
        self.__modification_datetimes = {}
        self.__prerequisites = {}
        # A task's or note's ID -> its categories' IDs
        self.__categories_of = {}
        # Before tskversion 38: a category's ID -> its members' IDs
        self.__members_of = {}
        # Track all IDs and their locations for duplicate detection
        # Maps ID -> list of (object_type, hierarchical_path) tuples
        self.__id_registry = {}
        self.__current_path = []  # Stack for tracking hierarchical location

    def tskversion(self):
        """Return the version of the current task file. Note that this is not
        the version of the application. The task file has its own version
        numbering (a number that is increasing on every change)."""
        return self.__tskversion

    def __register_id(self, obj_id, obj_type, subject):
        """Register an object's ID and return the ID it gets: the first
        item with an ID keeps it, a later duplicate gets a new one
        (docs/PERSISTENCE_XML.md, Duplicate IDs)."""
        if not obj_id:
            return obj_id
        path = " -> ".join(self.__current_path + [f"{obj_type}: {subject}"])
        locations = self.__id_registry.setdefault(obj_id, [])
        locations.append((obj_type, path))
        return obj_id if len(locations) == 1 else base.new_id()

    def get_duplicate_ids(self):
        """Return a dict of IDs that appear more than once.

        Returns dict mapping ID -> list of (object_type, path) tuples
        for IDs that have duplicates.
        """
        return {
            obj_id: locations
            for obj_id, locations in self.__id_registry.items()
            if len(locations) > 1
        }

    def read(self):
        """Read the task file and return the tasks, categories and
        notes."""
        content = self.__without_characters_xml_forbids(
            _without_broken_lines(self.__fd.read())
        )
        # As bytes: lxml refuses text that declares its encoding. lxml
        # reads the PIs
        root = ET.parse(io.BytesIO(content.encode("utf-8"))).getroot()
        versions = [
            pi.attrib.get("tskversion")
            for pi in root.xpath("//processing-instruction()")
            if pi.target == "taskcoach"
        ]
        if not versions or versions[0] is None:
            raise ValueError("no Task Coach file version (tskversion)")
        self.__tskversion = int(versions[0])  # pylint: disable=W0201
        if self.__tskversion > meta.data.tskversion:
            # Version number of task file is too high
            raise XMLReaderTooNewException
        tasks = self.__parse_task_nodes(root)
        self.__resolve_prerequisites_and_dependencies(tasks)
        notes = self.__parse_note_nodes(root)
        if self.__tskversion <= 13:
            categories = self.__parse_category_nodes_from_task_nodes(root)
        else:
            categories = self.__parse_category_nodes(root)
        self.__resolve_categories(categories, tasks, notes)

        # An old file's SyncML section and GUID are not read: SyncML
        # was removed, and nothing used the GUID after it

        # Restored last, over the dates the reading itself set, in one
        # event (docs/ATTRIBUTE_PATTERN.md, Event Batching During Load)
        event = patterns.Event()
        for (
            item,
            modification_datetime,
        ) in self.__modification_datetimes.items():
            item.set_modification_datetime(modification_datetime, event=event)
        event.send()

        return tasks, categories, notes

    def __without_characters_xml_forbids(self, content):
        """Stored text drops them since 2026-09-30
        (docs/ATTRIBUTE_PATTERN.md, Text); an older file may hold
        them."""
        cleaned = _REFERENCE.sub(
            _without_forbidden_reference, _XML_FORBIDDEN.sub("", content)
        )
        if cleaned != content:
            log_step(
                "dropped characters XML forbids from",
                self.__fd.name,
                prefix="XML",
            )
        return cleaned

    def __children_to_load(self, node, tag):
        """The child nodes with the tag, except those saved as deleted:
        until 2026, with SyncML enabled, deleting only marked an item
        (status 3) until the next sync. Such items were hidden and could
        not be restored, so they are not loaded."""
        return [
            child
            for child in node.findall(tag)
            if not (
                self.__tskversion >= 22 and child.attrib.get("status") == "3"
            )
        ]

    def __parse_task_nodes(self, node):
        """Recursively parse all tasks from the node and return a list of
        task instances."""
        return [
            self._parse_task_node(child)
            for child in self.__children_to_load(node, "task")
        ]

    def __resolve_prerequisites_and_dependencies(self, tasks):
        """Replace all prerequisites with the actual task instances
        and set the dependencies."""
        tasks_by_id = dict()

        def collect_ids(tasks):
            """Create a mapping from task ids to task instances."""
            for each_task in tasks:
                tasks_by_id[each_task.id()] = each_task
                collect_ids(each_task.children())

        def resolve_ids(tasks):
            """Replace all prerequisites ids with actual task instances and
            set the dependencies."""
            for each_task in tasks:
                prerequisites = set()
                for prerequisiteId in self.__prerequisites.get(
                    each_task.id(), []
                ):
                    try:
                        prerequisites.add(tasks_by_id[prerequisiteId])
                    except KeyError:
                        # Release 1.2.11 and older have a bug where tasks can
                        # have prerequisites listed that don't exist anymore
                        pass
                each_task.set_prerequisites(prerequisites)
                for prerequisite in prerequisites:
                    prerequisite.add_dependencies([each_task])
                resolve_ids(each_task.children())

        collect_ids(tasks)
        resolve_ids(tasks)

    def __resolve_categories(self, categories, tasks, notes):
        """Link each task and note to its categories. Before tskversion
        38 the file stored the links on the category, as its members:
        they are turned into the items' own, where the next save writes
        them (docs/PERSISTENCE_XML.md, Category Membership)."""

        items, categories_by_id = {}, {}

        def map_ids(obj):
            if isinstance(obj, categorizable.CategorizableCompositeObject):
                items[obj.id()] = obj
            if isinstance(obj, category.Category):
                categories_by_id[obj.id()] = obj
            if isinstance(obj, base.CompositeObject):
                for child in obj.children():
                    map_ids(child)
            if isinstance(obj, note.NoteOwner):
                for each in obj.notes():
                    map_ids(each)
            if isinstance(obj, attachment.AttachmentOwner):
                for each in obj.attachments():
                    map_ids(each)

        for each in list(categories) + list(tasks) + list(notes):
            map_ids(each)
        for category_id, member_ids in self.__members_of.items():
            for member_id in member_ids:
                self.__categories_of.setdefault(member_id, []).append(
                    category_id
                )
        event = patterns.Event()
        for item_id, category_ids in self.__categories_of.items():
            linked = [
                categories_by_id[each]
                for each in category_ids
                if each in categories_by_id
            ]
            if linked and item_id in items:
                items[item_id].addCategory(*linked, event=event)
        event.send()

    def __parse_category_nodes(self, node):
        return [
            self.__parse_category_node(child)
            for child in self.__children_to_load(node, "category")
        ]

    def __parse_note_nodes(self, node):
        return [
            self.__parse_note_node(child)
            for child in self.__children_to_load(node, "note")
        ]

    def __parse_category_node(self, category_node):
        """Recursively parse the categories from the node and return a
        category instance."""
        subject = category_node.attrib.get("subject", "")
        obj_id = self.__register_id(
            category_node.attrib.get("id", ""), "Category", subject
        )
        self.__current_path.append(f"Category: {subject}")
        try:
            kwargs = self.__parse_base_composite_attributes(
                category_node, self.__parse_category_nodes
            )
            kwargs["id"] = obj_id
            notes = self.__parse_note_nodes(category_node)
            filtered = self.__value(
                category_node, "filtered", self.__parse_boolean
            )
            exclusive = self.__value(
                category_node, "exclusiveSubcategories", self.__parse_boolean
            )
            style_priority = self.__value(category_node, "stylePriority", int)
            kwargs.update(
                dict(
                    notes=notes,
                    filtered=filtered,
                    exclusiveSubcategories=exclusive,
                    stylePriority=style_priority,
                )
            )
            if self.__tskversion > 20:
                kwargs["attachments"] = self.__parse_attachments(category_node)
            theCategory = category.Category(**kwargs)  # pylint: disable=W0142
            if self.__tskversion < 38:
                members = category_node.attrib.get(
                    "tasks" if self.__tskversion < 19 else "categorizables",
                    "",
                )
                self.__members_of.setdefault(theCategory.id(), []).extend(
                    members.split()
                )
            return self.__save_modification_datetime(theCategory)
        finally:
            self.__current_path.pop()

    def __parse_category_nodes_from_task_nodes(self, root):
        """In tskversion <=13 category nodes were subnodes of task nodes."""
        task_nodes = root.findall(".//task")
        category_mapping = self.__parse_category_nodes_within_task_nodes(
            task_nodes
        )
        subject_category_mapping = {}
        for task_id, categories in list(category_mapping.items()):
            for subject in categories:
                if subject in subject_category_mapping:
                    cat = subject_category_mapping[subject]
                else:
                    cat = category.Category(subject)
                    subject_category_mapping[subject] = cat
                self.__members_of.setdefault(cat.id(), []).append(task_id)
        return list(subject_category_mapping.values())

    def __parse_category_nodes_within_task_nodes(self, task_nodes):
        """In tskversion <=13 category nodes were subnodes of task nodes."""
        category_mapping = {}
        for node in task_nodes:
            task_id = node.attrib["id"]
            categories = [child.text for child in node.findall("category")]
            category_mapping.setdefault(task_id, []).extend(categories)
        return category_mapping

    def _parse_task_node(self, task_node):
        """Recursively parse the node and return a task instance."""
        # Get subject early for path tracking
        subject = task_node.attrib.get("subject", "")
        obj_id = self.__register_id(
            task_node.attrib.get("id", ""), "Task", subject
        )
        self.__current_path.append(f"Task: {subject}")
        try:
            planned_start_datetime_attribute_name = (
                "startdate" if self.tskversion() <= 33 else "plannedstartdate"
            )
            kwargs = self.__parse_base_composite_attributes(
                task_node, self.__parse_task_nodes
            )
            kwargs["id"] = obj_id
            value = self.__value

            def start_time(text):
                return date.parseDateTime(text, *self.default_start_time)

            def end_time(text):
                return date.parseDateTime(text, *self.default_end_time)

            def due_time(text):
                return parseAndAdjustDateTime(text, *self.default_end_time)

            kwargs.update(
                dict(
                    plannedStartDateTime=value(
                        task_node,
                        "plannedstartdate",
                        start_time,
                        planned_start_datetime_attribute_name,
                    ),
                    dueDateTime=value(task_node, "duedate", due_time),
                    actualStartDateTime=value(
                        task_node, "actualstartdate", start_time
                    ),
                    completionDateTime=value(
                        task_node, "completiondate", end_time
                    ),
                    percentageComplete=value(
                        task_node, "percentageComplete", int
                    ),
                    budget=value(task_node, "budget", date.parseTimeDelta),
                    plannedDuration=value(
                        task_node, "plannedDuration", date.parseTimeDelta
                    ),
                    plannedDurationMode=value(
                        task_node, "plannedDurationMode"
                    ),
                    priority=value(task_node, "priority", int),
                    hourlyFee=value(task_node, "hourlyFee", float),
                    fixedFee=value(task_node, "fixedFee", float),
                    reminder=value(task_node, "reminder", date.parseDateTime),
                    reminderBeforeSnooze=value(
                        task_node, "reminderBeforeSnooze", date.parseDateTime
                    ),
                    # Ignore prerequisites for now, they'll be resolved later
                    prerequisites=[],
                    shouldMarkCompletedWhenAllChildrenCompleted=value(
                        task_node,
                        "shouldMarkCompletedWhenAllChildrenCompleted",
                        self.__parse_boolean,
                    ),
                    efforts=self.__parse_effort_nodes(task_node),
                    notes=self.__parse_note_nodes(task_node),
                    recurrence=self.__parse_recurrence(task_node),
                )
            )
            self.__prerequisites[kwargs["id"]] = list(
                value(task_node, "prerequisites", str.split)
            )
            self.__parse_categories(task_node, kwargs["id"])
            if self.__tskversion > 20:
                kwargs["attachments"] = self.__parse_attachments(task_node)
            return self.__save_modification_datetime(
                task.Task(**kwargs)
            )  # pylint: disable=W0142
        finally:
            self.__current_path.pop()

    def __parse_categories(self, node, item_id):
        """A task's or note's categories, stored on it since tskversion
        38; linked once the categories are read."""
        if self.__tskversion >= 38:
            self.__categories_of[item_id] = list(
                self.__value(node, "categories", str.split)
            )

    def __parse_recurrence(self, task_node):
        """Parse the recurrence from the node and return a recurrence
        instance."""
        if self.__tskversion <= 19:
            parse_kwargs = self.__parse_recurrence_attributes_from_task_node
        else:
            parse_kwargs = self.__parse_recurrence_node
        return date.Recurrence(**parse_kwargs(task_node))

    def __parse_recurrence_node(self, task_node):
        """Since tskversion >= 20, recurrence information is stored in a
        separate node; without it, the task does not recur."""
        node = task_node.find("recurrence")
        if node is None:
            return {}
        value = self.__value
        return dict(
            unit=value(node, "unit"),
            amount=value(node, "amount", int),
            count=value(node, "count", int),
            maximum=value(node, "max", int),
            stop_datetime=value(node, "stop_datetime", date.parseDateTime),
            sameWeekday=value(node, "sameWeekday", self.__parse_boolean),
            recurBasedOnCompletion=value(
                node, "recurBasedOnCompletion", self.__parse_boolean
            ),
            weekdays=value(
                node,
                "weekdays",
                lambda text: [int(each) for each in text.split(",") if each],
            ),
        )

    def __parse_recurrence_attributes_from_task_node(self, task_node):
        """In tskversion <= 19 recurrence information was stored as attributes
        of task nodes."""
        value = self.__value
        return dict(
            unit=value(task_node, "unit", str, "recurrence"),
            count=value(task_node, "count", int, "recurrenceCount"),
            amount=value(task_node, "amount", int, "recurrenceFrequency"),
            maximum=value(task_node, "max", int, "maxRecurrenceCount"),
        )

    def __parse_note_node(self, note_node):
        """Parse the attributes and child notes from the note_node."""
        subject = note_node.attrib.get("subject", "")
        obj_id = self.__register_id(
            note_node.attrib.get("id", ""), "Note", subject
        )
        self.__current_path.append(f"Note: {subject}")
        try:
            kwargs = self.__parse_base_composite_attributes(
                note_node, self.__parse_note_nodes
            )
            kwargs["id"] = obj_id
            self.__parse_categories(note_node, obj_id)
            if self.__tskversion > 20:
                kwargs["attachments"] = self.__parse_attachments(note_node)
            return self.__save_modification_datetime(
                note.Note(**kwargs)
            )  # pylint: disable=W0142
        finally:
            self.__current_path.pop()

    def __parse_base_attributes(self, node):
        """Parse the attributes all composite domain objects share, such as
        id, subject, description, and return them as a
        keyword arguments dictionary that can be passed to the domain
        object constructor."""
        bg_color_attribute = "color" if self.__tskversion <= 27 else "bgColor"
        value = self.__value
        attributes = dict(
            id=node.attrib.get("id", ""),
            subject=value(node, "subject"),
            description=self.__parse_description(node),
            fgColor=value(node, "fgColor", self.__parse_tuple),
            bgColor=value(
                node, "bgColor", self.__parse_tuple, bg_color_attribute
            ),
            font=value(node, "font", self.__parse_font_description),
            icon=value(node, "icon", self.__parse_icon),
            ordering=value(node, "ordering", int),
            **self.__parse_dates(node),
        )

        if self.__tskversion <= 20:
            attributes["attachments"] = (
                self.__parse_attachments_before_version21(node)
            )

        return attributes

    def __parse_base_composite_attributes(
        self, node, parse_children, *parse_children_args
    ):
        """Same as __parse_base_attributes, but also parse children and
        expandedContexts."""
        kwargs = self.__parse_base_attributes(node)
        kwargs["children"] = parse_children(node, *parse_children_args)
        kwargs["expandedContexts"] = self.__value(
            node, "expandedContexts", self.__parse_tuple
        )
        return kwargs

    def __parse_attachments_before_version21(self, parent):
        """Parse the attachments from the node and return the attachment
        instances."""
        path, name = os.path.split(
            os.path.abspath(self.__fd.name)
        )  # pylint: disable=E1103
        name = os.path.splitext(name)[0]
        attdir = os.path.normpath(os.path.join(path, name + "_attachments"))

        attachments = []
        for node in parent.findall("attachment"):
            if self.__tskversion <= 16:
                args = (node.text,)
                kwargs = dict()
            else:
                args = (
                    os.path.join(attdir, node.find("data").text),
                    node.attrib["type"],
                )
                description = self.__parse_description(node)
                kwargs = dict(subject=description, description=description)
            # pylint: disable=W0142
            attachments.append(attachment.AttachmentFactory(*args, **kwargs))
        return attachments

    def __parse_effort_nodes(self, node):
        """Parse all effort records from the node."""
        return [
            self.__parse_effort_node(effort_node)
            for effort_node in self.__children_to_load(node, "effort")
        ]

    def __parse_effort_node(self, node):
        """Parse an effort record from the node."""
        kwargs = {}
        if self.__tskversion >= 29:
            start_str = node.attrib.get("start", "")
            kwargs["id"] = self.__register_id(
                node.attrib["id"], "Effort", f"started {start_str}"
            )
        start = node.attrib.get("start", "")
        description = self.__parse_description(node)
        # task=None because it is set when the effort is actually added to the
        # task by the task itself. This way no events are sent for changing the
        # effort owner, which is good.
        # pylint: disable=W0142
        return self.__save_modification_datetime(
            effort.Effort(
                task=None,
                start=date.parseDateTime(start),
                stop=self.__value(node, "stop", date.parseDateTime),
                description=description,
                entryMode=self.__value(node, "entryMode"),
                **self.__parse_dates(node),
                **kwargs,
            )
        )

    def __parse_attachments(self, node):
        """Parse the attachments from the node."""
        return [
            self.__parse_attachment(child_node)
            for child_node in self.__children_to_load(node, "attachment")
        ]

    def __parse_attachment(self, node):
        """Parse the attachment from the node."""
        subject = node.attrib.get("subject", "")
        obj_id = self.__register_id(
            node.attrib.get("id", ""), "Attachment", subject
        )
        kwargs = self.__parse_base_attributes(node)
        kwargs["id"] = obj_id
        kwargs["notes"] = self.__parse_note_nodes(node)

        if self.__tskversion <= 22:
            path, name = os.path.split(
                os.path.abspath(self.__fd.name)
            )  # pylint: disable=E1103
            name, ext = os.path.splitext(name)
            attdir = os.path.normpath(
                os.path.join(path, name + "_attachments")
            )
            location = os.path.join(attdir, node.attrib["location"])
        else:
            if "location" in node.attrib:
                location = node.attrib["location"]
            else:
                # Legacy inline attachments (base64 data embedded in XML)
                # are no longer supported. Keep the attachment object but
                # the file data is lost.
                data_node = node.find("data")
                ext = (
                    data_node.attrib.get("extension", "")
                    if data_node is not None
                    else ""
                )
                log_step(
                    f"WARNING: Inline attachment '{subject}' - "
                    f"embedded file data is not supported and will be "
                    f"lost on save. Use a legacy 1.x version to extract "
                    f"and save attachments before migrating",
                    prefix="FILE",
                )
                location = f"(embedded {ext} - data not migrated)"
        if node.attrib["type"] == "mail":
            kwargs.update(
                from_name=self.__value(node, "fromName"),
                from_address=self.__value(node, "fromAddress"),
                sent_datetime=self.__value(
                    node, "sentDateTime", date.parseDateTime
                ),
            )

        return self.__save_modification_datetime(
            attachment.AttachmentFactory(
                location,  # pylint: disable=W0142
                node.attrib["type"],
                **kwargs,
            )
        )

    def __parse_description(self, node):
        """Parse the description from the node."""
        if self.__tskversion <= 6:
            text = node.attrib.get("description")
        else:
            element = node.find("description")
            text = None if element is None else self.__parse_text(element)
        return read("description", text, str)

    def __parse_text(self, node):
        """Parse the text from a node."""
        text = "" if node is None else node.text or ""
        if self.__tskversion >= 24:
            # Strip newlines
            if text.startswith("\n"):
                text = text[1:]
            if text.endswith("\n"):
                text = text[:-1]
        return text

    @staticmethod
    def __value(node, name, parse=str, attribute=None):
        """A field's value: its default when the attribute (by default
        named as the field) is missing (defaults.DEFAULTS)."""
        return read(name, node.attrib.get(attribute or name), parse)

    def __parse_dates(self, node):
        """The creation and modification dates. Without a modification
        date the item was not modified since its creation; without
        either, both are unknown (DateTime.min)."""
        value = self.__value
        creation = value(node, "creationDateTime", self.__parse_timestamp)
        modification = value(
            node, "modificationDateTime", self.__parse_timestamp
        )
        return dict(
            creationDateTime=creation,
            modificationDateTime=modification or creation,
        )

    @staticmethod
    def __parse_timestamp(text):
        """Parse a timestamp, fractions of a second included."""
        try:
            return date.Timestamp.parse(text)
        except ValueError:
            return date.parseDateTime(text)

    def __parse_font_description(self, text, default_value=None):
        """Parse a font from the text. In case of failure, return the default
        value."""
        if text:
            font = wxhelper.font_from_native_info(text)
            if font and font.IsOk():
                if font.GetPointSize() < 4:
                    font.SetPointSize(self.__default_font_size)
                return font
        return default_value

    @staticmethod
    def __parse_icon(text):
        """Parse an icon name from the text, normalizing deprecated/duplicate."""
        from taskcoachlib.gui.icons.icon_library import icon_catalog

        return icon_catalog.normalize_icon_id(text)

    @staticmethod
    def __parse_boolean(text):
        """'True' or 'False'; a ValueError for any other text."""
        if text in ("True", "False"):
            return text == "True"
        raise ValueError("Expected 'True' or 'False', got '%s'" % text)

    @staticmethod
    def __parse_tuple(text):
        """A tuple literal; a ValueError for any other text."""
        if not (text.startswith("(") and text.endswith(")")):
            raise ValueError("Expected a tuple, got '%s'" % text)
        # A literal only: the text comes from the file, never run it
        try:
            return ast.literal_eval(text)
        except SyntaxError as error:
            raise ValueError(str(error))

    def __save_modification_datetime(self, item):
        """Save the modification date time of the item for later restore."""
        self.__modification_datetimes[item] = item.modificationDateTime()
        return item


class TemplateXMLReader(XMLReader):
    def read(self):
        return super().read()[0][0]

    def _parse_task_node(self, task_node):
        attrs = dict()
        attribute_renames = dict(startdate="plannedstartdate")
        for name in [
            "startdate",
            "plannedstartdate",
            "duedate",
            "completiondate",
            "reminder",
        ]:
            new_name = attribute_renames.get(name, name)
            template_name = name + "tmpl"
            if template_name in task_node.attrib:
                if self.tskversion() < 32:
                    value = TemplateXMLReader.convert_old_format(
                        task_node.attrib[template_name]
                    )
                else:
                    value = task_node.attrib[template_name]
                attrs[new_name] = value
                task_node.attrib[new_name] = str(
                    nlTimeExpression.parse_string(value).calculatedTime
                )
            elif new_name not in attrs:
                attrs[new_name] = None
        if "subject" in task_node.attrib:
            task_node.attrib["subject"] = translate(
                task_node.attrib["subject"]
            )
        parsed_task = super()._parse_task_node(task_node)
        for name, value in list(attrs.items()):
            setattr(parsed_task, name + "tmpl", value)
        return parsed_task

    @staticmethod
    def convert_old_format(expr, now=date.Now):
        # Built-in templates:
        built_in_templates = {
            "Now()": "now",
            "Now().endOfDay()": "11:59 PM today",
            "Now().endOfDay() + oneDay": "11:59 PM tomorrow",
            "Today()": "00:00 AM today",
            "Tomorrow()": "11:59 PM tomorrow",
        }
        if expr in built_in_templates:
            return built_in_templates[expr]
        # Not a built in template:
        new_datetime = safe_eval_date_expr(expr, OLD_TEMPLATE_NAMES)
        if isinstance(new_datetime, date.date.RealDate):
            new_datetime = date.DateTime(
                new_datetime.year, new_datetime.month, new_datetime.day
            )
        delta = new_datetime - now()
        minutes = delta.minutes()
        if minutes < 0:
            return "%d minutes ago" % (-minutes)
        else:
            return "%d minutes from now" % minutes
