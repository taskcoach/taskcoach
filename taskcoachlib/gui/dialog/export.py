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

from taskcoachlib.tools import wxhelper
import wx
import datetime
from taskcoachlib.i18n import _
from wx.lib import sized_controls
from wx.lib.agw import hypertreelist, customtreectrl
from taskcoachlib import meta, widgets
from pubsub import pub


class ExportDialog(sized_controls.SizedDialog):
    """Base class for all export dialogs. Use control classes below to add
    features."""

    title = "Override in subclass"
    section = "export"

    def __init__(self, *args, **kwargs):
        self.window = args[0]
        self.settings = kwargs.pop("settings")
        super().__init__(
            title=self.title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            *args,
            **kwargs
        )
        pane = self.GetContentsPane()
        pane.SetSizerType("vertical")
        self.components = self.createInterior(pane)
        buttonSizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        self.SetButtonSizer(buttonSizer)
        wxhelper.getButtonFromStdDialogButtonSizer(buttonSizer, wx.ID_OK).Bind(
            wx.EVT_BUTTON, self.onOk
        )
        self.Fit()
        # Set starting size to 600x700 for better usability
        self.SetSize(600, 700)
        self.SetMinSize((500, 400))
        self.CentreOnParent()

    def createInterior(self, pane):
        raise NotImplementedError

    def exportableViewers(self):
        return self.window.viewer

    def activeViewer(self):
        return self.window.viewer.activeViewer()

    def options(self):
        result = dict()
        for component in self.components:
            result.update(component.options())
        return result

    def onOk(self, event):
        event.Skip()
        for component in self.components:
            component.saveSettings()


# Controls for adding behavior to the base export dialog:

ViewerPickedEvent, EVT_VIEWERPICKED = wx.lib.newevent.NewEvent()


class ViewerPicker(sized_controls.SizedPanel):
    """Control for adding a viewer chooser widget to the export dialog."""

    def __init__(self, parent, viewers, activeViewer):
        super().__init__(parent)
        self.SetSizerType("horizontal")
        self.createPicker()
        self.populatePicker(viewers)
        self.selectActiveViewer(viewers, activeViewer)

    def createPicker(self):
        label = wx.StaticText(self, label=_("Export items from:"))
        label.SetSizerProps(valign="center")
        self.viewerComboBox = wx.ComboBox(
            self, style=wx.CB_READONLY | wx.CB_SORT
        )  # pylint: disable=W0201
        self.viewerComboBox.Bind(wx.EVT_COMBOBOX, self.onViewerChanged)

    def populatePicker(self, viewers):
        self.titleToViewer = dict()  # pylint: disable=W0201
        for viewer in viewers:
            self.viewerComboBox.Append(viewer.title())  # pylint: disable=E1101
            # Would like to user client data in the combobox, but that
            # doesn't work on all platforms
            self.titleToViewer[viewer.title()] = viewer

    def selectActiveViewer(self, viewers, activeViewer):
        selectedViewer = (
            activeViewer if activeViewer in viewers else viewers[0]
        )
        self.viewerComboBox.SetValue(selectedViewer.title())

    def selectedViewer(self):
        return self.titleToViewer[self.viewerComboBox.GetValue()]

    def options(self):
        return dict(selectedViewer=self.selectedViewer())

    def onViewerChanged(self, event):
        event.Skip()
        wx.PostEvent(self, ViewerPickedEvent(viewer=self.selectedViewer()))

    def saveSettings(self):
        pass  # No settings to remember


class SelectionOnlyCheckBox(wx.CheckBox):
    """Control for adding a widget to the export dialog that lets the
    user choose between exporting all items or just the selected items."""

    def __init__(self, parent, settings, section, setting):
        super().__init__(parent, label=_("Export only the selected items"))
        self.settings = settings
        self.section = section
        self.setting = setting
        self.initializeCheckBox()

    def initializeCheckBox(self):
        selectionOnly = self.settings.getboolean(self.section, self.setting)
        self.SetValue(selectionOnly)

    def options(self):
        return dict(selectionOnly=self.GetValue())

    def saveSettings(self):
        self.settings.set(
            self.section,
            self.setting,  # pylint: disable=E1101
            str(self.GetValue()),
        )


