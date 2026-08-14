# -*- coding: utf-8 -*-

"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2008 Rob McMullen <rob.mcmullen@gmail.com>

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

from taskcoachlib import (
    patterns,
    meta,
    command,
    help,
    widgets,
    persistence,
    thirdparty,
    render,
    operating_system,
)  # pylint: disable=W0622
from taskcoachlib.domain import (
    base,
    task,
    note,
    category,
    attachment,
    effort,
    date,
)
from taskcoachlib.gui import dialog, printer
from taskcoachlib.gui.wizard import CSVImportWizard
from taskcoachlib.i18n import _
from taskcoachlib.mailer import sendMail
from wx.lib.agw import hypertreelist
from pubsub import pub
from taskcoachlib.thirdparty.wxScheduler import (
    wxSCHEDULER_NEXT,
    wxSCHEDULER_PREV,
    wxSCHEDULER_TODAY,
)
from taskcoachlib.gui.icons.icon_library import icon_catalog
from taskcoachlib.tools import anonymize, openfile

import wx, re, operator
from . import base_uicommand
from . import mixin_uicommand
from . import settings_uicommand
from functools import reduce


class Separator(base_uicommand.UICommand):
    """Toolbar/menu separator — renders as a visual divider."""

    def __init__(self):
        super().__init__(menu_text="Separator")

    def is_separator(self):
        return True

    def is_command(self):
        return False

    def append_to_toolbar(self, toolbar):
        toolbar.AddSeparator()

    def add_to_menu(self, menu, window, position=None):
        menu.AppendSeparator()


class Spacer(base_uicommand.UICommand):
    """Toolbar spacer — pushes subsequent items to the right."""

    def __init__(self, proportion=1):
        super().__init__(menu_text="Spacer")
        self.proportion = proportion

    def is_spacer(self):
        return True

    def is_command(self):
        return False

    def append_to_toolbar(self, toolbar):
        toolbar.AddStretchSpacer(self.proportion)


class DisabledLabel(base_uicommand.UICommand):
    """Menu-only disabled label — renders as greyed-out text."""

    def __init__(self, text):
        super().__init__(menu_text=text)
        self.text = text

    def is_command(self):
        return False

    def add_to_menu(self, menu, window, position=None):
        label = wx.MenuItem(menu, text=self.text)
        menu.Append(label)
        label.Enable(False)


class SubMenu(base_uicommand.UICommand):
    """Menu-only submenu — renders as a nested menu."""

    def __init__(self, title, *commands):
        super().__init__(menu_text=title)
        self.title = title
        self.commands = commands

    def is_command(self):
        return False

    def add_to_menu(self, menu, window, position=None):
        from taskcoachlib.gui import menu as menu_module

        sub_menu = menu_module.Menu(window)
        menu.appendMenu(self.title, sub_menu)
        sub_menu.append_ui_commands(*self.commands)


class IOCommand(base_uicommand.UICommand):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        self.iocontroller = kwargs.pop("iocontroller", None)
        super().__init__(*args, **kwargs)


class TaskListCommand(base_uicommand.UICommand):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        self.taskList = kwargs.pop("taskList", None)
        super().__init__(*args, **kwargs)


class EffortListCommand(base_uicommand.UICommand):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        self.effortList = kwargs.pop("effortList", None)
        super().__init__(*args, **kwargs)


class CategoriesCommand(base_uicommand.UICommand):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        self.categories = kwargs.pop("categories", None)
        super().__init__(*args, **kwargs)


class NotesCommand(base_uicommand.UICommand):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        self.notes = kwargs.pop("notes", None)
        super().__init__(*args, **kwargs)


class AttachmentsCommand(base_uicommand.UICommand):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        self.attachments = kwargs.pop("attachments", None)
        super().__init__(*args, **kwargs)


class ViewerCommand(base_uicommand.UICommand):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        self.viewer = kwargs.pop("viewer", None)
        super().__init__(*args, **kwargs)

    def __eq__(self, other):
        return (
            super().__eq__(other)
            and self.viewer.settingsSection() == other.viewer.settingsSection()
        )


# Commands:


class FileOpen(IOCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Open...\tCtrl+O"),
            help_text=help.fileOpen,
            icon_id="nuvola_actions_document-open",
            id=wx.ID_OPEN,
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.iocontroller.open()


class RecentFileOpen(IOCommand):
    def __init__(self, *args, **kwargs):
        self.__filename = kwargs.pop("filename")
        index = kwargs.pop("index")
        super().__init__(
            menu_text="%d %s" % (index, self.__filename),
            help_text=_("Open %s") % self.__filename,
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.iocontroller.open(self.__filename)


class FileMerge(IOCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Merge..."),
            help_text=_("Merge tasks from another file with the current file"),
            icon_id="papirus_actions_kr_combine",
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.iocontroller.merge()


class FileClose(IOCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Close\tCtrl+W"),
            help_text=help.fileClose,
            icon_id="nuvola_actions_dialog-close",
            id=wx.ID_CLOSE,
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.main_window().closeEditors()
        self.iocontroller.close()


class FileSave(IOCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Save\tCtrl+S"),
            help_text=help.fileSave,
            icon_id="nuvola_devices_media-floppy",
            id=wx.ID_SAVE,
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        pub.subscribe(self._on_dirty_changed, "taskfile.dirty")
        pub.subscribe(self._on_dirty_changed, "taskfile.clean")

    def _on_dirty_changed(self, taskFile):
        try:
            self.toolbar.EnableTool(self.id, self.enabled(None))
            self.toolbar.Refresh(False)
        except RuntimeError:
            pass

    def do_command(self, event):
        self.iocontroller.save()

    def enabled(self, event):
        return self.iocontroller.need_save()


class FileMergeDiskChanges(IOCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Merge &disk changes\tShift-Ctrl-M"),
            help_text=help.fileMergeDiskChanges,
            icon_id="nuvola_actions_go-top",
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        for topic in ("taskfile.changed", "taskfile.dirty", "taskfile.clean"):
            pub.subscribe(self._on_file_state_changed, topic)

    def _on_file_state_changed(self, taskFile):
        try:
            self.toolbar.EnableTool(self.id, self.enabled(None))
            self.toolbar.Refresh(False)
        except RuntimeError:
            pass

    def do_command(self, event):
        self.iocontroller.merge_disk_changes()

    def enabled(self, event):
        return self.iocontroller.changed_on_disk()


class FileSaveAs(IOCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("S&ave as...\tShift+Ctrl+S"),
            help_text=help.fileSaveAs,
            icon_id="nuvola_actions_document-save-as",
            id=wx.ID_SAVEAS,
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.iocontroller.save_as()


class FileSaveSelection(IOCommand, ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Sa&ve selected tasks to new taskfile..."),
            help_text=_("Save the selected tasks to a separate taskfile"),
            icon_id="nuvola_actions_document-save-as",
            *args,
            **kwargs
        )

    def enabled(self, event):
        return self.viewer.has_selection and self.viewer.is_task

    def do_command(self, event):
        self.iocontroller.save_selection(self.viewer.curselection())


class FileSaveSelectedTaskAsTemplate(IOCommand, ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Save selected task as &template"),
            help_text=_("Save the selected task as a task template"),
            icon_id="taskcoach_actions_newtmpl",
            *args,
            **kwargs
        )

    def enabled(self, event):
        return self.viewer.has_single_selection and self.viewer.is_task

    def do_command(self, event):
        self.iocontroller.save_as_template(self.viewer.curselection()[0])


class FileImportTemplate(IOCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Import template..."),
            help_text=_("Import a new template from a template file"),
            icon_id="nuvola_actions_document-open",
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.iocontroller.import_template()


class FileEditTemplates(
    settings_uicommand.SettingsCommand, base_uicommand.UICommand
):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Edit templates..."),
            help_text=_("Edit existing templates"),
            *args,
            **kwargs
        )

    def do_command(self, event):
        templateDialog = dialog.templates.TemplatesDialog(
            self.settings, self.main_window(), title=_("Edit templates")
        )
        templateDialog.Show()


class FilePurgeDeletedItems(IOCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Purge deleted items"),
            help_text=_(
                "Permanently delete tasks and notes marked as deleted"
            ),
            icon_id="nuvola_actions_edit-delete",
            *args,
            **kwargs
        )

    def do_command(self, event):
        if (
            wx.MessageBox(
                _(
                    "Purging deleted items cannot be undone.\n\nDo you still want to purge?"
                ),
                _("Warning"),
                wx.YES_NO,
            )
            == wx.YES
        ):
            self.iocontroller.purge_deleted_items()

    def enabled(self, event):
        return self.iocontroller.has_deleted_items()


class PrintPageSetup(
    settings_uicommand.SettingsCommand, base_uicommand.UICommand
):
    """Action for changing page settings. The page settings are saved in the
    application wide settings."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Page setup...\tShift+Ctrl+P"),
            help_text=help.printPageSetup,
            icon_id="oxygen_actions_zoom-fit-best",
            id=wx.ID_PRINT_SETUP,
            *args,
            **kwargs
        )

    def do_command(self, event):
        printerSettings = printer.PrinterSettings(self.settings)
        pageSetupDialog = wx.PageSetupDialog(
            self.main_window(), printerSettings.pageSetupData
        )
        result = pageSetupDialog.ShowModal()
        if result == wx.ID_OK:
            pageSetupData = pageSetupDialog.GetPageSetupData()
            printerSettings.updatePageSetupData(pageSetupData)
        pageSetupDialog.Destroy()


class PrintPreview(ViewerCommand, settings_uicommand.SettingsCommand):
    """Action for previewing a print of the current viewer."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Print preview..."),
            help_text=_("Show a preview of what the print will look like"),
            icon_id="oxygen_actions_zoom-draw",
            id=wx.ID_PREVIEW,
            *args,
            **kwargs
        )

    def do_command(self, event):
        printout, printout2 = printer.Printout(
            self.viewer, self.settings, twoPrintouts=True
        )
        printerSettings = printer.PrinterSettings(self.settings)
        preview = wx.PrintPreview(
            printout, printout2, printerSettings.printData
        )
        if not preview.IsOk():
            wx.MessageBox(
                _("There was a problem creating the print preview."),
                _("Print Preview Error"),
                wx.OK | wx.ICON_ERROR,
            )
            return
        previewFrame = wx.PreviewFrame(
            preview, self.main_window(), _("Print preview"), size=(750, 700)
        )
        previewFrame.Initialize()
        previewFrame.Show()


class Print(ViewerCommand, settings_uicommand.SettingsCommand):
    """Action for printing the contents of the current viewer."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Print...\tCtrl+P"),
            help_text=help.print_,
            icon_id="nuvola_devices_printer",
            id=wx.ID_PRINT,
            *args,
            **kwargs
        )

    def do_command(self, event):
        printerSettings = printer.PrinterSettings(self.settings)
        printDialogData = wx.PrintDialogData(printerSettings.printData)
        printDialogData.EnableSelection(True)
        wxPrinter = wx.Printer(printDialogData)
        if not wxPrinter.PrintDialog(self.main_window()):
            return
        printout = printer.Printout(
            self.viewer,
            self.settings,
            printSelectionOnly=wxPrinter.PrintDialogData.Selection,
        )
        # If the user checks the selection radio button, the ToPage property
        # gets set to 1. Looks like a bug to me. The simple work-around is to
        # reset the ToPage property to the MaxPage value if necessary:
        if wxPrinter.PrintDialogData.Selection:
            wxPrinter.PrintDialogData.ToPage = (
                wxPrinter.PrintDialogData.MaxPage
            )
        wxPrinter.Print(self.main_window(), printout, prompt=False)


class FileExportCommand(IOCommand, settings_uicommand.SettingsCommand):
    """Base class for export actions."""

    def do_command(self, event):
        exportDialog = self.getExportDialogClass()(
            self.main_window(), settings=self.settings
        )  # pylint: disable=E1101
        try:
            if wx.ID_OK == exportDialog.ShowModal():
                exportOptions = exportDialog.options()
                selectedViewer = exportOptions.pop("selectedViewer")
                # pylint: disable=W0142
                self.exportFunction()(selectedViewer, **exportOptions)
        finally:
            if exportDialog:
                exportDialog.Destroy()

    @staticmethod
    def getExportDialogClass():
        """Return the class to be used for the export dialog."""
        raise NotImplementedError

    def exportFunction(self):
        """Return a function that does the actual export. The function should
        take the selected viewer as the first parameter and possibly a
        number of keyword arguments for export options."""
        raise NotImplementedError  # pragma: no cover


class FileManageBackups(IOCommand, settings_uicommand.SettingsCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Manage backups..."),
            help_text=_("Manage all task file backups"),
            *args,
            **kwargs
        )

    def do_command(self, event):
        dlg = dialog.BackupManagerDialog(
            self.main_window(), self.settings, self.iocontroller.filename()
        )
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self.iocontroller.open(dlg.restoredFilename())
        finally:
            dlg.Destroy()


class FileExportAsHTML(FileExportCommand):
    """Action for exporting the contents of a viewer to HTML.

    Uses a non-modal dialog to allow users to change selections while
    the export dialog is open."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Export as &HTML..."),
            help_text=_("Export items from a viewer in HTML format"),
            icon_id="nuvola_mimetypes_text-html",
            *args,
            **kwargs
        )
        self._exportDialog = None

    def do_command(self, event):
        """Show non-modal export dialog."""
        if self._exportDialog:
            self._exportDialog.Raise()
            return
        self._exportDialog = self.getExportDialogClass()(
            self.main_window(),
            settings=self.settings,
            exportCallback=self.exportFunction(),
        )
        self._exportDialog.Show()
        self._exportDialog.Bind(wx.EVT_WINDOW_DESTROY, self._onDialogDestroyed)

    def _onDialogDestroyed(self, event):
        """Clear dialog reference when destroyed."""
        self._exportDialog = None
        event.Skip()

    @staticmethod
    def getExportDialogClass():
        return dialog.export.ExportAsHTMLDialog

    def exportFunction(self):
        return self.iocontroller.export_as_html

    def enabled(self, event):
        return True


class FileExportAsCSV(FileExportCommand):
    """Action for exporting the contents of a viewer to CSV.

    Uses a non-modal dialog to allow users to change selections while
    the export dialog is open."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Export as &CSV..."),
            help_text=_(
                "Export items from a viewer in Comma Separated Values "
                "(CSV) format"
            ),
            icon_id="nuvola_mimetypes_x-office-spreadsheet",
            *args,
            **kwargs
        )
        self._exportDialog = None

    def do_command(self, event):
        """Show non-modal export dialog."""
        if self._exportDialog:
            self._exportDialog.Raise()
            return
        self._exportDialog = self.getExportDialogClass()(
            self.main_window(),
            settings=self.settings,
            exportCallback=self.exportFunction(),
        )
        self._exportDialog.Show()
        self._exportDialog.Bind(wx.EVT_WINDOW_DESTROY, self._onDialogDestroyed)

    def _onDialogDestroyed(self, event):
        """Clear dialog reference when destroyed."""
        self._exportDialog = None
        event.Skip()

    @staticmethod
    def getExportDialogClass():
        return dialog.export.ExportAsCSVDialog

    def exportFunction(self):
        return self.iocontroller.export_as_csv

    def enabled(self, event):
        return True


class FileExportAsICalendar(FileExportCommand):
    """Action for exporting the contents of a viewer to iCalendar format.

    Uses a non-modal dialog to allow users to change selections while
    the export dialog is open."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Export as &iCalendar..."),
            help_text=_("Export items from a viewer in iCalendar format"),
            icon_id="nuvola_mimetypes_text-vcalendar",
            *args,
            **kwargs
        )
        self._exportDialog = None

    def do_command(self, event):
        """Show non-modal export dialog."""
        # If dialog already open, just raise it
        if self._exportDialog:
            self._exportDialog.Raise()
            return

        self._exportDialog = self.getExportDialogClass()(
            self.main_window(),
            settings=self.settings,
            exportCallback=self.exportFunction(),
        )
        # Use Show() for non-modal dialog
        self._exportDialog.Show()
        # Clear reference when dialog is destroyed
        self._exportDialog.Bind(wx.EVT_WINDOW_DESTROY, self._onDialogDestroyed)

    def _onDialogDestroyed(self, event):
        """Clear dialog reference when destroyed."""
        self._exportDialog = None
        event.Skip()

    def exportFunction(self):
        return self.iocontroller.export_as_icalendar

    def enabled(self, event):
        # Always enabled since we have "Tasks (All)" and "Efforts (All)" options
        return True

    @staticmethod
    def getExportDialogClass():
        return dialog.export.ExportAsICalendarDialog

    @staticmethod
    def exportableViewer(aViewer):
        """Return whether the viewer can be exported to iCalendar format."""
        return aViewer.is_showing_tasks() or (
            aViewer.is_showing_effort()
            and not aViewer.is_showing_aggregated_effort()
        )


class FileExportAsTodoTxt(FileExportCommand):
    """Action for exporting the contents of a viewer to Todo.txt format.

    Uses a non-modal dialog to allow users to change selections while
    the export dialog is open."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Export as &Todo.txt..."),
            help_text=_(
                "Export items from a viewer in Todo.txt format "
                "(see todotxt.com)"
            ),
            icon_id="oxygen_mimetypes_text-plain",
            *args,
            **kwargs
        )
        self._exportDialog = None

    def do_command(self, event):
        """Show non-modal export dialog."""
        if self._exportDialog:
            self._exportDialog.Raise()
            return
        self._exportDialog = self.getExportDialogClass()(
            self.main_window(),
            settings=self.settings,
            exportCallback=self.exportFunction(),
        )
        self._exportDialog.Show()
        self._exportDialog.Bind(wx.EVT_WINDOW_DESTROY, self._onDialogDestroyed)

    def _onDialogDestroyed(self, event):
        """Clear dialog reference when destroyed."""
        self._exportDialog = None
        event.Skip()

    def exportFunction(self):
        return self.iocontroller.export_as_todo_txt

    def enabled(self, event):
        return True

    @staticmethod
    def getExportDialogClass():
        return dialog.export.ExportAsTodoTxtDialog


class FileImportCSV(IOCommand):
    """Action for importing data from a CSV file into the current task
    file."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Import CSV..."),
            help_text=_(
                "Import tasks from a Comma Separated Values (CSV) file"
            ),
            icon_id="nuvola_mimetypes_x-office-spreadsheet",
            *args,
            **kwargs
        )

    def do_command(self, event):
        while True:
            filename = wx.FileSelector(_("Import CSV"), wildcard="*.csv")
            if filename:
                if len(open(filename, "rb").read()) == 0:
                    wx.MessageBox(
                        _(
                            "The selected file is empty. "
                            "Please select a different file."
                        ),
                        _("Import CSV"),
                    )
                    continue
                wizard = CSVImportWizard(
                    filename, None, wx.ID_ANY, _("Import CSV")
                )
                if wizard.RunWizard():
                    self.iocontroller.import_csv(**wizard.GetOptions())
                    break
            else:
                break


