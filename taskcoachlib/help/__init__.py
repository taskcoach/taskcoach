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

import os

from taskcoachlib import meta
from taskcoachlib.i18n import _
from .tips import showTips
from .uicommand import *


_MSURL = "https://www.microsoft.com/en-us/download/details.aspx?id=5638"


def sequence(*text):
    return "".join(text)


def a_href(text, name):
    return '<a href="#%s">%s</a>' % (name, text)


def a_name(text, name):
    return '<a name="%s">%s</a>' % (name, text)


def h(level, text):
    return "<h%d>%s</h%d>" % (level, text, level)


def h3(text):
    return h(3, text)


def h4(text):
    return h(4, text)


def h5(text):
    return h(5, text)


def p(*text):
    return "<p>%s</p>" % "\n".join(text)


def ul(*li):  # pylint: disable=W0621
    return "<ul>%s</ul>" % "\n".join(li)


def li(*text):
    return "<li>%s</li>" % "\n".join(text)


def table(*tr):  # pylint: disable=W0621
    return "<table border=1>%s</table>" % "\n".join(tr)


def tr(*td):
    td = "\n".join(["<td>%s</td>" % td for td in td])
    return "<tr>%s</tr>\n" % td


_TOC = sequence(
    h3(_("Table of contents")),
    ul(
        li(
            a_href(_("Tasks"), "tasks"),
            ul(
                li(a_href(_("About tasks"), "abouttasks")),
                li(a_href(_("Task properties"), "taskproperties")),
                li(a_href(_("Task states"), "taskstates")),
                li(a_href(_("Task colors"), "taskcolor")),
                li(a_href(_("Reminders"), "reminders")),
            ),
        ),
        li(
            a_href(_("Effort"), "effort"),
            ul(
                li(a_href(_("About effort"), "abouteffort")),
                li(a_href(_("Effort properties"), "effortproperties")),
            ),
        ),
        li(
            a_href(_("Categories"), "categories"),
            ul(
                li(a_href(_("About categories"), "aboutcategories")),
                li(a_href(_("Category properties"), "categoryproperties")),
            ),
        ),
        li(
            a_href(_("Notes"), "notes"),
            ul(
                li(a_href(_("About notes"), "aboutnotes")),
                li(a_href(_("Note properties"), "noteproperties")),
            ),
        ),
        li(
            a_href(_("Printing and exporting"), "printingandexporting"),
            ul(
                li(
                    a_href(
                        _("About printing and exporting"),
                        "aboutprintingandexporting",
                    )
                ),
                li(a_href(_("Printing"), "printing")),
                li(a_href(_("Exporting"), "exporting")),
            ),
        ),
        li(
            a_href(_("Multi-user usage"), "multiuser"),
            ul(
                li(a_href(_("About multi-user"), "aboutmultiuser")),
                li(a_href(_("Storage options"), "storage")),
            ),
        ),
        li(
            a_href(_("E-mailing tasks"), "emailtasks"),
            ul(
                li(a_href(_("Custom attributes for e-mailing"), "emailcustom"))
            ),
        ),
        li(
            a_href(_("E-mail integration"), "email"),
            ul(
                li(a_href(_("About e-mail integration"), "aboutemail")),
                li(a_href(_("Attaching an e-mail to a task"), "emailattach")),
                li(a_href(_("Creating a task from an e-mail"), "emailcreate")),
            ),
        ),
        li(
            a_href(_("Task templates"), "templates"),
            ul(
                li(a_href(_("About templates"), "abouttemplates")),
                li(a_href(_("Using templates"), "usingtemplates")),
            ),
        ),
        li(a_href(_("Graphical user interface"), "gui")),
        li(a_href(_("Keyboard shortcuts"), "shortcuts")),
    ),
)


