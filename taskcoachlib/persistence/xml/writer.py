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
from taskcoachlib.domain import category, date, note, task
from .defaults import NOT_SET, UNKNOWN, is_default


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
    def __init__(self, fd, versionnr=meta.data.tskversion):
        self.__fd = fd
        self.__versionnr = versionnr
        self.__categories = set()

    def write(self, task_list, category_container, note_container):
        root = ET.Element("tasks")
        # The categories an item may link to (a template has none)
        self.__categories = set(category_container)

        for root_task in sortedById(task_list.rootItems()):
            self.task_node(root, root_task)

        for root_category in sortedById(category_container.rootItems()):
            self.category_node(root, root_category)

        for root_note in sortedById(note_container.rootItems()):
            self.note_node(root, root_note)

        flatten(root)
        PIElementTree(
            '<?taskcoach release="%s" tskversion="%d"?>\n'
            % (meta.data.version, self.__versionnr),
            root,
        ).write(self.__fd, "utf-8")

    def task_node(self, parent_node, task):  # pylint: disable=W0621
        node = self.base_composite_node(
            parent_node, task, "task", self.task_node
        )
        attribute = self.__attribute
        attribute(node, "plannedstartdate", task.plannedStartDateTime())
        attribute(node, "duedate", task.dueDateTime())
        attribute(node, "actualstartdate", task.actualStartDateTime())
        attribute(node, "completiondate", task.completionDateTime())
        attribute(node, "percentageComplete", task.percentageComplete())
        if task.recurrence():
            self.recurrence_node(node, task.recurrence())
        attribute(node, "budget", task.budget(), self.budgetAsAttribute)
        attribute(
            node,
            "plannedDuration",
            task.plannedDuration(),
            self.budgetAsAttribute,
        )
        attribute(node, "plannedDurationMode", task.plannedDurationMode())
        attribute(node, "priority", task.priority())
        attribute(node, "hourlyFee", task.hourlyFee())
        attribute(node, "fixedFee", task.fixedFee())
        reminder = task.reminder()
        attribute(node, "reminder", reminder)
        before_snooze = task.reminder(include_snooze=False)
        snoozed = reminder != NOT_SET and before_snooze < reminder
        attribute(
            node, "reminderBeforeSnooze", before_snooze if snoozed else None
        )
        attribute(node, "prerequisites", task.prerequisites(), self.__ids)
        self.__categories_attribute(node, task)
        attribute(
            node,
            "shouldMarkCompletedWhenAllChildrenCompleted",
            task.shouldMarkCompletedWhenAllChildrenCompleted(),
        )
        for effort in sortedById(task.efforts()):
            self.effort_node(node, effort)
        for eachNote in sortedById(task.notes()):
            self.note_node(node, eachNote)
        for attachment in sortedById(task.attachments()):
            self.attachment_node(node, attachment)
        return node

    def recurrence_node(self, parent_node, recurrence):
        node = ET.SubElement(parent_node, "recurrence")
        attribute = self.__attribute
        attribute(node, "unit", recurrence.unit)
        attribute(node, "amount", recurrence.amount)
        attribute(node, "count", recurrence.count)
        attribute(node, "max", recurrence.max)
        attribute(node, "stop_datetime", recurrence.stop_datetime)
        attribute(node, "sameWeekday", recurrence.sameWeekday)
        attribute(
            node, "recurBasedOnCompletion", recurrence.recurBasedOnCompletion
        )
        attribute(
            node,
            "weekdays",
            recurrence.weekdays,
            lambda weekdays: ",".join(str(each) for each in weekdays),
        )
        return node

    def effort_node(self, parent_node, effort):
        start = self.formatDateTime(effort.getStart())
        node = ET.SubElement(
            parent_node, "effort", dict(id=effort.id(), start=start)
        )

        def stop_text(stop):
            text = self.formatDateTime(stop)
            # At least one second long
            if text == start:
                text = self.formatDateTime(stop + date.ONE_SECOND)
            return text

        self.__attribute(node, "stop", effort.getStop(), stop_text)
        self.__attribute(node, "entryMode", effort.entryMode())
        self.__dates(node, effort)
        self.__description(node, effort)
        return node

    def category_node(self, parent_node, category):  # pylint: disable=W0621
        node = self.base_composite_node(
            parent_node, category, "category", self.category_node
        )
        self.__attribute(node, "filtered", category.isFiltered())
        self.__attribute(
            node,
            "exclusiveSubcategories",
            category.hasExclusiveSubcategories(),
        )
        self.__attribute(node, "stylePriority", category.stylePriority())
        for eachNote in sortedById(category.notes()):
            self.note_node(node, eachNote)
        for attachment in sortedById(category.attachments()):
            self.attachment_node(node, attachment)
        return node

    def note_node(self, parent_node, note):  # pylint: disable=W0621
        node = self.base_composite_node(
            parent_node, note, "note", self.note_node
        )
        self.__categories_attribute(node, note)
        for attachment in sortedById(note.attachments()):
            self.attachment_node(node, attachment)
        return node

    def __categories_attribute(self, node, item):
        """The item's categories, stored on the item (tskversion 38,
        docs/PERSISTENCE_XML.md, Category Membership)."""
        self.__attribute(
            node,
            "categories",
            item.categories() & self.__categories,
            self.__ids,
        )

    @staticmethod
    def __ids(items):
        return " ".join(each.id() for each in sortedById(items))

    @staticmethod
    def __attribute(node, name, value, text=str):
        """The field's attribute, left out when the item holds its
        default (defaults.DEFAULTS)."""
        if not is_default(name, value):
            node.attrib[name] = text(value)

    def __dates(self, node, item):
        self.__attribute(node, "creationDateTime", item.creationDateTime())
        # Written when known; a missing one is the creation date
        modification = item.modificationDateTime()
        self.__attribute(
            node,
            "modificationDateTime",
            None if modification == UNKNOWN else modification,
        )

    @staticmethod
    def __description(node, item):
        if not is_default("description", item.description()):
            ET.SubElement(node, "description").text = item.description()

    def __base_node(self, parent_node, item, node_name):
        node = ET.SubElement(
            parent_node,
            node_name,
            dict(id=item.id()),
        )
        self.__dates(node, item)
        self.__attribute(node, "subject", item.subject())
        self.__description(node, item)
        return node

    def __appearance(self, node, item):
        # An invalid colour or font is none
        self.__attribute(node, "fgColor", item.foregroundColor() or None)
        self.__attribute(node, "bgColor", item.backgroundColor() or None)
        self.__attribute(
            node,
            "font",
            item.font() or None,
            lambda font: font.GetNativeFontInfoDesc(),
        )
        self.__attribute(node, "icon", item.icon_id())
        self.__attribute(node, "ordering", item.ordering())

    def base_node(self, parent_node, item, node_name):
        """Create a node and add the attributes that all domain
        objects share, such as id, subject, description."""
        node = self.__base_node(parent_node, item, node_name)
        self.__appearance(node, item)
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
        node = self.base_node(parent_node, item, node_name)
        self.__attribute(
            node,
            "expandedContexts",
            item.expandedContexts(),
            lambda contexts: str(tuple(sorted(contexts))),
        )
        for child in sortedById(item.children()):
            childNodeFactory(
                node, child, *childNodeFactoryArgs
            )  # pylint: disable=W0142
        return node

    def attachment_node(self, parent_node, attachment):
        node = self.base_node(parent_node, attachment, "attachment")
        node.attrib["type"] = attachment.type_
        node.attrib["location"] = attachment.location()
        if attachment.type_ == "mail":
            self.__attribute(node, "fromName", attachment.from_name())
            self.__attribute(node, "fromAddress", attachment.from_address())
            self.__attribute(node, "sentDateTime", attachment.sent_datetime())
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