class FileImportTodoTxt(IOCommand):
    """Action for importing data from a Todo.txt file into the current task
    file."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Import Todo.txt..."),
            help_text=_("Import tasks from a Todo.txt (see todotxt.com) file"),
            icon_id="oxygen_mimetypes_text-plain",
            *args,
            **kwargs
        )

    def do_command(self, event):
        filename = wx.FileSelector(_("Import Todo.txt"), wildcard="*.txt")
        if filename:
            self.iocontroller.import_todo_txt(filename)


class FileQuit(base_uicommand.UICommand):
    """Action for quitting the application."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Quit\tCtrl+Q"),
            help_text=help.fileQuit,
            icon_id="nuvola_actions_application-exit",
            id=wx.ID_EXIT,
            *args,
            **kwargs
        )

    def do_command(self, event):
        # Use CallAfter so the tray popup menu can finish and release
        # its resources before quitApplication() destroys the tray icon.
        # Without this, Windows crashes (segfault) because PopupMenu()
        # is modal and the tray icon is destroyed while the menu is active.
        wx.CallAfter(self.main_window().Close, force=True)


class EditUndo(base_uicommand.UICommand):
    """Action for undoing the previous user action."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=self._undo_menu_text(),
            help_text=help.editUndo,
            icon_id="nuvola_actions_edit-undo",
            id=wx.ID_UNDO,
            *args,
            **kwargs
        )
        self.registerObserver(
            self._on_history_changed,
            eventType="commandhistory.changed",
            eventSource=patterns.CommandHistory(),
        )

    @staticmethod
    def _undo_menu_text():
        return "%s\tCtrl+Z" % patterns.CommandHistory().undostr(_("&Undo"))

    def _on_history_changed(self, event=None):  # pylint: disable=W0613
        self.update_menu_text(self._undo_menu_text())
        if self.toolbar:
            try:
                self.toolbar.EnableTool(self.id, self.enabled(None))
                self.toolbar.Refresh(False)
            except RuntimeError:
                pass

    def do_command(self, event):
        window_with_focus = wx.Window.FindFocus()
        if isinstance(window_with_focus, wx.TextCtrl):
            window_with_focus.Undo()
        else:
            patterns.CommandHistory().undo()

    def current_menu_text(self):
        return self._undo_menu_text()

    def enabled(self, event):
        window_with_focus = wx.Window.FindFocus()
        if isinstance(window_with_focus, wx.TextCtrl):
            return window_with_focus.CanUndo()
        return bool(patterns.CommandHistory().hasHistory())


class EditRedo(base_uicommand.UICommand):
    """Action for redoing the last undone user action."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=self._redo_menu_text(),
            help_text=help.editRedo,
            icon_id="nuvola_actions_edit-redo",
            id=wx.ID_REDO,
            *args,
            **kwargs
        )
        self.registerObserver(
            self._on_history_changed,
            eventType="commandhistory.changed",
            eventSource=patterns.CommandHistory(),
        )

    @staticmethod
    def _redo_menu_text():
        return "%s\tCtrl+Y" % patterns.CommandHistory().redostr(_("&Redo"))

    def _on_history_changed(self, event=None):  # pylint: disable=W0613
        self.update_menu_text(self._redo_menu_text())
        if self.toolbar:
            try:
                self.toolbar.EnableTool(self.id, self.enabled(None))
                self.toolbar.Refresh(False)
            except RuntimeError:
                pass

    def do_command(self, event):
        window_with_focus = wx.Window.FindFocus()
        if isinstance(window_with_focus, wx.TextCtrl):
            window_with_focus.Redo()
        else:
            patterns.CommandHistory().redo()

    def current_menu_text(self):
        return self._redo_menu_text()

    def enabled(self, event):
        window_with_focus = wx.Window.FindFocus()
        if isinstance(window_with_focus, wx.TextCtrl):
            return window_with_focus.CanRedo()
        return bool(patterns.CommandHistory().hasFuture())


class EditCut(ViewerCommand):
    """Action for cutting the currently selected item(s) to the
    clipboard."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Cu&t\tCtrl+X"),
            help_text=help.editCut,
            icon_id="nuvola_actions_edit-cut",
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self._selection_sync = _SelectionSync(self.viewer, self)

    def do_command(self, event):
        window_with_focus = wx.Window.FindFocus()
        if isinstance(window_with_focus, wx.TextCtrl):
            window_with_focus.Cut()
        else:
            cut_command = self.viewer.cutItemCommand()
            cut_command.do()

    def enabled(self, event):
        return self.viewer.has_selection


class EditCopy(ViewerCommand):
    """Action for copying the currently selected item(s) to the
    clipboard."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Copy\tCtrl+C"),
            help_text=help.editCopy,
            icon_id="nuvola_actions_edit-copy",
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self._selection_sync = _SelectionSync(self.viewer, self)

    def do_command(self, event):
        window_with_focus = wx.Window.FindFocus()
        if isinstance(window_with_focus, wx.TextCtrl):
            window_with_focus.Copy()
        else:
            copy_command = command.CopyCommand(
                self.viewer.presentation(), self.viewer.curselection()
            )
            copy_command.do()

    def enabled(self, event):
        return self.viewer.has_selection


class EditPaste(ViewerCommand):
    """Action for pasting the item(s) in the clipboard into the current
    viewer's presentation."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Paste\tCtrl+V"),
            help_text=help.editPaste,
            icon_id="nuvola_actions_edit-paste",
            id=wx.ID_PASTE,
            *args,
            **kwargs
        )

    def do_command(self, event):
        windowWithFocus = wx.Window.FindFocus()
        if isinstance(windowWithFocus, wx.TextCtrl):
            windowWithFocus.Paste()
        else:
            # Use viewer's pasteItemCommand if available
            viewer = self.viewer
            # If no viewer set, try to find one from the focused window hierarchy
            if viewer is None:
                viewer = self._findViewerFromFocus(windowWithFocus)
            if viewer is not None:
                pasteCommand = viewer.pasteItemCommand()
            else:
                pasteCommand = command.PasteCommand()
            if pasteCommand:
                pasteCommand.do()

    def _findViewerFromFocus(self, window):
        """Walk up the window hierarchy to find a viewer with pasteItemCommand.

        This is needed when paste is triggered from menus that don't have
        a viewer reference, but the focused window is inside a viewer.
        """
        while window is not None:
            if hasattr(window, "pasteItemCommand"):
                return window
            window = window.GetParent()
        return None

    def enabled(self, event):
        windowWithFocus = wx.Window.FindFocus()
        if isinstance(windowWithFocus, wx.TextCtrl):
            return windowWithFocus.CanPaste()
        else:
            clipboard = command.Clipboard()
            if not clipboard:
                return False
            if not super().enabled(event):
                return False
            # Check if clipboard contents are compatible with viewer
            if self.viewer and hasattr(self.viewer, "getSupportedPasteTypes"):
                supportedTypes = self.viewer.getSupportedPasteTypes()
                if supportedTypes:
                    items = clipboard.peek()
                    for item in items:
                        if not isinstance(item, supportedTypes):
                            return False
            return True


class EditPasteAsSubItem(ViewerCommand):
    """Action for pasting the item(s) in the clipboard into the current
    taskfile, as a subitem of the currently selected item."""

    shortcut = "\tShift+Ctrl+V"
    default_menu_text = _("P&aste as subitem") + shortcut

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=self.default_menu_text,
            help_text=help.editPasteAsSubitem,
            icon_id="taskcoach_actions_paste_subitem",
            *args,
            **kwargs
        )

    def current_menu_text(self):
        v = self.viewer
        if v.is_task:
            return _("P&aste as subtask") + self.shortcut
        elif v.is_note:
            return _("P&aste as subnote") + self.shortcut
        elif v.is_category:
            return _("P&aste as subcategory") + self.shortcut
        return self.default_menu_text

    def do_command(self, event):
        viewer = self.viewer
        if viewer is None:
            window_with_focus = wx.Window.FindFocus()
            viewer = self._find_viewer_from_focus(window_with_focus)
        if viewer is not None and hasattr(viewer, "pasteAsSubItemCommand"):
            parents = viewer.curselection()
            paste_command = viewer.pasteAsSubItemCommand()
        else:
            parents = self.viewer.curselection() if self.viewer else []
            paste_command = command.PasteAsSubItemCommand(items=parents)
        if paste_command:
            paste_command.do()
            if viewer is not None and hasattr(viewer, "settingsSection"):
                for parent in parents:
                    parent.expand(True, context=viewer.settingsSection())

    def _find_viewer_from_focus(self, window):
        """Walk up the window hierarchy to find a viewer with
        pasteAsSubItemCommand."""
        while window is not None:
            if hasattr(window, "pasteAsSubItemCommand"):
                return window
            window = window.GetParent()
        return None

    def enabled(self, event):
        selection = self.viewer.curselection()
        if not (selection and command.Clipboard()):
            return False
        target_class = selection[0].__class__
        pasted_classes = [
            item.__class__ for item in command.Clipboard().peek()
        ]
        return self._target_and_pasted_are_equal(
            target_class, pasted_classes
        ) or self._target_is_task_and_pasted_is_effort(
            target_class, pasted_classes
        )

    @classmethod
    def _target_is_task_and_pasted_is_effort(
        cls, target_class, pasted_classes
    ):
        """Return whether the target class is a task and the pasted classes
        are all effort."""
        if target_class != task.Task:
            return False
        return cls._target_and_pasted_are_equal(effort.Effort, pasted_classes)

    @staticmethod
    def _target_and_pasted_are_equal(target_class, pasted_classes):
        """Return whether target_class and pasted_classes are all equal."""
        for pasted_class in pasted_classes:
            if pasted_class != target_class:
                return False
        return True


class EditPreferences(settings_uicommand.SettingsCommand):
    """Action for bringing up the preferences dialog."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Preferences...\tAlt+P"),
            help_text=help.editPreferences,
            icon_id="nuvola_actions_configure",
            id=wx.ID_PREFERENCES,
            *args,
            **kwargs
        )

    def do_command(self, event, show=True):  # pylint: disable=W0221
        editor = dialog.preferences.Preferences(
            parent=self.main_window(),
            title=_("Preferences"),
            settings=self.settings,
            taskFile=self.main_window().taskFile,
        )
        editor.Show(show=show)


