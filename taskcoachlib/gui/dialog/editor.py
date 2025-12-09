# -*- coding: utf-8 -*-

"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2012 Nicola Chiapolini <nicola.chiapolini@physik.uzh.ch>
Copyright (C) 2008 Rob McMullen <rob.mcmullen@gmail.com>
Copyright (C) 2008 Carl Zmola <zmola@acm.org>

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

from taskcoachlib import widgets, patterns, command, operating_system, render
from taskcoachlib.domain import task, date, note, attachment
from taskcoachlib.gui import viewer, uicommand, windowdimensionstracker
from taskcoachlib.gui.dialog import entry, attributesync
from taskcoachlib.gui.newid import IdProvider
from taskcoachlib.i18n import _
from pubsub import pub
from taskcoachlib.thirdparty import smartdatetimectrl as sdtc
from taskcoachlib.help.balloontips import BalloonTipManager
import os.path
import wx


class Page(patterns.Observer, widgets.BookPage):
    columns = 2

    def __init__(self, items, *args, **kwargs):
        self.items = items
        super().__init__(columns=self.columns, *args, **kwargs)
        self.addEntries()
        self.fit()

    def selected(self):
        pass

    def addEntries(self):
        raise NotImplementedError

    def entries(self):
        """A mapping of names of columns to entries on this editor page."""
        return dict()

    def setFocusOnEntry(self, column_name):
        try:
            the_entry = self.entries()[column_name]
        except KeyError:
            the_entry = self.entries()["firstEntry"]
        self.__set_selection_and_focus(the_entry)

    def __set_selection_and_focus(self, the_entry):
        """If the entry has selectable text, select the text so that the user
        can start typing over it immediately, except on Linux because it
        overwrites the X clipboard."""
        if self.focusTextControl():
            the_entry.SetFocus()
            try:
                if operating_system.isWindows() and isinstance(
                    the_entry, wx.TextCtrl
                ):
                    # XXXFIXME: See SR #325. Disable this for now.

                    # This ensures that if the TextCtrl value is more than can
                    # be displayed, it will display the start instead of the
                    # end:
                    """from taskcoachlib.thirdparty import SendKeys  # pylint: disable=W0404
                    SendKeys.SendKeys('{END}+{HOME}')"""

                    # Scrol to left...
                    the_entry.SetInsertionPoint(0)
                the_entry.SetSelection(-1, -1)  # Select all text
            except (AttributeError, TypeError):
                pass  # Not a TextCtrl

    def focusTextControl(self):
        return True

    def close(self):
        self.removeInstance()
        for entry in list(self.entries().values()):
            if isinstance(entry, widgets.DateTimeCtrl):
                entry.Cleanup()


class SubjectPage(Page):
    pageName = "subject"
    pageTitle = _("Description")
    pageIcon = "pencil_icon"

    def __init__(self, items, parent, settings, *args, **kwargs):
        self._settings = settings
        super().__init__(items, parent, *args, **kwargs)

    def SetFocus(self):
        # Skip this on GTK because it selects the control's text, which
        # overrides the X selection. Simply commenting out the SetFocus() in
        # __load_perspective is not enough because the aui notebook calls this
        # when the user selects a tab.
        if self.focusTextControl():
            super().SetFocus()

    def focusTextControl(self):
        return self._settings.getboolean("os_linux", "focustextentry")

    def addEntries(self):
        self.addSubjectEntry()
        self.addDescriptionEntry()
        self.addCreationDateTimeEntry()
        self.addModificationDateTimeEntry()

    def addSubjectEntry(self):
        # pylint: disable=W0201
        current_subject = (
            self.items[0].subject()
            if len(self.items) == 1
            else _("Edit to change all subjects")
        )
        self._subjectEntry = widgets.SingleLineTextCtrl(self, current_subject)
        self._subjectSync = attributesync.AttributeSync(
            "subject",
            self._subjectEntry,
            current_subject,
            self.items,
            command.EditSubjectCommand,
            wx.EVT_KILL_FOCUS,
            self.items[0].subjectChangedEventType(),
        )
        self.addEntry(
            _("Subject"),
            self._subjectEntry,
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
        )

    def addDescriptionEntry(self):
        # pylint: disable=W0201
        def combined_description(items):
            return "[%s]\n\n" % _(
                "Edit to change all descriptions"
            ) + "\n\n".join(item.description() for item in items)

        current_description = (
            self.items[0].description()
            if len(self.items) == 1
            else combined_description(self.items)
        )
        self._descriptionEntry = widgets.MultiLineTextCtrl(
            self, current_description
        )
        native_info_string = self._settings.get("editor", "descriptionfont")
        font = (
            wx.FontFromNativeInfoString(native_info_string)
            if native_info_string
            else None
        )
        if font:
            self._descriptionEntry.SetFont(font)
        self._descriptionSync = attributesync.AttributeSync(
            "description",
            self._descriptionEntry,
            current_description,
            self.items,
            command.EditDescriptionCommand,
            wx.EVT_KILL_FOCUS,
            self.items[0].descriptionChangedEventType(),
        )
        self.addEntry(
            _("Description"),
            self._descriptionEntry,
            growable=True,
            flags=[wx.ALIGN_TOP | wx.ALIGN_RIGHT, wx.EXPAND],
        )

    def addCreationDateTimeEntry(self):
        creation_datetimes = [item.creationDateTime() for item in self.items]
        min_creation_datetime = min(creation_datetimes)
        max_creation_datetime = max(creation_datetimes)
        creation_text = render.dateTime(
            min_creation_datetime, humanReadable=True
        )
        if max_creation_datetime - min_creation_datetime > date.ONE_MINUTE:
            creation_text += " - %s" % render.dateTime(
                max_creation_datetime, humanReadable=True
            )
        self.addEntry(
            _("Creation date"),
            creation_text,
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
        )

    def addModificationDateTimeEntry(self):
        self._modificationTextEntry = wx.StaticText(
            self, label=self.__modification_text()
        )
        self.addEntry(
            _("Modification date"),
            self._modificationTextEntry,
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
        )
        for eventType in self.items[0].modificationEventTypes():
            if eventType.startswith("pubsub"):
                pub.subscribe(self.onAttributeChanged, eventType)
            else:
                patterns.Publisher().registerObserver(
                    self.onAttributeChanged_Deprecated,
                    eventType=eventType,
                    eventSource=self.items[0],
                )

    def __modification_text(self):
        modification_datetimes = [
            item.modificationDateTime() for item in self.items
        ]
        min_modification_datetime = min(modification_datetimes)
        max_modification_datetime = max(modification_datetimes)
        modification_text = render.dateTime(
            min_modification_datetime, humanReadable=True
        )
        if (
            max_modification_datetime - min_modification_datetime
            > date.ONE_MINUTE
        ):
            modification_text += " - %s" % render.dateTime(
                max_modification_datetime, humanReadable=True
            )
        return modification_text

    def onAttributeChanged(self, newValue, sender):
        self._modificationTextEntry.SetLabel(self.__modification_text())

    def onAttributeChanged_Deprecated(self, *args, **kwargs):
        self._modificationTextEntry.SetLabel(self.__modification_text())

    def close(self):
        super().close()
        for eventType in self.items[0].modificationEventTypes():
            try:
                pub.unsubscribe(self.onAttributeChanged, eventType)
            except pub.TopicNameError:
                pass
        patterns.Publisher().removeObserver(self.onAttributeChanged_Deprecated)

    def entries(self):
        return dict(
            firstEntry=self._subjectEntry,
            subject=self._subjectEntry,
            description=self._descriptionEntry,
            creationDateTime=self._subjectEntry,
            modificationDateTime=self._subjectEntry,
        )