class ColumnPicker(sized_controls.SizedPanel):
    """Control that lets the user select which columns should be used for
    exporting. Uses HyperTreeList with checkboxes for consistent UI."""

    def __init__(self, parent, viewer):
        super().__init__(parent)
        self.SetSizerType("vertical")
        self.SetSizerProps(expand=True, proportion=1)
        self._columnMap = {}  # Maps tree item to Column object
        self.createColumnPicker()
        self.populateFromViewer(viewer)

    def createColumnPicker(self):
        label = wx.StaticText(self, label=_("Columns to export:"))
        label.SetSizerProps(valign="top")

        agwStyle = (
            wx.TR_DEFAULT_STYLE
            | wx.TR_HIDE_ROOT
            | wx.TR_NO_BUTTONS
            | wx.TR_FULL_ROW_HIGHLIGHT
        )

        self.tree = hypertreelist.HyperTreeList(
            self,
            agwStyle=agwStyle
        )
        self.tree.SetSizerProps(expand=True, proportion=1)
        self.tree.AddColumn(_("Field"))

    # Indicator-only columns excluded from export per object type.
    # These columns only show icons (e.g. paperclip, note icon) and render
    # as empty strings — they have no meaningful data to export.
    EXCLUDED_EXPORT_COLUMNS = {
        "tasks": {"ordering", "notes", "attachments", "status", "statusIcon", "statusIconText"},
        "efforts": set(),
        "categories": {"ordering", "notes", "attachments"},
        "notes": {"ordering", "attachments"},
        "attachments": {"notes"},
    }

    def populateFromViewer(self, viewer, checkAll=False):
        """Populate columns from a viewer.

        Args:
            viewer: The viewer to get columns from
            checkAll: If True, check ALL columns (for 'All' exports).
                     If False, only check currently visible columns.
        """
        self.tree.DeleteAllItems()
        self._columnMap.clear()
        if viewer is None or not viewer.hasHideableColumns():
            self.tree.SetColumnWidth(0, 150)
            return
        root = self.tree.AddRoot("")
        visibleColumns = viewer.visibleColumns()
        objectType = getattr(viewer, 'coreObjectType', '')
        excluded = self.EXCLUDED_EXPORT_COLUMNS.get(objectType, set())
        headers = []
        for column in viewer.selectableColumns():
            if column.name() in excluded:
                continue
            item = self.tree.AppendItem(root, column.header(), ct_type=1)
            self._columnMap[id(item)] = column
            headers.append(column.header())
            if checkAll or column in visibleColumns:
                self.tree.CheckItem(item, True)
        self._sizeColumnsFromContent(headers)

    def selectedColumns(self):
        columns = []
        root = self.tree.GetRootItem()
        if not root or not root.IsOk():
            return columns
        item, cookie = self.tree.GetFirstChild(root)
        while item and item.IsOk():
            if self.tree.IsItemChecked(item):
                col = self._columnMap.get(id(item))
                if col:
                    columns.append(col)
            item, cookie = self.tree.GetNextChild(root, cookie)
        return columns

    def _sizeColumnsFromContent(self, headers):
        """Calculate column width from header text using DC text measurement."""
        dc = wx.ScreenDC()
        dc.SetFont(self.tree.GetMainWindow().GetFont())
        checkboxPad = 24
        colPad = 16
        maxWidth = 0
        for header in headers:
            w, _ = dc.GetTextExtent(header)
            maxWidth = max(maxWidth, w)
        self.tree.SetColumnWidth(0, max(maxWidth + checkboxPad + colPad, 150))

    def options(self):
        return dict(columns=self.selectedColumns())

    def saveSettings(self):
        pass  # No settings to save


class SeparateDateAndTimeColumnsCheckBox(wx.CheckBox):
    """Control that lets the user decide whether dates and times should be
    separated or kept together."""

    def __init__(self, parent, settings, section, setting):
        super().__init__(
            parent, label=_("Put task dates and times in separate columns")
        )
        self.settings = settings
        self.section = section
        self.setting = setting
        self.initializeCheckBox()

    def initializeCheckBox(self):
        separateDateAndTimeColumns = self.settings.getboolean(
            self.section, self.setting
        )
        self.SetValue(separateDateAndTimeColumns)

    def options(self):
        return dict(separateDateAndTimeColumns=self.GetValue())

    def saveSettings(self):
        self.settings.setboolean(self.section, self.setting, self.GetValue())


class SeparateCSSCheckBox(sized_controls.SizedPanel):
    """Control to let the user write CSS style information to a
    separate file instead of including it into the HTML file."""

    def __init__(self, parent, settings, section, setting):
        super().__init__(parent)
        self.SetSizerProps(expand=True)
        self.settings = settings
        self.section = section
        self.setting = setting
        self.createCheckBox()
        self.createHelpInformation()

    def createCheckBox(self):
        self.separateCSSCheckBox = wx.CheckBox(
            self,  # pylint: disable=W0201
            label=_("Write style information to a separate CSS file"),
        )
        separateCSS = self.settings.getboolean(self.section, self.setting)
        self.separateCSSCheckBox.SetValue(separateCSS)

    def createHelpInformation(self):
        self._helpText = (
            _("If a CSS file exists for the exported file, %(name)s will not overwrite it. "
              "This allows you to change the style information without losing your changes on the next export.")
            % meta.metaDict
        )
        self.infoText = wx.StaticText(self, label=self._helpText)
        self.infoText.SetSizerProps(expand=True)
        self.infoText.Wrap(380)
        self.Bind(wx.EVT_SIZE, self.onSize)

    def onSize(self, event):
        event.Skip()
        if hasattr(self, 'infoText') and hasattr(self, '_helpText'):
            width = self.GetClientSize().GetWidth()
            if width > 50:
                self.infoText.SetLabel(self._helpText)
                self.infoText.Wrap(width - 10)
                self.Layout()

    def options(self):
        return dict(separateCSS=self.separateCSSCheckBox.GetValue())

    def saveSettings(self):
        self.settings.set(
            self.section,
            self.setting,
            str(self.separateCSSCheckBox.GetValue()),
        )