class EditToolBarPerspective(settings_uicommand.SettingsCommand):
    """Action for editing a customizable toolbar"""

    def __init__(self, toolbar, editorClass, *args, **kwargs):
        self.__toolbar = toolbar
        self.__editorClass = editorClass
        super().__init__(
            help_text=_("Customize toolbar"),
            icon_id="nuvola_apps_preferences-system-session-services",
            menu_text=_("Customize"),
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.__editorClass(
            self.__toolbar,
            self.settings,
            self.main_window(),
            _("Customize toolbar"),
        ).ShowModal()


class SelectAll(ViewerCommand):
    """Action for selecting all items in a viewer."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Select &All\tCtrl+A"),
            help_text=help.editSelectAll,
            icon_id="taskcoach_actions_checkall",
            id=wx.ID_SELECTALL,
            *args,
            **kwargs
        )

    def do_command(self, event):
        window_with_focus = wx.Window.FindFocus()
        if self._is_text_ctrl(window_with_focus):
            window_with_focus.SetSelection(-1, -1)  # Select all text
        else:
            self.viewer.select_all()

    def enabled(self, event):
        return True

    @staticmethod
    def _is_text_ctrl(window):
        """Return whether the window is a text control."""
        return isinstance(window, wx.TextCtrl) or isinstance(
            window, hypertreelist.EditCtrl
        )


class ClearSelection(ViewerCommand):
    """Action for deselecting all items in a viewer."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Deselect All\tCtrl+Shift+A"),
            help_text=_("Deselect all items"),
            icon_id="taskcoach_actions_uncheckall",
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self._selection_sync = _SelectionSync(self.viewer, self)

    def enabled(self, event):
        return self.viewer.has_selection

    def do_command(self, event):
        self.viewer.clear_selection()


class ResetFilter(ViewerCommand):
    """Action for resetting all filters so that all items in all viewers
    become visible."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Clear all filters\tShift-Ctrl-R"),
            help_text=help.reset_filter,
            icon_id="taskcoach_actions_viewalltasks",
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self.registerObserver(
            self._on_filter_change,
            eventType=base.filter.Filter.filter_change_event_type(),
        )

    def _on_filter_change(self, event):
        try:
            self.toolbar.EnableTool(self.id, self.enabled(None))
            self.toolbar.Refresh(False)
        except RuntimeError:
            pass

    def do_command(self, event):
        self.viewer.reset_filter()

    def enabled(self, event):
        return self.viewer.has_filter()


class ResetCategoryFilter(CategoriesCommand):
    """Action for resetting all category filters so that items are no longer
    hidden if the don't belong to a certain category."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Reset all categories\tCtrl-R"),
            help_text=help.resetCategoryFilter,
            *args,
            **kwargs
        )

    def enabled(self, event):
        return self.categories.has_category_filters

    def do_command(self, event):
        self.categories.resetAllFilteredCategories()


class ToggleCategoryFilter(base_uicommand.UICommand):
    """Action for toggling filtering on a specific category."""

    def __init__(self, *args, **kwargs):
        self.category = kwargs.pop("category")
        subject = self.category.subject()
        # Would like to use wx.ITEM_RADIO for mutually exclusive categories, but
        # a menu with radio items always has to have at least of the items
        # checked, while we allow none of the mutually exclusive categories to
        # be checked. Dynamically changing between wx.ITEM_CHECK and
        # wx.ITEM_RADIO would be a work-around in theory, using wx.ITEM_CHECK
        # when none of the mutually exclusive categories is checked and
        # wx.ITEM_RADIO otherwise, but dynamically changing the type of menu
        # items isn't possible. Hence, we use wx.ITEM_CHECK, even for mutual
        # exclusive categories.
        kind = wx.ITEM_CHECK
        super().__init__(
            menu_text="&" + subject.replace("&", "&&"),
            help_text=_("Show/hide items belonging to %s") % subject,
            kind=kind,
            *args,
            **kwargs
        )

    def checked(self):
        return self.category.isFiltered()

    def do_command(self, event):
        self.category.setFiltered(event.IsChecked())


class ViewViewer(settings_uicommand.SettingsCommand, ViewerCommand):
    """Action for opening a new viewer of a specific class."""

    def __init__(self, *args, **kwargs):
        self.taskFile = kwargs.pop("taskFile")
        self.viewerClass = kwargs.pop("viewerClass")
        kwargs.setdefault("icon_id", self.viewerClass.defaultBitmap)
        super().__init__(*args, **kwargs)

    def do_command(self, event):
        from taskcoachlib.gui import viewer

        viewer.addOneViewer(
            self.viewer, self.taskFile, self.settings, self.viewerClass
        )
        self.increaseViewerCount()

    def increaseViewerCount(self):
        """Increase the viewer count for the viewer class this command is
        opening and store the viewer count in the settings."""
        setting = self.viewerClass.__name__.lower() + "count"
        viewerCount = self.settings.getint("view", setting)
        self.settings.set("view", setting, str(viewerCount + 1))


class ViewEffortViewerForSelectedTask(
    settings_uicommand.SettingsCommand, ViewerCommand
):
    def __init__(self, *args, **kwargs):
        from taskcoachlib.gui import viewer

        self.viewerClass = viewer.EffortViewerForSelectedTasks
        self.taskFile = kwargs.pop("taskFile")
        kwargs["icon_id"] = viewer.EffortViewer.defaultBitmap
        super().__init__(*args, **kwargs)

    def do_command(self, event):
        from taskcoachlib.gui import viewer

        viewer.addOneViewer(
            self.viewer, self.taskFile, self.settings, self.viewerClass
        )


class RenameViewer(ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Rename viewer..."),
            help_text=_("Rename the selected viewer"),
            *args,
            **kwargs
        )

    def do_command(self, event):
        active_viewer = self.viewer.active_viewer()
        viewer_name_dialog = wx.TextEntryDialog(
            self.main_window(),
            _("New title for the viewer:"),
            _("Rename viewer"),
            active_viewer.title(),
        )
        if viewer_name_dialog.ShowModal() == wx.ID_OK:
            active_viewer.set_title(viewer_name_dialog.GetValue())
        viewer_name_dialog.Destroy()

    def enabled(self, event):
        return bool(self.viewer.active_viewer())


class ActivateViewer(ViewerCommand):
    def __init__(self, *args, **kwargs):
        self.direction = kwargs.pop("forward")
        super().__init__(*args, **kwargs)

    def do_command(self, event):
        self.viewer.containerWidget.advance_selection(self.direction)

    def enabled(self, event):
        return self.viewer.containerWidget.viewerCount() > 1


class HideCurrentColumn(ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Hide this column"),
            help_text=_("Hide the selected column"),
            *args,
            **kwargs
        )

    def do_command(self, event):
        columnPopupMenu = event.GetEventObject()
        self.viewer.hide_column(columnPopupMenu.columnIndex)

    def enabled(self, event):
        # Unfortunately the event (an UpdateUIEvent) does not give us any
        # information to determine the current column, so we have to find
        # the column ourselves. We use the current mouse position to do so.
        widget = (
            self.viewer.getWidget()
        )  # Must use method to make sure viewer dispatch works!
        x, y = widget.ScreenToClient(wx.GetMousePosition())
        # Use wx.Point because CustomTreeCtrl assumes a wx.Point instance:
        columnIndex = widget.HitTest(wx.Point(x, y))[2]
        # The TreeListCtrl returns -1 for the first column sometimes,
        # don't understand why. Work around as follows:
        if columnIndex == -1:
            columnIndex = 0
        return self.viewer.is_hideable_column(columnIndex)


class ViewColumn(ViewerCommand, settings_uicommand.UICheckCommand):

    def is_setting_checked(self):
        return self.viewer.isVisibleColumnByName(self.setting)

    def do_command(self, event):
        self.viewer.showColumnByName(
            self.setting, self._isMenuItemChecked(event)
        )


class ViewColumns(ViewerCommand, settings_uicommand.UICheckCommand):

    def is_setting_checked(self):
        for columnName in self.setting:
            if not self.viewer.isVisibleColumnByName(columnName):
                return False
        return True

    def do_command(self, event):
        show = self._isMenuItemChecked(event)
        for columnName in self.setting:
            self.viewer.showColumnByName(columnName, show)


class _ViewSettingsSync:
    """Syncs a toolbar button's state with viewer settings changes.
    Sets initial state on construction, then listens for changes."""

    def __init__(self, viewer, button):
        self._button = button
        button.toolbar.EnableTool(button.id, button.enabled(None))
        viewer.registerObserver(
            self._on_view_settings_changed,
            eventType=viewer.view_settings_changed_event_type(),
            eventSource=viewer,
        )

    def _on_view_settings_changed(self, event):
        cmd = self._button
        cmd.toolbar.EnableTool(cmd.id, cmd.enabled(None))
        cmd.toolbar.Refresh(False)


class _SelectionSync:
    """Syncs a toolbar button's enabled state with the viewer's selection.
    Sets initial state on construction, then listens for changes."""

    def __init__(self, viewer, button):
        self._button = button
        button.toolbar.EnableTool(button.id, button.enabled(None))
        viewer.registerObserver(
            self._on_selection_changed,
            eventType=viewer.selection_changed_event_type(),
            eventSource=viewer,
        )

    def _on_selection_changed(self, event):
        cmd = self._button
        cmd.toolbar.EnableTool(cmd.id, cmd.enabled(None))
        cmd.toolbar.Refresh(False)


class ViewExpandAll(ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            icon_id="taskcoach_actions_tree_expand_all",
            menu_text=_("&Expand all\tShift+Ctrl+E"),
            help_text=help.viewExpandAll,
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self._tree_mode_sync = _ViewSettingsSync(self.viewer, self)

    def enabled(self, event):
        return self.viewer.is_tree_viewer()

    def do_command(self, event):
        self.viewer.expand_all()


class ViewCollapseAll(ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            icon_id="taskcoach_actions_tree_collapse_all",
            menu_text=_("Co&llapse all\tShift+Ctrl+C"),
            help_text=help.viewCollapseAll,
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self._tree_mode_sync = _ViewSettingsSync(self.viewer, self)

    def enabled(self, event):
        return self.viewer.is_tree_viewer()

    def do_command(self, event):
        self.viewer.collapse_all()


class ViewerSortByCommand(ViewerCommand, settings_uicommand.UIRadioCommand):

    def is_setting_checked(self):
        return self.viewer.isSortedBy(self.value)

    def do_command(self, event):
        self.viewer.sortBy(self.value)


class ViewerSortOrderCommand(ViewerCommand, settings_uicommand.UICheckCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Ascending"),
            help_text=_("Sort ascending (checked) or descending (unchecked)"),
            *args,
            **kwargs
        )

    def is_setting_checked(self):
        return self.viewer.isSortOrderAscending()

    def do_command(self, event):
        self.viewer.setSortOrderAscending(self._isMenuItemChecked(event))


class ViewerSortCaseSensitive(
    ViewerCommand, settings_uicommand.UICheckCommand
):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Sort &case sensitive"),
            help_text=_(
                "When comparing text, sorting is case sensitive "
                "(checked) or insensitive (unchecked)"
            ),
            *args,
            **kwargs
        )

    def is_setting_checked(self):
        return self.viewer.isSortCaseSensitive()

    def do_command(self, event):
        self.viewer.setSortCaseSensitive(self._isMenuItemChecked(event))


class ViewerSortByTaskStatusFirst(
    ViewerCommand, settings_uicommand.UICheckCommand
):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Sort by status &first"),
            help_text=_(
                "Sort tasks by status (active/inactive/completed) " "first"
            ),
            *args,
            **kwargs
        )

    def is_setting_checked(self):
        return self.viewer.isSortByTaskStatusFirst()

    def do_command(self, event):
        self.viewer.setSortByTaskStatusFirst(self._isMenuItemChecked(event))


