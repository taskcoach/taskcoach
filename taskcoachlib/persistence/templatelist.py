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

import os, pickle, tempfile, shutil
from pubsub import pub
from .xml import TemplateXMLWriter, TemplateXMLReader


class TemplateList(object):
    def __init__(self, path, TemplateReader=TemplateXMLReader, openFile=open):
        self._path = path
        self._templates = self._readTemplates(TemplateReader, openFile)
        self._toDelete = []

    def _readTemplates(self, TemplateReader, openFile):
        templates = []
        for filename in self._templateFilenames():
            template = self._readTemplate(filename, TemplateReader, openFile)
            if template:
                templates.append((template, filename))
        return templates

    def _readTemplate(self, filename, TemplateReader, openFile):
        try:
            fd = openFile(os.path.join(self._path, filename), "r")
        except IOError:
            return
        try:
            return TemplateReader(fd).read()
        except Exception as e:
            import sys
            print(f"Error reading template {filename}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        finally:
            fd.close()

    def _templateFilenames(self):
        if not os.path.exists(self._path):
            return []
        filenames = [
            name
            for name in os.listdir(self._path)
            if name.endswith(".tsktmpl")
            and os.path.exists(os.path.join(self._path, name))
        ]
        listName = os.path.join(self._path, "list.pickle")
        if os.path.exists(listName):
            try:
                filenames = pickle.load(open(listName, "rb"))
            except (OSError, pickle.UnpicklingError, EOFError):
                pass
        return filenames

    def save(self):
        pickle.dump(
            [name for task, name in self._templates],
            open(os.path.join(self._path, "list.pickle"), "wb"),
        )

        for task, name in self._templates:
            templateFile = open(os.path.join(self._path, name), "w")
            writer = TemplateXMLWriter(templateFile)
            writer.write(task)
            templateFile.close()

        for task, name in self._toDelete:
            os.remove(os.path.join(self._path, name))
        self._toDelete = []
        pub.sendMessage("templates.saved")

    def addTemplate(self, task):
        handle, filename = tempfile.mkstemp(".tsktmpl", dir=self._path)
        os.close(handle)
        templateFile = open(filename, "w")
        writer = TemplateXMLWriter(templateFile)
        writer.write(task.copy())
        templateFile.close()
        theTask = TemplateXMLReader(open(filename, "r")).read()
        self._templates.append((theTask, os.path.split(filename)[-1]))
        return theTask

    def deleteTemplate(self, idx):
        self._toDelete.append(self._templates[idx])
        del self._templates[idx]

    def copyTemplate(self, filename):
        shutil.copyfile(
            filename, os.path.join(self._path, os.path.split(filename)[-1])
        )
        pub.sendMessage("templates.saved")

    def swapTemplates(self, i, j):
        self._templates[i], self._templates[j] = (
            self._templates[j],
            self._templates[i],
        )

    def __len__(self):
        return len(self._templates)

    def tasks(self):
        return [task for task, _ in self._templates]

    def names(self):
        return [name for _, name in self._templates]
