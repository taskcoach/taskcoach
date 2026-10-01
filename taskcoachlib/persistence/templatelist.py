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
from taskcoachlib import meta
from taskcoachlib.meta.debug import log_step
from .xml import TemplateXMLWriter, TemplateXMLReader


class TemplateList(object):
    def __init__(self, path, TemplateReader=TemplateXMLReader, openFile=open):
        self._path = path
        self._templates = self._readTemplates(TemplateReader, openFile)
        self._toDelete = []

    def _readTemplates(self, TemplateReader, openFile):
        templates = []
        for filename in self._templateFilenames():
            template = self._read_template(filename, TemplateReader, openFile)
            if template:
                templates.append((template, filename))
        return templates

    def _read_template(self, filename, template_reader, open_file):
        path = os.path.join(self._path, filename)
        try:
            fd = open_file(path, "r", encoding="utf-8")
        except IOError:
            return None
        try:
            reader = template_reader(fd)
            template = reader.read()
        except Exception as e:
            log_step(
                f"ERROR! Reading template {filename}: {e}", prefix="TEMPLATE"
            )
            import traceback

            traceback.print_exc()
            return None
        finally:
            fd.close()
        if reader.version_needed() > meta.data.tskversion:
            # Saved by this release before it wrote the forms older
            # releases read, which skip it: saved again in them
            # (docs/PERSISTENCE_XML.md, Versions and Compatibility)
            with open(path, "w", encoding="utf-8") as out:
                TemplateXMLWriter(out).write(template)
            log_step(
                "template %s saved again so that releases reading "
                "tskversion %d read it" % (filename, meta.data.tskversion),
                prefix="TEMPLATE",
            )
        return template

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
            template_file = open(
                os.path.join(self._path, name), "w", encoding="utf-8"
            )
            writer = TemplateXMLWriter(template_file)
            writer.write(task)
            template_file.close()

        for task, name in self._toDelete:
            os.remove(os.path.join(self._path, name))
        self._toDelete = []

    def addTemplate(self, task):
        handle, filename = tempfile.mkstemp(".tsktmpl", dir=self._path)
        os.close(handle)
        template_file = open(filename, "w", encoding="utf-8")
        writer = TemplateXMLWriter(template_file)
        writer.write(task.copy())
        template_file.close()
        the_task = TemplateXMLReader(
            open(filename, "r", encoding="utf-8")
        ).read()
        self._templates.append((the_task, os.path.split(filename)[-1]))
        return the_task

    def deleteTemplate(self, idx):
        self._toDelete.append(self._templates[idx])
        del self._templates[idx]

    def copyTemplate(self, filename):
        shutil.copyfile(
            filename, os.path.join(self._path, os.path.split(filename)[-1])
        )

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
