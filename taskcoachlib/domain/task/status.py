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


class TaskStatus(object):
    def __init__(
        self, statusString, pluralLabel, countLabel, hideMenuText, hideHelpText,
        statusSortPriority=0
    ):
        self.statusString = statusString
        self.pluralLabel = pluralLabel
        self.countLabel = countLabel
        self.hideMenuText = hideMenuText
        self.hideHelpText = hideHelpText
        self.statusSortPriority = statusSortPriority

    # This is only used by uicommands so use default if the user configured 'no bitmap', because we
    # need one for the toolbar...

    def getBitmap(self, settings):
        if settings.get("icon", "%stasks" % self.statusString):
            return settings.get("icon", "%stasks" % self.statusString)
        return defaults.defaults["icon"]["%stasks" % self.statusString]

    def getHideBitmap(self, settings):
        if settings.get("icon", "%stasks" % self.statusString):
            return "%s+cross_red_icon" % settings.get(
                "icon", "%stasks" % self.statusString
            )
        return (
            "%s+cross_red_icon"
            % defaults.defaults["icon"]["%stasks" % self.statusString]
        )

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.statusString)

    def __str__(self):
        return self.statusString

    def __eq__(self, other):
        return self.statusString == other.statusString

    def __neq__(self, other):
        return self.statusString != other.statusString

    def __bool__(self):
        return True

    def __hash__(self) -> int:
        return hash(self.statusString)


inactive = TaskStatus(
    "inactive",
    _("Inactive tasks"),
    _("Inactive tasks: %d (%d%%)"),
    _("Hide &inactive tasks"),
    _("Show/hide inactive tasks (incomplete tasks without actual start date)"),
    statusSortPriority=2,
)

late = TaskStatus(
    "late",
    _("Late tasks"),
    _("Late tasks: %d (%d%%)"),
    _("Hide &late tasks"),
    _(
        "Show/hide late tasks (inactive tasks with a planned start in the past)"
    ),
    statusSortPriority=4,
)

active = TaskStatus(
    "active",
    _("Active tasks"),
    _("Active tasks: %d (%d%%)"),
    _("Hide &active tasks"),
    _(
        "Show/hide active tasks (incomplete tasks with an actual start date in the past)"
    ),
    statusSortPriority=3,
)

duesoon = TaskStatus(
    "duesoon",
    _("Due soon tasks"),
    _("Due soon tasks: %d (%d%%)"),
    _("Hide &due soon tasks"),
    _(
        "Show/hide due soon tasks (incomplete tasks with a due date in the near future)"
    ),
    statusSortPriority=5,
)

overdue = TaskStatus(
    "overdue",
    _("Overdue tasks"),
    _("Overdue tasks: %d (%d%%)"),
    _("Hide &over due tasks"),
    _(
        "Show/hide over due tasks (incomplete tasks with a due date in the past)"
    ),
    statusSortPriority=6,
)

completed = TaskStatus(
    "completed",
    _("Completed tasks"),
    _("Completed tasks: %d (%d%%)"),
    _("Hide &completed tasks"),
    _("Show/hide completed tasks"),
    statusSortPriority=1,
)


def loadSortPrioritiesFromSettings(settings):
    """Load status sort priorities from settings into status singletons."""
    for s in (inactive, late, active, duesoon, overdue, completed):
        key = "%stasks" % s.statusString
        s.statusSortPriority = int(settings.get("statussortpriority", key))
