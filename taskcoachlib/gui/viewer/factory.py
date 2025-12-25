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

from taskcoachlib import operating_system

from . import effort
from . import task
from . import category
from . import note


def viewerTypes():
    """Return the available viewer types, using the names as used in the
    settings."""
    types = [
        "timelineviewer",
        "taskviewer",
        "taskstatsviewer",
        "noteviewer",
        "categoryviewer",
        "effortviewer",
        "calendarviewer",
        "hierarchicalcalendarviewer",
        "effortviewerforselectedtasks",
    ]
    try:
        import squaremap
    except ImportError:
        pass
    else:
        types.append("squaretaskviewer")
    try:
        import igraph
    except ImportError:
        pass
    else:
        types.append("taskinterdepsviewer")
    return tuple(types)


class addViewers(object):  # pylint: disable=C0103, R0903
    """addViewers is a class masquerading as a method. It's a class because
    that makes it easier to split the work over different methods that
    use the same instance variables."""

    floating = False  # Start viewers floating? Not when restoring layout

    def __init__(self, viewer_container, task_file, settings):
        self.__viewer_container = viewer_container
        self.__settings = settings
        self.__viewer_init_args = (
            viewer_container.containerWidget,
            task_file,
            settings,
        )
        self.__add_all_viewers()

    def __add_all_viewers(self):
        """Open viewers as saved previously in the settings."""
        self.__add_viewers(task.TaskViewer)
        self.__add_viewers(task.TaskStatsViewer)
        try:
            import squaremap
        except ImportError:
            pass
        else:
            self.__add_viewers(task.SquareTaskViewer)
        self.__add_viewers(task.TimelineViewer)
        self.__add_viewers(task.CalendarViewer)
        self.__add_viewers(task.HierarchicalCalendarViewer)
        try:
            import igraph
        except ImportError:
            pass
        else:
            self.__add_viewers(task.TaskInterdepsViewer)
        self.__add_viewers(effort.EffortViewer)
        self.__add_viewers(effort.EffortViewerForSelectedTasks)
        self.__add_viewers(category.CategoryViewer)
        self.__add_viewers(note.NoteViewer)

    def __add_viewers(self, viewer_class):
        """Open viewers of the specified viewer class as saved previously in
        the settings."""
        number_of_viewers_to_add = self._number_of_viewers_to_add(viewer_class)
        for _ in range(number_of_viewers_to_add):
            viewer_instance = viewer_class(
                *self.__viewer_init_args, **self._viewer_kwargs(viewer_class)
            )
            self.__viewer_container.addViewer(
                viewer_instance, floating=self.floating
            )

    def _number_of_viewers_to_add(self, viewer_class):
        """Return the number of viewers of the specified viewer class the
        user has opened previously."""
        return self.__settings.getint(
            "view", viewer_class.__name__.lower() + "count"
        )

    def _viewer_kwargs(self, viewer_class):  # pylint: disable=R0201
        """Return the keyword arguments to be passed to the viewer
        initializer."""
        return (
            dict(viewerContainer=self.__viewer_container)
            if issubclass(viewer_class, effort.EffortViewerForSelectedTasks)
            else dict()
        )


class addOneViewer(addViewers):  # pylint: disable=C0103, R0903
    """addOneViewer is a class masquerading as a method to add one viewer
    of a specified viewer class."""

    floating = True  # Start viewer floating? Yes when opening a new viewer

    def __init__(
        self, viewer_container, task_file, settings, viewer_class, **kwargs
    ):
        self.__viewer_class = viewer_class
        self.__kwargs = kwargs
        super().__init__(viewer_container, task_file, settings)

    def _number_of_viewers_to_add(self, viewer_class):
        return 1 if viewer_class == self.__viewer_class else 0

    def _viewer_kwargs(self, viewer_class):
        kwargs = super()._viewer_kwargs(viewer_class)
        kwargs.update(self.__kwargs)
        return kwargs