# Export dialogs for different file types:


class ExportAsCSVDialog(ExportDialog):
    """Non-modal CSV export dialog with enhanced viewer picker."""

    title = _("Export as CSV")

    def __init__(self, *args, **kwargs):
        self._exportCallback = kwargs.pop("exportCallback", None)
        super().__init__(*args, **kwargs)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        cancelBtn = self.FindWindowById(wx.ID_CANCEL)
        if cancelBtn:
            cancelBtn.Bind(wx.EVT_BUTTON, self.onCancel)

    def createInterior(self, pane):
        from taskcoachlib.gui.viewer import (
            TaskViewer, EffortViewer, CategoryViewer, NoteViewer,
            AttachmentViewer
        )
        self._hiddenViewers = {}
        self._hiddenPanel = None

        self.viewerPicker = EnhancedViewerPicker(
            pane, self.window,
            supportedTypes=[TaskViewer, EffortViewer, CategoryViewer,
                            NoteViewer, AttachmentViewer]
        )
        self.viewerPicker.Bind(EVT_VIEWERPICKED, self.onViewerChanged)

        self.columnPicker = ColumnPicker(pane, None)
        self.separateDateAndTimeColumnsCheckBox = (
            SeparateDateAndTimeColumnsCheckBox(
                pane,
                self.settings,
                self.section,
                "csv_separatedateandtimecolumns",
            )
        )
        self._updateColumnPickerState()

        return (
            self.viewerPicker,
            self.columnPicker,
            self.separateDateAndTimeColumnsCheckBox,
        )

    def _getViewerForColumns(self, viewerClass):
        """Get a viewer for column definitions. Fallback chain:
        1. Find an existing open viewer matching coreObjectType
        2. Use cached hidden viewer
        3. Create a new hidden viewer instance
        """
        objectType = viewerClass.coreObjectType

        # 1. Search open viewers by coreObjectType
        for v in self.window.viewer:
            if getattr(v, 'coreObjectType', None) == objectType and v.hasHideableColumns():
                return v

        # 2. Check cached hidden viewers
        if viewerClass in self._hiddenViewers:
            return self._hiddenViewers[viewerClass]

        # 3. Create a hidden viewer
        if self._hiddenPanel is None:
            self._hiddenPanel = wx.Panel(self)
            self._hiddenPanel.Hide()
        kwargs = {}
        if objectType == "attachments":
            from taskcoachlib.domain.attachment import AttachmentList
            kwargs["attachmentsToShow"] = AttachmentList()
        hiddenViewer = viewerClass(
            self._hiddenPanel,
            self.window.taskFile,
            self.settings,
            **kwargs
        )
        hiddenViewer.Hide()
        self._hiddenViewers[viewerClass] = hiddenViewer
        return hiddenViewer

    def _destroyHiddenViewers(self):
        """Clean up any hidden viewers created for column definitions."""
        for viewer in self._hiddenViewers.values():
            try:
                viewer.detach()
            except Exception:
                pass
            try:
                viewer.Destroy()
            except Exception:
                pass
        self._hiddenViewers.clear()
        if self._hiddenPanel is not None:
            try:
                self._hiddenPanel.Destroy()
            except Exception:
                pass
            self._hiddenPanel = None

    def _updateColumnPickerState(self):
        """Update column picker and options based on viewer selection."""
        selected = self.viewerPicker.selectedViewer()
        viewerClass = self.viewerPicker.selectedViewerClass()

        if self.viewerPicker.isAllSelected():
            viewer = self._getViewerForColumns(viewerClass) if viewerClass else None
            self.columnPicker.populateFromViewer(viewer, checkAll=True)
        else:
            self.columnPicker.populateFromViewer(selected, checkAll=False)

        # Separate date/time only relevant for tasks and efforts
        hasDatetime = viewerClass is not None and viewerClass.coreObjectType in ("tasks", "efforts")
        self.separateDateAndTimeColumnsCheckBox.Enable(hasDatetime)

    def onViewerChanged(self, event):
        event.Skip()
        self._updateColumnPickerState()

    def onOk(self, event):
        for component in self.components:
            component.saveSettings()

        if self._exportCallback:
            exportOptions = self.options()
            selectedViewer = exportOptions.pop("selectedViewer")
            exportOptions["selectionOnly"] = not self.viewerPicker.isAllSelected()

            dateStr = datetime.date.today().strftime("%Y%m%d")
            exportOptions["defaultFilename"] = "%s-%s" % (
                self.viewerPicker.selectedTypeName(), dateStr
            )
            self._exportCallback(selectedViewer, **exportOptions)

        self._destroyHiddenViewers()
        self.Destroy()

    def onCancel(self, event):
        self._destroyHiddenViewers()
        self.Destroy()

    def onClose(self, event):
        self._destroyHiddenViewers()
        self.Destroy()


