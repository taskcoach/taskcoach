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

from xml.etree import ElementTree as ET
from taskcoachlib import meta
from taskcoachlib.domain import categorizable, category, date, note, task
import os
import sys


def flatten(elem):
    if len(elem) and not elem.text:
        elem.text = "\n"
    elif elem.text:
        elem.text = "\n%s\n" % elem.text
    elem.tail = "\n"
    for child in elem:
        flatten(child)


class PIElementTree(ET.ElementTree):
    def __init__(self, pi, *args, **kwargs):
        self.__pi = pi
        ET.ElementTree.__init__(self, *args, **kwargs)

    def _write(self, file, node, encoding, namespaces):
        if node == self._root:
            # WTF? ElementTree does not write the encoding if it's ASCII or UTF-8...
            if encoding in ["us-ascii", "utf-8", "unicode"]:
                # Check if file is in binary mode or text mode
                # Default to binary if mode cannot be determined (for wrapped file objects)
                is_binary = not (
                    hasattr(file, "mode") and "b" not in file.mode
                )
                if is_binary:
                    # Binary mode: write bytes
                    if encoding == "unicode":
                        file.write(
                            '<?xml version="1.0" encoding="utf-8"?>\n'.encode(
                                "utf-8"
                            )
                        )
                    else:
                        file.write(
                            (
                                '<?xml version="1.0" encoding="%s"?>\n'
                                % encoding
                            ).encode(encoding)
                        )
                else:
                    # Text mode: write strings
                    if encoding == "unicode":
                        file.write('<?xml version="1.0" encoding="utf-8"?>\n')
                    else:
                        file.write(
                            '<?xml version="1.0" encoding="%s"?>\n' % encoding
                        )
            # Write processing instruction
            is_binary = not (hasattr(file, "mode") and "b" not in file.mode)
            if is_binary:
                file.write(
                    (self.__pi + "\n").encode(
                        encoding if encoding != "unicode" else "utf-8"
                    )
                )
            else:
                file.write(self.__pi + "\n")
        ET.ElementTree._write(
            self, file, node, encoding, namespaces
        )  # pylint: disable=E1101

    def write(self, file, encoding, *args, **kwargs):
        if encoding is None:
            encoding = "utf-8"
        # Check if file is in binary mode or text mode
        # Default to binary if mode cannot be determined (for wrapped file objects)
        is_binary = not (hasattr(file, "mode") and "b" not in file.mode)

        # Write XML declaration and processing instruction
        if is_binary:
            # Binary mode: write bytes
            file.write(
                ('<?xml version="1.0" encoding="%s"?>\n' % encoding).encode(
                    encoding
                )
            )
            file.write((self.__pi + "\n").encode(encoding))
            kwargs["xml_declaration"] = False
            ET.ElementTree.write(self, file, encoding, *args, **kwargs)
        else:
            # Text mode: write strings
            file.write('<?xml version="1.0" encoding="%s"?>\n' % encoding)
            file.write(self.__pi + "\n")
            kwargs["xml_declaration"] = False
            # Use 'unicode' encoding to write strings instead of bytes
            ET.ElementTree.write(self, file, "unicode", *args, **kwargs)


def sortedById(objects):
    """Sort objects by their ID. Uses key function to avoid comparing objects
    directly, which would fail if two objects have the same ID and the object
    class doesn't implement __lt__."""
    return sorted(objects, key=lambda obj: obj.id())


