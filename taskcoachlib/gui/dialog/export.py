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
from taskcoachlib import meta
from taskcoachlib import patterns
from taskcoachlib.config import settings


class ExportDialog(sized_controls.SizedDialog):
    """Base class for all export dialogs. Use control classes below to add
    features."""

    title = "Override in subclass"
    section = "export"

    def __init__(self, *args, **kwargs):
        self.window = args[0]
        super().__init__(
            title=self.title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            *args,
            **kwargs
        )
        pane = self.GetContentsPane()
        pane.SetSizerType("vertical")
        self.components = self.createInterior(pane)
        button_sizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        self.SetButtonSizer(button_sizer)
        wxhelper.get_dialog_button(button_sizer, wx.ID_OK).Bind(
            wx.EVT_BUTTON, self.onOk
        )
        self.Fit()
        # Set starting size to 600x700 for better usability
        self.SetSize(600, 700)
        self.SetMinSize((500, 400))
        wxhelper.centre_on_parent(self)

    def createInterior(self, pane):
        raise NotImplementedError

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

        agw_style = (
            wx.TR_DEFAULT_STYLE
            | wx.TR_HIDE_ROOT
            | wx.TR_NO_BUTTONS
            | wx.TR_FULL_ROW_HIGHLIGHT
        )

        self.tree = hypertreelist.HyperTreeList(self, agwStyle=agw_style)
        self.tree.SetSizerProps(expand=True, proportion=1)
        self.tree.AddColumn(_("Field"))

    # Indicator-only columns excluded from export per object type.
    # These columns only show icons (e.g. paperclip, note icon) and render
    # as empty strings — they have no meaningful data to export.
    EXCLUDED_EXPORT_COLUMNS = {
        "tasks": {
            "ordering",
            "notes",
            "attachments",
            "statusIcon",
            "statusIconText",
        },
        "efforts": set(),
        "categories": {"ordering", "notes", "attachments"},
        "notes": {"ordering", "attachments"},
        "attachments": {"notes"},
    }

    def populateFromViewer(self, viewer, check_all=False):
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
        visible_columns = viewer.visibleColumns()
        object_type = getattr(viewer, "coreObjectType", "")
        excluded = self.EXCLUDED_EXPORT_COLUMNS.get(object_type, set())
        headers = []
        for column in viewer.selectable_columns():
            if column.name() in excluded:
                continue
            item = self.tree.AppendItem(root, column.header(), ct_type=1)
            self._columnMap[id(item)] = column
            headers.append(column.header())
            if check_all or column in visible_columns:
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
        checkbox_pad = 24
        col_pad = 16
        max_width = 0
        for header in headers:
            w, _ = dc.GetTextExtent(header)
            max_width = max(max_width, w)
        self.tree.SetColumnWidth(
            0, max(max_width + checkbox_pad + col_pad, 150)
        )

    def options(self):
        return dict(columns=self.selectedColumns())

    def saveSettings(self):
        pass  # No settings to save


class SeparateDateAndTimeColumnsCheckBox(wx.CheckBox):
    """Control that lets the user decide whether dates and times should be
    separated or kept together."""

    def __init__(self, parent, section, setting):
        super().__init__(
            parent, label=_("Put task dates and times in separate columns")
        )
        self.section = section
        self.setting = setting
        self.initializeCheckBox()

    def initializeCheckBox(self):
        self.SetValue(settings.get(self.section, self.setting))

    def options(self):
        return dict(separateDateAndTimeColumns=self.GetValue())

    def saveSettings(self):
        settings.set(self.section, self.setting, self.GetValue())


