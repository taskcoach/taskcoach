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

from taskcoachlib.domain import effort, date
from taskcoachlib.i18n import _
from . import base


class NewEffortCommand(base.BaseCommand):
    plural_name = _("New efforts")
    singular_name = _('New effort of "%s"')

    def __init__(self, *args, **kwargs):
        self.__tasks = []
        super().__init__(*args, **kwargs)
        self.__tasks = self.items
        self.items = self.efforts = [
            effort.Effort(task) for task in self.items
        ]
        self.__oldActualStartDateTimes = {}
        self.save_modification_datetimes()

    def modified_items(self):
        return self.__tasks

    def name_subject(self, effort):  # pylint: disable=W0621
        return effort.task().subject()

    def do_command(self):
        super().do_command()
        for effort in self.efforts:  # pylint: disable=W0621
            task = effort.task()
            if (
                task not in self.__oldActualStartDateTimes
                and effort.getStart() < task.actualStartDateTime()
            ):
                self.__oldActualStartDateTimes[task] = (
                    task.actualStartDateTime()
                )
                task.setActualStartDateTime(effort.getStart())
            task.addEffort(effort)

    def undo_command(self):
        super().undo_command()
        for effort in self.efforts:  # pylint: disable=W0621
            task = effort.task()
            task.removeEffort(effort)
            if task in self.__oldActualStartDateTimes:
                task.setActualStartDateTime(
                    self.__oldActualStartDateTimes[task]
                )
                del self.__oldActualStartDateTimes[task]

    redo_command = do_command


class DeleteEffortCommand(base.DeleteCommand):
    plural_name = _("Delete efforts")
    singular_name = _('Delete effort "%s"')

    def modified_items(self):
        return [item.task() for item in self.items]


class EditTaskCommand(base.BaseCommand):
    plural_name = _("Change task of effort")
    singular_name = _('Change task of "%s" effort')

    def __init__(self, *args, **kwargs):
        self.__task = kwargs.pop("newValue")
        self.__oldTasks = []
        super().__init__(*args, **kwargs)
        self.__oldTasks = [item.task() for item in self.items]
        self.save_modification_datetimes()

    def modified_items(self):
        return [self.__task] + self.__oldTasks

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setTask(self.__task)

    def undo_command(self):
        super().undo_command()
        for item, oldTask in zip(self.items, self.__oldTasks):
            item.setTask(oldTask)

    def redo_command(self):
        self.do_command()


class EditEffortStartDateTimeCommand(base.BaseCommand):
    plural_name = _("Change effort start date and time")
    singular_name = _('Change effort start date and time of "%s"')

    def __init__(self, *args, **kwargs):
        self.__datetime = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldDateTimes = [item.getStart() for item in self.items]
        self.__oldActualStartDateTimes = {}

    def canDo(self):
        maxDateTime = date.DateTime()
        return super().canDo() and all(
            self.__datetime < (item.getStop() or maxDateTime)
            for item in self.items
        )

    def do_command(self):
        import sys
        sys.stderr.write("[CMD] EditEffortStartDateTimeCommand.do_command called, datetime=%s\n" % self.__datetime)
        sys.stderr.flush()
        for item in self.items:
            sys.stderr.write("[CMD] About to call item.setStart(%s)\n" % self.__datetime)
            sys.stderr.flush()
            item.setStart(self.__datetime)
            sys.stderr.write("[CMD] item.setStart complete\n")
            sys.stderr.flush()
            task = item.task()
            if (
                task not in self.__oldActualStartDateTimes
                and self.__datetime < task.actualStartDateTime()
            ):
                self.__oldActualStartDateTimes[task] = (
                    task.actualStartDateTime()
                )
                sys.stderr.write("[CMD] About to call task.setActualStartDateTime\n")
                sys.stderr.flush()
                task.setActualStartDateTime(self.__datetime)
                sys.stderr.write("[CMD] task.setActualStartDateTime complete\n")
                sys.stderr.flush()
        sys.stderr.write("[CMD] EditEffortStartDateTimeCommand.do_command complete\n")
        sys.stderr.flush()

    def undo_command(self):
        for item, oldDateTime in zip(self.items, self.__oldDateTimes):
            item.setStart(oldDateTime)
            task = item.task()
            if task in self.__oldActualStartDateTimes:
                task.setActualStartDateTime(
                    self.__oldActualStartDateTimes[task]
                )
                del self.__oldActualStartDateTimes[task]

    def redo_command(self):
        self.do_command()


class EditEffortStopDateTimeCommand(base.BaseCommand):
    plural_name = _("Change effort stop date and time")
    singular_name = _('Change effort stop date and time of "%s"')

    def __init__(self, *args, **kwargs):
        self.__datetime = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldDateTimes = [item.getStop() for item in self.items]

    def canDo(self):
        return super().canDo() and all(
            self.__datetime > item.getStart() for item in self.items
        )

    def do_command(self):
        for item in self.items:
            item.setStop(self.__datetime)

    def undo_command(self):
        for item, oldDateTime in zip(self.items, self.__oldDateTimes):
            item.setStop(oldDateTime)

    def redo_command(self):
        self.do_command()