class EnhancedViewerPicker(sized_controls.SizedPanel):
    """Enhanced viewer picker with 'All' options and dynamic selection counts.

    Each export format declares what object types it supports via supportedTypes.
    The picker builds entries from this list, then searches open viewers to match."""

    def __init__(self, parent, mainWindow, supportedTypes):
        """Initialize the enhanced viewer picker.

        Args:
            parent: Parent window
            mainWindow: Main application window (for accessing viewers and taskFile)
            supportedTypes: List of viewer classes declaring what object types
                          this export format supports.
                          Example: [TaskViewer, EffortViewer]
                          Labels derived from cls.defaultTitle.
                          Markers derived from cls.coreObjectType.
        """
        super().__init__(parent)
        self.mainWindow = mainWindow
        self._supportedTypes = supportedTypes
        self.SetSizerType("horizontal")
        self._viewerMap = {}  # Maps display string to viewer or allMarker string
        self.createPicker()
        self.populatePicker()
        self._subscribeToSelectionChanges()
        topLevel = self.GetTopLevelParent()
        if topLevel:
            topLevel.Bind(wx.EVT_ACTIVATE, self._onDialogActivate)

    def createPicker(self):
        label = wx.StaticText(self, label=_("Export items from:"))
        label.SetSizerProps(valign="center")
        self.viewerComboBox = wx.Choice(self)
        self.viewerComboBox.Bind(wx.EVT_CHOICE, self.onViewerChanged)

    def _findOpenViewers(self):
        """Find open viewers matching each supported type using coreObjectType."""
        viewers = list(self.mainWindow.viewer)
        grouped = {}
        for viewerClass in self._supportedTypes:
            objectType = viewerClass.coreObjectType
            grouped[objectType] = [
                v for v in viewers
                if getattr(v, 'coreObjectType', None) == objectType
                and v.hasHideableColumns()
            ]
        return grouped

    def _getSelectionCount(self, viewer):
        """Get selection count for a viewer."""
        try:
            return len(viewer.curselection())
        except (RuntimeError, AttributeError):
            return 0

    def _buildEntries(self, groupedViewers):
        """Build dropdown entries from supported types and open viewers."""
        entries = []

        # Section 1: "All" entries - one per supported type, sorted by label
        allEntries = []
        for viewerClass in self._supportedTypes:
            label = _("%s (All)") % viewerClass.defaultTitle
            marker = "ALL_" + viewerClass.coreObjectType.upper()
            allEntries.append((label, marker))
        allEntries.sort(key=lambda x: x[0])
        entries.extend(allEntries)

        # Section 2: Open viewers matching supported types
        viewerEntries = []
        for viewerClass in self._supportedTypes:
            objectType = viewerClass.coreObjectType
            for viewer in groupedViewers.get(objectType, []):
                count = self._getSelectionCount(viewer)
                title = viewer.title()
                displayText = _("%s (%d selected)") % (title, count)
                viewerEntries.append((title, -count, displayText, viewer))

        if viewerEntries:
            entries.append(("---", None))
            viewerEntries.sort(key=lambda x: (x[0], x[1]))
            for title, negCount, displayText, viewer in viewerEntries:
                entries.append((displayText, viewer))

        return entries

    def populatePicker(self):
        """Populate the dropdown. Default selection is the first 'All' entry."""
        self.viewerComboBox.Clear()
        self._viewerMap.clear()

        groupedViewers = self._findOpenViewers()
        entries = self._buildEntries(groupedViewers)

        for displayText, viewerOrMarker in entries:
            if displayText == "---":
                self.viewerComboBox.Append("─" * 20)
            else:
                self.viewerComboBox.Append(displayText)
                self._viewerMap[displayText] = viewerOrMarker

        if self.viewerComboBox.GetCount() > 0:
            self.viewerComboBox.SetSelection(0)

    def _subscribeToSelectionChanges(self):
        """Subscribe to selection change events from all viewers."""
        pub.subscribe(self._onViewerStatusChanged, "viewer.status")

    def _onDialogActivate(self, event):
        """Rebuild dropdown when the export dialog gains focus."""
        event.Skip()
        if event.GetActive():
            self._onViewerStatusChanged()

    def _onViewerStatusChanged(self):
        """Handle viewer status changes (including selection changes)."""
        currentSelection = self.viewerComboBox.GetStringSelection()
        currentViewer = self._viewerMap.get(currentSelection)

        groupedViewers = self._findOpenViewers()
        entries = self._buildEntries(groupedViewers)

        self.viewerComboBox.Clear()
        self._viewerMap.clear()

        newSelectionIndex = 0
        for displayText, viewerOrMarker in entries:
            if displayText == "---":
                self.viewerComboBox.Append("─" * 20)
            else:
                self.viewerComboBox.Append(displayText)
                self._viewerMap[displayText] = viewerOrMarker
                if viewerOrMarker == currentViewer:
                    newSelectionIndex = self.viewerComboBox.GetCount() - 1

        if self.viewerComboBox.GetCount() > 0:
            self.viewerComboBox.SetSelection(newSelectionIndex)

    def selectedViewer(self):
        """Return the selected viewer instance or ALL_* marker string."""
        displayText = self.viewerComboBox.GetStringSelection()
        return self._viewerMap.get(displayText)

    def isAllSelected(self):
        """Return True if an 'All' option is selected."""
        selected = self.selectedViewer()
        return isinstance(selected, str)

    def selectedViewerClass(self):
        """Return the viewer class for the current selection."""
        selected = self.selectedViewer()
        for viewerClass in self._supportedTypes:
            marker = "ALL_" + viewerClass.coreObjectType.upper()
            if selected == marker:
                return viewerClass
            if hasattr(selected, 'coreObjectType') and selected.coreObjectType == viewerClass.coreObjectType:
                return viewerClass
        return None

    def selectedTypeName(self):
        """Return the type name for the current selection (for filenames)."""
        viewerClass = self.selectedViewerClass()
        if viewerClass:
            return viewerClass.defaultTitle
        return "Export"

    def options(self):
        return dict(selectedViewer=self.selectedViewer())

    def onViewerChanged(self, event):
        event.Skip()
        # Skip separator selections
        selection = self.viewerComboBox.GetStringSelection()
        if selection.startswith("─"):
            idx = self.viewerComboBox.GetSelection()
            if idx + 1 < self.viewerComboBox.GetCount():
                self.viewerComboBox.SetSelection(idx + 1)
            elif idx > 0:
                self.viewerComboBox.SetSelection(idx - 1)
        wx.PostEvent(self, ViewerPickedEvent(viewer=self.selectedViewer()))

    def saveSettings(self):
        pass

    def Destroy(self):
        try:
            pub.unsubscribe(self._onViewerStatusChanged, "viewer.status")
        except Exception:
            pass
        return super().Destroy()