class SeparateCSSCheckBox(sized_controls.SizedPanel):
    """Control to let the user write CSS style information to a
    separate file instead of including it into the HTML file."""

    def __init__(self, parent, section, setting):
        super().__init__(parent)
        self.SetSizerProps(expand=True)
        self.section = section
        self.setting = setting
        self.createCheckBox()
        self.createHelpInformation()

    def createCheckBox(self):
        self.separateCSSCheckBox = wx.CheckBox(
            self,  # pylint: disable=W0201
            label=_("Write style information to a separate CSS file"),
        )
        self.separateCSSCheckBox.SetValue(
            settings.get(self.section, self.setting)
        )

    def createHelpInformation(self):
        self._helpText = (
            _(
                "If a CSS file exists for the exported file, %(name)s "
                "will not overwrite it. This allows you to change the "
                "style information without losing your changes on the "
                "next export."
            )
            % meta.metaDict
        )
        self.infoText = wx.StaticText(self, label=self._helpText)
        self.infoText.SetSizerProps(expand=True)
        self.infoText.Wrap(380)
        self.Bind(wx.EVT_SIZE, self.onSize)

    def onSize(self, event):
        event.Skip()
        if hasattr(self, "infoText") and hasattr(self, "_helpText"):
            width = self.GetClientSize().GetWidth()
            if width > 50:
                self.infoText.SetLabel(self._helpText)
                self.infoText.Wrap(width - 10)
                self.Layout()

    def options(self):
        return dict(separateCSS=self.separateCSSCheckBox.GetValue())

    def saveSettings(self):
        settings.set(
            self.section, self.setting, self.separateCSSCheckBox.GetValue()
        )


# Export dialogs for different file types:


class ExportAsCSVDialog(ExportDialog):
    """Non-modal CSV export dialog with enhanced viewer picker."""

    title = _("Export as CSV")

    def __init__(self, *args, **kwargs):
        self._exportCallback = kwargs.pop("exportCallback", None)
        super().__init__(*args, **kwargs)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        cancel_btn = self.FindWindowById(wx.ID_CANCEL)
        if cancel_btn:
            cancel_btn.Bind(wx.EVT_BUTTON, self.onCancel)

    def createInterior(self, pane):
        from taskcoachlib.gui.viewer import (
            TaskViewer,
            EffortViewer,
            CategoryViewer,
            NoteViewer,
            AttachmentViewer,
        )

        self._hiddenViewers = {}
        self._hiddenPanel = None

        self.viewerPicker = EnhancedViewerPicker(
            pane,
            self.window,
            supported_types=[
                TaskViewer,
                EffortViewer,
                CategoryViewer,
                NoteViewer,
                AttachmentViewer,
            ],
        )
        self.viewerPicker.Bind(EVT_VIEWERPICKED, self.onViewerChanged)

        self.columnPicker = ColumnPicker(pane, None)
        self.separateDateAndTimeColumnsCheckBox = (
            SeparateDateAndTimeColumnsCheckBox(
                pane,
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
        object_type = viewerClass.coreObjectType

        # 1. Search open viewers by coreObjectType
        for v in self.window.viewer:
            if (
                getattr(v, "coreObjectType", None) == object_type
                and v.hasHideableColumns()
            ):
                return v

        # 2. Check cached hidden viewers
        if viewerClass in self._hiddenViewers:
            return self._hiddenViewers[viewerClass]

        # 3. Create a hidden viewer
        if self._hiddenPanel is None:
            self._hiddenPanel = wx.Panel(self)
            self._hiddenPanel.Hide()
        kwargs = {}
        if object_type == "attachments":
            from taskcoachlib.domain.attachment import AttachmentList

            kwargs["attachmentsToShow"] = AttachmentList()
        hidden_viewer = viewerClass(
            self._hiddenPanel, self.window.taskFile, **kwargs
        )
        hidden_viewer.Hide()
        self._hiddenViewers[viewerClass] = hidden_viewer
        return hidden_viewer

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
        viewer_class = self.viewerPicker.selectedViewerClass()

        if self.viewerPicker.isAllSelected():
            viewer = None
            if viewer_class:
                viewer = self._getViewerForColumns(viewer_class)
            self.columnPicker.populateFromViewer(viewer, check_all=True)
        else:
            self.columnPicker.populateFromViewer(selected, check_all=False)

        # Separate date/time only relevant for tasks and efforts
        has_datetime = (
            viewer_class is not None
            and viewer_class.coreObjectType in ("tasks", "efforts")
        )
        self.separateDateAndTimeColumnsCheckBox.Enable(has_datetime)

    def onViewerChanged(self, event):
        event.Skip()
        self._updateColumnPickerState()

    def onOk(self, event):
        for component in self.components:
            component.saveSettings()

        if self._exportCallback:
            export_options = self.options()
            selected_viewer = export_options.pop("selectedViewer")
            export_options["selectionOnly"] = (
                not self.viewerPicker.isAllSelected()
            )

            date_str = datetime.date.today().strftime("%Y%m%d")
            export_options["default_filename"] = "%s-%s" % (
                self.viewerPicker.selectedTypeName(),
                date_str,
            )
            self._exportCallback(selected_viewer, **export_options)

        self._destroyHiddenViewers()
        self.Destroy()

    def onCancel(self, event):
        self._destroyHiddenViewers()
        self.Destroy()

    def onClose(self, event):
        self._destroyHiddenViewers()
        self.Destroy()


class EnhancedViewerPicker(sized_controls.SizedPanel):
    """Enhanced viewer picker with 'All' options and dynamic selection
    counts.

    Each export format declares what object types it supports via
    supportedTypes. The picker builds entries from this list, then
    searches open viewers to match.
    """

    def __init__(self, parent, main_window, supported_types):
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
        self.mainWindow = main_window
        self._supportedTypes = supported_types
        self.SetSizerType("horizontal")
        # Maps display string to viewer or allMarker string
        self._viewerMap = {}
        self.createPicker()
        self.populatePicker()
        self._subscribe_to_selection_changes()
        top_level = self.GetTopLevelParent()
        if top_level:
            top_level.Bind(wx.EVT_ACTIVATE, self._onDialogActivate)

    def createPicker(self):
        label = wx.StaticText(self, label=_("Export items from:"))
        label.SetSizerProps(valign="center")
        self.viewerComboBox = wx.Choice(self)
        self.viewerComboBox.Bind(wx.EVT_CHOICE, self.onViewerChanged)

    def _findOpenViewers(self):
        """Find open viewers matching each supported type using coreObjectType."""
        viewers = list(self.mainWindow.viewer)
        grouped = {}
        for viewer_class in self._supportedTypes:
            object_type = viewer_class.coreObjectType
            grouped[object_type] = [
                v
                for v in viewers
                if getattr(v, "coreObjectType", None) == object_type
                and v.hasHideableColumns()
            ]
        return grouped

    def _getSelectionCount(self, viewer):
        """Get selection count for a viewer."""
        try:
            return len(viewer.curselection())
        except (RuntimeError, AttributeError):
            return 0

    def _buildEntries(self, grouped_viewers):
        """Build dropdown entries from supported types and open viewers."""
        entries = []

        # Section 1: "All" entries - one per supported type, sorted by label
        all_entries = []
        for viewer_class in self._supportedTypes:
            label = _("%s (All)") % viewer_class.defaultTitle
            marker = "ALL_" + viewer_class.coreObjectType.upper()
            all_entries.append((label, marker))
        all_entries.sort(key=lambda x: x[0])
        entries.extend(all_entries)

        # Section 2: Open viewers matching supported types
        viewer_entries = []
        for viewer_class in self._supportedTypes:
            object_type = viewer_class.coreObjectType
            for viewer in grouped_viewers.get(object_type, []):
                count = self._getSelectionCount(viewer)
                title = viewer.title()
                display_text = _("%s (%d selected)") % (title, count)
                viewer_entries.append((title, -count, display_text, viewer))

        if viewer_entries:
            entries.append(("---", None))
            viewer_entries.sort(key=lambda x: (x[0], x[1]))
            for title, neg_count, display_text, viewer in viewer_entries:
                entries.append((display_text, viewer))

        return entries

    def populatePicker(self):
        """Populate the dropdown. Default selection is the first 'All' entry."""
        self.viewerComboBox.Clear()
        self._viewerMap.clear()

        grouped_viewers = self._findOpenViewers()
        entries = self._buildEntries(grouped_viewers)

        for display_text, viewer_or_marker in entries:
            if display_text == "---":
                self.viewerComboBox.Append("─" * 20)
            else:
                self.viewerComboBox.Append(display_text)
                self._viewerMap[display_text] = viewer_or_marker

        if self.viewerComboBox.GetCount() > 0:
            self.viewerComboBox.SetSelection(0)

    def _subscribe_to_selection_changes(self):
        """Subscribe to selection change events from all viewers."""
        from taskcoachlib.gui.viewer.container import ViewerContainer

        patterns.Publisher().registerObserver(
            self._on_viewer_status_changed,
            eventType=ViewerContainer.status_event_type(),
        )

    def _onDialogActivate(self, event):
        """Rebuild dropdown when the export dialog gains focus."""
        event.Skip()
        if event.GetActive():
            self._on_viewer_status_changed()

    def _on_viewer_status_changed(self, event=None):  # pylint: disable=W0613
        """Handle viewer status changes (including selection changes)."""
        current_selection = self.viewerComboBox.GetStringSelection()
        current_viewer = self._viewerMap.get(current_selection)

        grouped_viewers = self._findOpenViewers()
        entries = self._buildEntries(grouped_viewers)

        self.viewerComboBox.Clear()
        self._viewerMap.clear()

        new_selection_index = 0
        for display_text, viewer_or_marker in entries:
            if display_text == "---":
                self.viewerComboBox.Append("─" * 20)
            else:
                self.viewerComboBox.Append(display_text)
                self._viewerMap[display_text] = viewer_or_marker
                if viewer_or_marker == current_viewer:
                    new_selection_index = self.viewerComboBox.GetCount() - 1

        if self.viewerComboBox.GetCount() > 0:
            self.viewerComboBox.SetSelection(new_selection_index)

    def selectedViewer(self):
        """Return the selected viewer instance or ALL_* marker string."""
        display_text = self.viewerComboBox.GetStringSelection()
        return self._viewerMap.get(display_text)

    def isAllSelected(self):
        """Return True if an 'All' option is selected."""
        selected = self.selectedViewer()
        return isinstance(selected, str)

    def selectedViewerClass(self):
        """Return the viewer class for the current selection."""
        selected = self.selectedViewer()
        for viewer_class in self._supportedTypes:
            marker = "ALL_" + viewer_class.coreObjectType.upper()
            if selected == marker:
                return viewer_class
            if (
                hasattr(selected, "coreObjectType")
                and selected.coreObjectType == viewer_class.coreObjectType
            ):
                return viewer_class
        return None

    def selectedTypeName(self):
        """Return the type name for the current selection (for filenames)."""
        viewer_class = self.selectedViewerClass()
        if viewer_class:
            return viewer_class.defaultTitle
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
        patterns.Publisher().removeObserver(self._on_viewer_status_changed)
        return super().Destroy()


class ICalendarFieldPicker(sized_controls.SizedPanel):
    """Control for selecting which fields to export in iCalendar format.
    Uses HyperTreeList with checkboxes."""

    # Field definitions: (field_key, taskcoach_label, icalendar_field,
    # required, formatting)
    TASK_FIELDS = [
        ("uid", _("ID"), "UID", True, _("Internal identifier")),
        (
            "dtstamp",
            _("(auto-generated)"),
            "DTSTAMP",
            True,
            _("Current UTC timestamp"),
        ),
        ("summary", _("Subject"), "SUMMARY", False, _("Text, quoted")),
        (
            "description",
            _("Description"),
            "DESCRIPTION",
            False,
            _("Text, quoted"),
        ),
        (
            "dtstart",
            _("Planned start date"),
            "DTSTART",
            False,
            _("UTC datetime"),
        ),
        ("due", _("Due date"), "DUE", False, _("UTC datetime")),
        (
            "completed",
            _("Completion date"),
            "COMPLETED",
            False,
            _("UTC datetime"),
        ),
        (
            "categories",
            _("Categories"),
            "CATEGORIES",
            False,
            _("Comma-separated, recursive"),
        ),
        (
            "status",
            _("Status"),
            "STATUS",
            False,
            _("NEEDS-ACTION / IN-PROCESS / COMPLETED"),
        ),
        (
            "priority",
            _("Priority"),
            "PRIORITY",
            False,
            _("Number, capped at 3"),
        ),
        (
            "percent",
            _("Percent complete"),
            "PERCENT-COMPLETE",
            False,
            _("Integer 0-100"),
        ),
        ("created", _("Creation date"), "CREATED", False, _("UTC datetime")),
        (
            "lastmod",
            _("Modification date"),
            "LAST-MODIFIED",
            False,
            _("UTC datetime"),
        ),
    ]

    EFFORT_FIELDS = [
        ("uid", _("ID"), "UID", True, _("Internal identifier")),
        (
            "dtstamp",
            _("(auto-generated)"),
            "DTSTAMP",
            True,
            _("Current UTC timestamp"),
        ),
        ("summary", _("Subject"), "SUMMARY", False, _("Task subject, quoted")),
        (
            "description",
            _("Description"),
            "DESCRIPTION",
            False,
            _("Task description, quoted"),
        ),
        ("dtstart", _("Start"), "DTSTART", False, _("UTC datetime")),
        ("dtend", _("End"), "DTEND", False, _("UTC datetime")),
    ]

    def __init__(self, parent, for_tasks=True):
        super().__init__(parent)
        self.SetSizerType("vertical")
        self.SetSizerProps(expand=True, proportion=1)
        self._forTasks = for_tasks
        self._checkedFields = set()
        self._itemMap = {}  # Maps field_key to tree item
        self.createFieldPicker()
        self.populateFields()

    def createFieldPicker(self):
        label = wx.StaticText(self, label=_("Fields to export:"))
        label.SetSizerProps(valign="top")

        agw_style = (
            wx.TR_DEFAULT_STYLE
            | wx.TR_HIDE_ROOT
            | wx.TR_NO_BUTTONS
            | wx.TR_FULL_ROW_HIGHLIGHT
            | customtreectrl.TR_AUTO_CHECK_CHILD
        )

        # Use default border style to match system theme
        self.tree = hypertreelist.HyperTreeList(self, agwStyle=agw_style)
        self.tree.SetSizerProps(expand=True, proportion=1)

        # Add columns - widths will be auto-sized after population
        self.tree.AddColumn(_("Source Field"))
        self.tree.AddColumn(_("Output Field"))
        self.tree.AddColumn(_("Formatting"))

        self.tree.Bind(
            customtreectrl.EVT_TREE_ITEM_CHECKED, self.onItemChecked
        )

    def populateFields(self):
        """Populate the field list based on whether we're exporting tasks or efforts."""
        self.tree.DeleteAllItems()
        self._itemMap.clear()
        self._checkedFields.clear()

        root = self.tree.AddRoot("")
        fields = self.TASK_FIELDS if self._forTasks else self.EFFORT_FIELDS

        for (
            field_key,
            tc_label,
            ical_field,
            required,
            formatting,
        ) in fields:
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
        num_cols = self.tree.GetColumnCount()
        max_widths = [0] * num_cols
        # Column 0 needs extra padding for checkbox (approx 24px)
        checkbox_pad = 24
        col_pad = 16  # General padding per column
        for field in fields:
            # tc_label, ical_field, formatting
            texts = [field[1], field[2], field[4]]
            for col in range(num_cols):
                w, _ = dc.GetTextExtent(texts[col])
                max_widths[col] = max(max_widths[col], w)
        for col in range(num_cols):
            width = (
                max_widths[col] + col_pad + (checkbox_pad if col == 0 else 0)
            )
            self.tree.SetColumnWidth(col, max(width, 100))

    def setForTasks(self, for_tasks):
        """Switch between task and effort field lists."""
        if self._forTasks != for_tasks:
            self._forTasks = for_tasks
            self.populateFields()

    def onItemChecked(self, event):
        """Handle checkbox changes."""
        item = event.GetItem()
        # Find the field key for this item
        for field_key, tree_item in self._itemMap.items():
            if tree_item == item:
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
        cancel_btn = self.FindWindowById(wx.ID_CANCEL)
        if cancel_btn:
            cancel_btn.Bind(wx.EVT_BUTTON, self.onCancel)

    def createInterior(self, pane):
        from taskcoachlib.gui.viewer import TaskViewer, EffortViewer

        self.viewerPicker = EnhancedViewerPicker(
            pane, self.window, supported_types=[TaskViewer, EffortViewer]
        )
        self.viewerPicker.Bind(EVT_VIEWERPICKED, self.onViewerChanged)

        # Determine initial field type based on active viewer
        for_tasks = self.viewerPicker.selectedViewerClass() is TaskViewer
        self.fieldPicker = ICalendarFieldPicker(pane, for_tasks=for_tasks)

        return self.viewerPicker, self.fieldPicker

    def onOk(self, event):
        """Handle OK button - perform export and close dialog."""
        for component in self.components:
            component.saveSettings()

        if self._exportCallback:
            export_options = self.options()
            selected_viewer = export_options.pop("selectedViewer")
            export_options["selectionOnly"] = (
                not self.viewerPicker.isAllSelected()
            )

            date_str = datetime.date.today().strftime("%Y%m%d")
            export_options["default_filename"] = "%s-%s" % (
                self.viewerPicker.selectedTypeName(),
                date_str,
            )
            self._exportCallback(selected_viewer, **export_options)

        self.Destroy()

    def onCancel(self, event):
        self.Destroy()

    def onClose(self, event):
        self.Destroy()

    def onViewerChanged(self, event):
        event.Skip()
        from taskcoachlib.gui.viewer import TaskViewer

        for_tasks = self.viewerPicker.selectedViewerClass() is TaskViewer
        self.fieldPicker.setForTasks(for_tasks)


class ExportAsHTMLDialog(ExportDialog):
    """Non-modal HTML export dialog with enhanced viewer picker."""

    title = _("Export as HTML")

    def __init__(self, *args, **kwargs):
        self._exportCallback = kwargs.pop("exportCallback", None)
        super().__init__(*args, **kwargs)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        cancel_btn = self.FindWindowById(wx.ID_CANCEL)
        if cancel_btn:
            cancel_btn.Bind(wx.EVT_BUTTON, self.onCancel)

    def createInterior(self, pane):
        from taskcoachlib.gui.viewer import (
            TaskViewer,
            EffortViewer,
            CategoryViewer,
            NoteViewer,
            AttachmentViewer,
        )

        self._hiddenViewers = {}
        self._hiddenPanel = None

        self.viewerPicker = EnhancedViewerPicker(
            pane,
            self.window,
            supported_types=[
                TaskViewer,
                EffortViewer,
                CategoryViewer,
                NoteViewer,
                AttachmentViewer,
            ],
        )
        self.viewerPicker.Bind(EVT_VIEWERPICKED, self.onViewerChanged)

        self.columnPicker = ColumnPicker(pane, None)
        separate_css_chooser = SeparateCSSCheckBox(
            pane, self.section, "html_separatecss"
        )
        self._updateColumnPickerState()

        return (
            self.viewerPicker,
            self.columnPicker,
            separate_css_chooser,
        )

    def _getViewerForColumns(self, viewerClass):
        """Get a viewer for column definitions. Fallback chain:
        1. Find an existing open viewer matching coreObjectType
        2. Use cached hidden viewer
        3. Create a new hidden viewer instance
        """
        object_type = viewerClass.coreObjectType

        for v in self.window.viewer:
            if (
                getattr(v, "coreObjectType", None) == object_type
                and v.hasHideableColumns()
            ):
                return v

        if viewerClass in self._hiddenViewers:
            return self._hiddenViewers[viewerClass]

        if self._hiddenPanel is None:
            self._hiddenPanel = wx.Panel(self)
            self._hiddenPanel.Hide()
        kwargs = {}
        if object_type == "attachments":
            from taskcoachlib.domain.attachment import AttachmentList

            kwargs["attachmentsToShow"] = AttachmentList()
        hidden_viewer = viewerClass(
            self._hiddenPanel, self.window.taskFile, **kwargs
        )
        hidden_viewer.Hide()
        self._hiddenViewers[viewerClass] = hidden_viewer
        return hidden_viewer

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
        viewer_class = self.viewerPicker.selectedViewerClass()

        if self.viewerPicker.isAllSelected():
            viewer = None
            if viewer_class:
                viewer = self._getViewerForColumns(viewer_class)
            self.columnPicker.populateFromViewer(viewer, check_all=True)
        else:
            self.columnPicker.populateFromViewer(selected, check_all=False)

    def onViewerChanged(self, event):
        event.Skip()
        self._updateColumnPickerState()

    def onOk(self, event):
        for component in self.components:
            component.saveSettings()

        if self._exportCallback:
            export_options = self.options()
            selected_viewer = export_options.pop("selectedViewer")
            export_options["selectionOnly"] = (
                not self.viewerPicker.isAllSelected()
            )

            date_str = datetime.date.today().strftime("%Y%m%d")
            export_options["default_filename"] = "%s-%s" % (
                self.viewerPicker.selectedTypeName(),
                date_str,
            )
            self._exportCallback(selected_viewer, **export_options)

        self._destroyHiddenViewers()
        self.Destroy()

    def onCancel(self, event):
        self._destroyHiddenViewers()
        self.Destroy()

    def onClose(self, event):
        self._destroyHiddenViewers()
        self.Destroy()
