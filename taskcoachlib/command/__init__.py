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

from .taskCommands import *
from .effortCommands import (
    NewEffortCommand,
    AddEffortCommand,
    DeleteEffortCommand,
    EditTaskCommand,
    EditEffortStartDateTimeCommand,
    EditEffortStopDateTimeCommand,
    EditEffortEntryModeCommand,
)
from .categoryCommands import *
from .categorizableCommands import *
from .noteCommands import *
from .attachmentCommands import *
from .base import (
    CopyCommand,
    DeleteCommand,
    CutCommand,
    PasteCommand,
    PasteAsSubItemCommand,
    EditSubjectCommand,
    EditDescriptionCommand,
    EditIconCommand,
    EditFontCommand,
    EditForegroundColorCommand,
    EditBackgroundColorCommand,
    PasteAsSubItemCommand,
    EditSubjectCommand,
    EditDescriptionCommand,
)
from .clipboard import Clipboard