class ViewerHideTasks(ViewerCommand, settings_uicommand.UICheckCommand):
    def __init__(self, taskStatus, *args, **kwargs):
        self.__taskStatus = taskStatus
        super().__init__(
            menu_text=taskStatus.hideMenuText,
            help_text=taskStatus.hideHelpText,
            icon_id="synthetic_hide_%s" % taskStatus.statusString,
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self.toolbar.ToggleTool(self.id, self.checked())
        self.registerObserver(
            self._on_filter_change,
            eventType=base.filter.Filter.filter_change_event_type(),
        )

    def _on_filter_change(self, event):
        self.toolbar.ToggleTool(self.id, self.checked())
        self.toolbar.Refresh(False)

    def unique_name(self):
        return super().unique_name() + "_" + str(self.__taskStatus)

    def is_setting_checked(self):
        return self.viewer.is_hiding_task_status(self.__taskStatus)

    def do_command(self, event):
        if wx.GetKeyState(wx.WXK_SHIFT):
            self.viewer.show_only_task_status(self.__taskStatus)
        else:
            self.viewer.hide_task_status(
                self.__taskStatus, self._isMenuItemChecked(event)
            )


class ViewerHideCompositeTasks(
    ViewerCommand, settings_uicommand.UICheckCommand
):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Hide c&omposite tasks"),
            help_text=_("Show/hide tasks with subtasks in list mode"),
            *args,
            **kwargs
        )

    def is_setting_checked(self):
        return self.viewer.is_hiding_composite_tasks()

    def do_command(self, event):
        self.viewer.hide_composite_tasks(self._isMenuItemChecked(event))

    def enabled(self, event):
        return not self.viewer.is_tree_viewer()


