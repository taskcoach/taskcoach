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
from taskcoachlib.domain import date, task, note, category
from xml.etree import ElementTree as ET
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
                is_binary = not (hasattr(file, 'mode') and 'b' not in file.mode)
                if is_binary:
                    # Binary mode: write bytes
                    if encoding == "unicode":
                        file.write('<?xml version="1.0" encoding="utf-8"?>\n'.encode('utf-8'))
                    else:
                        file.write(('<?xml version="1.0" encoding="%s"?>\n' % encoding).encode(encoding))
                else:
                    # Text mode: write strings
                    if encoding == "unicode":
                        file.write('<?xml version="1.0" encoding="utf-8"?>\n')
                    else:
                        file.write('<?xml version="1.0" encoding="%s"?>\n' % encoding)
            # Write processing instruction
            is_binary = not (hasattr(file, 'mode') and 'b' not in file.mode)
            if is_binary:
                file.write((self.__pi + "\n").encode(encoding if encoding != "unicode" else "utf-8"))
            else:
                file.write(self.__pi + "\n")
        ET.ElementTree._write(
            self, file, node, encoding, namespaces
        )  # pylint: disable=E1101

    def write(self, file, encoding, *args, **kwargs):
        if encoding is None:
            encoding = "utf-8"
        if sys.version_info >= (2, 7):
            # Check if file is in binary mode or text mode
            # Default to binary if mode cannot be determined (for wrapped file objects)
            is_binary = not (hasattr(file, 'mode') and 'b' not in file.mode)

            # Write XML declaration and processing instruction
            if is_binary:
                # Binary mode: write bytes
                file.write(('<?xml version="1.0" encoding="%s"?>\n' % encoding).encode(encoding))
                file.write((self.__pi + "\n").encode(encoding))
                kwargs["xml_declaration"] = False
                ET.ElementTree.write(self, file, encoding, *args, **kwargs)
            else:
                # Text mode: write strings
                file.write('<?xml version="1.0" encoding="%s"?>\n' % encoding)
                file.write(self.__pi + "\n")
                kwargs["xml_declaration"] = False
                # Use 'unicode' encoding to write strings instead of bytes
                ET.ElementTree.write(self, file, 'unicode', *args, **kwargs)
        else:
            ET.ElementTree.write(self, file, encoding, *args, **kwargs)


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

    def write(
        self, taskList, categoryContainer, noteContainer, syncMLConfig, guid
    ):
        root = ET.Element("tasks")

        for rootTask in sortedById(taskList.rootItems()):
            self.taskNode(root, rootTask)

        ownedNotes = self.notesOwnedByNoteOwners(taskList, categoryContainer)
        for rootCategory in sortedById(categoryContainer.rootItems()):
            self.categoryNode(
                root, rootCategory, taskList, noteContainer, ownedNotes
            )

        for rootNote in sortedById(noteContainer.rootItems()):
            self.noteNode(root, rootNote)

        if syncMLConfig:
            self.syncMLNode(root, syncMLConfig)
        if guid:
            ET.SubElement(root, "guid").text = guid

        flatten(root)
        PIElementTree(
            '<?taskcoach release="%s" tskversion="%d"?>\n'
            % (meta.data.version, self.__versionnr),
            root,
        ).write(self.__fd, "utf-8")

    def notesOwnedByNoteOwners(self, *collectionOfNoteOwners):
        notes = []
        for noteOwners in collectionOfNoteOwners:
            for noteOwner in noteOwners:
                notes.extend(noteOwner.notes(recursive=True))
        return notes

    def taskNode(self, parentNode, task):  # pylint: disable=W0621
        maxDateTime = self.maxDateTime
        node = self.baseCompositeNode(parentNode, task, "task", self.taskNode)
        node.attrib["status"] = str(task.getStatus())
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
            self.recurrenceNode(node, task.recurrence())
        if task.budget() != date.TimeDelta():
            node.attrib["budget"] = self.budgetAsAttribute(task.budget())
        if task.priority():
            node.attrib["priority"] = str(task.priority())
        if task.hourlyFee():
            node.attrib["hourlyFee"] = str(task.hourlyFee())
        if task.fixedFee():
            node.attrib["fixedFee"] = str(task.fixedFee())
        reminder = task.reminder()
        if reminder != maxDateTime and reminder != None:
            node.attrib["reminder"] = str(reminder)
            reminderBeforeSnooze = task.reminder(includeSnooze=False)
            if (
                reminderBeforeSnooze != None
                and reminderBeforeSnooze < task.reminder()
            ):
                node.attrib["reminderBeforeSnooze"] = str(reminderBeforeSnooze)
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
            self.effortNode(node, effort)
        for eachNote in sortedById(task.notes()):
            self.noteNode(node, eachNote)
        for attachment in sortedById(task.attachments()):
            self.attachmentNode(node, attachment)
        return node

    def recurrenceNode(self, parentNode, recurrence):
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
        return ET.SubElement(parentNode, "recurrence", attrs)

    def effortNode(self, parentNode, effort):
        formattedStart = self.formatDateTime(effort.getStart())
        attrs = dict(
            id=effort.id(),
            status=str(effort.getStatus()),
            start=formattedStart,
        )
        stop = effort.getStop()
        if stop != None:
            formattedStop = self.formatDateTime(stop)
            if formattedStop == formattedStart:
                # Make sure the effort duration is at least one second
                formattedStop = self.formatDateTime(stop + date.ONE_SECOND)
            attrs["stop"] = formattedStop
        node = ET.SubElement(parentNode, "effort", attrs)
        if effort.description():
            ET.SubElement(node, "description").text = effort.description()
        return node

    def categoryNode(
        self, parentNode, category, *categorizableContainers
    ):  # pylint: disable=W0621
        def inCategorizableContainer(categorizable):
            for container in categorizableContainers:
                if categorizable in container:
                    return True
            return False

        node = self.baseCompositeNode(
            parentNode,
            category,
            "category",
            self.categoryNode,
            categorizableContainers,
        )
        if category.isFiltered():
            node.attrib["filtered"] = str(category.isFiltered())
        if category.hasExclusiveSubcategories():
            node.attrib["exclusiveSubcategories"] = str(
                category.hasExclusiveSubcategories()
            )
        for eachNote in sortedById(category.notes()):
            self.noteNode(node, eachNote)
        for attachment in sortedById(category.attachments()):
            self.attachmentNode(node, attachment)
        # Make sure the categorizables referenced are actually in the
        # categorizableContainer, i.e. they are not deleted
        categorizableIds = " ".join(
            [
                categorizable.id()
                for categorizable in sortedById(category.categorizables())
                if inCategorizableContainer(categorizable)
            ]
        )
        if categorizableIds:
            node.attrib["categorizables"] = categorizableIds
        return node

    def noteNode(self, parentNode, note):  # pylint: disable=W0621
        node = self.baseCompositeNode(parentNode, note, "note", self.noteNode)
        for attachment in sortedById(note.attachments()):
            self.attachmentNode(node, attachment)
        return node

    def __baseNode(self, parentNode, item, nodeName):
        node = ET.SubElement(
            parentNode,
            nodeName,
            dict(id=item.id(), status=str(item.getStatus())),
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

    def baseNode(self, parentNode, item, nodeName):
        """Create a node and add the attributes that all domain
        objects share, such as id, subject, description."""
        node = self.__baseNode(parentNode, item, nodeName)
        if item.foregroundColor():
            node.attrib["fgColor"] = str(item.foregroundColor())
        if item.backgroundColor():
            node.attrib["bgColor"] = str(item.backgroundColor())
        if item.font():
            node.attrib["font"] = str(item.font().GetNativeFontInfoDesc())
        if item.icon():
            node.attrib["icon"] = str(item.icon())
        if item.selectedIcon():
            node.attrib["selectedIcon"] = str(item.selectedIcon())
        if item.ordering():
            node.attrib["ordering"] = str(item.ordering())
        return node

    def baseCompositeNode(
        self,
        parentNode,
        item,
        nodeName,
        childNodeFactory,
        childNodeFactoryArgs=(),
    ):
        """Same as baseNode, but also create child nodes by means of
        the childNodeFactory."""
        node = self.__baseNode(parentNode, item, nodeName)
        if item.foregroundColor():
            node.attrib["fgColor"] = str(item.foregroundColor())
        if item.backgroundColor():
            node.attrib["bgColor"] = str(item.backgroundColor())
        if item.font():
            node.attrib["font"] = str(item.font().GetNativeFontInfoDesc())
        if item.icon():
            node.attrib["icon"] = str(item.icon())
        if item.selectedIcon():
            node.attrib["selectedIcon"] = str(item.selectedIcon())
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

    def attachmentNode(self, parentNode, attachment):
        node = self.baseNode(parentNode, attachment, "attachment")
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
            self.noteNode(node, eachNote)
        return node

    def syncMLNode(self, parentNode, syncMLConfig):
        node = ET.SubElement(parentNode, "syncmlconfig")
        self.__syncMLNode(syncMLConfig, node)
        return node

    def __syncMLNode(self, cfg, node):
        for name, value in cfg.properties():
            ET.SubElement(node, "property", dict(name=name)).text = value

        for childCfg in cfg.children():
            child = ET.SubElement(node, childCfg.name)
            self.__syncMLNode(childCfg, child)

    def budgetAsAttribute(self, budget):
        return "%d:%02d:%02d" % budget.hoursMinutesSeconds()

    def formatDateTime(self, dateTime):
        return dateTime.strftime("%Y-%m-%d %H:%M:%S")


class ChangesXMLWriter(object):
    def __init__(self, fd):
        self.__fd = fd

    def write(self, allChanges):
        root = ET.Element("changes")
        if allChanges:
            for devName, monitor in list(allChanges.items()):
                devNode = ET.SubElement(root, "device")
                devNode.attrib["guid"] = monitor.guid()
                for id_, changes in list(monitor.allChanges().items()):
                    objNode = ET.SubElement(devNode, "obj")
                    objNode.attrib["id"] = id_
                    if changes:
                        objNode.text = ",".join(list(changes))

        tree = ET.ElementTree(root)
        tree.write(self.__fd)


class TemplateXMLWriter(XMLWriter):
    def write(self, tsk):  # pylint: disable=W0221
        super().write(
            task.TaskList([tsk]),
            category.CategoryList(),
            note.NoteContainer(),
            None,
            None,
        )

    def taskNode(self, parentNode, task):  # pylint: disable=W0621
        node = super().taskNode(parentNode, task)

        for name, getter in [
            ("plannedstartdate", "plannedStartDateTime"),
            ("duedate", "dueDateTime"),
            ("completiondate", "completionDateTime"),
            ("reminder", "reminder"),
        ]:
            if hasattr(task, name + "tmpl"):
                value = getattr(task, name + "tmpl") or None
            else:
                dateTime = getattr(task, getter)()
                if dateTime not in (None, date.DateTime()):
                    delta = dateTime - date.Now()
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
