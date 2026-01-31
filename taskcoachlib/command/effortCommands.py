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


class AddEffortCommand(base.BaseCommand):
    """Command to add efforts to a task.

    Used primarily for paste operations where efforts are copied from one
    task and pasted to another. Updates the effort's task reference and
    adds it to the target task's effort list.
    """
    plural_name = _("Add efforts")
    singular_name = _('Add effort to "%s"')

    def __init__(self, *args, **kwargs):
        self.__efforts = kwargs.pop("efforts", [])
        self.__tasks = []
        self.__old_task_refs = []
        super().__init__(*args, **kwargs)
        self.__tasks = self.items
        # Store original task references for undo support
        self.__old_task_refs = [eff.task() for eff in self.__efforts]
        self.items = self.__efforts
        self.save_modification_datetimes()

    def modified_items(self):
        # Filter out None values from old task refs
        return self.__tasks + [t for t in self.__old_task_refs if t is not None]

    def name_subject(self, anEffort):
        return self.__tasks[0].subject() if self.__tasks else ""

    def do_command(self):
        super().do_command()
        if not self.__tasks:
            return
        target_task = self.__tasks[0]
        for eff in self.__efforts:
            eff.setTask(target_task)
            target_task.addEffort(eff)

    def undo_command(self):
        super().undo_command()
        if not self.__tasks:
            return
        target_task = self.__tasks[0]
        for eff, old_task in zip(self.__efforts, self.__old_task_refs):
            target_task.removeEffort(eff)
            eff.setTask(old_task)
            if old_task:
                old_task.addEffort(eff)

    def redo_command(self):
        self.do_command()


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
        return super().canDo()

    def do_command(self):
        for item in self.items:
            item.setStart(self.__datetime)
            task = item.task()
            if (
                task not in self.__oldActualStartDateTimes
                and self.__datetime < task.actualStartDateTime()
            ):
                self.__oldActualStartDateTimes[task] = (
                    task.actualStartDateTime()
                )
                task.setActualStartDateTime(self.__datetime)

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
        return super().canDo()

    def do_command(self):
        for item in self.items:
            item.setStop(self.__datetime)

    def undo_command(self):
        for item, oldDateTime in zip(self.items, self.__oldDateTimes):
            item.setStop(oldDateTime)

    def redo_command(self):
        self.do_command()


class EditEffortDurationCommand(base.BaseCommand):
    plural_name = _("Change effort durations")
    singular_name = _('Change effort duration of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newDuration = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldDurations = [item.duration() for item in self.items]

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setDuration(self.__newDuration)

    def undo_command(self):
        super().undo_command()
        for item, oldDuration in zip(self.items, self.__oldDurations):
            item.setDuration(oldDuration)

    def redo_command(self):
        self.do_command()


class EditEffortEntryModeCommand(base.BaseCommand):
    plural_name = _("Change effort entry modes")
    singular_name = _('Change effort entry mode of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newMode = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)
        self.__oldModes = [item.entryMode() for item in self.items]

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setEntryMode(self.__newMode)

    def undo_command(self):
        super().undo_command()
        for item, oldMode in zip(self.items, self.__oldModes):
            item.setEntryMode(oldMode)

    def redo_command(self):
        self.do_command()
