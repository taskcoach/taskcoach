# -*- coding: utf-8 -*-

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

from changetypes import *

releases = [
    Release(
        "1.6.1.72",
        "December 23, 2025",
        summary="""This release improves the effort editor layout.""",
        bugsFixed=[
            Bugv2("""Fix warning message not fully visible in effort editor when
start time is later than stop time. The warning text was truncated until the
window was resized because the StaticText control was created with zero size."""),
            Bugv2("""Use default sizer flags for start/stop date-time entries
in effort editor for proper alignment and resize behavior."""),
            Bugv2("""Suppress wxPyDeprecationWarning messages from wx.lib.combotreebox."""),
        ],
        featuresAdded=[
            Feature("""Description text box in effort editor now spans full width
and expands with the window. Removed redundant "Description" label."""),
        ],
    ),
    Release(
        "1.6.1.71",
        "December 23, 2025",
        summary="""This release fixes task drag-and-drop functionality.""",
        bugsFixed=[
            Bugv2("""Fix task drag-and-drop to restore hierarchical task reorganization.
Dragging a task onto another task makes it a child. Dragging anywhere else,
including outside the window, moves the task to the root level. Dragging onto
prerequisites/dependencies columns sets task relationships (paperclip cursor)."""),
            Bugv2("""Fix drag image ghosting and highlight flickering during drag."""),
        ],
        featuresAdded=[
            Feature("""Auto-expand parent task when a child task is dropped onto it."""),
        ],
    ),
    Release(
        "1.5.0",
        "August ??, 2014",
        summary="""This is a major release.""",
        bugsFixed=[
            Bugv2("""Fix exception in HTML export."""),
        ],
    ),
    Release(
        "1.4.7",
        "September 5, 2020",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2(
                """Expand recurrence frequency and max count dialog entries (contributed by Alexander Bliznyuk)"""
            ),
        ],
    ),
    Release(
        "1.4.6",
        "April 27, 2019",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2(
                """Workaround for an underlying wxPython limitation we ran into.
After some time Task Coach would exhibit various symptoms because of an
exception in the event loop."""
            ),
        ],
    ),
    Release(
        "1.4.5",
        "March 24, 2019",
        summary="""This is a mixed feature and bugfix release.""",
        bugsFixed=[
            Bugv2("""Fix an exception that would fill up the log on Linux"""),
        ],
        featuresAdded=[
            Feature("""All Ubuntu versions since precise have now a PPA"""),
        ],
    ),
    Release(
        "1.4.4",
        "December 2, 2018",
        summary="""This is a mixed feature and bugfix release.""",
        bugsFixed=[
            Bugv2(
                """TaskCoach would not start on Fedora 23 using LXDE. This probably
concerns other distributions as well."""
            ),
            Bugv2("""Reminders would fire randomly or not at all."""),
        ],
        featuresAdded=[
            Feature(
                """Add a viewer for task dependencies based on igraph (contributed
by Matthias Tafelmeier)"""
            ),
            Feature(
                """Per-task effort total time consolidation, patch provided by rogerdc@gmail.com"""
            ),
            Feature(
                """Add a viewer for task dependencies based on igraph (contributed
by Matthias Tafelmeier). Not available on all platforms."""
            ),
        ],
        dependenciesChanged=[
            Dependency(
                """Task Coach now uses Mercurial for version control. This
only affects you if you want to develop or use Task Coach source code."""
            ),
        ],
    ),
    Release(
        "1.4.3",
        "January 31, 2016",
        summary="""This is a mixed feature and bugfix release.""",
        featuresAdded=[
            Feature("""Finnish translation fixed and enabled."""),
            Feature(
                """The shortcut to delete tasks is now Ctrl+DEL instead
of just DEL."""
            ),
        ],
        bugsFixed=[
            Bugv2(
                """Fix excessive CPU usage on Linux when smart filesystem monitoring is
enabled."""
            ),
            Bugv2("""Fix attachment opening on some Linux distros.""", "1613"),
        ],
    ),
    Release(
        "1.4.2",
        "January 31, 2015",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2("""Also avoid locking in an ownCloud folder."""),
            Bugv2(
                """Avoid a crash when files with badly encoded names are
in the same directory as the task file."""
            ),
            Bugv2("""Avoid data loss in some rare situations"""),
        ],
    ),
    Release(
        "1.4.1",
        "September 14, 2014",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2(
                """Increase taskbar icon size on Linux to avoid dead places.""",
                "1536",
            ),
            Bugv2(
                """Display time spent in decimal format in task viewer if the
option is set.""",
                "1534",
            ),
            Bugv2(
                """Fix todo.txt export when dates have a year < 1900""", "1541"
            ),
            Bugv2("""Avoid locking in Dropbox folder on Windows.""", "1540"),
            Bugv2(
                """Backup and save would fail if the path to the user's home contained
a non-ASCII character""",
                "1547",
                "1546",
            ),
            Bugv2("""Fix stop effort tooltip.""", "1537"),
        ],
    ),
    Release(
        "1.4.0",
        "July 3, 2014",
        summary="""This is a major feature release.""",
        featuresAdded=[
            Feature(
                """A task file can now be open by several instances
of Task Coach, allowing several users to work on the same file.""",
                "http://taskcoach.uservoice.com/forums/26465-desktop-version-windows-linux-mac-of-task-coach/suggestions/288999-enable-multi-user-task-management",
            ),
            Feature("""Backups are now always enabled."""),
        ],
        bugsFixed=[
            Bugv2("""Fix tooltips on notes.""", "1525"),
            Bugv2("""Fix sort order indication in viewer columns.""", "1527"),
            Bugv2(
                """Don't crash at startup if the locale is not supported.""",
                "1528",
            ),
        ],
    ),
    Release(
        "1.3.41",
        "June 22, 2014",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bugv2(
                """Fix a crash at startup on Linux when using some
window managers that don't set the SESSION_MANAGER environment
variable."""
            ),
            Bugv2("""Bring back effort tooltips."""),
            Bugv2(
                """Fix positionning of baloon tips when moving the
window from one display to another.""",
                "1522",
            ),
            Bugv2(
                """Fix for non-ASCII e-mail subjects without encoding
specification""",
                "1523",
            ),
        ],
        featuresAdded=[
            Feature("""Bring back the option to disable tooltips."""),
        ],
    ),
    Release(
        "1.3.40",
        "May 25, 2014",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bugv2("""Remove a debug trace in DnD code."""),
            Bugv2(
                '''"Effort for one task" becomes "Effort for
selected task(s)"''',
                "1474",
                "1520",
            ),
            Bugv2(
                """Fix an occasional "AlreadyCalledError" when iPhone
sync is enabled."""
            ),
        ],
        featuresAdded=[
            Feature(
                """Add an "add note to selected task" button in
the task toolbar; patch from Manab Chetia"""
            ),
        ],
    ),
    Release(
        "1.3.39",
        "May 18, 2014",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bugv2(
                """Some tabs would come up blank when the editor was in
multi-notebook mode.""",
                "1512",
            ),
            Bugv2(
                """In hierarchical calendar, when hitting Ctrl-A or
Shift-clicking a parent task, only select visible tasks."""
            ),
            Bugv2("""Fix a number of SyncML-related bugs."""),
            Bugv2(
                """Fix the "cannot create a file that exists" problem when
saving.""",
                "1517",
            ),
            Bugv2(
                """Fix an error introduced in 1.3.38 related to tips.""",
                "1518",
            ),
            Bugv2(
                """Hopefully fix a session-related bug on Windows""", "1516"
            ),
        ],
        featuresAdded=[
            Feature("""SyncML: add support for Horde-based servers."""),
            Feature(
                """All sort criterion are now persisted between
sessions.""",
                "http://taskcoach.uservoice.com/forums/26465-desktop-version-windows-linux-mac-of-task-coach/suggestions/289031-better-control-over-task-order",
            ),
        ],
    ),
    Release(
        "1.3.38",
        "April 21, 2014",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bugv2(
                """Code signature would become invalid on OSX after the
first run.""",
                "1506",
            ),
            Bugv2(
                """Task Coach wouldn't actually stop with older versions
of Twisted (<11).""",
                "1505",
            ),
            Bugv2("""Fix Todo.txt export""", "1274"),
            Bugv2("""Performance improvements."""),
            Bugv2("""In some circumstances, balloon tips would not close."""),
            Bugv2("""Locking would fail on SSHFS""", "1509"),
            Bugv2("""Fix CSV export for some setups.""", "1510"),
        ],
        featuresAdded=[
            Feature(
                """Always use "/" as path separator in relative attachment
file names.""",
                "https://taskcoach.uservoice.com/admin/forums/26465-desktop-version-windows-linux-mac-of-task-coach/suggestions/5721924-use-slash-instead-backslash-on-attachment-file-pat",
            ),
            Feature("""New hierarchical calendar viewer."""),
            Feature("""Efforts and notes are always enabled."""),
            Feature(
                """Display categories in tooltip.""",
                "https://taskcoach.uservoice.com/admin/forums/26465-desktop-version-windows-linux-mac-of-task-coach/suggestions/5727692-tooltips-for-grid-cells-with-too-long-contents-to",
            ),
            Feature("""The tooltip is now always enabled."""),
            Feature(
                """Manual reordering of tasks, categories and notes.""",
                "http://taskcoach.uservoice.com/forums/26465-desktop-version-windows-linux-mac-of-task-coach/suggestions/289031-better-control-over-task-order",
            ),
        ],
        dependenciesChanged=[
            Dependency("""Minimal Twisted version is now 10.0.""")
        ],
    ),
    Release(
        "1.3.37",
        "March 29, 2014",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bugv2("""Fix a crash at startup on Lucid.""", "1496"),
            Bugv2(
                """Behave like regular OS X apps with regards to
minimization and foreground behavior.""",
                "1500",
            ),
            Bugv2("""Fix idle time notification.""", "1503"),
        ],
        featuresAdded=[
            Feature(
                """Add an option to render efforts in decimal (patch
from Tom Monaco).""",
                "https://taskcoach.uservoice.com/admin/forums/26465-desktop-version-windows-linux-mac-of-task-coach/suggestions/739042-allow-display-of-effort-in-decimal-dd-dd-as-wel",
            ),
            Feature("""Improved import/export of Todo.txt"""),
            Feature(
                """Custom attributes for mailing tasks/categories/etc""",
                "https://taskcoach.uservoice.com/admin/forums/26465-desktop-version-windows-linux-mac-of-task-coach/suggestions/5342642-embeded-command-capability",
            ),
        ],
        dependenciesChanged=[
            Dependency("""Task Coach now depends on Twisted.""")
        ],
    ),
    Release(
        "1.3.36",
        "February 16, 2014",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2(
                """Prerequisites modification would not work.""",
                "1480",
                "1486",
                "1495",
            ),
            Bugv2(
                """LC_TIME would not be honored if set independently""", "1483"
            ),
            Bugv2(
                """Disable translations that are not at least 90%% complete."""
            ),
            Bugv2(
                """Do something a little more intuitive when editing efforts
in aggregated mode.""",
                "1485",
            ),
            Bugv2("""Fix a resource leak on Windows.""", "1488"),
            Bugv2(
                """Fix a crash on Mint when synchronizing with an iPhone
if the password is not set.""",
                "1487",
            ),
            Bugv2(
                """Show and bring minimized window to front on simple click in
the dock (OS X)""",
                "1490",
            ),
            Bugv2("""Disable dock icon ticking on Mavericks.""", "1489"),
            Bugv2(
                """Fix line ending problem when importing from CSV on
Mac/Linux""",
                "1493",
            ),
            Bugv2(
                """Delete .txt files as well when overwriting a task
file.""",
                "1274",
            ),
        ],
    ),
    Release(
        "1.3.35",
        "January 4, 2014",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2(
                """The task editor would not open if the user's date
format didn't include the year."""
            ),
            Bugv2(
                """Unsetting an exclusive category or its parent would
not work.""",
                "1475",
            ),
            Bugv2(
                """Remove file:// URL scheme from filenames dropped
from Nautilus."""
            ),
            Bugv2(
                """When exporting tasks to HTML or CSV, sort notes
alphabetically.""",
                "1477",
            ),
            Bugv2(
                """Sending a task by e-mail would not work on
XFCE 4.10."""
            ),
            Bugv2("""Fix AttributeError problem""", "1479"),
        ],
    ),
    Release(
        "1.3.34",
        "November 24, 2013",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2(
                """Silence the AttributeError problem in PyPubSub.""", "1456"
            ),
            Bugv2(
                """Fix some problems when saving the task file to
a Dropbox folder."""
            ),
            Bugv2("""Performance improvement when reading the task file."""),
            Bugv2(
                """Split date and time when exporting efforts to
CSV.""",
                "1472",
            ),
        ],
    ),
    Release(
        "1.3.33",
        "October 13, 2013",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2("""Fix budget entry.""", "1458"),
            Bugv2(
                """The search controls would not remember the previous
search string on launch, but the view would be filtered anyway."""
            ),
            Bugv2(
                """Fix date picker on locales that have non-ASCII
month/day abbreviations.""",
                "1463",
            ),
            Bugv2(
                """Fix position of text in subject entry on Windows.""", "1464"
            ),
            Bugv2(
                """When automatic import and export to ToDo.txt is
enabled, one could not delete tasks or change some task dates""",
                "1446",
            ),
        ],
    ),
    Release(
        "1.3.32",
        "August 28, 2013",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2(
                """Don't prevent shutdown on Windows if the minimize on
close option is set."""
            ),
            Bugv2(
                """Prevent a PyGTK warning on recent Linux distributions.""",
                "1435",
            ),
            Bugv2(
                """Fix main toolbar shrinking when resizing a viewer.""",
                "1431",
            ),
            Bugv2("""Improve performance when tracking effort.""", "1442"),
            Bugv2("""Prevent TypeError in date selection widget.""", "1445"),
            Bugv2("""Fix initial tab when creating new items"""),
            Bugv2("""Fix undo/redo in text controls on OS X.""", "1436"),
            Bugv2(
                """Fix loss of description edits when closing/quitting while
editors are still open.""",
                "1437",
            ),
            Bugv2(
                """Fix strange Escape behavior on multiple open editors
on OS X.""",
                "1438",
            ),
            Bugv2("""Fix German translation.""", "1448"),
            Bugv2(
                """"New note with selected categories" would create a new
category.""",
                "1447",
            ),
            Bugv2("""Fix search issue when editing the toolbar.""", "1449"),
            Bugv2("""Fix note creation in editor windows.""", "1451"),
            Bugv2(
                """Fix opening preferences dialog when the end of work day
is set to 24."""
            ),
        ],
    ),
    Release(
        "1.3.31",
        "July 29, 2013",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2(
                """Fix crash at startup on Ubuntu 13 if python-apscheduler
is installed.""",
                "1428",
            ),
            Bugv2(
                """Use the "Suggests" mechanism instead of "Recommends" for
the Debian package (python-kde4).""",
                "1430",
            ),
            Bugv2("""Handle short date formats with weekday"""),
            Bugv2(
                """When adding a viewer, the main toolbar would shrink.""",
                "1431",
            ),
            Bugv2(
                """Fix an error when the user types a numeric value in
the AM/PM field of the date/time picker.""",
                "1425",
            ),
            Bugv2(
                """Don't open floating viewers on the top-left corner of
the screen""",
                "1432",
                "1349",
            ),
            Bugv2(
                """Add a hint that the task file needs to be saved in the
main window title.""",
                "1434",
            ),
        ],
    ),
    Release(
        "1.3.30",
        "July 7, 2013",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bugv2(
                """Working day start hour would be reset to 0 every time
preferences are opened.""",
                "1418",
            ),
            Bugv2(
                """Fix the ICC warning with recent versions of libpng.""",
                "1422",
            ),
            Bugv2("""Fix path to log file.""", "1350"),
            Bugv2(
                """Total duration of efforts is the sum of rounded durations,
not the rounded sum of durations.""",
                "1426",
            ),
        ],
        dependenciesChanged=[
            Dependency("""The minimal version of Python is back to 2.6."""),
            Dependency(
                """On Linux, Task Coach does not depend on KDE any more,
but it is recommended."""
            ),
        ],
        featuresAdded=[
            Feature(
                """Display effort statistics in the status bar (patch
from Ivan Romanov).""",
                "https://taskcoach.uservoice.com/admin/forums/26465-desktop-version-windows-linux-mac-of-task-coach/suggestions/606269-section-in-status-bar-for-calculated-information-a",
            ),  # Where the hell do they hide short URLs ?
        ],
    ),
    Release(
        "1.3.29",
        "April 14, 2013",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bugv2("""Fix password entry on Windows.""", "1410"),
            Bugv2("""Fix category filter menu on Windows 7""", "1281"),
        ],
        featuresAdded=[
            Feature(
                """Display a few days of previous and next month in
the calendar popup."""
            ),
        ],
    ),
    Release(
        "1.3.28",
        "March 24, 2013",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2("""Fix a console warning on Ubuntu 64 bits.""", "1393"),
            Bugv2(
                """Fix task selection through keyboard in effort
editor (MS Windows and GTK).""",
                "1400",
            ),
            Bugv2(
                """Fix editing of effort start in the effort dialog.""", "1399"
            ),
            Bugv2(
                """Fix timezone-related display bug that would prevent
the task editor from opening on OS X.""",
                "1395",
            ),
            Bugv2(
                """Use presets for tasks created through mail DnD.""", "1403"
            ),
            Bugv2(
                """Fix loading of categories for notes belonging to
a subtask, and other such imbrications.""",
                "1404",
            ),
            Bugv2(
                """Fix preferences opening when end of work day is set to 24.""",
                "1394",
            ),
        ],
    ),
    Release(
        "1.3.27",
        "March 10, 2013",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2(
                """Follow system preferences to format dates (instead of
just times).""",
                "1386",
            ),
            Bugv2("""Fix date rendering on some versions of OSX.""", "1391"),
        ],
    ),
    Release(
        "1.3.26",
        "March 6, 2013",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2(
                """Exporting efforts in CSV with the 'Period' column and date/time
splitting would not work.""",
                "1387",
            ),
            Bugv2(
                """Task Coach would not launch on OS X 10.6 and later.""",
                "1388",
                "1390",
            ),
        ],
    ),
    Release(
        "1.3.25",
        "March 5, 2013",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bugv2("""Fix fonts in calendar viewer.""", "1370"),
            Bugv2("""Fix cutting attachments."""),
            Bugv2("""Fix focus on category viewer in task editor.""", "1382"),
            Bugv2("""Fix keyboard navigation in the editor's tabs.""", "1216"),
            Bugv2(
                """Make the effort stop menu a bit more contextual.""", "1381"
            ),
            Bugv2("""Fix effort stop button interaction with undo.""", "1381"),
            Bugv2(
                """Fix flickering on Windows 7 when Aero is enabled.""", "1384"
            ),
            Bugv2(
                """Fix opening of the task editor and preferences on
some locales.""",
                "1360",
            ),
            Bugv2(
                """Sorting by modification or creation date/time didn't
work.""",
                "1380",
            ),
            Bugv2(
                """Fix checkbox focus hint on Windows (in the date picker).""",
                "1372",
            ),
            Bugv2(
                """Use system settings for date and time formatting on OSX."""
            ),
            Bugv2(
                """Use system settings for date and time formatting on
KDE4.""",
                "1386",
            ),
            Bugv2(
                """Save templates to program directory for Task Coach Portable."""
            ),
        ],
        featuresAdded=[
            Feature(
                """Getting the subject from Mail.app on drag and drop is now
optional (takes too long)."""
            ),
            Feature(
                """Focus subject field when opening the task editor on Linux.
This is configurable.""",
                "1263",
            ),
        ],
    ),
    Release(
        "1.3.24",
        "February 17, 2013",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bugv2(
                """Clicking in the hour choice popup in the date/time
picker would select the wrong value.""",
                "1377",
            ),
            Bugv2(
                """Task Coach now follows the XDG specification for
configuration and data (template) files on Linux.""",
                "367",
            ),
            Bugv2("""Fix menu "Stop tracking multiple tasks" menu""", "1366"),
            Bugv2("""Fix focus issue in date picker.""", "1368"),
            Bugv2("""Fix discrepancy in due date time precision""", "1253"),
            Bugv2("""Fix multiple effort notices when idle.""", "1365"),
            Bugv2("""Fix font issue with calendar viewer.""", "1370"),
            Bugv2(
                """Fix "NoneType object is not callable" problem.""", "1371"
            ),
            Bugv2(
                """Prevent reminder dialogs and editors from stealing
focus.""",
                "956",
            ),
            Bugv2(
                """Add a visual hint that the checkbox has focus in the
date picker.""",
                "1372",
            ),
            Bugv2(
                """Fix opening of editor dialog on some locales""",
                "1360",
                "1375",
            ),
            Bugv2("""Fix idle notifications.""", "1365"),
            Bugv2(
                """Sort case insensitive in the toggle category menu.""",
                "1369",
            ),
            Bugv2("""Fix the N shortcut in datetime picker.""", "1378"),
        ],
        featuresAdded=[
            Feature(
                """The "notes" and "attachments" columns can now be
exported to HTML and CSV."""
            ),
            Feature("""Store the IMAP passwords in the user's keychain."""),
            Feature(
                """The default icon for completed tasks is now the green
checkmark."""
            ),
        ],
    ),
    Release(
        "1.3.23",
        "February 7, 2013",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2(
                """Some navigation shortcuts in the date/time picker
would not work on Windows or Linux.""",
                "1340",
            ),
            Bugv2(
                """Typing would not do anything on Windows in the
date/time picker if the calendar is shown.""",
                "1340",
            ),
            Bugv2(
                """The calendar popup from the date/time picker
would not show all days.""",
                "1340",
            ),
            Bugv2(
                """Task Coach would fail to start when the user had selected an 
empty bitmap for one of the task statuses."""
            ),
            Bugv2(
                """Non-ASCII characters would display wrong in the calendar popup
on OS X."""
            ),
            Bugv2(
                """Start/end of day choice in preferences now follow the user's
format preferences.""",
                "1331",
            ),
            Bugv2("""Resizing the toolbar would truncate it.""", "1341"),
            Bugv2(
                """Try to fetch Mail.app message subject.""", "1342", "1003"
            ),
            Bugv2(
                """Don't let the user pick columns that cannot be exported"""
            ),
            Bugv2(
                """When cancelling application shutdown, the window would
close nonetheless.""",
                "1346",
            ),
            Bugv2(
                """The calendar popup in the date picker would not use the
first week day setting.""",
                "1348",
            ),
            Bugv2(
                """Disable hide all filters when in tree mode and the only
filter is "hide composite tasks".""",
                "1351",
            ),
            Bugv2(
                """The task editor would not open on Windows if the user's short
date format used abbreviated or full month name.""",
                "1338",
            ),
            Bugv2("""Increase timer value for the date picker.""", "1354"),
            Bugv2(
                """Backspace/delete removes the last digit in the date
picker.""",
                "1354",
            ),
            Bugv2(
                """Fix Shift-S and Shift-E shortcuts in date picker on
Linux.""",
                "1358",
            ),
            Bugv2("""Fix overlay in toolbar icons.""", "1356"),
            Bugv2("""Use system default GUI font in date picker.""", "1361"),
            Bugv2("""Add shortcuts for AM/PM in date picker.""", "1362"),
            Bugv2(
                """Escape now dismisses calendar popup in date picker.""",
                "1362",
            ),
            Bugv2(
                """Fix crash when a task status icon has been set to
"No icon".""",
                "1364",
            ),
            Bugv2("""Fix refreshing of spent time in effort viewer""", "1363"),
        ],
        featuresAdded=[
            Feature(
                """Add a modification date attribute to tasks, notes, 
attachments, and categories.""",
                "http://uservoice.com/a/-2HX-",
            ),
            Feature(
                """Hitting Ctrl+V (or Cmd+V on OS X) while the date or time
picker has focus will try to interpret the clipboard's content. Ctrl+C
stores the current value in the clipboard.""",
                "1352",
            ),
        ],
        dependenciesChanged=[
            Dependency("""Task Coach now needs Python 2.7.""")
        ],
    ),
    Release(
        "1.3.22",
        "January 2, 2013",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2(
                """The task editor would not open after some time on Windows and
OS X.""",
                "1338",
            ),
        ],
    ),
    Release(
        "1.3.21",
        "January 1, 2013",
        summary="""This is a mixed feature and bugfix release.""",
        bugsFixed=[
            Bugv2(
                """Changing the percentage complete would not cause the
calendar viewer to refresh."""
            ),
            Bugv2(
                """On Mac OS X, clicking the period column in effort viewers to 
change the sort order didn't work."""
            ),
            Bugv2(
                """Adapt font size to available space in calendar view.""",
                "1309",
            ),
            Bugv2(
                """Using Shift+Enter key on the number keypad would not work on 
Mac OS X nor Linux.""",
                "1285",
            ),
            Bugv2("""Search defaults to simple substring matching.""", "1286"),
            Bugv2(
                """Growl notifications didn't work with Growl 2.0.""", "1324"
            ),
            Bugv2(
                """Fix another encoding problem on some locales (Windows).""",
                "1310",
                "1321",
            ),
            Bugv2("""Performance improvement in the edit dialogs.""", "991"),
            Bugv2("""Fix icon size in Unity.""", "1329"),
            Bugv2("""Fix docking of floating viewers on Windows."""),
            Bugv2(
                """When toggling the category of multiple items, not all of which 
are in the selected category, don't remove the items from the category that 
already belonged to that category.""",
                "1271",
            ),
            Bugv2(
                """Toolbar icons to show/hide tasks according to status now respect
appearance settings, and are overlayed with a red cross.""",
                "1104",
                "1323",
            ),
            Bugv2(
                """New date/time picker should fix most existing problems with the
old one.""",
                "702",
                "1089",
                "1212",
                "1266",
                "1233",
            ),
            Bugv2("""Fix wording for task statuses.""", "1333"),
        ],
        featuresAdded=[
            Feature("""New, hopefully more intuitive date/time control."""),
            Feature(
                """Display dates in human-readable form in viewers (today,
yesterday, tomorrow)."""
            ),
            Feature("""Startup and shutdown performance improvements."""),
            Feature("""Autosave is now on by default."""),
            Feature("""Support for Growl on Windows."""),
            Feature("""Toolbars are now customizable."""),
            Feature(
                """Add a creation date attribute to tasks, notes, attachments,
and categories.""",
                "http://uservoice.com/a/-2HX-",
            ),
            Feature(
                """Shift+Click on a filter button in the toolbar shows only the
corresponding task status"""
            ),
        ],
    ),
    Release(
        "1.3.20",
        "October 21, 2012",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bugv2(
                """Fix an encoding problem on Windows non-European locales""",
                "1306",
            ),
            Bugv2(
                """On Linux, Ctrl-Z in a text control would always remove the
whole contents of the text control instead of undoing the recent 
changes.""",
                "1267",
            ),
            Bugv2(
                """When adding a new item, always start the edit dialog with the 
description tab raised and focus on the item subject.""",
                "1263",
            ),
            Bugv2("""Editing templates would not work."""),
            Bugv2(
                """The effort dialog wouldn't function properly when the time
format contained dots, like in Italian.""",
                "1307",
            ),
            Bugv2(
                """Moving efforts between tasks would sometimes trigger an 
exception, resulting in lost efforts.""",
                "1203",
            ),
            Bugv2(
                """When there are multiple reminders and speech is on, don't
say all the reminders simultaneously, but one at a time.""",
                "1313",
            ),
        ],
    ),
    Release(
        "1.3.19",
        "October 7, 2012",
        summary="""This is a mixed feature and bugfix release.""",
        bugsFixed=[
            Bug(
                """Format times in the calendar view according to the user's
preferences.""",
                "3563441",
            ),
            Bug(
                """Do not automatically give focus to the subject field
in the task editor on Linux (it overwrites the X clipboard).""",
                "3539452",
            ),
            Bug(
                """After loading a task file, tasks would not become due soon
on time.""",
                "3562925",
            ),
            Bug(
                """On OS X, the first entry in an editor page would not be
automatically selected.""",
                "3562922",
            ),
            Bug(
                """On Linux, drag and drop of email messages from Evolution didn't
work.""",
                "3562808",
            ),
            Bug(
                """With autosaving on, Task Coach would actually save too often.""",
                "3562836",
            ),
            Bug(
                """On Ubuntu, a file was missing causing Task Coach not to
start.""",
                "3562695",
            ),
            Bug(
                """On Ubuntu, the native text control doesn't support undo and 
redo, added a home grown version.""",
                "3563376",
            ),
            Bug(
                """Don't silently adjust dates of parent and child tasks. See 
also the changed feature below.""",
                "3561465",
                "3564794",
            ),
            Bug(
                """Remember whether the "make this snooze time the default snooze
time for future reminders" check box was checked in the reminder dialog.""",
                "3567139",
            ),
            Bug("""The task viewer would not refresh at midnight."""),
            Bugv2(
                """On Windows with some locale settings, Task Coach would crash
trying to render dates.""",
                "1306",
            ),
        ],
        featuresAdded=[
            Feature(
                """In addition to specifying a maximum number of recurrences,
it is now also possible to specify an end date for recurrence. If both an end
date and a maximum number of recurrences are specified, recurrence stops when
the first of both conditions is met."""
            ),
            Feature(
                """Put a link to our IndieGoGo campaign on the toolbar of the
main window. The link will disappear when the campaign is over."""
            ),
        ],
        featuresChanged=[
            Feature(
                """Task Coach no longer enforces that the dates of child tasks
lie between the dates of its parent task. Previously, if the start date of a 
child task would be made earlier than the start date of its parent task, 
Task Coach would silently make the start of the parent task equal to the 
start date of the child task. The same for the due date: setting the due
date of the parent task earlier than the due date of a child task would 
silently change the due date of the child tasks if their due date would 
otherwise become later than the due date of the parent task.

When viewing tasks in the task tree viewer, collapsing a task with child tasks 
will show recursive dates when relevant. This means that the planned start 
date column will show the earliest start date of the task itself and all of
its child tasks. If the earliest start date is the start date of one of the 
child tasks, the date will be shown between brackets. Likewise, the actual 
start date column will show the earliest actual start date of the task and all 
of its child tasks. The due date column and the completion date column will 
show the latest date of the parent and child tasks combined. 

When sorting on a date column, the recursive value is used for sorting. So when
sorting ascending by due date a parent task without due date but with a child
task due today will sort before a task that is due tomorrow.

This change makes the date behavior consistent with priorities and other 
attributes."""
            ),
            Feature(
                """New viewers will open floating so that is easier to put them
in the position you want. Hopefully this will also make it more obvious for 
new users that viewers can be reordered any way they like since moving a 
floating viewer will show the docking guides."""
            ),
            Feature(
                """Clicking outside an inplace editor now accepts the changes
instead of discarding them."""
            ),
            Feature(
                """On Windows, both left clicking and left double clicking the 
Task Coach icon in the notification area (often called the system tray) will 
raise or minimize the main window (in accordance with 
http://msdn.microsoft.com/en-us/library/windows/desktop/aa511448.aspx#interaction).""",
                "http://uservoice.com/a/m3P6j",
            ),
        ],
    ),
    Release(
        "1.3.18",
        "August 28, 2012",
        summary="""This is a mixed feature and bugfix release.""",
        teamChanges=[
            Team(
                """We're happy to announce that Aaron Wolf joined the Task Coach
team. Aaron is already doing a great job scrutinizing the large number of 
feature requests we have open on http://taskcoach.uservoice.com. In addition,
he is helping us testing Task Coach and ironing out as many bugs as we can, see
the first results below. Furthermore, he is planning to develop an in-app 
tutorial for Task Coach so we're glad to have him on board. Welcome, Aaron!"""
            ),
        ],
        bugsFixed=[
            Bug(
                """Get rid of the infamous "AttributeError: __onDead" error""",
                "3546400",
            ),
            Bug(
                """Do not automatically give focus to the subject field
in the task editor on Linux (it overwrites the X clipboard).""",
                "3539452",
            ),
            Bug(
                """On Mac OS X, the window would shrink at each launch.
Tested on 10.5, 10.7 and 10.8DP4."""
            ),
            Bug("""Do not singularize user-set icons.""", "3539824"),
            Bug(
                """Disable spell checking on Mountain Lion because
it makes Task Coach crash.""",
                "3554534",
            ),
            Bug("""Fix opening URLs from the Help menu on KDE4.""", "3542487"),
            Bug("""Fix the About dialog on Kubuntu.""", "3542487"),
            Bug("""Reminders sometimes wouldn't fire.""", "3554603"),
            Bug(
                """On Mac OS X, idle time notifications would not work.""",
                "3554603",
            ),
            Bug(
                """On Mac OS X Snow Leopard (10.6) and earlier, the system would
ask the user to allow Task coach use a port (firewall) or the keychain
on every launch.""",
                "3556753",
            ),
            Bug(
                """On Mac OS X, the search options menu wouldn't work.""",
                "3558511",
            ),
            Bug(
                """When the language is set to English/US, use 12 hour clock in 
task and effort dialogs instead of 24 hour clock."""
            ),
            Bug(
                """Don't reset the edit dialog layout for editing single items
after editing multiple items at the same time.""",
                "3559292",
            ),
            Bug(
                """When changing the "Mark task completed when all children are 
completed?"-setting in the "Progress" tab of the task edit dialog, Task Coach
would set the percentage complete slider in the "Progress" tab to the 
recursive percentage complete while the slider is meant to only display and
change the percentage complete of the task itself.""",
                "3559740",
            ),
            Bug(
                """When a task with subtasks does not override the global setting
for marking a task completed when all of its subtasks are completed, actually
use that setting when displaying the percentage complete of the parent task
in the task viewer.""",
                "3559740",
            ),
            Bug(
                """The settings for the viewers in the edit dialogs (such as the
visible columns in the effort tab and the notes tab) wouldn't be consistently 
applied to each edit dialog.""",
                "3559057",
            ),
            Bug(
                """On Mac OS X, the button in the effort edit dialog for dropping
down the tree of tasks didn't work.""",
                "3560296",
            ),
            Bug(
                """Make recurrence label in the task edit dialog clearer.""",
                "3560420",
            ),
            Bug(
                """Make the description of the "idle time notice" setting in the 
preferences clearer.""",
                "3555498",
            ),
            Bug(
                """Make the description of the "minutes between suggested
times" setting in the preferences clearer.""",
                "3556765",
            ),
            Bug(
                """The combobox for selecting the snooze time in the reminder
dialog was not read only. This suggested that one could type in custom snooze 
times while that is not supported (yet).""",
                "3560416",
            ),
            Bug(
                """The "Filter on all checked categories/Filter on any checked
category" option was only available via the toolbar of the category viewer. 
Due to the width of the option, it could be difficult to access. The option
is now also available as menu item in the View->Filter menu.""",
                "3554627",
            ),
            Bug(
                """When the budget left is negative, the budget left field in the
task edit dialog would not show a minus sign.""",
                "3554616",
            ),
            Bug(
                """On Mac OS X, the tip of the day window would block the dialog 
for unlocking a locked task file.""",
                "3561499",
            ),
            Bug(
                """When saving selected tasks, not only include the categories
the selected tasks belong to, but also the parent categories of the used
categories, even though they may not have been used themselves.""",
                "3561159",
            ),
            Bug(
                """When creating a new item, set focus to the subject field so 
that the description tab is raised if needed.""",
                "3561515",
            ),
            Bug(
                """On Mac OS X, dropping of URLs without a protocol specification
('http:', 'https:', 'ftp:', etc.) would result in attachments that couldn't be
opened.""",
                "3561889",
            ),
            Bug("""On Linux, dropping of URLs didn't work.""", "3561889"),
            Bug(
                """The order of tabs in edit dialogs wouldn't be restored 
correctly after it had been changed by the user.""",
                "3562239",
            ),
            Bug(
                """Save size, position and maximization state of dialogs separately
for single-item and multi-item dialogs.""",
                "3562239",
            ),
            #        Bug('''Fix slowness when viewing aggregated efforts.''',
            #            '3538310', '3537702'),
        ],
        featuresAdded=[
            Feature(
                """Increase font size in the calendar view's header.""",
                "3558650",
            ),
            Feature(
                """In the calendar view, unplanned dates are now cropped
to the current day."""
            ),  # Close bug report 3539404 when 1.3.18 is released.
            Feature(
                """Add support for Thunderbird IMAP accounts that use
NTLM authentication (typically Exchange accounts)."""
            ),
            Feature(
                """When starting up, Task Coach checks for messages from the 
Task Coach developers. This allows us to reach all users for e.g. notifications 
on critical bugs or requests for support. Each message is displayed only once
and the display of messages can be turned off completely. This feature will be
used sparingly, of course."""
            ),
            Feature(
                """Added almost complete Belarusian translation thanks to 
Korney San."""
            ),
            Feature(
                """Allow for changing the font used in the description field
of edit dialogs. The font can be changed in the editor tab of the preferences 
dialog. Patch supplied by Nicola Chiapolini."""
            ),
        ],
        featuresChanged=[
            Feature(
                """When a task has no due date, instead of displaying 
"Infinite" for the time left in the task viewer, Task Coach now displays blank 
space."""
            ),
        ],
    ),
    Release(
        "1.3.17",
        "July 2, 2012",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Use the user-specified time format on Windows.""", "3530080"
            ),
            Bug(
                """In the effort viewer, when calculating total effort for tasks in 
a certain period, one effort would be skipped.""",
                "3537707",
            ),
            Bug(
                """When tracking effort for one task, don't show "Stop tracking
multiple tasks" as the menu label for the "Stop tracking" menu item in the 
action menu.""",
                "3536577",
            ),
            Bug(
                """On Windows, use a more recent Python27.dll to satisfy Secunia 
PSI.""",
                "3539139",
            ),
            Bug("""Loading a big task file is now much faster."""),
            Bug(
                """The calendar view would not react to changes to tasks.""",
                "3539402",
            ),
        ],
    ),
    Release(
        "1.3.16",
        "June 16, 2012",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Fix a crash during iPhone synchronization if a category 
associated with a modified task has been deleted on the desktop."""
            ),
            Bug(
                """The stop/resume effort tracking button on the toolbar wasn't
working correctly.""",
                "3529025",
            ),
            Bug(
                """When tracking effort, the time spent in the effort viewer was
not always updated."""
            ),
        ],
    ),
    Release(
        "1.3.15",
        "May 24, 2012",
        summary="""This is a mixed feature and bugfix release.""",
        bugsFixed=[
            Bug(
                """On Windows 7, when the language is English (US), render times
in the task viewer using AM/PM."""
            ),
            Bug(
                """On Mac OS X and Windows, don't crash when waking up from 
stand by.""",
                "3523648",
            ),
            Bug(
                """Resetting task filters at midnight was not working properly."""
            ),
            Bug(
                """Faster opening of task files when there are many effort 
records."""
            ),
        ],
        featuresAdded=[
            Feature("""Better word wrapping in calendar view."""),
        ],
    ),
    Release(
        "1.3.14",
        "May 13, 2012",
        summary="""This is a mixed feature and bugfix release.""",
        bugsFixed=[
            Bug("""Task Coach wouldn't start on Ubuntu 12.04.""", "3522305"),
        ],
        featuresAdded=[
            Feature(
                """Added support for pipe as separator symbol when importing 
from CSV.""",
                "http://uservoice.com/a/arHeO",
            ),
        ],
    ),
    Release(
        "1.3.13",
        "April 14, 2012",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug("""Translations couldn't be changed.""", "3516306"),
            Bug(
                """Exporting to CSV with dates and times to separate columns would
fail if any of the tasks had a date before 1900.""",
                "3516964",
            ),
            Bug(
                """Disable the checkbox for separate date and time columns in the CSV
export dialog when the user picks a viewer that doesn't contain tasks.""",
                "3515241",
            ),
            Bug(
                """Don't complain about a missing log handler in the log file
on Windows.""",
                "3517705",
            ),
        ],
    ),
    Release(
        "1.3.12",
        "April 9, 2012",
        summary="""This is a mixed feature and bugfix release.""",
        bugsFixed=[
            Bug(
                """X session management is now disabled by default.""",
                "3502180",
            ),
            Bug(
                """The percentage of tasks completed, active, etc. in the 
task statistics viewer (the pie chart) would be wrong when filtering 
categories."""
            ),
            Bug(
                """The category drop down menu for filtering on any or all
categories didn't have effect.""",
                "3514880",
            ),
            Bug(
                """Merging a file that would remove a subcategory linked to 
existing tasks or notes would not work.""",
                "3515503",
            ),
            Bug("""Drag and drop was broken.""", "3514209"),
            Bug(
                """On Windows, when emailing items, new lines in the description
would disappear.""",
                "3514288",
            ),
            Bug(
                """Properly shut down the internal scheduler before closing 
Task Coach to prevent an exception.""",
                "3514651",
            ),
            Bug(
                """Changing the task appearance in the preference dialog didn't 
work unless no tasks had been edited before changing the appearance.""",
                "3514174",
            ),
            Bug(
                """Marking a recurring task complete from a reminder could throw
an exception.""",
                "3514174",
            ),
        ],
        featuresAdded=[
            Feature(
                """The calendar view can now be printed as is.""", "3503258"
            ),
        ],
    ),
    Release(
        "1.3.11",
        "March 31, 2012",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Task Coach wouldn't start due to a missing module.""",
                "3513392",
            ),
        ],
    ),
    Release(
        "1.3.10",
        "March 30, 2012",
        summary="""This is a mixed feature and bugfix release.""",
        bugsFixed=[
            Bug(
                """The statusbar counts of over due tasks, late tasks, etc. would
include deleted tasks.""",
                "3501289",
            ),
        ],
        featuresAdded=[
            Feature(
                """Allow for importing reminder date/time when importing from
a CSV file.""",
                "http://uservoice.com/a/2xhV6",
            ),
            Feature(
                """Allow for setting the first day of the week (either Sunday
or Monday) in the preferences dialog (features tab).""",
                "http://uservoice.com/a/81C1K",
            ),
        ],
    ),
    Release(
        "1.3.9",
        "March 8, 2012",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """The drop down menu for the option 'Schedule each next 
recurrence based on' in the dates tab of the task edit dialog wasn't 
being enabled when the user turned on the recurrence of a task.""",
                "3496505",
            ),
            Bug(
                """On Xubuntu, Task Coach would briefly show dialogs centered over 
the Task Coach main window before showing them on their destined location.""",
                "3496271",
            ),
            Bug(
                """When exporting to CSV with separate date and time columns, 
don't write 31/12/9999 for empty dates.""",
                "3495429",
            ),
            Bug("""On Linux, honor the LC_TIME setting.""", "3495925"),
            Bug(
                """After reading a task file with a deleted task that had a
subtask with prerequisites, Task Coach would refuse to save the file.""",
                "3496986",
            ),
        ],
    ),
    Release(
        "1.3.8",
        "February 25, 2012",
        summary="""This is a mixed feature and bugfix release.""",
        featuresAdded=[
            Feature(
                """In task viewers, late tasks, due soon tasks, and over due
tasks can be hidden. It was already possible to hide inactive tasks, active 
tasks, and completed tasks. This makes it possible to create a task viewer
that only shows e.g. due soon tasks or late tasks, or any combination of
task statuses."""
            ),
            Feature(
                """Add an option to disable session management on GTK.
The XFCE session manager causes Task Coach to hang randomly on start."""
            ),
            Feature(
                """On Mac OS X and Linux (with espeak installed), 
reminders can be spoken. This can be turned on in the preferences dialog, 
on the task reminder tab."""
            ),
        ],
        bugsFixed=[
            Bug(
                """Show a warning dialog when running XFCE4 to highlight the
session management issues and tell the user about the option to disable it""",
                "3482752",
            ),
            Bug(
                """Display times with a 12 hour clock (AM/PM) when the language is 
set to English (US)."""
            ),
            Bug(
                """Don't change the selection when deleting or hiding items that 
are not selected. When adding a new item, select it. When adding a new sub 
item, also expand the parent item if necessary.""",
                "3484930",
            ),
            Bug(
                """When using the Norsk translation on Linux (both Nynorsk and 
Bokmal), Task Coach would crash when displaying a date picker control. This is 
a bug in the underlying wxWidgets toolkit. Worked around by using another 
locale for dates and times when the language is Norsk.""",
                "1820497",
            ),
            Bug(
                """On Mac OS X, the shortcut to email a task is now Shift-Cmd-M
instead of Cmd-M (which is the system shortcut to minimize the active
window).""",
                "3489341",
            ),
            Bug(
                """Don't escape characters on Mac OS X when emailing a task.""",
                "3489341",
            ),
        ],
    ),
    Release(
        "1.3.7",
        "February 3, 2012",
        summary="""This is a bug fix release.""",
        bugsFixed=[
            Bug("""Paste as subitem didn't work for efforts.""", "3479734"),
            Bug(
                """Hiding inactive tasks would also hide some active tasks.""",
                "3479952",
            ),
            Bug(
                """Setting the task font back to the default font
in the preferences dialog wouldn't work."""
            ),
            Bug(
                """Put a little bit of white space to the right of the priority
column in the task viewer to separate the numbers from the scroll bar.""",
                "3479686",
            ),
            Bug(
                """Disable the Anonymize menu item if there is no task file.""",
                "3482373",
            ),
            Bug(
                """After removing an actual start date of a task with effort and 
saving and opening the task file, the task would still have an actual start date 
(based on the earliest effort).""",
                "3478684",
                "3479444",
            ),
            Bug(
                """Marking an inactive task active wouldn't properly update the 
task icon from grey to blue.""",
                "3479444",
            ),
            Bug(
                """Exporting to iCalendar wouldn't work if the subject or
description had non-ASCII characters.""",
                "3483124",
            ),
        ],
        featuresRemoved=[
            Feature(
                """The more complex filtering options for hiding tasks have
been removed. The complexity was causing bugs."""
            ),
        ],
    ),
    Release(
        "1.3.6",
        "January 24, 2012",
        summary="""This is a bug fix release.""",
        bugsFixed=[
            Bug(
                """The link on the website for downloading sources pointed to the 
iOS downloads."""
            ),
            Bug(
                """Task Coach couldn't deal with circular dependencies between 
tasks.""",
                "3477762",
                "3477637",
            ),
            Bug(
                """The default actual start date and time couldn't be set in the
preferences.""",
                "3478747",
            ),
        ],
    ),
    Release(
        "1.3.5",
        "January 22, 2012",
        summary="""This is a mixed feature and bug fix release.""",
        bugsFixed=[
            Bug(
                """After a reminder of a recurring task had been dismissed, Task 
Coach would not create a new reminder when recurring the task.""",
                "3469217",
            ),
            Bug(
                """When the user is not using a translation, still set the 
locale so that the proper formatting for dates and numbers is used.""",
                "3091934",
            ),
            Bug("""Sorting case sensitive didn't work."""),
            Bug(
                """Categories of notes belonging to tasks and categories weren't 
saved.""",
                "3474487",
            ),
            Bug(
                """On OpenSuse, Task Coach would crash when changing the width of 
columns."""
            ),
        ],
        featuresAdded=[
            Feature("""Note categories are now synced as well (SyncML)"""),
            Feature("""Add "actual start date" attribute to tasks."""),
            Feature(
                """Add toolbar buttons and menu items for marking tasks 
inactive, active and completed."""
            ),
            Feature(
                """When exporting to iCal, include percentage complete of a 
task in the exported data."""
            ),
        ],
        featuresChanged=[
            Feature(
                """Rename "start date" to "planned start date" to enable
adding a separate "actual start date" attribute to tasks."""
            ),
        ],
        websiteChanges=[
            Website(
                """Redesigned website using Twitter Bootstrap.""", "index.html"
            ),
        ],
    ),
    Release(
        "1.3.4",
        "December 25, 2011",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Changing the color and font of tasks in the preferences dialog
didn't work."""
            ),
            Bug("""In Spanish, showing reminders wouldn't work.""", "3459524"),
            Bug(
                """Fix a small translation error in the French translation.""",
                "3459028",
            ),
            Bug(
                """Changes on a newly created template in the template editor
were discarded."""
            ),
            Bug(
                """Help text referred to "Add template", but the menu item is 
called "Import template".""",
                "3462367",
            ),
            Bug(
                """On Mac OS X, associate .tsk files with Task Coach and let the 
Finder use the Task Coach icon for .tsk files.""",
                "3462366",
            ),
            Bug(
                """On Linux without libXss installed (seen on Fedora 16), Task 
Coach would fail to start. Fixed by adding libXss as an explicit 
dependency to the RPM-package.""",
                "3463044",
            ),
            Bug(
                """A lock created under Mac OS X Lion on a network share could
not be broken on another OS."""
            ),
            Bug(
                """Trying to save to a disconnected network share/USB drive would
fail on Windows.""",
                "3462383",
            ),
        ],
        featuresAdded=[
            Feature(
                """Provide for an option to always round effort up to the next
increment in the effort viewer.""",
                "http://uservoice.com/a/5Hbrf",
            ),
        ],
    ),
    Release(
        "1.3.3",
        "December 13, 2011",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """On Linux, after every edit of a task, the undo history 
would contain a "recurrence edited" action even though the recurrence was 
not changed.""",
                "3453625",
            ),
            Bug(
                """On Ubuntu, the date controls in the effort edit dialog would
be invisible.""",
                "3452446",
            ),
            Bug(
                """On Windows, when users try to save the task file in a 
folder where they don't have permission, Task Coach would not give a proper
warning."""
            ),
            Bug(
                """When editing multiple items at once, show all descriptions in the
description field for easier editing and/or copying.""",
                "3446417",
            ),
        ],
    ),
    Release(
        "1.3.2",
        "December 5, 2011",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """When a subject contained an ampersand (&), the ampersand would 
not be shown in menu's where the subject is used."""
            ),
            Bug(
                """When creating new subtasks, they would always be inactive.""",
                "3446309",
            ),
            Bug(
                """Closing task dialogs was very slow with a large task file."""
            ),
            Bug(
                """Setting a budget to zero would make it impossible to save the 
task file.""",
                "3449423",
            ),
            Bug(
                """When the subject is too long to be displayed in the editor,
display its start instead of its end.""",
                "3433481",
            ),
        ],
        featuresAdded=[
            Feature(
                """Rounding of effort in effort viewers.""",
                "http://uservoice.com/a/6IzRQ",
            ),
        ],
    ),
    Release(
        "1.3.1",
        "November 27, 2011",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Don't turn off the start date on new tasks when users
have indicated in the preferences that they want a default start date.""",
                "3440634",
            ),
            Bug(
                """The "Start tracking from last effort" button in the effort
dialog didn't work.""",
                "3440794",
            ),
            Bug(
                """"View->Tree options->Collapse all items" did only collapse top
level items.""",
                "3441180",
            ),
            Bug(
                """The language choice control in the preferences dialog would 
always show "Let the system determine the language", no matter what language 
the user had picked before.""",
                "3441456",
            ),
            Bug(
                """Allow for flat pie charts, because reading data from flat pie
charts is easier than from 3D pie charts.""",
                "3441469",
            ),
            Bug(
                """On Windows, the Edit menu could become very wide if the user
would edit a long subject.""",
                " 3441474",
            ),
            Bug(
                """When the user edits the reminder date and time and it is
in the past, don't fire the reminder immediately, but wait a minute to give 
the user a change to finish changing the reminder date and time into a 
future date and time.""",
                "3441442",
            ),
            Bug(
                """Make sure the edit dialogs are by default big enough to show all
controls.""",
                "3441783",
            ),
            Bug(
                """On Linux without libXss installed (seen on Ubuntu 11.10), Task 
Coach would fail to start. Fixed by adding libXss as an explicit 
dependency to the Debian (.deb) package."""
            ),
        ],
        featuresAdded=[
            Feature(
                """The effort dialog now has a button to set the stop date and
time of the effort to the current date and time."""
            ),
            Feature(
                """Allow for changing the angle of the pie charts via a slider
in the toolbar of the task statistics viewer."""
            ),
            Feature(
                """Allow for 6 minutes between effort start and stop times,
in addition to 5, 10, 15, etc. See the features tab in the preferences 
dialog.""",
                "http://uservoice.com/a/3nnfc",
            ),
            Feature("""Dependencies can now be set using drag and drop."""),
        ],
    ),
    Release(
        "1.3.0",
        "November 20, 2011",
        summary="""This release makes all edits done in dialogs immediate.""",
        featuresAdded=[
            Feature(
                """Item edit dialogs make changes immediately, thus no need
for OK and Cancel buttons anymore.""",
                "http://uservoice.com/a/oNbcq",
            ),
            Feature(
                """If there is no user input for some (configurable) time,
Task coach now asks what to do with tracked efforts when the user comes
back.""",
                "http://uservoice.com/a/4656L",
            ),
        ],
        bugsFixed=[
            Bug(
                """It was and is possible to open multiple edit dialogs for the same
item. With earlier releases of Task Coach, the last edit dialog closed would 
overwrite changes made with edit dialogs that were closed earlier. With the new 
edit dialog functionality introduced in this release, changes are propagated 
immediately to all open dialogs. This will prevent overwriting
changes made in other dialogs.""",
                "1152561",
            ),
            Bug(
                """Don't close the edit dialog when dragging and dropping 
an item.""",
                "3424138",
            ),
            Bug(
                """When editing start or due date inline, Task Coach would ignore 
the preference for keeping the time between the two dates constant."""
            ),
            Bug(
                """Prevent an exception when opening the View menu when the
task statistics viewer is selected."""
            ),
            Bug(
                """The Ctrl-F shortcut didn't work in most viewers.""",
                "3438256",
            ),
            Bug(
                """The export to HTML and CSV dialog didn't work on Windows XP.""",
                "3440438",
            ),
            Bug(
                """On Windows, use wider date and time controls when the user 
is running the display with a higher DPI-setting.""",
                "3439774",
            ),
        ],
    ),
    Release(
        "1.2.31",
        "November 13, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """Immediately update the number of tasks completed in the status
bar of the task viewer when the user marks a task completed.""",
                "3185805",
            ),
            Bug(
                """When adding new tasks, Task Coach would first show them briefly 
as inactive before showing them as active.""",
                "3085362",
            ),
            Bug("""Only "preset" dates on new tasks."""),
            Bug(
                """When changing a date/time inline, hitting enter in the date part
of the control would close the inline control, but not change the date.""",
                "3428503",
            ),
            Bug(
                """The inline edit controls for dates/times didn't use the
preferences for start and end of working day.""",
                "3431160",
            ),
            Bug(
                """Using drag and drop to change dates in the calendar view would
produce erroneous results in some configurations.""",
                "3428525",
            ),
            Bug(
                """In some configurations, some hours would not be drawn in
the calendar view in vertical mode.""",
                "3428524",
            ),
        ],
        featuresAdded=[
            Feature(
                """When exporting to CSV, dates and times can optionally be 
put in separate columns."""
            ),
            Feature(
                """When exporting to CSV and HTML, the columns to be exported
can be changed in the export dialog."""
            ),
            Feature(
                """Simple task statistics viewer added that shows a pie chart
of the distribution of task states."""
            ),
        ],
    ),
    Release(
        "1.2.30",
        "October 23, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """Better explanation of the automatic import and export of
Todo.txt format in the preferences dialog.""",
                "3418906",
            ),
            Bug(
                """The task viewer in list mode now also shows the  
categories, prerequisites and dependencies inherited from parent tasks, between 
parentheses. In addition, the inherited categories, prerequisites or 
dependencies are taken into account when sorting by categories, prerequisites or
dependencies.""",
                "3414914",
            ),
            Bug(
                """Don't reset the percentage complete to 0 when the user changes
it from 100 to some other percentage less than 100."""
            ),
            Bug("""Fix a memory leak when opening edit dialogs."""),
        ],
        featuresAdded=[
            Feature(
                """The task viewer in list mode now also shows the  
categories, prerequisites and dependencies inherited from parent tasks, between 
parentheses. In addition, the inherited categories, prerequisites or 
dependencies are taken into account when sorting by categories, prerequisites or
dependencies.""",
                "http://uservoice.com/a/ksD1q",
            ),
            Feature(
                """Percentage complete, hourly fee and fixed fee of tasks can 
be edited in place."""
            ),
        ],
    ),
    Release(
        "1.2.29",
        "October 3, 2011",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """If auto importing of Todo.txt files was turned on, but
there was no Todo.txt file available for importing, saving would fail.""",
                "3410648",
            ),
            Bug(
                """When the priority field gets focus, select all priority digits
so the user can simply type a new number to overwrite the previous one.""",
                "3411384",
            ),
            Bug(
                """When showing effort in detail mode, Task Coach would only 
consider the start of a period to decide whether to hide the period as a
repeated period. Now it considers both the start and the end date and time."""
            ),
            Bug(
                """When editing multiple tasks at the same time, changing the
priority would not automatically check the priority checkbox.""",
                "3414423",
            ),
            Bug(
                """Don't reorder the contents of the task file randomly when saving
the task file. This makes it possible to easily see the differences between 
versions of a task file using diff.""",
                "3412300",
            ),
        ],
    ),
    Release(
        "1.2.28",
        "September 18, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """Task Coach would not work correctly with dates before 1900."""
            ),
            Bug(
                """When recovering from an error in the TaskCoach.ini file, get
the default settings from the right section.""",
                "3404024",
            ),
            Bug("""When opening a URL fails, show an error message dialog."""),
            Bug(
                """Task Coach would crash when editing a task/category/etc on
some versions of wxPython."""
            ),
            Bug(
                """Adding a subtask without a due date would reset its parent's
due date.""",
                "3405053",
            ),
            Bug(
                """Using the Delete key when editing the priority inline would 
delete the task on Windows.""",
                "3400086",
            ),
            Bug("""On Windows, SyncML couldn't be turned on.""", "3406653"),
            Bug(
                """When adding a new (recurring) subtask to a parent task,
push back the start date of the parent if necessary.""",
                "3409716",
            ),
            Bug(
                """On Mac OS X Tiger, whenever trying to give focus to the
search control focus would return to the viewer immediately, making
searching impossible.""",
                "3410268",
            ),
        ],
        featuresAdded=[
            Feature(
                """The SyncML password is now stored encrypted in the
system keychain, if available."""
            ),
            Feature(
                """Add task subject to the reminder dialog window title so that
it's easier to find a particular reminder when cycling through windows with
Alt-Tab.""",
                "http://uservoice.com/a/au6wa",
            ),
            Feature(
                """Allow for dragging and dropping multiple items (tasks,
notes, etc.) at once. Patch provided by Kirill Müller.""",
                "http://uservoice.com/a/hledQ",
            ),
        ],
    ),
    Release(
        "1.2.27",
        "August 28, 2011",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """When importing a CVS file, Task Coach would not always guess
the day/month order correctly. It is now possible to specify whether days or 
months come first in date columns."""
            ),
            Bug(
                """Unchecking an already checked mutually exclusive subcategory
would uncheck it, but not change the filtering.""",
                "3377145",
            ),
            Bug(
                """The calendar configuration dialog wouldn't open.""",
                "3395689",
            ),
            Bug(
                """Saving could fail after a reminder was first snoozed and then
later the reminder dialog was closed without snoozing.""",
                "3397920",
            ),
            Bug(
                """Using the Delete key when editing the priority inline would 
delete the task.""",
                "3400086",
            ),
            Bug(
                """Using the Enter key when editing the priority inline would not
accept the changes on Mac OS X."""
            ),
            Bug("""Fix issues in Italian translation.""", "3398600"),
        ],
    ),
    Release(
        "1.2.26",
        "August 20, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """Checking an already checked mutually exclusive subcategory now 
unchecks it.""",
                "3377145",
            ),
            Bug("""Task Coach would not start on PPC Macs.""", "3388666"),
            Bug(
                """Saving a task as template would not work if the subject or
description contains non-ascii characters"""
            ),
            Bug(
                """Fix case insensitive searching with non-ascii languages.""",
                "3395268",
            ),
            Bug(
                """The recent searches menu in the search control wasn't working
properly on Mac OS X."""
            ),
        ],
        featuresAdded=[
            Feature(
                """Importing and exporting of Todo.txt format task files. 
Todo.txt is an open source todo list manager that works with plain text files. 
Todo.txt Touch is a version of Todo.txt for the Android platform, that
syncs with Dropbox. By exporting your tasks to a todo.txt file in your Dropbox
folder, you can then edit them on your Android device with Todo.txt Touch. See
the help contents for more information.""",
                "http://uservoice.com/a/6Z54H",
                "http://uservoice.com/a/ceNES",
            ),
            Feature(
                """Automatic importing and/or exporting on every save. This can 
be turned on in the preferences dialog. Currently only possible for the Todo.txt 
format."""
            ),
            Feature(
                """When turning on the stop date and time in the effort edit
dialog, set the date and time to the current date and time.""",
                "http://uservoice.com/a/iFkds",
            ),
            Feature(
                """When editing templates, one can now also edit subtasks."""
            ),
            Feature(
                """Remember the last visited path when choosing a file
attachment.""",
                "http://uservoice.com/a/jz5dE",
            ),
            Feature(
                """Support times in addition to dates when importing from CSV."""
            ),
        ],
        featuresChanged=[
            Feature(
                """The maximum of the number of hours that tasks are considered 
"due soon" is now a big number instead of a mere 90.""",
                "http://uservoice.com/a/dVIBF",
            )
        ],
    ),
    Release(
        "1.2.25",
        "August 8, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """The anonymize function wouldn't give a notification after saving
the file."""
            ),
            Bug(
                """Refresh subtask appearance when moving it to a different parent
task."""
            ),
            Bug(
                """Indentation of categories with and without subcategories in the 
category viewer was slightly different.""",
                "3345002",
            ),
            Bug(
                """Windows would appear on the wrong monitor on Windows 7.""",
                "3370403",
            ),
            Bug(
                """On Windows 7, the task view would flicker every second.""",
                "3354402",
            ),
            Bug(
                """On Mac OS X, Task Coach would hang when both the splash screen
and the "file locked" dialog are displayed.""",
                "3383050",
            ),
            Bug(
                """Startup even when reading one of the templates fails.""",
                "3386296",
            ),
            Bug("""Task Coach would sometimes crash on startup on Linux."""),
        ],
        featuresAdded=[
            Feature(
                """Users can choose default (relative) dates and
times for tasks in the preference dialog. This allows for e.g. automatically 
setting a reminder the next day.""",
                "http://uservoice.com/a/g9xpy",
            ),
            Feature("""Faster saving."""),
            Feature("""Preset common SyncML servers (MemoToo)"""),
            Feature(
                """The user can choose to use the selected snooze time in the 
reminder dialog as default snooze time for future reminders."""
            ),
            Feature(
                """Support drag and drop of email messages from local 
folders in Thunderbird."""
            ),
            Feature(
                """Support drag and drop of email messages from Claws Mail.
Patch provided by Tobias Gradl."""
            ),
        ],
    ),
    Release(
        "1.2.24",
        "July 17, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """Synchronizing with an iDevice could change the whole UI font."""
            ),
            Bug(
                """Drag and drop from Thunderbird would not work in some circumstances."""
            ),
            Bug(
                """When recurring tasks with a snoozed reminder, use the original
reminder date and time as basis for the next reminder, instead of the snoozed 
reminder.""",
                "2942198",
            ),
            Bug("""In-place editing of reminders didn't work.""", "3361971"),
            Bug(
                """Completed tasks with a start date would not show up in the calendar."""
            ),
        ],
        featuresChanged=[
            Feature(
                """New "Anonymize" item in the Help menu. This saves an anonymized copy of 
all data from a task file in order to safely attach it to a bug report."""
            ),
            Feature(
                """Recurring tasks can recur based on the original start and due
date (as was the only option until now) or based on the last completion date.""",
                "http://uservoice.com/a/d3n3g",
            ),
        ],
    ),
    Release(
        "1.2.23",
        "July 7, 2011",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Task Coach would fail on parsing old templates, causing it not to start
properly."""
            )
        ],
    ),
    Release(
        "1.2.22",
        "July 2, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """Properly open task files with email attachments that
have a non-ascii subject.""",
                "3333730",
            )
        ],
        featuresChanged=[
            Feature(
                """You can set a default snooze time in the preferences
that is used in the reminder dialog as the default suggestion for the snooze
time. If you use Growl or Snarl, the default snooze time is added to the reminder
after the reminder fires."""
            )
        ],
    ),
    Release(
        "1.2.21",
        "June 25, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """Prevent exception messages in log file (Windows) or on command 
line (Linux).""",
                "3315358",
                "3316220",
                "3324330",
            ),
            Bug(
                """Properly decode non-ascii email subject headers.""",
                "3311272",
            ),
            Bug(
                """Creating a template from a task would not work any more.""",
                "3317048",
            ),
            Bug(
                """Unplugging a monitor while Task Coach was running would cause
the dialogs to always open in the top left corner on Windows."""
            ),
        ],
        featuresAdded=[
            Feature(
                """Start, due, completion, and reminder date and time of tasks 
can be edited in-place when the relevant column is visible."""
            )
        ],
    ),
    Release(
        "1.2.20",
        "June 10, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """Task Coach tried to use Python 2.5 on Ubuntu.""",
                "3309089",
                "3309317",
            ),
            Bug(
                """The total number of effort records displayed in the status
bar of an effort viewer would be incorrect when the effort viewer was showing 
aggregated effort (per day, per week or per month)."""
            ),
            Bug(
                """When hiding completed tasks and showing tasks belonging to a 
specific category (say C), Task Coach would show a task even though it didn't
belong to that category if that task had completed subtasks belonging 
to category C.""",
                "3309006",
            ),
            Bug(
                """Floating and then closing the task viewer didn't work.""",
                "3313199",
            ),
        ],
        featuresAdded=[
            Feature(
                """Descriptions of tasks, notes and categories can be edited 
in-place when the description column is visible. Priority of tasks can be
edited in-place when the priority column is visible. Budget of tasks can be
edited in-place when the budget column is visible."""
            ),
            Feature("""Basic editing (dates, subject) of task templates."""),
            Feature("""Session management on Linux is back.""", "2929786"),
        ],
    ),
    Release(
        "1.2.19",
        "May 29, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """Editing multiple items would hang Task Coach.""", "3305844"
            ),
            Bug(
                """Changing the task of an effort record would make it 
invisible.""",
                "3304940",
            ),
            Bug(
                """The keyboard shortcut for adding effort (Ctrl-E) wouldn't work 
in edit dialogs.""",
                "3306827",
            ),
            Bug(
                """Closing Task Coach with a square task viewer open caused
exceptions in the log file.""",
                "3307836",
            ),
            Bug(
                """Drag and drop email from Thunderbird, PortableApps edition,
didn't work.""",
                "3058781",
            ),
            Bug(
                """On Mac OS X, the main window would grow 11 pixels in height at
each launch."""
            ),
            Bug(
                """On Mac OS X, the editor dialogs would shrink a little each time
they were opened."""
            ),
        ],
        featuresAdded=[
            Feature(
                """The default foreground color, background color, font and 
icon of active, inactive, completed, over due and due soon tasks can be changed 
in the preferences.""",
                "http://uservoice.com/a/nLMgZ",
            ),
            Feature(
                """The way start and due dates are tied together when changing
one of them is now configurable."""
            ),
            Feature("""Add percentage complete to CSV import fields."""),
        ],
        distributionsChanged=[
            Distribution("""Removed support for Fedora 13.""")
        ],
    ),
    Release(
        "1.2.18",
        "May 21, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """Make sure long menu texts don't overlap the keyboard shortcut."""
            ),
            Bug(
                """CSV import would crash on Mac OS X if the number of fields wasn't
constant."""
            ),
            Bug(
                """When starting or stopping an effort, the task's icon in the
calendar viewer would not change."""
            ),
            Bug("""Session management wouldn't work on XFCE."""),
            Bug(
                """Start up even if the TaskCoach.ini file contains garbage.""",
                "3299850",
                "3300722",
            ),
            Bug(
                """Don't crash if there is no session manager on Linux""",
                "3300643",
            ),
            Bug("""Give the import dialog a proper window title bar."""),
            Bug(
                """Going back and then forward in the CSV import wizard didn't work."""
            ),
            Bug(
                """Task Coach wouldn't keep the inline subject edit control open
in the task viewer when tracking effort.""",
                "3301562",
            ),
        ],
        featuresAdded=[
            Feature(
                """Open tracked tasks without looking them up using the 
Actions->Edit tracked task menu item (Shift-Alt-T).""",
                "http://uservoice.com/a/itBB5",
            ),
            Feature(
                """Effort tracking can be started for inactive/future tasks.
Doing so sets the start date and time of the task to the current date and 
time.""",
                "http://uservoice.com/a/oyhL7",
            ),
            Feature(
                """Show name of the current task file in the system tray 
tooltip window.""",
                "http://uservoice.com/a/959Qc",
            ),
            Feature(
                """Tabs in the edit dialogs can be dragged and dropped to 
create any layout the user may want."""
            ),
            Feature(
                """CSV files may also have colons or semicolons as separators."""
            ),
            Feature(
                """It is possible to select which rows to import from a CSV file."""
            ),
            Feature(
                """The CSV import wizard tries to match column headers from the 
CSV file to task attributes."""
            ),
            Feature(
                """The CSV import will reuse existing categories if the names
match."""
            ),
        ],
        featuresRemoved=[
            Feature(
                """Session management for X is temporarily removed, until we can
fix the occasional crashes associated with it."""
            )
        ],
    ),
    Release(
        "1.2.17",
        "May 5, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """Make sure one of the viewers is selected in the export to 
iCalendar dialog."""
            ),
            Bug(
                """Properly update the icon of a task with subtasks when adding
it to a category with an icon.""",
                "3295077",
            ),
            Bug(
                """The calendar view would cause spurious errors on Windows.""",
                "3294878",
            ),
            Bug(
                """Use the actual system font on Mac OS X and Windows in the
tree and list viewers.""",
                "3295070",
            ),
            Bug(
                """Dutch translation used Ctrl-H as shortcut for both help and 
increase priority. Increase priority is now Ctrl-I. Maximize priority is
Shift-Ctrl-I, for consistency.""",
                "3296141",
            ),
            Bug(
                """The Ctrl-Enter keyboard shortcut for marking a task completed
wasn't working in the French translation.""",
                "3293786",
            ),
            Bug(
                """When quitting Task Coach in minimized mode, make sure the
main window is minimized the next session and not completely hidden.""",
                "3296144",
            ),
            Bug(
                """Packages of the previous release did not install correctly on 
some Linux distributions due to a non standard version number in the 
package (RPM or Deb).""",
                "3294852",
                "3297345",
            ),
            Bug(
                """For tasks with a non-default icon, still show the clock icon
when tracking effort.""",
                "3085094",
            ),
            Bug(
                """The width of the period column in the effort viewer would not
be reused across sessions.""",
                "3296303",
            ),
            Bug(
                """Fix session management on some Linux distributions. Also
automatically restart Task Coach when reopening the session.""",
                "3296733",
            ),
            Bug("""Category mappings in CSV import would not work"""),
            Bug(
                """On Windows, rearranging the order of the templates would have 
no effect.""",
                "3297913",
            ),
        ],
        featuresAdded=[
            Feature(
                """When importing a CSV file, let the user decide if quote
characters are escaped by doubling them or escaping them with another character."""
            ),
        ],
    ),
    Release(
        "1.2.16",
        "April 28, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """Installing as a non-admin user on Mac OS X wouldn't work.""",
                "3288682",
            ),
            Bug(
                """Don't crash when the SESSION_MANAGER environment variable is
not set (Linux).""",
                "3292509",
            ),
            Bug(
                """Update the task viewer every minute when the time left column is
shown."""
            ),
            Bug(
                """Task Coach would crash after 1 minute on XFCE.""", "3292509"
            ),
            Bug(
                """When multiple effort viewers are open, correctly remember
how effort is grouped in each effort viewer across sessions.""",
                "3294304",
            ),
        ],
        featuresAdded=[
            Feature(
                """Added a "Check for update" menu item to the help menu.""",
                "http://uservoice.com/a/dwNJ0",
            ),
            Feature(
                """Allow for exporting to HTML with CSS style information
included in the HTML file.""",
                "http://uservoice.com/a/i1LqL",
            ),
        ],
    ),
    Release(
        "1.2.15",
        "April 23, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """When deleting items, correctly move the selection.""",
                "3056999",
            ),
            Bug(
                """Saving would fail when the task file contains deleted tasks
with prerequisite tasks.""",
                "3290163",
                "3290300",
            ),
            Bug(
                """Try to guess the correct encoding when dragging and dropping
email messages from Outlook.""",
                "3288820",
            ),
        ],
        featuresAdded=[
            Feature(
                """Added a "Help improve translations" menu item to the 
help menu.""",
                "http://uservoice.com/a/468yX",
            ),
            Feature(
                """Remember size and position of edit dialogs.""",
                "http://uservoice.com/a/70ZTj",
            ),
            Feature(
                """Start effort tracking from the reminder dialog.""",
                "http://uservoice.com/a/f4UUt",
            ),
        ],
    ),
    Release(
        "1.2.14",
        "April 17, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug("""None of the translations were working.""", "3283447"),
            Bug(
                """Delete key was not working properly in the search box.""",
                "3286497",
            ),
        ],
        featuresAdded=[
            Feature("""More extensive help menu."""),
            Feature(
                """Import from CSV now includes budget, fixed fee
and hourly fee fields."""
            ),
            Feature(
                """Task Coach now supports a limited form of session
management under Windows and Linux; pending changes are automatically
saved when the user logs out."""
            ),
        ],
    ),
    Release(
        "1.2.13",
        "April 9, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """The notes section was missing from the help contents.""",
                "3241219",
            ),
            Bug(
                """Mark subtasks of tasks that have uncompleted prerequisites
as inactive (grey).""",
                "3237286",
            ),
            Bug(
                """In the setup script, don't assume Mac OS X when the operating
system isn't Linux or Windows. There's also the possibility the user is using
BSD.""",
                "3236769",
            ),
            Bug(
                """Don't force users to accept the license since the
license doesn't actually require users to accept it (Windows).""",
                "3247643",
            ),
            Bug(
                """Upon startup, effort viewers would always show the column header 
popup menu for detail mode, even when the effort viewer would be in aggregate
mode (i.e. effort aggregated per day, per week or per month)."""
            ),
            Bug(
                """Ask the user for confirmation before overwriting existing 
files.""",
                "2794041",
            ),
            Bug(
                """When adding an item, automatically select it. When removing an
item with a parent, automatically select it. Make sure keyboard navigation 
(up and down) correctly moves the selection after marking a task completed.""",
                "3056999",
            ),
        ],
        featuresAdded=[
            Feature(
                """Allow for filtering by category via the View->Filter 
menu. This also adds a menu item for showing all items regardless of 
category, with Ctrl-R (R for Reset) as keyboard shortcut."""
            ),
            Feature(
                """When possible, try to keep the task duration when
changing its start date."""
            ),
            Feature(
                """Tasks in the calendar view can now be dragged and dropped
and resized to change their dates."""
            ),
        ],
        featuresChanged=[
            Feature(
                """For consistency with the menu item for resetting category
filters, the keyboard shortcut for resetting all filters is now Shift-Ctrl-R 
(R for Reset)."""
            )
        ],
    ),
    Release(
        "1.2.12",
        "March 20, 2011",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Bring back the 'Stop tracking effort' menu item in the context
menu of task and effort viewers and make menu's more consistent.""",
                "3206702",
            ),
            Bug(
                """Added keyboard shortcuts for adding categories and notes."""
            ),
            Bug(
                """The Delete key wasn't working in text controls.""",
                "3206464",
                "3213964",
            ),
            Bug(
                """The Enter key wasn't working in text controls on Mac OS X.""",
                "3223714",
            ),
            Bug(
                """The Enter key would stop working after opening and closing a 
new viewer.""",
                "3206366",
            ),
            Bug(
                """Make Ctrl-Z (undo), Ctrl-Y (redo), Enter (edit) and Delete
work in edit dialogs."""
            ),
            Bug(
                """Fixed a performance issue with the calendar viewer when
tracking efforts."""
            ),
            Bug(
                """Don't clear the clipboard after pasting an item, so that an
item can be pasted multiple times.""",
                "3198880 ",
            ),
            Bug(
                """Don't try to add deleted prerequisite tasks when
loading the task file.""",
                "3219001",
            ),
        ],
        featuresAdded=[
            Feature(
                """Provide more options for filtering completed, due and
inactive tasks.""",
                "http://uservoice.com/a/eBFSz",
            )
        ],
    ),
    Release(
        "1.2.11",
        "March 10, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug(
                """Sometimes the total effort per period displayed in the effort
viewer would be wrong.""",
                "3146576",
            ),
            Bug(
                """On Windows, the icons of the undo and redo menu items would 
disappear after their first use."""
            ),
            Bug(
                """Correctly remember the main window position when closing 
Task Coach while the main window is minimized.""",
                "3199529",
            ),
        ],
        featuresAdded=[
            Feature("""Import tasks from CSV file."""),
            Feature(
                """In addition to hiding all completed tasks, it is now also
possible to hide completed tasks but keep recently completed tasks visible for
a limited amount of time. This can be done by hiding tasks that were completed 
before today, before yesterday, before the current week or before the current 
month, using the View->Filter menu.""",
                "http://uservoice.com/a/lZ8ss",
            ),
            Feature(
                """In addition to hiding all future tasks, it is now also
possible to hide future tasks but still show future tasks that will become
active in a short while. This can be done by hiding future tasks that start 
today, tomorrow, next week or next month, using the View->Filter menu."""
            ),
        ],
        featuresChanged=[
            Feature(
                """Keyboard shortcut improvements: On Windows and Linux, 
the keyboard shortcut for adding a task is now simply Insert. A new subtask can 
be added with Shift-Insert. On Mac OS X, the Insert shortcut doesn't work for 
some reason so there a new task can be added with Cmd-N and a new subtask with 
Shift-Cmd-N. The Delete keyboard shortcut works for all viewers. Notes can be 
added to tasks and categories with the Ctrl-B keyboard shortcut. Tasks and notes 
can be mailed with the Ctrl-M keyboard shortcut. Attachments can be added with 
the Shift-Ctrl-A keyboard shortcut and all attachments of an item can be opened 
with the Shift-Ctrl-O keyboard shortcut."""
            ),
            Feature(
                """Rearranged the menu's: Instead of a Task, Category, Effort
and Note menu, there are now a New menu for creating new items and an Actions
menu for applying actions such as marking a task completed, mailing an item
and starting and stopping effort tracking. The Edit and Delete menu items 
are now placed in the Edit menu."""
            ),
        ],
        distributionsChanged=[
            Distribution(
                """Task Coach was added to the Ports collection of FreeBSD 
thanks to Kevin Lo. See the download section of the Task Coach website."""
            )
        ],
    ),
    Release(
        "1.2.10",
        "February 20, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug("""Column header popup menu's didn't work.""", "3175083"),
            Bug(
                """The stop effort tracking button on the toolbar of effort viewers
wasn't working."""
            ),
            Bug(
                """The viewer background color would not obey the global user setting.""",
                "http://uservoice.com/a/g2CST",
            ),
            Bug(
                """Task files wouldn't specify the encoding in the XML header,
making it harder to process them with other tools.""",
                "3182504",
            ),
            Bug(
                """In the calendar viewer, use the completion date as end date when
a task is completed.""",
                "3183086",
            ),
        ],
        featuresAdded=[
            Feature(
                """Efforts are filtered by categories like tasks and notes."""
            ),
            Feature(
                """Pausing effort tracking: clicking the stop tracking effort
button when no effort is being tracked will resume tracking for the task that 
was last being tracked.""",
                "http://uservoice.com/a/cXLhb",
            ),
            Feature(
                """Start tracking effort and stop/resume tracking effort have
keyboard shortcuts: Ctrl-T for start tracking effort and Shift-Ctrl-T for 
stop/resume tracking effort.""",
                "http://uservoice.com/a/9hhaE",
            ),
            Feature(
                """Clear all filters via a keyboard shortcut: Shift-Ctrl-F""",
                "http://uservoice.com/a/4Tt4T",
            ),
            Feature(
                """Support for CRAM-MD5 authentication when dropping IMAP
mails from Thunderbird."""
            ),
        ],
        featuresChanged=[
            Feature(
                """Show left/right scroll buttons in notebook controls so that
it is more clear for users that there might be more tabs in the notebook than
currently visible. A drop down list of all tabs in the notebook can still be
accessed using the Ctrl-Tab shortcut."""
            )
        ],
    ),
    Release(
        "1.2.9",
        "February 5, 2011",
        summary="""This is a mixed bugfix and feature release.""",
        bugsFixed=[
            Bug("""Improve keyboard navigation between viewers."""),
            Bug(
                """Accept dropped mail messages from Outlook with non-ascii 
characters.""",
                "3172736",
            ),
            Bug(
                """Open editor on the same display as the main window on multi-monitor
setups.""",
                "3166563",
            ),
            Bug(
                """The shortcut for "Decrease priority" (Ctrl-D) wasn't working
in the Spanish translation.""",
                "3165234",
            ),
            Bug(
                """Prevent the tooltip overlapping popup menus on Linux.""",
                "2989198",
            ),
            Bug(
                """Dropping IMAP e-mails from Thunderbird would not work on some
configurations."""
            ),
        ],
        featuresAdded=[
            Feature(
                """Hitting Ctrl-F when a viewer has keyboard focus moves 
keyboard focus to the toolbar search control. Hitting Escape when the toolbar
search control has keyboard focus moves the focus back to the viewer. Hitting
Ctrl-Down when the toolbar search control has keyboard focus pops up the
search control menu.""",
                "http://uservoice.com/a/6fW73",
            ),
            Feature(
                """Added overview of keyboard shortcuts to help 
information."""
            ),
            Feature(
                """The calendar viewer configuration has been moved to its
own dialog. Add more configurable attributes: highlight color, show now,
font size."""
            ),
            Feature(
                """Effort viewers can be sorted ascending and descending."""
            ),
            Feature(
                """Edit, preferences and help dialogs have maximize and minimize
buttons.""",
                "http://uservoice.com/a/mymqf",
            ),
        ],
    ),
    Release(
        "1.2.8",
        "January 22, 2011",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Task Coach wouldn't open task files when a task viewer was
sorted by reminder date/time.""",
                "3153541",
            ),
            Bug(
                """Correctly fix drag-and-drop from Thunderbird.""",
                "2916405",
                "3058781",
            ),
            Bug(
                """Correctly keep track of selected items when using 
shift-click to select a range of items so that the right items are exported
when the user exports a selection.""",
                "3154036",
            ),
            Bug(
                """Task Coach would crash at launch if TaskCoach.ini could not
be loaded."""
            ),
            Bug(
                """When marking the only subtask of a task uncompleted, the 
subtask would stay green.""",
                "3151018",
            ),
            Bug(
                """On Windows 7 and Vista, the application icon wouldn't show up
correctly.""",
                "3158445",
            ),
            Bug(
                """Correctly use mail message subject when dropping a mail message from
Outlook.""",
                "2806617",
            ),
        ],
        featuresAdded=[
            Feature(
                """The effort edit dialog now has a "Edit task" button next to
the task selection drop down to quickly open the effort's task."""
            ),
            Feature(
                """The effort viewer now has "Start tracking effort" and "Stop 
tracking effort" buttons on the toolbar. The "Start tracking effort" starts 
tracking effort for the task(s) of the selected effort(s). This enables you to 
quickly resume tracking the most recent task by selecting the topmost effort 
record and hit the "Start tracking effort" button. The "Stop tracking effort" 
button simply does what it says and was added for consistencies sake.""",
                "http://uservoice.com/a/fHSAX",
            ),
        ],
    ),
    Release(
        "1.2.7",
        "January 8, 2011",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Performance improvements: faster closing of task dialogs, 
faster item selection, no redraw of task viewers every minute."""
            ),
            Bug(
                """When removing all efforts, correctly update the effort viewer.""",
                "3125553",
            ),
            Bug(
                """When editing a task that already has prerequisite tasks, don't 
reset the prerequisites.""",
                "3137055",
            ),
            Bug("""Huge performance fix in the calendar viewer."""),
            Bug(
                """When double clicking a column header border don't set the column
width to zero."""
            ),
            Bug(
                """Process drag-and-drops from Thunderbird.""",
                "2916405",
                "3058781",
            ),
            Bug(
                """When canceling the save dialog, the task file would be saved with
an empty filename.""",
                "3152160",
            ),
        ],
        featuresAdded=[
            Feature(
                """Always highlight the current day in the calendar view."""
            ),
            Feature("""Show current time in calendar view."""),
        ],
    ),
    Release(
        "1.2.6",
        "December 5, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Avoid the "Pas de sujet" bug when dropping a mail from Outlook on
a French Windows OS."""
            ),
            Bug("""Don't crash when the note viewer is open.""", "3122115"),
            Bug("""Don't crash when the square task viewer is open."""),
            Bug(
                """When double clicking the latest effort, don't open the previous
one, but the one double clicked.""",
                "3121403",
            ),
            Bug(
                """When searching in the effort viewer with "Include subitems"
turned on, actually include effort for subtasks in the search results.""",
                "3124833",
            ),
            Bug("""Some more performance improvements."""),
        ],
    ),
    Release(
        "1.2.5",
        "November 28, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Fixed another memory leak in the calendar view.""",
                "3108959",
            ),
            Bug("""Some performance improvements.""", "3117375"),
            Bug(
                """Don't throw exception when Snarl is not available.""",
                "3119740",
            ),
        ],
    ),
    Release(
        "1.2.4",
        "November 21, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """On Windows, make the installer check for running
instances of Task Coach before installing a new version. The installer is
able to detect running instances of Task Coach release 1.2.4 or newer.""",
                "3109658",
            ),
            Bug(
                """Mass editing of items wouldn't work after selecting items
with Ctrl-A (select all).""",
                "3108176",
            ),
            Bug(
                """Bring back total time spent and total revenue columns in the 
effort viewer.""",
                "3112807",
            ),
            Bug("""Fixed a memory leak in the calendar viewer.""", "3108959"),
        ],
    ),
    Release(
        "1.2.3",
        "November 14, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Show clock icon for tracked tasks in the task viewer.""",
                "3106158",
            ),
            Bug("""File => Save task as template didn't work any more."""),
            Bug(
                """Hide parent task when all of its subtasks are hidden by
filtered categories and the parent task itself doesn't belong to the
filtered categories."""
            ),
            Bug(
                """Don't throw exception when end of working day is 24.""",
                "3105496",
            ),
            Bug(
                """When recurring a task, make sure its start date stays 
before its due date. Patch provided by Svetoslav Trochev."""
            ),
            Bug(
                """The edit templates dialog was unresponsive under MS Windows.""",
                "3106221",
            ),
            Bug(
                """When setting the column width to the minimum in horizontal
monthly view, switching to weekly view would hang Task Coach and prevent
it from launching again.""",
                "3091151",
            ),
        ],
        featuresAdded=[
            Feature(
                """Updated translations and added partial Occitan and 
Papiamento translations."""
            )
        ],
    ),
    Release(
        "1.2.2",
        "November 6, 2010",
        summary="""This release adds a template edit dialog and fixes some bugs.""",
        featuresAdded=[
            Feature(
                """Don't ask for a name when creating a new template. There
is now a template edit dialog; one can only delete templates though.""",
                "http://uservoice.com/a/4Ntz6",
            ),
            Feature("""Allow the user to change the ordering of templates"""),
        ],
        bugsFixed=[
            Bug(
                """Type indicator of attachments in the attachment tab of edit
dialogs was missing.""",
                "3087177",
            ),
            Bug(
                """After editing the subject of a composite task in the task list
viewer (e.g. changing 'Project A' into 'Project B'), also update the subjects
of the subtasks (e.g. 'Project A -> Task 1' should update to 'Project B -> 
Task 1')."""
            ),
            Bug(
                """When editing a subject of a subtask in the task list viewer
inline, don't include the subjects of its ancestors in the text control."""
            ),
            Bug(
                """When filtering on categories, don't show tasks whose subtasks
(that belong to the filtered categories) are all hidden by another filter."""
            ),
            Bug(
                """When double clicking in the calendar viewer (when it is in 
vertical month mode) to create a new task, set the due date of the new task 
to the end of the day. This makes sure the new task is visible in the calendar 
after closing the task edit dialog.""",
                "3103011",
            ),
            Bug(
                """Include end of work day as option when selecting a time
in the effort edit dialog.""",
                "http://uservoice.com/a/380R8",
            ),
            Bug(
                """Remember column widths in the category viewer across 
sessions."""
            ),
        ],
        distributionsChanged=[
            Distribution("""Added support for Fedora 14.""", "3101814")
        ],
    ),
    Release(
        "1.2.1",
        "October 16, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Don't refuse to open a task file when it is sorted on a "total"
column.""",
                "3085056",
            ),
            Bug(
                """Don't expand tasks in the prerequisite tab when opening a task
dialog, it's really slow.""",
                "3085358",
            ),
            Bug(
                """Always display the month name in the horizontal monthly
calendar view.""",
                "3062505",
            ),
            Bug(
                """Allow the user to resize columns in horizontal calendar view""",
                "3062505",
            ),
            Bug("""Reset percentage complete when recurring a task."""),
            Bug(
                """When using relative paths for attachments, attachments couldn't
be opened from the attachments tab in the edit dialog.""",
                "3087177",
            ),
        ],
    ),
    Release(
        "1.2.0",
        "October 9, 2010",
        summary="""This release adds task dependencies.""",
        featuresAdded=[
            Feature(
                """Tasks can have one or more prerequisite tasks. As long as 
a task has one or more prerequisite tasks that are not completed, the 
dependent task is inactive. The task tree viewer has two extra columns,
one for showing prerequisite tasks and one for showing dependent tasks. 
Prerequisite tasks can be selected in the Prerequisites tab of the task edit 
dialog. Dependent tasks cannot be selected explicitly but are simply derived
from the prerequisite tasks. For example, if task B can be started only after 
task A has been completed, task A is called a prerequisite for task B and 
task B is called a dependency of task A."""
            )
        ],
        featuresChanged=[
            Feature(
                """To simplify the application and reduce the number of 
columns all "total" and "overall" columns have been removed. For composite 
items that have children, the tree viewers show the "total" or "overall" value 
when the item is collapsed and the individual value when the item is not 
collapsed. An example may help: suppose task A has a budget of 20 hours and 
subtask A1 has a budget of 10 hours. In the task viewer in tree mode, the 
budget column shows 20 hours for task A when it is expanded and 30 hours when 
it is collapsed. For task A1 the budget shown is always 10 hour. In list mode,
the task viewer shows the individual values, so a budget of 20 hours for task A
and 10 hours for task A1."""
            ),
            Feature(
                """The order of tabs in tabbed dialogs can be changed. 
Task Coach now remembers the order of the tabs in the item edit dialogs and 
the preferences dialog.""",
                "http://uservoice.com/a/oa7jx",
            ),
            Feature(
                """When printing, show the sorted column by underlining the
column header."""
            ),
            Feature(
                """Reorganized some menu items differently and added
mnemonics to all menu items."""
            ),
        ],
        implementationChanged=[
            Implementation(
                """The task file format was changed to support task 
dependencies. The task file format version number is now 31."""
            )
        ],
        bugsFixed=[
            Bug(
                """An exception would be thrown if search strings contained a 
percentage symbol."""
            ),
            Bug("""When printing, correctly align columns."""),
            Bug("""Show sort indicator in attachment viewers."""),
            Bug(
                """Task Coach would always change budget, hourly fee, and fixed fee
to zero when mass editing tasks.""",
                "3081666",
            ),
            Bug("""Better contrast in the calendar view""", "3072138"),
            Bug(
                """Tasks started at 00:00 would be displayed twice in the monthly
vertical calendar view""",
                "3062501",
            ),
        ],
    ),
    Release(
        "1.1.4",
        "September 30, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Task Coach would not properly use the system's locale to select
the language if the language was set to 'Let the system determine the 
language', resulting in the wrong language being used.""",
                "3064566",
            ),
            Bug(
                """Don't switch top/bottom and left/right margins in the print
preview."""
            ),
            Bug(
                """Refresh task viewer filters every minute so that
when the task viewer is hiding inactive tasks, inactive tasks that become
active also become visible.""",
                "3072013",
            ),
            Bug(
                """Displaying revenue in effort viewers was slow. 
The effort viewer has a revenue column that shows the
revenue earned per effort record. Until now, this would be the task fee per hour
times the duration of the effort record plus the part of the fixed fee of the 
task earned with this effort record. So if a task had a fixed fee of 1000,- and
you had spent 10 hours on the task, an effort record of one hour would have
a revenue of 100,-. However, calculating all this would get slow for larger 
amounts of effort records, so the effort revenue now only shows the variable
part, i.e. fee per hour times effort duration.""",
                "3056540",
            ),
            Bug(
                """In the situation where Task Coach was started minimized in the
system tray and with the setting "Hide window when minimizing" turned on,
the main window would not be hidden when minimizing it.""",
                "3077271",
            ),
        ],
        featuresAdded=[
            Feature(
                """Allow hiding composite tasks in calendar view.""",
                "http://uservoice.com/a/aul3S",
            ),
            Feature(
                """In the tree/list task viewer, allow additional selection
with Cmd-click on Mac OS X."""
            ),
        ],
    ),
    Release(
        "1.1.3",
        "September 10, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """When closing a edit dialog, don't delete the category, note,
and attachment viewers in the dialog before the data has been processed.""",
                "3059143",
            ),
            Bug(
                """The PortableApps platform would override the language selected
by the user in Task Coach.""",
                "2965342",
                "3059429",
            ),
            Bug(
                """When retrieving the latest available Task Coach version number
from the Task Coach website doesn't work, simply ignore that."""
            ),
            Bug(
                """Don't crash when searching efforts with "Include subitems" turned
on."""
            ),
        ],
        featuresAdded=[
            Feature(
                """When selecting the language in the preferences dialog, you
can select 'Let the system determine the language'. If you're using the 
PortableApps version of Task Coach and the PortableApps platform, the 
PortableApps platform language will be used. Otherwise, Task Coach
will let your system's locale determine the language."""
            )
        ],
    ),
    Release(
        "1.1.2",
        "September 2, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Task Coach wouldn't run on Ubuntu 9.04. This is because Task
Coach tried to use a feature from wxPython 2.8.9.2 while Ubuntu 9.04 ships with
wxPython 2.8.9.1.""",
                "3054431",
            ),
            Bug(
                """Only close edit dialogs when the edited item is really deleted,
not when the item is hidden by a filter.""",
                "3042880",
            ),
            Bug(
                """Refresh filtered task viewers at midnight to properly show 
tasks that become active.""",
                "3035384",
            ),
            Bug(
                """The checkbox for mutually exclusive subcategories in the 
category editor would be unchecked even if a category had exclusive 
subcategories."""
            ),
        ],
    ),
    Release(
        "1.1.1",
        "August 26, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """On Mac OS X, properly read task files when the font description
cannot be parsed. This may happen when reading a task file that was last
saved on a different platform. Unfortunately, font specifications are platform
specific.""",
                "3047183",
            ),
            Bug("""Prevent exception when reading old task files."""),
            Bug(
                """Saving of templates didn't work, resulting in invalid template
files that would in turn prevent Task Coach from starting properly.""",
                "3052090",
            ),
            Bug(
                """On Windows, the tabs of the dialogs would flicker when moving
the mouse over the tabs."""
            ),
            Bug("""Use dialogs for reminders.""", "3050445"),
        ],
    ),
    Release(
        "1.1.0",
        "August 20, 2010",
        summary="""This release adds time to start, due and completion dates of 
tasks and adds support for mass editing of items. It also adds support for the
upcoming version 3.0 for the iPhone/iPod/iPad.""",
        featuresAdded=[
            Feature(
                """The start, due and completion dates of tasks now also include
a time. When reading old task files, Task Coach adds a default time to tasks: 
start dates get a time of "00:00", due dates and completion dates get a time
of "23:59".""",
                "http://uservoice.com/a/nd3mH",
            ),
            Feature(
                """Mass editing of items. When editing multiple items (tasks, 
notes, etc.), the edit dialog allows for selectively changing attributes
of all edited items.""",
                "http://uservoice.com/a/ahxq8",
            ),
            Feature("""Less intrusive notifications (reminders)."""),
            Feature("""The calendar orientation can be changed."""),
            Feature(
                """Add an option to the calendar viewer to show all tasks but
those which have no start nor due date""",
                "3008517",
            ),
            Feature(
                """The headers in the calendar view are now always visible.""",
                "http://uservoice.com/a/irtQs",
            ),
            Feature(
                """The calendar view can show an arbitrary number of periods
(except months).""",
                "http://uservoice.com/a/5F5Ka",
            ),
        ],
        implementationChanged=[
            Implementation(
                """The task file format was changed to support start, due
and completion date and time. The task file format version number is now 30."""
            )
        ],
        bugsFixed=[
            Bug(
                """Icons in edit dialogs would be lined up vertically on some 
versions of Windows XP. Fixed by using a notebook widget instead of the
listbook widget.""",
                "2927384",
            ),
            Bug(
                """The new edit dialogs better support tabbing through the dialogs.""",
                "2687959",
            ),
            Bug(
                """On Mac OS X, the tabs in the editor and preferences dialogs were
too small."""
            ),
            Bug(
                """Searching descriptions wasn't working in the effort viewer.""",
                "3031411",
            ),
        ],
    ),
    Release(
        "1.0.10",
        "August 15, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """When SyncML was on, the effort viewer would show effort for 
deleted tasks."""
            ),
            Bug(
                """When dragging panes and dropping them onto each other to create
an automatic notebook, make sure dropped viewers are properly contained in 
the notebook."""
            ),
            Bug(
                """When renaming a viewer, apply the new name to the active
viewer.""",
                "3042037",
            ),
        ],
        featuresAdded=[
            Feature(
                """Allow automatic creation of a notebook of viewers on top
of the initial task viewer. This makes the user interface functionally 
equivalent to the previously removed "tabbed" mode."""
            )
        ],
    ),
    Release(
        "1.0.9",
        "August 8, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """On Windows, Task Coach wouldn't start when the user interface
was in "tabbed" mode.""",
                "3041123",
            ),
            Bug(
                """On Windows, toolbar items that should trigger a popup menu 
(e.g. templates) wouldn't."""
            ),
            Bug(
                """On Windows, disabled toolbar buttons wouldn't be greyed out."""
            ),
        ],
        featuresRemoved=[
            Feature(
                """The "tabbed" user interface mode has been removed. 
Having two different user interfaces makes it harder to test changes that
affect the user interface, as evidenced by a bug in the previous release."""
            )
        ],
    ),
    Release(
        "1.0.8",
        "August 6, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Drop support for SyncML on Debian; too many architectures/versions
to support."""
            ),
            Bug("""File attachments would not open on Lubuntu"""),
            Bug("""Task Coach would crash on start on Ubuntu 10.10"""),
            Bug(
                """Fix an exception that would prevent Task Coach from closing.""",
                "3031709",
                "3031711",
            ),
            Bug(
                """Close task tree popup (in the effort dialog) when clicking
the dropdown button twice.""",
                "3032835",
            ),
            Bug(
                """On Windows, toolbar buttons in dialogs would stop working after 
a while.""",
                "3032834",
                "2560895",
            ),
            Bug(
                """Refresh filter for tasks due today/tomorrow/etc. at midnight.""",
                "3035384",
            ),
            Bug(
                """On Linux, when selecting an effort in the effort viewer with
the mouse also give keyboard focus to the effort viewer.""",
                "3039519",
            ),
        ],
    ),
    Release(
        "1.0.7",
        "July 2, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """On some Linux platforms, when using KDE, Task Coach would 
not properly restore after being minimized to the system tray.""",
                "2988693",
                "3011539",
            ),
            Bug(
                """Reduce flickering when tracking effort.""",
                "2819141",
                "2995374",
            ),
            Bug("""Task Coach wasn't installing on Ubuntu 9.04.""", "3022926"),
            Bug(
                """The right-click column header menu still wasn't working in task,
note and category viewers."""
            ),
        ],
    ),
    Release(
        "1.0.6",
        "June 26, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """The right-click column header menu wasn't working in task,
note and category viewers."""
            ),
            Bug("""On Jolicloud, don't crash when printing.""", "3018038"),
            Bug(
                """On Ubuntu 10.4, don't crash when clicking the font button in 
the appearance tab of edit dialogs.""",
                "2992006",
                "3021759",
            ),
            Bug(
                """Don't display long descriptions in an inline text control,
it's too buggy.""",
                "2992853",
                "2992850",
                "2992848",
            ),
            Bug(
                """On Mac OS X, don't cut text in text controls when users
type <cmd><shift>X, only when they type <cmd>X.""",
                "2942288",
            ),
            Bug(
                """Properly save the task file when the font name contains
non-ascii characters.""",
                "3014110",
            ),
            Bug(
                """Correctly export tasks and effort to vCalendar (.ics) when they
contain non-ascii characters.""",
                "3016528",
            ),
        ],
    ),
    Release(
        "1.0.5",
        "June 8, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Task Coach would fail to save the task file correctly, when 
it couldn't read temporary files for email attachments.""",
                "2369711",
            ),
            Bug(
                """Don't crash when using a purple folder or led icon.""",
                "3009432",
            ),
            Bug(
                """Don't allow exporting efforts to iCalendar when effort viewer is
in aggregate mode, it would result in an empty .ics file.""",
                "2935616",
            ),
            Bug(
                """SyncML synchronization did not work for tasks.""", "3012234"
            ),
        ],
        featuresChanged=[
            Feature(
                """Renamed the Edit->Paste into task menu item to 
Edit->Paste as subitem and made it work for categories and notes too."""
            )
        ],
    ),
    Release(
        "1.0.4",
        "May 30, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """When starting iconized on Mac OS X, the application window
would close.""",
                "2992764",
            ),
            Bug(
                """When exporting tasks with descriptions that contain newlines
to iCalendar (.ics) format, produce a valid iCalendar file.""",
                "2975805",
            ),
            Bug(
                """When reading a task file saved on another platform, be prepared 
for fonts with size zero; use the default font size instead.""",
                "2968199",
                "3002577",
            ),
            Bug(
                """After deleting multiple efforts for one task in the effort 
viewer, the effort viewer would still show some of the removed efforts."""
            ),
            Bug(
                """When waking up from standby/sleep, only request user 
attention when there are reminders to display.""",
                "2992049",
            ),
            Bug(
                """The synchronization with the iPhone would crash in some
circumstances, when parent objects have been used on the iPhone and
are deleted on the desktop.""",
                "3007248",
            ),
            Bug(
                """When maximizing or minimizing priority, don't take the priority
of deleted tasks into account.""",
                "3008495",
            ),
            Bug(
                """When calculating overall percentage complete of a task, consider
whether the task will be completed automatically when all of its subtasks
are completed.""",
                "2992534",
            ),
        ],
        featuresChanged=[
            Feature(
                """Added some more possible snooze times. Use the preferences
dialog to turn them on."""
            )
        ],
        distributionsChanged=[
            Distribution(
                """We no longer build a Task Coach RPM for Fedora 8, 9, 
and 10. These releases of Fedora are unsupported by the Fedora project."""
            ),
            Distribution(
                """The OpenSuse RPM is not "noarch" but "i386".""", "2997377"
            ),
        ],
    ),
    Release(
        "1.0.3",
        "April 25, 2010",
        summary="""This release fixes a few bugs, and improves a few features, such
as making the calendar view sortable.""",
        bugsFixed=[
            Bug(
                """When showing effort records in aggregate mode (per day, per week,
per month), always put the Total row on the first line of its period.""",
                "2895940",
            ),
            Bug(
                """The download link for the Debian package wasn't pointing at any
package.""",
                "2985649",
            ),
            Bug(
                """Don't show deleted tasks in the task dropdown of the effort
edit dialog.""",
                "2987202",
            ),
            Bug(
                """Snarl notifications wouldn't work when the subject or
description included non-ASCII characters.""",
                "2986071",
            ),
            Bug(
                """When saving files, make sure the default extension is added to 
filenames if both the user and the native save dialog don't add it.""",
                "2987204",
            ),
            Bug(
                """When listing notes and attachment in a popup window, show
them sorted instead of in a seemingly random order.""",
                "2991230",
            ),
            Bug(
                """Don't crash and corrupt the task file when the user
assigns the green folder icon to a task, category or note.""",
                "2991511",
            ),
            Bug(
                """Tasks wouldn't use the exact same font as the category they
belong to.""",
                "2990350",
            ),
            Bug(
                """The calendar view didn't handle the task's font.""",
                "2990875",
            ),
        ],
        featuresAdded=[
            Feature(
                """Use item titles in dialogs and in the undo/redo menu to
make it clearer what items the user is/was working on.""",
                "http://uservoice.com/a/9zBuo",
            ),
            Feature(
                """In the task, category, and note viewers, show long
descriptions in a text control with scrollbars so the rows don't take up too
much vertical space.""",
                "http://uservoice.com/a/h37jH",
            ),
            Feature("""Tasks can now be sorted in the calendar viewer."""),
            Feature("""Support for libnotify under Linux (for reminders)."""),
        ],
    ),
    Release(
        "1.0.2",
        "April 10, 2010",
        summary="""This release fixes some bugs, and adds support for the Snarl
notification system.""",
        bugsFixed=[
            Bug(
                """Exports and prints would show long descriptions abbreviated with
"...", exactly as the long descriptions were displayed in the description 
column of task, category, and note tree viewers. To fix this, the task, 
category, and note tree viewers show descriptions fully (when the description 
column is visible).""",
                "2975805",
            ),
            Bug(
                """In the calendar viewer, March 31st would not appear.""",
                "2979461",
            ),
            Bug(
                """The 13th hour would not show up in thr daily calendar view.""",
                "2979452",
            ),
            Bug(
                """The position of the main window wouldn't be saved so it
couldn't be restored the next session.""",
                "2969292",
            ),
            Bug(
                """On Ubuntu, when the user would scroll to the bottom of a tree
viewer and collaps an item, the tree would not be redrawn correctly.""",
                "2947136",
            ),
            Bug(
                """Setting a task to 100 percent complete didn't work.""",
                "2982561",
            ),
            Bug(
                """When the user clicks on a URL embedded in a description
and the URL fails to open, show an error dialog instead of throwing an 
exception."""
            ),
            Bug(
                """The website pointed Ubuntu 9.10 users to the wrong deb package.""",
                "2983202",
            ),
            Bug(
                """On Ubuntu 10.04, Task Coach wouldn't be added to the Applications/Office menu.""",
                "2978098",
            ),
            Bug(
                """After double clicking a task in the calendar viewer and
changing its dates, if the change would make the task disappear from the
current period, the task would not be properly drawn."""
            ),
        ],
        featuresAdded=[
            Feature("""Support for Snarl under Windows (for reminders)."""),
        ],
    ),
    Release(
        "1.0.1",
        "March 26, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Task Coach would try to use a non-existing icon when
the SyncML feature was turned on.""",
                "2975952",
            ),
            Bug(
                """Task Coach wouldn't install properly on Ubuntu 10.04. Added
a deb for Ubuntu 10.04.""",
                "2975538",
            ),
            Bug(
                """When setting the end working hour to 24, the calendar viewer
would crash.""",
                "2975347",
            ),
            Bug(
                """When trying to display tasks with notes, the calendar viewer
would crash."""
            ),
            Bug(
                """Synchronization with the iPhone did not work.""",
                "2975920",
                "2976427",
            ),
        ],
    ),
    Release(
        "1.0.0",
        "March 22, 2010",
        summary="""To mark that Task Coach has been available for five years
now, we call this release version 1.0. This release adds a calendar viewer
for tasks, partial drag and drop support for Mail.app under Mac OS X Leopard
and Snow Leopard, and configurable icons.""",
        featuresAdded=[
            Feature(
                """Calendar viewer for tasks.""",
                "http://uservoice.com/a/iQI4g",
            ),
            Feature(
                """Drag and drop e-mail from Mail.app, on Max OS X Leopard and
Snow Leopard.""",
                "http://uservoice.com/a/niJMS",
            ),
            Feature(
                """The square map task viewer can also display tasks by
priority. Note that tasks with negative priorities are not displayed.""",
                "http://uservoice.com/a/kxeoS",
            ),
            Feature(
                """The icons of tasks, notes, and categories can be changed."""
            ),
        ],
        bugsFixed=[
            Bug(
                """The template pop-up menu in task viewers would not show up
at the right position."""
            )
        ],
    ),
    Release(
        "0.78.4",
        "March 6, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """In some cases, when typing dates in the editor, they would
be reset to the current day.""",
                "2942425",
            ),
            Bug(
                """Clear the drag image after dropping an item onto white space 
(on Linux).""",
                "2947127",
            ),
            Bug(
                """Reminders that should have fired when the computer was asleep
wouldn't until the next launch of Task Coach (Windows and Mac OS X only).""",
                "2888688",
            ),
            Bug(
                """On Mac OS X, task viewers would not be refreshed at midnight
if the computer was sleeping by this time."""
            ),
            Bug(
                """Having too many mail attachments on Windows would cause a
"Too many open files" error."""
            ),
            Bug(
                """When closing a viewer, Task Coach would sometimes try to destroy
an already deleted right-click menu, leading to an exception or an error
message in the log file.""",
                "2948302",
            ),
        ],
    ),
    Release(
        "0.78.3",
        "January 31, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Free up resources (user objects and memory) on Windows when
closing dialogs. The memory leak was caused by popup menu's in dialogs not
being deleted.""",
                "2938091",
                "2891350",
                "2560895",
                "2444185",
                "2214043",
            ),
            Bug(
                """Close the inline subject edit control before showing or hiding
columns in tree viewers, to prevent problems redrawing the tree items.""",
                "2940211",
            ),
            Bug(
                """Prevent "zombie" viewers; viewers that are not visible but do
still use processing power.""",
                "2932609",
            ),
        ],
    ),
    Release(
        "0.78.2",
        "January 23, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[Bug("""Faster redrawing of task/category/note trees.""")],
    ),
    Release(
        "0.78.1",
        "January 17, 2010",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Bring back the "Don't snooze" option in reminder dialogs."""
            ),
            Bug("""Synchronizing with the iPhone didn't work.""", "2925618"),
            Bug(
                """When an active task's foreground color is the default (black),
don't mix that color with the foreground colors of the task's categories.""",
                "2930751",
            ),
            Bug(
                """Let subtasks use their parent's category-based foreground
color when they don't have their own foreground color.""",
                "2930751",
            ),
            Bug(
                """When there are a lot of old backup files don't clean them
up all at once, but instead a few on each save.""",
                "2929692",
                "2929475",
            ),
        ],
    ),
    Release(
        "0.78.0",
        "January 10, 2010",
        summary="""This release adds configurable fonts and foreground colors,
enhances the reminder dialog, makes other small changes and fixes some bugs.""",
        featuresAdded=[
            Feature(
                """Tasks, categories, notes and attachment can have their own
font. Tasks, notes and attachments that don't have their own font use the font
of the categories they belong to. Effort records use the font of the task they
belong to."""
            ),
            Feature(
                """In addition to the background color, the foreground (text) 
color of tasks, categories, notes and attachments can now also be changed. 
Tasks, notes and attachments that don't have their own foreground color use the 
foreground color of the categories they belong to. Effort records use the 
foreground color of the task they belong to."""
            ),
            Feature(
                """Added Ctrl+E keyboard shortcut to "New effort..." menu 
item."""
            ),
            Feature(
                """Reminder dialogs have an extra button to mark the  
task completed.""",
                "http://uservoice.com/a/5HVq3",
            ),
            Feature(
                """The snooze times offered by the reminder dialog can be
configured via the preferences dialog."""
            ),
        ],
        bugsFixed=[
            Bug(
                """Make file locking work on Windows computers that have a  
hostname with non-ASCII characters in it.""",
                "2904864",
            ),
            Bug(
                """Avoid deploying UxTheme.dll because it causes problems
on 64-bits Windows systems.""",
                "2911280",
                "2897639",
                "2886396",
            ),
            Bug(
                """Correctly refresh task square map and task time line viewers
after stopping effort tracking, i.e. stop showing the clock icon on the
previously tracked task."""
            ),
            Bug(
                """When maximizing and restoring panes (viewers), don't change the 
order.""",
                "2922952",
            ),
            Bug(
                """Slightly faster redrawing of task viewers after sorting or 
filtering."""
            ),
            Bug(
                """In some circumstances, synchronization with an iPhone/iPod
Touch device would crash the app.""",
                "2925618",
            ),
        ],
        featuresChanged=[
            Feature(
                """Task Coach now limits the number of backups made of a task 
file. The number of backups retained increases logarithmically with the age 
of the oldest backup of the task file. When Task Coach needs to remove a backup
it tries to keep the remaining backups spread evenly across time.""",
                "http://uservoice.com/a/5FrtF",
            ),
            Feature(
                """Merged the four menu items for exporting tasks and effort to 
iCalendar and vCalendar formats into two menu items."""
            ),
        ],
    ),
    Release(
        "0.77.0",
        "December 6, 2009",
        summary="""This release adds mutually exclusive categories and fixes some
bugs.""",
        featuresAdded=[
            Feature(
                """Categories can have mutually exclusive subcategories. This
makes it easier to e.g. create your own statuses or to keep track of which
task was assigned to whom.""",
                "http://uservoice.com/a/tvOIS",
            ),
            Feature(
                """F2 can be used to start in-line editing of the subject of a 
task, category or note.""",
                "http://uservoice.com/a/9pLUT",
            ),
            Feature("""Added partial Mongolian translation."""),
        ],
        bugsFixed=[
            Bug(
                """Only the first reminder defined in a session
would be fired.""",
                "2901254",
            ),
            Bug(
                """Don't start in-line editing of subjects when an item is double
clicked. Properly close the subject edit text control, e.g. when sort order
is changed.""",
                "2896654",
                "2899913",
            ),
            Bug(
                """Don't open effort viewer contex (right-click) menu twice on
every right-click.""",
                "2902389",
            ),
        ],
    ),
    Release(
        "0.76.1",
        "November 13, 2009",
        summary="""This release adds Growl support on Mac OS X, and fixes
some bugs.""",
        featuresAdded=[
            Feature(
                """On Mac OS X, you can optionally choose to use Growl for
reminders. When enabled, this disables two other features: snooze/don't snooze
and open task on reminder."""
            ),
            Feature(
                """Added back the possibility to hide active tasks so that 
people can have a task viewer that only displays completed tasks.""",
                "http://uservoice.com/a/NQCUV",
            ),
        ],
        bugsFixed=[
            Bug(
                """The notes and attachment columns were not properly refreshed
after removing the last note or attachment.""",
                "2894530",
            ),
            Bug("""Reminders would randomly not work.""", "2888688"),
            Bug(
                """Recurrence frequency would be reset to zero when edited.""",
                "2895085",
            ),
            Bug(
                """Instead of the whole description, show only the first few lines 
of descriptions in the description column of task, note, and category 
viewers."""
            ),
        ],
    ),
    Release(
        "0.76.0",
        "November 7, 2009",
        summary="""This release adds buttons on the toolbar of task viewers to
hide completed and/or future tasks, makes subjects editable in-line, removes
a couple of silly features, and fixes some bugs.""",
        featuresAdded=[
            Feature(
                """Task viewers now have buttons on the toolbar to hide or 
show completed and/or inactive (future) tasks.""",
                "http://uservoice.com/a/EfkNL",
            ),
            Feature(
                """Subjects of tasks, notes and categories can be edited in-line
by clicking the subject of a selected item."""
            ),
        ],
        bugsFixed=[
            Bug("""Iterating over viewers wasn't working in tabbed mode."""),
            Bug(
                """When merging a task file with categories, don't break the 
links between tasks/notes and categories.""",
                "2882493",
            ),
            Bug(
                """Tree viewers wouldn't properly refresh when an attribute of
a task, category, or note was changed to be empty.""",
                "2806354",
            ),
            Bug(
                """When tracking effort, effort viewers in aggregated mode (showing
effort per day/week/month) were not being updated every second."""
            ),
            Bug("""Tabs in the tabbed window layout could not be closed."""),
            Bug(
                """Don't complain when the system locale has a thousands separator
that consists of more than one character.""",
                "2889931",
                "2888714",
            ),
        ],
        featuresRemoved=[
            Feature(
                """Don't have a setting for the maximum number of recent files
to show, simply use some reasonable maximum (9)."""
            ),
            Feature(
                """It's no longer possible to hide active tasks, over budget 
tasks, and overdue tasks. These filters were silly."""
            ),
        ],
    ),
    Release(
        "0.75.0",
        "October 24, 2009",
        summary="""This release adds percentage complete tracking for tasks,
a PortableApps version of Task Coach and some minor features and bug fixes.""",
        featuresAdded=[
            Feature(
                """Tasks have a percentage complete property.""",
                "http://uservoice.com/a/Icogx",
            ),
            Feature(
                """Double clicking the task bar icon will iconize the main
window when it is visible and restore it when iconized (Mac OS X and 
Windows).""",
                "http://uservoice.com/a/dKfBt",
            ),
            Feature(
                """When browsing for an attachment, start in the
current attachment directory."""
            ),
            Feature(
                """Under Windows, prevent users from deleting
temporary files and thus loosing all their e-mail attachments."""
            ),
        ],
        bugsFixed=[
            Bug("""Make opening (task) edit dialogs faster.""", "2884522"),
            Bug(
                """Use 'now' as default time in effort dialogs on Mac OS X 
instead of '0:00:00'.""",
                "2874824",
            ),
        ],
        distributionsChanged=[
            Distribution(
                """Added a PortableApps version of Task Coach to the 
set of available distributions."""
            )
        ],
    ),
    Release(
        "0.74.4",
        "October 17, 2009",
        summary="""This is a bugfix release that fixes some user interface
bugs, most notably that entering dates with the keyboard was not working 
on Mac OS X and Linux.""",
        bugsFixed=[
            Bug(
                """Typing in time controls (effort start and stop, reminder)
didn't work on Mac OS X.""",
                "2798239",
            ),
            Bug(
                """Prevent the locked file dialog and the new 
version notification dialog of blocking each other on Mac OS X."""
            ),
            Bug(
                """When using the context menu of a selected effort record to 
create a new effort record use the task of the selected effort record as 
task of the new effort record as well.""",
                "2873933",
            ),
            Bug(
                """After expanding all items (Shift+Ctrl+E), keep items expanded
even when sort order changes or tasks are completed.""",
                "2841854",
            ),
            Bug(
                """The "Open all attachments" menu item was always disabled.""",
                "2874180",
            ),
            Bug(
                """When sorting tasks and notes by their categories use the 
recursive subjects (e.g. 'Parent -> Child') of the categories to sort by. 
Previous versions would only use the 'Child' part.""",
                "2874153",
            ),
            Bug(
                """Remove double slash ('//') from URL used in Windows 
installer.""",
                "2877126",
            ),
            Bug(
                """On Linux and Mac OS X, changing dates by typing a new date 
(i.e. not using the dropdown menu) didn't work.""",
                "2874408",
                "2867623",
            ),
        ],
    ),
    Release(
        "0.74.3",
        "October 4, 2009",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Exporting and printing, including displaying the print preview,
is now much faster."""
            ),
            Bug("""Drag and drop wasn't working."""),
            Bug(
                """Starting or stopping effort tracking for a selected task
would cause the task to be unselected.""",
                "2869959",
            ),
            Bug(
                """Don't show effort records twice in the effort viewer after 
deleting or dragging and dropping a task.""",
                "2869520",
                "2859882",
            ),
            Bug("""Fix printing of non-task viewers.""", "2871365"),
            Bug(
                """Task Coach wouldn't start when using the tabbed main window
mode on Mac OS X.""",
                "2867585",
            ),
        ],
    ),
    Release(
        "0.74.2",
        "September 25, 2009",
        summary="""This is a bugfix release that fixes several minor bugs and
increases performance.""",
        bugsFixed=[
            Bug(
                """iPhone synchronization: when doing a full refresh
from desktop, categories parents could be mismatched."""
            ),
            Bug(
                """A bug in the task filter would cause tasks to be shown that
were supposed to be hidden.""",
                "2841854",
            ),
            Bug(
                """The filter submenu would sometimes be in the wrong
state (enabled or disabled)."""
            ),
            Bug(
                """On Linux, locking two task files in the same folder, e.g. when 
merging, would make Task Coach think that its task file was locked by another 
instance of Task Coach.""",
                "2852216",
            ),
            Bug(
                """Performance improvements. Task Coach still isn't super fast,
but at least performance should be a bit better now.""",
                "2807678",
                "2683002",
            ),
        ],
        featuresAdded=[
            Feature(
                """Add an option to avoid uploading completed tasks to
the iPhone/iPod Touch when synchronizing. For people who hide completed
tasks, this can make the synchronization much quicker."""
            ),
            Feature(
                """Under MS Windows, the task template directory
may now be a shortcut to another directory."""
            ),
            Feature(
                """In the attachment viewer, display a red icon for
files attachments when the file does not exist. Also prevent the user
from trying to open it."""
            ),
        ],
        featuresRemoved=[
            Feature(
                """Removed the Edit->Select->Invert selection menu item since
it was very slow and not very useful."""
            )
        ],
    ),
    Release(
        "0.74.1",
        "August 22, 2009",
        summary="""This is a bugfix release.""",
        featuresAdded=[
            Feature(
                """Drag and drop from Thunderbird now works with multiple
accounts in the default profile."""
            )
        ],
        bugsFixed=[
            Bug("""Printing didn't work.""", "2840010"),
            Bug(
                """Prevent exception when locking a file on a machine with a
hostname containing non-ascii characters.""",
                "2835047",
            ),
            Bug(
                """Make the winPenPack portable app start in English 
by default."""
            ),
            Bug(
                """Drag and drop from Thunderbird would not work if the storage
directory wasn't the default.""",
                "2840460",
            ),
            Bug("""Expand parent item when adding a sub item."""),
        ],
    ),
    Release(
        "0.74.0",
        "August 16, 2009",
        summary="""This release adds better HTML export, a winPenPack version of
Task Coach, and fixes some bugs. Task Coach now uses Uservoice.com for
feature requests.""",
        featuresAdded=[
            Feature(
                """When exporting data to an HTML file, Task Coach writes a
simple CSS stylesheet alongside it. The CSS stylesheet can be edited by the 
user using a text editor; Task Coach won't overwrite it."""
            ),
            Feature(
                """Tasks that are due soon are colored orange. How many
days left is to be considered 'soon' can now be set via the preferences dialog, 
in the task behavior tab.""",
                "1312000",
            ),
        ],
        bugsFixed=[
            Bug(
                """Avoid nested syncml tags in the XML task file""",
                "2832062",
                "2813816",
            ),
            Bug(
                """Some macro's (e.g. "%(name)s") in the help text were not 
properly expanded.""",
                "2833904",
                "2833903",
            ),
            Bug(
                """Translate tip window and search controls on Windows.""",
                "2825463",
            ),
        ],
        distributionsChanged=[
            Distribution(
                """Added a winPackPen (http://www.winpackpen.com) 
portable package to the set of available distributions."""
            )
        ],
        websiteChanges=[
            Website(
                """We're now using http://taskcoach.uservoice.com for feature 
requests. The big advantage of Uservoice over the Sourceforge feature request 
tracker is that Uservoice allows for voting. Because we have over 250 open 
feature requests on Sourceforge, it is not possible for us to move all 
feature requests ourselves. People that submitted a feature request on 
Sourceforge will receive a notification and a request to help us move their 
request(s) to Uservoice.""",
                "index.html",
            )
        ],
    ),
    Release(
        "0.73.4",
        "August 6, 2009",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Prevent text in right-aligned columns, like dates in
the task viewer, to be partially cut off.""",
                "2806466",
            ),
            Bug(
                """Don't crash when a template task has an empty subject.""",
                "2831233",
            ),
            Bug(
                """Always show the correct 'mark task (un)completed' bitmap in the 
task context menu.""",
                "2830125",
            ),
            Bug(
                """The GUI would always display English, instead of the language
set via the preference dialog or specified on the command line.""",
                "2831534",
            ),
        ],
    ),
    Release(
        "0.73.3",
        "August 2, 2009",
        summary="""This release fixes some bugs, and adds support for synchronizing
with the next version of the iPhone app (1.1).""",
        bugsFixed=[
            Bug(
                """Opening the task menu in the main menu bar while a category 
viewer was active would result in exceptions.""",
                "2818254",
            ),
            Bug(
                """The time control in the effort editor was too narrow""",
                "2790805",
            ),
            Bug(
                """Link to http://www.cygwin.com on the website had a typo.""",
                "2819702",
            ),
            Bug("""The context menu key didn't work.""", "2807326"),
            Bug(
                """With SyncML enabled, tasks deleted on the desktop would still 
show up on the iPhone/iPod Touch."""
            ),
            Bug(
                """Translate tip window controls, search controls, and
viewer titles.""",
                "2825463",
                "2825222",
            ),
            Bug("""Prevent exception when opening a new viewer.""", "2825222"),
            Bug(
                """Don't fail silently when something goes wrong while opening 
an attachment.""",
                "2826178",
            ),
        ],
        featuresAdded=[
            Feature(
                """Specify which language to use on the command line. Type
"taskcoach[.py|.exe] --help" on the command line for more information."""
            ),
            Feature(
                """Load a .po file (a file containing translations) with a 
command line option. Type "taskcoach[.py|.exe] --help" on the command line for 
more information. This option allows translators to check their work more 
easily.""",
                "1599933",
            ),
            Feature(
                """Synchronizing with the next version for the iPhone (1.1) is
now supported (one can edit a task's categories from the device)."""
            ),
        ],
    ),
    Release(
        "0.73.2",
        "July 8, 2009",
        summary="""This release fixes some bugs, and adds synchronization with
the iPhone version now available on the AppStore.""",
        featuresAdded=[
            Feature(
                """Two-way synchronization with Task Coach for the iPhone.""",
                "2042153",
                "2722216",
            ),
        ],
        bugsFixed=[
            Bug(
                """Export of selected effort to a CSV-file would result in an empty 
file.""",
                "2810978",
            ),
            Bug(
                """Fix a crash when creating/editing tasks for non-english
locales.""",
                "2817287",
                "2817335",
                "2812005",
            ),
        ],
    ),
    Release(
        "0.73.1",
        "June 24, 2009",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Dates and amounts were not localized.""",
                "2806189",
                "1625111",
                "1790055",
            ),
            Bug(
                """Use folder icons for tasks with subtasks in the task viewer.""",
                "2806191",
            ),
            Bug(
                """Export of selected effort to a CSV-file would result in an empty 
file.""",
                "2806383",
                "2807003",
                "2810978",
            ),
        ],
    ),
    Release(
        "0.73.0",
        "June 12, 2009",
        summary="""This release adds a timeline viewer, the ability to search
item descriptions, total-per-period information in the effort viewer, and
easier category manipulation.""",
        featuresAdded=[
            Feature(
                """Added a timeline viewer that shows tasks and efforts on 
a horizontal time scale.""",
                "2533644",
                "1230080",
            ),
            Feature(
                """When an effort viewer is displaying effort per day, week,
or month, a total line is shown for each period.""",
                "1962219",
            ),
            Feature(
                """The search control in the toolbar of viewers now includes
an option to search descriptions too.""",
                "1816660",
                "2020347",
                "2157010",
                "2510045",
            ),
            Feature(
                """Add or remove tasks and notes from categories using the
task and note menus in the menubar or the right-click popup menu for tasks
and notes.""",
                "1931323",
                "2011031",
                "1918685",
            ),
            Feature(
                """Added largely incomplete Bosnian and Basque 
translations. Please help make these translations complete. 
See http://www.taskcoach.org/i18n.html."""
            ),
        ],
    ),
    Release(
        "0.72.10",
        "June 9, 2009",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """When opening a task edit dialog, the priority field would not
show the priority until the up or down button was clicked (Mac OS X only)."""
            ),
            Bug(
                """When opening a locked file, Task Coach would hang
(Mac OS X only)."""
            ),
            Bug(
                """Require wxPython 2.8.9.1 instead of 2.8.9.2 in the Debian 
package file (.deb) because Ubuntu 9.04 is still shipping 2.8.9.1 (Ubuntu 
only).""",
                "2798457",
            ),
            Bug(
                """Fix drag and drop from Outlook (Windows only).""", "2803013"
            ),
            Bug(
                """When logging off or shutting down the computer save unsaved 
changes (Linux only)."""
            ),
            Bug("""When using SyncML the task file could get corrupted."""),
        ],
    ),
    Release(
        "0.72.9",
        "May 28, 2009",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Don't throw an exception when exporting an active effort record
to iCal format."""
            ),
            Bug(
                """Refuse to open task files that have a different format because
they are created by a newer version of Task Coach than the one the user is 
using."""
            ),
            Bug(
                """Updating menu items would trigger exceptions after closing a
(task) viewer."""
            ),
            Bug(
                """After merging, Task Coach would display the wrong filename in the
window title."""
            ),
            Bug(
                """Smaller task edit dialog to cater for lower resolution 
screens.""",
                "2214687",
            ),
            Bug(
                """Dragging email from a Thunderbird client that uses Gmail as IMAP
server didn't work."""
            ),
            Bug(
                """When the SyncML feature is turned on, Task Coach would show 
deleted tasks in the drop down menu of the start effort tracking button on the 
toolbar and it would show effort for deleted tasks in the effort viewer.""",
                "2679544",
                "2214043",
            ),
        ],
        featuresAdded=[
            Feature(
                """All export options can now also export selected items only."""
            ),
            Feature(
                """Put line breaks in the XML so that task files are 
easier to examine in a text editor.""",
                "1277365",
            ),
        ],
    ),
    Release(
        "0.72.8",
        "May 17, 2009",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Drag and drop from Thunderbird would not work on Debian-derived 
distributions.""",
                "2790274",
            ),
            Bug(
                """Work around a bug in wxPython 2.8.9.2 on Mac OS X that prevented
dialogs to be opened for items that have a color set.""",
                "2789977",
            ),
            Bug(
                """Draw check boxes instead of black squares in the category viewer
on Windows XP and Vista with the classic theme."""
            ),
            Bug(
                """The background of check boxes were corrupted under Linux."""
            ),
            Bug(
                """Double clicking an item in a specific column wouldn't select the 
appropriate tab in the dialog.""",
                "2791100",
            ),
            Bug("""Reduce flickering when tracking effort for a task."""),
            Bug(
                """Opening a task file with e-mail attachments not specifying their
encoding on a different system than the one the task file was created could fail."""
            ),
            Bug("""Couldn't add effort to a freshly created task."""),
        ],
        featuresAdded=[
            Feature(
                """Use the settings for effort dialog start and stop times for
the reminder drop down as well.""",
                "2792160",
            )
        ],
        dependenciesChanged=[
            Dependency(
                """Task Coach now at least needs wxPython 2.8.9.2-unicode.
Since the Windows installer and the Mac OS X dmg package have wxPython included, 
this only affects users of the RPM, Debian, and source distributions."""
            )
        ],
    ),
    Release(
        "0.72.7",
        "May 10, 2009",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Support locking of task files on USB sticks/drives that
have a different file system than the host system has.""",
                "2776249",
            ),
            Bug(
                """Task Coach would sometimes crash when dragging a task onto 
another task on Windows. Fixed by using a different widget for tree-list 
controls.""",
                "2573263",
                "1995248",
                "2247808",
                "1963262",
            ),
        ],
        featuresAdded=[
            Feature(
                """The category viewer can show additional columns (description,
attachment, ...) besides just the subject of categories. This is a side effect 
of the fix for the drag and drop issues."""
            )
        ],
        websiteChanges=[
            Website(
                """Follow Task Coach on twitter: http://twitter.com/taskcoach. 
The latest tweets are also listed on http://www.taskcoach.org.""",
                "index.html",
            ),
            Website(
                """Added Google Ads to generate additional revenue to cover the
cost of hardware and commercial operating systems.""",
                "index.html",
            ),
        ],
    ),
    Release(
        "0.72.6",
        "April 18, 2009",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug("""Task Coach couldn't be installed using EasyInstall."""),
            Bug(
                """Task Coach couldn't be installed on Linux systems that have 
2.6 as their default Python version. Task Coach currently needs Python 2.5.
Fixed by forcing an install for Python 2.5 on all Linux systems when 
installing from a RPM or Debian package.""",
                "2724839",
            ),
            Bug(
                """The lockfile package used for file locking had a bug when
used with Python 2.6. Fixed by upgrading the lockfile package to version 
0.8.""",
                "2761466",
            ),
            Bug(
                """Task Coach would sometimes crash when dragging a task onto 
another task on Windows.""",
                "2573263",
                "1995248",
            ),
        ],
    ),
    Release(
        "0.72.5",
        "April 5, 2009",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug("""Include the lockfile package in the distributions.""")
        ],
    ),
    Release(
        "0.72.4",
        "April 5, 2009",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """When exporting effort to iCalendar format, use 'floating times'
rather than UTC.""",
                "2722224",
            ),
            Bug(
                """Lock a task file while the user is working on it. Note that
locks are only honored by Task Coach itself; locked files can still be 
removed using a file explorer.""",
                "2318647",
                "2236420",
            ),
            Bug(
                """Fail silently if checking for the availability of a new 
Task Coach version doesn't work for some reason.""",
                "2669995",
            ),
            Bug(
                """Don't open the category edit dialog when the user double clicks
a category check box.""",
                "2685754",
            ),
            Bug(
                """In the budget page of the task edit dialog, make sure that 
selected values can be overwritten.""",
                "2654254",
            ),
            Bug(
                """Make the Debian package work with python versions >= 2.5 
(but smaller than python 3.0).""",
                "2724839",
            ),
        ],
    ),
    Release(
        "0.72.3",
        "March 13, 2009",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Don't turn on the color selection in the task edit dialog when 
the task color is based on the category it belongs to."""
            ),
            Bug(
                """Make it easier to edit budget values in the task edit 
dialog.""",
                "2654254",
            ),
            Bug(
                """Fix regression caused by the saving of print margins added in 
release 0.72.2.""",
                "2632431",
            ),
        ],
    ),
    Release(
        "0.72.2",
        "March 11, 2009",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Support drag and drop from Thunderbird Portable under
Windows""",
                "2665317",
            ),
            Bug(
                """Correctly read task files with version <= 13 (Task Coach release
0.57 and earlier) that contain categories."""
            ),
            Bug(
                """When a subtask belongs to a category with color, use that 
color to color the subtask, rather than the color of the parent task."""
            ),
            Bug(
                """Save print margins in the TaskCoach.ini file.""", "2632431"
            ),
        ],
    ),
    Release(
        "0.72.1",
        "February 14, 2009",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Drag and drop from Thunderbird wouldn't work with
GMail IMAP accounts.""",
                "2549194",
            ),
            Bug(
                """Exception when synchronizing with the new version of
ScheduleWorld.""",
                "2553046",
            ),
            Bug(
                """On MacOS, the window height would increase by 29 pixels
each time Task Coach was launched."""
            ),
            Bug(
                """Exporting a selection of effort records resulted in an empty 
HTML file."""
            ),
            Bug(
                """Opening a task from a reminder dialog didn't work.""",
                "2580772",
            ),
            Bug(
                """Include effort for subtasks in the effort viewer for one task."""
            ),
            Bug(
                """Correctly display error message when the user enters an invalid
regular expression in a search control."""
            ),
            Bug(
                """Update the task square map viewer when the task status changes
(e.g. when a task is completed)."""
            ),
            Bug(
                """When SyncML is enabled and the last subtask of a task is
deleted, correctly update the icon in the task viewer."""
            ),
        ],
        featuresAdded=[
            Feature(
                """When the single task, whose effort records are shown in
a single task effort viewer, is removed, the effort viewer resets to
show all effort records of all tasks."""
            ),
            Feature("""Tool tips for task square map viewer."""),
        ],
    ),
    Release(
        "0.72.0",
        "January 30, 2009",
        summary="""This release adds a square map task viewer and a 
single-task effort viewer. This release also fixes a few bugs and adds a few
smaller feature enhancements.""",
        featuresAdded=[
            Feature(
                """One can now export only the current selection as HTML."""
            ),
            Feature(
                """When using yearly recurrence of tasks, allow for keeping
the recurring date on the same weekday (e.g. to recur on the first
Monday of the year).""",
                "2164568",
            ),
            Feature(
                """Added a square map viewer for tasks that displays tasks in 
the form of a set of nested squares. The relative size of the squares is 
determined by either budget, budget left, time spent, fixed fee or revenue."""
            ),
            Feature(
                """One can now open an effort viewer for a specific task."""
            ),
            Feature(
                """Added (incomplete) Hindi and German (Low) translations."""
            ),
        ],
        bugsFixed=[
            Bug("""Don't crash when adding a task.""", "2467347"),
            Bug(
                """Update the total fixed fee column in the task viewer when
adding a subtask with a fixed fee."""
            ),
            Bug("""Mark task file dirty when the user edits a task color."""),
            Bug(
                """Update the hourly fee column in the task viewer when the 
the user edits the hourly fee of a task."""
            ),
            Bug("""Make it possible to add an effort record to a new task."""),
            Bug(
                """When opening all attachments of an item, give an error message
for each attachment that cannot be opened."""
            ),
        ],
    ),
    Release(
        "0.71.5",
        "December 24, 2008",
        summary="""This release adds one usability enhancement and a few bug 
fixes.""",
        featuresAdded=[
            Feature(
                """When double clicking an item in a viewer, open the editor
on the right page, depending on the column clicked. For example, when clicking
on the due date column in a task viewer, Task Coach will open the task editor
with the dates page raised. Patch provided by Carl Zmola."""
            )
        ],
        bugsFixed=[
            Bug(
                """Don't wake up every second just to keep track of reminders and 
midnight."""
            ),
            Bug(
                """Hide main window after showing reminder dialog when it was 
hidden before.""",
                "2372909",
            ),
            Bug(
                """When marking a recurring task completed, recur its reminder too, 
if any.""",
                "2376415",
            ),
            Bug("""Refresh task status at midnight.""", "2095205"),
            Bug(
                """Fix tab traversal in the effort editor on Linux.""",
                "1965751",
            ),
        ],
    ),
    Release(
        "0.71.4",
        "December 6, 2008",
        summary="""This is a bugfix release.""",
        featuresAdded=[
            Feature(
                """Add a "Purge deleted items" entry in the File menu for
people who have been using Task Coach with SyncML disabled."""
            ),
        ],
        bugsFixed=[
            Bug(
                """Opening an old .tsk file with missing e-mail attachments
would crash Task Coach."""
            ),
            Bug(
                """Don't throw exception when showing an (error) message while
synchronizing.""",
                "2356799",
            ),
            Bug(
                """When merging from the same file multiple times, update the
existing items instead of duplicating them.""",
                "2062616",
            ),
            Bug(
                """Don't set negative priorities to zero in the task editor
(Linux only).""",
                "2324869",
            ),
            Bug(
                """Save the column width of the first column when automatic 
resizing of columns is off.""",
                "2255690",
            ),
            Bug(
                """Actually delete tasks and notes when SyncML is disabled.""",
                "2319921",
            ),
            Bug(
                """Do not create subitems in two steps, this is counter intuitive."""
            ),
            Bug(
                """Properly iterate over the open viewers with Ctrl-PgDn and 
Ctrl-PgUp.""",
                "1973357",
            ),
            Bug(
                """Update the task viewer when a note is deleted from a task.""",
                "2277217",
            ),
            Bug(
                """Update the tray icon tool tip when deleting an overdue task.""",
                "2321351",
            ),
            Bug(
                """Wrap long lines in description tool tip windows.""",
                "2318094",
            ),
        ],
    ),
    Release(
        "0.71.3",
        "November 10, 2008",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Spell checking in editor didn't work under Mac OS X.""",
                "2214676",
            ),
            Bug(
                """Dropping a mail with several recipients from Outlook would result
in a "No subject" subject.""",
                "2220224",
            ),
            Bug(
                """A ghost window would appear on the secondary display under 
Mac OS X if it's placed on the right.""",
                "2206656",
            ),
            Bug("""The note total would include deleted notes.""", "2209640"),
            Bug(
                """Don't hang when exiting the application.""",
                "2185910",
                "2209679",
            ),
            Bug(
                """Don't show all effort in the effort tab of a task editor, but
only effort for the task being edited.""",
                "2207166",
            ),
            Bug(
                """Fix for a backwards incompatible change in python 2.6.""",
                "2212857",
            ),
            Bug(
                """Update task details at midnight, even when Task Coach is not 
active at precisely midnight.""",
                "2095205",
                "2061826",
            ),
            Bug("""Allow for empty task subjects.""", "2214812"),
            Bug(
                """Make the drop down button for picking dates look disabled when
it is disabled.""",
                "2214706",
            ),
        ],
    ),
    Release(
        "0.71.2",
        "October 24, 2008",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug("""The reminder dialog didn't work.""", "2168756"),
            Bug(
                """One couldn't add an URI attachment "by hand".""", "2167705"
            ),
            Bug(
                """The combobox with tasks in the effort editor
wouldn't always be properly filled, making it impossible to edit the effort
record.""",
                "2167798",
                "2173127",
            ),
            Bug(
                """Warn the user when the task file cannot be saved.""",
                "2121470",
            ),
            Bug(
                """Warn the user when the TaskCoach.ini file cannot be loaded.""",
                "2101765",
            ),
            Bug(
                """When saving selected tasks, also include any categories the 
selected tasks are in."""
            ),
            Bug(
                """The right-click menu item 'Start tracking effort' wouldn't 
work for recurring tasks.""",
                "2165652",
            ),
        ],
        featuresAdded=[
            Feature(
                """The SyncML password dialog now has a more specific
title.""",
                "2176781",
            ),
            Feature(
                """The system tray popup menu now has a 'New note' menu 
item.""",
                "2182735",
            ),
        ],
    ),
    Release(
        "0.71.1",
        "October 13, 2008",
        summary="""This is a bugfix release.""",
        bugsFixed=[
            Bug(
                """Older task files containing e-mail attachments could
not be opened."""
            ),
            Bug(
                """Newly created templates would not appear in the Task
menu, only in the toolbar template button."""
            ),
            Bug(
                """Installing from source wouldn't work on platforms
where pysyncml is not supported.""",
                "2164313",
            ),
            Bug(
                """The installers for Mac OS X and Windows for release 0.71.0
were missing some files, causing Task Coach not to be able to save.""",
                "2162181",
            ),
        ],
    ),
    Release(
        "0.71.0",
        "October 12, 2008",
        summary="""This release adds task and note synchronization, task templates, 
more task recurrence options, more translations and a whole bunch of smaller 
enhancements.""",
        featuresAdded=[
            Feature(
                """E-mail attachments are now stored directly in the
task file."""
            ),
            Feature(
                """Tasks and notes can now be synchronized with a
Funambol server (http://www.funambol.com/).""",
                "2006123",
                "1892874",
            ),
            Feature(
                """Tasks can now be saved and reused as templates.""",
                "1851847",
                "1549002",
                "1484368",
                "1601869",
            ),
            Feature(
                """Attachments are now regular domain objects; they may
have notes."""
            ),
            Feature(
                """The task and note editors now use an actual category
viewer. It is possible to create and edit categories from these editors."""
            ),
            Feature(
                """The description tooltip now works for efforts and
categories. It also contains a summary of notes and attachments belonging
to the hovered object.""",
                "1642608",
                "1917999",
            ),
            Feature(
                """More task recurrence options. Tasks can now also recur 
yearly, in addition to daily, weekly, and monthly. Tasks can also recur 
with a multiple period frequency, e.g. every other week or every three months.
Monthly recurring tasks can be set to recur on the same week day (e.g. first
Monday of the month).""",
                "1963803",
                "1917090",
                "1913656",
                "2076511",
            ),
            Feature(
                """The times used in the drop down menus of the start and stop
entries of the effort dialog can now be changed via the preferences dialog. 
Patch supplied by Rob McMullen."""
            ),
            Feature(
                """The effort tracking feature can be turned off via the
preferences dialog."""
            ),
            Feature(
                """The system tray icon shows the task being tracked in 
its tool tip. Patch provided by JoÃ£o Alexandre de Toledo."""
            ),
            Feature("""Categories and notes can have attachments."""),
            Feature(
                """Tasks and categories can contain notes. """,
                "1954879",
                "2140239",
                "1525434",
            ),
            Feature(
                """The four different effort viewers are integrated in one
viewer that can switch between different effort aggregation modes, i.e. details,
per day, per week and per month, via the toolbar."""
            ),
            Feature(
                """The two different task viewers are integrated in one
viewer that can switch between list and tree mode, via the toolbar."""
            ),
            Feature(
                """Category filtering is done either by showing tasks and notes
that match any category or that match all categories. This filtering mode 
can be switched via the toolbar of the category viewer.""",
                "2024510",
            ),
            Feature(
                """The effort background is now colored with the same color as
the task it belongs to."""
            ),
            Feature(
                """The effort viewer can show the (overall) categories of the 
task of each effort in an (overall) categories column. Patch provided by
Thomas Sonne Olesen.""",
                "1911052",
                "1791670",
            ),
            Feature(
                """When the effort viewer is in weekly mode, it can show effort
per weekday. Patch provided by Thomas Sonne Olesen."""
            ),
            Feature(
                """The automatic resizing of columns can be turned off on a
viewer by viewer basis, using the 'Automatic column resizing' checkable
menu item in the View->Columns menu and/or in the column header right-click
menu.""",
                "2047851",
                "1466164",
            ),
            Feature(
                """The expansion state of tasks, categories and notes is 
saved in the task file.""",
                "2045453",
                "1790057",
            ),
            Feature(
                """Added Catalan translation thanks to Ferran Roig, Jordi
Mallach, Josep-Miquel Ivars, and devaleitzer."""
            ),
            Feature(
                """Added an (incomplete) Arabic translation thanks to 
Moayyed. Please help finish it. See http://www.taskcoach.org/i18n.html."""
            ),
            Feature(
                """Added largely incomplete Esperanto, Estonian, Indonesian, 
Marathi, Lithuanian, Norwegion Nynorsk, Slovenian, Telugu, and Vietnamese 
translations. Please help finish them. 
See http://www.taskcoach.org/i18n.html."""
            ),
        ],
        bugsFixed=[
            Bug(
                """Undo would not work well when creating notes in a category or 
task."""
            ),
            Bug(
                """An IndexError would be raised when undoing then editing."""
            ),
            Bug(
                """Ctrl-PgDn and Ctrl-PgUp would sometimes need to be pressed
multiple times before the next or previous viewer would be activated. """
            ),
        ],
        implementationChanged=[
            Implementation(
                """The task file format (version 20) was changed.  
Task nodes may have a recurrence node that contains the recurrence state of
the task. Categories and notes can contain attachments. Tasks and categories
can now contain notes."""
            )
        ],
    ),
    Release(
        "0.70.4",
        "September 28, 2008",
        summary="""Bug fix release.""",
        bugsFixed=[
            Bug(
                """Allow Task Coach to be installed on Ubuntu 7.10.""",
                "2117477",
            ),
            Bug("""Task Coach wasn't notifying users of new versions."""),
            Bug("""When merging, merge notes too."""),
            Bug(
                """When the notes feature is turned off, hide
the 'Create new note' menu item in the category pop up menu."""
            ),
            Bug("""Fixed a translation bug.""", "2087395"),
            Bug(
                """Hide/show the main window with one click on the task bar icon 
instead of a double click (Linux only)."""
            ),
            Bug(
                """The Task Coach main window would get a very small size if it
was started minimized and had not been restored in the previous session.""",
                "2052910",
            ),
        ],
    ),
    Release(
        "0.70.3",
        "August 17, 2008",
        summary="""Bug fix release.""",
        bugsFixed=[
            Bug(
                """wxPython 2.8.8.1 generates images in a new, backwards 
incompatible way, even when told not to do that. This bug affects users 
that have an older version of wxPython installed and use one of the 
Linux packages. Fixed by adding the relevant pieces from wxPython 2.8.8.1 to 
the Task Coach sources.""",
                "2046084",
            ),
            Bug("""Opening a new task viewer didn't work.""", "2053008"),
            Bug("""Closing effort viewers causes exceptions.""", "2053008"),
        ],
    ),
    Release(
        "0.70.2",
        "August 6, 2008",
        summary="""This release fixes some bugs and brings back
the Fedora RPM.""",
        bugsFixed=[
            Bug(
                """Using the "Save selection" feature together with
mail attachments could result in data loss."""
            ),
            Bug(
                """Under KDE, the maximized state of the main window
would not be restored."""
            ),
            Bug(
                """One couldn't e-mail tasks with non-ASCII characters
in their description.""",
                "2025676",
            ),
            Bug(
                """Dragging an email message from Thunderbird and dropping it
on Task Coach could give a "UnicodeDecodeError" on Fedora.""",
                "1953166",
            ),
            Bug(
                """When an invalid regular expression was entered in
a search control, no items were displayed. Additionally, if it was
saved in TaskCoach.ini, TaskCoach would crash on launch later."""
            ),
            Bug(
                """Mention of non-existing files in taskcoach.spec
prevented the Fedora RPM from being built."""
            ),
            Bug(
                """The category viewer would sometimes skip keyboard navigation or
need an extra mouse-click to get focus.""",
                "2020816",
                "2020812",
            ),
            Bug(
                """On Mac OS X, the keyboard shortcut for 'help' was interfering 
with the shortcut for 'hide window'.""",
                "2006455",
            ),
        ],
        featuresAdded=[
            Feature("""Notes can be e-mailed."""),
            Feature(
                """Display a tool tip to warn user when a search
string is an invalid regular expression. In this case, default to
substring search."""
            ),
            Feature(
                """Optionally put Task Coach in the user's startup menu so
that Task Coach is started automatically when the user logs on 
(Windows only).""",
                "2017400",
                "1913650",
            ),
            Feature("""Made (right-click) context menu's more consistent."""),
        ],
        featuresRemoved=[
            Feature(
                """Don't supply the dummy recipient 'Please enter recipient' to 
the email program when mailing a task. This only forces users to perform 
an extra action to remove that dummy text, while most if not all email 
programs will warn users when they forget to enter a recipient. """,
                "2026833",
            )
        ],
    ),
    Release(
        "0.70.1",
        "June 28, 2008",
        summary="""This release optionally brings back the tabbed user 
interface that was removed in the previous release and fixes a few 
bugs.""",
        bugsFixed=[
            Bug(
                """The search control in the toolbar did not maintain 
state correctly for different viewers. Task Coach viewers now each 
have their own toolbar with search control.""",
                "1977196",
            ),
            Bug(
                """Marking tasks completed or changing their priority would change
the selection.""",
                "1888598",
                "1926362",
            ),
            Bug(
                """On Max OS X, put preferences menu item in the TaskCoach 
menu instead of the Edit menu to conform with Mac OS X standards.""",
                "1965861",
            ),
            Bug(
                """Focus issues: On Mac OS X, text couldn't be edited while the 
timer was running. On Windows, notifications from other programs overlapping 
with the main window would take away focus from dialogs.""",
                "1995469",
                "2000152",
            ),
            Bug(
                """Prevent crash under Windows XP when dropping e-mail 
from Thunderbird if the APPDATA environment variable is not 
defined.""",
                "1960827",
            ),
            Bug(
                """ImportError: No module named thirdparty.ElementTree. 
This exception would happen when using a source distribution of Task 
Coach or a package (rpm, deb) for Linux *and* when the default version 
of Python on the system is Python 2.4. Task Coach tried to import a 
module from the wrong package.""",
                "1964069",
            ),
            Bug(
                """On Linux, when using a dark theme, use appropriate 
background colors for the category viewer and the text color buttons 
in the preferences dialog.""",
                "1988160",
            ),
            Bug(
                """Remember whether the main window was maximized and if 
so, maximize the main window when starting the next time.""",
                "1969266",
            ),
            Bug(
                """Correctly sort tasks on startup when sort column is 
'Overall categories'.""",
                "1962003",
            ),
            Bug(
                """Correctly redraw toolbar when it is 'damaged' by other 
windows""",
                "1977208",
            ),
            Bug(
                """Correctly sort effort for subtasks in effort per day, 
per week, and per month effort viewers.""",
                "1989553",
            ),
            Bug("""Better navigation with tab key in dialogs."""),
            Bug(
                """Keep newlines in descriptions when printing or 
exporting to HTML."""
            ),
        ],
        featuresAdded=[
            Feature(
                """Task Coach can now use either the old tabbed user interface
(whose layout still cannot be saved, by the way) or the 'managed frame' 
interface introduced in release 0.70.0. This can be changed in the Preferences
dialog.""",
                "1964213",
            )
        ],
    ),
    Release(
        "0.70.0",
        "May 12, 2008",
        summary="""Small feature enhancements, more translations and several bug 
fixes. Task Coach is now distributed under the GPLv3+.""",
        featuresAdded=[
            Feature("Paths to file attachments may be relative."),
            Feature("Monthly recurrence of tasks.", "1933222", "1957687"),
            Feature("Added and reorganized keyboard short cuts.", "1857101"),
            Feature(
                """Start tracking effort for any active task using the 
system tray icon right-click menu.""",
                "1934738",
                "1739666",
            ),
            Feature(
                """Added a largely complete Ukranian translation thanks to
Vitovt and incomplete Finnish, Greek, Persian and Thai translations."""
            ),
        ],
        featuresChanged=[
            Feature(
                """Slightly higher preference window so all icons fit and
no scrolling is needed.""",
                "1918678",
            )
        ],
        bugsFixed=[
            Bug("""Allow for editing seconds in effort editor.""", "1925748"),
            Bug(
                """The combobox in the effort detail editor always picked the 
first task when multiple tasks had the same subject, effectively prohibiting
the user to move an effort record to another task with the same subject.""",
                "1918033",
            ),
            Bug(
                """Reset invalid input in the priority field of the task editor
to 0 instead of to the minimum priority (a large negative value).""",
                "1949222",
            ),
            Bug(
                """"View->Filter->Reset all filters" now also unchecks all 
categories."""
            ),
            Bug(
                """Task Coach now is packaged as a proper Debian package, thanks to
Stani Michiels. The Debian package installs a menu item for Task Coach in the 
Applications/Office menu.""",
                "1792706",
                "1792711",
                "1896796",
            ),
        ],
        dependenciesChanged=[
            Dependency(
                """Task Coach now uses Subversion for version control. See
http://sourceforge.net/svn/?group_id=130831. This only affects you if
you want to develop or use Task Coach source code."""
            ),
            Dependency(
                """Task Coach is now distributed under the GNU General 
Public License version 3 or (at your option) any later version. This only 
affects you if you want to distribute changed versions of Task Coach or 
want to include source code from Task Coach in other software."""
            ),
        ],
    ),
    Release(
        "0.69.2",
        "March 28, 2008",
        summary="Bug fix release.",
        featuresAdded=[
            Feature(
                """Task Coach now suggests a reminder date, based
on the due date or start date of a task."""
            ),
            Feature(
                """Added a complete Norwegion Bokmal translation thanks to Amund Amundsen
and incomplete Galician, Korean and Romanian translations."""
            ),
        ],
        bugsFixed=[
            Bug(
                """Tasks created via the context menu of the category view now 
automatically belong to the selected category.""",
                "1592103",
            ),
            Bug("""Update task status and colors at midnight.""", "1183043"),
            Bug(
                """Exception when starting Task Coach ("AttributeError: 
'CategoryList' object has no attribute 'EventTypePrefix'").""",
                "1901385",
            ),
            Bug(
                """Exception when reopening a closed viewer (with the message
"ConfigParser.NoSectionError: No section: 'effortperdayviewer1'" in the log 
file).""",
                "1894488",
            ),
            Bug(
                """Exception when resetting all filters in the task tree viewer
(with the message "No option 'hidecompositetasks' in section: 
'tasktreelistview'" in the log file).""",
                "1903679",
            ),
            Bug(
                """Don't take the priority of completed subtasks into account when
calculating the overall priority of a task.""",
                "1905774",
            ),
            Bug(
                """It was not clear that backup files can be opened in Task Coach.
Backup files now have the extension '.tsk.bak'. The file open dialog has 
'*.tsk.bak' as selectable file type to make it easier to open backup files.""",
                "1911538",
            ),
            Bug(
                """Exception when opening the task menu while the toolbar 
is hidden."""
            ),
        ],
    ),
    Release(
        "0.69.1",
        "February 14, 2008",
        summary="Bug fix release.",
        bugsFixed=[
            Bug(
                """Exception when closing a task editor dialog. This 
causes updates of task states not to be displayed properly. The bug itself
does not cause data loss, but it might trick users into saving an empty
task file over their existing data.""",
                "1893634",
            ),
            Bug(
                """On Mac OS X, users couldn't enter 'P' and 'M' in text boxes,
because these were mapped to menu items. Reorganized keyboard shortcuts to fix 
this.""",
                "1890566",
            ),
            Bug(
                """The arrow ('â†’') and infinity symbol ('âˆž') are not 
visible on all computers, so Task Coach is back to using '->' and 'Infinite'
again."""
            ),
        ],
    ),
    Release(
        "0.69.0",
        "February 9, 2008",
        summary="""This release makes it possible to repeat tasks on either a daily 
or a weekly basis and to add notes to categories. It also contains a number of 
other changes and bug fixes.""",
        featuresAdded=[
            Feature(
                """Tasks can recur on a daily or weekly basis. This feature is
not complete yet. Most obviously, recurring on a monthly basis is missing. 
Also, recurring tasks with recurring subtasks do not behave entirely 
correctly yet.""",
                "1623364",
                "1464793",
                "1264210",
            ),
            Feature("""Notes can be assigned to categories."""),
            Feature("""Added Bulgarian translation, thanks to Rumen Belev."""),
            Feature(
                """Added Danish translation, thanks to different translators."""
            ),
            Feature(
                """Added a number of rather incomplete translations (Italian,
Portuguese, Swedish, and Turkish).
See http://www.taskcoach.org/i18n.html for how you can help improve these 
translations."""
            ),
            Feature(
                """When filtering by one or more categories, new tasks and 
notes are automatically added to those categories. Of course, you can still
change the categories in the category tab of the edit dialog before pressing
the OK button."""
            ),
            Feature(
                """Whether descriptions of tasks, effort records, categories and
notes are shown in a popup tooltip window is now a setting.""",
                "1857098",
            ),
            Feature(
                """Added menu items for increasing, decreasing, maximizing, and 
minimizing task priority.""",
                "1768210",
                "1570616",
            ),
            Feature(
                """Clicking a column header in a task viewer now iterates
through the following sort orders: 'ascending, after sorting by task status first', 
'descending, after sorting by task status first', 'ascending, without sorting
by task status first', 'descending, without sorting by task status first'."""
            ),
        ],
        featuresChanged=[
            Feature(
                """Previously, unset dates were displayed as 'None' in   
date columns. To be consistent with how other attributes are displayed in 
columns, Task Coach now simply displays nothing for unset dates in date
columns."""
            ),
            Feature(
                """Task Coach now uses the infinity symbol ('âˆž') to display
the number of days left for tasks without a due date, instead of the word 
'Infinite'."""
            ),
            Feature(
                """Task Coach now uses a real arrow symbol ('â†’') instead of 
'->' for separating parent and child subjects in the different viewers."""
            ),
        ],
        featuresRemoved=[
            Feature(
                """Task Coach no longer keeps track of the 'last modification 
time' of tasks."""
            )
        ],
        bugsFixed=[
            Bug(
                """The reminder dialog didn't close when opening the task from
the reminder dialog. If the user had entered a snooze option in the reminder
dialog, that snooze option would be overwritten when closing the task 
editor.""",
                "1862286",
            ),
            Bug(
                """Don't allow filtering by both a parent and a child category at
the same time."""
            ),
            Bug(
                """Sorting by total categories in the task viewers didn't sort
correctly."""
            ),
            Bug(
                """Save didn't work for task files without a file name and
without tasks, but with categories or notes."""
            ),
            Bug(
                """Adding a task to a category or removing it from a category
was not undoable."""
            ),
        ],
    ),
    Release(
        "0.68.0",
        "December 26, 2007",
        summary="""This release makes it possible to open a task from its reminder dialog, adds
a command line option to facilitate the PortableApps.com Task Coach distribution, makes 
starting and stopping effort tracking quicker and fixes a number of bugs.""",
        featuresAdded=[
            Feature(
                """It is possible to open a task from its reminder 
dialog."""
            ),
            Feature(
                """Task Coach has a --ini command line option that can
be used to specify where the ini file is located."""
            ),
        ],
        bugsFixed=[
            Bug(
                """Start and stop tracking effort is faster for tasks that 
have a large number of associated effort records."""
            ),
            Bug(
                """Task Coach now gives an error message if the file that it tries
to open doesn't exist.""",
                "1857093",
            ),
            Bug(
                """When selecting all text in a text control with '<cmd>a',
indeed select all text and not all tasks (Max OSX only).""",
                "1857091",
            ),
            Bug(
                """Attempt to prevent crashes on Fedora 8 that sometimes happen
when adding top level tasks.""",
                "1840111",
            ),
        ],
    ),
    Release(
        "0.67.0",
        "December 16, 2007",
        summary="""This release make it possible to color tasks via their
categories, adds a translation in Hebrew, and makes it easier to mark 
tasks as not completed.""",
        featuresAdded=[
            Feature("""Added Hebrew translation thanks to Ziv Barcesat."""),
            Feature(
                """You can assign a color to a category. Tasks are colored 
according to the color of the categories they belong to.""",
                "1466159",
                "1784932",
            ),
            Feature(
                """The 'mark task completed' button and menu items can now 
also be used to mark tasks as not completed.""",
                "1449714",
            ),
        ],
        bugsFixed=[
            Bug(
                """Don't move selection to the first line of the task tree viewer
when deleting a subtask.""",
                "1849171",
            )
        ],
        dependenciesChanged=[
            Dependency(
                """Task Coach now needs at least wxPython 
2.8.6.0-unicode. Since the Windows installer and the Mac OSX dmg package have
wxPython included, this only affects users of the RPM, Debian, and source
distributions."""
            )
        ],
    ),
    Release(
        "0.66.3",
        "December 11, 2007",
        summary="Bug fix release to address crashes.",
        bugsFixed=[
            Bug(
                """Work around a bug in the TreeListCtrl widget that caused
crashes. The TreeListCtrl widget is used by Task Coach for the task tree 
view.""",
                "1846906",
                "1840111",
                "1832490",
                "1829622",
                "1821858",
                "1820497",
            )
        ],
    ),
    Release(
        "0.66.2",
        "November 9, 2007",
        summary="Bug fix release to address crashes.",
        bugsFixed=[
            Bug("""Don't crash when refreshing a tree view.""", "1828846")
        ],
    ),
    Release(
        "0.66.1",
        "November 7, 2007",
        summary="This release fixes a number of minor bugs.",
        bugsFixed=[
            Bug(
                """When changing the sort order in a tree viewer, keep 
collapsed items collapsed and expanded items expanded.""",
                "1791638",
            ),
            Bug("Sort categories alphabetically in task editor.", "1824180"),
            Bug(
                """Double clicking a task in the tree view did not open
the task edit dialog."""
            ),
            Bug(
                """When filtering on a specific category, a newly added task
belonging to that category was not shown in the task viewers."""
            ),
        ],
    ),
    Release(
        "0.66.0",
        "October 31, 2007",
        summary="""Small feature enhancements and a translation in 
Traditional Chinese.""",
        featuresAdded=[
            Feature(
                "Added Traditional Chinese translation thanks to Joey Weng."
            ),
            Feature(
                """Added an 'overall categories' column that recursively shows 
the categories a task belongs to, i.e. its own categories and the categories
of its parent task(s).""",
                "1790054",
            ),
            Feature("Column widths are saved between sessions.", "1799998"),
            Feature(
                """Ctrl-PageUp and Ctrl-PageDown can be used to cycle through 
open viewers.""",
                "1818428",
            ),
        ],
        bugsFixed=[
            Bug("Make categories and category viewer more robust.", "1821776")
        ],
    ),
    Release(
        "0.65.3",
        "October 20, 2007",
        summary="""This bugfix release fixes one critical bug that affects 
users on the Windows platform and several minor bugs that affect users on all 
platforms.""",
        bugsFixed=[
            Bug(
                """Don't leak GDI objects on Windows.""",
                "1813632",
                "1811058",
                "1810297",
                "1806004",
                "1803085",
            ),
            Bug(
                """Don't notify of new version when the user has just installed 
that version."""
            ),
            Bug(
                """Mail disappears from Outlook when dropped in TaskCoach. Try to
use Outlook to open mail attachment when it's the "default" mailer.""",
                "1812399",
            ),
            Bug("""Mail task doesn't work.""", "1810356"),
            Bug("""Categories not sorted correctly.""", "1810469"),
        ],
    ),
    Release(
        "0.65.2",
        "October 8, 2007",
        summary="This release is aimed at better performance.",
        bugsFixed=[
            Bug("""Slow performance.""", "1806001", "1794007"),
            Bug(
                """Don't require administrator privileges for installation
on Windows XP/Vista."""
            ),
        ],
    ),
    Release(
        "0.65.1",
        "September 23, 2007",
        summary="""This release fixes one critical bug and two minor bugs.""",
        bugsFixed=[
            Bug(
                """Tooltip windows steals keyboard focus on some platforms.""",
                "1791627",
            ),
            Bug("""Taskbar icon is not transparent on Linux.""", "1648082"),
            Bug(
                """Saving a task file after adding attachments via the
'add attachment' menu or context menu fails.""",
                "1796829",
            ),
        ],
    ),
    Release(
        "0.65.0",
        "September 9, 2007",
        summary="""This release adds the ability to record notes, improves the 
flexibility of the different views, and fixes several bugs.""",
        featuresAdded=[
            Feature(
                """Notes. Notes have a subject and an optional description.
Notes can be hierarchical, i.e. notes may contain subnotes. Notes can be sorted
and searched (filtered), printed, and exported. This feature can be turned
on or off via the preferences dialog."""
            ),
            Feature(
                """Categories can be searched (filtered) using the search
control on the toolbar. """
            ),
            Feature(
                """Category sorting can be changed: ascending or descending,
case sensitive or case insensitive."""
            ),
            Feature("""Categories can have a description."""),
            Feature(
                """Each viewer/tab has its own settings for sort order
and visible columns. Viewers can be renamed. This makes it possible to
e.g. create a 'Todo today'."""
            ),
            Feature(
                """The search control on the toolbar can (optionally) include
subitems in the search result. This makes it easy to show
one task and its subtasks in a task viewer or show effort for one task and 
its subtasks in an effort viewer."""
            ),
            Feature(
                """Added a setting to start Task Coach iconized either 
always, never, or only when Task Coach was iconized when last 
quitted.""",
                "1749886",
            ),
            Feature(
                """Added a setting to turn off spell checking 
(Mac OSX only)""",
                "1768330",
            ),
            Feature(
                """Added (incomplete) translations in Brazilian Portuguese, 
Czech, Latvian and Polish. See http://www.taskcoach.org/i18n.html for more
information about translations and on how you can help."""
            ),
        ],
        bugsFixed=[
            Bug("""Made subject column resizable.""", "1702270", "1766664"),
            Bug(
                """Enable export of data containing non-ASCII 
characters to CSV.""",
                "1753422",
            ),
            Bug(
                """Don't activate another viewer when another application is
minimized (Windows only).""",
                "1765103",
            ),
            Bug(
                """Outlook 2003 email messages added as attachment couldn't be
opened from Task Coach.""",
                "1748738",
            ),
            Bug(
                """German translation had wrong menu accelerators.""",
                "1772019",
            ),
            Bug(
                """Apply undo/redo/cut/copy/paste actions to text if a text control
is visible and has focus (Mac OSX only)""",
                "1768315",
            ),
            Bug(
                """Added a copy of the ElementTree package to the Task Coach 
source code, so the source code distribution of Task Coach
works with Python 2.4, without needing to install ElementTree.""",
                "1783575",
            ),
        ],
    ),
    Release(
        "0.64.2",
        "June 30, 2007",
        summary="""This release fixes sorting of tasks by priority
and makes sure that Task Coach does not block OS shutdown.""",
        bugsFixed=[
            Bug(
                """Don't take child task priority into account when sorting by 
priority in the task tree view.""",
                "1732968",
            ),
            Bug(
                """Don't block OS shutdown on Windows.""",
                "1735532",
                "1484652",
                "1489870",
            ),
        ],
    ),
    Release(
        "0.64.1",
        "June 10, 2007",
        bugsFixed=[
            Bug(
                """Task Coach would complain about an error when closing the 
application. This was due to a missing package in the Windows executable
distribution.""",
                "1727237",
            ),
            Bug(
                """On Linux, Task Coach was not very helpful when the 
taskcoachlib package is installed for a different python version than the one
the user is starting Task Coach with. """,
                "1728485",
            ),
        ],
    ),
    Release(
        "0.64.0",
        "May 28, 2007",
        bugsFixed=[
            Bug(
                """Ubuntu users had to manually install the wxaddons package. 
This package is now included in the Task Coach distribution."""
            ),
            Bug(
                """Don't hide the main window when it's iconized by default 
because on Linux with some window managers the main window receives minimize 
events in other situations as well, most notably when changing virtual 
desktops. So, to reduce the chances of confusing new users this option is off 
by default.""",
                "1721166",
            ),
        ],
        featuresAdded=[
            Feature("""Added Breton translation thanks to Ronan Le DÃ©roff"""),
            Feature(
                """Show a tooltip with a task's description when the mouse
is hovering over a task. Patch provided by Jérôme Laheurte.""",
                "1642608",
                "1619521",
                "1578623",
            ),
            Feature(
                """Allow for dragging emails from Thunderbird and Outlook to 
the attachment pane of tasks to create email attachments. Opening an attached 
email will open it in the user's default mail program. Patch provided by 
Jérôme Laheurte."""
            ),
        ],
    ),
    Release(
        "0.63.2",
        "April 20, 2007",
        bugsFixed=[
            Bug(
                """Task tree view does not refresh tasks after task editing.""",
                "1701368",
            )
        ],
    ),
    Release(
        "0.63.1",
        "April 16, 2007",
        bugsFixed=(
            Bug(
                """Dropping a file on a task in the tree viewer didn't work."""
            ),
            Bug(
                """Showing the description column in the composite effort viewers 
(effort per day, per week, per month) caused exceptions."""
            ),
            Bug(
                """The task tree viewer was trying to update tasks that weren't
shown, resulting in exceptions.""",
                "1697568",
                "1697574",
            ),
        ),
    ),
    Release(
        "0.63.0",
        "April 9, 2007",
        featuresAdded=(
            Feature(
                """Export to HTML and printing of tasks colors tasks 
appropriately."""
            ),
            Feature(
                """Added description columns to the task and effort viewers. 
Like other columns, the description column is printed and exported if 
visible."""
            ),
            Feature("""Added reminder column to the task viewers."""),
        ),
        bugsFixed=(
            Bug("""Cancelling printing would give a 'Task Coach Error'"""),
            Bug(
                """Make sure the main window is on a visible display when starting. 
This is for laptop users that sometimes extend their desktop to a second 
display.""",
                "1667120",
            ),
            Bug(
                """Sort categories alphabetically in the categories viewer.""",
                "1694532",
            ),
            Bug(
                """Filtering a category no longer automatically checks all 
subcategories. However, tasks belonging to a subcategory are still filtered 
(since they belong to the filtered category via the subcategory)."""
            ),
        ),
    ),
    Release(
        "0.62.0",
        "April 1, 2007",
        dependenciesChanged=[
            Dependency(
                """Task Coach now requires 
wxPython 2.8.3-unicode or newer (this is only relevant if you use the 
source distribution)."""
            )
        ],
        bugsFixed=[
            Bug(
                """When saving timestamps in a task file, e.g. for effort start
and stop times, microseconds are no longer saved as part of the timestamp. 
The microseconds caused problems when importing Task Coach data in
Excel.""",
                "1660670",
            ),
            Bug(
                """When exporting tasks to HTML or CSV format from the task
tree viewer, child tasks hidden by a filter would still be exported.""",
                "1659307",
            ),
        ],
        featuresAdded=[
            Feature("Added Slovak translation thanks to Viliam BÃºr"),
            Feature(
                """Printing a selection is enabled (except on Mac OSX)."""
            ),
            Feature(
                """The notebook that contains the different views allows for
dragging and dropping of tabs, enabling you to create almost any layout you
like. Unfortunately, this widget does not yet provide functionality to store
the layout in the TaskCoach.ini file."""
            ),
            Feature(
                """Whether the clock icon in the task bar blinks
or not is now a setting (see Edit -> Preferences -> Window 
behavior."""
            ),
            Feature(
                """The toolbar buttons for 'new item', 'new sub item',
'edit item' and 'delete item' now work for tasks, effort records
and categories, depending on what view is active."""
            ),
            Feature(
                """Added a category column for task viewers.""", "1629283"
            ),
            Feature(
                """Added an attachment column that shows whether a task
has one or more attachments."""
            ),
            Feature("""Added an 'Open all attachments' menu item for tasks"""),
            Feature("""Added snooze option to reminders."""),
        ],
        featuresChanged=[
            Feature(
                """Removed filter sidebar. Filter options previously available 
on the sidebar are now available via the search filter on the toolbar, the
category tab and the view menu. """
            )
        ],
    ),
    Release(
        "0.61.6",
        "January 27, 2007",
        bugsFixed=[
            Bug(
                """Crash on trying to use down-arrow to move to sub-task.""",
                "1640806",
            ),
            Bug(
                """When deleting a task that has subtasks that belong to categories,
the task file gets 'corrupted', giving errors when loading it.""",
                "1638419",
                "1589993",
            ),
        ],
    ),
    Release(
        "0.61.5",
        "January 10, 2007",
        bugsFixed=[
            Bug(
                """Opening a Task Coach file with many effort records is slow.
Opening an edit dialog for a task with many effort records is slow too.""",
                "1630102",
            )
        ],
    ),
    Release(
        "0.61.4",
        "December 30, 2006",
        featuresAdded=[Feature("Added RPM and Debian distributions.")],
        bugsFixed=[
            Bug("Make Task Coach work with Python 2.5."),
            Bug("Cancel reminders when marking a task completed.", "1606990"),
            Bug("Unchecking a reminder would cause an exception.", "1606990"),
            Bug("Column resizing is now less jumpy.", "1606319"),
            Bug(
                "MSVCP71.DLL was missing from the Windows distribution.",
                "1602364",
            ),
            Bug(
                """Marking a task completed while completed tasks are hidden 
wouldn't immediately hide the completed task.""",
                "1572920",
            ),
            Bug(
                """The category filter was not applied correctly on launch; 
showing categories as filtered but not hiding the associated tasks.""",
                "1603846",
            ),
            Bug(
                """Turning on filtering for a category didn't mark the
task file as changed.""",
                "1603846",
            ),
        ],
    ),
    Release(
        "0.61.3",
        "November 19, 2006",
        bugsFixed=[
            Bug(
                """If saving the TaskCoach.ini file would fail, displaying
the error message would fail (too) because the i18n translator had not
been imported at that point.""",
                "1598568",
            ),
            Bug(
                """Mac OSX distribution did not start. Upgraded py2app.""",
                "1594190",
            ),
            Bug(
                """Dragging and dropping a task in the task tree view would 
sometimes drag the wrong task."""
            ),
            Bug(
                """Give category dialog focus and select default category title
to make it easier to quickly enter categories using the keyboard."""
            ),
            Bug(
                """The gdiplus.dll was missing from the Windows 
distribution.""",
                "1596843",
            ),
        ],
    ),
    Release(
        "0.61.2",
        "November 11, 2006",
        bugsFixed=[
            Bug(
                """Some Linux distributions do not have the BROWSER environment
variable set, causing errors. Be prepared.""",
                "1567244",
            ),
            Bug(
                """Saving failed with a UnicodeError if a category
description would contain non-ASCII characters.""",
                "1589991",
            ),
            Bug(
                """Deleting a task would not delete the task from the
categories it belonged to, resulting in errors upon next loading
of the task file.""",
                "1589993",
            ),
        ],
    ),
    Release(
        "0.61.1",
        "November 3, 2006",
        bugsFixed=[Bug("""Source distribution was missing some files.""")],
    ),
    Release(
        "0.61.0",
        "November 2, 2006",
        bugsFixed=[
            Bug(
                """Displaying a previously hidden toolbar would result in
an incorrectly drawn window.""",
                "1551885",
            ),
            Bug(
                """Exported HTML didn't contain an explicit charset.""",
                "1561490",
            ),
            Bug(
                """Negative effort preventation was not working correctly.""",
                "1575458",
            ),
        ],
        featuresAdded=[
            Feature("""Hierarchical categories."""),
            Feature(
                """Export in Comma Separated Values (CSV) format. As
with export to HTML, the current view is exported.""",
                "1534862",
            ),
            Feature(
                """Task Coach can be run from a removable medium, such as a 
USB stick. On Windows, use the installer to install Task Coach to the medium.
Then, start Task Coach and turn the setting 'Save settings to same 
directory as program' on. This setting can be found in Edit -> Preferences -> 
File). This makes sure the TaskCoach.ini file is saved on the 
removable medium, in the same directory as the main program.""",
                "1464435",
            ),
        ],
    ),
    Release(
        "0.60",
        "August 30, 2006",
        bugsFixed=[
            Bug(
                """Closing a task file did not reset the 'lastfile'
setting.""",
                "1548126",
            ),
            Bug(
                """Selecting Japanese translation would cause error upon next 
restart.""",
                "1545593",
            ),
            Bug(
                """Task Coach wouldn't quit when the setting 'Minimize window
when closing' was set.""",
                "1545936",
            ),
            Bug(
                """Deleting an effort record would throw an exception.""",
                "1548117",
            ),
        ],
        websiteChanges=[
            Website("Added MD5 digests to download page.", "download.html")
        ],
    ),
    Release(
        "0.59",
        "August 23, 2006",
        bugsFixed=[
            Bug(
                """Improved efficiency while tracking effort for tasks.""",
                "1429545",
            ),
            Bug(
                """The column width of the list with filenames in the attachment 
page of the task editor is now adaptable, so that long filenames can be made 
visible entirely.""",
                "1503006",
            ),
            Bug("""Translation errors in tips.""", "1525410", "1525423"),
            Bug(
                """When having multiple tasks with the same subject, new effort
records would always be created for the first of these tasks instead of the
selected task.""",
                "1513403",
                "1524037",
            ),
            Bug(
                """Opening a file with a non-ascii filename specified on the 
command line did not work.""",
                "1532528",
            ),
        ],
        featuresAdded=[
            Feature("""Japanese translation thanks to Yutaka Usui."""),
            Feature("""Filter sidebar."""),
            Feature(
                """Printing. Selecting 'File' -> 'Print' will print the 
currently active view. This means only the visible columns will be
printed and only the filtered tasks will be printed, in the current sort
order.""",
                "1481881",
                "1472662",
                "1307275",
                "1205819",
            ),
            Feature(
                """Export to HTML. Selecting 'File' -> 'Export' ->
'Export to HTML' will export the currently active view to HTML. This
means only the visible columns will be exported and only the filtered
tasks will be printed, in the current sort order.""",
                "1375773",
                "1205819",
            ),
            Feature("""Columns with numbers or dates are right-aligned."""),
        ],
    ),
    Release(
        "0.58",
        "May 14, 2006",
        bugsFixed=[
            Bug("""On Mac OSX, Task Coach would seg fault upon exiting."""),
            Bug(
                """Right-clicking a task in the task tree view would,
correctly, pop up the context menu, but would not select the underlying
task.""",
                "1440416",
            ),
            Bug(
                """The memory leak in the TreeListCtrl was fixed in wxPython
2.6.3.2. The installer for Windows and the disk image for Mac OSX use
wxPython 2.6.3.2, thus fixing the memory leak in Task Coach. If you use
the source distribution of Task Coach you will have to install wxPython
2.6.3.2 yourself to get the fix.""",
                "1309858",
            ),
            Bug("""Filtering on task categories was improved."""),
            Bug(
                """Hitting Delete when editing the text in the find dialog would 
delete any selected tasks. Unfortunately, to fix this bug some accelerators had
to be changed: the accelerator for "Delete task" is now Ctrl-Delete, for 
"New task" it is now Ctrl-Insert, and for "New subtask" it is now 
Shift-Ctrl-Insert.""",
                "1463316",
            ),
            Bug(
                """Don't close the current file when user cancels opening another
file.""",
                "1475473",
            ),
        ],
        featuresAdded=[
            Feature("""Added toolbar button for 'new subtask'."""),
            Feature(
                """Task Coach searches incrementally as you type a query 
in the find bar."""
            ),
            Feature(
                """When dragging a task in the tree view, hover over
a tree button (a boxed plus-sign or a triangle, depending on your
platform) to expand the sub tree."""
            ),
            Feature(
                """To promote a sub task to a top-level task in the tree
view, drag it and drop it anywhere as long as it is not on another task."""
            ),
            Feature(
                """When filtering tasks by multiple categories, you may 
either choose to view tasks that belong to at least one of the selected
categories, or view tasks that belong to all selected categories."""
            ),
        ],
    ),
    Release(
        "0.57",
        "March 16, 2006",
        featuresAdded=[
            Feature(
                """Task Coach is now also available as disk image (.dmg)
for Mac OSX (tested on OSX 10.4)."""
            )
        ],
        bugsFixed=[
            Bug(
                """When adding a new effort to a task, take into account that the
user may have changed the task that the effort belongs to in the effort editor
dialog (using the dropdown combobox). Because Task Coach didn't do that, the
effort would be added twice if the user changed the task of the new effort
record.""",
                "1443906",
            ),
            Bug(
                """A file that was saved with an active effort couldn't be loaded 
again. Task Coach would complain that the file was invalid.""",
                "1433611",
            ),
            Bug(
                """Added different sizes of the Task Coach icon. This 
prevents scaling up the 16x16 version to 32x32 on Windows or to even 128x128
on the Mac.""",
                "1406651",
                "1434044",
            ),
        ],
    ),
    Release(
        "0.56",
        "February 14, 2006",
        featuresAdded=[
            Feature(
                """Tasks can have attachments. Attachments can be added, removed
and opened. Opening of attachments is done by starting the default application
for the attachment file type. Attachments can also be dragged from a file 
browser and dropped onto a task in one of the task viewers or on the task 
attachment pane in the task editor dialog.""",
                "1250241",
                "1339113",
            ),
            Feature(
                """Whether a task is marked completed when all its
child tasks are completed is now a setting that can be changed application-wide
via the preferences dialog. The application-wide setting can be overruled
on a task-by-task basis via the task editor dialog.""",
                "1393803",
            ),
            Feature(
                """Task Coach shows a 'tips' dialog at startup. Hopefully it
is helpful for new users. Experienced users can turn it off."""
            ),
        ],
        featuresChanged=[
            Feature(
                """More visual feedback when dragging tasks in the tree 
view."""
            ),
            Feature(
                """Task editor layout changed. Priority is now part of the
task description. Budget and revenue have been merged into one pane.""",
                "1312284",
            ),
        ],
        implementationChanged=[
            Implementation(
                """Default values for task and effort attributes are 
no longer saved in the Task Coach file, resulting in an estimated 33%% 
reduction of file size."""
            )
        ],
    ),
    Release(
        "0.55",
        "January 13, 2006",
        dependenciesChanged=[
            Dependency(
                """Task Coach now requires wxPython 2.6.1.0-unicode or newer
(this is only relevant if you use the source distribution)."""
            )
        ],
        bugsFixed=[Bug("""Sorting by total budget was broken.""", "1399116")],
        featuresAdded=[Feature("""Simple reminders.""", "1372932")],
    ),
    Release(
        "0.54",
        "January 6, 2006",
        bugsFixed=[
            Bug(
                """The accelerators INSERT and Ctrl+INSERT were mapped to 'c'
and 'Command-Copy' on the Mac, which caused Task Coach to create a new task
whenever the user typed a 'c'. Fixed by changing the accelerators for
new task and new subtask to Ctrl+N and Shift+Ctrl+N (on the Mac only).""",
                "1311413",
            ),
            Bug(
                """It was possible to enter control characters -- by 
copy-and-pasting -- resulting in invalid XML in the Task Coach 
file.""",
                "1288689",
            ),
            Bug(
                """One python file was missing in the source distribution
of release 0.53. Added a test to check that all python files in the source
are actually added to the source distributions, so hopefully this will never
happen again.""",
                "1389224",
            ),
        ],
        featuresAdded=[
            Feature(
                """Effort can be exported as iCalendar (ICS) file and imported
into e.g. Mozilla Sunbird. Each effort record is exported as a "VEVENT".
This is an experimental feature. Patch provided by Gissehel."""
            )
        ],
    ),
    Release(
        "0.53",
        "December 19, 2005",
        bugsFixed=[
            Bug(
                """On some platforms, Python and wxPython seem to disagree on what
the maximum integer is. The maximum integer is used to set the maximum and 
minimum allowed priority values. Fixed by allowing priority values between 
the rather arbitrary minimum and maximum values of -1000000000 and
1000000000."""
            ),
            Bug(
                """Fixed exception: "wx._core.PyAssertionError: C++ assertion
"ucf.GotUpdate()" failed in ..\..\src\msw\textctrl.cpp(813): EM_STREAMIN didn't 
send EN_UPDATE?". This seems to be a bug in wxPython 2.6.0 and 2.6.1.
Patch provided by Franz Steinhaeusler.""",
                "1344023",
            ),
        ],
        featuresAdded=[
            Feature(
                """Columns in the effort view are hideable too, just like
columns in the task views. See 'View' -> 'Effort columns', or right-click
a column header in the effort view."""
            ),
            Feature(
                """Added possibility to mail tasks via your default mailer, see 
'Task' -> 'Mail task' or right-click a task in one of the task views."""
            ),
            Feature(
                """Added option to minimize the window when you attempt
to close the application via the close button on the window title bar or 
the system menu. See 'Edit' -> 'Preferences' -> 'Window behavior'."""
            ),
        ],
    ),
    Release(
        "0.52",
        "November 29, 2005",
        featuresRemoved=[
            Feature(
                """Files in the old comma-separated format can no longer
be read by Task Coach."""
            )
        ],
        featuresAdded=[
            Feature("""Tasks can be dragged and dropped.""", "1262863"),
            Feature(
                """Tasks can have an hourly fee and/or a fixed fee. Revenue
is calculated based on effort spent.""",
                "1361790",
            ),
            Feature(
                """First tiny steps towards a user manual, see 'Help' -> 
'Help contents'."""
            ),
            Feature(
                """Whether the main window hides itself when iconized is now
adjustable behavior. See 'Edit' -> 'Preferences'."""
            ),
        ],
        featuresChanged=[
            Feature(
                """Backups are created just before saving, instead of when 
loading a .tsk file. Patch provided by Maciej Malycha."""
            )
        ],
        bugsFixed=[
            Bug(
                """For completed tasks, the number of days left for a task is 
now the number of days between the completion date and the due 
date. This prevents that the number of days left of completed tasks keeps 
decreasing, i.e. becoming more negative. For uncompleted tasks, the number
of days left is still the number of days between today and the due date, 
of course. Patch provided by Maciej Malycha."""
            ),
            Bug(
                """Put taskocachlib package first on the Python search path to
prevent name conflict with the config module on Gentoo Linux.""",
                "1353636",
            ),
            Bug(
                """Mention blue icon in the help on task colors.""", "1355985"
            ),
            Bug("""Don't allow empty categories.""", "1333896"),
        ],
    ),
    Release(
        "0.51",
        "October 30, 2005",
        featuresAdded=[
            Feature(
                """Escape closes pop-up windows. Patch provided by
Markus Meyer.""",
                "1241547",
            ),
            Feature("""The task of an effort record can be changed."""),
            Feature("""Effort records can be cut, copied, and pasted."""),
        ],
        bugsFixed=[
            Bug("""Hitting enter in the find dialog didn't work on Linux."""),
            Bug(
                """Old TaskCoach.ini files with a language setting of 'en' instead
of 'en_US' or 'en_GB' would cause an exception. Patch provided by 
Nirendra Maharaj."""
            ),
        ],
    ),
    Release(
        "0.50",
        "October 2, 2005",
        bugsFixed=[
            Bug(
                """Exception was thrown when opening a task with logged effort."""
            )
        ],
    ),
    Release(
        "0.49",
        "October 2, 2005",
        bugsFixed=[
            Bug(
                """Previous release did not work on Linux/Mac OSX because of a
platform inconsistency between Windows and Linux (GetCountPerPage method 
is missing on Linux, added manually).""",
                "1305457",
            )
        ],
        featuresAdded=[
            Feature(
                """Task colors can be adjusted via 
'Edit' -> 'Preferences'.""",
                "1205579",
            )
        ],
    ),
    Release(
        "0.48",
        "September 24, 2005",
        bugsFixed=[
            Bug(
                """Filtering tasks by status ('View' -> 'Tasks that are' -> '...')
would cause an exception."""
            ),
            Bug(
                """Sorting by days left would cause an exception.""", "1295122"
            ),
        ],
    ),
    Release(
        "0.47",
        "September 18, 2005",
        featuresAdded=[
            Feature(
                """Added Hungarian translation thanks to Majsa Norbert."""
            ),
            Feature(
                """The task tree view now also shows columns with task details,
similar to the task list view.""",
                "1194642",
            ),
            Feature(
                """Sorting on task subject can now also be case 
insensitive. See the menu item 'View' -> 'Sort' -> 'Sort case sensitive'.""",
                "1228873",
            ),
            Feature(
                """Recent files are remembered and can be opened from the 
File menu. The maximum number of recent files shown can be set in the
Preferences dialog. Set the maximum to zero to disable this feature. """,
                "1191707",
            ),
            Feature("""The last modification time of tasks can be viewed."""),
        ],
        bugsFixed=[
            Bug(
                """'View'->'All tasks' now also resets any search criterium entered
by the user in the search bar."""
            ),
            Bug(
                """When opening a task with a (long) description, the cursor will
be positioned on the first line of the text, instead of on the last line.""",
                "1265845",
            ),
            Bug(
                """When viewing tasks due before a certain date in the tree view,
tasks with subtasks due before that date will be visible.""",
                "1275708",
            ),
        ],
    ),
    Release(
        "0.46",
        "August 12, 2005",
        bugsFixed=[
            Bug(
                """In the effort views, the status bar would show information about
tasks, not about effort."""
            ),
            Bug(
                """Entering a negative effort duration while using a non-english 
language would crash Task Coach.""",
                "1250177",
            ),
            Bug(
                """Having a two letter language string (e.g. 'en') in the 
TaskCoach.ini file would cause an error in the preferences dialog.""",
                "1247506",
            ),
        ],
        featuresChanged=[
            Feature(
                """Keyboard shortcut for deleting a task is now 'Delete'
instead of 'Ctrl-D' and 'Ctrl-Enter' marks the selected task(s) completed.""",
                "1241549",
            )
        ],
        featuresAdded=[
            Feature(
                """Double-clicking the system tray icon when Task Coach
is not minimized will raise the Task Coach window.""",
                "1242520",
            ),
            Feature("""Added Spanish translation thanks to Juan JosÃ©."""),
        ],
        implementationChanged=[
            Implementation(
                """Task ids are now persistent, i.e. they are saved to
and loaded from the Task Coach (XML) file. This will make it easier, in the future,
to keep tasks synchronized with external sources, e.g. Outlook."""
            ),
            Implementation(
                """Task Coach now keeps track of the last modification 
time of tasks. These times are saved to and loaded from the Task Coach (XML) file.
This change is also in preparation of synchronization functionality."""
            ),
        ],
    ),
    Release(
        "0.45",
        "July 26, 2005",
        bugsFixed=[
            Bug(
                """When tracking effort the task file would be marked as 
changed after every clock tick."""
            ),
            Bug(
                """Task priority can now be set to both positive and
negative integers."""
            ),
            Bug(
                """Opening a help dialog before the splash screen disappeared
would make Task Coach stop responding to input. Fixed by making the
helpdialogs modeless (as they should be).""",
                "1241058",
            ),
        ],
        featuresChanged=[
            Bug(
                """Setting the start date of a subtask earlier than the
start date of the parent task, or setting the due date of a subtask
later than the due date of the parent task will adapt the parent start
or due date as necessary.""",
                "1237634",
            )
        ],
    ),
    Release(
        "0.44",
        "July 21, 2005",
        featuresAdded=[
            Feature("Added Russian translation thanks to Valdimir Ilyash.")
        ],
    ),
    Release(
        "0.43",
        "July 19, 2005",
        bugsFixed=[
            Bug(
                """Tree and list view were not updated correctly when changing sort key 
or sort order."""
            )
        ],
    ),
    Release(
        "0.42",
        "July 17, 2005",
        bugsFixed=[
            Bug(
                """Double clicking a task with children in the tree view would 
open the edit dialog and expand or collapse the task as well. Fixed to not 
collapse or expand the task when double clicking it."""
            ),
            Bug(
                """Adding a subtask to a collapsed parent task now automatically
expands the parent task."""
            ),
            Bug(
                """Changing the description of a task or effort record wouldn't 
mark the task file as changed."""
            ),
            Bug("Time spent is now updated every second.", "1173048"),
            Bug(
                """Don't try to make a backup when loading the file fails. 
Reported by Scott Schroeder."""
            ),
            Bug(
                """(Windows installer only) Association between .tsk files and
Task Coach was broken."""
            ),
        ],
        featuresChanged=[
            Feature(
                """The start date of a task can now be left unset, creating
a task that is permanently inactive. This can be useful for activities that
you would normally not want to plan, but have to keep a time record for, e.g.
sickness."""
            )
        ],
    ),
    Release(
        "0.41",
        "June 20, 2005",
        bugsFixed=[],
        featuresAdded=[
            Feature(
                """URL's (including mailto) in task and effort descriptions are
clickable.""",
                "1190310",
            ),
            Feature(
                """Tasks can have a priority. Priorities are integer numbers:
the higher the number, the higher the priority. Default priority is 0.
Negative numbers are allowed""",
                "1194527",
                "1194567",
                "1210154",
            ),
        ],
        featuresChanged=[
            Feature(
                """Default start date of new subtasks is today
(used to be the start date of the parent task)"""
            ),
            Feature(
                """When 'sort by status first' is on, active tasks always come
before inactive tasks which in turn come before completed tasks, regardless of
whether the sort order is ascending or descending."""
            ),
        ],
    ),
    Release(
        "0.40",
        "June 16, 2005",
        bugsFixed=[
            Bug(
                "Budget left was rendered incorrectly when over budget.",
                "1216951",
            )
        ],
        featuresAdded=[
            Feature(
                """Tasks can belong to zero or more categories.
Tasks can be viewed/hidden by category.""",
                "1182172",
            )
        ],
    ),
    Release(
        "0.39",
        "June 6, 2005",
        bugsFixed=[
            Bug(
                """When sorting by due date, composite tasks in the tree view are
now sorted according to the most urgent subtask instead of the least urgent
subtask."""
            )
        ],
        featuresAdded=[
            Feature(
                """Tasks can be sorted on all attributes (subject, start date,
due date, budget, etc.) This includes options to sort ascending or descending
and to first sort by status (active/inactive/completed)."""
            ),
            Feature(
                "Sorting order can be changed by clicking on column headers."
            ),
            Feature("Added German translation, thanks to J. Martin."),
            Feature("Minor view menu changes.", "1189978"),
        ],
    ),
    Release(
        "0.38",
        "May 22, 2005",
        featuresAdded=[
            Feature(
                "Simplified Chinese user interface added, thanks to limodou."
            ),
            Feature(
                "Autosave setting to automatically save after every change.",
                "1188194",
            ),
            Feature(
                """Backup setting to create a backup when opening a Task
Coach file."""
            ),
            Feature(
                """Added preference dialog to edit preferences not related
to the view settings."""
            ),
            Feature("Now using gettext for i18n."),
        ],
    ),
    Release(
        "0.37",
        "May 14, 2005",
        bugsFixed=[Bug("Icons in tree view on Windows 2000.", "1194654")],
        featuresAdded=[
            Feature(
                """Columns in the task list view can be turned on/off by
right-clicking on the column headers."""
            ),
            Feature(
                "Tasks can be sorted either by due date or alphabetically.",
                "1177984",
            ),
            Feature("More options when editing an effort record."),
            Feature("Used a new DatePickerCtrl.", "1191909"),
        ],
    ),
    Release(
        "0.36",
        "May 5, 2005",
        bugsFixed=[
            Bug("Descriptions loose newlines after reload.", "1194259")
        ],
        featuresAdded=[
            Feature("French user interface added, thanks to Jérôme Laheurte.")
        ],
    ),
    Release(
        "0.35",
        "May 2, 2005",
        bugsFixed=[
            Bug(
                """Toolbar icons had a black background instead of a transparent
background on some Windows platforms.""",
                "1190230",
            ),
            Bug("Package i18n was missing.", "1190967"),
        ],
        featuresAdded=[
            Feature(
                """Internationalization support. Task Coach is available with
Dutch and English user interface.""",
                "1164461",
            ),
            Feature(
                """Added 'expand selected task' and 'collapse selected task'
menu items to the view menu and the task context menu.""",
                "1189978",
            ),
        ],
        featuresRemoved=[
            Feature(
                """'Select' -> 'Completed tasks'. This can be done through
the View menu too."""
            )
        ],
    ),
    Release(
        "0.34",
        "April 25, 2005",
        bugsFixed=[
            Bug(
                "msvcr71.dll was not shipped with the Windows installer.",
                "1189311",
            ),
            Bug(
                """Budgets larger than 24 hours were not written correctly to
the XML file."""
            ),
            Bug(
                "Mark completed stops effort tracking of parent task.",
                "1186667",
            ),
        ],
    ),
    Release(
        "0.33",
        "April 24, 2005",
        bugsFixed=[
            Bug(
                """The .tsk fileformat is now XML, making Task Coach fully
unicode-enabled."""
            )
        ],
    ),
    Release(
        "0.32",
        "April 18, 2005",
        bugsFixed=[
            Bug(
                """Task Coach failure on startup due to trying to add a column
from the task list view to the effort view."""
            ),
            Bug(
                """Budget couldn't be filled in in the executable Windows
distribution "LookupError: unknown encoding: latin1"."""
            ),
            Bug(
                "Loading files with the executable Windows distribution failed.",
                "1185259",
            ),
        ],
    ),
    Release(
        "0.31",
        "April 17, 2005",
        dependenciesChanged=[
            Dependency(
                """Task Coach migrated to Python 2.4.1 and wxPython
2.5.5.1. Added check to give friendly message if wxPython version is below 
the required version number."""
            )
        ],
        bugsFixed=[
            Bug(
                """A unittest.py bug that was fixed in Python 2.4 revealed a
bug in test.py.""",
                "1181714",
            ),
            Bug(
                """When searching for a task that is completed, while the
'show completed' switch is off, the search shows the path to
the task (i.e. parent tasks), but not the matched task itself.""",
                "1182528",
            ),
            Bug(
                """When searching for tasks in the tree view, composite tasks
are expanded automatically to show the children that match
the search string.""",
                "1182528",
            ),
            Bug(
                """Columns were hidden by setting their width to 0, but that did 
not make them entirely invisible on some Linux platforms.""",
                "1152566",
            ),
            Bug(
                """When editing a subtask, sometimes its branch would be
collapsed.""",
                "1179266",
            ),
        ],
        featuresAdded=[
            Feature(
                """In the task list and effort list the task column is 
automatically resized to take up the available space."""
            ),
            Feature(
                """Added columns to the task list view for: budget, 
total budget, budget left, and total budget left."""
            ),
            Feature(
                """Reorganized view menu, added extra task filters, 
added menu item to reset filters""",
                "1181762",
                "1178882",
                "1178780",
            ),
            Feature(
                """The subject is selected in the task editor so that 
replacing it is a bit easier.""",
                "1180887",
            ),
        ],
    ),
    Release(
        "0.30",
        "April 11, 2005",
        bugsFixed=[
            Bug(
                "More than one task due today would crash Task Coach.",
                "1180641",
            )
        ],
    ),
    Release(
        "0.29",
        "April 10, 2005",
        bugsFixed=[
            Bug(
                "New effort in the context menu did not work in release 0.28.",
                "1178562",
            ),
            Bug(
                """When selecting 'View' -> 'Completed tasks' in the task tree,
only completed root tasks were hidden.""",
                "1179372",
            ),
        ],
        featuresAdded=[
            Feature(
                """What tab is active is now a persistent setting. This
includes the tabs and choices in the main window and the effort choices in
the task editor.""",
                "1178779",
            ),
            Feature(
                "Reordered 'View' -> 'Tasks due before end of' menu.",
                "1178880",
            ),
            Feature("Added a separate 'Budget' tab in the task editor."),
            Feature(
                """Taskbar icon now indicates whether task effort tracking
is on.""",
                "1178057",
            ),
            Feature(
                "Effort is sorted from most recent to least recent.", "1179332"
            ),
            Feature(
                """Changed task/subtask separator in the task list view
from '|' to ' -> '.""",
                "1179374",
            ),
        ],
    ),
    Release(
        "0.28",
        "April 6, 2005",
        bugsFixed=[
            Bug(
                """Hitting return or double click to edit effort in the task
editor now works.""",
                "1172164",
            ),
            Bug(
                """Subtasks with the same name would only be visible once in
the task tree view."""
            ),
        ],
        featuresAdded=[
            Feature(
                """You can hide composite tasks in the task list view so
that only leaf tasks are visible. Menu item 'View' -> 'Tasks with subtasks'.
Requested by Brian Crounse."""
            )
        ],
    ),
    Release(
        "0.27",
        "April 4, 2005",
        featuresAdded=[Feature("Tasks can have a budget.")],
    ),
    Release(
        "0.26",
        "March 28, 2005",
        bugsFixed=[
            Bug(
                "Marking a task completed did not stop effort tracking.",
                "1159918",
            ),
            Bug("Reading lots of efforts was slow."),
        ],
        featuresAdded=[
            Feature(
                """Save button is disabled when saving is not necessary,
requested by Mike Vorozhbensky.""",
                "1164472",
            ),
            Feature(
                """Effort records have a description field, requested by
Kent.""",
                "1167147",
            ),
        ],
    ),
    Release(
        "0.25",
        "March 13, 2005",
        bugsFixed=[
            Bug(
                """The menu item 'Effort' -> 'New effort' did not work in
release 0.24."""
            )
        ],
        featuresAdded=[
            Feature("XML export now includes effort records."),
            Feature(
                """Effort per day, per week and per month view now also 
show total time spent (i.e. time including time spent on subtasks)."""
            ),
        ],
    ),
    Release(
        "0.24",
        "March 10, 2005",
        bugsFixed=[
            Bug(
                """Saving a selection of tasks to a separate file would also
save all effort records to that file (instead of just the effort records
for the selected tasks), giving errors when loading that file."""
            ),
            Bug(
                """Deleting a task with effort records would not delete the
effort records."""
            ),
        ],
        featuresAdded=[
            Feature(
                """The tracking status of tasks is saved. So if you start 
tracking a task, quit Task Coach, and restart Task Coach later, effort for 
that task is still being tracked. Requested by Bob Hossley."""
            )
        ],
    ),
    Release(
        "0.23",
        "February 20, 2005",
        bugsFixed=[
            Bug(
                """Fixed a couple of bugs in the unit tests, discovered by
Stephen Boulet and Jérôme Laheurte on the Linux platform."""
            )
        ],
    ),
    Release(
        "0.22",
        "February 17, 2005",
        bugsFixed=[
            Bug(
                """In the effort summary view, effort spent on a task in the
same month or week but in different years would erroneously be added.
E.g. effort in January 2004 and January 2006 would be added."""
            ),
            Bug(
                """The mechanism to prevent effort periods with a negative
duration (i.e.  a start time later than the stop time) in the effort editor
was invoked on each key stroke which caused inconvenient behavior. Fixed
it by only invoking it when the user leaves the text or combo box."""
            ),
        ],
        featuresAdded=[
            Feature(
                """Added possibility to start tracking effort for a task, 
with start time equal to the end time of the previous effort period. This is 
for example convenient if you stop working on a task and then spend some time 
deciding on what to do next. This is the 'Start tracking from last stop time' 
menu item in the 'Effort' menu."""
            ),
            Feature(
                """(Re)Added the unittests to the source distribution.
See INSTALL.txt."""
            ),
            Feature(
                """Export to XML. Currently limited to tasks, effort is not
exported yet."""
            ),
        ],
    ),
    Release(
        "0.21",
        "February 9, 2005",
        bugsFixed=[
            Bug(
                """Setting the start date/time in the effort editor would change
the stop date/time while not strictly necessary to prevent negative 
durations."""
            ),
            Bug(
                """Refreshing the virtual ListCtrl failed under
wxPython2.5-gtk2-unicode-2.5.3.1-fc2_py2.3 and
wxPython-common-gtk2-unicode-2.5.3.1-fc2_py2.3. Reported by Stephen
Boulet."""
            ),
            Bug(
                """After iconizing the main window for a second time, the icon
in the task bar wouldn't be hidden anymore. Reported and fixed by Jérôme
Laheurte."""
            ),
        ],
    ),
    Release(
        "0.20",
        "February 6, 2005",
        bugsFixed=[
            Bug("Reading .tsk files version 2 failed."),
            Bug(
                """Completed child tasks were not hidden in the tree view when
'View->Completed tasks' was on."""
            ),
            Bug("Hiding the find panel did not clear the search filter."),
            Bug(
                """When searching for tasks, not all matches were shown in the
tree view."""
            ),
            Bug(
                """Displaying time spent and total time spent in the list view
for more than a dozen tasks and efforts was slow. Used caching to speed it
up."""
            ),
            Bug(
                """Tool tips on the toolbar included mnemonics and accelerator
characters on Linux. Reported on python-2.3.4 and 
wxPython2.5-gtk2-unicode-2.5.3.1-fc2_py2.3 on Suse 9.2 by Stephen
Boulet."""
            ),
        ],
        featuresAdded=[
            Feature(
                """Effort can be viewed summarized per day, per week, and
per month."""
            ),
            Feature(
                """Effort for a specific task can be viewed (and edited) in
the task editor."""
            ),
            Feature(
                """Effort tracking can be stopped from the taskbar
menu."""
            ),
            Feature(
                """Size and position of the main window are saved in the
settings and restored on the next session. This also includes whether the
main window is iconized or not."""
            ),
            Feature("Splash screen can be turned off."),
        ],
    ),
]
