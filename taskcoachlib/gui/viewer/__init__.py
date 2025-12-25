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

from .task import (
    TaskViewer,
    TaskStatsViewer,
    CheckableTaskViewer,
    TimelineViewer,
    CalendarViewer,
    HierarchicalCalendarViewer,
)

# SquareTaskViewer requires optional squaremap dependency
try:
    from .task import SquareTaskViewer
except ImportError:
    SquareTaskViewer = None
from .category import CategoryViewer, BaseCategoryViewer
from .effort import EffortViewer, EffortViewerForSelectedTasks
from .note import NoteViewer, BaseNoteViewer
from .attachment import AttachmentViewer
from .container import ViewerContainer
from .factory import viewerTypes, addViewers, addOneViewer

from taskcoachlib import operating_system

try:
    import igraph
except ImportError:
    pass
else:
    from .task import TaskInterdepsViewer
