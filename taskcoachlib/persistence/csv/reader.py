"""
Task Coach - Your friendly task manager
Copyright (C) 2011 Task Coach developers <developers@taskcoach.org>

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

from taskcoachlib.domain.category import Category
from taskcoachlib.domain.date import DateTime, TimeDelta
from taskcoachlib.domain.task import Task
from taskcoachlib.i18n import _
from dateutil import parser as dparser
import csv
import tempfile
import io
import re
import math


class CSVReader(object):
    def __init__(self, taskList, categoryList):
        self.taskList = taskList
        self.categoryList = categoryList

    def createReader(self, fp, dialect, hasHeaders):
        reader = csv.reader(fp, dialect=dialect)
        if hasHeaders:
            next(reader)
        return reader

    def read(self, **kwargs):
        fp = tempfile.TemporaryFile()
        fp.write(
            open(kwargs["filename"], "r")
            .read()
            .decode(kwargs["encoding"])
            .encode("UTF-8")
        )
        fp.seek(0)

        rx1 = re.compile(r"^(\d+):(\d+)$")
        rx2 = re.compile(r"^(\d+):(\d+):(\d+)$")

        reader = self.createReader(fp, kwargs["dialect"], kwargs["hasHeaders"])
        dayfirst = kwargs["dayfirst"]
        tasksById = dict()
        tasks = []

        for index, line in enumerate(reader):
            if (
                kwargs["importSelectedRowsOnly"]
                and index not in kwargs["selectedRows"]
            ):
                continue
            subject = _("No subject")
            id_ = None
            description = io.StringIO()
            categories = []
            priority = 0
            actualStartDateTime = None
            plannedStartDateTime = None
            dueDateTime = None
            completionDateTime = None
            reminderDateTime = None
            budget = TimeDelta()
            fixedFee = 0.0
            hourlyFee = 0.0
            percentComplete = 0

            for idx, fieldValue in enumerate(line):
                if kwargs["mappings"][idx] == _("ID"):
                    id_ = fieldValue.decode("UTF-8")
                elif kwargs["mappings"][idx] == _("Subject"):
                    subject = fieldValue.decode("UTF-8")
                elif kwargs["mappings"][idx] == _("Description"):
                    description.write(fieldValue.decode("UTF-8"))
                    description.write("\n")
                elif kwargs["mappings"][idx] == _("Category") and fieldValue:
                    name = fieldValue.decode("UTF-8")
                    if name.startswith("(") and name.endswith(")"):
                        continue  # Skip categories of subitems
                    cat = self.categoryList.findCategoryByName(name)
                    if not cat:
                        cat = self.createCategory(name)
                    categories.append(cat)
                elif kwargs["mappings"][idx] == _("Priority"):
                    try:
                        priority = int(fieldValue)
                    except ValueError:
                        pass
                elif kwargs["mappings"][idx] == _("Actual start date"):
                    actualStartDateTime = self.parseDateTime(
                        fieldValue, dayfirst=dayfirst
                    )
                elif kwargs["mappings"][idx] == _("Planned start date"):
                    plannedStartDateTime = self.parseDateTime(
                        fieldValue, dayfirst=dayfirst
                    )
                elif kwargs["mappings"][idx] == _("Due date"):
                    dueDateTime = self.parseDateTime(
                        fieldValue, 23, 59, 59, dayfirst=dayfirst
                    )
                elif kwargs["mappings"][idx] == _("Completion date"):
                    completionDateTime = self.parseDateTime(
                        fieldValue, 12, 0, 0, dayfirst=dayfirst
                    )
                elif kwargs["mappings"][idx] == _("Reminder date"):
                    reminderDateTime = self.parseDateTime(
                        fieldValue, dayfirst=dayfirst
                    )
                elif kwargs["mappings"][idx] == _("Budget"):
                    try:
                        value = float(fieldValue)
                        hours = int(math.floor(value))
                        minutes = int(60 * (value - hours))
                        budget = TimeDelta(
                            hours=hours, minutes=minutes, seconds=0
                        )
                    except ValueError:
                        mt = rx1.search(fieldValue)
                        if mt:
                            budget = TimeDelta(
                                hours=int(mt.group(1)),
                                minutes=int(mt.group(2)),
                                seconds=0,
                            )
                        else:
                            mt = rx2.search(fieldValue)
                            if mt:
                                budget = TimeDelta(
                                    hours=int(mt.group(1)),
                                    minutes=int(mt.group(2)),
                                    seconds=int(mt.group(3)),
                                )
                elif kwargs["mappings"][idx] == _("Fixed fee"):
                    try:
                        fixedFee = float(fieldValue)
                    except ValueError:
                        pass
                elif kwargs["mappings"][idx] == _("Hourly fee"):
                    try:
                        hourlyFee = float(fieldValue)
                    except ValueError:
                        pass
                elif kwargs["mappings"][idx] == _("Percent complete"):
                    try:
                        percentComplete = max(0, min(100, int(fieldValue)))
                    except ValueError:
                        pass

            task = Task(
                subject=subject,
                description=description.getvalue(),
                priority=priority,
                actualStartDateTime=actualStartDateTime,
                plannedStartDateTime=plannedStartDateTime,
                dueDateTime=dueDateTime,
                completionDateTime=completionDateTime,
                reminder=reminderDateTime,
                budget=budget,
                fixedFee=fixedFee,
                hourlyFee=hourlyFee,
                percentageComplete=percentComplete,
            )

            if id_ is not None:
                tasksById[id_] = task

            for category in categories:
                category.addCategorizable(task)
                task.addCategory(category)

            tasks.append(task)

        # OmniFocus uses the task's ID to keep track of hierarchy: 1 => 1.1 and 1.2, etc...

        if tasksById:
            ids = []
            for id_, task in list(tasksById.items()):
                try:
                    ids.append(tuple(map(int, id_.split("."))))
                except ValueError:
                    self.taskList.append(task)

            ids.sort()
            ids.reverse()

            for id_ in ids:
                sid = ".".join(map(str, id_))
                if len(id_) >= 2:
                    pid = ".".join(map(str, id_[:-1]))
                    if pid in tasksById:
                        tasksById[pid].addChild(tasksById[sid])
                else:
                    self.taskList.append(tasksById[sid])
        else:
            self.taskList.extend(tasks)

    def createCategory(self, name):
        if " -> " in name:
            parentName, childName = name.rsplit(" -> ", 1)
            parent = self.categoryList.findCategoryByName(parentName)
            if not parent:
                parent = self.createCategory(parentName)
            newCategory = Category(subject=childName)
            parent.addChild(newCategory)
            newCategory.setParent(parent)
        else:
            newCategory = Category(subject=name)
        self.categoryList.append(newCategory)
        return newCategory

    def parseDateTime(
        self,
        fieldValue,
        defaultHour=0,
        defaultMinute=0,
        defaultSecond=0,
        dayfirst=False,
    ):
        if not fieldValue:
            return None
        try:
            dateTime = dparser.parse(
                fieldValue.decode("UTF-8"), dayfirst=dayfirst, fuzzy=True
            ).replace(tzinfo=None)
            hour, minute, second = (
                dateTime.hour,
                dateTime.minute,
                dateTime.second,
            )
            if 0 == hour == minute == second:
                hour = defaultHour
                minute = defaultMinute
                second = defaultSecond
            return DateTime(
                dateTime.year,
                dateTime.month,
                dateTime.day,
                hour,
                minute,
                second,
            )
        except (ValueError, AttributeError):
            return None
