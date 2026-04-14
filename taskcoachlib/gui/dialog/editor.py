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
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
from taskcoachlib.meta.debug import log_step
from taskcoachlib.domain import task, category, date, note, attachment, effort, base
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
from taskcoachlib.help.balloontips import BalloonTipManager
import datetime
import os.path
import wx


# --- System Theme Resolution Helpers ---
# Single point for converting domain symbolic constants to wx values.
# Domain SSOT methods return these constants; UI uses these helpers to resolve.

def resolve_color(value):
    """Convert domain color value to wx.Colour.

    Args:
        value: Color tuple (r,g,b), symbolic constant, or wx.Colour

    Returns:
        wx.Colour instance
    """
    if value == base.SYSTEM_FG_COLOR:
        return wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
    elif value == base.SYSTEM_BG_COLOR:
        return wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
    elif isinstance(value, (tuple, list)):
        return wx.Colour(*value)
    elif isinstance(value, wx.Colour):
        return value
    else:
        import inspect
        caller = inspect.stack()[1]
        log_step("resolve_color: unhandled value", repr(value),
                 "from %s:%d in %s" % (caller[1], caller[2], caller[3]),
                 prefix="APPEARANCE-BUG")
        return wx.NullColour


def resolve_font(value):
    """Convert domain font value to wx.Font.

    Args:
        value: wx.Font or symbolic constant (SYSTEM_FONT)

    Returns:
        wx.Font instance, or wx.NullFont if value is unhandled (bug)
    """
    if value == base.SYSTEM_FONT:
        return wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
    elif isinstance(value, wx.Font):
        return value
    else:
        import inspect
        caller = inspect.stack()[1]
        log_step("resolve_font: unhandled value", repr(value),
                 "from %s:%d in %s" % (caller[1], caller[2], caller[3]),
                 prefix="APPEARANCE-BUG")
        return wx.NullFont


def is_system_theme(value):
    """Check if value is a system theme symbolic constant."""
    return value in (base.SYSTEM_FG_COLOR, base.SYSTEM_BG_COLOR, base.SYSTEM_FONT)


class Page(patterns.Observer, widgets.BookPage):
    columns = 2

    def __init__(self, items, *args, **kwargs):
        self.items = items
        super().__init__(columns=self.columns, *args, **kwargs)
        self.addEntries()
        self.fit()

    def selected(self):
        """Called when this page is selected. Override in subclasses for lazy initialization."""
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
            the_entry = self.entries().get("firstEntry")
            if the_entry is None:
                return
        self.__set_selection_and_focus(the_entry)

    def __set_selection_and_focus(self, the_entry):
        """If the entry has selectable text, select the text so that the user
        can start typing over it immediately."""
        the_entry.SetFocus()
        try:
            if operating_system.isWindows() and hasattr(
                the_entry, "SetInsertionPoint"
            ):
                # Scroll to left before selecting
                the_entry.SetInsertionPoint(0)
            the_entry.SetSelection(-1, -1)  # Select all text
        except (AttributeError, TypeError) as e:
            log_step("SetSelection failed on %s: %s" %
                     (type(the_entry).__name__, e), prefix="EDITOR")

    def close(self):
        self.removeInstance()


class ScrolledPage(patterns.Observer, widgets.ScrolledBookPage):
    """A scrollable page for dialogs with lots of content (e.g., Appearance tab)."""
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
            the_entry = self.entries().get("firstEntry")
            if the_entry is None:
                return
        self.__set_selection_and_focus(the_entry)

    def __set_selection_and_focus(self, the_entry):
        """If the entry has selectable text, select the text so that the user
        can start typing over it immediately."""
        the_entry.SetFocus()
        try:
            if operating_system.isWindows() and hasattr(
                the_entry, "SetInsertionPoint"
            ):
                # Scroll to left before selecting
                the_entry.SetInsertionPoint(0)
            the_entry.SetSelection(-1, -1)  # Select all text
        except (AttributeError, TypeError) as e:
            log_step("SetSelection failed on %s: %s" %
                     (type(the_entry).__name__, e), prefix="EDITOR")

    def close(self):
        self.removeInstance()


class SubjectPage(Page):
    pageName = "subject"
    pageTitle = _("Description")
    pageIcon = "nuvola_actions_draw-freehand"

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
        self._subjectEntry = widgets.SingleLineTextCtrl(
            self, current_subject, settings=self._settings
        )
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
            flags=[None, wx.ALL | wx.EXPAND],
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
            self, current_description, settings=self._settings
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
            flags=[None, wx.ALL | wx.EXPAND],
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
        self.addEntry(_("Creation date"), creation_text)

    def addModificationDateTimeEntry(self):
        self._modificationTextEntry = wx.StaticText(
            self, label=self.__modification_text()
        )
        self.addEntry(_("Modification date"), self._modificationTextEntry)
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
        self.addEntry(_("Priority"), self._priorityEntry)

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
        self.addStylePriorityEntry()
        self.addCreationDateTimeEntry()
        self.addModificationDateTimeEntry()

    def addExclusiveSubcategoriesEntry(self):
        # pylint: disable=W0201
        currentExclusivity = (
            self.items[0].hasExclusiveSubcategories()
            if len(self.items) == 1
            else False
        )
        panel = wx.Panel(self)
        panelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self._exclusiveSubcategoriesCheckBox = wx.CheckBox(panel)
        self._exclusiveSubcategoriesCheckBox.SetValue(currentExclusivity)
        panelSizer.Add(self._exclusiveSubcategoriesCheckBox, 0, wx.ALIGN_CENTER_VERTICAL)
        hintText = wx.StaticText(panel, label=_("Subcategories are mutually exclusive"))
        hintText.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        panelSizer.Add(hintText, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5)
        panel.SetSizer(panelSizer)
        self._exclusiveSubcategoriesSync = attributesync.AttributeSync(
            "hasExclusiveSubcategories",
            self._exclusiveSubcategoriesCheckBox,
            currentExclusivity,
            self.items,
            command.EditExclusiveSubcategoriesCommand,
            wx.EVT_CHECKBOX,
            self.items[0].exclusiveSubcategoriesChangedEventType(),
        )
        self.addEntry(_("Mutually exclusive"), panel)

    def addStylePriorityEntry(self):
        # pylint: disable=W0201
        currentPriority = (
            self.items[0].stylePriority() if len(self.items) == 1 else 0
        )
        self._stylePriorityEntry = widgets.SpinCtrl(
            self, size=(100, -1), value=currentPriority, min=-999, max=999
        )
        self._stylePrioritySync = attributesync.AttributeSync(
            "stylePriority",
            self._stylePriorityEntry,
            currentPriority,
            self.items,
            command.EditStylePriorityCommand,
            wx.EVT_SPINCTRL,
            self.items[0].stylePriorityChangedEventType(),
        )
        self.addEntry(_("Style priority"), self._stylePriorityEntry)