class TaskSubjectPage(SubjectPage):
    def addEntries(self):
        # Override to insert a priority entry between the description and the
        # creation date/time entry
        self.addSubjectEntry()
        self.addDescriptionEntry()
        self.addPriorityEntry()
        self.addCreationDateTimeEntry()
        self.addModificationDateTimeEntry()

    def addPriorityEntry(self):
        # pylint: disable=W0201
        current_priority = (
            self.items[0].priority() if len(self.items) == 1 else 0
        )
        self._priorityEntry = widgets.SpinCtrl(
            self, size=(100, -1), value=current_priority
        )
        self._prioritySync = attributesync.AttributeSync(
            "priority",
            self._priorityEntry,
            current_priority,
            self.items,
            command.EditPriorityCommand,
            wx.EVT_SPINCTRL,
            self.items[0].priorityChangedEventType(),
        )
        self.addEntry(
            _("Priority"),
            self._priorityEntry,
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
        )

    def entries(self):
        entries = super().entries()
        entries["priority"] = self._priorityEntry
        return entries


class CategorySubjectPage(SubjectPage):
    def addEntries(self):
        # Override to insert an exclusive subcategories entry
        # between the description and the creation date/time entry
        self.addSubjectEntry()
        self.addDescriptionEntry()
        self.addExclusiveSubcategoriesEntry()
        self.addCreationDateTimeEntry()
        self.addModificationDateTimeEntry()

    def addExclusiveSubcategoriesEntry(self):
        # pylint: disable=W0201
        currentExclusivity = (
            self.items[0].hasExclusiveSubcategories()
            if len(self.items) == 1
            else False
        )
        self._exclusiveSubcategoriesCheckBox = wx.CheckBox(
            self, label=_("Mutually exclusive")
        )
        self._exclusiveSubcategoriesCheckBox.SetValue(currentExclusivity)
        self._exclusiveSubcategoriesSync = attributesync.AttributeSync(
            "hasExclusiveSubcategories",
            self._exclusiveSubcategoriesCheckBox,
            currentExclusivity,
            self.items,
            command.EditExclusiveSubcategoriesCommand,
            wx.EVT_CHECKBOX,
            self.items[0].exclusiveSubcategoriesChangedEventType(),
        )
        self.addEntry(
            _("Subcategories"),
            self._exclusiveSubcategoriesCheckBox,
            flags=[None, wx.ALL],
        )


