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
from taskcoachlib.domain.task import status
from taskcoachlib.gui import viewer, uicommand, windowdimensionstracker
from taskcoachlib.gui.dialog import entry, attributesync
from taskcoachlib.gui.dialog.entry import (
    get_suggested_hour_choices,
    get_suggested_minute_choices,
    get_suggested_second_choices,
)
from taskcoachlib.gui.newid import IdProvider
from taskcoachlib.i18n import _
from pubsub import pub
from taskcoachlib.thirdparty import smartdatetimectrl as sdtc
from taskcoachlib.help.balloontips import BalloonTipManager
import datetime
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
        can start typing over it immediately."""
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

    def close(self):
        self.removeInstance()


class SubjectPage(Page):
    pageName = "subject"
    pageTitle = _("Description")
    pageIcon = "pencil_icon"

    def __init__(self, items, parent, settings, *args, **kwargs):
        self._settings = settings
        super().__init__(items, parent, *args, **kwargs)

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
    # Map type_ values to human-readable names and icons
    TYPE_INFO = {
        "file": (_("File"), "document_icon"),
        "folder": (_("Folder"), "folder_blue_icon"),
        "uri": (_("Link"), "earth_blue_icon"),
        "mail": (_("Email"), "envelope_icon"),
        "unknown": (_("Unknown"), None),
    }

    def _isFolderUri(self, item):
        """Check if a URI attachment points to a local folder."""
        if item.type_ != "uri":
            return False
        location = item.location()
        if location.startswith("file://"):
            import urllib.request
            import os
            try:
                path = urllib.request.url2pathname(location[7:])
                return os.path.isdir(path)
            except Exception:
                return False
        return False

    def addEntries(self):
        # Override to insert type and location entries
        self.addSubjectEntry()
        self.addTypeEntry()
        self.addLocationEntry()
        self.addDescriptionEntry()
        self.addCreationDateTimeEntry()
        self.addModificationDateTimeEntry()

    def addTypeEntry(self):
        """Add a read-only type field with icon."""
        import os
        if len(self.items) == 1:
            item = self.items[0]
            if self._isFolderUri(item):
                type_name, icon_name = self.TYPE_INFO.get("folder")
            else:
                item_type = item.type_
                type_name, icon_name = self.TYPE_INFO.get(
                    item_type, (item_type, None)
                )
                # Check if file exists for file attachments
                if item_type == "file":
                    attachmentBase = self._settings.get("file", "attachmentbase")
                    if not os.path.exists(item.normalizedLocation(attachmentBase)):
                        icon_name = "fileopen_red"
        else:
            # Multiple items - show type if all same, otherwise "Mixed"
            types = set(item.type_ for item in self.items)
            if len(types) == 1:
                item_type = types.pop()
                type_name, icon_name = self.TYPE_INFO.get(
                    item_type, (_("Unknown"), None)
                )
            else:
                type_name = _("Mixed")
                icon_name = None

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        if icon_name:
            bitmap = wx.ArtProvider.GetBitmap(icon_name, wx.ART_MENU, (16, 16))
            if bitmap.IsOk():
                icon = wx.StaticBitmap(panel, bitmap=bitmap)
                sizer.Add(icon, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        type_label = wx.StaticText(panel, label=type_name)
        sizer.Add(type_label, 0, wx.ALIGN_CENTER_VERTICAL)
        panel.SetSizer(sizer)
        self.addEntry(_("Type"), panel, flags=[wx.ALIGN_RIGHT, wx.ALIGN_CENTER_VERTICAL])

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
        sizer.Add(self._locationEntry, 1, wx.EXPAND)
        if all(item.type_ == "file" for item in self.items):
            button = wx.Button(panel, wx.ID_ANY, _("Browse"))
            sizer.Add(button, 0, wx.LEFT, 5)
            button.Bind(wx.EVT_BUTTON, self.onSelectLocation)
        panel.SetSizer(sizer)
        self.addEntry(_("Location"), panel, flags=[wx.ALIGN_RIGHT, wx.EXPAND])

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
    columns = 3  # label, datetime row, rest

    def __init__(
        self, theTask, parent, settings, items_are_new, *args, **kwargs
    ):
        self.__settings = settings
        self._duration = None
        self.__items_are_new = items_are_new
        super().__init__(theTask, parent, *args, **kwargs)

    def __onPlannedStartChanged(self, value):
        """AttributeSync callback for planned start date changes."""
        self._currentPlannedStartDateTime = value
        self.__onPlannedStartDateTimeChanged(value)

    def __onPlannedStartDateTimeChanged(self, value):
        """Called when planned start date changes - update based on mode."""
        if hasattr(self, '_currentPlannedDurationMode'):
            if self._currentPlannedDurationMode == "implicit":
                self.__updateImplicitDuration()
            elif self._currentPlannedDurationMode == "adjdue":
                # Planned start changed, recalculate due date
                self.__updateDueDateFromDuration()

    def __onDueDateChanged(self, value):
        """AttributeSync callback for due date changes."""
        self._currentDueDateTime = value
        self.__onDueDateTimeChanged(value)

    def __onDueDateTimeChanged(self, value):
        """Called when due date changes - update based on mode."""
        if hasattr(self, '_currentPlannedDurationMode'):
            if self._currentPlannedDurationMode == "implicit":
                self.__updateImplicitDuration()
            elif self._currentPlannedDurationMode == "adjstart":
                # Due date changed, recalculate planned start
                self.__updatePlannedStartFromDuration()

    def addEntries(self):
        self.addStatusEntry()
        self.addLine()
        self.addDateEntries()
        self.addLine()
        self.addReminderEntry()
        self.addLine()
        self.addRecurrenceEntry()

    def addStatusEntry(self):
        """Add a read-only status display showing icon, color, and status text."""
        if len(self.items) != 1:
            return  # Only show for single task editing

        # Create panel that doesn't accept keyboard focus (skipped in tab order)
        class NoFocusPanel(wx.Panel):
            def AcceptsFocusFromKeyboard(self):
                return False
        self._statusPanel = NoFocusPanel(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self._statusIcon = wx.StaticBitmap(self._statusPanel)
        sizer.Add(self._statusIcon, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

        self._statusLabel = wx.StaticText(self._statusPanel, label="")
        sizer.Add(self._statusLabel, 0, wx.ALIGN_CENTER_VERTICAL)

        self._statusPanel.SetSizer(sizer)
        # 2 controls: label + panel (panel auto-spans columns 1-4 in 5-column grid)
        self.addEntry(
            _("Status"),
            self._statusPanel,
            flags=[wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL,
                   wx.ALIGN_CENTER_VERTICAL | wx.EXPAND]
        )

        # Initial display
        self._updateStatusDisplay()

        # Subscribe to date change events (these affect status)
        pub.subscribe(self._onStatusMayHaveChanged, self.items[0].actualStartDateTimeChangedEventType())
        pub.subscribe(self._onStatusMayHaveChanged, self.items[0].plannedStartDateTimeChangedEventType())
        pub.subscribe(self._onStatusMayHaveChanged, self.items[0].dueDateTimeChangedEventType())
        pub.subscribe(self._onStatusMayHaveChanged, self.items[0].completionDateTimeChangedEventType())

    def _onStatusMayHaveChanged(self, newValue=None, sender=None):
        """Called when task appearance or dates change."""
        if sender == self.items[0] or sender is None:
            self._updateStatusDisplay()

    def _updateStatusDisplay(self):
        """Update the status icon, text, and colors."""
        if not hasattr(self, '_statusLabel'):
            return
        theTask = self.items[0]
        taskStatus = theTask.status()

        # Update icon
        icon_name = taskStatus.getBitmap(self.__settings)
        bitmap = wx.ArtProvider.GetBitmap(icon_name, wx.ART_MENU, (16, 16))
        if bitmap.IsOk():
            self._statusIcon.SetBitmap(bitmap)

        # Update text and colors
        statusText = taskStatus.pluralLabel.replace(" tasks", "").replace("tasks", "").strip()
        self._statusLabel.SetLabel(statusText)
        self._statusLabel.SetForegroundColour(theTask.statusFgColor())
        bgColor = theTask.statusBgColor()
        if bgColor:
            self._statusLabel.SetBackgroundColour(bgColor)
        else:
            self._statusLabel.SetBackgroundColour(wx.NullColour)

        self._statusPanel.Layout()

    def _onLocalValueChanged(self, event):
        """Handle live value changes in date fields for local status preview."""
        source = event.GetEventObject()
        mode = getattr(self, '_currentPlannedDurationMode', None)
        self._updateLocalStatusDisplay()

        # Check if source belongs to planned start or due date combos
        isPlannedStartSource = self._plannedStartDateTimeCombo.ContainsControl(source)
        isDueDateSource = self._dueDateTimeCombo.ContainsControl(source)

        if mode == "implicit":
            # Inputs: planned start, due date -> Output: duration
            if isPlannedStartSource or isDueDateSource:
                self.__updateImplicitDuration()
        elif mode == "adjdue":
            # Inputs: planned start, duration -> Output: due date
            if isPlannedStartSource:
                self.__updateDueDateLive()
        elif mode == "adjstart":
            # Inputs: due date, duration -> Output: planned start
            if isDueDateSource:
                self.__updatePlannedStartLive()

        event.Skip()

    def _onDurationValueChanged(self, event):
        """Handle live value changes in duration control."""
        self._updateLocalStatusDisplay()
        self.__updatePresetSelection()  # Match preset dropdown to current value

        # Duration is an INPUT only for adjdue and adjstart modes
        mode = getattr(self, '_currentPlannedDurationMode', None)

        if mode == "adjdue":
            # Inputs: planned start, duration -> Output: due date
            self.__updateDueDateLive()
        elif mode == "adjstart":
            # Inputs: due date, duration -> Output: planned start
            self.__updatePlannedStartLive()
        # In "implicit" mode, duration is the OUTPUT, so don't trigger anything

        event.Skip()

    def __updateDueDateLive(self):
        """Calculate and display due date from planned start + duration (no commit)."""
        start = self._plannedStartDateTimeCombo.GetDateTime()
        if start is None:
            return  # No start date, can't calculate

        duration = self._plannedDurationCtrl.GetDuration()
        new_due = start + duration

        # Update display only, don't commit to domain
        self._dueDateTimeCombo.SetDateTime(new_due)

    def __updatePlannedStartLive(self):
        """Calculate and display planned start from due date - duration (no commit)."""
        due = self._dueDateTimeCombo.GetDateTime()
        if due is None:
            return  # No due date, can't calculate

        duration = self._plannedDurationCtrl.GetDuration()
        new_start = due - duration

        # Update display only, don't commit to domain
        self._plannedStartDateTimeCombo.SetDateTime(new_start)

    def _computeLocalStatus(self):
        """Compute task status based on current field values (not domain object).

        This provides live preview as user edits, before focus loss commits changes.
        """
        theTask = self.items[0]
        now = date.Now()
        dueSoonHours = self.__settings.getint("behavior", "duesoonhours")

        # Get values from fields (not from task object)
        completionDT = self._completionDateTimeCombo.GetDateTime() if hasattr(self, '_completionDateTimeCombo') else None
        actualStartDT = self._actualStartDateTimeCombo.GetDateTime() if hasattr(self, '_actualStartDateTimeCombo') else None
        plannedStartDT = self._plannedStartDateTimeCombo.GetDateTime() if hasattr(self, '_plannedStartDateTimeCombo') else None
        dueDT = self._dueDateTimeCombo.GetDateTime() if hasattr(self, '_dueDateTimeCombo') else None

        # Convert None to sentinel for comparison
        maxDT = date.DateTime.max

        # Completion check
        if completionDT is not None:
            return status.completed

        # Prerequisites check (use task object since we can't edit these here)
        if any(
            prerequisite.completionDateTime() == theTask.maxDateTime
            for prerequisite in theTask.prerequisites(recursive=True, upwards=True)
        ):
            return status.inactive

        # Due date checks
        if dueDT is not None:
            dueDT = date.DateTime.fromDateTime(dueDT) if not isinstance(dueDT, date.DateTime) else dueDT
            if dueDT < now:
                return status.overdue
            timeLeft = dueDT - now
            if 0 <= timeLeft.hours() < dueSoonHours:
                return status.duesoon

        # Actual start check
        if actualStartDT is not None:
            actualStartDT = date.DateTime.fromDateTime(actualStartDT) if not isinstance(actualStartDT, date.DateTime) else actualStartDT
            if actualStartDT <= now:
                return status.active

        # Planned start check
        if plannedStartDT is not None:
            plannedStartDT = date.DateTime.fromDateTime(plannedStartDT) if not isinstance(plannedStartDT, date.DateTime) else plannedStartDT
            if plannedStartDT < now:
                return status.late

        return status.inactive

    def _updateLocalStatusDisplay(self):
        """Update status display based on current field values (live preview)."""
        if not hasattr(self, '_statusLabel'):
            return
        taskStatus = self._computeLocalStatus()

        # Update icon
        icon_name = taskStatus.getBitmap(self.__settings)
        bitmap = wx.ArtProvider.GetBitmap(icon_name, wx.ART_MENU, (16, 16))
        if bitmap.IsOk():
            self._statusIcon.SetBitmap(bitmap)

        # Update text and colors - use task class methods to get colors for status
        statusText = taskStatus.pluralLabel.replace(" tasks", "").replace("tasks", "").strip()
        self._statusLabel.SetLabel(statusText)

        # Get colors for this status from settings via task class methods
        fgColor = task.Task.fgColorForStatus(taskStatus)
        bgColor = task.Task.bgColorForStatus(taskStatus)
        self._statusLabel.SetForegroundColour(fgColor)
        if bgColor and bgColor != wx.WHITE:
            self._statusLabel.SetBackgroundColour(bgColor)
        else:
            self._statusLabel.SetBackgroundColour(wx.NullColour)

        self._statusPanel.Layout()

    def addDateEntries(self):
        # Create panel for planned date section with table layout
        self._addPlannedDateSection()
        self.addLine()
        self._addActualStartDateEntry()
        self._addCompletionDateEntry()

        # Now that all date entries exist, set initial enabled state and calculate values
        if hasattr(self, '_currentPlannedDurationMode'):
            # Set initial enabled state for date fields
            self._updateDateFieldsEnabled(self._currentPlannedDurationMode)

            # Calculate initial values based on mode
            if self._currentPlannedDurationMode == "implicit":
                self.__updateImplicitDuration()

    def _addPlannedDateSection(self):
        """Add the planned date section using the main grid (5 columns: label, checkbox, date, time, rest)."""
        # Row 1: Planned start date
        plannedStartDateTime = (
            self.items[0].plannedStartDateTime()
            if len(self.items) == 1
            else date.DateTime()
        )
        self._currentPlannedStartDateTime = plannedStartDateTime

        # value=None means unchecked, value=datetime means checked
        value = plannedStartDateTime if plannedStartDateTime != date.DateTime() else None

        self._plannedStartDateTimeCombo = widgets.DateTimeCombo(
            self, value=value,
            hourChoices=lambda: get_suggested_hour_choices(self._DatesPage__settings),
            minuteChoices=lambda: get_suggested_minute_choices(self._DatesPage__settings)
        )
        # Use AttributeSync for automatic external update handling
        # Use EVT_KILL_FOCUS to sync on focus loss (same pattern as subject field)
        self._plannedStartDateTimeSync = attributesync.AttributeSync(
            "plannedStartDateTime",
            self._plannedStartDateTimeCombo,
            plannedStartDateTime,
            self.items,
            command.EditPlannedStartDateTimeCommand,
            wx.EVT_KILL_FOCUS,
            self.items[0].plannedStartDateTimeChangedEventType(),
            callback=self.__onPlannedStartChanged,
        )
        # Bind value change for live status preview
        self._plannedStartDateTimeCombo.Bind(widgets.EVT_VALUE_CHANGED, self._onLocalValueChanged)

        # Add planned start row: label | datetime row | (empty)
        self.addEntry(
            _("Planned start date"),
            self._plannedStartDateTimeCombo.CreateRowPanel(self),
            wx.StaticText(self, label=""),
        )

        # Row 2: Planned duration
        plannedDuration = (
            self.items[0].plannedDuration()
            if len(self.items) == 1
            else date.TimeDelta()
        )
        plannedDurationMode = (
            self.items[0].plannedDurationMode()
            if len(self.items) == 1
            else "implicit"
        )

        total_seconds = int(plannedDuration.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        self._plannedDurationCtrl = widgets.MaskedDurationCtrl(
            self, days=days, hours=hours, minutes=minutes,
            dayChoices=[0, 1, 2, 3, 5, 7, 14, 21, 28, 30, 60, 90],
            hourChoices=list(range(24)),  # Duration uses full 0-23 range (not workday)
            minuteChoices=lambda: get_suggested_minute_choices(self._DatesPage__settings)
        )
        if plannedDurationMode == "implicit":
            self._plannedDurationCtrl.Enable(False)
        self._plannedDurationCtrl.Bind(
            wx.EVT_KILL_FOCUS, self.__onPlannedDurationChanged
        )
        # Bind value change for live calculated field updates
        self._plannedDurationCtrl.Bind(
            widgets.EVT_VALUE_CHANGED, self._onDurationValueChanged
        )

        # Presets dropdown
        self._durationPresetsChoice = wx.Choice(self)
        self.__populateDurationPresets()
        self._durationPresetsChoice.Bind(wx.EVT_CHOICE, self.__onDurationPresetSelected)
        if plannedDurationMode == "implicit":
            self._durationPresetsChoice.Enable(False)

        pub.subscribe(self.__onPresetsConfigChanged, "settings.feature.sdtcspans")

        # Mode dropdown
        self._durationModeChoices = [
            ("implicit", _("Implicit")),
            ("adjdue", _("Adjust Due Date")),
            ("adjstart", _("Adjust Planned Start Date")),
        ]
        self._durationModeChoice = wx.Choice(self)
        for key, label in self._durationModeChoices:
            self._durationModeChoice.Append(label, key)

        mode_index = 0
        for idx, (key, label) in enumerate(self._durationModeChoices):
            if key == plannedDurationMode:
                mode_index = idx
                break
        self._durationModeChoice.SetSelection(mode_index)
        self._durationModeChoice.Bind(wx.EVT_CHOICE, self.__onDurationModeChanged)

        self._currentPlannedDuration = plannedDuration
        self._currentPlannedDurationMode = plannedDurationMode

        # Create panel for presets + mode in last column
        durationRestPanel = wx.Panel(self)
        durationRestSizer = wx.BoxSizer(wx.HORIZONTAL)
        # Re-parent the controls to the panel
        self._durationPresetsChoice.Reparent(durationRestPanel)
        self._durationModeChoice.Reparent(durationRestPanel)
        durationRestSizer.Add(self._durationPresetsChoice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        durationRestSizer.Add(self._durationModeChoice, 0, wx.ALIGN_CENTER_VERTICAL)
        durationRestPanel.SetSizer(durationRestSizer)

        # Add duration row: label | duration | presets+mode (left-aligned)
        self.addEntry(
            _("Planned duration"),
            self._plannedDurationCtrl,
            durationRestPanel,
            flags=[None, None, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.ALL],
        )

        # Row 3: Due date
        dueDateTime = (
            self.items[0].dueDateTime()
            if len(self.items) == 1
            else date.DateTime()
        )
        self._currentDueDateTime = dueDateTime

        # value=None means unchecked, value=datetime means checked
        value = dueDateTime if dueDateTime != date.DateTime() else None

        self._dueDateTimeCombo = widgets.DateTimeCombo(
            self, value=value,
            hourChoices=lambda: get_suggested_hour_choices(self._DatesPage__settings),
            minuteChoices=lambda: get_suggested_minute_choices(self._DatesPage__settings)
        )
        # Use AttributeSync for automatic external update handling
        # Use EVT_KILL_FOCUS to sync on focus loss (same pattern as subject field)
        self._dueDateTimeSync = attributesync.AttributeSync(
            "dueDateTime",
            self._dueDateTimeCombo,
            dueDateTime,
            self.items,
            command.EditDueDateTimeCommand,
            wx.EVT_KILL_FOCUS,
            self.items[0].dueDateTimeChangedEventType(),
            callback=self.__onDueDateChanged,
        )
        # Bind value change for live status preview
        self._dueDateTimeCombo.Bind(widgets.EVT_VALUE_CHANGED, self._onLocalValueChanged)

        # Add due date row: label | datetime row | (empty)
        self.addEntry(
            _("Due date"),
            self._dueDateTimeCombo.CreateRowPanel(self),
            wx.StaticText(self, label=""),
        )

    def _addActualStartDateEntry(self):
        """Add actual start date entry using DateTimeCombo."""
        actualStartDateTime = (
            self.items[0].actualStartDateTime()
            if len(self.items) == 1
            else date.DateTime()
        )
        self._currentActualStartDateTime = actualStartDateTime

        # value=None means unchecked, value=datetime means checked
        value = actualStartDateTime if actualStartDateTime != date.DateTime() else None

        self._actualStartDateTimeCombo = widgets.DateTimeCombo(
            self, value=value,
            hourChoices=lambda: get_suggested_hour_choices(self._DatesPage__settings),
            minuteChoices=lambda: get_suggested_minute_choices(self._DatesPage__settings)
        )
        # Use AttributeSync for automatic external update handling
        # Use EVT_KILL_FOCUS to sync on focus loss (same pattern as subject field)
        self._actualStartDateTimeSync = attributesync.AttributeSync(
            "actualStartDateTime",
            self._actualStartDateTimeCombo,
            actualStartDateTime,
            self.items,
            command.EditActualStartDateTimeCommand,
            wx.EVT_KILL_FOCUS,
            self.items[0].actualStartDateTimeChangedEventType(),
            callback=self.__onActualStartChanged,
        )
        # Bind value change for live status preview
        self._actualStartDateTimeCombo.Bind(widgets.EVT_VALUE_CHANGED, self._onLocalValueChanged)

        self.addEntry(
            _("Actual start date"),
            self._actualStartDateTimeCombo.CreateRowPanel(self),
            wx.StaticText(self, label=""),
        )

    def __onActualStartChanged(self, value):
        """AttributeSync callback for actual start date changes."""
        self._currentActualStartDateTime = value

    def _addCompletionDateEntry(self):
        """Add completion date entry using DateTimeCombo with AttributeSync."""
        completionDateTime = (
            self.items[0].completionDateTime()
            if len(self.items) == 1
            else date.DateTime()
        )

        # value=None means unchecked, value=datetime means checked
        value = completionDateTime if completionDateTime != date.DateTime() else None

        self._completionDateTimeCombo = widgets.DateTimeCombo(
            self, value=value,
            hourChoices=lambda: get_suggested_hour_choices(self._DatesPage__settings),
            minuteChoices=lambda: get_suggested_minute_choices(self._DatesPage__settings)
        )

        # Use AttributeSync for automatic external update handling
        # Use EVT_KILL_FOCUS to sync on focus loss (same pattern as other date fields)
        self._completionDateTimeSync = attributesync.AttributeSync(
            "completionDateTime",
            self._completionDateTimeCombo,
            completionDateTime,
            self.items,
            command.EditCompletionDateTimeCommand,
            wx.EVT_KILL_FOCUS,
            self.items[0].completionDateTimeChangedEventType(),
        )
        # Bind value change for live status preview
        self._completionDateTimeCombo.Bind(widgets.EVT_VALUE_CHANGED, self._onLocalValueChanged)

        self.addEntry(
            _("Completion date"),
            self._completionDateTimeCombo.CreateRowPanel(self),
            wx.StaticText(self, label=""),
        )

    def addDateEntry(self, label, taskMethodName):
        """Add a date entry using the old DateTimeEntry control (for comparison)."""
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
        datetimeSync = attributesync.AttributeSync(
            taskMethodName,
            dateTimeEntry,
            dateTime,
            self.items,
            commandClass,
            entry.EVT_DATETIMEENTRY,
            eventType,
            commit_on_focus_loss=True,
        )
        setattr(self, "_%sSync" % taskMethodName, datetimeSync)
        self.addEntry(label, dateTimeEntry, flags=[wx.ALIGN_RIGHT, wx.EXPAND])

    def __populateDurationPresets(self):
        """Populate the duration presets dropdown from settings."""
        self._durationPresetsChoice.Clear()
        self._durationPresetsChoice.Append(_("Presets..."), None)  # Placeholder

        presets_str = self.__settings.get("feature", "sdtcspans")
        if not presets_str:
            self._durationPresetsChoice.SetSelection(0)
            return

        presets = []
        for minutes_str in presets_str.split(","):
            try:
                presets.append(int(minutes_str.strip()))
            except ValueError:
                pass

        for total_minutes in sorted(presets):
            label = self.__formatDurationPreset(total_minutes)
            self._durationPresetsChoice.Append(label, total_minutes)

        self._durationPresetsChoice.SetSelection(0)
        self.__updatePresetSelection()  # Match initial value

    def __updatePresetSelection(self):
        """Update preset dropdown to match current duration value."""
        if not hasattr(self, '_plannedDurationCtrl'):
            return

        # Get current duration in total minutes
        duration = self._plannedDurationCtrl.GetDuration()
        current_minutes = int(duration.total_seconds() // 60)

        # Search for matching preset
        for i in range(1, self._durationPresetsChoice.GetCount()):
            preset_minutes = self._durationPresetsChoice.GetClientData(i)
            if preset_minutes == current_minutes:
                self._durationPresetsChoice.SetSelection(i)
                return

        # No match - reset to placeholder
        self._durationPresetsChoice.SetSelection(0)

    def __formatDurationPreset(self, total_minutes):
        """Format minutes as a readable duration string."""
        days = total_minutes // (24 * 60)
        hours = (total_minutes % (24 * 60)) // 60
        minutes = total_minutes % 60

        parts = []
        if days > 0:
            if days == 1:
                parts.append(_("1 day"))
            elif days == 7:
                parts.append(_("1 week"))
            elif days % 7 == 0:
                weeks = days // 7
                parts.append(_("%d weeks") % weeks)
            else:
                parts.append(_("%d days") % days)
        if hours > 0:
            if hours == 1:
                parts.append(_("1 hour"))
            else:
                parts.append(_("%d hours") % hours)
        if minutes > 0:
            if minutes == 1:
                parts.append(_("1 minute"))
            else:
                parts.append(_("%d minutes") % minutes)

        if not parts:
            return _("0 minutes")
        elif len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            return _("%s and %s") % (parts[0], parts[1])
        else:
            return _("%s, %s and %s") % (parts[0], parts[1], parts[2])

    def __onPresetsConfigChanged(self, value=""):
        """Called when duration presets change in preferences."""
        self.__populateDurationPresets()

    def __onDurationPresetSelected(self, event):
        """Handle preset selection from dropdown."""
        selection = self._durationPresetsChoice.GetSelection()
        if selection <= 0:  # Placeholder selected
            return

        total_minutes = self._durationPresetsChoice.GetClientData(selection)
        if total_minutes is None:
            return

        # Convert to timedelta and set on the duration control
        import datetime
        days = total_minutes // (24 * 60)
        hours = (total_minutes % (24 * 60)) // 60
        minutes = total_minutes % 60

        self._plannedDurationCtrl.SetDuration(
            datetime.timedelta(days=days, hours=hours, minutes=minutes)
        )

        # Reset dropdown to placeholder
        self._durationPresetsChoice.SetSelection(0)

        # Trigger the duration changed handler
        self.__onPlannedDurationChangedInternal()

    def __onDurationModeChanged(self, event):
        """Handle mode dropdown change."""
        selection = self._durationModeChoice.GetSelection()
        new_mode = self._durationModeChoice.GetClientData(selection)

        if new_mode == self._currentPlannedDurationMode:
            return

        # Update enabled state for duration control and presets dropdown
        # In implicit mode: enabled/read-only state is set by __updateImplicitDuration
        # In other modes: enabled and editable
        if new_mode != "implicit":
            self._plannedDurationCtrl.Enable(True)
            self._plannedDurationCtrl.SetReadOnly(False)
        self._durationPresetsChoice.Enable(new_mode != "implicit")

        # Update enabled state for date fields based on mode
        # adjdue: due date is auto-calculated, so disable it
        # adjstart: planned start is auto-calculated, so disable it
        self._updateDateFieldsEnabled(new_mode)

        # Save mode change via command
        cmd = command.EditPlannedDurationModeCommand(
            items=self.items, newValue=new_mode
        )
        cmd.do()

        self._currentPlannedDurationMode = new_mode

        # Calculate the target field based on mode
        if new_mode == "implicit":
            self.__updateImplicitDuration()
        elif new_mode == "adjdue":
            self.__updateDueDateFromDuration()
        elif new_mode == "adjstart":
            self.__updatePlannedStartFromDuration()

    def _updateDateFieldsEnabled(self, mode):
        """Enable/disable date fields based on duration mode."""
        # In adjdue mode, due date is calculated automatically
        # In adjstart mode, planned start is calculated automatically
        self._dueDateTimeCombo.SetEditable(mode != "adjdue")
        self._plannedStartDateTimeCombo.SetEditable(mode != "adjstart")

    def __onPlannedDurationChanged(self, event):
        """Handle duration value change from the duration control."""
        self.__onPlannedDurationChangedInternal()
        event.Skip()  # Allow event to propagate to control's _onKillFocus

    def __onPlannedDurationChangedInternal(self):
        """Handle duration value change (called from event or preset selection)."""
        if self._currentPlannedDurationMode == "implicit":
            return  # Ignore changes in Implicit mode

        new_duration = self._plannedDurationCtrl.GetDuration()
        new_timedelta = date.TimeDelta(
            days=new_duration.days,
            seconds=new_duration.seconds
        )

        if new_timedelta == self._currentPlannedDuration:
            return

        # Save duration change via command
        cmd = command.EditPlannedDurationCommand(
            items=self.items, newValue=new_timedelta
        )
        cmd.do()

        self._currentPlannedDuration = new_timedelta

        # Adjust the target date based on mode
        if self._currentPlannedDurationMode == "adjdue":
            self.__updateDueDateFromDuration()
        elif self._currentPlannedDurationMode == "adjstart":
            self.__updatePlannedStartFromDuration()

    def __updateImplicitDuration(self):
        """Calculate and display duration from planned start and due date.

        Shows calculated duration if both dates are set.
        Shows N/A if one or both dates are missing.
        """
        import datetime as dt
        start = self._plannedStartDateTimeCombo.GetDateTime()
        due = self._dueDateTimeCombo.GetDateTime()

        if start is not None and due is not None:
            # Both dates present - show calculated duration (read-only)
            self._plannedDurationCtrl.Enable(True)
            self._plannedDurationCtrl.SetReadOnly(True)
            if due > start:
                duration = due - start
            else:
                duration = dt.timedelta()  # Zero or negative = show 0
            self._plannedDurationCtrl.SetDuration(duration)
            self.__updatePresetSelection()
        else:
            # One or both dates missing - show N/A (disabled)
            self._plannedDurationCtrl.Enable(False)
            self._plannedDurationCtrl.SetDuration(dt.timedelta())
            self.__updatePresetSelection()

    def __updateDueDateFromDuration(self):
        """Calculate due date from planned start + duration (adjdue mode)."""
        start = self._plannedStartDateTimeCombo.GetDateTime()
        if start is None:
            return  # No start date, can't calculate

        duration = self._plannedDurationCtrl.GetDuration()
        new_due = start + duration

        self._dueDateTimeCombo.SetDateTime(new_due)
        new_due_domain = date.DateTime.fromDateTime(new_due)
        self._currentDueDateTime = new_due_domain
        cmd = command.EditDueDateTimeCommand(items=self.items, newValue=new_due_domain)
        cmd.do()

    def __updatePlannedStartFromDuration(self):
        """Calculate planned start from due date - duration (adjstart mode)."""
        due = self._dueDateTimeCombo.GetDateTime()
        if due is None:
            return  # No due date, can't calculate

        duration = self._plannedDurationCtrl.GetDuration()
        new_start = due - duration

        self._plannedStartDateTimeCombo.SetDateTime(new_start)
        new_start_domain = date.DateTime.fromDateTime(new_start)
        self._currentPlannedStartDateTime = new_start_domain
        cmd = command.EditPlannedStartDateTimeCommand(items=self.items, newValue=new_start_domain)
        cmd.do()

    def addReminderEntry(self):
        """Add reminder entry using DateTimeCombo."""
        reminderDateTime = (
            self.items[0].reminder()
            if len(self.items) == 1
            else date.DateTime()
        )
        self._currentReminderDateTime = reminderDateTime

        # value=None means unchecked, value=datetime means checked
        value = reminderDateTime if reminderDateTime != date.DateTime() else None

        self._reminderDateTimeCombo = widgets.DateTimeCombo(
            self, value=value,
            hourChoices=lambda: get_suggested_hour_choices(self._DatesPage__settings),
            minuteChoices=lambda: get_suggested_minute_choices(self._DatesPage__settings)
        )
        # Use AttributeSync for automatic external update handling
        # Use EVT_KILL_FOCUS to sync on focus loss (same pattern as subject field)
        self._reminderDateTimeSync = attributesync.AttributeSync(
            "reminder",
            self._reminderDateTimeCombo,
            reminderDateTime,
            self.items,
            command.EditReminderDateTimeCommand,
            wx.EVT_KILL_FOCUS,
            self.items[0].reminderChangedEventType(),
            callback=self.__onReminderChanged,
        )

        self.addEntry(
            _("Reminder"),
            self._reminderDateTimeCombo.CreateRowPanel(self),
            wx.StaticText(self, label=""),
        )

    def __onReminderChanged(self, value):
        """AttributeSync callback for reminder date changes."""
        self._currentReminderDateTime = value

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
        # For DateTimeCombo controls, return the date control as the focusable widget
        return dict(
            firstEntry=self._plannedStartDateTimeCombo.GetDateCtrl(),
            plannedStartDateTime=self._plannedStartDateTimeCombo.GetDateCtrl(),
            dueDateTime=self._dueDateTimeCombo.GetDateCtrl(),
            actualStartDateTime=self._actualStartDateTimeCombo.GetDateCtrl(),
            completionDateTime=self._completionDateTimeCombo.GetDateCtrl(),
            timeLeft=self._dueDateTimeCombo.GetDateCtrl(),
            reminder=self._reminderDateTimeCombo.GetDateCtrl(),
            recurrence=self._recurrenceEntry,
        )

    def close(self):
        """Clean up resources when dialog closes."""
        # Unsubscribe from pubsub topics
        try:
            pub.unsubscribe(self.__onPresetsConfigChanged, "settings.feature.sdtcspans")
        except Exception:
            pass
        super().close()


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
                self._startClock()
        else:
            # We might need to keep tracking the clock if the user was tracking this
            # task with multiple effort records simultaneously
            if not self.items[0].isBeingTracked():
                self._stopClock()

    def _startClock(self):
        if not getattr(self, '_clockRunning', False):
            pub.subscribe(self._onTimerSecond, 'timer.second')
            self._clockRunning = True

    def _stopClock(self):
        if getattr(self, '_clockRunning', False):
            pub.unsubscribe(self._onTimerSecond, 'timer.second')
            self._clockRunning = False

    def _onTimerSecond(self, timestamp):
        """Handle second tick from global timer."""
        self.onEverySecond()

    def onEverySecond(self):
        taskDisplayed = self.items[0]
        self.onTimeSpentChanged(taskDisplayed.timeSpent(), taskDisplayed)
        self.onBudgetLeftChanged(taskDisplayed.budgetLeft(), taskDisplayed)
        self.onRevenueChanged(taskDisplayed.revenue(), taskDisplayed)

    def close(self):
        self._stopClock()
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
        # Track original category state for each item to support tri-state "no change"
        self.__originalCategories = {
            item: set(item.categories()) for item in items
        }
        super().__init__(*args, **kwargs)
        for item in self.domainObjectsToView():
            item.expand(context=self.settingsSection(), notify=False)

    def getIsItemChecked(self, category):  # pylint: disable=W0621
        items_with_category = sum(
            1 for item in self.__items if category in item.categories()
        )
        if items_with_category == 0:
            return False  # No items have category
        elif items_with_category == len(self.__items):
            return True  # All items have category
        else:
            return None  # Mixed state

    def onCheck(self, event, final):
        """Here we keep track of the items checked by the user so that these
        items remain checked when refreshing the viewer."""
        if final:
            category = self.widget.GetItemPyData(event.GetItem())
            command.ToggleCategoryCommand(
                None, self.__items, category=category
            ).do()

    def checkAllCategories(self):
        """Assign all categories to the items being edited."""
        for cat in self.presentation():
            for item in self.__items:
                if cat not in item.categories():
                    item.addCategory(cat)
        self.widget.refreshAllCheckStates()

    def uncheckAllCategories(self):
        """Remove all categories from the items being edited."""
        for cat in self.presentation():
            for item in self.__items:
                if cat in item.categories():
                    item.removeCategory(cat)
        self.widget.refreshAllCheckStates()

    def createActionToolBarUICommands(self):
        """UI commands for check/uncheck all in the edit task categories tab."""
        return (
            uicommand.CategoryCheckAll(viewer=self),
            uicommand.CategoryUncheckAll(viewer=self),
        )

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
        for item in self.items:
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

    def pasteItemCommand(self):
        """Paste attachments from clipboard to this task's attachments."""
        from taskcoachlib.command.clipboard import Clipboard
        items, source = Clipboard().get()
        copies = [item.copy() for item in items]
        return command.AddAttachmentCommand(
            None, [self.attachmentOwner], attachments=copies
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

    def _expandNoteAndChildren(self, aNote):
        """Recursively expand a note and all its children in this viewer."""
        context = self.settingsSection()
        aNote.expand(True, context=context, notify=False)
        for child in aNote.children():
            self._expandNoteAndChildren(child)

    def pasteItemCommand(self):
        """Paste notes from clipboard to this task's notes as top-level notes.

        Clears parent reference so notes always become top-level, even if
        copied from a nested location.
        """
        from taskcoachlib.command.clipboard import Clipboard
        items, source = Clipboard().get()
        copies = [item.copy() for item in items]
        # Clear parent so notes become top-level (even if source was nested)
        # and expand all pasted notes so children are visible
        for n in copies:
            n.setParent(None)
            self._expandNoteAndChildren(n)
        return command.AddNoteCommand(
            None, [self.__note_owner], notes=copies
        )

    def pasteAsSubItemCommand(self):
        """Paste notes as subnotes of the selected note.

        Uses AddSubNoteCommand which properly adds notes as children only,
        not to the owner's notes list (which would cause duplicates).
        """
        selected = self.curselection()
        if not selected:
            return None
        parent_note = selected[0]
        from taskcoachlib.command.clipboard import Clipboard
        items, source = Clipboard().get()
        copies = [item.copy() for item in items]
        # Clear parent references - AddSubNoteCommand will set correct parent via addChild
        # and expand all pasted notes so children are visible
        for n in copies:
            n.setParent(None)
            self._expandNoteAndChildren(n)
        # Also expand the parent note so the pasted subnotes are visible
        parent_note.expand(True, context=self.settingsSection(), notify=False)
        # Repeat parent_note for each copy so zip in AddSubNoteCommand pairs correctly
        parents = [parent_note] * len(copies)
        return command.AddSubNoteCommand(
            None, parents, owner=self.__note_owner, notes=copies
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


class PathPage(Page):
    """Page that displays the hierarchical path (nesting) of the current object.

    The path is built only when the tab is selected (lazy loading).
    It subscribes to ALL modification events to catch any change that might
    affect the path, and rebuilds when the tab is visible.
    """

    pageName = "path"
    pageTitle = _("Path")
    pageIcon = "arrow_down_right"
    columns = 1

    def __init__(self, items, parent, taskFile, *args, **kwargs):
        self._taskFile = taskFile
        self._pathPanel = None
        self._pathSizer = None
        self._subscribed = False
        self._realized = False
        super().__init__(items, parent, *args, **kwargs)

    def addEntries(self):
        """Create the container panel (content built lazily in selected())."""
        self._pathPanel = wx.Panel(self)
        self._pathSizer = wx.BoxSizer(wx.VERTICAL)
        self._pathPanel.SetSizer(self._pathSizer)
        self.addEntry(self._pathPanel, growable=True, flags=[wx.EXPAND])

    def selected(self):
        """Called when this tab is selected. Build/rebuild the path display."""
        if not self._realized:
            self._realized = True
            self._subscribeToChanges()
        self._rebuildPathDisplay()

    def _subscribeToChanges(self):
        """Subscribe to all modification events that could affect the path."""
        if self._subscribed:
            return
        self._subscribed = True

        from taskcoachlib.domain import task, category, note, attachment, effort

        # Subscribe to ALL modification event types from all domain classes
        # This is comprehensive and catches any change that could affect the path
        all_event_types = (
            task.Task.modificationEventTypes()
            + category.Category.modificationEventTypes()
            + note.Note.modificationEventTypes()
            + effort.Effort.modificationEventTypes()
            + attachment.FileAttachment.modificationEventTypes()
            + attachment.URIAttachment.modificationEventTypes()
            + attachment.MailAttachment.modificationEventTypes()
        )

        for eventType in all_event_types:
            if eventType.startswith("pubsub"):
                pub.subscribe(self._onAnyChange, eventType)
            else:
                patterns.Publisher().registerObserver(
                    self._onAnyChange,
                    eventType=eventType,
                )

    def _onAnyChange(self, *args, **kwargs):
        """Called when any domain object changes. Rebuild if visible."""
        if self._realized and self._pathPanel:
            try:
                if self._pathPanel.IsShownOnScreen():
                    wx.CallAfter(self._rebuildPathDisplay)
            except RuntimeError:
                pass  # Window destroyed

    def _rebuildPathDisplay(self):
        """Rebuild the path display."""
        if not self._pathPanel or not self._pathSizer:
            return
        try:
            self._pathPanel.GetName()  # Check if still valid
        except RuntimeError:
            return

        # Clear existing content
        self._pathSizer.Clear(True)

        # Only show path for single item
        if len(self.items) != 1:
            label = wx.StaticText(self._pathPanel,
                                  label=_("Path is only shown for single items"))
            self._pathSizer.Add(label, 0, wx.EXPAND)
            self._pathPanel.Layout()
            self._restoreFocus()
            return

        item = self.items[0]
        path_objects = self._buildPathObjects(item)

        if not path_objects:
            label = wx.StaticText(self._pathPanel,
                                  label=_("This item has no parent objects"))
            self._pathSizer.Add(label, 0, wx.EXPAND)
            self._pathPanel.Layout()
            self._restoreFocus()
            return

        # Display path from root to current item
        for index, obj in enumerate(path_objects):
            obj_type, icon_name = self._getTypeInfo(obj)
            subject = obj.subject()

            item_panel = wx.Panel(self._pathPanel)
            item_sizer = wx.BoxSizer(wx.HORIZONTAL)

            # Add indentation based on depth
            if index > 0:
                indent = wx.Panel(item_panel, size=(index * 20, 1))
                item_sizer.Add(indent, 0)
                # Add arrow icon to show hierarchy
                arrow_bitmap = wx.ArtProvider.GetBitmap(
                    "arrow_down_right", wx.ART_MENU, (16, 16)
                )
                if arrow_bitmap.IsOk():
                    arrow = wx.StaticBitmap(item_panel, bitmap=arrow_bitmap)
                    item_sizer.Add(arrow, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

            # Add type icon if available
            if icon_name:
                bitmap = wx.ArtProvider.GetBitmap(icon_name, wx.ART_MENU, (16, 16))
                if bitmap.IsOk():
                    icon = wx.StaticBitmap(item_panel, bitmap=bitmap)
                    item_sizer.Add(icon, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

            # Add type and subject label using [Type] Subject format
            label_text = "[%s] %s" % (obj_type, subject)
            label = wx.StaticText(item_panel, label=label_text)

            # Make current item bold
            if index == len(path_objects) - 1:
                font = label.GetFont()
                font.SetWeight(wx.FONTWEIGHT_BOLD)
                label.SetFont(font)

            item_sizer.Add(label, 1, wx.ALIGN_CENTER_VERTICAL)
            item_panel.SetSizer(item_sizer)
            self._pathSizer.Add(item_panel, 0, wx.EXPAND | wx.ALL, 2)

        self._pathPanel.Layout()
        self.Layout()
        self._restoreFocus()

    def _restoreFocus(self):
        """Restore focus to the path panel after rebuild.

        This is critical because rebuilding destroys all child widgets,
        which destroys focus. Without restoring focus, keyboard shortcuts
        like Escape to close the dialog won't work.
        """
        try:
            self._pathPanel.SetFocus()
        except RuntimeError:
            pass

    def _buildPathObjects(self, item):
        """Build the path from root to current item.

        Returns a list of actual objects for display.
        """
        path = []

        # Find owner for notes and attachments
        owner = self._findOwner(item)
        if owner:
            owner_path = self._buildPathObjects(owner)
            path.extend(owner_path)

        # Add ancestors for composite objects
        if hasattr(item, 'ancestors'):
            path.extend(item.ancestors())

        # Add current item
        path.append(item)
        return path

    def close(self):
        """Clean up observers when the page is closed."""
        if self._subscribed:
            from taskcoachlib.domain import task, category, note, attachment, effort
            all_event_types = (
                task.Task.modificationEventTypes()
                + category.Category.modificationEventTypes()
                + note.Note.modificationEventTypes()
                + effort.Effort.modificationEventTypes()
                + attachment.FileAttachment.modificationEventTypes()
                + attachment.URIAttachment.modificationEventTypes()
                + attachment.MailAttachment.modificationEventTypes()
            )
            for eventType in all_event_types:
                if eventType.startswith("pubsub"):
                    try:
                        pub.unsubscribe(self._onAnyChange, eventType)
                    except Exception:
                        pass
            patterns.Publisher().removeObserver(self._onAnyChange)
        super().close()

    def _getTypeInfo(self, obj):
        """Get the type name and icon for an object."""
        from taskcoachlib.domain import task as task_module
        from taskcoachlib.domain import category, note, attachment, effort

        if isinstance(obj, task_module.Task):
            return (_("Task"), obj.icon(recursive=True) or "led_blue_icon")
        elif isinstance(obj, category.Category):
            return (_("Category"), obj.icon(recursive=True) or "folder_blue_icon")
        elif isinstance(obj, note.Note):
            return (_("Note"), obj.icon(recursive=True) or "note_icon")
        elif isinstance(obj, attachment.Attachment):
            return (_("Attachment"), "paperclip_icon")
        elif isinstance(obj, effort.Effort):
            return (_("Effort"), "clock_icon")
        else:
            return (_("Item"), None)

    def _findOwner(self, item):
        """Find the immediate owner of a note or attachment.

        Notes can be owned by: tasks, categories, attachments, or other notes (parent)
        Attachments can be owned by: tasks, categories, or notes
        Efforts are owned by their task

        For notes with a parent note, returns None (ancestors() handles the hierarchy).
        For root-level notes, finds the task/category/attachment that owns it.
        """
        from taskcoachlib.domain import note, attachment, effort

        # Efforts have a task() method that returns their owner
        if isinstance(item, effort.Effort):
            return item.task()

        if not isinstance(item, (note.Note, attachment.Attachment)):
            return None

        # For notes with a parent note, the parent relationship is handled by ancestors()
        # But we still need to find the owner of the ROOT note in the hierarchy
        if isinstance(item, note.Note) and item.parent():
            # Get the root note (the one without a parent)
            root_note = item
            while root_note.parent():
                root_note = root_note.parent()
            # Find owner of root note
            return self._findNoteOwner(root_note)

        # For root-level notes
        if isinstance(item, note.Note):
            return self._findNoteOwner(item)

        # For attachments
        return self._findAttachmentOwner(item)

    def _findNoteOwner(self, target_note):
        """Find the owner of a root-level note (task, category, or attachment)."""
        # Check tasks
        for t in self._taskFile.tasks():
            if target_note in t.notes(recursive=False):
                return t

        # Check categories
        for c in self._taskFile.categories():
            if target_note in c.notes(recursive=False):
                return c

        # Check all attachments (they can own notes too)
        # This requires searching through all attachments in the system
        owner = self._findNoteOwnerInAttachments(target_note)
        if owner:
            return owner

        return None

    def _findNoteOwnerInAttachments(self, target_note):
        """Search for a note's owner among all attachments in the system."""
        # We need to search ALL attachments, including deeply nested ones
        # Attachments can be owned by tasks, categories, notes, and notes owned by attachments...

        visited = set()
        attachments_to_check = []

        # Collect all "root" attachments from tasks and categories
        for t in self._taskFile.tasks():
            attachments_to_check.extend(t.attachments())
        for c in self._taskFile.categories():
            attachments_to_check.extend(c.attachments())

        # Also from global notes and their children
        for n in self._taskFile.notes():
            attachments_to_check.extend(n.attachments())
            for child in n.children(recursive=True):
                attachments_to_check.extend(child.attachments())

        # From task notes
        for t in self._taskFile.tasks():
            for n in t.notes(recursive=True):
                attachments_to_check.extend(n.attachments())

        # From category notes
        for c in self._taskFile.categories():
            for n in c.notes(recursive=True):
                attachments_to_check.extend(n.attachments())

        # Now search through all attachments, including their nested notes' attachments
        while attachments_to_check:
            att = attachments_to_check.pop()
            att_id = att.id()
            if att_id in visited:
                continue
            visited.add(att_id)

            # Check if this attachment owns our target note
            if hasattr(att, 'notes'):
                if target_note in att.notes(recursive=False):
                    return att
                # Add attachments from this attachment's notes to search
                for n in att.notes(recursive=True):
                    attachments_to_check.extend(n.attachments())

        return None

    def _findAttachmentOwner(self, target_attachment):
        """Find the owner of an attachment (task, category, or note)."""
        # Check tasks
        for t in self._taskFile.tasks():
            if target_attachment in t.attachments():
                return t

        # Check categories
        for c in self._taskFile.categories():
            if target_attachment in c.attachments():
                return c

        # Check all notes (including deeply nested ones)
        owner = self._findAttachmentOwnerInNotes(target_attachment)
        if owner:
            return owner

        return None

    def _findAttachmentOwnerInNotes(self, target_attachment):
        """Search for an attachment's owner among all notes in the system."""
        visited = set()
        notes_to_check = []

        # Collect all "root" notes from tasks and categories
        for t in self._taskFile.tasks():
            notes_to_check.extend(t.notes(recursive=True))
        for c in self._taskFile.categories():
            notes_to_check.extend(c.notes(recursive=True))

        # Global notes
        for n in self._taskFile.notes():
            notes_to_check.append(n)
            notes_to_check.extend(n.children(recursive=True))

        # Now we also need to check notes owned by attachments
        # First, collect all attachments from tasks, categories, and notes
        attachments_checked = set()
        attachments_to_check = []
        for t in self._taskFile.tasks():
            attachments_to_check.extend(t.attachments())
        for c in self._taskFile.categories():
            attachments_to_check.extend(c.attachments())
        # Also from global notes
        for n in self._taskFile.notes():
            attachments_to_check.extend(n.attachments())
            for child in n.children(recursive=True):
                attachments_to_check.extend(child.attachments())

        # Search notes, and also add notes from attachments
        while notes_to_check or attachments_to_check:
            # Process notes
            while notes_to_check:
                n = notes_to_check.pop()
                note_id = n.id()
                if note_id in visited:
                    continue
                visited.add(note_id)

                # Check if this note owns our target attachment
                if target_attachment in n.attachments():
                    return n

                # Add this note's attachments to check for more notes
                for att in n.attachments():
                    if att.id() not in attachments_checked:
                        attachments_to_check.append(att)

            # Process attachments to find more notes
            while attachments_to_check:
                att = attachments_to_check.pop()
                att_id = att.id()
                if att_id in attachments_checked:
                    continue
                attachments_checked.add(att_id)

                # Add notes from this attachment
                if hasattr(att, 'notes'):
                    for n in att.notes(recursive=True):
                        if n.id() not in visited:
                            notes_to_check.append(n)

        return None

    def entries(self):
        return dict(firstEntry=self, path=self)


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
            "categories",
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
        elif page_name == "path":
            return PathPage(self.items, self, task_file)

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
        "path",
    ]
    domainObject = "task"

    def create_subject_page(self):
        return TaskSubjectPage(self.items, self, self.settings)


class CategoryEditBook(EditBook):
    allPageNames = ["subject", "notes", "attachments", "appearance", "path"]
    domainObject = "category"

    def create_subject_page(self):
        return CategorySubjectPage(self.items, self, self.settings)


class NoteEditBook(EditBook):
    allPageNames = ["subject", "categories", "attachments", "appearance", "path"]
    domainObject = "note"


class AttachmentEditBook(EditBook):
    allPageNames = ["subject", "notes", "appearance", "path"]
    domainObject = "attachment"

    def create_subject_page(self):
        return AttachmentSubjectPage(self.items, self, self.settings)

    def isDisplayingItemOrChildOfItem(self, targetItem):
        return targetItem in self.items


class NullableDateTimeWrapper:
    """Virtual wrapper linking a checkbox with a DateTimeEntry.

    GetValue returns None when checkbox is unchecked, otherwise returns
    the datetime value. The checkbox and datetime entry remain separate
    widgets for grid layout, but this wrapper provides unified GetValue.
    """

    def __init__(self, checkbox, datetime_entry):
        self._checkbox = checkbox
        self._datetime_entry = datetime_entry

    def GetValue(self):
        """Return None if checkbox unchecked, else datetime value."""
        try:
            if not self._checkbox.GetValue():
                return None
            return self._datetime_entry.GetValue()
        except RuntimeError:
            return None  # Widget already deleted (dialog closed)

    def SetValue(self, value):
        """Set value - None unchecks checkbox, otherwise sets datetime."""
        try:
            if value is None:
                self._checkbox.SetValue(False)
                self._datetime_entry.Enable(False)
            else:
                self._checkbox.SetValue(True)
                self._datetime_entry.Enable(True)
                self._datetime_entry.SetValue(value)
        except RuntimeError:
            pass  # Widget already deleted (dialog closed)

    def Bind(self, event_type, handler, source=None, id=wx.ID_ANY, id2=wx.ID_ANY):
        """Forward bind to datetime entry."""
        self._datetime_entry.Bind(event_type, handler, source, id, id2)

    def LoadChoices(self, choices):
        """Forward to datetime entry."""
        self._datetime_entry.LoadChoices(choices)

    def SetRelativeChoicesStart(self, start=None):
        """Forward to datetime entry."""
        self._datetime_entry.SetRelativeChoicesStart(start)

    def GetChildren(self):
        """Return children for focus tracking."""
        return self._datetime_entry.GetChildren()

    def SetFocus(self):
        """Forward focus to datetime entry."""
        self._datetime_entry.SetFocus()

    def Enable(self, enable=True):
        """Enable/disable the datetime entry."""
        self._datetime_entry.Enable(enable)
        return True

    def GetId(self):
        """Return ID of datetime entry for widget validity checks."""
        return self._datetime_entry.GetId()


class EffortEditBook(Page):
    domainObject = "effort"
    columns = 3  # Label, DateTime row, Button/Rest (matches DatesPage)

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
        self._updatingControls = False  # Guard flag to prevent infinite loops
        super().__init__(efforts, parent, *args, **kwargs)

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

    def __add_start_and_stop_entries(self):
        # pylint: disable=W0201
        # Using 3 columns: Label, DateTime row, Button/Rest (matches DatesPage)

        # Entry mode tracking (dropdown created in Duration row)
        self._effortEntryMode = 0  # 0=Standard, 1=Retroactive

        # --- Start row: Label, DateTime row (checkbox hidden), Button ---
        current_start_date_time = self.items[0].getStart()
        self._startDateTimeCombo = widgets.DateTimeCombo(
            self,
            value=current_start_date_time,
            showSeconds=True,
            hourChoices=lambda: get_suggested_hour_choices(self._settings),
            minuteChoices=lambda: get_suggested_minute_choices(self._settings),
            secondChoices=lambda: get_suggested_second_choices(self._settings),
        )
        # Hide checkbox - start is always required
        self._startDateTimeCombo.GetCheckBox().Hide()

        self._startDateTimeSync = attributesync.AttributeSync(
            "getStart",
            self._startDateTimeCombo,
            current_start_date_time,
            self.items,
            command.EditEffortStartDateTimeCommand,
            wx.EVT_KILL_FOCUS,
            self.items[0].startChangedEventType(),
            callback=self.__onEffortStartChanged,
        )
        self._startDateTimeCombo.Bind(widgets.EVT_VALUE_CHANGED, self.__onStartValueChanged)

        self._startFromLastEffortButton = self.__create_start_from_last_effort_button()

        self.addEntry(
            _("Start"),
            self._startDateTimeCombo.CreateRowPanel(self),
            self._startFromLastEffortButton,
            flags=[None, None, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.ALL],
        )

        # --- Duration row ---
        current_stop_date_time = self.items[0].getStop()
        if current_stop_date_time is not None:
            duration = current_stop_date_time - current_start_date_time
            total_seconds = int(duration.total_seconds())
        else:
            total_seconds = 0

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        self._effortDurationCtrl = widgets.MaskedDurationCtrl(
            self,
            days=0, hours=hours, minutes=minutes, seconds=seconds,
            dayChoices=None,
            hourChoices=list(range(24)),
            minuteChoices=lambda: get_suggested_minute_choices(self._settings),
            showSeconds=True,
            secondChoices=lambda: get_suggested_second_choices(self._settings),
        )
        if current_stop_date_time is None:
            self._effortDurationCtrl.Enable(False)
        self._effortDurationCtrl.Bind(widgets.EVT_VALUE_CHANGED, self.__onDurationValueChanged)
        self._effortDurationCtrl.Bind(wx.EVT_KILL_FOCUS, self.__onDurationKillFocus)

        self._effortDurationPresetsChoice = wx.Choice(self)
        self.__populateEffortDurationPresets()
        self._effortDurationPresetsChoice.Bind(wx.EVT_CHOICE, self.__onEffortDurationPresetSelected)
        if current_stop_date_time is None:
            self._effortDurationPresetsChoice.Enable(False)

        pub.subscribe(self.__onEffortPresetsConfigChanged, "settings.feature.sdtcspans_effort")

        # Entry mode dropdown (Standard / Retroactive) - placed next to presets
        self._effortEntryModeChoice = wx.Choice(self, choices=[_("Standard"), _("Retroactive")])
        self._effortEntryModeChoice.SetSelection(0)
        self._effortEntryModeChoice.Bind(wx.EVT_CHOICE, self.__onEffortEntryModeChanged)

        # Create panel with presets and entry mode dropdowns
        presetsAndModePanel = wx.Panel(self)
        presetsAndModeSizer = wx.BoxSizer(wx.HORIZONTAL)
        self._effortDurationPresetsChoice.Reparent(presetsAndModePanel)
        self._effortEntryModeChoice.Reparent(presetsAndModePanel)
        presetsAndModeSizer.Add(self._effortDurationPresetsChoice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        presetsAndModeSizer.Add(self._effortEntryModeChoice, 0, wx.ALIGN_CENTER_VERTICAL)
        presetsAndModePanel.SetSizer(presetsAndModeSizer)

        # Duration row: label, duration, presets+mode (left-aligned)
        self.addEntry(
            _("Duration"),
            self._effortDurationCtrl,
            presetsAndModePanel,
            flags=[None, None, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.ALL],
        )

        # --- Stop row: Label, DateTime row (with checkbox), Button ---
        self._stopDateTimeCombo = widgets.DateTimeCombo(
            self,
            value=current_stop_date_time,
            showSeconds=True,
            hourChoices=lambda: get_suggested_hour_choices(self._settings),
            minuteChoices=lambda: get_suggested_minute_choices(self._settings),
            secondChoices=lambda: get_suggested_second_choices(self._settings),
        )

        self._stopDateTimeSync = attributesync.AttributeSync(
            "getStop",
            self._stopDateTimeCombo,
            current_stop_date_time,
            self.items,
            command.EditEffortStopDateTimeCommand,
            wx.EVT_KILL_FOCUS,
            self.items[0].stopChangedEventType(),
            callback=self.__onEffortStopChanged,
        )
        self._stopDateTimeCombo.Bind(widgets.EVT_VALUE_CHANGED, self.__onStopValueChanged)
        self._stopDateTimeCombo.GetCheckBox().Bind(wx.EVT_CHECKBOX, self.__onStopCheckboxChanged)

        self._stopNowButton = self.__create_stop_now_button()

        self.addEntry(
            _("Stop"),
            self._stopDateTimeCombo.CreateRowPanel(self),
            self._stopNowButton,
            flags=[None, None, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.ALL],
        )

        # --- Warning message ---
        self._invalidPeriodMessage = self.__create_invalid_period_message()
        self.addEntry(
            self._invalidPeriodMessage,
            flags=[wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND]
        )

    def __onEffortStartChanged(self, value):
        """Called when start datetime is committed - update duration."""
        if self._updatingControls:
            return
        self._updatingControls = True
        try:
            self.__syncDurationFromStartStop()
        finally:
            self._updatingControls = False

    def __onEffortStopChanged(self, value):
        """Called when stop datetime is committed - update duration."""
        if self._updatingControls:
            return
        self._updatingControls = True
        try:
            self.__syncDurationFromStartStop()
        finally:
            self._updatingControls = False

    def __onStartValueChanged(self, event):
        """Called when start value changes (live) - update duration display."""
        if self._updatingControls:
            event.Skip()
            return
        self._updatingControls = True
        try:
            self.__syncDurationFromStartStop()
            self.__update_invalid_period_message()
        finally:
            self._updatingControls = False
        event.Skip()

    def __onStopValueChanged(self, event):
        """Called when stop value changes (live) - update duration or start based on mode."""
        if self._updatingControls:
            event.Skip()
            return
        self._updatingControls = True
        try:
            if self._effortEntryMode == 1:  # Retroactive mode
                # Calculate Start = Stop - Duration
                self.__syncStartFromStopDuration()
            else:  # Standard mode
                # Calculate Duration = Stop - Start
                self.__syncDurationFromStartStop()
            self.__update_invalid_period_message()
        finally:
            self._updatingControls = False
        event.Skip()

    def __onDurationValueChanged(self, event):
        """Called when duration is edited - update stop or start time based on mode."""
        if self._updatingControls:
            event.Skip()
            return
        if not self._stopDateTimeCombo.IsChecked():
            event.Skip()
            return

        self._updatingControls = True
        try:
            duration = self._effortDurationCtrl.GetTimeDelta()

            if self._effortEntryMode == 1:  # Retroactive mode
                # Calculate Start = Stop - Duration
                stop = self._stopDateTimeCombo.GetDateTime()
                if stop and duration:
                    new_start = stop - duration
                    self._startDateTimeCombo.SetDateTime(new_start)
                    command.EditEffortStartDateTimeCommand(
                        None, self.items, newValue=date.DateTime.fromDateTime(new_start)
                    ).do()
            else:  # Standard mode
                # Calculate Stop = Start + Duration
                start = self._startDateTimeCombo.GetDateTime()
                if start:
                    new_stop = start + duration
                    self._stopDateTimeCombo.SetDateTime(new_stop)

            self.__updateEffortPresetSelection()
            self.__update_invalid_period_message()
        finally:
            self._updatingControls = False
        event.Skip()

    def __onDurationKillFocus(self, event):
        """Commit duration changes when focus is lost - syncs with other windows."""
        event.Skip()
        if self._updatingControls:
            return
        if not self._stopDateTimeCombo.IsChecked():
            return

        self._updatingControls = True
        try:
            if self._effortEntryMode == 1:  # Retroactive mode
                # Commit start time change
                command.EditEffortStartDateTimeCommand(
                    None, self.items, newValue=self._startDateTimeCombo.GetValue()
                ).do()
            else:  # Standard mode
                # Commit stop time change
                command.EditEffortStopDateTimeCommand(
                    None, self.items, newValue=self._stopDateTimeCombo.GetValue()
                ).do()
        finally:
            self._updatingControls = False

    def __onStopCheckboxChanged(self, event):
        """Handle stop checkbox toggle."""
        if self._updatingControls:
            event.Skip()
            return
        self._updatingControls = True
        try:
            if self._stopDateTimeCombo.IsChecked():
                # Enabling stop - set to now and enable duration
                now = date.DateTime.now()
                start = self._startDateTimeCombo.GetDateTime()
                new_stop = start if start > now else now
                self._stopDateTimeCombo.SetDateTime(new_stop)
                self._effortDurationCtrl.Enable(True)
                self._effortDurationPresetsChoice.Enable(True)

                if self._effortEntryMode == 1:  # Retroactive mode
                    # Calculate start from stop - duration
                    self.__syncStartFromStopDuration()
                else:
                    # Standard mode - sync duration
                    self.__syncDurationFromStartStop()

                # Commit the change
                command.EditEffortStopDateTimeCommand(
                    None, self.items, newValue=self._stopDateTimeCombo.GetValue()
                ).do()
            else:
                # Disabling stop - resume tracking
                self._effortDurationCtrl.Enable(False)
                self._effortDurationPresetsChoice.Enable(False)
                self._effortDurationCtrl.SetDuration(date.TimeDelta(), quiet=True)
                for item in self.items:
                    item.setStop(date.DateTime.max)
            self.__update_invalid_period_message()
        finally:
            self._updatingControls = False
        event.Skip()

    def __onEffortEntryModeChanged(self, event):
        """Handle switching between Standard and Retroactive entry modes."""
        if self._updatingControls:
            return
        self._updatingControls = True
        try:
            self._effortEntryMode = self._effortEntryModeChoice.GetSelection()
            self.__applyEffortEntryMode()
        finally:
            self._updatingControls = False

    def __applyEffortEntryMode(self):
        """Apply the current entry mode to control states and recalculate values.

        Standard mode: Start is editable, Duration/Stop update each other
        Retroactive mode: Start is read-only (calculated from Stop - Duration)
                         If stop is unchecked, start remains as-is
        """
        is_retroactive = self._effortEntryMode == 1

        if is_retroactive:
            # Retroactive mode: Start is calculated (read-only)
            self._startDateTimeCombo.SetEditable(False)
            self._startFromLastEffortButton.Enable(False)

            # Calculate start only if stop is active
            if self._stopDateTimeCombo.IsChecked():
                self.__syncStartFromStopDuration()
        else:
            # Standard mode: Start is editable
            self._startDateTimeCombo.SetEditable(True)
            self._startFromLastEffortButton.Enable(
                self._effortList.maxDateTime() is not None
            )

            # Sync duration from start/stop
            self.__syncDurationFromStartStop()

    def __syncStartFromStopDuration(self):
        """In Retroactive mode: Calculate Start = Stop - Duration."""
        if self._effortEntryMode != 1:  # Only in retroactive mode
            return

        stop = self._stopDateTimeCombo.GetDateTime()
        duration = self._effortDurationCtrl.GetTimeDelta()

        if stop and duration:
            new_start = stop - duration
            self._startDateTimeCombo.SetDateTime(new_start)
            # Commit the start change
            command.EditEffortStartDateTimeCommand(
                None, self.items, newValue=date.DateTime.fromDateTime(new_start)
            ).do()
            self.__updateEffortPresetSelection()
            self.__update_invalid_period_message()

    def __syncDurationFromStartStop(self):
        """Sync duration display from current start and stop values (no event firing)."""
        if not self._stopDateTimeCombo.IsChecked():
            return

        start = self._startDateTimeCombo.GetDateTime()
        stop = self._stopDateTimeCombo.GetDateTime()

        if start and stop:
            duration = stop - start
            total_seconds = max(0, int(duration.total_seconds()))
            self._effortDurationCtrl.SetDuration(datetime.timedelta(seconds=total_seconds), quiet=True)
            self.__updateEffortPresetSelection()

    def __populateEffortDurationPresets(self):
        """Populate the effort duration presets dropdown from settings."""
        self._effortDurationPresetsChoice.Clear()
        self._effortDurationPresetsChoice.Append(_("Presets..."), None)  # Placeholder

        presets_str = self._settings.get("feature", "sdtcspans_effort")
        if not presets_str:
            self._effortDurationPresetsChoice.SetSelection(0)
            return

        presets = []
        for seconds_str in presets_str.split(","):
            try:
                presets.append(int(seconds_str.strip()))
            except ValueError:
                pass

        for total_seconds in sorted(presets):
            label = self.__formatEffortDurationPreset(total_seconds)
            self._effortDurationPresetsChoice.Append(label, total_seconds)

        self._effortDurationPresetsChoice.SetSelection(0)
        self.__updateEffortPresetSelection()

    def __formatEffortDurationPreset(self, total_seconds):
        """Format seconds as a readable duration string for effort presets."""
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        if hours > 0:
            if hours == 1:
                parts.append(_("1 hour"))
            else:
                parts.append(_("%d hours") % hours)
        if minutes > 0:
            if minutes == 1:
                parts.append(_("1 min"))
            else:
                parts.append(_("%d mins") % minutes)
        if seconds > 0:
            if seconds == 1:
                parts.append(_("1 sec"))
            else:
                parts.append(_("%d secs") % seconds)

        if not parts:
            return _("0 secs")
        return " ".join(parts)

    def __updateEffortPresetSelection(self):
        """Update preset dropdown to match current duration value."""
        if not hasattr(self, '_effortDurationCtrl'):
            return

        duration = self._effortDurationCtrl.GetDuration()
        current_seconds = int(duration.total_seconds())

        for i in range(1, self._effortDurationPresetsChoice.GetCount()):
            preset_seconds = self._effortDurationPresetsChoice.GetClientData(i)
            if preset_seconds == current_seconds:
                self._effortDurationPresetsChoice.SetSelection(i)
                return

        self._effortDurationPresetsChoice.SetSelection(0)

    def __onEffortDurationPresetSelected(self, event):
        """Handle selection of a duration preset."""
        if self._updatingControls:
            return
        idx = self._effortDurationPresetsChoice.GetSelection()
        if idx <= 0:
            return

        total_seconds = self._effortDurationPresetsChoice.GetClientData(idx)
        if total_seconds is None:
            return

        self._updatingControls = True
        try:
            # Update duration control
            self._effortDurationCtrl.SetDuration(datetime.timedelta(seconds=total_seconds), quiet=True)

            if self._effortEntryMode == 1:  # Retroactive mode
                # Calculate Start = Stop - Duration
                stop = self._stopDateTimeCombo.GetDateTime()
                if stop:
                    new_start = stop - datetime.timedelta(seconds=total_seconds)
                    self._startDateTimeCombo.SetDateTime(new_start)
                    # Commit the start change
                    command.EditEffortStartDateTimeCommand(
                        None, self.items, newValue=date.DateTime.fromDateTime(new_start)
                    ).do()
                    self.__update_invalid_period_message()
            else:  # Standard mode
                # Calculate Stop = Start + Duration
                start = self._startDateTimeCombo.GetDateTime()
                if start:
                    new_stop = start + datetime.timedelta(seconds=total_seconds)
                    self._stopDateTimeCombo.SetDateTime(new_stop)
                    self._stopDateTimeCombo.SetChecked(True)
                    self._effortDurationCtrl.Enable(True)
                    self._effortDurationPresetsChoice.Enable(True)
                    # Commit the stop change
                    command.EditEffortStopDateTimeCommand(
                        None, self.items, newValue=date.DateTime.fromDateTime(new_stop)
                    ).do()
                    self.__update_invalid_period_message()
        finally:
            self._updatingControls = False

    def __onEffortPresetsConfigChanged(self):
        """Handle changes to effort preset configuration."""
        self.__populateEffortDurationPresets()

    def __create_start_from_last_effort_button(self, parent=None):
        if parent is None:
            parent = self
        button = wx.Button(parent, label=_("Start tracking from last stop time"))
        self.Bind(wx.EVT_BUTTON, self.onStartFromLastEffort, button)
        if self._effortList.maxDateTime() is None:
            button.Disable()
        return button

    def __create_stop_now_button(self, parent=None):
        if parent is None:
            parent = self
        button = wx.Button(parent, label=_("Stop tracking now"))
        self.Bind(wx.EVT_BUTTON, self.onStopNow, button)
        return button

    def __create_invalid_period_message(self):
        text = wx.StaticText(self, label="")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        text.SetFont(font)
        return text

    def onStartFromLastEffort(self, event):  # pylint: disable=W0613
        self._updatingControls = True
        try:
            maxDateTime = self._effortList.maxDateTime()
            if self._startDateTimeCombo.GetValue() != maxDateTime:
                self._startDateTimeCombo.SetDateTime(maxDateTime)
                self._startDateTimeSync.onAttributeEdited(event)
            self.__syncDurationFromStartStop()
            self.__update_invalid_period_message()
        finally:
            self._updatingControls = False

    def onStopNow(self, event):
        # Stop only the specific effort(s) being edited, not all efforts for the task
        self._updatingControls = True
        try:
            new_value = date.DateTime.now()
            self._stopDateTimeCombo.SetChecked(True)
            self._stopDateTimeCombo.SetDateTime(new_value)
            self._effortDurationCtrl.Enable(True)
            self._effortDurationPresetsChoice.Enable(True)
            self.__syncDurationFromStartStop()
            command.EditEffortStopDateTimeCommand(
                None, self.items, newValue=new_value
            ).do()
            self.__update_invalid_period_message()
        finally:
            self._updatingControls = False

    def onStopDateTimeChanged(self, *args, **kwargs):
        self.onDateTimeChanged(*args, **kwargs)

    def __onStopDateTimeChanged(self, new_value):
        # The actual start date/time was not changed (the command class checks that) if
        # if was greater than the stop date/time then, so make sure it is if everything is
        # OK now.
        command.EditEffortStartDateTimeCommand(
            None, self.items, newValue=self._startDateTimeCombo.GetValue()
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
            if not self._stopDateTimeCombo.IsChecked():
                return True  # No stop time means effort is ongoing
            stop_value = self._stopDateTimeCombo.GetValue()
            if stop_value is None:
                return True
            return self._startDateTimeCombo.GetValue() < stop_value
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
        # Description text box spans full width - label not needed as purpose is obvious
        self.addEntry(
            self._descriptionEntry,
            flags=[wx.ALL | wx.EXPAND],
            growable=True
        )

    def setFocus(self, column_name):
        self.setFocusOnEntry(column_name)

    def isDisplayingItemOrChildOfItem(self, item):
        if hasattr(item, "setTask"):
            return self.items[0] == item  # Regular effort
        else:
            return item.mayContain(self.items[0])  # Composite effort

    def entries(self):
        return dict(
            firstEntry=self._startDateTimeCombo,
            task=self._taskEntry,
            period=self._stopDateTimeCombo,
            description=self._descriptionEntry,
            timeSpent=self._stopDateTimeCombo,
            revenue=self._taskEntry,
        )

    def close_edit_book(self):
        """Cleanup method called when dialog closes."""
        try:
            pub.unsubscribe(self.__onEffortPresetsConfigChanged, "settings.feature.sdtcspans_effort")
        except Exception:
            pass


class Editor(BalloonTipManager, widgets.Dialog):
    EditBookClass = lambda *args: "Subclass responsibility"
    singular_title = "Subclass responsibility %s"
    plural_title = "Subclass responsibility"
    item_type_plural = "Items"

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
        self.__next_tab_id = IdProvider.get()
        self.__prev_tab_id = IdProvider.get()
        table = wx.AcceleratorTable(
            [
                (wx.ACCEL_CMD, ord("Z"), wx.ID_UNDO),
                (wx.ACCEL_CMD, ord("Y"), wx.ID_REDO),
                (wx.ACCEL_CMD, ord("E"), self.__new_effort_id),
                (wx.ACCEL_CTRL, wx.WXK_TAB, self.__next_tab_id),
                (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, wx.WXK_TAB, self.__prev_tab_id),
            ]
        )
        self._interior.SetAcceleratorTable(table)
        # Bind tab navigation commands
        self._interior.Bind(wx.EVT_MENU, self.__on_next_tab, id=self.__next_tab_id)
        self._interior.Bind(wx.EVT_MENU, self.__on_prev_tab, id=self.__prev_tab_id)
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

    def __on_next_tab(self, event):
        """Handle Ctrl+Tab to move to next tab."""
        self._interior.AdvanceSelectionForward()

    def __on_prev_tab(self, event):
        """Handle Ctrl+Shift+Tab to move to previous tab."""
        self._interior.AdvanceSelectionBackward()

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
            self.__timer.Stop()
            IdProvider.put(self.__timer.GetId())
        IdProvider.put(self.__new_effort_id)
        IdProvider.put(self.__next_tab_id)
        IdProvider.put(self.__prev_tab_id)
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
        if len(self._items) > 1:
            # Indicate modal window for multi-item editing
            return _("Editing Multiple %s - Modal Window") % self.item_type_plural
        else:
            return self.singular_title % self._items[0].subject()


class TaskEditor(Editor):
    plural_title = _("Multiple tasks")
    singular_title = _("%s (Task)")
    item_type_plural = _("Tasks")
    EditBookClass = TaskEditBook


class CategoryEditor(Editor):
    plural_title = _("Multiple categories")
    singular_title = _("%s (Category)")
    item_type_plural = _("Categories")
    EditBookClass = CategoryEditBook


class NoteEditor(Editor):
    plural_title = _("Multiple notes")
    singular_title = _("%s (Note)")
    item_type_plural = _("Notes")
    EditBookClass = NoteEditBook


class AttachmentEditor(Editor):
    plural_title = _("Multiple attachments")
    singular_title = _("%s (Attachment)")
    item_type_plural = _("Attachments")
    EditBookClass = AttachmentEditBook


class EffortEditor(Editor):
    plural_title = _("Multiple efforts")
    singular_title = _("%s (Effort)")
    item_type_plural = _("Efforts")
    EditBookClass = EffortEditBook
