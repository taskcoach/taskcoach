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
import calendar
import csv
import datetime
import io
import re
import math

_YEAR_FIRST = re.compile(r"(?<!\d)\d{4}[-/.]\d")
# Task Coach's own "2026-Mar-28-Sat"; its weekday adds nothing and may
# read as a month ("mar." is Tuesday in French)
_OWN_ABBREVIATED = re.compile(r"^\s*(\d{4})-([^-]+)-(\d{1,2})-\S+")
_LETTERS = re.compile(r"[^\W\d_]+")
_NUMBER = re.compile(r"\d+")
_LETTER_DOT = re.compile(r"(?<=[^\W\d_])\.")
# Two defaults that differ in every part: a part the text lacks shows
_DEFAULTS = (datetime.datetime(2001, 1, 1), datetime.datetime(2002, 2, 2))


def _system_names():
    """The system language's month names, full and short, and AM and
    PM: what Task Coach's own export writes."""
    months = [
        (calendar.month_name[number], calendar.month_abbr[number])
        for number in range(1, 13)
    ]
    ampm = [datetime.time(hour).strftime("%p") for hour in (1, 13)]
    return months, ampm


def _local_word(name):
    """The word dateutil sees for a name: its last run of letters ("de
    gener", "d’abril", "janv."), or None for a name with a number
    ("1月")."""
    words = _LETTERS.findall(name.lower())
    if words and not _NUMBER.search(name):
        return words[-1]
    return None


def _is_known(info, word):
    lookups = (info.weekday, info.month, info.hms, info.ampm, info.tzoffset)
    return (
        info.jump(word)
        or info.pertain(word)
        or info.utczone(word)
        or any(lookup(word) is not None for lookup in lookups)
    )


def _with_local(english, names, info):
    words = list(english)
    for name in names:
        word = _local_word(name)
        if word and word not in words and not _is_known(info, word):
            words.append(word)
    return tuple(words)


def _parser_info():
    """dateutil's English month names and AM/PM plus the system
    language's; a word dateutil already reads otherwise is left out."""
    english = dparser.parserinfo()
    months, ampm = _system_names()
    return type(
        "SystemLanguage",
        (dparser.parserinfo,),
        dict(
            MONTHS=[
                _with_local(names, local, english)
                for names, local in zip(dparser.parserinfo.MONTHS, months)
            ],
            AMPM=[
                _with_local(names, (local,), english)
                for names, local in zip(dparser.parserinfo.AMPM, ampm)
            ],
        ),
    )()


def _own_abbreviated(match):
    """Year, month and day of Task Coach's own form; a month written
    with a number ("1月", "Thg 1") is that number."""
    year, month, day = match.groups()
    number = _NUMBER.search(month)
    words = _LETTERS.findall(month)
    month = number.group() if number else (words[-1] if words else month)
    return "%s-%s-%s" % (year, month, day)