class ToggleAutoScroll(settings_uicommand.UICheckCommand):
    """Global toggle: automatically scroll/center the selected item
    when list content changes. When off, views never scroll by
    themselves."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Auto-scroll to selection"),
            help_text=_(
                "Keep the selected item centered when the list changes"
            ),
            icon_id="oxygen_actions_align-vertical-center",
            setting="autoscrollselection",
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self.toolbar.ToggleTool(self.id, self.checked())
        # Keep all toolbar instances (viewer and main window) in sync
        # when the setting changes from any of them or from the menu.
        # Publisher dispatch, not pypubsub; see PUBLISHER_OBSERVER.md.
        self.registerObserver(
            self._on_setting_change,
            eventType="view.autoscrollselection",
            eventSource=self.settings,
        )

    def _on_setting_change(self, event=None):
        try:
            self.toolbar.ToggleTool(self.id, self.checked())
            self.toolbar.Refresh(False)
        except RuntimeError:
            pass  # wrapped C/C++ object has been deleted


class Edit(ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Edit...\tRETURN"),
            help_text=_("Edit the selected item(s)"),
            icon_id="nuvola_actions_edit",
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self._selection_sync = _SelectionSync(self.viewer, self)

    def do_command(self, event, show=True):  # pylint: disable=W0221
        window_with_focus = wx.Window.FindFocus()
        edit_ctrl = self._find_edit_ctrl(window_with_focus)
        if edit_ctrl:
            edit_ctrl.AcceptChanges()
            if edit_ctrl:
                edit_ctrl.Finish()
            return
        try:
            column_name = event.columnName
        except AttributeError:
            column_name = ""
        # curselection() always queries widget fresh (SSOT principle)
        items = self.viewer.curselection()
        editor = self.viewer.editItemDialog(items, self.icon_id, column_name)
        if len(items) > 1:
            # Use modal dialog for multi-item editing to prevent selection
            # changes while editing
            editor.ShowModal()
        else:
            editor.Show(show)

    def enabled(self, event):
        return self.viewer.has_selection

    def _find_edit_ctrl(self, window):
        while window:
            if isinstance(window, hypertreelist.EditCtrl):
                break
            window = window.GetParent()
        return window


class EditTrackedTasks(TaskListCommand, settings_uicommand.SettingsCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Edit &tracked task...\tShift-Alt-T"),
            help_text=_("Edit the currently tracked task(s)"),
            icon_id="nuvola_actions_edit",
            *args,
            **kwargs
        )

    def do_command(self, event, show=True):
        editTaskDialog = dialog.editor.TaskEditor(
            self.main_window(),
            self.taskList.tasks_being_tracked(),
            self.settings,
            self.taskList,
            self.main_window().taskFile,
            icon_id=self.icon_id,
        )
        editTaskDialog.Show(show)
        return editTaskDialog  # for testing purposes

    def enabled(self, event):
        return any(self.taskList.tasks_being_tracked())


class Delete(ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Delete\tCtrl+DEL"),
            help_text=_("Delete the selected item(s)"),
            icon_id="nuvola_actions_edit-delete",
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self._selection_sync = _SelectionSync(self.viewer, self)

    def enabled(self, event):
        return self.viewer.has_selection

    def do_command(self, event):
        window_with_focus = wx.Window.FindFocus()
        if self._window_is_text_ctrl(window_with_focus):
            # Simulate Delete key press
            from_index, to_index = window_with_focus.GetSelection()
            if from_index == to_index:
                pos = window_with_focus.GetInsertionPoint()
                from_index, to_index = pos, pos + 1
            window_with_focus.Remove(from_index, to_index)
        else:
            # Check if we're deleting categories that have assigned objects
            selected_items = self.viewer.curselection()
            if selected_items and isinstance(
                selected_items[0], category.Category
            ):
                assigned_objects = self._get_assigned_objects(selected_items)
                if assigned_objects:
                    self._show_category_in_use_dialog(assigned_objects)
                    return
            delete_command = self.viewer.deleteItemCommand()
            delete_command.do()

    def _get_assigned_objects(self, categories):
        """Collect all objects assigned to the given categories and their
        subcategories."""
        all_assigned = {}
        for cat in categories:
            all_categories = [cat] + list(cat.children(recursive=True))
            for c in all_categories:
                categorizables = c.categorizables()
                if categorizables:
                    all_assigned[c] = list(categorizables)
        return all_assigned

    def _find_note_owner(self, target_note, task_file):
        """Find the owner (task or category) of a note."""
        for a_task in task_file.tasks():
            if hasattr(a_task, "notes"):
                for a_note in a_task.notes(recursive=True):
                    if a_note is target_note:
                        return a_task
        for a_cat in task_file.categories():
            if hasattr(a_cat, "notes"):
                for a_note in a_cat.notes(recursive=True):
                    if a_note is target_note:
                        return a_cat
        return None

    def _get_object_display_path(self, obj, task_file):
        """Get the full display path for an object, including its owner."""
        obj_type = obj.__class__.__name__
        obj_subject = obj.subject(recursive=True)

        if isinstance(obj, note.Note):
            owner = self._find_note_owner(obj, task_file)
            if owner:
                owner_path = owner.subject(recursive=True)
                owner_type = owner.__class__.__name__
                return "[%s] %s -> [%s] %s" % (
                    owner_type,
                    owner_path,
                    obj_type,
                    obj_subject,
                )

        return "[%s] %s" % (obj_type, obj_subject)

    def _show_category_in_use_dialog(self, assigned_objects):
        """Show a scrollable dialog listing all objects that prevent
        category deletion."""
        lines = []
        task_file = self.main_window().taskFile

        for cat, objects in assigned_objects.items():
            cat_name = cat.subject(recursive=True)
            lines.append(_("Category: %s") % cat_name)
            for obj in sorted(
                objects, key=lambda x: x.subject(recursive=True)
            ):
                display_path = self._get_object_display_path(obj, task_file)
                lines.append("  - %s" % display_path)
            lines.append("")

        dlg = wx.Dialog(
            self.main_window(),
            title=_("Cannot Delete - Category In Use"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        sizer = wx.BoxSizer(wx.VERTICAL)

        header_text = wx.StaticText(
            dlg,
            label=_(
                "Cannot delete the selected category/categories "
                "because they have assigned objects:"
            ),
        )
        sizer.Add(header_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)

        text_ctrl = wx.TextCtrl(
            dlg,
            value="\n".join(lines),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
            size=(600, 400),
        )
        sizer.Add(text_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        footer_text = wx.StaticText(
            dlg,
            label=_(
                "Please remove these assignments before deleting "
                "the category."
            ),
        )
        sizer.Add(footer_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)

        ok_btn = wx.Button(dlg, wx.ID_OK, _("OK"))
        ok_btn.SetDefault()
        sizer.Add(ok_btn, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

        dlg.SetSizer(sizer)
        dlg.Fit()
        dlg.CentreOnParent()
        dlg.ShowModal()
        dlg.Destroy()

    @staticmethod
    def _window_is_text_ctrl(window):
        return isinstance(window, wx.TextCtrl) or isinstance(
            window, hypertreelist.EditCtrl
        )


class TaskNew(TaskListCommand, settings_uicommand.SettingsCommand):
    def __init__(self, *args, **kwargs):
        self.taskKeywords = kwargs.pop("taskKeywords", dict())
        taskList = kwargs["taskList"]
        if "menu_text" not in kwargs:  # Provide for subclassing
            kwargs["menu_text"] = taskList.newItemMenuText
            kwargs["help_text"] = taskList.newItemHelpText
        super().__init__(
            icon_id="nuvola_actions_document-new", *args, **kwargs
        )

    def do_command(self, event, show=True):  # pylint: disable=W0221
        kwargs = self.taskKeywords.copy()
        if self.__shouldPresetPlannedStartDateTime():
            kwargs["plannedStartDateTime"] = (
                task.Task.suggestedPlannedStartDateTime()
            )
        if self.__shouldPresetDueDateTime():
            kwargs["dueDateTime"] = task.Task.suggestedDueDateTime()
        if self.__shouldPresetActualStartDateTime():
            kwargs["actualStartDateTime"] = (
                task.Task.suggestedActualStartDateTime()
            )
        if self.__shouldPresetCompletionDateTime():
            kwargs["completionDateTime"] = (
                task.Task.suggestedCompletionDateTime()
            )
        if self.__shouldPresetReminderDateTime():
            kwargs["reminder"] = task.Task.suggestedReminderDateTime()
        newTaskCommand = command.NewTaskCommand(
            self.taskList,
            categories=self.categoriesForTheNewTask(),
            prerequisites=self.prerequisitesForTheNewTask(),
            dependencies=self.dependenciesForTheNewTask(),
            **kwargs
        )
        newTaskCommand.do()
        newTaskDialog = dialog.editor.TaskEditor(
            self.main_window(),
            newTaskCommand.items,
            self.settings,
            self.taskList,
            self.main_window().taskFile,
            icon_id=self.icon_id,
            items_are_new=True,
        )
        newTaskDialog.Show(show)
        return newTaskDialog  # for testing purposes

    def categoriesForTheNewTask(self):
        return self.main_window().taskFile.categories().filteredCategories()

    def prerequisitesForTheNewTask(self):
        return []

    def dependenciesForTheNewTask(self):
        return []

    def __shouldPresetPlannedStartDateTime(self):
        return (
            "plannedStartDateTime" not in self.taskKeywords
            and self.settings.get(
                "view", "defaultplannedstartdatetime"
            ).startswith("preset")
        )

    def __shouldPresetDueDateTime(self):
        return "dueDateTime" not in self.taskKeywords and self.settings.get(
            "view", "defaultduedatetime"
        ).startswith("preset")

    def __shouldPresetActualStartDateTime(self):
        return (
            "actualStartDateTime" not in self.taskKeywords
            and self.settings.get(
                "view", "defaultactualstartdatetime"
            ).startswith("preset")
        )

    def __shouldPresetCompletionDateTime(self):
        return (
            "completionDateTime" not in self.taskKeywords
            and self.settings.get(
                "view", "defaultcompletiondatetime"
            ).startswith("preset")
        )

    def __shouldPresetReminderDateTime(self):
        return "reminder" not in self.taskKeywords and self.settings.get(
            "view", "defaultreminderdatetime"
        ).startswith("preset")


class TaskNewFromTemplate(TaskNew):
    def __init__(self, filename, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__filename = filename
        templateTask = self.__readTemplate()
        self.menu_text = "&" + templateTask.subject().replace(
            "&", "&&"
        )  # pylint: disable=E1103

    def __readTemplate(self):
        return persistence.TemplateXMLReader(
            open(self.__filename, "r", encoding="utf-8")
        ).read()

    def do_command(self, event, show=True):  # pylint: disable=W0221
        # The task template is read every time because it's the
        # TemplateXMLReader that evaluates dynamic values (Now()
        # should be evaluated at task creation for instance).
        templateTask = self.__readTemplate()
        kwargs = templateTask.__getcopystate__()  # pylint: disable=E1103
        kwargs["categories"] = self.categoriesForTheNewTask()
        newTaskCommand = command.NewTaskCommand(self.taskList, **kwargs)
        newTaskCommand.do()
        # pylint: disable=W0142
        newTaskDialog = dialog.editor.TaskEditor(
            self.main_window(),
            newTaskCommand.items,
            self.settings,
            self.taskList,
            self.main_window().taskFile,
            icon_id=self.icon_id,
            items_are_new=True,
        )
        newTaskDialog.Show(show)
        return newTaskDialog  # for testing purposes


class TaskNewFromTemplateButton(
    mixin_uicommand.PopupButtonMixin,
    TaskListCommand,
    settings_uicommand.SettingsCommand,
):
    def createPopupMenu(self):
        from taskcoachlib.gui import menu

        return menu.TaskTemplateMenu(
            self.main_window(), self.taskList, self.settings
        )

    def get_menu_text(self):
        return _("New task from &template")

    def get_help_text(self):
        return _("Create a new task from a template")


class NewTaskWithSelectedCategories(TaskNew, ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("New task with selected &categories..."),
            help_text=_(
                "Insert a new task with the selected categories checked"
            ),
            *args,
            **kwargs
        )

    def enabled(self, event):
        return super().enabled(event) and bool(self.viewer.curselection())

    def categoriesForTheNewTask(self):
        return self.viewer.curselection()


class NewTaskWithSelectedTasksAsPrerequisites(TaskNew, ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("New task with selected tasks as &prerequisites..."),
            help_text=_(
                "Insert a new task with the selected tasks as prerequisite tasks"
            ),
            *args,
            **kwargs
        )

    def enabled(self, event):
        return self.viewer.has_selection and self.viewer.is_task

    def prerequisitesForTheNewTask(self):
        return self.viewer.curselection()


class NewTaskWithSelectedTasksAsDependencies(TaskNew, ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("New task with selected tasks as &dependents..."),
            help_text=_(
                "Insert a new task with the selected tasks as dependent tasks"
            ),
            *args,
            **kwargs
        )

    def enabled(self, event):
        return self.viewer.has_selection and self.viewer.is_task

    def dependenciesForTheNewTask(self):
        return self.viewer.curselection()


class NewSubItem(ViewerCommand):
    shortcut = (
        "\tCtrl+INS" if operating_system.isWindows() else "\tShift+Ctrl+N"
    )
    defaultMenuText = _("New &subitem...") + shortcut

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=self.defaultMenuText,
            help_text=_("Insert a new subitem of the selected item"),
            icon_id="taskcoach_actions_newsub",
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self._selection_sync = _SelectionSync(self.viewer, self)

    def do_command(self, event, show=True):  # pylint: disable=W0221
        self.viewer.newSubItemDialog(icon_id=self.icon_id).Show(show)

    def enabled(self, event):
        v = self.viewer
        return v.has_selection and (v.is_task or v.is_note or v.is_category)

    def current_menu_text(self):
        v = self.viewer
        if v.is_task:
            return _("New &subtask...") + self.shortcut
        elif v.is_note:
            return _("New &subnote...") + self.shortcut
        elif v.is_category:
            return _("New &subcategory...") + self.shortcut
        return self.defaultMenuText


class TaskMarkActive(
    settings_uicommand.SettingsCommand,
    ViewerCommand,
):
    def __init__(self, *args, **kwargs):
        super().__init__(
            icon_id=task.active.getBitmap(kwargs["settings"]),
            menu_text=_("Mark task &active\tAlt+RETURN"),
            help_text=_("Mark the selected task(s) active"),
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self._selection_sync = _SelectionSync(self.viewer, self)

    def do_command(self, event):
        command.MarkActiveCommand(
            self.viewer.presentation(), self.viewer.curselection()
        ).do()

    def enabled(self, event):
        selection = self.viewer.curselection()
        return (
            bool(selection)
            and self.viewer.is_task
            and any(
                t.actualStartDateTime() > date.Now() or t.completed()
                for t in selection
            )
        )


class TaskMarkInactive(
    settings_uicommand.SettingsCommand,
    ViewerCommand,
):
    def __init__(self, *args, **kwargs):
        super().__init__(
            icon_id=task.inactive.getBitmap(kwargs["settings"]),
            menu_text=_("Mark task &inactive\tCtrl+Alt+RETURN"),
            help_text=_("Mark the selected task(s) inactive"),
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self._selection_sync = _SelectionSync(self.viewer, self)

    def do_command(self, event):
        command.MarkInactiveCommand(
            self.viewer.presentation(), self.viewer.curselection()
        ).do()

    def enabled(self, event):
        selection = self.viewer.curselection()
        return (
            bool(selection)
            and self.viewer.is_task
            and any(not t.inactive() and not t.late() for t in selection)
        )


class TaskMarkCompleted(
    settings_uicommand.SettingsCommand,
    ViewerCommand,
):
    def __init__(self, *args, **kwargs):
        super().__init__(
            icon_id=task.completed.getBitmap(kwargs["settings"]),
            menu_text=_("Mark task &completed\tCtrl+RETURN"),
            help_text=_("Mark the selected task(s) completed"),
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self._selection_sync = _SelectionSync(self.viewer, self)

    def do_command(self, event):
        mark_completed_command = command.MarkCompletedCommand(
            self.viewer.presentation(), self.viewer.curselection()
        )
        mark_completed_command.do()

    def enabled(self, event):
        selection = self.viewer.curselection()
        return (
            bool(selection)
            and self.viewer.is_task
            and any(not t.completed() for t in selection)
        )


class TaskMaxPriority(TaskListCommand, ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Maximize priority\tShift+Ctrl+I"),
            help_text=help.taskMaxPriority,
            icon_id="nuvola_actions_arrow-up-double",
            *args,
            **kwargs
        )

    def enabled(self, event):
        return self.viewer.has_selection and self.viewer.is_task

    def do_command(self, event):
        max_priority = command.MaxPriorityCommand(
            self.taskList, self.viewer.curselection()
        )
        max_priority.do()


class TaskMinPriority(TaskListCommand, ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Minimize priority\tShift+Ctrl+D"),
            help_text=help.taskMinPriority,
            icon_id="nuvola_actions_arrow-down-double",
            *args,
            **kwargs
        )

    def enabled(self, event):
        return self.viewer.has_selection and self.viewer.is_task

    def do_command(self, event):
        min_priority = command.MinPriorityCommand(
            self.taskList, self.viewer.curselection()
        )
        min_priority.do()


class TaskPriorityParentMenu(ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Priority"),
            help_text=_("Change the priority of the selected task(s)"),
            icon_id="nuvola_actions_arrow-up",
            *args,
            **kwargs
        )

    def enabled(self, event):
        return self.viewer.has_selection and self.viewer.is_task

    def do_command(self, event):
        pass


class TaskIncPriority(TaskListCommand, ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Increase priority\tCtrl+I"),
            help_text=help.taskIncreasePriority,
            icon_id="nuvola_actions_arrow-up",
            *args,
            **kwargs
        )

    def enabled(self, event):
        return self.viewer.has_selection and self.viewer.is_task

    def do_command(self, event):
        inc_priority = command.IncPriorityCommand(
            self.taskList, self.viewer.curselection()
        )
        inc_priority.do()


class TaskDecPriority(TaskListCommand, ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Decrease priority\tCtrl+D"),
            help_text=help.taskDecreasePriority,
            icon_id="nuvola_actions_arrow-down",
            *args,
            **kwargs
        )

    def enabled(self, event):
        return self.viewer.has_selection and self.viewer.is_task

    def do_command(self, event):
        dec_priority = command.DecPriorityCommand(
            self.taskList, self.viewer.curselection()
        )
        dec_priority.do()


class DragAndDropCommand(ViewerCommand):
    def on_command_activate(
        self, dropItem, dragItems, part, column
    ):  # pylint: disable=W0221
        """Override on_command_activate to be able to accept two items instead
        of one event."""
        self.do_command(
            dropItem,
            dragItems,
            part,
            None if column == -1 else self.viewer.visibleColumns()[column],
            column,  # Pass raw column index as dropColumn
        )

    def do_command(
        self, dropItem, dragItems, part, column, dropColumn=-1
    ):  # pylint: disable=W0221
        dragAndDropCommand = self.createCommand(
            dropItem=dropItem,
            dragItems=dragItems,
            part=part,
            column=column,
            isTree=self.viewer.is_tree_viewer(),
            dropColumn=dropColumn,
        )
        if dragAndDropCommand.canDo():
            dragAndDropCommand.do()
            return dragAndDropCommand

    def createCommand(
        self, dropItem, dragItems, part, column, isTree, dropColumn=-1
    ):
        raise NotImplementedError  # pragma: no cover


class OrderingDragAndDropCommand(DragAndDropCommand):
    def do_command(self, dropItem, dragItems, part, column, dropColumn=-1):
        cmd = super().do_command(dropItem, dragItems, part, column, dropColumn)
        if cmd is not None and cmd.isOrdering():
            sortCommand = ViewerSortByCommand(
                viewer=self.viewer, value="ordering"
            )
            sortCommand.do_command(None)


class TaskDragAndDrop(OrderingDragAndDropCommand, TaskListCommand):
    def createCommand(
        self, dropItem, dragItems, part, column, isTree, dropColumn=-1
    ):
        # Get column name if dropColumn is valid
        dropColumnName = None
        if dropColumn >= 0:
            visibleCols = self.viewer.visibleColumns()
            if dropColumn < len(visibleCols):
                dropColumnName = visibleCols[dropColumn].name()

        return command.DragAndDropTaskCommand(
            self.taskList,
            dragItems,
            drop=[dropItem],
            part=part,
            column=column,
            isTree=isTree,
            dropColumn=dropColumn,
            dropColumnName=dropColumnName,
        )


class ToggleCategory(ViewerCommand):
    def __init__(self, *args, **kwargs):
        self.category = kwargs.pop("category")
        subject = self.category.subject()
        # Would like to use wx.ITEM_RADIO for mutually exclusive categories, but
        # a menu with radio items always has to have at least of the items
        # checked, while we allow none of the mutually exclusive categories to
        # be checked. Dynamically changing between wx.ITEM_CHECK and
        # wx.ITEM_RADIO would be a work-around in theory, using wx.ITEM_CHECK
        # when none of the mutually exclusive categories is checked and
        # wx.ITEM_RADIO otherwise, but dynamically changing the type of menu
        # items isn't possible. Hence, we use wx.ITEM_CHECK, even for mutual
        # exclusive categories.
        super().__init__(
            menu_text="&" + subject.replace("&", "&&"),
            help_text=_("Toggle %s") % subject,
            kind=wx.ITEM_CHECK,
            *args,
            **kwargs
        )

    def do_command(self, event):
        check = command.ToggleCategoryCommand(
            category=self.category, items=self.viewer.curselection()
        )
        check.do()

    def checked(self):
        selection = self.viewer.curselection()
        if not selection:
            return False
        return all(self.category in item.categories() for item in selection)

    def enabled(self, event):
        selection = self.viewer.curselection()
        if not selection:
            return False
        if not (self.viewer.is_task or self.viewer.is_note):
            return False
        if self.viewer.is_showing_categories():
            return False
        mutual_exclusive_ancestors = [
            ancestor
            for ancestor in self.category.ancestors()
            if ancestor.isMutualExclusive()
        ]
        for categorizable in selection:
            for ancestor in mutual_exclusive_ancestors:
                if ancestor not in categorizable.categories():
                    return False
        return True


class Mail(ViewerCommand):
    rx_attr = re.compile(r"(cc|to)=(.*)")

    def __init__(self, *args, **kwargs):
        menu_text = (
            _("&Mail...\tShift-Ctrl-M")
            if operating_system.isMac()
            else _("&Mail...\tCtrl-M")
        )
        super().__init__(
            menu_text=menu_text,
            help_text=help.mailItem,
            icon_id="nuvola_apps_email",
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self._selection_sync = _SelectionSync(self.viewer, self)

    def enabled(self, event):
        return self.viewer.has_selection

    def do_command(
        self, event, mail=sendMail, showerror=wx.MessageBox
    ):  # pylint: disable=W0221
        items = self.viewer.curselection()
        subject = self.subject(items)
        body = self.body(items)
        to = self.to(items)
        cc = self.cc(items)
        self.mail(to, cc, subject, body, mail, showerror)

    def subject(self, items):
        assert items
        if len(items) > 2:
            return _("Several things")
        elif len(items) == 2:
            subjects = [item.subject(recursive=True) for item in items]
            return " ".join([subjects[0], _("and"), subjects[1]])
        else:
            return items[0].subject(recursive=True)

    def body(self, items):
        if len(items) > 1:
            body_lines = []
            for item in items:
                body_lines.extend(self._item_to_lines(item))
        else:
            body_lines = items[0].description().splitlines()
        return "\r\n".join(body_lines)

    def to(self, items):
        return self._mail_attr("to", items)

    def cc(self, items):
        return self._mail_attr("cc", items)

    def _mail_attr(self, name, items):
        sets = []
        for item in items:
            sets.append(
                set(
                    [
                        value[len(name) + 1 :]
                        for value in item.customAttributes("mailto")
                        if value.startswith("%s=" % name)
                    ]
                )
            )
        return reduce(operator.or_, sets)

    def _item_to_lines(self, item):
        lines = []
        subject = item.subject(recursive=True)
        lines.append(subject)
        if item.description():
            lines.extend(item.description().splitlines())
            lines.extend("\r\n")
        return lines

    def mail(self, to, cc, subject, body, mail, showerror):
        try:
            mail(to, subject, body, cc=cc)
        except Exception:
            # Try again with a dummy recipient:
            try:
                mail("recipient@domain.com", subject, body)
            except Exception as reason:  # pylint: disable=W0703
                showerror(
                    _("Cannot send email:\n%s") % str(reason),
                    caption=_("%s mail error") % meta.name,
                    style=wx.ICON_ERROR,
                )


class AddNote(ViewerCommand, settings_uicommand.SettingsCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Add &note...\tCtrl+B"),
            help_text=help.addNote,
            icon_id="nuvola_apps_knotes",
            *args,
            **kwargs
        )

    def enabled(self, event):
        v = self.viewer
        return v.has_selection and (
            v.is_task or v.is_category or v.is_attachment
        )

    def do_command(self, event, show=True):  # pylint: disable=W0221
        addNoteCommand = command.AddNoteCommand(
            self.viewer.presentation(), self.viewer.curselection()
        )
        addNoteCommand.do()
        editDialog = dialog.editor.NoteEditor(
            self.main_window(),
            addNoteCommand.items,
            self.settings,
            self.viewer.presentation(),
            self.main_window().taskFile,
            icon_id=self.icon_id,
        )
        editDialog.Show(show)
        return editDialog  # for testing purposes


class OpenAllNotes(ViewerCommand, settings_uicommand.SettingsCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Open all notes...\tShift+Ctrl+B"),
            help_text=help.openAllNotes,
            icon_id="nuvola_actions_edit",
            *args,
            **kwargs
        )

    def enabled(self, event):
        v = self.viewer
        if not v.has_selection:
            return False
        if not (v.is_task or v.is_category or v.is_attachment):
            return False
        return any(item.notes() for item in v.curselection())

    def do_command(self, event):
        for item in self.viewer.curselection():
            for note in item.notes():
                editDialog = dialog.editor.NoteEditor(
                    self.main_window(),
                    [note],
                    self.settings,
                    self.viewer.presentation(),
                    self.main_window().taskFile,
                    icon_id=self.icon_id,
                )
                editDialog.Show()


class EffortNew(
    ViewerCommand,
    EffortListCommand,
    TaskListCommand,
    settings_uicommand.SettingsCommand,
):
    def __init__(self, *args, **kwargs):
        effort_list = kwargs["effortList"]
        super().__init__(
            icon_id="nuvola_actions_document-new",
            menu_text=effort_list.newItemMenuText,
            help_text=effort_list.newItemHelpText,
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        if self.viewer:
            self._selection_sync = _SelectionSync(self.viewer, self)

    def enabled(self, event):
        if not self.taskList:
            return False
        # When viewer is showing tasks, require a task to be selected
        if self.viewer and self.viewer.is_showing_tasks():
            return bool(self.viewer.curselection())
        return True

    def do_command(self, event, show=True):
        if (
            self.viewer
            and self.viewer.is_showing_tasks()
            and self.viewer.curselection()
        ):
            selected_tasks = self.viewer.curselection()
        elif self.viewer and self.viewer.is_showing_effort():
            selected_efforts = self.viewer.curselection()
            if selected_efforts:
                selected_tasks = [selected_efforts[0].task()]
            else:
                selected_tasks = [
                    self.first_task(self.viewer.domainObjectsToView())
                ]
        else:
            selected_tasks = [self.first_task(self.taskList)]

        new_effort_command = command.NewEffortCommand(
            self.effortList, selected_tasks
        )
        new_effort_command.do()
        new_effort_dialog = dialog.editor.EffortEditor(
            self.main_window(),
            new_effort_command.items,
            self.settings,
            self.effortList,
            self.main_window().taskFile,
            icon_id=self.icon_id,
        )
        if show:
            new_effort_dialog.Show()
        return new_effort_dialog

    @staticmethod
    def first_task(tasks):
        decorated = [(t.subject(recursive=True), t) for t in tasks]
        decorated.sort()
        return decorated[0][1]


class EffortStart(ViewerCommand, TaskListCommand):
    """UICommand to start tracking effort for the selected task(s)."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            icon_id="nuvola_apps_clock",
            menu_text=_("&Start tracking effort\tCtrl-T"),
            help_text=help.effortStart,
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self._selection_sync = _SelectionSync(self.viewer, self)

    def do_command(self, event):
        start = command.StartEffortCommand(
            self.taskList, self.viewer.curselection()
        )
        start.do()

    def enabled(self, event):
        selection = self.viewer.curselection()
        return (
            bool(selection)
            and self.viewer.is_task
            and any(
                not t.completed() and not t.isBeingTracked() for t in selection
            )
        )