class ICalendarFieldPicker(sized_controls.SizedPanel):
    """Control for selecting which fields to export in iCalendar format.
    Uses HyperTreeList with checkboxes."""

    # Field definitions: (field_key, taskcoach_label, icalendar_field, required, formatting, for_tasks, for_efforts)
    TASK_FIELDS = [
        ("uid", _("ID"), "UID", True, _("Internal identifier"), True, False),
        ("dtstamp", _("(auto-generated)"), "DTSTAMP", True, _("Current UTC timestamp"), True, False),
        ("summary", _("Subject"), "SUMMARY", False, _("Text, quoted"), True, False),
        ("description", _("Description"), "DESCRIPTION", False, _("Text, quoted"), True, False),
        ("dtstart", _("Planned start date"), "DTSTART", False, _("UTC datetime"), True, False),
        ("due", _("Due date"), "DUE", False, _("UTC datetime"), True, False),
        ("completed", _("Completion date"), "COMPLETED", False, _("UTC datetime"), True, False),
        ("categories", _("Categories"), "CATEGORIES", False, _("Comma-separated, recursive"), True, False),
        ("status", _("Status"), "STATUS", False, _("NEEDS-ACTION / IN-PROCESS / COMPLETED"), True, False),
        ("priority", _("Priority"), "PRIORITY", False, _("Number, capped at 3"), True, False),
        ("percent", _("Percent complete"), "PERCENT-COMPLETE", False, _("Integer 0-100"), True, False),
        ("created", _("Creation date"), "CREATED", False, _("UTC datetime"), True, False),
        ("lastmod", _("Modification date"), "LAST-MODIFIED", False, _("UTC datetime"), True, False),
    ]

    EFFORT_FIELDS = [
        ("uid", _("ID"), "UID", True, _("Internal identifier"), False, True),
        ("dtstamp", _("(auto-generated)"), "DTSTAMP", True, _("Current UTC timestamp"), False, True),
        ("summary", _("Subject"), "SUMMARY", False, _("Task subject, quoted"), False, True),
        ("description", _("Description"), "DESCRIPTION", False, _("Task description, quoted"), False, True),
        ("dtstart", _("Start"), "DTSTART", False, _("UTC datetime"), False, True),
        ("dtend", _("End"), "DTEND", False, _("UTC datetime"), False, True),
    ]

    def __init__(self, parent, forTasks=True):
        super().__init__(parent)
        self.SetSizerType("vertical")
        self.SetSizerProps(expand=True, proportion=1)
        self._forTasks = forTasks
        self._checkedFields = set()
        self._itemMap = {}  # Maps field_key to tree item
        self.createFieldPicker()
        self.populateFields()

    def createFieldPicker(self):
        label = wx.StaticText(self, label=_("Fields to export:"))
        label.SetSizerProps(valign="top")

        agwStyle = (
            wx.TR_DEFAULT_STYLE
            | wx.TR_HIDE_ROOT
            | wx.TR_NO_BUTTONS
            | wx.TR_FULL_ROW_HIGHLIGHT
            | customtreectrl.TR_AUTO_CHECK_CHILD
        )

        # Use default border style to match system theme
        self.tree = hypertreelist.HyperTreeList(
            self,
            agwStyle=agwStyle
        )
        self.tree.SetSizerProps(expand=True, proportion=1)

        # Add columns - widths will be auto-sized after population
        self.tree.AddColumn(_("Source Field"))
        self.tree.AddColumn(_("Output Field"))
        self.tree.AddColumn(_("Formatting"))

        self.tree.Bind(customtreectrl.EVT_TREE_ITEM_CHECKED, self.onItemChecked)

    def populateFields(self):
        """Populate the field list based on whether we're exporting tasks or efforts."""
        self.tree.DeleteAllItems()
        self._itemMap.clear()
        self._checkedFields.clear()

        root = self.tree.AddRoot("")
        fields = self.TASK_FIELDS if self._forTasks else self.EFFORT_FIELDS

        for field_key, tc_label, ical_field, required, formatting, for_tasks, for_efforts in fields:
            item = self.tree.AppendItem(root, tc_label, ct_type=1)
            self.tree.SetItemText(item, ical_field, 1)
            self.tree.SetItemText(item, formatting, 2)
            self._itemMap[field_key] = item

            # Check all items by default
            self.tree.CheckItem(item, True)
            self._checkedFields.add(field_key)

            # Disable required fields (greyed out but checked)
            if required:
                self.tree.EnableItem(item, False)

        # Size columns from text content (no deferred sizing needed)
        self._sizeColumnsFromContent()

    def _sizeColumnsFromContent(self):
        """Calculate column widths from field text using DC text measurement."""
        fields = self.TASK_FIELDS if self._forTasks else self.EFFORT_FIELDS
        dc = wx.ScreenDC()
        dc.SetFont(self.tree.GetMainWindow().GetFont())
        numCols = self.tree.GetColumnCount()
        maxWidths = [0] * numCols
        # Column 0 needs extra padding for checkbox (approx 24px)
        checkboxPad = 24
        colPad = 16  # General padding per column
        for field in fields:
            texts = [field[1], field[2], field[4]]  # tc_label, ical_field, formatting
            for col in range(numCols):
                w, _ = dc.GetTextExtent(texts[col])
                maxWidths[col] = max(maxWidths[col], w)
        for col in range(numCols):
            width = maxWidths[col] + colPad + (checkboxPad if col == 0 else 0)
            self.tree.SetColumnWidth(col, max(width, 100))

    def setForTasks(self, forTasks):
        """Switch between task and effort field lists."""
        if self._forTasks != forTasks:
            self._forTasks = forTasks
            self.populateFields()

    def onItemChecked(self, event):
        """Handle checkbox changes."""
        item = event.GetItem()
        # Find the field key for this item
        for field_key, treeItem in self._itemMap.items():
            if treeItem == item:
                if self.tree.IsItemChecked(item):
                    self._checkedFields.add(field_key)
                else:
                    self._checkedFields.discard(field_key)
                break
        event.Skip()

    def selectedFields(self):
        """Return set of selected field keys."""
        return self._checkedFields.copy()

    def options(self):
        return dict(selectedFields=self.selectedFields())

    def saveSettings(self):
        pass


