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
        # Set starting size to 500x700 for better usability
        self.SetSize(500, 700)
        self.SetMinSize((400, 400))
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
    exporting."""

    def __init__(self, parent, viewer):
        super().__init__(parent)
        self.SetSizerType("horizontal")
        self.SetSizerProps(expand=True, proportion=1)
        self.createColumnPicker()
        self.populateColumnPicker(viewer)

    def createColumnPicker(self):
        label = wx.StaticText(self, label=_("Columns to export:"))
        label.SetSizerProps(valign="top")
        self.columnPicker = widgets.CheckListBox(self)  # pylint: disable=W0201
        self.columnPicker.SetSizerProps(expand=True, proportion=1)

    def populateColumnPicker(self, viewer):
        self.columnPicker.Clear()
        self.fillColumnPicker(viewer)

    def fillColumnPicker(self, viewer):
        if not viewer.hasHideableColumns():
            return
        visibleColumns = viewer.visibleColumns()
        for column in viewer.selectableColumns():
            if column.header():
                index = self.columnPicker.Append(
                    column.header(), clientData=column
                )
                self.columnPicker.Check(index, column in visibleColumns)

    def selectedColumns(self):
        indices = [
            index
            for index in range(self.columnPicker.GetCount())
            if self.columnPicker.IsChecked(index)
        ]
        return [self.columnPicker.GetClientData(index) for index in indices]

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
    title = _("Export as CSV")

    def createInterior(self, pane):
        viewerPicker = ViewerPicker(
            pane, self.exportableViewers(), self.activeViewer()
        )
        viewerPicker.Bind(EVT_VIEWERPICKED, self.onViewerChanged)
        # pylint: disable=W0201
        self.columnPicker = ColumnPicker(pane, viewerPicker.selectedViewer())
        selectionOnlyCheckBox = SelectionOnlyCheckBox(
            pane, self.settings, self.section, "csv_selectiononly"
        )
        self.separateDateAndTimeColumnsCheckBox = (
            SeparateDateAndTimeColumnsCheckBox(
                pane,
                self.settings,
                self.section,
                "csv_separatedateandtimecolumns",
            )
        )
        self.__check(viewerPicker.selectedViewer())
        return (
            viewerPicker,
            self.columnPicker,
            selectionOnlyCheckBox,
            self.separateDateAndTimeColumnsCheckBox,
        )

    def onViewerChanged(self, event):
        event.Skip()
        self.columnPicker.populateColumnPicker(event.viewer)
        self.__check(event.viewer)

    def __check(self, viewer):
        self.separateDateAndTimeColumnsCheckBox.Enable(
            viewer.isShowingTasks() or viewer.isShowingEffort()
        )


class ICalendarViewerPicker(sized_controls.SizedPanel):
    """Enhanced viewer picker for iCalendar export with 'All' options and
    dynamic selection counts."""

    # Special markers for "All" entries
    ALL_TASKS = "ALL_TASKS"
    ALL_EFFORTS = "ALL_EFFORTS"

    def __init__(self, parent, mainWindow, activeViewer):
        super().__init__(parent)
        self.mainWindow = mainWindow
        self.SetSizerType("horizontal")
        self._viewerMap = {}  # Maps display string to viewer or ALL_* constant
        self._subscriptions = []
        self.createPicker()
        self.populatePicker(activeViewer)
        self._subscribeToSelectionChanges()

    def createPicker(self):
        label = wx.StaticText(self, label=_("Export items from:"))
        label.SetSizerProps(valign="center")
        # Use wx.Choice instead of ComboBox - it's a true dropdown with no editable text field
        self.viewerComboBox = wx.Choice(self)
        self.viewerComboBox.Bind(wx.EVT_CHOICE, self.onViewerChanged)

    def _getOpenViewers(self):
        """Get open Task and Effort viewers."""
        viewers = list(self.mainWindow.viewer)
        taskViewers = [v for v in viewers if v.isShowingTasks()]
        effortViewers = [
            v for v in viewers
            if v.isShowingEffort() and not v.isShowingAggregatedEffort()
        ]
        return taskViewers, effortViewers

    def _getSelectionCount(self, viewer):
        """Get selection count for a viewer."""
        try:
            return len(viewer.curselection())
        except (RuntimeError, AttributeError):
            return 0

    def _buildSortedEntries(self, taskViewers, effortViewers):
        """Build sorted entries for the dropdown."""
        entries = []

        # Section 1: "All" entries (alphabetical)
        allEntries = [
            (_("Efforts (All)"), self.ALL_EFFORTS),
            (_("Tasks (All)"), self.ALL_TASKS),
        ]
        allEntries.sort(key=lambda x: x[0])
        entries.extend(allEntries)

        # Separator marker
        entries.append(("---", None))

        # Section 2: Open viewers
        # Group by type, alphabetical, then by selection count descending
        viewerEntries = []

        # Effort viewers
        for viewer in effortViewers:
            count = self._getSelectionCount(viewer)
            title = viewer.title()
            displayText = _("%s (%d selected)") % (title, count)
            # Sort key: (type for alpha sort, -count for descending)
            viewerEntries.append((title, -count, displayText, viewer))

        # Task viewers
        for viewer in taskViewers:
            count = self._getSelectionCount(viewer)
            title = viewer.title()
            displayText = _("%s (%d selected)") % (title, count)
            viewerEntries.append((title, -count, displayText, viewer))

        # Sort by title (alphabetical), then by -count (most selected first)
        viewerEntries.sort(key=lambda x: (x[0], x[1]))

        for title, negCount, displayText, viewer in viewerEntries:
            entries.append((displayText, viewer))

        return entries

    def populatePicker(self, activeViewer=None):
        """Populate the dropdown with sorted entries.

        Default selection is always the first item (an "All" choice)."""
        self.viewerComboBox.Clear()
        self._viewerMap.clear()

        taskViewers, effortViewers = self._getOpenViewers()
        entries = self._buildSortedEntries(taskViewers, effortViewers)

        for i, (displayText, viewerOrMarker) in enumerate(entries):
            if displayText == "---":
                # Add separator (visual only - wxComboBox doesn't support real separators)
                self.viewerComboBox.Append("─" * 20)
            else:
                self.viewerComboBox.Append(displayText)
                self._viewerMap[displayText] = viewerOrMarker

        # Default to first item (first "All" choice)
        if self.viewerComboBox.GetCount() > 0:
            self.viewerComboBox.SetSelection(0)

    def _subscribeToSelectionChanges(self):
        """Subscribe to selection change events from all viewers."""
        pub.subscribe(self._onViewerStatusChanged, "viewer.status")

    def _onViewerStatusChanged(self):
        """Handle viewer status changes (including selection changes)."""
        # Refresh the dropdown to update selection counts
        currentSelection = self.viewerComboBox.GetStringSelection()
        currentViewer = self._viewerMap.get(currentSelection)

        taskViewers, effortViewers = self._getOpenViewers()
        entries = self._buildSortedEntries(taskViewers, effortViewers)

        self.viewerComboBox.Clear()
        self._viewerMap.clear()

        newSelectionIndex = 0
        for i, (displayText, viewerOrMarker) in enumerate(entries):
            if displayText == "---":
                self.viewerComboBox.Append("─" * 20)
            else:
                self.viewerComboBox.Append(displayText)
                self._viewerMap[displayText] = viewerOrMarker

                # Try to keep the same viewer selected
                if viewerOrMarker == currentViewer:
                    newSelectionIndex = self.viewerComboBox.GetCount() - 1

        if self.viewerComboBox.GetCount() > 0:
            self.viewerComboBox.SetSelection(newSelectionIndex)

    def selectedViewer(self):
        """Return the selected viewer or ALL_* constant."""
        displayText = self.viewerComboBox.GetStringSelection()
        return self._viewerMap.get(displayText)

    def isAllSelected(self):
        """Return True if an 'All' option is selected."""
        selected = self.selectedViewer()
        return selected in (self.ALL_TASKS, self.ALL_EFFORTS)

    def isTasksSelected(self):
        """Return True if Tasks (All) or a Task viewer is selected."""
        selected = self.selectedViewer()
        if selected == self.ALL_TASKS:
            return True
        if selected and selected != self.ALL_EFFORTS:
            try:
                return selected.isShowingTasks()
            except AttributeError:
                pass
        return False

    def options(self):
        return dict(selectedViewer=self.selectedViewer())

    def onViewerChanged(self, event):
        event.Skip()
        # Skip separator selections
        selection = self.viewerComboBox.GetStringSelection()
        if selection.startswith("─"):
            # Move to next valid item
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

    # Field definitions: (field_key, taskcoach_label, icalendar_field, required, for_tasks, for_efforts)
    TASK_FIELDS = [
        ("uid", _("ID"), "UID", True, True, False),
        ("dtstamp", _("(auto-generated)"), "DTSTAMP", True, True, False),
        ("summary", _("Subject"), "SUMMARY", False, True, False),
        ("description", _("Description"), "DESCRIPTION", False, True, False),
        ("dtstart", _("Planned start date"), "DTSTART", False, True, False),
        ("due", _("Due date"), "DUE", False, True, False),
        ("completed", _("Completion date"), "COMPLETED", False, True, False),
        ("categories", _("Categories"), "CATEGORIES", False, True, False),
        ("status", _("Status"), "STATUS", False, True, False),
        ("priority", _("Priority"), "PRIORITY", False, True, False),
        ("percent", _("Percent complete"), "PERCENT-COMPLETE", False, True, False),
        ("created", _("Creation date"), "CREATED", False, True, False),
        ("lastmod", _("Modification date"), "LAST-MODIFIED", False, True, False),
    ]

    EFFORT_FIELDS = [
        ("uid", _("ID"), "UID", True, False, True),
        ("dtstamp", _("(auto-generated)"), "DTSTAMP", True, False, True),
        ("summary", _("Subject"), "SUMMARY", False, False, True),
        ("description", _("Description"), "DESCRIPTION", False, False, True),
        ("dtstart", _("Start"), "DTSTART", False, False, True),
        ("dtend", _("End"), "DTEND", False, False, True),
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
        self.tree.AddColumn(_("TaskCoach Field"))
        self.tree.AddColumn(_("iCalendar Field"))

        self.tree.Bind(customtreectrl.EVT_TREE_ITEM_CHECKED, self.onItemChecked)

    def populateFields(self):
        """Populate the field list based on whether we're exporting tasks or efforts."""
        self.tree.DeleteAllItems()
        self._itemMap.clear()
        self._checkedFields.clear()

        root = self.tree.AddRoot("")
        fields = self.TASK_FIELDS if self._forTasks else self.EFFORT_FIELDS

        for field_key, tc_label, ical_field, required, for_tasks, for_efforts in fields:
            # ct_type: 0=normal, 1=checkbox, 2=radiobutton
            item = self.tree.AppendItem(root, tc_label, ct_type=1)
            self.tree.SetItemText(item, ical_field, 1)
            self._itemMap[field_key] = item

            # Check all items by default
            self.tree.CheckItem(item, True)
            self._checkedFields.add(field_key)

            # Disable required fields (greyed out but checked)
            if required:
                self.tree.EnableItem(item, False)

        # Auto-size columns to fit content
        self._autoSizeColumns()

    def _autoSizeColumns(self):
        """Auto-size columns to fit their content."""
        for col in range(self.tree.GetColumnCount()):
            self.tree.SetColumnWidth(col, wx.LIST_AUTOSIZE)
            # Ensure minimum width for readability
            if self.tree.GetColumnWidth(col) < 100:
                self.tree.SetColumnWidth(col, 100)

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
        self.viewerPicker = ICalendarViewerPicker(
            pane, self.window, self.activeViewer()
        )
        self.viewerPicker.Bind(EVT_VIEWERPICKED, self.onViewerChanged)

        # Determine initial field type based on active viewer
        forTasks = self._isTasksSelected()
        self.fieldPicker = ICalendarFieldPicker(pane, forTasks=forTasks)

        # Note: "Selection only" checkbox removed - behavior is now implicit:
        # - "All" choices export all items
        # - Viewer choices export only selected items from that viewer

        return self.viewerPicker, self.fieldPicker

    def onOk(self, event):
        """Handle OK button - perform export and close dialog."""
        # Save settings
        for component in self.components:
            component.saveSettings()

        # Perform export if callback is set
        if self._exportCallback:
            exportOptions = self.options()
            selectedViewer = exportOptions.pop("selectedViewer")
            # Selection behavior is implicit based on dropdown choice:
            # - "All" choices: selectionOnly=False (handled by writer)
            # - Viewer choices: selectionOnly=True (export selected items)
            isAllChoice = self.viewerPicker.isAllSelected()
            exportOptions["selectionOnly"] = not isAllChoice

            # Generate default filename: Tasks-YYYYMMDD or Effort-YYYYMMDD
            dateStr = datetime.date.today().strftime("%Y%m%d")
            if self._isTasksSelected():
                exportOptions["defaultFilename"] = "Tasks-%s" % dateStr
            else:
                exportOptions["defaultFilename"] = "Effort-%s" % dateStr

            self._exportCallback(selectedViewer, **exportOptions)

        self.Destroy()

    def onCancel(self, event):
        """Handle Cancel button."""
        self.Destroy()

    def onClose(self, event):
        """Handle window close (X button)."""
        self.Destroy()

    def _isTasksSelected(self):
        """Check if Tasks are selected (All or viewer)."""
        return self.viewerPicker.isTasksSelected()

    def onViewerChanged(self, event):
        event.Skip()
        # Update field picker based on task/effort selection
        forTasks = self._isTasksSelected()
        self.fieldPicker.setForTasks(forTasks)

    def exportableViewers(self):
        """Not used for iCalendar - we use ICalendarViewerPicker instead."""
        viewers = super().exportableViewers()
        return [
            viewer
            for viewer in viewers
            if viewer.isShowingTasks()
            or (
                viewer.isShowingEffort()
                and not viewer.isShowingAggregatedEffort()
            )
        ]


