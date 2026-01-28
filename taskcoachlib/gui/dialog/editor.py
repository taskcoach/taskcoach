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
        return wx.NullColour


def resolve_font(value):
    """Convert domain font value to wx.Font.

    Args:
        value: wx.Font, symbolic constant, or None

    Returns:
        wx.Font instance
    """
    if value == base.SYSTEM_FONT:
        return wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
    elif isinstance(value, wx.Font):
        return value
    elif value is None:
        return wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
    else:
        return value


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
            if operating_system.isWindows() and isinstance(
                the_entry, wx.TextCtrl
            ):
                # Scroll to left...
                the_entry.SetInsertionPoint(0)
            the_entry.SetSelection(-1, -1)  # Select all text
        except (AttributeError, TypeError):
            pass  # Not a TextCtrl

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
            if operating_system.isWindows() and isinstance(
                the_entry, wx.TextCtrl
            ):
                # Scroll to left...
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

    def addStylePriorityEntry(self):
        # pylint: disable=W0201
        currentPriority = (
            self.items[0].stylePriority() if len(self.items) == 1 else 0
        )
        self._stylePriorityEntry = widgets.SpinCtrl(
            self, size=(100, -1), value=currentPriority, min=0, max=99
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
        self.addEntry(
            _("Style priority"),
            self._stylePriorityEntry,
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
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


class TaskAppearancePage(ScrolledPage):
    """Appearance tab with scrollbar support for all domain object types."""
    pageName = "appearance"
    pageTitle = _("Appearance")
    pageIcon = "palette_icon"
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
        self._derivedIconNA = wx.StaticText(self._derivedIconPanel, label=_("N/A"))
        self._derivedIconNA.Bind(wx.EVT_NAVIGATION_KEY, rejectNav)
        self._derivedIconNA.Bind(wx.EVT_SET_FOCUS, rejectFocus)
        self._derivedIconNA.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        iconSizer.Add(self._derivedIconDisplay, 0, wx.ALIGN_CENTER_VERTICAL)
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
            bitmap = wx.ArtProvider.GetBitmap(iconValue, wx.ART_MENU, (16, 16))
            self._derivedIconDisplay.SetBitmap(bitmap)
            self._derivedIconDisplay.Show()
            self._derivedIconNA.Hide()
            self._derivedIconSource.SetLabel(iconSource)
        else:
            self._derivedIconDisplay.Hide()
            self._derivedIconNA.Show()
            self._derivedIconSource.SetLabel(_("N/A"))
        self._derivedIconPanel.Layout()

        # --- Foreground Color ---
        # fgValue is either a color tuple or base.SYSTEM_FG_COLOR constant
        # fgSource is either "[Category] Name" or "System Theme"
        derivedFgColour = resolve_color(fgValue)
        self._derivedFgPicker.SetColour(derivedFgColour)
        self._derivedFgPicker.Show()
        self._derivedFgSource.SetLabel(fgSource)

        # --- Background Color ---
        # bgValue is either a color tuple or base.SYSTEM_BG_COLOR constant
        # bgSource is either "[Category] Name" or "System Theme"
        derivedBgColour = resolve_color(bgValue)
        self._derivedBgPicker.SetColour(derivedBgColour)
        self._derivedBgPicker.Show()
        self._derivedBgSource.SetLabel(bgSource)

        # --- Font ---
        # fontValue is either a wx.Font or base.SYSTEM_FONT constant
        # fontSource is either "[Category] Name" or "System Theme"
        derivedFont = resolve_font(fontValue)
        self._derivedFontPicker.SetSelectedFont(derivedFont)
        self._derivedFontPicker.Show()
        self._derivedFontSource.SetLabel(fontSource)

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
        self._effectiveIconNA = wx.StaticText(self._effectiveIconPanel, label=_("N/A"))
        self._effectiveIconNA.Bind(wx.EVT_NAVIGATION_KEY, rejectNav)
        self._effectiveIconNA.Bind(wx.EVT_SET_FOCUS, rejectFocus)
        self._effectiveIconNA.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        iconSizer.Add(self._effectiveIconDisplay, 0, wx.ALIGN_CENTER_VERTICAL)
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
            bitmap = wx.ArtProvider.GetBitmap(iconValue, wx.ART_MENU, (16, 16))
            self._effectiveIconDisplay.SetBitmap(bitmap)
            self._effectiveIconDisplay.Show()
            self._effectiveIconNA.Hide()
            self._effectiveIconSource.SetLabel(iconSource)
        else:
            self._effectiveIconDisplay.Hide()
            self._effectiveIconNA.Show()
            self._effectiveIconSource.SetLabel(_("N/A"))
        self._effectiveIconPanel.Layout()

        # --- Foreground Color ---
        fgActual = item.effectiveFgColor()
        fgDefault = item.effectiveFgColorDefault()
        fgSource = item.effectiveFgColorSource()
        effectiveFgColour = resolve_color(fgActual if fgActual else fgDefault)
        self._effectiveFgPicker.SetColour(effectiveFgColour)
        self._effectiveFgSource.SetLabel(fgSource)

        # --- Background Color ---
        bgActual = item.effectiveBgColor()
        bgDefault = item.effectiveBgColorDefault()
        bgSource = item.effectiveBgColorSource()
        effectiveBgColour = resolve_color(bgActual if bgActual else bgDefault)
        self._effectiveBgPicker.SetColour(effectiveBgColour)
        self._effectiveBgSource.SetLabel(bgSource)

        # --- Font ---
        fontActual = item.effectiveFont()
        fontDefault = item.effectiveFontDefault()
        fontSource = item.effectiveFontSource()
        self._effectiveFontPicker.SetSelectedFont(resolve_font(fontActual if fontActual else fontDefault))
        self._effectiveFontSource.SetLabel(fontSource)

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
        currentIcon = self.items[0].icon() if len(self.items) == 1 else ""

        # Debug logging for Priority categories
        settings = self.GetParent().settings
        status_keys = ["activetasks", "latetasks", "completedtasks",
                       "overduetasks", "inactivetasks", "duesoontasks"]
        excluded = set()
        for key in status_keys:
            excluded.add(settings.gettext("icon", key))
            excluded.add(settings.gettext("icon_dark", key))
        excluded.discard("")
        self._iconEntry = entry.IconEntry(self, currentIcon, excluded_icons=excluded)
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
            _("Icon"), self._iconEntry, flags=[None, wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT]
        )

    def entries(self):
        return dict(
            firstEntry=self._iconEntry
        )  # pylint: disable=E1101

    def close(self):
        super().close()


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

    def close(self):
        if len(self.items) == 1 and hasattr(self, '_statusLabel'):
            try:
                pub.unsubscribe(self._onStatusMayHaveChanged,
                                self.items[0].statusChangedEventType())
            except Exception:
                pass
        super().close()

    def __onPlannedStartChanged(self, value):
        """AttributeSync callback for planned start date changes."""
        self._currentPlannedStartDateTime = value
        self.__onPlannedStartDateTimeChanged(value)

    def __onPlannedStartDateTimeChanged(self, value):
        """Called when planned start date changes - update based on mode."""
        if hasattr(self, '_currentPlannedDurationMode'):
            self.__syncDurationState()

    def __onDueDateChanged(self, value):
        """AttributeSync callback for due date changes."""
        self._currentDueDateTime = value
        self.__onDueDateTimeChanged(value)

    def __onDueDateTimeChanged(self, value):
        """Called when due date changes - update based on mode."""
        if hasattr(self, '_currentPlannedDurationMode'):
            self.__syncDurationState()

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
        icon_name = taskStatus.getBitmap(self.__settings)
        bitmap = wx.ArtProvider.GetBitmap(icon_name, wx.ART_MENU, (16, 16))
        if bitmap.IsOk():
            self._statusIcon.SetBitmap(bitmap)

        # Update text and foreground color only (no background painting)
        statusText = taskStatus.pluralLabel.replace(" tasks", "").replace("tasks", "").strip()
        self._statusLabel.SetLabel(statusText)
        self._statusLabel.SetForegroundColour(theTask.statusFgColor())

        # Update source explanation
        if hasattr(self, '_statusSource'):
            self._statusSource.SetLabel(statusSource)
            self._statusSource.InvalidateBestSize()

        # Relayout panel and parent to accommodate new text sizes
        self._statusLabel.InvalidateBestSize()
        self._statusPanel.Layout()
        self._statusPanel.Fit()
        self.Layout()

    def _onLocalValueChanged(self, event):
        """Handle live value changes in date fields."""
        source = event.GetEventObject()

        # Check if source belongs to planned start or due date combos
        isPlannedStartSource = self._plannedStartDateTimeCombo.ContainsControl(source)
        isDueDateSource = self._dueDateTimeCombo.ContainsControl(source)

        effectiveMode = self.__getEffectiveMode()

        if effectiveMode == "implicit":
            # Implicit: recalculate duration when either date changes
            if isPlannedStartSource or isDueDateSource:
                self.__updateImplicitDuration()
        elif effectiveMode == "adjdue":
            # Inputs: planned start, duration -> Output: due date
            # Only update Due if it's already checked (don't auto-enable on date value change)
            if isPlannedStartSource and self._dueDateTimeCombo.IsChecked():
                self.__updateDueDateLive()
        elif effectiveMode == "adjstart":
            # Inputs: due date, duration -> Output: planned start
            # Only update Start if it's already checked (don't auto-enable on date value change)
            if isDueDateSource and self._plannedStartDateTimeCombo.IsChecked():
                self.__updatePlannedStartLive()

        event.Skip()

    def _onDurationValueChanged(self, event):
        """Handle live value changes in duration control."""
        self.__updatePresetSelection()  # Match preset dropdown to current value

        # In implicit mode, duration is output not input (don't process as input)
        if self._currentPlannedDurationMode != "implicit":
            self.__syncDurationState(liveUpdate=True)

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

    def addDateEntries(self):
        # Create panel for planned date section with table layout
        self._addPlannedDateSection()
        self.addLine()
        self._addActualStartDateEntry()
        self._addCompletionDateEntry()

        # Now that all date entries exist, set initial enabled state
        if hasattr(self, '_currentPlannedDurationMode'):
            self.__syncDurationState()

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
        # Bind checkbox to track which date is activated first for auto mode detection
        self._plannedStartDateTimeCombo.GetCheckBox().Bind(wx.EVT_CHECKBOX, self.__onPlannedStartCheckboxChanged)
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
        # Duration is always enabled - mode is auto-determined by which date is activated first
        self._plannedDurationCtrl.Bind(
            wx.EVT_KILL_FOCUS, self.__onPlannedDurationChanged
        )
        # Bind value change for live calculated field updates
        self._plannedDurationCtrl.Bind(
            widgets.EVT_VALUE_CHANGED, self._onDurationValueChanged
        )
        # Rebuild dropdown when focus leaves this field
        self._plannedDurationCtrl.Bind(wx.EVT_KILL_FOCUS, self.__onDurationFieldKillFocus)

        # Presets dropdown
        self._durationPresetsChoice = wx.Choice(self)
        self.__populateDurationPresets()
        self._durationPresetsChoice.Bind(wx.EVT_CHOICE, self.__onDurationPresetSelected)
        # Rebuild mode dropdown when focus leaves preset dropdown
        self._durationPresetsChoice.Bind(wx.EVT_KILL_FOCUS, self.__onDurationFieldKillFocus)

        pub.subscribe(self.__onPresetsConfigChanged, "settings.feature.task_duration_presets")

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

        self._currentPlannedDuration = plannedDuration
        # Get stored mode from task, default to "automatic"
        storedMode = (
            self.items[0].plannedDurationMode()
            if len(self.items) == 1
            else "automatic"
        )
        # Convert old modes if needed (backward compatibility)
        if storedMode not in ["automatic", "implicit", "adjdue", "adjstart"]:
            storedMode = "automatic"
        self._currentPlannedDurationMode = storedMode

        # Set dropdown selection
        mode_index = 0
        for idx, (key, label) in enumerate(self._durationModeChoices):
            if key == storedMode:
                mode_index = idx
                break
        self._durationModeChoice.SetSelection(mode_index)

        # Create panel for presets + mode in last column
        durationRestPanel = wx.Panel(self)
        durationRestSizer = wx.BoxSizer(wx.HORIZONTAL)
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

        # Row 3: Due date (value already retrieved above)

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
        # Bind checkbox to track which date is activated first for auto mode detection
        self._dueDateTimeCombo.GetCheckBox().Bind(wx.EVT_CHECKBOX, self.__onDueDateCheckboxChanged)
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
        self.__syncDurationState()
        # Set initial presets state (enabled except in Implicit mode)
        self._durationPresetsChoice.Enable(self._currentPlannedDurationMode != "implicit")

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
        # Commit on checkbox toggle (same as focus loss)
        self._actualStartDateTimeCombo.GetCheckBox().Bind(wx.EVT_CHECKBOX, self.__onActualStartCheckboxChanged)

        self.addEntry(
            _("Actual start date"),
            self._actualStartDateTimeCombo.CreateRowPanel(self),
            wx.StaticText(self, label=""),
        )

    def __onActualStartCheckboxChanged(self, event):
        """Handle actual start checkbox toggle."""
        # Commit value to model immediately (checkbox toggle = focus loss)
        self._actualStartDateTimeSync.commit()
        event.Skip()

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
        # Commit on checkbox toggle (same as focus loss)
        self._completionDateTimeCombo.GetCheckBox().Bind(wx.EVT_CHECKBOX, self.__onCompletionCheckboxChanged)

        self.addEntry(
            _("Completion date"),
            self._completionDateTimeCombo.CreateRowPanel(self),
            wx.StaticText(self, label=""),
        )

    def __onCompletionCheckboxChanged(self, event):
        """Handle completion checkbox toggle."""
        # Commit value to model immediately (checkbox toggle = focus loss)
        self._completionDateTimeSync.commit()
        event.Skip()

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
        self.__updatePresetSelection()  # Match initial value

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

    def __onPresetsConfigChanged(self, value=""):
        """Called when duration presets change in preferences."""
        self.__populateDurationPresets()

    def __onDurationPresetSelected(self, event):
        """Handle preset selection from dropdown."""
        selection = self._durationPresetsChoice.GetSelection()
        if selection == 0:  # Placeholder selected
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

    def __getEffectiveMode(self):
        """Get the effective mode for calculations.

        In automatic mode, determines direction based on which dates are set.
        Returns: 'adjdue', 'adjstart', 'implicit', or None (no direction yet)
        """
        mode = self._currentPlannedDurationMode
        if mode == "implicit":
            return "implicit"
        elif mode in ("adjdue", "adjstart"):
            return mode
        else:  # automatic
            startSet = self._plannedStartDateTimeCombo.IsChecked()
            dueSet = self._dueDateTimeCombo.IsChecked()
            if startSet and not dueSet:
                return "adjdue"
            elif dueSet and not startSet:
                return "adjstart"
            elif startSet and dueSet:
                # Both set in automatic - default to adjdue
                return "adjdue"
            else:
                return None  # Neither set, no direction yet

    def __onPlannedStartCheckboxChanged(self, event):
        """Handle planned start checkbox toggle."""
        # Commit value to model immediately (checkbox toggle = focus loss)
        self._plannedStartDateTimeSync.commit()
        # 0.1 User unchecked Start-Date
        userAction = "start_unchecked" if not self._plannedStartDateTimeCombo.IsChecked() else None
        self.__syncDurationState(userAction=userAction)
        event.Skip()

    def __onDueDateCheckboxChanged(self, event):
        """Handle due date checkbox toggle."""
        # Commit value to model immediately (checkbox toggle = focus loss)
        self._dueDateTimeSync.commit()
        # 0.2 User unchecked Due-Date
        userAction = "due_unchecked" if not self._dueDateTimeCombo.IsChecked() else None
        self.__syncDurationState(userAction=userAction)
        event.Skip()

    def __onDurationFieldKillFocus(self, event):
        """Rebuild duration mode dropdown and update presets state when focus leaves fields.

        This handles both:
        - Mode dropdown rebuild (per Mode Dropdown Build Logic in docs)
        - Presets dropdown enable/disable (enabled except in Implicit mode)
        """
        self.__updateDurationModeDropdown()
        # Presets enabled in all modes except Implicit
        self._durationPresetsChoice.Enable(self._currentPlannedDurationMode != "implicit")
        event.Skip()

    def __syncDurationState(self, userAction=None, liveUpdate=False):
        """Sync duration state based on Logic Flow.

        See docs/DURATION_CALCULATIONS.md "Logic Flow" section.

        Args:
            userAction: The user action that triggered this sync (step 0):
                       - "start_unchecked": User unchecked Start-Date (0.1)
                       - "due_unchecked": User unchecked Due-Date (0.2)
                       - None: Other action (mode selected, value changed, etc.)
            liveUpdate: If True, only update display (no commands executed).
                       If False, execute commands to persist changes.
        """
        mode = self._currentPlannedDurationMode
        startChecked = self._plannedStartDateTimeCombo.IsChecked()
        dueChecked = self._dueDateTimeCombo.IsChecked()

        # === Logic Flow: Mode Transitions and Calculations ===

        if mode == "automatic":
            # 1.1 If Start-Date set, Then set Adj-Due mode, Loop
            if startChecked:
                self.__setDurationMode("adjdue")
                return self.__syncDurationState(userAction, liveUpdate)  # Loop
            # 1.2 If Due-Date set, Then set Adj-Start mode, Loop
            if dueChecked:
                self.__setDurationMode("adjstart")
                return self.__syncDurationState(userAction, liveUpdate)  # Loop

        elif mode == "adjdue":
            # 2.1 Activate Start-Date, If not unchecked by user [Ref2, 0.1]
            if userAction != "start_unchecked" and not startChecked:
                self._plannedStartDateTimeCombo.SetChecked(True)
                startChecked = True
            # 2.2 Activate Due-Date (Read-Only) [Ref2]
            if not dueChecked:
                self._dueDateTimeCombo.SetChecked(True)
                dueChecked = True
            # 2.6 If Start-Date disabled, Then deactivate Due-Date, set Automatic mode, Loop
            if not startChecked:
                self._dueDateTimeCombo.SetChecked(False)
                self.__setDurationMode("automatic")
                return self.__syncDurationState(userAction, liveUpdate)  # Loop
            # 2.4/2.5 Adj Due-Date (on Duration or Start-Date change)
            if liveUpdate:
                self.__updateDueDateLive()
            else:
                self.__updateDueDateFromDuration()

        elif mode == "adjstart":
            # 3.1 Activate Due-Date, If not unchecked by user [Ref2, 0.2]
            if userAction != "due_unchecked" and not dueChecked:
                self._dueDateTimeCombo.SetChecked(True)
                dueChecked = True
            # 3.2 Activate Start-Date (Read-Only) [Ref2]
            if not startChecked:
                self._plannedStartDateTimeCombo.SetChecked(True)
                startChecked = True
            # 3.6 If Due-Date disabled, Then deactivate Start-Date, set Automatic mode, Loop
            if not dueChecked:
                self._plannedStartDateTimeCombo.SetChecked(False)
                self.__setDurationMode("automatic")
                return self.__syncDurationState(userAction, liveUpdate)  # Loop
            # 3.4/3.5 Adj Start-Date (on Duration or Due-Date change)
            if liveUpdate:
                self.__updatePlannedStartLive()
            else:
                self.__updatePlannedStartFromDuration()

        elif mode == "implicit":
            # 4.2/4.3 Based on which dates are enabled
            startChecked = self._plannedStartDateTimeCombo.IsChecked()
            dueChecked = self._dueDateTimeCombo.IsChecked()
            if startChecked and dueChecked:
                # 4.2.1 Both enabled - adj Duration
                self.__updateImplicitDuration()
            # 4.3 If Start-Date disabled (or Due-Date disabled), Duration handled by __updateFieldStates

        # 5. Update Field States (See: UI Field States section)
        self.__updateFieldStates()

    def __updateFieldStates(self):
        """Update field enabled/disabled/readonly states based on current mode.

        See docs/DURATION_CALCULATIONS.md "UI Field States" table.
        Implements: __updateFieldStates()
        """
        mode = self._currentPlannedDurationMode
        startChecked = self._plannedStartDateTimeCombo.IsChecked()
        dueChecked = self._dueDateTimeCombo.IsChecked()

        if mode == "automatic":
            # Automatic | ❌ | ❌ | Editable | Editable | Editable
            self._plannedStartDateTimeCombo.Enable(True)
            self._plannedStartDateTimeCombo.SetEditable(True)
            self._plannedDurationCtrl.Enable(True)
            self._plannedDurationCtrl.SetReadOnly(False)
            self._dueDateTimeCombo.Enable(True)
            self._dueDateTimeCombo.SetEditable(True)

        elif mode == "adjdue":
            # Adjust Due | ✅ | ✅ | Editable + Check | Editable | Read-only + Check
            if not startChecked:
                log_step("WARNING: adjdue mode but Start not checked - logic flow should have set this", prefix="DURATION")
            if not dueChecked:
                log_step("WARNING: adjdue mode but Due not checked - logic flow should have set this", prefix="DURATION")
            self._plannedStartDateTimeCombo.SetChecked(True)
            self._plannedStartDateTimeCombo.Enable(True)
            self._plannedStartDateTimeCombo.SetEditable(True)
            self._plannedDurationCtrl.Enable(True)
            self._plannedDurationCtrl.SetReadOnly(False)
            self._dueDateTimeCombo.SetChecked(True)
            self._dueDateTimeCombo.Enable(True)
            self._dueDateTimeCombo.SetEditable(False)  # Read-only

        elif mode == "adjstart":
            # Adjust Start | ✅ | ✅ | Read-only + Check | Editable | Editable + Check
            if not startChecked:
                log_step("WARNING: adjstart mode but Start not checked - logic flow should have set this", prefix="DURATION")
            if not dueChecked:
                log_step("WARNING: adjstart mode but Due not checked - logic flow should have set this", prefix="DURATION")
            self._plannedStartDateTimeCombo.SetChecked(True)
            self._plannedStartDateTimeCombo.Enable(True)
            self._plannedStartDateTimeCombo.SetEditable(False)  # Read-only
            self._plannedDurationCtrl.Enable(True)
            self._plannedDurationCtrl.SetReadOnly(False)
            self._dueDateTimeCombo.SetChecked(True)
            self._dueDateTimeCombo.Enable(True)
            self._dueDateTimeCombo.SetEditable(True)

        elif mode == "implicit":
            # Start and Due always Editable
            self._plannedStartDateTimeCombo.Enable(True)
            self._plannedStartDateTimeCombo.SetEditable(True)
            self._dueDateTimeCombo.Enable(True)
            self._dueDateTimeCombo.SetEditable(True)
            if startChecked and dueChecked:
                # Implicit | ✅ | ✅ | Editable | Read-only | Editable
                self._plannedDurationCtrl.Enable(True)
                self._plannedDurationCtrl.SetReadOnly(True)
            else:
                # Implicit | other | Editable | Disabled | Editable
                self._plannedDurationCtrl.Enable(False)

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

        # Set the mode (if different) - syncDurationState will handle any forcing
        if newMode != self._currentPlannedDurationMode:
            self._currentPlannedDurationMode = newMode
            cmd = command.EditPlannedDurationModeCommand(
                items=self.items, newValue=newMode
            )
            cmd.do()

        # Sync state - handles mode forcing per Decision Tree and field states
        self.__syncDurationState()

        # Always update dropdown to show actual mode (may differ from selection)
        self.__updateDurationModeDropdown()
        # Update presets state (enabled except in Implicit mode)
        self._durationPresetsChoice.Enable(self._currentPlannedDurationMode != "implicit")

    def __updateImplicitDuration(self):
        """Calculate and display duration from planned start and due date (implicit mode)."""
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
            # One or both dates missing - show 0 (disabled)
            self._plannedDurationCtrl.Enable(False)
            self._plannedDurationCtrl.SetDuration(dt.timedelta())
            self.__updatePresetSelection()

    def __onPlannedDurationChanged(self, event):
        """Handle duration value change from the duration control."""
        self.__onPlannedDurationChangedInternal()
        event.Skip()  # Allow event to propagate to control's _onKillFocus

    def __onPlannedDurationChangedInternal(self):
        """Handle duration value change (called from event or preset selection)."""
        # In implicit mode, duration is calculated, not edited
        if self._currentPlannedDurationMode == "implicit":
            return

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

        # Update all duration-related state (fields, date calculations)
        self.__syncDurationState()

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
            flags=[None, wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND],
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
            pub.unsubscribe(self.__onPresetsConfigChanged, "settings.feature.task_duration_presets")
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
            return (_("Task"), obj.effectiveIcon() or "led_blue_icon")
        elif isinstance(obj, category.Category):
            return (_("Category"), obj.effectiveIcon() or "folder_blue_icon")
        elif isinstance(obj, note.Note):
            # Notes use icon(recursive=True) - no effectiveIcon() SSOT
            return (_("Note"), obj.icon(recursive=True) or "note_icon")
        elif isinstance(obj, attachment.Attachment):
            # Attachments have no inheritance
            return (_("Attachment"), obj.icon() or "paperclip_icon")
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
        # Load from effort object, default to standard
        storedMode = self.items[0].entryMode() if len(self.items) == 1 else "standard"
        self._effortEntryMode = {"standard": 0, "retroactive": 1, "implicit": 2}.get(storedMode, 0)

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
        # Deactivate when stop time exists, read-only (but not disabled) when tracking
        if current_stop_date_time is not None:
            self._timeSpentCtrl.Enable(False)
        else:
            self._timeSpentCtrl.SetReadOnly(True)

        self._timeSpentLabel = wx.StaticText(self, label=_("Calculated time spent until now"))
        self._timeSpentLabel.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        self._timeSpentTimer = None
        # Start timer only if effort is being tracked (no stop time)
        if current_stop_date_time is None:
            self._timeSpentTimer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self.__onTimeSpentTimer, self._timeSpentTimer)
            self._timeSpentTimer.Start(1000)  # Update every second

        self.addEntry(
            _("Time spent"),
            self._timeSpentCtrl,
            self._timeSpentLabel,
            flags=[None, None, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.ALL],
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
        self._effortDurationCtrl.Bind(widgets.EVT_VALUE_CHANGED, self.__onDurationValueChanged)
        self._effortDurationCtrl.Bind(wx.EVT_KILL_FOCUS, self.__onDurationKillFocus)

        self._effortDurationPresetsChoice = wx.Choice(self)
        self.__populateEffortDurationPresets()
        self._effortDurationPresetsChoice.Bind(wx.EVT_CHOICE, self.__onEffortDurationPresetSelected)

        pub.subscribe(self.__onEffortPresetsConfigChanged, "settings.feature.effort_duration_presets")

        # Entry mode dropdown (Standard / Retroactive) - placed next to presets
        self._effortEntryModeChoice = wx.Choice(self, choices=[_("Standard"), _("Retroactive"), _("Implicit")])
        self._effortEntryModeChoice.SetSelection(self._effortEntryMode)
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

        # Apply initial entry mode state (after all controls are created)
        self.__applyEffortEntryMode()

    def __onEffortStartChanged(self, value):
        """Called when start datetime is committed."""
        if self._updatingControls:
            return
        self._updatingControls = True
        try:
            self.__syncEffortState('start')
        finally:
            self._updatingControls = False

    def __onEffortStopChanged(self, value):
        """Called when stop datetime is committed."""
        if self._updatingControls:
            return
        self._updatingControls = True
        try:
            self.__syncEffortState('stop')
        finally:
            self._updatingControls = False

    def __onStartValueChanged(self, event):
        """Called when start value changes (live)."""
        if self._updatingControls:
            event.Skip()
            return
        self._updatingControls = True
        try:
            self.__syncEffortState('start')
        finally:
            self._updatingControls = False
        event.Skip()

    def __onStopValueChanged(self, event):
        """Called when stop value changes (live)."""
        if self._updatingControls:
            event.Skip()
            return
        self._updatingControls = True
        try:
            self.__syncEffortState('stop')
        finally:
            self._updatingControls = False
        event.Skip()

    def __onDurationValueChanged(self, event):
        """Called when duration is edited."""
        if self._updatingControls:
            event.Skip()
            return

        self._updatingControls = True
        try:
            self.__syncEffortState('duration')
        finally:
            self._updatingControls = False
        event.Skip()

    def __onDurationKillFocus(self, event):
        """Commit duration changes when focus is lost - syncs with other windows."""
        event.Skip()
        if self._updatingControls:
            return

        self._updatingControls = True
        try:
            if self._effortEntryMode == 1:  # Retroactive mode
                # In retroactive mode, only commit if stop is active
                if not self._stopDateTimeCombo.IsChecked():
                    return
                # Commit start time change
                command.EditEffortStartDateTimeCommand(
                    None, self.items, newValue=self._startDateTimeCombo.GetValue()
                ).do()
            else:  # Standard mode
                # Commit stop time change (stop may have been auto-enabled)
                if self._stopDateTimeCombo.IsChecked():
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
                # Enabling stop - set to now
                now = date.DateTime.now()
                start = self._startDateTimeCombo.GetDateTime()
                new_stop = start if start > now else now
                self._stopDateTimeCombo.SetDateTime(new_stop)
                # Sync based on mode
                self.__syncEffortState('stop')
                # Commit the change
                command.EditEffortStopDateTimeCommand(
                    None, self.items, newValue=self._stopDateTimeCombo.GetValue()
                ).do()
                # Stop timer - effort is no longer being tracked
                self.__stopTimeSpentTimer()
                # Deactivate time spent control
                self._timeSpentCtrl.Enable(False)
            else:
                # Disabling stop - duration stays enabled
                for item in self.items:
                    item.setStop(date.DateTime.max)
                self.__updateEffortPresetSelection()
                self.__update_invalid_period_message()
                self.__updateTimeSpentDisplay()
                # Start timer - effort is now being tracked
                self.__startTimeSpentTimer()
                # Enable time spent control but make it read-only (not editable)
                self._timeSpentCtrl.Enable(True)
                self._timeSpentCtrl.SetReadOnly(True)
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
            # Save mode to effort object
            newMode = {0: "standard", 1: "retroactive", 2: "implicit"}.get(self._effortEntryMode, "standard")
            command.EditEffortEntryModeCommand(
                items=self.items, newValue=newMode
            ).do()
            self.__applyEffortEntryMode()
        finally:
            self._updatingControls = False

    def __applyEffortEntryMode(self):
        """Apply the current entry mode to control states and recalculate values."""
        self.__syncEffortState('mode')

    def __syncEffortState(self, changed_field):
        """Central sync function implementing the Logic Flow.

        Called on every change of Start-Date, Stop-Date, Duration, or Mode.

        Args:
            changed_field: 'start', 'duration', 'stop', or 'mode'
        """
        is_standard = self._effortEntryMode == 0
        is_retroactive = self._effortEntryMode == 1
        stop_enabled = self._stopDateTimeCombo.IsChecked()

        start = self._startDateTimeCombo.GetDateTime()
        stop = self._stopDateTimeCombo.GetDateTime()
        duration = self._effortDurationCtrl.GetTimeDelta()
        total_seconds = int(duration.total_seconds()) if duration else 0

        if is_standard:
            # Auto-switch: if stop is active and duration is 0, switch to Implicit
            if stop_enabled and total_seconds == 0:
                self._effortEntryMode = 2
                self._effortEntryModeChoice.SetSelection(2)
                # Fall through to Implicit branch by re-calling
                self.__syncEffortState(changed_field)
                return

            # 1.2 Set Start-Date editable, Duration editable
            self._startDateTimeCombo.SetEditable(True)
            self._startFromLastEffortButton.Enable(
                self._effortList.maxDateTime() is not None
            )
            self._effortDurationCtrl.SetReadOnly(False)

            # 1.3 If Start-Date changed
            if changed_field == 'start':
                # 1.3.1 If Duration > 0, Then adj Stop-Date
                if total_seconds > 0 and start:
                    new_stop = start + duration
                    self._stopDateTimeCombo.SetDateTime(new_stop)

            # 1.4 If Duration changed
            elif changed_field == 'duration':
                # 1.4.1 If Duration > 0
                if total_seconds > 0:
                    # 1.4.1.1 Enable Stop-Date
                    if not stop_enabled:
                        self._stopDateTimeCombo.SetChecked(True)
                        self._stopDateTimeCombo.SetDateTime(date.DateTime.now())
                    # 1.4.1.2 Adj Stop-Date
                    if start:
                        new_stop = start + duration
                        self._stopDateTimeCombo.SetDateTime(new_stop)
                # 1.4.2 If Duration = 0, Then disable Stop-Date
                elif total_seconds == 0:
                    self._stopDateTimeCombo.SetChecked(False)

            # 1.5 If Stop-Date changed
            elif changed_field == 'stop':
                if stop and start:
                    # 1.5.1 If Stop-Date <= Start-Date
                    if stop <= start:
                        # 1.5.1.1 Set Stop-Date = Start-Date + 1s
                        new_stop = start + datetime.timedelta(seconds=1)
                        self._stopDateTimeCombo.SetDateTime(new_stop)
                        # 1.5.1.2 Adj Duration to 1s
                        self._effortDurationCtrl.SetDuration(datetime.timedelta(seconds=1), quiet=True)
                    # 1.5.2 If Stop-Date > Start-Date, Then adj Duration
                    else:
                        calc_duration = stop - start
                        calc_seconds = max(0, int(calc_duration.total_seconds()))
                        self._effortDurationCtrl.SetDuration(datetime.timedelta(seconds=calc_seconds), quiet=True)

        elif is_retroactive:
            # 2.2 Set Start-Date read-only, Duration editable
            self._startDateTimeCombo.SetEditable(False)
            self._startFromLastEffortButton.Enable(False)
            self._effortDurationCtrl.SetReadOnly(False)

            # 2.3 If Duration changed
            if changed_field == 'duration':
                # 2.3.1 If Duration > 0
                if total_seconds > 0:
                    # 2.3.1.1 Enable Stop-Date
                    if not stop_enabled:
                        self._stopDateTimeCombo.SetChecked(True)
                        self._stopDateTimeCombo.SetDateTime(date.DateTime.now())
                        stop = self._stopDateTimeCombo.GetDateTime()
                    # 2.3.1.2 Adj Start-Date
                    if stop:
                        new_start = stop - duration
                        self._startDateTimeCombo.SetDateTime(new_start)
                # 2.3.2 If Duration = 0, Then disable Stop-Date
                elif total_seconds == 0:
                    self._stopDateTimeCombo.SetChecked(False)

            # 2.4 If Stop-Date changed
            elif changed_field == 'stop':
                # 2.4.1 If Duration <= 0
                if total_seconds <= 0:
                    # 2.4.1.1 Set Duration to 1s
                    self._effortDurationCtrl.SetDuration(datetime.timedelta(seconds=1), quiet=True)
                    # 2.4.1.2 Set Start-Date = Stop-Date - 1s
                    if stop:
                        new_start = stop - datetime.timedelta(seconds=1)
                        self._startDateTimeCombo.SetDateTime(new_start)
                # 2.4.2 If Duration > 0, Then adj Start-Date
                elif total_seconds > 0 and stop:
                    new_start = stop - duration
                    self._startDateTimeCombo.SetDateTime(new_start)

        else:  # Implicit mode (mode == 2)
            # 3.2 Set Start-Date editable
            self._startDateTimeCombo.SetEditable(True)
            self._startFromLastEffortButton.Enable(
                self._effortList.maxDateTime() is not None
            )
            # 3.3 Set Duration read-only
            self._effortDurationCtrl.SetReadOnly(True)

            # 3.4 If Start-Date or Stop-Date changed (or mode switched)
            if changed_field in ('start', 'stop', 'mode'):
                if stop_enabled and stop and start:
                    if stop > start:
                        calc_duration = stop - start
                        calc_seconds = max(0, int(calc_duration.total_seconds()))
                        self._effortDurationCtrl.SetDuration(
                            datetime.timedelta(seconds=calc_seconds), quiet=True
                        )
                    else:
                        # Stop <= Start: set duration to 0
                        self._effortDurationCtrl.SetDuration(
                            datetime.timedelta(seconds=0), quiet=True
                        )

        self.__updateEffortPresetSelection()
        self.__update_invalid_period_message()
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

        # Search for matching preset (start at 1 to skip placeholder, stop before last "Reset to zero")
        for i in range(1, self._effortDurationPresetsChoice.GetCount() - 1):
            preset_seconds = self._effortDurationPresetsChoice.GetClientData(i)
            if preset_seconds == current_seconds:
                self._effortDurationPresetsChoice.SetSelection(i)
                return

        # No match - reset to placeholder "Presets..."
        self._effortDurationPresetsChoice.SetSelection(0)

    def __onEffortDurationPresetSelected(self, event):
        """Handle selection of a duration preset."""
        if self._updatingControls:
            return
        idx = self._effortDurationPresetsChoice.GetSelection()
        if idx == 0:  # Placeholder selected
            return

        total_seconds = self._effortDurationPresetsChoice.GetClientData(idx)
        if total_seconds is None:
            return

        self._updatingControls = True
        try:
            # Auto-switch from Implicit to Standard when a preset is selected
            if self._effortEntryMode == 2 and total_seconds > 0:
                self._effortEntryMode = 0
                self._effortEntryModeChoice.SetSelection(0)
                command.EditEffortEntryModeCommand(
                    items=self.items, newValue="standard"
                ).do()
                self._effortDurationCtrl.SetReadOnly(False)
                self._effortDurationPresetsChoice.Enable(True)

            # Update duration control
            self._effortDurationCtrl.SetDuration(datetime.timedelta(seconds=total_seconds), quiet=True)

            # Reset to zero: clear stop time for both modes
            if total_seconds == 0:
                self._stopDateTimeCombo.SetChecked(False)
                # Commit stop cleared (set to max to indicate no stop)
                for item in self.items:
                    item.setStop(date.DateTime.max)
                self.__update_invalid_period_message()
                # Reset dropdown back to "Presets..." (don't show "Reset to zero" as selected)
                self._effortDurationPresetsChoice.SetSelection(0)
                return

            if self._effortEntryMode == 1:  # Retroactive mode
                # Auto-enable stop if not already checked (set to now)
                if not self._stopDateTimeCombo.IsChecked():
                    self._stopDateTimeCombo.SetChecked(True)
                    self._stopDateTimeCombo.SetDateTime(date.DateTime.now())
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

    def __updateTimeSpentDisplay(self):
        """Update the Time Spent display control based on current start/stop times."""
        if not hasattr(self, '_timeSpentCtrl'):
            return
        if not hasattr(self, '_stopDateTimeCombo'):
            return

        start = self._startDateTimeCombo.GetDateTime()
        if start is None:
            self._timeSpentCtrl.SetDuration(datetime.timedelta(seconds=0), quiet=True)
            return

        # Get stop time, or use current time if effort is being tracked
        if self._stopDateTimeCombo.IsChecked():
            stop = self._stopDateTimeCombo.GetDateTime()
        else:
            stop = date.DateTime.now()

        if stop is None or start is None:
            self._timeSpentCtrl.SetDuration(datetime.timedelta(seconds=0), quiet=True)
            return

        # Calculate duration
        if stop > start:
            duration = stop - start
            total_seconds = int(duration.total_seconds())
        else:
            total_seconds = 0

        self._timeSpentCtrl.SetDuration(datetime.timedelta(seconds=total_seconds), quiet=True)

    def __onTimeSpentTimer(self, event):
        """Timer handler to update time spent display for tracking efforts."""
        self.__updateTimeSpentDisplay()

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
        return text

    def onStartFromLastEffort(self, event):  # pylint: disable=W0613
        self._updatingControls = True
        try:
            maxDateTime = self._effortList.maxDateTime()
            if self._startDateTimeCombo.GetValue() != maxDateTime:
                self._startDateTimeCombo.SetDateTime(maxDateTime)
                self._startDateTimeSync.onAttributeEdited(event)
            self.__syncEffortState('start')
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
            self.__syncEffortState('stop')
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
        try:
            pub.unsubscribe(self.__onEffortPresetsConfigChanged, "settings.feature.effort_duration_presets")
        except Exception:
            pass
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