class ExportAsICalendarDialog(ExportDialog):
    """Non-modal export dialog for iCalendar format.

    This dialog is non-modal to allow users to change selections in the
    main window while the export dialog is open."""

    title = _("Export as iCalendar")

    def __init__(self, *args, **kwargs):
        self._exportCallback = kwargs.pop("exportCallback", None)
        # Use non-modal style (no DIALOG_MODAL)
        super().__init__(*args, **kwargs)
        # Bind cancel button and close event
        self.Bind(wx.EVT_CLOSE, self.onClose)
        cancelBtn = self.FindWindowById(wx.ID_CANCEL)
        if cancelBtn:
            cancelBtn.Bind(wx.EVT_BUTTON, self.onCancel)

    def createInterior(self, pane):
        from taskcoachlib.gui.viewer import TaskViewer, EffortViewer
        self.viewerPicker = EnhancedViewerPicker(
            pane, self.window,
            supportedTypes=[TaskViewer, EffortViewer]
        )
        self.viewerPicker.Bind(EVT_VIEWERPICKED, self.onViewerChanged)

        # Determine initial field type based on active viewer
        forTasks = self.viewerPicker.selectedViewerClass() is TaskViewer
        self.fieldPicker = ICalendarFieldPicker(pane, forTasks=forTasks)

        return self.viewerPicker, self.fieldPicker

    def onOk(self, event):
        """Handle OK button - perform export and close dialog."""
        for component in self.components:
            component.saveSettings()

        if self._exportCallback:
            exportOptions = self.options()
            selectedViewer = exportOptions.pop("selectedViewer")
            exportOptions["selectionOnly"] = not self.viewerPicker.isAllSelected()

            dateStr = datetime.date.today().strftime("%Y%m%d")
            exportOptions["defaultFilename"] = "%s-%s" % (
                self.viewerPicker.selectedTypeName(), dateStr
            )
            self._exportCallback(selectedViewer, **exportOptions)

        self.Destroy()

    def onCancel(self, event):
        self.Destroy()

    def onClose(self, event):
        self.Destroy()

    def onViewerChanged(self, event):
        event.Skip()
        from taskcoachlib.gui.viewer import TaskViewer
        forTasks = self.viewerPicker.selectedViewerClass() is TaskViewer
        self.fieldPicker.setForTasks(forTasks)