class AttachmentSubjectPage(SubjectPage):
    def addEntries(self):
        # Override to insert a location entry between the subject and
        # description entry
        self.addSubjectEntry()
        self.addLocationEntry()
        self.addDescriptionEntry()
        self.addCreationDateTimeEntry()
        self.addModificationDateTimeEntry()

    def addLocationEntry(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        # pylint: disable=W0201
        current_location = (
            self.items[0].location()
            if len(self.items) == 1
            else _("Edit to change location of all attachments")
        )
        self._locationEntry = widgets.SingleLineTextCtrl(
            panel, current_location
        )
        self._locationSync = attributesync.AttributeSync(
            "location",
            self._locationEntry,
            current_location,
            self.items,
            command.EditAttachmentLocationCommand,
            wx.EVT_KILL_FOCUS,
            self.items[0].locationChangedEventType(),
        )
        sizer.Add(self._locationEntry, 1, wx.ALL, 3)
        if all(item.type_ == "file" for item in self.items):
            button = wx.Button(panel, wx.ID_ANY, _("Browse"))
            sizer.Add(button, 0, wx.ALL, 3)
            button.Bind(wx.EVT_BUTTON, self.onSelectLocation)
        panel.SetSizer(sizer)
        self.addEntry(_("Location"), panel, flags=[None, wx.ALL | wx.EXPAND])

    def onSelectLocation(self, event):  # pylint: disable=W0613
        base_path = self._settings.get("file", "lastattachmentpath")
        if not base_path:
            base_path = os.getcwd()
        filename = widgets.AttachmentSelector(default_path=base_path)

        if filename:
            self._settings.set(
                "file",
                "lastattachmentpath",
                os.path.abspath(os.path.split(filename)[0]),
            )
            if self._settings.get("file", "attachmentbase"):
                filename = attachment.getRelativePath(
                    filename, self._settings.get("file", "attachmentbase")
                )
            self._subjectEntry.SetValue(os.path.split(filename)[-1])
            self._locationEntry.SetValue(filename)
            self._subjectSync.onAttributeEdited(event)
            self._locationSync.onAttributeEdited(event)


class TaskAppearancePage(Page):
    pageName = "appearance"
    pageTitle = _("Appearance")
    pageIcon = "palette_icon"
    columns = 5

    def addEntries(self):
        self.addColorEntries()
        self.addFontEntry()
        self.addIconEntry()

    def addColorEntries(self):
        self.addColorEntry(_("Foreground color"), "foreground", wx.BLACK)
        self.addColorEntry(_("Background color"), "background", wx.WHITE)

    def addColorEntry(self, labelText, colorType, defaultColor):
        currentColor = (
            getattr(self.items[0], "%sColor" % colorType)(recursive=False)
            if len(self.items) == 1
            else None
        )
        colorEntry = entry.ColorEntry(self, currentColor, defaultColor)
        setattr(self, "_%sColorEntry" % colorType, colorEntry)
        commandClass = getattr(
            command, "Edit%sColorCommand" % colorType.capitalize()
        )
        colorSync = attributesync.AttributeSync(
            "%sColor" % colorType,
            colorEntry,
            currentColor,
            self.items,
            commandClass,
            entry.EVT_COLORENTRY,
            self.items[0].appearanceChangedEventType(),
        )
        setattr(self, "_%sColorSync" % colorType, colorSync)
        self.addEntry(labelText, colorEntry, flags=[wx.ALIGN_RIGHT, wx.ALL])

    def addFontEntry(self):
        # pylint: disable=W0201,E1101
        currentFont = self.items[0].font() if len(self.items) == 1 else None
        currentColor = self._foregroundColorEntry.GetValue()
        self._fontEntry = entry.FontEntry(self, currentFont, currentColor)
        self._fontSync = attributesync.AttributeSync(
            "font",
            self._fontEntry,
            currentFont,
            self.items,
            command.EditFontCommand,
            entry.EVT_FONTENTRY,
            self.items[0].appearanceChangedEventType(),
        )
        self._fontColorSync = attributesync.FontColorSync(
            "foregroundColor",
            self._fontEntry,
            currentColor,
            self.items,
            command.EditForegroundColorCommand,
            entry.EVT_FONTENTRY,
            self.items[0].appearanceChangedEventType(),
        )
        self.addEntry(
            _("Font"), self._fontEntry, flags=[wx.ALIGN_RIGHT, wx.ALL]
        )

    def addIconEntry(self):
        # pylint: disable=W0201,E1101
        currentIcon = self.items[0].icon() if len(self.items) == 1 else ""
        self._iconEntry = entry.IconEntry(self, currentIcon)
        self._iconSync = attributesync.AttributeSync(
            "icon",
            self._iconEntry,
            currentIcon,
            self.items,
            command.EditIconCommand,
            entry.EVT_ICONENTRY,
            self.items[0].appearanceChangedEventType(),
        )
        self.addEntry(
            _("Icon"), self._iconEntry, flags=[wx.ALIGN_RIGHT, wx.ALL]
        )

    def entries(self):
        return dict(
            firstEntry=self._foregroundColorEntry
        )  # pylint: disable=E1101


class DatesPage(Page):
    pageName = "dates"
    pageTitle = _("Dates")
    pageIcon = "calendar_icon"

    def __init__(
        self, theTask, parent, settings, items_are_new, *args, **kwargs
    ):
        self.__settings = settings
        self._duration = None
        self.__items_are_new = items_are_new
        super().__init__(theTask, parent, *args, **kwargs)
        pub.subscribe(
            self.__onChoicesConfigChanged, "settings.feature.sdtcspans"
        )

    def __onChoicesConfigChanged(self, value=""):
        self._dueDateTimeEntry.LoadChoices(value)

    def __onTimeChoicesChange(self, event):
        self.__settings.settext("feature", "sdtcspans", event.GetValue())

    def __onPlannedStartDateTimeChanged(self, value):
        self._dueDateTimeEntry.SetRelativeChoicesStart(
            None if value == date.DateTime() else value
        )

    def addEntries(self):
        self.addDateEntries()
        self.addLine()
        self.addReminderEntry()
        self.addLine()
        self.addRecurrenceEntry()

    def addDateEntries(self):
        self.addDateEntry(_("Planned start date"), "plannedStartDateTime")
        self.addDateEntry(_("Due date"), "dueDateTime")
        self.addLine()
        self.addDateEntry(_("Actual start date"), "actualStartDateTime")
        self.addDateEntry(_("Completion date"), "completionDateTime")

        start = self._plannedStartDateTimeEntry.GetValue()
        self._dueDateTimeEntry.SetRelativeChoicesStart(
            start=None if start == date.DateTime() else start
        )
        self._dueDateTimeEntry.LoadChoices(
            self.__settings.get("feature", "sdtcspans")
        )

        self._dueDateTimeEntry.Bind(
            sdtc.EVT_TIME_CHOICES_CHANGE, self.__onTimeChoicesChange
        )

    def addDateEntry(self, label, taskMethodName):
        TaskMethodName = taskMethodName[0].capitalize() + taskMethodName[1:]
        dateTime = (
            getattr(self.items[0], taskMethodName)()
            if len(self.items) == 1
            else date.DateTime()
        )
        setattr(self, "_current%s" % TaskMethodName, dateTime)
        suggestedDateTimeMethodName = "suggested" + TaskMethodName
        suggestedDateTime = getattr(
            self.items[0], suggestedDateTimeMethodName
        )()
        dateTimeEntry = entry.DateTimeEntry(
            self,
            self.__settings,
            dateTime,
            suggestedDateTime=suggestedDateTime,
            showRelative=taskMethodName == "dueDateTime",
            adjustEndOfDay=taskMethodName == "dueDateTime",
        )
        setattr(self, "_%sEntry" % taskMethodName, dateTimeEntry)
        commandClass = getattr(command, "Edit%sCommand" % TaskMethodName)
        eventType = getattr(
            self.items[0], "%sChangedEventType" % taskMethodName
        )()
        keep_delta = self.__keep_delta(taskMethodName)
        datetimeSync = attributesync.AttributeSync(
            taskMethodName,
            dateTimeEntry,
            dateTime,
            self.items,
            commandClass,
            entry.EVT_DATETIMEENTRY,
            eventType,
            commit_on_focus_loss=True,  # Only commit when focus leaves the field
            keep_delta=keep_delta,
            callback=(
                self.__onPlannedStartDateTimeChanged
                if taskMethodName == "plannedStartDateTime"
                else None
            ),
        )
        setattr(self, "_%sSync" % taskMethodName, datetimeSync)
        self.addEntry(label, dateTimeEntry, flags=[wx.ALIGN_RIGHT, wx.EXPAND])

    def __keep_delta(self, taskMethodName):
        datesTied = self.__settings.get("view", "datestied")
        return (
            datesTied == "startdue"
            and taskMethodName == "plannedStartDateTime"
        ) or (datesTied == "duestart" and taskMethodName == "dueDateTime")

    def addReminderEntry(self):
        # pylint: disable=W0201
        reminderDateTime = (
            self.items[0].reminder()
            if len(self.items) == 1
            else date.DateTime()
        )
        suggestedDateTime = self.items[0].suggestedReminderDateTime()
        self._reminderDateTimeEntry = entry.DateTimeEntry(
            self,
            self.__settings,
            reminderDateTime,
            suggestedDateTime=suggestedDateTime,
        )
        self._reminderDateTimeSync = attributesync.AttributeSync(
            "reminder",
            self._reminderDateTimeEntry,
            reminderDateTime,
            self.items,
            command.EditReminderDateTimeCommand,
            entry.EVT_DATETIMEENTRY,
            self.items[0].reminderChangedEventType(),
            commit_on_focus_loss=True,  # Only commit when focus leaves the field
        )
        self.addEntry(
            _("Reminder"),
            self._reminderDateTimeEntry,
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
        )

    def addRecurrenceEntry(self):
        # pylint: disable=W0201
        currentRecurrence = (
            self.items[0].recurrence()
            if len(self.items) == 1
            else date.Recurrence()
        )
        self._recurrenceEntry = entry.RecurrenceEntry(
            self, currentRecurrence, self.__settings
        )
        self._recurrenceSync = attributesync.AttributeSync(
            "recurrence",
            self._recurrenceEntry,
            currentRecurrence,
            self.items,
            command.EditRecurrenceCommand,
            entry.EVT_RECURRENCEENTRY,
            self.items[0].recurrenceChangedEventType(),
        )
        self.addEntry(
            _("Recurrence"),
            self._recurrenceEntry,
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
        )

    def entries(self):
        # pylint: disable=E1101
        return dict(
            firstEntry=self._plannedStartDateTimeEntry,
            plannedStartDateTime=self._plannedStartDateTimeEntry,
            dueDateTime=self._dueDateTimeEntry,
            actualStartDateTime=self._actualStartDateTimeEntry,
            completionDateTime=self._completionDateTimeEntry,
            timeLeft=self._dueDateTimeEntry,
            reminder=self._reminderDateTimeEntry,
            recurrence=self._recurrenceEntry,
        )


class ProgressPage(Page):
    pageName = "progress"
    pageTitle = _("Progress")
    pageIcon = "progress"

    def addEntries(self):
        self.addProgressEntry()
        self.addBehaviorEntry()

    def addProgressEntry(self):
        # pylint: disable=W0201
        currentPercentageComplete = (
            self.items[0].percentageComplete()
            if len(self.items) == 1
            else self.averagePercentageComplete(self.items)
        )
        self._percentageCompleteEntry = entry.PercentageEntry(
            self, currentPercentageComplete
        )
        self._percentageCompleteSync = attributesync.AttributeSync(
            "percentageComplete",
            self._percentageCompleteEntry,
            currentPercentageComplete,
            self.items,
            command.EditPercentageCompleteCommand,
            entry.EVT_PERCENTAGEENTRY,
            self.items[0].percentageCompleteChangedEventType(),
        )
        self.addEntry(
            _("Percentage complete"),
            self._percentageCompleteEntry,
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
        )

    @staticmethod
    def averagePercentageComplete(items):
        return (
            sum([item.percentageComplete() for item in items])
            // float(len(items))
            if items
            else 0
        )

    def addBehaviorEntry(self):
        # pylint: disable=W0201
        choices = [
            (None, _("Use application-wide setting")),
            (False, _("No")),
            (True, _("Yes")),
        ]
        currentChoice = (
            self.items[0].shouldMarkCompletedWhenAllChildrenCompleted()
            if len(self.items) == 1
            else None
        )
        self._shouldMarkCompletedEntry = entry.ChoiceEntry(
            self, choices, currentChoice
        )
        self._shouldMarkCompletedSync = attributesync.AttributeSync(
            "shouldMarkCompletedWhenAllChildrenCompleted",
            self._shouldMarkCompletedEntry,
            currentChoice,
            self.items,
            command.EditShouldMarkCompletedCommand,
            entry.EVT_CHOICEENTRY,
            task.Task.shouldMarkCompletedWhenAllChildrenCompletedChangedEventType(),
        )
        self.addEntry(
            _("Mark task completed when all children are completed?"),
            self._shouldMarkCompletedEntry,
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
        )

    def entries(self):
        return dict(
            firstEntry=self._percentageCompleteEntry,
            percentageComplete=self._percentageCompleteEntry,
        )


class BudgetPage(Page):
    pageName = "budget"
    pageTitle = _("Budget")
    pageIcon = "calculator_icon"

    def NavigateBook(self, forward):
        self.GetParent().NavigateBook(forward)

    def addEntries(self):
        self.addBudgetEntries()
        self.addLine()
        self.addRevenueEntries()
        self.observeTracking()

    def addBudgetEntries(self):
        self.addBudgetEntry()
        if len(self.items) == 1:
            self.addTimeSpentEntry()
            self.addBudgetLeftEntry()

    def addBudgetEntry(self):
        # pylint: disable=W0201,W0212
        currentBudget = (
            self.items[0].budget()
            if len(self.items) == 1
            else date.TimeDelta()
        )
        self._budgetEntry = entry.TimeDeltaEntry(self, currentBudget)
        self._budgetSync = attributesync.AttributeSync(
            "budget",
            self._budgetEntry,
            currentBudget,
            self.items,
            command.EditBudgetCommand,
            wx.EVT_KILL_FOCUS,
            self.items[0].budgetChangedEventType(),
        )
        self.addEntry(
            _("Budget"), self._budgetEntry, flags=[wx.ALIGN_RIGHT, wx.ALL]
        )

    def addTimeSpentEntry(self):
        assert len(self.items) == 1
        # pylint: disable=W0201
        self._timeSpentEntry = entry.TimeDeltaEntry(
            self, self.items[0].timeSpent(), readonly=True
        )
        self.addEntry(
            _("Time spent"),
            self._timeSpentEntry,
            flags=[wx.ALIGN_RIGHT, wx.ALL],
        )
        pub.subscribe(
            self.onTimeSpentChanged, self.items[0].timeSpentChangedEventType()
        )

    def onTimeSpentChanged(self, newValue, sender):
        if sender == self.items[0]:
            time_spent = sender.timeSpent()
            if time_spent != self._timeSpentEntry.GetValue():
                self._timeSpentEntry.SetValue(time_spent)

    def addBudgetLeftEntry(self):
        assert len(self.items) == 1
        # pylint: disable=W0201
        self._budgetLeftEntry = entry.TimeDeltaEntry(
            self, self.items[0].budgetLeft(), readonly=True
        )
        self.addEntry(
            _("Budget left"),
            self._budgetLeftEntry,
            flags=[wx.ALIGN_RIGHT, wx.ALL],
        )
        pub.subscribe(
            self.onBudgetLeftChanged,
            self.items[0].budgetLeftChangedEventType(),
        )

    def onBudgetLeftChanged(self, newValue, sender):  # pylint: disable=W0613
        if sender == self.items[0]:
            budget_left = sender.budgetLeft()
            if budget_left != self._budgetLeftEntry.GetValue():
                self._budgetLeftEntry.SetValue(budget_left)

    def addRevenueEntries(self):
        self.addHourlyFeeEntry()
        self.addFixedFeeEntry()
        if len(self.items) == 1:
            self.addRevenueEntry()

    def addHourlyFeeEntry(self):
        # pylint: disable=W0201,W0212
        currentHourlyFee = (
            self.items[0].hourlyFee() if len(self.items) == 1 else 0
        )
        self._hourlyFeeEntry = entry.AmountEntry(self, currentHourlyFee)
        self._hourlyFeeSync = attributesync.AttributeSync(
            "hourlyFee",
            self._hourlyFeeEntry,
            currentHourlyFee,
            self.items,
            command.EditHourlyFeeCommand,
            wx.EVT_KILL_FOCUS,
            self.items[0].hourlyFeeChangedEventType(),
        )
        self.addEntry(
            _("Hourly fee"),
            self._hourlyFeeEntry,
            flags=[wx.ALIGN_RIGHT, wx.ALL],
        )

    def addFixedFeeEntry(self):
        # pylint: disable=W0201,W0212
        currentFixedFee = (
            self.items[0].fixedFee() if len(self.items) == 1 else 0
        )
        self._fixedFeeEntry = entry.AmountEntry(self, currentFixedFee)
        self._fixedFeeSync = attributesync.AttributeSync(
            "fixedFee",
            self._fixedFeeEntry,
            currentFixedFee,
            self.items,
            command.EditFixedFeeCommand,
            wx.EVT_KILL_FOCUS,
            self.items[0].fixedFeeChangedEventType(),
        )
        self.addEntry(
            _("Fixed fee"), self._fixedFeeEntry, flags=[wx.ALIGN_RIGHT, wx.ALL]
        )

    def addRevenueEntry(self):
        assert len(self.items) == 1
        revenue = self.items[0].revenue()
        self._revenueEntry = entry.AmountEntry(
            self, revenue, readonly=True
        )  # pylint: disable=W0201
        self.addEntry(
            _("Revenue"), self._revenueEntry, flags=[wx.ALIGN_RIGHT, wx.ALL]
        )
        pub.subscribe(
            self.onRevenueChanged, self.items[0].revenueChangedEventType()
        )

    def onRevenueChanged(self, newValue, sender):
        if sender == self.items[0]:
            if newValue != self._revenueEntry.GetValue():
                self._revenueEntry.SetValue(newValue)

    def observeTracking(self):
        if len(self.items) != 1:
            return
        item = self.items[0]
        pub.subscribe(self.onTrackingChanged, item.trackingChangedEventType())
        if item.isBeingTracked():
            self.onTrackingChanged(True, item)

    def onTrackingChanged(self, newValue, sender):
        if newValue:
            if sender in self.items:
                date.Scheduler().schedule_interval(
                    self.onEverySecond, seconds=1
                )
        else:
            # We might need to keep tracking the clock if the user was tracking this
            # task with multiple effort records simultaneously
            if not self.items[0].isBeingTracked():
                date.Scheduler().unschedule(self.onEverySecond)

    def onEverySecond(self):
        taskDisplayed = self.items[0]
        self.onTimeSpentChanged(taskDisplayed.timeSpent(), taskDisplayed)
        self.onBudgetLeftChanged(taskDisplayed.budgetLeft(), taskDisplayed)
        self.onRevenueChanged(taskDisplayed.revenue(), taskDisplayed)

    def close(self):
        date.Scheduler().unschedule(self.onEverySecond)
        super().close()

    def entries(self):
        return dict(
            firstEntry=self._budgetEntry,
            budget=self._budgetEntry,
            budgetLeft=self._budgetEntry,
            hourlyFee=self._hourlyFeeEntry,
            fixedFee=self._fixedFeeEntry,
            revenue=self._hourlyFeeEntry,
        )


class PageWithViewer(Page):
    columns = 1

    def __init__(
        self,
        items,
        parent,
        taskFile,
        settings,
        settingsSection,
        *args,
        **kwargs
    ):
        self.__taskFile = taskFile
        self.__settings = settings
        self.__settingsSection = settingsSection
        super().__init__(items, parent, *args, **kwargs)

    def addEntries(self):
        # pylint: disable=W0201
        self.viewer = self.createViewer(
            self.__taskFile, self.__settings, self.__settingsSection
        )
        self.addEntry(self.viewer, growable=True, flags=[wx.EXPAND])

    def createViewer(self, taskFile, settings, settingsSection):
        raise NotImplementedError

    def close(self):
        # Clean up the viewer immediately now that the SearchCtrl timer
        # cleanup is properly implemented (see PYTHON3_MIGRATION_NOTES.md)
        if hasattr(self, "viewer"):
            self.viewer.detach()
            del self.viewer
        super().close()


class EffortPage(PageWithViewer):
    pageName = "effort"
    pageTitle = _("Effort")
    pageIcon = "clock_icon"

    def createViewer(self, taskFile, settings, settingsSection):
        return viewer.EffortViewer(
            self,
            taskFile,
            settings,
            settingsSection=settingsSection,
            use_separate_settings_section=False,
            tasksToShowEffortFor=task.TaskList(self.items),
        )

    def entries(self):
        if hasattr(self, "viewer"):
            return dict(firstEntry=self.viewer, timeSpent=self.viewer)
        return dict()


class LocalCategoryViewer(viewer.BaseCategoryViewer):  # pylint: disable=W0223
    def __init__(self, items, *args, **kwargs):
        self.__items = items
        super().__init__(*args, **kwargs)
        for item in self.domainObjectsToView():
            item.expand(context=self.settingsSection(), notify=False)

    def getIsItemChecked(self, category):  # pylint: disable=W0621
        for item in self.__items:
            if category in item.categories():
                return True
        return False

    def onCheck(self, event, final):
        """Here we keep track of the items checked by the user so that these
        items remain checked when refreshing the viewer."""
        if final:
            category = self.widget.GetItemPyData(event.GetItem())
            command.ToggleCategoryCommand(
                None, self.__items, category=category
            ).do()

    def createCategoryPopupMenu(self):  # pylint: disable=W0221
        return super().createCategoryPopupMenu(True)


class CategoriesPage(PageWithViewer):
    pageName = "categories"
    pageTitle = _("Categories")
    pageIcon = "folder_blue_arrow_icon"

    def __init__(self, *args, **kwargs):
        self.__realized = False
        super().__init__(*args, **kwargs)

    def addEntries(self):
        pass

    def selected(self):
        if not self.__realized:
            self.__realized = True
            super().addEntries()
            self.fit()

    def createViewer(self, taskFile, settings, settingsSection):
        assert len(self.items) == 1
        item = self.items[0]
        for eventType in (
            item.categoryAddedEventType(),
            item.categoryRemovedEventType(),
        ):
            self.registerObserver(
                self.onCategoryChanged, eventType=eventType, eventSource=item
            )
        return LocalCategoryViewer(
            self.items,
            self,
            taskFile,
            settings,
            settingsSection=settingsSection,
            use_separate_settings_section=False,
        )

    def onCategoryChanged(self, event):
        self.viewer.refreshItems(*list(event.values()))

    def entries(self):
        # Always include "categories" key so setFocus() can find this page
        # before it's realized. The actual viewer is used if available.
        if self.__realized and hasattr(self, "viewer"):
            return dict(firstEntry=self.viewer, categories=self.viewer)
        return dict(firstEntry=self, categories=self)


class LocalAttachmentViewer(viewer.AttachmentViewer):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        self.attachmentOwner = kwargs.pop("owner")
        attachments = attachment.AttachmentList(
            self.attachmentOwner.attachments()
        )
        super().__init__(attachmentsToShow=attachments, *args, **kwargs)

    def newItemCommand(self, *args, **kwargs):
        return command.AddAttachmentCommand(
            None, [self.attachmentOwner], *args, **kwargs
        )

    def deleteItemCommand(self):
        return command.RemoveAttachmentCommand(
            None, [self.attachmentOwner], attachments=self.curselection()
        )

    def cutItemCommand(self):
        return command.CutAttachmentCommand(
            None, [self.attachmentOwner], attachments=self.curselection()
        )


class AttachmentsPage(PageWithViewer):
    pageName = "attachments"
    pageTitle = _("Attachments")
    pageIcon = "paperclip_icon"

    def createViewer(self, taskFile, settings, settingsSection):
        assert len(self.items) == 1
        item = self.items[0]
        self.registerObserver(
            self.onAttachmentsChanged,
            eventType=item.attachmentsChangedEventType(),
            eventSource=item,
        )
        return LocalAttachmentViewer(
            self,
            taskFile,
            settings,
            settingsSection=settingsSection,
            use_separate_settings_section=False,
            owner=item,
        )

    def onAttachmentsChanged(self, event):  # pylint: disable=W0613
        self.viewer.domainObjectsToView().clear()
        self.viewer.domainObjectsToView().extend(self.items[0].attachments())

    def entries(self):
        if hasattr(self, "viewer"):
            return dict(firstEntry=self.viewer, attachments=self.viewer)
        return dict()


class LocalNoteViewer(viewer.BaseNoteViewer):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        self.__note_owner = kwargs.pop("owner")
        notes = note.NoteContainer(self.__note_owner.notes())
        super().__init__(notesToShow=notes, *args, **kwargs)

    def newItemCommand(self, *args, **kwargs):
        return command.AddNoteCommand(None, [self.__note_owner])

    def newSubItemCommand(self):
        return command.AddSubNoteCommand(
            None, self.curselection(), owner=self.__note_owner
        )

    def deleteItemCommand(self):
        return command.RemoveNoteCommand(
            None, [self.__note_owner], notes=self.curselection()
        )


class NotesPage(PageWithViewer):
    pageName = "notes"
    pageTitle = _("Notes")
    pageIcon = "note_icon"

    def createViewer(self, taskFile, settings, settingsSection):
        assert len(self.items) == 1
        item = self.items[0]
        self.registerObserver(
            self.onNotesChanged,
            eventType=item.notesChangedEventType(),
            eventSource=item,
        )
        return LocalNoteViewer(
            self,
            taskFile,
            settings,
            settingsSection=settingsSection,
            use_separate_settings_section=False,
            owner=item,
        )

    def onNotesChanged(self, event):  # pylint: disable=W0613
        self.viewer.domainObjectsToView().clear()
        self.viewer.domainObjectsToView().extend(self.items[0].notes())

    def entries(self):
        if hasattr(self, "viewer"):
            return dict(firstEntry=self.viewer, notes=self.viewer)
        return dict()


class LocalPrerequisiteViewer(
    viewer.CheckableTaskViewer
):  # pylint: disable=W0223
    def __init__(self, items, *args, **kwargs):
        self.__items = items
        super().__init__(*args, **kwargs)

    def getIsItemChecked(self, item):
        return item in self.__items[0].prerequisites()

    def getIsItemCheckable(self, item):
        return item not in self.__items

    def onCheck(self, event, final):
        item = self.widget.GetItemPyData(event.GetItem())
        is_checked = event.GetItem().IsChecked()
        if is_checked != self.getIsItemChecked(item):
            checked, unchecked = ([item], []) if is_checked else ([], [item])
            command.TogglePrerequisiteCommand(
                None,
                self.__items,
                checkedPrerequisites=checked,
                uncheckedPrerequisites=unchecked,
            ).do()


class PrerequisitesPage(PageWithViewer):
    pageName = "prerequisites"
    pageTitle = _("Prerequisites")
    pageIcon = "trafficlight_icon"

    def __init__(self, *args, **kwargs):
        self.__realized = False
        super().__init__(*args, **kwargs)

    def addEntries(self):
        pass

    def selected(self):
        if not self.__realized:
            self.__realized = True
            super().addEntries()
            self.fit()

    def createViewer(self, taskFile, settings, settingsSection):
        assert len(self.items) == 1
        pub.subscribe(
            self.onPrerequisitesChanged,
            self.items[0].prerequisitesChangedEventType(),
        )
        return LocalPrerequisiteViewer(
            self.items,
            self,
            taskFile,
            settings,
            settingsSection=settingsSection,
            use_separate_settings_section=False,
        )

    def onPrerequisitesChanged(self, newValue, sender):
        if sender == self.items[0]:
            self.viewer.refreshItems(*newValue)

    def entries(self):
        if self.__realized and hasattr(self, "viewer"):
            return dict(
                firstEntry=self.viewer,
                prerequisites=self.viewer,
                dependencies=self.viewer,
            )
        return dict()


class EditBook(widgets.Notebook):
    allPageNames = ["subclass responsibility"]
    domainObject = "subclass responsibility"

    def __init__(self, parent, items, taskFile, settings, items_are_new):
        self.items = items
        self.settings = settings
        super().__init__(parent)
        self.addPages(taskFile, items_are_new)
        self.__load_perspective(items_are_new)

    def NavigateBook(self, forward):
        curSel = self.GetSelection()
        curSel = curSel + 1 if forward else curSel - 1
        if curSel >= 0 and curSel < self.GetPageCount():
            self.SetSelection(curSel)

    def addPages(self, task_file, items_are_new):
        page_names = self.settings.getlist(self.settings_section(), "pages")
        for page_name in page_names:
            page = self.createPage(page_name, task_file, items_are_new)
            self.AddPage(page, page.pageTitle, page.pageIcon)
        # DISABLED: SetMinSize was locking entire notebook to max page size
        # width, height = self.__get_minimum_page_size()
        # self.SetMinSize((width, self.GetHeightForPageHeight(height)))

    def onPageChanged(self, event):
        self.GetPage(event.Selection).selected()
        event.Skip()
        if operating_system.isMac():
            # The dialog loses focus sometimes...
            wx.GetTopLevelParent(self).Raise()

    def getPage(self, page_name):
        index = self.getPageIndex(page_name)
        if index is not None:
            return self[index]
        return None

    def getPageIndex(self, page_name):
        for index in range(self.GetPageCount()):
            if page_name == self[index].pageName:
                return index
        return None

    def __get_minimum_page_size(self):
        min_widths, min_heights = [], []
        for page in self:
            min_width, min_height = page.GetMinSize()
            min_widths.append(min_width)
            min_heights.append(min_height)
        return max(min_widths), max(min_heights)

    def __pages_to_create(self):
        return [
            page_name
            for page_name in self.allPageNames
            if self.__should_create_page(page_name)
        ]

    def __should_create_page(self, page_name):
        return (
            self.__page_supports_mass_editing(page_name)
            if len(self.items) > 1
            else True
        )

    @staticmethod
    def __page_supports_mass_editing(page_name):
        """Return whether the_module page supports editing multiple items
        at once."""
        return page_name in (
            "subject",
            "dates",
            "progress",
            "budget",
            "appearance",
        )

    def createPage(self, page_name, task_file, items_are_new):
        if page_name == "subject":
            return self.create_subject_page()
        elif page_name == "dates":
            return DatesPage(self.items, self, self.settings, items_are_new)
        elif page_name == "prerequisites":
            return PrerequisitesPage(
                self.items,
                self,
                task_file,
                self.settings,
                settingsSection="prerequisiteviewerin%seditor"
                % self.domainObject,
            )
        elif page_name == "progress":
            return ProgressPage(self.items, self)
        elif page_name == "categories":
            return CategoriesPage(
                self.items,
                self,
                task_file,
                self.settings,
                settingsSection="categoryviewerin%seditor" % self.domainObject,
            )
        elif page_name == "budget":
            return BudgetPage(self.items, self)
        elif page_name == "effort":
            return EffortPage(
                self.items,
                self,
                task_file,
                self.settings,
                settingsSection="effortviewerin%seditor" % self.domainObject,
            )
        elif page_name == "notes":
            return NotesPage(
                self.items,
                self,
                task_file,
                self.settings,
                settingsSection="noteviewerin%seditor" % self.domainObject,
            )
        elif page_name == "attachments":
            return AttachmentsPage(
                self.items,
                self,
                task_file,
                self.settings,
                settingsSection="attachmentviewerin%seditor"
                % self.domainObject,
            )
        elif page_name == "appearance":
            return TaskAppearancePage(self.items, self)

    def create_subject_page(self):
        return SubjectPage(self.items, self, self.settings)

    def setFocus(self, columnName):
        """Select the correct page of the editor and correct control on a page
        based on the column that the user double clicked."""
        page = 0
        for page_index in range(self.GetPageCount()):
            if columnName in self[page_index].entries():
                page = page_index
                break
        self.SetSelection(page)
        self[page].setFocusOnEntry(columnName)

    def isDisplayingItemOrChildOfItem(self, targetItem):
        ancestors = []
        for item in self.items:
            ancestors.extend(item.ancestors())
        return targetItem in self.items + ancestors

    def perspective(self):
        """Return the perspective for the notebook."""
        return self.settings.gettext(self.settings_section(), "perspective")

    def __load_perspective(self, items_are_new=False):
        """Load the perspective (layout) for the current combination of visible
        pages from the settings."""
        perspective = self.perspective()
        if perspective:
            try:
                # DISABLED: LoadPerspective was restoring stale AuiNotebook perspective with broken sizing
                # self.LoadPerspective(perspective)
                pass
            except Exception:
                pass  # Perspective loading may fail
        if items_are_new:
            current_page = (
                self.getPageIndex("subject") or 0
            )  # For new items, start at the subject page.
        else:
            # Although the active/current page is written in the perspective
            # string (a + before the number of the active page), the current
            # page is not set when restoring the perspective. This does it by
            # hand:
            try:
                current_page = int(
                    perspective.split("@")[0].split("+")[1].split(",")[0]
                )
            except (IndexError, ValueError):
                current_page = 0
        self.SetSelection(current_page)
        self.GetPage(current_page).SetFocus()

        for idx in range(self.GetPageCount()):
            page = self.GetPage(idx)
            if page.IsShown():
                page.selected()

    def __save_perspective(self):
        """Save the current perspective of the editor in the settings.
        Multiple perspectives are supported, for each set of visible pages.
        This allows different perspectives for e.g. single item editors and
        multi-item editors."""
        page_names = [
            self[index].pageName for index in range(self.GetPageCount())
        ]
        section = self.settings_section()
        self.settings.settext(section, "perspective", self.SavePerspective())
        self.settings.setlist(section, "pages", page_names)

    def settings_section(self):
        """Create the settings section for this dialog if necessary and
        return it."""
        section = self.__settings_section_name()
        if not self.settings.has_section(section):
            self.__create_settings_section(section)
        else:
            # Ensure parent_offset exists for backward compatibility with old sections
            if not self.settings.has_option(section, "parent_offset"):
                self.settings.init(section, "parent_offset", "(-1, -1)")
        return section

    def __settings_section_name(self):
        """Return the section name of this notebook. The name of the section
        depends on the visible pages so that different variants of the
        notebook store their settings in different sections."""
        page_names = self.__pages_to_create()
        sorted_page_names = "_".join(sorted(page_names))
        return "%sdialog_with_%s" % (self.domainObject, sorted_page_names)

    def __create_settings_section(self, section):
        """Create the section and initialize the options in the section."""
        self.settings.add_section(section)
        for option, value in list(
            dict(
                perspective="",
                pages=str(self.__pages_to_create()),
                size="(-1, -1)",
                position="(-1, -1)",
                parent_offset="(-1, -1)",  # Offset from parent window for multi-monitor support
                maximized="False",
            ).items()
        ):
            self.settings.init(section, option, value)

    def close_edit_book(self):
        """Close all pages in the edit book and save the current layout in
        the settings."""
        for page in self:
            page.close()
        self.__save_perspective()


class TaskEditBook(EditBook):
    allPageNames = [
        "subject",
        "dates",
        "prerequisites",
        "progress",
        "categories",
        "budget",
        "effort",
        "notes",
        "attachments",
        "appearance",
    ]
    domainObject = "task"

    def create_subject_page(self):
        return TaskSubjectPage(self.items, self, self.settings)


class CategoryEditBook(EditBook):
    allPageNames = ["subject", "notes", "attachments", "appearance"]
    domainObject = "category"

    def create_subject_page(self):
        return CategorySubjectPage(self.items, self, self.settings)


class NoteEditBook(EditBook):
    allPageNames = ["subject", "categories", "attachments", "appearance"]
    domainObject = "note"


class AttachmentEditBook(EditBook):
    allPageNames = ["subject", "notes", "appearance"]
    domainObject = "attachment"

    def create_subject_page(self):
        return AttachmentSubjectPage(self.items, self, self.settings)

    def isDisplayingItemOrChildOfItem(self, targetItem):
        return targetItem in self.items


class EffortEditBook(Page):
    domainObject = "effort"
    columns = 3

    def __init__(
        self,
        parent,
        efforts,
        taskFile,
        settings,
        items_are_new,
        *args,
        **kwargs
    ):  # pylint: disable=W0613
        self._effortList = taskFile.efforts()
        task_list = taskFile.tasks()
        self._taskList = task.TaskList(task_list)
        self._taskList.extend(
            [
                effort.task()
                for effort in efforts
                if effort.task() not in task_list
            ]
        )
        self._settings = settings
        self._taskFile = taskFile
        super().__init__(efforts, parent, *args, **kwargs)
        pub.subscribe(
            self.__onChoicesConfigChanged, "settings.feature.sdtcspans_effort"
        )

    def __onChoicesConfigChanged(self, value=""):
        self._stopDateTimeEntry.LoadChoices(value)

    def getPage(self, pageName):  # pylint: disable=W0613
        return None  # An EffortEditBook is not really a notebook...

    def settings_section(self):
        """Return the settings section for the effort dialog."""
        # Since the effort dialog has no tabs, the settings section does not
        # depend on the visible tabs.
        return "effortdialog"

    def perspective(self):
        """Return the perspective for the effort dialog."""
        # Since the effort dialog has no tabs, the perspective is always the
        # same and the value does not matter.
        return "effort dialog perspective"

    def addEntries(self):
        self.__add_task_entry()
        self.__add_start_and_stop_entries()
        self.addDescriptionEntry()

    def __add_task_entry(self):
        """Add an entry for changing the task that this effort record
        belongs to."""
        # pylint: disable=W0201,W0212
        panel = wx.Panel(self)
        current_task = self.items[0].task()
        self._taskEntry = entry.TaskEntry(
            panel,
            rootTasks=self._taskList.rootItems(),
            selectedTask=current_task,
        )
        self._taskSync = attributesync.AttributeSync(
            "task",
            self._taskEntry,
            current_task,
            self.items,
            command.EditTaskCommand,
            entry.EVT_TASKENTRY,
            self.items[0].taskChangedEventType(),
        )
        edit_task_button = wx.Button(panel, label=_("Edit task"))
        edit_task_button.Bind(wx.EVT_BUTTON, self.onEditTask)
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_sizer.Add(
            self._taskEntry,
            proportion=1,
            flag=wx.EXPAND,
        )
        panel_sizer.Add((3, -1))
        panel_sizer.Add(
            edit_task_button, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL
        )
        panel.SetSizerAndFit(panel_sizer)
        self.addEntry(_("Task"), panel, flags=[None, wx.ALL | wx.EXPAND])

    def __onStartDateTimeChanged(self, value):
        self._stopDateTimeEntry.SetRelativeChoicesStart(start=value)

    def __onChoicesChanged(self, event):
        self._settings.settext("feature", "sdtcspans_effort", event.GetValue())

    def __add_start_and_stop_entries(self):
        # pylint: disable=W0201,W0142
        date_time_entry_kw_args = dict(showSeconds=True)
        flags = [
            None,
            wx.ALIGN_RIGHT | wx.ALL,
            wx.ALIGN_LEFT | wx.ALL | wx.ALIGN_CENTER_VERTICAL,
            None,
        ]

        current_start_date_time = self.items[0].getStart()
        self._startDateTimeEntry = entry.DateTimeEntry(
            self,
            self._settings,
            current_start_date_time,
            noneAllowed=False,
            showRelative=True,
            **date_time_entry_kw_args
        )
        wx.CallAfter(self._startDateTimeEntry.HideRelativeButton)
        self._startDateTimeSync = attributesync.AttributeSync(
            "getStart",
            self._startDateTimeEntry,
            current_start_date_time,
            self.items,
            command.EditEffortStartDateTimeCommand,
            entry.EVT_DATETIMEENTRY,
            self.items[0].startChangedEventType(),
            commit_on_focus_loss=True,  # Only commit when focus leaves the field
            callback=self.__onStartDateTimeChanged,
        )
        self._startDateTimeEntry.Bind(
            entry.EVT_DATETIMEENTRY, self.onDateTimeChanged
        )
        start_from_last_effort_button = (
            self.__create_start_from_last_effort_button()
        )
        self.addEntry(
            _("Start"),
            self._startDateTimeEntry,
            start_from_last_effort_button,
            flags=flags,
        )

        current_stop_date_time = self.items[0].getStop()
        self._stopDateTimeEntry = entry.DateTimeEntry(
            self,
            self._settings,
            current_stop_date_time,
            noneAllowed=True,
            showRelative=True,
            units=[
                (_("Minute(s)"), 60),
                (_("Hour(s)"), 3600),
                (_("Day(s)"), 24 * 3600),
                (_("Week(s)"), 7 * 24 * 3600),
            ],
            **date_time_entry_kw_args
        )
        self._stopDateTimeSync = attributesync.AttributeSync(
            "getStop",
            self._stopDateTimeEntry,
            current_stop_date_time,
            self.items,
            command.EditEffortStopDateTimeCommand,
            entry.EVT_DATETIMEENTRY,
            self.items[0].stopChangedEventType(),
            commit_on_focus_loss=True,  # Only commit when focus leaves the field
            callback=self.__onStopDateTimeChanged,
        )
        self._stopDateTimeEntry.Bind(
            entry.EVT_DATETIMEENTRY, self.onStopDateTimeChanged
        )
        stop_now_button = self.__create_stop_now_button()
        self._invalidPeriodMessage = self.__create_invalid_period_message()
        self.addEntry(
            _("Stop"), self._stopDateTimeEntry, stop_now_button, flags=flags
        )
        self.__onStartDateTimeChanged(current_start_date_time)
        self._stopDateTimeEntry.LoadChoices(
            self._settings.get("feature", "sdtcspans_effort")
        )

        self._stopDateTimeEntry.Bind(
            sdtc.EVT_TIME_CHOICES_CHANGE, self.__onChoicesChanged
        )
        self.addEntry("", self._invalidPeriodMessage)

    def __create_start_from_last_effort_button(self):
        button = wx.Button(self, label=_("Start tracking from last stop time"))
        self.Bind(wx.EVT_BUTTON, self.onStartFromLastEffort, button)
        if self._effortList.maxDateTime() is None:
            button.Disable()
        return button

    def __create_stop_now_button(self):
        button = wx.Button(self, label=_("Stop tracking now"))
        self.Bind(wx.EVT_BUTTON, self.onStopNow, button)
        return button

    def __create_invalid_period_message(self):
        text = wx.StaticText(self, label="")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        text.SetFont(font)
        return text

    def onStartFromLastEffort(self, event):  # pylint: disable=W0613
        maxDateTime = self._effortList.maxDateTime()
        if self._startDateTimeEntry.GetValue() != maxDateTime:
            self._startDateTimeEntry.SetValue(self._effortList.maxDateTime())
            self._startDateTimeSync.onAttributeEdited(event)
        self.onDateTimeChanged(event)

    def onStopNow(self, event):
        command.StopEffortCommand(self._effortList, self.items).do()

    def onStopDateTimeChanged(self, *args, **kwargs):
        self.onDateTimeChanged(*args, **kwargs)

    def __onStopDateTimeChanged(self, new_value):
        # The actual start date/time was not changed (the command class checks that) if
        # if was greater than the stop date/time then, so make sure it is if everything is
        # OK now.
        command.EditEffortStartDateTimeCommand(
            None, self.items, newValue=self._startDateTimeEntry.GetValue()
        ).do()

    def onDateTimeChanged(self, event):
        event.Skip()
        self.__update_invalid_period_message()

    def __update_invalid_period_message(self):
        message = (
            ""
            if self.__is_period_valid()
            else _("Warning: start must be earlier than stop")
        )
        self._invalidPeriodMessage.SetLabel(message)

    def __is_period_valid(self):
        """Return whether the current period is valid, i.e. the start date
        and time is earlier than the stop date and time."""
        try:
            return (
                self._startDateTimeEntry.GetValue()
                < self._stopDateTimeEntry.GetValue()
            )
        except AttributeError:
            return True  # Entries not created yet

    def onEditTask(self, event):  # pylint: disable=W0613
        task_to_edit = self._taskEntry.GetValue()
        TaskEditor(
            None,
            [task_to_edit],
            self._settings,
            self._taskFile.tasks(),
            self._taskFile,
        ).Show()

    def addDescriptionEntry(self):
        # pylint: disable=W0201
        def combined_description(items):
            distinctDescriptions = set(item.description() for item in items)
            if len(distinctDescriptions) == 1 and distinctDescriptions.pop():
                return items[0].description()
            lines = ["[%s]" % _("Edit to change all descriptions")]
            lines.extend(
                item.description() for item in items if item.description()
            )
            return "\n\n".join(lines)

        current_description = (
            self.items[0].description()
            if len(self.items) == 1
            else combined_description(self.items)
        )
        self._descriptionEntry = widgets.MultiLineTextCtrl(
            self, current_description
        )
        native_info_string = self._settings.get("editor", "descriptionfont")
        font = (
            wx.FontFromNativeInfoString(native_info_string)
            if native_info_string
            else None
        )
        if font:
            self._descriptionEntry.SetFont(font)
        self._descriptionEntry.SetSizeHints(300, 150)
        self._descriptionSync = attributesync.AttributeSync(
            "description",
            self._descriptionEntry,
            current_description,
            self.items,
            command.EditDescriptionCommand,
            wx.EVT_KILL_FOCUS,
            self.items[0].descriptionChangedEventType(),
        )
        self.addEntry(_("Description"), self._descriptionEntry, growable=True)

    def setFocus(self, column_name):
        self.setFocusOnEntry(column_name)

    def isDisplayingItemOrChildOfItem(self, item):
        if hasattr(item, "setTask"):
            return self.items[0] == item  # Regular effort
        else:
            return item.mayContain(self.items[0])  # Composite effort

    def entries(self):
        return dict(
            firstEntry=self._startDateTimeEntry,
            task=self._taskEntry,
            period=self._stopDateTimeEntry,
            description=self._descriptionEntry,
            timeSpent=self._stopDateTimeEntry,
            revenue=self._taskEntry,
        )

    def close_edit_book(self):
        pass


class Editor(BalloonTipManager, widgets.Dialog):
    EditBookClass = lambda *args: "Subclass responsibility"
    singular_title = "Subclass responsibility %s"
    plural_title = "Subclass responsibility"

    def __init__(
        self, parent, items, settings, container, task_file, *args, **kwargs
    ):
        self._items = items
        self._settings = settings
        self._taskFile = task_file
        self.__items_are_new = kwargs.pop("items_are_new", False)
        column_name = kwargs.pop("columnName", "")
        self.__call_after = kwargs.get("call_after", wx.CallAfter)
        super().__init__(
            parent, self.__title(), buttonTypes=wx.ID_CLOSE, *args, **kwargs
        )
        if not column_name:
            if self._interior.perspective() and hasattr(
                self._interior, "GetSelection"
            ):
                column_name = self._interior[
                    self._interior.GetSelection()
                ].pageName
            else:
                column_name = "subject"
        if column_name:
            self._interior.setFocus(column_name)

        patterns.Publisher().registerObserver(
            self.on_item_removed,
            eventType=container.removeItemEventType(),
            eventSource=container,
        )
        if len(self._items) == 1:
            patterns.Publisher().registerObserver(
                self.on_subject_changed,
                eventType=self._items[0].subjectChangedEventType(),
                eventSource=self._items[0],
            )
        self.Bind(wx.EVT_CLOSE, self.on_close_editor)

        # Note: We intentionally do NOT freeze viewers while the dialog is open.
        # Updates should propagate immediately so other windows stay in sync.
        # The commit_on_focus_loss option on AttributeSync handles batching
        # rapid edits into single commands.

        if operating_system.isMac():
            # Sigh. On OS X, if you open an editor, switch back to the main window, open
            # another editor, then hit Escape twice, the second editor disappears without any
            # notification (EVT_CLOSE, EVT_ACTIVATE), so poll for this, because there might
            # be pending changes...
            id_ = IdProvider.get()
            self.__timer = wx.Timer(self, id_)
            self.Bind(wx.EVT_TIMER, self.__on_timer, id=id_)
            self.__timer.Start(1000, False)
        else:
            self.__timer = None

        # Position and size handling is done by WindowGeometryTracker
        # which will center on parent if no saved position exists, or
        # restore the last saved position (must be on same monitor as parent)
        self.__create_ui_commands()
        self.__dimensions_tracker = (
            windowdimensionstracker.WindowGeometryTracker(
                self, settings, self._interior.settings_section(), parent=parent
            )
        )

    def __on_timer(self, event):
        if not self.IsShown():
            self.Close()

    def __create_ui_commands(self):
        # FIXME: keyboard shortcuts are hardcoded here, but they can be
        # changed in the translations
        # FIXME: there are more keyboard shortcuts that don't work in dialogs
        # at the moment, like DELETE
        self.__new_effort_id = IdProvider.get()
        table = wx.AcceleratorTable(
            [
                (wx.ACCEL_CMD, ord("Z"), wx.ID_UNDO),
                (wx.ACCEL_CMD, ord("Y"), wx.ID_REDO),
                (wx.ACCEL_CMD, ord("E"), self.__new_effort_id),
            ]
        )
        self._interior.SetAcceleratorTable(table)
        # pylint: disable=W0201
        self.__undo_command = uicommand.EditUndo()
        self.__redo_command = uicommand.EditRedo()
        effort_page = self._interior.getPage("effort")
        effort_viewer = effort_page.viewer if effort_page else None
        self.__new_effort_command = uicommand.EffortNew(
            viewer=effort_viewer,
            taskList=self._taskFile.tasks(),
            effortList=self._taskFile.efforts(),
            settings=self._settings,
        )
        self.__undo_command.bind(self._interior, wx.ID_UNDO)
        self.__redo_command.bind(self._interior, wx.ID_REDO)
        self.__new_effort_command.bind(self._interior, self.__new_effort_id)

    def createInterior(self):
        return self.EditBookClass(
            self._panel,
            self._items,
            self._taskFile,
            self._settings,
            self.__items_are_new,
        )

    def on_close_editor(self, event):
        event.Skip()
        # Save dialog position/size before closing
        self.__dimensions_tracker.save()
        self._interior.close_edit_book()
        patterns.Publisher().removeObserver(self.on_item_removed)
        patterns.Publisher().removeObserver(self.on_subject_changed)
        # On Mac OS X, the text control does not lose focus when
        # destroyed...
        if operating_system.isMac():
            self._interior.SetFocusIgnoringChildren()
        if self.__timer is not None:
            IdProvider.put(self.__timer.GetId())
        IdProvider.put(self.__new_effort_id)
        # Note: No need to thaw viewers since we don't freeze them on open anymore
        self.Destroy()

    def on_activate(self, event):
        event.Skip()

    def on_item_removed(self, event):
        """The item we're editing or one of its ancestors has been removed or
        is hidden by a filter. If the item is really removed, close the tab
        of the item involved and close the whole editor if there are no
        tabs left."""
        if self:  # Prevent _wxPyDeadObject TypeError
            self.__call_after(
                self.__close_if_item_is_deleted, list(event.values())
            )

    def __close_if_item_is_deleted(self, items):
        # Guard against deleted C++ object - can happen when wx.CallAfter
        # callback executes after window destruction (e.g., closing nested dialogs)
        try:
            if not self or self.IsBeingDeleted():
                return
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            return
        for item in items:
            if (
                self._interior.isDisplayingItemOrChildOfItem(item)
                and not item in self._taskFile
            ):
                self.Close()
                break

    def on_subject_changed(self, event):  # pylint: disable=W0613
        self.SetTitle(self.__title())

    def __title(self):
        return (
            self.plural_title
            if len(self._items) > 1
            else self.singular_title % self._items[0].subject()
        )


class TaskEditor(Editor):
    plural_title = _("Multiple tasks")
    singular_title = _("%s (task)")
    EditBookClass = TaskEditBook


class CategoryEditor(Editor):
    plural_title = _("Multiple categories")
    singular_title = _("%s (category)")
    EditBookClass = CategoryEditBook


class NoteEditor(Editor):
    plural_title = _("Multiple notes")
    singular_title = _("%s (note)")
    EditBookClass = NoteEditBook


class AttachmentEditor(Editor):
    plural_title = _("Multiple attachments")
    singular_title = _("%s (attachment)")
    EditBookClass = AttachmentEditBook


class EffortEditor(Editor):
    plural_title = _("Multiple efforts")
    singular_title = _("%s (effort)")
    EditBookClass = EffortEditBook
