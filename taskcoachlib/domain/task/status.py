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

from taskcoachlib.i18n import _
from taskcoachlib.config import defaults


def themed_section(section):
    """The settings section of a status style in the current theme:
    its _dark twin in a dark one."""
    try:
        from taskcoachlib.config import settings2

        return section + "_dark" if settings2.window.theme_is_dark else section
    except Exception as e:
        from taskcoachlib.meta.debug import log_step

        log_step("themed_section(%s): %s" % (section, e), prefix="THEME")
        return section


class TaskStatus(object):
    def __init__(
        self,
        status_string,
        plural_label,
        count_label,
        hide_menu_text,
        hide_help_text,
    ):
        self.status_string = status_string
        self.plural_label = plural_label
        self.count_label = count_label
        self.hide_menu_text = hide_menu_text
        self.hide_help_text = hide_help_text

    def get_sort_priority(self, settings):
        return int(
            settings.get("statussortpriority", "%stasks" % self.status_string)
        )

    def icon_id(self, settings, required=False):
        """The status's icon in the current theme (Preferences >
        Statuses), empty when set to none; required gives the default
        then (a toolbar button needs one)."""
        section = themed_section("icon")
        key = "%stasks" % self.status_string
        return settings.get(section, key) or (
            defaults.defaults[section][key] if required else ""
        )

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.status_string)

    def __str__(self):
        return self.status_string

    def __eq__(self, other):
        return self.status_string == other.status_string

    def __neq__(self, other):
        return self.status_string != other.status_string

    def __bool__(self):
        return True

    def __hash__(self) -> int:
        return hash(self.status_string)


inactive = TaskStatus(
    "inactive",
    _("Inactive tasks"),
    _("Inactive tasks: %d (%d%%)"),
    _("Hide &inactive tasks"),
    _("Show/hide inactive tasks (incomplete tasks without actual start date)"),
)

late = TaskStatus(
    "late",
    _("Late tasks"),
    _("Late tasks: %d (%d%%)"),
    _("Hide &late tasks"),
    _(
        "Show/hide late tasks (inactive tasks with a planned start in the past)"
    ),
)

active = TaskStatus(
    "active",
    _("Active tasks"),
    _("Active tasks: %d (%d%%)"),
    _("Hide &active tasks"),
    _(
        "Show/hide active tasks (incomplete tasks with an actual start date in the past)"
    ),
)

duesoon = TaskStatus(
    "duesoon",
    _("Due soon tasks"),
    _("Due soon tasks: %d (%d%%)"),
    _("Hide &due soon tasks"),
    _(
        "Show/hide due soon tasks (incomplete tasks with a due date in the near future)"
    ),
)

overdue = TaskStatus(
    "overdue",
    _("Overdue tasks"),
    _("Overdue tasks: %d (%d%%)"),
    _("Hide &over due tasks"),
    _(
        "Show/hide over due tasks (incomplete tasks with a due date in the past)"
    ),
)

completed = TaskStatus(
    "completed",
    _("Completed tasks"),
    _("Completed tasks: %d (%d%%)"),
    _("Hide &completed tasks"),
    _("Show/hide completed tasks"),
)
