# -*- coding: utf-8 -*-

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

from taskcoachlib import meta, persistence, patterns, operating_system
from taskcoachlib.i18n import _
from taskcoachlib.widgets import GetPassword
from taskcoachlib.workarounds import ExceptionAsUnicode
from taskcoachlib.gui.dialog import BackupManagerDialog
import wx
import os
import gc
import sys
import codecs
import traceback

try:
    from taskcoachlib.syncml import sync
except ImportError:  # pragma: no cover
    # Unsupported platform.
    pass


class IOController(object):
    """IOController is responsible for opening, closing, loading,
    saving, and exporting files. It also presents the necessary dialogs
    to let the user specify what file to load/save/etc."""

    def __init__(self, taskFile, messageCallback, settings):
        super().__init__()
        self.__taskFile = taskFile
        self.__messageCallback = messageCallback
        self.__settings = settings
        defaultPath = os.path.expanduser("~")
        self.__tskFileSaveDialogOpts = {
            "default_path": defaultPath,
            "default_extension": "tsk",
            "wildcard": _("%s files (*.tsk)|*.tsk|All files (*.*)|*")
            % meta.name,
        }
        self.__tskFileOpenDialogOpts = {
            "default_path": defaultPath,
            "default_extension": "tsk",
            "wildcard": _(
                "%s files (*.tsk)|*.tsk|Backup files (*.tsk.bak)|*.tsk.bak|"
                "All files (*.*)|*"
            )
            % meta.name,
        }
        self.__icsFileDialogOpts = {
            "default_path": defaultPath,
            "default_extension": "ics",
            "wildcard": _("iCalendar files (*.ics)|*.ics|All files (*.*)|*"),
        }
        self.__htmlFileDialogOpts = {
            "default_path": defaultPath,
            "default_extension": "html",
            "wildcard": _("HTML files (*.html)|*.html|All files (*.*)|*"),
        }
        self.__csvFileDialogOpts = {
            "default_path": defaultPath,
            "default_extension": "csv",
            "wildcard": _(
                "CSV files (*.csv)|*.csv|Text files (*.txt)|*.txt|"
                "All files (*.*)|*"
            ),
        }
        self.__todotxtFileDialogOpts = {
            "default_path": defaultPath,
            "default_extension": "txt",
            "wildcard": _("Todo.txt files (*.txt)|*.txt|All files (*.*)|*"),
        }
        self.__errorMessageOptions = dict(
            caption=_("%s file error") % meta.name, style=wx.ICON_ERROR
        )

    def syncMLConfig(self):
        return self.__taskFile.syncMLConfig()

    def setSyncMLConfig(self, config):
        self.__taskFile.setSyncMLConfig(config)

    def needSave(self):
        return self.__taskFile.needSave()

    def changedOnDisk(self):
        return self.__taskFile.changedOnDisk()

    def hasDeletedItems(self):
        return bool(
            [task for task in self.__taskFile.tasks() if task.isDeleted()]
            + [note for note in self.__taskFile.notes() if note.isDeleted()]
        )

    def purgeDeletedItems(self):
        self.__taskFile.tasks().removeItems(
            [task for task in self.__taskFile.tasks() if task.isDeleted()]
        )
        self.__taskFile.notes().removeItems(
            [note for note in self.__taskFile.notes() if note.isDeleted()]
        )

    def openAfterStart(self, commandLineArgs, earlyLockResult=None):
        """Open either the file specified on the command line, or the file
        the user was working on previously, or none at all.

        Args:
            commandLineArgs: Command line arguments
            earlyLockResult: Result from early lock check before main window:
                None = no file to open
                'ok' = file not locked, proceed normally
                'break' = file locked, user chose to break lock
                'skip' = file locked, user chose not to break (start fresh)
        """
        if commandLineArgs:
            filename = commandLineArgs[0].decode(sys.getfilesystemencoding())
        else:
            filename = self.__settings.get("file", "lastfile")
        if filename:
            # If early lock check was done, use its result
            if earlyLockResult == 'break':
                # User already confirmed breaking the lock
                wx.CallAfter(self.open, filename, breakLock=True)
            elif earlyLockResult == 'skip':
                # User chose not to break lock - start with no file (fresh)
                pass
            else:
                # Normal case - open file (will check lock again if needed)
                wx.CallAfter(self.open, filename)

    def open(
        self,
        filename=None,
        showerror=wx.MessageBox,
        fileExists=os.path.exists,
        breakLock=False,
        lock=True,
    ):
        if self.__taskFile.needSave():
            if not self.__saveUnsavedChanges():
                return
        if not filename:
            filename = self.__askUserForFile(
                _("Open"), self.__tskFileOpenDialogOpts
            )
        if not filename:
            return
        self.__updateDefaultPath(filename)
        if fileExists(filename):
            self.__closeUnconditionally()
            self.__addRecentFile(filename)
            try:
                try:
                    self.__taskFile.load(
                        filename, lock=lock, breakLock=breakLock
                    )
                except Exception:
                    raise
            except persistence.LockTimeout:
                if breakLock:
                    if self.__askOpenUnlocked(filename):
                        self.open(filename, showerror, lock=False)
                elif self.__askBreakLock(filename):
                    self.open(filename, showerror, breakLock=True)
                else:
                    return
            except persistence.LockFailed:
                if self.__askOpenUnlocked(filename):
                    self.open(filename, showerror, lock=False)
                else:
                    return
            except persistence.xml.reader.XMLReaderTooNewException:
                self.__showTooNewErrorMessage(filename, showerror)
                return
            except Exception:
                self.__showGenericErrorMessage(
                    filename, showerror, showBackups=True
                )
                return
            self.__messageCallback(
                _("Loaded %(nrtasks)d tasks from " "%(filename)s")
                % dict(
                    nrtasks=len(self.__taskFile.tasks()),
                    filename=self.__taskFile.filename(),
                )
            )
        else:
            errorMessage = (
                _("Cannot open %s because it doesn't exist") % filename
            )
            # Use CallAfter on Mac OS X because otherwise the app will hang:
            if operating_system.isMac():
                wx.CallAfter(
                    showerror, errorMessage, **self.__errorMessageOptions
                )
            else:
                showerror(errorMessage, **self.__errorMessageOptions)
            self.__removeRecentFile(filename)

    def merge(self, filename=None, showerror=wx.MessageBox):
        if not filename:
            filename = self.__askUserForFile(
                _("Merge"), self.__tskFileOpenDialogOpts
            )
        if filename:
            try:
                self.__taskFile.merge(filename)
            except persistence.LockTimeout:
                showerror(
                    _("Cannot open %(filename)s\nbecause it is locked.")
                    % dict(filename=filename),
                    **self.__errorMessageOptions
                )
                return
            except persistence.xml.reader.XMLReaderTooNewException:
                self.__showTooNewErrorMessage(filename, showerror)
                return
            except Exception:
                self.__showGenericErrorMessage(filename, showerror)
                return
            self.__messageCallback(
                _("Merged %(filename)s") % dict(filename=filename)
            )
            self.__addRecentFile(filename)

    def save(self, showerror=wx.MessageBox):
        if self.__taskFile.filename():
            if self._saveSave(self.__taskFile, showerror):
                return True
            else:
                return self.saveas(showerror=showerror)
        elif not self.__taskFile.isEmpty():
            return self.saveas(showerror=showerror)  # Ask for filename
        else:
            return False

    def mergeDiskChanges(self):
        self.__taskFile.mergeDiskChanges()

    def saveas(
        self, filename=None, showerror=wx.MessageBox, fileExists=os.path.exists
    ):
        if not filename:
            filename = self.__askUserForFile(
                _("Save as"),
                self.__tskFileSaveDialogOpts,
                flag=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
                fileExists=fileExists,
            )
            if not filename:
                return False  # User didn't enter a filename, cancel save
        if self._saveSave(self.__taskFile, showerror, filename):
            return True
        else:
            return self.saveas(showerror=showerror)  # Try again

    def saveselection(
        self,
        tasks,
        filename=None,
        showerror=wx.MessageBox,
        TaskFileClass=persistence.TaskFile,
        fileExists=os.path.exists,
    ):
        if not filename:
            filename = self.__askUserForFile(
                _("Save selection"),
                self.__tskFileSaveDialogOpts,
                flag=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
                fileExists=fileExists,
            )
            if not filename:
                return False  # User didn't enter a filename, cancel save
        selectionFile = self._createSelectionFile(tasks, TaskFileClass)
        if self._saveSave(selectionFile, showerror, filename):
            return True
        else:
            return self.saveselection(
                tasks, showerror=showerror, TaskFileClass=TaskFileClass
            )  # Try again

    def _createSelectionFile(self, tasks, TaskFileClass):
        selectionFile = TaskFileClass()
        # Add the selected tasks:
        selectionFile.tasks().extend(tasks)
        # Include categories used by the selected tasks:
        allCategories = set()
        for task in tasks:
            allCategories.update(task.categories())
        # Also include parents of used categories, recursively:
        for category in allCategories.copy():
            allCategories.update(category.ancestors())
        selectionFile.categories().extend(allCategories)
        return selectionFile

    def _saveSave(self, taskFile, showerror, filename=None):
        """Save the file and show an error message if saving fails."""
        try:
            if filename:
                taskFile.saveas(filename)
            else:
                filename = taskFile.filename()
                taskFile.save()
            self.__showSaveMessage(taskFile)
            self.__addRecentFile(filename)
            return True
        except persistence.LockTimeout:
            errorMessage = _(
                "Cannot save %s\nIt is locked by another instance " "of %s.\n"
            ) % (filename, meta.name)
            showerror(errorMessage, **self.__errorMessageOptions)
            return False
        except (OSError, IOError, persistence.LockFailed) as reason:
            errorMessage = _("Cannot save %s\n%s") % (
                filename,
                ExceptionAsUnicode(reason),
            )
            showerror(errorMessage, **self.__errorMessageOptions)
            return False

    def saveastemplate(self, task):
        templates = persistence.TemplateList(
            self.__settings.pathToTemplatesDir()
        )
        templates.addTemplate(task)
        templates.save()

    def importTemplate(self, showerror=wx.MessageBox):
        filename = self.__askUserForFile(
            _("Import template"),
            fileDialogOpts={
                "default_extension": "tsktmpl",
                "wildcard": _("%s template files (*.tsktmpl)|" "*.tsktmpl")
                % meta.name,
            },
        )
        if filename:
            templates = persistence.TemplateList(
                self.__settings.pathToTemplatesDir()
            )
            try:
                templates.copyTemplate(filename)
            except Exception as reason:  # pylint: disable=W0703
                errorMessage = _("Cannot import template %s\n%s") % (
                    filename,
                    ExceptionAsUnicode(reason),
                )
                showerror(errorMessage, **self.__errorMessageOptions)

    def close(self, force=False):
        if self.__taskFile.needSave():
            if force:
                # No user interaction, since we're forced to close right now.
                if self.__taskFile.filename():
                    self._saveSave(
                        self.__taskFile, lambda *args, **kwargs: None
                    )
                else:
                    pass  # No filename, we cannot ask, give up...
            else:
                if not self.__saveUnsavedChanges():
                    return False
        self.__closeUnconditionally()
        return True

    def export(
        self,
        title,
        fileDialogOpts,
        writerClass,
        viewer,
        selectionOnly,
        openfile=codecs.open,
        showerror=wx.MessageBox,
        filename=None,
        fileExists=os.path.exists,
        **kwargs
    ):
        filename = filename or self.__askUserForFile(
            title,
            fileDialogOpts,
            flag=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            fileExists=fileExists,
        )
        if filename:
            fd = self.__openFileForWriting(filename, openfile, showerror)
            if fd is None:
                return False
            count = writerClass(fd, filename).write(
                viewer, self.__settings, selectionOnly, **kwargs
            )
            fd.close()
            self.__messageCallback(
                _("Exported %(count)d items to " "%(filename)s")
                % dict(count=count, filename=filename)
            )
            return True
        else:
            return False

    def exportAsHTML(
        self,
        viewer,
        selectionOnly=False,
        separateCSS=False,
        columns=None,
        openfile=codecs.open,
        showerror=wx.MessageBox,
        filename=None,
        fileExists=os.path.exists,
    ):
        return self.export(
            _("Export as HTML"),
            self.__htmlFileDialogOpts,
            persistence.HTMLWriter,
            viewer,
            selectionOnly,
            openfile,
            showerror,
            filename,
            fileExists,
            separateCSS=separateCSS,
            columns=columns,
        )

    def exportAsCSV(
        self,
        viewer,
        selectionOnly=False,
        separateDateAndTimeColumns=False,
        columns=None,
        fileExists=os.path.exists,
    ):
        return self.export(
            _("Export as CSV"),
            self.__csvFileDialogOpts,
            persistence.CSVWriter,
            viewer,
            selectionOnly,
            separateDateAndTimeColumns=separateDateAndTimeColumns,
            columns=columns,
            fileExists=fileExists,
        )

    def exportAsICalendar(
        self, viewer, selectionOnly=False, fileExists=os.path.exists
    ):
        return self.export(
            _("Export as iCalendar"),
            self.__icsFileDialogOpts,
            persistence.iCalendarWriter,
            viewer,
            selectionOnly,
            fileExists=fileExists,
        )

    def exportAsTodoTxt(
        self, viewer, selectionOnly=False, fileExists=os.path.exists
    ):
        return self.export(
            _("Export as Todo.txt"),
            self.__todotxtFileDialogOpts,
            persistence.TodoTxtWriter,
            viewer,
            selectionOnly,
            fileExists=fileExists,
        )

    def importCSV(self, **kwargs):
        persistence.CSVReader(
            self.__taskFile.tasks(), self.__taskFile.categories()
        ).read(**kwargs)

    def importTodoTxt(self, filename):
        persistence.TodoTxtReader(
            self.__taskFile.tasks(), self.__taskFile.categories()
        ).read(filename)

    def synchronize(self):
        doReset = False
        while True:
            password = GetPassword("Task Coach", "SyncML", reset=doReset)
            if not password:
                break

            synchronizer = sync.Synchronizer(
                self.__syncReport, self.__taskFile, password
            )
            try:
                synchronizer.synchronize()
            except sync.AuthenticationFailure:
                doReset = True
            else:
                self.__messageCallback(_("Finished synchronization"))
                break
            finally:
                synchronizer.Destroy()

    def filename(self):
        return self.__taskFile.filename()

    def __syncReport(self, msg):
        wx.MessageBox(
            msg, _("Synchronization status"), style=wx.OK | wx.ICON_ERROR
        )

    def __openFileForWriting(
        self, filename, openfile, showerror, mode="w", encoding="utf-8"
    ):
        try:
            return openfile(filename, mode, encoding)
        except IOError as reason:
            errorMessage = _("Cannot open %s\n%s") % (
                filename,
                ExceptionAsUnicode(reason),
            )
            showerror(errorMessage, **self.__errorMessageOptions)
            return None

    def __addRecentFile(self, fileName):
        recentFiles = self.__settings.getlist("file", "recentfiles")
        if fileName in recentFiles:
            recentFiles.remove(fileName)
        recentFiles.insert(0, fileName)
        maximumNumberOfRecentFiles = self.__settings.getint(
            "file", "maxrecentfiles"
        )
        recentFiles = recentFiles[:maximumNumberOfRecentFiles]
        self.__settings.setlist("file", "recentfiles", recentFiles)

    def __removeRecentFile(self, fileName):
        recentFiles = self.__settings.getlist("file", "recentfiles")
        if fileName in recentFiles:
            recentFiles.remove(fileName)
            self.__settings.setlist("file", "recentfiles", recentFiles)

    def __askUserForFile(
        self, title, fileDialogOpts, flag=wx.FD_OPEN, fileExists=os.path.exists
    ):
        filename = wx.FileSelector(
            title, flags=flag, **fileDialogOpts
        )  # pylint: disable=W0142
        if filename and (flag & wx.FD_SAVE):
            # On Ubuntu, the default extension is not added automatically to
            # a filename typed by the user. Add the extension if necessary.
            extension = os.path.extsep + fileDialogOpts["default_extension"]
            if not filename.endswith(extension):
                filename += extension
                if fileExists(filename):
                    return self.__askUserForOverwriteConfirmation(
                        filename, title, fileDialogOpts
                    )
        return filename

    def __askUserForOverwriteConfirmation(
        self, filename, title, fileDialogOpts
    ):
        result = wx.MessageBox(
            _("A file named %s already exists.\n" "Do you want to replace it?")
            % filename,
            title,
            style=wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION | wx.NO_DEFAULT,
        )
        if result == wx.YES:
            extensions = {"Todo.txt": ".txt"}
            for auto in set(
                self.__settings.getlist("file", "autoimport")
                + self.__settings.getlist("file", "autoexport")
            ):
                autoName = os.path.splitext(filename)[0] + extensions[auto]
                if os.path.exists(autoName):
                    os.remove(autoName)
                if os.path.exists(autoName + "-meta"):
                    os.remove(autoName + "-meta")
            return filename
        elif result == wx.NO:
            return self.__askUserForFile(
                title, fileDialogOpts, flag=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
            )
        else:
            return None

    def __saveUnsavedChanges(self):
        result = wx.MessageBox(
            _("You have unsaved changes.\n" "Save before closing?"),
            _("%s: save changes?") % meta.name,
            style=wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION | wx.YES_DEFAULT,
        )
        if result == wx.YES:
            if not self.save():
                return False
        elif result == wx.CANCEL:
            return False
        return True

    def __askBreakLock(self, filename):
        result = wx.MessageBox(
            _(
                """Cannot open %s because it is locked.

This means either that another instance of TaskCoach
is running and has this file opened, or that a previous
instance of Task Coach crashed. If no other instance is
running, you can safely break the lock.

Break the lock?"""
            )
            % filename,
            _("%s: file locked") % meta.name,
            style=wx.YES_NO | wx.ICON_QUESTION | wx.NO_DEFAULT,
        )
        return result == wx.YES

    def __askOpenUnlocked(self, filename):
        result = wx.MessageBox(
            _(
                "Cannot acquire a lock because locking is not "
                "supported\non the location of %s.\n"
                "Open %s unlocked?"
            )
            % (filename, filename),
            _("%s: file locked") % meta.name,
            style=wx.YES_NO | wx.ICON_QUESTION | wx.NO_DEFAULT,
        )
        return result == wx.YES

    def __closeUnconditionally(self):
        self.__messageCallback(_("Closed %s") % self.__taskFile.filename())
        self.__taskFile.close()
        patterns.CommandHistory().clear()
        gc.collect()

    def __showSaveMessage(self, savedFile):
        self.__messageCallback(
            _("Saved %(nrtasks)d tasks to %(filename)s")
            % {
                "nrtasks": len(savedFile.tasks()),
                "filename": savedFile.filename(),
            }
        )

    def __showTooNewErrorMessage(self, filename, showerror):
        showerror(
            _(
                "Cannot open %(filename)s\n"
                "because it was created by a newer version of %(name)s.\n"
                "Please upgrade %(name)s."
            )
            % dict(filename=filename, name=meta.name),
            **self.__errorMessageOptions
        )

    def __showGenericErrorMessage(
        self, filename, showerror, showBackups=False
    ):
        sys.stderr.write("".join(traceback.format_exception(*sys.exc_info())))
        limitedException = "".join(
            traceback.format_exception(*sys.exc_info(), limit=10)
        )
        message = _("Error while reading %s:\n") % filename + limitedException
        man = persistence.BackupManifest(self.__settings)
        if showBackups and man.hasBackups(filename):
            message += "\n" + _(
                "The backup manager will now open to allow you to restore\nan older version of this file."
            )
        showerror(message, **self.__errorMessageOptions)

        if showBackups and man.hasBackups(filename):
            dlg = BackupManagerDialog(None, self.__settings, filename)
            try:
                if dlg.ShowModal() == wx.ID_OK:
                    wx.CallAfter(self.open, dlg.restoredFilename())
            finally:
                dlg.Destroy()

    def __updateDefaultPath(self, filename):
        for options in [
            self.__tskFileOpenDialogOpts,
            self.__tskFileSaveDialogOpts,
            self.__csvFileDialogOpts,
            self.__icsFileDialogOpts,
            self.__htmlFileDialogOpts,
        ]:
            options["default_path"] = os.path.dirname(filename)
