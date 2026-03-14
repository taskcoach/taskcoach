"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2012 Nicola Chiapolini <nicola.chiapolini@physik.uzh.ch>
Copyright (C) 2008 Rob McMullen <rob.mcmullen@gmail.com>

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

import wx
from taskcoachlib import meta

# Main toolbar icon sizes (user-selectable via View > Toolbar menu).
# Used by: gui/toolbar.py, gui/menu.py. See also docs/TOOLBAR.md.
MAIN_TOOLBAR_ICON_SIZE_SMALL = 16
MAIN_TOOLBAR_ICON_SIZE_MEDIUM = 22
MAIN_TOOLBAR_ICON_SIZE_LARGE = 32
MAIN_TOOLBAR_ICON_SIZE_DEFAULT = MAIN_TOOLBAR_ICON_SIZE_MEDIUM

defaults = {
    "balloontips": {
        "customizabletoolbars": "True",
        "customizabletoolbars_dnd": "True",
        "filtershiftclick": "True",
        "autosavehint": "True",
        "manualordering": "True",
        "treemanualordering": "True",
        "treechildrenmanualordering": "True",
    },
    "view": {
        "statusbar": "True",
        "toolbar": str((MAIN_TOOLBAR_ICON_SIZE_DEFAULT,) * 2),
        "toolbarperspective": "FileOpen,Print,Separator,EditUndo,EditRedo,Separator,EffortStartButton,EffortStop",
        # Index of the active effort viewer in task editor:
        "effortviewerintaskeditor": "0",
        "taskviewercount": "1",  # Number of task viewers in main window
        "categoryviewercount": "1",  # Number of category viewers in main window
        "noteviewercount": "0",  # Number of note viewers in main window
        "effortviewercount": "0",  # Number of effort viewers in main window
        "effortviewerforselectedtaskscount": "0",
        "squaretaskviewercount": "0",
        "timelineviewercount": "0",
        "calendarviewercount": "0",
        "hierarchicalcalendarviewercount": "0",
        "taskstatsviewercount": "0",
        "taskinterdepsviewercount": "0",  # Number of interdep viewers in main window
        # Language and locale, maybe set externally (e.g. by PortableApps):
        "language": "",
        # Language and locale as set by user via preferences, overrides language:
        "language_set_by_user": "",
        # Date format override: "" = automatic (detect from locale), or explicit format
        # Possible values: "", "YMD-", "MDY/", "DMY/", "DMY.", "YMD/"
        "dateformat": "",
        # Time format override: "24" = 24-hour (default), "12" = 12-hour with AM/PM, "" = automatic
        "timeformat": "24",
        # Decimal separator override: "" = automatic (from locale), "." = period, "," = comma
        "decimal_separator": "",
        # Currency decimal places override: "" = automatic (from locale frac_digits), or "0"/"2"/"3"
        "currency_decimal_places": "",
        "categoryfiltermatchall": "False",
        "weekstart": "monday",  # Start of work week, 'monday' or 'sunday'
        # The next three options are used in the effort dialog to populate the
        # drop down menu with start and stop times.
        "efforthourstart": "8",  # Earliest time, i.e. start of working day
        "efforthourend": "18",  # Last time, i.e. end of working day
        "efforthourend_endofday": "False",  # If True, end of working day = 23:59:59
        "effortminuteinterval": "15",  # Generate minute choices with this interval
        "effortsecondinterval": "15",  # Generate second choices with this interval
        "snoozetimes": "[5, 10, 15, 30, 60, 120, 1440]",
        "defaultsnoozetime": "5",  # Default snooze time
        "replacedefaultsnoozetime": "True",  # Make chosen snooze time the default?
        "perspective": "",  # The layout of the viewers in the main window
        # What to do when changing the planned start date or due date:
        "datestied": "",
        # Default date and times to offer in the task dialog, see preferences for
        # possible values:
        "defaultplannedstartdatetime": "propose_today_currenttime",
        "defaultduedatetime": "propose_tomorrow_endofworkingday",
        "defaultactualstartdatetime": "propose_today_currenttime",
        "defaultcompletiondatetime": "propose_today_currenttime",
        "defaultreminderdatetime": "propose_tomorrow_startofworkingday",
        # Show messages from the developers downloaded from the website:
        "developermessages": "True",
        "lastdevelopermessage": "",
        "descriptionpopups": "True",
    },
    "taskviewer": {
        "title": "",  # User supplied viewer title
        "toolbarperspective": "TaskNew,NewSubItem,TaskNewFromTemplateButton,Separator,Edit,Delete,Separator,TaskMarkInactive,TaskMarkActive,TaskMarkCompleted,Separator,EffortStart,EffortStop,Separator,ViewExpandAll,ViewCollapseAll,Spacer,ViewerHideTasks_completed,ViewerHideTasks_inactive,ResetFilter,TaskViewerTreeOrListChoice,Search",
        "treemode": "True",  # True = tree mode, False = list mode
        "sortby": '["dueDateTime"]',
        "sortbystatusfirst": "True",
        "sortcasesensitive": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "columns": "['plannedStartDateTime', 'dueDateTime']",
        "columnsalwaysvisible": "['subject']",
        "columnwidths": "{'attachments': 28, 'notes': 28, 'ordering': 28}",
        "columnautoresizing": "False",
        "hideinactivetasks": "False",
        "hidelatetasks": "False",
        "hideactivetasks": "False",
        "hideduesoontasks": "False",
        "hideoverduetasks": "False",
        "hidecompletedtasks": "False",
        "hidecompositetasks": "False",
    },
    "taskstatsviewer": {
        "title": "",
        "toolbarperspective": "TaskNew,TaskNewFromTemplateButton,Separator,ViewerPieChartAngle,Spacer,ViewerHideTasks_completed,ViewerHideTasks_inactive,ResetFilter,Search",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "hideinactivetasks": "False",
        "hidelatetasks": "False",
        "hideactivetasks": "False",
        "hideduesoontasks": "False",
        "hideoverduetasks": "False",
        "hidecompletedtasks": "False",
        "hidecompositetasks": "False",
        "piechartangle": "30",
    },
    "taskinterdepsviewer": {
        "title": "",
        "toolbarperspective": "Separator,Spacer,ViewerHideTasks_completed,ViewerHideTasks_inactive,ResetFilter,Search",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "hideinactivetasks": "False",
        "hidelatetasks": "False",
        "hideactivetasks": "False",
        "hideduesoontasks": "False",
        "hideoverduetasks": "False",
        "hidecompletedtasks": "False",
        "hidecompositetasks": "False",
    },
    "prerequisiteviewerintaskeditor": {
        "title": "",  # User supplied viewer title
        "toolbarperspective": "TaskNew,NewSubItem,TaskNewFromTemplateButton,Separator,Edit,Delete,Separator,TaskMarkInactive,TaskMarkActive,TaskMarkCompleted,Separator,EffortStart,EffortStop,Separator,ViewExpandAll,ViewCollapseAll,Spacer,ViewerHideTasks_completed,ViewerHideTasks_inactive,ResetFilter,Search",
        "treemode": "True",  # True = tree mode, False = list mode
        "sortby": '["subject"]',
        "sortbystatusfirst": "True",
        "sortcasesensitive": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "columns": "['prerequisites', 'dependencies', 'plannedStartDateTime', "
        "'dueDateTime']",
        "columnsalwaysvisible": "['subject']",
        "columnwidths": "{'attachments': 28, 'notes': 28}",
        "columnautoresizing": "False",
        "hideinactivetasks": "False",
        "hidelatetasks": "False",
        "hideduesoontasks": "False",
        "hideoverduetasks": "False",
        "hidecompletedtasks": "False",
        "hideactivetasks": "False",
        "hidecompositetasks": "False",
    },
    "squaretaskviewer": {
        "title": "",
        "toolbarperspective": "TaskNew,NewSubItem,TaskNewFromTemplateButton,Separator,Edit,Delete,Separator,TaskMarkInactive,TaskMarkActive,TaskMarkCompleted,Separator,EffortStart,EffortStop,Separator,SquareTaskViewerOrderChoice,Spacer,ViewerHideTasks_completed,ViewerHideTasks_inactive,ResetFilter,Search",
        "sortby": '["budget"]',
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "hideinactivetasks": "False",
        "hidelatetasks": "False",
        "hideactivetasks": "False",
        "hideduesoontasks": "False",
        "hideoverduetasks": "False",
        "hidecompletedtasks": "False",
        "hidecompositetasks": "False",
    },
    "timelineviewer": {
        "title": "",
        "toolbarperspective": "TaskNew,NewSubItem,TaskNewFromTemplateButton,Separator,Edit,Delete,Separator,TaskMarkInactive,TaskMarkActive,TaskMarkCompleted,Separator,EffortStart,EffortStop,Spacer,ViewerHideTasks_completed,ViewerHideTasks_inactive,ResetFilter,Search",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "hideinactivetasks": "False",
        "hidelatetasks": "False",
        "hideduesoontasks": "False",
        "hideoverduetasks": "False",
        "hideactivetasks": "False",
        "hidecompletedtasks": "False",
        "hidecompositetasks": "False",
    },
    "hierarchicalcalendarviewer": {
        "title": "",
        "calendarformat": "0",
        "headerformat": "1",
        "drawnow": "True",
        "todaycolor": "0, 0, 200",
        "toolbarperspective": "TaskNew,NewSubItem,TaskNewFromTemplateButton,Separator,Edit,Delete,Separator,TaskMarkInactive,TaskMarkActive,TaskMarkCompleted,Separator,EffortStart,EffortStop,Separator,HierarchicalCalendarViewerConfigure,HierarchicalCalendarViewerPreviousPeriod,HierarchicalCalendarViewerToday,HierarchicalCalendarViewerNextPeriod,Spacer,ViewerHideTasks_completed,ViewerHideTasks_inactive,ResetFilter,Search",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "hideinactivetasks": "False",
        "hidelatetasks": "False",
        "hideactivetasks": "False",
        "hideduesoontasks": "False",
        "hideoverduetasks": "False",
        "hidecompletedtasks": "False",
        "hidecompositetasks": "False",
        "sortby": '["subject"]',
        "sortcasesensitive": "False",
        "sortbystatusfirst": "True",
    },
    "calendarviewer": {
        "title": "",
        "toolbarperspective": "TaskNew,NewSubItem,TaskNewFromTemplateButton,Separator,Edit,Delete,Separator,TaskMarkInactive,TaskMarkActive,TaskMarkCompleted,Separator,EffortStart,EffortStop,Separator,CalendarViewerConfigure,CalendarViewerPreviousPeriod,CalendarViewerToday,CalendarViewerNextPeriod,Spacer,ViewerHideTasks_completed,ViewerHideTasks_inactive,ResetFilter,Search",
        "viewtype": "1",
        "periodcount": "1",
        "periodwidth": "150",
        "vieworientation": "1",
        "viewdate": "",
        "gradient": "False",
        "shownostart": "False",
        "shownodue": "False",
        "showunplanned": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "hideinactivetasks": "False",
        "hidelatetasks": "False",
        "hideactivetasks": "False",
        "hideduesoontasks": "False",
        "hideoverduetasks": "False",
        "hidecompletedtasks": "False",
        "hidecompositetasks": "False",
        "sortby": '["subject"]',
        "sortcasesensitive": "False",
        "sortbystatusfirst": "True",
        "highlightcolor": "",
        "shownow": "True",
    },
    "categoryviewer": {
        "title": "",
        "toolbarperspective": "CategoryNew,NewSubItem,Separator,Edit,Delete,Separator,ViewExpandAll,ViewCollapseAll,Spacer,ResetFilter,Search",
        "sortby": '["subject"]',
        "sortcasesensitive": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "columns": "[]",
        "columnsalwaysvisible": "['subject']",
        "columnwidths": "{'attachments': 28, 'notes': 28, 'ordering': 28}",
        "columnautoresizing": "False",
    },
    "categoryviewerintaskeditor": {
        "title": "",
        "toolbarperspective": "CategoryNew,NewSubItem,Separator,Edit,Delete,Separator,CategoryCheckAll,CategoryUncheckAll,Separator,ViewExpandAll,ViewCollapseAll,Spacer,ResetFilter,Search",
        "sortby": '["subject"]',
        "sortcasesensitive": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "columns": "[]",
        "columnsalwaysvisible": "['subject']",
        "columnwidths": "{'attachments': 28, 'notes': 28, 'ordering': 28}",
        "columnautoresizing": "False",
    },
    "categoryviewerinnoteeditor": {
        "title": "",
        "toolbarperspective": "CategoryNew,NewSubItem,Separator,Edit,Delete,Spacer,ResetFilter,Search",
        "sortby": '["subject"]',
        "sortcasesensitive": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "columns": "[]",
        "columnsalwaysvisible": "['subject']",
        "columnwidths": "{'attachments': 28, 'notes': 28, 'ordering': 28}",
        "columnautoresizing": "False",
    },
    "noteviewer": {
        "title": "",
        "toolbarperspective": "NoteNew,NewSubItem,Separator,Edit,Delete,Separator,ViewExpandAll,ViewCollapseAll,Spacer,ResetFilter,Search",
        "sortby": '["subject"]',
        "sortcasesensitive": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "columns": "['attachments', 'description', 'creationDateTime', \
                 'modificationDateTime']",
        "columnsalwaysvisible": "['subject']",
        "columnwidths": "{'attachments': 28, 'description': 200, 'ordering': 28}",
        "columnautoresizing": "False",
    },
    "noteviewerintaskeditor": {
        "toolbarperspective": "NoteNew,NewSubItem,Separator,Edit,Delete,Separator,ViewExpandAll,ViewCollapseAll,Spacer,ResetFilter,Search",
        "sortby": '["subject"]',
        "sortcasesensitive": "False",
        "columns": "['attachments', 'description', 'creationDateTime', \
                 'modificationDateTime']",
        "columnsalwaysvisible": "['subject']",
        "columnwidths": "{'attachments': 28, 'description': 200, 'ordering': 28}",
        "columnautoresizing": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
    },
    "noteviewerincategoryeditor": {
        "toolbarperspective": "NoteNew,NewSubItem,Separator,Edit,Delete,Spacer,ResetFilter,Search",
        "sortby": '["subject"]',
        "sortcasesensitive": "False",
        "columns": "['subject']",
        "columnsalwaysvisible": "['subject']",
        "columnwidths": "{'ordering': 28}",
        "columnautoresizing": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
    },
    "noteviewerinattachmenteditor": {
        "toolbarperspective": "NoteNew,NewSubItem,Separator,Edit,Delete,Spacer,ResetFilter,Search",
        "sortby": '["subject"]',
        "sortcasesensitive": "False",
        "columns": "['subject']",
        "columnsalwaysvisible": "['subject']",
        "columnwidths": "{'ordering': 28}",
        "columnautoresizing": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
    },
    "effortviewer": {
        "title": "",
        "toolbarperspective": "EffortNew,Separator,Edit,Delete,Separator,EffortStartForEffort,EffortStop,Separator,EffortViewerAggregationChoice,Spacer,ResetFilter,Search",
        "aggregation": "details",  # 'details' (default), 'day', 'week', or 'month'
        "sortby": '["-period"]',
        "sortcasesensitive": "False",
        "columns": "['description', 'timeSpent']",
        "columnsalwaysvisible": "['period', 'task']",
        "columnwidths": "{'period': 160, 'monday': 70, 'tuesday': 70, "
        "'wednesday': 70, 'thursday': 70, 'friday': 70, "
        "'saturday': 70, 'sunday': 70, 'description': 200}",
        "columnautoresizing": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "round": "0",  # round effort to this number of seconds, 0 = no rounding
        "alwaysroundup": "False",
        "consolidateeffortspertask": "False",
    },
    "effortviewerforselectedtasks": {
        "title": "",
        "toolbarperspective": "EffortNew,Separator,Edit,Delete,Separator,EffortStartForEffort,EffortStop,Separator,EffortViewerAggregationChoice,Spacer,ResetFilter,Search",
        "aggregation": "details",  # 'details' (default), 'day', 'week', or 'month'
        "sortby": '["-period"]',
        "sortcasesensitive": "False",
        "columns": "['description', 'timeSpent']",
        "columnsalwaysvisible": "['period', 'task']",
        "columnwidths": "{'period': 160, 'monday': 70, 'tuesday': 70, "
        "'wednesday': 70, 'thursday': 70, 'friday': 70, "
        "'saturday': 70, 'sunday': 70, 'description': 200}",
        "columnautoresizing": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "round": "0",  # round effort to this number of seconds, 0 = no rounding
        "alwaysroundup": "False",
        "consolidateeffortspertask": "False",
    },
    "effortviewerintaskeditor": {
        "toolbarperspective": "EffortNew,Separator,Edit,Delete,Separator,EffortStartForEffort,EffortStop,Separator,EffortViewerAggregationChoice,Spacer,ResetFilter,Search",
        "aggregation": "details",  # 'details' (default), 'day', 'week', or 'month'
        "sortby": '["-period"]',
        "sortcasesensitive": "False",
        "columns": "['description', 'timeSpent']",
        "columnsalwaysvisible": "['period', 'task']",
        "columnwidths": "{'period': 160, 'monday': 70, 'tuesday': 70, "
        "'wednesday': 70, 'thursday': 70, 'friday': 70, "
        "'saturday': 70, 'sunday': 70, 'description': 200}",
        "columnautoresizing": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "round": "0",  # round effort to this number of seconds, 0 = no rounding
        "alwaysroundup": "False",
        "consolidateeffortspertask": "False",
    },
    "attachmentviewer": {
        "title": "",
        "toolbarperspective": "AttachmentNew,Separator,Edit,Delete,Separator,AttachmentOpen,Spacer,Search",
        "sortby": '["subject"]',
        "sortcasesensitive": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "columns": "[]",
        "columnsalwaysvisible": "['type', 'subject']",
        "columnwidths": "{'notes': 28, 'type': 28}",
        "columnautoresizing": "False",
    },
    "attachmentviewerintaskeditor": {
        "title": "",
        "toolbarperspective": "AttachmentNew,Separator,Edit,Delete,Separator,AttachmentOpen,Spacer,Search",
        "sortby": '["subject"]',
        "sortcasesensitive": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "columns": "[]",
        "columnsalwaysvisible": "['type', 'subject']",
        "columnwidths": "{'notes': 28, 'type': 28}",
        "columnautoresizing": "False",
    },
    "attachmentviewerinnoteeditor": {
        "title": "",
        "toolbarperspective": "AttachmentNew,Separator,Edit,Delete,Separator,AttachmentOpen,Spacer,Search",
        "sortby": '["subject"]',
        "sortcasesensitive": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "columns": "[]",
        "columnsalwaysvisible": "['type', 'subject']",
        "columnwidths": "{'notes': 28, 'type': 28}",
        "columnautoresizing": "False",
    },
    "attachmentviewerincategoryeditor": {
        "title": "",
        "toolbarperspective": "AttachmentNew,Separator,Edit,Delete,Separator,AttachmentOpen,Spacer,Search",
        "sortby": '["subject"]',
        "sortcasesensitive": "False",
        "searchfilterstring": "",
        "searchfiltermatchcase": "False",
        "searchfilterincludesubitems": "False",
        "searchdescription": "False",
        "regularexpression": "False",
        "columns": "[]",
        "columnsalwaysvisible": "['type', 'subject']",
        "columnwidths": "{'notes': 28, 'type': 28}",
        "columnautoresizing": "False",
    },
    "window": {
        "size": "(900, 500)",  # Default size of the main window
        "position": "(-1, -1)",  # Position of the main window, undefined by default
        "monitor_index": "-1",  # Monitor the window was on, -1 means unknown/default
        "iconized": "False",  # Don't start up iconized by default
        "maximized": "False",  # Don't start up maximized by default
        # Possible strticonized values: 'Never', 'Always', 'WhenClosedIconized'
        "starticonized": "WhenClosedIconized",
        "hidewheniconized": "False",  # Don't hide the window from the task bar
        "hidewhenclosed": "False",  # Close window quits the application
        "tips": "True",  # Show tips after starting up
        "tipsindex": "0",  # Start at the first tip
        "blinktaskbariconwhentrackingeffort": "True",
        # Theme: 'automatic' (detect from system), 'light', or 'dark'
        "theme": "automatic",
        "hoverlinewidth": "1",
    },
    "effortdialog": {
        "size": "(-1, -1)",  # Size of the dialogs, calculated by default
        "position": "(-1, -1)",  # Position of the dialog, undefined by default
        "parent_offset": "(-1, -1)",  # Offset from parent window for multi-monitor support
        "maximized": "False",  # Don't open the dialog maximized by default
    },
    "file": {
        "recentfiles": "[]",
        "maxrecentfiles": "9",
        "lastfile": "",
        "autosave": "True",
        "autoload": "False",
        # Formats to automatically import from, only "Todo.txt" supported at this
        # time:
        "autoimport": "[]",
        # Formats to automatically export to, only "Todo.txt" supported at this
        # time:
        "autoexport": "[]",
        "fspoll": "False",  # Use polling instead of watchdog for file monitoring
        "saveinifileinprogramdir": "False",
        "attachmentbase": "",
        "lastattachmentpath": "",
        "inifileloaded": "True",
        "inifileloaderror": "",
    },
    "fgcolor": {
        "activetasks": "(0, 0, 0, 255)",
        "latetasks": "(160, 32, 240, 255)",
        "completedtasks": "(0, 255, 0, 255)",
        "overduetasks": "(255, 0, 0, 255)",
        "inactivetasks": "(192, 192, 192, 255)",
        "duesoontasks": "(255, 128, 0, 255)",
    },
    "bgcolor": {
        "activetasks": "(255, 255, 255, 255)",
        "latetasks": "(255, 255, 255, 255)",
        "completedtasks": "(255, 255, 255, 255)",
        "overduetasks": "(255, 255, 255, 255)",
        "inactivetasks": "(255, 255, 255, 255)",
        "duesoontasks": "(255, 255, 255, 255)",
    },
    "font": {
        "activetasks": "",
        "latetasks": "",
        "completedtasks": "",
        "overduetasks": "",
        "inactivetasks": "",
        "duesoontasks": "",
    },
    "icon": {
        "activetasks": "nuvola_actions_ledblue",
        "latetasks": "nuvola_actions_ledpurple",
        "completedtasks": "nuvola_actions_ok",
        "overduetasks": "nuvola_actions_ledred",
        "inactivetasks": "taskcoach_actions_led_grey_icon",
        "duesoontasks": "nuvola_actions_ledorange",
        "legacystatusicons": "False",
        "iconsize": "16",
    },
    "fgcolor_dark": {
        "activetasks": "(255, 255, 255, 255)",
        "latetasks": "(200, 160, 255, 255)",
        "completedtasks": "(100, 255, 100, 255)",
        "overduetasks": "(255, 100, 100, 255)",
        "inactivetasks": "(140, 140, 140, 255)",
        "duesoontasks": "(255, 180, 80, 255)",
    },
    "bgcolor_dark": {
        "activetasks": "(40, 40, 40, 255)",
        "latetasks": "(40, 40, 40, 255)",
        "completedtasks": "(40, 40, 40, 255)",
        "overduetasks": "(40, 40, 40, 255)",
        "inactivetasks": "(40, 40, 40, 255)",
        "duesoontasks": "(40, 40, 40, 255)",
    },
    "font_dark": {
        "activetasks": "",
        "latetasks": "",
        "completedtasks": "",
        "overduetasks": "",
        "inactivetasks": "",
        "duesoontasks": "",
    },
    "icon_dark": {
        "activetasks": "nuvola_actions_ledblue",
        "latetasks": "nuvola_actions_ledpurple",
        "completedtasks": "nuvola_actions_ok",
        "overduetasks": "nuvola_actions_ledred",
        "inactivetasks": "taskcoach_actions_led_grey_icon",
        "duesoontasks": "nuvola_actions_ledorange",
    },
    "statussortpriority": {
        "inactivetasks": "2",
        "latetasks": "4",
        "activetasks": "3",
        "duesoontasks": "5",
        "overduetasks": "6",
        "completedtasks": "1",
    },
    "version": {
        "python": "",  # Filled in by the Settings class when saving the settings
        "wxpython": "",  # Idem
        "pythonfrozen": "",  # Idem
        "current": meta.data.version,
        "notified": meta.data.version,
        "notify": "True",
    },
    "behavior": {
        "markparentcompletedwhenallchildrencompleted": "False",
        "duesoonhours": "24",  # When a task is considered to be "due soon"
    },
    "feature": {
        "minidletime": "0",
        "reminder_sound": "gentle-chime",  # Key from taskcoachlib.sounds.SOUNDS
        "sayreminder": "False",
        "task_duration_presets": "60,120,1440,2880",  # Minutes: 1h, 2h, 1 day, 2 days
        "effort_duration_presets": "300,900,1800,3600,7200",  # Seconds: 5m, 15m, 30m, 1h, 2h
        # New settings should use snake_case naming convention (PEP 8)
    },
    "printer": {
        "margin_left": "0",
        "margin_top": "0",
        "margin_bottom": "0",
        "margin_right": "0",
        "paper_id": "0",
        "orientation": str(wx.PORTRAIT),
    },
    "export": {
        "html_selectiononly": "False",
        "html_separatecss": "False",
        "csv_selectiononly": "False",
        "csv_separatedateandtimecolumns": "False",
        "ical_selectiononly": "False",
        "todotxt_selectiononly": "False",
    },
    "spellcheck": {
        # Enable spell checking for subject and description fields
        "enabled": "True",
        # Language code for spell checking (empty = auto-detect from system locale)
        # Examples: "en_US", "en_GB", "de_DE", "fr_FR", "es_ES"
        "language": "",
    },
    "calendar_light": {
        "weekday_header_bg": "(192, 192, 192, 255)",
        "weekday_header_fg": "(0, 0, 255, 255)",
        "weekend_day_fg": "(255, 0, 0, 255)",
        "today_border": "(255, 0, 0, 255)",
        "other_month_bg": "(211, 211, 211, 255)",
        "other_month_bg_system": "True",
    },
    "calendar_dark": {
        "weekday_header_bg": "(75, 75, 75, 255)",
        "weekday_header_fg": "(100, 160, 255, 255)",
        "weekend_day_fg": "(255, 100, 100, 255)",
        "today_border": "(255, 100, 100, 255)",
        "other_month_bg": "(55, 55, 55, 255)",
        "other_month_bg_system": "False",
    },
    "spellcheck_light": {
        "squiggle_color": "(255, 0, 0, 255)",
    },
    "spellcheck_dark": {
        "squiggle_color": "(255, 80, 80, 255)",
    },
    "iconpicker": {
        # Theme visibility in icon picker (legacy always enabled)
        "theme_nuvola": "True",
        "theme_oxygen": "True",
        "theme_papirus": "True",
        "theme_breeze": "True",
        "theme_noto_emoji": "True",
        "theme_taskcoach": "True",
        # Search options
        "search_include_theme": "False",
        "search_include_context": "False",
    },
}

minimum = {"view": {"taskviewercount": "1"}}
