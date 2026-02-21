# -*- coding: utf-8 -*-

"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2008 João Alexandre de Toledo <jtoledo@griffo.com.br>

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

from taskcoachlib.i18n import _
from taskcoachlib.domain import categorizable
from taskcoachlib import help, operating_system  # pylint: disable=W0622
from . import task


class TaskListQueryMixin(object):
    def nr_of_tasks_per_status(self):
        statuses = [
            eachTask.status() for eachTask in self if not eachTask.isDeleted()
        ]
        count = dict()
        for status in task.Task.possibleStatuses():
            count[status] = statuses.count(status)
        return count


class TaskList(TaskListQueryMixin, categorizable.CategorizableContainer):
    # FIXME: TaskList should be called TaskCollection or TaskSet

    newItemMenuText = _("&New task...") + (
        "\tINSERT" if not operating_system.isMac() else "\tCtrl+N"
    )
    newItemHelpText = help.taskNew

    def nr_being_tracked(self):
        return len(self.tasks_being_tracked())

    def tasks_being_tracked(self):
        return [eachTask for eachTask in self if eachTask.isBeingTracked()]

    def efforts(self):
        result = []
        for task in self:  # pylint: disable=W0621
            result.extend(task.efforts())
        return result

    def original_length(self):
        """Provide a way for bypassing the __len__ method of decorators."""
        return len([t for t in self if not t.isDeleted()])

    def min_priority(self):
        return min(self.__allPriorities())

    def max_priority(self):
        return max(self.__allPriorities())

    def __allPriorities(self):
        return [task.priority() for task in self if not task.isDeleted()] or (
            0,
        )  # pylint: disable=W0621
