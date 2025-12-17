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

from .. import sessiontempfile  # pylint: disable=F0401
from taskcoachlib import meta, patterns
from taskcoachlib.changes import ChangeMonitor
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
from taskcoachlib.syncml.config import (
    SyncMLConfigNode,
    createDefaultSyncConfig,
)
from taskcoachlib.thirdparty.deltaTime import nlTimeExpression
import uuid
import ast
import io
import operator
import os
import re
import stat
import wx
from lxml import etree as ET


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
            microsecond=999999,
        )
    return dateTime


class PIParser(ET.XMLParser):
    """See http://effbot.org/zone/element-pi.htm"""

    def __init__(self):
        super().__init__()

        # FIXME: The codes below no longer works with lastest python
        #
        # Codes refs: https://uucode.com/blog/2012/06/19/xmletreeelementtree-and-processing-instructions/
        # self._parser.ProcessingInstructionHandler = self.handle_pi
        #
        # Use lxml's ElementTree instead, it's provided better Processing Instruction handling


class XMLReaderTooNewException(Exception):
    pass


class XMLReader(object):
    """Class for reading task files in the default XML task file format."""

    defaultStartTime = (0, 0, 0, 0)
    defaultEndTime = (23, 59, 59, 999999)

    def __init__(self, fd):
        self.__fd = fd
        self.__default_font_size = wx.SystemSettings.GetFont(
            wx.SYS_DEFAULT_GUI_FONT
        ).GetPointSize()
        self.__modification_datetimes = {}
        self.__prerequisites = {}
        self.__categorizables = {}
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
        """Register an object's ID for duplicate detection."""
        if not obj_id:
            return
        path = " -> ".join(self.__current_path + [f"{obj_type}: {subject}"])
        if obj_id not in self.__id_registry:
            self.__id_registry[obj_id] = []
        self.__id_registry[obj_id].append((obj_type, path))

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
        """Read the task file and return the tasks, categories, notes, SyncML
        configuration and GUID."""
        if self.__has_broken_lines():
            self.__fix_broken_lines()
        parser = PIParser()
        tree = ET.parse(self.__fd, parser)
        root = tree.getroot()
        pis = tree.getroot().xpath("//processing-instruction()")
        for pi in pis:
            if pi.target == "taskcoach":
                tskversion = int(pi.attrib.get("tskversion"))
                break
        self.__tskversion = tskversion  # pylint: disable=W0201
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

        guid = self.__parse_guid_node(root.find("guid"))
        syncml_config = self.__parse_syncml_node(root, guid)

        for (
            object,
            modification_datetime,
        ) in self.__modification_datetimes.items():
            object.setModificationDateTime(modification_datetime)

        changesName = self.__fd.name + ".delta"
        if os.path.exists(changesName):
            changes = ChangesXMLReader(
                open(self.__fd.name + ".delta", "r")
            ).read()
        else:
            changes = dict()

        return tasks, categories, notes, syncml_config, changes, guid

    def __has_broken_lines(self):
        """tskversion 24 may contain newlines in element tags."""
        has_broken_lines = "><spds><sources><TaskCoach-\n" in self.__fd.read()
        self.__fd.seek(0)
        return has_broken_lines

    def __fix_broken_lines(self):
        """Remove spurious newlines from element tags."""
        self.__origFd = self.__fd  # pylint: disable=W0201
        self.__fd = io.StringIO()
        self.__fd.name = self.__origFd.name
        lines = self.__origFd.readlines()
        for index in range(len(lines)):
            if lines[index].endswith("<TaskCoach-\n") or lines[index].endswith(
                "</TaskCoach-\n"
            ):
                lines[index] = lines[index][:-1]  # Remove newline
                lines[index + 1] = lines[index + 1][:-1]  # Remove newline
        self.__fd.write("".join(lines))
        self.__fd.seek(0)

    def __parse_task_nodes(self, node):
        """Recursively parse all tasks from the node and return a list of
        task instances."""
        return [self._parse_task_node(child) for child in node.findall("task")]

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
                if each_task.isDeleted():
                    # Don't restore prerequisites and dependencies for deleted
                    # tasks
                    for deleted_task in [each_task] + each_task.children(
                        recursive=True
                    ):
                        deleted_task.setPrerequisites([])
                    continue
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
                each_task.setPrerequisites(prerequisites)
                for prerequisite in prerequisites:
                    prerequisite.addDependencies([each_task])
                resolve_ids(each_task.children())

        collect_ids(tasks)
        resolve_ids(tasks)

    def __resolve_categories(self, categories, tasks, notes):
        def mapCategorizables(obj, resultMap, categoryMap):
            if isinstance(obj, categorizable.CategorizableCompositeObject):
                resultMap[obj.id()] = obj
            if isinstance(obj, category.Category):
                categoryMap[obj.id()] = obj
            if isinstance(obj, base.CompositeObject):
                for child in obj.children():
                    mapCategorizables(child, resultMap, categoryMap)
            if isinstance(obj, note.NoteOwner):
                for theNote in obj.notes():
                    mapCategorizables(theNote, resultMap, categoryMap)
            if isinstance(obj, attachment.AttachmentOwner):
                for theAttachment in obj.attachments():
                    mapCategorizables(theAttachment, resultMap, categoryMap)

        categorizableMap = dict()
        categoryMap = dict()
        for theCategory in categories:
            mapCategorizables(theCategory, categorizableMap, categoryMap)
        for theTask in tasks:
            mapCategorizables(theTask, categorizableMap, categoryMap)
        for theNote in notes:
            mapCategorizables(theNote, categorizableMap, categoryMap)

        event = patterns.Event()
        for categoryId, categorizableIds in list(
            self.__categorizables.items()
        ):
            theCategory = categoryMap[categoryId]
            for categorizableId in categorizableIds:
                if categorizableId in categorizableMap:
                    theCategorizable = categorizableMap[categorizableId]
                    theCategory.addCategorizable(theCategorizable)
                    theCategorizable.addCategory(theCategory, event=event)
        event.send()

    def __parse_category_nodes(self, node):
        return [
            self.__parse_category_node(child)
            for child in node.findall("category")
        ]

    def __parse_note_nodes(self, node):
        return [
            self.__parse_note_node(child) for child in node.findall("note")
        ]

    def __parse_category_node(self, category_node):
        """Recursively parse the categories from the node and return a
        category instance."""
        subject = category_node.attrib.get("subject", "")
        obj_id = category_node.attrib.get("id", "")
        self.__register_id(obj_id, "Category", subject)
        self.__current_path.append(f"Category: {subject}")
        try:
            kwargs = self.__parse_base_composite_attributes(
                category_node, self.__parse_category_nodes
            )
            notes = self.__parse_note_nodes(category_node)
            filtered = self.__parse_boolean(
                category_node.attrib.get("filtered", "False")
            )
            exclusive = self.__parse_boolean(
                category_node.attrib.get("exclusiveSubcategories", "False")
            )
            kwargs.update(
                dict(
                    notes=notes,
                    filtered=filtered,
                    exclusiveSubcategories=exclusive,
                )
            )
            if self.__tskversion < 19:
                categorizable_ids = category_node.attrib.get("tasks", "")
            else:
                categorizable_ids = category_node.attrib.get("categorizables", "")
            if self.__tskversion > 20:
                kwargs["attachments"] = self.__parse_attachments(category_node)
            theCategory = category.Category(**kwargs)  # pylint: disable=W0142
            self.__categorizables.setdefault(theCategory.id(), list()).extend(
                categorizable_ids.split(" ")
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
                self.__categorizables.setdefault(cat.id(), list()).append(
                    task_id
                )
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
        obj_id = task_node.attrib.get("id", "")
        self.__register_id(obj_id, "Task", subject)
        self.__current_path.append(f"Task: {subject}")
        try:
            planned_start_datetime_attribute_name = (
                "startdate" if self.tskversion() <= 33 else "plannedstartdate"
            )
            kwargs = self.__parse_base_composite_attributes(
                task_node, self.__parse_task_nodes
            )
            kwargs.update(
                dict(
                    plannedStartDateTime=date.parseDateTime(
                        task_node.attrib.get(
                            planned_start_datetime_attribute_name, ""
                        ),
                        *self.defaultStartTime
                    ),
                    dueDateTime=parseAndAdjustDateTime(
                        task_node.attrib.get("duedate", ""), *self.defaultEndTime
                    ),
                    actualStartDateTime=date.parseDateTime(
                        task_node.attrib.get("actualstartdate", ""),
                        *self.defaultStartTime
                    ),
                    completionDateTime=date.parseDateTime(
                        task_node.attrib.get("completiondate", ""),
                        *self.defaultEndTime
                    ),
                    percentageComplete=self.__parse_int_attribute(
                        task_node, "percentageComplete"
                    ),
                    budget=date.parseTimeDelta(task_node.attrib.get("budget", "")),
                    priority=self.__parse_int_attribute(task_node, "priority"),
                    hourlyFee=float(task_node.attrib.get("hourlyFee", "0")),
                    fixedFee=float(task_node.attrib.get("fixedFee", "0")),
                    reminder=self.__parse_datetime(
                        task_node.attrib.get("reminder", "")
                    ),
                    reminderBeforeSnooze=self.__parse_datetime(
                        task_node.attrib.get("reminderBeforeSnooze", "")
                    ),
                    # Ignore prerequisites for now, they'll be resolved later
                    prerequisites=[],
                    shouldMarkCompletedWhenAllChildrenCompleted=self.__parse_boolean(
                        task_node.attrib.get(
                            "shouldMarkCompletedWhenAllChildrenCompleted", ""
                        )
                    ),
                    efforts=self.__parse_effort_nodes(task_node),
                    notes=self.__parse_note_nodes(task_node),
                    recurrence=self.__parse_recurrence(task_node),
                )
            )
            self.__prerequisites[kwargs["id"]] = [
                id_
                for id_ in task_node.attrib.get("prerequisites", "").split(" ")
                if id_
            ]
            if self.__tskversion > 20:
                kwargs["attachments"] = self.__parse_attachments(task_node)
            return self.__save_modification_datetime(
                task.Task(**kwargs)
            )  # pylint: disable=W0142
        finally:
            self.__current_path.pop()

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
        separate node."""
        kwargs = dict(
            unit="",
            amount=1,
            count=0,
            maximum=0,
            stop_datetime=None,
            sameWeekday=False,
        )
        node = task_node.find("recurrence")
        if node is not None:
            kwargs = dict(
                unit=node.attrib.get("unit", ""),
                amount=int(node.attrib.get("amount", "1")),
                count=int(node.attrib.get("count", "0")),
                maximum=int(node.attrib.get("max", "0")),
                stop_datetime=self.__parse_datetime(
                    node.attrib.get("stop_datetime", "")
                ),
                sameWeekday=self.__parse_boolean(
                    node.attrib.get("sameWeekday", "False")
                ),
                recurBasedOnCompletion=self.__parse_boolean(
                    node.attrib.get("recurBasedOnCompletion", "False")
                ),
            )
        return kwargs

    @staticmethod
    def __parse_recurrence_attributes_from_task_node(task_node):
        """In tskversion <= 19 recurrence information was stored as attributes
        of task nodes."""
        return dict(
            unit=task_node.attrib.get("recurrence", ""),
            count=int(task_node.attrib.get("recurrenceCount", "0")),
            amount=int(task_node.attrib.get("recurrenceFrequency", "1")),
            maximum=int(task_node.attrib.get("maxRecurrenceCount", "0")),
        )

    def __parse_note_node(self, note_node):
        """Parse the attributes and child notes from the noteNode."""
        subject = note_node.attrib.get("subject", "")
        obj_id = note_node.attrib.get("id", "")
        self.__register_id(obj_id, "Note", subject)
        self.__current_path.append(f"Note: {subject}")
        try:
            kwargs = self.__parse_base_composite_attributes(
                note_node, self.__parse_note_nodes
            )
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
        attributes = dict(
            id=node.attrib.get("id", ""),
            creationDateTime=self.__parse_datetime(
                node.attrib.get("creationDateTime", "1-1-1 0:0")
            ),
            modificationDateTime=self.__parse_datetime(
                node.attrib.get("modificationDateTime", "1-1-1 0:0")
            ),
            subject=node.attrib.get("subject", ""),
            description=self.__parse_description(node),
            fgColor=self.__parse_tuple(node.attrib.get("fgColor", ""), None),
            bgColor=self.__parse_tuple(
                node.attrib.get(bg_color_attribute, ""), None
            ),
            font=self.__parse_font_description(node.attrib.get("font", "")),
            icon=self.__parse_icon(node.attrib.get("icon", "")),
            selectedIcon=self.__parse_icon(
                node.attrib.get("selectedIcon", "")
            ),
            ordering=int(node.attrib.get("ordering", "0")),
        )

        if self.__tskversion <= 20:
            attributes["attachments"] = (
                self.__parse_attachments_before_version21(node)
            )
        if self.__tskversion >= 22:
            attributes["status"] = int(node.attrib.get("status", "1"))

        return attributes

    def __parse_base_composite_attributes(
        self, node, parse_children, *parse_children_args
    ):
        """Same as __parse_base_attributes, but also parse children and
        expandedContexts."""
        kwargs = self.__parse_base_attributes(node)
        kwargs["children"] = parse_children(node, *parse_children_args)
        expanded_contexts = node.attrib.get("expandedContexts", "")
        kwargs["expandedContexts"] = self.__parse_tuple(expanded_contexts, [])
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
            try:
                # pylint: disable=W0142
                attachments.append(
                    attachment.AttachmentFactory(*args, **kwargs)
                )
            except IOError:
                # Mail attachment, file doesn't exist. Ignore this.
                pass
        return attachments

    def __parse_effort_nodes(self, node):
        """Parse all effort records from the node."""
        return [
            self.__parse_effort_node(effort_node)
            for effort_node in node.findall("effort")
        ]

    def __parse_effort_node(self, node):
        """Parse an effort record from the node."""
        kwargs = {}
        if self.__tskversion >= 22:
            kwargs["status"] = int(node.attrib.get("status", "1"))
        if self.__tskversion >= 29:
            kwargs["id"] = node.attrib["id"]
            # Register effort ID for duplicate detection
            start_str = node.attrib.get("start", "")
            self.__register_id(kwargs["id"], "Effort", f"started {start_str}")
        start = node.attrib.get("start", "")
        stop = node.attrib.get("stop", "")
        description = self.__parse_description(node)
        # task=None because it is set when the effort is actually added to the
        # task by the task itself. This way no events are sent for changing the
        # effort owner, which is good.
        # pylint: disable=W0142
        return effort.Effort(
            task=None,
            start=date.parseDateTime(start),
            stop=date.parseDateTime(stop),
            description=description,
            **kwargs
        )

    def __parse_syncml_node(self, nodes, guid):
        """Parse the SyncML node from the nodes."""
        syncml_config = createDefaultSyncConfig(guid)

        node_name = "syncmlconfig"
        if self.__tskversion < 25:
            node_name = "syncml"

        for node in nodes.findall(node_name):
            self.__parse_syncml_nodes(node, syncml_config)
        return syncml_config

    def __parse_syncml_nodes(self, node, config_node):
        """Parse the SyncML nodes from the node."""
        for child_node in node:
            if child_node.tag == "property":
                config_node.set(
                    child_node.attrib["name"], self.__parse_text(child_node)
                )
            else:
                for child_config_node in config_node.children():
                    if child_config_node.name == child_node.tag:
                        break
                else:
                    tag = child_node.tag
                    child_config_node = SyncMLConfigNode(tag)
                    config_node.addChild(child_config_node)
                self.__parse_syncml_nodes(child_node, child_config_node)

    def __parse_guid_node(self, node):
        """Parse the GUID from the node."""
        guid = self.__parse_text(node).strip()
        return guid if guid else str(uuid.uuid4())

    def __parse_attachments(self, node):
        """Parse the attachments from the node."""
        attachments = []
        for child_node in node.findall("attachment"):
            try:
                attachments.append(self.__parse_attachment(child_node))
            except IOError:
                pass
        return attachments

    def __parse_attachment(self, node):
        """Parse the attachment from the node."""
        subject = node.attrib.get("subject", "")
        obj_id = node.attrib.get("id", "")
        self.__register_id(obj_id, "Attachment", subject)
        kwargs = self.__parse_base_attributes(node)
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
                data_node = node.find("data")

                if data_node is None:
                    raise ValueError(
                        "Neither location or data are defined "
                        "for this attachment."
                    )

                data = self.__parse_text(data_node)
                ext = data_node.attrib["extension"]

                location = sessiontempfile.get_temp_file(suffix=ext)
                open(location, "wb").write(data.decode("base64"))

                if os.name == "nt":
                    os.chmod(location, stat.S_IREAD)

        return self.__save_modification_datetime(
            attachment.AttachmentFactory(
                location,  # pylint: disable=W0142
                node.attrib["type"],
                **kwargs
            )
        )

    def __parse_description(self, node):
        """Parse the description from the node."""
        if self.__tskversion <= 6:
            description = node.attrib.get("description", "")
        else:
            description = self.__parse_text(node.find("description"))
        return description

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

    @classmethod
    def __parse_int_attribute(cls, node, attribute_name, default_value=0):
        """Parse the integer attribute with the specified name from the
        node. In case of failure, return the default value."""
        text = node.attrib.get(attribute_name, "0")
        return cls.__parse(text, int, default_value)

    @classmethod
    def __parse_datetime(cls, text):
        """Parse a datetime from the text."""
        return cls.__parse(text, date.parseDateTime, None)

    def __parse_font_description(self, text, default_value=None):
        """Parse a font from the text. In case of failure, return the default
        value."""
        if text:
            font = wx.FontFromNativeInfoString(text)
            if font and font.IsOk():
                if font.GetPointSize() < 4:
                    font.SetPointSize(self.__default_font_size)
                return font
        return default_value

    @staticmethod
    def __parse_icon(text):
        """Parse an icon name from the text."""
        # Parse is a big word, we just need to fix one particular icon
        return "clock_alarm_icon" if text == "clock_alarm" else text

    @classmethod
    def __parse_boolean(cls, text, default_value=None):
        """Parse a boolean from the text. In case of failure, return the
        default value."""

        def text_to_boolean(text):
            """Transform 'True' to True and 'False' to False, raise a
            ValueError for any other text."""
            if text in ("True", "False"):
                return text == "True"
            else:
                raise ValueError("Expected 'True' or 'False', got '%s'" % text)

        return cls.__parse(text, text_to_boolean, default_value)

    @classmethod
    def __parse_tuple(cls, text, default_value=None):
        """Parse a tuple from the text. In case of failure, return the default
        value."""
        if text.startswith("(") and text.endswith(")"):
            return cls.__parse(text, eval, default_value)
        else:
            return default_value

    @staticmethod
    def __parse(text, parse_function, default_value):
        """Parse the text using the parse function. In case of failure, return
        the default value."""
        try:
            return parse_function(text)
        except ValueError:
            return default_value

    def __save_modification_datetime(self, item):
        """Save the modification date time of the item for later restore."""
        self.__modification_datetimes[item] = item.modificationDateTime()
        return item


class ChangesXMLReader(object):
    def __init__(self, fd):
        self.__fd = fd

    def read(self):
        allChanges = dict()
        tree = ET.parse(self.__fd)
        for devNode in tree.getroot().findall("device"):
            id_ = devNode.attrib["guid"]
            mon = ChangeMonitor(id_)
            for objNode in devNode.findall("obj"):
                if objNode.text:
                    changes = set(objNode.text.split(","))
                else:
                    changes = set()
                mon.setChanges(objNode.attrib["id"], changes)
            allChanges[id_] = mon
        return allChanges


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
                    nlTimeExpression.parseString(value).calculatedTime
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
        new_datetime = safe_eval_date_expr(expr, date.__dict__)
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