_taskSection = sequence(
    h3(a_name(_("Tasks"), "tasks")),
    h4(a_name(_("About tasks"), "abouttasks")),
    p(
        _(
            """Tasks are the basic objects that you manipulate. Tasks can
represent anything from a single little thing you have to do to a complete 
project consisting of different phases and numerous activities."""
        )
    ),
    h4(a_name(_("Task properties"), "taskproperties")),
    p(
        _("Tasks have the following properties you can change:"),
        ul(
            li(_("Subject: a single line that summarizes the task.")),
            li(_("Description: a multi-line description of the task.")),
            li(
                _(
                    """Planned start date: the first date on which the task can be started. 
The planned start date defaults to the date the task is created. It can also be 'None' 
indicating that you don't really want to start this task. This can be convenient 
for e.g. registering sick leave."""
                )
            ),
            li(
                _(
                    """Due date: the date the task should be finished. 
This can be 'None' indicating that this task has no fixed due date."""
                )
            ),
            li(
                _(
                    """Actual start date: the date the task was actually started.
The actual start date can be edited directly, but it is also set when you 
track effort for the task or when you set the percentage completed of a task
to a value between 0% and 100%."""
                )
            ),
            li(
                _(
                    """Completion date: this date is 'None' as long as the task has 
not been completed. It is set to the current date when you mark the task as 
completed. The completion date can also be entered manually."""
                )
            ),
            li(
                _(
                    """Prerequisites: other tasks that need to be completed before
a task can be started. The task remains inactive until the last prerequisite task is 
completed. Note that if the task has a specific planned start date set, that
date has to be in the past <em>and</em> all prerequisite tasks need to be
completed before the task becomes late."""
                )
            ),
            li(_("Budget: amount of hours available for the task.")),
            li(
                _(
                    "Hourly fee: the amount of money earned with the task per hour."
                )
            ),
            li(
                _(
                    """Fixed fee: the amount of money earned with the task 
regardless of the time spent."""
                )
            ),
        ),
    ),
    p(
        _(
            "The following properties are calculated from the properties above:"
        ),
        ul(
            li(_("Days left: the number of days left until the due date.")),
            li(
                _(
                    """Dependents: other tasks that can be started when the 
prerequisite task has been completed."""
                )
            ),
            li(_("Time spent: effort spent on the task.")),
            li(_("Budget left: task budget minus time spent on the task.")),
            li(_("Revenue: hourly fee times hours spent plus fixed fee.")),
        ),
    ),
    h4(a_name(_("Task states"), "taskstates")),
    p(
        _("Tasks always have exactly one of the following states:"),
        ul(
            li(_("Active: the actual start date is in the past;")),
            li(
                _(
                    """Inactive: the task has not been started and/or not all 
prerequisite tasks have been completed;"""
                )
            ),
            li(_("Completed: the task has been completed.")),
        ),
    ),
    p(
        _("In addition, tasks can be referenced as:"),
        ul(
            li(_("Overdue: the due date is in the past;")),
            li(
                _(
                    """Due soon: the due date is soon (what 'soon' is, can be 
changed in the preferences);"""
                )
            ),
            li(
                _(
                    """Late: the planned start is in the past and the task has 
not been started;"""
                )
            ),
            li(_("Over budget: no budget left;")),
            li(_("Under budget: still budget left;")),
            li(_("No budget: the task has no budget.")),
        ),
    ),
    h4(a_name(_("Task colors"), "taskcolors")),
    p(
        _("The text of tasks is colored according to the following rules:"),
        ul(
            li(_("Overdue tasks are red;")),
            li(_("Tasks due soon are orange;")),
            li(_("Active tasks are black text with a blue icon;")),
            li(_("Late tasks are purple;")),
            li(_("Future tasks are gray, and")),
            li(_("Completed tasks are green.")),
        ),
        _(
            """This all assumes you have not changed the text colors through the 
preferences dialog, of course."""
        ),
    ),
    p(
        _(
            """The background color of tasks is determined by the categories the 
task belongs to. See the section about 
<a href="#categoryproperties">category properties</a> below."""
        )
    ),
    h4(a_name(_("Reminders"), "reminders")),
    p(
        _(
            """You can set a reminder for a specific date and time. %(name)s will
show a reminder message at that date and time. From the reminder dialog
you can open the task, start tracking effort for the task, or mark the task
completed. It is also possible to snooze the reminder."""
        )
        % meta.metaDict
    ),
)