class ExportAsHTMLDialog(ExportDialog):
    title = _("Export as HTML")

    def createInterior(self, pane):
        viewerPicker = ViewerPicker(
            pane, self.exportableViewers(), self.activeViewer()
        )
        viewerPicker.Bind(EVT_VIEWERPICKED, self.onViewerChanged)
        self.columnPicker = ColumnPicker(
            pane, viewerPicker.selectedViewer()
        )  # pylint: disable=W0201
        selectionOnlyCheckBox = SelectionOnlyCheckBox(
            pane, self.settings, self.section, "html_selectiononly"
        )
        separateCSSChooser = SeparateCSSCheckBox(
            pane, self.settings, self.section, "html_separatecss"
        )
        return (
            viewerPicker,
            self.columnPicker,
            selectionOnlyCheckBox,
            separateCSSChooser,
        )

    def onViewerChanged(self, event):
        event.Skip()
        self.columnPicker.populateColumnPicker(event.viewer)


class ExportAsTodoTxtDialog(ExportDialog):
    title = _("Export as Todo.txt")

    def createInterior(self, pane):
        viewerPicker = ViewerPicker(
            pane, self.exportableViewers(), self.activeViewer()
        )
        selectionOnlyCheckBox = SelectionOnlyCheckBox(
            pane, self.settings, self.section, "todotxt_selectiononly"
        )
        return viewerPicker, selectionOnlyCheckBox

    def exportableViewers(self):
        viewers = super().exportableViewers()
        return [viewer for viewer in viewers if viewer.isShowingTasks()]