class CSVReader(object):
    def __init__(self, taskList, category_list):
        self.taskList = taskList
        self.categoryList = category_list
        self.__parser_info = _parser_info()

    def createReader(self, fp, dialect, hasHeaders):
        reader = csv.reader(fp, dialect=dialect)
        if hasHeaders:
            next(reader)
        return reader

    def read(self, **kwargs):
        # As the wizard's preview showed it
        with open(
            kwargs["filename"],
            "r",
            encoding=kwargs["encoding"],
            errors="replace",
        ) as fp:
            rows = list(
                self.createReader(fp, kwargs["dialect"], kwargs["hasHeaders"])
            )

        rx1 = re.compile(r"^(\d+):(\d+)$")
        rx2 = re.compile(r"^(\d+):(\d+):(\d+)$")

        dayfirst = kwargs["dayfirst"]
        tasks_by_id = dict()
        tasks = []

        for index, line in enumerate(rows):
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
            actual_start_date_time = None
            planned_start_date_time = None
            due_date_time = None
            completion_date_time = None
            reminder_date_time = None
            budget = TimeDelta()
            fixed_fee = 0.0
            hourly_fee = 0.0
            percent_complete = 0

            for idx, field_value in enumerate(line):
                if kwargs["mappings"][idx] == _("ID"):
                    id_ = field_value
                elif kwargs["mappings"][idx] == _("Subject"):
                    subject = field_value
                elif kwargs["mappings"][idx] == _("Description"):
                    description.write(field_value)
                    description.write("\n")
                elif kwargs["mappings"][idx] == _("Category") and field_value:
                    name = field_value
                    if name.startswith("(") and name.endswith(")"):
                        continue  # Skip categories of subitems
                    cat = self.categoryList.findCategoryByName(name)
                    if not cat:
                        cat = self.createCategory(name)
                    categories.append(cat)
                elif kwargs["mappings"][idx] == _("Priority"):
                    try:
                        priority = int(field_value)
                    except ValueError:
                        pass
                elif kwargs["mappings"][idx] == _("Actual start date"):
                    actual_start_date_time = self.parse_date_time(
                        field_value, dayfirst=dayfirst
                    )
                elif kwargs["mappings"][idx] == _("Planned start date"):
                    planned_start_date_time = self.parse_date_time(
                        field_value, dayfirst=dayfirst
                    )
                elif kwargs["mappings"][idx] == _("Due date"):
                    due_date_time = self.parse_date_time(
                        field_value, 23, 59, 59, dayfirst=dayfirst
                    )
                elif kwargs["mappings"][idx] == _("Completion date"):
                    completion_date_time = self.parse_date_time(
                        field_value, 12, 0, 0, dayfirst=dayfirst
                    )
                elif kwargs["mappings"][idx] == _("Reminder date"):
                    reminder_date_time = self.parse_date_time(
                        field_value, dayfirst=dayfirst
                    )
                elif kwargs["mappings"][idx] == _("Budget"):
                    try:
                        value = float(field_value)
                        hours = int(math.floor(value))
                        minutes = int(60 * (value - hours))
                        budget = TimeDelta(
                            hours=hours, minutes=minutes, seconds=0
                        )
                    except ValueError:
                        mt = rx1.search(field_value)
                        if mt:
                            budget = TimeDelta(
                                hours=int(mt.group(1)),
                                minutes=int(mt.group(2)),
                                seconds=0,
                            )
                        else:
                            mt = rx2.search(field_value)
                            if mt:
                                budget = TimeDelta(
                                    hours=int(mt.group(1)),
                                    minutes=int(mt.group(2)),
                                    seconds=int(mt.group(3)),
                                )
                elif kwargs["mappings"][idx] == _("Fixed fee"):
                    try:
                        fixed_fee = float(field_value)
                    except ValueError:
                        pass
                elif kwargs["mappings"][idx] == _("Hourly fee"):
                    try:
                        hourly_fee = float(field_value)
                    except ValueError:
                        pass
                elif kwargs["mappings"][idx] == _("Percent complete"):
                    try:
                        percent_complete = max(0, min(100, int(field_value)))
                    except ValueError:
                        pass

            task = Task(
                subject=subject,
                description=description.getvalue(),
                priority=priority,
                actualStartDateTime=actual_start_date_time,
                plannedStartDateTime=planned_start_date_time,
                dueDateTime=due_date_time,
                completionDateTime=completion_date_time,
                reminder=reminder_date_time,
                budget=budget,
                fixedFee=fixed_fee,
                hourlyFee=hourly_fee,
                percentageComplete=percent_complete,
            )

            if id_ is not None:
                tasks_by_id[id_] = task

            for category in categories:
                task.addCategory(category)

            tasks.append(task)

        # OmniFocus uses the task's ID to keep track of hierarchy: 1 => 1.1 and 1.2, etc...

        if tasks_by_id:
            ids = []
            for id_, task in list(tasks_by_id.items()):
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
                    if pid in tasks_by_id:
                        tasks_by_id[pid].addChild(tasks_by_id[sid])
                else:
                    self.taskList.append(tasks_by_id[sid])
        else:
            self.taskList.extend(tasks)

    def createCategory(self, name):
        if " -> " in name:
            parent_name, child_name = name.rsplit(" -> ", 1)
            parent = self.categoryList.findCategoryByName(parent_name)
            if not parent:
                parent = self.createCategory(parent_name)
            new_category = Category(subject=child_name)
            parent.addChild(new_category)
            new_category.set_parent(parent)
        else:
            new_category = Category(subject=name)
        self.categoryList.append(new_category)
        return new_category

    def parse_date_time(
        self,
        text,
        default_hour=0,
        default_minute=0,
        default_second=0,
        dayfirst=False,
    ):
        """The date and time in text, or None when it lacks its day or
        its month: no part comes from today but a missing year."""
        if not text:
            return None
        text = _OWN_ABBREVIATED.sub(_own_abbreviated, text)
        # A date with the year first is year-month-day (ISO 8601);
        # dateutil would read it year-day-month when day first
        dayfirst = dayfirst and not _YEAR_FIRST.search(text)
        # "janv." in "2026-janv.-06": the dot is no separator
        text = _LETTER_DOT.sub("", text)
        try:
            first, second = (
                dparser.parse(
                    text,
                    self.__parser_info,
                    default=default,
                    dayfirst=dayfirst,
                    fuzzy=True,
                )
                for default in _DEFAULTS
            )
            if (first.month, first.day) != (second.month, second.day):
                return None
            if first.year != second.year:
                first = first.replace(year=datetime.date.today().year)
        # dateutil 2.8.1 (Ubuntu 22.04) raises TypeError for some
        # out-of-range months
        except (ValueError, OverflowError, TypeError, AttributeError):
            return None
        if (first.hour, first.minute, first.second) == (0, 0, 0):
            first = first.replace(
                hour=default_hour, minute=default_minute, second=default_second
            )
        return DateTime(
            first.year,
            first.month,
            first.day,
            first.hour,
            first.minute,
            first.second,
        )