_effortSection = sequence(
    h3(a_name(_("Effort"), "effort")),
    h4(a_name(_("About effort"), "abouteffort")),
    p(
        _(
            """Whenever you spent time on tasks, you can record the amount of time
spent by tracking effort. Select a task and invoke 'Start tracking effort' in
the Effort menu or context menu or via the 'Start tracking effort' toolbar 
button."""
        )
    ),
    h4(a_name(_("Effort properties"), "effortproperties")),
    p(
        _("Effort records have the following properties you can change:"),
        ul(
            li(_("Task: the task the effort belongs to.")),
            li(_("Start date/time: start date and time of the effort.")),
            li(
                _(
                    """Stop date/time: stop date and time of the effort. This can be 
'None' as long as you are still working on the task."""
                )
            ),
            li(_("Description: a multi-line description of the effort.")),
        ),
    ),
    p(
        _(
            "The following properties are calculated from the properties above:"
        ),
        ul(
            li(
                _(
                    "Time spent: how much time you have spent working on the task."
                )
            ),
            li(_("Revenue: money earned with the time spent.")),
        ),
    ),
)

_categorySection = sequence(
    h3(a_name(_("Categories"), "categories")),
    h4(a_name(_("About categories"), "aboutcategories")),
    p(
        _(
            """Tasks and notes may belong to one or more categories. First, you 
need to create the category that you want to use via the 'Category' menu. Then, 
you can add items to one or more categories by editing the item and checking the 
relevant categories for that item in the category pane of the edit dialog."""
        )
    ),
    p(
        _(
            """You can limit the items shown in the task and notes viewers to one 
or more categories by checking a category in the category viewer. For example, 
if you have a category 'phone calls' and you check that category, the task 
viewers will only show tasks belonging to that category; in other words the 
phone calls you need to make."""
        )
    ),
    h4(a_name(_("Category properties"), "categoryproperties")),
    p(
        _("Categories have the following properties you can change:"),
        ul(
            li(_("Subject: a single line that summarizes the category.")),
            li(_("Description: a multi-line description of the category.")),
            li(
                _(
                    """Mutually exclusive subcategories: a check box indicating
whether the subcategories of the category are mutually exclusive. If they are,
items can only belong to one of the subcategories. When filtering, you can only
filter by one of the subcategories at a time."""
                )
            ),
            li(
                _(
                    """Appearance properties such as icon, font and colors: 
the appearance properties are used to render the category, but also the items
that belong to that category. If a category has no color, font or icon of its 
own, but it has a parent category with such a property, the parent's property 
will be used. If an item belongs to multiple categories that each have a color 
associated with it, a mixture of those colors will be used to render that 
item."""
                )
            ),
        ),
    ),
)

_noteSection = sequence(
    h3(a_name(_("Notes"), "notes")),
    h4(a_name(_("About notes"), "aboutnotes")),
    p(
        _(
            """Notes can be used to capture random information that you want
to keep in your task file. Notes can be stand-alone or be part of other items,
such as tasks and categories. Stand-alone notes are displayed in the notes
viewer. Notes that are part of other items are not displayed in the notes
viewer."""
        )
    ),
    h4(a_name(_("Note properties"), "noteproperties")),
    p(
        _("Notes have the following properties you can change:"),
        ul(
            li(_("Subject: a single line that summarizes the note.")),
            li(_("Description: a multi-line description of the note.")),
            li(_("Appearance properties such as icon, font and colors.")),
        ),
    ),
)


_printingAndExportingSection = sequence(
    h3(a_name(_("Printing and exporting"), "printingandexporting")),
    h4(a_name(_("About printing and exporting"), "aboutprintingandexporting")),
    p(
        _(
            """Both printing and exporting work in the same way: when you print
or export data, the data from the active viewer is printed or exported.
Moreover, the data is printed or exported in the same way as the viewer is 
displaying it. The data is printed or exported in the same order as the
viewer is displaying it. The columns that are visible determine what 
details get printed or exported. When you filter items, for example hide
completed tasks, those items don't get printed or exported."""
        )
    ),
    h4(a_name(_("Printing"), "printing")),
    p(
        _(
            """Prepare the contents of a viewer, by putting the items in the 
right order, show or hide the appropriate columns and apply the relevant 
filters."""
        )
    ),
    p(
        _(
            """You can preview how the print will look
using the File -> Print preview menu item. You can edit the page settings
using File -> Page setup. When printing and the platform supports it, you can 
choose to print all visible items in the active viewer, or just the 
selected items."""
        )
    ),
    h4(a_name(_("Exporting"), "exporting")),
    p(
        _(
            """Prepare the contents of a viewer, by putting the items in the 
right order, show or hide the appropriate columns and apply the relevant 
filters."""
        )
    ),
    p(
        _(
            """Next, choose the format you want to export to and whether you
want to export all visible items or just the selected ones. Available formats
to export to include CSV (comma separated format), HTML and iCalendar. When
you export to HTML, a CSS file is created that you can edit to change
the appearance of the HTML."""
        )
    ),
)

