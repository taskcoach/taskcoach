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

# This is the persistence package. It contains classes for reading and
# writing domain objects in different formats such as XML, HTML, iCalendar, ...

from .xml.writer import XMLWriter, TemplateXMLWriter, ChangesXMLWriter
from .xml.reader import XMLReader, TemplateXMLReader, ChangesXMLReader
from .xml.templates import getDefaultTemplates
from .html.writer import HTMLWriter
from .html.generator import viewer2html
from .csv.generator import viewer2csv
from .csv.writer import CSVWriter
from .csv.reader import CSVReader
from .todotxt import TodoTxtReader, TodoTxtWriter
from .icalendar.writer import iCalendarWriter
from .icalendar.ical import VCalendarParser
from .taskfile import TaskFile, LockedTaskFile
from .autosaver import AutoSaver
from .autoimporterexporter import AutoImporterExporter
from .autobackup import AutoBackup, BackupManifest
from .sessiontempfile import get_temp_file
from .templatelist import TemplateList
