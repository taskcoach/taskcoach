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

# What a missing attribute means, for the writer and the reader alike
# (docs/PERSISTENCE_XML.md, Defaults). The first value of each field
# is its default: an item holding it is saved without the attribute,
# and a missing attribute is read as it. The other values are other
# written forms of that default, read as it.

from taskcoachlib.domain import date

NOT_SET = date.DateTime()  # A date not set: the latest date
UNKNOWN = date.DateTime.min  # A creation date from before they were kept

DEFAULTS = {
    # Every item
    "subject": ("",),
    "description": ("",),  # An element, not an attribute
    "fgColor": (None,),
    "bgColor": (None,),
    "font": (None,),
    "icon": ("",),
    "noIcon": (False,),  # The "No icon" override (format 39)
    "ordering": (0,),
    "creationDateTime": (UNKNOWN,),
    "modificationDateTime": (None,),  # None: the creation date
    # Tasks, notes and categories
    "expandedContexts": ([],),
    # Tasks
    "plannedstartdate": (NOT_SET, "", "None"),
    "duedate": (NOT_SET, "", "None"),
    "actualstartdate": (NOT_SET, "", "None"),
    "completiondate": (NOT_SET, "", "None"),
    "percentageComplete": (0,),
    "budget": (date.TimeDelta(),),
    "plannedDuration": (date.TimeDelta(),),
    "plannedDurationMode": ("implicit", ""),
    "priority": (0,),
    "hourlyFee": (0,),
    "fixedFee": (0,),
    "reminder": (NOT_SET, "", "None"),
    "reminderBeforeSnooze": (None, "", "None"),  # None: the reminder
    "prerequisites": (frozenset(),),
    "shouldMarkCompletedWhenAllChildrenCompleted": (None,),  # Preference
    # Tasks and notes
    "categories": (frozenset(),),
    # A task's recurrence
    "unit": ("",),
    "amount": (1,),
    "count": (0,),
    "max": (0,),  # No maximum
    "stop_datetime": (NOT_SET, "", "None"),
    "sameWeekday": (False,),
    "recurBasedOnCompletion": (False,),
    "weekdays": ([],),
    # Categories
    "filtered": (False,),
    "exclusiveSubcategories": (False,),
    "stylePriority": (0,),
    # Efforts
    "stop": (None, "", "None"),  # None: still running
    "entryMode": ("standard", ""),
    # Mail attachments
    "fromName": ("",),
    "fromAddress": ("",),
    "sentDateTime": (NOT_SET, "", "None"),
}


def is_default(name, value):
    """Whether an item's value is the field's default: saved without
    the attribute."""
    default = DEFAULTS[name][0]
    return value is None if default is None else value == default


def read(name, text, parse):
    """A field's value from its attribute's text, None when missing:
    the default when missing, written in another form of it, or not
    readable."""
    default, *forms = DEFAULTS[name]
    if text is None or text in forms:
        return default
    try:
        return parse(text)
    except ValueError:
        return default