class EffortStartForEffort(ViewerCommand, TaskListCommand):
    """UICommand to start tracking for the task(s) of selected effort(s)."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            icon_id="nuvola_apps_clock",
            menu_text=_("&Start tracking effort"),
            help_text=_(
                "Start tracking effort for the task(s) of the selected effort(s)"
            ),
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self._selection_sync = _SelectionSync(self.viewer, self)

    def do_command(self, event):
        start = command.StartEffortCommand(
            self.taskList, self.trackable_tasks()
        )
        start.do()

    def enabled(self, event):
        selection = self.viewer.curselection()
        return (
            bool(selection)
            and self.viewer.is_effort
            and bool(self.trackable_tasks())
        )

    def trackable_tasks(self):
        tasks = set([e.task() for e in self.viewer.curselection()])
        return [
            t for t in tasks if not t.completed() and not t.isBeingTracked()
        ]


class EffortStartForTask(TaskListCommand):
    """UICommand to start tracking for a specific task. This command can
    be used to build a menu with separate menu items for all tasks.
    See gui.menu.StartEffortForTaskMenu."""

    def __init__(self, *args, **kwargs):
        self.task = kwargs.pop("task")
        subject = self.task.subject() or _("(No subject)")
        super().__init__(
            icon_id=self.task.icon_id(recursive=True),
            menu_text="&" + subject.replace("&", "&&"),
            help_text=_("Start tracking effort for %s") % subject,
            *args,
            **kwargs
        )

    def do_command(self, event):
        start = command.StartEffortCommand(self.taskList, [self.task])
        start.do()

    def enabled(self, event):
        return not self.task.isBeingTracked() and not self.task.completed()


class EffortStartButton(mixin_uicommand.PopupButtonMixin, TaskListCommand):
    def __init__(self, *args, **kwargs):
        kwargs["taskList"] = base.filter.DeletedFilter(kwargs["taskList"])
        super().__init__(
            icon_id="taskcoach_actions_clock_menu_icon",
            menu_text=_("&Start tracking effort"),
            help_text=_(
                "Select a task via the menu and start tracking effort for it"
            ),
            *args,
            **kwargs
        )

    def createPopupMenu(self):
        from taskcoachlib.gui import menu

        return menu.StartEffortForTaskMenu(self.main_window(), self.taskList)


class EffortStop(EffortListCommand, TaskListCommand, ViewerCommand):
    defaultMenuText = _(
        "Stop tracking or resume tracking effort\tShift+Ctrl+T"
    )
    defaultHelpText = help.effortStopOrResume
    stopMenuText = _("St&op tracking %s\tShift+Ctrl+T")
    stopHelpText = _("Stop tracking effort for the active task(s)")
    resumeMenuText = _("&Resume tracking %s\tShift+Ctrl+T")
    resumeHelpText = _("Resume tracking effort for the last tracked task")

    def __init__(self, *args, **kwargs):
        super().__init__(
            icon_id="taskcoach_actions_clock_resume_icon",
            icon_id2="taskcoach_actions_clock_stop_icon",
            menu_text=self.defaultMenuText,
            help_text=self.defaultHelpText,
            kind=wx.ITEM_CHECK,
            *args,
            **kwargs
        )
        self.__tracker = effort.EffortListTracker(self.effortList)
        for subtype in ["", ".added", ".removed"]:
            self.__tracker.subscribe(
                self.__onEffortsChanged, "effortlisttracker%s" % subtype
            )
        self.__current_icon_id = None

    def removeInstance(self):
        self._EffortStop__tracker.removeInstance()
        super().removeInstance()

    def __onEffortsChanged(self, efforts):
        self.updateUI()

    def efforts(self):
        selectedEfforts = set()
        for item in self.viewer.curselection():
            if isinstance(item, task.Task):
                selectedEfforts |= set(item.efforts())
            elif isinstance(item, effort.Effort):
                selectedEfforts.add(item)
        selectedEfforts &= set(self.__tracker.trackedEfforts())
        return (
            selectedEfforts
            if selectedEfforts
            else self.__tracker.trackedEfforts()
        )

    def do_command(self, event=None):
        efforts = self.efforts()
        if efforts:
            # Stop the tracked effort(s)
            effortCommand = command.StopEffortCommand(self.effortList, efforts)
        else:
            # Resume tracking the last task
            effortCommand = command.StartEffortCommand(
                self.taskList, [self.mostRecentTrackedTask()]
            )
        effortCommand.do()

    def enabled(self, event=None):
        # If there are tracked efforts this command will stop them. If there are
        # untracked efforts this command will resume them. Otherwise this
        # command is disabled.
        return self.anyTrackedEfforts() or self.anyStoppedEfforts()

    def updateUI(self):
        if wx.GetApp().quitting:
            return
        paused = self.anyStoppedEfforts() and not self.anyTrackedEfforts()
        if self.toolbar:
            self.toolbar.EnableTool(self.id, self.enabled(None))
        self.updateToolState(not paused)
        current_icon_id = self.icon_id if paused else self.icon_id2
        menu_text = self.get_menu_text(paused)
        if (current_icon_id != self.__current_icon_id) or bool(
            [
                item
                for item in self.menu_items
                if item.GetItemLabel() != menu_text
            ]
        ):
            self.__current_icon_id = current_icon_id
            self.updateToolBitmap(current_icon_id)
            self.update_tool_help()
            self.updateMenuItems(paused)

    def updateToolState(self, paused):
        if not self.toolbar:
            return  # Toolbar is hidden
        if paused != self.toolbar.GetToolState(self.id):
            self.toolbar.ToggleTool(self.id, paused)

    def updateToolBitmap(self, icon_id):
        if not self.toolbar:
            return  # Toolbar is hidden
        bitmap = icon_catalog.get_bitmap(
            icon_id, self.toolbar.GetToolBitmapSize()[0]
        )
        # On wxGTK, changing the bitmap doesn't work when the tool is
        # disabled, so we first enable it if necessary:
        disable = False
        if not self.toolbar.GetToolEnabled(self.id):
            self.toolbar.EnableTool(self.id, True)
            disable = True
        self.toolbar.SetToolNormalBitmap(self.id, bitmap)
        if disable:
            self.toolbar.EnableTool(self.id, False)
        self.toolbar.Realize()

    def updateMenuItems(self, paused):
        menu_text = self.get_menu_text(paused)
        help_text = self.get_help_text(paused)
        for menuItem in self.menu_items:
            menuItem.Check(paused)
            menuItem.SetItemLabel(menu_text)
            menuItem.SetHelp(help_text)

    def get_menu_text(self, paused=None):  # pylint: disable=W0221
        if self.anyTrackedEfforts():
            trackedEfforts = list(self.efforts())
            subject = (
                _("multiple tasks")
                if len(trackedEfforts) > 1
                else trackedEfforts[0].task().subject()
            )
            return self.stopMenuText % self.trimmedSubject(subject)
        if paused is None:
            paused = self.anyStoppedEfforts()
        if paused:
            return self.resumeMenuText % self.trimmedSubject(
                self.mostRecentTrackedTask().subject()
            )
        else:
            return self.defaultMenuText

    def get_help_text(self, paused=None):  # pylint: disable=W0221
        if self.anyTrackedEfforts():
            return self.stopHelpText
        if paused is None:
            paused = self.anyStoppedEfforts()
        return self.resumeHelpText if paused else self.defaultHelpText

    def anyStoppedEfforts(self):
        return bool(self.effortList.maxDateTime())

    def anyTrackedEfforts(self):
        return bool(self.efforts())

    def mostRecentTrackedTask(self):
        stopTimes = [
            (effort.getStop(), effort)
            for effort in self.effortList
            if effort.getStop() is not None
        ]
        return max(stopTimes)[1].task()

    @staticmethod
    def trimmedSubject(subject, maxLength=35, postFix="..."):
        trim = len(subject) > maxLength
        return (
            subject[: maxLength - len(postFix)] + postFix if trim else subject
        )


class CategoryNew(CategoriesCommand, settings_uicommand.SettingsCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            icon_id="nuvola_actions_document-new",
            menu_text=_("New category...\tCtrl-G"),
            help_text=help.categoryNew,
            *args,
            **kwargs
        )

    def do_command(self, event, show=True):  # pylint: disable=W0221
        newCategoryCommand = command.NewCategoryCommand(self.categories)
        newCategoryCommand.do()
        taskFile = self.main_window().taskFile
        newCategoryDialog = dialog.editor.CategoryEditor(
            self.main_window(),
            newCategoryCommand.items,
            self.settings,
            taskFile.categories(),
            taskFile,
            icon_id=self.icon_id,
        )
        newCategoryDialog.Show(show)


class CategoryDragAndDrop(OrderingDragAndDropCommand, CategoriesCommand):
    def createCommand(
        self, dropItem, dragItems, part, column, isTree, dropColumn=-1
    ):
        return command.DragAndDropCategoryCommand(
            self.categories,
            dragItems,
            drop=[dropItem],
            part=part,
            column=column,
            isTree=isTree,
            dropColumn=dropColumn,
        )


class CategoryCheckAll(ViewerCommand):
    """Command to check all category checkboxes in the viewer.

    Used in the category viewer to quickly select all categories for
    filtering or assignment.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            icon_id="taskcoach_actions_checkall",
            menu_text=_("Check &all categories"),
            help_text=_("Check all category checkboxes"),
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.viewer.check_all_categories()


