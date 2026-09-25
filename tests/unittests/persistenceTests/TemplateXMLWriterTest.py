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

import test, io
from taskcoachlib import persistence, config
from taskcoachlib.domain import task, date
from unittests.asserts import sorted_attributes


class TemplateXMLWriterTestCase(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.fd = io.BytesIO()  # The app writes UTF-8 bytes (SafeWriteFile)
        self.fd.name = "testfile.tsk"
        self.writer = persistence.TemplateXMLWriter(self.fd)
        self.task = task.Task()

    def __writeAndRead(self):
        self.writer.write(self.task)
        return self.fd.getvalue().decode("utf-8")

    def expect_in_xml(self, xml_fragment):
        xml = sorted_attributes(self.__writeAndRead())
        xml_fragment = sorted_attributes(xml_fragment)
        self.assertTrue(
            xml_fragment in xml, "%s not in %s" % (xml_fragment, xml)
        )

    # tests

    def testDefaultTask(self):
        self.expect_in_xml(
            '<tasks>\n<task creationDateTime="%s" id="%s" '
            'status="1" />\n</tasks>'
            % (self.task.creationDateTime(), self.task.id())
        )

    def testTaskWithPlannedStartDateTime(self):
        self.task.setPlannedStartDateTime(
            date.Now() + date.TimeDelta(minutes=31)
        )
        self.expect_in_xml('plannedstartdatetmpl="31 minutes from now')

    def testTaskWithDueDateTime(self):
        self.task.setDueDateTime(date.Now() + date.TimeDelta(minutes=13))
        self.expect_in_xml('duedatetmpl="13 minutes from now')

    def testTaskWithCompletionDateTime(self):
        self.task.setCompletionDateTime(date.Now() + date.TimeDelta(minutes=4))
        self.expect_in_xml('completiondatetmpl="4 minutes from now')

    def testTaskWithReminder(self):
        self.task.setReminder(date.Now() + date.TimeDelta(seconds=10))
        self.expect_in_xml('remindertmpl="0 minutes from now')