class ExportAsHTMLDialog(ExportDialog):
    """Non-modal HTML export dialog with enhanced viewer picker."""

    title = _("Export as HTML")

    def __init__(self, *args, **kwargs):
        self._exportCallback = kwargs.pop("exportCallback", None)
        super().__init__(*args, **kwargs)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        cancelBtn = self.FindWindowById(wx.ID_CANCEL)
        if cancelBtn:
            cancelBtn.Bind(wx.EVT_BUTTON, self.onCancel)

    def createInterior(self, pane):
        from taskcoachlib.gui.viewer import (
            TaskViewer, EffortViewer, CategoryViewer, NoteViewer,
            AttachmentViewer
        )
        self._hiddenViewers = {}
        self._hiddenPanel = None

        self.viewerPicker = EnhancedViewerPicker(
            pane, self.window,
            supportedTypes=[TaskViewer, EffortViewer, CategoryViewer,
                            NoteViewer, AttachmentViewer]
        )
        self.viewerPicker.Bind(EVT_VIEWERPICKED, self.onViewerChanged)

        self.columnPicker = ColumnPicker(pane, None)
        separateCSSChooser = SeparateCSSCheckBox(
            pane, self.settings, self.section, "html_separatecss"
        )
        self._updateColumnPickerState()

        return (
            self.viewerPicker,
            self.columnPicker,
            separateCSSChooser,
        )

    def _getViewerForColumns(self, viewerClass):
        """Get a viewer for column definitions. Fallback chain:
        1. Find an existing open viewer matching coreObjectType
        2. Use cached hidden viewer
        3. Create a new hidden viewer instance
        """
        objectType = viewerClass.coreObjectType

        for v in self.window.viewer:
            if getattr(v, 'coreObjectType', None) == objectType and v.hasHideableColumns():
                return v

        if viewerClass in self._hiddenViewers:
            return self._hiddenViewers[viewerClass]

        if self._hiddenPanel is None:
            self._hiddenPanel = wx.Panel(self)
            self._hiddenPanel.Hide()
        kwargs = {}
        if objectType == "attachments":
            from taskcoachlib.domain.attachment import AttachmentList
            kwargs["attachmentsToShow"] = AttachmentList()
        hiddenViewer = viewerClass(
            self._hiddenPanel,
            self.window.taskFile,
            self.settings,
            **kwargs
        )
        hiddenViewer.Hide()
        self._hiddenViewers[viewerClass] = hiddenViewer
        return hiddenViewer

    def _destroyHiddenViewers(self):
        """Clean up any hidden viewers created for column definitions."""
        for viewer in self._hiddenViewers.values():
            try:
                viewer.detach()
            except Exception:
                pass
            try:
                viewer.Destroy()
            except Exception:
                pass
        self._hiddenViewers.clear()
        if self._hiddenPanel is not None:
            try:
                self._hiddenPanel.Destroy()
            except Exception:
                pass
            self._hiddenPanel = None

    def _updateColumnPickerState(self):
        """Update column picker based on viewer selection."""
        selected = self.viewerPicker.selectedViewer()
        viewerClass = self.viewerPicker.selectedViewerClass()

        if self.viewerPicker.isAllSelected():
            viewer = self._getViewerForColumns(viewerClass) if viewerClass else None
            self.columnPicker.populateFromViewer(viewer, checkAll=True)
        else:
            self.columnPicker.populateFromViewer(selected, checkAll=False)

    def onViewerChanged(self, event):
        event.Skip()
        self._updateColumnPickerState()

    def onOk(self, event):
        for component in self.components:
            component.saveSettings()

        if self._exportCallback:
            exportOptions = self.options()
            selectedViewer = exportOptions.pop("selectedViewer")
            exportOptions["selectionOnly"] = not self.viewerPicker.isAllSelected()

            dateStr = datetime.date.today().strftime("%Y%m%d")
            exportOptions["defaultFilename"] = "%s-%s" % (
                self.viewerPicker.selectedTypeName(), dateStr
            )
            self._exportCallback(selectedViewer, **exportOptions)

        self._destroyHiddenViewers()
        self.Destroy()

    def onCancel(self, event):
        self._destroyHiddenViewers()
        self.Destroy()

    def onClose(self, event):
        self._destroyHiddenViewers()
        self.Destroy()


