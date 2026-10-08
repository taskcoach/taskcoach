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

from taskcoachlib import patterns
from taskcoachlib.config import settings
from taskcoachlib.domain import category, effort, note, task

# Each "(All)" choice of the export dialogs: the file's items, the
# sorter of the type's views and the settings section they start from
_TYPES = {
    "ALL_TASKS": (
        lambda task_file: task_file.tasks(),
        task.sorter.Sorter,
        "taskviewer",
    ),
    "ALL_EFFORTS": (
        lambda task_file: task_file.efforts(),
        effort.EffortSorter,
        "effortviewer",
    ),
    "ALL_CATEGORIES": (
        lambda task_file: task_file.categories(),
        category.CategorySorter,
        "categoryviewer",
    ),
    "ALL_NOTES": (
        lambda task_file: task_file.notes(),
        note.NoteSorter,
        "noteviewer",
    ),
}

# The sorters' options and the view settings that hold them
_SORT_OPTIONS = dict(
    sortBy="sortby",
    sortCaseSensitive="sortcasesensitive",
    sortByTaskStatusFirst="sortbystatusfirst",
)


def all_items(task_file, marker):
    """Every item of the type an "(All)" choice names, in one list
    ordered as a new view of the type orders it: the file holds them
    in no order."""
    if marker not in _TYPES:
        return []
    items, sorter_class, section = _TYPES[marker]
    defaults = settings.template(section)
    options = {
        name: settings.default(section, option)
        for name, option in _SORT_OPTIONS.items()
        if option in defaults
    }
    # Over a copy: detaching a sorter detaches the list it sorts
    sorter = sorter_class(patterns.ObservableList(items(task_file)), **options)
    try:
        return list(sorter)
    finally:
        sorter.detach()