class AttachmentSubjectPage(SubjectPage):
    # Map type_ values to human-readable names and icons
    TYPE_INFO = {
        "file": (_("File"), "nuvola_mimetypes_application-x-dvi"),
        "folder": (_("Folder"), "nuvola_mimetypes_inode-directory"),
        "uri": (_("Link"), "nuvola_categories_applications-internet"),
        "mail": (_("Email"), "nuvola_apps_email"),
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
                type_name, icon_id = self.TYPE_INFO.get("folder")
            else:
                item_type = item.type_
                type_name, icon_id = self.TYPE_INFO.get(
                    item_type, (item_type, None)
                )
                # Check if file exists for file attachments
                if item_type == "file":
                    attachmentBase = self._settings.get("file", "attachmentbase")
                    if not os.path.exists(item.normalizedLocation(attachmentBase)):
                        icon_id = "taskcoach_actions_fileopen_red"
        else:
            # Multiple items - show type if all same, otherwise "Mixed"
            types = set(item.type_ for item in self.items)
            if len(types) == 1:
                item_type = types.pop()
                type_name, icon_id = self.TYPE_INFO.get(
                    item_type, (_("Unknown"), None)
                )
            else:
                type_name = _("Mixed")
                icon_id = None

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        if icon_id:
            bitmap = icon_catalog.get_bitmap(icon_id, LIST_ICON_SIZE)
            if bitmap.IsOk():
                icon = wx.StaticBitmap(panel, bitmap=bitmap)
                sizer.Add(icon, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        type_label = wx.StaticText(panel, label=type_name)
        sizer.Add(type_label, 0, wx.ALIGN_CENTER_VERTICAL)
        panel.SetSizer(sizer)
        self.addEntry(_("Type"), panel, flags=[None, wx.ALIGN_CENTER_VERTICAL])

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
            panel, current_location, spellCheck=False  # File paths/URLs shouldn't be spell checked
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
        self.addEntry(_("Location"), panel, flags=[None, wx.EXPAND])

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


class TaskAppearancePage(ScrolledPage):
    """Appearance tab with scrollbar support for all domain object types."""
    pageName = "appearance"
    pageTitle = _("Appearance")
    pageIcon = "nuvola_apps_kcoloredit"
    columns = 3  # Label, Control, Source
    _vgap = 2
    _hgap = 5
    _borderWidth = 2

    def addEntries(self):
        self.addCalculatedSection()
        # Show "Override values" header for all single-item edits
        if len(self.items) == 1:
            self.addLine()
            self.addSectionHeader(_("Override values"))
        self.addIconEntry()
        self.addColorEntries()
        self.addFontEntry()
        self.addEffectiveSection()
        # Update derived values now that all widgets exist
        if len(self.items) == 1:
            self._updateDerivedValues()

    def addSectionHeader(self, title, sourceLabel=None):
        """Add a bold section header spanning columns 0-1, optional label in column 2."""
        header = wx.StaticText(self, label=title)
        header.SetFont(header.GetFont().Bold())
        flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT
        self._sizer.Add(header, self._position.next(2), span=(1, 2),
                        flag=flag, border=self._borderWidth)
        if sourceLabel:
            source = wx.StaticText(self, label=sourceLabel)
            source.SetFont(source.GetFont().Bold())
            self._sizer.Add(source, self._position.next(1), span=(1, 1),
                            flag=flag, border=self._borderWidth)
        else:
            self._sizer.Add((0, 0), self._position.next(1), span=(1, 1))

    def addCalculatedSection(self):
        """Add read-only display of derived appearance values.

        Layout: 3 columns - Label, Control, Source
        - Tasks: derived from category/parent/status
        - Categories: derived from parent category
        - Notes: derived from parent note (or System Theme)
        - Efforts/Attachments: always System Theme (no inheritance)
        """
        if len(self.items) != 1:
            return
        item = self.items[0]

        self.addSectionHeader(_("Derived values"), _("Source"))
        entryFlags = [
            wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT,  # Label
            wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT,  # Control
            wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT,  # Source
        ]

        # Icon - panel with both bitmap and "N/A" text (show one or the other)
        def rejectNav(evt):
            evt.GetEventObject().Navigate(evt.GetDirection())
        def rejectFocus(evt):
            forward = not wx.GetKeyState(wx.WXK_SHIFT)
            wx.CallAfter(evt.GetEventObject().Navigate, forward)
        self._derivedIconPanel = wx.Panel(self, style=0)
        self._derivedIconPanel.Bind(wx.EVT_NAVIGATION_KEY, rejectNav)
        self._derivedIconPanel.Bind(wx.EVT_SET_FOCUS, rejectFocus)
        iconSizer = wx.BoxSizer(wx.HORIZONTAL)
        self._derivedIconDisplay = wx.StaticBitmap(self._derivedIconPanel)
        self._derivedIconDisplay.Bind(wx.EVT_NAVIGATION_KEY, rejectNav)
        self._derivedIconDisplay.Bind(wx.EVT_SET_FOCUS, rejectFocus)
        self._derivedIconName = wx.StaticText(self._derivedIconPanel, label="")
        self._derivedIconName.Bind(wx.EVT_NAVIGATION_KEY, rejectNav)
        self._derivedIconName.Bind(wx.EVT_SET_FOCUS, rejectFocus)
        self._derivedIconNA = wx.StaticText(self._derivedIconPanel, label=_("N/A"))
        self._derivedIconNA.Bind(wx.EVT_NAVIGATION_KEY, rejectNav)
        self._derivedIconNA.Bind(wx.EVT_SET_FOCUS, rejectFocus)
        self._derivedIconNA.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        iconSizer.Add(self._derivedIconDisplay, 0, wx.ALIGN_CENTER_VERTICAL)
        iconSizer.Add(self._derivedIconName, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5)
        iconSizer.Add(self._derivedIconNA, 0, wx.ALIGN_CENTER_VERTICAL)
        self._derivedIconPanel.SetSizer(iconSizer)
        self._derivedIconSource = wx.StaticText(self, label="")
        self._derivedIconSource.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        self.addEntry(_("Icon"), self._derivedIconPanel, self._derivedIconSource, flags=entryFlags)

        # Foreground
        self._derivedFgPicker = widgets.ColourPickerCtrl(self, colour=wx.BLACK, readOnly=True)
        self._derivedFgSource = wx.StaticText(self, label="")
        self._derivedFgSource.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        self.addEntry(_("Foreground"), self._derivedFgPicker, self._derivedFgSource, flags=entryFlags)

        # Background
        self._derivedBgPicker = widgets.ColourPickerCtrl(self, colour=wx.WHITE, readOnly=True)
        self._derivedBgSource = wx.StaticText(self, label="")
        self._derivedBgSource.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        self.addEntry(_("Background"), self._derivedBgPicker, self._derivedBgSource, flags=entryFlags)

        # Font
        defaultFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        self._derivedFontPicker = widgets.FontPickerCtrl(
            self, font=defaultFont, colour=(0, 0, 0, 255), readOnly=True)
        self._derivedFontSource = wx.StaticText(self, label="")
        self._derivedFontSource.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        self.addEntry(_("Font"), self._derivedFontPicker, self._derivedFontSource, flags=entryFlags)

        # Note: _updateDerivedValues() is called at end of addEntries() after all widgets exist

        # Subscribe to SSOT derived change events for automatic updates
        for eventType in (item.derivedFgColorChangedEventType(),
                          item.derivedBgColorChangedEventType(),
                          item.derivedIconChangedEventType(),
                          item.derivedFontChangedEventType()):
            self.registerObserver(
                self._onDerivedAppearanceChanged,
                eventType=eventType,
                eventSource=item
            )

    def _onDerivedAppearanceChanged(self, event):
        """Update derived display when SSOT appearance changes."""
        self._updateDerivedValues()

    def _updateDerivedValues(self):
        """Refresh the derived icon and color displays (pre-override values).

        Unified display logic for all item types. Always shows pickers with
        system theme colors as fallback. No N/A, no hiding.
        """
        if len(self.items) != 1:
            return
        # Guard: only update if derived display widgets exist
        if not hasattr(self, "_derivedIconDisplay"):
            return

        # Get derived values based on item type
        iconValue, iconSource, fgValue, fgSource, bgValue, bgSource, fontValue, fontSource = \
            self._getDerivedValuesForItem(self.items[0])

        # Display derived values (unified for all item types)
        self._displayDerivedValues(iconValue, iconSource, fgValue, fgSource,
                                   bgValue, bgSource, fontValue, fontSource)

    def _getDerivedValuesForItem(self, item):
        """Get derived appearance values from SSOT accessors.

        Returns: (iconValue, iconSource, fgValue, fgSource, bgValue, bgSource, fontValue, fontSource)

        Uses separate derivedXxx() and derivedXxxSource() accessors.
        """
        # Get derived values and sources using separate accessors
        iconActual = item.derivedIcon()
        iconSource = item.derivedIconSource()
        fgActual = item.derivedFgColor()
        fgSource = item.derivedFgColorSource()
        bgActual = item.derivedBgColor()
        bgSource = item.derivedBgColorSource()
        fontActual = item.derivedFont()
        fontSource = item.derivedFontSource()

        # Get defaults for fallback
        iconDefault = item.effectiveIconDefault() if hasattr(item, 'effectiveIconDefault') else ""
        fgDefault = item.effectiveFgColorDefault() if hasattr(item, 'effectiveFgColorDefault') else base.SYSTEM_FG_COLOR
        bgDefault = item.effectiveBgColorDefault() if hasattr(item, 'effectiveBgColorDefault') else base.SYSTEM_BG_COLOR
        fontDefault = item.effectiveFontDefault() if hasattr(item, 'effectiveFontDefault') else base.SYSTEM_FONT

        # Resolve to wx values: use actual if set, otherwise default
        iconValue = iconActual if iconActual else iconDefault
        fgValue = resolve_color(fgActual if fgActual else fgDefault)
        bgValue = resolve_color(bgActual if bgActual else bgDefault)
        fontValue = resolve_font(fontActual if fontActual else fontDefault)

        return (iconValue, iconSource, fgValue, fgSource, bgValue, bgSource, fontValue, fontSource)

    def _displayDerivedValues(self, iconValue, iconSource, fgValue, fgSource,
                              bgValue, bgSource, fontValue, fontSource):
        """Display derived values in the UI.

        Domain SSOT methods (derivedXxx) return:
        - Actual value + source when inherited from parent
        - Symbolic constant (e.g., base.SYSTEM_FG_COLOR) + "System Theme" when no parent

        This method uses resolve_color/resolve_font helpers to convert
        symbolic constants to actual wx values. No fallback logic here -
        domain is the single source of truth.

        Icons are special: no system theme exists, so empty icon shows "N/A".
        """
        # --- Icon ---
        # Icons have no system theme - show "N/A" when no inherited value
        if iconValue:
            from taskcoachlib.gui.icons.icon_library import icon_catalog
            icon_id = iconValue  # iconValue follows the *Value/*Source pattern
            self._derivedIconDisplay.SetBitmap(icon_catalog.get_bitmap(icon_id, LIST_ICON_SIZE))
            self._derivedIconDisplay.Show()
            icon = icon_catalog.get_icon(icon_id)
            self._derivedIconName.SetLabel(icon.label if icon else icon_id)
            self._derivedIconName.Show()
            self._derivedIconNA.Hide()
            self._derivedIconSource.SetLabel(iconSource or _("Initializing..."))
        else:
            self._derivedIconDisplay.Hide()
            self._derivedIconName.Hide()
            self._derivedIconNA.Show()
            self._derivedIconSource.SetLabel(_("N/A"))
        self._derivedIconPanel.Layout()

        # --- Foreground Color ---
        # fgValue is either a color tuple or base.SYSTEM_FG_COLOR constant
        # fgSource is either "[Category] Name" or "System Theme"
        derivedFgColour = resolve_color(fgValue)
        self._derivedFgPicker.SetColour(derivedFgColour)
        self._derivedFgPicker.Show()
        self._derivedFgSource.SetLabel(fgSource or _("Initializing..."))

        # --- Background Color ---
        # bgValue is either a color tuple or base.SYSTEM_BG_COLOR constant
        # bgSource is either "[Category] Name" or "System Theme"
        derivedBgColour = resolve_color(bgValue)
        self._derivedBgPicker.SetColour(derivedBgColour)
        self._derivedBgPicker.Show()
        self._derivedBgSource.SetLabel(bgSource or _("Initializing..."))

        # --- Font ---
        # fontValue is either a wx.Font or base.SYSTEM_FONT constant
        # fontSource is either "[Category] Name" or "System Theme"
        derivedFont = resolve_font(fontValue)
        self._derivedFontPicker.SetSelectedFont(derivedFont)
        self._derivedFontPicker.Show()
        self._derivedFontSource.SetLabel(fontSource or _("Initializing..."))

        # Update font picker demo colors to match derived colors
        self._derivedFontPicker.SetSelectedColour(derivedFgColour)
        self._derivedFontPicker.SetSelectedBgColour(derivedBgColour)

        # Note: override entries now track effective values, not derived
        # (updated in _updateEffectiveValues)

    def addColorEntries(self):
        self.addColorEntry(_("Foreground"), "foreground", wx.BLACK)
        self.addColorEntry(_("Background"), "background", wx.WHITE)

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
        self.addEntry(labelText, colorEntry, flags=[None, wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT])

    def addFontEntry(self):
        # pylint: disable=W0201,E1101
        currentFont = self.items[0].font() if len(self.items) == 1 else None
        # Use override color if set, otherwise use effective/inherited color
        # Tasks and Categories have effectiveFgColor() (SSOT)
        # Notes/Efforts/Attachments use foregroundColor(recursive=True)
        overrideFgColor = self._foregroundColorEntry.GetValue()
        overrideBgColor = self._backgroundColorEntry.GetValue()
        if len(self.items) == 1:
            item = self.items[0]
            if hasattr(item, 'effectiveFgColor'):
                # Tasks and Categories use SSOT effective methods
                currentColor = overrideFgColor if overrideFgColor else item.effectiveFgColor()
                currentBgColor = overrideBgColor if overrideBgColor else item.effectiveBgColor()
            else:
                # Notes inherit from parent notes, Efforts/Attachments have no inheritance
                currentColor = overrideFgColor if overrideFgColor else item.foregroundColor(recursive=True)
                currentBgColor = overrideBgColor if overrideBgColor else item.backgroundColor(recursive=True)
        else:
            currentColor = overrideFgColor
            currentBgColor = overrideBgColor
        # Convert to wx.Colour using generic resolve helper (handles tuples and symbolic constants)
        currentColor = resolve_color(currentColor) if currentColor else None
        currentBgColor = resolve_color(currentBgColor) if currentBgColor else None
        self._fontEntry = entry.FontEntry(self, currentFont, currentColor, currentBgColor)
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
            _("Font"), self._fontEntry, flags=[None, wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT]
        )

    def addEffectiveSection(self):
        """Add read-only display of effective/final appearance values.

        Layout: 3 columns - Label, Control, Source
        - Tasks/Categories: have effectiveXxx() SSOT methods
        - Notes: effective = override or parent (recursive lookup)
        - Attachments: effective = override or System Theme
        """
        if len(self.items) != 1:
            return
        item = self.items[0]

        self.addLine()
        self.addSectionHeader(_("Effective values"), _("Source"))
        entryFlags = [
            wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT,  # Label
            wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT,  # Control
            wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT,  # Source
        ]

        # Icon - panel with bitmap and "N/A" text (show one or the other)
        def rejectNav(evt):
            evt.GetEventObject().Navigate(evt.GetDirection())
        def rejectFocus(evt):
            forward = not wx.GetKeyState(wx.WXK_SHIFT)
            wx.CallAfter(evt.GetEventObject().Navigate, forward)
        self._effectiveIconPanel = wx.Panel(self, style=0)
        self._effectiveIconPanel.Bind(wx.EVT_NAVIGATION_KEY, rejectNav)
        self._effectiveIconPanel.Bind(wx.EVT_SET_FOCUS, rejectFocus)
        iconSizer = wx.BoxSizer(wx.HORIZONTAL)
        self._effectiveIconDisplay = wx.StaticBitmap(self._effectiveIconPanel)
        self._effectiveIconDisplay.Bind(wx.EVT_NAVIGATION_KEY, rejectNav)
        self._effectiveIconDisplay.Bind(wx.EVT_SET_FOCUS, rejectFocus)
        self._effectiveIconName = wx.StaticText(self._effectiveIconPanel, label="")
        self._effectiveIconName.Bind(wx.EVT_NAVIGATION_KEY, rejectNav)
        self._effectiveIconName.Bind(wx.EVT_SET_FOCUS, rejectFocus)
        self._effectiveIconNA = wx.StaticText(self._effectiveIconPanel, label=_("N/A"))
        self._effectiveIconNA.Bind(wx.EVT_NAVIGATION_KEY, rejectNav)
        self._effectiveIconNA.Bind(wx.EVT_SET_FOCUS, rejectFocus)
        self._effectiveIconNA.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        iconSizer.Add(self._effectiveIconDisplay, 0, wx.ALIGN_CENTER_VERTICAL)
        iconSizer.Add(self._effectiveIconName, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5)
        iconSizer.Add(self._effectiveIconNA, 0, wx.ALIGN_CENTER_VERTICAL)
        self._effectiveIconPanel.SetSizer(iconSizer)
        self._effectiveIconSource = wx.StaticText(self, label="")
        self._effectiveIconSource.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        self.addEntry(_("Icon"), self._effectiveIconPanel, self._effectiveIconSource, flags=entryFlags)

        # Foreground - read-only color picker with source
        self._effectiveFgPicker = widgets.ColourPickerCtrl(
            self, colour=wx.BLACK, readOnly=True
        )
        self._effectiveFgSource = wx.StaticText(self, label="")
        self._effectiveFgSource.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        self.addEntry(_("Foreground"), self._effectiveFgPicker, self._effectiveFgSource, flags=entryFlags)

        # Background - read-only color picker with source
        self._effectiveBgPicker = widgets.ColourPickerCtrl(
            self, colour=wx.WHITE, readOnly=True
        )
        self._effectiveBgSource = wx.StaticText(self, label="")
        self._effectiveBgSource.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        self.addEntry(_("Background"), self._effectiveBgPicker, self._effectiveBgSource, flags=entryFlags)

        # Font - read-only font picker with source
        defaultFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        self._effectiveFontPicker = widgets.FontPickerCtrl(
            self, font=defaultFont,
            colour=wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT),
            bgColour=wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW),
            readOnly=True
        )
        self._effectiveFontSource = wx.StaticText(self, label="")
        self._effectiveFontSource.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        self.addEntry(_("Font"), self._effectiveFontPicker, self._effectiveFontSource, flags=entryFlags)

        # Initial update
        self._updateEffectiveValues()

        # Subscribe to SSOT effective change events for automatic updates
        for eventType in (item.effectiveFgColorChangedEventType(),
                          item.effectiveBgColorChangedEventType(),
                          item.effectiveIconChangedEventType(),
                          item.effectiveFontChangedEventType()):
            self.registerObserver(
                self._onEffectiveAppearanceChanged,
                eventType=eventType,
                eventSource=item
            )

    def _onEffectiveAppearanceChanged(self, event):
        self._updateEffectiveValues()
        self._updateFontDemoColors()

    def _updateEffectiveValues(self):
        """Refresh the effective appearance display from item's effective fields.

        All domain objects (Task, Category, Note, Attachment) use the same SSOT
        accessor pattern: effectiveXxx(), effectiveXxxSource(), and effectiveXxxDefault()
        (except icon which has no default).
        """
        if len(self.items) != 1:
            return
        if not hasattr(self, '_effectiveIconDisplay'):
            return
        item = self.items[0]

        # --- Icon ---
        iconActual = item.effectiveIcon()
        iconSource = item.effectiveIconSource()
        # Icons have no system default - use empty string if no value
        iconValue = iconActual if iconActual else ""
        if iconValue:
            from taskcoachlib.gui.icons.icon_library import icon_catalog
            icon_id = iconValue  # iconValue follows the *Value/*Source pattern
            self._effectiveIconDisplay.SetBitmap(icon_catalog.get_bitmap(icon_id, LIST_ICON_SIZE))
            self._effectiveIconDisplay.Show()
            icon = icon_catalog.get_icon(icon_id)
            self._effectiveIconName.SetLabel(icon.label if icon else icon_id)
            self._effectiveIconName.Show()
            self._effectiveIconNA.Hide()
            self._effectiveIconSource.SetLabel(iconSource or _("Initializing..."))
        else:
            self._effectiveIconDisplay.Hide()
            self._effectiveIconName.Hide()
            self._effectiveIconNA.Show()
            self._effectiveIconSource.SetLabel(_("N/A"))
        self._effectiveIconPanel.Layout()

        # --- Foreground Color ---
        fgActual = item.effectiveFgColor()
        fgDefault = item.effectiveFgColorDefault()
        fgSource = item.effectiveFgColorSource()
        effectiveFgColour = resolve_color(fgActual if fgActual else fgDefault)
        self._effectiveFgPicker.SetColour(effectiveFgColour)
        self._effectiveFgSource.SetLabel(fgSource or _("Initializing..."))

        # --- Background Color ---
        bgActual = item.effectiveBgColor()
        bgDefault = item.effectiveBgColorDefault()
        bgSource = item.effectiveBgColorSource()
        effectiveBgColour = resolve_color(bgActual if bgActual else bgDefault)
        self._effectiveBgPicker.SetColour(effectiveBgColour)
        self._effectiveBgSource.SetLabel(bgSource or _("Initializing..."))

        # --- Font ---
        fontActual = item.effectiveFont()
        fontDefault = item.effectiveFontDefault()
        fontSource = item.effectiveFontSource()
        self._effectiveFontPicker.SetSelectedFont(resolve_font(fontActual if fontActual else fontDefault))
        self._effectiveFontSource.SetLabel(fontSource or _("Initializing..."))

        # Update font picker demo colors
        self._effectiveFontPicker.SetSelectedColour(effectiveFgColour)
        self._effectiveFontPicker.SetSelectedBgColour(effectiveBgColour)

        # Update override entries to track effective values
        # (shown when override checkbox is unchecked; always for colors on font picker)
        effectiveFont = resolve_font(fontActual if fontActual else fontDefault)
        if hasattr(self, '_foregroundColorEntry'):
            self._foregroundColorEntry.setEffectiveColor(effectiveFgColour)
        if hasattr(self, '_backgroundColorEntry'):
            self._backgroundColorEntry.setEffectiveColor(effectiveBgColour)
        if hasattr(self, '_fontEntry'):
            self._fontEntry.setEffectiveFont(effectiveFont)

    def _updateFontDemoColors(self):
        if len(self.items) != 1:
            return
        item = self.items[0]
        self._fontEntry.SetColor(resolve_color(
            item.effectiveFgColor() or item.effectiveFgColorDefault()))
        self._fontEntry.SetBgColor(resolve_color(
            item.effectiveBgColor() or item.effectiveBgColorDefault()))

    def addIconEntry(self):
        # pylint: disable=W0201,E1101
        current_icon_id = self.items[0].icon_id() if len(self.items) == 1 else ""

        self._iconEntry = entry.IconEntry(self, current_icon_id, exclude="status")
        self._iconSync = attributesync.AttributeSync(
            "icon_id",
            self._iconEntry,
            current_icon_id,
            self.items,
            command.EditIconCommand,
            entry.EVT_ICONENTRY,
            self.items[0].appearanceChangedEventType(),
        )
        self.addEntry(
            _("Icon"), self._iconEntry, flags=[None, wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT]
        )

    def entries(self):
        return dict(
            firstEntry=self._iconEntry
        )  # pylint: disable=E1101

    def close(self):
        super().close()