class CategoryUncheckAll(ViewerCommand):
    """Command to uncheck all category checkboxes in the viewer.

    Used in the category viewer to quickly deselect all categories.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            icon_id="taskcoach_actions_uncheckall",
            menu_text=_("&Uncheck all categories"),
            help_text=_("Uncheck all category checkboxes"),
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.viewer.uncheck_all_categories()


class NoteNew(NotesCommand, settings_uicommand.SettingsCommand, ViewerCommand):
    menu_text = _("New note...\tCtrl-J")
    help_text = help.noteNew

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=self.menu_text,
            help_text=self.help_text,
            icon_id="nuvola_actions_document-new",
            *args,
            **kwargs
        )

    def do_command(self, event, show=True):  # pylint: disable=W0221
        if self.viewer and self.viewer.is_showing_notes():
            noteDialog = self.viewer.newItemDialog(icon_id=self.icon_id)
        else:
            newNoteCommand = command.NewNoteCommand(
                self.notes, categories=self.categoriesForTheNewNote()
            )
            newNoteCommand.do()
            noteDialog = dialog.editor.NoteEditor(
                self.main_window(),
                newNoteCommand.items,
                self.settings,
                self.notes,
                self.main_window().taskFile,
                icon_id=self.icon_id,
            )
        noteDialog.Show(show)
        return noteDialog  # for testing purposes

    def categoriesForTheNewNote(self):
        return self.main_window().taskFile.categories().filteredCategories()


class NewNoteWithSelectedCategories(NoteNew, ViewerCommand):
    menu_text = _("New &note with selected categories...")
    help_text = _("Insert a new note with the selected categories checked")

    def enabled(self, event):
        return super().enabled(event) and bool(self.viewer.curselection())

    def categoriesForTheNewNote(self):
        return self.viewer.curselection()


class NoteDragAndDrop(OrderingDragAndDropCommand, NotesCommand):
    def createCommand(
        self, dropItem, dragItems, part, column, isTree, dropColumn=-1
    ):
        return command.DragAndDropNoteCommand(
            self.notes,
            dragItems,
            drop=[dropItem],
            part=part,
            column=column,
            isTree=isTree,
            dropColumn=dropColumn,
        )


class AttachmentNew(
    AttachmentsCommand, ViewerCommand, settings_uicommand.SettingsCommand
):
    def __init__(self, *args, **kwargs):
        attachments = kwargs["attachments"]
        if "menu_text" not in kwargs:
            kwargs["menu_text"] = attachments.newItemMenuText
            kwargs["help_text"] = attachments.newItemHelpText
        super().__init__(
            icon_id="nuvola_actions_document-new", *args, **kwargs
        )

    def do_command(self, event, show=True):  # pylint: disable=W0221
        attachmentDialog = self.viewer.newItemDialog(icon_id=self.icon_id)
        attachmentDialog.Show(show)
        return attachmentDialog  # for testing purposes


class AddAttachment(ViewerCommand, settings_uicommand.SettingsCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Add attachment...\tShift-Ctrl-A"),
            help_text=help.addAttachment,
            icon_id="nuvola_status_mail-attachment",
            *args,
            **kwargs
        )

    def enabled(self, event):
        v = self.viewer
        return v.has_selection and (v.is_task or v.is_category or v.is_note)

    def do_command(self, event):
        filename = widgets.AttachmentSelector()
        if not filename:
            return
        attachmentBase = self.settings.get("file", "attachmentbase")
        if attachmentBase:
            filename = attachment.getRelativePath(filename, attachmentBase)
        addAttachmentCommand = command.AddAttachmentCommand(
            self.viewer.presentation(),
            self.viewer.curselection(),
            attachments=[attachment.FileAttachment(filename)],
        )
        addAttachmentCommand.do()


def openAttachments(attachments, settings, showerror):
    attachmentBase = settings.get("file", "attachmentbase")
    for eachAttachment in attachments:
        try:
            eachAttachment.open(attachmentBase)
        except Exception as instance:  # pylint: disable=W0703
            showerror(
                render.exception(Exception, instance),
                caption=_("Error opening attachment"),
                style=wx.ICON_ERROR,
            )


class AttachmentOpen(
    ViewerCommand,
    AttachmentsCommand,
    settings_uicommand.SettingsCommand,
):
    def __init__(self, *args, **kwargs):
        attachments = kwargs["attachments"]
        super().__init__(
            icon_id="nuvola_actions_document-open",
            menu_text=attachments.openItemMenuText,
            help_text=attachments.openItemHelpText,
            *args,
            **kwargs
        )

    def enabled(self, event):
        return (
            self.viewer.has_selection and self.viewer.is_showing_attachments()
        )

    def do_command(
        self, event, showerror=wx.MessageBox
    ):  # pylint: disable=W0221
        openAttachments(self.viewer.curselection(), self.settings, showerror)


class OpenAllAttachments(ViewerCommand, settings_uicommand.SettingsCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Open all attachments...\tShift+Ctrl+O"),
            help_text=help.openAllAttachments,
            icon_id="nuvola_status_mail-attachment",
            *args,
            **kwargs
        )

    def enabled(self, event):
        if not self.viewer.has_selection:
            return False
        return any(
            item.attachments()
            for item in self.viewer.curselection()
            if not isinstance(item, effort.Effort)
        )

    def do_command(
        self, event, showerror=wx.MessageBox
    ):  # pylint: disable=W0221
        allAttachments = []
        for item in self.viewer.curselection():
            allAttachments.extend(item.attachments())
        openAttachments(allAttachments, self.settings, showerror)


class DialogCommand(base_uicommand.UICommand):
    def __init__(self, *args, **kwargs):
        self._dialogTitle = kwargs.pop("dialogTitle")
        self._dialogText = kwargs.pop("dialogText")
        self._direction = kwargs.pop("direction", None)
        self.closed = True
        super().__init__(*args, **kwargs)

    def do_command(self, event):
        self.closed = False
        # pylint: disable=W0201
        self.dialog = widgets.HTMLDialog(
            self._dialogTitle,
            self._dialogText,
            parent=wx.GetApp().GetTopWindow(),
            icon_id=self.icon_id,
            direction=self._direction,
        )
        for event in wx.EVT_CLOSE, wx.EVT_BUTTON:
            self.dialog.Bind(event, self.onClose)
        self.dialog.Show()

    def onClose(self, event):
        self.closed = True
        self.dialog.Destroy()
        event.Skip()

    def enabled(self, event):
        return self.closed


class Help(DialogCommand):
    def __init__(self, *args, **kwargs):
        if operating_system.isMac():
            # Use default keyboard shortcut for Mac OS X:
            menu_text = _("&Help contents\tCtrl+?")
        else:
            # Use a letter, because 'Ctrl-?' doesn't work on Windows:
            menu_text = _("&Help contents\tCtrl+H")
        super().__init__(
            menu_text=menu_text,
            help_text=help.help,
            icon_id="nuvola_actions_help-about",
            dialogTitle=_("Help"),
            dialogText=help.helpHTML,
            id=wx.ID_HELP,
            *args,
            **kwargs
        )


class Tips(settings_uicommand.SettingsCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Tips"),
            help_text=_("Tips about the program"),
            icon_id="nuvola_apps_ktip",
            *args,
            **kwargs
        )

    def do_command(self, event):
        help.showTips(self.main_window(), self.settings)


class Anonymize(IOCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Anonymize"),
            help_text=_("Anonymize a task file to attach it to a bug report"),
            *args,
            **kwargs
        )

    def do_command(self, event):
        anonymized_filename = anonymize(self.iocontroller.filename())
        wx.MessageBox(
            _("Your task file has been anonymized and saved to:")
            + "\n"
            + anonymized_filename,
            _("Finished"),
            wx.OK,
        )

    def enabled(self, event):
        return bool(self.iocontroller.filename())


class HelpAbout(DialogCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&About %s") % meta.name,
            help_text=_("Version and contact information about %s")
            % meta.name,
            dialogTitle=_("About %s") % meta.name,
            dialogText=help.aboutHTML,
            id=wx.ID_ABOUT,
            icon_id="nuvola_status_dialog-information",
            *args,
            **kwargs
        )


class HelpLicense(DialogCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&License"),
            help_text=_("%s license") % meta.name,
            dialogTitle=_("%s license") % meta.name,
            dialogText=meta.licenseHTML,
            direction=wx.Layout_LeftToRight,
            icon_id="nuvola_mimetypes_application-x-dvi",
            *args,
            **kwargs
        )


class URLCommand(base_uicommand.UICommand):
    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop("url")
        super().__init__(*args, **kwargs)

    def do_command(self, event):
        try:
            openfile.openFile(self.url)
        except Exception as reason:
            wx.MessageBox(
                _("Cannot open URL:\n%s") % str(reason),
                caption=_("%s URL error") % meta.name,
                style=wx.ICON_ERROR,
            )


class FAQ(URLCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Frequently asked questions"),
            help_text=_("Browse the frequently asked questions and answers"),
            icon_id="nuvola_actions_help-about",
            url=meta.faq_url,
            *args,
            **kwargs
        )


class ReportBug(URLCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Report a &bug..."),
            help_text=_("Report a bug or browse known bugs"),
            icon_id="nuvola_apps_kbugbuster",
            url=meta.known_bugs_url,
            *args,
            **kwargs
        )


class RequestFeature(URLCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Request a &feature..."),
            help_text=_("Request a new feature or vote for existing requests"),
            icon_id="nuvola_apps_preferences-system-session-services",
            url=meta.feature_request_url,
            *args,
            **kwargs
        )


class RequestSupport(URLCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Request &support..."),
            help_text=_("Request user support from the developers"),
            icon_id="nuvola_apps_help-browser",
            url=meta.support_request_url,
            *args,
            **kwargs
        )


class HelpTranslate(URLCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Help improve &translations..."),
            help_text=_("Help improve the translations of %s") % meta.name,
            icon_id="nuvola_categories_applications-education-language",
            url=meta.translations_url,
            *args,
            **kwargs
        )


class CheckForUpdate(URLCommand):
    def __init__(self, *args, **kwargs):
        # Remove settings from kwargs if present (not needed for URLCommand)
        kwargs.pop("settings", None)
        super().__init__(
            menu_text=_("Check for update"),
            help_text=_("Check for the availability of a new version of %s")
            % meta.name,
            icon_id="nuvola_apps_kpackage",
            url=meta.github_url,
            *args,
            **kwargs
        )


class MainWindowRestore(base_uicommand.UICommand):
    """Toggle main window visibility (Hide/Restore) from the tray menu."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Restore"),
            help_text=_("Restore the window to its previous state"),
            icon_id="nuvola_apps_preferences-system-windows",
            *args,
            **kwargs
        )

    def do_command(self, event):
        window = self.main_window()
        if window.IsIconized() or not window.IsShown():
            window.restore(event)
        else:
            window.Iconize()

    def get_help_text(self):
        window = self.main_window()
        if window.IsIconized() or not window.IsShown():
            return _("Restore the window to its previous state")
        return _("Hide the main window")

    def get_menu_text(self):
        window = self.main_window()
        if window.IsIconized() or not window.IsShown():
            return _("&Restore")
        return _("&Hide")


