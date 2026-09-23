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
from taskcoachlib.filesystem import resourcelock

from taskcoachlib.gui.dialog import BackupManagerDialog
import wx
import os
import re
import gc
import sys
import codecs
import traceback


def copy_name(path, file_exists=os.path.exists):
    """Return the file name (without folder) to suggest for a copy of
    path: the first free name of "Tasks copy.tsk", "Tasks copy 2.tsk",
    and so on. One style on every platform, with only letters, digits
    and spaces added. A name that already is such a copy is numbered on
    rather than getting a second suffix."""
    first, numbered = _("%s copy"), _("%s copy %d")
    folder, basename = os.path.split(path)
    stem, extension = os.path.splitext(basename)
    for template in (first, numbered):
        pattern = (
            re.escape(template)
            .replace(re.escape("%s"), "(.+)")
            .replace(re.escape("%d"), r"\d+")
        )
        match = re.fullmatch(pattern, stem)
        if match:
            stem = match.group(1)
            break
    number = 1
    while True:
        name = first % stem if number == 1 else numbered % (stem, number)
        name += extension
        if name != basename and not file_exists(os.path.join(folder, name)):
            return name
        number += 1


class IOController(object):
    """IOController is responsible for opening, closing, loading,
    saving, and exporting files. It also presents the necessary dialogs
    to let the user specify what file to load/save/etc."""

    def __init__(self, task_file, message_callback, settings):
        super().__init__()
        self.__task_file = task_file
        self.__message_callback = message_callback
        self.__settings = settings
        default_path = os.path.expanduser("~")
        self.__tsk_file_save_dialog_opts = {
            "default_path": default_path,
            "default_extension": "tsk",
            "wildcard": _("%s files (*.tsk)|*.tsk|All files (*.*)|*")
            % meta.name,
        }
        self.__tsk_file_open_dialog_opts = {
            "default_path": default_path,
            "default_extension": "tsk",
            "wildcard": _(
                "%s files (*.tsk)|*.tsk|Backup files (*.tsk.bak)|*.tsk.bak|"
                "All files (*.*)|*"
            )
            % meta.name,
        }
        self.__ics_file_dialog_opts = {
            "default_path": default_path,
            "default_extension": "ics",
            "wildcard": _("iCalendar files (*.ics)|*.ics|All files (*.*)|*"),
        }
        self.__html_file_dialog_opts = {
            "default_path": default_path,
            "default_extension": "html",
            "wildcard": _("HTML files (*.html)|*.html|All files (*.*)|*"),
        }
        self.__csv_file_dialog_opts = {
            "default_path": default_path,
            "default_extension": "csv",
            "wildcard": _(
                "CSV files (*.csv)|*.csv|Text files (*.txt)|*.txt|"
                "All files (*.*)|*"
            ),
        }
        self.__todotxt_file_dialog_opts = {
            "default_path": default_path,
            "default_extension": "txt",
            "wildcard": _("Todo.txt files (*.txt)|*.txt|All files (*.*)|*"),
        }
        self.__error_message_options = dict(
            caption=_("%s file error") % meta.name, style=wx.ICON_ERROR
        )

    def need_save(self):
        return self.__task_file.need_save()

    def changed_on_disk(self):
        return self.__task_file.changed_on_disk()

    def has_deleted_items(self):
        return bool(
            [task for task in self.__task_file.tasks() if task.isDeleted()]
            + [note for note in self.__task_file.notes() if note.isDeleted()]
        )

    def purge_deleted_items(self):
        self.__task_file.tasks().removeItems(
            [task for task in self.__task_file.tasks() if task.isDeleted()]
        )
        self.__task_file.notes().removeItems(
            [note for note in self.__task_file.notes() if note.isDeleted()]
        )

    def open_after_start(self, command_line_args, early_lock_result=None):
        """Open either the file specified on the command line, or the file
        the user was working on previously, or none at all.

        Args:
            command_line_args: Command line arguments
            early_lock_result: Result from the early lock check before the
                main window: None = no file to open, 'ok' = locked for
                this instance, 'skip' = open in another Task Coach (the
                user was told), so start without a file
        """
        if command_line_args:
            filename = command_line_args[0]
        else:
            filename = self.__settings.get("file", "lastfile")
        if filename and early_lock_result != "skip":
            wx.CallAfter(self.open, filename)

    def open(
        self,
        filename=None,
        showerror=wx.MessageBox,
        file_exists=os.path.exists,
    ):
        if self.__task_file.need_save():
            if not self.__save_unsaved_changes():
                return
        if not filename:
            filename = self.__ask_user_for_file(
                _("Open"), self.__tsk_file_open_dialog_opts
            )
        if not filename:
            return
        self.__update_default_path(filename)
        if file_exists(filename):
            self.__close_unconditionally()
            self.__add_recent_file(filename)
            try:
                self.__task_file.load(filename)
            except resourcelock.LockInUse as in_use:
                showerror(
                    resourcelock.in_use_message(filename, in_use.owner),
                    **self.__error_message_options
                )
                return
            except persistence.xml.reader.XMLReaderTooNewException:
                self.__show_too_new_error_message(filename, showerror)
                return
            except Exception:
                self.__show_generic_error_message(
                    filename, showerror, show_backups=True
                )
                return
            self.__message_callback(
                _("Loaded %(nrtasks)d tasks from " "%(filename)s")
                % dict(
                    nrtasks=len(self.__task_file.tasks()),
                    filename=self.__task_file.filename(),
                )
            )
        else:
            error_message = (
                _("Cannot open %s because it doesn't exist") % filename
            )
            # Use CallAfter on Mac OS X because otherwise the app will hang:
            if operating_system.isMac():
                wx.CallAfter(
                    showerror, error_message, **self.__error_message_options
                )
            else:
                showerror(error_message, **self.__error_message_options)
            self.__remove_recent_file(filename)

    def merge(self, filename=None, showerror=wx.MessageBox):
        if not filename:
            filename = self.__ask_user_for_file(
                _("Merge"), self.__tsk_file_open_dialog_opts
            )
        if filename:
            try:
                self.__task_file.merge(filename)
            except persistence.xml.reader.XMLReaderTooNewException:
                self.__show_too_new_error_message(filename, showerror)
                return
            except Exception:
                self.__show_generic_error_message(filename, showerror)
                return
            self.__message_callback(
                _("Merged %(filename)s") % dict(filename=filename)
            )
            self.__add_recent_file(filename)

    def save(self, showerror=wx.MessageBox):
        if self.__task_file.filename():
            if self._save_save(self.__task_file, showerror):
                return True
            else:
                return self.save_as(showerror=showerror)
        elif not self.__task_file.isEmpty():
            return self.save_as(showerror=showerror)  # Ask for filename
        else:
            return False

    def merge_disk_changes(self):
        self.__task_file.merge_disk_changes()

    def save_as(
        self,
        filename=None,
        showerror=wx.MessageBox,
        file_exists=os.path.exists,
    ):
        if not filename:
            file_dialog_opts = dict(self.__tsk_file_save_dialog_opts)
            current = self.__task_file.filename()
            if current:
                # Suggest "name copy.tsk" next to the current file
                file_dialog_opts["default_path"] = os.path.dirname(
                    os.path.abspath(current)
                )
                file_dialog_opts["default_filename"] = copy_name(
                    current, file_exists
                )
            filename = self.__ask_user_for_file(
                _("Save as"),
                file_dialog_opts,
                flag=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
                file_exists=file_exists,
            )
            if not filename:
                return False  # User didn't enter a filename, cancel save
        if self._save_save(self.__task_file, showerror, filename):
            return True
        else:
            return self.save_as(showerror=showerror)  # Try again

    def save_selection(
        self,
        tasks,
        filename=None,
        showerror=wx.MessageBox,
        task_file_class=persistence.TaskFile,
        file_exists=os.path.exists,
    ):
        if not filename:
            filename = self.__ask_user_for_file(
                _("Save selection"),
                self.__tsk_file_save_dialog_opts,
                flag=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
                file_exists=file_exists,
            )
            if not filename:
                return False  # User didn't enter a filename, cancel save
        selection_file = self._create_selection_file(tasks, task_file_class)
        if self._save_save(selection_file, showerror, filename):
            return True
        else:
            return self.save_selection(
                tasks, showerror=showerror, task_file_class=task_file_class
            )  # Try again

    def _create_selection_file(self, tasks, task_file_class):
        selection_file = task_file_class()
        # Add the selected tasks:
        selection_file.tasks().extend(tasks)
        # Include categories used by the selected tasks:
        all_categories = set()
        for task in tasks:
            all_categories.update(task.categories())
        # Also include parents of used categories, recursively:
        for category in all_categories.copy():
            all_categories.update(category.ancestors())
        selection_file.categories().extend(all_categories)
        return selection_file

    def _save_save(self, task_file, showerror, filename=None):
        """Save the file and show an error message if saving fails."""
        try:
            if filename:
                task_file.saveas(filename)
            else:
                filename = task_file.filename()
                task_file.save()
            self.__show_save_message(task_file)
            self.__add_recent_file(filename)
            return True
        except resourcelock.LockInUse as in_use:
            showerror(
                resourcelock.in_use_message(filename, in_use.owner),
                **self.__error_message_options
            )
            return False
        except (OSError, IOError) as reason:
            error_message = _("Cannot save %s\n%s") % (
                filename,
                str(reason),
            )
            showerror(error_message, **self.__error_message_options)
            return False

    def save_as_template(self, task):
        templates = persistence.TemplateList(
            self.__settings.pathToTemplatesDir()
        )
        templates.addTemplate(task)
        templates.save()

    def import_template(self, showerror=wx.MessageBox):
        filename = self.__ask_user_for_file(
            _("Import template"),
            file_dialog_opts={
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
                error_message = _("Cannot import template %s\n%s") % (
                    filename,
                    str(reason),
                )
                showerror(error_message, **self.__error_message_options)

    def close(self, force=False):
        if self.__task_file.need_save():
            if force:
                # No user interaction, since we're forced to close right now.
                if self.__task_file.filename():
                    self._save_save(
                        self.__task_file, lambda *args, **kwargs: None
                    )
                else:
                    pass  # No filename, we cannot ask, give up...
            else:
                if not self.__save_unsaved_changes():
                    return False
        self.__close_unconditionally()
        return True

    def export(
        self,
        title,
        file_dialog_opts,
        writer_class,
        viewer,
        selectionOnly,
        openfile=codecs.open,
        showerror=wx.MessageBox,
        filename=None,
        file_exists=os.path.exists,
        **kwargs
    ):
        filename = filename or self.__ask_user_for_file(
            title,
            file_dialog_opts,
            flag=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            file_exists=file_exists,
        )
        if filename:
            fd = self.__open_file_for_writing(filename, openfile, showerror)
            if fd is None:
                return False
            count = writer_class(fd, filename).write(
                viewer, self.__settings, selectionOnly, **kwargs
            )
            fd.close()
            self.__message_callback(
                _("Exported %(count)d items to " "%(filename)s")
                % dict(count=count, filename=filename)
            )
            return True
        else:
            return False

    def export_as_html(
        self,
        viewer,
        selectionOnly=False,
        separateCSS=False,
        columns=None,
        openfile=codecs.open,
        showerror=wx.MessageBox,
        filename=None,
        file_exists=os.path.exists,
        default_filename=None,
    ):
        file_opts = self.__html_file_dialog_opts.copy()
        if default_filename:
            file_opts["default_filename"] = default_filename
        return self.export(
            _("Export as HTML"),
            file_opts,
            persistence.HTMLWriter,
            viewer,
            selectionOnly,
            openfile,
            showerror,
            filename,
            file_exists,
            separateCSS=separateCSS,
            columns=columns,
            taskFile=self.__task_file,
        )

    def export_as_csv(
        self,
        viewer,
        selectionOnly=False,
        separateDateAndTimeColumns=False,
        columns=None,
        file_exists=os.path.exists,
        default_filename=None,
    ):
        file_opts = self.__csv_file_dialog_opts.copy()
        if default_filename:
            file_opts["default_filename"] = default_filename
        return self.export(
            _("Export as CSV"),
            file_opts,
            persistence.CSVWriter,
            viewer,
            selectionOnly,
            separateDateAndTimeColumns=separateDateAndTimeColumns,
            columns=columns,
            file_exists=file_exists,
            taskFile=self.__task_file,
        )

    def export_as_icalendar(
        self,
        viewer,
        selectionOnly=False,
        selectedFields=None,
        default_filename=None,
        file_exists=os.path.exists,
    ):
        # Use default filename if provided
        file_opts = self.__ics_file_dialog_opts.copy()
        if default_filename:
            file_opts["default_filename"] = default_filename
        return self.export(
            _("Export as iCalendar"),
            file_opts,
            persistence.iCalendarWriter,
            viewer,
            selectionOnly,
            file_exists=file_exists,
            selectedFields=selectedFields,
            taskFile=self.__task_file,
        )

    def export_as_todo_txt(
        self,
        viewer,
        selectionOnly=False,
        file_exists=os.path.exists,
        default_filename=None,
    ):
        file_opts = self.__todotxt_file_dialog_opts.copy()
        if default_filename:
            file_opts["default_filename"] = default_filename
        return self.export(
            _("Export as Todo.txt"),
            file_opts,
            persistence.TodoTxtWriter,
            viewer,
            selectionOnly,
            file_exists=file_exists,
            taskFile=self.__task_file,
        )

    def import_csv(self, **kwargs):
        persistence.CSVReader(
            self.__task_file.tasks(), self.__task_file.categories()
        ).read(**kwargs)

    def import_todo_txt(self, filename):
        persistence.TodoTxtReader(
            self.__task_file.tasks(), self.__task_file.categories()
        ).read(filename)

    def filename(self):
        return self.__task_file.filename()

    def __open_file_for_writing(
        self, filename, openfile, showerror, mode="w", encoding="utf-8"
    ):
        try:
            return openfile(filename, mode, encoding)
        except IOError as reason:
            error_message = _("Cannot open %s\n%s") % (
                filename,
                str(reason),
            )
            showerror(error_message, **self.__error_message_options)
            return None

    def __add_recent_file(self, file_name):
        recent_files = self.__settings.getlist("file", "recentfiles")
        if file_name in recent_files:
            recent_files.remove(file_name)
        recent_files.insert(0, file_name)
        maximum_number_of_recent_files = self.__settings.getint(
            "file", "maxrecentfiles"
        )
        recent_files = recent_files[:maximum_number_of_recent_files]
        self.__settings.setlist("file", "recentfiles", recent_files)

    def __remove_recent_file(self, file_name):
        recent_files = self.__settings.getlist("file", "recentfiles")
        if file_name in recent_files:
            recent_files.remove(file_name)
            self.__settings.setlist("file", "recentfiles", recent_files)

    def __ask_user_for_file(
        self,
        title,
        file_dialog_opts,
        flag=wx.FD_OPEN,
        file_exists=os.path.exists,
    ):
        filename = wx.FileSelector(
            title, flags=flag, **file_dialog_opts
        )  # pylint: disable=W0142
        if filename and (flag & wx.FD_SAVE):
            # On Ubuntu, the default extension is not added automatically to
            # a filename typed by the user. Add the extension if necessary.
            extension = os.path.extsep + file_dialog_opts["default_extension"]
            if not filename.endswith(extension):
                filename += extension
                if file_exists(filename):
                    return self.__ask_user_for_overwrite_confirmation(
                        filename, title, file_dialog_opts
                    )
        return filename

    def __ask_user_for_overwrite_confirmation(
        self, filename, title, file_dialog_opts
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
                auto_name = os.path.splitext(filename)[0] + extensions[auto]
                if os.path.exists(auto_name):
                    os.remove(auto_name)
                if os.path.exists(auto_name + "-meta"):
                    os.remove(auto_name + "-meta")
            return filename
        elif result == wx.NO:
            return self.__ask_user_for_file(
                title,
                file_dialog_opts,
                flag=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            )
        else:
            return None

    def __save_unsaved_changes(self):
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

    def __close_unconditionally(self):
        self.__message_callback(_("Closed %s") % self.__task_file.filename())
        self.__task_file.close()
        patterns.CommandHistory().clear()
        gc.collect()

    def __show_save_message(self, saved_file):
        self.__message_callback(
            _("Saved %(nrtasks)d tasks to %(filename)s")
            % {
                "nrtasks": len(saved_file.tasks()),
                "filename": saved_file.filename(),
            }
        )

    def __show_too_new_error_message(self, filename, showerror):
        showerror(
            _(
                "Cannot open %(filename)s\n"
                "because it was created by a newer version of %(name)s.\n"
                "Please upgrade %(name)s."
            )
            % dict(filename=filename, name=meta.name),
            **self.__error_message_options
        )

    def __show_generic_error_message(
        self, filename, showerror, show_backups=False
    ):
        sys.stderr.write("".join(traceback.format_exception(*sys.exc_info())))
        limited_exception = "".join(
            traceback.format_exception(*sys.exc_info(), limit=10)
        )
        message = _("Error while reading %s:\n") % filename + limited_exception
        man = persistence.BackupManifest(self.__settings)
        if show_backups and man.hasBackups(filename):
            message += "\n" + _(
                "The backup manager will now open to allow you to restore\n"
                "an older version of this file."
            )
        showerror(message, **self.__error_message_options)

        if show_backups and man.hasBackups(filename):
            dlg = BackupManagerDialog(None, self.__settings, filename)
            try:
                if dlg.ShowModal() == wx.ID_OK:
                    wx.CallAfter(self.open, dlg.restoredFilename())
            finally:
                dlg.Destroy()

    def __update_default_path(self, filename):
        for options in [
            self.__tsk_file_open_dialog_opts,
            self.__tsk_file_save_dialog_opts,
            self.__csv_file_dialog_opts,
            self.__ics_file_dialog_opts,
            self.__html_file_dialog_opts,
        ]:
            options["default_path"] = os.path.dirname(filename)