_emailTasksSection = sequence(
    h3(a_name(_("E-mailing tasks"), "emailtasks")),
    h4(a_name(_("Custom attributes for e-mailing tasks"), "emailcustom")),
    p(
        _(
            """You can alter the behaviour of the e-mail command using custom attributes
in a task description. Those attributes must be on a line by themselves. Supported
attributes are 'cc' and 'to'. Examples:"""
        )
        % meta.metaDict
    ),
    p(_("[email:to=foo@spam.com]")),
    p(_("[email:cc=bar@spam.com]")),
)

_multiuserSection = sequence(
    h3(a_name(_("Multi-user usage"), "multiuser")),
    h4(a_name(_("About multi-user"), "aboutmultiuser")),
    p(
        _(
            """A task file may be opened by several instances of %(name)s, either
running on the same computer or on different ones, on a network share for
instance. When you save, %(name)s will actually merge your work with whatever
has been saved on disk since the last time you did. Conflicts are automatically
resolved, usually by you winning the conflict. This serves two use cases:"""
        )
        % meta.metaDict
    ),
    ul(
        li(
            _(
                """A single user, opening the task file on several computers (work,
home, laptop)."""
            )
        ),
        li(_("""Several users working on the same task file.""")),
    ),
    p(
        _(
            """The first case is the most common and the most secure. The second
case may be dangerous. Most network disk sharing protocols do not support the
kind of file locking that would make this 100% secure. A list of common protocols
and their behaviour follows."""
        )
    ),
    h4(a_name(_("Storage options"), "storage")),
    p(
        _(
            """None of the sharing options discussed here work fully. If two users
save their changes within a few hundreds of milliseconds time frame, data will be lost."""
        )
    ),
    h5(_("SMB/CIFS")),
    p(
        _(
            """This is the most common protocol: Windows shares and their lookalikes
(Samba). If the server and client don't support certain extensions, Task Coach will not
be able to detect automatically when the file has been modified by someone else."""
        )
    ),
    h5(_("NFS")),
    p(_("Not tested yet.")),
    h5(_("DropBox")),
    p(
        _(
            """A popular way to access files from several computers (also see SpiderOak
for a more secure alternative). Changes to the task file are correctly detected by %(name)s
when it's updated."""
        )
        % meta.metaDict
    ),
)


_emailSection = sequence(
    h3(a_name(_("E-mail integration"), "email")),
    h4(a_name(_("About e-mail integration"), "aboutemail")),
    p(
        _(
            """%(name)s integrates with several mail user
agents, through drag and drop. This has some limitations; e-mails are
copied in a directory next to the %(name)s file, as .eml files and are
later opened using whatever program is associated with this file type
on your system. On the other hand, this allows you to open these
e-mail attachments on a system which is different from the one you
created it first."""
        )
        % meta.metaDict
    ),
    p(
        _("""Mail user agents supported include:"""),
        ul(
            li(_("Mozilla Thunderbird")),
            li(_("Microsoft Outlook")),
            li(_("Claws Mail")),
            li(_("Apple Mail")),
        ),
    ),
    p(
        _(
            """Due to a Thunderbird limitation, you can't drag and drop several
e-mails from Thunderbird. This does not apply to Outlook."""
        )
    ),
    h4(a_name(_("Attaching an e-mail to a task"), "emailattach")),
    p(
        _("""There are two ways to attach an e-mail to a task; you can:"""),
        ul(
            li(
                _(
                    "Drop it on a task either in the task tree or the task list."
                )
            ),
            li(_("Drop it in the attachment pane in the task editor.")),
        ),
    ),
    h4(a_name(_("Creating a task from an e-mail"), "emailcreate")),
    p(
        _(
            """Dropping an e-mail on an empty part of the task tree or task list
creates a new task. Its subject is the subject of the mail, its
description is its content. Additionally, the mail is automatically
attached to the newly created task."""
        )
    ),
)


