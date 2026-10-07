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

from taskcoachlib.domain import effort
from taskcoachlib.i18n import _
from . import base


class NewEffortCommand(base.BaseCommand):
    plural_name = _("New efforts")
    singular_name = _('New effort of "%s"')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items = self.efforts = [
            effort.Effort(task) for task in self.items
        ]

    def name_subject(self, effort):  # pylint: disable=W0621
        return effort.task().subject()

    def do_command(self):
        super().do_command()
        for effort in self.efforts:  # pylint: disable=W0621
            effort.task().addEffort(effort)


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
        super().__init__(*args, **kwargs)
        self.__tasks = self.items
        self.items = self.__efforts

    def name_subject(self, an_effort):
        return self.__tasks[0].subject() if self.__tasks else ""

    def do_command(self):
        super().do_command()
        if not self.__tasks:
            return
        target_task = self.__tasks[0]
        for eff in self.__efforts:
            eff.set_task(target_task)
            target_task.addEffort(eff)


class DeleteEffortCommand(base.DeleteCommand):
    plural_name = _("Delete efforts")
    singular_name = _('Delete effort "%s"')


class EditTaskCommand(base.BaseCommand):
    plural_name = _("Change task of effort")
    singular_name = _('Change task of "%s" effort')

    def __init__(self, *args, **kwargs):
        self.__task = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.set_task(self.__task)


class EditEffortStartDateTimeCommand(base.BaseCommand):
    plural_name = _("Change effort start date and time")
    singular_name = _('Change effort start date and time of "%s"')

    def __init__(self, *args, **kwargs):
        self.__datetime = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    def can_do(self):
        return super().can_do()

    def do_command(self):
        for item in self.items:
            item.setStart(self.__datetime)
            task = item.task()
            if self.__datetime < task.actualStartDateTime():
                task.set_actual_start_date_time(self.__datetime)


class EditEffortStopDateTimeCommand(base.BaseCommand):
    plural_name = _("Change effort stop date and time")
    singular_name = _('Change effort stop date and time of "%s"')

    def __init__(self, *args, **kwargs):
        self.__datetime = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    def can_do(self):
        return super().can_do()

    def do_command(self):
        for item in self.items:
            item.setStop(self.__datetime)


class EditEffortDurationCommand(base.BaseCommand):
    plural_name = _("Change effort durations")
    singular_name = _('Change effort duration of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newDuration = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setDuration(self.__newDuration)


class EditEffortEntryModeCommand(base.BaseCommand):
    plural_name = _("Change effort entry modes")
    singular_name = _('Change effort entry mode of "%s"')

    def __init__(self, *args, **kwargs):
        self.__newMode = kwargs.pop("newValue")
        super().__init__(*args, **kwargs)

    def do_command(self):
        super().do_command()
        for item in self.items:
            item.setEntryMode(self.__newMode)
