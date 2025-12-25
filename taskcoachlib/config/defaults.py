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
        "toolbar": "(22, 22)",
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
        "categoryfiltermatchall": "False",
        "weekstart": "monday",  # Start of work week, 'monday' or 'sunday'
        # The next three options are used in the effort dialog to populate the
        # drop down menu with start and stop times.
        "efforthourstart": "8",  # Earliest time, i.e. start of working day
        "efforthourend": "18",  # Last time, i.e. end of working day
        "effortminuteinterval": "15",  # Generate times with this interval
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
        "toolbarperspective": "TaskNew,NewSubItem,TaskNewFromTemplateButton,Separator,Edit,Delete,Separator,TaskMarkInactive,TaskMarkActive,TaskMarkCompleted,Separator,EffortStart,EffortStop,Separator,Spacer,ViewerHideTasks_completed,ViewerHideTasks_inactive,ResetFilter,TaskViewerTreeOrListChoice,Search",
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
        "toolbarperspective": "TaskNew,NewSubItem,TaskNewFromTemplateButton,Separator,Edit,Delete,Separator,TaskMarkInactive,TaskMarkActive,TaskMarkCompleted,Separator,EffortStart,EffortStop,Spacer,ViewerHideTasks_completed,ViewerHideTasks_inactive,ResetFilter,Search",
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
    "categoryviewerintaskeditor": {
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
        "toolbarperspective": "NoteNew,NewSubItem,Separator,Edit,Delete,Spacer,ResetFilter,Search",
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
        "toolbarperspective": "NoteNew,NewSubItem,Separator,Edit,Delete,Spacer,ResetFilter,Search",
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
        "nopoll": "False",
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
        "activetasks": "led_blue_icon",
        "latetasks": "led_purple_icon",
        "completedtasks": "checkmark_green_icon",
        "overduetasks": "led_red_icon",
        "inactivetasks": "led_grey_icon",
        "duesoontasks": "led_orange_icon",
    },
    "editor": {
        "descriptionfont": "",  # Font to use in the desciption field of editors
        "maccheckspelling": "True",
    },
    "os_darwin": {"getmailsubject": "False"},
    "os_linux": {"focustextentry": "True"},
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
        "syncml": "False",
        "iphone": "False",
        "notifier": "Task Coach",
        "minidletime": "0",
        "usesm2": "False",
        "showsmwarning": "True",
        "sayreminder": "False",
        "sdtcspans": "60,120,1440,2880",
        "sdtcspans_effort": "60,120,180,240",
        "decimaltime": "False",
        # New settings should use snake_case naming convention (PEP 8)
    },
    "syncml": {
        "url": "",
        "username": "",
        "preferredsyncmode": "TWO_WAY",
        "verbose": "True",
        "taskdbname": "task",
        "notedbname": "note",
        "synctasks": "True",
        "syncnotes": "True",
        "showwarning": "True",
    },
    "iphone": {
        "password": "",
        "service": "",
        "synccompleted": "True",
        "showlog": "False",
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
}

minimum = {"view": {"taskviewercount": "1"}}