_templatesSection = sequence(
    h3(a_name(_("Task templates"), "templates")),
    h4(a_name(_("About templates"), "abouttemplates")),
    p(
        _(
            """Templates are blueprints for new tasks. Right now, the only task 
properties that can be "parameterized" are the dates. When instantiating a 
template, the created task has its dates replaced with dates relative to the 
current date."""
        )
    ),
    h4(a_name(_("Using templates"), "usingtemplates")),
    p(
        _(
            """One can create a template by selecting a task (only one) and click 
on the "Save task as template" item in the File menu. All subtasks, notes and 
attachments are part of the template. Only categories are not saved."""
        )
    ),
    p(
        _(
            """You can also create a new template from a pre-made template file 
(.tsktmpl); just select "Import template" in the File menu and select the file. 
Template files are stored in a subdirectory of the directory where TaskCoach.ini 
is."""
        )
    ),
    p(
        _(
            """In order to instantiate a task template, use the "New task from 
template" menu in the Task menu, or the equivalent toolbar button. When the 
task is created, the due, start and completion dates, if applicable, are 
reevaluated relatively to the current date. That means that if you create a 
template from a task starting today and due tomorrow, every time the template 
is instantiated, the planned start date will be replaced by the current date and the 
due date by the current date plus one day."""
        )
    ),
    p(
        _(
            """You can also add templates from the template editor (File/Edit
templates), as well as edit the template's basic properties (dates and
subject). Dates are provided in a human-readable format; the date editor
will become red if %(name)s cannot figure out what it means. Example
dates:"""
        )
        % meta.metaDict
    ),
    ul(li("3 pm tomorrow"), li("next saturday"), li("noon")),
    p(
        _(
            """Please note that this system is not localized; you must enter
the dates in english."""
        )
    ),
)

_guiSection = sequence(
    h3(a_name(_("Graphical user interface"), "gui")),
    p(
        _(
            """You can drag and drop viewers to create almost any user interface 
layout you want. When you start dragging a viewer, drop hints will appear to
show where you can drop the viewer. Viewers can also be dropped onto each other
to create notebooks."""
        )
    ),
    p(
        _(
            """In the edit dialogs, you can drag and drop tabs to rearrange 
the order or to create a whole different user interface layout by placing tabs 
next to eachother."""
        )
    ),
    p(
        _(
            """Subjects and descriptions of tasks, notes and categories can be
edited without opening an edit dialog. Select the item whose subject or
description you want to change and click the item again, either in the subject
column or in the description column. A text control will appear that lets you 
change the subject or description. Hit return to confirm your changes. Hit 
escape to cancel your changes. F2 is a keyboard shortcut for editing the 
subject."""
        )
    ),
)

