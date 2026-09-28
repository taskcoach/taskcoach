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

import codecs, os
from taskcoachlib import patterns
from . import todotxt


class AutoImporterExporter(object):
    """AutoImporterExporter observes task files. If a task file is saved,
    either by the user or automatically (when autosave is on) and auto
    import and/or export is on, AutoImporterExporter imports and/or exports
    the task file."""

    def __init__(self, settings):
        super().__init__()
        self.__settings = settings
        register = patterns.Publisher().registerObserver
        register(
            self.on_task_file_about_to_save, eventType="taskfile.aboutToSave"
        )
        register(self.on_task_file_read, eventType="taskfile.justRead")

    def on_task_file_read(self, event):
        for task_file in event.sources():
            self.onTaskFileJustRead(task_file)

    def on_task_file_about_to_save(self, event):
        for task_file in event.sources():
            self.onTaskFileAboutToBeSaved(task_file)

    def onTaskFileJustRead(self, taskFile):
        """After a task file has been read and if auto import is on,
        import it."""
        self.importFiles(taskFile)

    def onTaskFileAboutToBeSaved(self, taskFile):
        """When a task file is about to be saved and auto import and/or
        export is on, import and/or export it."""
        self.importFiles(taskFile)
        self.exportFiles(taskFile)

    def importFiles(self, taskFile):
        importFormats = self.__settings.getlist("file", "autoimport")
        for importFormat in importFormats:
            if importFormat == "Todo.txt":
                self.importTodoTxt(taskFile)

    def exportFiles(self, taskFile):
        exportFormats = self.__settings.getlist("file", "autoexport")
        for exportFormat in exportFormats:
            if exportFormat == "Todo.txt":
                self.exportTodoTxt(taskFile)

    @classmethod
    def importTodoTxt(cls, taskFile):
        filename = cls.todoTxtFilename(taskFile)
        if os.path.exists(filename):
            todotxt.TodoTxtReader(
                taskFile.tasks(), taskFile.categories()
            ).read(filename)

    @classmethod
    def exportTodoTxt(cls, taskFile):
        filename = cls.todoTxtFilename(taskFile)
        with codecs.open(filename, "w", "utf-8") as todoFile:
            todotxt.TodoTxtWriter(todoFile, filename).writeTasks(
                taskFile.tasks()
            )

    @staticmethod
    def todoTxtFilename(taskFile):
        return taskFile.filename()[: -len("tsk")] + "txt"
