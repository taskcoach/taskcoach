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

# Module for metaclasses that are not widely recognized patterns.

import weakref


class NumberedInstances(type):
    """A metaclass that numbers class instances. Use by defining the metaclass
    of a class NumberedInstances, e.g.:
    class Numbered:
        __metaclass__ = NumberedInstances
    Each instance of class Numbered will have an attribute instanceNumber
    that is unique.

    Callers may pass an explicit instanceNumber to reuse a specific
    number instead of the lowest unused one. Restoring a saved layout
    needs that: the numbers it has to reproduce may contain a gap, which
    lowest_unused_number would fill in and thereby rename the pane."""

    count = dict()

    def __call__(cls, *args, **kwargs):
        if cls not in NumberedInstances.count:
            NumberedInstances.count[cls] = weakref.WeakKeyDictionary()
        instance_number = kwargs.get("instanceNumber")
        if instance_number is None:
            instance_number = NumberedInstances.lowest_unused_number(cls)
        kwargs["instanceNumber"] = instance_number
        instance = super(NumberedInstances, cls).__call__(*args, **kwargs)
        NumberedInstances.count[cls][instance] = instance_number
        return instance

    def lowest_unused_number(cls):
        used_numbers = sorted(NumberedInstances.count[cls].values())
        for index, used_number in enumerate(used_numbers):
            if used_number != index:
                return index
        return len(used_numbers)