_shortcutSection = sequence(
    h3(a_name(_("Keyboard shortcuts"), "shortcuts")),
    p(
        _(
            """%(name)s has several keyboard shortcuts, listed below. Keyboard 
shortcuts are not configurable at the moment."""
        )
        % meta.metaDict
    ),
    p(
        table(
            tr(_("Ctrl-A"), editSelectAll),
            tr(_("Shift-Ctrl-A"), addAttachment),
            tr(_("Ctrl-B"), addNote),
            tr(_("Shift-Ctrl-B"), openAllNotes),
            tr(_("Ctrl-C"), editCopy),
            tr(_("Shift-Ctrl-C"), viewCollapseAll),
            tr(_("Ctrl-D"), taskDecreasePriority),
            tr(_("Shift-Ctrl-D"), taskMinPriority),
            tr(_("Ctrl-E"), effortNew),
            tr(_("Shift-Ctrl-E"), viewExpandAll),
            tr(_("Ctrl-F"), search),
            tr(_("Ctrl-G"), categoryNew),
            tr(_("Ctrl-H"), help),
            tr(_("Ctrl-I"), taskIncreasePriority),
            tr(_("Shift-Ctrl-I"), taskMaxPriority),
            tr(_("Ctrl-J"), noteNew),
            tr(_("Ctrl-M (Linux and Windows)"), mailItem),
            tr(_("Shift-Ctrl-M (Mac OS X)"), mailItem),
            tr(_("Shift-Ctrl-M"), fileMergeDiskChanges),
            tr(_("Ctrl-N (Linux and Mac OS X)"), taskNew),
            tr(
                _("Shift-Ctrl-N (Linux and Mac OS X)"),
                _("Insert a new subitem"),
            ),
            tr(_("Ctrl-O"), fileOpen),
            tr(_("Shift-Ctrl-O"), openAllAttachments),
            tr(_("Alt-P"), editPreferences),
            tr(_("Ctrl-P"), print_),
            tr(_("Shift-Ctrl-P"), printPageSetup),
            tr(_("Ctrl-Q"), fileQuit),
            tr(_("Ctrl-R"), resetCategoryFilter),
            tr(_("Shift-Ctrl-R"), resetFilter),
            tr(_("Ctrl-S"), fileSave),
            tr(_("Shift-Ctrl-S"), fileSaveAs),
            tr(_("Ctrl-T"), effortStart),
            tr(_("Shift-Ctrl-T"), effortStopOrResume),
            tr(_("Ctrl-V"), editPaste),
            tr(_("Shift-Ctrl-V"), editPasteAsSubitem),
            tr(_("Ctrl-W"), fileClose),
            tr(_("Ctrl-X"), editCut),
            tr(_("Ctrl-Y"), editRedo),
            tr(_("Ctrl-Z"), editUndo),
            tr(_("Enter"), _("Edit the selected item(s) or close a dialog")),
            tr(_("Ctrl-Enter"), _("Mark the selected task(s) (un)completed")),
            tr(
                _("Escape"),
                _(
                    "Cancel a dialog or move keyboard focus from search control back to viewer"
                ),
            ),
            tr(
                _("Tab"),
                _("Move keyboard focus to the next field in the dialog"),
            ),
            tr(
                _("Shift-Tab"),
                _("Move keyboard focus to the previous field in the dialog"),
            ),
            tr(
                _("Ctrl-Tab"),
                _("Move keyboard focus to the next tab in a notebook control"),
            ),
            tr(
                _("Shift-Ctrl-Tab"),
                _(
                    "Move keyboard focus to the previous tab in a notebook control"
                ),
            ),
            tr(_("DELETE"), _("Delete the selected item(s)")),
            tr(_("INSERT (Windows)"), taskNew),
            tr(_("Shift-INSERT (Windows)"), _("Insert a new subitem")),
            tr(_("Ctrl-PgDn"), viewNextViewer),
            tr(_("Ctrl-PgUp"), viewPreviousViewer),
            tr(_("Alt-Down"), _("Pop up menu or drop down box")),
            tr(
                _("F2"), _("Edit the subject of the selected item in a viewer")
            ),
        )
    ),
)


helpHTML = (
    _TOC
    + _taskSection
    + _effortSection
    + _categorySection
    + _noteSection
    + _printingAndExportingSection
    + _multiuserSection
    + _emailTasksSection
    + _emailSection
    + _templatesSection
    + _guiSection
    + _shortcutSection
)


def _get_splash_path():
    """Get the path to the legacy splash screen image."""
    splash_path = os.path.join(os.path.dirname(__file__), "..", "gui", "icons", "splash.png")
    splash_path = os.path.normpath(splash_path)
    if os.path.exists(splash_path):
        return splash_path
    return None


aboutHTML = (
    _(
        """<h4>%(name)s - %(description)s</h4>
<h5>Version %(version_full)s %(release_status)s (commit %(version_commit)s), %(date)s</h5>
<p>By %(author)s &lt;%(author_email)s&gt;<p>
<p><a href="%(url)s" target="_blank">%(url)s</a></p>
<p>%(copyright)s</p>
<p>%(license_notice_html)s</p>
"""
    )
    % meta.metaDict
)

# Add legacy splash screen to About dialog
# Note: wx.html.HtmlWindow doesn't support data URIs, so we use file:// path
_splash_path = _get_splash_path()
if _splash_path:
    aboutHTML += """
<hr>
<h5>Legacy Splash Screen</h5>
<p>This splash screen was displayed on startup in earlier versions of Task Coach.</p>
<p><img src="file://%s" alt="Legacy Splash Screen" /></p>
""" % _splash_path

# Add legacy site reference
aboutHTML += """
<hr>
<p>Legacy site (no longer maintained): <a href="https://taskcoach.org" target="_blank">https://taskcoach.org</a></p>
"""