class TodoTxtFieldMapping(sized_controls.SizedPanel):
    """Read-only field mapping display for Todo.txt export.
    Shows source fields, output format, and transformation details.
    All fields are required (checked but disabled)."""

    # (source_label, output_field, transformation)
    FIELDS = [
        (_("Priority"), "(A)", _("Number 1-26 mapped to letter A-Z")),
        (_("Completion date"), "X YYYY-MM-DD", _("Prefix 'X', date only")),
        (_("Planned start date"), "YYYY-MM-DD", _("Date only, time stripped")),
        (_("Subject"), _("text"), _("Recursive with arrow separator")),
        (_("Categories"), "@context +project", _("@ and + prefixed, spaces to underscores")),
        (_("Due date"), "due:YYYY-MM-DD", _("Key:value, date only")),
        (_("Task ID"), "tcid:<id>", _("Key:value, internal identifier")),
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self.SetSizerType("vertical")
        self.SetSizerProps(expand=True, proportion=1)
        self.createFieldMapping()
        self.populateFields()

    def createFieldMapping(self):
        label = wx.StaticText(self, label=_("Fields exported (all required):"))
        label.SetSizerProps(valign="top")

        agwStyle = (
            wx.TR_DEFAULT_STYLE
            | wx.TR_HIDE_ROOT
            | wx.TR_NO_BUTTONS
            | wx.TR_FULL_ROW_HIGHLIGHT
        )

        self.tree = hypertreelist.HyperTreeList(
            self,
            agwStyle=agwStyle
        )
        self.tree.SetSizerProps(expand=True, proportion=1)

        self.tree.AddColumn(_("Source Field"))
        self.tree.AddColumn(_("Output Field"))
        self.tree.AddColumn(_("Formatting"))

    def populateFields(self):
        self.tree.DeleteAllItems()
        root = self.tree.AddRoot("")

        for source_label, output_field, transformation in self.FIELDS:
            item = self.tree.AppendItem(root, source_label, ct_type=1)
            self.tree.SetItemText(item, output_field, 1)
            self.tree.SetItemText(item, transformation, 2)
            self.tree.CheckItem(item, True)
            self.tree.EnableItem(item, False)

        # Size columns from text content (no deferred sizing needed)
        self._sizeColumnsFromContent()

    def _sizeColumnsFromContent(self):
        """Calculate column widths from field text using DC text measurement."""
        dc = wx.ScreenDC()
        dc.SetFont(self.tree.GetMainWindow().GetFont())
        numCols = self.tree.GetColumnCount()
        maxWidths = [0] * numCols
        checkboxPad = 24
        colPad = 16
        for field in self.FIELDS:
            texts = [field[0], field[1], field[2]]
            for col in range(numCols):
                w, _ = dc.GetTextExtent(texts[col])
                maxWidths[col] = max(maxWidths[col], w)
        for col in range(numCols):
            width = maxWidths[col] + colPad + (checkboxPad if col == 0 else 0)
            self.tree.SetColumnWidth(col, max(width, 100))

    def options(self):
        return {}

    def saveSettings(self):
        pass


class ExportAsTodoTxtDialog(ExportDialog):
    """Non-modal Todo.txt export dialog with enhanced viewer picker."""

    title = _("Export as Todo.txt")

    def __init__(self, *args, **kwargs):
        self._exportCallback = kwargs.pop("exportCallback", None)
        super().__init__(*args, **kwargs)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        cancelBtn = self.FindWindowById(wx.ID_CANCEL)
        if cancelBtn:
            cancelBtn.Bind(wx.EVT_BUTTON, self.onCancel)

    def createInterior(self, pane):
        from taskcoachlib.gui.viewer import TaskViewer
        self.viewerPicker = EnhancedViewerPicker(
            pane, self.window,
            supportedTypes=[TaskViewer]
        )
        self.fieldMapping = TodoTxtFieldMapping(pane)
        return (self.viewerPicker, self.fieldMapping)

    def onOk(self, event):
        for component in self.components:
            component.saveSettings()

        if self._exportCallback:
            exportOptions = self.options()
            selectedViewer = exportOptions.pop("selectedViewer")
            exportOptions["selectionOnly"] = not self.viewerPicker.isAllSelected()

            dateStr = datetime.date.today().strftime("%Y%m%d")
            exportOptions["defaultFilename"] = "%s-%s" % (
                self.viewerPicker.selectedTypeName(), dateStr
            )
            self._exportCallback(selectedViewer, **exportOptions)

        self.Destroy()

    def onCancel(self, event):
        self.Destroy()

    def onClose(self, event):
        self.Destroy()