class XMLWriter(object):
    maxDateTime = date.DateTime()

    def __init__(self, fd, versionnr=meta.data.tskversion):
        self.__fd = fd
        self.__versionnr = versionnr

    def write(self, task_list, category_container, note_container):
        root = ET.Element("tasks")

        for root_task in sortedById(task_list.rootItems()):
            self.task_node(root, root_task)

        in_file = categorizable.categorizables_in(
            task_list, note_container, category_container
        )
        for root_category in sortedById(category_container.rootItems()):
            self.category_node(root, root_category, in_file)

        for root_note in sortedById(note_container.rootItems()):
            self.note_node(root, root_note)

        flatten(root)
        PIElementTree(
            '<?taskcoach release="%s" tskversion="%d"?>\n'
            % (meta.data.version, self.__versionnr),
            root,
        ).write(self.__fd, "utf-8")

    def task_node(self, parent_node, task):  # pylint: disable=W0621
        maxDateTime = self.maxDateTime
        node = self.base_composite_node(
            parent_node, task, "task", self.task_node
        )
        if task.plannedStartDateTime() != maxDateTime:
            node.attrib["plannedstartdate"] = str(task.plannedStartDateTime())
        if task.dueDateTime() != maxDateTime:
            node.attrib["duedate"] = str(task.dueDateTime())
        if task.actualStartDateTime() != maxDateTime:
            node.attrib["actualstartdate"] = str(task.actualStartDateTime())
        if task.completionDateTime() != maxDateTime:
            node.attrib["completiondate"] = str(task.completionDateTime())
        if task.percentageComplete():
            node.attrib["percentageComplete"] = str(task.percentageComplete())
        if task.recurrence():
            self.recurrence_node(node, task.recurrence())
        if task.budget() != date.TimeDelta():
            node.attrib["budget"] = self.budgetAsAttribute(task.budget())
        if task.plannedDuration() != date.TimeDelta():
            node.attrib["plannedDuration"] = self.budgetAsAttribute(
                task.plannedDuration()
            )
        if task.plannedDurationMode() != "implicit":
            node.attrib["plannedDurationMode"] = task.plannedDurationMode()
        if task.priority():
            node.attrib["priority"] = str(task.priority())
        if task.hourlyFee():
            node.attrib["hourlyFee"] = str(task.hourlyFee())
        if task.fixedFee():
            node.attrib["fixedFee"] = str(task.fixedFee())
        reminder = task.reminder()
        if reminder != maxDateTime:
            node.attrib["reminder"] = str(reminder)
            before_snooze = task.reminder(include_snooze=False)
            if before_snooze < reminder:
                node.attrib["reminderBeforeSnooze"] = str(before_snooze)
        prerequisiteIds = " ".join(
            [
                prerequisite.id()
                for prerequisite in sortedById(task.prerequisites())
            ]
        )
        if prerequisiteIds:
            node.attrib["prerequisites"] = prerequisiteIds
        if task.shouldMarkCompletedWhenAllChildrenCompleted() != None:
            node.attrib["shouldMarkCompletedWhenAllChildrenCompleted"] = str(
                task.shouldMarkCompletedWhenAllChildrenCompleted()
            )
        for effort in sortedById(task.efforts()):
            self.effort_node(node, effort)
        for eachNote in sortedById(task.notes()):
            self.note_node(node, eachNote)
        for attachment in sortedById(task.attachments()):
            self.attachment_node(node, attachment)
        return node

    def recurrence_node(self, parent_node, recurrence):
        attrs = dict(unit=recurrence.unit)
        if recurrence.amount > 1:
            attrs["amount"] = str(recurrence.amount)
        if recurrence.count > 0:
            attrs["count"] = str(recurrence.count)
        if recurrence.max > 0:
            attrs["max"] = str(recurrence.max)
        if recurrence.stop_datetime != self.maxDateTime:
            attrs["stop_datetime"] = str(recurrence.stop_datetime)
        if recurrence.sameWeekday:
            attrs["sameWeekday"] = "True"
        if recurrence.recurBasedOnCompletion:
            attrs["recurBasedOnCompletion"] = "True"
        if recurrence.weekdays:
            attrs["weekdays"] = ",".join(str(d) for d in recurrence.weekdays)
        return ET.SubElement(parent_node, "recurrence", attrs)

    def effort_node(self, parent_node, effort):
        formattedStart = self.formatDateTime(effort.getStart())
        attrs = dict(
            id=effort.id(),
            start=formattedStart,
        )
        stop = effort.getStop()
        if stop != None:
            formattedStop = self.formatDateTime(stop)
            if formattedStop == formattedStart:
                # Make sure the effort duration is at least one second
                formattedStop = self.formatDateTime(stop + date.ONE_SECOND)
            attrs["stop"] = formattedStop
        entryMode = effort.entryMode()
        if entryMode and entryMode != "standard":
            attrs["entryMode"] = entryMode
        if effort.creationDateTime() > date.DateTime.min:
            attrs["creationDateTime"] = str(effort.creationDateTime())
        if effort.modificationDateTime() > date.DateTime.min:
            attrs["modificationDateTime"] = str(effort.modificationDateTime())
        node = ET.SubElement(parent_node, "effort", attrs)
        if effort.description():
            ET.SubElement(node, "description").text = effort.description()
        return node

    def category_node(
        self, parent_node, category, in_file
    ):  # pylint: disable=W0621
        node = self.base_composite_node(
            parent_node, category, "category", self.category_node, (in_file,)
        )
        if category.isFiltered():
            node.attrib["filtered"] = str(category.isFiltered())
        if category.hasExclusiveSubcategories():
            node.attrib["exclusiveSubcategories"] = str(
                category.hasExclusiveSubcategories()
            )
        if category.stylePriority():
            node.attrib["stylePriority"] = str(category.stylePriority())
        for eachNote in sortedById(category.notes()):
            self.note_node(node, eachNote)
        for attachment in sortedById(category.attachments()):
            self.attachment_node(node, attachment)
        # Its members in the file, not a copy or a deleted item
        member_ids = " ".join(
            member.id()
            for member in sortedById(category.categorizables() & in_file)
        )
        if member_ids:
            node.attrib["categorizables"] = member_ids
        return node

    def note_node(self, parent_node, note):  # pylint: disable=W0621
        node = self.base_composite_node(
            parent_node, note, "note", self.note_node
        )
        for attachment in sortedById(note.attachments()):
            self.attachment_node(node, attachment)
        return node

    def __base_node(self, parent_node, item, node_name):
        node = ET.SubElement(
            parent_node,
            node_name,
            dict(id=item.id()),
        )
        if item.creationDateTime() > date.DateTime.min:
            node.attrib["creationDateTime"] = str(item.creationDateTime())
        if item.modificationDateTime() > date.DateTime.min:
            node.attrib["modificationDateTime"] = str(
                item.modificationDateTime()
            )
        if item.subject():
            node.attrib["subject"] = item.subject()
        if item.description():
            ET.SubElement(node, "description").text = item.description()
        return node

    def base_node(self, parent_node, item, node_name):
        """Create a node and add the attributes that all domain
        objects share, such as id, subject, description."""
        node = self.__base_node(parent_node, item, node_name)
        if item.foregroundColor():
            node.attrib["fgColor"] = str(item.foregroundColor())
        if item.backgroundColor():
            node.attrib["bgColor"] = str(item.backgroundColor())
        if item.font():
            node.attrib["font"] = str(item.font().GetNativeFontInfoDesc())
        if item.icon_id():
            node.attrib["icon"] = str(item.icon_id())
        if item.ordering():
            node.attrib["ordering"] = str(item.ordering())
        return node

    def base_composite_node(
        self,
        parent_node,
        item,
        node_name,
        childNodeFactory,
        childNodeFactoryArgs=(),
    ):
        """Same as base_node, but also create child nodes by means of
        the childNodeFactory."""
        node = self.__base_node(parent_node, item, node_name)
        if item.foregroundColor():
            node.attrib["fgColor"] = str(item.foregroundColor())
        if item.backgroundColor():
            node.attrib["bgColor"] = str(item.backgroundColor())
        if item.font():
            node.attrib["font"] = str(item.font().GetNativeFontInfoDesc())
        if item.icon_id():
            node.attrib["icon"] = str(item.icon_id())
        if item.ordering():
            node.attrib["ordering"] = str(item.ordering())
        if item.expandedContexts():
            node.attrib["expandedContexts"] = str(
                tuple(sorted(item.expandedContexts()))
            )
        for child in sortedById(item.children()):
            childNodeFactory(
                node, child, *childNodeFactoryArgs
            )  # pylint: disable=W0142
        return node

    def attachment_node(self, parent_node, attachment):
        node = self.base_node(parent_node, attachment, "attachment")
        node.attrib["type"] = attachment.type_
        data = attachment.data()
        if data is None:
            node.attrib["location"] = attachment.location()
        else:
            ET.SubElement(
                node,
                "data",
                dict(extension=os.path.splitext(attachment.location())[-1]),
            ).text = data.encode("base64")
        for eachNote in sortedById(attachment.notes()):
            self.note_node(node, eachNote)
        return node

    def budgetAsAttribute(self, budget):
        return "%d:%02d:%02d" % budget.hoursMinutesSeconds()

    def formatDateTime(self, dateTime):
        return dateTime.strftime("%Y-%m-%d %H:%M:%S")


class TemplateXMLWriter(XMLWriter):
    def write(self, tsk):  # pylint: disable=W0221
        super().write(
            task.TaskList([tsk]),
            category.CategoryList(),
            note.NoteContainer(),
        )

    def task_node(self, parent_node, task):  # pylint: disable=W0621
        node = super().task_node(parent_node, task)

        for name, getter in [
            ("plannedstartdate", "plannedStartDateTime"),
            ("duedate", "dueDateTime"),
            ("completiondate", "completionDateTime"),
            ("reminder", "reminder"),
        ]:
            if hasattr(task, name + "tmpl"):
                value = getattr(task, name + "tmpl") or None
            else:
                date_time = getattr(task, getter)()
                if date_time not in (None, date.DateTime()):
                    delta = date_time - date.Now()
                    minutes = delta.days * 24 * 60 + round(
                        delta.seconds / 60.0
                    )
                    if minutes < 0:
                        value = "%d minutes ago" % -minutes
                    else:
                        value = "%d minutes from now" % minutes
                else:
                    value = None

            if value is None:
                if name in node.attrib:
                    del node.attrib[name]
            else:
                node.attrib[name + "tmpl"] = value

        return node
