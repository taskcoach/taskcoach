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

from .notebook import Notebook, BookPage
from .frame import AuiManagedFrameWithDynamicCenterPane
from .dialog import Dialog, NotebookDialog, HTMLDialog, AttachmentSelector
from .itemctrl import Column
from .listctrl import VirtualListCtrl
from .checklistbox import CheckListBox
from .treectrl import CheckTreeCtrl, TreeListCtrl
try:
    from .tcsquaremap import TcSquareMap
except ImportError:
    TcSquareMap = None  # squaremap not installed
from .timeline import Timeline
from .datectrl import DateTimeCtrl, TimeEntry
from .textctrl import (
    SingleLineTextCtrl,
    MultiLineTextCtrl,
    StaticTextWithToolTip,
)
from .panel import PanelWithBoxSizer, BoxWithFlexGridSizer, BoxWithBoxSizer
from .searchctrl import SearchCtrl
from .spinctrl import SpinCtrl
from .tooltip import ToolTipMixin, SimpleToolTip
from .dirchooser import DirectoryChooser
from .fontpicker import FontPickerCtrl
from .syncmlwarning import SyncMLWarningDialog
from .calendarwidget import Calendar
from .calendarconfig import CalendarConfigDialog
from .password import GetPassword
from .hcalendar import HierarchicalCalendar
from .hcalendarconfig import HierarchicalCalendarConfigDialog
from . import masked
from wx.lib import sized_controls
