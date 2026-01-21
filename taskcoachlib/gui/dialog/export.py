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
from taskcoachlib.i18n import _
from wx.lib import sized_controls
from taskcoachlib import meta, widgets


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


class ExportAsICalendarDialog(ExportDialog):
    title = _("Export as iCalendar")

    def createInterior(self, pane):
        viewerPicker = ViewerPicker(
            pane, self.exportableViewers(), self.activeViewer()
        )
        selectionOnlyCheckBox = SelectionOnlyCheckBox(
            pane, self.settings, self.section, "ical_selectiononly"
        )
        return viewerPicker, selectionOnlyCheckBox

    def exportableViewers(self):
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