class DatesPage(ScrolledPage):
    pageName = "dates"
    pageTitle = _("Dates")
    pageIcon = "nuvola_apps_date"
    columns = 3  # label, datetime row, rest

    def __init__(
        self, theTask, parent, settings, items_are_new, *args, **kwargs
    ):
        self.__settings = settings
        self._duration = None
        self.__items_are_new = items_are_new
        super().__init__(theTask, parent, *args, **kwargs)

    def close(self):
        if len(self.items) == 1 and hasattr(self, '_statusLabel'):
            try:
                pub.unsubscribe(self._onStatusMayHaveChanged,
                                self.items[0].statusChangedEventType())
            except Exception as e:
                log_step("unsubscribe failed in %s.close: %s" %
                         (self.__class__.__name__, e), prefix="DEAD-OBJ")
        if len(self.items) == 1:
            try:
                pub.unsubscribe(self._onDomainPlannedDurationModeChanged,
                                self.items[0].plannedDurationModeChangedEventType())
            except Exception as e:
                log_step("unsubscribe failed in %s.close: %s" %
                         (self.__class__.__name__, e), prefix="DEAD-OBJ")
            try:
                pub.unsubscribe(self.__onTaskDurationDomainChanged,
                                self.items[0].plannedDurationChangedEventType())
            except Exception as e:
                log_step("unsubscribe failed in %s.close: %s" %
                         (self.__class__.__name__, e), prefix="DEAD-OBJ")
        super().close()

    def __onPlannedStartChanged(self, value):
        """AttributeSync callback for planned start date changes."""
        self._currentPlannedStartDateTime = value
        self.__onPlannedStartDateTimeChanged(value)

    def __onPlannedStartDateTimeChanged(self, value):
        """Called when planned start date changes - update based on mode."""
        if hasattr(self, '_currentPlannedDurationMode'):
            self.__syncTaskState(sourceField='start')

    def __onDueDateChanged(self, value):
        """AttributeSync callback for due date changes."""
        self._currentDueDateTime = value
        self.__onDueDateTimeChanged(value)

    def __onDueDateTimeChanged(self, value):
        """Called when due date changes - update based on mode."""
        if hasattr(self, '_currentPlannedDurationMode'):
            self.__syncTaskState(sourceField='due')

    def _onDomainPlannedDurationModeChanged(self, newValue, sender):
        """Layer 2: Domain plannedDurationMode changed externally."""
        if sender not in self.items:
            return
        self._currentPlannedDurationMode = newValue
        self.__updateDurationModeDropdown()
        self.__syncTaskState()

    def __onPlannedDurationSyncCallback(self, value):
        """AttributeSync callback: duration committed or changed externally."""
        self.__syncTaskState(sourceField='duration')

    def __onTaskDurationDomainChanged(self, newValue, sender):
        """Domain duration changed — update preset dropdown to match."""
        if sender in self.items:
            self.__updatePresetSelection()

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

        # Source explanation (gray text)
        self._statusSource = wx.StaticText(self, label="")
        self._statusSource.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        # 3 controls: label + panel + source
        self.addEntry(
            _("Status"),
            self._statusPanel,
            self._statusSource,
            flags=[None, wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT,
                   wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT],
        )

        # Initial display
        self._updateStatusDisplay()

        # Subscribe to status change event (fired by computeStoredStatus when status changes)
        pub.subscribe(self._onStatusMayHaveChanged, self.items[0].statusChangedEventType())

    def _onStatusMayHaveChanged(self, newValue, sender):
        if sender == self.items[0] or sender is None:
            self._updateStatusDisplay()

    def _updateStatusDisplay(self):
        if not hasattr(self, '_statusLabel'):
            return
        theTask = self.items[0]
        # Use centralized computedStatus(explain=True) for status and source
        taskStatus, statusSource = theTask.computedStatus(explain=True)

        # Update icon
        icon_id = taskStatus.getBitmap(self.__settings)
        bitmap = icon_catalog.get_bitmap(icon_id, LIST_ICON_SIZE)
        if bitmap.IsOk():
            self._statusIcon.SetBitmap(bitmap)

        # Update text and foreground color only (no background painting)
        statusText = taskStatus.pluralLabel.replace(" tasks", "").replace("tasks", "").strip()
        self._statusLabel.SetLabel(statusText)
        self._statusLabel.SetForegroundColour(theTask.statusFgColor())

        # Update source explanation
        if hasattr(self, '_statusSource'):
            self._statusSource.SetLabel(statusSource or _("Initializing..."))
            self._statusSource.InvalidateBestSize()

        # Relayout panel and parent to accommodate new text sizes
        self._statusLabel.InvalidateBestSize()
        self._statusPanel.Layout()
        self._statusPanel.Fit()
        self.Layout()

    def addDateEntries(self):
        # Create panel for planned date section with table layout
        self._addPlannedDateSection()
        self.addLine()
        self._addActualStartDateEntry()
        self._addCompletionDateEntry()

        # Now that all date entries exist, set initial enabled state
        if hasattr(self, '_currentPlannedDurationMode'):
            self.__syncTaskState()

    def _addPlannedDateSection(self):
        """Add the planned date section using the main grid (5 columns: label, checkbox, date, time, rest)."""
        # Row 1: Planned start date
        plannedStartDateTime = (
            self.items[0].plannedStartDateTime()
            if len(self.items) == 1
            else date.DateTime()
        )
        self._currentPlannedStartDateTime = plannedStartDateTime

        # value=None means no date set, value=datetime means date exists
        value = plannedStartDateTime if plannedStartDateTime != date.DateTime() else None

        self._plannedStartDateTimeCombo = widgets.DateTimeComboCtrl(
            self, value=value,
            suggestedValue=task.Task.suggestedPlannedStartDateTime(),
            hourChoices=lambda: get_suggested_hour_choices(self._DatesPage__settings),
            minuteChoices=lambda: get_suggested_minute_choices(self._DatesPage__settings)
        )
        # Use AttributeSync for automatic external update handling
        # Sync on EVT_VALUE_CHANGED — fires on checkbox toggle AND date/time edits
        self._plannedStartDateTimeSync = attributesync.AttributeSync(
            "plannedStartDateTime",
            self._plannedStartDateTimeCombo,
            plannedStartDateTime,
            self.items,
            command.EditPlannedStartDateTimeCommand,
            widgets.EVT_VALUE_CHANGED,
            self.items[0].plannedStartDateTimeChangedEventType(),
            callback=self.__onPlannedStartChanged,
        )
        # Rebuild dropdown when focus leaves this field
        self._plannedStartDateTimeCombo.Bind(wx.EVT_KILL_FOCUS, self.__onDurationFieldKillFocus)

        # Add planned start row: label | datetime row | (empty)
        self.addEntry(
            _("Planned start date"),
            self._plannedStartDateTimeCombo.CreateRowPanel(self),
            wx.StaticText(self, label=""),
        )

        # Get due date value early so we can determine the initial mode
        dueDateTime = (
            self.items[0].dueDateTime()
            if len(self.items) == 1
            else date.DateTime()
        )
        self._currentDueDateTime = dueDateTime

        # Row 2: Planned duration
        plannedDuration = (
            self.items[0].plannedDuration()
            if len(self.items) == 1
            else date.TimeDelta()
        )

        total_seconds = int(plannedDuration.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        self._plannedDurationCtrl = widgets.MaskedDurationCtrl(
            self, days=days, hours=hours, minutes=minutes
        )
        # Rebuild dropdown when focus leaves this field
        self._plannedDurationCtrl.Bind(wx.EVT_KILL_FOCUS, self.__onDurationFieldKillFocus)

        # Layer 2: AttributeSync for duration (user edits → command,
        # domain changes → widget update). Callback triggers sync cascade.
        self._plannedDurationSync = attributesync.AttributeSync(
            "plannedDuration",
            self._plannedDurationCtrl,
            plannedDuration,
            self.items,
            command.EditPlannedDurationCommand,
            widgets.EVT_VALUE_CHANGED,
            self.items[0].plannedDurationChangedEventType(),
            callback=self.__onPlannedDurationSyncCallback,
        )

        # Subscribe to domain changes BEFORE __syncTaskState()
        # so that changes during init sync trigger UI updates.
        if len(self.items) == 1:
            pub.subscribe(self._onDomainPlannedDurationModeChanged,
                          self.items[0].plannedDurationModeChangedEventType())
            pub.subscribe(self.__onTaskDurationDomainChanged,
                          self.items[0].plannedDurationChangedEventType())

        # Presets dropdown
        self._durationPresetsChoice = wx.Choice(self)
        self.__populateDurationPresets()
        self._durationPresetsChoice.Bind(wx.EVT_CHOICE, self.__onDurationPresetSelected)
        # Rebuild mode dropdown when focus leaves preset dropdown
        self._durationPresetsChoice.Bind(wx.EVT_KILL_FOCUS, self.__onDurationFieldKillFocus)

        self.registerObserver(
            self.__onPresetsConfigChanged,
            eventType="feature.task_duration_presets",
            eventSource=self.__settings,
        )

        # Mode dropdown: Automatic, Implicit, Adjust Due Date, Adjust Start Date
        self._durationModeChoices = [
            ("automatic", _("Automatic")),
            ("implicit", _("Implicit")),
            ("adjdue", _("Adjust Due Date")),
            ("adjstart", _("Adjust Start Date")),
        ]
        self._automaticModeDisabled = False  # Track if Automatic is disabled
        self._durationModeChoice = wx.Choice(self)
        for key, label in self._durationModeChoices:
            self._durationModeChoice.Append(label, key)
        self._durationModeChoice.Bind(wx.EVT_CHOICE, self.__onDurationModeChanged)

        # Get stored mode from task, default to "automatic"
        stored_mode = (
            self.items[0].plannedDurationMode()
            if len(self.items) == 1
            else "automatic"
        )
        # Convert old modes if needed (backward compatibility)
        if stored_mode not in ["automatic", "implicit", "adjdue", "adjstart"]:
            stored_mode = "automatic"
        self._currentPlannedDurationMode = stored_mode

        # Set dropdown selection
        mode_index = 0
        for idx, (key, label) in enumerate(self._durationModeChoices):
            if key == stored_mode:
                mode_index = idx
                break
        self._durationModeChoice.SetSelection(mode_index)

        # Create panel for presets + mode in last column
        duration_rest_panel = wx.Panel(self)
        duration_rest_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._durationPresetsChoice.Reparent(duration_rest_panel)
        self._durationModeChoice.Reparent(duration_rest_panel)
        duration_rest_sizer.Add(self._durationPresetsChoice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        duration_rest_sizer.Add(self._durationModeChoice, 0, wx.ALIGN_CENTER_VERTICAL)
        duration_rest_panel.SetSizer(duration_rest_sizer)

        # Add duration row: label | duration | presets+mode (left-aligned)
        self.addEntry(
            _("Planned duration"),
            self._plannedDurationCtrl,
            duration_rest_panel,
            flags=[None, wx.ALL | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.ALL],
        )

        # Row 3: Due date (value already retrieved above)

        # value=None means no date set, value=datetime means date exists
        value = dueDateTime if dueDateTime != date.DateTime() else None

        self._dueDateTimeCombo = widgets.DateTimeComboCtrl(
            self, value=value,
            suggestedValue=task.Task.suggestedDueDateTime(),
            hourChoices=lambda: get_suggested_hour_choices(self._DatesPage__settings),
            minuteChoices=lambda: get_suggested_minute_choices(self._DatesPage__settings)
        )
        # Use AttributeSync for automatic external update handling
        # Sync on EVT_VALUE_CHANGED — fires on checkbox toggle AND date/time edits
        self._dueDateTimeSync = attributesync.AttributeSync(
            "dueDateTime",
            self._dueDateTimeCombo,
            dueDateTime,
            self.items,
            command.EditDueDateTimeCommand,
            widgets.EVT_VALUE_CHANGED,
            self.items[0].dueDateTimeChangedEventType(),
            callback=self.__onDueDateChanged,
        )
        # Rebuild dropdown when focus leaves this field
        self._dueDateTimeCombo.Bind(wx.EVT_KILL_FOCUS, self.__onDurationFieldKillFocus)

        # Add due date row: label | datetime row | (empty)
        self.addEntry(
            _("Due date"),
            self._dueDateTimeCombo.CreateRowPanel(self),
            wx.StaticText(self, label=""),
        )

        # Update dropdown based on initial checkbox states, then apply mode state
        self.__updateDurationModeDropdown()
        self.__syncTaskState()
        self.__updatePresetSelection()

    def _addActualStartDateEntry(self):
        """Add actual start date entry using DateTimeComboCtrl."""
        actualStartDateTime = (
            self.items[0].actualStartDateTime()
            if len(self.items) == 1
            else date.DateTime()
        )
        self._currentActualStartDateTime = actualStartDateTime

        # value=None means no date set, value=datetime means date exists
        value = actualStartDateTime if actualStartDateTime != date.DateTime() else None

        self._actualStartDateTimeCombo = widgets.DateTimeComboCtrl(
            self, value=value,
            suggestedValue=task.Task.suggestedActualStartDateTime(),
            hourChoices=lambda: get_suggested_hour_choices(self._DatesPage__settings),
            minuteChoices=lambda: get_suggested_minute_choices(self._DatesPage__settings)
        )
        # Use AttributeSync for automatic external update handling
        # Sync on EVT_VALUE_CHANGED — fires on checkbox toggle AND date/time edits
        self._actualStartDateTimeSync = attributesync.AttributeSync(
            "actualStartDateTime",
            self._actualStartDateTimeCombo,
            actualStartDateTime,
            self.items,
            command.EditActualStartDateTimeCommand,
            widgets.EVT_VALUE_CHANGED,
            self.items[0].actualStartDateTimeChangedEventType(),
            callback=self.__onActualStartChanged,
        )

        self.addEntry(
            _("Actual start date"),
            self._actualStartDateTimeCombo.CreateRowPanel(self),
            wx.StaticText(self, label=""),
        )

    def __onActualStartChanged(self, value):
        """AttributeSync callback for actual start date changes."""
        self._currentActualStartDateTime = value

    def _addCompletionDateEntry(self):
        """Add completion date entry using DateTimeComboCtrl with AttributeSync."""
        completionDateTime = (
            self.items[0].completionDateTime()
            if len(self.items) == 1
            else date.DateTime()
        )

        # value=None means no date set, value=datetime means date exists
        value = completionDateTime if completionDateTime != date.DateTime() else None

        self._completionDateTimeCombo = widgets.DateTimeComboCtrl(
            self, value=value,
            suggestedValue=task.Task.suggestedCompletionDateTime(),
            hourChoices=lambda: get_suggested_hour_choices(self._DatesPage__settings),
            minuteChoices=lambda: get_suggested_minute_choices(self._DatesPage__settings)
        )

        # Use AttributeSync for automatic external update handling
        # Sync on EVT_VALUE_CHANGED — fires on checkbox toggle AND date/time edits
        self._completionDateTimeSync = attributesync.AttributeSync(
            "completionDateTime",
            self._completionDateTimeCombo,
            completionDateTime,
            self.items,
            command.EditCompletionDateTimeCommand,
            widgets.EVT_VALUE_CHANGED,
            self.items[0].completionDateTimeChangedEventType(),
        )

        self.addEntry(
            _("Completion date"),
            self._completionDateTimeCombo.CreateRowPanel(self),
            wx.StaticText(self, label=""),
        )

    def __populateDurationPresets(self):
        """Populate the duration presets dropdown from settings."""
        self._durationPresetsChoice.Clear()
        self._durationPresetsChoice.Append(_("Presets..."), None)  # Placeholder

        presets_str = self.__settings.get("feature", "task_duration_presets")
        if presets_str:
            presets = []
            for minutes_str in presets_str.split(","):
                try:
                    val = int(minutes_str.strip())
                    if val > 0:  # Only add non-zero presets
                        presets.append(val)
                except ValueError:
                    pass

            for total_minutes in sorted(presets):
                label = self.__formatDurationPreset(total_minutes)
                self._durationPresetsChoice.Append(label, total_minutes)

        self._durationPresetsChoice.Append(_("Reset to zero"), 0)  # Reset option (last)

        self._durationPresetsChoice.SetSelection(0)

    def __updatePresetSelection(self):
        """Update preset dropdown to match current duration value."""
        if not hasattr(self, '_plannedDurationCtrl'):
            return

        # Get current duration in total minutes
        duration = self._plannedDurationCtrl.GetDuration()
        current_minutes = int(duration.total_seconds() // 60)

        # Search for matching preset (start at 1 to skip placeholder, stop before last "Reset to zero")
        for i in range(1, self._durationPresetsChoice.GetCount() - 1):
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

    def __onPresetsConfigChanged(self, event=None):
        """Called when duration presets change in preferences."""
        self.__populateDurationPresets()

    def __onDurationPresetSelected(self, event):
        """Handle preset selection from dropdown.

        Presets route through duration change — fire command only,
        then pubsub callback handles widget update, preset alignment,
        and sync. Same pattern as effort presets."""
        selection = self._durationPresetsChoice.GetSelection()
        if selection == 0:  # Placeholder selected
            return

        total_minutes = self._durationPresetsChoice.GetClientData(selection)
        if total_minutes is None:
            return

        new_duration = date.TimeDelta(minutes=total_minutes)

        # SetDuration → EVT_VALUE_CHANGED → AttributeSync → command → pubsub → preset update
        self._plannedDurationCtrl.SetDuration(new_duration)



    def __onDurationFieldKillFocus(self, event):
        """Rebuild mode dropdown on focus loss."""
        self.__updateDurationModeDropdown()
        event.Skip()

    # --- Existence checks: read from widgets (domain-synced by Layer 2) ---

    def __syncTaskState(self, sourceField=None, depth=0):
        """Sync duration state based on Logic Flow.

        See docs/DURATION_CALCULATIONS.md "Logic Flow" section.

        Args:
            sourceField: Which field triggered this sync (section 0.1):
                       - 'start': User explicitly changed Start-Date (0.1.1)
                       - 'due': User explicitly changed Due-Date (0.1.2)
                       - 'duration': User explicitly changed Duration (0.1.3)
                       - None: Init or recursive loop call
            depth: Recursion depth (section 0.3). Starts at 0.
        """
        # 0.4 Sync-mode guard — flag on domain SSOT, shared across windows
        task = self.items[0]
        if getattr(task, '_durationSyncInProgress', False):
            return

        # 0.3 Recursive safety
        # 0.3.4 Depth > 1 should never occur, log error, exit
        if depth > 1:
            log_step("ERROR: __syncTaskState depth > 1 (%d), exiting" % depth, prefix="SYNC")
            return
        # 0.3.3 depth == 1 should never receive a user action, log error, continue
        if depth == 1 and sourceField is not None:
            log_step("ERROR: __syncTaskState depth==1 received sourceField=%s, expected None" % sourceField, prefix="SYNC")

        # Read current widget state once — no step in a single pass
        # depends on values changed by a prior step in the same pass.
        mode = self._currentPlannedDurationMode
        start = self._plannedStartDateTimeCombo.GetDateTime()
        due = self._dueDateTimeCombo.GetDateTime()
        duration = self._plannedDurationCtrl.GetDuration()

        if mode == "automatic":
            # 1.1 Note: Mode changes away never come back here
            # 1.2 If Start-Date exists, Then set Adj-Due mode, Loop
            if start is not None:
                self.__setDurationMode("adjdue")
                return self.__syncTaskState(None, depth=depth + 1)  # 0.3.2
            # 1.3 If Due-Date exists, Then set Adj-Start mode, Loop
            if due is not None:
                self.__setDurationMode("adjstart")
                return self.__syncTaskState(None, depth=depth + 1)  # 0.3.2

        elif mode == "adjdue":
            # 2.1 Note: Mode changes away never come back here
            # 2.2 Activate Start-Date, If not Unset-Action [Ref2, 0.1.1]
            if sourceField != 'start' and start is None:
                self._plannedStartDateTimeCombo.ActivateValue()
            # 2.3 Activate Due-Date (Read-Only) [Ref2]
            #     On first entry (sourceField=None), adj if due doesn't exist yet.
            if due is None and start is not None and duration is not None:
                self._dueDateTimeCombo.ActivateValue(start + duration)
            # 2.4 Disable Automatic mode option in dropdown [Ref1]
            #     (handled by __updateDurationModeDropdown on focus loss)
            # 2.5 If Duration changed, Then adj Due-Date
            if sourceField == 'duration' and start is not None and duration is not None:
                self._dueDateTimeCombo.ActivateValue(start + duration)
            # 2.6 If Start-Date Unset-Action, Then
            if sourceField == 'start' and start is None:
                # 2.6.1 Set Sync-Mode [0.4]
                task._durationSyncInProgress = True
                try:
                    # 2.6.2 Deactivate Due-Date
                    self._dueDateTimeCombo.DeactivateValue()
                    # 2.6.3 Reactivate Automatic mode option in dropdown
                    #        (handled by __updateDurationModeDropdown on focus loss)
                    # 2.6.4 Set Automatic mode
                    self.__setDurationMode("automatic")
                finally:
                    # 2.6.5 Unset Sync-Mode
                    task._durationSyncInProgress = False
                # 2.6.6 Loop
                return self.__syncTaskState(None, depth=depth + 1)  # 0.3.2
            # 2.7 If Start-Date changed, Then adj Due-Date
            if sourceField == 'start' and start is not None and duration is not None:
                self._dueDateTimeCombo.ActivateValue(start + duration)

        elif mode == "adjstart":
            # 3.1 Note: Mode changes away never come back here
            # 3.2 Activate Due-Date, If not Unset-Action [Ref2, 0.1.2]
            if sourceField != 'due' and due is None:
                self._dueDateTimeCombo.ActivateValue()
            # 3.3 Activate Start-Date (Read-Only) [Ref2]
            #     On first entry (sourceField=None), adj if start doesn't exist.
            if start is None and due is not None and duration is not None:
                self._plannedStartDateTimeCombo.ActivateValue(due - duration)
            # 3.4 Disable Automatic mode option in dropdown [Ref1]
            #     (handled by __updateDurationModeDropdown on focus loss)
            # 3.5 If Duration changed, Then adj Start-Date
            if sourceField == 'duration' and due is not None and duration is not None:
                self._plannedStartDateTimeCombo.ActivateValue(due - duration)
            # 3.6 If Due-Date Unset-Action, Then
            if sourceField == 'due' and due is None:
                # 3.6.1 Set Sync-Mode [0.4]
                task._durationSyncInProgress = True
                try:
                    # 3.6.2 Deactivate Start-Date
                    self._plannedStartDateTimeCombo.DeactivateValue()
                    # 3.6.3 Reactivate Automatic mode option in dropdown
                    #        (handled by __updateDurationModeDropdown on focus loss)
                    # 3.6.4 Set Automatic mode
                    self.__setDurationMode("automatic")
                finally:
                    # 3.6.5 Unset Sync-Mode
                    task._durationSyncInProgress = False
                # 3.6.6 Loop
                return self.__syncTaskState(None, depth=depth + 1)  # 0.3.2
            # 3.7 If Due-Date changed, Then adj Start-Date
            if sourceField == 'due' and due is not None and duration is not None:
                self._plannedStartDateTimeCombo.ActivateValue(due - duration)

        elif mode == "implicit":
            # 4.1 Note: Mode changes away never come back here
            # 4.2 Disable Automatic mode option in dropdown [Ref1]
            #     (handled by __updateDurationModeDropdown on focus loss)
            # 4.3 If Start-Date exists
            if start is not None:
                # 4.3.1 If Due-Date exists
                if due is not None:
                    # 4.3.1.1 Enable Duration (Read-Only)
                    # 4.3.1.2 Adj Duration (duration = due - start)
                    new_duration = due - start  # 4.3.1.3 Negative Durations permitted
                    self._plannedDurationCtrl.SetDuration(
                        date.TimeDelta(days=new_duration.days, seconds=new_duration.seconds))
                # 4.3.2 If Due-Date Unset-Action, Then disable Duration
                #        -- handled by __updateFieldStates
            # 4.4 If Start-Date Unset-Action, Then disable Duration
            #     -- handled by __updateFieldStates

        # 5. Update Field States (See: UI Field States section)
        self.__updateFieldStates()

    def __updateFieldStates(self):
        """Set field states per UI Field States table in DURATION_CALCULATIONS.md."""
        mode = self._currentPlannedDurationMode
        start = self._plannedStartDateTimeCombo.GetDateTime()
        due = self._dueDateTimeCombo.GetDateTime()

        if mode == "automatic":
            # Automatic | Editable | Editable | Editable
            self._plannedStartDateTimeCombo.SetEditable()
            self._plannedDurationCtrl.Enable(True)
            self._plannedDurationCtrl.SetReadOnly(False)
            self._dueDateTimeCombo.SetEditable()

        elif mode == "adjdue":
            # Adjust Due | Editable | Editable | Read-only
            if start is None:
                log_step("WARNING: adjdue mode but Start-Date does not exist", prefix="DURATION")
            if due is None:
                log_step("WARNING: adjdue mode but Due-Date does not exist", prefix="DURATION")
            self._plannedStartDateTimeCombo.SetEditable()
            self._plannedDurationCtrl.Enable(True)
            self._plannedDurationCtrl.SetReadOnly(False)
            self._dueDateTimeCombo.SetReadOnly()

        elif mode == "adjstart":
            # Adjust Start | Read-only | Editable | Editable
            if start is None:
                log_step("WARNING: adjstart mode but Start-Date does not exist", prefix="DURATION")
            if due is None:
                log_step("WARNING: adjstart mode but Due-Date does not exist", prefix="DURATION")
            self._plannedStartDateTimeCombo.SetReadOnly()
            self._plannedDurationCtrl.Enable(True)
            self._plannedDurationCtrl.SetReadOnly(False)
            self._dueDateTimeCombo.SetEditable()

        elif mode == "implicit":
            # Start and Due always Editable
            self._plannedStartDateTimeCombo.SetEditable()
            self._dueDateTimeCombo.SetEditable()
            if start is not None and due is not None:
                # Both dates exist: Duration Read-only
                self._plannedDurationCtrl.Enable(True)
                self._plannedDurationCtrl.SetReadOnly(True)
            else:
                # One or both dates missing: Duration Disabled
                self._plannedDurationCtrl.Enable(False)

        # Presets enabled in all modes except Implicit (per UI Field States table)
        self._durationPresetsChoice.Enable(mode != "implicit")

    def __setDurationMode(self, newMode):
        """Set the duration mode and update dropdown."""
        if newMode == self._currentPlannedDurationMode:
            return
        self._currentPlannedDurationMode = newMode
        # Update dropdown to reflect available choices and selection
        self.__updateDurationModeDropdown()
        # Save mode change
        cmd = command.EditPlannedDurationModeCommand(
            items=self.items, newValue=newMode
        )
        cmd.do()

    def __strikethrough(self, text):
        """Apply Unicode strikethrough effect using combining character U+0336."""
        return ''.join(char + '\u0336' for char in text)

    def __updateDurationModeDropdown(self):
        """Update the duration mode dropdown based on current mode.

        See docs/DURATION_CALCULATIONS.md "Calculation Mode Dropdown Build Logic".
        Rule: If current mode is Automatic, enable Automatic option; otherwise disable it.
        """
        self._automaticModeDisabled = self._currentPlannedDurationMode != "automatic"

        # Rebuild dropdown with updated labels
        self._durationModeChoice.Clear()
        for key, label in self._durationModeChoices:
            if key == "automatic" and self._automaticModeDisabled:
                # Show as disabled with strikethrough
                label = self.__strikethrough(_("Automatic"))
            self._durationModeChoice.Append(label, key)

        # Set selection to current mode
        for idx, (key, label) in enumerate(self._durationModeChoices):
            if key == self._currentPlannedDurationMode:
                self._durationModeChoice.SetSelection(idx)
                return

        self._durationModeChoice.SetSelection(0)

    def __onDurationModeChanged(self, event):
        """Handle manual mode dropdown change."""
        selection = self._durationModeChoice.GetSelection()
        newMode = self._durationModeChoice.GetClientData(selection)

        # Prevent selecting disabled Automatic mode (both dates checked)
        if newMode == "automatic" and getattr(self, '_automaticModeDisabled', False):
            self.__updateDurationModeDropdown()  # Revert visual
            return

        # Set the mode (if different) - __syncTaskState will handle any forcing
        if newMode != self._currentPlannedDurationMode:
            self._currentPlannedDurationMode = newMode
            cmd = command.EditPlannedDurationModeCommand(
                items=self.items, newValue=newMode
            )
            cmd.do()

        # Sync state - handles mode forcing per Decision Tree and field states
        self.__syncTaskState()

        # Always update dropdown to show actual mode (may differ from selection)
        self.__updateDurationModeDropdown()

    def addReminderEntry(self):
        """Add reminder entry using DateTimeComboCtrl."""
        reminderDateTime = (
            self.items[0].reminder()
            if len(self.items) == 1
            else date.DateTime()
        )
        self._currentReminderDateTime = reminderDateTime

        # value=None means no date set, value=datetime means date exists
        value = reminderDateTime if reminderDateTime != date.DateTime() else None

        self._reminderDateTimeCombo = widgets.DateTimeComboCtrl(
            self, value=value,
            suggestedValue=task.Task.suggestedReminderDateTime(),
            hourChoices=lambda: get_suggested_hour_choices(self._DatesPage__settings),
            minuteChoices=lambda: get_suggested_minute_choices(self._DatesPage__settings)
        )
        # Use AttributeSync for automatic external update handling
        # Sync on EVT_VALUE_CHANGED — fires on checkbox toggle AND date/time edits
        self._reminderDateTimeSync = attributesync.AttributeSync(
            "reminder",
            self._reminderDateTimeCombo,
            reminderDateTime,
            self.items,
            command.EditReminderDateTimeCommand,
            widgets.EVT_VALUE_CHANGED,
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
        # Place each recurrence sub-panel as its own grid row.
        # "Recurrence" label on the first row; empty label on the rest.
        recurrenceFlags = [None, wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND]
        panels = self._recurrenceEntry.getSubPanels()
        for i, panel in enumerate(panels):
            panel.Reparent(self)
            self.addEntry(
                _("Recurrence") if i == 0 else "",
                panel,
                flags=recurrenceFlags,
            )

    def entries(self):
        # pylint: disable=E1101
        # For DateTimeComboCtrl controls, return the date control as the focusable widget
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

class ProgressPage(Page):
    pageName = "progress"
    pageTitle = _("Progress")
    pageIcon = "nuvola_actions_go-last"

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
            flags=[None, wx.EXPAND],
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
            flags=[None, wx.EXPAND],
        )

    def entries(self):
        return dict(
            firstEntry=self._percentageCompleteEntry,
            percentageComplete=self._percentageCompleteEntry,
        )


class BudgetPage(ScrolledPage):
    pageName = "budget"
    pageTitle = _("Budget")
    pageIcon = "nuvola_apps_accessories-calculator"

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
        self._budgetEntry = widgets.MaskedDurationCtrl(
            self, showSeconds=True
        )
        self._budgetEntry.SetDuration(currentBudget)
        self._budgetSync = attributesync.AttributeSync(
            "budget",
            self._budgetEntry,
            currentBudget,
            self.items,
            command.EditBudgetCommand,
            widgets.EVT_VALUE_CHANGED,
            self.items[0].budgetChangedEventType(),
        )
        self.addEntry(
            _("Budget"), self._budgetEntry, flags=[None, wx.ALL]
        )

    def addTimeSpentEntry(self):
        assert len(self.items) == 1
        # pylint: disable=W0201
        self._timeSpentEntry = widgets.MaskedDurationCtrl(
            self, showSeconds=True
        )
        self._timeSpentEntry.SetDuration(self.items[0].timeSpent())
        self._timeSpentEntry.SetReadOnly(True)
        self.addEntry(
            _("Time spent"),
            self._timeSpentEntry,
            flags=[None, wx.ALL],
        )
        pub.subscribe(
            self.onTimeSpentChanged, self.items[0].timeSpentChangedEventType()
        )

    def onTimeSpentChanged(self, newValue, sender):
        if sender == self.items[0]:
            self._timeSpentEntry.SetDuration(sender.timeSpent())

    def addBudgetLeftEntry(self):
        assert len(self.items) == 1
        # pylint: disable=W0201
        self._budgetLeftEntry = widgets.MaskedDurationCtrl(
            self, showSeconds=True
        )
        self._budgetLeftEntry.SetDuration(self.items[0].budgetLeft())
        self._budgetLeftEntry.SetReadOnly(True)
        self.addEntry(
            _("Budget left"),
            self._budgetLeftEntry,
            flags=[None, wx.ALL],
        )
        pub.subscribe(
            self.onBudgetLeftChanged,
            self.items[0].budgetLeftChangedEventType(),
        )

    def onBudgetLeftChanged(self, newValue, sender):  # pylint: disable=W0613
        if sender == self.items[0]:
            self._budgetLeftEntry.SetDuration(sender.budgetLeft())

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
            widgets.EVT_VALUE_CHANGED,
            self.items[0].hourlyFeeChangedEventType(),
        )
        self.addEntry(
            _("Hourly fee"),
            self._hourlyFeeEntry,
            flags=[None, wx.ALL],
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
            widgets.EVT_VALUE_CHANGED,
            self.items[0].fixedFeeChangedEventType(),
        )
        self.addEntry(
            _("Fixed fee"), self._fixedFeeEntry, flags=[None, wx.ALL]
        )

    def addRevenueEntry(self):
        assert len(self.items) == 1
        revenue = self.items[0].revenue()
        self._revenueEntry = entry.AmountEntry(
            self, revenue, readonly=True
        )  # pylint: disable=W0201
        self.addEntry(
            _("Revenue"), self._revenueEntry, flags=[None, wx.ALL]
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
        result = dict(
            firstEntry=self._budgetEntry,
            budget=self._budgetEntry,
            hourlyFee=self._hourlyFeeEntry,
            fixedFee=self._fixedFeeEntry,
        )
        if len(self.items) == 1:
            result["budgetLeft"] = self._budgetLeftEntry
            result["revenue"] = self._revenueEntry
        return result


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
    pageIcon = "nuvola_apps_clock"

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

    def get_is_item_checked(self, category):  # pylint: disable=W0621
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

    def check_all_categories(self):
        """Assign all categories to the items being edited."""
        for cat in self.presentation():
            for item in self.__items:
                if cat not in item.categories():
                    item.addCategory(cat)
        self.widget.refreshAllCheckStates()

    def uncheck_all_categories(self):
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
    pageIcon = "nuvola_places_folder-downloads"

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
    pageIcon = "nuvola_status_mail-attachment"

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
    pageIcon = "nuvola_apps_knotes"

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

    def get_is_item_checked(self, item):
        return item in self.__items[0].prerequisites()

    def getIsItemCheckable(self, item):
        return item not in self.__items

    def onCheck(self, event, final):
        item = self.widget.GetItemPyData(event.GetItem())
        is_checked = event.GetItem().IsChecked()
        if is_checked != self.get_is_item_checked(item):
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
    pageIcon = "nuvola_apps_ksysv"

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


class PathPage(ScrolledPage):
    """Page that displays the hierarchical path (nesting) of the current object.

    The path is built only when the tab is selected (lazy loading).
    It subscribes to ALL modification events to catch any change that might
    affect the path, and rebuilds when the tab is visible.
    """

    pageName = "path"
    pageTitle = _("Path")
    pageIcon = "taskcoach_actions_arrow_down_right"
    columns = 1

    def __init__(self, items, parent, taskFile, *args, **kwargs):
        self._taskFile = taskFile
        self._pathPanel = None
        self._pathSizer = None
        self._subscribed = False
        self._realized = False
        self._iconWidgets = {}  # Dict of object -> StaticBitmap for icon updates
        self._iconSubscribed = False
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

        # Subscribe to effective icon changes for individual icon updates
        self._ensureIconSubscription()

        from taskcoachlib.domain import task, category, note, attachment, effort

        # Subscribe to parent pubsub topics (pubsub uses hierarchical topics)
        # This catches all child topic messages (e.g., pubsub.task covers
        # pubsub.task.subject, pubsub.task.dependencies, etc.)
        pubsub_parent_topics = [
            "pubsub.task",
            "pubsub.category",
            "pubsub.note",
            "pubsub.attachment",
        ]
        for topic in pubsub_parent_topics:
            pub.subscribe(self._onAnyChange, topic)

        # Subscribe to deprecated event types via patterns.Publisher
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
            if not eventType.startswith("pubsub"):
                patterns.Publisher().registerObserver(
                    self._onAnyChange,
                    eventType=eventType,
                )

    def _onAnyChange(self, event=None, **kwargs):
        """Called when any domain object changes. Rebuild if visible."""
        if self._realized and self._pathPanel:
            try:
                if self._pathPanel.IsShownOnScreen():
                    wx.CallAfter(self._rebuildPathDisplay)
            except RuntimeError:
                log_step("_onAnyChange: pathPanel dead %x" % id(self),
                         prefix="DEAD-OBJ")

    def _rebuildPathDisplay(self):
        """Rebuild the path display with all sections."""
        if not self._pathPanel or not self._pathSizer:
            return
        try:
            self._pathPanel.GetName()  # Check if still valid
        except RuntimeError:
            log_step("_rebuildPathDisplay: pathPanel dead %x" % id(self),
                     prefix="DEAD-OBJ")
            return

        # Unsubscribe existing icon handlers before clearing
        self._unsubscribeIconUpdates()

        # Clear existing content
        self._pathSizer.Clear(True)

        # Only show sections for single item
        if len(self.items) != 1:
            label = wx.StaticText(self._pathPanel,
                                  label=_("Path is only shown for single items"))
            self._pathSizer.Add(label, 0, wx.EXPAND)
            self._pathPanel.Layout()
            return

        item = self.items[0]

        # Section: Path
        self._buildPathSection(item)

        # Section: Categories (Tasks and Notes only)
        from taskcoachlib.domain import task as task_module, note
        if isinstance(item, (task_module.Task, note.Note)):
            self._buildCategoriesSection(item)

        # Section: Prerequisites (Tasks only)
        if isinstance(item, task_module.Task):
            self._buildPrerequisitesSection(item)

        # Section: Dependants (Tasks only)
        if isinstance(item, task_module.Task):
            self._buildDependantsSection(item)

        self._pathPanel.Layout()
        self.Layout()
        self.SetupScrolling(scroll_x=True, scroll_y=True)

    # -- Section builders --------------------------------------------------

    def _buildPathSection(self, item):
        """Build the Path section: header + hierarchical path display."""
        self._addSectionHeader(_("Path"))
        path_objects = self._buildPathObjects(item)

        if not path_objects:
            label = wx.StaticText(self._pathPanel,
                                  label=_("This item has no parent objects"))
            self._pathSizer.Add(label, 0, wx.EXPAND | wx.LEFT, 5)
            return

        for index, obj in enumerate(path_objects):
            obj_type, icon_id = self._getTypeInfo(obj)
            subject = obj.subject()

            item_panel = wx.Panel(self._pathPanel)
            item_sizer = wx.BoxSizer(wx.HORIZONTAL)

            # Add indentation based on depth
            if index > 0:
                indent = wx.Panel(item_panel, size=(index * 20, 1))
                item_sizer.Add(indent, 0)
                arrow_bitmap = icon_catalog.get_bitmap(
                    "taskcoach_actions_arrow_down_right", LIST_ICON_SIZE
                )
                if arrow_bitmap.IsOk():
                    arrow = wx.StaticBitmap(item_panel, bitmap=arrow_bitmap)
                    item_sizer.Add(arrow, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

            # Add type icon if available
            if icon_id:
                bitmap = icon_catalog.get_bitmap(icon_id, LIST_ICON_SIZE)
                if bitmap.IsOk():
                    icon = wx.StaticBitmap(item_panel, bitmap=bitmap)
                    item_sizer.Add(icon, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
                    self._subscribeIconToObject(obj, icon)

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

    def _buildCategoriesSection(self, item):
        """Build the Categories section: separator, header, category list."""
        self._addSectionSeparator()
        self._addSectionHeader(_("Categories"))
        categories = sorted(item.categories(), key=lambda c: c.subject())
        if not categories:
            self._addNoneLabel()
            return
        for cat in categories:
            # Build breadcrumb path: "Parent > Child > Grandchild"
            ancestors = cat.ancestors()
            if ancestors:
                display = " > ".join(a.subject() for a in ancestors)
                display += " > " + cat.subject()
            else:
                display = cat.subject()
            self._addItemRow(cat, display_text=display)

    def _buildPrerequisitesSection(self, item):
        """Build the Prerequisites section: separator, header, task list."""
        self._addSectionSeparator()
        self._addSectionHeader(_("Prerequisites"))
        prerequisites = sorted(item.prerequisites(), key=lambda t: t.subject())
        if not prerequisites:
            self._addNoneLabel()
            return
        for prereq in prerequisites:
            self._addItemRow(prereq)

    def _buildDependantsSection(self, item):
        """Build the Dependants section: separator, header, task list."""
        self._addSectionSeparator()
        self._addSectionHeader(_("Dependants"))
        dependants = sorted(item.dependencies(), key=lambda t: t.subject())
        if not dependants:
            self._addNoneLabel()
            return
        for dep in dependants:
            self._addItemRow(dep)

    # -- Shared helpers ----------------------------------------------------

    def _addSectionSeparator(self):
        """Add a horizontal line separator to the path panel."""
        line = wx.StaticLine(self._pathPanel)
        self._pathSizer.Add(line, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 8)

    def _addSectionHeader(self, title):
        """Add a bold section header to the path panel."""
        header = wx.StaticText(self._pathPanel, label=title)
        font = header.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        header.SetFont(font)
        self._pathSizer.Add(header, 0, wx.EXPAND | wx.BOTTOM, 4)

    def _addNoneLabel(self):
        """Add a '(none)' label for empty sections."""
        label = wx.StaticText(self._pathPanel, label=_("(none)"))
        self._pathSizer.Add(label, 0, wx.LEFT, 20)

    def _addItemRow(self, obj, display_text=None):
        """Add an item row with icon and label to the path panel."""
        obj_type, icon_id = self._getTypeInfo(obj)
        item_panel = wx.Panel(self._pathPanel)
        item_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Add type icon if available
        if icon_id:
            bitmap = icon_catalog.get_bitmap(icon_id, LIST_ICON_SIZE)
            if bitmap.IsOk():
                icon = wx.StaticBitmap(item_panel, bitmap=bitmap)
                item_sizer.Add(icon, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
                self._subscribeIconToObject(obj, icon)

        label_text = display_text or ("[%s] %s" % (obj_type, obj.subject()))
        label = wx.StaticText(item_panel, label=label_text)
        item_sizer.Add(label, 1, wx.ALIGN_CENTER_VERTICAL)

        item_panel.SetSizer(item_sizer)
        self._pathSizer.Add(item_panel, 0, wx.EXPAND | wx.ALL, 2)

    def _subscribeIconToObject(self, obj, bitmap):
        """Register a StaticBitmap for updates when object's effective icon changes."""
        if not hasattr(obj, 'effectiveIconChangedEventType'):
            return
        self._iconWidgets[id(obj)] = (obj, bitmap)

    def _ensureIconSubscription(self):
        """Subscribe to effective icon changes (once per rebuild)."""
        if self._iconSubscribed:
            return
        self._iconSubscribed = True
        self.registerObserver(
            self._onEffectiveIconChanged,
            eventType="effective.icon"
        )

    def _onEffectiveIconChanged(self, event):
        """Handle effective icon changes - update only the matching icon widget."""
        for source in event.sources():
            obj_id = id(source)
            if obj_id in self._iconWidgets:
                obj, bitmap = self._iconWidgets[obj_id]
                try:
                    _, icon_id = self._getTypeInfo(obj)
                    if icon_id:
                        new_bitmap = icon_catalog.get_bitmap(icon_id, LIST_ICON_SIZE)
                        if new_bitmap.IsOk():
                            bitmap.SetBitmap(new_bitmap)
                            bitmap.Refresh()
                except RuntimeError:
                    log_step("_onEffectiveIconChanged: icon widget dead %x" %
                             id(self), prefix="DEAD-OBJ")

    def _unsubscribeIconUpdates(self):
        """Clear icon widget tracking (subscription cleaned up on page close)."""
        self._iconWidgets = {}

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
        # Unsubscribe icon-specific handlers
        self._unsubscribeIconUpdates()

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
                    except Exception as e:
                        log_step("unsubscribe failed in %s.close: %s" %
                                 (self.__class__.__name__, e), prefix="DEAD-OBJ")
            patterns.Publisher().removeObserver(self._onAnyChange)
        super().close()

    def _getTypeInfo(self, obj):
        """Get the type name and effective icon for an object."""
        from taskcoachlib.domain import task as task_module
        from taskcoachlib.domain import category, note, attachment, effort

        if isinstance(obj, task_module.Task):
            return (_("Task"), obj.effectiveIcon())
        elif isinstance(obj, category.Category):
            return (_("Category"), obj.effectiveIcon())
        elif isinstance(obj, note.Note):
            return (_("Note"), obj.effectiveIcon())
        elif isinstance(obj, attachment.Attachment):
            return (_("Attachment"), obj.effectiveIcon())
        elif isinstance(obj, effort.Effort):
            return (_("Effort"), "nuvola_apps_clock")
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
            log_step("DateTimeEntry.GetValue: widget dead %x" % id(self),
                     prefix="DEAD-OBJ")
            return None

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
            log_step("DateTimeEntry.SetValue: widget dead %x" % id(self),
                     prefix="DEAD-OBJ")

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
        # Load from effort object, default to standard
        stored_mode = self.items[0].entryMode() if len(self.items) == 1 else "standard"
        self._effortEntryMode = {"standard": 0, "retroactive": 1, "implicit": 2}.get(stored_mode, 0)

        # --- Start row: Label, DateTime row (checkbox hidden), Button ---
        current_start_date_time = self.items[0].getStart()
        self._startDateTimeCombo = widgets.DateTimeComboCtrl(
            self,
            value=current_start_date_time,
            showSeconds=True,
            hourChoices=lambda: get_suggested_hour_choices(self._settings),
            minuteChoices=lambda: get_suggested_minute_choices(self._settings),
            secondChoices=lambda: get_suggested_second_choices(self._settings),
        )
        # Hide checkbox - start is always required
        self._startDateTimeCombo.HideCheckBox()

        self._startDateTimeSync = attributesync.AttributeSync(
            "getStart",
            self._startDateTimeCombo,
            current_start_date_time,
            self.items,
            command.EditEffortStartDateTimeCommand,
            widgets.EVT_VALUE_CHANGED,
            self.items[0].startChangedEventType(),
            callback=self.__onEffortStartChanged,
        )

        self._startFromLastEffortButton = self.__create_start_from_last_effort_button()

        self.addEntry(
            _("Start"),
            self._startDateTimeCombo.CreateRowPanel(self),
            self._startFromLastEffortButton,
            flags=[wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, wx.ALL | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL, wx.ALL | wx.ALIGN_CENTER_VERTICAL],
        )

        # --- Time Spent row (display only) ---
        # Get stop time early - needed for timer decision and duration calculation
        current_stop_date_time = self.items[0].getStop()

        # Calculate initial time spent
        if current_stop_date_time is not None:
            time_spent_duration = current_stop_date_time - current_start_date_time
            time_spent_seconds = max(0, int(time_spent_duration.total_seconds()))
        else:
            # Tracking - calculate from start to now
            now = date.DateTime.now()
            if current_start_date_time and now > current_start_date_time:
                time_spent_duration = now - current_start_date_time
                time_spent_seconds = int(time_spent_duration.total_seconds())
            else:
                time_spent_seconds = 0

        ts_hours = time_spent_seconds // 3600
        ts_minutes = (time_spent_seconds % 3600) // 60
        ts_seconds = time_spent_seconds % 60

        self._timeSpentCtrl = widgets.MaskedDurationCtrl(
            self,
            days=0, hours=ts_hours, minutes=ts_minutes, seconds=ts_seconds,
            showSeconds=True
        )
        # Initial state managed by __updateTimeSpentDisplay (called from __applyEffortEntryMode)

        self._timeSpentLabel = wx.StaticText(self, label=_("Calculated time spent until now"))
        self._timeSpentLabel.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        self._timeSpentTimer = None

        self.addEntry(
            _("Time spent"),
            self._timeSpentCtrl,
            self._timeSpentLabel,
            flags=[wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, wx.ALL | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL, wx.ALL | wx.ALIGN_CENTER_VERTICAL],
        )

        # --- Duration row ---
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
            showSeconds=True
        )
        # Standard mode: duration always active (start always exists)
        # Retroactive mode: duration inactive only if stop is inactive
        # Initial mode is Standard (0), so duration is always enabled at init
        current_duration = (current_stop_date_time - current_start_date_time) if current_stop_date_time is not None else date.TimeDelta()
        self._effortDurationSync = attributesync.AttributeSync(
            "duration",
            self._effortDurationCtrl,
            current_duration,
            self.items,
            command.EditEffortDurationCommand,
            widgets.EVT_VALUE_CHANGED,
            self.items[0].durationChangedEventType(),
            callback=self.__onEffortDurationChanged,
        )

        self._effortDurationPresetsChoice = wx.Choice(self)
        self.__populateEffortDurationPresets()
        self._effortDurationPresetsChoice.Bind(wx.EVT_CHOICE, self.__onEffortDurationPresetSelected)

        self.registerObserver(
            self.__onEffortPresetsConfigChanged,
            eventType="feature.effort_duration_presets",
            eventSource=self._settings,
        )
        if len(self.items) == 1:
            pub.subscribe(self.__onEffortDurationDomainChanged,
                          self.items[0].durationChangedEventType())

        # Entry mode dropdown (Standard / Retroactive) - placed next to presets
        self._effortEntryModeChoice = wx.Choice(self, choices=[_("Standard"), _("Retroactive"), _("Implicit")])
        self._effortEntryModeChoice.SetSelection(self._effortEntryMode)
        self._effortEntryModeChoice.Bind(wx.EVT_CHOICE, self.__onEffortEntryModeChanged)

        # Create panel with presets and entry mode dropdowns
        presets_and_mode_panel = wx.Panel(self)
        presets_and_mode_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._effortDurationPresetsChoice.Reparent(presets_and_mode_panel)
        self._effortEntryModeChoice.Reparent(presets_and_mode_panel)
        presets_and_mode_sizer.Add(self._effortDurationPresetsChoice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        presets_and_mode_sizer.Add(self._effortEntryModeChoice, 0, wx.ALIGN_CENTER_VERTICAL)
        presets_and_mode_panel.SetSizer(presets_and_mode_sizer)

        # Duration row: label, duration (right-aligned), presets+mode (left-aligned)
        self.addEntry(
            _("Duration"),
            self._effortDurationCtrl,
            presets_and_mode_panel,
            flags=[wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, wx.ALL | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL, wx.ALL | wx.ALIGN_CENTER_VERTICAL],
        )

        # --- Stop row: Label, DateTime row (with checkbox), Button ---
        self._stopDateTimeCombo = widgets.DateTimeComboCtrl(
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
            widgets.EVT_VALUE_CHANGED,
            self.items[0].stopChangedEventType(),
            callback=self.__onEffortStopChanged,
        )
        self._stopNowButton = self.__create_stop_now_button()

        self.addEntry(
            _("Stop"),
            self._stopDateTimeCombo.CreateRowPanel(self),
            self._stopNowButton,
            flags=[wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, wx.ALL | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL, wx.ALL | wx.ALIGN_CENTER_VERTICAL],
        )

        # --- Warning message ---
        self._invalidPeriodMessage = self.__create_invalid_period_message()
        self.addEntry(
            self._invalidPeriodMessage,
            flags=[wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND]
        )

        # Apply initial entry mode state (after all controls are created)
        self.__applyEffortEntryMode()

        # Layer 2: Subscribe to domain entryMode and duration changes
        if len(self.items) == 1:
            pub.subscribe(self._onDomainEntryModeChanged,
                          self.items[0].entryModeChangedEventType())

    def _onDomainEntryModeChanged(self, newValue, sender):
        """Layer 2: Domain entryMode changed externally."""
        if sender not in self.items:
            return
        mode_index = {"standard": 0, "retroactive": 1, "implicit": 2}.get(newValue, 0)
        self._effortEntryMode = mode_index
        self._effortEntryModeChoice.SetSelection(mode_index)
        self.__applyEffortEntryMode()

    def __onEffortDurationChanged(self, value):
        """AttributeSync callback: effort duration committed or changed externally."""
        self.__syncEffortState(sourceField='duration')

    def __onEffortStartChanged(self, value):
        """Called when start datetime is committed."""
        self.__syncEffortState(sourceField='start')

    def __onEffortStopChanged(self, value):
        """Called when stop datetime is committed."""
        self.__syncEffortState(sourceField='stop')

    def __onEffortEntryModeChanged(self, event):
        """Handle switching between Standard and Retroactive entry modes."""
        self._effortEntryMode = self._effortEntryModeChoice.GetSelection()
        new_mode = {0: "standard", 1: "retroactive", 2: "implicit"}.get(self._effortEntryMode, "standard")
        command.EditEffortEntryModeCommand(
            items=self.items, newValue=new_mode
        ).do()
        self.__applyEffortEntryMode()

    def __applyEffortEntryMode(self):
        """Apply the current entry mode to control states and recalculate values."""
        self.__syncEffortState(sourceField='mode')

    # --- Effort helpers (mirroring task pattern) ---


    def __setEffortEntryMode(self, new_mode):
        """Set entry mode, update dropdown, write through command.
        Mirrors __setDurationMode for tasks."""
        mode_index = {"standard": 0, "retroactive": 1, "implicit": 2}[new_mode]
        if mode_index == self._effortEntryMode:
            return
        self._effortEntryMode = mode_index
        self._effortEntryModeChoice.SetSelection(mode_index)
        command.EditEffortEntryModeCommand(
            items=self.items, newValue=new_mode
        ).do()

    def __syncEffortState(self, sourceField=None, depth=0):
        """Central sync function implementing the Effort Logic Flow.

        The logic flow is triggered by ONE user-initiated change at a time.
        The flow processes (including explicit loops) until it stabilizes.

        See docs/DURATION_CALCULATIONS.md "Edit Effort Window" section.
        Implements: __syncEffortState()
        Called on: Every change of Start-Date, Stop-Date, Duration, or Mode dropdown.

        Sync-mode guard [0.4] is set inline around multi-adjustment
        sequences (e.g. 1.9.1) to prevent re-entry from pubsub callbacks.
        Flag lives on the domain effort instance (SSOT), shared across windows.

        Args:
            sourceField: Which field triggered this sync:
                         'start', 'stop', 'duration', 'mode', or None (depth>0 loop).
                         Proxy for user-action — cannot differentiate user clicks from
                         system-triggered changes. See TODO item 4 in doc.
            depth: Recursive depth counter (doc 0.3).
                   0 = initial call from handler (default).
                   1 = explicit Loop call (sourceField=None, reads widget state).
                   >1 = error, exit immediately.
        """
        # 0.4 Sync-mode guard — flag on domain SSOT, shared across windows
        effort = self.items[0]
        if getattr(effort, '_effortSyncInProgress', False):
            return

        # 0.3 Recursive safety
        if depth > 1:
            # 0.3.4 Depth > 1 should never occur, log error, exit
            log_step("ERROR: __syncEffortState depth > 1 (%d), exiting" % depth, prefix="EFFORT")
            return
        if depth == 1 and sourceField is not None:
            # 0.3.3 depth==1 should never receive a sourceField, log error, continue
            log_step("ERROR: __syncEffortState depth==1 received sourceField=%s, expected None" % sourceField, prefix="EFFORT")

        # Read current widget state once — no step in a single pass
        # depends on values changed by a prior step in the same pass.
        start = self._startDateTimeCombo.GetDateTime()
        stop = self._stopDateTimeCombo.GetDateTime()
        duration = self._effortDurationCtrl.GetTimeDelta()
        total_seconds = int(duration.total_seconds()) if duration else 0

        if self._effortEntryMode == 0:  # 1. If Mode Standard
            # 1.3 Set Start-Date editable
            self._startDateTimeCombo.SetEditable()
            self._startFromLastEffortButton.Enable(
                self._effortList.maxDateTime() is not None
            )
            # 1.4 Set Duration editable
            self._effortDurationCtrl.Enable(True)
            self._effortDurationCtrl.SetReadOnly(False)
            # 1.5 Set Presets dropdown enabled [Ref1]

            # 1.6 If Duration Unset-Action, Then disable Stop-Date
            if sourceField == 'duration' and total_seconds == 0:
                self._stopDateTimeCombo.DeactivateValue()

            # 1.7 If Stop-Date Unset-Action, Then set Duration = 0
            elif sourceField == 'stop' and stop is None:
                self._effortDurationCtrl.SetDuration(date.TimeDelta())

            # 1.8 If Stop-Date Set-Action
            elif sourceField == 'stop' and stop is not None and total_seconds == 0:
                # 1.8.1 If Duration = 0, Then set Implicit mode, Loop
                self.__setEffortEntryMode("implicit")
                return self.__syncEffortState(None, depth=depth + 1)

            # 1.9 If Start-Date changed
            elif sourceField == 'start':
                # 1.9.1 If Duration > 0
                if total_seconds > 0:
                    # 1.9.1.1 Set Sync-Mode [0.4]
                    effort._effortSyncInProgress = True
                    try:
                        # 1.9.1.2 Adj Stop-Date (stop = start + duration)
                        if start is not None and duration is not None:
                            self._stopDateTimeCombo.ActivateValue(start + duration)
                        # 1.9.1.3 Adj Duration *Impossible* — see spec TODO
                    finally:
                        # 1.9.1.4 Unset Sync-Mode
                        effort._effortSyncInProgress = False
                # 1.9.2 If Duration = 0, Then do nothing

            # 1.10 If Duration changed and exists
            elif sourceField == 'duration':
                # 1.10.1 If Duration > 0
                if total_seconds > 0:
                    # 1.10.1.1 Enable Stop-Date
                    if stop is None:
                        self._stopDateTimeCombo.ActivateValue()
                    # 1.10.1.2 Adj Stop-Date (stop = start + duration)
                    if start is not None and duration is not None:
                        self._stopDateTimeCombo.ActivateValue(start + duration)
                # 1.10.2 If Duration = 0, Then disable Stop-Date
                # (already handled in 1.6 above)

            # 1.11 If Stop-Date changed and exists, Then adj Duration (duration = stop - start)
            elif sourceField == 'stop':
                if start is not None and stop is not None:
                    self._effortDurationCtrl.SetDuration(stop - start)

            # 1.12 If Duration = 0, Then Autoheal, Thus
            if total_seconds == 0:
                # 1.12.1 Not possible: Disable Stop-Date Conflicts [Ref3]
                pass
            # 1.13 If Duration > 0, Then Autoheal, Thus
            elif total_seconds > 0:
                # 1.13.1 Enable Stop-Date [0.1, 0.2]
                if sourceField != 'stop' and stop is None:
                    self._stopDateTimeCombo.ActivateValue()
                # 1.13.2 Adj Stop-Date [0.1, 0.2] (stop = start + duration)
                if sourceField != 'stop' and start is not None and duration is not None:
                    self._stopDateTimeCombo.ActivateValue(start + duration)
            # 1.14 If Duration < 0, Then Negative Durations permitted

        elif self._effortEntryMode == 1:  # 2. If Mode Retroactive
            # 2.3 Set Start-Date read-only
            self._startDateTimeCombo.SetReadOnly()
            self._startFromLastEffortButton.Enable(False)
            # 2.4 Set Duration editable
            self._effortDurationCtrl.Enable(True)
            self._effortDurationCtrl.SetReadOnly(False)
            # 2.5 Set Presets dropdown enabled [Ref1]

            # 2.6 If Duration Unset-Action, Then disable Stop-Date
            if sourceField == 'duration' and total_seconds == 0:
                self._stopDateTimeCombo.DeactivateValue()

            # 2.7 If Stop-Date Unset-Action, Then set Duration = 0
            elif sourceField == 'stop' and stop is None:
                self._effortDurationCtrl.SetDuration(date.TimeDelta())

            # 2.8 If Stop-Date changed and exists, Then adj Start-Date (start = stop - duration)
            elif sourceField == 'stop':
                if stop is not None and duration is not None:
                    self._startDateTimeCombo.ActivateValue(stop - duration)

            # 2.9 If Duration changed and exists
            elif sourceField == 'duration':
                # 2.9.1 If Duration > 0
                if total_seconds > 0:
                    # 2.9.1.1 Enable Stop-Date
                    if stop is None:
                        self._stopDateTimeCombo.ActivateValue()
                    # 2.9.1.2 Adj Start-Date (start = stop - duration)
                    if stop is not None and duration is not None:
                        self._startDateTimeCombo.ActivateValue(stop - duration)
                # 2.9.2 If Duration = 0, Then disable Stop-Date
                # (already handled in 2.6 above)

            # 2.10 If Duration = 0, Then Autoheal, Thus
            if total_seconds == 0:
                # 2.10.1 Not possible: Disable Stop-Date Conflicts [Ref2]
                pass
            # 2.11 If Duration > 0, Then Autoheal, Thus
            elif total_seconds > 0:
                # 2.11.1 Enable Stop-Date [0.1, 0.2]
                if sourceField != 'stop' and stop is None:
                    self._stopDateTimeCombo.ActivateValue()
                # 2.11.2 Adj Start-Date [0.1, 0.2] (start = stop - duration)
                if sourceField != 'start' and stop is not None and duration is not None:
                    self._startDateTimeCombo.ActivateValue(stop - duration)
            # 2.12 If Duration < 0, Then Negative Durations permitted

        elif self._effortEntryMode == 2:  # 3. If Mode Implicit
            # 3.3 Set Presets dropdown disabled [Ref1]
            # 3.4 Set Start-Date editable
            self._startDateTimeCombo.SetEditable()
            self._startFromLastEffortButton.Enable(
                self._effortList.maxDateTime() is not None
            )

            # 3.5 If Stop-Date does not exist, Disable Duration
            if stop is None:
                self._effortDurationCtrl.Enable(False)
                self._effortDurationCtrl.SetDuration(date.TimeDelta())

            # 3.6 If Stop-Date exists
            elif stop is not None:
                # 3.6.1 Enable Duration (Read-Only)
                self._effortDurationCtrl.Enable(True)
                self._effortDurationCtrl.SetReadOnly(True)
                # 3.6.2 Adj Duration (duration = stop - start)
                # 3.6.3 Negative Durations permitted
                if start is not None and stop is not None:
                    self._effortDurationCtrl.SetDuration(stop - start)
    

        self.__update_invalid_period_message()
        self.__updateFieldStates()

    def __updateFieldStates(self):
        """See UI Field States table in DURATION_CALCULATIONS.md.
        Currently only implements Time Spent and Presets dropdown."""
        # Presets: disabled in implicit, enabled otherwise [Ref1]
        if self._effortEntryMode == 2:  # Implicit
            self._effortDurationPresetsChoice.Enable(False)
        else:
            self._effortDurationPresetsChoice.Enable(True)
        # Preset auto-align
        self.__updateEffortPresetSelection()
        # Time Spent
        self.__updateTimeSpentDisplay()

    def __populateEffortDurationPresets(self):
        """Populate the effort duration presets dropdown from settings."""
        self._effortDurationPresetsChoice.Clear()
        self._effortDurationPresetsChoice.Append(_("Presets..."), None)  # Placeholder

        presets_str = self._settings.get("feature", "effort_duration_presets")
        if presets_str:
            presets = []
            for seconds_str in presets_str.split(","):
                try:
                    val = int(seconds_str.strip())
                    if val > 0:  # Only add non-zero presets
                        presets.append(val)
                except ValueError:
                    pass

            for total_seconds in sorted(presets):
                label = self.__formatEffortDurationPreset(total_seconds)
                self._effortDurationPresetsChoice.Append(label, total_seconds)

        self._effortDurationPresetsChoice.Append(_("Reset to zero"), 0)  # Reset option (last)

        self._effortDurationPresetsChoice.SetSelection(0)

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

    def __onEffortDurationDomainChanged(self, newValue, sender):
        """Domain duration changed — update preset dropdown to match."""
        if sender in self.items:
            self.__updateEffortPresetSelection()

    def __updateEffortPresetSelection(self):
        """Update preset dropdown to match current duration value."""
        if not hasattr(self, '_effortDurationCtrl'):
            return

        duration = self._effortDurationCtrl.GetDuration()
        current_seconds = int(duration.total_seconds())

        # Search for matching preset (start at 1 to skip placeholder, stop before last "Reset to zero")
        for i in range(1, self._effortDurationPresetsChoice.GetCount() - 1):
            preset_seconds = self._effortDurationPresetsChoice.GetClientData(i)
            if preset_seconds == current_seconds:
                self._effortDurationPresetsChoice.SetSelection(i)
                return

        # No match - reset to placeholder "Presets..."
        self._effortDurationPresetsChoice.SetSelection(0)

    def __onEffortDurationPresetSelected(self, event):
        """Handle selection of a duration preset.

        Presets route through duration change — set duration via command,
        then let __syncEffortState handle all derived adjustments.
        """
        idx = self._effortDurationPresetsChoice.GetSelection()
        if idx == 0:  # Placeholder selected
            return

        total_seconds = self._effortDurationPresetsChoice.GetClientData(idx)
        if total_seconds is None:
            return

        # SetDuration → EVT_VALUE_CHANGED → AttributeSync → command → pubsub → preset update
        self._effortDurationCtrl.SetDuration(date.TimeDelta(seconds=total_seconds))

    def __onEffortPresetsConfigChanged(self, event=None):
        """Handle changes to effort preset configuration."""
        self.__populateEffortDurationPresets()

    def __updateTimeSpentDisplay(self):
        """Enable/disable Time Spent and start/stop timer.

        Activated when tracking (no Stop-Date), deactivated when Stop-Date exists.
        See DURATION_CALCULATIONS.md "Time Spent" section.
        """
        if not hasattr(self, '_timeSpentCtrl'):
            return

        stop = self._stopDateTimeCombo.GetDateTime()
        if stop is not None:
            # Stop exists — deactivate time spent
            self._timeSpentCtrl.Enable(False)
            self.__stopTimeSpentTimer()
        else:
            # Tracking — activate time spent (read-only)
            self._timeSpentCtrl.Enable(True)
            self._timeSpentCtrl.SetReadOnly(True)
            self.__startTimeSpentTimer()

        self.__refreshTimeSpentValue()

    def __refreshTimeSpentValue(self):
        """Calculate and display Time Spent value (Now - Start).

        Called by timer every 1s and by __updateTimeSpentDisplay.
        """
        if not hasattr(self, '_timeSpentCtrl'):
            return

        start = self._startDateTimeCombo.GetDateTime()
        if start is None:
            self._timeSpentCtrl.SetDuration(datetime.timedelta(seconds=0))
            return

        stop = self._stopDateTimeCombo.GetDateTime()
        if stop is None:
            stop = date.DateTime.now()

        total_seconds = int((stop - start).total_seconds())
        self._timeSpentCtrl.SetDuration(datetime.timedelta(seconds=total_seconds))

    def __onTimeSpentTimer(self, event):
        """Timer handler — refresh value only, not enable/disable state."""
        self.__refreshTimeSpentValue()

    def __startTimeSpentTimer(self):
        """Start the timer for updating time spent display."""
        if self._timeSpentTimer is None:
            self._timeSpentTimer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self.__onTimeSpentTimer, self._timeSpentTimer)
            self._timeSpentTimer.Start(1000)

    def __stopTimeSpentTimer(self):
        """Stop the timer for updating time spent display."""
        if self._timeSpentTimer is not None:
            self._timeSpentTimer.Stop()
            self._timeSpentTimer = None

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
        text.SetForegroundColour(wx.RED)
        return text

    def onStartFromLastEffort(self, event):  # pylint: disable=W0613
        maxDateTime = self._effortList.maxDateTime()
        if maxDateTime is not None:
            self._startDateTimeCombo.ActivateValue(maxDateTime)

    def onStopNow(self, event):
        # Stop only the specific effort(s) being edited, not all efforts for the task
        self._stopDateTimeCombo.ActivateValue(datetime.datetime.now())

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
        warnings = []
        try:
            now = date.DateTime.now()
            start_value = self._startDateTimeCombo.GetValue()
            stop_value = None
            if self._stopDateTimeCombo.IsActive():
                stop_value = self._stopDateTimeCombo.GetValue()
            if stop_value is not None and start_value is not None and start_value >= stop_value:
                warnings.append(_("Warning: start date-time is after the stop date-time!"))
            if stop_value is not None and stop_value > now:
                warnings.append(_("Warning: stop date-time is in the future!"))
            if start_value is not None and start_value > now:
                warnings.append(_("Warning: start date-time is in the future!"))
        except AttributeError:
            pass  # Entries not created yet
        self._invalidPeriodMessage.SetLabel("  ".join(warnings))

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
            self, current_description, settings=self._settings
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
        if len(self.items) == 1:
            try:
                pub.unsubscribe(self.__onEffortDurationDomainChanged,
                                self.items[0].durationChangedEventType())
            except Exception as e:
                log_step("unsubscribe failed in %s.close_edit_book: %s" %
                         (self.__class__.__name__, e), prefix="DEAD-OBJ")
            try:
                pub.unsubscribe(self._onDomainEntryModeChanged,
                                self.items[0].entryModeChangedEventType())
            except Exception as e:
                log_step("unsubscribe failed in %s.close_edit_book: %s" %
                         (self.__class__.__name__, e), prefix="DEAD-OBJ")
        # Stop the time spent timer
        self.__stopTimeSpentTimer()


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
        # Controls fire EVT_VALUE_CHANGED on blur (user edits) and from
        # programmatic setters — AttributeSync commits immediately.

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
        # DO NOT call event.Skip() — we call Destroy() explicitly below.
        # Calling both is an anti-pattern: the default EVT_CLOSE handler
        # would run after Destroy(), accessing the dead dialog.
        self.Unbind(wx.EVT_CLOSE)
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
        # Clean up UICommands created in __create_ui_commands()
        self.__undo_command.unbind(self._interior, wx.ID_UNDO)
        self.__undo_command.removeInstance()
        self.__redo_command.unbind(self._interior, wx.ID_REDO)
        self.__redo_command.removeInstance()
        self.__new_effort_command.unbind(
            self._interior, self.__new_effort_id)
        self.__new_effort_command.removeInstance()
        IdProvider.put(self.__new_effort_id)
        IdProvider.put(self.__next_tab_id)
        IdProvider.put(self.__prev_tab_id)
        # Close any child Editor dialogs BEFORE Destroy(). Without
        # this, Destroy() cascades to children without sending
        # EVT_CLOSE, so their on_close_editor never runs — leaving
        # dangling observers, UICommands, and pubsub subscriptions
        # that cause C++ segfaults.
        for child in list(self.GetChildren()):
            if isinstance(child, Editor) and child is not self:
                child.Close()
        # Hide first to stop GTK rendering, then destroy on next
        # idle cycle. Direct Destroy() crashes in C++ deferred
        # destruction with GTK popup widgets (PopupTransientWindow,
        # GTKPopupFrame). Separating hide from destroy lets pending
        # GTK events settle. Same pattern as PYTHON3_MIGRATION_1.md.
        self.Hide()
        wx.CallAfter(self._deferred_destroy)

    def _deferred_destroy(self):
        """Destroy the editor after one event loop iteration.
        Called via wx.CallAfter from on_close_editor to let GTK
        process pending events before C++ widget destruction."""
        try:
            if self:
                self.Destroy()
        except RuntimeError:
            log_step("_deferred_destroy: already dead %x" % (
                id(self)), prefix="DEAD-OBJ")

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
                log_step("__close_if_item_is_deleted: dialog already dead/deleting %x" %
                         id(self), prefix="DEAD-OBJ")
                return
        except RuntimeError:
            log_step("__close_if_item_is_deleted: C++ object deleted %x" %
                     id(self), prefix="DEAD-OBJ")
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