class ResetWindowLayout(base_uicommand.UICommand):
    """Reset the window layout (AUI panes) to default positions."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("Reset &window layout"),
            help_text=_("Reset all panes to their default positions"),
            icon_id="nuvola_actions_view-split-left-right",
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.main_window().resetWindowLayout()


class Search(ViewerCommand, settings_uicommand.SettingsCommand):
    # Search can only be attached to a real viewer, not to a viewercontainer
    def __init__(self, *args, **kwargs):
        self.__bound = False
        super().__init__(*args, help_text=_("Search"), **kwargs)
        assert self.viewer.isSearchable()

    def onFind(
        self,
        searchString,
        matchCase,
        includeSubItems,
        searchDescription,
        regularExpression,
    ):
        if self.__bound:
            self.viewer.setSearchFilter(
                searchString,
                matchCase,
                includeSubItems,
                searchDescription,
                regularExpression,
            )

    def append_to_toolbar(self, toolbar):
        self.__bound = True
        (
            searchString,
            matchCase,
            includeSubItems,
            searchDescription,
            regularExpression,
        ) = self.viewer.getSearchFilter()
        # pylint: disable=W0201
        self.searchControl = widgets.SearchCtrl(
            toolbar,
            value=searchString,
            style=wx.TE_PROCESS_ENTER,
            matchCase=matchCase,
            includeSubItems=includeSubItems,
            searchDescription=searchDescription,
            regularExpression=regularExpression,
            callback=self.onFind,
        )
        # Set minimum size to ensure the text input is visible in AUI toolbars
        # that use AUI_TB_NO_AUTORESIZE flag
        self.searchControl.SetMinSize((150, -1))
        toolbar.AddControl(self.searchControl)
        self.bindKeyDownInViewer()
        self.bindKeyDownInSearchCtrl()

    def bindKeyDownInViewer(self):
        """Bind wx.EVT_KEY_DOWN to self.onViewerKeyDown so we can catch
        Ctrl-F."""
        widget = self.viewer.getWidget()
        try:
            window = widget.GetMainWindow()
        except AttributeError:
            window = widget
        window.Bind(wx.EVT_KEY_DOWN, self.onViewerKeyDown)

    def bindKeyDownInSearchCtrl(self):
        """Bind wx.EVT_KEY_DOWN to self.onSearchCtrlKeyDown so we can catch
        the Escape key and drop down the menu on Ctrl-Down."""
        self.searchControl.getTextCtrl().Bind(
            wx.EVT_KEY_DOWN, self.onSearchCtrlKeyDown
        )

    def unbind(self, window, id_):
        self.__bound = False
        if hasattr(self, "searchControl") and self.searchControl:
            self.searchControl.cleanup()
        super().unbind(window, id_)

    def onViewerKeyDown(self, event):
        """On Ctrl-F, move focus to the search control."""
        if (
            event.KeyCode == ord("F")
            and event.CmdDown()
            and not event.AltDown()
        ):
            self.searchControl.SetFocus()
        else:
            event.Skip()

    def onSearchCtrlKeyDown(self, event):
        """On Escape, move focus to the viewer, on Ctrl-Down popup the
        menu."""
        if event.KeyCode == wx.WXK_ESCAPE:
            self.viewer.SetFocus()
        elif event.KeyCode == wx.WXK_DOWN and event.AltDown():
            self.searchControl.PopupMenu()
        else:
            event.Skip()

    def do_command(self, event):
        pass  # Not used


class ToolbarChoiceCommandMixin(object):
    def __init__(self, *args, **kwargs):
        self.choiceCtrl = None
        super().__init__(*args, **kwargs)

    def append_to_toolbar(self, toolbar):
        """Add our choice control to the toolbar."""
        # pylint: disable=W0201
        self.choiceCtrl = wx.Choice(toolbar, choices=self.choiceLabels)
        self.currentChoice = self.choiceCtrl.Selection
        self.choiceCtrl.Bind(wx.EVT_CHOICE, self.onChoice)
        toolbar.AddControl(self.choiceCtrl)

    def unbind(self, window, id_):
        if self.choiceCtrl is not None:
            self.choiceCtrl.Unbind(wx.EVT_CHOICE)
            self.choiceCtrl = None
        super().unbind(window, id_)

    def onChoice(self, event):
        """The user selected a choice from the choice control."""
        choiceIndex = event.GetInt()
        if choiceIndex == self.currentChoice:
            return
        self.currentChoice = choiceIndex
        self.doChoice(self.choiceData[choiceIndex])

    def doChoice(self, choice):
        raise NotImplementedError  # pragma: no cover

    def do_command(self, event):
        pass  # Not used

    def set_choice(self, choice):
        """Programmatically set the current choice in the choice control."""
        if self.choiceCtrl is not None:
            index = self.choiceData.index(choice)
            self.choiceCtrl.Selection = index
            self.currentChoice = index

    def enable(self, enable=True):
        if self.choiceCtrl is not None:
            self.choiceCtrl.Enable(enable)


class EffortViewerAggregationChoice(
    ToolbarChoiceCommandMixin,
    settings_uicommand.SettingsCommand,
    ViewerCommand,
):
    choiceLabels = [
        _("Effort details"),
        _("Effort per day"),
        _("Effort per week"),
        _("Effort per month"),
    ]
    choiceData = ["details", "day", "week", "month"]

    def __init__(self, **kwargs):
        super().__init__(help_text=_("Aggregation mode"), **kwargs)

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self.set_choice(self.viewer.aggregation)
        self.viewer.registerObserver(
            self._on_view_settings_changed,
            eventType=self.viewer.view_settings_changed_event_type(),
            eventSource=self.viewer,
        )

    def doChoice(self, choice):
        self.viewer.set_aggregation(choice)

    def _on_view_settings_changed(self, event):
        self.set_choice(self.viewer.aggregation)


class EffortViewerAggregationOption(
    settings_uicommand.UIRadioCommand, ViewerCommand
):

    def is_setting_checked(self):
        return self.viewer.aggregation == self.value

    def do_command(self, event):
        self.viewer.set_aggregation(self.value)


class TaskViewerTreeOrListChoice(
    ToolbarChoiceCommandMixin, settings_uicommand.UICheckCommand, ViewerCommand
):
    choiceLabels = [_("Tree"), _("List")]
    choiceData = [True, False]

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=self.choiceLabels[0],
            help_text=_(
                "When checked, show tasks as tree, "
                "otherwise show tasks as list"
            ),
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self.set_choice(
            self.settings.getboolean(self.viewer.settingsSection(), "treemode")
        )
        self.viewer.registerObserver(
            self._on_view_settings_changed,
            eventType=self.viewer.view_settings_changed_event_type(),
            eventSource=self.viewer,
        )

    def doChoice(self, choice):
        self.viewer.set_tree_mode(choice)

    def _on_view_settings_changed(self, event):
        self.set_choice(
            self.settings.getboolean(self.viewer.settingsSection(), "treemode")
        )


class TaskViewerTreeOrListOption(
    settings_uicommand.UIRadioCommand, ViewerCommand
):

    def is_setting_checked(self):
        return (
            self.settings.getboolean(self.viewer.settingsSection(), "treemode")
            == self.value
        )

    def do_command(self, event):
        self.viewer.set_tree_mode(self.value)


class CategoryViewerFilterChoice(
    ToolbarChoiceCommandMixin, settings_uicommand.UICheckCommand
):
    choiceLabels = [
        _("Filter on all checked categories"),
        _("Filter on any checked category"),
    ]
    choiceData = [True, False]

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=self.choiceLabels[0],
            help_text=_(
                "When checked, filter on all checked categories, "
                "otherwise on any checked category"
            ),
            *args,
            **kwargs
        )

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        patterns.Publisher().registerObserver(
            self.on_setting_changed,
            eventType="view.categoryfiltermatchall",
            eventSource=self.settings,
        )

    def is_setting_checked(self):
        return self.settings.getboolean("view", "categoryfiltermatchall")

    def doChoice(self, choice):
        self.settings.setboolean("view", "categoryfiltermatchall", choice)

    def do_command(self, event):
        self.settings.setboolean(
            "view", "categoryfiltermatchall", self._isMenuItemChecked(event)
        )

    def on_setting_changed(self, event):  # pylint: disable=W0613
        self.set_choice(
            self.settings.getboolean("view", "categoryfiltermatchall")
        )


class SquareTaskViewerOrderChoice(
    ToolbarChoiceCommandMixin,
    settings_uicommand.SettingsCommand,
    ViewerCommand,
):
    choiceLabels = [
        _("Budget"),
        _("Time spent"),
        _("Fixed fee"),
        _("Revenue"),
        _("Priority"),
    ]
    choiceData = ["budget", "timeSpent", "fixedFee", "revenue", "priority"]

    def __init__(self, **kwargs):
        super().__init__(help_text=_("Order choice"), **kwargs)

    def append_to_toolbar(self, *args, **kwargs):
        super().append_to_toolbar(*args, **kwargs)
        self.set_choice(self.viewer.order_by)
        self.viewer.registerObserver(
            self._on_view_settings_changed,
            eventType=self.viewer.view_settings_changed_event_type(),
            eventSource=self.viewer,
        )

    def doChoice(self, choice):
        self.viewer.set_order_by(choice)

    def _on_view_settings_changed(self, event):
        self.set_choice(self.viewer.order_by)


class SquareTaskViewerOrderByOption(
    settings_uicommand.UIRadioCommand, ViewerCommand
):

    def is_setting_checked(self):
        return self.viewer.order_by == self.value

    def do_command(self, event):
        self.viewer.set_order_by(self.value)


class CalendarViewerConfigure(ViewerCommand):
    menu_text = _("&Configure")
    help_text = _("Configure the calendar viewer")
    icon_id = "nuvola_actions_configure"

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=self.menu_text,
            help_text=self.help_text,
            icon_id=self.icon_id,
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.viewer.configure()


class HierarchicalCalendarViewerConfigure(CalendarViewerConfigure):
    help_text = _("Configure the hierarchical calendar viewer")


class CalendarViewerNavigationCommand(ViewerCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=self.menu_text,
            help_text=self.help_text,
            icon_id=self.icon_id,
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.viewer.freeze()
        try:
            self.viewer.SetViewType(
                self.calendarViewType
            )  # pylint: disable=E1101
        finally:
            self.viewer.thaw()


class CalendarViewerNextPeriod(CalendarViewerNavigationCommand):
    menu_text = _("&Next period")
    help_text = _("Show next period")
    icon_id = "nuvola_actions_go-next-document"
    calendarViewType = wxSCHEDULER_NEXT


class HierarchicalCalendarViewerNextPeriod(ViewerCommand):
    menu_text = _("&Next period")
    help_text = _("Show next period")
    icon_id = "nuvola_actions_go-next-document"

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=self.menu_text,
            help_text=self.help_text,
            icon_id=self.icon_id,
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.viewer.widget.Next()


class CalendarViewerPreviousPeriod(CalendarViewerNavigationCommand):
    menu_text = _("&Previous period")
    help_text = _("Show previous period")
    icon_id = "nuvola_actions_go-previous-document"
    calendarViewType = wxSCHEDULER_PREV


class HierarchicalCalendarViewerPreviousPeriod(ViewerCommand):
    menu_text = _("&Previous period")
    help_text = _("Show previous period")
    icon_id = "nuvola_actions_go-previous-document"

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=self.menu_text,
            help_text=self.help_text,
            icon_id=self.icon_id,
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.viewer.widget.Prev()


class CalendarViewerToday(CalendarViewerNavigationCommand):
    menu_text = _("&Today")
    help_text = _("Show today")
    icon_id = "nuvola_apps_date"
    calendarViewType = wxSCHEDULER_TODAY


class HierarchicalCalendarViewerToday(ViewerCommand):
    menu_text = _("&Today")
    help_text = _("Show today")
    icon_id = "nuvola_apps_date"

    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=self.menu_text,
            help_text=self.help_text,
            icon_id=self.icon_id,
            *args,
            **kwargs
        )

    def do_command(self, event):
        self.viewer.widget.Today()


class ToggleAutoColumnResizing(
    settings_uicommand.UICheckCommand, ViewerCommand
):
    def __init__(self, *args, **kwargs):
        super().__init__(
            menu_text=_("&Automatic column resizing"),
            help_text=_(
                "When checked, automatically resize columns to fill"
                " available space"
            ),
            *args,
            **kwargs
        )
        wx.CallAfter(self.updateWidget)

    def updateWidget(self):
        # Guard against deleted C++ object - can happen when wx.CallAfter
        # callback executes after window destruction
        try:
            widget = self.viewer.getWidget()
            if widget:
                widget.ToggleAutoResizing(self.is_setting_checked())
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            pass

    def is_setting_checked(self):
        return self.settings.getboolean(
            self.viewer.settingsSection(), "columnautoresizing"
        )

    def do_command(self, event):
        self.settings.set(
            self.viewer.settingsSection(),
            "columnautoresizing",
            str(self._isMenuItemChecked(event)),
        )
        self.updateWidget()


class ViewerPieChartAngle(ViewerCommand, settings_uicommand.SettingsCommand):
    def __init__(self, *args, **kwargs):
        self.sliderCtrl = None
        super().__init__(help_text=_("Set pie chart angle"), *args, **kwargs)

    def append_to_toolbar(self, toolbar):
        """Add our slider control to the toolbar."""
        # pylint: disable=W0201
        self.sliderCtrl = wx.Slider(
            toolbar,
            minValue=0,
            maxValue=90,
            value=self.getCurrentAngle(),
            size=(120, -1),
        )
        self.sliderCtrl.Bind(wx.EVT_SLIDER, self.onSlider)
        toolbar.AddControl(self.sliderCtrl)

    def unbind(self, window, item_id):
        if self.sliderCtrl is not None:
            self.sliderCtrl.Unbind(wx.EVT_SLIDER)
            self.sliderCtrl = None
        super().unbind(window, item_id)

    def onSlider(self, event):
        """The user picked a new angle."""
        event.Skip()
        self.setCurrentAngle()

    def do_command(self, event):
        pass  # Not used

    def getCurrentAngle(self):
        return self.settings.getint(
            self.viewer.settingsSection(), "piechartangle"
        )

    def setCurrentAngle(self):
        if self.sliderCtrl is not None:
            self.settings.setint(
                self.viewer.settingsSection(),
                "piechartangle",
                self.sliderCtrl.GetValue(),
            )


class RoundingPrecision(
    ToolbarChoiceCommandMixin,
    ViewerCommand,
    settings_uicommand.SettingsCommand,
):
    roundingChoices = (0, 1, 3, 5, 6, 10, 15, 20, 30, 60)  # Minutes
    choiceData = [minutes * 60 for minutes in roundingChoices]  # Seconds
    choiceLabels = [_("No rounding"), _("1 minute")] + [
        _("%d minutes") % minutes for minutes in roundingChoices[2:]
    ]

    def __init__(self, **kwargs):
        super().__init__(help_text=_("Rounding precision"), **kwargs)

    def doChoice(self, choice):
        self.settings.setint(self.viewer.settingsSection(), "round", choice)


class RoundBy(settings_uicommand.UIRadioCommand, ViewerCommand):

    def is_setting_checked(self):
        return (
            self.settings.getint(self.viewer.settingsSection(), "round")
            == self.value
        )

    def do_command(self, event):
        self.settings.setint(
            self.viewer.settingsSection(), "round", self.value
        )


class AlwaysRoundUp(settings_uicommand.UICheckCommand, ViewerCommand):
    def __init__(self, *args, **kwargs):
        self.checkboxCtrl = None
        super().__init__(
            menu_text=_("&Always round up"),
            help_text=_("Always round up to the next rounding increment"),
            *args,
            **kwargs
        )

    def append_to_toolbar(self, toolbar):
        """Add a checkbox control to the toolbar."""
        # pylint: disable=W0201
        self.checkboxCtrl = wx.CheckBox(toolbar, label=self.menu_text)
        self.checkboxCtrl.Bind(wx.EVT_CHECKBOX, self.onCheck)
        toolbar.AddControl(self.checkboxCtrl)

    def unbind(self, window, item_id):
        if self.checkboxCtrl is not None:
            self.checkboxCtrl.Unbind(wx.EVT_CHECKBOX)
            self.checkboxCtrl = None
        super().unbind(window, item_id)

    def is_setting_checked(self):
        return self.settings.getboolean(
            self.viewer.settingsSection(), "alwaysroundup"
        )

    def onCheck(self, event):
        self.setSetting(event.IsChecked())

    def do_command(self, event):
        self.setSetting(self._isMenuItemChecked(event))

    def setSetting(self, alwaysRoundUp):
        self.settings.setboolean(
            self.viewer.settingsSection(), "alwaysroundup", alwaysRoundUp
        )

    def setValue(self, value):
        if self.checkboxCtrl is not None:
            self.checkboxCtrl.SetValue(value)

    def enable(self, enable=True):
        if self.checkboxCtrl is not None:
            self.checkboxCtrl.Enable(enable)


class ConsolidateEffortsPerTask(
    settings_uicommand.UICheckCommand, ViewerCommand
):
    def __init__(self, *args, **kwargs):
        self.checkboxCtrl = None
        super().__init__(
            menu_text=_("&Consolidate efforts per task"),
            help_text=_(
                "Consolidate all efforts per task to a single effort before rounding"
            ),
            *args,
            **kwargs
        )

    def append_to_toolbar(self, toolbar):
        """Add a checkbox control to the toolbar."""
        # pylint: disable=W0201
        self.checkboxCtrl = wx.CheckBox(toolbar, label=self.menu_text)
        self.checkboxCtrl.Bind(wx.EVT_CHECKBOX, self.onCheck)
        toolbar.AddControl(self.checkboxCtrl)

    def unbind(self, window, item_id):
        if self.checkboxCtrl is not None:
            self.checkboxCtrl.Unbind(wx.EVT_CHECKBOX)
            self.checkboxCtrl = None
        super().unbind(window, item_id)

    def is_setting_checked(self):
        return self.settings.getboolean(
            self.viewer.settingsSection(), "consolidateeffortspertask"
        )

    def onCheck(self, event):
        self.setSetting(self._isMenuItemChecked(event))

    def do_command(self, event):
        self.setSetting(self._isMenuItemChecked(event))

    def setSetting(self, consolidateEffortsPerTask):
        self.settings.setboolean(
            self.viewer.settingsSection(),
            "consolidateeffortspertask",
            consolidateEffortsPerTask,
        )

    def setValue(self, value):
        if self.checkboxCtrl is not None:
            self.checkboxCtrl.SetValue(value)

    def enable(self, enable=True):
        if self.checkboxCtrl is not None:
            self.checkboxCtrl.Enable(enable)
